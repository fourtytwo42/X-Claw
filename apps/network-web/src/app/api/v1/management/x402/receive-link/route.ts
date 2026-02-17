import crypto from 'node:crypto';

import type { NextRequest } from 'next/server';

import { getChainConfig } from '@/lib/chains';
import { dbQuery } from '@/lib/db';
import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import { parseJsonBody } from '@/lib/http';
import { makeId } from '@/lib/ids';
import { requireManagementSession, requireManagementWriteAuth } from '@/lib/management-auth';
import { getRequestId } from '@/lib/request-id';

export const runtime = 'nodejs';

function isoNow(): string {
  return new Date().toISOString();
}

function buildOrigin(req: NextRequest): string {
  const explicit = process.env.XCLAW_PUBLIC_BASE_URL?.trim();
  if (explicit) {
    return explicit.replace(/\/$/, '');
  }
  return req.nextUrl.origin.replace(/\/$/, '');
}

function parseAmountAtomic(value: unknown): string | null {
  const raw = String(value ?? '').trim();
  if (!raw) {
    return null;
  }
  if (!/^[0-9]+(\.[0-9]+)?$/.test(raw)) {
    return null;
  }
  return raw;
}

type ResolvedAsset = {
  assetKind: 'native' | 'erc20';
  assetAddress: string | null;
  assetSymbol: 'ETH' | 'USDC' | 'WETH';
};

function resolveSupportedAsset(
  chainKey: string,
  assetKindRaw: unknown,
  assetAddressRaw: unknown,
  assetSymbolRaw: unknown
): ResolvedAsset | null {
  const config = getChainConfig(chainKey);
  if (!config) {
    return null;
  }
  const canonicalTokens = config.canonicalTokens ?? {};
  const assetKind = assetKindRaw === 'erc20' ? 'erc20' : 'native';
  const symbol = String(assetSymbolRaw ?? '').trim().toUpperCase();
  if (assetKind === 'native') {
    return { assetKind: 'native', assetAddress: null, assetSymbol: 'ETH' };
  }

  const bySymbol = new Map<string, string>();
  for (const [tokenSymbol, tokenAddress] of Object.entries(canonicalTokens)) {
    if (!tokenAddress || typeof tokenAddress !== 'string') {
      continue;
    }
    const normalized = tokenSymbol.trim().toUpperCase();
    if (normalized === 'USDC' || normalized === 'WETH') {
      bySymbol.set(normalized, tokenAddress.toLowerCase());
    }
  }

  const requestedAddress = String(assetAddressRaw ?? '').trim().toLowerCase();
  if (symbol && bySymbol.has(symbol)) {
    return { assetKind: 'erc20', assetAddress: bySymbol.get(symbol) ?? null, assetSymbol: symbol as 'USDC' | 'WETH' };
  }
  if (requestedAddress) {
    for (const [knownSymbol, knownAddress] of bySymbol.entries()) {
      if (knownAddress === requestedAddress) {
        return { assetKind: 'erc20', assetAddress: knownAddress, assetSymbol: knownSymbol as 'USDC' | 'WETH' };
      }
    }
  }
  return null;
}

