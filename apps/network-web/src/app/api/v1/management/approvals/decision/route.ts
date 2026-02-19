import { existsSync } from 'node:fs';
import { spawn, spawnSync } from 'node:child_process';
import { join } from 'node:path';

import type { NextRequest } from 'next/server';

import { dbQuery, withTransaction } from '@/lib/db';
import { issueSignedAgentToken } from '@/lib/agent-token';
import { getEnv } from '@/lib/env';
import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import { parseJsonBody } from '@/lib/http';
import { makeId } from '@/lib/ids';
import { requireManagementWriteAuth } from '@/lib/management-auth';
import { buildWebTradeDecisionProdMessage, dispatchNonTelegramAgentProd } from '@/lib/non-telegram-agent-prod';
import { getRequestId } from '@/lib/request-id';
import { validatePayload } from '@/lib/validation';

export const runtime = 'nodejs';

type ApprovalDecisionRequest = {
  agentId: string;
  tradeId: string;
  decision: 'approve' | 'reject';
  reasonCode?: string;
  reasonMessage?: string;
};

function runtimeCanonicalApprovalDecisionsEnabled(): boolean {
  const raw = (process.env.XCLAW_RUNTIME_CANONICAL_APPROVAL_DECISIONS ?? '').trim().toLowerCase();
  if (!raw) {
    return false;
  }
  return !['0', 'false', 'off', 'no'].includes(raw);
}

function runtimeDecisionTimeoutMs(): number {
  const raw = (process.env.XCLAW_RUNTIME_DECISION_TIMEOUT_MS ?? '').trim();
  if (!raw || !/^\d+$/.test(raw)) {
    return 12000;
  }
  const parsed = Number.parseInt(raw, 10);
  if (!Number.isFinite(parsed) || parsed < 1000) {
    return 12000;
  }
  return parsed;
}

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
  return env;
}

type RuntimeDecisionInvokeResult = {
  queued: boolean;
  runtimeBin: string;
  runtimeArgs: string[];
  payload?: Record<string, unknown>;
  runtimeExitStatus?: number | null;
  timeout?: boolean;
  stderrSummary?: string;
};

function invokeRuntimeDecisionSync(input: {
  req: NextRequest;
  agentId: string;
  chainKey: string;
  tradeId: string;
  decision: 'approve' | 'reject';
  reasonMessage?: string | null;
}): RuntimeDecisionInvokeResult {
  const runtimeBin = resolveRuntimeBin();
  const runtimeArgs = [
    'approvals',
    'decide-spot',
    '--trade-id',
    input.tradeId,
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
  const child = spawnSync(runtimeBin, runtimeArgs, {
    encoding: 'utf8',
    timeout: runtimeDecisionTimeoutMs(),
    env: runtimeSpawnEnv(input.req, input.agentId, input.chainKey)
  });
  const stdout = String(child.stdout ?? '');
  const stderr = String(child.stderr ?? '');
  let payload: Record<string, unknown> | undefined;
  const lines = stdout
    .split(/\r?\n/)
    .map((value) => value.trim())
    .filter((value) => value.length > 0);
  if (lines.length > 0) {
    try {
      const parsed = JSON.parse(lines[lines.length - 1]);
      if (parsed && typeof parsed === 'object') {
        payload = parsed as Record<string, unknown>;
      }
    } catch {}
  }
  const timedOut = child.error?.name === 'Error' && String(child.error?.message || '').toLowerCase().includes('timed out');
  return {
    queued: false,
    runtimeBin,
    runtimeArgs,
    payload,
    runtimeExitStatus: child.status,
    timeout: timedOut,
    stderrSummary: stderr.slice(0, 500),
  };
}

function spawnResumeSpotInBackground(input: {
  req: NextRequest;
  agentId: string;
  tradeId: string;
  chainKey: string;
}): Record<string, unknown> {
  const runtimeBin = resolveRuntimeBin();
  const runtimeArgs = ['approvals', 'resume-spot', '--trade-id', input.tradeId, '--chain', input.chainKey, '--json'];
  try {
    const child = spawn(runtimeBin, runtimeArgs, {
      detached: true,
      stdio: 'ignore',
      env: runtimeSpawnEnv(input.req, input.agentId, input.chainKey)
    });
    child.unref();
    return {
      ok: true,
      code: 'resume_queued_background',
      message: 'Trade resume queued in background runtime process.',
      runtimeBin,
      runtimeArgs
    };
  } catch (error) {
    return {
      ok: false,
      code: 'resume_queue_failed',
      message: String((error as Error)?.message || 'Failed to queue background resume process.'),
      runtimeBin,
      runtimeArgs
    };
  }
}

function enqueueRuntimeDecision(input: {
  req: NextRequest;
  agentId: string;
  tradeId: string;
  chainKey: string;
  decision: 'approve' | 'reject';
  reasonMessage?: string | null;
}): Record<string, unknown> {
  const runtimeBin = resolveRuntimeBin();
  const runtimeArgs = [
    'approvals',
    'decide-spot',
    '--trade-id',
    input.tradeId,
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
      code: 'runtime_decision_queued',
      runtimeBin,
      runtimeArgs
    };
  } catch (error) {
    return {
      ok: false,
      code: 'runtime_decision_queue_failed',
      message: String((error as Error)?.message || 'Failed to queue runtime decision.'),
      runtimeBin,
      runtimeArgs
    };
  }
}

