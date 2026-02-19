import type { NextRequest } from 'next/server';

import { authenticateAgentByToken } from '@/lib/agent-auth';
import { dbQuery } from '@/lib/db';
import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import { parseIntQuery } from '@/lib/http';
import { getRequestId } from '@/lib/request-id';

export const runtime = 'nodejs';

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
    const limit = parseIntQuery(req.nextUrl.searchParams.get('limit'), 25, 1, 100);
    const result = await dbQuery<{
      liquidity_intent_id: string;
      chain_key: string;
      dex_key: string;
      action_type: string;
      position_type: string;
      status: string;
      token_a: string | null;
      token_b: string | null;
      amount_a: string | null;
      amount_b: string | null;
      slippage_bps: number | null;
      position_ref: string | null;
      created_at: string;
      updated_at: string;
    }>(
      `
      select
        liquidity_intent_id,
        chain_key,
        dex_key,
        action_type,
        position_type,
        status,
        token_a,
        token_b,
        amount_a::text,
        amount_b::text,
        slippage_bps,
        position_ref,
        created_at::text,
        updated_at::text
      from liquidity_intents
      where agent_id = $1
        and chain_key = $2
        and status in ('approved', 'failed')
      order by created_at asc
      limit $3
      `,
      [auth.agentId, chainKey, limit]
    );
    return successResponse(
      {
        ok: true,
        agentId: auth.agentId,
        chainKey,
        limit,
        items: result.rows.map((row) => ({
          liquidityIntentId: row.liquidity_intent_id,
          chainKey: row.chain_key,
          dex: row.dex_key,
          action: row.action_type,
          positionType: row.position_type,
          status: row.status,
          tokenA: row.token_a,
          tokenB: row.token_b,
          amountA: row.amount_a,
          amountB: row.amount_b,
          slippageBps: row.slippage_bps,
          positionRef: row.position_ref,
          createdAt: row.created_at,
          updatedAt: row.updated_at,
        })),
      },
      200,
      requestId
    );
  } catch {
    return internalErrorResponse(requestId);
  }
}
