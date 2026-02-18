import type { NextRequest } from 'next/server';

import { dbQuery } from '@/lib/db';
import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import { requireManagementSession, sessionHasAgentAccess } from '@/lib/management-auth';
import { getRequestId } from '@/lib/request-id';

export const runtime = 'nodejs';

function normalizeChainKey(raw: string | null): string {
  const trimmed = String(raw ?? '').trim().toLowerCase();
  return trimmed || 'base_sepolia';
}

function parseLimit(raw: string | null, fallback: number, max: number): number {
  const parsed = Number.parseInt(String(raw ?? ''), 10);
  if (!Number.isFinite(parsed) || parsed < 1) {
    return fallback;
  }
  return Math.min(max, parsed);
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
    if (!sessionHasAgentAccess(auth.session, agentId)) {
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

    const chainKey = normalizeChainKey(req.nextUrl.searchParams.get('chainKey'));
    const limit = parseLimit(req.nextUrl.searchParams.get('limit'), 20, 100);
    const trackedAgentId = req.nextUrl.searchParams.get('trackedAgentId')?.trim() || null;

    const rows = await dbQuery<{
      trade_id: string;
      tracked_agent_id: string;
      agent_name: string;
      chain_key: string;
      status: string;
      pair: string | null;
      token_in: string;
      token_out: string;
      amount_in: string | null;
      amount_out: string | null;
      tx_hash: string | null;
      executed_at: string | null;
      created_at: string;
    }>(
      `
      select
        t.trade_id,
        t.agent_id as tracked_agent_id,
        a.agent_name,
        t.chain_key,
        t.status::text,
        t.pair,
        t.token_in,
        t.token_out,
        t.amount_in::text,
        t.amount_out::text,
        t.tx_hash,
        t.executed_at::text,
        t.created_at::text
      from trades t
      inner join agent_tracked_agents ata
        on ata.agent_id = $1
       and ata.tracked_agent_id = t.agent_id
      inner join agents a
        on a.agent_id = t.agent_id
      where t.status = 'filled'
        and ($2::text = 'all' or t.chain_key = $2)
        and ($3::text is null or t.agent_id = $3)
      order by coalesce(t.executed_at, t.created_at) desc, t.created_at desc
      limit $4
      `,
      [agentId, chainKey, trackedAgentId, limit]
    );

    return successResponse(
      {
        ok: true,
        agentId,
        chainKey,
        items: rows.rows.map((row) => ({
          tradeId: row.trade_id,
          trackedAgentId: row.tracked_agent_id,
          agentName: row.agent_name,
          chainKey: row.chain_key,
          status: row.status,
          pair: row.pair,
          tokenIn: row.token_in,
          tokenOut: row.token_out,
          amountIn: row.amount_in,
          amountOut: row.amount_out,
          txHash: row.tx_hash,
          executedAt: row.executed_at,
          createdAt: row.created_at
        }))
      },
      200,
      requestId
    );
  } catch {
    return internalErrorResponse(requestId);
  }
}
