import type { NextRequest } from 'next/server';

import { dbQuery } from '@/lib/db';
import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import { parseJsonBody } from '@/lib/http';
import { makeId } from '@/lib/ids';
import { requireManagementSession, requireManagementWriteAuth } from '@/lib/management-auth';
import { getRequestId } from '@/lib/request-id';
import { validatePayload } from '@/lib/validation';

export const runtime = 'nodejs';

type ManagementTrackedAgentsUpsertRequest = {
  agentId: string;
  trackedAgentId: string;
};

type ManagementTrackedAgentsDeleteRequest = {
  agentId: string;
  trackedAgentId: string;
};

function normalizeChainKey(raw: string | null): string {
  const trimmed = String(raw ?? '').trim().toLowerCase();
  return trimmed || 'base_sepolia';
}

async function readTrackedAgents(agentId: string, chainKey: string) {
  const result = await dbQuery<{
    tracking_id: string;
    tracked_agent_id: string;
    agent_name: string;
    public_status: string;
    wallet_address: string | null;
    last_activity_at: string | null;
    last_heartbeat_at: string | null;
    metrics_pnl_usd: string | null;
    metrics_return_pct: string | null;
    metrics_volume_usd: string | null;
    metrics_trades_count: number | null;
    metrics_as_of: string | null;
    created_at: string;
  }>(
    `
    select
      ata.tracking_id,
      ata.tracked_agent_id,
      a.agent_name,
      a.public_status::text,
      aw.address as wallet_address,
      a.last_activity_at::text,
      a.last_heartbeat_at::text,
      ps.pnl_usd::text as metrics_pnl_usd,
      ps.return_pct::text as metrics_return_pct,
      ps.volume_usd::text as metrics_volume_usd,
      ps.trades_count as metrics_trades_count,
      ps.created_at::text as metrics_as_of,
      ata.created_at::text
    from agent_tracked_agents ata
    inner join agents a on a.agent_id = ata.tracked_agent_id
    left join agent_wallets aw
      on aw.agent_id = ata.tracked_agent_id
      and aw.chain_key = $2
    left join lateral (
      select
        ps.pnl_usd,
        ps.return_pct,
        ps.volume_usd,
        ps.trades_count,
        ps.created_at
      from performance_snapshots ps
      where ps.agent_id = ata.tracked_agent_id
        and ps.window = '24h'
        and ps.mode = 'real'
        and ps.chain_key = $2
      order by ps.created_at desc
      limit 1
    ) ps on true
    where ata.agent_id = $1
    order by ata.created_at desc
    `,
    [agentId, chainKey]
  );

  return result.rows.map((row) => ({
    trackingId: row.tracking_id,
    trackedAgentId: row.tracked_agent_id,
    agentName: row.agent_name,
    publicStatus: row.public_status,
    walletAddress: row.wallet_address,
    lastActivityAt: row.last_activity_at,
    lastHeartbeatAt: row.last_heartbeat_at,
    latestMetrics:
      row.metrics_pnl_usd !== null ||
      row.metrics_return_pct !== null ||
      row.metrics_volume_usd !== null ||
      row.metrics_trades_count !== null
        ? {
            pnlUsd: row.metrics_pnl_usd,
            returnPct: row.metrics_return_pct,
            volumeUsd: row.metrics_volume_usd,
            tradesCount: Number.isFinite(Number(row.metrics_trades_count)) ? Number(row.metrics_trades_count) : 0,
            asOf: row.metrics_as_of
          }
        : null,
    createdAt: row.created_at
  }));
}

export async function GET(req: NextRequest) {
  const requestId = getRequestId(req);
  try {
    const agentId = req.nextUrl.searchParams.get('agentId')?.trim();
    if (!agentId) {
      return errorResponse(
        400,
        { code: 'payload_invalid', message: 'agentId query parameter is required.', actionHint: 'Provide ?agentId=<agent-id>.' },
        requestId
      );
    }

    const auth = await requireManagementSession(req, requestId);
    if (!auth.ok) {
      return auth.response;
    }
    if (auth.session.agentId !== agentId) {
      return errorResponse(
        401,
        {
          code: 'auth_invalid',
          message: 'Management session is not authorized for this agent.',
          actionHint: 'Use the matching agent management session.'
        },
        requestId
      );
    }

    const chainKey = normalizeChainKey(req.nextUrl.searchParams.get('chainKey'));
    const items = await readTrackedAgents(agentId, chainKey);
    return successResponse({ ok: true, agentId, chainKey, items }, 200, requestId);
  } catch {
    return internalErrorResponse(requestId);
  }
}

export async function POST(req: NextRequest) {
  const requestId = getRequestId(req);
  try {
    const parsed = await parseJsonBody(req, requestId);
    if (!parsed.ok) {
      return parsed.response;
    }
    const validated = validatePayload<ManagementTrackedAgentsUpsertRequest>('management-tracked-agents-upsert-request.schema.json', parsed.body);
    if (!validated.ok) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Tracked-agents payload does not match schema.',
          actionHint: 'Provide valid agentId and trackedAgentId.',
          details: validated.details
        },
        requestId
      );
    }

    const body = validated.data;
    if (body.agentId === body.trackedAgentId) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'An agent cannot track itself.',
          actionHint: 'Choose a different trackedAgentId.'
        },
        requestId
      );
    }

    const auth = await requireManagementWriteAuth(req, requestId, body.agentId);
    if (!auth.ok) {
      return auth.response;
    }

    const exists = await dbQuery<{ agent_id: string }>('select agent_id from agents where agent_id in ($1, $2)', [body.agentId, body.trackedAgentId]);
    if ((exists.rowCount ?? 0) < 2) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'agentId or trackedAgentId was not found.',
          actionHint: 'Verify both agents exist and retry.'
        },
        requestId
      );
    }

    await dbQuery(
      `
      insert into agent_tracked_agents (
        tracking_id,
        agent_id,
        tracked_agent_id,
        created_by_management_session_id,
        created_at,
        updated_at
      ) values ($1, $2, $3, $4, now(), now())
      on conflict (agent_id, tracked_agent_id)
      do update set
        created_by_management_session_id = excluded.created_by_management_session_id,
        updated_at = now()
      `,
      [makeId('trk'), body.agentId, body.trackedAgentId, auth.session.sessionId]
    );

    return successResponse({ ok: true, agentId: body.agentId, trackedAgentId: body.trackedAgentId }, 200, requestId);
  } catch {
    return internalErrorResponse(requestId);
  }
}

export async function DELETE(req: NextRequest) {
  const requestId = getRequestId(req);
  try {
    const parsed = await parseJsonBody(req, requestId);
    if (!parsed.ok) {
      return parsed.response;
    }
    const validated = validatePayload<ManagementTrackedAgentsDeleteRequest>('management-tracked-agents-delete-request.schema.json', parsed.body);
    if (!validated.ok) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Tracked-agents delete payload does not match schema.',
          actionHint: 'Provide valid agentId and trackedAgentId.',
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

    const removed = await dbQuery(
      `
      delete from agent_tracked_agents
      where agent_id = $1
        and tracked_agent_id = $2
      `,
      [body.agentId, body.trackedAgentId]
    );

    return successResponse({ ok: true, agentId: body.agentId, trackedAgentId: body.trackedAgentId, removed: (removed.rowCount ?? 0) > 0 }, 200, requestId);
  } catch {
    return internalErrorResponse(requestId);
  }
}
