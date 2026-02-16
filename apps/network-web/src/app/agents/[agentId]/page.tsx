'use client';

import Link from 'next/link';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useParams, useRouter, useSearchParams } from 'next/navigation';

import { ChainHeaderControl } from '@/components/chain-header-control';
import { rememberManagedAgent } from '@/components/management-header-controls';
import { PublicStatusBadge } from '@/components/public-status-badge';
import { SidebarIcon } from '@/components/sidebar-icons';
import { ThemeToggle } from '@/components/theme-toggle';
import { useActiveChainKey } from '@/lib/active-chain';
import { AGENT_PAGE_CAPABILITIES } from '@/lib/agent-page-capabilities';
import {
  buildActivityRows,
  buildHoldings,
  formatDecimalText,
  formatUnitsTruncated,
  type ActivityPayload,
  type AgentProfilePayload,
  type DepositPayload,
  type LimitOrderItem,
  type ManagementStatePayload,
  type TradePayload,
  tokenSymbolByAddress
} from '@/lib/agent-page-view-model';
import { formatPercent, formatUsd, formatUtc, isStale, shortenAddress } from '@/lib/public-format';
import { isPublicStatus } from '@/lib/public-types';

import styles from './page.module.css';

type BootstrapState =
  | { phase: 'bootstrapping' }
  | { phase: 'error'; message: string; code?: string; actionHint?: string }
  | { phase: 'ready' };

type ManagementViewState =
  | { phase: 'loading' }
  | { phase: 'unauthorized' }
  | { phase: 'error'; message: string }
  | { phase: 'ready'; data: ManagementStatePayload };

type CopySubscription = {
  subscriptionId: string;
  leaderAgentId: string;
  followerAgentId: string;
  enabled: boolean;
  scaleBps: number;
  maxTradeUsd: string | null;
  allowedTokens: string[];
  createdAt: string;
  updatedAt: string;
};

type CopySubscriptionsGetPayload = {
  ok: boolean;
  items: CopySubscription[];
};

type PageTab = 'overview' | 'trades' | 'holdings' | 'permissions' | 'risk';

type TimeRange = '1h' | '24h' | '7d' | '30d';

const HEARTBEAT_STALE_THRESHOLD_SECONDS = 180;

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

async function managementPost(path: string, payload: Record<string, unknown>) {
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

  const json = (await response.json().catch(() => null)) as { message?: string; code?: string; actionHint?: string } | null;
  if (!response.ok) {
    const error = new Error(json?.message ?? 'Management request failed.') as Error & { code?: string; actionHint?: string };
    if (json?.code) {
      error.code = json.code;
    }
    if (json?.actionHint) {
      error.actionHint = json.actionHint;
    }
    throw error;
  }

  return json;
}

async function managementGet(path: string) {
  const csrf = getCsrfToken();
  const headers: Record<string, string> = {};
  if (csrf) {
    headers['x-csrf-token'] = csrf;
  }

  const response = await fetch(path, {
    method: 'GET',
    credentials: 'same-origin',
    headers,
    cache: 'no-store'
  });
  const json = (await response.json().catch(() => null)) as { message?: string } | null;
  if (!response.ok) {
    throw new Error(json?.message ?? 'Management request failed.');
  }
  return json;
}

async function bootstrapSession(
  agentId: string,
  token: string
): Promise<{ ok: true } | { ok: false; message: string; code?: string; actionHint?: string }> {
  const response = await fetch('/api/v1/management/session/bootstrap', {
    method: 'POST',
    headers: {
      'content-type': 'application/json'
    },
    credentials: 'same-origin',
    body: JSON.stringify({ agentId, token })
  });

  if (!response.ok) {
    let message = 'Bootstrap failed. Verify token and retry.';
    let code: string | undefined;
    let actionHint: string | undefined;
    try {
      const payload = (await response.json()) as { message?: string; code?: string; actionHint?: string };
      if (payload?.message) {
        message = payload.message;
      }
      if (typeof payload?.code === 'string' && payload.code.trim()) {
        code = payload.code.trim();
      }
      if (typeof payload?.actionHint === 'string' && payload.actionHint.trim()) {
        actionHint = payload.actionHint.trim();
      }
    } catch {
      // no-op
    }
    return { ok: false, message, code, actionHint };
  }

  return { ok: true };
}

function usagePercent(current: number, maxRaw: string, enabled: boolean): number {
  if (!enabled) {
    return 0;
  }
  const max = Number(maxRaw);
  if (!Number.isFinite(max) || max <= 0) {
    return 0;
  }
  return Math.max(0, Math.min(100, (current / max) * 100));
}

function shortenHex(value: string | null | undefined, head = 8, tail = 6): string {
  if (!value) {
    return '—';
  }
  const raw = String(value);
  if (raw.length <= head + tail + 3) {
    return raw;
  }
  return `${raw.slice(0, head)}...${raw.slice(-tail)}`;
}

function policyApprovalLabel(item: { request_type: string; token_address: string | null }, chainTokens?: Array<{ symbol: string; address: string }>) {
  const map = tokenSymbolByAddress(chainTokens);

  if (item.request_type === 'global_approval_enable') {
    return 'Enable approve-all policy';
  }
  if (item.request_type === 'global_approval_disable') {
    return 'Disable approve-all policy';
  }
  if (item.request_type === 'token_preapprove_add') {
    if (!item.token_address) {
      return 'Preapprove token';
    }
    return `Preapprove ${map.get(item.token_address.toLowerCase()) ?? shortenAddress(item.token_address)}`;
  }
  if (item.request_type === 'token_preapprove_remove') {
    if (!item.token_address) {
      return 'Revoke preapproved token';
    }
    return `Revoke ${map.get(item.token_address.toLowerCase()) ?? shortenAddress(item.token_address)}`;
  }
  return item.request_type;
}

