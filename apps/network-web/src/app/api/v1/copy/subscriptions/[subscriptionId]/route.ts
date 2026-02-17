import type { NextRequest } from 'next/server';

import { withTransaction } from '@/lib/db';
import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import { parseJsonBody } from '@/lib/http';
import { requireCsrfToken, requireManagementSession } from '@/lib/management-auth';
import { recomputeMetricsForAgents } from '@/lib/metrics';
import { getRequestId } from '@/lib/request-id';
import { validatePayload } from '@/lib/validation';

export const runtime = 'nodejs';

type CopySubscriptionPatchRequest = {
  enabled?: boolean;
  scaleBps?: number;
  maxTradeUsd?: string;
  allowedTokens?: string[];
};

export async function PATCH(
  req: NextRequest,
  context: { params: Promise<{ subscriptionId: string }> }
) {
  const requestId = getRequestId(req);

  try {
    const { subscriptionId } = await context.params;

    const auth = await requireManagementSession(req, requestId);
    if (!auth.ok) {
      return auth.response;
    }

    const csrf = requireCsrfToken(req, requestId);
    if (!csrf.ok) {
      return csrf.response;
    }

    const parsed = await parseJsonBody(req, requestId);
    if (!parsed.ok) {
      return parsed.response;
    }

    const validated = validatePayload<CopySubscriptionPatchRequest>('copy-subscription-patch-request.schema.json', parsed.body);
    if (!validated.ok) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Copy subscription patch payload does not match schema.',
          actionHint: 'Use one or more mutable fields: enabled, scaleBps, maxTradeUsd, allowedTokens.',
          details: validated.details
        },
        requestId
      );
    }

    const body = validated.data;

    const result = await withTransaction(async (client) => {
      const current = await client.query<{
        subscription_id: string;
        leader_agent_id: string;
        follower_agent_id: string;
        enabled: boolean;
        scale_bps: number;
        max_trade_usd: string | null;
        allowed_tokens: string[] | null;
      }>(
        `
        select
          subscription_id,
          leader_agent_id,
          follower_agent_id,
          enabled,
          scale_bps,
          max_trade_usd::text,
          allowed_tokens
        from copy_subscriptions
        where subscription_id = $1
        limit 1
        `,
        [subscriptionId]
      );

      if ((current.rowCount ?? 0) === 0) {
        return { ok: false as const, kind: 'missing' as const };
      }

      const row = current.rows[0];
      if (row.follower_agent_id !== auth.session.agentId) {
        return { ok: false as const, kind: 'forbidden' as const };
      }

      const nextEnabled = body.enabled ?? row.enabled;
      const nextScaleBps = body.scaleBps ?? row.scale_bps;
      const nextMaxTradeUsd = body.maxTradeUsd ?? row.max_trade_usd;
      const nextAllowedTokens = body.allowedTokens ?? row.allowed_tokens ?? [];

      const updated = await client.query<{
        subscription_id: string;
        leader_agent_id: string;
        follower_agent_id: string;
        enabled: boolean;
        scale_bps: number;
        max_trade_usd: string | null;
        allowed_tokens: string[] | null;
        created_at: string;
        updated_at: string;
      }>(
        `
        update copy_subscriptions
        set
          enabled = $2,
          scale_bps = $3,
          max_trade_usd = $4::numeric,
          allowed_tokens = $5::jsonb,
          updated_at = now()
        where subscription_id = $1
        returning
          subscription_id,
          leader_agent_id,
          follower_agent_id,
          enabled,
          scale_bps,
          max_trade_usd::text,
          allowed_tokens,
          created_at::text,
          updated_at::text
        `,
        [subscriptionId, nextEnabled, nextScaleBps, nextMaxTradeUsd, JSON.stringify(nextAllowedTokens)]
      );

      await recomputeMetricsForAgents(client, [updated.rows[0].leader_agent_id, updated.rows[0].follower_agent_id]);

      return { ok: true as const, row: updated.rows[0] };
    });

    if (!result.ok) {
      if (result.kind === 'missing') {
        return errorResponse(
          404,
          {
            code: 'payload_invalid',
            message: 'Copy subscription was not found.',
            actionHint: 'Verify subscriptionId and retry.'
          },
          requestId
        );
      }

      return errorResponse(
        401,
        {
          code: 'auth_invalid',
          message: 'Subscription does not belong to authenticated follower session.',
          actionHint: 'Use the management session for the subscription follower agent.'
        },
        requestId
      );
    }

    return successResponse(
      {
        ok: true,
        subscription: {
          subscriptionId: result.row.subscription_id,
          leaderAgentId: result.row.leader_agent_id,
          followerAgentId: result.row.follower_agent_id,
          enabled: result.row.enabled,
          scaleBps: result.row.scale_bps,
          maxTradeUsd: result.row.max_trade_usd,
          allowedTokens: result.row.allowed_tokens ?? [],
          createdAt: result.row.created_at,
          updatedAt: result.row.updated_at
        }
      },
      200,
      requestId
    );
  } catch {
    return internalErrorResponse(requestId);
  }
}

export async function DELETE(
  req: NextRequest,
  context: { params: Promise<{ subscriptionId: string }> }
) {
  const requestId = getRequestId(req);

  try {
    const { subscriptionId } = await context.params;

    const auth = await requireManagementSession(req, requestId);
    if (!auth.ok) {
      return auth.response;
    }

    const csrf = requireCsrfToken(req, requestId);
    if (!csrf.ok) {
      return csrf.response;
    }

    const result = await withTransaction(async (client) => {
      const existing = await client.query<{
        subscription_id: string;
        leader_agent_id: string;
        follower_agent_id: string;
      }>(
        `
        select subscription_id, leader_agent_id, follower_agent_id
        from copy_subscriptions
        where subscription_id = $1
        limit 1
        `,
        [subscriptionId]
      );

      if ((existing.rowCount ?? 0) === 0) {
        return { ok: false as const, kind: 'missing' as const };
      }

      const row = existing.rows[0];
      if (row.follower_agent_id !== auth.session.agentId) {
        return { ok: false as const, kind: 'forbidden' as const };
      }

      await client.query('delete from copy_subscriptions where subscription_id = $1', [subscriptionId]);
      await recomputeMetricsForAgents(client, [row.leader_agent_id, row.follower_agent_id]);
      return { ok: true as const };
    });

    if (!result.ok) {
      if (result.kind === 'missing') {
        return errorResponse(
          404,
          {
            code: 'payload_invalid',
            message: 'Copy subscription was not found.',
            actionHint: 'Verify subscriptionId and retry.'
          },
          requestId
        );
      }

      return errorResponse(
        401,
        {
          code: 'auth_invalid',
          message: 'Subscription does not belong to authenticated follower session.',
          actionHint: 'Use the management session for the subscription follower agent.'
        },
        requestId
      );
    }

    return successResponse({ ok: true, subscriptionId }, 200, requestId);
  } catch {
    return internalErrorResponse(requestId);
  }
}
