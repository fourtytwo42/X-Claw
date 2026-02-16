import type { NextRequest } from 'next/server';

import { dbQuery } from '@/lib/db';
import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import { enforcePublicReadRateLimit } from '@/lib/rate-limit';
import { getRequestId } from '@/lib/request-id';

export const runtime = 'nodejs';

export async function GET(
  req: NextRequest,
  context: { params: Promise<{ agentId: string }> }
) {
  const requestId = getRequestId(req);

  try {
    const rateLimited = await enforcePublicReadRateLimit(req, requestId);
    if (!rateLimited.ok) {
      return rateLimited.response;
    }

    const { agentId } = await context.params;

    const agent = await dbQuery<{
      agent_id: string;
      agent_name: string;
      description: string | null;
      owner_label: string | null;
      runtime_platform: string;
      public_status: string;
      created_at: string;
      updated_at: string;
      last_activity_at: string | null;
      last_heartbeat_at: string | null;
    }>(
      `
      select
        a.agent_id,
        a.agent_name,
        null::text as description,
        null::text as owner_label,
        a.runtime_platform,
        a.public_status,
        a.created_at::text,
        a.created_at::text as updated_at,
        null::text as last_activity_at,
        null::text as last_heartbeat_at
      from agents a
      where a.agent_id = $1
      limit 1
      `,
      [agentId]
    );

    if (agent.rowCount === 0) {
      return errorResponse(
        404,
        {
          code: 'payload_invalid',
          message: 'Agent profile not found.',
          actionHint: 'Verify agentId and retry.'
        },
        requestId
      );
    }

    const wallets = await dbQuery<{
      chain_key: string;
      address: string;
      custody: string;
    }>(
      `
      select chain_key, address, custody
      from agent_wallets
      where agent_id = $1
      order by chain_key asc
      `,
      [agentId]
    ).catch(() => ({ rowCount: 0, rows: [] }));

    const walletBalances = await dbQuery<{
      chain_key: string;
      token: string;
      balance: string;
      decimals: number | null;
      observed_at: string;
    }>(
      `
      with ranked as (
        select
          chain_key,
          token,
          balance::text,
          null::int as decimals,
          observed_at::text,
          row_number() over (partition by chain_key, token order by observed_at desc) as rn
        from wallet_balance_snapshots
        where agent_id = $1
      )
      select chain_key, token, balance, decimals, observed_at
      from ranked
      where rn = 1
      order by chain_key asc, token asc
      `,
      [agentId]
    ).catch(() => ({ rowCount: 0, rows: [] }));

    const metrics = await dbQuery<{
      mode: 'mock' | 'real';
      window_key: string;
      chain_key: string;
      score: string | null;
      pnl_usd: string | null;
      return_pct: string | null;
      volume_usd: string | null;
      trades_count: number;
      followers_count: number;
      self_trades_count: number;
      copied_trades_count: number;
      self_volume_usd: string | null;
      copied_volume_usd: string | null;
      self_pnl_usd: string | null;
      copied_pnl_usd: string | null;
      stale: boolean;
      degraded_reason: string | null;
      created_at: string;
    }>(
      `
      with ranked as (
        select
          mode,
          "window" as window_key,
          chain_key,
          score::text,
          pnl_usd::text,
          return_pct::text,
          volume_usd::text,
          trades_count,
          followers_count,
          self_trades_count,
          copied_trades_count,
          self_volume_usd::text,
          copied_volume_usd::text,
          self_pnl_usd::text,
          copied_pnl_usd::text,
          stale,
          degraded_reason,
          created_at::text,
          row_number() over (partition by mode, "window", chain_key order by created_at desc) as rn
        from performance_snapshots
        where agent_id = $1
          and "window" = '7d'::performance_window
          and chain_key = 'all'
          and mode = 'real'
      )
      select
        mode,
        window_key,
        chain_key,
        score,
        pnl_usd,
        return_pct,
        volume_usd,
        trades_count,
        followers_count,
        self_trades_count,
        copied_trades_count,
        self_volume_usd,
        copied_volume_usd,
        self_pnl_usd,
        copied_pnl_usd,
        stale,
        degraded_reason,
        created_at
      from ranked
      where rn = 1
      order by mode asc
      `,
      [agentId]
    ).catch(() => ({ rowCount: 0, rows: [] }));

    const mapMetric = (row: (typeof metrics.rows)[number] | null) =>
      row
        ? {
            ...row,
            window: row.window_key
          }
        : null;

    const latestMetrics = mapMetric(metrics.rows.find((row) => row.mode === 'real') ?? metrics.rows[0] ?? null);
    const realMetrics = mapMetric(metrics.rows.find((row) => row.mode === 'real') ?? null);

    const copyBreakdown = latestMetrics
      ? {
          selfTradesCount: latestMetrics.self_trades_count,
          copiedTradesCount: latestMetrics.copied_trades_count,
          selfVolumeUsd: latestMetrics.self_volume_usd,
          copiedVolumeUsd: latestMetrics.copied_volume_usd,
          selfPnlUsd: latestMetrics.self_pnl_usd,
          copiedPnlUsd: latestMetrics.copied_pnl_usd
        }
      : null;

    return successResponse(
      {
        ok: true,
        agent: agent.rows[0],
        wallets: wallets.rows,
        walletBalances: walletBalances.rows,
        latestMetrics,
        metricsByMode: {
          mock: null,
          real: realMetrics
        },
        copyBreakdown
      },
      200,
      requestId
    );
  } catch {
    return internalErrorResponse(requestId);
  }
}
