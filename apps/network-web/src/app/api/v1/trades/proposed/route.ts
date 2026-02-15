import type { NextRequest } from 'next/server';

import { requireAgentAuth } from '@/lib/agent-auth';
import { withTransaction } from '@/lib/db';
import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import { parseJsonBody } from '@/lib/http';
import { ensureIdempotency, storeIdempotencyResponse } from '@/lib/idempotency';
import { makeId } from '@/lib/ids';
import { getRequestId } from '@/lib/request-id';
import { requireAgentChainEnabled } from '@/lib/agent-chain-policy';
import { getChainConfig } from '@/lib/chains';
import { evaluateTradeCaps } from '@/lib/trade-caps';
import { validatePayload } from '@/lib/validation';

export const runtime = 'nodejs';

type TradeProposedRequest = {
  schemaVersion: number;
  agentId: string;
  chainKey: string;
  mode: 'mock' | 'real';
  tokenIn: string;
  tokenOut: string;
  amountIn: string;
  slippageBps: number;
  amountOut?: string | null;
  priceImpactBps?: number | null;
  reason?: string | null;
};

export async function POST(req: NextRequest) {
  const requestId = getRequestId(req);

  try {
    const parsed = await parseJsonBody(req, requestId);
    if (!parsed.ok) {
      return parsed.response;
    }

    const validated = validatePayload<TradeProposedRequest>('trade-proposed-request.schema.json', parsed.body);
    if (!validated.ok) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Trade proposed payload does not match schema.',
          actionHint: 'Verify required fields, numeric formats, and mode values.',
          details: validated.details
        },
        requestId
      );
    }

    const body = validated.data;

    const auth = requireAgentAuth(req, body.agentId, requestId);
    if (!auth.ok) {
      return auth.response;
    }

    const idempotency = await ensureIdempotency(req, 'trade_proposed', body.agentId, body, requestId);
    if (!idempotency.ok) {
      return idempotency.response;
    }

    if (idempotency.ctx.replayResponse) {
      return successResponse(idempotency.ctx.replayResponse.body, idempotency.ctx.replayResponse.status, requestId);
    }

    const tradeId = makeId('trd');
    const projectedSpendUsd = body.amountIn;

    const inserted = await withTransaction(async (client) => {
      const agent = await client.query('select agent_id from agents where agent_id = $1', [body.agentId]);
      if (agent.rowCount === 0) {
        return { found: false as const };
      }

      const chainGate = await requireAgentChainEnabled(client, { agentId: body.agentId, chainKey: body.chainKey });
      if (!chainGate.ok) {
        return { found: true as const, blocked: chainGate.violation };
      }

      const capCheck = await evaluateTradeCaps(client, {
        agentId: body.agentId,
        chainKey: body.chainKey,
        projectedSpendUsd,
        projectedFilledTrades: 1
      });
      if (!capCheck.ok) {
        return { found: true as const, blocked: capCheck.violation };
      }

      const tokenInNormalized = body.tokenIn.trim().toLowerCase();
      const allowedTokenSet = new Set(
        capCheck.caps.allowedTokens.map((token) => String(token).trim().toLowerCase()).filter((v) => v.length > 0)
      );
      // Back-compat: older snapshots may contain canonical token symbols. Convert those to addresses for the current chain.
      const cfg = getChainConfig(body.chainKey);
      for (const [symbol, address] of Object.entries(cfg?.canonicalTokens ?? {})) {
        if (!symbol || !address) continue;
        if (allowedTokenSet.has(symbol.trim().toLowerCase())) {
          allowedTokenSet.add(address.trim().toLowerCase());
        }
      }
      const approvalRequired = capCheck.caps.approvalMode !== 'auto' && !allowedTokenSet.has(tokenInNormalized);
      const initialStatus = approvalRequired ? 'approval_pending' : 'approved';
      const initialEventType = approvalRequired ? 'trade_approval_pending' : 'trade_approved';

      await client.query(
        `
        insert into trades (
          trade_id, agent_id, chain_key, is_mock, status,
          token_in, token_out, pair, amount_in, amount_out,
          price_impact_bps, slippage_bps, reason, created_at, updated_at
        )
        values (
          $1, $2, $3, $4, $5::trade_status,
          $6, $7, $8, $9, $10,
          $11, $12, $13, now(), now()
        )
        `,
        [
          tradeId,
          body.agentId,
          body.chainKey,
          body.mode === 'mock',
          initialStatus,
          body.tokenIn,
          body.tokenOut,
          `${body.tokenIn}/${body.tokenOut}`,
          body.amountIn,
          body.amountOut ?? null,
          body.priceImpactBps ?? null,
          body.slippageBps,
          body.reason ?? null
        ]
      );

      await client.query(
        `
        insert into agent_events (event_id, agent_id, trade_id, event_type, payload, created_at)
        values ($1, $2, $3, $4, $5::jsonb, now())
        `,
        [
          makeId('evt'),
          body.agentId,
          tradeId,
          initialEventType,
          JSON.stringify({
            chainKey: body.chainKey,
            mode: body.mode,
            tokenIn: body.tokenIn,
            tokenOut: body.tokenOut,
            amountIn: body.amountIn,
            slippageBps: body.slippageBps
          })
        ]
      );

      return { found: true as const, status: initialStatus };
    });

    if (!inserted.found) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Trade proposal rejected because agent is not registered.',
          actionHint: 'Register agent before proposing trades.'
        },
        requestId
      );
    }

    if ('blocked' in inserted && inserted.blocked) {
      return errorResponse(
        400,
        {
          code: inserted.blocked.code,
          message: inserted.blocked.message,
          actionHint: inserted.blocked.actionHint,
          details: inserted.blocked.details
        },
        requestId
      );
    }

    const responseBody = {
      ok: true,
      tradeId,
      status: 'status' in inserted ? inserted.status : 'proposed'
    };

    await storeIdempotencyResponse(idempotency.ctx, 200, responseBody);
    return successResponse(responseBody, 200, requestId);
  } catch {
    return internalErrorResponse(requestId);
  }
}
