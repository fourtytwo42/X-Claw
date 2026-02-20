import { existsSync } from 'node:fs';
import { spawn } from 'node:child_process';
import { join } from 'node:path';

import type { NextRequest } from 'next/server';

import { dbQuery } from '@/lib/db';
import { issueSignedAgentToken } from '@/lib/agent-token';
import { getEnv } from '@/lib/env';
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

function resolveRuntimeBin(): string {
  const cwd = process.cwd();
  const candidates = [
    process.env.XCLAW_AGENT_RUNTIME_BIN?.trim() ?? '',
    join(cwd, 'apps', 'agent-runtime', 'bin', 'xclaw-agent'),
    join(cwd, '..', 'agent-runtime', 'bin', 'xclaw-agent')
  ].filter((value) => value.length > 0);
  for (const candidate of candidates) {
    if (existsSync(candidate)) {
      return candidate;
    }
  }
  throw new Error('xclaw-agent runtime binary not found. Set XCLAW_AGENT_RUNTIME_BIN or deploy apps/agent-runtime/bin/xclaw-agent.');
}

function resolveRuntimeApiBase(req: NextRequest): string {
  const explicit = (process.env.XCLAW_API_BASE_URL ?? '').trim();
  if (explicit.length > 0) {
    return explicit;
  }
  return `${req.nextUrl.origin}/api/v1`;
}

function runtimeSpawnEnv(req: NextRequest, agentId: string, chainKey: string): NodeJS.ProcessEnv {
  const env: NodeJS.ProcessEnv = {
    ...process.env,
    XCLAW_API_BASE_URL: resolveRuntimeApiBase(req),
    XCLAW_AGENT_ID: agentId,
    XCLAW_DEFAULT_CHAIN: chainKey
  };
  if (!(env.XCLAW_AGENT_API_KEY ?? '').trim()) {
    const mapped = getEnv().agentApiKeys[agentId];
    if (mapped) {
      env.XCLAW_AGENT_API_KEY = mapped;
    } else {
      const signed = issueSignedAgentToken(agentId);
      if (signed) {
        env.XCLAW_AGENT_API_KEY = signed;
      }
    }
  }
  if (!(env.XCLAW_WALLET_PASSPHRASE ?? '').trim()) {
    const mapped = resolveAgentWalletPassphrase(agentId);
    if (mapped) {
      env.XCLAW_WALLET_PASSPHRASE = mapped;
    }
  }
  return env;
}

function resolveAgentWalletPassphrase(agentId: string): string | null {
  const direct = String(process.env.XCLAW_WALLET_PASSPHRASE ?? '').trim();
  if (direct) {
    return direct;
  }
  const raw = String(process.env.XCLAW_AGENT_WALLET_PASSPHRASES ?? '').trim();
  if (!raw) {
    return null;
  }
  try {
    const parsed = JSON.parse(raw) as Record<string, unknown>;
    const value = parsed && typeof parsed === 'object' ? parsed[agentId] : null;
    const mapped = typeof value === 'string' ? value.trim() : '';
    return mapped || null;
  } catch {
    return null;
  }
}

function enqueueTransferRuntimeDecision(input: {
  req: NextRequest;
  agentId: string;
  approvalId: string;
  chainKey: string;
  decision: 'approve' | 'deny';
  reasonMessage?: string | null;
  approvalSource: 'transfer' | 'x402';
}): Record<string, unknown> {
  const runtimeBin = resolveRuntimeBin();
  const runtimeArgs =
    input.approvalSource === 'x402'
      ? [
          'x402',
          'pay-decide',
          '--approval-id',
          input.approvalId,
          '--decision',
          input.decision === 'approve' ? 'approve' : 'deny',
          '--json'
        ]
      : [
          'approvals',
          'decide-transfer',
          '--approval-id',
          input.approvalId,
          '--decision',
          input.decision,
          '--chain',
          input.chainKey,
          '--source',
          'web',
          '--json'
        ];
  const reason = String(input.reasonMessage ?? '').trim();
  if (reason) {
    runtimeArgs.push('--reason-message', reason);
  }
  try {
    const child = spawn(runtimeBin, runtimeArgs, {
      detached: true,
      stdio: 'ignore',
      env: runtimeSpawnEnv(input.req, input.agentId, input.chainKey)
    });
    child.unref();
    return {
      ok: true,
      code: 'runtime_transfer_decision_queued',
      runtimeBin,
      runtimeArgs
    };
  } catch (error) {
    return {
      ok: false,
      code: 'runtime_transfer_decision_queue_failed',
      message: String((error as Error)?.message || 'Failed to queue runtime transfer decision.'),
      runtimeBin,
      runtimeArgs
    };
  }
}

