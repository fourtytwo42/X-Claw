import type { NextRequest } from 'next/server';

import { getChainConfig } from '@/lib/chains';
import { dbQuery } from '@/lib/db';
import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import { parseIntQuery } from '@/lib/http';
import { enforcePublicReadRateLimit } from '@/lib/rate-limit';
import { getRequestId } from '@/lib/request-id';

export const runtime = 'nodejs';

function isHexAddress(value: string | null | undefined): value is string {
  return typeof value === 'string' && /^0x[a-fA-F0-9]{40}$/.test(value);
}

function tokenSymbolForAddress(chainKey: string, tokenAddress: string | null): string | null {
  if (!isHexAddress(tokenAddress)) {
    return null;
  }

  const cfg = getChainConfig(chainKey);
  const tokens = cfg?.canonicalTokens ?? {};
  const match = Object.entries(tokens).find(([, address]) => String(address).toLowerCase() === tokenAddress.toLowerCase());
  return match?.[0] ?? null;
}

export async function GET(req: NextRequest) {
  const requestId = getRequestId(req);

  try {
    const rateLimited = await enforcePublicReadRateLimit(req, requestId);
    if (!rateLimited.ok) {
      return rateLimited.response;
    }

    const limit = parseIntQuery(req.nextUrl.searchParams.get('limit'), 100, 1, 500);
    const agentId = (req.nextUrl.searchParams.get('agentId') ?? '').trim();
    if (agentId && !/^[a-zA-Z0-9_-]{1,128}$/.test(agentId)) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'agentId query parameter is invalid.',
          actionHint: 'Use a valid agentId and retry.'
        },
        requestId
      );
    }

    const rows = await dbQuery<{
      event_id: string;
      agent_id: string;
      agent_name: string;
      trade_id: string | null;
      event_type: string;
      payload: Record<string, unknown>;
      chain_key: string;
      pair: string | null;
      token_in: string | null;
      token_out: string | null;
      created_at: string;
    }>(
      `
      select
        ev.event_id,
        ev.agent_id,
        a.agent_name,
        ev.trade_id,
        ev.event_type,
        ev.payload,
        coalesce(t.chain_key, nullif(ev.payload->>'chainKey', ''), 'base_sepolia') as chain_key,
        coalesce(t.pair, nullif(ev.payload->>'pair', '')) as pair,
        coalesce(t.token_in, nullif(ev.payload->>'tokenIn', ''), nullif(ev.payload->>'tokenAddress', '')) as token_in,
        coalesce(t.token_out, nullif(ev.payload->>'tokenOut', '')) as token_out,
        ev.created_at::text
      from agent_events ev
      inner join agents a on a.agent_id = ev.agent_id
      left join trades t on t.trade_id = ev.trade_id
      where (ev.event_type::text like 'trade_%' or ev.event_type::text like 'policy_%')
        and ($2 = '' or ev.agent_id = $2)
      order by ev.created_at desc
      limit $1
      `,
      [limit, agentId]
    );

    const items = rows.rows.map((row) => {
      const tokenInSymbol = tokenSymbolForAddress(row.chain_key, row.token_in);
      const tokenOutSymbol = tokenSymbolForAddress(row.chain_key, row.token_out);

      let pairDisplay: string | null = row.pair;
      if (row.pair && row.pair.includes('/')) {
        const [leftRaw, rightRaw] = row.pair.split('/', 2).map((value) => value.trim());
        const leftSymbol = tokenSymbolForAddress(row.chain_key, leftRaw) ?? leftRaw;
        const rightSymbol = tokenSymbolForAddress(row.chain_key, rightRaw) ?? rightRaw;
        pairDisplay = `${leftSymbol}/${rightSymbol}`;
      } else if (!pairDisplay && tokenInSymbol && tokenOutSymbol) {
        pairDisplay = `${tokenInSymbol}/${tokenOutSymbol}`;
      }

      return {
        ...row,
        token_in_symbol: tokenInSymbol,
        token_out_symbol: tokenOutSymbol,
        pair_display: pairDisplay
      };
    });

    return successResponse(
      {
        ok: true,
        limit,
        agentId: agentId || null,
        items
      },
      200,
      requestId
    );
  } catch {
    return internalErrorResponse(requestId);
  }
}
