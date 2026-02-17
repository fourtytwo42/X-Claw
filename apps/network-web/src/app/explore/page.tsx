'use client';

import Image from 'next/image';
import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';

import { ChainHeaderControl } from '@/components/chain-header-control';
import { ActiveAgentSidebarLink } from '@/components/active-agent-sidebar-link';
import { PublicStatusBadge } from '@/components/public-status-badge';
import { SidebarIcon } from '@/components/sidebar-icons';
import { ThemeToggle } from '@/components/theme-toggle';
import { useDashboardChainKey } from '@/lib/active-chain';
import { EXPLORE_PAGE_CAPABILITIES } from '@/lib/explore-page-capabilities';
import {
  badgeLabel,
  filterByStatus,
  type LeaderboardMetric,
  normalizeAgents,
  searchAgents,
  sortAgents,
  type ExploreAgent,
  type ExploreSort
} from '@/lib/explore-page-view-model';
import { formatNumber, formatPercent, formatUsd, formatUtc } from '@/lib/public-format';
import { PUBLIC_STATUSES, type PublicStatus } from '@/lib/public-types';

import styles from './page.module.css';

type TimeWindow = '24h' | '7d' | '30d' | 'all';

type AgentsPayload = {
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
  }>;
};

type LeaderboardPayload = {
  items: Array<{
    agent_id: string;
    pnl_usd: string | null;
    volume_usd: string | null;
    return_pct: string | null;
    followers_count: number;
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

const FAVORITES_KEY = 'xclaw_explore_favorite_agent_ids';

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

export default function ExplorePage() {
  const [chainKey, , chainLabel] = useDashboardChainKey();
  const [ownerContext, setOwnerContext] = useState<OwnerContext>({ phase: 'loading' });

  const [query, setQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [status, setStatus] = useState<'all' | PublicStatus>('all');
  const [sort, setSort] = useState<ExploreSort>('pnl');
  const [windowRange, setWindowRange] = useState<TimeWindow>('24h');
  const [page, setPage] = useState(1);
  const pageSize = 20;

  const [agents, setAgents] = useState<ExploreAgent[] | null>(null);
  const [favorites, setFavorites] = useState<string[]>([]);
  const [copySubscriptions, setCopySubscriptions] = useState<CopySubscriptionPayload['items']>([]);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busyCopy, setBusyCopy] = useState(false);

  const [copyModal, setCopyModal] = useState<CopyModalState>({
    open: false,
    leader: null,
    followerAgentId: '',
    scaleBps: 10000,
    maxTradeUsd: '1000',
    requirePerTradeApprovals: true
  });

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setDebouncedQuery(query.trim());
      setPage(1);
    }, 260);

    return () => {
      window.clearTimeout(timer);
    };
  }, [query]);

  useEffect(() => {
    setFavorites(parseStoredIds(FAVORITES_KEY));
  }, []);

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
    let cancelled = false;

    async function load() {
      setError(null);
      const directoryParams = new URLSearchParams({
        page: '1',
        pageSize: '100',
        includeMetrics: 'true',
        includeDeactivated: 'false',
        mode: 'real',
        chain: chainKey,
        query: debouncedQuery,
        sort: sort === 'name' ? 'agent_name' : sort === 'recent' ? 'last_activity' : 'registration'
      });
      if (status !== 'all') {
        directoryParams.set('status', status);
      }

      const leaderboardParams = new URLSearchParams({ window: windowRange, mode: 'real', chain: chainKey, includeDeactivated: 'false' });

      try {
        const [agentsRes, leaderboardRes] = await Promise.all([
          fetch(`/api/v1/public/agents?${directoryParams.toString()}`, { cache: 'no-store' }),
          fetch(`/api/v1/public/leaderboard?${leaderboardParams.toString()}`, { cache: 'no-store' })
        ]);

        if (!agentsRes.ok) {
          throw new Error('Failed to load explore agents.');
        }

        const agentsPayload = (await agentsRes.json()) as AgentsPayload;
        const leaderboardPayload = leaderboardRes.ok ? ((await leaderboardRes.json()) as LeaderboardPayload) : { items: [] };
        const byAgent = new Map<string, LeaderboardMetric>();
        for (const item of leaderboardPayload.items ?? []) {
          byAgent.set(item.agent_id, {
            pnlUsd: item.pnl_usd,
            volumeUsd: item.volume_usd,
            returnPct: item.return_pct,
            followersCount: item.followers_count
          });
        }

        if (!cancelled) {
          const normalized = normalizeAgents(agentsPayload.items ?? [], byAgent);
          setAgents(sortAgents(filterByStatus(normalized, status), sort));
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : 'Failed to load explore directory.');
        }
      }
    }

    void load();

    return () => {
      cancelled = true;
    };
  }, [chainKey, debouncedQuery, sort, status, windowRange]);

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
      }
    }

    void loadSubs();

    return () => {
      cancelled = true;
    };
  }, [ownerContext]);

  const filtered = useMemo(() => searchAgents(agents ?? [], debouncedQuery), [agents, debouncedQuery]);

  const myAgents = useMemo(() => {
    if (ownerContext.phase !== 'ready') {
      return [] as ExploreAgent[];
    }
    const managed = new Set(ownerContext.managedAgents);
    return filtered.filter((item) => managed.has(item.agentId));
  }, [filtered, ownerContext]);

  const favoriteAgents = useMemo(() => {
    const favoriteSet = new Set(favorites);
    return filtered.filter((item) => favoriteSet.has(item.agentId));
  }, [filtered, favorites]);

  const allAgents = useMemo(() => {
    const total = filtered.length;
    const totalPages = Math.max(1, Math.ceil(total / pageSize));
    const clamped = Math.min(page, totalPages);
    const start = (clamped - 1) * pageSize;
    return {
      items: filtered.slice(start, start + pageSize),
      total,
      totalPages,
      page: clamped
    };
  }, [filtered, page]);

  useEffect(() => {
    if (allAgents.page !== page) {
      setPage(allAgents.page);
    }
  }, [allAgents.page, page]);

  function toggleFavorite(agentId: string) {
    const next = favorites.includes(agentId) ? favorites.filter((item) => item !== agentId) : [...favorites, agentId];
    setFavorites(next);
    storeIds(FAVORITES_KEY, next);
  }

  function copySubscriptionForLeader(leaderAgentId: string) {
    return (copySubscriptions ?? []).find((item) => item.leaderAgentId === leaderAgentId);
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

      setNotice(`Copy relationship saved: ${copyModal.followerAgentId} now follows ${copyModal.leader.agentId}.`);
      setCopyModal((current) => ({ ...current, open: false, leader: null }));
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : 'Failed to save copy relationship.');
    } finally {
      setBusyCopy(false);
    }
  }

  function renderCard(item: ExploreAgent, section: 'mine' | 'favorites' | 'all') {
    const owner = ownerContext.phase === 'ready';
    const copyRel = copySubscriptionForLeader(item.agentId);

    return (
      <article key={`${section}:${item.agentId}`} className={styles.agentCard}>
        <div className={styles.cardHeader}>
          <div>
            <div className={styles.titleRow}>
              <h3>
                <Link href={`/agents/${encodeURIComponent(item.agentId)}`}>{item.agentName}</Link>
              </h3>
              <button type="button" className={styles.starBtn} onClick={() => toggleFavorite(item.agentId)} aria-label="Toggle favorite">
                {favorites.includes(item.agentId) ? '★' : '☆'}
              </button>
            </div>
            <p className={styles.subMeta}>{item.agentId}</p>
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
            <strong>{formatNumber(item.followersCount)}</strong>
          </div>
        </div>

        <div className={styles.metaRow}>
          <span className={styles.chip}>{badgeLabel(item)}</span>
          <span className={styles.chip}>Window: {windowRange.toUpperCase()}</span>
          <span className={styles.chip} title="Placeholder until strategy metadata API support is available">
            strategy filter placeholder
          </span>
          <span className={styles.chip} title="Placeholder until risk metadata API support is available">
            risk placeholder
          </span>
        </div>

        {copyRel?.enabled ? <p className={styles.copyState}>Copying into follower: {copyRel.followerAgentId}</p> : null}

        <div className={styles.actionRow}>
          <Link href={`/agents/${encodeURIComponent(item.agentId)}`} className={styles.viewBtn}>
            View
          </Link>
          <button
            type="button"
            className={styles.copyBtn}
            onClick={() => openCopyModal(item)}
            disabled={!owner}
            title={!owner ? 'Add an owned agent via key link to enable copy trading.' : 'Copy this agent'}
          >
            Copy Trade
          </button>
        </div>
        {!owner ? <p className={styles.gated}>Add an owned agent via key link to enable copy trading.</p> : null}
      </article>
    );
  }

  return (
    <div className={styles.root}>
      <aside className={styles.sidebar}>
        <Link href="/" className={styles.sidebarLogo} aria-label="X-Claw home">
          <Image src="/X-Claw-Logo.png" alt="X-Claw" width={900} height={280} className={styles.sidebarLogoImage} priority />
        </Link>
        <nav className={styles.sidebarNav} aria-label="Explore sections">
          <Link className={styles.sidebarItem} href="/dashboard" aria-label="Dashboard" title="Dashboard">
            <SidebarIcon name="dashboard" />
          </Link>
          <Link className={`${styles.sidebarItem} ${styles.sidebarItemActive}`} href="/explore" aria-label="Explore" title="Explore">
            <SidebarIcon name="explore" />
          </Link>
          <Link className={styles.sidebarItem} href="/approvals" aria-label="Approvals Center" title="Approvals Center">
            <SidebarIcon name="approvals" />
          </Link>
          <ActiveAgentSidebarLink itemClassName={styles.sidebarItem} />
          <div style={{ marginTop: 'auto', display: 'grid', gap: '0.42rem' }}>
            <Link className={styles.sidebarItem} href="/settings" aria-label="Settings & Security" title="Settings & Security">
              <SidebarIcon name="settings" />
            </Link>
            <Link className={styles.sidebarItem} href="/how-to" aria-label="How To" title="How To">
              <SidebarIcon name="howto" />
            </Link>
          </div>
        </nav>
      </aside>

      <section className={styles.mainSurface}>
        <header className={styles.topbar}>
          <div className={styles.topbarTitle}>Explore</div>
          <input
            className={styles.search}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search wallet, strategy, or agent..."
            aria-label="Explore search"
          />
          <div className={styles.topbarControls}>
            <ChainHeaderControl includeAll className={styles.chainControl} id="explore-chain-select" />
            <ThemeToggle className={styles.topbarThemeToggle} />
          </div>
        </header>

        {notice ? <p className={styles.successBanner}>{notice}</p> : null}
        {error ? <p className={styles.warningBanner}>{error}</p> : null}

        <section className={styles.headerRow}>
          <div className={styles.switches}>
            <button type="button" className={styles.switchActive}>
              {ownerContext.phase === 'ready' ? 'My Agents' : 'All Agents'}
            </button>
            <button type="button" className={styles.switchBtn}>
              Favorites
            </button>
            <button type="button" className={styles.switchBtn}>
              All Agents
            </button>
          </div>

          <div className={styles.controls}>
            <label>
              Sort
              <select value={sort} onChange={(event) => setSort(event.target.value as ExploreSort)}>
                <option value="pnl">PnL</option>
                <option value="volume">Volume</option>
                <option value="winrate">Win Rate</option>
                <option value="recent">Recently Active</option>
                <option value="name">Name</option>
              </select>
            </label>
            <div className={styles.windowButtons}>
              {(['24h', '7d', '30d', 'all'] as TimeWindow[]).map((windowValue) => (
                <button
                  key={windowValue}
                  type="button"
                  onClick={() => setWindowRange(windowValue)}
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
            <select value={status} onChange={(event) => setStatus(event.target.value as 'all' | PublicStatus)}>
              <option value="all">All</option>
              {PUBLIC_STATUSES.map((statusValue) => (
                <option key={statusValue} value={statusValue}>
                  {statusValue}
                </option>
              ))}
            </select>
          </label>
          <button type="button" disabled={!EXPLORE_PAGE_CAPABILITIES.strategyFilterApi}>
            Strategy (placeholder)
          </button>
          <button type="button" disabled={!EXPLORE_PAGE_CAPABILITIES.venueFilterApi}>
            Venue (placeholder)
          </button>
          <button type="button" disabled={!EXPLORE_PAGE_CAPABILITIES.riskFilterApi}>
            Any risk (placeholder)
          </button>
          <div className={styles.filterSummary}>Showing {formatNumber(filtered.length)} agents · Network: {chainLabel}</div>
        </section>

        {ownerContext.phase === 'ready' ? (
          <section className={styles.sectionCard}>
            <div className={styles.sectionHeader}>
              <h2>My Agents</h2>
              <span>{formatNumber(myAgents.length)}</span>
            </div>
            {myAgents.length === 0 ? <p className={styles.empty}>No owned agents match the current filters.</p> : null}
            <div className={styles.grid}>{myAgents.map((item) => renderCard(item, 'mine'))}</div>
          </section>
        ) : null}

        <section className={styles.sectionCard}>
          <div className={styles.sectionHeader}>
            <h2>Favorites</h2>
            <span>{formatNumber(favoriteAgents.length)}</span>
          </div>
          {favoriteAgents.length === 0 ? <p className={styles.empty}>No favorites yet. Star agents to pin them here.</p> : null}
          <div className={styles.grid}>{favoriteAgents.map((item) => renderCard(item, 'favorites'))}</div>
        </section>

        <section className={styles.sectionCard}>
          <div className={styles.sectionHeader}>
            <h2>All Agents</h2>
            <span>{formatNumber(allAgents.total)}</span>
          </div>
          {allAgents.items.length === 0 ? <p className={styles.empty}>No agents match current search/filter settings. Reset filters and retry.</p> : null}
          <div className={styles.grid}>{allAgents.items.map((item) => renderCard(item, 'all'))}</div>

          <div className={styles.pagination}>
            <button type="button" onClick={() => setPage((value) => Math.max(1, value - 1))} disabled={allAgents.page <= 1}>
              Previous
            </button>
            <span>
              Page {allAgents.page} / {allAgents.totalPages}
            </span>
            <button type="button" onClick={() => setPage((value) => Math.min(allAgents.totalPages, value + 1))} disabled={allAgents.page >= allAgents.totalPages}>
              Next
            </button>
          </div>
          <p className={styles.placeholderNotice}>
            Strategy/risk/venue enrichment, advanced filters, and follower-rich metadata are placeholder-only until API support is added.
          </p>
          <p className={styles.placeholderNotice}>Updated activity timestamps are shown in UTC. Example latest activity: {formatUtc(allAgents.items[0]?.lastActivityAt ?? null)} UTC</p>
        </section>
      </section>

      {copyModal.open && copyModal.leader ? (
        <div className={styles.modalOverlay} role="dialog" aria-modal="true" aria-label="Copy trade configuration">
          <div className={styles.modalCard}>
            <h3>Copy this agent into...</h3>
            <p className={styles.muted}>Leader: {copyModal.leader.agentName}</p>

            <label>
              Destination agent
              <select
                value={copyModal.followerAgentId}
                onChange={(event) => setCopyModal((current) => ({ ...current, followerAgentId: event.target.value }))}
              >
                {(ownerContext.phase === 'ready' ? ownerContext.managedAgents : []).map((agentId) => (
                  <option key={agentId} value={agentId}>
                    {agentId}
                  </option>
                ))}
              </select>
            </label>

            <label>
              Scale (bps)
              <select
                value={copyModal.scaleBps}
                onChange={(event) => setCopyModal((current) => ({ ...current, scaleBps: Number(event.target.value) || 10000 }))}
              >
                <option value={2500}>0.25x</option>
                <option value={5000}>0.5x</option>
                <option value={10000}>1.0x</option>
                <option value={20000}>2.0x</option>
              </select>
            </label>

            <label>
              Max trade USD
              <input
                value={copyModal.maxTradeUsd}
                onChange={(event) => setCopyModal((current) => ({ ...current, maxTradeUsd: event.target.value }))}
              />
            </label>

            <label className={styles.checkbox}>
              <input
                type="checkbox"
                checked={copyModal.requirePerTradeApprovals}
                onChange={(event) => setCopyModal((current) => ({ ...current, requirePerTradeApprovals: event.target.checked }))}
              />
              Require per-trade approvals (device default hint)
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
                {busyCopy ? 'Saving...' : 'Enable Copy Trading'}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
