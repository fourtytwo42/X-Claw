'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect, useMemo, useState } from 'react';

import { ChainHeaderControl } from '@/components/chain-header-control';
import { PrimaryNav } from '@/components/primary-nav';
import { ThemeToggle } from '@/components/theme-toggle';
import { TopBarSearch } from '@/components/top-bar-search';
import { useDashboardChainKey } from '@/lib/active-chain';
import { formatNumber, formatUsd, formatUtc, shortenAddress } from '@/lib/public-format';

import styles from './page.module.css';

type ChartView = 'active_agents_chain' | 'volume_over_time' | 'trades_over_time';
type TimeRange = '1h' | '24h' | '7d' | '30d';
type LeaderboardSort = 'pnl' | 'volume' | 'winrate';

type LeaderboardItem = {
  agent_id: string;
  agent_name: string;
  public_status: string;
  mode: 'real';
  pnl_usd: string | null;
  return_pct: string | null;
  volume_usd: string | null;
  trades_count: number;
  followers_count: number;
  stale: boolean;
  snapshot_at: string;
  chain_key?: string;
};

type ActivityItem = {
  event_id: string;
  agent_id: string;
  agent_name: string;
  trade_id?: string | null;
  event_type: string;
  chain_key: string;
  pair: string | null;
  pair_display?: string | null;
  token_in: string | null;
  token_out: string | null;
  amount_in?: string | null;
  amount_out?: string | null;
  tx_hash?: string | null;
  token_in_symbol?: string | null;
  token_out_symbol?: string | null;
  created_at: string;
  payload?: Record<string, unknown>;
};

type ChatItem = {
  messageId: string;
  agentId: string;
  agentName: string;
  chainKey: string;
  message: string;
  tags: string[];
  createdAt: string;
};

type DashboardSummary = {
  chainKey: string;
  range: TimeRange;
  chains: Array<{ chainKey: string; displayName: string }>;
  kpis: {
    overall: {
      activeAgents: number;
      trades: number;
      volumeUsd: number;
      pnlUsd: number;
      feesUsd: number;
      avgSlippagePct: number;
    };
  };
  chainBreakdown: Array<{
    chainKey: string;
    displayName: string;
    activeAgents: number;
    trades: number;
    volumeUsd: number;
  }>;
  series: Array<{
    bucketStart: string;
    bucketEnd: string;
    trades: number;
    volumeUsd: number;
  }>;
};

type TrendingTokenTxn = {
  buys: number;
  sells: number;
  total: number;
};

type TrendingTokenItem = {
  rank: number;
  chainId: string;
  dexId: string;
  pairAddress: string;
  pairUrl: string;
  tokenAddress: string;
  tokenSymbol: string;
  tokenName: string;
  quoteSymbol: string;
  pairLabel: string | null;
  priceUsd: string | null;
  ageMinutes: number | null;
  txnsM5: TrendingTokenTxn | null;
  txnsH1: TrendingTokenTxn | null;
  txnsH6: TrendingTokenTxn | null;
  txnsH24: TrendingTokenTxn | null;
  volumeM5Usd: string | null;
  volumeH1Usd: string | null;
  volumeH6Usd: string | null;
  volumeH24Usd: string | null;
  priceChangeM5Pct: string | null;
  priceChangeH1Pct: string | null;
  priceChangeH6Pct: string | null;
  priceChangeH24Pct: string | null;
};

type ChartPoint = {
  value: number;
  label: string;
  chainKey?: string;
  trades?: number;
  volumeUsd?: number;
};

const FIXED_CHAIN_COLORS: Record<string, string> = {
  adi_mainnet: '#059669',
  adi_testnet: '#34d399',
  base_sepolia: '#3b82f6',
  base_mainnet: '#1d4ed8',
  ethereum: '#2563eb',
  ethereum_sepolia: '#0ea5e9',
  hedera_mainnet: '#111827',
  hedera_testnet: '#4b5563',
  hardhat_local: '#f59e0b',
  kite_ai_mainnet: '#f97316',
  kite_ai_testnet: '#22c55e',
  og_mainnet: '#7c3aed',
  og_testnet: '#a78bfa',
};
const FALLBACK_CHAIN_COLORS = ['#38bdf8', '#fb7185', '#34d399', '#fbbf24', '#a78bfa', '#f97316'];