function spawnApprovalPromptSyncInBackground(input: {
  req: NextRequest;
  agentId: string;
  chainKey: string;
}): Record<string, unknown> {
  const runtimeBin = resolveRuntimeBin();
  const runtimeArgs = ['approvals', 'sync', '--chain', input.chainKey, '--json'];
  try {
    const child = spawn(runtimeBin, runtimeArgs, {
      detached: true,
      stdio: 'ignore',
      env: runtimeSpawnEnv(input.req, input.agentId, input.chainKey)
    });
    child.unref();
    return {
      ok: true,
      code: 'approval_prompt_sync_queued',
      message: 'Queued background approval prompt cleanup sync.',
      runtimeBin,
      runtimeArgs
    };
  } catch (error) {
    return {
      ok: false,
      code: 'approval_prompt_sync_queue_failed',
      message: String((error as Error)?.message || 'Failed to queue approval prompt cleanup sync.'),
      runtimeBin,
      runtimeArgs
    };
  }
}

function invokeRuntimePromptCleanupSync(input: {
  req: NextRequest;
  agentId: string;
  tradeId: string;
  chainKey: string;
}): { ok: boolean; code: string; payload?: Record<string, unknown>; runtimeExitStatus?: number | null; stderrSummary?: string } {
  const runtimeBin = resolveRuntimeBin();
  const runtimeArgs = [
    'approvals',
    'clear-prompt',
    '--subject-type',
    'trade',
    '--subject-id',
    input.tradeId,
    '--chain',
    input.chainKey,
    '--json'
  ];
  const child = spawnSync(runtimeBin, runtimeArgs, {
    encoding: 'utf8',
    timeout: runtimeDecisionTimeoutMs(),
    env: runtimeSpawnEnv(input.req, input.agentId, input.chainKey)
  });
  const stdout = String(child.stdout ?? '');
  const stderr = String(child.stderr ?? '');
  let payload: Record<string, unknown> | undefined;
  const lines = stdout
    .split(/\r?\n/)
    .map((value) => value.trim())
    .filter((value) => value.length > 0);
  if (lines.length > 0) {
    try {
      const parsed = JSON.parse(lines[lines.length - 1]);
      if (parsed && typeof parsed === 'object') {
        payload = parsed as Record<string, unknown>;
      }
    } catch {}
  }
  const ok = child.status === 0 && Boolean(payload?.ok);
  return {
    ok,
    code: ok ? 'runtime_cleanup_applied' : 'runtime_cleanup_failed',
    payload,
    runtimeExitStatus: child.status,
    stderrSummary: stderr.slice(0, 500)
  };
}

