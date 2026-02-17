import crypto from 'node:crypto';

import type { NextRequest } from 'next/server';

import { authenticateAgentByToken } from '@/lib/agent-auth';
import { getChainConfig } from '@/lib/chains';
import { dbQuery } from '@/lib/db';
import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import { parseJsonBody } from '@/lib/http';
import { makeId } from '@/lib/ids';
import { getRequestId } from '@/lib/request-id';
import { validatePayload } from '@/lib/validation';

export const runtime = 'nodejs';

async function ensureX402ResourceDescriptionColumn(): Promise<void> {
  await dbQuery(`
    alter table if exists agent_x402_payment_mirror
    add column if not exists resource_description text
  `);
}

type AgentX402InboundProposedRequest = {
  schemaVersion: 1;
  networkKey: string;
  facilitatorKey: string;
  assetKind: 'native' | 'erc20';
  assetAddress?: string | null;
  assetSymbol?: string | null;
  amountAtomic: string;
  resourceDescription?: string | null;
};

type ResolvedAsset = {
  assetKind: 'native' | 'erc20';
  assetAddress: string | null;
  assetSymbol: 'ETH' | 'KITE' | 'USDC' | 'WETH' | 'WKITE' | 'USDT';
};

function parseAmountAtomic(value: unknown): string | null {
  const raw = String(value ?? '').trim();
  if (!raw || !/^[0-9]+(\.[0-9]+)?$/.test(raw)) {
    return null;
  }
  return raw;
}

function parseResourceDescription(value: unknown): string | null {
  const raw = String(value ?? '').trim();
  if (!raw) {
    return null;
  }
  if (raw.length > 280) {
    return null;
  }
  return raw;
}

function buildOrigin(req: NextRequest): string {
  const explicit = process.env.XCLAW_PUBLIC_BASE_URL?.trim();
  if (explicit) {
    return explicit.replace(/\/$/, '');
  }
  const forwardedHost = req.headers.get('x-forwarded-host')?.trim();
  const forwardedProto = req.headers.get('x-forwarded-proto')?.trim();
  if (forwardedHost) {
    const proto = forwardedProto && (forwardedProto === 'http' || forwardedProto === 'https') ? forwardedProto : 'https';
    return `${proto}://${forwardedHost}`.replace(/\/$/, '');
  }
  return 'https://xclaw.trade';
}

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
    const nativeSymbol = chainKey === 'kite_ai_testnet' ? 'KITE' : 'ETH';
    return { assetKind: 'native', assetAddress: null, assetSymbol: nativeSymbol };
  }

  const bySymbol = new Map<string, string>();
  for (const [tokenSymbol, tokenAddress] of Object.entries(canonicalTokens)) {
    if (!tokenAddress || typeof tokenAddress !== 'string') {
      continue;
    }
    const normalized = tokenSymbol.trim().toUpperCase();
    if (normalized === 'USDC' || normalized === 'WETH' || normalized === 'WKITE' || normalized === 'USDT') {
      bySymbol.set(normalized, tokenAddress.toLowerCase());
    }
  }

  const requestedAddress = String(assetAddressRaw ?? '').trim().toLowerCase();
  if (symbol && bySymbol.has(symbol)) {
    return { assetKind: 'erc20', assetAddress: bySymbol.get(symbol) ?? null, assetSymbol: symbol as ResolvedAsset['assetSymbol'] };
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

export async function POST(req: NextRequest) {
  const requestId = getRequestId(req);
  try {
    await ensureX402ResourceDescriptionColumn();
    const auth = authenticateAgentByToken(req, requestId);
    if (!auth.ok) {
      return auth.response;
    }

    const parsed = await parseJsonBody(req, requestId);
    if (!parsed.ok) {
      return parsed.response;
    }
    const validated = validatePayload<AgentX402InboundProposedRequest>('agent-x402-inbound-proposed-request.schema.json', parsed.body);
    if (!validated.ok) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'x402 inbound proposed payload does not match schema.',
          actionHint: 'Provide canonical x402 inbound proposed fields.',
          details: validated.details
        },
        requestId
      );
    }

    const body = validated.data;
    const amountAtomic = parseAmountAtomic(body.amountAtomic);
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
    const resourceDescription = parseResourceDescription(body.resourceDescription);
    if (String(body.resourceDescription ?? '').trim() && !resourceDescription) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'resourceDescription must be 280 characters or less.',
          actionHint: 'Use a shorter payment description.'
        },
        requestId
      );
    }

    const resolvedAsset = resolveSupportedAsset(body.networkKey, body.assetKind, body.assetAddress, body.assetSymbol);
    if (!resolvedAsset) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Unsupported x402 asset for selected chain.',
          actionHint:
            body.networkKey === 'kite_ai_testnet'
              ? 'Use KITE, WKITE, or USDT on Kite AI Testnet.'
              : 'Use ETH, USDC, or WETH on supported chain configuration.'
        },
        requestId
      );
    }

    const paymentId = makeId('xpm');
    const linkToken = crypto.randomBytes(10).toString('hex');
    const paymentUrl = `${buildOrigin(req)}/api/v1/x402/pay/${encodeURIComponent(auth.agentId)}/${encodeURIComponent(linkToken)}`;
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
        resource_description,
        payment_url,
        link_token,
        expires_at,
        created_at,
        updated_at,
        terminal_at
      ) values (
        $1, $2, 'inbound', 'proposed', $3, $4, $5, $6, $7, $8::numeric, $9, $10, $11, null, now(), now(), null
      )
      `,
      [
        paymentId,
        auth.agentId,
        body.networkKey,
        body.facilitatorKey,
        resolvedAsset.assetKind,
        resolvedAsset.assetAddress,
        resolvedAsset.assetSymbol,
        amountAtomic,
        resourceDescription,
        paymentUrl,
        linkToken
      ]
    );

    return successResponse(
      {
        ok: true,
        agentId: auth.agentId,
        paymentId,
        networkKey: body.networkKey,
        facilitatorKey: body.facilitatorKey,
        assetKind: resolvedAsset.assetKind,
        assetAddress: resolvedAsset.assetAddress,
        assetSymbol: resolvedAsset.assetSymbol,
        amountAtomic,
        resourceDescription,
        paymentUrl,
        linkToken,
        ttlSeconds: null,
        expiresAt: null,
        timeLimitNotice: 'This payment link does not expire.',
        status: 'proposed',
        requestSource: 'hosted'
      },
      200,
      requestId
    );
  } catch {
    return internalErrorResponse(requestId);
  }
}
