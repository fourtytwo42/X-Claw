import type { NextRequest } from 'next/server';

import { authenticateAgentByToken } from '@/lib/agent-auth';
import { dbQuery } from '@/lib/db';
import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import { getRequestId } from '@/lib/request-id';

export const runtime = 'nodejs';

const STALE_MS = 60 * 1000;

export async function GET(req: NextRequest) {
  const requestId = getRequestId(req);

  try {
    const auth = authenticateAgentByToken(req, requestId);
    if (!auth.ok) {
      return auth.response;
    }

    const chainKey = req.nextUrl.searchParams.get('chainKey')?.trim();
    if (!chainKey) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'chainKey query parameter is required.',
          actionHint: 'Provide ?chainKey=<chain-key>.',
        },
        requestId
      );
    }

    const agentIdQuery = req.nextUrl.searchParams.get('agentId')?.trim();
    if (agentIdQuery && agentIdQuery !== auth.agentId) {
      return errorResponse(
        401,
        {
          code: 'auth_invalid',
          message: 'Requested agentId does not match authenticated agent.',
          actionHint: 'Use your own authenticated agent id.',
        },
        requestId
      );
    }

    const result = await dbQuery<{
      position_id: string;
      chain_key: string;
      dex_key: string;
      position_type: string;
      pool_ref: string;
      token_a: string;
      token_b: string;
      deposited_a: string;
      deposited_b: string;
      current_a: string;
      current_b: string;
      unclaimed_fees_a: string;
      unclaimed_fees_b: string;
      realized_fees_usd: string;
      unrealized_pnl_usd: string;
      position_value_usd: string | null;
      status: string;
      explorer_url: string | null;
      last_synced_at: string;
      updated_at: string;
    }>(
      `
      select
        position_id,
        chain_key,
        dex_key,
        position_type,
        pool_ref,
        token_a,
        token_b,
        deposited_a::text,
        deposited_b::text,
        current_a::text,
        current_b::text,
        unclaimed_fees_a::text,
        unclaimed_fees_b::text,
        realized_fees_usd::text,
        unrealized_pnl_usd::text,
        position_value_usd::text,
        status,
        explorer_url,
        last_synced_at::text,
        updated_at::text
      from liquidity_position_snapshots
      where agent_id = $1
        and chain_key = $2
      order by updated_at desc
      `,
      [auth.agentId, chainKey]
    );

    const now = Date.now();
    return successResponse(
      {
        ok: true,
        agentId: auth.agentId,
        chainKey,
        items: result.rows.map((row) => ({
          positionId: row.position_id,
          chainKey: row.chain_key,
          dex: row.dex_key,
          positionType: row.position_type,
          pool: row.pool_ref,
          tokenA: row.token_a,
          tokenB: row.token_b,
          depositedA: row.deposited_a,
          depositedB: row.deposited_b,
          currentA: row.current_a,
          currentB: row.current_b,
          unclaimedFeesA: row.unclaimed_fees_a,
          unclaimedFeesB: row.unclaimed_fees_b,
          realizedFeesUsd: row.realized_fees_usd,
          unrealizedPnlUsd: row.unrealized_pnl_usd,
          positionValueUsd: row.position_value_usd,
          status: row.status,
          explorerUrl: row.explorer_url,
          lastUpdatedAt: row.updated_at,
          stale: now - new Date(row.last_synced_at).getTime() > STALE_MS,
        })),
      },
      200,
      requestId
    );
  } catch {
    return internalErrorResponse(requestId);
  }
}
