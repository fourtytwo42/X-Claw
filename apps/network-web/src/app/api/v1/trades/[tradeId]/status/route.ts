import type { NextRequest } from 'next/server';

import { authenticateAgentByToken } from '@/lib/agent-auth';
import { withTransaction } from '@/lib/db';
import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import { parseJsonBody } from '@/lib/http';
import { ensureIdempotency, storeIdempotencyResponse } from '@/lib/idempotency';
import { makeId } from '@/lib/ids';
import { getRequestId } from '@/lib/request-id';
import { requireAgentChainEnabled } from '@/lib/agent-chain-policy';
import { eventTypeForTradeStatus, isAllowedTransition } from '@/lib/trade-state';
import { validatePayload } from '@/lib/validation';
import { generateCopyIntentsForLeaderFill, syncCopyIntentFromTradeStatus } from '@/lib/copy-lifecycle';
import { recomputeMetricsForAgents } from '@/lib/metrics';

export const runtime = 'nodejs';

type TradeStatusRequest = {
  tradeId: string;
  fromStatus: string;
  toStatus: string;
  amountIn?: string | null;
  amountOut?: string | null;
  reasonCode?: string | null;
  reasonMessage?: string | null;
  txHash?: string | null;
  mockReceiptId?: string | null;
  errorMessage?: string | null;
  at: string;
};