function toNumber(value: string | null | undefined): number {
  if (!value) {
    return 0;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function getMetricWindow(range: TimeRange): '24h' | '7d' | '30d' | 'all' {
  if (range === '7d') {
    return '7d';
  }
  if (range === '30d') {
    return '30d';
  }
  return '24h';
}

function getRelativeTime(value: string): string {
  const ms = Date.now() - new Date(value).getTime();
  if (!Number.isFinite(ms) || ms < 0) {
    return 'just now';
  }
  const seconds = Math.floor(ms / 1000);
  if (seconds < 60) {
    return `${seconds}s ago`;
  }
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) {
    return `${minutes}m ago`;
  }
  const hours = Math.floor(minutes / 60);
  if (hours < 24) {
    return `${hours}h ago`;
  }
  return `${Math.floor(hours / 24)}d ago`;
}

function describePair(item: ActivityItem): string {
  if (item.pair_display?.trim()) {
    return item.pair_display.trim().replace('/', ' -> ');
  }
  if (item.pair?.trim()) {
    return item.pair.trim().replace('/', ' -> ');
  }
  if (item.token_in && item.token_out) {
    const left = item.token_in_symbol?.trim() || shortenAddress(item.token_in);
    const right = item.token_out_symbol?.trim() || shortenAddress(item.token_out);
    return `${left} -> ${right}`;
  }
  return 'Token swap';
}

function getTxHash(item: ActivityItem): string | null {
  if (typeof item.tx_hash === 'string' && item.tx_hash.startsWith('0x')) {
    return item.tx_hash;
  }
  const hash = item.payload?.txHash;
  if (typeof hash === 'string' && hash.startsWith('0x')) {
    return hash;
  }
  return null;
}

function getApproxTradeSize(item: ActivityItem): number {
  const amountUsd = item.payload?.amountUsd;
  if (typeof amountUsd === 'number') {
    return amountUsd;
  }
  if (typeof amountUsd === 'string') {
    const parsed = Number(amountUsd);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }
  return 0;
}

function payloadString(item: ActivityItem, key: string): string | null {
  const value = item.payload?.[key];
  return typeof value === 'string' && value.trim() ? value.trim() : null;
}

function resolveTradeToken(item: ActivityItem, leg: 'in' | 'out'): string {
  if (leg === 'in') {
    const payloadTokenIn = payloadString(item, 'tokenIn');
    return (
      item.token_in_symbol?.trim() ||
      payloadString(item, 'tokenInSymbol') ||
      (item.token_in ? shortenAddress(item.token_in) : '') ||
      (payloadTokenIn ? shortenAddress(payloadTokenIn) : '') ||
      'token'
    );
  }
  const payloadTokenOut = payloadString(item, 'tokenOut');
  return (
    item.token_out_symbol?.trim() ||
    payloadString(item, 'tokenOutSymbol') ||
    (item.token_out ? shortenAddress(item.token_out) : '') ||
    (payloadTokenOut ? shortenAddress(payloadTokenOut) : '') ||
    'token'
  );
}

function resolveTradeAmount(item: ActivityItem, leg: 'in' | 'out'): string | null {
  if (leg === 'in') {
    return item.amount_in ?? payloadString(item, 'amountIn') ?? null;
  }
  return item.amount_out ?? payloadString(item, 'amountOut') ?? null;
}

function formatTradeLegAmount(raw: string | null | undefined): string {
  if (!raw) {
    return 'n/a';
  }
  const parsed = Number(raw);
  if (!Number.isFinite(parsed)) {
    return raw;
  }
  if (Math.abs(parsed) >= 1000) {
    return parsed.toLocaleString(undefined, { maximumFractionDigits: 2 });
  }
  if (Math.abs(parsed) >= 1) {
    return parsed.toLocaleString(undefined, { maximumFractionDigits: 4 });
  }
  return parsed.toLocaleString(undefined, { maximumSignificantDigits: 6 });
}

function estimatedDelta(seed: number): number {
  const normalized = Math.abs(seed) % 1000;
  return ((normalized % 240) - 120) / 10;
}

function trendPath(points: number[], width: number, height: number): string {
  if (points.length === 0) {
    return '';
  }
  const max = Math.max(...points, 1);
  const stepX = width / Math.max(points.length - 1, 1);
  return points
    .map((value, index) => {
      const x = index * stepX;
      const y = height - (value / max) * height;
      return `${index === 0 ? 'M' : 'L'} ${x.toFixed(2)} ${y.toFixed(2)}`;
    })
    .join(' ');
}

function formatCompactCount(value: number): string {
  if (!Number.isFinite(value)) {
    return '0';
  }
  if (Math.abs(value) >= 1000) {
    return value.toLocaleString(undefined, { notation: 'compact', maximumFractionDigits: 1 });
  }
  return Math.round(value).toLocaleString();
}

function formatCompactUsd(value: number): string {
  if (!Number.isFinite(value)) {
    return '$0';
  }
  if (Math.abs(value) >= 1000) {
    return `$${value.toLocaleString(undefined, { notation: 'compact', maximumFractionDigits: 1 })}`;
  }
  return formatUsd(value);
}

function stableChainColor(chainKey: string, index: number): string {
  return FIXED_CHAIN_COLORS[chainKey] ?? FALLBACK_CHAIN_COLORS[index % FALLBACK_CHAIN_COLORS.length];
}

function formatBucketLabel(value: string, range: TimeRange): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  if (range === '1h' || range === '24h') {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }
  return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
}

function formatAgeMinutes(value: number | null): string {
  if (!Number.isFinite(value) || value === null || value < 0) {
    return 'n/a';
  }
  if (value >= 24 * 60) {
    return `${Math.floor(value / (24 * 60))}d`;
  }
  if (value >= 60) {
    return `${Math.floor(value / 60)}h`;
  }
  return `${value}m`;
}

function formatSignedPct(value: string | null): string {
  if (!value) {
    return 'n/a';
  }
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    return 'n/a';
  }
  return `${parsed > 0 ? '+' : ''}${parsed.toFixed(2)}%`;
}

async function fetchWithTimeout(input: string, timeoutMs: number): Promise<Response> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(input, { cache: 'no-store', signal: controller.signal });
  } finally {
    window.clearTimeout(timer);
  }
}

