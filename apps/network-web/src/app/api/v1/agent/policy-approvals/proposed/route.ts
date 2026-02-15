import type { NextRequest } from 'next/server';

import { authenticateAgentByToken } from '@/lib/agent-auth';
import { dbQuery, withTransaction } from '@/lib/db';
import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import { getChainConfig } from '@/lib/chains';
import { parseJsonBody } from '@/lib/http';
import { ensureIdempotency, storeIdempotencyResponse } from '@/lib/idempotency';
import { makeId } from '@/lib/ids';
import { getRequestId } from '@/lib/request-id';
import { validatePayload } from '@/lib/validation';

export const runtime = 'nodejs';

type AgentPolicyApprovalProposedRequest = {
  schemaVersion: 1;
  chainKey: string;
  requestType: 'token_preapprove_add' | 'token_preapprove_remove' | 'global_approval_enable' | 'global_approval_disable';
  tokenAddress?: string | null;
};

function normalizeTokenAddress(value: unknown): string | null {
  if (typeof value !== 'string') {
    return null;
  }
  const normalized = value.trim().toLowerCase();
  return /^0x[a-f0-9]{40}$/.test(normalized) ? normalized : null;
}

export async function POST(req: NextRequest) {
  const requestId = getRequestId(req);

  try {
    const auth = authenticateAgentByToken(req, requestId);
    if (!auth.ok) {
      return auth.response;
    }

    const parsed = await parseJsonBody(req, requestId);
    if (!parsed.ok) {
      return parsed.response;
    }

    const validated = validatePayload<AgentPolicyApprovalProposedRequest>('agent-policy-approval-proposed-request.schema.json', parsed.body);
    if (!validated.ok) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Policy approval proposal payload does not match schema.',
          actionHint: 'Provide chainKey, requestType, and tokenAddress when required.',
          details: validated.details
        },
        requestId
      );
    }

    const body = validated.data;

    if (!getChainConfig(body.chainKey)) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Invalid chainKey value.',
          actionHint: 'Use a supported chain key (for example base_sepolia).',
          details: { chainKey: body.chainKey }
        },
        requestId
      );
    }

    const needsToken =
      body.requestType === 'token_preapprove_add' || body.requestType === 'token_preapprove_remove';
    const tokenAddress = needsToken ? normalizeTokenAddress(body.tokenAddress) : null;
    if (needsToken && !tokenAddress) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'tokenAddress is required for token preapprove add/remove and must be a 0x address.',
          actionHint: 'Provide tokenAddress like 0xabc... (20-byte hex).'
        },
        requestId
      );
    }

    const idempotency = await ensureIdempotency(req, 'agent_policy_approval_proposed', auth.agentId, body, requestId);
    if (!idempotency.ok) {
      return idempotency.response;
    }
    if (idempotency.ctx.replayResponse) {
      return successResponse(idempotency.ctx.replayResponse.body as Record<string, unknown>, idempotency.ctx.replayResponse.status, requestId);
    }

    const agent = await dbQuery<{ agent_id: string }>(
      `
      select agent_id
      from agents
      where agent_id = $1
      limit 1
      `,
      [auth.agentId]
    );
    if (agent.rowCount === 0) {
      return errorResponse(
        404,
        {
          code: 'payload_invalid',
          message: 'Agent was not found.',
          actionHint: 'Register agent before proposing policy approvals.'
        },
        requestId
      );
    }

    const approvalId = makeId('ppr');
    await withTransaction(async (client) => {
      await client.query(
        `
        insert into agent_policy_approval_requests (
          request_id, agent_id, chain_key, request_type, token_address, status, reason_message,
          decided_by_management_session_id, created_at, decided_at, updated_at
        ) values ($1, $2, $3, $4, $5, 'approval_pending', null, null, now(), null, now())
        `,
        [approvalId, auth.agentId, body.chainKey, body.requestType, tokenAddress]
      );

      await client.query(
        `
        insert into agent_events (event_id, agent_id, trade_id, event_type, payload, created_at)
        values ($1, $2, null, 'policy_approval_pending', $3::jsonb, now())
        `,
        [
          makeId('evt'),
          auth.agentId,
          JSON.stringify({
            policyApprovalId: approvalId,
            chainKey: body.chainKey,
            requestType: body.requestType,
            tokenAddress
          })
        ]
      );
    });

    const responseBody = {
      ok: true,
      policyApprovalId: approvalId,
      status: 'approval_pending',
      chainKey: body.chainKey,
      requestType: body.requestType,
      tokenAddress
    };
    await storeIdempotencyResponse(idempotency.ctx, 200, responseBody);
    return successResponse(responseBody, 200, requestId);
  } catch {
    return internalErrorResponse(requestId);
  }
}
