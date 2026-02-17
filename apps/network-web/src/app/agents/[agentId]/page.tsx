'use client';

import Image from 'next/image';
import Link from 'next/link';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useParams, useRouter, useSearchParams } from 'next/navigation';

import { ChainHeaderControl } from '@/components/chain-header-control';
import { ActiveAgentSidebarLink } from '@/components/active-agent-sidebar-link';
import { rememberManagedAgent } from '@/components/management-header-controls';
import { PublicStatusBadge } from '@/components/public-status-badge';
import { SidebarIcon } from '@/components/sidebar-icons';
import { ThemeToggle } from '@/components/theme-toggle';
import { useActiveChainKey } from '@/lib/active-chain';
import { getAgentAvatarPalette, getAgentInitial } from '@/lib/agent-avatar-color';
import {
  buildHoldings,
  formatActivityTitle,
  formatDecimalText,
  formatUnitsTruncated,
  resolveTokenLabel,
  type ActivityPayload,
  type AgentProfilePayload,
  type DepositPayload,
  type LimitOrderItem,
  type ManagementStatePayload,
  type TradePayload,
  tokenSymbolByAddress
} from '@/lib/agent-page-view-model';
import { formatUsd, formatUtc, shortenAddress } from '@/lib/public-format';
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
  txExplorerUrl: string | null;
  tokenSymbols: string[];
  source?: 'default' | 'x402';
};

type X402PaymentRow = {
  payment_id: string;
  approval_id: string | null;
  direction: 'inbound' | 'outbound';
  status: string;
  network_key: string;
  facilitator_key: string;
  asset_kind: 'native' | 'erc20';
  asset_address: string | null;
  asset_symbol: string | null;
  amount_atomic: string;
  payment_url: string | null;
  link_token: string | null;
  tx_hash: string | null;
  reason_code: string | null;
  reason_message: string | null;
  created_at: string;
  updated_at: string;
  terminal_at: string | null;
};

type X402PaymentsPayload = {
  ok: boolean;
  agentId: string;
  chainKey: string;
  queue: X402PaymentRow[];
  history: X402PaymentRow[];
};

type X402ReceiveLinkPayload = {
  ok: boolean;
  agentId: string;
  chainKey: string;
  paymentId: string;
  networkKey: string;
  facilitatorKey: string;
  assetKind: 'native' | 'erc20';
  assetAddress: string | null;
  amountAtomic: string;
  ttlSeconds: number | null;
  paymentUrl: string;
  expiresAt: string | null;
  timeLimitNotice: string;
  status: string;
};

