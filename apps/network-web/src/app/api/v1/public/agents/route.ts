import type { NextRequest } from 'next/server';

import { getChainConfig } from '@/lib/chains';
import { dbQuery } from '@/lib/db';
import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import { parseIntQuery } from '@/lib/http';
import { PUBLIC_STATUSES, isPublicStatus } from '@/lib/public-types';
import { enforcePublicReadRateLimit } from '@/lib/rate-limit';
import { getRequestId } from '@/lib/request-id';

export const runtime = 'nodejs';

type ExploreRiskTier = 'low' | 'medium' | 'high' | 'very_high';

const SORT_TO_ORDER_BY: Record<string, string> = {
  registration: 'f.created_at desc, f.agent_name asc',
  agent_name: 'f.agent_name asc',
  last_activity: 'f.last_activity_at desc nulls last, f.agent_name asc',
  recent: 'f.last_activity_at desc nulls last, f.agent_name asc',
  name: 'f.agent_name asc',
  pnl: 'f.latest_pnl_usd_num desc nulls last, f.agent_name asc',
  volume: 'f.latest_volume_usd_num desc nulls last, f.agent_name asc',
  winrate: 'f.latest_return_pct_num desc nulls last, f.agent_name asc',
  followers: 'f.follower_meta_followers desc nulls last, f.agent_name asc'
};

const RISK_TIERS: ExploreRiskTier[] = ['low', 'medium', 'high', 'very_high'];

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

function parseCsvTagQuery(value: string | null): string[] {
  if (!value) {
    return [];
  }
  const seen = new Set<string>();
  for (const raw of value.split(',')) {
    const normalized = raw.trim().toLowerCase();
    if (!normalized) {
      continue;
    }
    if (!/^[a-z0-9_]+$/.test(normalized)) {
      continue;
    }
    seen.add(normalized);
  }
  return [...seen];
}

function parseNumericMinQuery(value: string | null): number | null {
  if (!value || !value.trim()) {
    return null;
  }
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed < 0) {
    return null;
  }
  return parsed;
}

function parseRiskTier(value: string | null): ExploreRiskTier | null {
  if (!value || value === 'all') {
    return null;
  }
  const normalized = value.trim().toLowerCase() as ExploreRiskTier;
  return RISK_TIERS.includes(normalized) ? normalized : null;
}

function parseWindow(value: string | null): '24h' | '7d' | '30d' | 'all' {
  const normalized = (value ?? '7d').trim();
  if (normalized === '24h' || normalized === '7d' || normalized === '30d' || normalized === 'all') {
    return normalized;
  }
  return '7d';
}

