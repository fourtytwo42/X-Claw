import type { NextRequest } from 'next/server';

import { authenticateAgentByToken } from '@/lib/agent-auth';
import { withTransaction } from '@/lib/db';
import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import { parseJsonBody } from '@/lib/http';
import { makeId } from '@/lib/ids';
import { maybeSyncLiquiditySnapshots } from '@/lib/liquidity-indexer';
import { getRequestId } from '@/lib/request-id';
import { validatePayload } from '@/lib/validation';

export const runtime = 'nodejs';

type LiquidityStatusBody = {
  status: string;
  reasonCode?: string;
  reasonMessage?: string;
  txHash?: string;
  positionId?: string;
  amountOut?: string | number;
  providerRequested?: 'uniswap_api' | 'legacy_router';
  providerUsed?: 'uniswap_api' | 'legacy_router';
  fallbackUsed?: boolean;
  fallbackReason?: { code: string; message: string };
  uniswapLpOperation?: 'approve' | 'create' | 'increase' | 'decrease' | 'claim';
  details?: Record<string, unknown>;
};

type LiquidityFeeEventInput = {
  token?: string;
  amount?: string | number;
  amountUsd?: string | number | null;
  txHash?: string | null;
  occurredAt?: string | null;
};

const ALLOWED_TRANSITIONS = new Map<string, Set<string>>([
  ['proposed', new Set(['approval_pending', 'approved'])],
  ['approval_pending', new Set(['approved', 'rejected', 'expired'])],
  ['approved', new Set(['executing'])],
  ['executing', new Set(['verifying', 'failed'])],
  ['verifying', new Set(['filled', 'failed', 'verification_timeout'])],
  ['failed', new Set(['executing'])],
]);

function canTransition(from: string, to: string): boolean {
  if (from === to) {
    return true;
  }
  const allowed = ALLOWED_TRANSITIONS.get(from);
  return allowed ? allowed.has(to) : false;
}

