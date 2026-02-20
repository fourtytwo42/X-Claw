import type { NextRequest } from 'next/server';

import { authenticateAgentByToken } from '@/lib/agent-auth';
import { dbQuery } from '@/lib/db';
import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import { parseJsonBody } from '@/lib/http';
import { makeId } from '@/lib/ids';
import { getRequestId } from '@/lib/request-id';
import { validatePayload } from '@/lib/validation';

export const runtime = 'nodejs';

type AgentTrackedTokensMirrorRequest = {
  agentId: string;
  chainKey: string;
  tokens: Array<{
    token: string;
    symbol?: string | null;
    name?: string | null;
    decimals?: number | null;
  }>;
};

function normalizeAddress(value: unknown): string {
  const normalized = String(value ?? '').trim().toLowerCase();
  return /^0x[a-f0-9]{40}$/.test(normalized) ? normalized : '';
}

export async function POST(req: NextRequest) {
  const requestId = getRequestId(req);
  try {
    const auth = authenticateAgentByToken(req, requestId);
    if (!auth.ok) {
      return auth.response;
    }

    const parsed = await parseJsonBody(req, requestId);
    if (!parsed.ok) {
      return parsed.response;
    }

    const validated = validatePayload<AgentTrackedTokensMirrorRequest>('agent-tracked-tokens-mirror-request.schema.json', parsed.body);
    if (!validated.ok) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Tracked tokens mirror payload does not match schema.',
          actionHint: 'Provide agentId, chainKey, and tokens[] with token addresses.',
          details: validated.details,
        },
        requestId
      );
    }

    const body = validated.data;
    if (body.agentId !== auth.agentId) {
      return errorResponse(
        401,
        {
          code: 'auth_invalid',
          message: 'agentId does not match authenticated agent.',
          actionHint: 'Use the authenticated agentId.',
        },
        requestId
      );
    }

    const chainKey = String(body.chainKey || '').trim();
    const deduped = new Map<string, { symbol: string | null; name: string | null; decimals: number | null }>();
    for (const row of body.tokens ?? []) {
      const tokenAddress = normalizeAddress(row?.token);
      if (!tokenAddress) {
        continue;
      }
      const symbol = String(row?.symbol ?? '').trim() || null;
      const name = String(row?.name ?? '').trim() || null;
      const decimalsRaw = row?.decimals;
      const decimals =
        typeof decimalsRaw === 'number' && Number.isInteger(decimalsRaw) && decimalsRaw >= 0 && decimalsRaw <= 255
          ? decimalsRaw
          : null;
      deduped.set(tokenAddress, { symbol, name, decimals });
    }

    const tokenAddresses = Array.from(deduped.keys());
    await dbQuery(
      `
      delete from agent_tracked_tokens
      where agent_id = $1
        and chain_key = $2
        and not (token_address = any($3::text[]))
      `,
      [auth.agentId, chainKey, tokenAddresses.length > 0 ? tokenAddresses : ['']]
    );

    for (const tokenAddress of tokenAddresses) {
      const meta = deduped.get(tokenAddress) ?? { symbol: null, name: null, decimals: null };
      await dbQuery(
        `
        insert into agent_tracked_tokens (
          tracked_token_id, agent_id, chain_key, token_address, symbol, name, decimals, source, created_at, updated_at
        ) values ($1, $2, $3, $4, $5, $6, $7, 'runtime', now(), now())
        on conflict (agent_id, chain_key, token_address)
        do update set
          symbol = excluded.symbol,
          name = excluded.name,
          decimals = excluded.decimals,
          source = excluded.source,
          updated_at = now()
        `,
        [makeId('ttk'), auth.agentId, chainKey, tokenAddress, meta.symbol, meta.name, meta.decimals]
      );
    }

    return successResponse(
      {
        ok: true,
        agentId: auth.agentId,
        chainKey,
        count: tokenAddresses.length,
        items: tokenAddresses.map((tokenAddress) => ({
          tokenAddress,
          symbol: deduped.get(tokenAddress)?.symbol ?? null,
          name: deduped.get(tokenAddress)?.name ?? null,
          decimals: deduped.get(tokenAddress)?.decimals ?? null,
        })),
      },
      200,
      requestId
    );
  } catch {
    return internalErrorResponse(requestId);
  }
}
