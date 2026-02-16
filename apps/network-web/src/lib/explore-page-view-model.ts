import { shortenAddress } from '@/lib/public-format';

export type ExploreAgent = {
  agentId: string;
  agentName: string;
  publicStatus: string;
  runtimePlatform: string;
  chainKey: string | null;
  walletAddress: string | null;
  lastActivityAt: string | null;
  lastHeartbeatAt: string | null;
  pnlUsd: string | null;
  returnPct: string | null;
  volumeUsd: string | null;
  tradesCount: number | null;
  followersCount: number | null;
};

export type ExploreSort = 'pnl' | 'volume' | 'winrate' | 'recent' | 'name';

export type LeaderboardMetric = {
  pnlUsd: string | null;
  volumeUsd: string | null;
  returnPct: string | null;
  followersCount: number | null;
};

function toNumber(value: string | number | null | undefined): number {
  if (value === null || value === undefined) {
    return Number.NEGATIVE_INFINITY;
  }
  const parsed = typeof value === 'number' ? value : Number(value);
  return Number.isFinite(parsed) ? parsed : Number.NEGATIVE_INFINITY;
}

export function normalizeAgents(
  payload: Array<{
    agent_id: string;
    agent_name: string;
    runtime_platform: string;
    public_status: string;
    last_activity_at: string | null;
    last_heartbeat_at: string | null;
    wallet: { chain_key: string; address: string } | null;
    latestMetrics:
      | {
          pnl_usd: string | null;
          return_pct: string | null;
          volume_usd: string | null;
          trades_count: number | null;
          followers_count: number | null;
        }
      | null;
  }>,
  leaderboard: Map<string, LeaderboardMetric>
): ExploreAgent[] {
  return payload.map((item) => {
    const metric = leaderboard.get(item.agent_id);
    return {
      agentId: item.agent_id,
      agentName: item.agent_name,
      publicStatus: item.public_status,
      runtimePlatform: item.runtime_platform,
      chainKey: item.wallet?.chain_key ?? null,
      walletAddress: item.wallet?.address ?? null,
      lastActivityAt: item.last_activity_at,
      lastHeartbeatAt: item.last_heartbeat_at,
      pnlUsd: metric?.pnlUsd ?? item.latestMetrics?.pnl_usd ?? null,
      returnPct: metric?.returnPct ?? item.latestMetrics?.return_pct ?? null,
      volumeUsd: metric?.volumeUsd ?? item.latestMetrics?.volume_usd ?? null,
      tradesCount: item.latestMetrics?.trades_count ?? null,
      followersCount: metric?.followersCount ?? item.latestMetrics?.followers_count ?? null
    };
  });
}

export function sortAgents(items: ExploreAgent[], sort: ExploreSort): ExploreAgent[] {
  const out = [...items];
  out.sort((left, right) => {
    if (sort === 'name') {
      return left.agentName.localeCompare(right.agentName);
    }
    if (sort === 'recent') {
      return new Date(right.lastActivityAt ?? 0).getTime() - new Date(left.lastActivityAt ?? 0).getTime();
    }
    if (sort === 'volume') {
      return toNumber(right.volumeUsd) - toNumber(left.volumeUsd);
    }
    if (sort === 'winrate') {
      return toNumber(right.returnPct) - toNumber(left.returnPct);
    }
    return toNumber(right.pnlUsd) - toNumber(left.pnlUsd);
  });
  return out;
}

export function filterByStatus(items: ExploreAgent[], status: 'all' | string): ExploreAgent[] {
  if (status === 'all') {
    return items;
  }
  return items.filter((item) => item.publicStatus === status);
}

export function searchAgents(items: ExploreAgent[], query: string): ExploreAgent[] {
  const normalized = query.trim().toLowerCase();
  if (!normalized) {
    return items;
  }

  return items.filter((item) => {
    const chainText = item.chainKey ?? '';
    const walletText = item.walletAddress ?? '';
    const target = `${item.agentName} ${item.agentId} ${item.runtimePlatform} ${chainText} ${walletText}`.toLowerCase();
    return target.includes(normalized);
  });
}

export function badgeLabel(item: ExploreAgent): string {
  if (!item.walletAddress) {
    return item.runtimePlatform;
  }
  return `${item.runtimePlatform} · ${shortenAddress(item.walletAddress)}`;
}