export async function POST(req: NextRequest, ctx: { params: Promise<{ intentId: string }> }) {
  const requestId = getRequestId(req);

  try {
    const auth = authenticateAgentByToken(req, requestId);
    if (!auth.ok) {
      return auth.response;
    }

    const { intentId } = await ctx.params;
    if (!intentId || !intentId.trim()) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Liquidity intent id is required.',
          actionHint: 'Use /api/v1/liquidity/<intentId>/status with a valid id.',
        },
        requestId
      );
    }

    const parsed = await parseJsonBody(req, requestId);
    if (!parsed.ok) {
      return parsed.response;
    }
    const validated = validatePayload<LiquidityStatusBody>('liquidity-status.schema.json', parsed.body);
    if (!validated.ok) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Liquidity status payload does not match schema.',
          actionHint: 'Provide a valid status body and retry.',
          details: validated.details,
        },
        requestId
      );
    }
    const body = validated.data;

    const updated = await withTransaction(async (client) => {
      const row = await client.query<{
        liquidity_intent_id: string;
        agent_id: string;
        chain_key: string;
        dex_key: string;
        position_type: 'v2' | 'v3';
        action_type: 'add' | 'remove';
        status: string;
        token_a: string | null;
        token_b: string | null;
        amount_a: string | null;
        amount_b: string | null;
        details: Record<string, unknown>;
      }>(
        `
        select
          liquidity_intent_id, agent_id, chain_key, dex_key, position_type, action_type, status,
          token_a, token_b, amount_a::text, amount_b::text, details
        from liquidity_intents
        where liquidity_intent_id = $1
        limit 1
        `,
        [intentId.trim()]
      );
      if (row.rowCount === 0) {
        return { kind: 'missing' as const };
      }
      if (row.rows[0].agent_id !== auth.agentId) {
        return { kind: 'forbidden' as const };
      }
      const current = row.rows[0];
      const nextStatus = String(body.status || '').trim();
      if (!canTransition(current.status, nextStatus)) {
        return { kind: 'transition_invalid' as const, currentStatus: current.status, requestedStatus: nextStatus };
      }

      const detailsPatch: Record<string, unknown> = { ...(body.details ?? {}) };
      if (body.providerRequested) {
        detailsPatch.providerRequested = body.providerRequested;
      }
      if (body.providerUsed) {
        detailsPatch.providerUsed = body.providerUsed;
      }
      if (body.fallbackUsed !== undefined) {
        detailsPatch.fallbackUsed = body.fallbackUsed;
      }
      if (body.fallbackReason) {
        detailsPatch.fallbackReason = body.fallbackReason;
      }
      if (body.uniswapLpOperation) {
        detailsPatch.uniswapLpOperation = body.uniswapLpOperation;
      }

      await client.query(
        `
        update liquidity_intents
        set
          status = $2,
          reason_code = coalesce($3, reason_code),
          reason_message = coalesce($4, reason_message),
          tx_hash = coalesce($5, tx_hash),
          amount_out = coalesce($6::numeric, amount_out),
          position_ref = coalesce($7, position_ref),
          details = case when $8::jsonb = '{}'::jsonb then details else details || $8::jsonb end,
          updated_at = now()
        where liquidity_intent_id = $1
        `,
        [
          intentId.trim(),
          nextStatus,
          body.reasonCode ?? null,
          body.reasonMessage ?? null,
          body.txHash ?? null,
          body.amountOut !== undefined ? String(body.amountOut) : null,
          body.positionId ?? null,
          JSON.stringify(detailsPatch),
        ]
      );

      if (nextStatus === 'filled') {
        const positionId = String(body.positionId || current.details?.positionId || current.liquidity_intent_id).trim();
        await client.query(
          `
          insert into liquidity_position_snapshots (
            snapshot_id, agent_id, chain_key, dex_key, position_id, position_type, pool_ref,
            token_a, token_b, deposited_a, deposited_b, current_a, current_b, status, last_synced_at, created_at, updated_at
          ) values (
            $1, $2, $3, $4, $5, $6, $7,
            $8, $9, $10::numeric, $11::numeric, $12::numeric, $13::numeric, 'active', now(), now(), now()
          )
          on conflict (agent_id, chain_key, position_id) do update set
            dex_key = excluded.dex_key,
            position_type = excluded.position_type,
            pool_ref = excluded.pool_ref,
            token_a = excluded.token_a,
            token_b = excluded.token_b,
            deposited_a = excluded.deposited_a,
            deposited_b = excluded.deposited_b,
            current_a = excluded.current_a,
            current_b = excluded.current_b,
            status = 'active',
            last_synced_at = now(),
            updated_at = now()
          `,
          [
            makeId('lps'),
            current.agent_id,
            current.chain_key,
            current.dex_key,
            positionId,
            current.position_type,
            `${current.token_a ?? 'tokenA'}/${current.token_b ?? 'tokenB'}`,
            current.token_a ?? '',
            current.token_b ?? '',
            current.amount_a ?? '0',
            current.amount_b ?? '0',
            current.amount_a ?? '0',
            current.amount_b ?? '0',
          ]
        );

        const feeEvents = Array.isArray(body.details?.feeEvents) ? (body.details?.feeEvents as LiquidityFeeEventInput[]) : [];
        for (const event of feeEvents) {
          const token = String(event?.token ?? '').trim();
          const amount = String(event?.amount ?? '').trim();
          if (!token || !amount) {
            continue;
          }
          await client.query(
            `
            insert into liquidity_fee_events (
              fee_event_id, agent_id, chain_key, dex_key, position_id, token, amount, amount_usd, tx_hash, occurred_at, created_at
            ) values (
              $1, $2, $3, $4, $5, $6, $7::numeric, $8::numeric, $9, coalesce($10::timestamptz, now()), now()
            )
            `,
            [
              makeId('lfe'),
              current.agent_id,
              current.chain_key,
              current.dex_key,
              positionId,
              token,
              amount,
              event?.amountUsd === undefined || event?.amountUsd === null ? null : String(event.amountUsd),
              event?.txHash ?? body.txHash ?? null,
              event?.occurredAt ?? null,
            ]
          );
        }
      }

      return { kind: 'ok' as const, status: nextStatus, agentId: current.agent_id, chainKey: current.chain_key };
    });

    if (updated.kind === 'missing') {
      return errorResponse(
        404,
        {
          code: 'payload_invalid',
          message: 'Liquidity intent was not found.',
          actionHint: 'Check intent id and retry.',
        },
        requestId
      );
    }
    if (updated.kind === 'forbidden') {
      return errorResponse(
        401,
        {
          code: 'auth_invalid',
          message: 'Agent is not authorized to update this liquidity intent.',
          actionHint: 'Use the API key for the owning agent.',
        },
        requestId
      );
    }
    if (updated.kind === 'transition_invalid') {
      return errorResponse(
        409,
        {
          code: 'liquidity_invalid_transition',
          message: `Invalid liquidity status transition from '${updated.currentStatus}' to '${updated.requestedStatus}'.`,
          actionHint: 'Submit a valid transition and retry.',
          details: { currentStatus: updated.currentStatus, requestedStatus: updated.requestedStatus },
        },
        requestId
      );
    }

    if (updated.status === 'filled' || updated.status === 'failed' || updated.status === 'verification_timeout') {
      await maybeSyncLiquiditySnapshots(updated.agentId, updated.chainKey, { force: true });
    }

    return successResponse({ ok: true, liquidityIntentId: intentId.trim(), status: updated.status }, 200, requestId);
  } catch {
    return internalErrorResponse(requestId);
  }
}
