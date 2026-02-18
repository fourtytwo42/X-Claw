import type { NextRequest } from 'next/server';

import { requireAgentAuth } from '@/lib/agent-auth';
import { withTransaction } from '@/lib/db';
import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import { parseJsonBody } from '@/lib/http';
import { ensureIdempotency, storeIdempotencyResponse } from '@/lib/idempotency';
import { makeId } from '@/lib/ids';
import { getRequestId } from '@/lib/request-id';
import { validatePayload } from '@/lib/validation';

export const runtime = 'nodejs';

type HeartbeatRequest = {
  schemaVersion: number;
  agentId: string;
  publicStatus: 'active' | 'offline' | 'degraded' | 'paused' | 'deactivated';
  mode: 'mock' | 'real';
  approvalMode: 'per_trade' | 'auto';
  maxTradeUsd?: string | number | null;
  maxDailyUsd?: string | number | null;
  allowedTokens?: string[];
  balances?: Array<{
    chainKey: string;
    token: string;
    amount: string;
  }>;
};

export async function POST(req: NextRequest) {
  const requestId = getRequestId(req);

  try {
    const parsed = await parseJsonBody(req, requestId);
    if (!parsed.ok) {
      return parsed.response;
    }

    const validated = validatePayload<HeartbeatRequest>('agent-heartbeat-request.schema.json', parsed.body);
    if (!validated.ok) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Heartbeat payload does not match schema.',
          actionHint: 'Verify status, mode, approvalMode, and payload field types.',
          details: validated.details
        },
        requestId
      );
    }

    const body = validated.data;
    const policyChainKey =
      (Array.isArray(body.balances) ? String(body.balances[0]?.chainKey ?? '').trim() : '') || 'base_sepolia';

    const auth = requireAgentAuth(req, body.agentId, requestId);
    if (!auth.ok) {
      return auth.response;
    }

    const idempotency = await ensureIdempotency(req, 'agent_heartbeat', body.agentId, body, requestId);
    if (!idempotency.ok) {
      return idempotency.response;
    }

    if (idempotency.ctx.replayResponse) {
      return successResponse(idempotency.ctx.replayResponse.body, idempotency.ctx.replayResponse.status, requestId);
    }

    const statusResult = await withTransaction(async (client) => {
      const updated = await client.query(
        `
        update agents
        set public_status = $1,
            updated_at = now()
        where agent_id = $2
        returning agent_id
        `,
        [body.publicStatus, body.agentId]
      );

      if (updated.rowCount === 0) {
        return { found: false as const };
      }

      await client.query(
        `
        insert into agent_policy_snapshots (
          snapshot_id, agent_id, chain_key, mode, approval_mode,
          max_trade_usd, max_daily_usd, allowed_tokens, created_at
        )
        values ($1, $2, $3, $4, $5, $6, $7, $8::jsonb, now())
        `,
        [
          makeId('aps'),
          body.agentId,
          policyChainKey,
          body.mode,
          body.approvalMode,
          body.maxTradeUsd ?? null,
          body.maxDailyUsd ?? null,
          JSON.stringify(body.allowedTokens ?? [])
        ]
      );

      await client.query(
        `
        insert into agent_events (event_id, agent_id, event_type, payload, created_at)
        values ($1, $2, 'heartbeat', $3::jsonb, now())
        `,
        [
          makeId('evt'),
          body.agentId,
          JSON.stringify({
            mode: body.mode,
            approvalMode: body.approvalMode,
            balances: body.balances ?? []
          })
        ]
      );

      return { found: true as const };
    });

    if (!statusResult.found) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Heartbeat rejected because agent is not registered.',
          actionHint: 'Register the agent before posting heartbeat updates.'
        },
        requestId
      );
    }

    const responseBody = {
      ok: true,
      agentId: body.agentId,
      publicStatus: body.publicStatus
    };

    await storeIdempotencyResponse(idempotency.ctx, 200, responseBody);
    return successResponse(responseBody, 200, requestId);
  } catch {
    return internalErrorResponse(requestId);
  }
}
