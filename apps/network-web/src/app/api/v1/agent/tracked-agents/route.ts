import type { NextRequest } from 'next/server';

import { authenticateAgentByToken } from '@/lib/agent-auth';
import { dbQuery } from '@/lib/db';
import { internalErrorResponse, successResponse } from '@/lib/errors';
import { getRequestId } from '@/lib/request-id';

export const runtime = 'nodejs';

function normalizeChainKey(raw: string | null): string {
  const trimmed = String(raw ?? '').trim().toLowerCase();
  return trimmed || 'base_sepolia';
}

export async function GET(req: NextRequest) {
  const requestId = getRequestId(req);
  try {
    const auth = authenticateAgentByToken(req, requestId);
    if (!auth.ok) {
      return auth.response;
    }

    const chainKey = normalizeChainKey(req.nextUrl.searchParams.get('chainKey'));
    const rows = await dbQuery<{
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
      [auth.agentId, chainKey]
    );

    return successResponse(
      {
        ok: true,
        agentId: auth.agentId,
        chainKey,
        items: rows.rows.map((row) => ({
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
        }))
      },
      200,
      requestId
    );
  } catch {
    return internalErrorResponse(requestId);
  }
}