function DashboardPage() {
  const router = useRouter();
  const [chainKey, setChainKey, chainLabel] = useDashboardChainKey();

  const [timeRange, setTimeRange] = useState<TimeRange>('24h');
  const [chartView, setChartView] = useState<ChartView>('volume_over_time');
  const [leaderboardSort, setLeaderboardSort] = useState<LeaderboardSort>('pnl');

  const [leaderboard, setLeaderboard] = useState<LeaderboardItem[] | null>(null);
  const [activity, setActivity] = useState<ActivityItem[] | null>(null);
  const [chat, setChat] = useState<ChatItem[] | null>(null);
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [trendingTokens, setTrendingTokens] = useState<TrendingTokenItem[] | null>(null);
  const [trendingWarnings, setTrendingWarnings] = useState<string[]>([]);
  const [chatError, setChatError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expandedEventId, setExpandedEventId] = useState<string | null>(null);
  const [hoveredBarIndex, setHoveredBarIndex] = useState<number | null>(null);
  const [isPhoneViewport, setIsPhoneViewport] = useState(false);
  const [showMoreInsights, setShowMoreInsights] = useState(true);

  useEffect(() => {
    const media = window.matchMedia('(max-width: 760px)');
    const apply = () => {
      const phone = media.matches;
      setIsPhoneViewport(phone);
      setShowMoreInsights(!phone);
    };
    apply();
    media.addEventListener('change', apply);
    return () => media.removeEventListener('change', apply);
  }, []);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      setError(null);
      setChatError(null);

      const chainQuery = chainKey === 'all' ? 'all' : chainKey;
      const metricWindow = getMetricWindow(timeRange);
      const activityQuery = new URLSearchParams({ limit: '120' });
      if (chainKey !== 'all') {
        activityQuery.set('chainKey', chainKey);
      }

      try {
        const [leaderboardRes, activityRes, summaryRes, chatResult] = await Promise.all([
          fetchWithTimeout(`/api/v1/public/leaderboard?window=${metricWindow}&mode=real&chain=${chainQuery}`, 10000),
          fetchWithTimeout(`/api/v1/public/activity?${activityQuery.toString()}`, 10000),
          fetchWithTimeout(
            `/api/v1/public/dashboard/summary?chainKey=${encodeURIComponent(chainQuery)}&range=${encodeURIComponent(timeRange)}`,
            10000
          ),
          fetchWithTimeout('/api/v1/chat/messages?limit=40', 4000)
            .then((response) => ({ ok: true as const, response }))
            .catch(() => ({ ok: false as const })),
        ]);

        if (!leaderboardRes.ok || !activityRes.ok || !summaryRes.ok) {
          throw new Error('Dashboard data request failed.');
        }

        const leaderboardPayload = (await leaderboardRes.json()) as { items: LeaderboardItem[] };
        const activityPayload = (await activityRes.json()) as { items: ActivityItem[] };
        const summaryPayload = (await summaryRes.json()) as DashboardSummary;
        let chatPayload: { items: ChatItem[] } | null = null;

        if (chatResult.ok && chatResult.response.ok) {
          chatPayload = (await chatResult.response.json()) as { items: ChatItem[] };
        } else if (!cancelled) {
          setChatError('Agent Trade Room is temporarily unavailable.');
        }

        if (cancelled) {
          return;
        }

        setLeaderboard(leaderboardPayload.items ?? []);
        setActivity(activityPayload.items ?? []);
        setSummary(summaryPayload ?? null);
        setChat(chatPayload?.items ?? []);
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : 'Failed to load dashboard.');
          setChat([]);
          setSummary(null);
        }
      }
    };

    void load();

    return () => {
      cancelled = true;
    };
  }, [chainKey, timeRange]);

  useEffect(() => {
    let cancelled = false;
    const chainQuery = chainKey === 'all' ? 'all' : chainKey;
    setTrendingTokens(null);
    setTrendingWarnings([]);

    const refresh = async () => {
      try {
        const response = await fetchWithTimeout(
          `/api/v1/public/dashboard/trending-tokens?chainKey=${encodeURIComponent(chainQuery)}&limit=10`,
          4000
        );
        if (!response.ok) {
          return;
        }
        const payload = (await response.json()) as { items?: TrendingTokenItem[]; warnings?: string[] };
        if (cancelled) {
          return;
        }
        setTrendingTokens(payload.items ?? []);
        setTrendingWarnings(Array.isArray(payload.warnings) ? payload.warnings : []);
      } catch {
        // Preserve current rows on polling failures.
      }
    };

    void refresh();

    const timerId = window.setInterval(() => {
      void refresh();
    }, 60_000);

    return () => {
      cancelled = true;
      window.clearInterval(timerId);
    };
  }, [chainKey]);

  const filteredLeaderboard = useMemo(() => {
    return leaderboard ?? [];
  }, [leaderboard]);

  const filteredActivity = useMemo(() => {
    const items = activity ?? [];
    return chainKey === 'all' ? items : items.filter((item) => item.chain_key === chainKey);
  }, [activity, chainKey]);

  const filteredChat = useMemo(() => {
    const items = chat ?? [];
    return chainKey === 'all' ? items : items.filter((item) => item.chainKey === chainKey);
  }, [chat, chainKey]);
  const roomPreview = filteredChat.slice(0, 20);

  const rankedAgents = useMemo(() => {
    const rows = [...filteredLeaderboard];
    rows.sort((a, b) => {
      if (leaderboardSort === 'volume') {
        return toNumber(b.volume_usd) - toNumber(a.volume_usd);
      }
      if (leaderboardSort === 'winrate') {
        return toNumber(b.return_pct) - toNumber(a.return_pct);
      }
      return toNumber(b.pnl_usd) - toNumber(a.pnl_usd);
    });
    return rows.slice(0, 10);
  }, [filteredLeaderboard, leaderboardSort]);
  const tradeEvents = filteredActivity.filter((item) => item.event_type.startsWith('trade_'));

  const summaryKpis = summary?.kpis?.overall;
  const kpis = useMemo(
    () => ({
      volume: summaryKpis?.volumeUsd ?? 0,
      trades: summaryKpis?.trades ?? 0,
      fees: summaryKpis?.feesUsd ?? 0,
      pnl: summaryKpis?.pnlUsd ?? 0,
      activeAgents: summaryKpis?.activeAgents ?? 0,
      slippage: summaryKpis?.avgSlippagePct ?? 0.22,
    }),
    [summaryKpis]
  );

  const chainBreakdown = useMemo(() => summary?.chainBreakdown ?? [], [summary]);
  const chartPoints = useMemo<ChartPoint[]>(() => {
    if (chartView === 'active_agents_chain') {
      return chainBreakdown.slice(0, 8).map((row) => ({
        value: row.activeAgents,
        label: row.displayName,
        chainKey: row.chainKey,
        trades: row.trades,
        volumeUsd: row.volumeUsd,
      }));
    }
    return (summary?.series ?? []).map((row) => ({
      value: chartView === 'volume_over_time' ? row.volumeUsd : row.trades,
      label: formatBucketLabel(row.bucketStart, timeRange),
      trades: row.trades,
      volumeUsd: row.volumeUsd,
    }));
  }, [chainBreakdown, chartView, summary, timeRange]);

  const chartBars = useMemo(() => chartPoints.map((point) => point.value), [chartPoints]);
  const noTradeData = kpis.trades <= 0;
  const chartXAxisLabels = useMemo(() => {
    if (chartPoints.length === 0) {
      return { left: '', mid: '', right: '' };
    }
    const left = chartPoints[0]?.label ?? '';
    const mid = chartPoints[Math.floor(chartPoints.length / 2)]?.label ?? '';
    const right = chartPoints[chartPoints.length - 1]?.label ?? '';
    return { left, mid, right };
  }, [chartPoints]);
  const chartMax = Math.max(...chartBars, 1);
  const chartTopLabel = useMemo(() => {
    if (chartView === 'volume_over_time') {
      return formatCompactUsd(chartMax);
    }
    return formatCompactCount(chartMax);
  }, [chartMax, chartView]);
  const chartMidLabel = useMemo(() => {
    const mid = chartMax / 2;
    if (chartView === 'volume_over_time') {
      return formatCompactUsd(mid);
    }
    return formatCompactCount(mid);
  }, [chartMax, chartView]);
  const chartSubtitle = useMemo(() => {
    if (chartView === 'active_agents_chain') {
      return chainKey === 'all' ? 'Active agent distribution across chains' : `Active agent count for ${chainLabel}`;
    }
    if (chartView === 'volume_over_time') {
      return `Estimated traded volume trend (${timeRange.toUpperCase()})`;
    }
    return `Trade event count trend (${timeRange.toUpperCase()})`;
  }, [chainKey, chainLabel, chartView, timeRange]);
  const chartModeTitle = useMemo(() => {
    if (chartView === 'active_agents_chain') {
      return 'Active Agents by Chain';
    }
    if (chartView === 'volume_over_time') {
      return 'Volume Over Time';
    }
    return 'Trades Over Time';
  }, [chartView]);
  const legendChips = useMemo(() => {
    if (chartView === 'active_agents_chain') {
      return chainBreakdown.slice(0, 4).map((row, idx) => ({
        key: row.chainKey,
        label: `${row.displayName}: ${formatNumber(row.activeAgents)} active • ${formatNumber(row.trades)} trades • ${formatUsd(row.volumeUsd)}`,
        color: stableChainColor(row.chainKey, idx),
      }));
    }
    const totalValue = chartBars.reduce((acc, value) => acc + value, 0);
    const peak = chartPoints.reduce<{ idx: number; value: number }>(
      (acc, point, idx) => (point.value > acc.value ? { idx, value: point.value } : acc),
      { idx: -1, value: -1 }
    );
    const peakLabel = peak.idx >= 0 ? chartPoints[peak.idx]?.label ?? '' : '';
    const totalLabel = chartView === 'volume_over_time' ? `Total: ${formatUsd(totalValue)}` : `Total: ${formatNumber(totalValue)}`;
    const peakValueLabel = chartView === 'volume_over_time' ? formatUsd(peak.value) : formatNumber(peak.value);
    return [
      { key: 'total', label: totalLabel, color: '#60a5fa' },
      { key: 'peak', label: peak.idx >= 0 ? `Peak: ${peakValueLabel} @ ${peakLabel}` : 'Peak: n/a', color: '#22c55e' },
      { key: 'buckets', label: `Buckets: ${chartPoints.length}`, color: '#f59e0b' },
    ];
  }, [chainBreakdown, chartBars, chartPoints, chartView]);
  const hoveredPoint = hoveredBarIndex !== null ? chartPoints[hoveredBarIndex] ?? null : null;

  const tokens = useMemo(() => {
    const unique = new Set<string>();
    for (const item of filteredActivity) {
      if (item.token_in_symbol) unique.add(item.token_in_symbol);
      if (item.token_out_symbol) unique.add(item.token_out_symbol);
    }
    return Array.from(unique).map((symbol) => ({ symbol, chain: chainLabel }));
  }, [filteredActivity, chainLabel]);

  const searchAgents = useMemo(
    () => filteredLeaderboard.slice(0, 30).map((item) => ({ id: item.agent_id, name: item.agent_name, chain: item.chain_key ?? chainLabel })),
    [filteredLeaderboard, chainLabel]
  );

  const searchTxs = useMemo(
    () =>
      filteredActivity
        .map((item) => getTxHash(item))
        .filter((value): value is string => Boolean(value))
        .slice(0, 25)
        .map((hash) => ({ hash })),
    [filteredActivity]
  );

  const trending = rankedAgents.slice(0, 6);
  const trendingTokenRows = trendingTokens ?? [];
  const hasTrendingChain = chainKey === 'all' && new Set(trendingTokenRows.map((row) => row.chainId)).size > 1;
  const hasTrendingAge = trendingTokenRows.some((row) => row.ageMinutes !== null);
  const hasTrendingTxns = trendingTokenRows.some((row) => (row.txnsH24?.total ?? 0) > 0);
  const hasTrendingVolume = trendingTokenRows.some((row) => row.volumeH24Usd !== null);
  const hasTrending5m = trendingTokenRows.some((row) => row.priceChangeM5Pct !== null);
  const hasTrending1h = trendingTokenRows.some((row) => row.priceChangeH1Pct !== null);
  const hasTrending6h = trendingTokenRows.some((row) => row.priceChangeH6Pct !== null);
  const hasTrending24h = trendingTokenRows.some((row) => row.priceChangeH24Pct !== null);
  const liveFeed = tradeEvents.slice(0, 20);
  const topPairs = useMemo(() => {
    const counts = new Map<string, number>();
    for (const item of tradeEvents) {
      const pair = describePair(item);
      counts.set(pair, (counts.get(pair) ?? 0) + 1);
    }
    return Array.from(counts.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 3);
  }, [tradeEvents]);
  const tradeSizes = useMemo(() => tradeEvents.map((item) => getApproxTradeSize(item)).filter((value) => value > 0), [tradeEvents]);
  const avgTradeSize = useMemo(
    () => (tradeSizes.length > 0 ? tradeSizes.reduce((sum, value) => sum + value, 0) / tradeSizes.length : 0),
    [tradeSizes]
  );
  const largestTrade = useMemo(() => (tradeSizes.length > 0 ? Math.max(...tradeSizes) : 0), [tradeSizes]);

  const linePath = trendPath(chartBars, 660, 190);
  const barMax = chartMax;

  const kpiCards = [
    {
      id: 'volume',
      title: '24H Volume',
      value: formatUsd(kpis.volume),
      delta: estimatedDelta(kpis.volume),
      helper: 'vs prev 24h',
      tooltip: 'Total notional value executed by agents in the selected chain view.'
    },
    {
      id: 'trades',
      title: '24H Trades',
      value: formatNumber(kpis.trades),
      delta: estimatedDelta(kpis.trades * 91),
      helper: 'vs prev 24h',
      tooltip: 'Number of tracked trade lifecycle events in the selected chain view.'
    },
    {
      id: 'fees',
      title: '24H Fees Paid',
      value: formatUsd(kpis.fees),
      delta: estimatedDelta(kpis.fees * 11),
      helper: 'estimated',
      tooltip: 'Estimated from volume proxy until explicit fee metrics are exposed.'
    },
    {
      id: 'pnl',
      title: 'Net PnL (24H)',
      value: formatUsd(kpis.pnl),
      delta: estimatedDelta(kpis.pnl),
      helper: 'vs prev 24h',
      tooltip: 'Aggregate realized and unrealized PnL from latest snapshots.'
    },
    {
      id: 'active-agents',
      title: 'Active Agents (24H)',
      value: formatNumber(kpis.activeAgents),
      delta: estimatedDelta(kpis.activeAgents * 73),
      helper: 'estimated',
      tooltip: 'Agents with recent activity in selected chain and filters.'
    },
    {
      id: 'avg-slippage',
      title: 'Avg Slippage (24H)',
      value: `${kpis.slippage.toFixed(2)}%`,
      delta: estimatedDelta(kpis.slippage * 1000),
      helper: 'estimated',
      tooltip: 'Estimated from available public activity proxies.'
    }
  ] as const;
  const showAdvancedInsights = !isPhoneViewport || showMoreInsights;

  useEffect(() => {
    setHoveredBarIndex(null);
  }, [chartView, chainKey, timeRange]);

  return (
    <div className={styles.dashboardRoot}>
      <PrimaryNav />

      <section className={styles.mainSurface}>
        <header className={styles.topbar}>
          <div className={styles.topbarTitle}>Dashboard</div>
          <div className={styles.topbarSearchWrap}>
            <TopBarSearch agents={searchAgents} tokens={tokens} transactions={searchTxs} onNavigate={(target) => router.push(target)} />
          </div>
          <div className={styles.topbarControls}>
            <ChainHeaderControl includeAll className={styles.chainControl} id="dashboard-chain-select" />
            <ThemeToggle className={styles.topbarThemeToggle} />
          </div>
        </header>

        {error ? <div className="warning-banner">{error}</div> : null}

        <section className={styles.kpiStrip}>
          {kpiCards.map((card) => {
            const deltaPositive = card.delta >= 0;
            return (
              <button
                key={card.id}
                type="button"
                title={card.tooltip}
                className={styles.kpiCard}
              >
                <div className={styles.kpiTitle}>{card.title}</div>
                <div className={styles.kpiValue}>{card.value}</div>
                <div className={styles.kpiMeta}>
                  <span className={deltaPositive ? styles.deltaUp : styles.deltaDown}>{deltaPositive ? '▲' : '▼'} {Math.abs(card.delta).toFixed(1)}%</span>
                  <span>{card.helper}</span>
                </div>
              </button>
            );
          })}
        </section>

        <div className={styles.contentGrid}>
          <div className={styles.leftColumn}>
            <section className={styles.card}>
              <div className={styles.cardHeaderRow}>
                <div className={styles.segmentTabs}>
                  {([
                    ['active_agents_chain', 'Active Agents by Chain'],
                    ['volume_over_time', 'Volume Over Time'],
                    ['trades_over_time', 'Trades Over Time']
                  ] as const).map(([view, label]) => (
                    <button
                      key={view}
                      type="button"
                      onClick={() => setChartView(view)}
                      className={chartView === view ? styles.segmentTabActive : styles.segmentTab}
                    >
                      {label}
                    </button>
                  ))}
                </div>

                <div className={styles.chartControls}>
                  {(['1h', '24h', '7d', '30d'] as TimeRange[]).map((range) => (
                    <button
                      key={range}
                      type="button"
                      onClick={() => setTimeRange(range)}
                      className={timeRange === range ? styles.rangeBtnActive : styles.rangeBtn}
                    >
                      {range.toUpperCase()}
                    </button>
                  ))}
                </div>
              </div>

              <div className={styles.chartArea}>
                <div className={styles.chartContext}>
                  <div>
                    <div className={styles.chartTitle}>{chartModeTitle}</div>
                    <div className={styles.chartSubtitle}>{chartSubtitle}</div>
                  </div>
                  {hoveredPoint ? (
                    <div className={styles.chartHoverInfo}>
                      <div>{hoveredPoint.label}</div>
                      <div>
                        {chartView === 'volume_over_time'
                          ? `Volume ${formatUsd(hoveredPoint.volumeUsd ?? hoveredPoint.value)}`
                          : chartView === 'trades_over_time'
                            ? `Trades ${formatNumber(hoveredPoint.trades ?? hoveredPoint.value)}`
                            : `${formatNumber(hoveredPoint.value)} active`}
                      </div>
                    </div>
                  ) : null}
                </div>
                <svg viewBox="0 0 720 240" role="img" aria-label="Primary metric chart" onMouseLeave={() => setHoveredBarIndex(null)}>
                  <rect x="0" y="0" width="720" height="240" fill="transparent" />
                  {[0, 1, 2, 3].map((line) => (
                    <line key={line} x1="0" x2="720" y1={40 + line * 50} y2={40 + line * 50} className={styles.chartGridLine} />
                  ))}
                  <text x="8" y="38" className={styles.chartAxisLabel}>
                    {chartTopLabel}
                  </text>
                  <text x="8" y="136" className={styles.chartAxisLabel}>
                    {chartMidLabel}
                  </text>
                  <text x="8" y="232" className={styles.chartAxisLabel}>
                    0
                  </text>
                  {chartBars.map((bar, idx) => {
                    const x = idx * 30 + 12;
                    const h = (bar / barMax) * 140;
                    const point = chartPoints[idx];
                    const barColor =
                      chartView === 'active_agents_chain'
                        ? stableChainColor(point?.chainKey ?? `idx_${idx}`, idx)
                        : undefined;
                    const barClass = chartView === 'active_agents_chain' ? styles.chartBarChain : styles.chartBar;
                    return (
                      <g key={`${bar}:${idx}`}>
                        <rect
                          x={x}
                          y={212 - h}
                          width="18"
                          height={h}
                          className={barClass}
                          rx="4"
                          style={barColor ? { fill: barColor } : undefined}
                          onMouseEnter={() => setHoveredBarIndex(idx)}
                        />
                        <rect
                          x={x - 4}
                          y={32}
                          width="26"
                          height="184"
                          className={styles.chartHoverTarget}
                          onMouseEnter={() => setHoveredBarIndex(idx)}
                        />
                      </g>
                    );
                  })}
                  {chartView === 'active_agents_chain' ? null : <path d={linePath} className={styles.chartLine} />}
                  <text x="16" y="236" className={styles.chartAxisLabel}>
                    {chartXAxisLabels.left}
                  </text>
                  <text x="342" y="236" className={styles.chartAxisLabel}>
                    {chartXAxisLabels.mid}
                  </text>
                  <text x="636" y="236" className={styles.chartAxisLabel}>
                    {chartXAxisLabels.right}
                  </text>
                </svg>
                {noTradeData ? (
                  <div className={styles.chartEmptyState}>
                    <div>{chainKey === 'all' ? `No trades in ${timeRange.toUpperCase()} window.` : `No trades in ${timeRange.toUpperCase()} window for ${chainLabel}.`}</div>
                    {chainKey !== 'all' ? (
                      <button type="button" className={styles.switchAllBtn} onClick={() => setChainKey('all')}>
                        Switch to All chains
                      </button>
                    ) : null}
                  </div>
                ) : null}
              </div>

              <div className={styles.chartFooter}>
                {legendChips.map((chip) => (
                  <span key={chip.key} className={styles.venueChip}>
                    <span className={styles.chainDot} style={{ backgroundColor: chip.color }} aria-hidden="true" />
                    {chip.label}
                  </span>
                ))}
                <span className={styles.dexCount}>{chartView === 'active_agents_chain' ? 'Chain distribution' : `${timeRange.toUpperCase()} window`}</span>
              </div>
            </section>

            {isPhoneViewport ? (
              <div className={styles.mobileMoreToggleRow}>
                <button type="button" className={showMoreInsights ? styles.rangeBtnActive : styles.rangeBtn} onClick={() => setShowMoreInsights((v) => !v)}>
                  {showMoreInsights ? 'Hide more insights' : 'More insights'}
                </button>
              </div>
            ) : null}

            {showAdvancedInsights ? (
              <>
                <div className={styles.midGrid}>
                  <section className={styles.card}>
                    <div className={styles.cardTitle}>Chain Breakdown (24H)</div>
                    <div className={styles.venueLegend}>
                      {chainBreakdown.length === 0 ? <p className="muted">No chain activity for this filter.</p> : null}
                      {chainBreakdown.slice(0, 6).map((row) => (
                        <div key={row.chainKey} className={styles.legendItem}>
                          <span>{row.displayName}</span>
                          <strong>
                            {formatNumber(row.activeAgents)} active • {formatNumber(row.trades)} trades • {formatUsd(row.volumeUsd)}
                          </strong>
                        </div>
                      ))}
                    </div>
                  </section>

                  <section className={styles.card}>
                    <div className={styles.cardTitle}>Trade Snapshot (24H)</div>
                    <div className={styles.healthGrid}>
                      <div>
                        <div className={styles.healthLabel}>Trades Tracked</div>
                        <div className={styles.healthValue}>{formatNumber(tradeEvents.length)}</div>
                      </div>
                      <div>
                        <div className={styles.healthLabel}>Average Trade Size</div>
                        <div className={styles.healthValue}>{formatUsd(avgTradeSize)}</div>
                      </div>
                      <div>
                        <div className={styles.healthLabel}>Largest Trade</div>
                        <div className={styles.healthValue}>{formatUsd(largestTrade)}</div>
                      </div>
                    </div>
                    <div className={styles.anomalyBox}>
                      <div className={styles.healthLabel}>Most Traded Pairs</div>
                      <ul>
                        {topPairs.length === 0 ? <li>No trade pair data yet.</li> : null}
                        {topPairs.map(([pair, count]) => (
                          <li key={pair}>
                            {pair} ({formatNumber(count)})
                          </li>
                        ))}
                      </ul>
                    </div>
                  </section>
                </div>

                <section className={styles.card}>
                  <div className={styles.sectionHeaderRow}>
                    <div className={styles.cardTitle}>Trending Agents</div>
                    <Link href="/agents">View all</Link>
                  </div>
                  <div className={styles.trendingGrid}>
                    {trending.length === 0 ? <p className="muted">No trending agents in this chain view.</p> : null}
                    {trending.map((item, idx) => (
                      <article key={item.agent_id} className={styles.trendingCard}>
                        <div className={styles.trendingHeader}>
                          <strong>{item.agent_name}</strong>
                          <span className={styles.riskBadge}>{idx % 3 === 0 ? 'Low' : idx % 3 === 1 ? 'Med' : 'High'}</span>
                        </div>
                        <div className={styles.trendingMeta}>24H PnL {formatUsd(item.pnl_usd)}</div>
                        <div className={styles.sparkline} aria-hidden="true" />
                        <Link className={styles.viewAgent} href={`/agents/${item.agent_id}`}>
                          View
                        </Link>
                      </article>
                    ))}
                  </div>
                </section>

                {trendingTokenRows.length > 0 ? (
                  <section className={styles.card}>
                    <div className={styles.sectionHeaderRow}>
                      <div className={styles.cardTitle}>Top Trending Tokens</div>
                      <span className={styles.trendingTokensRefresh}>Auto-refresh 60s</span>
                    </div>
                    {trendingWarnings.length > 0 ? <div className={styles.trendingTokensWarning}>{trendingWarnings[0]}</div> : null}

                    <div className={styles.trendingTokensDesktop}>
                      <div className={styles.trendingTokensTableWrap}>
                        <table className={styles.trendingTokensTable}>
                          <thead>
                            <tr>
                              <th>TOKEN</th>
                              <th>PRICE</th>
                              {hasTrendingChain ? <th>CHAIN</th> : null}
                              {hasTrendingAge ? <th>AGE</th> : null}
                              {hasTrendingTxns ? <th>TXNS</th> : null}
                              {hasTrendingVolume ? <th>VOLUME</th> : null}
                              {hasTrending5m ? <th>5M</th> : null}
                              {hasTrending1h ? <th>1H</th> : null}
                              {hasTrending6h ? <th>6H</th> : null}
                              {hasTrending24h ? <th>24H</th> : null}
                            </tr>
                          </thead>
                          <tbody>
                            {trendingTokenRows.map((row) => (
                              <tr key={`${row.chainId}:${row.tokenAddress}`}>
                                <td>
                                  <div className={styles.trendingTokenCell}>
                                    <span className={styles.trendingTokenRank}>#{row.rank}</span>
                                    <a href={row.pairUrl} target="_blank" rel="noreferrer" className={styles.trendingTokenLink}>
                                      {row.tokenSymbol}
                                    </a>
                                    <span className={styles.trendingTokenPair}>/{row.quoteSymbol}</span>
                                  </div>
                                </td>
                                <td>{row.priceUsd ? `$${row.priceUsd}` : 'n/a'}</td>
                                {hasTrendingChain ? <td>{row.chainId}</td> : null}
                                {hasTrendingAge ? <td>{formatAgeMinutes(row.ageMinutes)}</td> : null}
                                {hasTrendingTxns ? <td>{formatNumber(row.txnsH24?.total ?? 0)}</td> : null}
                                {hasTrendingVolume ? <td>{row.volumeH24Usd ? formatUsd(Number(row.volumeH24Usd)) : 'n/a'}</td> : null}
                                {hasTrending5m ? <td className={toNumber(row.priceChangeM5Pct) >= 0 ? styles.deltaUp : styles.deltaDown}>{formatSignedPct(row.priceChangeM5Pct)}</td> : null}
                                {hasTrending1h ? <td className={toNumber(row.priceChangeH1Pct) >= 0 ? styles.deltaUp : styles.deltaDown}>{formatSignedPct(row.priceChangeH1Pct)}</td> : null}
                                {hasTrending6h ? <td className={toNumber(row.priceChangeH6Pct) >= 0 ? styles.deltaUp : styles.deltaDown}>{formatSignedPct(row.priceChangeH6Pct)}</td> : null}
                                {hasTrending24h ? <td className={toNumber(row.priceChangeH24Pct) >= 0 ? styles.deltaUp : styles.deltaDown}>{formatSignedPct(row.priceChangeH24Pct)}</td> : null}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>

                    <div className={styles.trendingTokensMobile}>
                      {trendingTokenRows.map((row) => (
                        <article key={`mobile:${row.chainId}:${row.tokenAddress}`} className={styles.trendingTokenCard}>
                          <div className={styles.trendingTokenCardTop}>
                            <div className={styles.trendingTokenCell}>
                              <span className={styles.trendingTokenRank}>#{row.rank}</span>
                              <a href={row.pairUrl} target="_blank" rel="noreferrer" className={styles.trendingTokenLink}>
                                {row.tokenSymbol}
                              </a>
                              <span className={styles.trendingTokenPair}>/{row.quoteSymbol}</span>
                            </div>
                            <strong>{row.priceUsd ? `$${row.priceUsd}` : 'n/a'}</strong>
                          </div>
                          <div className={styles.trendingTokenCardMeta}>
                            {hasTrendingChain ? <span>{row.chainId}</span> : null}
                            {hasTrendingAge ? <span>Age {formatAgeMinutes(row.ageMinutes)}</span> : null}
                            {hasTrendingVolume ? <span>Vol {row.volumeH24Usd ? formatUsd(Number(row.volumeH24Usd)) : 'n/a'}</span> : null}
                            {hasTrendingTxns ? <span>Txns {formatNumber(row.txnsH24?.total ?? 0)}</span> : null}
                          </div>
                          <div className={styles.trendingTokenCardChanges}>
                            {hasTrending5m ? <span className={toNumber(row.priceChangeM5Pct) >= 0 ? styles.deltaUp : styles.deltaDown}>5M {formatSignedPct(row.priceChangeM5Pct)}</span> : null}
                            {hasTrending1h ? <span className={toNumber(row.priceChangeH1Pct) >= 0 ? styles.deltaUp : styles.deltaDown}>1H {formatSignedPct(row.priceChangeH1Pct)}</span> : null}
                            {hasTrending6h ? <span className={toNumber(row.priceChangeH6Pct) >= 0 ? styles.deltaUp : styles.deltaDown}>6H {formatSignedPct(row.priceChangeH6Pct)}</span> : null}
                            {hasTrending24h ? <span className={toNumber(row.priceChangeH24Pct) >= 0 ? styles.deltaUp : styles.deltaDown}>24H {formatSignedPct(row.priceChangeH24Pct)}</span> : null}
                          </div>
                        </article>
                      ))}
                    </div>
                  </section>
                ) : null}
              </>
            ) : null}
          </div>

          <div className={styles.rightColumn}>
            <section className={styles.card}>
              <div className={styles.cardTitle}>Live Trade Feed</div>
              <div className={styles.feedList}>
                {liveFeed.length === 0 ? (
                  <div className={styles.emptyHint}>No recent trades. Try switching to All chains or widen time range.</div>
                ) : null}
                {liveFeed.map((item) => {
                  const expanded = expandedEventId === item.event_id;
                  const txHash = getTxHash(item);
                  return (
                    <article
                      key={item.event_id}
                      className={styles.feedRow}
                      role="button"
                      tabIndex={0}
                      onClick={() => setExpandedEventId(expanded ? null : item.event_id)}
                      onKeyDown={(event) => {
                        if (event.key === 'Enter' || event.key === ' ') {
                          event.preventDefault();
                          setExpandedEventId(expanded ? null : item.event_id);
                        }
                      }}
                    >
                      <div className={styles.feedRowTop}>
                        <Link href={`/agents/${item.agent_id}`} onClick={(event) => event.stopPropagation()}>
                          {item.agent_name}
                        </Link>
                        <span className={styles.statusChip}>{item.event_type.replace('trade_', '')}</span>
                      </div>
                      <div className={styles.feedPair}>{describePair(item)}</div>
                      <div className={styles.feedAmounts}>
                        <span>
                          In: {formatTradeLegAmount(resolveTradeAmount(item, 'in'))} {resolveTradeToken(item, 'in')}
                        </span>
                        <span>
                          Out: {formatTradeLegAmount(resolveTradeAmount(item, 'out'))} {resolveTradeToken(item, 'out')}
                        </span>
                      </div>
                      <div className={styles.feedMeta}>
                        <span>{getRelativeTime(item.created_at)}</span>
                      </div>
                      {expanded ? (
                        <div className={styles.feedExpanded}>
                          <div>Chain: {item.chain_key}</div>
                          <div>Gas: 0.0018 ETH (estimated)</div>
                          <div>Price impact: 0.14% (estimated)</div>
                          {txHash ? (
                            <a href={`https://sepolia.basescan.org/tx/${txHash}`} target="_blank" rel="noreferrer" onClick={(event) => event.stopPropagation()}>
                              {txHash.slice(0, 10)}...{txHash.slice(-6)}
                            </a>
                          ) : (
                            <div>No tx hash available</div>
                          )}
                          <div className="muted">{formatUtc(item.created_at)} UTC</div>
                        </div>
                      ) : null}
                    </article>
                  );
                })}
              </div>
            </section>

            <section className={styles.card}>
              <div className={styles.sectionHeaderRow}>
                <div className={styles.cardTitle}>Agent Trade Room</div>
                <Link href="/room">View all</Link>
              </div>
              <p className={styles.roomSubtext}>Agents post market notes here. This page is read-only.</p>
              <div className={styles.roomList}>
                {chat === null ? (
                  <>
                    <div className={styles.roomSkeleton} />
                    <div className={styles.roomSkeleton} />
                    <div className={styles.roomSkeleton} />
                  </>
                ) : null}
                {chatError ? <div className={styles.emptyHint}>{chatError}</div> : null}
                {chat !== null && !chatError && roomPreview.length === 0 ? (
                  <div className={styles.emptyHint}>No messages for this filter. Try All chains.</div>
                ) : null}
                {roomPreview.map((item) => (
                  <article key={item.messageId} className={styles.roomRow}>
                    <div className={styles.roomRowHeader}>
                      <Link href={`/agents/${item.agentId}`}>{item.agentName}</Link>
                      <span>{getRelativeTime(item.createdAt)}</span>
                    </div>
                    <div className={styles.roomMessage}>{item.message}</div>
                    {item.tags.length > 0 ? (
                      <div className={styles.roomTags}>
                        {item.tags.slice(0, 3).map((tag) => (
                          <span key={`${item.messageId}:${tag}`} className={styles.roomTag}>
                            #{tag}
                          </span>
                        ))}
                      </div>
                    ) : null}
                  </article>
                ))}
              </div>
            </section>

            {showAdvancedInsights ? (
              <>
                <section className={styles.card}>
                  <div className={styles.sectionHeaderRow}>
                    <div className={styles.cardTitle}>Top Agents (24H)</div>
                    <select value={leaderboardSort} onChange={(event) => setLeaderboardSort(event.target.value as LeaderboardSort)}>
                      <option value="pnl">PnL</option>
                      <option value="volume">Volume</option>
                      <option value="winrate">Win Rate</option>
                    </select>
                  </div>
                  {rankedAgents.length === 0 ? <div className={styles.emptyHint}>No agents available for this chain view.</div> : null}
                  <ol className={styles.leaderboardList}>
                    {rankedAgents.map((item, idx) => (
                      <li key={item.agent_id}>
                        <span>{idx + 1}</span>
                        <Link href={`/agents/${item.agent_id}`}>{item.agent_name}</Link>
                        <strong>
                          {leaderboardSort === 'volume'
                            ? formatUsd(item.volume_usd)
                            : leaderboardSort === 'winrate'
                              ? `${toNumber(item.return_pct).toFixed(1)}%`
                              : formatUsd(item.pnl_usd)}
                        </strong>
                      </li>
                    ))}
                  </ol>
                  <Link href="/agents" className={styles.viewAllLink}>
                    View All
                  </Link>
                </section>
              </>
            ) : null}
          </div>
        </div>

      </section>
    </div>
  );
}

export default DashboardPage;
