import type { NextRequest } from 'next/server';

import { dbQuery } from '@/lib/db';
import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import { parseJsonBody } from '@/lib/http';
import { makeId } from '@/lib/ids';
import { requireManagementWriteAuth } from '@/lib/management-auth';
import {
  buildWebTransferDecisionProdMessage,
  dispatchNonTelegramAgentProd
} from '@/lib/non-telegram-agent-prod';
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

    const decisionId = makeId('tdi');
    await dbQuery(
      `
      insert into agent_transfer_decision_inbox (
        decision_id, approval_id, agent_id, chain_key, decision, reason_message, source, status, created_at
      ) values ($1, $2, $3, $4, $5, $6, 'web', 'pending', now())
      `,
      [decisionId, body.approvalId, body.agentId, chainKey, body.decision, body.reasonMessage ?? null]
    );

    if (body.decision === 'deny') {
      const fallbackReason = body.reasonMessage?.trim() || 'Rejected by owner.';
      const appliedUpdate = await dbQuery<{ approval_id: string }>(
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
      if ((appliedUpdate.rowCount ?? 0) === 0) {
        await dbQuery(
          `
          update agent_transfer_decision_inbox
          set status = 'failed', applied_at = now()
          where decision_id = $1
            and status = 'pending'
          `,
          [decisionId]
        );
        return errorResponse(
          409,
          {
            code: 'not_actionable',
            message: 'Transfer approval is no longer actionable.',
            actionHint: 'Refresh queue and retry only pending items.'
          },
          requestId
        );
      }

      setImmediate(() => {
        void (async () => {
          const agentProdDecision = await dispatchNonTelegramAgentProd({
            allowTelegramLastChannel: true,
            message: buildWebTransferDecisionProdMessage({
              decision: body.decision,
              approvalId: body.approvalId,
              chainKey,
              source: 'web_management_transfer_decision',
              reasonMessage: body.reasonMessage ?? null
            })
          });
          console.info('[management.transfer_approvals.decision] prod decision dispatch', {
            requestId,
            approvalId: body.approvalId,
            chainKey,
            decision: body.decision,
            agentProdDecision
          });
        })().catch((error) => {
          console.error('[management.transfer_approvals.decision] async prod decision dispatch failure', {
            requestId,
            approvalId: body.approvalId,
            decision: body.decision,
            error: String((error as Error)?.message || error)
          });
        });
      });

      await dbQuery(
        `
        insert into management_audit_log (
          audit_id, agent_id, management_session_id, action_type, action_status,
          public_redacted_payload, private_payload, user_agent, created_at
        ) values ($1, $2, $3, 'transfer_approval.decision', 'accepted', $4::jsonb, $5::jsonb, $6, now())
        `,
        [
          makeId('aud'),
          body.agentId,
          auth.session.sessionId,
          JSON.stringify({ approvalId: body.approvalId, decision: body.decision, chainKey }),
          JSON.stringify({
            approvalSource,
            appliedVia: 'mirror_fallback',
            decisionInbox: {
              decisionId,
              status: 'pending'
            },
            promptCleanup: {
              ok: false,
              code: 'agent_runtime_cleanup_pending'
            },
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
          status: 'rejected',
          appliedVia: 'mirror_fallback',
          decisionInbox: {
            decisionId,
            status: 'pending'
          },
          promptCleanup: {
            ok: false,
            code: 'agent_runtime_cleanup_pending'
          },
          agentProdTerminal: {
            attempted: false,
            skipped: true,
            reason: 'queued_async'
          }
        },
        200,
        requestId
      );
    }

    const appliedUpdate = await dbQuery<{ approval_id: string }>(
      `
      update agent_transfer_approval_mirror
      set status = 'approved',
          decided_at = coalesce(decided_at, now()),
          updated_at = now()
      where approval_id = $1
        and agent_id = $2
        and status in ('approval_pending', 'approved')
      returning approval_id
      `,
      [body.approvalId, body.agentId]
    );

    if ((appliedUpdate.rowCount ?? 0) === 0) {
      await dbQuery(
        `
        update agent_transfer_decision_inbox
        set status = 'failed', applied_at = now()
        where decision_id = $1
          and status = 'pending'
        `,
        [decisionId]
      );
      return errorResponse(
        409,
        {
          code: 'not_actionable',
          message: 'Transfer approval is no longer actionable.',
          actionHint: 'Refresh queue and retry only pending items.'
        },
        requestId
      );
    }

    setImmediate(() => {
      void (async () => {
        const agentProdDecision = await dispatchNonTelegramAgentProd({
          allowTelegramLastChannel: true,
          message: buildWebTransferDecisionProdMessage({
            decision: body.decision,
            approvalId: body.approvalId,
            chainKey,
            source: 'web_management_transfer_decision',
            reasonMessage: body.reasonMessage ?? null
          })
        });
        console.info('[management.transfer_approvals.decision] prod decision dispatch', {
          requestId,
          approvalId: body.approvalId,
          chainKey,
          decision: body.decision,
          agentProdDecision
        });
      })().catch((error) => {
        console.error('[management.transfer_approvals.decision] async prod decision dispatch failure', {
          requestId,
          approvalId: body.approvalId,
          decision: body.decision,
          error: String((error as Error)?.message || error)
        });
      });
    });

    await dbQuery(
      `
      insert into management_audit_log (
        audit_id, agent_id, management_session_id, action_type, action_status,
        public_redacted_payload, private_payload, user_agent, created_at
      ) values ($1, $2, $3, 'transfer_approval.decision', 'accepted', $4::jsonb, $5::jsonb, $6, now())
      `,
      [
        makeId('aud'),
        body.agentId,
        auth.session.sessionId,
        JSON.stringify({ approvalId: body.approvalId, decision: body.decision, chainKey }),
        JSON.stringify({
          approvalSource,
          appliedVia: 'agent_runtime_inbox_queue',
          decisionInbox: {
            decisionId,
            status: 'pending'
          },
          promptCleanup: {
            ok: false,
            code: 'agent_runtime_cleanup_pending'
          },
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
        status: 'approved',
        appliedVia: 'agent_runtime_inbox_queue',
        decisionInbox: {
          decisionId,
          status: 'pending'
        },
        promptCleanup: {
          ok: false,
          code: 'agent_runtime_cleanup_pending'
        },
        agentProdTerminal: {
          attempted: false,
          skipped: true,
          reason: 'queued_async'
        }
      },
      202,
      requestId
    );
  } catch {
    return internalErrorResponse(requestId);
  }
}
