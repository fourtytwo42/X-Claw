import crypto from 'node:crypto';

import type { NextRequest } from 'next/server';

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
    const assetKind = req.nextUrl.searchParams.get('assetKind')?.trim() === 'erc20' ? 'erc20' : 'native';
    const assetAddressRaw = req.nextUrl.searchParams.get('assetAddress')?.trim();
    const assetAddress = assetKind === 'erc20' ? assetAddressRaw || null : null;
    const amountAtomic = req.nextUrl.searchParams.get('amountAtomic')?.trim() || '0.01';
    const active = await dbQuery<{
      payment_id: string;
      network_key: string;
      facilitator_key: string;
      asset_kind: 'native' | 'erc20';
      asset_address: string | null;
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
          amount_atomic = $4::numeric,
          payment_url = $5,
          reason_code = null,
          reason_message = null,
          expires_at = null,
          updated_at = $6::timestamptz,
          terminal_at = null
        where payment_id = $7
        `,
        [facilitatorKey, assetKind, assetAddress, amountAtomic, paymentUrl, isoNow(), paymentId]
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
          amount_atomic,
          payment_url,
          link_token,
          expires_at,
          created_at,
          updated_at,
          terminal_at
        ) values (
          $1, $2, 'inbound', 'proposed', $3, $4, $5, $6, $7::numeric, $8, null, null, $9::timestamptz, $10::timestamptz, null
        )
        `,
        [paymentId, agentId, chainKey, facilitatorKey, assetKind, assetAddress, amountAtomic, paymentUrl, isoNow(), isoNow()]
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
        assetKind,
        assetAddress,
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
  amountAtomic?: string;
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
    const assetKind = body.assetKind === 'erc20' ? 'erc20' : 'native';
    const assetAddress = assetKind === 'erc20' ? String(body.assetAddress ?? '').trim() || null : null;
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
        amount_atomic,
        payment_url,
        link_token,
        expires_at,
        created_at,
        updated_at,
        terminal_at
      ) values (
        $1, $2, 'inbound', 'proposed', $3, $4, $5, $6, $7::numeric, $8, $9, null, now(), now(), null
      )
      `,
      [paymentId, agentId, chainKey, facilitatorKey, assetKind, assetAddress, amountAtomic, paymentUrl, linkToken]
    );

    return successResponse(
      {
        ok: true,
        agentId,
        chainKey,
        paymentId,
        networkKey: chainKey,
        facilitatorKey,
        assetKind,
        assetAddress,
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