export async function GET(req: NextRequest) {
  const requestId = getRequestId(req);

  try {
    const rateLimited = await enforcePublicReadRateLimit(req, requestId);
    if (!rateLimited.ok) {
      return rateLimited.response;
    }

    const query = (req.nextUrl.searchParams.get('query') ?? '').trim();
    const requestedMode = req.nextUrl.searchParams.get('mode') ?? 'all';
    const mode: 'real' = 'real';
    const chain = req.nextUrl.searchParams.get('chain') ?? 'all';
    if (chain !== 'all' && !getChainConfig(chain)) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Invalid chain query value.',
          actionHint: 'Use one of: all, base_sepolia, hardhat_local.'
        },
        requestId
      );
    }

    const status = req.nextUrl.searchParams.get('status') ?? 'all';
    if (status !== 'all' && !isPublicStatus(status)) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Invalid status query value.',
          actionHint: `Use one of: all, ${PUBLIC_STATUSES.join(', ')}.`
        },
        requestId
      );
    }

    const sort = req.nextUrl.searchParams.get('sort') ?? 'registration';
    const orderBy = SORT_TO_ORDER_BY[sort];
    if (!orderBy) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Invalid sort query value.',
          actionHint: `Use one of: ${Object.keys(SORT_TO_ORDER_BY).join(', ')}.`
        },
        requestId
      );
    }

    const includeDeactivated = parseBoolean(req.nextUrl.searchParams.get('includeDeactivated'), false);
    const includeMetrics = parseBoolean(req.nextUrl.searchParams.get('includeMetrics'), false);
    const verifiedOnly = parseBoolean(req.nextUrl.searchParams.get('verifiedOnly'), false);

    const strategyTags = parseCsvTagQuery(req.nextUrl.searchParams.get('strategy'));
    const venueTags = parseCsvTagQuery(req.nextUrl.searchParams.get('venue'));

    const riskTierRaw = req.nextUrl.searchParams.get('riskTier');
    const riskTier = parseRiskTier(riskTierRaw);
    if (riskTierRaw && riskTierRaw !== 'all' && !riskTier) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Invalid riskTier query value.',
          actionHint: 'Use one of: low, medium, high, very_high.'
        },
        requestId
      );
    }

    const minFollowers = parseIntQuery(req.nextUrl.searchParams.get('minFollowers'), 0, 0, 1_000_000);
    const minVolumeUsd = parseNumericMinQuery(req.nextUrl.searchParams.get('minVolumeUsd'));
    if (req.nextUrl.searchParams.get('minVolumeUsd') && minVolumeUsd === null) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Invalid minVolumeUsd query value.',
          actionHint: 'Use a non-negative numeric value.'
        },
        requestId
      );
    }

    const activeWithinHoursRaw = req.nextUrl.searchParams.get('activeWithinHours');
    const activeWithinHours =
      activeWithinHoursRaw && activeWithinHoursRaw.trim().length > 0
        ? parseIntQuery(activeWithinHoursRaw, 24, 1, 24 * 365)
        : null;

    const page = parseIntQuery(req.nextUrl.searchParams.get('page'), 1, 1, 10000);
    const pageSize = parseIntQuery(req.nextUrl.searchParams.get('pageSize'), 20, 1, 100);
    const offset = (page - 1) * pageSize;
    const likeQuery = `%${query}%`;
    const statusFilter = status === 'all' ? '' : status;
    const verifiedRecencyHours = parseIntQuery(process.env.EXPLORE_VERIFIED_RECENCY_HOURS ?? '72', 72, 1, 24 * 365);
    const window = parseWindow(req.nextUrl.searchParams.get('window'));

    const totalRows = await dbQuery<{ total: string }>(
      `
      with base as (
        select
          a.agent_id,
          a.agent_name,
          a.runtime_platform,
          a.public_status,
          a.created_at,
          events.last_activity_at,
          events.last_heartbeat_at,
          wallet.chain_key as wallet_chain_key,
          wallet.address as wallet_address,
          metrics.pnl_usd as latest_pnl_usd,
          metrics.return_pct as latest_return_pct,
          metrics.volume_usd as latest_volume_usd,
          metrics.trades_count as latest_trades_count,
          metrics.followers_count as latest_followers_count,
          metrics.as_of as latest_metrics_as_of,
          profile.strategy_tags,
          profile.venue_tags,
          profile.risk_tier,
          profile.description_short,
          coalesce(metrics.followers_count, followers.enabled_followers, 0) as follower_meta_followers,
          coalesce(followers.enabled_followers, 0) as follower_meta_copy_enabled,
          (
            a.public_status = 'active'
            and wallet.address is not null
            and coalesce(greatest(events.last_heartbeat_at, events.last_activity_at), '-infinity'::timestamptz)
              >= (now() - ($1::int * interval '1 hour'))
          ) as verified,
          case when metrics.pnl_usd is not null then metrics.pnl_usd::numeric else null end as latest_pnl_usd_num,
          case when metrics.return_pct is not null then metrics.return_pct::numeric else null end as latest_return_pct_num,
          case when metrics.volume_usd is not null then metrics.volume_usd::numeric else null end as latest_volume_usd_num
        from agents a
        left join lateral (
          select aw.chain_key, aw.address
          from agent_wallets aw
          where aw.agent_id = a.agent_id
            and ($2 = 'all' or aw.chain_key = $2)
          order by case when aw.chain_key = $2 then 0 else 1 end, aw.chain_key asc
          limit 1
        ) wallet on true
        left join lateral (
          select
            max(ev.created_at) as last_activity_at,
            max(ev.created_at) filter (where ev.event_type = 'heartbeat') as last_heartbeat_at
          from agent_events ev
          where ev.agent_id = a.agent_id
        ) events on true
        left join lateral (
          select
            ps.pnl_usd::text as pnl_usd,
            ps.return_pct::text as return_pct,
            ps.volume_usd::text as volume_usd,
            ps.trades_count,
            ps.followers_count,
            ps.created_at::text as as_of
          from performance_snapshots ps
          where ps.agent_id = a.agent_id
            and ps.mode = 'real'
            and ps.chain_key = 'all'
            and ps."window" = $3::performance_window
          order by ps.created_at desc
          limit 1
        ) metrics on true
        left join lateral (
          select count(distinct cs.follower_agent_id)::int as enabled_followers
          from copy_subscriptions cs
          where cs.leader_agent_id = a.agent_id
            and cs.enabled = true
        ) followers on true
        left join agent_explore_profile profile on profile.agent_id = a.agent_id
      ), filtered as (
        select
          b.*,
          round((100 - (percent_rank() over (order by b.follower_meta_followers desc nulls last) * 100))::numeric, 2) as follower_rank_percentile
        from base b
        where
          ($4 = '' or b.agent_name ilike $5 or b.agent_id ilike $5 or coalesce(b.wallet_address, '') ilike $5)
          and ($6 = '' or b.public_status::text = $6)
          and ($7::boolean = true or b.public_status <> 'deactivated')
          and ($2 = 'all' or b.wallet_chain_key = $2)
          and (cardinality($8::text[]) = 0 or coalesce(b.strategy_tags, '[]'::jsonb) ?| $8::text[])
          and (cardinality($9::text[]) = 0 or coalesce(b.venue_tags, '[]'::jsonb) ?| $9::text[])
          and ($10::text = '' or coalesce(b.risk_tier, '') = $10)
          and (coalesce(b.follower_meta_followers, 0) >= $11::int)
          and ($12::numeric is null or coalesce(b.latest_volume_usd_num, 0) >= $12::numeric)
          and (
            $13::int is null
            or coalesce(b.last_activity_at, '-infinity'::timestamptz) >= (now() - ($13::int * interval '1 hour'))
          )
          and ($14::boolean = false or b.verified = true)
      )
      select count(*)::text as total
      from filtered
      `,
      [
        verifiedRecencyHours,
        chain,
        window,
        query,
        likeQuery,
        statusFilter,
        includeDeactivated,
        strategyTags,
        venueTags,
        riskTier ?? '',
        minFollowers,
        minVolumeUsd,
        activeWithinHours,
        verifiedOnly
      ]
    );

    const rows = await dbQuery<{
      agent_id: string;
      agent_name: string;
      runtime_platform: string;
      public_status: string;
      created_at: string;
      last_activity_at: string | null;
      last_heartbeat_at: string | null;
      wallet_chain_key: string | null;
      wallet_address: string | null;
      latest_pnl_usd: string | null;
      latest_return_pct: string | null;
      latest_volume_usd: string | null;
      latest_trades_count: number | null;
      latest_followers_count: number | null;
      latest_metrics_as_of: string | null;
      strategy_tags: string[] | null;
      venue_tags: string[] | null;
      risk_tier: ExploreRiskTier | null;
      description_short: string | null;
      follower_meta_followers: number;
      follower_meta_copy_enabled: number;
      follower_rank_percentile: string | null;
      verified: boolean;
    }>(
      `
      with base as (
        select
          a.agent_id,
          a.agent_name,
          a.runtime_platform,
          a.public_status,
          a.created_at,
          events.last_activity_at,
          events.last_heartbeat_at,
          wallet.chain_key as wallet_chain_key,
          wallet.address as wallet_address,
          metrics.pnl_usd as latest_pnl_usd,
          metrics.return_pct as latest_return_pct,
          metrics.volume_usd as latest_volume_usd,
          metrics.trades_count as latest_trades_count,
          metrics.followers_count as latest_followers_count,
          metrics.as_of as latest_metrics_as_of,
          profile.strategy_tags,
          profile.venue_tags,
          profile.risk_tier,
          profile.description_short,
          coalesce(metrics.followers_count, followers.enabled_followers, 0) as follower_meta_followers,
          coalesce(followers.enabled_followers, 0) as follower_meta_copy_enabled,
          (
            a.public_status = 'active'
            and wallet.address is not null
            and coalesce(greatest(events.last_heartbeat_at, events.last_activity_at), '-infinity'::timestamptz)
              >= (now() - ($1::int * interval '1 hour'))
          ) as verified,
          case when metrics.pnl_usd is not null then metrics.pnl_usd::numeric else null end as latest_pnl_usd_num,
          case when metrics.return_pct is not null then metrics.return_pct::numeric else null end as latest_return_pct_num,
          case when metrics.volume_usd is not null then metrics.volume_usd::numeric else null end as latest_volume_usd_num
        from agents a
        left join lateral (
          select aw.chain_key, aw.address
          from agent_wallets aw
          where aw.agent_id = a.agent_id
            and ($2 = 'all' or aw.chain_key = $2)
          order by case when aw.chain_key = $2 then 0 else 1 end, aw.chain_key asc
          limit 1
        ) wallet on true
        left join lateral (
          select
            max(ev.created_at) as last_activity_at,
            max(ev.created_at) filter (where ev.event_type = 'heartbeat') as last_heartbeat_at
          from agent_events ev
          where ev.agent_id = a.agent_id
        ) events on true
        left join lateral (
          select
            ps.pnl_usd::text as pnl_usd,
            ps.return_pct::text as return_pct,
            ps.volume_usd::text as volume_usd,
            ps.trades_count,
            ps.followers_count,
            ps.created_at::text as as_of
          from performance_snapshots ps
          where ps.agent_id = a.agent_id
            and ps.mode = 'real'
            and ps.chain_key = 'all'
            and ps."window" = $3::performance_window
          order by ps.created_at desc
          limit 1
        ) metrics on true
        left join lateral (
          select count(distinct cs.follower_agent_id)::int as enabled_followers
          from copy_subscriptions cs
          where cs.leader_agent_id = a.agent_id
            and cs.enabled = true
        ) followers on true
        left join agent_explore_profile profile on profile.agent_id = a.agent_id
      ), filtered as (
        select
          b.*,
          round((100 - (percent_rank() over (order by b.follower_meta_followers desc nulls last) * 100))::numeric, 2) as follower_rank_percentile
        from base b
        where
          ($4 = '' or b.agent_name ilike $5 or b.agent_id ilike $5 or coalesce(b.wallet_address, '') ilike $5)
          and ($6 = '' or b.public_status::text = $6)
          and ($7::boolean = true or b.public_status <> 'deactivated')
          and ($2 = 'all' or b.wallet_chain_key = $2)
          and (cardinality($8::text[]) = 0 or coalesce(b.strategy_tags, '[]'::jsonb) ?| $8::text[])
          and (cardinality($9::text[]) = 0 or coalesce(b.venue_tags, '[]'::jsonb) ?| $9::text[])
          and ($10::text = '' or coalesce(b.risk_tier, '') = $10)
          and (coalesce(b.follower_meta_followers, 0) >= $11::int)
          and ($12::numeric is null or coalesce(b.latest_volume_usd_num, 0) >= $12::numeric)
          and (
            $13::int is null
            or coalesce(b.last_activity_at, '-infinity'::timestamptz) >= (now() - ($13::int * interval '1 hour'))
          )
          and ($14::boolean = false or b.verified = true)
      )
      select
        f.agent_id,
        f.agent_name,
        f.runtime_platform,
        f.public_status,
        f.created_at::text,
        f.last_activity_at::text,
        f.last_heartbeat_at::text,
        f.wallet_chain_key,
        f.wallet_address,
        f.latest_pnl_usd,
        f.latest_return_pct,
        f.latest_volume_usd,
        f.latest_trades_count,
        f.latest_followers_count,
        f.latest_metrics_as_of,
        coalesce(f.strategy_tags, '[]'::jsonb) as strategy_tags,
        coalesce(f.venue_tags, '[]'::jsonb) as venue_tags,
        f.risk_tier,
        f.description_short,
        f.follower_meta_followers,
        f.follower_meta_copy_enabled,
        f.follower_rank_percentile::text,
        f.verified
      from filtered f
      order by ${orderBy}
      limit $15 offset $16
      `,
      [
        verifiedRecencyHours,
        chain,
        window,
        query,
        likeQuery,
        statusFilter,
        includeDeactivated,
        strategyTags,
        venueTags,
        riskTier ?? '',
        minFollowers,
        minVolumeUsd,
        activeWithinHours,
        verifiedOnly,
        pageSize,
        offset
      ]
    );

    return successResponse(
      {
        ok: true,
        query,
        mode,
        requestedMode,
        chain,
        status,
        sort,
        window,
        includeDeactivated,
        includeMetrics,
        verifiedOnly,
        strategy: strategyTags,
        venue: venueTags,
        riskTier,
        minFollowers,
        minVolumeUsd,
        activeWithinHours,
        page,
        pageSize,
        total: Number(totalRows.rows[0]?.total ?? '0'),
        items: rows.rows.map((row) => ({
          agent_id: row.agent_id,
          agent_name: row.agent_name,
          runtime_platform: row.runtime_platform,
          public_status: row.public_status,
          created_at: row.created_at,
          last_activity_at: row.last_activity_at,
          last_heartbeat_at: row.last_heartbeat_at,
          wallet: row.wallet_address
            ? {
                chain_key: row.wallet_chain_key ?? (chain === 'all' ? 'base_sepolia' : chain),
                address: row.wallet_address
              }
            : null,
          latestMetrics: includeMetrics
            ? {
                pnl_usd: row.latest_pnl_usd,
                return_pct: row.latest_return_pct,
                volume_usd: row.latest_volume_usd,
                trades_count: row.latest_trades_count,
                followers_count: row.latest_followers_count,
                as_of: row.latest_metrics_as_of
              }
            : null,
          exploreProfile: {
            strategyTags: row.strategy_tags ?? [],
            venueTags: row.venue_tags ?? [],
            riskTier: row.risk_tier,
            descriptionShort: row.description_short
          },
          verified: row.verified,
          followerMeta: {
            followersCount: row.follower_meta_followers,
            copyEnabledFollowers: row.follower_meta_copy_enabled,
            followerRankPercentile: row.follower_rank_percentile
          }
        }))
      },
      200,
      requestId
    );
  } catch {
    return internalErrorResponse(requestId);
  }
}
