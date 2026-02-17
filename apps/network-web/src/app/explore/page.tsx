'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useEffect, useMemo, useState } from 'react';

import { ChainHeaderControl } from '@/components/chain-header-control';
import { PrimaryNav } from '@/components/primary-nav';
import { PublicStatusBadge } from '@/components/public-status-badge';
import { ThemeToggle } from '@/components/theme-toggle';
import { useDashboardChainKey } from '@/lib/active-chain';
import {
  badgeLabel,
  normalizeAgents,
  type ExploreAgent,
  type ExploreRiskTier,
  type ExploreSort
} from '@/lib/explore-page-view-model';
import { formatNumber, formatPercent, formatUsd } from '@/lib/public-format';
import { PUBLIC_STATUSES, type PublicStatus } from '@/lib/public-types';

import styles from './page.module.css';

type TimeWindow = '24h' | '7d' | '30d' | 'all';
type SectionKey = 'all' | 'mine' | 'favorites';

type AgentsPayload = {
  total: number;
  page: number;
  pageSize: number;
  items: Array<{
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
  }>;
};

type SessionAgentsPayload = {
  managedAgents?: string[];
  activeAgentId?: string;
};

type OwnerContext =
  | { phase: 'loading' }
  | { phase: 'none' }
  | { phase: 'ready'; managedAgents: string[]; activeAgentId: string };

type CopySubscriptionPayload = {
  items?: Array<{
    subscriptionId: string;
    leaderAgentId: string;
    followerAgentId: string;
    enabled: boolean;
    scaleBps: number;
    maxTradeUsd: string;
    allowedTokens: string[];
  }>;
};

type CopyModalState = {
  open: boolean;
  leader: ExploreAgent | null;
  followerAgentId: string;
  scaleBps: number;
  maxTradeUsd: string;
  requirePerTradeApprovals: boolean;
};

type ProfileModalState = {
  open: boolean;
  agentId: string;
  strategyTags: string;
  venueTags: string;
  riskTier: ExploreRiskTier;
  descriptionShort: string;
};

const FAVORITES_KEY = 'xclaw_explore_favorite_agent_ids';
const STRATEGY_OPTIONS = ['momentum', 'mean_reversion', 'trend_following', 'arb', 'market_making'];
const VENUE_OPTIONS = ['base', 'aerodrome', 'uniswap', 'sushiswap', 'kite_ai'];
const LABEL_OVERRIDES: Record<string, string> = {
  arb: 'Arbitrage',
  kite_ai: 'Kite AI'
};

function getCsrfToken(): string | null {
  if (typeof document === 'undefined') {
    return null;
  }
  const raw = document.cookie
    .split(';')
    .map((part) => part.trim())
    .find((part) => part.startsWith('xclaw_csrf='));
  if (!raw) {
    return null;
  }
  return decodeURIComponent(raw.split('=')[1] ?? '');
}

function parseStoredIds(key: string): string[] {
  if (typeof window === 'undefined') {
    return [];
  }
  try {
    const raw = window.localStorage.getItem(key);
    if (!raw) {
      return [];
    }
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) {
      return [];
    }
    return parsed.filter((item): item is string => typeof item === 'string' && item.length > 0);
  } catch {
    return [];
  }
}

function storeIds(key: string, ids: string[]) {
  if (typeof window === 'undefined') {
    return;
  }
  window.localStorage.setItem(key, JSON.stringify(Array.from(new Set(ids))));
}

function splitCsv(value: string): string[] {
  const out = new Set<string>();
  for (const part of value.split(',')) {
    const normalized = part.trim().toLowerCase();
    if (!normalized || !/^[a-z0-9_]+$/.test(normalized)) {
      continue;
    }
    out.add(normalized);
  }
  return [...out];
}

