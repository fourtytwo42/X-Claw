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
import { invokeTransferPromptCleanupNow } from '@/lib/transfer-recovery';
import { validatePayload } from '@/lib/validation';

export const runtime = 'nodejs';

type ManagementTransferApprovalDecisionRequest = {
  agentId: string;
  approvalId: string;
  decision: 'approve' | 'deny';
  reasonMessage?: string | null;
  chainKey?: string;
};

type RuntimeSigningReadiness = {
  walletSigningReady: boolean;
  walletSigningReasonCode: string | null;
  walletSigningCheckedAt: string | null;
};

const HARD_BLOCK_RUNTIME_SIGNING_REASONS = new Set<string>([
  'wallet_passphrase_missing',
  'wallet_passphrase_invalid',
  'wallet_store_unavailable',
  'wallet_missing'
]);

function normalizeChainKey(value: string): string {
  return String(value || '').trim().toLowerCase().replace(/-/g, '_');
}

function resolveRuntimeSigningReadiness(metadata: unknown, chainKey: string): RuntimeSigningReadiness {
  if (!metadata || typeof metadata !== 'object') {
    return {
      walletSigningReady: false,
      walletSigningReasonCode: 'runtime_readiness_missing',
      walletSigningCheckedAt: null
    };
  }
  const root = metadata as Record<string, unknown>;
  const runtimeReadiness = root.runtimeReadiness && typeof root.runtimeReadiness === 'object'
    ? (root.runtimeReadiness as Record<string, unknown>)
    : null;
  const chains = runtimeReadiness?.chains && typeof runtimeReadiness.chains === 'object'
    ? (runtimeReadiness.chains as Record<string, unknown>)
    : null;
  const chainCandidates = [chainKey, normalizeChainKey(chainKey)];
  let chain: Record<string, unknown> | null = null;
  for (const candidate of chainCandidates) {
    if (!candidate || !chains) {
      continue;
    }
    const direct = chains[candidate];
    if (direct && typeof direct === 'object') {
      chain = direct as Record<string, unknown>;
      break;
    }
  }
  if (!chain && chains) {
    const wanted = normalizeChainKey(chainKey);
    for (const [key, value] of Object.entries(chains)) {
      if (normalizeChainKey(key) !== wanted) {
        continue;
      }
      if (value && typeof value === 'object') {
        chain = value as Record<string, unknown>;
        break;
      }
    }
  }
  // Fallback for defensive reliability: when chain-specific key is missing,
  // use the most recent walletSigningReady=true snapshot across chain map.
  if (!chain && chains) {
    let best: { checkedAt: string; value: Record<string, unknown> } | null = null;
    for (const value of Object.values(chains)) {
      if (!value || typeof value !== 'object') {
        continue;
      }
      const record = value as Record<string, unknown>;
      if (!Boolean(record.walletSigningReady)) {
        continue;
      }
      const checkedAt = String(record.walletSigningCheckedAt ?? '').trim() || String(record.updatedAt ?? '').trim();
      if (!checkedAt) {
        continue;
      }
      if (!best || checkedAt > best.checkedAt) {
        best = { checkedAt, value: record };
      }
    }
    if (best) {
      chain = best.value;
    }
  }
  if (!chain) {
    return {
      walletSigningReady: false,
      walletSigningReasonCode: 'runtime_readiness_missing',
      walletSigningCheckedAt: null
    };
  }
  return {
    walletSigningReady: Boolean(chain.walletSigningReady),
    walletSigningReasonCode: String(chain.walletSigningReasonCode ?? '').trim() || null,
    walletSigningCheckedAt: String(chain.walletSigningCheckedAt ?? '').trim() || null
  };
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

    if (body.decision === 'approve') {
      const agentMeta = await dbQuery<{ openclaw_metadata: Record<string, unknown> | null }>(
        `
        select openclaw_metadata
        from agents
        where agent_id = $1
        limit 1
        `,
        [body.agentId]
      );
      const readiness = resolveRuntimeSigningReadiness(agentMeta.rows[0]?.openclaw_metadata ?? null, chainKey);
      const readinessReasonCode = String(readiness.walletSigningReasonCode ?? '').trim() || 'runtime_readiness_missing';
      const shouldHardBlock = !readiness.walletSigningReady && HARD_BLOCK_RUNTIME_SIGNING_REASONS.has(readinessReasonCode);
      if (shouldHardBlock) {
        await dbQuery(
          `
          insert into management_audit_log (
            audit_id, agent_id, management_session_id, action_type, action_status,
            public_redacted_payload, private_payload, user_agent, created_at
          ) values ($1, $2, $3, 'transfer_approval.decision', 'failed', $4::jsonb, $5::jsonb, $6, now())
          `,
          [
            makeId('aud'),
            body.agentId,
            auth.session.sessionId,
            JSON.stringify({ approvalId: body.approvalId, decision: body.decision, chainKey }),
            JSON.stringify({
              approvalSource,
              reasonCode: 'runtime_signing_unavailable',
              readiness
            }),
            req.headers.get('user-agent')
          ]
        );
        return errorResponse(
          409,
          {
            code: 'runtime_signing_unavailable',
            message: 'Agent runtime signing is unavailable for this chain.',
            actionHint: 'Ensure agent runtime has wallet passphrase configured and heartbeat/readiness updates are healthy, then retry approve.',
            details: {
              approvalId: body.approvalId,
              chainKey,
              walletSigningReasonCode: readinessReasonCode,
              walletSigningCheckedAt: readiness.walletSigningCheckedAt
            }
          },
          requestId
        );
      }
      if (!readiness.walletSigningReady && !shouldHardBlock) {
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
              reasonCode: 'runtime_signing_preflight_degraded',
              readiness
            }),
            req.headers.get('user-agent')
          ]
        );
      }
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
    const promptCleanupNow = invokeTransferPromptCleanupNow({
      agentId: body.agentId,
      chainKey,
      approvalId: body.approvalId
    });
    const promptCleanup = (promptCleanupNow.payload?.promptCleanup && typeof promptCleanupNow.payload.promptCleanup === 'object')
      ? (promptCleanupNow.payload.promptCleanup as Record<string, unknown>)
      : {
          ok: false,
          code: promptCleanupNow.code === 'runtime_cleanup_applied' ? 'runtime_cleanup_applied' : 'agent_runtime_cleanup_pending',
          runtimeExitStatus: promptCleanupNow.runtimeExitStatus ?? null
        };

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
            promptCleanup,
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
          promptCleanup,
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
          promptCleanup,
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
        promptCleanup,
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