export default function AgentPublicProfilePage() {
  const params = useParams<{ agentId: string }>();
  const router = useRouter();
  const searchParams = useSearchParams();
  const agentId = params.agentId;
  const [activeChainKey, , activeChainLabel] = useActiveChainKey();

  const [bootstrapState, setBootstrapState] = useState<BootstrapState>({ phase: 'ready' });
  const [profile, setProfile] = useState<AgentProfilePayload | null>(null);
  const [trades, setTrades] = useState<TradePayload['items'] | null>(null);
  const [activity, setActivity] = useState<ActivityPayload['items'] | null>(null);
  const [management, setManagement] = useState<ManagementViewState>({ phase: 'loading' });
  const [error, setError] = useState<string | null>(null);
  const [managementNotice, setManagementNotice] = useState<string | null>(null);
  const [managementError, setManagementError] = useState<string | null>(null);

  const [depositData, setDepositData] = useState<DepositPayload | null>(null);
  const [limitOrders, setLimitOrders] = useState<LimitOrderItem[]>([]);
  const [copySubscriptions, setCopySubscriptions] = useState<CopySubscription[]>([]);

  const [activeTab, setActiveTab] = useState<PageTab>('overview');
  const [chartRange, setChartRange] = useState<TimeRange>('24h');
  const [approvalRejectReasons, setApprovalRejectReasons] = useState<Record<string, string>>({});

  const [withdrawDestination, setWithdrawDestination] = useState('');
  const [withdrawAmount, setWithdrawAmount] = useState('0.1');
  const [copyLeaderAgentId, setCopyLeaderAgentId] = useState('');
  const [copyScaleBps, setCopyScaleBps] = useState('10000');
  const [copyMaxTradeUsd, setCopyMaxTradeUsd] = useState('1000');

  const [outboundTransfersEnabled, setOutboundTransfersEnabled] = useState(false);
  const [outboundMode, setOutboundMode] = useState<'disabled' | 'allow_all' | 'whitelist'>('disabled');
  const [outboundWhitelistInput, setOutboundWhitelistInput] = useState('');
  const [policyApprovalMode, setPolicyApprovalMode] = useState<'per_trade' | 'auto'>('per_trade');
  const [policyMaxTradeUsd, setPolicyMaxTradeUsd] = useState('50');
  const [policyMaxDailyUsd, setPolicyMaxDailyUsd] = useState('250');
  const [policyDailyCapUsdEnabled, setPolicyDailyCapUsdEnabled] = useState(true);
  const [policyDailyTradeCapEnabled, setPolicyDailyTradeCapEnabled] = useState(true);
  const [policyMaxDailyTradeCount, setPolicyMaxDailyTradeCount] = useState('0');
  const [policyAllowedTokens, setPolicyAllowedTokens] = useState<string[]>([]);
  const [transferApprovalMode, setTransferApprovalMode] = useState<'auto' | 'per_transfer'>('per_transfer');
  const [transferNativePreapproved, setTransferNativePreapproved] = useState<boolean>(false);
  const [transferAllowedTokensText, setTransferAllowedTokensText] = useState<string>('');
  const [telegramApprovalsEnabled, setTelegramApprovalsEnabled] = useState(false);

  const isOwner = management.phase === 'ready';

  useEffect(() => {
    if (!agentId) {
      return;
    }

    const token = searchParams.get('token');
    if (!token) {
      setBootstrapState({ phase: 'ready' });
      return;
    }

    setBootstrapState({ phase: 'bootstrapping' });
    void bootstrapSession(agentId, token).then((result) => {
      if (!result.ok) {
        setBootstrapState({
          phase: 'error',
          message: result.message,
          code: result.code,
          actionHint: result.actionHint
        });
        return;
      }

      rememberManagedAgent(agentId);
      router.replace(`/agents/${agentId}`);
      setBootstrapState({ phase: 'ready' });
    });
  }, [agentId, router, searchParams]);

  const loadPublicData = useCallback(async () => {
    const [profileRes, tradesRes, activityRes] = await Promise.all([
      fetch(`/api/v1/public/agents/${agentId}`, { cache: 'no-store' }),
      fetch(`/api/v1/public/agents/${agentId}/trades?limit=30`, { cache: 'no-store' }),
      fetch(`/api/v1/public/activity?limit=30&agentId=${encodeURIComponent(agentId)}`, { cache: 'no-store' })
    ]);

    if (!profileRes.ok || !tradesRes.ok || !activityRes.ok) {
      throw new Error('Failed to load public profile data.');
    }

    const profilePayload = (await profileRes.json()) as AgentProfilePayload;
    const tradesPayload = (await tradesRes.json()) as TradePayload;
    const activityPayload = (await activityRes.json()) as ActivityPayload;

    setProfile(profilePayload);
    setTrades(tradesPayload.items);
    setActivity(activityPayload.items.slice(0, 20));
  }, [agentId]);

  const loadManagementData = useCallback(async () => {
    const managementRes = await fetch(
      `/api/v1/management/agent-state?agentId=${encodeURIComponent(agentId)}&chainKey=${encodeURIComponent(activeChainKey)}`,
      {
        cache: 'no-store',
        credentials: 'same-origin'
      }
    );

    if (managementRes.status === 401) {
      setManagement({ phase: 'unauthorized' });
      setDepositData(null);
      setLimitOrders([]);
      setCopySubscriptions([]);
      return;
    }

    if (!managementRes.ok) {
      const payload = (await managementRes.json().catch(() => null)) as { message?: string } | null;
      throw new Error(payload?.message ?? 'Failed to load management state.');
    }

    const payload = (await managementRes.json()) as ManagementStatePayload;
    setManagement({ phase: 'ready', data: payload });
    rememberManagedAgent(agentId);

    setOutboundTransfersEnabled(payload.outboundTransfersPolicy.outboundTransfersEnabled);
    setOutboundMode(payload.outboundTransfersPolicy.outboundMode);
    setOutboundWhitelistInput(payload.outboundTransfersPolicy.outboundWhitelistAddresses.join(','));
    setPolicyApprovalMode(payload.latestPolicy?.approval_mode ?? 'per_trade');
    setPolicyMaxTradeUsd(payload.latestPolicy?.max_trade_usd ?? '50');
    setPolicyMaxDailyUsd(payload.latestPolicy?.max_daily_usd ?? '250');
    setPolicyDailyCapUsdEnabled(payload.tradeCaps?.dailyCapUsdEnabled ?? payload.latestPolicy?.daily_cap_usd_enabled ?? true);
    setPolicyDailyTradeCapEnabled(payload.tradeCaps?.dailyTradeCapEnabled ?? payload.latestPolicy?.daily_trade_cap_enabled ?? true);
    setPolicyMaxDailyTradeCount(
      payload.tradeCaps?.maxDailyTradeCount !== null && payload.tradeCaps?.maxDailyTradeCount !== undefined
        ? String(payload.tradeCaps.maxDailyTradeCount)
        : (payload.latestPolicy?.max_daily_trade_count ?? '0')
    );
    setPolicyAllowedTokens(payload.latestPolicy?.allowed_tokens ?? []);
    setTransferApprovalMode(payload.transferApprovalPolicy?.transferApprovalMode ?? 'per_transfer');
    setTransferNativePreapproved(Boolean(payload.transferApprovalPolicy?.nativeTransferPreapproved));
    setTransferAllowedTokensText((payload.transferApprovalPolicy?.allowedTransferTokens ?? []).join(', '));
    setTelegramApprovalsEnabled(Boolean(payload.approvalChannels?.telegram?.enabled));

    const savedDestination =
      (payload.agent?.metadata as { management?: { withdrawDestinations?: Record<string, string> } } | undefined)?.management
        ?.withdrawDestinations?.[activeChainKey] ??
      (payload.agent?.metadata as { management?: { withdrawDestinations?: Record<string, string> } } | undefined)?.management
        ?.withdrawDestinations?.base_sepolia ??
      '';

    if (savedDestination) {
      setWithdrawDestination(savedDestination);
    }

    const [depositPayload, limitOrderPayload, copyPayload] = await Promise.all([
      managementGet(`/api/v1/management/deposit?agentId=${encodeURIComponent(agentId)}&chainKey=${encodeURIComponent(activeChainKey)}`),
      managementGet(`/api/v1/management/limit-orders?agentId=${encodeURIComponent(agentId)}&limit=50`),
      managementGet('/api/v1/copy/subscriptions')
    ]);

    setDepositData(depositPayload as DepositPayload);
    setLimitOrders(((limitOrderPayload as { items?: LimitOrderItem[] }).items ?? []).filter(Boolean));
    setCopySubscriptions(((copyPayload as CopySubscriptionsGetPayload).items ?? []).filter(Boolean));
  }, [activeChainKey, agentId]);

  const refreshAll = useCallback(async () => {
    setError(null);
    setManagementError(null);
    try {
      await loadPublicData();
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Failed to load public profile data.');
    }

    try {
      setManagement({ phase: 'loading' });
      await loadManagementData();
    } catch (loadError) {
      setManagement({
        phase: 'error',
        message: loadError instanceof Error ? loadError.message : 'Failed to load management state.'
      });
    }
  }, [loadManagementData, loadPublicData]);

  useEffect(() => {
    if (!agentId || bootstrapState.phase !== 'ready') {
      return;
    }
    void refreshAll();
  }, [agentId, bootstrapState.phase, refreshAll]);

  useEffect(() => {
    if (management.phase !== 'ready' || !agentId) {
      return;
    }
    const intervalId = window.setInterval(() => {
      void refreshAll();
    }, 5000);
    return () => {
      window.clearInterval(intervalId);
    };
  }, [management.phase, agentId, refreshAll]);

  async function runManagementAction(action: () => Promise<void>, successMessage: string) {
    setManagementError(null);
    setManagementNotice(null);
    try {
      await action();
      setManagementNotice(successMessage);
      await refreshAll();
    } catch (actionError) {
      setManagementError(actionError instanceof Error ? actionError.message : 'Management action failed.');
      await refreshAll();
    }
  }

  const chainTokenAddressBySymbol = useMemo(() => {
    const out: Record<string, string> = {};
    if (management.phase !== 'ready') {
      return out;
    }
    for (const entry of management.data.chainTokens ?? []) {
      const symbol = typeof entry?.symbol === 'string' ? entry.symbol.trim().toUpperCase() : '';
      const address = typeof entry?.address === 'string' ? entry.address.trim() : '';
      if (symbol && address) {
        out[symbol] = address;
      }
    }
    return out;
  }, [management]);

  const policyAllowedTokenSet = useMemo(
    () =>
      new Set(
        policyAllowedTokens
          .map((token) => String(token).trim().toLowerCase())
          .filter((token) => token.length > 0)
      ),
    [policyAllowedTokens]
  );

  function buildPolicyUpdatePayload(next: { approvalMode?: 'per_trade' | 'auto'; allowedTokens?: string[] }) {
    return {
      agentId,
      mode: 'real' as const,
      approvalMode: next.approvalMode ?? policyApprovalMode,
      maxTradeUsd: policyMaxTradeUsd,
      maxDailyUsd: policyMaxDailyUsd,
      dailyCapUsdEnabled: policyDailyCapUsdEnabled,
      dailyTradeCapEnabled: policyDailyTradeCapEnabled,
      maxDailyTradeCount: policyDailyTradeCapEnabled ? Number(policyMaxDailyTradeCount || '0') : null,
      allowedTokens: next.allowedTokens ?? policyAllowedTokens,
      outboundTransfersEnabled,
      outboundMode,
      outboundWhitelistAddresses: outboundWhitelistInput
        .split(',')
        .map((value) => value.trim())
        .filter((value) => value.length > 0)
    };
  }

  function isTokenPreapproved(symbol: string): boolean {
    const normalizedSymbol = symbol.trim().toUpperCase();
    const address = chainTokenAddressBySymbol[normalizedSymbol];
    if (address) {
      return policyAllowedTokenSet.has(address.toLowerCase());
    }
    return policyAllowedTokenSet.has(normalizedSymbol.toLowerCase());
  }

  function nextAllowedTokensForSymbol(symbol: string, enable: boolean): string[] {
    const normalizedSymbol = symbol.trim().toUpperCase();
    const address = chainTokenAddressBySymbol[normalizedSymbol]?.trim() ?? '';
    const current = policyAllowedTokens.map((token) => String(token).trim()).filter((token) => token.length > 0);

    const removeKeys = new Set<string>([normalizedSymbol.toLowerCase()]);
    if (address) {
      removeKeys.add(address.toLowerCase());
    }

    const cleaned = current.filter((token) => !removeKeys.has(token.toLowerCase()));
    if (!enable) {
      return cleaned;
    }
    if (address) {
      return [...cleaned, address];
    }
    return [...cleaned, normalizedSymbol];
  }

  const activeWallet = useMemo(
    () => profile?.wallets.find((wallet) => wallet.chain_key === activeChainKey) ?? profile?.wallets[0] ?? null,
    [profile, activeChainKey]
  );

  const activeDepositChain = useMemo(
    () => depositData?.chains.find((chain) => chain.chainKey === activeChainKey) ?? depositData?.chains[0] ?? null,
    [depositData, activeChainKey]
  );

  const holdings = useMemo(() => buildHoldings(profile, depositData, activeChainKey), [profile, depositData, activeChainKey]);
  const activityRows = useMemo(
    () => buildActivityRows(trades, activity, management.phase === 'ready' ? management.data.chainTokens : undefined),
    [trades, activity, management]
  );

  const filledTrades = useMemo(() => (trades ?? []).filter((trade) => trade.status === 'filled').length, [trades]);
  const winRate = useMemo(() => {
    const total = trades?.length ?? 0;
    if (total === 0) {
      return '—';
    }
    return `${((filledTrades / total) * 100).toFixed(1)}%`;
  }, [filledTrades, trades]);

  const status = profile?.agent.public_status;
  const heartbeatStale = profile?.agent.last_heartbeat_at
    ? isStale(profile.agent.last_heartbeat_at, HEARTBEAT_STALE_THRESHOLD_SECONDS)
    : true;

  if (bootstrapState.phase === 'bootstrapping') {
    return <main className={styles.loadingPage}>Validating management token...</main>;
  }

  if (bootstrapState.phase === 'error') {
    return (
      <main className={styles.errorPage}>
        <h1>Management bootstrap failed</h1>
        <p>{bootstrapState.message}</p>
        {bootstrapState.code ? <p>Code: {bootstrapState.code}</p> : null}
        {bootstrapState.actionHint ? <p>{bootstrapState.actionHint}</p> : null}
      </main>
    );
  }

  return (
    <div className={styles.root}>
      <aside className={styles.sidebar}>
        <div className={styles.logo}>X</div>
        <nav className={styles.nav}>
          <Link href="/dashboard" className={styles.navItem} aria-label="Dashboard" title="Dashboard">
            <SidebarIcon name="dashboard" />
          </Link>
          <Link href="/explore" className={`${styles.navItem} ${styles.navItemActive}`} aria-label="Explore" title="Explore">
            <SidebarIcon name="explore" />
          </Link>
          <Link href="/approvals" className={styles.navItem} aria-label="Approvals Center" title="Approvals Center">
            <SidebarIcon name="approvals" />
          </Link>
          <Link href="/settings" className={styles.navItem} aria-label="Settings & Security" title="Settings & Security">
            <SidebarIcon name="settings" />
          </Link>
        </nav>
      </aside>

      <section className={styles.surface}>
        <header className={styles.topbar}>
          <div className={styles.breadcrumb}>Wallet / Agents / {profile?.agent.agent_name ?? agentId}</div>
          <div className={styles.topControls}>
            <ChainHeaderControl />
            <ThemeToggle className={styles.themeButton} />
          </div>
        </header>

        {error ? <p className={styles.warningBanner}>{error}</p> : null}
        {managementNotice ? <p className={styles.successBanner}>{managementNotice}</p> : null}
        {managementError ? <p className={styles.warningBanner}>{managementError}</p> : null}

        <section className={styles.heroCard}>
          <div className={styles.heroIdentity}>
            <div className={styles.avatar}>{(profile?.agent.agent_name ?? 'A').slice(0, 1).toUpperCase()}</div>
            <div>
              <div className={styles.heroTitleRow}>
                <h1>{profile?.agent.agent_name ?? 'Loading agent...'}</h1>
                {status && isPublicStatus(status) ? <PublicStatusBadge status={status} /> : null}
                {!status ? <span className={styles.muted}>status unavailable</span> : null}
              </div>
              <div className={styles.heroMeta}>
                <span>{profile?.agent.runtime_platform ?? 'runtime unavailable'}</span>
                <span>Vault: {activeWallet ? shortenAddress(activeWallet.address) : '—'}</span>
                <span>Chain: {activeChainLabel}</span>
              </div>
              <div className={styles.heroTags}>
                <span>Arbitrage</span>
                <span>DeFi</span>
                <span>DEX</span>
                {heartbeatStale ? <span className={styles.warnTag}>degraded heartbeat</span> : <span className={styles.okTag}>heartbeat healthy</span>}
              </div>
            </div>
          </div>

          <div className={styles.heroActions}>
            {isOwner ? (
              <>
                <button type="button" onClick={() => setActiveTab('risk')}>
                  Deposit
                </button>
                <button type="button" onClick={() => setActiveTab('risk')}>
                  Withdraw
                </button>
                <button
                  type="button"
                  className={styles.dangerButton}
                  onClick={() =>
                    void runManagementAction(
                      () => managementPost('/api/v1/management/revoke-all', { agentId }).then(() => Promise.resolve()),
                      'Revoked management sessions and rotated owner token.'
                    )
                  }
                  disabled={!isOwner}
                >
                  Revoke All
                </button>
                <button type="button" onClick={() => setActiveTab('permissions')}>
                  Manage Approvals
                </button>
              </>
            ) : (
              <>
                <button type="button" disabled={!AGENT_PAGE_CAPABILITIES.watchApi}>
                  Watch
                </button>
                <button type="button" disabled={!AGENT_PAGE_CAPABILITIES.shareApi}>
                  Share
                </button>
                <button type="button" disabled={!AGENT_PAGE_CAPABILITIES.copyAgentLinkApi}>
                  Copy Agent Link
                </button>
              </>
            )}
          </div>
        </section>

        <section className={styles.kpiGrid}>
          <article className={styles.kpiCard}>
            <div className={styles.kpiLabel}>Lifetime PnL</div>
            <div className={styles.kpiValue}>{formatUsd(profile?.latestMetrics?.pnl_usd ?? null)}</div>
          </article>
          <article className={styles.kpiCard}>
            <div className={styles.kpiLabel}>24h Volume</div>
            <div className={styles.kpiValue}>{formatUsd(profile?.latestMetrics?.volume_usd ?? null)}</div>
          </article>
          <article className={styles.kpiCard}>
            <div className={styles.kpiLabel}>Win Rate</div>
            <div className={styles.kpiValue}>{winRate}</div>
          </article>
          <article className={styles.kpiCard}>
            <div className={styles.kpiLabel}>Fees Paid</div>
            <div className={styles.kpiValue}>—</div>
            <div className={styles.kpiHint}>Placeholder until dedicated fee metric API is added.</div>
          </article>
        </section>

        <section className={styles.tabs}>
          {([
            ['overview', 'Performance'],
            ['trades', 'Trades'],
            ['holdings', 'Holdings'],
            ['permissions', 'Permissions'],
            ['risk', 'Risk & Limits']
          ] as const).map(([key, label]) => (
            <button
              key={key}
              type="button"
              className={activeTab === key ? styles.tabActive : styles.tabButton}
              onClick={() => setActiveTab(key)}
            >
              {label}
            </button>
          ))}
        </section>

        <div className={styles.grid}>
          <div className={styles.mainCol}>
            {activeTab === 'overview' ? (
              <>
                <article className={styles.card}>
                  <div className={styles.cardHeader}>
                    <h2>Equity &amp; Volume</h2>
                    <div className={styles.rangeButtons}>
                      {(['1h', '24h', '7d', '30d'] as const).map((range) => (
                        <button
                          key={range}
                          type="button"
                          className={chartRange === range ? styles.rangeActive : styles.rangeButton}
                          onClick={() => setChartRange(range)}
                        >
                          {range.toUpperCase()}
                        </button>
                      ))}
                    </div>
                  </div>
                  <div className={styles.chartPlaceholder}>
                    <p>Chart uses current aggregate metrics. Full time-series API integration is planned for a follow-up slice.</p>
                  </div>
                  <div className={styles.cardFooterMeta}>
                    <span>Active DEXs: 3</span>
                    <span>Window: {chartRange.toUpperCase()}</span>
                  </div>
                </article>

                <article className={styles.card}>
                  <div className={styles.cardHeader}>
                    <h2>Recent Activity</h2>
                    <button type="button" onClick={() => setActiveTab('trades')}>
                      View all
                    </button>
                  </div>
                  {activityRows.length === 0 ? <p className={styles.muted}>No activity yet.</p> : null}
                  <div className={styles.list}>
                    {activityRows.slice(0, 10).map((row) => (
                      <div key={row.id} className={styles.listRow}>
                        <div>
                          <div className={styles.listTitle}>{row.title}</div>
                          <div className={styles.muted}>{row.subtitle}</div>
                        </div>
                        <div className={styles.listMeta}>
                          <span className={styles.statusChip}>{row.status}</span>
                          <span>{formatUtc(row.at)} UTC</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </article>

                <article className={styles.card}>
                  <div className={styles.cardHeader}>
                    <h2>Holdings</h2>
                    <button type="button" onClick={() => setActiveTab('holdings')}>
                      Manage
                    </button>
                  </div>
                  {holdings.length === 0 ? <p className={styles.muted}>No balances available yet.</p> : null}
                  {holdings.slice(0, 8).map((holding) => (
                    <div key={holding.token} className={styles.holdingRow}>
                      <span>{holding.token}</span>
                      <span>{formatUnitsTruncated(holding.amountRaw, holding.decimals, 4)}</span>
                    </div>
                  ))}
                </article>
              </>
            ) : null}

            {activeTab === 'trades' ? (
              <article className={styles.card}>
                <div className={styles.cardHeader}>
                  <h2>Trades</h2>
                  <span className={styles.muted}>Public execution history</span>
                </div>
                {(trades ?? []).length === 0 ? <p className={styles.muted}>No trades yet.</p> : null}
                {(trades ?? []).map((trade) => (
                  <div key={trade.trade_id} className={styles.listRow}>
                    <div>
                      <div className={styles.listTitle}>{trade.pair || `${trade.token_in} -> ${trade.token_out}`}</div>
                      <div className={styles.muted}>
                        {formatDecimalText(trade.amount_in)} in / {formatDecimalText(trade.amount_out)} out
                      </div>
                      {trade.tx_hash ? <div className={styles.muted}>Tx: {shortenHex(trade.tx_hash, 10, 8)}</div> : null}
                    </div>
                    <div className={styles.listMeta}>
                      <span className={styles.statusChip}>{trade.status}</span>
                      <span>{formatUtc(trade.created_at)} UTC</span>
                    </div>
                  </div>
                ))}
              </article>
            ) : null}

            {activeTab === 'holdings' ? (
              <article className={styles.card}>
                <div className={styles.cardHeader}>
                  <h2>Holdings &amp; Allowances</h2>
                  <span className={styles.muted}>{activeChainLabel}</span>
                </div>
                {holdings.length === 0 ? <p className={styles.muted}>No balances detected for this chain.</p> : null}
                {holdings.map((holding) => (
                  <div key={holding.token} className={styles.listRow}>
                    <div>
                      <div className={styles.listTitle}>{holding.token}</div>
                      <div className={styles.muted}>Balance in vault wallet</div>
                    </div>
                    <div className={styles.listMeta}>
                      <span>{formatUnitsTruncated(holding.amountRaw, holding.decimals, 6)}</span>
                      {isOwner ? (
                        <button
                          type="button"
                          onClick={() => {
                            const approved = isTokenPreapproved(holding.token);
                            const allowedTokens = nextAllowedTokensForSymbol(holding.token, !approved);
                            void runManagementAction(
                              () =>
                                managementPost('/api/v1/management/policy/update', buildPolicyUpdatePayload({ allowedTokens })).then(
                                  () => Promise.resolve()
                                ),
                              `${approved ? 'Removed' : 'Added'} ${holding.token} preapproval.`
                            );
                          }}
                        >
                          {isTokenPreapproved(holding.token) ? 'Preapproved' : 'Preapprove'}
                        </button>
                      ) : (
                        <span className={styles.muted}>Read-only</span>
                      )}
                    </div>
                  </div>
                ))}

                <div className={styles.placeholderPanel}>
                  <h3>Allowance Inventory</h3>
                  <p>
                    {AGENT_PAGE_CAPABILITIES.allowanceInventoryBySpender
                      ? 'Allowance inventory is enabled.'
                      : 'Detailed spender/utilization allowance inventory is placeholder-only until API support is added.'}
                  </p>
                </div>
              </article>
            ) : null}

            {activeTab === 'permissions' ? (
              <article className={styles.card}>
                <div className={styles.cardHeader}>
                  <h2>Permissions &amp; Approvals</h2>
                  <span className={styles.muted}>Owner-only controls</span>
                </div>

                {!isOwner ? <p className={styles.muted}>Owner-only approvals and permission controls are locked.</p> : null}

                {isOwner ? (
                  <>
                    <div className={styles.formGrid}>
                      <label>
                        Approval mode
                        <select value={policyApprovalMode} onChange={(event) => setPolicyApprovalMode(event.target.value as 'per_trade' | 'auto')}>
                          <option value="per_trade">Per trade</option>
                          <option value="auto">Approve all</option>
                        </select>
                      </label>
                      <label>
                        Max trade (USD)
                        <input value={policyMaxTradeUsd} onChange={(event) => setPolicyMaxTradeUsd(event.target.value)} />
                      </label>
                      <label>
                        Max daily (USD)
                        <input value={policyMaxDailyUsd} onChange={(event) => setPolicyMaxDailyUsd(event.target.value)} />
                      </label>
                      <label>
                        Max daily trade count
                        <input value={policyMaxDailyTradeCount} onChange={(event) => setPolicyMaxDailyTradeCount(event.target.value)} />
                      </label>
                    </div>

                    <div className={styles.toggleRow}>
                      <label>
                        <input
                          type="checkbox"
                          checked={policyDailyCapUsdEnabled}
                          onChange={(event) => setPolicyDailyCapUsdEnabled(event.target.checked)}
                        />
                        Daily USD cap enabled
                      </label>
                      <label>
                        <input
                          type="checkbox"
                          checked={policyDailyTradeCapEnabled}
                          onChange={(event) => setPolicyDailyTradeCapEnabled(event.target.checked)}
                        />
                        Daily trade count cap enabled
                      </label>
                    </div>

                    <button
                      type="button"
                      onClick={() =>
                        void runManagementAction(
                          () => managementPost('/api/v1/management/policy/update', buildPolicyUpdatePayload({})).then(() => Promise.resolve()),
                          'Policy updated.'
                        )
                      }
                    >
                      Save Policy
                    </button>

                    <div className={styles.subSection}>
                      <h3>Approval Queue</h3>
                      {management.data.approvalsQueue.length === 0 ? <p className={styles.muted}>No pending approvals.</p> : null}
                      {management.data.approvalsQueue.map((item) => {
                        const tokenMap = tokenSymbolByAddress(management.data.chainTokens);
                        const tokenIn = tokenMap.get(item.token_in.toLowerCase()) ?? shortenAddress(item.token_in);
                        const tokenOut = tokenMap.get(item.token_out.toLowerCase()) ?? shortenAddress(item.token_out);
                        return (
                          <div key={item.trade_id} className={styles.queueRow}>
                            <div>
                              <strong>
                                {formatDecimalText(item.amount_in)} {tokenIn} {'->'} {tokenOut}
                              </strong>
                              <div className={styles.muted}>{shortenHex(item.trade_id, 10, 8)}</div>
                              <div className={styles.muted}>{formatUtc(item.created_at)} UTC</div>
                            </div>
                            <div className={styles.queueActions}>
                              <input
                                value={approvalRejectReasons[item.trade_id] ?? ''}
                                onChange={(event) =>
                                  setApprovalRejectReasons((current) => ({
                                    ...current,
                                    [item.trade_id]: event.target.value
                                  }))
                                }
                                placeholder="Rejection reason (optional)"
                              />
                              <button
                                type="button"
                                onClick={() =>
                                  void runManagementAction(
                                    () =>
                                      managementPost('/api/v1/management/approvals/decision', {
                                        agentId,
                                        tradeId: item.trade_id,
                                        decision: 'approve'
                                      }).then(() => Promise.resolve()),
                                    `Approved ${item.trade_id}`
                                  )
                                }
                              >
                                Approve Once
                              </button>
                              <button
                                type="button"
                                className={styles.dangerButton}
                                onClick={() =>
                                  void runManagementAction(
                                    () =>
                                      managementPost('/api/v1/management/approvals/decision', {
                                        agentId,
                                        tradeId: item.trade_id,
                                        decision: 'reject',
                                        reasonCode: 'approval_rejected',
                                        reasonMessage:
                                          (approvalRejectReasons[item.trade_id] ?? '').trim() || 'Rejected by owner.'
                                      }).then(() => Promise.resolve()),
                                    `Rejected ${item.trade_id}`
                                  )
                                }
                              >
                                Reject
                              </button>
                            </div>
                          </div>
                        );
                      })}
                    </div>

                    <div className={styles.subSection}>
                      <h3>Policy Approval Requests</h3>
                      {(management.data.policyApprovalsQueue ?? []).length === 0 ? (
                        <p className={styles.muted}>No pending policy approvals.</p>
                      ) : null}
                      {(management.data.policyApprovalsQueue ?? []).map((item) => (
                        <div key={item.request_id} className={styles.queueRow}>
                          <div>
                            <strong>{policyApprovalLabel(item, management.data.chainTokens)}</strong>
                            <div className={styles.muted}>{shortenHex(item.request_id, 10, 8)}</div>
                            <div className={styles.muted}>{formatUtc(item.created_at)} UTC</div>
                          </div>
                          <div className={styles.queueActions}>
                            <input
                              value={approvalRejectReasons[item.request_id] ?? ''}
                              onChange={(event) =>
                                setApprovalRejectReasons((current) => ({
                                  ...current,
                                  [item.request_id]: event.target.value
                                }))
                              }
                              placeholder="Rejection reason (optional)"
                            />
                            <button
                              type="button"
                              onClick={() =>
                                void runManagementAction(
                                  () =>
                                    managementPost('/api/v1/management/policy-approvals/decision', {
                                      agentId,
                                      policyApprovalId: item.request_id,
                                      decision: 'approve'
                                    }).then(() => Promise.resolve()),
                                  `Approved ${item.request_id}`
                                )
                              }
                            >
                              Approve
                            </button>
                            <button
                              type="button"
                              className={styles.dangerButton}
                              onClick={() =>
                                void runManagementAction(
                                  () =>
                                    managementPost('/api/v1/management/policy-approvals/decision', {
                                      agentId,
                                      policyApprovalId: item.request_id,
                                      decision: 'reject',
                                      reasonMessage:
                                        (approvalRejectReasons[item.request_id] ?? '').trim() || 'Rejected by owner.'
                                    }).then(() => Promise.resolve()),
                                  `Rejected ${item.request_id}`
                                )
                              }
                            >
                              Deny
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </>
                ) : null}
              </article>
            ) : null}

            {activeTab === 'risk' ? (
              <article className={styles.card}>
                <div className={styles.cardHeader}>
                  <h2>Risk, Limits, and Operations</h2>
                  <span className={styles.muted}>Owner operations console</span>
                </div>

                {!isOwner ? <p className={styles.muted}>Owner-only management controls are locked.</p> : null}

                {isOwner ? (
                  <>
                    <div className={styles.subSection}>
                      <h3>Runtime and Chain Access</h3>
                      <div className={styles.toggleRow}>
                        <button
                          type="button"
                          onClick={() =>
                            void runManagementAction(
                              () => managementPost('/api/v1/management/pause', { agentId }).then(() => Promise.resolve()),
                              'Agent paused.'
                            )
                          }
                        >
                          Pause Agent
                        </button>
                        <button
                          type="button"
                          onClick={() =>
                            void runManagementAction(
                              () => managementPost('/api/v1/management/resume', { agentId }).then(() => Promise.resolve()),
                              'Agent resumed.'
                            )
                          }
                        >
                          Resume Agent
                        </button>
                        <label>
                          <input
                            type="checkbox"
                            checked={management.data.chainPolicy?.chainEnabled}
                            onChange={(event) =>
                              void runManagementAction(
                                () =>
                                  managementPost('/api/v1/management/chains/update', {
                                    agentId,
                                    chainKey: activeChainKey,
                                    chainEnabled: event.target.checked
                                  }).then(() => Promise.resolve()),
                                event.target.checked ? 'Chain access enabled.' : 'Chain access disabled.'
                              )
                            }
                          />
                          Chain enabled ({activeChainLabel})
                        </label>
                      </div>
                    </div>

                    <div className={styles.subSection}>
                      <h3>Deposit &amp; Withdraw</h3>
                      <p className={styles.muted}>
                        Deposit address: {activeDepositChain?.depositAddress ? shortenAddress(activeDepositChain.depositAddress) : 'unavailable'}
                      </p>
                      <div className={styles.formGrid}>
                        <label>
                          Withdraw destination
                          <input value={withdrawDestination} onChange={(event) => setWithdrawDestination(event.target.value)} />
                        </label>
                        <label>
                          Withdraw amount (ETH)
                          <input value={withdrawAmount} onChange={(event) => setWithdrawAmount(event.target.value)} />
                        </label>
                      </div>
                      <div className={styles.toggleRow}>
                        <button
                          type="button"
                          onClick={() =>
                            void runManagementAction(
                              () =>
                                managementPost('/api/v1/management/withdraw/destination', {
                                  agentId,
                                  chainKey: activeChainKey,
                                  destination: withdrawDestination
                                }).then(() => Promise.resolve()),
                              'Withdraw destination updated.'
                            )
                          }
                        >
                          Save Destination
                        </button>
                        <button
                          type="button"
                          onClick={() =>
                            void runManagementAction(
                              () =>
                                managementPost('/api/v1/management/withdraw', {
                                  agentId,
                                  chainKey: activeChainKey,
                                  asset: 'NATIVE',
                                  amount: withdrawAmount,
                                  destination: withdrawDestination
                                }).then(() => Promise.resolve()),
                              'Withdraw request submitted.'
                            )
                          }
                        >
                          Submit Withdraw
                        </button>
                      </div>
                    </div>

                    <div className={styles.subSection}>
                      <h3>Outbound Transfer Policy</h3>
                      <div className={styles.toggleRow}>
                        <label>
                          <input
                            type="checkbox"
                            checked={outboundTransfersEnabled}
                            onChange={(event) => setOutboundTransfersEnabled(event.target.checked)}
                          />
                          Outbound transfers enabled
                        </label>
                        <label>
                          Mode
                          <select value={outboundMode} onChange={(event) => setOutboundMode(event.target.value as 'disabled' | 'allow_all' | 'whitelist')}>
                            <option value="disabled">disabled</option>
                            <option value="allow_all">allow_all</option>
                            <option value="whitelist">whitelist</option>
                          </select>
                        </label>
                      </div>
                      <label>
                        Whitelist addresses (comma-separated)
                        <input value={outboundWhitelistInput} onChange={(event) => setOutboundWhitelistInput(event.target.value)} />
                      </label>
                      <button
                        type="button"
                        onClick={() =>
                          void runManagementAction(
                            () => managementPost('/api/v1/management/policy/update', buildPolicyUpdatePayload({})).then(() => Promise.resolve()),
                            'Outbound policy saved.'
                          )
                        }
                      >
                        Save Outbound Policy
                      </button>
                    </div>

                    <div className={styles.subSection}>
                      <h3>Transfer Approval Policy</h3>
                      <div className={styles.toggleRow}>
                        <label>
                          <input
                            type="checkbox"
                            checked={transferApprovalMode === 'auto'}
                            onChange={(event) => setTransferApprovalMode(event.target.checked ? 'auto' : 'per_transfer')}
                          />
                          Auto-approve transfers
                        </label>
                        <label>
                          <input
                            type="checkbox"
                            checked={transferNativePreapproved}
                            disabled={transferApprovalMode === 'auto'}
                            onChange={(event) => setTransferNativePreapproved(event.target.checked)}
                          />
                          Native preapproved
                        </label>
                      </div>
                      <label>
                        Allowed transfer tokens (comma-separated 0x addresses)
                        <input value={transferAllowedTokensText} onChange={(event) => setTransferAllowedTokensText(event.target.value)} />
                      </label>
                      <button
                        type="button"
                        onClick={() =>
                          void runManagementAction(
                            () =>
                              managementPost('/api/v1/management/transfer-policy/update', {
                                agentId,
                                chainKey: activeChainKey,
                                transferApprovalMode,
                                nativeTransferPreapproved: transferNativePreapproved,
                                allowedTransferTokens: transferAllowedTokensText
                                  .split(',')
                                  .map((value) => value.trim().toLowerCase())
                                  .filter((value) => /^0x[a-f0-9]{40}$/.test(value))
                              }).then(() => Promise.resolve()),
                            'Transfer approval policy updated.'
                          )
                        }
                      >
                        Save Transfer Approval Policy
                      </button>
                    </div>

                    <div className={styles.subSection}>
                      <h3>Transfer Approvals</h3>
                      {(management.data.transferApprovalsQueue ?? []).length === 0 ? (
                        <p className={styles.muted}>No pending transfer approvals.</p>
                      ) : null}
                      {(management.data.transferApprovalsQueue ?? []).map((item) => (
                        <div key={item.approval_id} className={styles.queueRow}>
                          <div>
                            <strong>
                              {item.amount_wei} {item.transfer_type === 'native' ? 'ETH' : item.token_symbol ?? shortenAddress(item.token_address ?? '')}
                            </strong>
                            <div className={styles.muted}>To: {shortenAddress(item.to_address)}</div>
                            <div className={styles.muted}>{shortenHex(item.approval_id, 10, 8)}</div>
                            {item.policy_blocked_at_create ? <div className={styles.muted}>Policy blocked at create</div> : null}
                          </div>
                          <div className={styles.queueActions}>
                            <input
                              value={approvalRejectReasons[item.approval_id] ?? ''}
                              onChange={(event) =>
                                setApprovalRejectReasons((current) => ({
                                  ...current,
                                  [item.approval_id]: event.target.value
                                }))
                              }
                              placeholder="Rejection reason (optional)"
                            />
                            <button
                              type="button"
                              onClick={() =>
                                void runManagementAction(
                                  () =>
                                    managementPost('/api/v1/management/transfer-approvals/decision', {
                                      agentId,
                                      approvalId: item.approval_id,
                                      decision: 'approve',
                                      chainKey: item.chain_key
                                    }).then(() => Promise.resolve()),
                                  `Approved ${item.approval_id}`
                                )
                              }
                            >
                              Approve
                            </button>
                            <button
                              type="button"
                              className={styles.dangerButton}
                              onClick={() =>
                                void runManagementAction(
                                  () =>
                                    managementPost('/api/v1/management/transfer-approvals/decision', {
                                      agentId,
                                      approvalId: item.approval_id,
                                      decision: 'deny',
                                      chainKey: item.chain_key,
                                      reasonMessage:
                                        (approvalRejectReasons[item.approval_id] ?? '').trim() || 'Rejected by owner.'
                                    }).then(() => Promise.resolve()),
                                  `Denied ${item.approval_id}`
                                )
                              }
                            >
                              Deny
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>

                    <div className={styles.subSection}>
                      <h3>Telegram Approval Channel</h3>
                      <label>
                        <input
                          type="checkbox"
                          checked={telegramApprovalsEnabled}
                          onChange={(event) => {
                            const next = event.target.checked;
                            void runManagementAction(
                              () =>
                                managementPost('/api/v1/management/approval-channels/update', {
                                  agentId,
                                  chainKey: activeChainKey,
                                  channel: 'telegram',
                                  enabled: next
                                }).then(() => Promise.resolve()),
                              `Telegram approvals ${next ? 'enabled' : 'disabled'}.`
                            );
                          }}
                        />
                        Telegram approvals enabled
                      </label>
                    </div>

                    <div className={styles.subSection}>
                      <h3>Daily Usage</h3>
                      <div className={styles.usageRow}>
                        <span>
                          Daily spend: {formatUsd(management.data.dailyUsage.dailySpendUsd)} /{' '}
                          {policyDailyCapUsdEnabled ? formatUsd(policyMaxDailyUsd) : 'No cap'}
                        </span>
                        <div className={styles.usageBar}>
                          <span
                            className={styles.usageFill}
                            style={{
                              width: `${usagePercent(
                                Number(management.data.dailyUsage.dailySpendUsd),
                                policyMaxDailyUsd,
                                policyDailyCapUsdEnabled
                              )}%`
                            }}
                          />
                        </div>
                      </div>
                      <div className={styles.usageRow}>
                        <span>
                          Daily filled trades: {management.data.dailyUsage.dailyFilledTrades} /{' '}
                          {policyDailyTradeCapEnabled ? policyMaxDailyTradeCount : 'No cap'}
                        </span>
                        <div className={styles.usageBar}>
                          <span
                            className={styles.usageFill}
                            style={{
                              width: `${usagePercent(
                                management.data.dailyUsage.dailyFilledTrades,
                                policyMaxDailyTradeCount,
                                policyDailyTradeCapEnabled
                              )}%`
                            }}
                          />
                        </div>
                      </div>
                    </div>

                    <div className={styles.subSection}>
                      <h3>Limit Orders</h3>
                      {limitOrders.length === 0 ? <p className={styles.muted}>No limit orders.</p> : null}
                      {limitOrders.map((item) => (
                        <div key={item.orderId} className={styles.queueRow}>
                          <div>
                            <strong>
                              {item.side.toUpperCase()} {item.amountIn}
                            </strong>
                            <div className={styles.muted}>{item.chainKey}</div>
                            <div className={styles.muted}>
                              {shortenAddress(item.tokenIn)} {'->'} {shortenAddress(item.tokenOut)} @ {item.limitPrice}
                            </div>
                          </div>
                          {(item.status === 'open' || item.status === 'triggered') && (
                            <button
                              type="button"
                              onClick={() =>
                                void runManagementAction(
                                  () =>
                                    managementPost(`/api/v1/management/limit-orders/${item.orderId}/cancel`, { agentId }).then(() =>
                                      Promise.resolve()
                                    ),
                                  `Cancelled ${item.orderId}`
                                )
                              }
                            >
                              Cancel
                            </button>
                          )}
                        </div>
                      ))}
                    </div>

                    <div className={styles.subSection}>
                      <h3>Management Audit Log</h3>
                      {management.data.auditLog.length === 0 ? <p className={styles.muted}>No audit entries.</p> : null}
                      {management.data.auditLog.map((entry) => (
                        <div key={entry.audit_id} className={styles.listRow}>
                          <div>
                            <div className={styles.listTitle}>
                              {entry.action_type} ({entry.action_status})
                            </div>
                          </div>
                          <div className={styles.listMeta}>{formatUtc(entry.created_at)} UTC</div>
                        </div>
                      ))}
                    </div>
                  </>
                ) : null}
              </article>
            ) : null}
          </div>

          <aside className={styles.railCol}>
            <article className={styles.card}>
              <div className={styles.cardHeader}>
                <h3>Pending Approval Requests</h3>
                <span>{isOwner ? management.phase === 'ready' ? management.data.approvalsQueue.length : '—' : 'locked'}</span>
              </div>
              {!isOwner ? (
                <p className={styles.muted}>Owner-only approvals and withdrawals are locked for viewers.</p>
              ) : null}
              {isOwner && management.phase === 'ready' && management.data.approvalsQueue.length === 0 ? (
                <p className={styles.muted}>No pending approvals. Agent is operating within limits.</p>
              ) : null}
              {isOwner && management.phase === 'ready'
                ? management.data.approvalsQueue.slice(0, 3).map((item) => (
                    <div key={item.trade_id} className={styles.railQueueRow}>
                      <div>
                        <div className={styles.listTitle}>{item.pair || `${item.token_in} -> ${item.token_out}`}</div>
                        <div className={styles.muted}>{item.reason ?? 'Approval required by policy'}</div>
                      </div>
                      <div className={styles.inlineActions}>
                        <button
                          type="button"
                          onClick={() =>
                            void runManagementAction(
                              () =>
                                managementPost('/api/v1/management/approvals/decision', {
                                  agentId,
                                  tradeId: item.trade_id,
                                  decision: 'approve'
                                }).then(() => Promise.resolve()),
                              `Approved ${item.trade_id}`
                            )
                          }
                        >
                          Approve Once
                        </button>
                        <button
                          type="button"
                          className={styles.dangerButton}
                          onClick={() =>
                            void runManagementAction(
                              () =>
                                managementPost('/api/v1/management/approvals/decision', {
                                  agentId,
                                  tradeId: item.trade_id,
                                  decision: 'reject',
                                  reasonCode: 'approval_rejected',
                                  reasonMessage: 'Rejected by owner.'
                                }).then(() => Promise.resolve()),
                              `Rejected ${item.trade_id}`
                            )
                          }
                        >
                          Reject
                        </button>
                      </div>
                    </div>
                  ))
                : null}
              <div className={styles.placeholderLine}>
                {AGENT_PAGE_CAPABILITIES.approvalRiskChips
                  ? 'Risk chips enabled'
                  : 'Risk chips, gas estimate, and route details are placeholder-only until API support is added.'}
              </div>
            </article>

            <article className={styles.card}>
              <div className={styles.cardHeader}>
                <h3>Copy Trading</h3>
                <span>{isOwner ? `${copySubscriptions.length} active` : 'viewer'}</span>
              </div>
              {!isOwner ? <p className={styles.muted}>Copy this agent from one of your owned agents after owner session bootstrap.</p> : null}
              {isOwner ? (
                <>
                  {copySubscriptions.length === 0 ? <p className={styles.muted}>No copy subscriptions configured.</p> : null}
                  {copySubscriptions.map((item) => (
                    <div key={item.subscriptionId} className={styles.railQueueRow}>
                      <div>
                        <div className={styles.listTitle}>Leader: {item.leaderAgentId}</div>
                        <div className={styles.muted}>
                          {item.enabled ? 'active' : 'paused'} · scale {(item.scaleBps / 10000).toFixed(2)}x · max {item.maxTradeUsd ?? '—'}
                        </div>
                      </div>
                      <div className={styles.inlineActions}>
                        <button
                          type="button"
                          onClick={() =>
                            void runManagementAction(
                              () =>
                                fetch(`/api/v1/copy/subscriptions/${encodeURIComponent(item.subscriptionId)}`, {
                                  method: 'PATCH',
                                  credentials: 'same-origin',
                                  headers: {
                                    'content-type': 'application/json',
                                    ...(getCsrfToken() ? { 'x-csrf-token': getCsrfToken() as string } : {})
                                  },
                                  body: JSON.stringify({ enabled: !item.enabled })
                                }).then((res) => {
                                  if (!res.ok) {
                                    throw new Error('Failed to update copy subscription.');
                                  }
                                  return Promise.resolve();
                                }),
                              `Copy subscription ${item.enabled ? 'paused' : 'resumed'}.`
                            )
                          }
                        >
                          {item.enabled ? 'Pause' : 'Resume'}
                        </button>
                      </div>
                    </div>
                  ))}

                  <div className={styles.subSection}>
                    <h4>Enable Copy Relationship</h4>
                    <div className={styles.formGridCompact}>
                      <label>
                        Leader agent id
                        <input value={copyLeaderAgentId} onChange={(event) => setCopyLeaderAgentId(event.target.value)} placeholder="leader agent id" />
                      </label>
                      <label>
                        Scale bps
                        <input value={copyScaleBps} onChange={(event) => setCopyScaleBps(event.target.value)} />
                      </label>
                      <label>
                        Max trade USD
                        <input value={copyMaxTradeUsd} onChange={(event) => setCopyMaxTradeUsd(event.target.value)} />
                      </label>
                    </div>
                    <button
                      type="button"
                      onClick={() =>
                        void runManagementAction(
                          () =>
                            fetch('/api/v1/copy/subscriptions', {
                              method: 'POST',
                              credentials: 'same-origin',
                              headers: {
                                'content-type': 'application/json',
                                ...(getCsrfToken() ? { 'x-csrf-token': getCsrfToken() as string } : {})
                              },
                              body: JSON.stringify({
                                leaderAgentId: copyLeaderAgentId.trim(),
                                followerAgentId: agentId,
                                enabled: true,
                                scaleBps: Number(copyScaleBps || '10000'),
                                maxTradeUsd: copyMaxTradeUsd,
                                allowedTokens: []
                              })
                            }).then((res) => {
                              if (!res.ok) {
                                throw new Error('Failed to create copy subscription.');
                              }
                              return Promise.resolve();
                            }),
                          'Copy subscription saved.'
                        )
                      }
                    >
                      Save Copy Trading
                    </button>
                  </div>
                </>
              ) : null}
            </article>

            <article className={styles.card}>
              <div className={styles.cardHeader}>
                <h3>Permissions Highlights</h3>
                {isOwner ? <button onClick={() => setActiveTab('permissions')}>Manage</button> : null}
              </div>
              {isOwner && management.phase === 'ready' ? (
                <div className={styles.keyValueList}>
                  <div>
                    <span>Global approval</span>
                    <span>{management.data.latestPolicy?.approval_mode === 'auto' ? 'On' : 'Off'}</span>
                  </div>
                  <div>
                    <span>Allowlist tokens</span>
                    <span>{management.data.latestPolicy?.allowed_tokens.length ?? 0}</span>
                  </div>
                  <div>
                    <span>Transfer approval mode</span>
                    <span>{management.data.transferApprovalPolicy?.transferApprovalMode ?? 'per_transfer'}</span>
                  </div>
                  <div>
                    <span>Chain access</span>
                    <span>{management.data.chainPolicy.chainEnabled ? 'enabled' : 'disabled'}</span>
                  </div>
                </div>
              ) : (
                <p className={styles.muted}>Viewer posture summary only. Owner controls are locked.</p>
              )}
            </article>

            <article className={styles.card}>
              <div className={styles.cardHeader}>
                <h3>Quick Limits</h3>
                {isOwner ? <button onClick={() => setActiveTab('risk')}>Edit</button> : null}
              </div>
              <div className={styles.keyValueList}>
                <div>
                  <span>Daily spend cap</span>
                  <span>{policyDailyCapUsdEnabled ? formatUsd(policyMaxDailyUsd) : 'Disabled'}</span>
                </div>
                <div>
                  <span>Max trade</span>
                  <span>{formatUsd(policyMaxTradeUsd)}</span>
                </div>
                <div>
                  <span>Allowed chains</span>
                  <span>{activeChainLabel}</span>
                </div>
                <div>
                  <span>Session</span>
                  <span>{isOwner && management.phase === 'ready' ? `expires ${formatUtc(management.data.managementSession.expiresAt)}` : 'viewer'}</span>
                </div>
              </div>
            </article>
          </aside>
        </div>
      </section>
    </div>
  );
}
