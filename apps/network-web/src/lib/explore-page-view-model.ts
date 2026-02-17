import { shortenAddress } from '@/lib/public-format';

export type ExploreRiskTier = 'low' | 'medium' | 'high' | 'very_high';

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
  verified: boolean;
  exploreProfile: {
    strategyTags: string[];
    venueTags: string[];
    riskTier: ExploreRiskTier | null;
    descriptionShort: string | null;
  };
  followerMeta: {
    followersCount: number;
    copyEnabledFollowers: number;
    followerRankPercentile: string | null;
  };
};

export type ExploreSort = 'pnl' | 'volume' | 'winrate' | 'recent' | 'name' | 'followers';

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
    exploreProfile?: {
      strategyTags?: string[];
      venueTags?: string[];
      riskTier?: ExploreRiskTier | null;
      descriptionShort?: string | null;
    } | null;
    verified?: boolean;
    followerMeta?: {
      followersCount?: number | null;
      copyEnabledFollowers?: number | null;
      followerRankPercentile?: string | null;
    } | null;
  }>
): ExploreAgent[] {
  return payload.map((item) => {
    const followerCount = Number(item.followerMeta?.followersCount ?? item.latestMetrics?.followers_count ?? 0);
    const copyEnabledFollowers = Number(item.followerMeta?.copyEnabledFollowers ?? 0);
    return {
      agentId: item.agent_id,
      agentName: item.agent_name,
      publicStatus: item.public_status,
      runtimePlatform: item.runtime_platform,
      chainKey: item.wallet?.chain_key ?? null,
      walletAddress: item.wallet?.address ?? null,
      lastActivityAt: item.last_activity_at,
      lastHeartbeatAt: item.last_heartbeat_at,
      pnlUsd: item.latestMetrics?.pnl_usd ?? null,
      returnPct: item.latestMetrics?.return_pct ?? null,
      volumeUsd: item.latestMetrics?.volume_usd ?? null,
      tradesCount: item.latestMetrics?.trades_count ?? null,
      followersCount: item.latestMetrics?.followers_count ?? followerCount,
      verified: Boolean(item.verified),
      exploreProfile: {
        strategyTags: item.exploreProfile?.strategyTags ?? [],
        venueTags: item.exploreProfile?.venueTags ?? [],
        riskTier: item.exploreProfile?.riskTier ?? null,
        descriptionShort: item.exploreProfile?.descriptionShort ?? null
      },
      followerMeta: {
        followersCount: Number.isFinite(followerCount) ? followerCount : 0,
        copyEnabledFollowers: Number.isFinite(copyEnabledFollowers) ? copyEnabledFollowers : 0,
        followerRankPercentile: item.followerMeta?.followerRankPercentile ?? null
      }
    };
  });
}

export function badgeLabel(item: ExploreAgent): string {
  if (!item.walletAddress) {
    return item.runtimePlatform;
  }
  return `${item.runtimePlatform} · ${shortenAddress(item.walletAddress)}`;
}
