import type { NextRequest } from 'next/server';

import { getChainConfig } from '@/lib/chains';
import { dbQuery } from '@/lib/db';
import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import { parseIntQuery } from '@/lib/http';
import { enforcePublicReadRateLimit } from '@/lib/rate-limit';
import { getRequestId } from '@/lib/request-id';

export const runtime = 'nodejs';

export async function GET(
  req: NextRequest,
  context: { params: Promise<{ agentId: string }> }
) {
  const requestId = getRequestId(req);

  try {
    const rateLimited = await enforcePublicReadRateLimit(req, requestId);
    if (!rateLimited.ok) {
      return rateLimited.response;
    }

    const { agentId } = await context.params;
    const limit = parseIntQuery(req.nextUrl.searchParams.get('limit'), 50, 1, 200);
    const chainKey = req.nextUrl.searchParams.get('chainKey')?.trim() || '';
    if (chainKey && !getChainConfig(chainKey)) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Invalid chainKey query parameter value.',
          actionHint: 'Provide a supported chain key (or omit chainKey).',
          details: { chainKey }
        },
        requestId
      );
    }

    const rows = await dbQuery<{
      trade_id: string;
      source_trade_id: string | null;
      chain_key: string;
      is_mock: boolean;
      status: string;
      token_in: string;
      token_out: string;
      pair: string;
      amount_in: string | null;
      amount_out: string | null;
      slippage_bps: number | null;
      reason: string | null;
      reason_code: string | null;
      reason_message: string | null;
      tx_hash: string | null;
      mock_receipt_id: string | null;
      executed_at: string | null;
      created_at: string;
      updated_at: string;
    }>(
      `
      select
        trade_id,
        source_trade_id,
        chain_key,
        is_mock,
        status,
        token_in,
        token_out,
        pair,
        amount_in::text,
        amount_out::text,
        slippage_bps,
        reason,
        reason_code,
        reason_message,
        tx_hash,
        mock_receipt_id,
        executed_at::text,
        created_at::text,
        updated_at::text
      from trades
      where agent_id = $1
        and is_mock = false
        and ($3 = '' or chain_key = $3)
      order by created_at desc
      limit $2
      `,
      [agentId, limit, chainKey]
    );

    return successResponse(
      {
        ok: true,
        agentId,
        limit,
        items: rows.rows
          .map((row) => ({
            ...row,
            source_label: row.source_trade_id ? 'copied' : 'self'
          }))
      },
      200,
      requestId
    );
  } catch {
    return internalErrorResponse(requestId);
  }
}
