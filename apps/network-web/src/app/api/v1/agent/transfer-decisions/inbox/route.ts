import type { NextRequest } from 'next/server';

import { authenticateAgentByToken } from '@/lib/agent-auth';
import { dbQuery } from '@/lib/db';
import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import { parseJsonBody } from '@/lib/http';
import { getRequestId } from '@/lib/request-id';
import { validatePayload } from '@/lib/validation';

export const runtime = 'nodejs';

type AgentTransferDecisionInboxAckRequest = {
  schemaVersion: 1;
  decisionId: string;
  status: 'applied' | 'failed';
  reasonCode?: string | null;
  reasonMessage?: string | null;
};

function parseLimit(raw: string | null): number {
  if (!raw) {
    return 20;
  }
  const parsed = Number.parseInt(raw, 10);
  if (!Number.isFinite(parsed) || parsed < 1) {
    return 20;
  }
  return Math.min(parsed, 50);
}

export async function GET(req: NextRequest) {
  const requestId = getRequestId(req);
  try {
    const auth = authenticateAgentByToken(req, requestId);
    if (!auth.ok) {
      return auth.response;
    }

    const chainKey = String(req.nextUrl.searchParams.get('chainKey') ?? '').trim();
    const limit = parseLimit(req.nextUrl.searchParams.get('limit'));

    const rows = await dbQuery<{
      decision_id: string;
      approval_id: string;
      chain_key: string;
      decision: 'approve' | 'deny';
      reason_message: string | null;
      source: string;
      created_at: string;
    }>(
      `
      select decision_id, approval_id, chain_key, decision, reason_message, source, created_at
      from agent_transfer_decision_inbox
      where agent_id = $1
        and status = 'pending'
        and ($2 = '' or chain_key = $2)
      order by created_at asc
      limit $3
      `,
      [auth.agentId, chainKey, limit]
    );

    return successResponse(
      {
        ok: true,
        agentId: auth.agentId,
        chainKey: chainKey || null,
        count: rows.rowCount ?? 0,
        decisions: rows.rows.map((row) => ({
          decisionId: row.decision_id,
          approvalId: row.approval_id,
          chainKey: row.chain_key,
          decision: row.decision,
          reasonMessage: row.reason_message,
          source: row.source,
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

    const validated = validatePayload<AgentTransferDecisionInboxAckRequest>('agent-transfer-decisions-ack-request.schema.json', parsed.body);
    if (!validated.ok) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Transfer decision inbox ack payload does not match schema.',
          actionHint: 'Provide schemaVersion, decisionId, status, and optional reason fields.',
          details: validated.details
        },
        requestId
      );
    }

    const body = validated.data;
    const reasonCode = String(body.reasonCode ?? '').trim() || null;
    const reasonMessage = String(body.reasonMessage ?? '').trim() || null;

    const updated = await dbQuery<{ decision_id: string }>(
      `
      update agent_transfer_decision_inbox
      set status = $1,
          reason_message = coalesce($2, reason_message),
          applied_at = now()
      where decision_id = $3
        and agent_id = $4
        and status = 'pending'
      returning decision_id
      `,
      [body.status, reasonMessage, body.decisionId, auth.agentId]
    );

    if ((updated.rowCount ?? 0) === 0) {
      return errorResponse(
        409,
        {
          code: 'not_actionable',
          message: 'Transfer decision inbox row is not pending or was not found.',
          actionHint: 'Refresh inbox and ack only pending decisions.',
          details: {
            decisionId: body.decisionId,
            status: body.status,
            reasonCode
          }
        },
        requestId
      );
    }

    return successResponse(
      {
        ok: true,
        decisionId: body.decisionId,
        status: body.status,
        reasonCode,
        reasonMessage
      },
      200,
      requestId
    );
  } catch {
    return internalErrorResponse(requestId);
  }
}
