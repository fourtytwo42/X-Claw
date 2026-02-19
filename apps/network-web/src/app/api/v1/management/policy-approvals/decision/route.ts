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
import { getRequestId } from '@/lib/request-id';
import { validatePayload } from '@/lib/validation';

export const runtime = 'nodejs';

type ManagementPolicyApprovalDecisionRequest = {
  agentId: string;
  policyApprovalId: string;
  decision: 'approve' | 'reject';
  reasonMessage?: string | null;
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

export async function POST(req: NextRequest) {
  const requestId = getRequestId(req);

  try {
    const parsed = await parseJsonBody(req, requestId);
    if (!parsed.ok) {
      return parsed.response;
    }

    const validated = validatePayload<ManagementPolicyApprovalDecisionRequest>('management-policy-approval-decision-request.schema.json', parsed.body);
    if (!validated.ok) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Policy approval decision payload does not match schema.',
          actionHint: 'Provide agentId, policyApprovalId, decision, and optional reasonMessage.',
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
      const approvalRow = await dbQuery<{ chain_key: string }>(
        `
        select chain_key
        from agent_policy_approval_requests
        where request_id = $1 and agent_id = $2
        limit 1
        `,
        [body.policyApprovalId, body.agentId]
      );
      if ((approvalRow.rowCount ?? 0) === 0) {
        return errorResponse(
          404,
          {
            code: 'payload_invalid',
            message: 'Policy approval request was not found.',
            actionHint: 'Verify policyApprovalId and retry.'
          },
          requestId
        );
      }
      const chainKey = approvalRow.rows[0].chain_key;
      const runtimeBin = resolveRuntimeBin();
      const runtimeArgs = [
        'approvals',
        'decide-policy',
        '--approval-id',
        body.policyApprovalId,
        '--decision',
        body.decision,
        '--chain',
        chainKey,
        '--source',
        'web',
        '--json'
      ];
      const reason = String(body.reasonMessage ?? '').trim();
      if (reason) {
        runtimeArgs.push('--reason-message', reason);
      }
      const child = spawnSync(runtimeBin, runtimeArgs, {
        encoding: 'utf8',
        timeout: runtimeDecisionTimeoutMs(),
        env: runtimeSpawnEnv(req, body.agentId, chainKey)
      });
      let payload: Record<string, unknown> | null = null;
      const lines = String(child.stdout ?? '')
        .split(/\r?\n/)
        .map((value) => value.trim())
        .filter((value) => value.length > 0);
      if (lines.length > 0) {
        try {
          const parsedLast = JSON.parse(lines[lines.length - 1]);
          if (parsedLast && typeof parsedLast === 'object') {
            payload = parsedLast as Record<string, unknown>;
          }
        } catch {}
      }
      await dbQuery(
        `
        insert into management_audit_log (
          audit_id, agent_id, management_session_id, action_type, action_status,
          public_redacted_payload, private_payload, user_agent, created_at
        ) values ($1, $2, $3, 'policy_approval.decision.runtime', $4, $5::jsonb, $6::jsonb, $7, now())
        `,
        [
          makeId('aud'),
          body.agentId,
          auth.session.sessionId,
          child.status === 0 ? 'accepted' : 'failed',
          JSON.stringify({ policyApprovalId: body.policyApprovalId, decision: body.decision, mode: 'runtime_canonical' }),
          JSON.stringify({ reasonMessage: body.reasonMessage ?? null, runtime: payload ?? null }),
          req.headers.get('user-agent')
        ]
      );
      if (child.status === 0 && payload?.ok) {
        return successResponse({ ok: true, source: 'runtime', policyApprovalId: body.policyApprovalId, runtimeDecision: payload }, 200, requestId);
      }
      try {
        const bg = spawn(runtimeBin, runtimeArgs, {
          detached: true,
          stdio: 'ignore',
          env: runtimeSpawnEnv(req, body.agentId, chainKey)
        });
        bg.unref();
      } catch {}
      return successResponse(
        {
          ok: true,
          source: 'runtime',
          policyApprovalId: body.policyApprovalId,
          runtimeDecision: payload,
          queued: true
        },
        202,
        requestId
      );
    }

    const decisionAt = new Date().toISOString();
    const toStatus = body.decision === 'approve' ? 'approved' : 'rejected';

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
        [body.policyApprovalId]
      );

      if (approval.rowCount === 0) {
        return { ok: false as const, kind: 'missing' as const };
      }

      const row = approval.rows[0];
      if (row.agent_id !== body.agentId) {
        return { ok: false as const, kind: 'agent_mismatch' as const };
      }
      if (row.status !== 'approval_pending') {
        return { ok: false as const, kind: 'not_actionable' as const, currentStatus: row.status };
      }

      await client.query(
        `
        update agent_policy_approval_requests
        set
          status = $1,
          reason_message = $2,
          decided_by_management_session_id = $3,
          decided_at = $4::timestamptz,
          updated_at = now()
        where request_id = $5
        `,
        [toStatus, body.reasonMessage ?? null, auth.session.sessionId, decisionAt, body.policyApprovalId]
      );

      if (toStatus === 'approved') {
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
            and chain_key = $2
          order by created_at desc
          limit 1
          `,
          [body.agentId, row.chain_key]
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
            snapshot_id, agent_id, chain_key, mode, approval_mode, max_trade_usd, max_daily_usd, allowed_tokens,
            daily_cap_usd_enabled, daily_trade_cap_enabled, max_daily_trade_count, created_at
          ) values ($1, $2, $3, $4::policy_mode, $5::policy_approval_mode, $6::numeric, $7::numeric, $8::jsonb, $9, $10, $11, now())
          `,
          [
            makeId('pol'),
            body.agentId,
            row.chain_key,
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
        values ($1, $2, null, $3, $4::jsonb, now())
        `,
        [
          makeId('evt'),
          body.agentId,
          toStatus === 'approved' ? 'policy_approved' : 'policy_rejected',
          JSON.stringify({
            policyApprovalId: body.policyApprovalId,
            chainKey: row.chain_key,
            requestType: row.request_type,
            tokenAddress: row.token_address ?? null,
            reasonMessage: body.reasonMessage ?? null,
            source: 'web'
          })
        ]
      );

      await client.query(
        `
        insert into management_audit_log (
          audit_id, agent_id, management_session_id, action_type, action_status,
          public_redacted_payload, private_payload, user_agent, created_at
        ) values ($1, $2, $3, 'policy_approval.decision', 'accepted', $4::jsonb, $5::jsonb, $6, now())
        `,
        [
          makeId('aud'),
          body.agentId,
          auth.session.sessionId,
          JSON.stringify({ policyApprovalId: body.policyApprovalId, decision: body.decision }),
          JSON.stringify({ requestType: row.request_type, tokenAddress: row.token_address ?? null, reasonMessage: body.reasonMessage ?? null }),
          req.headers.get('user-agent')
        ]
      );

      return { ok: true as const };
    });

    if (!result.ok) {
      if (result.kind === 'missing') {
        return errorResponse(
          404,
          { code: 'payload_invalid', message: 'Policy approval request was not found.', actionHint: 'Verify policyApprovalId and retry.' },
          requestId
        );
      }
      if (result.kind === 'agent_mismatch') {
        return errorResponse(
          401,
          { code: 'auth_invalid', message: 'Request does not belong to this agent.', actionHint: 'Use the correct agent management session.' },
          requestId
        );
      }
      if (result.kind === 'not_actionable') {
        return errorResponse(
          409,
          {
            code: 'not_actionable',
            message: 'Policy approval request is not actionable from its current status.',
            actionHint: 'Refresh and retry with an approval_pending request.',
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

    return successResponse({ ok: true, policyApprovalId: body.policyApprovalId, status: toStatus }, 200, requestId);
  } catch {
    return internalErrorResponse(requestId);
  }
}
