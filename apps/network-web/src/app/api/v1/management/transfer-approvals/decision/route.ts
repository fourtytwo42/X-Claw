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

const RUNTIME_RECONCILE_STATUSES = new Set(['approved', 'executing', 'filled', 'failed', 'rejected']);

function runtimeStatusFromPayload(payload: Record<string, unknown> | null): string | null {
  if (!payload) {
    return null;
  }
  const raw = String(payload.status ?? '').trim().toLowerCase();
  if (!RUNTIME_RECONCILE_STATUSES.has(raw)) {
    return null;
  }
  return raw;
}

function transferDecisionRuntimeTimeoutMs(): number {
  const raw = (process.env.XCLAW_TRANSFER_DECISION_TIMEOUT_MS ?? '').trim();
  if (raw.length === 0) {
    return 240_000;
  }
  if (!/^\d+$/.test(raw)) {
    return 240_000;
  }
  const parsed = Number.parseInt(raw, 10);
  if (!Number.isFinite(parsed) || parsed < 1_000) {
    return 240_000;
  }
  return parsed;
}

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

    const child = spawnSync(runtimeBin, runtimeArgs, {
      encoding: 'utf8',
      timeout: transferDecisionRuntimeTimeoutMs()
    });

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

    let applied = child.status === 0;
    let appliedVia: 'runtime' | 'mirror_fallback' | 'none' = applied ? 'runtime' : 'none';

    // Deny should be deterministic from management UI even when immediate runtime application is unavailable.
    if (!applied && body.decision === 'deny') {
      const fallbackReason = body.reasonMessage?.trim() || 'Rejected by owner.';
      const fallbackUpdate = await dbQuery<{ approval_id: string }>(
        `
        update agent_transfer_approval_mirror
        set status = 'rejected',
            reason_message = $1,
            decided_at = now(),
            terminal_at = now(),
            updated_at = now()
        where approval_id = $2
          and agent_id = $3
          and status in ('approval_pending', 'approved')
        returning approval_id
        `,
        [fallbackReason, body.approvalId, body.agentId]
      );
      if ((fallbackUpdate.rowCount ?? 0) > 0) {
        applied = true;
        appliedVia = 'mirror_fallback';
        runtimePayload = {
          ok: true,
          code: 'decision_applied_via_mirror',
          message: 'Transfer deny decision applied via management mirror fallback.'
        };
      }
    }

    // Runtime decisions can succeed locally while mirror sync fails (for example missing runtime API env).
    // Reconcile mirror row from runtime payload so management UI does not remain stuck in approval_pending.
    const reconciledStatus = runtimeStatusFromPayload(runtimePayload);
    if (applied && reconciledStatus) {
      const runtimeTxHash = String(runtimePayload?.txHash ?? '').trim() || null;
      const runtimeReasonCode = String(runtimePayload?.reasonCode ?? '').trim() || null;
      const runtimeReasonMessage = String(runtimePayload?.reasonMessage ?? '').trim() || null;
      const shouldSetDecidedAt = ['approved', 'executing', 'filled', 'failed', 'rejected'].includes(reconciledStatus);
      const shouldSetTerminalAt = ['filled', 'failed', 'rejected'].includes(reconciledStatus);
      await dbQuery(
        `
        update agent_transfer_approval_mirror
        set status = $1::varchar,
            tx_hash = coalesce($2, tx_hash),
            reason_code = $3,
            reason_message = $4,
            decided_at = case
              when $7
                then coalesce(decided_at, now())
              else decided_at
            end,
            terminal_at = case
              when $8
                then coalesce(terminal_at, now())
              else terminal_at
            end,
            updated_at = now()
        where approval_id = $5
          and agent_id = $6
        `,
        [
          reconciledStatus,
          runtimeTxHash,
          runtimeReasonCode,
          runtimeReasonMessage,
          body.approvalId,
          body.agentId,
          shouldSetDecidedAt,
          shouldSetTerminalAt
        ]
      );
      if (appliedVia === 'runtime') {
        appliedVia = 'mirror_fallback';
      }
    }

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
          appliedVia,
          runtimePayload,
          stderr: (child.stderr || '').slice(0, 1200),
          reasonMessage: body.reasonMessage ?? null
        }),
        req.headers.get('user-agent')
      ]
    );

    if (!applied) {
      return errorResponse(
        409,
        {
          code: 'not_actionable',
          message: 'Transfer decision was accepted but could not be applied immediately.',
          actionHint: 'Retry once, then refresh approvals. If it remains pending, verify runtime health.',
          details: {
            approvalId: body.approvalId,
            chainKey,
            decision: body.decision,
            approvalSource,
            runtimeExitStatus: child.status,
            runtimePayload
          }
        },
        requestId
      );
    }

    return successResponse(
      {
        ok: true,
        approvalId: body.approvalId,
        chainKey,
        decision: body.decision,
        appliedVia,
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