export async function POST(
  req: NextRequest,
  context: { params: Promise<{ tradeId: string }> }
) {
  const requestId = getRequestId(req);

  try {
    const { tradeId: pathTradeId } = await context.params;

    const parsed = await parseJsonBody(req, requestId);
    if (!parsed.ok) {
      return parsed.response;
    }

    const validated = validatePayload<TradeStatusRequest>('trade-status.schema.json', parsed.body);
    if (!validated.ok) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Trade status payload does not match schema.',
          actionHint: 'Check trade status fields and required timestamps.',
          details: validated.details
        },
        requestId
      );
    }

    const body = validated.data;

    if (body.tradeId !== pathTradeId) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Path tradeId must match body tradeId.',
          actionHint: 'Use the same tradeId in URL and JSON body.'
        },
        requestId
      );
    }

    const auth = authenticateAgentByToken(req, requestId);
    if (!auth.ok) {
      return auth.response;
    }

    const idempotency = await ensureIdempotency(req, 'trade_status', auth.agentId, body, requestId);
    if (!idempotency.ok) {
      return idempotency.response;
    }

    if (idempotency.ctx.replayResponse) {
      return successResponse(idempotency.ctx.replayResponse.body, idempotency.ctx.replayResponse.status, requestId);
    }

    const updateResult = await withTransaction(async (client) => {
      const trade = await client.query<{
        agent_id: string;
        chain_key: string;
        mode: string;
        status: string;
        amount_in: string | null;
        amount_out: string | null;
        tx_hash: string | null;
      }>(
        'select agent_id, chain_key, mode, status, amount_in, amount_out, tx_hash from trades where trade_id = $1',
        [pathTradeId]
      );

      if (trade.rowCount === 0) {
        return { ok: false as const, kind: 'missing_trade' as const };
      }

      const row = trade.rows[0];
      const resolvedTxHash = body.txHash ?? row.tx_hash;
      const resolvedAmountOut = body.amountOut ?? row.amount_out;

      if (row.agent_id !== auth.agentId) {
        return { ok: false as const, kind: 'auth_mismatch' as const };
      }

      // Prevent execution-related transitions when owner has disabled this chain for the agent.
      if (['executing', 'verifying', 'filled'].includes(body.toStatus)) {
        const chainGate = await requireAgentChainEnabled(client, { agentId: row.agent_id, chainKey: row.chain_key });
        if (!chainGate.ok) {
          return { ok: false as const, kind: 'chain_disabled' as const, violation: chainGate.violation };
        }
      }

      if (row.status !== body.fromStatus) {
        return {
          ok: false as const,
          kind: 'state_mismatch' as const,
          currentStatus: row.status
        };
      }

      if (!isAllowedTransition(body.fromStatus, body.toStatus)) {
        return {
          ok: false as const,
          kind: 'invalid_transition' as const,
          currentStatus: row.status
        };
      }

      if (row.mode === 'real' && ['executing', 'verifying', 'filled'].includes(body.toStatus) && !resolvedTxHash) {
        return {
          ok: false as const,
          kind: 'missing_tx_hash' as const
        };
      }

      if (body.toStatus === 'filled' && !resolvedAmountOut) {
        return {
          ok: false as const,
          kind: 'missing_amount_out' as const
        };
      }

      await client.query(
        `
        update trades
        set
          status = $1::trade_status,
          reason_code = $2,
          reason_message = $3,
          tx_hash = coalesce($4, tx_hash),
          mock_receipt_id = coalesce($5, mock_receipt_id),
          error_message = coalesce($6, error_message),
          amount_in = coalesce($7, amount_in),
          amount_out = coalesce($8, amount_out),
          executed_at = case when $1::trade_status in ('filled', 'failed') then $9::timestamptz else executed_at end,
          updated_at = now()
        where trade_id = $10
        `,
        [
          body.toStatus,
          body.reasonCode ?? null,
          body.reasonMessage ?? null,
          body.txHash ?? null,
          body.mockReceiptId ?? null,
          body.errorMessage ?? null,
          body.amountIn ?? null,
          body.amountOut ?? null,
          body.at,
          pathTradeId
        ]
      );

      await client.query(
        `
        insert into agent_events (event_id, agent_id, trade_id, event_type, payload, created_at)
        values ($1, $2, $3, $4, $5::jsonb, $6::timestamptz)
        `,
        [
          makeId('evt'),
          auth.agentId,
          pathTradeId,
          eventTypeForTradeStatus(body.toStatus),
          JSON.stringify({
            fromStatus: body.fromStatus,
            toStatus: body.toStatus,
            reasonCode: body.reasonCode ?? null,
            reasonMessage: body.reasonMessage ?? null,
            amountIn: body.amountIn ?? null,
            amountOut: body.amountOut ?? null,
            txHash: body.txHash ?? null,
            mockReceiptId: body.mockReceiptId ?? null
          }),
          body.at
        ]
      );

      const affectedAgents = new Set<string>([auth.agentId]);
      const copySyncAgents = await syncCopyIntentFromTradeStatus(
        client,
        pathTradeId,
        body.toStatus,
        body.reasonCode ?? null,
        body.reasonMessage ?? null
      );
      for (const agentId of copySyncAgents) {
        affectedAgents.add(agentId);
      }

      if (body.toStatus === 'filled') {
        const generatedAgents = await generateCopyIntentsForLeaderFill(client, pathTradeId, auth.agentId, body.at);
        for (const agentId of generatedAgents) {
          affectedAgents.add(agentId);
        }
      }

      if (['filled', 'failed', 'verification_timeout', 'rejected', 'expired'].includes(body.toStatus)) {
        await recomputeMetricsForAgents(client, [...affectedAgents]);
      }

      return { ok: true as const };
    });

    if (!updateResult.ok) {
      if (updateResult.kind === 'missing_trade') {
        return errorResponse(
          404,
          {
            code: 'payload_invalid',
            message: 'Trade was not found for status update.',
            actionHint: 'Verify tradeId before retrying.'
          },
          requestId
        );
      }

      if (updateResult.kind === 'auth_mismatch') {
        return errorResponse(
          401,
          {
            code: 'auth_invalid',
            message: 'Authenticated agent is not allowed to update this trade.',
            actionHint: 'Use the bearer token for the trade owner agent.'
          },
          requestId
        );
      }

      if (updateResult.kind === 'chain_disabled') {
        return errorResponse(
          400,
          {
            code: updateResult.violation.code,
            message: updateResult.violation.message,
            actionHint: updateResult.violation.actionHint,
            details: updateResult.violation.details
          },
          requestId
        );
      }

      if (updateResult.kind === 'state_mismatch') {
        return errorResponse(
          409,
          {
            code: 'trade_invalid_transition',
            message: 'Trade status update rejected because fromStatus does not match current state.',
            actionHint: 'Refresh trade state and retry with the correct fromStatus.',
            details: { currentStatus: updateResult.currentStatus }
          },
          requestId
        );
      }

      if (updateResult.kind === 'missing_tx_hash') {
        return errorResponse(
          400,
          {
            code: 'payload_invalid',
            message: 'txHash is required for real-mode execution transitions.',
            actionHint: 'Include txHash when transitioning to executing, verifying, or filled.'
          },
          requestId
        );
      }

      if (updateResult.kind === 'missing_amount_out') {
        return errorResponse(
          400,
          {
            code: 'payload_invalid',
            message: 'amountOut is required when marking a trade as filled.',
            actionHint: 'Include amountOut in the status payload for filled transitions.'
          },
          requestId
        );
      }

      return errorResponse(
        409,
        {
          code: 'trade_invalid_transition',
          message: 'Trade status transition is not allowed.',
          actionHint: 'Follow canonical transition rules from Source-of-Truth section 27.',
          details: { currentStatus: updateResult.currentStatus }
        },
        requestId
      );
    }

    const responseBody = {
      ok: true,
      tradeId: pathTradeId,
      status: body.toStatus
    };

    await storeIdempotencyResponse(idempotency.ctx, 200, responseBody);
    return successResponse(responseBody, 200, requestId);
  } catch (error) {
    console.error('trade_status_route_error', error);
    return internalErrorResponse(requestId);
  }
}