type ToastType = 'success' | 'error' | 'info';
type ToastItem = {
  id: number;
  message: string;
  type: ToastType;
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

function normalizeTokenSelectionSymbol(value: string | null | undefined): string {
  const raw = String(value ?? '').trim();
  if (!raw) {
    return '';
  }
  const upper = raw.toUpperCase();
  if (upper === 'NATIVE' || upper === 'ETH' || upper.endsWith(' ETH')) {
    return 'ETH';
  }
  return upper;
}

export default function AgentPublicProfilePage() {
  const params = useParams<{ agentId: string }>();
  const router = useRouter();
  const searchParams = useSearchParams();
  const agentId = params.agentId;
  const [activeChainKey, , activeChainLabel] = useActiveChainKey();
  const avatarPalette = useMemo(() => getAgentAvatarPalette(agentId), [agentId]);

  const [bootstrapState, setBootstrapState] = useState<BootstrapState>({ phase: 'ready' });
  const [profile, setProfile] = useState<AgentProfilePayload | null>(null);
  const [trades, setTrades] = useState<TradePayload['items'] | null>(null);
  const [activity, setActivity] = useState<ActivityPayload['items'] | null>(null);
  const [management, setManagement] = useState<ManagementViewState>({ phase: 'loading' });
  const [error, setError] = useState<string | null>(null);
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const [depositData, setDepositData] = useState<DepositPayload | null>(null);
  const [x402Payments, setX402Payments] = useState<X402PaymentsPayload | null>(null);
  const [x402ReceiveLink, setX402ReceiveLink] = useState<X402ReceiveLinkPayload | null>(null);
  const [limitOrders, setLimitOrders] = useState<LimitOrderItem[]>([]);
  const [copySubscriptions, setCopySubscriptions] = useState<CopySubscription[]>([]);
  const [vaultAddressCopied, setVaultAddressCopied] = useState(false);
  const vaultCopyResetTimerRef = useRef<number | null>(null);
  const telegramAutoEnableInFlightRef = useRef<Set<string>>(new Set());

  const [walletActivityFilter, setWalletActivityFilter] = useState<WalletActivityFilter>('all');
  const [approvalStatusFilter, setApprovalStatusFilter] = useState<ApprovalStatusFilter>('all');
  const [approvalRejectReasons, setApprovalRejectReasons] = useState<Record<string, string>>({});

  const [withdrawDestination, setWithdrawDestination] = useState('');
  const [withdrawAmount, setWithdrawAmount] = useState('0.1');
  const [withdrawAsset, setWithdrawAsset] = useState('NATIVE');
  const [withdrawCardOpen, setWithdrawCardOpen] = useState(false);
  const [selectedWalletTokens, setSelectedWalletTokens] = useState<string[]>([]);
  const [walletActivityExpanded, setWalletActivityExpanded] = useState(false);
  const [walletActivityPage, setWalletActivityPage] = useState(1);
  const [approvalHistoryExpanded, setApprovalHistoryExpanded] = useState(false);
  const [approvalHistoryPage, setApprovalHistoryPage] = useState(1);
  const [auditExpanded, setAuditExpanded] = useState(false);
  const [auditPage, setAuditPage] = useState(1);
  const [walletExpanded, setWalletExpanded] = useState(false);
  const [walletPage, setWalletPage] = useState(1);
  const [copyExpanded, setCopyExpanded] = useState(false);
  const [copyPage, setCopyPage] = useState(1);
  const [limitExpanded, setLimitExpanded] = useState(false);
  const [limitPage, setLimitPage] = useState(1);

  const [policyApprovalMode, setPolicyApprovalMode] = useState<'per_trade' | 'auto'>('per_trade');
  const [policyMaxTradeUsd, setPolicyMaxTradeUsd] = useState('50');
  const [policyMaxDailyUsd, setPolicyMaxDailyUsd] = useState('250');
  const [policyDailyCapUsdEnabled, setPolicyDailyCapUsdEnabled] = useState(true);
  const [policyDailyTradeCapEnabled, setPolicyDailyTradeCapEnabled] = useState(true);
  const [policyMaxDailyTradeCount, setPolicyMaxDailyTradeCount] = useState('0');
  const [policyAllowedTokens, setPolicyAllowedTokens] = useState<string[]>([]);
  const toastIdRef = useRef(0);
  const toastTimersRef = useRef<Map<number, number>>(new Map());

  const isOwner = management.phase === 'ready';

  function dismissToast(id: number) {
    const timer = toastTimersRef.current.get(id);
    if (timer !== undefined) {
      window.clearTimeout(timer);
      toastTimersRef.current.delete(id);
    }
    setToasts((current) => current.filter((toast) => toast.id !== id));
  }

  function showToast(message: string, type: ToastType = 'info', durationMs = 2800) {
    const id = ++toastIdRef.current;
    setToasts((current) => [...current, { id, message, type }].slice(-4));
    const timer = window.setTimeout(() => dismissToast(id), durationMs);
    toastTimersRef.current.set(id, timer);
  }

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
      setX402Payments(null);
      setX402ReceiveLink(null);
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
    const telegramEnabled = Boolean(payload.approvalChannels?.telegram?.enabled);
    if (!telegramEnabled) {
      const autoEnableKey = `${agentId}:${activeChainKey}:telegram`;
      if (!telegramAutoEnableInFlightRef.current.has(autoEnableKey)) {
        telegramAutoEnableInFlightRef.current.add(autoEnableKey);
        void managementPost('/api/v1/management/approval-channels/update', {
          agentId,
          chainKey: activeChainKey,
          channel: 'telegram',
          enabled: true
        })
          .catch(() => {
            // Keep silent: this is a best-effort background default-on sync.
          })
          .finally(() => {
            telegramAutoEnableInFlightRef.current.delete(autoEnableKey);
          });
      }
    }

    const [depositPayload, x402PaymentsPayload, x402ReceivePayload, limitOrderPayload, copyPayload] = await Promise.all([
      managementGet(`/api/v1/management/deposit?agentId=${encodeURIComponent(agentId)}&chainKey=${encodeURIComponent(activeChainKey)}`),
      managementGet(`/api/v1/management/x402/payments?agentId=${encodeURIComponent(agentId)}&chainKey=${encodeURIComponent(activeChainKey)}`),
      managementGet(`/api/v1/management/x402/receive-link?agentId=${encodeURIComponent(agentId)}&chainKey=${encodeURIComponent(activeChainKey)}`),
      managementGet(`/api/v1/management/limit-orders?agentId=${encodeURIComponent(agentId)}&limit=50`),
      managementGet('/api/v1/copy/subscriptions')
    ]);

    setDepositData(depositPayload as DepositPayload);
    setX402Payments(x402PaymentsPayload as X402PaymentsPayload);
    setX402ReceiveLink(x402ReceivePayload as X402ReceiveLinkPayload);
    setLimitOrders(((limitOrderPayload as { items?: LimitOrderItem[] }).items ?? []).filter(Boolean));
    setCopySubscriptions(((copyPayload as CopySubscriptionsGetPayload).items ?? []).filter(Boolean));
  }, [activeChainKey, agentId]);

  const refreshAll = useCallback(async (options?: { showLoading?: boolean }) => {
    const showLoading = options?.showLoading ?? true;
    setError(null);
    try {
      await loadPublicData();
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Failed to load public profile data.');
    }

    try {
      if (showLoading) {
        setManagement({ phase: 'loading' });
      }
      await loadManagementData();
    } catch (loadError) {
      const message = loadError instanceof Error ? loadError.message : 'Failed to load management state.';
      if (showLoading) {
        setManagement({
          phase: 'error',
          message
        });
      }
    }
  }, [loadManagementData, loadPublicData]);

  useEffect(() => {
    if (!agentId || bootstrapState.phase !== 'ready') {
      return;
    }
    void refreshAll({ showLoading: true });
  }, [agentId, bootstrapState.phase, refreshAll]);

  useEffect(() => {
    if (management.phase !== 'ready' || !agentId) {
      return;
    }
    const intervalId = window.setInterval(() => {
      void refreshAll({ showLoading: false });
    }, 5000);
    return () => {
      window.clearInterval(intervalId);
    };
  }, [management.phase, agentId, refreshAll]);

  async function runManagementAction(action: () => Promise<void>, successMessage: string) {
    try {
      await action();
      showToast(successMessage, 'success');
      await refreshAll({ showLoading: false });
    } catch (actionError) {
      showToast(actionError instanceof Error ? actionError.message : 'Management action failed.', 'error', 3600);
      await refreshAll({ showLoading: false });
    }
  }

  async function copyToClipboard(value: string, successMessage: string, onSuccess?: () => void) {
    try {
      await navigator.clipboard.writeText(value);
      showToast(successMessage, 'success');
      onSuccess?.();
    } catch {
      showToast('Copy failed. Copy the address manually.', 'error', 3200);
    }
  }

  useEffect(() => {
    return () => {
      if (vaultCopyResetTimerRef.current !== null) {
        window.clearTimeout(vaultCopyResetTimerRef.current);
      }
      for (const timer of toastTimersRef.current.values()) {
        window.clearTimeout(timer);
      }
      toastTimersRef.current.clear();
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
  const chainTokenSymbolByAddress = useMemo(
    () => tokenSymbolByAddress(management.phase === 'ready' ? management.data.chainTokens : undefined),
    [management]
  );

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
      outboundTransfersEnabled:
        management.phase === 'ready' ? management.data.outboundTransfersPolicy.outboundTransfersEnabled : false,
      outboundMode: management.phase === 'ready' ? management.data.outboundTransfersPolicy.outboundMode : 'disabled',
      outboundWhitelistAddresses:
        management.phase === 'ready' ? management.data.outboundTransfersPolicy.outboundWhitelistAddresses : []
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

  const preferredWithdrawDestination = useMemo(() => {
    if (management.phase !== 'ready') {
      return '';
    }
    return (
      management.data.outboundTransfersPolicy.outboundWhitelistAddresses.find(
        (address) => typeof address === 'string' && address.trim().length > 0
      )?.trim() ?? ''
    );
  }, [management]);

  const withdrawDestinationPreview = preferredWithdrawDestination ? shortenAddress(preferredWithdrawDestination) : '';

  const activeDepositChain = useMemo(
    () => depositData?.chains.find((chain) => chain.chainKey === activeChainKey) ?? depositData?.chains[0] ?? null,
    [depositData, activeChainKey]
  );

  const holdings = useMemo(() => buildHoldings(profile, depositData, activeChainKey), [profile, depositData, activeChainKey]);
  const withdrawAssetOptions = useMemo(() => {
    const nativeHolding =
      holdings.find((holding) => {
        const symbol = holding.token.trim().toUpperCase();
        return symbol === 'ETH' || symbol === 'NATIVE';
      }) ?? null;
    const nativeBalance = nativeHolding ? formatUnitsTruncated(nativeHolding.amountRaw, nativeHolding.decimals, 6) : '0';
    const opts: Array<{ label: string; value: string }> = [{ label: `${activeChainLabel} ETH (${nativeBalance})`, value: 'NATIVE' }];
    const seen = new Set<string>(['NATIVE']);
    for (const holding of holdings) {
      const symbol = holding.token.trim().toUpperCase();
      if (!symbol || symbol === 'ETH' || symbol === 'NATIVE') {
        continue;
      }
      if (!seen.has(symbol)) {
        seen.add(symbol);
        opts.push({ label: `${symbol} (${formatUnitsTruncated(holding.amountRaw, holding.decimals, 6)})`, value: symbol });
      }
    }
    return opts;
  }, [holdings, activeChainLabel]);

  const withdrawSelectedHolding = useMemo(() => {
    if (withdrawAsset === 'NATIVE') {
      return holdings.find((holding) => {
        const symbol = holding.token.trim().toUpperCase();
        return symbol === 'ETH' || symbol === 'NATIVE';
      }) ?? null;
    }
    return holdings.find((holding) => holding.token.trim().toUpperCase() === withdrawAsset.trim().toUpperCase()) ?? null;
  }, [holdings, withdrawAsset]);

  const withdrawMaxAmount = useMemo(() => {
    if (!withdrawSelectedHolding) {
      return '';
    }
    return formatUnitsTruncated(withdrawSelectedHolding.amountRaw, withdrawSelectedHolding.decimals, 18);
  }, [withdrawSelectedHolding]);

  useEffect(() => {
    if (!preferredWithdrawDestination) {
      return;
    }
    setWithdrawDestination((current) => (current.trim().length === 0 ? preferredWithdrawDestination : current));
  }, [preferredWithdrawDestination]);
  const tokenDecimalsBySymbol = useMemo(() => {
    const map = new Map<string, number>();
    for (const holding of holdings) {
      const symbol = normalizeTokenSelectionSymbol(holding.token);
      if (symbol) {
        map.set(symbol, holding.decimals);
      }
    }
    return map;
  }, [holdings]);

  const explorerTxBaseUrl = useMemo(() => {
    const base = activeDepositChain?.explorerBaseUrl ?? null;
    if (!base) {
      return null;
    }
    return `${base.replace(/\/+$/, '')}/tx/`;
  }, [activeDepositChain?.explorerBaseUrl]);

  const toTxExplorerUrl = useCallback(
    (txHash: string | null | undefined) => {
      if (!txHash || !explorerTxBaseUrl) {
        return null;
      }
      return `${explorerTxBaseUrl}${txHash}`;
    },
    [explorerTxBaseUrl]
  );

  const formatHumanAmount = useCallback(
    (amount: string | null | undefined, tokenLabel: string, decimalsHint?: number) => {
      const normalized = normalizeTokenSelectionSymbol(tokenLabel);
      if (!amount) {
        return `— ${tokenLabel}`;
      }

      if (decimalsHint !== undefined) {
        const units = formatUnitsTruncated(amount, decimalsHint, normalized === 'USDC' ? 2 : 6);
        if (units === '—') {
          return `— ${tokenLabel}`;
        }
        if (normalized === 'USDC') {
          const numeric = Number(units);
          if (Number.isFinite(numeric)) {
            return `${new Intl.NumberFormat('en-US', {
              style: 'currency',
              currency: 'USD',
              minimumFractionDigits: 2,
              maximumFractionDigits: 2
            }).format(numeric)} USDC`;
          }
        }
        return `${formatDecimalText(units)} ${tokenLabel}`;
      }

      if (normalized === 'USDC') {
        const numeric = Number(amount);
        if (Number.isFinite(numeric)) {
          return `${new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
          }).format(numeric)} USDC`;
        }
      }
      return `${formatDecimalText(amount)} ${tokenLabel}`;
    },
    []
  );

  const transferApprovedState = useCallback((status: string) => {
    const normalized = (status ?? '').toLowerCase();
    if (normalized === 'approved' || normalized === 'filled' || normalized === 'executed') {
      return 'Yes';
    }
    if (normalized === 'pending' || normalized === 'approval_pending') {
      return 'Pending';
    }
    return 'No';
  }, []);

  const walletTimeline = useMemo(() => {
    const items: WalletTimelineItem[] = [];

    for (const trade of trades ?? []) {
      const tokenIn = resolveTokenLabel(trade.token_in, chainTokenSymbolByAddress);
      const tokenOut = resolveTokenLabel(trade.token_out, chainTokenSymbolByAddress);
      const normalizedIn = normalizeTokenSelectionSymbol(tokenIn);
      const normalizedOut = normalizeTokenSelectionSymbol(tokenOut);
      const tradedAmount = formatHumanAmount(trade.amount_in, tokenIn);
      const gainedAmount = formatHumanAmount(trade.amount_out, tokenOut);
      const reason = trade.reason ?? trade.reason_code ?? trade.reason_message;
      items.push({
        id: `trd-${trade.trade_id}`,
        at: trade.executed_at ?? trade.created_at,
        kind: 'trades',
        title: `${tokenIn} -> ${tokenOut}`,
        subtitle: `Traded ${tradedAmount}; Received ${gainedAmount}${reason ? `; ${reason}` : ''}`,
        status: trade.status,
        txHash: trade.tx_hash ?? null,
        txExplorerUrl: toTxExplorerUrl(trade.tx_hash),
        tokenSymbols: [normalizedIn, normalizedOut].filter(Boolean)
      });
    }

    for (const event of activity ?? []) {
      if (event.event_type.startsWith('trade_')) {
        continue;
      }
      const tokenIn = normalizeTokenSelectionSymbol(event.token_in_symbol);
      const tokenOut = normalizeTokenSelectionSymbol(event.token_out_symbol);
      const pair = event.pair_display ?? `${event.token_in_symbol ?? 'token'} / ${event.token_out_symbol ?? 'token'}`;
      items.push({
        id: `evt-${event.event_id}`,
        at: event.created_at,
        kind: event.event_type.startsWith('policy_') ? 'approvals' : 'trades',
        title: formatActivityTitle(event.event_type),
        subtitle: pair,
        status: event.event_type,
        txHash: null,
        txExplorerUrl: null,
        tokenSymbols: [tokenIn, tokenOut].filter(Boolean)
      });
    }

    for (const deposit of activeDepositChain?.recentDeposits ?? []) {
      const depositSymbol = normalizeTokenSelectionSymbol(deposit.token);
      const depositAmount = formatHumanAmount(deposit.amount, deposit.token);
      const confirmationsText = activeDepositChain?.minConfirmations
        ? `Confirmations: >= ${activeDepositChain.minConfirmations}`
        : 'Confirmations: n/a';
      items.push({
        id: `dep-${deposit.txHash}-${deposit.blockNumber}`,
        at: deposit.confirmedAt,
        kind: 'deposits',
        title: `Deposit ${depositAmount}`,
        subtitle: `Status: ${deposit.status || 'confirmed'}; ${confirmationsText}; Block ${deposit.blockNumber}`,
        status: deposit.status || 'confirmed',
        txHash: deposit.txHash ?? null,
        txExplorerUrl: toTxExplorerUrl(deposit.txHash),
        tokenSymbols: depositSymbol ? [depositSymbol] : []
      });
    }

    if (management.phase === 'ready') {
      for (const payment of x402Payments?.history ?? []) {
        const symbol = normalizeTokenSelectionSymbol(payment.asset_symbol || (payment.asset_kind === 'native' ? 'ETH' : 'TOKEN'));
        const directionLabel = payment.direction === 'inbound' ? 'Received' : 'Sent';
        const titleToken = payment.asset_symbol || (payment.asset_kind === 'native' ? `${activeChainLabel} ETH` : 'Token');
        items.push({
          id: `x402-${payment.payment_id}`,
          at: payment.terminal_at ?? payment.updated_at ?? payment.created_at,
          kind: payment.direction === 'inbound' ? 'deposits' : 'transfers',
          title: `x402 ${directionLabel} ${formatDecimalText(payment.amount_atomic)} ${titleToken}`,
          subtitle: `Status: ${payment.status}; Network: ${payment.network_key}; Facilitator: ${payment.facilitator_key}`,
          status: payment.status,
          txHash: payment.tx_hash ?? null,
          txExplorerUrl: toTxExplorerUrl(payment.tx_hash),
          tokenSymbols: symbol ? [symbol] : [],
          source: 'x402'
        });
      }
      for (const item of management.data.transferApprovalsHistory ?? []) {
        const transferTokenLabel = item.transfer_type === 'native' ? `${activeChainLabel} ETH` : item.token_symbol ?? 'Token';
        const transferSymbol = item.transfer_type === 'native' ? 'ETH' : normalizeTokenSelectionSymbol(item.token_symbol);
        const transferDecimals =
          item.transfer_type === 'native' ? 18 : (tokenDecimalsBySymbol.get(normalizeTokenSelectionSymbol(item.token_symbol)) ?? 18);
        const transferAmount = formatHumanAmount(item.amount_wei, transferTokenLabel, transferDecimals);
        items.push({
          id: `xfrh-${item.approval_id}`,
          at: item.terminal_at ?? item.decided_at ?? item.created_at,
          kind: 'transfers',
          title: item.approval_source === 'x402' ? `x402 outbound approval` : `${transferTokenLabel} transfer`,
          subtitle:
            item.approval_source === 'x402'
              ? `URL: ${item.x402_url ?? 'n/a'}; Amount: ${item.x402_amount_atomic ?? item.amount_wei}; Approved: ${transferApprovedState(item.status)}`
              : `To: ${item.to_address}; Amount: ${transferAmount}; Approved: ${transferApprovedState(item.status)}; Confirmations: ${item.confirmations ?? 'n/a'}`,
          status: item.status,
          txHash: item.tx_hash ?? null,
          txExplorerUrl: toTxExplorerUrl(item.tx_hash),
          tokenSymbols: transferSymbol ? [transferSymbol] : [],
          source: item.approval_source === 'x402' ? 'x402' : 'default'
        });
      }
      for (const item of management.data.transferApprovalsQueue ?? []) {
        const transferTokenLabel = item.transfer_type === 'native' ? `${activeChainLabel} ETH` : item.token_symbol ?? 'Token';
        const transferSymbol = item.transfer_type === 'native' ? 'ETH' : normalizeTokenSelectionSymbol(item.token_symbol);
        const transferDecimals =
          item.transfer_type === 'native' ? 18 : (tokenDecimalsBySymbol.get(normalizeTokenSelectionSymbol(item.token_symbol)) ?? 18);
        const transferAmount = formatHumanAmount(item.amount_wei, transferTokenLabel, transferDecimals);
        items.push({
          id: `xfrq-${item.approval_id}`,
          at: item.created_at,
          kind: 'transfers',
          title: item.approval_source === 'x402' ? 'Pending x402 approval' : 'Pending transfer approval',
          subtitle:
            item.approval_source === 'x402'
              ? `URL: ${item.x402_url ?? 'n/a'}; Amount: ${item.x402_amount_atomic ?? item.amount_wei}; Approved: Pending`
              : `To: ${item.to_address}; Amount: ${transferAmount}; Approved: Pending; Confirmations: ${item.confirmations ?? 'n/a'}`,
          status: item.status,
          txHash: null,
          txExplorerUrl: null,
          tokenSymbols: transferSymbol ? [transferSymbol] : [],
          source: item.approval_source === 'x402' ? 'x402' : 'default'
        });
      }
      for (const item of management.data.policyApprovalsHistory ?? []) {
        const policySymbol = item.token_address ? normalizeTokenSelectionSymbol(chainTokenSymbolByAddress.get(item.token_address.toLowerCase()) ?? '') : '';
        items.push({
          id: `polh-${item.request_id}`,
          at: item.decided_at ?? item.created_at,
          kind: 'approvals',
          title: policyApprovalLabel(item, management.data.chainTokens),
          subtitle: item.reason_message ? item.reason_message : 'Policy approval decision',
          status: item.status,
          txHash: null,
          txExplorerUrl: null,
          tokenSymbols: policySymbol ? [policySymbol] : []
        });
      }
      for (const item of management.data.policyApprovalsQueue ?? []) {
        const policySymbol = item.token_address ? normalizeTokenSelectionSymbol(chainTokenSymbolByAddress.get(item.token_address.toLowerCase()) ?? '') : '';
        items.push({
          id: `polq-${item.request_id}`,
          at: item.created_at,
          kind: 'approvals',
          title: policyApprovalLabel(item, management.data.chainTokens),
          subtitle: 'Pending policy approval',
          status: 'pending',
          txHash: null,
          txExplorerUrl: null,
          tokenSymbols: policySymbol ? [policySymbol] : []
        });
      }
      for (const item of management.data.approvalsQueue) {
        const tokenInLabel = resolveTokenLabel(item.token_in, chainTokenSymbolByAddress);
        const tokenOutLabel = resolveTokenLabel(item.token_out, chainTokenSymbolByAddress);
        const tokenIn = normalizeTokenSelectionSymbol(tokenInLabel);
        const tokenOut = normalizeTokenSelectionSymbol(tokenOutLabel);
        items.push({
          id: `trdapp-${item.trade_id}`,
          at: item.created_at,
          kind: 'approvals',
          title: `${tokenInLabel} -> ${tokenOutLabel}`,
          subtitle: item.reason ?? 'Pending trade approval',
          status: 'pending',
          txHash: null,
          txExplorerUrl: null,
          tokenSymbols: [tokenIn, tokenOut].filter(Boolean)
        });
      }
    }

    items.sort((a, b) => {
      const atA = Number(new Date(a.at).getTime());
      const atB = Number(new Date(b.at).getTime());
      return atB - atA;
    });
    return items;
  }, [
    activeChainLabel,
    activeDepositChain?.minConfirmations,
    activeDepositChain?.recentDeposits,
    activity,
    chainTokenSymbolByAddress,
    formatHumanAmount,
    management,
    toTxExplorerUrl,
    tokenDecimalsBySymbol,
    x402Payments?.history,
    trades,
    transferApprovedState
  ]);

  const selectedWalletTokenSet = useMemo(() => new Set(selectedWalletTokens), [selectedWalletTokens]);

  const filteredWalletTimeline = useMemo(() => {
    const tokenFiltered =
      selectedWalletTokenSet.size === 0
        ? walletTimeline
        : walletTimeline.filter((item) => item.tokenSymbols.some((token) => selectedWalletTokenSet.has(token)));
    if (walletActivityFilter === 'all') {
      return tokenFiltered;
    }
    return tokenFiltered.filter((item) => item.kind === walletActivityFilter);
  }, [walletActivityFilter, walletTimeline, selectedWalletTokenSet]);
  const walletActivityTotalPages = walletActivityExpanded ? Math.max(1, Math.ceil(filteredWalletTimeline.length / 10)) : 1;
  const normalizedWalletActivityPage = Math.min(walletActivityPage, walletActivityTotalPages);
  const visibleWalletActivity = useMemo(() => {
    if (!walletActivityExpanded) {
      return filteredWalletTimeline.slice(0, 3);
    }
    const start = (normalizedWalletActivityPage - 1) * 10;
    return filteredWalletTimeline.slice(start, start + 10);
  }, [filteredWalletTimeline, normalizedWalletActivityPage, walletActivityExpanded]);

  const approvalHistoryItems = useMemo(() => {
    if (management.phase !== 'ready') {
      return [] as Array<{
        id: string;
        at: string;
        title: string;
        status: string;
        subtitle: string;
        type: 'trade' | 'policy' | 'transfer';
        tokenSymbols: string[];
        raw: any;
      }>;
    }
    const rows: Array<{
      id: string;
      at: string;
      title: string;
      status: string;
      subtitle: string;
      type: 'trade' | 'policy' | 'transfer';
      tokenSymbols: string[];
      raw: any;
    }> = [];
    for (const item of management.data.approvalsQueue) {
      const tokenInLabel = resolveTokenLabel(item.token_in, chainTokenSymbolByAddress);
      const tokenOutLabel = resolveTokenLabel(item.token_out, chainTokenSymbolByAddress);
      const tokenIn = normalizeTokenSelectionSymbol(tokenInLabel);
      const tokenOut = normalizeTokenSelectionSymbol(tokenOutLabel);
      rows.push({
        id: `trade-${item.trade_id}`,
        at: item.created_at,
        title: `${tokenInLabel} -> ${tokenOutLabel}`,
        status: 'pending',
        subtitle: item.reason ?? 'Pending trade approval',
        type: 'trade',
        tokenSymbols: [tokenIn, tokenOut].filter(Boolean),
        raw: item
      });
    }
    for (const item of management.data.policyApprovalsQueue ?? []) {
      const policySymbol = item.token_address ? normalizeTokenSelectionSymbol(chainTokenSymbolByAddress.get(item.token_address.toLowerCase()) ?? '') : '';
      rows.push({
        id: `policy-pending-${item.request_id}`,
        at: item.created_at,
        title: policyApprovalLabel(item, management.data.chainTokens),
        status: 'pending',
        subtitle: 'Pending policy approval',
        type: 'policy',
        tokenSymbols: policySymbol ? [policySymbol] : [],
        raw: item
      });
    }
    for (const item of management.data.policyApprovalsHistory ?? []) {
      const policySymbol = item.token_address ? normalizeTokenSelectionSymbol(chainTokenSymbolByAddress.get(item.token_address.toLowerCase()) ?? '') : '';
      rows.push({
        id: `policy-history-${item.request_id}`,
        at: item.decided_at ?? item.created_at,
        title: policyApprovalLabel(item, management.data.chainTokens),
        status: item.status,
        subtitle: item.reason_message || 'Policy approval history',
        type: 'policy',
        tokenSymbols: policySymbol ? [policySymbol] : [],
        raw: item
      });
    }
    for (const item of management.data.transferApprovalsQueue ?? []) {
      const transferSymbol = item.transfer_type === 'native' ? 'ETH' : normalizeTokenSelectionSymbol(item.token_symbol);
      rows.push({
        id: `transfer-pending-${item.approval_id}`,
        at: item.created_at,
        title: item.approval_source === 'x402' ? 'x402 outbound payment' : `Transfer to ${shortenAddress(item.to_address)}`,
        status: item.status,
        subtitle:
          item.approval_source === 'x402'
            ? `URL: ${item.x402_url ?? 'n/a'}; Amount: ${item.x402_amount_atomic ?? item.amount_wei}; Network: ${item.x402_network_key ?? item.chain_key}`
            : `${item.amount_wei} wei`,
        type: 'transfer',
        tokenSymbols: transferSymbol ? [transferSymbol] : [],
        raw: item
      });
    }
    for (const item of management.data.transferApprovalsHistory ?? []) {
      const transferSymbol = item.transfer_type === 'native' ? 'ETH' : normalizeTokenSelectionSymbol(item.token_symbol);
      rows.push({
        id: `transfer-history-${item.approval_id}`,
        at: item.terminal_at ?? item.decided_at ?? item.created_at,
        title: item.approval_source === 'x402' ? 'x402 outbound payment' : `Transfer to ${shortenAddress(item.to_address)}`,
        status: item.status,
        subtitle:
          item.approval_source === 'x402'
            ? `URL: ${item.x402_url ?? 'n/a'}; Amount: ${item.x402_amount_atomic ?? item.amount_wei}; Network: ${item.x402_network_key ?? item.chain_key}`
            : `${item.amount_wei} wei`,
        type: 'transfer',
        tokenSymbols: transferSymbol ? [transferSymbol] : [],
        raw: item
      });
    }
    rows.sort((a, b) => Number(new Date(b.at).getTime()) - Number(new Date(a.at).getTime()));
    return rows;
  }, [management, chainTokenSymbolByAddress]);

  const filteredApprovalHistory = useMemo(() => {
    const tokenFiltered =
      selectedWalletTokenSet.size === 0
        ? approvalHistoryItems
        : approvalHistoryItems.filter((row) => row.tokenSymbols.some((token) => selectedWalletTokenSet.has(token)));
    if (approvalStatusFilter === 'all') {
      return tokenFiltered;
    }
    if (approvalStatusFilter === 'pending') {
      return tokenFiltered.filter((row) => row.status === 'pending' || row.status === 'approval_pending');
    }
    if (approvalStatusFilter === 'approved') {
      return tokenFiltered.filter((row) => row.status === 'approved');
    }
    return tokenFiltered.filter((row) => row.status === 'rejected' || row.status === 'deny' || row.status === 'denied');
  }, [approvalHistoryItems, approvalStatusFilter, selectedWalletTokenSet]);
  const approvalHistoryTotalPages = approvalHistoryExpanded ? Math.max(1, Math.ceil(filteredApprovalHistory.length / 10)) : 1;
  const normalizedApprovalHistoryPage = Math.min(approvalHistoryPage, approvalHistoryTotalPages);
  const visibleApprovalHistory = useMemo(() => {
    if (!approvalHistoryExpanded) {
      return filteredApprovalHistory.slice(0, 3);
    }
    const start = (normalizedApprovalHistoryPage - 1) * 10;
    return filteredApprovalHistory.slice(start, start + 10);
  }, [approvalHistoryExpanded, filteredApprovalHistory, normalizedApprovalHistoryPage]);
  const auditEntries = management.phase === 'ready' ? management.data.auditLog : [];
  const auditTotalPages = auditExpanded ? Math.max(1, Math.ceil(auditEntries.length / 10)) : 1;
  const normalizedAuditPage = Math.min(auditPage, auditTotalPages);
  const visibleAuditEntries = useMemo(() => {
    if (!auditExpanded) {
      return auditEntries.slice(0, 3);
    }
    const start = (normalizedAuditPage - 1) * 10;
    return auditEntries.slice(start, start + 10);
  }, [auditEntries, auditExpanded, normalizedAuditPage]);

  useEffect(() => {
    setApprovalHistoryPage(1);
  }, [approvalHistoryExpanded, approvalStatusFilter, selectedWalletTokens, filteredApprovalHistory.length]);

  useEffect(() => {
    setAuditPage(1);
  }, [auditExpanded, auditEntries.length]);

  const filledTrades = useMemo(() => (trades ?? []).filter((trade) => trade.status === 'filled').length, [trades]);
  const winRate = useMemo(() => {
    const total = trades?.length ?? 0;
    if (total === 0) {
      return '—';
    }
    return `${((filledTrades / total) * 100).toFixed(1)}%`;
  }, [filledTrades, trades]);

  const status = profile?.agent.public_status;
  const isPaused =
    (management.phase === 'ready' ? management.data.agent.publicStatus : profile?.agent.public_status) === 'paused';
  const selectedTokenSummary =
    selectedWalletTokens.length === 0 ? 'All tokens' : `${selectedWalletTokens.join(', ')} selected`;
  const displayWalletTokenLabel = (token: string): string => {
    const normalized = normalizeTokenSelectionSymbol(token);
    if (normalized === 'ETH') {
      return `${activeChainLabel} ETH`;
    }
    return token;
  };
  const formatWalletHoldingAmount = (holding: { token: string; amountRaw: string; decimals: number }): string => {
    const normalized = normalizeTokenSelectionSymbol(holding.token);
    const base = formatUnitsTruncated(holding.amountRaw, holding.decimals, 6);
    if (normalized === 'USDC') {
      const numeric = Number(base);
      if (Number.isFinite(numeric)) {
        return new Intl.NumberFormat('en-US', {
          style: 'currency',
          currency: 'USD',
          minimumFractionDigits: 2,
          maximumFractionDigits: 2
        }).format(numeric);
      }
      return `$${base}`;
    }
    return base;
  };
  const walletTotalPages = walletExpanded ? Math.max(1, Math.ceil(holdings.length / 10)) : 1;
  const normalizedWalletPage = Math.min(walletPage, walletTotalPages);
  const visibleWalletHoldings = useMemo(() => {
    if (!walletExpanded) {
      return holdings.slice(0, 3);
    }
    const start = (normalizedWalletPage - 1) * 10;
    return holdings.slice(start, start + 10);
  }, [holdings, normalizedWalletPage, walletExpanded]);
  const copyTotalPages = copyExpanded ? Math.max(1, Math.ceil(copySubscriptions.length / 10)) : 1;
  const normalizedCopyPage = Math.min(copyPage, copyTotalPages);
  const visibleCopySubscriptions = useMemo(() => {
    if (!copyExpanded) {
      return copySubscriptions.slice(0, 3);
    }
    const start = (normalizedCopyPage - 1) * 10;
    return copySubscriptions.slice(start, start + 10);
  }, [copyExpanded, copySubscriptions, normalizedCopyPage]);
  const limitTotalPages = limitExpanded ? Math.max(1, Math.ceil(limitOrders.length / 10)) : 1;
  const normalizedLimitPage = Math.min(limitPage, limitTotalPages);
  const visibleLimitOrders = useMemo(() => {
    if (!limitExpanded) {
      return limitOrders.slice(0, 3);
    }
    const start = (normalizedLimitPage - 1) * 10;
    return limitOrders.slice(start, start + 10);
  }, [limitExpanded, limitOrders, normalizedLimitPage]);

  useEffect(() => {
    setWalletPage(1);
  }, [walletExpanded, holdings.length]);

  useEffect(() => {
    setWalletActivityPage(1);
  }, [walletActivityExpanded, walletActivityFilter, selectedWalletTokens, filteredWalletTimeline.length]);

  useEffect(() => {
    setCopyPage(1);
  }, [copyExpanded, copySubscriptions.length]);

  useEffect(() => {
    setLimitPage(1);
  }, [limitExpanded, limitOrders.length]);

  const renderUtilityBar = () => (
    <header className={styles.utilityBar}>
      <div className={styles.utilityLabel}>Agent Wallet</div>
      {activeWallet?.address ? (
        <button
          type="button"
          className={`${styles.addressCopyButton} ${styles.utilityAddressCopyButton} ${vaultAddressCopied ? styles.addressCopyButtonActive : ''}`}
          onClick={() =>
            void copyToClipboard(activeWallet.address, 'Vault address copied.', () => {
              setVaultAddressCopied(true);
              if (vaultCopyResetTimerRef.current !== null) {
                window.clearTimeout(vaultCopyResetTimerRef.current);
              }
              vaultCopyResetTimerRef.current = window.setTimeout(() => {
                setVaultAddressCopied(false);
                vaultCopyResetTimerRef.current = null;
              }, 1000);
            })
          }
          title="Copy full wallet address"
        >
          <span className={styles.utilityAddressInline}>
            <code className={styles.utilityAddressValue}>{activeWallet.address}</code>
          </span>
          <span className={styles.copyIcon} aria-hidden="true">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M9 9.75A2.25 2.25 0 0 1 11.25 7.5h6A2.25 2.25 0 0 1 19.5 9.75v6A2.25 2.25 0 0 1 17.25 18h-6A2.25 2.25 0 0 1 9 15.75v-6Z" stroke="currentColor" strokeWidth="1.5" />
              <path d="M15 7.5V6.75A2.25 2.25 0 0 0 12.75 4.5h-6A2.25 2.25 0 0 0 4.5 6.75v6A2.25 2.25 0 0 0 6.75 15H9" stroke="currentColor" strokeWidth="1.5" />
            </svg>
          </span>
        </button>
      ) : null}
      <div className={styles.utilityControls}>
        <ChainHeaderControl />
        {isOwner ? (
          <button
            type="button"
            className={`${styles.iconOnlyButton} ${styles.utilityPlayPauseButton} ${isPaused ? styles.utilityPlayButton : styles.utilityPauseButton}`}
            aria-label={isPaused ? 'Play agent' : 'Pause agent'}
            title={isPaused ? 'Play agent' : 'Pause agent'}
            onClick={() =>
              void runManagementAction(
                () => managementPost(isPaused ? '/api/v1/management/resume' : '/api/v1/management/pause', { agentId }).then(() => Promise.resolve()),
                isPaused ? 'Agent resumed.' : 'Agent paused.'
              )
            }
          >
            {isPaused ? (
              <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                <path d="M8 5.5v13l10-6.5-10-6.5Z" />
              </svg>
            ) : (
              <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                <rect x="7" y="5.5" width="3.8" height="13" rx="0.9" />
                <rect x="13.2" y="5.5" width="3.8" height="13" rx="0.9" />
              </svg>
            )}
            <span className="sr-only">{isPaused ? 'Play' : 'Pause'}</span>
          </button>
        ) : null}
        <ThemeToggle className={styles.themeButton} />
      </div>
    </header>
  );

  const renderToasts = () => (
    <div className={styles.toastStack} aria-live="polite" aria-atomic="false">
      {toasts.map((toast) => (
        <div key={toast.id} className={`${styles.toast} ${toast.type === 'success' ? styles.toastSuccess : toast.type === 'error' ? styles.toastError : styles.toastInfo}`}>
          {toast.message}
        </div>
      ))}
    </div>
  );

  const renderKpiStrip = () => (
    <section className={styles.kpiStrip}>
      <article className={`${styles.kpiChip} ${styles.walletCard}`}>
        <div className={styles.kpiLabel}>Lifetime PnL</div>
        <div className={styles.kpiValueCompact}>{formatUsd(profile?.latestMetrics?.pnl_usd ?? null)}</div>
      </article>
      <article className={`${styles.kpiChip} ${styles.walletCard}`}>
        <div className={styles.kpiLabel}>24h Volume</div>
        <div className={styles.kpiValueCompact}>{formatUsd(profile?.latestMetrics?.volume_usd ?? null)}</div>
      </article>
      <article className={`${styles.kpiChip} ${styles.walletCard}`}>
        <div className={styles.kpiLabel}>Win Rate</div>
        <div className={styles.kpiValueCompact}>{winRate}</div>
      </article>
      <article className={`${styles.kpiChip} ${styles.walletCard}`}>
        <div className={styles.kpiLabel}>Fees Paid</div>
        <div className={styles.kpiValueCompact}>—</div>
      </article>
    </section>
  );

  const renderWithdrawModal = () => {
    if (!withdrawCardOpen) {
      return null;
    }
    return (
      <div className={styles.withdrawModalBackdrop} onClick={() => setWithdrawCardOpen(false)} role="presentation">
        <article id="withdraw" className={styles.withdrawModalCard} onClick={(event) => event.stopPropagation()}>
          <div className={styles.withdrawModalHeader}>
            <div className={styles.withdrawModalTitle}>
              <h2>Withdraw</h2>
              <span className={styles.withdrawChainBadge}>{activeChainLabel}</span>
            </div>
            <label className={styles.withdrawHeaderAsset}>
              <span>Asset</span>
              <select value={withdrawAsset} onChange={(event) => setWithdrawAsset(event.target.value)}>
                {withdrawAssetOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            <button type="button" className={styles.withdrawCloseButton} onClick={() => setWithdrawCardOpen(false)}>
              Close
            </button>
          </div>
          <div className={`${styles.formGrid} ${styles.withdrawModalForm}`}>
            <label>
              Withdraw destination
              <input value={withdrawDestination} onChange={(event) => setWithdrawDestination(event.target.value)} />
            </label>
            <label>
              Withdraw amount
              <div className={styles.amountInputWrap}>
                <input value={withdrawAmount} onChange={(event) => setWithdrawAmount(event.target.value)} />
                <button
                  type="button"
                  className={styles.withdrawMaxButton}
                  disabled={!withdrawMaxAmount}
                  onClick={() => setWithdrawAmount(withdrawMaxAmount || '0')}
                >
                  Max
                </button>
              </div>
            </label>
          </div>
          <div className={`${styles.toggleRow} ${styles.withdrawModalActions}`}>
            <button
              type="button"
              className={styles.withdrawSubmitButton}
              disabled={!isOwner || !withdrawDestination.trim() || !withdrawAmount.trim()}
              onClick={() =>
                void runManagementAction(
                  () =>
                    managementPost('/api/v1/management/withdraw', {
                      agentId,
                      chainKey: activeChainKey,
                      asset: withdrawAsset,
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
        </article>
      </div>
    );
  };

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
      {renderToasts()}
      <aside className={styles.sidebar}>
        <Link href="/" className={styles.sidebarLogo} aria-label="X-Claw home">
          <Image src="/X-Claw-Logo.png" alt="X-Claw" width={900} height={280} className={styles.sidebarLogoImage} priority />
        </Link>
        <nav className={styles.nav}>
          <Link href="/dashboard" className={styles.navItem} aria-label="Dashboard" title="Dashboard">
            <SidebarIcon name="dashboard" />
          </Link>
          <Link href="/explore" className={styles.navItem} aria-label="Explore" title="Explore">
            <SidebarIcon name="explore" />
          </Link>
          <Link href="/approvals" className={styles.navItem} aria-label="Approvals Center" title="Approvals Center">
            <SidebarIcon name="approvals" />
          </Link>
          <ActiveAgentSidebarLink itemClassName={styles.navItem} activeClassName={styles.navItemActive} />
          <div style={{ marginTop: 'auto', display: 'grid', gap: '0.42rem' }}>
            <Link href="/settings" className={styles.navItem} aria-label="Settings & Security" title="Settings & Security">
              <SidebarIcon name="settings" />
            </Link>
            <Link href="/how-to" className={styles.navItem} aria-label="How To" title="How To">
              <SidebarIcon name="howto" />
            </Link>
          </div>
        </nav>
      </aside>

      <section className={styles.surface}>
        {renderUtilityBar()}

        {error ? <p className={styles.warningBanner}>{error}</p> : null}

        <section className={`${styles.walletHeaderCard} ${styles.walletCard}`}>
          <div className={styles.walletHeaderTop}>
            <div className={styles.walletIdentity}>
              <div
                className={styles.avatar}
                style={{
                  backgroundColor: avatarPalette.backgroundColor,
                  borderColor: avatarPalette.borderColor,
                  color: avatarPalette.textColor
                }}
              >
                {getAgentInitial(profile?.agent.agent_name, agentId)}
              </div>
              <div>
                <div className={styles.walletTitleRow}>
                <h1>{profile?.agent.agent_name ?? 'Loading agent...'}</h1>
                {status && isPublicStatus(status) ? <PublicStatusBadge status={status} /> : null}
                {!status ? <span className={styles.muted}>status unavailable</span> : null}
              </div>
                <div className={styles.accountMetaChips}>
                  <span className={styles.walletChip}>{profile?.agent.runtime_platform ?? 'runtime unavailable'}</span>
                  <span className={styles.walletChip}>Chain: {activeChainLabel}</span>
                  <span className={styles.walletChip}>Vault: {activeWallet ? shortenAddress(activeWallet.address) : '—'}</span>
                </div>
              </div>
            </div>
            <div className={styles.headerApprovalControl}>
              <span className={styles.globalApprovalLabel}>Approve all</span>
              {isOwner ? (
                <label className={styles.iosToggle} title="Allow all trades without per-trade approval.">
                  <input
                    type="checkbox"
                    checked={policyApprovalMode === 'auto'}
                    onChange={(event) => {
                      const nextMode = event.target.checked ? 'auto' : 'per_trade';
                      setPolicyApprovalMode(nextMode);
                      void runManagementAction(
                        () =>
                          managementPost('/api/v1/management/policy/update', buildPolicyUpdatePayload({ approvalMode: nextMode })).then(() =>
                            Promise.resolve()
                          ),
                        `Global approval ${nextMode === 'auto' ? 'enabled' : 'disabled'}.`
                      );
                    }}
                  />
                  <span className={styles.iosSlider} />
                </label>
              ) : (
                <span className={styles.muted}>{policyApprovalMode === 'auto' ? 'Enabled' : 'Disabled'}</span>
              )}
            </div>

          </div>

          <div className={`${styles.walletActions} ${styles.walletActionRow}`}>
            {isOwner && management.phase === 'ready' ? (
              <>
                <button
                  type="button"
                  className={styles.dangerButton}
                  onClick={() => {
                    if (!window.confirm('Revoke all permissions for this agent? This cannot be undone.')) {
                      return;
                    }
                    void runManagementAction(
                      () => managementPost('/api/v1/management/revoke-all', { agentId }).then(() => Promise.resolve()),
                      'Revoked all permissions for this agent.'
                    );
                  }}
                >
                  Revoke All Permissions
                </button>
                <div className={styles.withdrawInline}>
                  {withdrawDestinationPreview ? <span className={styles.withdrawPreviewLabel}>{withdrawDestinationPreview}</span> : null}
                  <button type="button" onClick={() => setWithdrawCardOpen((current) => !current)}>
                    {withdrawCardOpen ? 'Close Withdraw' : 'Withdraw'}
                  </button>
                </div>
              </>
            ) : (
              <p className={styles.muted}>Viewer mode: owner controls are locked.</p>
            )}
          </div>
        </section>

        {renderKpiStrip()}

        {renderWithdrawModal()}

        <div className={styles.contentGrid}>
          <div className={styles.mainColumn}>
            <article className={`${styles.card} ${styles.walletCard}`}>
            <div className={`${styles.cardHeader} ${styles.walletCardHeader}`}>
              <h2>Wallet</h2>
              <span className={styles.muted}>{selectedTokenSummary}</span>
            </div>
            {!isOwner ? <p className={styles.muted}>Viewer mode: approval controls are read-only.</p> : null}
            {holdings.length === 0 ? <p className={styles.muted}>No balances detected for this chain.</p> : null}
            <p className={styles.muted}>Click a token to filter Activity and Approval History. Hold Ctrl/Cmd for multi-select.</p>
            {visibleWalletHoldings.map((holding) => (
              <div
                key={holding.token}
                className={`${styles.listRow} ${styles.walletTokenRow} ${selectedWalletTokenSet.has(normalizeTokenSelectionSymbol(holding.token)) ? styles.selectedWalletRow : ''}`}
                onClick={(event) => {
                  const symbol = normalizeTokenSelectionSymbol(holding.token);
                  if (!symbol) {
                    return;
                  }
                  const multi = event.ctrlKey || event.metaKey;
                  setSelectedWalletTokens((current) => {
                    const has = current.includes(symbol);
                    if (multi) {
                      if (has) {
                        return current.filter((item) => item !== symbol);
                      }
                      return [...current, symbol];
                    }
                    if (has && current.length === 1) {
                      return [];
                    }
                    return [symbol];
                  });
                }}
                title="Click to filter by token. Hold Ctrl/Cmd for multi-select."
              >
                <div>
                  <div className={styles.walletTokenTitleRow}>
                    <div className={styles.listTitle}>{displayWalletTokenLabel(holding.token)}</div>
                    {isTokenPreapproved(holding.token) ? <span className={styles.approvedChip}>Approved</span> : null}
                  </div>
                </div>
                <div className={styles.walletTokenMeta}>
                  <div className={styles.walletTokenMetricColumn}>
                    <span className={styles.walletTokenMetricLabel}>Balance</span>
                    <span className={styles.walletTokenAmount}>{formatWalletHoldingAmount(holding)}</span>
                  </div>
                  <div className={`${styles.walletTokenMetricColumn} ${styles.tokenApprovalControl}`} onClick={(event) => event.stopPropagation()}>
                    <span className={styles.walletTokenMetricLabel}>Approval</span>
                    <label className={styles.iosToggle} title="Allow this token without per-trade approval.">
                      <input
                        type="checkbox"
                        checked={isTokenPreapproved(holding.token)}
                        disabled={!isOwner}
                        onChange={(event) => {
                          const enabled = event.target.checked;
                          const allowedTokens = nextAllowedTokensForSymbol(holding.token, enabled);
                          void runManagementAction(
                            () => managementPost('/api/v1/management/policy/update', buildPolicyUpdatePayload({ allowedTokens })).then(() => Promise.resolve()),
                            `${enabled ? 'Added' : 'Removed'} ${holding.token} preapproval.`
                          );
                        }}
                      />
                      <span className={styles.iosSlider} />
                    </label>
                  </div>
                </div>
              </div>
            ))}
            {holdings.length > 3 ? (
              <div className={styles.paginationRow}>
                <button type="button" onClick={() => setWalletExpanded((current) => !current)}>
                  {walletExpanded ? 'Show less' : 'Show more'}
                </button>
                {walletExpanded && holdings.length > 10 ? (
                  <div className={styles.paginationControls}>
                    <button
                      type="button"
                      onClick={() => setWalletPage((current) => Math.max(1, current - 1))}
                      disabled={normalizedWalletPage <= 1}
                    >
                      Prev
                    </button>
                    <span className={styles.muted}>
                      Page {normalizedWalletPage} / {walletTotalPages}
                    </span>
                    <button
                      type="button"
                      onClick={() => setWalletPage((current) => Math.min(walletTotalPages, current + 1))}
                      disabled={normalizedWalletPage >= walletTotalPages}
                    >
                      Next
                    </button>
                  </div>
                ) : null}
              </div>
            ) : null}
          </article>

            <article className={`${styles.card} ${styles.walletCard}`}>
            <div className={`${styles.cardHeader} ${styles.walletCardHeader}`}>
              <h2>Wallet Activity</h2>
              <div className={styles.inlineActions}>
                <span className={styles.muted}>All wallet-impact events</span>
              </div>
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
              {visibleWalletActivity.map((row) => (
                <div key={row.id} className={styles.listRow}>
                  <div>
                    <div className={styles.listTitle}>{row.title}</div>
                    <div className={styles.muted}>{row.subtitle}</div>
                    {row.source === 'x402' ? <div className={styles.muted}>Source: x402</div> : null}
                    {row.txHash ? (
                      <div className={styles.muted}>
                        Tx:{' '}
                        {row.txExplorerUrl ? (
                          <a href={row.txExplorerUrl} target="_blank" rel="noreferrer" className={styles.inlineLink}>
                            {shortenHex(row.txHash, 10, 8)}
                          </a>
                        ) : (
                          shortenHex(row.txHash, 10, 8)
                        )}
                      </div>
                    ) : null}
                  </div>
                  <div className={styles.listMeta}>
                    <span className={styles.statusChip}>{row.status}</span>
                    <span>{formatUtc(row.at)} UTC</span>
                  </div>
                </div>
              ))}
            </div>
            {filteredWalletTimeline.length > 3 ? (
              <div className={styles.paginationRow}>
                <button type="button" onClick={() => setWalletActivityExpanded((current) => !current)}>
                  {walletActivityExpanded ? 'Show less' : 'Show more'}
                </button>
                {walletActivityExpanded && filteredWalletTimeline.length > 10 ? (
                  <div className={styles.paginationControls}>
                    <button
                      type="button"
                      onClick={() => setWalletActivityPage((current) => Math.max(1, current - 1))}
                      disabled={normalizedWalletActivityPage <= 1}
                    >
                      Prev
                    </button>
                    <span className={styles.muted}>
                      Page {normalizedWalletActivityPage} / {walletActivityTotalPages}
                    </span>
                    <button
                      type="button"
                      onClick={() => setWalletActivityPage((current) => Math.min(walletActivityTotalPages, current + 1))}
                      disabled={normalizedWalletActivityPage >= walletActivityTotalPages}
                    >
                      Next
                    </button>
                  </div>
                ) : null}
              </div>
            ) : null}
          </article>

            <article id="approval-history" className={`${styles.card} ${styles.walletCard}`}>
            <div className={`${styles.cardHeader} ${styles.walletCardHeader}`}>
              <h2>Approval History</h2>
              <div className={styles.inlineActions}>
                <span className={styles.muted}>Trade, policy, and transfer approvals</span>
              </div>
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
            {visibleApprovalHistory.map((row) => (
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
            {filteredApprovalHistory.length > 3 ? (
              <div className={styles.paginationRow}>
                <button type="button" onClick={() => setApprovalHistoryExpanded((current) => !current)}>
                  {approvalHistoryExpanded ? 'Show less' : 'Show more'}
                </button>
                {approvalHistoryExpanded && filteredApprovalHistory.length > 10 ? (
                  <div className={styles.paginationControls}>
                    <button
                      type="button"
                      onClick={() => setApprovalHistoryPage((current) => Math.max(1, current - 1))}
                      disabled={normalizedApprovalHistoryPage <= 1}
                    >
                      Prev
                    </button>
                    <span className={styles.muted}>
                      Page {normalizedApprovalHistoryPage} / {approvalHistoryTotalPages}
                    </span>
                    <button
                      type="button"
                      onClick={() => setApprovalHistoryPage((current) => Math.min(approvalHistoryTotalPages, current + 1))}
                      disabled={normalizedApprovalHistoryPage >= approvalHistoryTotalPages}
                    >
                      Next
                    </button>
                  </div>
                ) : null}
              </div>
            ) : null}
          </article>

            <article className={`${styles.card} ${styles.walletCard}`}>
              <div className={`${styles.cardHeader} ${styles.walletCardHeader}`}>
                <h3>Management Audit Log</h3>
                <div className={styles.inlineActions}>
                  <span>{management.phase === 'ready' ? management.data.auditLog.length : '—'}</span>
                </div>
              </div>
              {management.phase === 'ready' && auditEntries.length === 0 ? <p className={styles.muted}>No audit entries.</p> : null}
              {management.phase === 'ready'
                ? visibleAuditEntries.map((entry) => (
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
              {management.phase === 'ready' && auditEntries.length > 3 ? (
                <div className={styles.paginationRow}>
                  <button type="button" onClick={() => setAuditExpanded((current) => !current)}>
                    {auditExpanded ? 'Show less' : 'Show more'}
                  </button>
                  {auditExpanded && auditEntries.length > 10 ? (
                    <div className={styles.paginationControls}>
                      <button
                        type="button"
                        onClick={() => setAuditPage((current) => Math.max(1, current - 1))}
                        disabled={normalizedAuditPage <= 1}
                      >
                        Prev
                      </button>
                      <span className={styles.muted}>
                        Page {normalizedAuditPage} / {auditTotalPages}
                      </span>
                      <button
                        type="button"
                        onClick={() => setAuditPage((current) => Math.min(auditTotalPages, current + 1))}
                        disabled={normalizedAuditPage >= auditTotalPages}
                      >
                        Next
                      </button>
                    </div>
                  ) : null}
                </div>
              ) : null}
            </article>
          </div>

          <aside className={styles.sideColumn}>
            <article className={`${styles.card} ${styles.walletCard}`}>
              <div className={`${styles.cardHeader} ${styles.walletCardHeader}`}>
                <h3>x402 Receive Link</h3>
                <span>{x402ReceiveLink?.status ?? 'loading'}</span>
              </div>
              {x402ReceiveLink ? (
                <>
                  <div className={styles.muted}>Network: {x402ReceiveLink.networkKey}</div>
                  <div className={styles.muted}>Facilitator: {x402ReceiveLink.facilitatorKey}</div>
                  <div className={styles.muted}>
                    Amount: {x402ReceiveLink.amountAtomic} ({x402ReceiveLink.assetKind})
                  </div>
                  {x402ReceiveLink.expiresAt ? (
                    <div className={styles.muted}>Expires: {formatUtc(x402ReceiveLink.expiresAt)} UTC</div>
                  ) : (
                    <div className={styles.muted}>Expires: never (static link)</div>
                  )}
                  <div className={styles.muted}>{x402ReceiveLink.timeLimitNotice}</div>
                  <div className={styles.inlineActions}>
                    <button type="button" onClick={() => void copyToClipboard(x402ReceiveLink.paymentUrl, 'x402 receive link copied.')}>
                      Copy Link
                    </button>
                    <button
                      type="button"
                      onClick={() =>
                        void runManagementAction(
                          async () => {
                            const refreshed = (await managementGet(
                              `/api/v1/management/x402/receive-link?agentId=${encodeURIComponent(agentId)}&chainKey=${encodeURIComponent(activeChainKey)}`
                            )) as X402ReceiveLinkPayload;
                            setX402ReceiveLink(refreshed);
                          },
                          'x402 receive link refreshed.'
                        )
                      }
                    >
                      Refresh
                    </button>
                  </div>
                </>
              ) : (
                <p className={styles.muted}>Receive link unavailable.</p>
              )}
            </article>

            <article className={`${styles.card} ${styles.walletCard}`}>
            <div className={`${styles.cardHeader} ${styles.walletCardHeader}`}>
              <h3>Copy Trading</h3>
              <span>{isOwner ? `${copySubscriptions.length} relationships` : 'viewer'}</span>
            </div>
            {!isOwner ? <p className={styles.muted}>Copy relationships are owner-only.</p> : null}
            <p className={styles.muted}>
              Create copy relationships from <Link href="/explore" className={styles.inlineLink}>Explore</Link>. This panel is review and delete only.
            </p>
            {isOwner ? (
              <>
                {copySubscriptions.length === 0 ? <p className={styles.muted}>No copy subscriptions configured.</p> : null}
                {visibleCopySubscriptions.map((item) => (
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
                        className={styles.dangerButton}
                        onClick={() =>
                          void runManagementAction(
                            () =>
                              fetch(`/api/v1/copy/subscriptions/${encodeURIComponent(item.subscriptionId)}`, {
                                method: 'DELETE',
                                credentials: 'same-origin',
                                headers: {
                                  ...(getCsrfToken() ? { 'x-csrf-token': getCsrfToken() as string } : {})
                                }
                              }).then((res) => {
                                if (!res.ok) {
                                  throw new Error('Failed to delete copy subscription.');
                                }
                                return Promise.resolve();
                              }),
                            `Deleted copy subscription ${item.subscriptionId}.`
                          )
                        }
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                ))}
                {copySubscriptions.length > 3 ? (
                  <div className={styles.paginationRow}>
                    <button type="button" onClick={() => setCopyExpanded((current) => !current)}>
                      {copyExpanded ? 'Show less' : 'Show more'}
                    </button>
                    {copyExpanded && copySubscriptions.length > 10 ? (
                      <div className={styles.paginationControls}>
                        <button
                          type="button"
                          onClick={() => setCopyPage((current) => Math.max(1, current - 1))}
                          disabled={normalizedCopyPage <= 1}
                        >
                          Prev
                        </button>
                        <span className={styles.muted}>
                          Page {normalizedCopyPage} / {copyTotalPages}
                        </span>
                        <button
                          type="button"
                          onClick={() => setCopyPage((current) => Math.min(copyTotalPages, current + 1))}
                          disabled={normalizedCopyPage >= copyTotalPages}
                        >
                          Next
                        </button>
                      </div>
                    ) : null}
                  </div>
                ) : null}
              </>
            ) : null}
          </article>

            <article className={`${styles.card} ${styles.walletCard}`}>
            <div className={`${styles.cardHeader} ${styles.walletCardHeader}`}>
              <h3>Limit Orders</h3>
              <span>{isOwner ? `${limitOrders.length} loaded` : 'viewer'}</span>
            </div>
            {!isOwner ? <p className={styles.muted}>Viewer mode cannot manage limit orders.</p> : null}
            {isOwner ? (
              <>
                {limitOrders.length === 0 ? <p className={styles.muted}>No open or recent limit orders.</p> : null}
                {visibleLimitOrders.map((order) => (
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
                {limitOrders.length > 3 ? (
                  <div className={styles.paginationRow}>
                    <button type="button" onClick={() => setLimitExpanded((current) => !current)}>
                      {limitExpanded ? 'Show less' : 'Show more'}
                    </button>
                    {limitExpanded && limitOrders.length > 10 ? (
                      <div className={styles.paginationControls}>
                        <button
                          type="button"
                          onClick={() => setLimitPage((current) => Math.max(1, current - 1))}
                          disabled={normalizedLimitPage <= 1}
                        >
                          Prev
                        </button>
                        <span className={styles.muted}>
                          Page {normalizedLimitPage} / {limitTotalPages}
                        </span>
                        <button
                          type="button"
                          onClick={() => setLimitPage((current) => Math.min(limitTotalPages, current + 1))}
                          disabled={normalizedLimitPage >= limitTotalPages}
                        >
                          Next
                        </button>
                      </div>
                    ) : null}
                  </div>
                ) : null}
              </>
            ) : null}
          </article>

          </aside>
        </div>
      </section>
    </div>
  );
}
