import type { NextRequest } from 'next/server';

import { authenticateAgentByToken } from '@/lib/agent-auth';
import { withTransaction } from '@/lib/db';
import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import { parseJsonBody } from '@/lib/http';
import { ensureIdempotency, storeIdempotencyResponse } from '@/lib/idempotency';
import { makeId } from '@/lib/ids';
import { getRequestId } from '@/lib/request-id';
import { validatePayload } from '@/lib/validation';

export const runtime = 'nodejs';

type PolicyApprovalDecisionRequest = {
  policyApprovalId: string;
  fromStatus: 'approval_pending';
  toStatus: 'approved' | 'rejected';
  reasonMessage?: string | null;
  at: string;
};

function normalizeTokenSet(values: unknown): Set<string> {
  if (!Array.isArray(values)) {
    return new Set<string>();
  }
  const out = new Set<string>();
  for (const entry of values) {
    if (typeof entry !== 'string') {
      continue;
    }
    const normalized = entry.trim().toLowerCase();
    if (normalized.length > 0) {
      out.add(normalized);
    }
  }
  return out;
}

export async function POST(
  req: NextRequest,
  context: { params: Promise<{ requestId: string }> }
) {
  const requestId = getRequestId(req);

  try {
    const { requestId: pathId } = await context.params;

    const auth = authenticateAgentByToken(req, requestId);
    if (!auth.ok) {
      return auth.response;
    }

    const parsed = await parseJsonBody(req, requestId);
    if (!parsed.ok) {
      return parsed.response;
    }

    const validated = validatePayload<PolicyApprovalDecisionRequest>('policy-approval-decision-request.schema.json', parsed.body);
    if (!validated.ok) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Policy approval decision payload does not match schema.',
          actionHint: 'Provide policyApprovalId, fromStatus, toStatus, and at timestamp.',
          details: validated.details
        },
        requestId
      );
    }

    const body = validated.data;
    if (body.policyApprovalId !== pathId) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Path requestId must match body policyApprovalId.',
          actionHint: 'Use the same id in URL and JSON body.'
        },
        requestId
      );
    }

    const idempotency = await ensureIdempotency(req, 'policy_approval_decision', auth.agentId, body, requestId);
    if (!idempotency.ok) {
      return idempotency.response;
    }
    if (idempotency.ctx.replayResponse) {
      return successResponse(idempotency.ctx.replayResponse.body as Record<string, unknown>, idempotency.ctx.replayResponse.status, requestId);
    }

    const result = await withTransaction(async (client) => {
      const approval = await client.query<{
        agent_id: string;
        chain_key: string;
        request_type: string;
        token_address: string | null;
        status: string;
      }>(
        `
        select agent_id, chain_key, request_type, token_address, status
        from agent_policy_approval_requests
        where request_id = $1
        limit 1
        `,
        [pathId]
      );

      if (approval.rowCount === 0) {
        return { ok: false as const, kind: 'missing' as const };
      }

      const row = approval.rows[0];
      if (row.agent_id !== auth.agentId) {
        return { ok: false as const, kind: 'auth_mismatch' as const };
      }

      if (row.status !== body.fromStatus) {
        return { ok: false as const, kind: 'state_mismatch' as const, currentStatus: row.status };
      }

      await client.query(
        `
        update agent_policy_approval_requests
        set
          status = $1,
          reason_message = $2,
          decided_at = $3::timestamptz,
          updated_at = now()
        where request_id = $4
        `,
        [body.toStatus, body.reasonMessage ?? null, body.at, pathId]
      );

      if (body.toStatus === 'approved') {
        const latest = await client.query<{
          mode: 'mock' | 'real';
          approval_mode: 'per_trade' | 'auto';
          max_trade_usd: string | null;
          max_daily_usd: string | null;
          allowed_tokens: unknown;
          daily_cap_usd_enabled: boolean;
          daily_trade_cap_enabled: boolean;
          max_daily_trade_count: number | null;
        }>(
          `
          select
            mode,
            approval_mode,
            max_trade_usd::text,
            max_daily_usd::text,
            allowed_tokens,
            daily_cap_usd_enabled,
            daily_trade_cap_enabled,
            max_daily_trade_count
          from agent_policy_snapshots
          where agent_id = $1
          order by created_at desc
          limit 1
          `,
          [auth.agentId]
        );

        if (latest.rowCount === 0) {
          return { ok: false as const, kind: 'missing_policy' as const };
        }

        const snapshot = latest.rows[0];
        let nextApprovalMode = snapshot.approval_mode;
        let nextAllowedTokens = normalizeTokenSet(snapshot.allowed_tokens);

        if (row.request_type === 'global_approval_enable') {
          nextApprovalMode = 'auto';
        } else if (row.request_type === 'global_approval_disable') {
          nextApprovalMode = 'per_trade';
        } else if (row.request_type === 'token_preapprove_add' && row.token_address) {
          nextAllowedTokens.add(String(row.token_address).trim().toLowerCase());
        } else if (row.request_type === 'token_preapprove_remove' && row.token_address) {
          nextAllowedTokens.delete(String(row.token_address).trim().toLowerCase());
        }

        await client.query(
          `
          insert into agent_policy_snapshots (
            snapshot_id, agent_id, mode, approval_mode, max_trade_usd, max_daily_usd, allowed_tokens,
            daily_cap_usd_enabled, daily_trade_cap_enabled, max_daily_trade_count, created_at
          ) values ($1, $2, $3::policy_mode, $4::policy_approval_mode, $5::numeric, $6::numeric, $7::jsonb, $8, $9, $10, now())
          `,
          [
            makeId('pol'),
            auth.agentId,
            snapshot.mode,
            nextApprovalMode,
            snapshot.max_trade_usd ?? '0',
            snapshot.max_daily_usd ?? '0',
            JSON.stringify([...nextAllowedTokens]),
            snapshot.daily_cap_usd_enabled,
            snapshot.daily_trade_cap_enabled,
            snapshot.max_daily_trade_count
          ]
        );
      }

      await client.query(
        `
        insert into agent_events (event_id, agent_id, trade_id, event_type, payload, created_at)
        values ($1, $2, null, $3, $4::jsonb, $5::timestamptz)
        `,
        [
          makeId('evt'),
          auth.agentId,
          body.toStatus === 'approved' ? 'policy_approved' : 'policy_rejected',
          JSON.stringify({
            policyApprovalId: pathId,
            chainKey: row.chain_key,
            requestType: row.request_type,
            tokenAddress: row.token_address ?? null,
            reasonMessage: body.reasonMessage ?? null
          }),
          body.at
        ]
      );

      return { ok: true as const, chainKey: row.chain_key };
    });

    if (!result.ok) {
      if (result.kind === 'missing') {
        return errorResponse(
          404,
          { code: 'payload_invalid', message: 'Policy approval request was not found.', actionHint: 'Verify policyApprovalId and retry.' },
          requestId
        );
      }
      if (result.kind === 'auth_mismatch') {
        return errorResponse(
          401,
          { code: 'auth_invalid', message: 'Agent is not allowed to decide this request.', actionHint: 'Use the api key for the owning agent.' },
          requestId
        );
      }
      if (result.kind === 'state_mismatch') {
        return errorResponse(
          409,
          {
            code: 'not_actionable',
            message: 'Policy approval status update rejected because fromStatus does not match current state.',
            actionHint: 'Refresh policy approval state and retry with the correct fromStatus.',
            details: { currentStatus: result.currentStatus }
          },
          requestId
        );
      }
      if (result.kind === 'missing_policy') {
        return errorResponse(
          409,
          {
            code: 'policy_denied',
            message: 'Cannot apply policy approval because no policy snapshot exists.',
            actionHint: 'Create a policy snapshot first, then retry approval.'
          },
          requestId
        );
      }
    }

    const responseBody = { ok: true, policyApprovalId: pathId, status: body.toStatus };
    await storeIdempotencyResponse(idempotency.ctx, 200, responseBody);
    return successResponse(responseBody, 200, requestId);
  } catch {
    return internalErrorResponse(requestId);
  }
}
