import type { NextRequest } from 'next/server';

import { withTransaction } from '@/lib/db';
import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import { parseJsonBody } from '@/lib/http';
import { makeId } from '@/lib/ids';
import { requireManagementWriteAuth } from '@/lib/management-auth';
import { buildWebTradeDecisionProdMessage, dispatchNonTelegramAgentProd } from '@/lib/non-telegram-agent-prod';
import { getRequestId } from '@/lib/request-id';
import { validatePayload } from '@/lib/validation';

export const runtime = 'nodejs';

type ApproveAllowlistTokenRequest = {
  agentId: string;
  tradeId: string;
};

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

    const validated = validatePayload<ApproveAllowlistTokenRequest>('management-approve-allowlist-token-request.schema.json', parsed.body);
    if (!validated.ok) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Approve + allowlist payload does not match schema.',
          actionHint: 'Provide agentId and tradeId.',
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

    const result = await withTransaction(async (client) => {
      const trade = await client.query<{
        status: string;
        chain_key: string;
        token_in: string;
      }>(
        `
        select status, chain_key, token_in
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

      const tradeRow = trade.rows[0];
      if (tradeRow.status !== 'approval_pending') {
        return { ok: false as const, kind: 'transition' as const, currentStatus: tradeRow.status };
      }

      await client.query(
        `
        update trades
        set
          status = 'approved'::trade_status,
          updated_at = now()
        where trade_id = $1
        `,
        [body.tradeId]
      );

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
        [body.agentId, tradeRow.chain_key]
      );
      if (latest.rowCount === 0) {
        return { ok: false as const, kind: 'missing_policy' as const };
      }

      const snapshot = latest.rows[0];
      const nextAllowed = normalizeTokenSet(snapshot.allowed_tokens);
      const tokenIn = String(tradeRow.token_in ?? '').trim().toLowerCase();
      if (tokenIn) {
        nextAllowed.add(tokenIn);
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
          tradeRow.chain_key,
          snapshot.mode,
          snapshot.approval_mode,
          snapshot.max_trade_usd ?? '0',
          snapshot.max_daily_usd ?? '0',
          JSON.stringify([...nextAllowed]),
          snapshot.daily_cap_usd_enabled,
          snapshot.daily_trade_cap_enabled,
          snapshot.max_daily_trade_count
        ]
      );

      await client.query(
        `
        insert into agent_events (event_id, agent_id, trade_id, event_type, payload, created_at)
        values ($1, $2, $3, 'trade_approved', $4::jsonb, now())
        `,
        [
          makeId('evt'),
          body.agentId,
          body.tradeId,
          JSON.stringify({ decision: 'approve_allowlist', tokenIn: tradeRow.token_in, chainKey: tradeRow.chain_key })
        ]
      );

      await client.query(
        `
        insert into management_audit_log (
          audit_id, agent_id, management_session_id, action_type, action_status,
          public_redacted_payload, private_payload, user_agent, created_at
        ) values ($1, $2, $3, 'approval.allowlist_decision', 'accepted', $4::jsonb, $5::jsonb, $6, now())
        `,
        [
          makeId('aud'),
          body.agentId,
          auth.session.sessionId,
          JSON.stringify({ tradeId: body.tradeId, decision: 'approve_allowlist' }),
          JSON.stringify({ tokenIn: tradeRow.token_in, chainKey: tradeRow.chain_key }),
          req.headers.get('user-agent')
        ]
      );

      return {
        ok: true as const,
        tradeId: body.tradeId,
        chainKey: tradeRow.chain_key,
        allowlistedToken: tradeRow.token_in,
        status: 'approved' as const
      };
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
      if (result.kind === 'transition') {
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
      return errorResponse(
        409,
        {
          code: 'policy_denied',
          message: 'Cannot allowlist token because no chain policy snapshot exists.',
          actionHint: 'Create a policy snapshot first, then retry.'
        },
        requestId
      );
    }

    const agentProdDecision = await dispatchNonTelegramAgentProd({
      allowTelegramLastChannel: true,
      message: buildWebTradeDecisionProdMessage({
        decision: 'approved_allowlist',
        tradeId: result.tradeId,
        chainKey: result.chainKey,
        source: 'web_management_trade_allowlist_decision',
        reasonMessage: null
      })
    });

    return successResponse(
      {
        ...result,
        agentProdDecision
      },
      200,
      requestId
    );
  } catch {
    return internalErrorResponse(requestId);
  }
}
