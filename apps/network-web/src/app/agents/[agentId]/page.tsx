'use client';

import Image from 'next/image';
import Link from 'next/link';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
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

type WalletActivityFilter = 'all' | 'trades' | 'transfers' | 'approvals' | 'deposits';
type ApprovalStatusFilter = 'all' | 'pending' | 'approved' | 'rejected';

type WalletTimelineItem = {
  id: string;
  at: string;
  kind: WalletActivityFilter;
  title: string;
  subtitle: string;
  status: string;
  txHash: string | null;
};

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
  const [depositAddressCopied, setDepositAddressCopied] = useState(false);
  const depositCopyResetTimerRef = useRef<number | null>(null);

  const [walletActivityFilter, setWalletActivityFilter] = useState<WalletActivityFilter>('all');
  const [approvalStatusFilter, setApprovalStatusFilter] = useState<ApprovalStatusFilter>('all');
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

  async function copyToClipboard(value: string, successMessage: string, onSuccess?: () => void) {
    setManagementError(null);
    try {
      await navigator.clipboard.writeText(value);
      setManagementNotice(successMessage);
      onSuccess?.();
    } catch {
      setManagementError('Copy failed. Copy the address manually.');
    }
  }

  useEffect(() => {
    return () => {
      if (depositCopyResetTimerRef.current !== null) {
        window.clearTimeout(depositCopyResetTimerRef.current);
      }
    };
  }, []);

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
  const walletTimeline = useMemo(() => {
    const items: WalletTimelineItem[] = [];
    for (const row of activityRows) {
      items.push({
        id: `act-${row.id}`,
        at: row.at,
        kind: 'trades',
        title: row.title,
        subtitle: row.subtitle,
        status: row.status,
        txHash: null
      });
    }

    for (const deposit of activeDepositChain?.recentDeposits ?? []) {
      items.push({
        id: `dep-${deposit.txHash}-${deposit.blockNumber}`,
        at: deposit.confirmedAt,
        kind: 'deposits',
        title: `Deposit ${deposit.amount} ${deposit.token}`,
        subtitle: `Block ${deposit.blockNumber}`,
        status: deposit.status || 'confirmed',
        txHash: deposit.txHash ?? null
      });
    }

    if (management.phase === 'ready') {
      for (const item of management.data.transferApprovalsHistory ?? []) {
        items.push({
          id: `xfrh-${item.approval_id}`,
          at: item.terminal_at ?? item.decided_at ?? item.created_at,
          kind: 'transfers',
          title: `${item.transfer_type === 'native' ? 'ETH' : item.token_symbol ?? 'Token'} transfer`,
          subtitle: `${item.amount_wei} wei to ${shortenAddress(item.to_address)}`,
          status: item.status,
          txHash: item.tx_hash
        });
      }
      for (const item of management.data.transferApprovalsQueue ?? []) {
        items.push({
          id: `xfrq-${item.approval_id}`,
          at: item.created_at,
          kind: 'transfers',
          title: `Pending transfer approval`,
          subtitle: `${item.amount_wei} wei to ${shortenAddress(item.to_address)}`,
          status: item.status,
          txHash: null
        });
      }
      for (const item of management.data.policyApprovalsHistory ?? []) {
        items.push({
          id: `polh-${item.request_id}`,
          at: item.decided_at ?? item.created_at,
          kind: 'approvals',
          title: policyApprovalLabel(item, management.data.chainTokens),
          subtitle: item.reason_message ? item.reason_message : 'Policy approval decision',
          status: item.status,
          txHash: null
        });
      }
      for (const item of management.data.policyApprovalsQueue ?? []) {
        items.push({
          id: `polq-${item.request_id}`,
          at: item.created_at,
          kind: 'approvals',
          title: policyApprovalLabel(item, management.data.chainTokens),
          subtitle: 'Pending policy approval',
          status: 'pending',
          txHash: null
        });
      }
      for (const item of management.data.approvalsQueue) {
        items.push({
          id: `trdapp-${item.trade_id}`,
          at: item.created_at,
          kind: 'approvals',
          title: item.pair || `${item.token_in} -> ${item.token_out}`,
          subtitle: item.reason ?? 'Pending trade approval',
          status: 'pending',
          txHash: null
        });
      }
    }

    items.sort((a, b) => {
      const atA = Number(new Date(a.at).getTime());
      const atB = Number(new Date(b.at).getTime());
      return atB - atA;
    });
    return items;
  }, [activityRows, activeDepositChain?.recentDeposits, management]);

  const filteredWalletTimeline = useMemo(() => {
    if (walletActivityFilter === 'all') {
      return walletTimeline;
    }
    return walletTimeline.filter((item) => item.kind === walletActivityFilter);
  }, [walletActivityFilter, walletTimeline]);

  const approvalHistoryItems = useMemo(() => {
    if (management.phase !== 'ready') {
      return [] as Array<{ id: string; at: string; title: string; status: string; subtitle: string; type: 'trade' | 'policy' | 'transfer'; raw: any }>;
    }
    const rows: Array<{ id: string; at: string; title: string; status: string; subtitle: string; type: 'trade' | 'policy' | 'transfer'; raw: any }> = [];
    for (const item of management.data.approvalsQueue) {
      rows.push({
        id: `trade-${item.trade_id}`,
        at: item.created_at,
        title: item.pair || `${item.token_in} -> ${item.token_out}`,
        status: 'pending',
        subtitle: item.reason ?? 'Pending trade approval',
        type: 'trade',
        raw: item
      });
    }
    for (const item of management.data.policyApprovalsQueue ?? []) {
      rows.push({
        id: `policy-pending-${item.request_id}`,
        at: item.created_at,
        title: policyApprovalLabel(item, management.data.chainTokens),
        status: 'pending',
        subtitle: 'Pending policy approval',
        type: 'policy',
        raw: item
      });
    }
    for (const item of management.data.policyApprovalsHistory ?? []) {
      rows.push({
        id: `policy-history-${item.request_id}`,
        at: item.decided_at ?? item.created_at,
        title: policyApprovalLabel(item, management.data.chainTokens),
        status: item.status,
        subtitle: item.reason_message || 'Policy approval history',
        type: 'policy',
        raw: item
      });
    }
    for (const item of management.data.transferApprovalsQueue ?? []) {
      rows.push({
        id: `transfer-pending-${item.approval_id}`,
        at: item.created_at,
        title: `Transfer to ${shortenAddress(item.to_address)}`,
        status: item.status,
        subtitle: `${item.amount_wei} wei`,
        type: 'transfer',
        raw: item
      });
    }
    for (const item of management.data.transferApprovalsHistory ?? []) {
      rows.push({
        id: `transfer-history-${item.approval_id}`,
        at: item.terminal_at ?? item.decided_at ?? item.created_at,
        title: `Transfer to ${shortenAddress(item.to_address)}`,
        status: item.status,
        subtitle: `${item.amount_wei} wei`,
        type: 'transfer',
        raw: item
      });
    }
    rows.sort((a, b) => Number(new Date(b.at).getTime()) - Number(new Date(a.at).getTime()));
    return rows;
  }, [management]);

  const filteredApprovalHistory = useMemo(() => {
    if (approvalStatusFilter === 'all') {
      return approvalHistoryItems;
    }
    if (approvalStatusFilter === 'pending') {
      return approvalHistoryItems.filter((row) => row.status === 'pending' || row.status === 'approval_pending');
    }
    if (approvalStatusFilter === 'approved') {
      return approvalHistoryItems.filter((row) => row.status === 'approved');
    }
    return approvalHistoryItems.filter((row) => row.status === 'rejected' || row.status === 'deny' || row.status === 'denied');
  }, [approvalHistoryItems, approvalStatusFilter]);

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
        <Link href="/dashboard" className={styles.sidebarLogo} aria-label="X-Claw dashboard">
          <Image src="/X-Claw-Logo.png" alt="X-Claw" width={900} height={280} className={styles.sidebarLogoImage} priority />
        </Link>
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
                <button type="button" onClick={() => document.getElementById('wallet-controls')?.scrollIntoView({ behavior: 'smooth' })}>
                  Wallet Controls
                </button>
                <button type="button" onClick={() => document.getElementById('approval-history')?.scrollIntoView({ behavior: 'smooth' })}>
                  Approval History
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

        <div className={styles.grid}>
          <div className={styles.mainCol}>
            <article id="wallet-controls" className={styles.card}>
              <div className={styles.cardHeader}>
                <h2>Wallet Controls</h2>
                <span className={styles.muted}>{activeChainLabel}</span>
              </div>
              {!isOwner ? <p className={styles.muted}>Owner-only controls are locked for viewers.</p> : null}
              {isOwner && management.phase === 'ready' ? (
                <>
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
                      Chain enabled
                    </label>
                  </div>

                  <div className={styles.subSection}>
                    <h3>Deposit &amp; Withdraw</h3>
                    {activeDepositChain?.depositAddress ? (
                      <button
                        type="button"
                        className={`${styles.addressCopyButton} ${depositAddressCopied ? styles.addressCopyButtonActive : ''}`}
                        onClick={() =>
                          void copyToClipboard(activeDepositChain.depositAddress, 'Deposit address copied.', () => {
                            setDepositAddressCopied(true);
                            if (depositCopyResetTimerRef.current !== null) {
                              window.clearTimeout(depositCopyResetTimerRef.current);
                            }
                            depositCopyResetTimerRef.current = window.setTimeout(() => {
                              setDepositAddressCopied(false);
                              depositCopyResetTimerRef.current = null;
                            }, 1000);
                          })
                        }
                        title="Click to copy full deposit address"
                      >
                        <span className={styles.addressCopyHeader}>
                          <span className={styles.muted}>Deposit address</span>
                          <span className={styles.copyIcon} aria-hidden="true">
                            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" xmlns="http://www.w3.org/2000/svg">
                              <path
                                d="M9 9.75A2.25 2.25 0 0 1 11.25 7.5h6A2.25 2.25 0 0 1 19.5 9.75v6A2.25 2.25 0 0 1 17.25 18h-6A2.25 2.25 0 0 1 9 15.75v-6Z"
                                stroke="currentColor"
                                strokeWidth="1.5"
                              />
                              <path
                                d="M15 7.5V6.75A2.25 2.25 0 0 0 12.75 4.5h-6A2.25 2.25 0 0 0 4.5 6.75v6A2.25 2.25 0 0 0 6.75 15H9"
                                stroke="currentColor"
                                strokeWidth="1.5"
                              />
                            </svg>
                          </span>
                        </span>
                        <code className={styles.addressValue}>{activeDepositChain.depositAddress}</code>
                      </button>
                    ) : (
                      <p className={styles.muted}>Deposit address unavailable</p>
                    )}
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
                </>
              ) : null}
            </article>

            <article className={styles.card}>
              <div className={styles.cardHeader}>
                <h2>Assets &amp; Approvals</h2>
                <span className={styles.muted}>{policyApprovalMode === 'auto' ? 'Global Approval: On' : 'Global Approval: Off'}</span>
              </div>
              {isOwner ? (
                <div className={styles.toggleRow}>
                  <label>
                    <input
                      type="checkbox"
                      checked={policyApprovalMode === 'auto'}
                      onChange={(event) => {
                        const nextMode = event.target.checked ? 'auto' : 'per_trade';
                        setPolicyApprovalMode(nextMode);
                        void runManagementAction(
                          () => managementPost('/api/v1/management/policy/update', buildPolicyUpdatePayload({ approvalMode: nextMode })).then(() => Promise.resolve()),
                          `Global approval ${nextMode === 'auto' ? 'enabled' : 'disabled'}.`
                        );
                      }}
                    />
                    Approve all
                  </label>
                </div>
              ) : (
                <p className={styles.muted}>Viewer mode: approval controls are read-only.</p>
              )}
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
                            () => managementPost('/api/v1/management/policy/update', buildPolicyUpdatePayload({ allowedTokens })).then(() => Promise.resolve()),
                            `${approved ? 'Removed' : 'Added'} ${holding.token} preapproval.`
                          );
                        }}
                      >
                        {isTokenPreapproved(holding.token) ? 'Preapproved' : 'Preapprove'}
                      </button>
                    ) : (
                      <span className={styles.muted}>{isTokenPreapproved(holding.token) ? 'Preapproved' : 'Not preapproved'}</span>
                    )}
                  </div>
                </div>
              ))}
            </article>

            <article className={styles.card}>
              <div className={styles.cardHeader}>
                <h2>Wallet Activity</h2>
                <span className={styles.muted}>All wallet-impact events</span>
              </div>
              <div className={styles.rangeButtons}>
                {([
                  ['all', 'All'],
                  ['trades', 'Trades'],
                  ['transfers', 'Transfers'],
                  ['approvals', 'Approvals'],
                  ['deposits', 'Deposits/Withdrawals']
                ] as const).map(([key, label]) => (
                  <button
                    key={key}
                    type="button"
                    className={walletActivityFilter === key ? styles.rangeActive : ''}
                    onClick={() => setWalletActivityFilter(key)}
                  >
                    {label}
                  </button>
                ))}
              </div>
              {filteredWalletTimeline.length === 0 ? <p className={styles.muted}>No wallet activity in this filter.</p> : null}
              <div className={styles.list}>
                {filteredWalletTimeline.slice(0, 60).map((row) => (
                  <div key={row.id} className={styles.listRow}>
                    <div>
                      <div className={styles.listTitle}>{row.title}</div>
                      <div className={styles.muted}>{row.subtitle}</div>
                      {row.txHash ? <div className={styles.muted}>Tx: {shortenHex(row.txHash, 10, 8)}</div> : null}
                    </div>
                    <div className={styles.listMeta}>
                      <span className={styles.statusChip}>{row.status}</span>
                      <span>{formatUtc(row.at)} UTC</span>
                    </div>
                  </div>
                ))}
              </div>
            </article>

            <article id="approval-history" className={styles.card}>
              <div className={styles.cardHeader}>
                <h2>Approval History</h2>
                <span className={styles.muted}>Trade, policy, and transfer approvals</span>
              </div>
              <div className={styles.rangeButtons}>
                {([
                  ['all', 'All'],
                  ['pending', 'Pending'],
                  ['approved', 'Approved'],
                  ['rejected', 'Rejected/Denied']
                ] as const).map(([key, label]) => (
                  <button
                    key={key}
                    type="button"
                    className={approvalStatusFilter === key ? styles.rangeActive : ''}
                    onClick={() => setApprovalStatusFilter(key)}
                  >
                    {label}
                  </button>
                ))}
              </div>
              {!isOwner ? <p className={styles.muted}>Viewer mode: approval actions are locked.</p> : null}
              {filteredApprovalHistory.length === 0 ? <p className={styles.muted}>No approvals in this filter.</p> : null}
              {filteredApprovalHistory.map((row) => (
                <div key={row.id} className={styles.queueRow}>
                  <div>
                    <div className={styles.listTitle}>{row.title}</div>
                    <div className={styles.muted}>{row.subtitle}</div>
                    <div className={styles.muted}>{formatUtc(row.at)} UTC</div>
                  </div>
                  <div className={styles.queueActions}>
                    <span className={styles.statusChip}>{row.status}</span>
                    {isOwner && (row.status === 'pending' || row.status === 'approval_pending') && row.type === 'trade' ? (
                      <>
                        <input
                          value={approvalRejectReasons[row.raw.trade_id] ?? ''}
                          onChange={(event) =>
                            setApprovalRejectReasons((current) => ({
                              ...current,
                              [row.raw.trade_id]: event.target.value
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
                                  tradeId: row.raw.trade_id,
                                  decision: 'approve'
                                }).then(() => Promise.resolve()),
                              `Approved ${row.raw.trade_id}`
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
                                managementPost('/api/v1/management/approvals/decision', {
                                  agentId,
                                  tradeId: row.raw.trade_id,
                                  decision: 'reject',
                                  reasonCode: 'approval_rejected',
                                  reasonMessage: (approvalRejectReasons[row.raw.trade_id] ?? '').trim() || 'Rejected by owner.'
                                }).then(() => Promise.resolve()),
                              `Rejected ${row.raw.trade_id}`
                            )
                          }
                        >
                          Reject
                        </button>
                      </>
                    ) : null}
                    {isOwner && row.status === 'pending' && row.type === 'policy' ? (
                      <>
                        <input
                          value={approvalRejectReasons[row.raw.request_id] ?? ''}
                          onChange={(event) =>
                            setApprovalRejectReasons((current) => ({
                              ...current,
                              [row.raw.request_id]: event.target.value
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
                                  policyApprovalId: row.raw.request_id,
                                  decision: 'approve'
                                }).then(() => Promise.resolve()),
                              `Approved ${row.raw.request_id}`
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
                                  policyApprovalId: row.raw.request_id,
                                  decision: 'reject',
                                  reasonMessage: (approvalRejectReasons[row.raw.request_id] ?? '').trim() || 'Rejected by owner.'
                                }).then(() => Promise.resolve()),
                              `Rejected ${row.raw.request_id}`
                            )
                          }
                        >
                          Deny
                        </button>
                      </>
                    ) : null}
                    {isOwner && row.status === 'pending' && row.type === 'transfer' ? (
                      <>
                        <input
                          value={approvalRejectReasons[row.raw.approval_id] ?? ''}
                          onChange={(event) =>
                            setApprovalRejectReasons((current) => ({
                              ...current,
                              [row.raw.approval_id]: event.target.value
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
                                  approvalId: row.raw.approval_id,
                                  decision: 'approve',
                                  chainKey: row.raw.chain_key
                                }).then(() => Promise.resolve()),
                              `Approved ${row.raw.approval_id}`
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
                                  approvalId: row.raw.approval_id,
                                  decision: 'deny',
                                  chainKey: row.raw.chain_key,
                                  reasonMessage: (approvalRejectReasons[row.raw.approval_id] ?? '').trim() || 'Rejected by owner.'
                                }).then(() => Promise.resolve()),
                              `Denied ${row.raw.approval_id}`
                            )
                          }
                        >
                          Deny
                        </button>
                      </>
                    ) : null}
                  </div>
                </div>
              ))}
            </article>
          </div>

          <aside className={styles.railCol}>
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
                <h3>Limits &amp; Policy</h3>
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
                <h3>Limit Orders</h3>
                <span>{isOwner ? `${limitOrders.length} loaded` : 'viewer'}</span>
              </div>
              {!isOwner ? <p className={styles.muted}>Viewer mode cannot manage limit orders.</p> : null}
              {isOwner ? (
                <>
                  {limitOrders.length === 0 ? <p className={styles.muted}>No open or recent limit orders.</p> : null}
                  {limitOrders.slice(0, 20).map((order) => (
                    <div key={order.orderId} className={styles.railQueueRow}>
                      <div>
                        <div className={styles.listTitle}>
                          {order.tokenIn} {order.side === 'buy' ? '->' : 'to'} {order.tokenOut}
                        </div>
                        <div className={styles.muted}>
                          {order.status} · amount {order.amountIn} · limit {order.limitPrice}
                        </div>
                      </div>
                      <div className={styles.inlineActions}>
                        <span className={styles.statusChip}>{order.status}</span>
                        {(order.status === 'open' || order.status === 'triggered') && (
                          <button
                            type="button"
                            className={styles.dangerButton}
                            onClick={() =>
                              void runManagementAction(
                                () =>
                                  managementPost(`/api/v1/management/limit-orders/${encodeURIComponent(order.orderId)}/cancel`, {
                                    agentId
                                  }).then(() => Promise.resolve()),
                                `Cancelled limit order ${order.orderId}.`
                              )
                            }
                          >
                            Cancel
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </>
              ) : null}
            </article>

            <article className={styles.card}>
              <div className={styles.cardHeader}>
                <h3>Secondary Operations</h3>
              </div>
              {!isOwner ? <p className={styles.muted}>Owner-only operations are hidden in viewer mode.</p> : null}
              {isOwner && management.phase === 'ready' ? (
                <>
                  <div className={styles.subSection}>
                    <h4>Outbound Transfer Policy</h4>
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
                    <h4>Transfer Approval Policy</h4>
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
                    <h4>Telegram Approval Channel</h4>
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
                </>
              ) : null}
            </article>

            <article className={styles.card}>
              <div className={styles.cardHeader}>
                <h3>Management Audit Log</h3>
                <span>{management.phase === 'ready' ? management.data.auditLog.length : '—'}</span>
              </div>
              {management.phase === 'ready' && management.data.auditLog.length === 0 ? <p className={styles.muted}>No audit entries.</p> : null}
              {management.phase === 'ready'
                ? management.data.auditLog.slice(0, 25).map((entry) => (
                    <div key={entry.audit_id} className={styles.listRow}>
                      <div>
                        <div className={styles.listTitle}>
                          {entry.action_type} ({entry.action_status})
                        </div>
                      </div>
                      <div className={styles.listMeta}>{formatUtc(entry.created_at)} UTC</div>
                    </div>
                  ))
                : null}
            </article>
          </aside>
        </div>
      </section>
    </div>
  );
}
