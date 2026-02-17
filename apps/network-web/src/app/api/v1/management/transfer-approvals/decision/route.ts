import { existsSync } from 'node:fs';
import { spawnSync } from 'node:child_process';

import type { NextRequest } from 'next/server';

import { dbQuery } from '@/lib/db';
import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import { parseJsonBody } from '@/lib/http';
import { makeId } from '@/lib/ids';
import { requireManagementWriteAuth } from '@/lib/management-auth';
import { getRequestId } from '@/lib/request-id';
import { validatePayload } from '@/lib/validation';

export const runtime = 'nodejs';

type ManagementTransferApprovalDecisionRequest = {
  agentId: string;
  approvalId: string;
  decision: 'approve' | 'deny';
  reasonMessage?: string | null;
  chainKey?: string;
};

function resolveRuntimeBin(): string {
  const candidates = [
    process.env.XCLAW_AGENT_RUNTIME_BIN?.trim() ?? '',
    `${process.env.HOME ?? ''}/.local/bin/xclaw-agent`,
    `${process.env.HOME ?? ''}/.nvm/current/bin/xclaw-agent`,
    'xclaw-agent'
  ].filter((value) => value.length > 0);
  for (const candidate of candidates) {
    if (candidate === 'xclaw-agent' || existsSync(candidate)) {
      return candidate;
    }
  }
  return 'xclaw-agent';
}

export async function POST(req: NextRequest) {
  const requestId = getRequestId(req);
  try {
    const parsed = await parseJsonBody(req, requestId);
    if (!parsed.ok) {
      return parsed.response;
    }

    const validated = validatePayload<ManagementTransferApprovalDecisionRequest>(
      'management-transfer-approval-decision-request.schema.json',
      parsed.body
    );
    if (!validated.ok) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Transfer approval decision payload does not match schema.',
          actionHint: 'Provide agentId, approvalId, decision, and optional reasonMessage.',
          details: validated.details
        },
        requestId
      );
    }
    const body = validated.data;

    const auth = await requireManagementWriteAuth(req, requestId, body.agentId);
    if (!auth.ok) {
      return auth.response;
    }

    const mirror = await dbQuery<{ chain_key: string; status: string; approval_source: 'transfer' | 'x402' }>(
      `
      select chain_key, status::text, approval_source::text
      from agent_transfer_approval_mirror
      where approval_id = $1
        and agent_id = $2
      limit 1
      `,
      [body.approvalId, body.agentId]
    );
    if ((mirror.rowCount ?? 0) === 0) {
      return errorResponse(
        404,
        {
          code: 'payload_invalid',
          message: 'Transfer approval was not found.',
          actionHint: 'Refresh transfer approvals and retry.'
        },
        requestId
      );
    }

    const chainKey = body.chainKey?.trim() || mirror.rows[0].chain_key;
    const currentStatus = mirror.rows[0].status;
    const approvalSource = mirror.rows[0].approval_source || 'transfer';
    if (currentStatus !== 'approval_pending' && currentStatus !== 'approved') {
      return errorResponse(
        409,
        {
          code: 'not_actionable',
          message: 'Transfer approval is not actionable from its current status.',
          actionHint: 'Refresh queue and retry with a pending item.',
          details: { currentStatus }
        },
        requestId
      );
    }

    await dbQuery(
      `
      insert into agent_transfer_decision_inbox (
        decision_id, approval_id, agent_id, chain_key, decision, reason_message, source, status, created_at
      ) values ($1, $2, $3, $4, $5, $6, 'web', 'pending', now())
      `,
      [makeId('tdi'), body.approvalId, body.agentId, chainKey, body.decision, body.reasonMessage ?? null]
    );

    const runtimeBin = resolveRuntimeBin();
    const runtimeArgs =
      approvalSource === 'x402'
        ? [
            'x402',
            'pay-decide',
            '--approval-id',
            body.approvalId,
            '--decision',
            body.decision === 'approve' ? 'approve' : 'deny',
            '--reason-message',
            body.reasonMessage ?? '',
            '--json'
          ]
        : [
            'approvals',
            'decide-transfer',
            '--approval-id',
            body.approvalId,
            '--decision',
            body.decision,
            '--chain',
            chainKey,
            '--reason-message',
            body.reasonMessage ?? '',
            '--json'
          ];

    const child = spawnSync(runtimeBin, runtimeArgs, { encoding: 'utf8', timeout: 60_000 });

    let runtimePayload: Record<string, unknown> | null = null;
    if (child.stdout) {
      const lines = child.stdout
        .split(/\r?\n/)
        .map((value) => value.trim())
        .filter((value) => value.length > 0);
      if (lines.length > 0) {
        try {
          const parsedLast = JSON.parse(lines[lines.length - 1]);
          if (parsedLast && typeof parsedLast === 'object') {
            runtimePayload = parsedLast as Record<string, unknown>;
          }
        } catch {}
      }
    }

    const applied = child.status === 0;
    await dbQuery(
      `
      update agent_transfer_decision_inbox
      set status = $1, applied_at = now()
      where approval_id = $2
        and agent_id = $3
        and chain_key = $4
        and status = 'pending'
      `,
      [applied ? 'applied' : 'failed', body.approvalId, body.agentId, chainKey]
    );

    await dbQuery(
      `
      insert into management_audit_log (
        audit_id, agent_id, management_session_id, action_type, action_status,
        public_redacted_payload, private_payload, user_agent, created_at
      ) values ($1, $2, $3, 'transfer_approval.decision', $4, $5::jsonb, $6::jsonb, $7, now())
      `,
      [
        makeId('aud'),
        body.agentId,
        auth.session.sessionId,
        applied ? 'accepted' : 'failed',
        JSON.stringify({ approvalId: body.approvalId, decision: body.decision, chainKey }),
        JSON.stringify({
          runtimeBin,
          approvalSource,
          runtimeArgs,
          runtimeExitStatus: child.status,
          runtimePayload,
          stderr: (child.stderr || '').slice(0, 1200),
          reasonMessage: body.reasonMessage ?? null
        }),
        req.headers.get('user-agent')
      ]
    );

    return successResponse(
      {
        ok: true,
        approvalId: body.approvalId,
        chainKey,
        decision: body.decision,
        runtimeApplied: applied,
        runtimePayload
      },
      200,
      requestId
    );
  } catch {
    return internalErrorResponse(requestId);
  }
}