export async function GET(req: NextRequest) {
  const requestId = getRequestId(req);
  try {
    const agentId = req.nextUrl.searchParams.get('agentId')?.trim();
    if (!agentId) {
      return errorResponse(
        400,
        { code: 'payload_invalid', message: 'agentId query parameter is required.', actionHint: 'Provide ?agentId=<agent-id>.' },
        requestId
      );
    }

    const auth = await requireManagementSession(req, requestId);
    if (!auth.ok) {
      return auth.response;
    }
    if (auth.session.agentId !== agentId) {
      return errorResponse(
        401,
        {
          code: 'auth_invalid',
          message: 'Management session is not authorized for this agent.',
          actionHint: 'Use the matching agent management session.'
        },
        requestId
      );
    }

    const chainKey = req.nextUrl.searchParams.get('chainKey')?.trim() || 'base_sepolia';
    const facilitatorKey = req.nextUrl.searchParams.get('facilitatorKey')?.trim() || 'cdp';
    const resolvedAsset = resolveSupportedAsset(
      chainKey,
      req.nextUrl.searchParams.get('assetKind')?.trim(),
      req.nextUrl.searchParams.get('assetAddress')?.trim(),
      req.nextUrl.searchParams.get('assetSymbol')?.trim()
    );
    if (!resolvedAsset) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Unsupported x402 asset for selected chain.',
          actionHint: 'Use ETH, USDC, or WETH on supported chain configuration.'
        },
        requestId
      );
    }
    const amountAtomic = req.nextUrl.searchParams.get('amountAtomic')?.trim() || '0.01';
    const active = await dbQuery<{
      payment_id: string;
      network_key: string;
      facilitator_key: string;
      asset_kind: 'native' | 'erc20';
      asset_address: string | null;
      asset_symbol: string | null;
      amount_atomic: string;
      payment_url: string | null;
      link_token: string | null;
      status: string;
      terminal_at: string | null;
      created_at: string;
      updated_at: string;
    }>(
      `
      select
        payment_id,
        network_key,
        facilitator_key,
        asset_kind::text,
        asset_address,
        asset_symbol,
        amount_atomic::text,
        payment_url,
        link_token,
        status::text,
        terminal_at::text,
        created_at::text,
        updated_at::text
      from agent_x402_payment_mirror
      where agent_id = $1
        and direction = 'inbound'
        and network_key = $2
        and link_token is null
        and status in ('proposed', 'executing')
      order by created_at desc
      limit 1
      `,
      [agentId, chainKey]
    );

    const origin = buildOrigin(req);
    let paymentId: string;
    let paymentUrl: string;
    let status: string;
    const staticPath = `/api/v1/x402/pay/${encodeURIComponent(agentId)}`;
    paymentUrl = `${origin}${staticPath}`;

    if ((active.rowCount ?? 0) > 0 && active.rows[0].payment_url) {
      paymentId = active.rows[0].payment_id;
      status = active.rows[0].status;
      await dbQuery(
        `
        update agent_x402_payment_mirror
        set
          facilitator_key = $1,
          asset_kind = $2,
          asset_address = $3,
          asset_symbol = $4,
          amount_atomic = $5::numeric,
          payment_url = $6,
          reason_code = null,
          reason_message = null,
          expires_at = null,
          updated_at = $7::timestamptz,
          terminal_at = null
        where payment_id = $8
        `,
        [
          facilitatorKey,
          resolvedAsset.assetKind,
          resolvedAsset.assetAddress,
          resolvedAsset.assetSymbol,
          amountAtomic,
          paymentUrl,
          isoNow(),
          paymentId
        ]
      );
    } else {
      paymentId = makeId('xpm');
      status = 'proposed';
      await dbQuery(
        `
        insert into agent_x402_payment_mirror (
          payment_id,
          agent_id,
          direction,
          status,
          network_key,
          facilitator_key,
          asset_kind,
          asset_address,
          asset_symbol,
          amount_atomic,
          payment_url,
          link_token,
          expires_at,
          created_at,
          updated_at,
          terminal_at
        ) values (
          $1, $2, 'inbound', 'proposed', $3, $4, $5, $6, $7, $8::numeric, $9, null, null, $10::timestamptz, $11::timestamptz, null
        )
        `,
        [
          paymentId,
          agentId,
          chainKey,
          facilitatorKey,
          resolvedAsset.assetKind,
          resolvedAsset.assetAddress,
          resolvedAsset.assetSymbol,
          amountAtomic,
          paymentUrl,
          isoNow(),
          isoNow()
        ]
      );
    }

    return successResponse(
      {
        ok: true,
        agentId,
        chainKey,
        paymentId,
        networkKey: chainKey,
        facilitatorKey,
        assetKind: resolvedAsset.assetKind,
        assetAddress: resolvedAsset.assetAddress,
        assetSymbol: resolvedAsset.assetSymbol,
        amountAtomic,
        paymentUrl,
        ttlSeconds: null,
        expiresAt: null,
        timeLimitNotice: 'This payment link does not expire.',
        status
      },
      200,
      requestId
    );
  } catch {
    return internalErrorResponse(requestId);
  }
}

type CreateReceiveRequestBody = {
  agentId?: string;
  chainKey?: string;
  facilitatorKey?: string;
  assetKind?: 'native' | 'erc20';
  assetAddress?: string | null;
  assetSymbol?: string;
  amountAtomic?: string;
};

type DeleteReceiveRequestBody = {
  agentId?: string;
  paymentId?: string;
};

