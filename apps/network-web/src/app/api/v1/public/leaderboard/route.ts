import type { NextRequest } from 'next/server';

import { dbQuery } from '@/lib/db';
import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import { LEADERBOARD_CACHE_PREFIX, LEADERBOARD_CACHE_TTL_SEC } from '@/lib/metrics';
import { enforcePublicReadRateLimit } from '@/lib/rate-limit';
import { getRedisClient } from '@/lib/redis';
import { getRequestId } from '@/lib/request-id';

export const runtime = 'nodejs';

function parseBoolean(value: string | null, fallback: boolean): boolean {
  if (value === null || value === '') {
    return fallback;
  }
  if (value === 'true' || value === '1') {
    return true;
  }
  if (value === 'false' || value === '0') {
    return false;
  }
  return fallback;
}

function cacheKey(window: string, mode: string, chain: string, includeDeactivated: boolean): string {
  return `${LEADERBOARD_CACHE_PREFIX}${window}:${mode}:${chain}:${includeDeactivated ? '1' : '0'}:explorev2`;
}

export async function GET(req: NextRequest) {
  const requestId = getRequestId(req);

  try {
    const rateLimited = await enforcePublicReadRateLimit(req, requestId);
    if (!rateLimited.ok) {
      return rateLimited.response;
    }

    const window = req.nextUrl.searchParams.get('window') ?? '7d';
    const requestedMode = req.nextUrl.searchParams.get('mode') ?? 'real';
    const mode: 'real' = 'real';
    const chain = req.nextUrl.searchParams.get('chain') ?? 'all';
    const includeDeactivated = parseBoolean(req.nextUrl.searchParams.get('includeDeactivated'), false);
    const verifiedRecencyHours = Number.parseInt(process.env.EXPLORE_VERIFIED_RECENCY_HOURS ?? '72', 10);
    const verifiedHours = Number.isFinite(verifiedRecencyHours) && verifiedRecencyHours > 0 ? verifiedRecencyHours : 72;

    if (!['24h', '7d', '30d', 'all'].includes(window)) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Invalid window query value.',
          actionHint: 'Use one of: 24h, 7d, 30d, all.'
        },
        requestId
      );
    }

    if (!['mock', 'real', 'all'].includes(requestedMode)) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Invalid mode query value.',
          actionHint: 'Use one of: mock, real, all.'
        },
        requestId
      );
    }

    const key = cacheKey(window, mode, chain, includeDeactivated);
    try {
      const redis = await getRedisClient();
      const cached = await redis.get(key);
      if (cached) {
        const parsed = JSON.parse(cached) as { items: unknown[] };
        return successResponse(
          {
            ok: true,
            window,
            mode,
            requestedMode,
            chain,
            includeDeactivated,
            cached: true,
            items: parsed.items
          },
          200,
          requestId
        );
      }
    } catch {
      // Cache read is best effort.
    }

    const rows = await dbQuery<{
      agent_id: string;
      agent_name: string;
      public_status: string;
      mode: 'mock' | 'real';
      chain_key: string;
      score: string | null;
      pnl_usd: string | null;
      return_pct: string | null;
      volume_usd: string | null;
      trades_count: number;
      followers_count: number;
      stale: boolean;
      degraded_reason: string | null;
      snapshot_at: string;
      strategy_tags: string[] | null;
      venue_tags: string[] | null;
      risk_tier: string | null;
      verified: boolean;
    }>(
      `
      with ranked as (
        select
          ps.agent_id,
          ps.mode,
          ps.chain_key,
          ps.score::text,
          ps.pnl_usd::text,
          ps.return_pct::text,
          ps.volume_usd::text,
          ps.trades_count,
          ps.followers_count,
          ps.stale,
          ps.degraded_reason,
          ps.created_at::text as snapshot_at,
          row_number() over (
            partition by ps.agent_id, ps.mode, ps.chain_key, ps."window"
            order by ps.created_at desc
          ) as rn
        from performance_snapshots ps
        where ps."window" = $1::performance_window
          and ps.mode::text = $2
          and (
            ($3::text = 'all' and ps.chain_key = 'all')
            or ($3::text <> 'all' and ps.chain_key = $3)
          )
      )
      select
        r.agent_id,
        a.agent_name,
        a.public_status,
        r.mode,
        r.chain_key,
        r.score,
        r.pnl_usd,
        r.return_pct,
        r.volume_usd,
        r.trades_count,
        r.followers_count,
        r.stale,
        r.degraded_reason,
        r.snapshot_at,
        coalesce(profile.strategy_tags, '[]'::jsonb) as strategy_tags,
        coalesce(profile.venue_tags, '[]'::jsonb) as venue_tags,
        profile.risk_tier,
        (
          a.public_status = 'active'
          and wallet.address is not null
          and coalesce(greatest(events.last_heartbeat_at, events.last_activity_at), '-infinity'::timestamptz)
              >= (now() - ($5::int * interval '1 hour'))
        ) as verified
      from ranked r
      inner join agents a on a.agent_id = r.agent_id
      left join agent_explore_profile profile on profile.agent_id = a.agent_id
      left join lateral (
        select aw.address
        from agent_wallets aw
        where aw.agent_id = a.agent_id
          and ($3 = 'all' or aw.chain_key = $3)
        order by case when aw.chain_key = $3 then 0 else 1 end, aw.chain_key asc
        limit 1
      ) wallet on true
      left join lateral (
        select
          max(ev.created_at) as last_activity_at,
          max(ev.created_at) filter (where ev.event_type = 'heartbeat') as last_heartbeat_at
        from agent_events ev
        where ev.agent_id = a.agent_id
      ) events on true
      where r.rn = 1
        and ($4::boolean = true or a.public_status <> 'deactivated')
      order by
        coalesce(r.score::numeric, 0) desc,
        coalesce(r.volume_usd::numeric, 0) desc,
        a.created_at asc
      limit 200
      `,
      [window, mode, chain, includeDeactivated, verifiedHours]
    );

    const items = rows.rows.map((row) => ({
      ...row,
      exploreProfile: {
        strategyTags: row.strategy_tags ?? [],
        venueTags: row.venue_tags ?? [],
        riskTier: row.risk_tier
      }
    }));

    try {
      const redis = await getRedisClient();
      await redis.set(key, JSON.stringify({ items }), { EX: LEADERBOARD_CACHE_TTL_SEC });
    } catch {
      // Cache write is best effort.
    }

    return successResponse(
      {
        ok: true,
        window,
        mode,
        requestedMode,
        chain,
        includeDeactivated,
        cached: false,
        items
      },
      200,
      requestId
    );
  } catch {
    return internalErrorResponse(requestId);
  }
}
