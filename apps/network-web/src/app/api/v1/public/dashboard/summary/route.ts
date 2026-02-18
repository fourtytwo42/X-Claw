import type { NextRequest } from 'next/server';

import { getChainConfig, listEnabledChains } from '@/lib/chains';
import { dbQuery } from '@/lib/db';
import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import { enforcePublicReadRateLimit } from '@/lib/rate-limit';
import { getRequestId } from '@/lib/request-id';

export const runtime = 'nodejs';

type RangeKey = '1h' | '24h' | '7d' | '30d';

type ChainKpiRow = {
  chain_key: string;
  active_agents: number;
  volume_usd: string;
  trades_count: number;
  pnl_usd: string;
};

function parseRange(value: string | null): RangeKey {
  if (value === '1h' || value === '24h' || value === '7d' || value === '30d') {
    return value;
  }
  return '24h';
}

function asNumber(value: string | number | null | undefined): number {
  if (typeof value === 'number') {
    return Number.isFinite(value) ? value : 0;
  }
  if (typeof value === 'string') {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : 0;
  }
  return 0;
}

function estimateSlippage(volumeUsd: number, tradesCount: number): number {
  if (tradesCount <= 0 || volumeUsd <= 0) {
    return 0.22;
  }
  const avgSize = volumeUsd / tradesCount;
  return Math.min(1.8, 0.08 + avgSize / 180000);
}

function bucketConfig(range: RangeKey): { count: number; windowSeconds: number } {
  if (range === '1h') {
    return { count: 12, windowSeconds: 60 * 60 };
  }
  if (range === '24h') {
    return { count: 24, windowSeconds: 24 * 60 * 60 };
  }
  if (range === '7d') {
    return { count: 28, windowSeconds: 7 * 24 * 60 * 60 };
  }
  return { count: 30, windowSeconds: 30 * 24 * 60 * 60 };
}

function buildKpiRow(row: { activeAgents: number; trades: number; volumeUsd: number; pnlUsd: number }) {
  const fees = row.volumeUsd * 0.003;
  return {
    activeAgents: row.activeAgents,
    trades: row.trades,
    volumeUsd: row.volumeUsd,
    pnlUsd: row.pnlUsd,
    feesUsd: fees,
    avgSlippagePct: estimateSlippage(row.volumeUsd, row.trades),
  };
}

