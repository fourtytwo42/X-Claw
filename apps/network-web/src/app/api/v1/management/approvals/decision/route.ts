import { existsSync } from 'node:fs';
import { spawnSync } from 'node:child_process';

import type { NextRequest } from 'next/server';

import { withTransaction } from '@/lib/db';
import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import { parseJsonBody } from '@/lib/http';
import { makeId } from '@/lib/ids';
import { requireManagementWriteAuth } from '@/lib/management-auth';
import {
  buildWebTradeDecisionProdMessage,
  buildWebTradeResultProdMessage,
  dispatchNonTelegramAgentProd,
  isTradeTerminalStatus
} from '@/lib/non-telegram-agent-prod';
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

function approvalDecisionRuntimeTimeoutMs(): number {
  const raw = (process.env.XCLAW_APPROVAL_DECISION_TIMEOUT_MS ?? '').trim();
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

    let runtimeResume: Record<string, unknown> | null = null;
    const agentProdDecision = await dispatchNonTelegramAgentProd({
      allowTelegramLastChannel: true,
      message: buildWebTradeDecisionProdMessage({
        decision: body.decision,
        tradeId: body.tradeId,
        chainKey: result.chainKey,
        source: 'web_management_trade_decision',
        reasonMessage: body.reasonMessage ?? null
      })
    });
    let agentProdTerminal: Awaited<ReturnType<typeof dispatchNonTelegramAgentProd>> | null = null;

    if (body.decision === 'approve') {
      const runtimeBin = resolveRuntimeBin();
      const runtimeArgs = ['approvals', 'resume-spot', '--trade-id', body.tradeId, '--chain', result.chainKey, '--json'];
      const child = spawnSync(runtimeBin, runtimeArgs, {
        encoding: 'utf8',
        timeout: approvalDecisionRuntimeTimeoutMs()
      });
      if (child.stdout) {
        const lines = child.stdout
          .split(/\r?\n/)
          .map((value) => value.trim())
          .filter((value) => value.length > 0);
        if (lines.length > 0) {
          try {
            const parsedLast = JSON.parse(lines[lines.length - 1]);
            if (parsedLast && typeof parsedLast === 'object') {
              runtimeResume = parsedLast as Record<string, unknown>;
            }
          } catch {}
        }
      }
      if (!runtimeResume) {
        runtimeResume = {
          ok: child.status === 0,
          code: child.status === 0 ? 'ok' : 'resume_failed',
          runtimeExitStatus: child.status,
          stderr: (child.stderr || '').slice(0, 1200)
        };
      }

      const terminalStatus = String(runtimeResume.status ?? '').trim().toLowerCase();
      if (isTradeTerminalStatus(terminalStatus)) {
        agentProdTerminal = await dispatchNonTelegramAgentProd({
          allowTelegramLastChannel: true,
          message: buildWebTradeResultProdMessage({
            status: terminalStatus,
            tradeId: body.tradeId,
            chainKey: result.chainKey,
            txHash: String(runtimeResume.txHash ?? '').trim() || null,
            source: 'web_management_trade_decision_resume',
            reasonMessage: String(runtimeResume.reasonMessage ?? '').trim() || (body.reasonMessage ?? null)
          })
        });
      }
    }

    return successResponse(
      {
        ok: true,
        tradeId: body.tradeId,
        status: result.status,
        chainKey: result.chainKey,
        runtimeResume,
        agentProdDecision,
        agentProdTerminal
      },
      200,
      requestId
    );
  } catch {
    return internalErrorResponse(requestId);
  }
}