function enqueueTransferPromptCleanup(input: {
  req: NextRequest;
  agentId: string;
  approvalId: string;
  chainKey: string;
}): Record<string, unknown> {
  const runtimeBin = resolveRuntimeBin();
  const runtimeArgs = [
    'approvals',
    'clear-prompt',
    '--subject-type',
    'transfer',
    '--subject-id',
    input.approvalId,
    '--chain',
    input.chainKey,
    '--json'
  ];
  try {
    const child = spawn(runtimeBin, runtimeArgs, {
      detached: true,
      stdio: 'ignore',
      env: runtimeSpawnEnv(input.req, input.agentId, input.chainKey)
    });
    child.unref();
    return {
      ok: true,
      code: 'runtime_cleanup_queued',
      runtimeBin,
      runtimeArgs
    };
  } catch (error) {
    return {
      ok: false,
      code: 'runtime_cleanup_queue_failed',
      message: String((error as Error)?.message || 'Failed to queue runtime prompt cleanup.'),
      runtimeBin,
      runtimeArgs
    };
  }
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
          where approval_id = $1
            and agent_id = $2
            and chain_key = $3
            and status = 'pending'
          `,
          [body.approvalId, body.agentId, chainKey]
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

      const promptCleanup = enqueueTransferPromptCleanup({
        req,
        agentId: body.agentId,
        approvalId: body.approvalId,
        chainKey
      });

      await dbQuery(
        `
        update agent_transfer_decision_inbox
        set status = 'applied', applied_at = now()
        where approval_id = $1
          and agent_id = $2
          and chain_key = $3
          and status = 'pending'
        `,
        [body.approvalId, body.agentId, chainKey]
      );

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
            runtimeQueued: {
              ok: false,
              code: 'runtime_transfer_decision_skipped',
              reason: 'deny_applied_directly'
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
          runtimeQueued: {
            ok: false,
            code: 'runtime_transfer_decision_skipped',
            reason: 'deny_applied_directly'
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

    const walletPassphrasePresent = Boolean(resolveAgentWalletPassphrase(body.agentId));
    if (!walletPassphrasePresent) {
      await dbQuery(
        `
        update agent_transfer_decision_inbox
        set status = 'failed', applied_at = now()
        where approval_id = $1
          and agent_id = $2
          and chain_key = $3
          and status = 'pending'
        `,
        [body.approvalId, body.agentId, chainKey]
      );
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
            reasonMessage: body.reasonMessage ?? null,
            reasonCode: 'runtime_wallet_passphrase_missing'
          }),
          req.headers.get('user-agent')
        ]
      );
      return errorResponse(
        503,
        {
          code: 'not_actionable',
          message: 'Runtime wallet passphrase is not configured for transfer execution.',
          actionHint:
            'Set XCLAW_WALLET_PASSPHRASE (or XCLAW_AGENT_WALLET_PASSPHRASES mapping for this agent) in web runtime env and retry approve.',
          details: {
            approvalId: body.approvalId,
            agentId: body.agentId,
            chainKey
          }
        },
        requestId
      );
    }

    const runtimeQueued = enqueueTransferRuntimeDecision({
      req,
      agentId: body.agentId,
      approvalId: body.approvalId,
      chainKey,
      decision: body.decision,
      reasonMessage: body.reasonMessage ?? null,
      approvalSource
    });

    if (!runtimeQueued.ok) {
      await dbQuery(
        `
        update agent_transfer_decision_inbox
        set status = 'failed', applied_at = now()
        where approval_id = $1
          and agent_id = $2
          and chain_key = $3
          and status = 'pending'
        `,
        [body.approvalId, body.agentId, chainKey]
      );
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
            runtimeQueued,
            reasonMessage: body.reasonMessage ?? null
          }),
          req.headers.get('user-agent')
        ]
      );
      return errorResponse(
        503,
        {
          code: 'not_actionable',
          message: 'Transfer approve decision could not be queued in runtime.',
          actionHint: 'Retry once. If this persists, verify runtime availability and API key wiring.',
          details: {
            approvalId: body.approvalId,
            chainKey,
            approvalSource,
            runtimeQueued
          }
        },
        requestId
      );
    }

    await dbQuery(
      `
      update agent_transfer_approval_mirror
      set status = 'approved',
          decided_at = coalesce(decided_at, now()),
          updated_at = now()
      where approval_id = $1
        and agent_id = $2
        and status in ('approval_pending', 'approved')
      `,
      [body.approvalId, body.agentId]
    );

    const promptCleanup = enqueueTransferPromptCleanup({
      req,
      agentId: body.agentId,
      approvalId: body.approvalId,
      chainKey
    });

    await dbQuery(
      `
      update agent_transfer_decision_inbox
      set status = 'applied', applied_at = now()
      where approval_id = $1
        and agent_id = $2
        and chain_key = $3
        and status = 'pending'
      `,
      [body.approvalId, body.agentId, chainKey]
    );

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
          appliedVia: 'runtime_async_queue',
          runtimeQueued,
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
        appliedVia: 'runtime_async_queue',
        runtimeQueued,
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