export async function GET(req: NextRequest) {
  const requestId = getRequestId(req);

  try {
    const rateLimited = await enforcePublicReadRateLimit(req, requestId);
    if (!rateLimited.ok) {
      return rateLimited.response;
    }

    const range = parseRange(req.nextUrl.searchParams.get('range'));
    const chainKey = (req.nextUrl.searchParams.get('chainKey') ?? 'all').trim() || 'all';
    const visibleChains = listEnabledChains().filter((cfg) => cfg.uiVisible !== false);
    const validChainKeys = new Set(visibleChains.map((cfg) => cfg.chainKey));

    if (chainKey !== 'all' && !getChainConfig(chainKey)) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'chainKey query parameter is invalid.',
          actionHint: `Use all or one of: ${Array.from(validChainKeys).join(', ')}.`,
        },
        requestId
      );
    }

    const chainRows = visibleChains
      .filter((cfg) => chainKey === 'all' || cfg.chainKey === chainKey)
      .map((cfg) => ({
        chainKey: cfg.chainKey,
        displayName: cfg.displayName ?? cfg.chainKey,
      }));

    const targetChainKeys = chainRows.map((row) => row.chainKey);

    const kpiRows = await dbQuery<ChainKpiRow>(
      `
      with latest as (
        select
          ps.agent_id,
          ps.chain_key,
          ps.volume_usd,
          ps.trades_count,
          ps.pnl_usd,
          row_number() over (
            partition by ps.agent_id, ps.chain_key, ps.mode, ps.window
            order by ps.created_at desc
          ) as rn
        from performance_snapshots ps
        where ps.mode::text = 'real'
          and ps.window = '24h'::performance_window
          and ps.chain_key = any($1::text[])
      )
      select
        chain_key,
        count(*)::int as active_agents,
        coalesce(sum(coalesce(volume_usd, 0)), 0)::text as volume_usd,
        coalesce(sum(coalesce(trades_count, 0)), 0)::int as trades_count,
        coalesce(sum(coalesce(pnl_usd, 0)), 0)::text as pnl_usd
      from latest
      where rn = 1
      group by chain_key
      `,
      [targetChainKeys]
    );

    const kpiByChainMap = new Map<string, { activeAgents: number; trades: number; volumeUsd: number; pnlUsd: number }>();
    for (const row of chainRows) {
      kpiByChainMap.set(row.chainKey, { activeAgents: 0, trades: 0, volumeUsd: 0, pnlUsd: 0 });
    }
    for (const row of kpiRows.rows) {
      if (!kpiByChainMap.has(row.chain_key)) {
        continue;
      }
      kpiByChainMap.set(row.chain_key, {
        activeAgents: Number(row.active_agents) || 0,
        trades: Number(row.trades_count) || 0,
        volumeUsd: asNumber(row.volume_usd),
        pnlUsd: asNumber(row.pnl_usd),
      });
    }

    const overall = (() => {
      if (chainKey !== 'all') {
        return buildKpiRow(kpiByChainMap.get(chainKey) ?? { activeAgents: 0, trades: 0, volumeUsd: 0, pnlUsd: 0 });
      }
      const totals = [...kpiByChainMap.values()].reduce(
        (acc, row) => {
          acc.activeAgents += row.activeAgents;
          acc.trades += row.trades;
          acc.volumeUsd += row.volumeUsd;
          acc.pnlUsd += row.pnlUsd;
          return acc;
        },
        { activeAgents: 0, trades: 0, volumeUsd: 0, pnlUsd: 0 }
      );
      return buildKpiRow(totals);
    })();

    const breakdownRows = await dbQuery<{
      chain_key: string;
      active_agents: number;
      trades: number;
      volume_usd: string;
    }>(
      `
      select
        t.chain_key,
        count(distinct t.agent_id)::int as active_agents,
        count(*)::int as trades,
        coalesce(sum(coalesce(t.amount_out, t.amount_in)), 0)::text as volume_usd
      from trades t
      where t.created_at >= (now() - interval '24 hour')
        and t.chain_key = any($1::text[])
      group by t.chain_key
      `,
      [targetChainKeys]
    );

    const breakdownByChain = new Map<string, { activeAgents: number; trades: number; volumeUsd: number }>();
    for (const row of chainRows) {
      breakdownByChain.set(row.chainKey, { activeAgents: 0, trades: 0, volumeUsd: 0 });
    }
    for (const row of breakdownRows.rows) {
      if (!breakdownByChain.has(row.chain_key)) {
        continue;
      }
      breakdownByChain.set(row.chain_key, {
        activeAgents: Number(row.active_agents) || 0,
        trades: Number(row.trades) || 0,
        volumeUsd: asNumber(row.volume_usd),
      });
    }

    const chainBreakdown = chainRows
      .map((row) => {
        const counts = breakdownByChain.get(row.chainKey) ?? { activeAgents: 0, trades: 0, volumeUsd: 0 };
        return {
          chainKey: row.chainKey,
          displayName: row.displayName,
          activeAgents: counts.activeAgents,
          trades: counts.trades,
          volumeUsd: counts.volumeUsd,
        };
      })
      .sort((a, b) => b.activeAgents - a.activeAgents || b.trades - a.trades || a.chainKey.localeCompare(b.chainKey));

    const bucket = bucketConfig(range);
    const seriesRows = await dbQuery<{
      bucket_start: string;
      bucket_end: string;
      trades: number;
      volume_usd: string;
    }>(
      `
      with params as (
        select
          now() as window_end,
          (now() - make_interval(secs => $1::int)) as window_start,
          $2::int as bucket_count,
          $3::int as bucket_seconds
      ),
      buckets as (
        select
          p.window_start + ((g.i) * make_interval(secs => p.bucket_seconds)) as bucket_start,
          p.window_start + ((g.i + 1) * make_interval(secs => p.bucket_seconds)) as bucket_end
        from params p
        cross join lateral generate_series(0, p.bucket_count - 1) as g(i)
      )
      select
        b.bucket_start::text,
        b.bucket_end::text,
        count(t.trade_id)::int as trades,
        coalesce(sum(coalesce(t.amount_out, t.amount_in)), 0)::text as volume_usd
      from buckets b
      left join trades t
        on t.created_at >= b.bucket_start
       and t.created_at < b.bucket_end
       and ($4::text = 'all' or t.chain_key = $4::text)
      group by b.bucket_start, b.bucket_end
      order by b.bucket_start asc
      `,
      [bucket.windowSeconds, bucket.count, Math.max(Math.floor(bucket.windowSeconds / bucket.count), 1), chainKey]
    );

    const series = seriesRows.rows.map((row) => ({
      bucketStart: row.bucket_start,
      bucketEnd: row.bucket_end,
      trades: Number(row.trades) || 0,
      volumeUsd: asNumber(row.volume_usd),
    }));

    return successResponse(
      {
        ok: true,
        chainKey,
        range,
        generatedAt: new Date().toISOString(),
        chains: chainRows,
        kpis: {
          overall,
          byChain: chainRows.map((row) => ({
            chainKey: row.chainKey,
            displayName: row.displayName,
            ...buildKpiRow(kpiByChainMap.get(row.chainKey) ?? { activeAgents: 0, trades: 0, volumeUsd: 0, pnlUsd: 0 }),
          })),
        },
        chainBreakdown,
        series,
      },
      200,
      requestId
    );
  } catch {
    return internalErrorResponse(requestId);
  }
}
