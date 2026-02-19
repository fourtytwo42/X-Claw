import type { NextRequest } from 'next/server';

import { requireAgentAuth } from '@/lib/agent-auth';
import { requireAgentChainEnabled } from '@/lib/agent-chain-policy';
import { withTransaction } from '@/lib/db';
import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import { parseJsonBody } from '@/lib/http';
import { ensureIdempotency, storeIdempotencyResponse } from '@/lib/idempotency';
import { makeId } from '@/lib/ids';
import { getRequestId } from '@/lib/request-id';
import { evaluateTradeCaps } from '@/lib/trade-caps';
import { validatePayload } from '@/lib/validation';

export const runtime = 'nodejs';

type LiquidityProposedRequest = {
  schemaVersion: number;
  agentId: string;
  chainKey: string;
  dex: string;
  action: 'add' | 'remove';
  positionType: 'v2' | 'v3';
  tokenA: string;
  tokenB: string;
  amountA: string;
  amountB: string;
  slippageBps: number;
  positionId?: string;
  details?: Record<string, unknown>;
};

export async function POST(req: NextRequest) {
  const requestId = getRequestId(req);

  try {
    const parsed = await parseJsonBody(req, requestId);
    if (!parsed.ok) {
      return parsed.response;
    }

    const validated = validatePayload<LiquidityProposedRequest>('liquidity-proposed-request.schema.json', parsed.body);
    if (!validated.ok) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Liquidity proposed payload does not match schema.',
          actionHint: 'Verify required fields and retry.',
          details: validated.details,
        },
        requestId
      );
    }
    const body = validated.data;

    const auth = requireAgentAuth(req, body.agentId, requestId);
    if (!auth.ok) {
      return auth.response;
    }

    const idempotency = await ensureIdempotency(req, 'liquidity_proposed', body.agentId, body, requestId);
    if (!idempotency.ok) {
      return idempotency.response;
    }
    if (idempotency.ctx.replayResponse) {
      return successResponse(idempotency.ctx.replayResponse.body, idempotency.ctx.replayResponse.status, requestId);
    }

    const created = await withTransaction(async (client) => {
      const agent = await client.query('select agent_id from agents where agent_id = $1', [body.agentId]);
      if (agent.rowCount === 0) {
        return { kind: 'missing_agent' as const };
      }

      const chainGate = await requireAgentChainEnabled(client, { agentId: body.agentId, chainKey: body.chainKey });
      if (!chainGate.ok) {
        return { kind: 'blocked' as const, blocked: chainGate.violation };
      }

      const capCheck = await evaluateTradeCaps(client, {
        agentId: body.agentId,
        chainKey: body.chainKey,
        projectedSpendUsd: body.amountA,
        projectedFilledTrades: 1,
      });
      if (!capCheck.ok) {
        return { kind: 'blocked' as const, blocked: capCheck.violation };
      }

      const existing = await client.query<{ liquidity_intent_id: string }>(
        `
        select liquidity_intent_id
        from liquidity_intents
        where agent_id = $1
          and chain_key = $2
          and dex_key = $3
          and action_type = $4
          and token_a = $5
          and token_b = $6
          and amount_a::text = $7
          and amount_b::text = $8
          and slippage_bps = $9
          and status = 'approval_pending'
        order by created_at desc
        limit 1
        `,
        [
          body.agentId,
          body.chainKey,
          body.dex.trim().toLowerCase(),
          body.action,
          body.tokenA.trim(),
          body.tokenB.trim(),
          body.amountA.trim(),
          body.amountB.trim(),
          body.slippageBps,
        ]
      );
      if ((existing.rowCount ?? 0) > 0) {
        return { kind: 'reused' as const, liquidityIntentId: existing.rows[0].liquidity_intent_id, status: 'approval_pending' };
      }

      const tokenANormalized = body.tokenA.trim().toLowerCase();
      const allowedTokenSet = new Set(capCheck.caps.allowedTokens.map((token) => String(token || '').trim().toLowerCase()).filter(Boolean));
      const approvalRequired = capCheck.caps.approvalMode !== 'auto' && !allowedTokenSet.has(tokenANormalized);
      const status = approvalRequired ? 'approval_pending' : 'approved';
      const liquidityIntentId = makeId('liq');

      await client.query(
        `
        insert into liquidity_intents (
          liquidity_intent_id, agent_id, chain_key, dex_key, action_type, position_type, status,
          token_a, token_b, amount_a, amount_b, slippage_bps, position_ref, details, created_at, updated_at
        ) values (
          $1, $2, $3, $4, $5, $6, $7,
          $8, $9, $10::numeric, $11::numeric, $12, $13, $14::jsonb, now(), now()
        )
        `,
        [
          liquidityIntentId,
          body.agentId,
          body.chainKey,
          body.dex.trim().toLowerCase(),
          body.action,
          body.positionType,
          status,
          body.tokenA.trim(),
          body.tokenB.trim(),
          body.amountA.trim(),
          body.amountB.trim(),
          body.slippageBps,
          body.positionId?.trim() || null,
          JSON.stringify(body.details ?? {}),
        ]
      );

      return { kind: 'created' as const, liquidityIntentId, status };
    });

    if (created.kind === 'missing_agent') {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Liquidity proposal rejected because agent is not registered.',
          actionHint: 'Register agent before proposing liquidity intents.',
        },
        requestId
      );
    }

    if (created.kind === 'blocked') {
      return errorResponse(
        400,
        {
          code: created.blocked.code,
          message: created.blocked.message,
          actionHint: created.blocked.actionHint,
          details: created.blocked.details,
        },
        requestId
      );
    }

    const responseBody = {
      ok: true,
      liquidityIntentId: created.liquidityIntentId,
      status: created.status,
    };
    await storeIdempotencyResponse(idempotency.ctx, 200, responseBody);
    return successResponse(responseBody, 200, requestId);
  } catch {
    return internalErrorResponse(requestId);
  }
}