export async function POST(req: NextRequest) {
  const requestId = getRequestId(req);

  try {
    const parsed = await parseJsonBody(req, requestId);
    if (!parsed.ok) {
      return parsed.response;
    }

    const validated = validatePayload<ApprovalDecisionRequest>('management-approval-decision-request.schema.json', parsed.body);
    if (!validated.ok) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Approval decision payload does not match schema.',
          actionHint: 'Provide agentId, tradeId, and decision.',
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

    if (runtimeCanonicalApprovalDecisionsEnabled()) {
      const tradeRow = await dbQuery<{ status: string; chain_key: string }>(
        `
        select status, chain_key
        from trades
        where trade_id = $1 and agent_id = $2
        limit 1
        `,
        [body.tradeId, body.agentId]
      );
      if ((tradeRow.rowCount ?? 0) === 0) {
        return errorResponse(
          404,
          {
            code: 'payload_invalid',
            message: 'Trade was not found for this agent.',
            actionHint: 'Verify tradeId and retry.'
          },
          requestId
        );
      }
      const chainKey = tradeRow.rows[0].chain_key;
      const invoked = invokeRuntimeDecisionSync({
        req,
        agentId: body.agentId,
        tradeId: body.tradeId,
        chainKey,
        decision: body.decision,
        reasonMessage: body.reasonMessage ?? null,
      });
      await dbQuery(
        `
        insert into management_audit_log (
          audit_id, agent_id, management_session_id, action_type, action_status,
          public_redacted_payload, private_payload, user_agent, created_at
        ) values ($1, $2, $3, 'approval.decision.runtime', $4, $5::jsonb, $6::jsonb, $7, now())
        `,
        [
          makeId('aud'),
          body.agentId,
          auth.session.sessionId,
          invoked.runtimeExitStatus === 0 ? 'accepted' : 'failed',
          JSON.stringify({ tradeId: body.tradeId, decision: body.decision, mode: 'runtime_canonical' }),
          JSON.stringify({ reasonCode: body.reasonCode ?? null, reasonMessage: body.reasonMessage ?? null, runtime: invoked.payload ?? null }),
          req.headers.get('user-agent')
        ]
      );

      const runtimeOk = invoked.runtimeExitStatus === 0 && Boolean(invoked.payload?.ok);
      if (runtimeOk) {
        return successResponse(
          {
            ok: true,
            decisionAccepted: true,
            source: 'runtime',
            tradeId: body.tradeId,
            chainKey,
            runtimeDecision: invoked.payload
          },
          200,
          requestId
        );
      }
      const queued = enqueueRuntimeDecision({
        req,
        agentId: body.agentId,
        tradeId: body.tradeId,
        chainKey,
        decision: body.decision,
        reasonMessage: body.reasonMessage ?? null,
      });
      console.info('[management.approvals.decision] runtime-canonical queued', {
        requestId,
        tradeId: body.tradeId,
        chainKey,
        invoked,
        queued,
      });
      return successResponse(
        {
          ok: true,
          decisionAccepted: true,
          source: 'runtime',
          tradeId: body.tradeId,
          chainKey,
          runtimeDecision: invoked.payload ?? null,
          runtimeQueued: queued
        },
        202,
        requestId
      );
    }

    const targetStatus = body.decision === 'approve' ? 'approved' : 'rejected';
    const eventType = body.decision === 'approve' ? 'trade_approved' : 'trade_rejected';

    const result = await withTransaction(async (client) => {
      const trade = await client.query<{ status: string; chain_key: string }>(
        `
        select status, chain_key
        from trades
        where trade_id = $1
          and agent_id = $2
        limit 1
        `,
        [body.tradeId, body.agentId]
      );

      if (trade.rowCount === 0) {
        return { ok: false as const, kind: 'missing' as const };
      }

      const currentStatus = trade.rows[0].status;
      if (currentStatus !== 'approval_pending') {
        return { ok: false as const, kind: 'transition' as const, currentStatus };
      }

      await client.query(
        `
        update trades
        set
          status = $1::trade_status,
          reason_code = $2,
          reason_message = $3,
          updated_at = now()
        where trade_id = $4
        `,
        [targetStatus, body.reasonCode ?? null, body.reasonMessage ?? null, body.tradeId]
      );

      await client.query(
        `
        insert into agent_events (event_id, agent_id, trade_id, event_type, payload, created_at)
        values ($1, $2, $3, $4, $5::jsonb, now())
        `,
        [
          makeId('evt'),
          body.agentId,
          body.tradeId,
          eventType,
          JSON.stringify({
            decision: body.decision,
            reasonCode: body.reasonCode ?? null,
            reasonMessage: body.reasonMessage ?? null,
            managedBySessionId: auth.session.sessionId
          })
        ]
      );

      await client.query(
        `
        insert into management_audit_log (
          audit_id, agent_id, management_session_id, action_type, action_status,
          public_redacted_payload, private_payload, user_agent, created_at
        ) values ($1, $2, $3, 'approval.decision', 'accepted', $4::jsonb, $5::jsonb, $6, now())
        `,
        [
          makeId('aud'),
          body.agentId,
          auth.session.sessionId,
          JSON.stringify({ tradeId: body.tradeId, decision: body.decision }),
          JSON.stringify({ reasonCode: body.reasonCode ?? null, reasonMessage: body.reasonMessage ?? null }),
          req.headers.get('user-agent')
        ]
      );

      return { ok: true as const, status: targetStatus, chainKey: trade.rows[0].chain_key };
    });

    if (!result.ok) {
      if (result.kind === 'missing') {
        return errorResponse(
          404,
          {
            code: 'payload_invalid',
            message: 'Trade was not found for this agent.',
            actionHint: 'Verify tradeId and retry.'
          },
          requestId
        );
      }

      return errorResponse(
        409,
        {
          code: 'trade_invalid_transition',
          message: 'Trade is not in approval_pending state.',
          actionHint: 'Refresh queue and retry only pending items.',
          details: { currentStatus: result.currentStatus }
        },
        requestId
      );
    }

    const queued = {
      requestId,
      agentId: body.agentId,
      tradeId: body.tradeId,
      chainKey: result.chainKey,
      decision: body.decision,
      reasonMessage: body.reasonMessage ?? null
    };
    setImmediate(() => {
      void (async () => {
        const runtimeCleanup = invokeRuntimePromptCleanupSync({
          req,
          agentId: queued.agentId,
          tradeId: queued.tradeId,
          chainKey: queued.chainKey
        });
        let promptCleanup: Record<string, unknown> = (runtimeCleanup.payload?.promptCleanup && typeof runtimeCleanup.payload.promptCleanup === 'object')
          ? (runtimeCleanup.payload.promptCleanup as Record<string, unknown>)
          : {
              ok: runtimeCleanup.ok,
              code: runtimeCleanup.code
            };
        let cleanupOk = promptCleanup.ok === true;
        let cleanupCode = String(promptCleanup.code ?? '');

        if (cleanupOk) {
          await dbQuery(
            `
            update trade_approval_prompts
            set deleted_at = coalesce(deleted_at, now()), delete_error = null
            where trade_id = $1 and channel = 'telegram'
            `,
            [queued.tradeId]
          );
        } else {
          const cleanupError = String((promptCleanup.error ?? runtimeCleanup.stderrSummary ?? cleanupCode) || 'runtime_clear_failed').slice(0, 500);
          await dbQuery(
            `
            update trade_approval_prompts
            set delete_error = $2
            where trade_id = $1 and channel = 'telegram'
            `,
            [queued.tradeId, cleanupError]
          );
        }

        if (!cleanupOk) {
          const promptSync = spawnApprovalPromptSyncInBackground({
            req,
            agentId: queued.agentId,
            chainKey: queued.chainKey
          });
          console.info('[management.approvals.decision] approval prompt sync dispatch', {
            requestId: queued.requestId,
            tradeId: queued.tradeId,
            chainKey: queued.chainKey,
            promptSync
          });
        }
        console.info('[management.approvals.decision] approval prompt cleanup result', {
          requestId: queued.requestId,
          tradeId: queued.tradeId,
          chainKey: queued.chainKey,
          promptCleanup
        });

        if (queued.decision === 'approve') {
          const runtimeResume = spawnResumeSpotInBackground({
            req,
            agentId: queued.agentId,
            tradeId: queued.tradeId,
            chainKey: queued.chainKey
          });
          console.info('[management.approvals.decision] runtime resume dispatch', {
            requestId: queued.requestId,
            tradeId: queued.tradeId,
            chainKey: queued.chainKey,
            runtimeResume
          });
          return;
        }

        const agentProdDecision = await dispatchNonTelegramAgentProd({
          allowTelegramLastChannel: true,
          message: buildWebTradeDecisionProdMessage({
            decision: queued.decision,
            tradeId: queued.tradeId,
            chainKey: queued.chainKey,
            source: 'web_management_trade_decision',
            reasonMessage: queued.reasonMessage
          })
        });
        console.info('[management.approvals.decision] prod decision dispatch', {
          requestId: queued.requestId,
          tradeId: queued.tradeId,
          chainKey: queued.chainKey,
          agentProdDecision
        });
      })().catch((error) => {
        console.error('[management.approvals.decision] async dispatch failure', {
          requestId: queued.requestId,
          tradeId: queued.tradeId,
          error: String((error as Error)?.message || error)
        });
      });
    });

    return successResponse(
      {
        ok: true,
        tradeId: body.tradeId,
        status: result.status,
        chainKey: result.chainKey,
        runtimeResume: {
          ok: true,
          code: 'resume_dispatch_async',
          message: 'Decision accepted; agent prod/resume dispatch queued asynchronously.'
        },
        agentProdDecision: {
          attempted: false,
          skipped: true,
          reason: 'queued_async'
        }
      },
      200,
      requestId
    );
  } catch {
    return internalErrorResponse(requestId);
  }
}