export async function POST(req: NextRequest) {
  const requestId = getRequestId(req);
  try {
    const parsed = await parseJsonBody(req, requestId);
    if (!parsed.ok) {
      return parsed.response;
    }
    const body = (parsed.body ?? {}) as CreateReceiveRequestBody;
    const agentId = String(body.agentId ?? '').trim();
    if (!agentId) {
      return errorResponse(
        400,
        { code: 'payload_invalid', message: 'agentId is required.', actionHint: 'Provide agentId in request body.' },
        requestId
      );
    }

    const auth = await requireManagementWriteAuth(req, requestId, agentId);
    if (!auth.ok) {
      return auth.response;
    }

    const chainKey = String(body.chainKey ?? 'base_sepolia').trim() || 'base_sepolia';
    const facilitatorKey = String(body.facilitatorKey ?? 'cdp').trim() || 'cdp';
    const resolvedAsset = resolveSupportedAsset(chainKey, body.assetKind, body.assetAddress, body.assetSymbol);
    if (!resolvedAsset) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Unsupported x402 asset for selected chain.',
          actionHint: 'Use ETH, USDC, or WETH on supported chain configuration.'
        },
        requestId
      );
    }
    const amountAtomic = parseAmountAtomic(body.amountAtomic ?? '0.01');
    if (!amountAtomic) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'amountAtomic must be a positive numeric string.',
          actionHint: 'Use values like 0.01 or 1.'
        },
        requestId
      );
    }

    const paymentId = makeId('xpm');
    const linkToken = crypto.randomBytes(10).toString('hex');
    const paymentUrl = `${buildOrigin(req)}/api/v1/x402/pay/${encodeURIComponent(agentId)}/${encodeURIComponent(linkToken)}`;
    await dbQuery(
      `
      insert into agent_x402_payment_mirror (
        payment_id,
        agent_id,
        direction,
        status,
        network_key,
        facilitator_key,
        asset_kind,
        asset_address,
        asset_symbol,
        amount_atomic,
        payment_url,
        link_token,
        expires_at,
        created_at,
        updated_at,
        terminal_at
      ) values (
        $1, $2, 'inbound', 'proposed', $3, $4, $5, $6, $7, $8::numeric, $9, $10, null, now(), now(), null
      )
      `,
      [
        paymentId,
        agentId,
        chainKey,
        facilitatorKey,
        resolvedAsset.assetKind,
        resolvedAsset.assetAddress,
        resolvedAsset.assetSymbol,
        amountAtomic,
        paymentUrl,
        linkToken
      ]
    );

    return successResponse(
      {
        ok: true,
        agentId,
        chainKey,
        paymentId,
        networkKey: chainKey,
        facilitatorKey,
        assetKind: resolvedAsset.assetKind,
        assetAddress: resolvedAsset.assetAddress,
        assetSymbol: resolvedAsset.assetSymbol,
        amountAtomic,
        paymentUrl,
        linkToken,
        ttlSeconds: null,
        expiresAt: null,
        timeLimitNotice: 'This payment link does not expire.',
        status: 'proposed'
      },
      200,
      requestId
    );
  } catch {
    return internalErrorResponse(requestId);
  }
}

export async function DELETE(req: NextRequest) {
  const requestId = getRequestId(req);
  try {
    const parsed = await parseJsonBody(req, requestId);
    if (!parsed.ok) {
      return parsed.response;
    }
    const body = (parsed.body ?? {}) as DeleteReceiveRequestBody;
    const agentId = String(body.agentId ?? '').trim();
    const paymentId = String(body.paymentId ?? '').trim();
    if (!agentId || !paymentId) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'agentId and paymentId are required.',
          actionHint: 'Provide both agentId and paymentId in request body.'
        },
        requestId
      );
    }

    const auth = await requireManagementWriteAuth(req, requestId, agentId);
    if (!auth.ok) {
      return auth.response;
    }

    const updated = await dbQuery(
      `
      update agent_x402_payment_mirror
      set
        status = 'expired',
        reason_code = 'request_deleted',
        reason_message = 'Deleted by owner.',
        updated_at = now(),
        terminal_at = now()
      where payment_id = $1
        and agent_id = $2
        and direction = 'inbound'
        and status in ('proposed', 'executing')
      returning payment_id
      `,
      [paymentId, agentId]
    );

    if ((updated.rowCount ?? 0) === 0) {
      return errorResponse(
        404,
        {
          code: 'payload_invalid',
          message: 'Active x402 receive request not found.',
          actionHint: 'Refresh receive requests and retry.'
        },
        requestId
      );
    }

    return successResponse(
      {
        ok: true,
        agentId,
        paymentId,
        status: 'expired',
        message: 'x402 receive request removed from active queue.'
      },
      200,
      requestId
    );
  } catch {
    return internalErrorResponse(requestId);
  }
}