function humanizeKeyLabel(value: string): string {
  const normalized = value.trim().toLowerCase();
  const override = LABEL_OVERRIDES[normalized];
  if (override) {
    return override;
  }
  return normalized
    .split('_')
    .filter((part) => part.length > 0)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

async function postJson(path: string, payload: Record<string, unknown>) {
  const csrf = getCsrfToken();
  const headers: Record<string, string> = { 'content-type': 'application/json' };
  if (csrf) {
    headers['x-csrf-token'] = csrf;
  }
  const response = await fetch(path, {
    method: 'POST',
    credentials: 'same-origin',
    headers,
    body: JSON.stringify(payload)
  });
  const json = (await response.json().catch(() => null)) as { message?: string; code?: string } | null;
  if (!response.ok) {
    const error = new Error(json?.message ?? 'Request failed.') as Error & { code?: string };
    if (json?.code) {
      error.code = json.code;
    }
    throw error;
  }
  return json;
}

async function patchJson(path: string, payload: Record<string, unknown>) {
  const csrf = getCsrfToken();
  const headers: Record<string, string> = { 'content-type': 'application/json' };
  if (csrf) {
    headers['x-csrf-token'] = csrf;
  }
  const response = await fetch(path, {
    method: 'PATCH',
    credentials: 'same-origin',
    headers,
    body: JSON.stringify(payload)
  });
  const json = (await response.json().catch(() => null)) as { message?: string; code?: string } | null;
  if (!response.ok) {
    const error = new Error(json?.message ?? 'Request failed.') as Error & { code?: string };
    if (json?.code) {
      error.code = json.code;
    }
    throw error;
  }
  return json;
}

async function putJson(path: string, payload: Record<string, unknown>) {
  const csrf = getCsrfToken();
  const headers: Record<string, string> = { 'content-type': 'application/json' };
  if (csrf) {
    headers['x-csrf-token'] = csrf;
  }
  const response = await fetch(path, {
    method: 'PUT',
    credentials: 'same-origin',
    headers,
    body: JSON.stringify(payload)
  });
  const json = (await response.json().catch(() => null)) as { message?: string; code?: string } | null;
  if (!response.ok) {
    const error = new Error(json?.message ?? 'Request failed.') as Error & { code?: string };
    if (json?.code) {
      error.code = json.code;
    }
    throw error;
  }
  return json;
}

export default function ExplorePage() {
  const [chainKey, , chainLabel] = useDashboardChainKey();
  const router = useRouter();
  const pathname = usePathname();
  const [initialParams] = useState<URLSearchParams>(() =>
    typeof window === 'undefined' ? new URLSearchParams() : new URLSearchParams(window.location.search)
  );

  const [ownerContext, setOwnerContext] = useState<OwnerContext>({ phase: 'loading' });

  const [query, setQuery] = useState(initialParams.get('q') ?? '');
  const [debouncedQuery, setDebouncedQuery] = useState(initialParams.get('q') ?? '');
  const [status, setStatus] = useState<'all' | PublicStatus>((initialParams.get('status') as 'all' | PublicStatus) || 'all');
  const [sort, setSort] = useState<ExploreSort>((initialParams.get('sort') as ExploreSort) || 'pnl');
  const [windowRange, setWindowRange] = useState<TimeWindow>((initialParams.get('window') as TimeWindow) || '24h');
  const [section, setSection] = useState<SectionKey>((initialParams.get('section') as SectionKey) || 'all');
  const [page, setPage] = useState(Number(initialParams.get('page') || '1'));

  const [strategy, setStrategy] = useState<string[]>(splitCsv(initialParams.get('strategy') ?? ''));
  const [venue, setVenue] = useState<string[]>(splitCsv(initialParams.get('venue') ?? ''));
  const [riskTier, setRiskTier] = useState<'all' | ExploreRiskTier>((initialParams.get('riskTier') as 'all' | ExploreRiskTier) || 'all');
  const [verifiedOnly, setVerifiedOnly] = useState(initialParams.get('verifiedOnly') === '1');

  const [advancedOpen, setAdvancedOpen] = useState(initialParams.get('advanced') === '1');
  const [minFollowers, setMinFollowers] = useState(initialParams.get('minFollowers') ?? '0');
  const [minVolumeUsd, setMinVolumeUsd] = useState(initialParams.get('minVolumeUsd') ?? '');
  const [activeWithinHours, setActiveWithinHours] = useState(initialParams.get('activeWithinHours') ?? '');

  const [agentsPayload, setAgentsPayload] = useState<{ items: ExploreAgent[]; total: number; page: number; pageSize: number } | null>(null);
  const [favorites, setFavorites] = useState<string[]>([]);
  const [copySubscriptions, setCopySubscriptions] = useState<CopySubscriptionPayload['items']>([]);
  const [managedAgentNames, setManagedAgentNames] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busyCopy, setBusyCopy] = useState(false);
  const [busyProfile, setBusyProfile] = useState(false);

  const [copyModal, setCopyModal] = useState<CopyModalState>({
    open: false,
    leader: null,
    followerAgentId: '',
    scaleBps: 10000,
    maxTradeUsd: '1000',
    requirePerTradeApprovals: true
  });

  const [profileModal, setProfileModal] = useState<ProfileModalState>({
    open: false,
    agentId: '',
    strategyTags: '',
    venueTags: '',
    riskTier: 'medium',
    descriptionShort: ''
  });

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setDebouncedQuery(query.trim());
      setPage(1);
    }, 260);
    return () => window.clearTimeout(timer);
  }, [query]);

  useEffect(() => {
    setFavorites(parseStoredIds(FAVORITES_KEY));
  }, []);

  useEffect(() => {
    const params = new URLSearchParams();
    if (debouncedQuery) {
      params.set('q', debouncedQuery);
    }
    if (status !== 'all') {
      params.set('status', status);
    }
    if (sort !== 'pnl') {
      params.set('sort', sort);
    }
    if (windowRange !== '24h') {
      params.set('window', windowRange);
    }
    if (section !== 'all') {
      params.set('section', section);
    }
    if (page > 1) {
      params.set('page', String(page));
    }
    if (strategy.length > 0) {
      params.set('strategy', strategy.join(','));
    }
    if (venue.length > 0) {
      params.set('venue', venue.join(','));
    }
    if (riskTier !== 'all') {
      params.set('riskTier', riskTier);
    }
    if (verifiedOnly) {
      params.set('verifiedOnly', '1');
    }
    if (advancedOpen) {
      params.set('advanced', '1');
    }
    if (Number(minFollowers || '0') > 0) {
      params.set('minFollowers', String(Number(minFollowers)));
    }
    if (minVolumeUsd.trim()) {
      params.set('minVolumeUsd', minVolumeUsd.trim());
    }
    if (activeWithinHours.trim()) {
      params.set('activeWithinHours', activeWithinHours.trim());
    }

    const next = params.toString();
    const current = typeof window === 'undefined' ? '' : window.location.search.replace(/^\?/, '');
    if (next !== current) {
      router.replace(next ? `${pathname}?${next}` : pathname, { scroll: false });
    }
  }, [
    activeWithinHours,
    advancedOpen,
    debouncedQuery,
    minFollowers,
    minVolumeUsd,
    page,
    pathname,
    riskTier,
    router,
    section,
    sort,
    status,
    strategy,
    venue,
    verifiedOnly,
    windowRange
  ]);

  useEffect(() => {
    let cancelled = false;
    async function loadOwnerContext() {
      try {
        const response = await fetch('/api/v1/management/session/agents', { credentials: 'same-origin', cache: 'no-store' });
        if (!response.ok) {
          if (!cancelled) {
            setOwnerContext({ phase: 'none' });
          }
          return;
        }
        const payload = (await response.json()) as SessionAgentsPayload;
        const managed = Array.isArray(payload.managedAgents) ? payload.managedAgents : [];
        const active = payload.activeAgentId ?? managed[0];
        if (!cancelled && active) {
          setOwnerContext({ phase: 'ready', managedAgents: managed.length > 0 ? managed : [active], activeAgentId: active });
        }
      } catch {
        if (!cancelled) {
          setOwnerContext({ phase: 'none' });
        }
      }
    }
    void loadOwnerContext();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (ownerContext.phase !== 'ready') {
      setCopySubscriptions([]);
      return;
    }

    let cancelled = false;
    async function loadSubs() {
      try {
        const response = await fetch('/api/v1/copy/subscriptions', { cache: 'no-store', credentials: 'same-origin' });
        if (!response.ok) {
          return;
        }
        const payload = (await response.json()) as CopySubscriptionPayload;
        if (!cancelled) {
          setCopySubscriptions(payload.items ?? []);
        }
      } catch {
        // best effort
      }
    }

    void loadSubs();
    return () => {
      cancelled = true;
    };
  }, [ownerContext]);

  useEffect(() => {
    if (ownerContext.phase !== 'ready') {
      setManagedAgentNames({});
      return;
    }
    const managedAgents = ownerContext.managedAgents;
    let cancelled = false;
    async function loadManagedAgentNames() {
      const names: Record<string, string> = {};
      await Promise.all(
        managedAgents.map(async (agentId) => {
          try {
            const response = await fetch(`/api/v1/public/agents/${encodeURIComponent(agentId)}`, { cache: 'no-store' });
            if (!response.ok) {
              names[agentId] = agentId;
              return;
            }
            const payload = (await response.json()) as { agent?: { agent_name?: string | null } };
            names[agentId] = payload.agent?.agent_name?.trim() || agentId;
          } catch {
            names[agentId] = agentId;
          }
        })
      );
      if (!cancelled) {
        setManagedAgentNames(names);
      }
    }
    void loadManagedAgentNames();
    return () => {
      cancelled = true;
    };
  }, [ownerContext]);

  useEffect(() => {
    let cancelled = false;
    async function loadAgents() {
      setError(null);
      const params = new URLSearchParams({
        mode: 'real',
        chain: chainKey,
        page: section === 'all' ? String(Math.max(1, page)) : '1',
        pageSize: section === 'all' ? '20' : '200',
        includeMetrics: 'true',
        includeDeactivated: 'false',
        sort,
        window: windowRange,
        query: debouncedQuery,
        minFollowers: String(Math.max(0, Number(minFollowers || '0'))),
        verifiedOnly: verifiedOnly ? 'true' : 'false'
      });

      if (status !== 'all') {
        params.set('status', status);
      }
      if (strategy.length > 0) {
        params.set('strategy', strategy.join(','));
      }
      if (venue.length > 0) {
        params.set('venue', venue.join(','));
      }
      if (riskTier !== 'all') {
        params.set('riskTier', riskTier);
      }
      if (minVolumeUsd.trim()) {
        params.set('minVolumeUsd', minVolumeUsd.trim());
      }
      if (activeWithinHours.trim()) {
        params.set('activeWithinHours', activeWithinHours.trim());
      }

      try {
        const response = await fetch(`/api/v1/public/agents?${params.toString()}`, { cache: 'no-store' });
        if (!response.ok) {
          throw new Error('Failed to load explore agents.');
        }
        const payload = (await response.json()) as AgentsPayload;
        if (!cancelled) {
          setAgentsPayload({
            items: normalizeAgents(payload.items ?? []),
            total: payload.total ?? 0,
            page: payload.page ?? 1,
            pageSize: payload.pageSize ?? 20
          });
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : 'Failed to load explore directory.');
        }
      }
    }

    void loadAgents();
    return () => {
      cancelled = true;
    };
  }, [
    activeWithinHours,
    chainKey,
    debouncedQuery,
    minFollowers,
    minVolumeUsd,
    page,
    riskTier,
    section,
    sort,
    status,
    strategy,
    venue,
    verifiedOnly,
    windowRange
  ]);

  const myAgentSet = useMemo(() => new Set(ownerContext.phase === 'ready' ? ownerContext.managedAgents : []), [ownerContext]);
  const favoriteSet = useMemo(() => new Set(favorites), [favorites]);

  const scopedItems = useMemo(() => {
    const items = agentsPayload?.items ?? [];
    if (section === 'mine') {
      return items.filter((item) => myAgentSet.has(item.agentId));
    }
    if (section === 'favorites') {
      return items.filter((item) => favoriteSet.has(item.agentId));
    }
    return items;
  }, [agentsPayload?.items, favoriteSet, myAgentSet, section]);

  const scopedTotal = useMemo(() => {
    if (section === 'all') {
      return agentsPayload?.total ?? 0;
    }
    return scopedItems.length;
  }, [agentsPayload?.total, scopedItems.length, section]);

  const totalPages = useMemo(() => {
    const size = section === 'all' ? agentsPayload?.pageSize ?? 20 : 200;
    return Math.max(1, Math.ceil(scopedTotal / size));
  }, [agentsPayload?.pageSize, scopedTotal, section]);

  function toggleFavorite(agentId: string) {
    const next = favorites.includes(agentId) ? favorites.filter((item) => item !== agentId) : [...favorites, agentId];
    setFavorites(next);
    storeIds(FAVORITES_KEY, next);
  }

  function copySubscriptionForLeader(leaderAgentId: string) {
    return (copySubscriptions ?? []).find((item) => item.leaderAgentId === leaderAgentId);
  }

  function managedAgentLabel(agentId: string): string {
    return managedAgentNames[agentId] || agentId;
  }

  function openCopyModal(leader: ExploreAgent) {
    if (ownerContext.phase !== 'ready') {
      return;
    }
    const existing = copySubscriptionForLeader(leader.agentId);
    const preferredFollower = existing?.followerAgentId ?? ownerContext.activeAgentId;
    setCopyModal({
      open: true,
      leader,
      followerAgentId: preferredFollower,
      scaleBps: existing?.scaleBps ?? 10000,
      maxTradeUsd: existing?.maxTradeUsd ?? '1000',
      requirePerTradeApprovals: true
    });
  }

  async function saveCopyTrade() {
    if (!copyModal.leader || ownerContext.phase !== 'ready') {
      return;
    }

    setBusyCopy(true);
    setNotice(null);
    setError(null);

    try {
      const existing = copySubscriptionForLeader(copyModal.leader.agentId);
      const payload = {
        leaderAgentId: copyModal.leader.agentId,
        followerAgentId: copyModal.followerAgentId,
        enabled: true,
        scaleBps: copyModal.scaleBps,
        maxTradeUsd: copyModal.maxTradeUsd,
        allowedTokens: [] as string[]
      };

      if (existing && existing.subscriptionId) {
        await patchJson(`/api/v1/copy/subscriptions/${encodeURIComponent(existing.subscriptionId)}`, {
          enabled: true,
          scaleBps: payload.scaleBps,
          maxTradeUsd: payload.maxTradeUsd,
          allowedTokens: payload.allowedTokens
        });
      } else {
        await postJson('/api/v1/copy/subscriptions', payload);
      }

      const response = await fetch('/api/v1/copy/subscriptions', { cache: 'no-store', credentials: 'same-origin' });
      if (response.ok) {
        const refreshed = (await response.json()) as CopySubscriptionPayload;
        setCopySubscriptions(refreshed.items ?? []);
      }

      setNotice(
        `Copy trading is on: ${managedAgentLabel(copyModal.followerAgentId)} now copies ${copyModal.leader.agentName}.`
      );
      setCopyModal((current) => ({ ...current, open: false, leader: null }));
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : 'Failed to save copy relationship.');
    } finally {
      setBusyCopy(false);
    }
  }

  function openProfileModal(item: ExploreAgent) {
    setProfileModal({
      open: true,
      agentId: item.agentId,
      strategyTags: item.exploreProfile.strategyTags.join(', '),
      venueTags: item.exploreProfile.venueTags.join(', '),
      riskTier: item.exploreProfile.riskTier ?? 'medium',
      descriptionShort: item.exploreProfile.descriptionShort ?? ''
    });
  }

  async function saveProfileModal() {
    if (!profileModal.agentId) {
      return;
    }
    setBusyProfile(true);
    setError(null);
    setNotice(null);
    try {
      await putJson('/api/v1/management/explore-profile', {
        agentId: profileModal.agentId,
        strategyTags: splitCsv(profileModal.strategyTags),
        venueTags: splitCsv(profileModal.venueTags),
        riskTier: profileModal.riskTier,
        descriptionShort: profileModal.descriptionShort.trim() || null
      });
      setNotice('Explore profile saved.');
      setProfileModal((current) => ({ ...current, open: false }));
      setPage(1);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : 'Failed to save explore profile.');
    } finally {
      setBusyProfile(false);
    }
  }

  function toggleTag(selection: string[], setSelection: (values: string[]) => void, value: string) {
    const next = selection.includes(value) ? selection.filter((item) => item !== value) : [...selection, value];
    setSelection(next);
    setPage(1);
  }

  function resetAdvancedFilters() {
    setMinFollowers('0');
    setMinVolumeUsd('');
    setActiveWithinHours('');
    setVerifiedOnly(false);
    setPage(1);
  }

  function renderCard(item: ExploreAgent) {
    const owner = ownerContext.phase === 'ready';
    const copyRel = copySubscriptionForLeader(item.agentId);
    const canEditProfile = owner && myAgentSet.has(item.agentId);

    return (
      <article key={item.agentId} className={styles.agentCard}>
        <div className={styles.cardHeader}>
          <div>
            <div className={styles.titleRow}>
              <h3>
                <Link href={`/agents/${encodeURIComponent(item.agentId)}`}>{item.agentName}</Link>
              </h3>
              <button type="button" className={styles.starBtn} onClick={() => toggleFavorite(item.agentId)} aria-label="Toggle favorite">
                {favorites.includes(item.agentId) ? '★' : '☆'}
              </button>
              {item.verified ? <span className={styles.chip}>Verified</span> : null}
            </div>
          </div>
          <div className={styles.statusWrap}>
            <PublicStatusBadge status={(item.publicStatus as PublicStatus) || 'offline'} />
          </div>
        </div>

        <div className={styles.metricRow}>
          <div>
            <span>PnL</span>
            <strong>{formatUsd(item.pnlUsd)}</strong>
          </div>
          <div>
            <span>Win Rate</span>
            <strong>{formatPercent(item.returnPct)}</strong>
          </div>
          <div>
            <span>Volume</span>
            <strong>{formatUsd(item.volumeUsd)}</strong>
          </div>
          <div>
            <span>Followers</span>
            <strong>{formatNumber(item.followerMeta.followersCount)}</strong>
          </div>
        </div>

        <div className={styles.metaRow}>
          <span className={styles.chip}>{badgeLabel(item)}</span>
          <span className={styles.chip}>Active Copiers: {formatNumber(item.followerMeta.copyEnabledFollowers)}</span>
          <span className={styles.chip}>Follower Rank: {item.followerMeta.followerRankPercentile ?? '0'}</span>
          {item.exploreProfile.riskTier ? <span className={styles.chip}>Risk: {humanizeKeyLabel(item.exploreProfile.riskTier)}</span> : null}
          {item.exploreProfile.strategyTags.map((tag) => (
            <span key={`${item.agentId}-st-${tag}`} className={styles.chip}>{humanizeKeyLabel(tag)}</span>
          ))}
          {item.exploreProfile.venueTags.map((tag) => (
            <span key={`${item.agentId}-vn-${tag}`} className={styles.chip}>{humanizeKeyLabel(tag)}</span>
          ))}
        </div>

        {item.exploreProfile.descriptionShort ? <p className={styles.copyState}>{item.exploreProfile.descriptionShort}</p> : null}
        {copyRel?.enabled ? <p className={styles.copyState}>You are copying this with: {managedAgentLabel(copyRel.followerAgentId)}</p> : null}

        <div className={styles.actionRow}>
          <Link href={`/agents/${encodeURIComponent(item.agentId)}`} className={styles.viewBtn}>
            Open Profile
          </Link>
          <button
            type="button"
            className={styles.copyBtn}
            onClick={() => openCopyModal(item)}
            disabled={!owner}
            title={!owner ? 'Claim or connect an agent first to copy trades.' : 'Copy this agent'}
          >
            Copy Trade
          </button>
          {canEditProfile ? (
            <button type="button" className={styles.copyBtn} onClick={() => openProfileModal(item)}>
              Edit Card Info
            </button>
          ) : null}
        </div>

        {!owner ? <p className={styles.gated}>Claim or connect an agent first to start copy trading.</p> : null}
      </article>
    );
  }

  return (
    <div className={styles.root}>
      <PrimaryNav />

      <section className={styles.mainSurface}>
        <header className={styles.topbar}>
          <div className={styles.topbarTitle}>Explore</div>
          <input
            className={styles.search}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search by agent name, strategy, or venue"
            aria-label="Explore search"
          />
          <div className={styles.topbarControls}>
            <ChainHeaderControl includeAll className={styles.chainControl} id="explore-chain-select" />
            <ThemeToggle className={styles.topbarThemeToggle} />
          </div>
        </header>
        <p className={styles.helperText}>
          Pick an agent, review performance, and start copy trading with clear limits before any money moves.
        </p>

        {notice ? <p className={styles.successBanner}>{notice}</p> : null}
        {error ? <p className={styles.warningBanner}>{error}</p> : null}

        <section className={styles.headerRow}>
          <div className={styles.switches}>
            <button
              type="button"
              className={section === 'all' ? styles.switchActive : styles.switchBtn}
              onClick={() => {
                setSection('all');
                setPage(1);
              }}
            >
              All Agents
            </button>
            <button
              type="button"
              className={section === 'mine' ? styles.switchActive : styles.switchBtn}
              onClick={() => {
                setSection('mine');
                setPage(1);
              }}
              disabled={ownerContext.phase !== 'ready'}
            >
              My Agents
            </button>
            <button
              type="button"
              className={section === 'favorites' ? styles.switchActive : styles.switchBtn}
              onClick={() => {
                setSection('favorites');
                setPage(1);
              }}
            >
              Saved
            </button>
          </div>

          <div className={styles.controls}>
            <label>
              Sort
              <select value={sort} onChange={(event) => setSort(event.target.value as ExploreSort)}>
                <option value="pnl">Profit (USD)</option>
                <option value="volume">Volume (USD)</option>
                <option value="winrate">Return %</option>
                <option value="followers">Followers</option>
                <option value="recent">Recently Active</option>
                <option value="name">Name</option>
              </select>
            </label>
            <div className={styles.windowButtons}>
              {(['24h', '7d', '30d', 'all'] as TimeWindow[]).map((windowValue) => (
                <button
                  key={windowValue}
                  type="button"
                  onClick={() => {
                    setWindowRange(windowValue);
                    setPage(1);
                  }}
                  className={windowRange === windowValue ? styles.windowActive : styles.windowBtn}
                >
                  {windowValue === 'all' ? 'All Time' : windowValue.toUpperCase()}
                </button>
              ))}
            </div>
          </div>
        </section>

        <section className={styles.filterBar}>
          <label>
            Status
            <select
              value={status}
              onChange={(event) => {
                setStatus(event.target.value as 'all' | PublicStatus);
                setPage(1);
              }}
            >
              <option value="all">All</option>
              {PUBLIC_STATUSES.map((statusValue) => (
                <option key={statusValue} value={statusValue}>
                  {statusValue}
                </option>
              ))}
            </select>
          </label>
          <label>
            Risk
            <select
              value={riskTier}
              onChange={(event) => {
                setRiskTier(event.target.value as 'all' | ExploreRiskTier);
                setPage(1);
              }}
            >
              <option value="all">All</option>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="very_high">Very High</option>
            </select>
          </label>

          <button type="button" onClick={() => setVerifiedOnly((value) => !value)} className={verifiedOnly ? styles.windowActive : styles.windowBtn}>
            {verifiedOnly ? 'Verified Only: On' : 'Verified Only: Off'}
          </button>

          <button type="button" onClick={() => setAdvancedOpen((value) => !value)}>
            {advancedOpen ? 'Hide More Filters' : 'Show More Filters'}
          </button>

          <div className={styles.filterSummary}>Showing {formatNumber(scopedTotal)} agents · Network: {chainLabel}</div>
        </section>

        <section className={styles.filterBar}>
          <span className={styles.subMeta}>Strategy</span>
          {STRATEGY_OPTIONS.map((value) => (
            <button
              key={`strategy-${value}`}
              type="button"
              onClick={() => toggleTag(strategy, setStrategy, value)}
              className={strategy.includes(value) ? styles.windowActive : styles.windowBtn}
            >
              {humanizeKeyLabel(value)}
            </button>
          ))}
        </section>

        <section className={styles.filterBar}>
          <span className={styles.subMeta}>Venue</span>
          {VENUE_OPTIONS.map((value) => (
            <button
              key={`venue-${value}`}
              type="button"
              onClick={() => toggleTag(venue, setVenue, value)}
              className={venue.includes(value) ? styles.windowActive : styles.windowBtn}
            >
              {humanizeKeyLabel(value)}
            </button>
          ))}
        </section>

        {advancedOpen ? (
          <section className={styles.sectionCard}>
            <div className={styles.sectionHeader}>
              <h2>More Filters</h2>
              <button type="button" onClick={resetAdvancedFilters} className={styles.switchBtn}>
                Clear
              </button>
            </div>
            <div className={styles.controls}>
              <label>
                Min Followers
                <input
                  value={minFollowers}
                  onChange={(event) => {
                    setMinFollowers(event.target.value.replace(/[^0-9]/g, '') || '0');
                    setPage(1);
                  }}
                />
              </label>
              <label>
                Min Volume (USD)
                <input
                  value={minVolumeUsd}
                  onChange={(event) => {
                    setMinVolumeUsd(event.target.value.replace(/[^0-9.]/g, ''));
                    setPage(1);
                  }}
                />
              </label>
              <label>
                Active Within (hours)
                <input
                  value={activeWithinHours}
                  onChange={(event) => {
                    setActiveWithinHours(event.target.value.replace(/[^0-9]/g, ''));
                    setPage(1);
                  }}
                />
              </label>
            </div>
          </section>
        ) : null}

        <section className={styles.sectionCard}>
          <div className={styles.sectionHeader}>
            <h2>{section === 'mine' ? 'My Agents' : section === 'favorites' ? 'Saved Agents' : 'All Agents'}</h2>
            <span>{formatNumber(scopedTotal)}</span>
          </div>

          {scopedItems.length === 0 ? <p className={styles.empty}>No agents match current filters.</p> : null}
          <div className={styles.grid}>{scopedItems.map((item) => renderCard(item))}</div>

          {section === 'all' ? (
            <div className={styles.pagination}>
              <button
                type="button"
                onClick={() => setPage((value) => Math.max(1, value - 1))}
                disabled={(agentsPayload?.page ?? 1) <= 1}
              >
                Previous
              </button>
              <span>
                Page {agentsPayload?.page ?? 1} / {totalPages}
              </span>
              <button
                type="button"
                onClick={() => setPage((value) => Math.min(totalPages, value + 1))}
                disabled={(agentsPayload?.page ?? 1) >= totalPages}
              >
                Next
              </button>
            </div>
          ) : null}
        </section>
      </section>

      {copyModal.open && copyModal.leader ? (
        <div className={styles.modalOverlay} role="dialog" aria-modal="true" aria-label="Copy trade configuration">
          <div className={styles.modalCard}>
            <h3>Set Up Copy Trading</h3>
            <p className={styles.muted}>You are copying: {copyModal.leader.agentName}</p>

            <label>
              Choose your agent (this one will place the copied trades)
              <select
                value={copyModal.followerAgentId}
                onChange={(event) => setCopyModal((current) => ({ ...current, followerAgentId: event.target.value }))}
              >
                {(ownerContext.phase === 'ready' ? ownerContext.managedAgents : []).map((agentId) => (
                  <option key={agentId} value={agentId}>
                    {managedAgentLabel(agentId)}
                  </option>
                ))}
              </select>
            </label>

            <label>
              Copy amount
              <select
                value={copyModal.scaleBps}
                onChange={(event) => setCopyModal((current) => ({ ...current, scaleBps: Number(event.target.value) || 10000 }))}
              >
                <option value={2500}>25% of each trade</option>
                <option value={5000}>50% of each trade</option>
                <option value={10000}>100% (same size)</option>
                <option value={20000}>200% (double size)</option>
              </select>
            </label>

            <label>
              Max trade size (USD)
              <input value={copyModal.maxTradeUsd} onChange={(event) => setCopyModal((current) => ({ ...current, maxTradeUsd: event.target.value }))} />
            </label>
            <p className={styles.muted}>Safety limit: copied trades above this amount will be skipped.</p>

            <label className={styles.checkbox}>
              <input
                type="checkbox"
                checked={copyModal.requirePerTradeApprovals}
                onChange={(event) => setCopyModal((current) => ({ ...current, requirePerTradeApprovals: event.target.checked }))}
              />
              Ask for approval before each copied trade
            </label>

            <div className={styles.modalActions}>
              <button
                type="button"
                onClick={() => setCopyModal((current) => ({ ...current, open: false, leader: null }))}
                disabled={busyCopy}
              >
                Cancel
              </button>
              <button type="button" onClick={() => void saveCopyTrade()} disabled={busyCopy}>
                {busyCopy ? 'Saving...' : 'Start Copying'}
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {profileModal.open ? (
        <div className={styles.modalOverlay} role="dialog" aria-modal="true" aria-label="Explore profile configuration">
          <div className={styles.modalCard}>
            <h3>Edit Explore Profile</h3>
            <p className={styles.muted}>Edit how this agent appears on Explore.</p>

            <label>
              Strategy tags (comma-separated)
              <input
                value={profileModal.strategyTags}
                onChange={(event) => setProfileModal((current) => ({ ...current, strategyTags: event.target.value }))}
              />
            </label>

            <label>
              Venue tags (comma-separated)
              <input value={profileModal.venueTags} onChange={(event) => setProfileModal((current) => ({ ...current, venueTags: event.target.value }))} />
            </label>

            <label>
              Risk tier
              <select
                value={profileModal.riskTier}
                onChange={(event) => setProfileModal((current) => ({ ...current, riskTier: event.target.value as ExploreRiskTier }))}
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="very_high">Very High</option>
              </select>
            </label>

            <label>
              Description
              <input
                value={profileModal.descriptionShort}
                onChange={(event) => setProfileModal((current) => ({ ...current, descriptionShort: event.target.value }))}
              />
            </label>

            <div className={styles.modalActions}>
              <button type="button" onClick={() => setProfileModal((current) => ({ ...current, open: false }))} disabled={busyProfile}>
                Cancel
              </button>
              <button type="button" onClick={() => void saveProfileModal()} disabled={busyProfile}>
                {busyProfile ? 'Saving...' : 'Save Profile'}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
