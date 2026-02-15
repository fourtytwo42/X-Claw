'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { useParams, useRouter, useSearchParams } from 'next/navigation';

import { rememberManagedAgent } from '@/components/management-header-controls';
import { PublicStatusBadge } from '@/components/public-status-badge';
import { useActiveChainKey } from '@/lib/active-chain';
import { formatNumber, formatPercent, formatUsd, formatUtc, isStale, shortenAddress } from '@/lib/public-format';
import { isPublicStatus } from '@/lib/public-types';

type BootstrapState =
  | { phase: 'bootstrapping' }
  | { phase: 'error'; message: string; code?: string; actionHint?: string }
  | { phase: 'ready' };

type AgentProfilePayload = {
  ok: boolean;
  agent: {
    agent_id: string;
    agent_name: string;
    description: string | null;
    owner_label: string | null;
    runtime_platform: string;
    public_status: string;
    created_at: string;
    updated_at: string;
    last_activity_at: string | null;
    last_heartbeat_at: string | null;
  };
  wallets: Array<{
    chain_key: string;
    address: string;
    custody: string;
  }>;
  latestMetrics:
    | {
        window: string;
        pnl_usd: string | null;
        return_pct: string | null;
        volume_usd: string | null;
        trades_count: number;
        followers_count: number;
        created_at: string;
      }
    | null;
  copyBreakdown:
    | {
        selfTradesCount: number;
        copiedTradesCount: number;
        selfVolumeUsd: string | null;
        copiedVolumeUsd: string | null;
        selfPnlUsd: string | null;
        copiedPnlUsd: string | null;
      }
    | null;
};

type TradePayload = {
  ok: boolean;
  items: Array<{
    trade_id: string;
    source_trade_id: string | null;
    source_label?: 'self' | 'copied';
    chain_key: string;
    status: string;
    token_in: string;
    token_out: string;
    pair: string;
    amount_in: string | null;
    amount_out: string | null;
    reason: string | null;
    reason_code: string | null;
    reason_message: string | null;
    tx_hash: string | null;
    executed_at: string | null;
    created_at: string;
  }>;
};

type ActivityPayload = {
  ok: boolean;
  items: Array<{
    event_id: string;
    agent_id: string;
    event_type: string;
    chain_key: string;
    pair_display: string | null;
    token_in_symbol: string | null;
    token_out_symbol: string | null;
    created_at: string;
  }>;
};

type ManagementStatePayload = {
  ok: boolean;
  agent: {
    agentId: string;
    publicStatus: string;
    metadata: Record<string, unknown>;
  };
  chainTokens?: Array<{ symbol: string; address: string }>;
  approvalChannels?: {
    telegram?: { enabled: boolean; updatedAt?: string | null };
  };
  chainPolicy: {
    chainKey: string;
    chainEnabled: boolean;
    updatedAt: string | null;
  };
  approvalsQueue: Array<{
    trade_id: string;
    chain_key: string;
    pair: string;
    amount_in: string | null;
    token_in: string;
    token_out: string;
    reason: string | null;
    created_at: string;
  }>;
  latestPolicy: {
    mode: 'real';
    approval_mode: 'per_trade' | 'auto';
    max_trade_usd: string | null;
    max_daily_usd: string | null;
    max_daily_trade_count: string | null;
    daily_cap_usd_enabled: boolean;
    daily_trade_cap_enabled: boolean;
    allowed_tokens: string[];
    created_at: string;
  } | null;
  tradeCaps: {
    dailyCapUsdEnabled: boolean;
    dailyTradeCapEnabled: boolean;
    maxDailyTradeCount: number | null;
  };
  dailyUsage: {
    utcDay: string;
    dailySpendUsd: string;
    dailyFilledTrades: number;
  };
  outboundTransfersPolicy: {
    outboundTransfersEnabled: boolean;
    outboundMode: 'disabled' | 'allow_all' | 'whitelist';
    outboundWhitelistAddresses: string[];
    updatedAt: string | null;
  };
  auditLog: Array<{
    audit_id: string;
    action_type: string;
    action_status: string;
    public_redacted_payload: Record<string, unknown>;
    created_at: string;
  }>;
  managementSession: {
    sessionId: string;
    expiresAt: string;
  };
};

type ManagementViewState =
  | { phase: 'loading' }
  | { phase: 'unauthorized' }
  | { phase: 'error'; message: string }
  | { phase: 'ready'; data: ManagementStatePayload };

type DepositPayload = {
  ok: boolean;
  agentId: string;
  chains: Array<{
    chainKey: string;
    depositAddress: string;
    minConfirmations: number;
    lastSyncedAt: string | null;
    syncStatus: 'ok' | 'degraded';
    syncDetail: string | null;
    balances: Array<{ token: string; balance: string; decimals?: number; blockNumber: number | null; observedAt: string }>;
    recentDeposits: Array<{
      token: string;
      amount: string;
      txHash: string;
      blockNumber: number;
      confirmedAt: string;
      status: string;
    }>;
    explorerBaseUrl: string | null;
  }>;
};

type LimitOrderItem = {
  orderId: string;
  agentId: string;
  chainKey: string;
  mode: 'real';
  side: 'buy' | 'sell';
  tokenIn: string;
  tokenOut: string;
  amountIn: string;
  limitPrice: string;
  slippageBps: number;
  status: string;
  expiresAt: string | null;
  cancelledAt: string | null;
  triggerSource: string;
  createdAt: string;
  updatedAt: string;
};

const HEARTBEAT_STALE_THRESHOLD_SECONDS = 180;

function formatActivityTitle(eventType: string): string {
  if (eventType === 'trade_filled') {
    return 'Trade filled';
  }
  if (eventType === 'trade_failed') {
    return 'Trade failed';
  }
  if (eventType === 'trade_executing') {
    return 'Trade executing';
  }
  if (eventType === 'trade_approval_pending') {
    return 'Awaiting approval';
  }
  if (eventType.startsWith('trade_')) {
    return eventType.replace(/^trade_/, '').replace(/_/g, ' ');
  }
  return eventType.replace(/_/g, ' ');
}

function formatDecimalText(value: string | null | undefined): string {
  const raw = (value ?? '').trim();
  if (!raw) {
    return '—';
  }
  const sign = raw.startsWith('-') ? '-' : '';
  const unsigned = sign ? raw.slice(1) : raw;
  const [intPartRaw, fracPartRaw] = unsigned.split('.', 2);
  const intPart = (intPartRaw || '0').replace(/^0+(?=\\d)/, '');
  const intWithCommas = intPart.replace(/\\B(?=(\\d{3})+(?!\\d))/g, ',');
  if (fracPartRaw && fracPartRaw.length > 0) {
    return `${sign}${intWithCommas}.${fracPartRaw}`;
  }
  return `${sign}${intWithCommas}`;
}

function normalizeHexAddress(value: string): string {
  const raw = (value ?? '').trim();
  return raw.startsWith('0x') ? raw.toLowerCase() : raw.toLowerCase();
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

function CopyIcon() {
  return (
    <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <rect x="9" y="9" width="11" height="11" rx="2" />
      <rect x="4" y="4" width="11" height="11" rx="2" />
    </svg>
  );
}

function shortenHex(value: string | null | undefined, head = 6, tail = 4): string {
  if (!value) {
    return '—';
  }
  const raw = String(value);
  if (raw.length <= head + tail + 3) {
    return raw;
  }
  return `${raw.slice(0, head)}...${raw.slice(-tail)}`;
}

function formatUnitsTruncated(raw: string | null | undefined, decimals: number, maxFraction: number): string {
  if (!raw) {
    return '—';
  }
  let value: bigint;
  try {
    value = BigInt(raw);
  } catch {
    return '—';
  }
  if (value < BigInt(0)) {
    value = BigInt(0);
  }
  if (decimals <= 0) {
    return value.toString();
  }

  const neg = value < BigInt(0);
  const digits = (neg ? -value : value).toString();
  const padded = digits.padStart(decimals + 1, '0');
  const whole = padded.slice(0, -decimals) || '0';
  let frac = padded.slice(-decimals);
  // Trim trailing zeros, then truncate to maxFraction without rounding.
  frac = frac.replace(/0+$/, '');
  if (maxFraction >= 0 && frac.length > maxFraction) {
    frac = frac.slice(0, maxFraction).replace(/0+$/, '');
  }
  const core = frac.length > 0 ? `${whole}.${frac}` : whole;
  return neg ? `-${core}` : core;
}

function formatUsdFromBaseUnits(raw: string | null | undefined, decimals: number): string {
  if (!raw) {
    return '—';
  }
  let value: bigint;
  try {
    value = BigInt(raw);
  } catch {
    return '—';
  }
  if (value < BigInt(0)) {
    value = BigInt(0);
  }

  const digits = value.toString();
  const safeDecimals = Math.max(0, Math.trunc(decimals || 0));
  const padded = digits.padStart(safeDecimals + 1, '0');
  const wholeRaw = safeDecimals > 0 ? padded.slice(0, -safeDecimals) || '0' : padded;
  const whole = wholeRaw.replace(/\B(?=(\d{3})+(?!\d))/g, ',');

  if (safeDecimals === 0) {
    return `$${whole}.00`;
  }

  const frac = padded.slice(-safeDecimals);
  const frac2 = (frac + '00').slice(0, 2);
  return `$${whole}.${frac2}`;
}

function TokenIcon({ symbol }: { symbol: string }) {
  const text = (symbol || '?').slice(0, 1).toUpperCase();
  return <span className="asset-icon" aria-hidden="true">{text}</span>;
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
      // fallback
    }
    return { ok: false, message, code, actionHint };
  }

  return { ok: true };
}

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
  const headers: Record<string, string> = {
    'content-type': 'application/json'
  };
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
  const [withdrawDestination, setWithdrawDestination] = useState('');
  const [withdrawAmount, setWithdrawAmount] = useState('0.1');
  const [depositCopied, setDepositCopied] = useState(false);
  const [overviewDepositCopied, setOverviewDepositCopied] = useState(false);
  const [depositData, setDepositData] = useState<DepositPayload | null>(null);
  const [limitOrders, setLimitOrders] = useState<LimitOrderItem[]>([]);
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
  const [approvalRejectReasons, setApprovalRejectReasons] = useState<Record<string, string>>({});
  const [chainUpdatePending, setChainUpdatePending] = useState(false);
  const [telegramApprovalsEnabled, setTelegramApprovalsEnabled] = useState(false);
  const [telegramUpdatePending, setTelegramUpdatePending] = useState(false);

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

  useEffect(() => {
    let cancelled = false;

    async function load() {
      if (!agentId || bootstrapState.phase !== 'ready') {
        return;
      }

      setError(null);
      setManagementError(null);

      try {
        const [profileRes, tradesRes, activityRes] = await Promise.all([
          fetch(`/api/v1/public/agents/${agentId}`, { cache: 'no-store' }),
          fetch(`/api/v1/public/agents/${agentId}/trades?limit=20`, { cache: 'no-store' }),
          fetch(`/api/v1/public/activity?limit=20&agentId=${encodeURIComponent(agentId)}`, { cache: 'no-store' })
        ]);

        if (!profileRes.ok || !tradesRes.ok || !activityRes.ok) {
          throw new Error('Failed to load public profile data.');
        }

        const profilePayload = (await profileRes.json()) as AgentProfilePayload;
        const tradesPayload = (await tradesRes.json()) as TradePayload;
        const activityPayload = (await activityRes.json()) as ActivityPayload;

        if (!cancelled) {
          setProfile(profilePayload);
          setTrades(tradesPayload.items);
          setActivity(activityPayload.items.slice(0, 12));
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : 'Failed to load public profile data.');
        }
      }

      try {
        setManagement({ phase: 'loading' });
        const managementRes = await fetch(
          `/api/v1/management/agent-state?agentId=${encodeURIComponent(agentId)}&chainKey=${encodeURIComponent(activeChainKey)}`,
          {
          cache: 'no-store',
          credentials: 'same-origin'
          }
        );

        if (managementRes.status === 401) {
          if (!cancelled) {
            setManagement({ phase: 'unauthorized' });
          }
          return;
        }

        if (!managementRes.ok) {
          const payload = (await managementRes.json().catch(() => null)) as { message?: string } | null;
          throw new Error(payload?.message ?? 'Failed to load management state.');
        }

        const payload = (await managementRes.json()) as ManagementStatePayload;
        if (!cancelled) {
          setManagement({ phase: 'ready', data: payload });
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
          setTelegramApprovalsEnabled(Boolean(payload.approvalChannels?.telegram?.enabled));
          rememberManagedAgent(agentId);

          const savedDestination =
            (payload.agent?.metadata as { management?: { withdrawDestinations?: Record<string, string> } } | undefined)?.management
              ?.withdrawDestinations?.[activeChainKey] ??
            (payload.agent?.metadata as { management?: { withdrawDestinations?: Record<string, string> } } | undefined)?.management
              ?.withdrawDestinations?.base_sepolia ??
            '';
          if (savedDestination) {
            setWithdrawDestination(savedDestination);
          }

          const [depositPayload, limitOrderPayload] = await Promise.all([
            managementGet(
              `/api/v1/management/deposit?agentId=${encodeURIComponent(agentId)}&chainKey=${encodeURIComponent(activeChainKey)}`
            ),
            managementGet(`/api/v1/management/limit-orders?agentId=${encodeURIComponent(agentId)}&limit=50`)
          ]);
          setDepositData(depositPayload as DepositPayload);
          setLimitOrders(((limitOrderPayload as { items?: LimitOrderItem[] }).items ?? []).filter(Boolean));
        }
      } catch (loadError) {
        if (!cancelled) {
          setManagement({
            phase: 'error',
            message: loadError instanceof Error ? loadError.message : 'Failed to load management state.'
          });
        }
      }
    }

    void load();

    return () => {
      cancelled = true;
    };
  }, [agentId, bootstrapState.phase, activeChainKey]);

  const policyAllowedTokenSet = useMemo(() => {
    return new Set(
      policyAllowedTokens
        .map((token) => String(token).trim().toLowerCase())
        .filter((token) => token.length > 0)
    );
  }, [policyAllowedTokens]);

  const chainTokenAddressBySymbol = useMemo(() => {
    const out: Record<string, string> = {};
    if (management.phase !== 'ready') {
      return out;
    }
    for (const entry of management.data.chainTokens ?? []) {
      const symbol = typeof entry?.symbol === 'string' ? entry.symbol.trim().toUpperCase() : '';
      const address = typeof entry?.address === 'string' ? entry.address.trim() : '';
      if (!symbol || !address) {
        continue;
      }
      out[symbol] = address;
    }
    return out;
  }, [management]);

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
      allowedTokens: next.allowedTokens ?? policyAllowedTokens
    };
  }

  function isTokenPreapproved(symbol: string): boolean {
    const normalizedSymbol = symbol.trim().toUpperCase();
    const address = chainTokenAddressBySymbol[normalizedSymbol];
    if (address) {
      return policyAllowedTokenSet.has(address.toLowerCase());
    }
    // Back-compat fallback if old snapshots stored symbols directly.
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

  const activityFeed = useMemo(() => {
    const tokenSymbolByAddress = new Map<string, string>();
    if (management.phase === 'ready') {
      for (const entry of management.data.chainTokens ?? []) {
        tokenSymbolByAddress.set(normalizeHexAddress(entry.address), entry.symbol);
      }
    }

    const resolveTokenLabel = (value: string | null | undefined) => {
      const raw = (value ?? '').trim();
      if (!raw) return 'token';
      if (!raw.startsWith('0x')) return raw;
      return tokenSymbolByAddress.get(normalizeHexAddress(raw)) ?? shortenAddress(raw);
    };

    const items: Array<
      | {
          kind: 'trade';
          id: string;
          at: string;
          status: string;
          pair: string;
          tokenIn: string;
          tokenOut: string;
          tokenInLabel: string;
          tokenOutLabel: string;
          amountIn: string | null;
          amountOut: string | null;
          txHash: string | null;
          reason: string | null;
        }
      | { kind: 'event'; id: string; at: string; eventType: string; pairDisplay: string | null; tokenInSymbol: string | null; tokenOutSymbol: string | null }
    > = [];

    for (const trade of trades ?? []) {
      items.push({
        kind: 'trade',
        id: trade.trade_id,
        at: trade.created_at,
        status: trade.status,
        pair: trade.pair,
        tokenIn: trade.token_in,
        tokenOut: trade.token_out,
        tokenInLabel: resolveTokenLabel(trade.token_in),
        tokenOutLabel: resolveTokenLabel(trade.token_out),
        amountIn: trade.amount_in,
        amountOut: trade.amount_out,
        txHash: trade.tx_hash,
        reason: trade.reason_code ?? trade.reason_message ?? trade.reason ?? null
      });
    }

    for (const event of activity ?? []) {
      items.push({
        kind: 'event',
        id: event.event_id,
        at: event.created_at,
        eventType: event.event_type,
        pairDisplay: event.pair_display,
        tokenInSymbol: event.token_in_symbol,
        tokenOutSymbol: event.token_out_symbol
      });
    }

    items.sort((a, b) => new Date(b.at).getTime() - new Date(a.at).getTime());
    return items.slice(0, 30);
  }, [activity, trades, management.phase]);

  async function refreshManagementState() {
    if (!agentId) {
      return;
    }

    try {
      const managementRes = await fetch(
        `/api/v1/management/agent-state?agentId=${encodeURIComponent(agentId)}&chainKey=${encodeURIComponent(activeChainKey)}`,
        {
          cache: 'no-store',
          credentials: 'same-origin'
        }
      );

      if (managementRes.status === 401) {
        setManagement({ phase: 'unauthorized' });
        return;
      }

      if (!managementRes.ok) {
        const payload = (await managementRes.json().catch(() => null)) as { message?: string } | null;
        throw new Error(payload?.message ?? 'Failed to refresh management state.');
      }

      const payload = (await managementRes.json()) as ManagementStatePayload;
      setManagement({ phase: 'ready', data: payload });
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
      setTelegramApprovalsEnabled(Boolean(payload.approvalChannels?.telegram?.enabled));
      const [depositPayload, limitOrderPayload] = await Promise.all([
        managementGet(`/api/v1/management/deposit?agentId=${encodeURIComponent(agentId)}&chainKey=${encodeURIComponent(activeChainKey)}`),
        managementGet(`/api/v1/management/limit-orders?agentId=${encodeURIComponent(agentId)}&limit=50`)
      ]);
      setDepositData(depositPayload as DepositPayload);
      setLimitOrders(((limitOrderPayload as { items?: LimitOrderItem[] }).items ?? []).filter(Boolean));
    } catch (loadError) {
      setManagementError(loadError instanceof Error ? loadError.message : 'Failed to refresh management state.');
    }
  }

  async function runManagementAction(
    action: () => Promise<void>,
    successMessage: string
  ) {
    setManagementError(null);
    setManagementNotice(null);
    try {
      await action();
      setManagementNotice(successMessage);
      await refreshManagementState();
    } catch (actionError) {
      setManagementError(actionError instanceof Error ? actionError.message : 'Management action failed.');
      try {
        await refreshManagementState();
      } catch {
        // ignore refresh failures on error path
      }
    }
  }

  if (bootstrapState.phase === 'bootstrapping') {
    return <main className="panel">Validating management token...</main>;
  }

  if (bootstrapState.phase === 'error') {
    return (
      <main className="panel">
        <h1 className="section-title">Management bootstrap failed</h1>
        <p>{bootstrapState.message}</p>
        {bootstrapState.code ? <p className="muted">Code: {bootstrapState.code}</p> : null}
        {bootstrapState.actionHint ? <p className="muted">{bootstrapState.actionHint}</p> : null}
      </main>
    );
  }

  return (
    <div className="agent-layout">
      <div className="profile-grid">
        {error ? <p className="warning-banner">{error}</p> : null}

        <section className="panel" id="overview">
          <h1 className="section-title">Wallet</h1>
          {!profile ? <p className="muted">Loading agent profile...</p> : null}

          {profile ? (
            <>
              <div className="identity-row">
                <strong>{profile.agent.agent_name}</strong>
                {isPublicStatus(profile.agent.public_status) ? <PublicStatusBadge status={profile.agent.public_status} /> : profile.agent.public_status}
                <span className="muted">{profile.agent.runtime_platform}</span>
                <span className="muted">Last activity: {formatUtc(profile.agent.last_activity_at)} UTC</span>
              </div>
              {isStale(profile.agent.last_heartbeat_at, HEARTBEAT_STALE_THRESHOLD_SECONDS) ? (
                <p className="stale">Agent is idle.</p>
              ) : (
                <p className="muted">Idle (heartbeat healthy).</p>
              )}
              {profile.agent.description ? <p style={{ marginTop: '0.8rem' }}>{profile.agent.description}</p> : null}

              <div className="overview-wallet">
                <div style={{ marginTop: '0.8rem' }}>
                  <div className="muted">Address</div>
                  {(() => {
                    const activeWallet = (profile.wallets ?? []).find((w) => w.chain_key === activeChainKey) ?? null;
                    const address = activeWallet?.address ?? null;
                    return (
                      <button
                        type="button"
                        className="copy-pill"
                        disabled={!address}
                        onClick={async () => {
                          if (!address) return;
                          try {
                            await navigator.clipboard.writeText(address);
                            setOverviewDepositCopied(true);
                            window.setTimeout(() => setOverviewDepositCopied(false), 1000);
                          } catch {
                            setOverviewDepositCopied(false);
                          }
                        }}
                        aria-label={address ? 'Copy deposit address' : 'Deposit address unavailable'}
                        title={address ? 'Copy deposit address' : 'Deposit address unavailable'}
                      >
                        <span className="copy-row-icon">
                          <CopyIcon />
                        </span>
                        <span className="copy-row-text">{address ? shortenAddress(address) : '-'}</span>
                      </button>
                    );
                  })()}
                </div>

                <div style={{ marginTop: '0.9rem' }}>
                  <div className="muted">Assets</div>
                  {management.phase === 'ready' ? (
                    <div className="wallet-approvals">
                      <div className="wallet-approvals-row">
                        <label className="wallet-approvals-toggle">
                          <input
                            type="checkbox"
                            checked={policyApprovalMode === 'auto'}
                            onChange={(event) => {
                              const next = event.target.checked ? 'auto' : 'per_trade';
                              void runManagementAction(
                                () =>
                                  managementPost('/api/v1/management/policy/update', buildPolicyUpdatePayload({ approvalMode: next })).then(
                                    () => Promise.resolve()
                                  ),
                                next === 'auto' ? 'Global approval enabled.' : 'Global approval disabled.'
                              );
                            }}
                          />{' '}
                          Approve all
                        </label>
                        <span className="muted">
                          {policyApprovalMode === 'auto'
                            ? 'On: new trades auto-approved.'
                            : 'Off: approvals required unless tokenIn is preapproved.'}
                        </span>
                      </div>
                    </div>
                  ) : null}
                  {(() => {
                  const chain = depositData?.chains?.[0];
                  const balances = chain?.balances ?? [];
                  const byToken = new Map<string, { balance: string; decimals: number }>();
                  for (const row of balances) {
                    if (!row?.token) continue;
                    const token = String(row.token);
                    const balance = String(row.balance ?? '0');
                    const decimals =
                      typeof row.decimals === 'number' && Number.isFinite(row.decimals) ? Math.trunc(row.decimals) : 18;
                    byToken.set(token, { balance, decimals });
                  }

                  const usdcDecimals = byToken.get('USDC')?.decimals ?? 6;
                  const items: Array<{ symbol: string; name: string; decimals: number; raw: string | null }> = [
                    {
                      symbol: 'ETH',
                      name: 'Ethereum',
                      decimals: 18,
                      raw: byToken.get('NATIVE')?.balance ?? null
                    },
                    {
                      symbol: 'WETH',
                      name: 'Wrapped Ether',
                      decimals: 18,
                      raw: byToken.get('WETH')?.balance ?? null
                    },
                    {
                      symbol: 'USDC',
                      name: 'USD Coin',
                      decimals: usdcDecimals,
                      raw: byToken.get('USDC')?.balance ?? null
                    }
                  ];

                  // Room for more tokens: append any other known snapshot tokens.
                  const known = new Set(['NATIVE', 'WETH', 'USDC']);
                  for (const [token, meta] of byToken.entries()) {
                    if (known.has(token)) continue;
                    items.push({ symbol: token, name: 'Token', decimals: meta.decimals ?? 18, raw: meta.balance });
                  }

                    return (
                      <div className="asset-list">
                      {items.map((item) => {
                        const display = item.symbol === 'USDC'
                          ? formatUsdFromBaseUnits(item.raw, item.decimals)
                          : formatUnitsTruncated(item.raw, item.decimals, 4);
                        const preapprovable = item.symbol !== 'ETH' && item.symbol !== 'NATIVE';
                        const approved = management.phase === 'ready' ? isTokenPreapproved(item.symbol) : false;
                        return (
                          <div className="asset-row" key={item.symbol}>
                            <div className="asset-left">
                              <TokenIcon symbol={item.symbol} />
                              <div className="asset-meta">
                                  <div className="asset-symbol">{item.symbol}</div>
                                  <div className="asset-name">{item.name}</div>
                                </div>
                              </div>
                              <div className="asset-right">
                                <div className="asset-balance">
                                  <div className="asset-balance-main">{display}</div>
                                  <div className="asset-balance-sub">{item.symbol}</div>
                                </div>
                                {management.phase === 'ready' && preapprovable ? (
                                  <div className="asset-actions">
                                    <button
                                      type="button"
                                      className={approved ? 'asset-approval-btn asset-approval-btn-on' : 'asset-approval-btn'}
                                      disabled={policyApprovalMode === 'auto'}
                                      onClick={() => {
                                        const nextEnabled = !approved;
                                        void runManagementAction(
                                          () =>
                                            managementPost(
                                              '/api/v1/management/policy/update',
                                              buildPolicyUpdatePayload({
                                                allowedTokens: nextAllowedTokensForSymbol(item.symbol, nextEnabled)
                                              })
                                            ).then(() => Promise.resolve()),
                                          nextEnabled ? `${item.symbol} preapproved.` : `${item.symbol} preapproval removed.`
                                        );
                                      }}
                                      title={
                                        policyApprovalMode === 'auto'
                                          ? 'Global approval is on.'
                                          : approved
                                            ? 'Remove preapproval'
                                            : 'Preapprove tokenIn'
                                      }
                                    >
                                      {approved ? 'Preapproved' : 'Preapprove'}
                                    </button>
                                  </div>
                                ) : null}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    );
                  })()}
                </div>
              </div>
            </>
          ) : null}
        </section>

        <section className="kpi-grid">
          <article className="panel">
            <div className="muted">PnL</div>
            <div className="kpi-value">{formatUsd(profile?.latestMetrics?.pnl_usd ?? null)}</div>
          </article>
          <article className="panel">
            <div className="muted">Return</div>
            <div className="kpi-value">{formatPercent(profile?.latestMetrics?.return_pct ?? null)}</div>
          </article>
          <article className="panel">
            <div className="muted">Volume</div>
            <div className="kpi-value">{formatUsd(profile?.latestMetrics?.volume_usd ?? null)}</div>
          </article>
          <article className="panel">
            <div className="muted">Trades / Followers</div>
            <div className="kpi-value">
              {formatNumber(profile?.latestMetrics?.trades_count ?? null)} / {formatNumber(profile?.latestMetrics?.followers_count ?? null)}
            </div>
          </article>
        </section>

        <section className="panel" id="activity">
          <h2 className="section-title">Activity</h2>
          <p className="muted">Trades and lifecycle events for this agent. Timestamps are UTC.</p>
          {!trades || !activity ? <p className="muted">Loading activity...</p> : null}
          {activityFeed.length === 0 && trades && activity ? <p className="muted">No activity yet.</p> : null}
          {activityFeed.length > 0 ? (
            <div className="wallet-activity-list">
              {activityFeed.map((item) =>
                item.kind === 'trade' ? (
                  <article className="wallet-activity-item" key={`trade:${item.id}`}>
                    <div className="wallet-activity-main">
                      <div className="wallet-activity-title">
                        <strong>Swap</strong>
                        <span className="status-chip">{item.status}</span>
                      </div>
                      <div className="muted">
                        {formatDecimalText(item.amountIn)} {item.tokenInLabel} {'->'}{' '}
                        {item.amountOut ? `${formatDecimalText(item.amountOut)} ` : ''}
                        {item.tokenOutLabel}
                      </div>
                      <div className="muted">{item.pair || `${item.tokenIn} -> ${item.tokenOut}`}</div>
                      {item.txHash ? <div className="muted hard-wrap">Tx: {shortenHex(item.txHash, 10, 8)}</div> : null}
                      {item.reason ? <div className="muted">Reason: {item.reason}</div> : null}
                    </div>
                    <div className="wallet-activity-meta muted">{formatUtc(item.at)} UTC</div>
                  </article>
                ) : (
                  <article className="wallet-activity-item" key={`event:${item.id}`}>
                    <div className="wallet-activity-main">
                      <div className="wallet-activity-title">
                        <strong>{formatActivityTitle(item.eventType)}</strong>
                      </div>
                      <div className="muted">
                        {item.pairDisplay ?? `${item.tokenInSymbol ?? 'token'} -> ${item.tokenOutSymbol ?? 'token'}`}
                      </div>
                    </div>
                    <div className="wallet-activity-meta muted">{formatUtc(item.at)} UTC</div>
                  </article>
                )
              )}
            </div>
          ) : null}
          {profile?.copyBreakdown ? (
            <div style={{ marginTop: '0.8rem' }}>
              <div className="muted">Copy Breakdown (7d)</div>
              <div>
                Self trades: {formatNumber(profile.copyBreakdown.selfTradesCount)} | Copied trades:{' '}
                {formatNumber(profile.copyBreakdown.copiedTradesCount)}
              </div>
              <div>
                Self PnL: {formatUsd(profile.copyBreakdown.selfPnlUsd)} | Copied PnL: {formatUsd(profile.copyBreakdown.copiedPnlUsd)}
              </div>
            </div>
          ) : null}
        </section>
      </div>

      <aside className="management-rail" id="management">
        <section className="panel">
          <h2 className="section-title">Management</h2>
          <p className="muted">
            Session:{' '}
            {management.phase === 'ready'
              ? 'Management session active for this host.'
              : management.phase === 'unauthorized'
                ? 'No active management session for this host.'
                : 'Checking management session...'}
          </p>

          {managementNotice ? <p className="success-banner">{managementNotice}</p> : null}
          {managementError ? <p className="warning-banner">{managementError}</p> : null}

          {management.phase === 'loading' ? <p className="muted">Loading management state...</p> : null}
          {management.phase === 'unauthorized' ? (
            <div className="muted">
              <p>Unauthorized: management controls require a bootstrap token session on this host.</p>
              <p>Owner links are one-time use. If one was already used elsewhere, ask the agent to generate a fresh link.</p>
              <p>Open the fresh link directly on https://xclaw.trade.</p>
            </div>
          ) : null}
          {management.phase === 'error' ? <p className="warning-banner">{management.message}</p> : null}

          {management.phase === 'ready' ? (
            <div className="management-stack">
              <article className="management-card">
                <h3>Session</h3>
                <p className="muted">Session expires at {formatUtc(management.data.managementSession.expiresAt)} UTC.</p>
              </article>

              <article className="management-card">
                <h3>Safety Controls</h3>
                <p className="muted">Control runtime safety and outbound transfer restrictions.</p>
                <div className="toolbar">
                  <button
                    type="button"
                    className="theme-toggle"
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
                    className="theme-toggle"
                    onClick={() =>
                      void runManagementAction(
                        () => managementPost('/api/v1/management/resume', { agentId }).then(() => Promise.resolve()),
                        'Agent resumed.'
                      )
                    }
                  >
                    Resume Agent
                  </button>
                </div>
                <div className="toolbar">
                  <label>
                    <input
                      type="checkbox"
                      checked={outboundTransfersEnabled}
                      onChange={(event) => setOutboundTransfersEnabled(event.target.checked)}
                    />{' '}
                    Outbound transfers enabled
                  </label>
                  <select
                    value={outboundMode}
                    onChange={(event) => setOutboundMode((event.target.value as 'disabled' | 'allow_all' | 'whitelist') ?? 'disabled')}
                  >
                    <option value="disabled">disabled</option>
                    <option value="allow_all">allow_all</option>
                    <option value="whitelist">whitelist</option>
                  </select>
                </div>
                <div className="toolbar">
                  <input
                    value={outboundWhitelistInput}
                    onChange={(event) => setOutboundWhitelistInput(event.target.value)}
                    placeholder="Comma-separated whitelist addresses"
                  />
                </div>
                <div className="toolbar">
                  <button
                    className="theme-toggle"
                    type="button"
                    onClick={() =>
                      void runManagementAction(
                        () =>
                          managementPost('/api/v1/management/policy/update', {
                            agentId,
                            mode: 'real',
                            approvalMode: policyApprovalMode,
                            maxTradeUsd: policyMaxTradeUsd,
                            maxDailyUsd: policyMaxDailyUsd,
                            dailyCapUsdEnabled: policyDailyCapUsdEnabled,
                            dailyTradeCapEnabled: policyDailyTradeCapEnabled,
                            maxDailyTradeCount: policyDailyTradeCapEnabled ? Number(policyMaxDailyTradeCount || '0') : null,
                            allowedTokens: policyAllowedTokens,
                            outboundTransfersEnabled,
                            outboundMode,
                            outboundWhitelistAddresses: outboundWhitelistInput
                              .split(',')
                              .map((value) => value.trim())
                              .filter((value) => value.length > 0)
                          }).then(() => Promise.resolve()),
                        'Transfer policy saved.'
                      )
                    }
                  >
                    Save Transfer Policy
                  </button>
                </div>
              </article>

              <article className="management-card">
                <h3>Chain Access</h3>
                <p className="muted">Enable or disable agent trading and wallet-send for the active chain.</p>
                <p className="muted">
                  Active chain: <strong>{activeChainLabel}</strong>
                </p>
                <div className="toolbar">
                  <label>
                    <input
                      type="checkbox"
                      checked={management.data.chainPolicy?.chainEnabled ?? true}
                      disabled={chainUpdatePending}
                      onChange={(event) => {
                        const next = Boolean(event.target.checked);
                        setChainUpdatePending(true);
                        void (async () => {
                          await runManagementAction(
                            () =>
                              managementPost('/api/v1/management/chains/update', {
                                agentId,
                                chainKey: activeChainKey,
                                chainEnabled: next
                              }).then(() => Promise.resolve()),
                            next ? 'Chain enabled.' : 'Chain disabled.'
                          );
                          setChainUpdatePending(false);
                        })();
                      }}
                    />{' '}
                    Chain enabled
                  </label>
                  <span className="muted">
                    {management.data.chainPolicy?.updatedAt ? `Updated ${formatUtc(management.data.chainPolicy.updatedAt)} UTC` : 'Default: enabled'}
                  </span>
                </div>
                {management.data.chainPolicy?.chainEnabled ? (
                  <p className="muted">Agent trading + wallet send are allowed on this chain.</p>
                ) : (
                  <p className="warning-banner">Disabled: agent cannot trade or wallet-send on this chain.</p>
                )}
              </article>

              <article className="management-card">
                <h3>Deposit and Withdraw</h3>
                <p className="muted">Deposit address and withdrawals for the active chain.</p>
                {depositData?.chains?.[0]?.depositAddress ? (
                  <button
                    type="button"
                    className="copy-row"
                    onClick={async () => {
                      try {
                        await navigator.clipboard.writeText(depositData.chains[0].depositAddress);
                        setDepositCopied(true);
                        window.setTimeout(() => setDepositCopied(false), 1000);
                      } catch {
                        setDepositCopied(false);
                      }
                    }}
                    aria-label="Copy deposit address"
                    title="Copy deposit address"
                  >
                    <span className="copy-row-icon">
                      <CopyIcon />
                    </span>
                    <span className="copy-row-text">
                      {depositData.chains[0].chainKey}: {shortenAddress(depositData.chains[0].depositAddress)}
                    </span>
                  </button>
                ) : (
                  <p className="muted">Loading deposit address...</p>
                )}

                <div className="toolbar" style={{ marginTop: '0.6rem' }}>
                  <input
                    value={withdrawDestination}
                    onChange={(event) => setWithdrawDestination(event.target.value)}
                    placeholder="Withdraw destination 0x..."
                  />
                  <input value={withdrawAmount} onChange={(event) => setWithdrawAmount(event.target.value)} placeholder="Amount (ETH)" />
                </div>
                <div className="toolbar">
                  <button
                    type="button"
                    className="theme-toggle"
                    onClick={() =>
                      void runManagementAction(
                        () =>
                          managementPost('/api/v1/management/withdraw/destination', {
                            agentId,
                            chainKey: activeChainKey,
                            destination: withdrawDestination
                          }).then(() => Promise.resolve()),
                        'Withdraw destination saved.'
                      )
                    }
                  >
                    Save Destination
                  </button>
                  <button
                    type="button"
                    className="theme-toggle"
                    onClick={() =>
                      void runManagementAction(
                        () =>
                          managementPost('/api/v1/management/withdraw', {
                            agentId,
                            chainKey: activeChainKey,
                            asset: 'ETH',
                            amount: withdrawAmount,
                            destination: withdrawDestination
                          }).then(() => Promise.resolve()),
                        'Withdraw request submitted.'
                      )
                    }
                  >
                    Request Withdraw
                  </button>
                </div>
              </article>

              <article className="management-card">
                <h3>Risk Limits</h3>
                <div className="toolbar">
                  <label>
                    <input
                      type="checkbox"
                      checked={policyDailyCapUsdEnabled}
                      onChange={(event) => setPolicyDailyCapUsdEnabled(event.target.checked)}
                    />{' '}
                    Daily USD cap enabled
                  </label>
                  <label>
                    <input
                      type="checkbox"
                      checked={policyDailyTradeCapEnabled}
                      onChange={(event) => setPolicyDailyTradeCapEnabled(event.target.checked)}
                    />{' '}
                    Daily trade-count cap enabled
                  </label>
                </div>
                <div className="toolbar">
                  <input value={policyMaxTradeUsd} onChange={(event) => setPolicyMaxTradeUsd(event.target.value)} placeholder="Max Trade USD" />
                  <input
                    value={policyMaxDailyUsd}
                    onChange={(event) => setPolicyMaxDailyUsd(event.target.value)}
                    placeholder="Max Daily USD"
                    disabled={!policyDailyCapUsdEnabled}
                  />
                  <input
                    value={policyMaxDailyTradeCount}
                    onChange={(event) => setPolicyMaxDailyTradeCount(event.target.value.replace(/[^0-9]/g, ''))}
                    placeholder="Max Daily Trades"
                    disabled={!policyDailyTradeCapEnabled}
                  />
                </div>
                <div className="toolbar">
                  <button
                    type="button"
                    className="theme-toggle"
                    onClick={() =>
                      void runManagementAction(
                        () =>
                          managementPost('/api/v1/management/policy/update', {
                            agentId,
                            mode: 'real',
                            approvalMode: policyApprovalMode,
                            maxTradeUsd: policyMaxTradeUsd,
                            maxDailyUsd: policyMaxDailyUsd,
                            dailyCapUsdEnabled: policyDailyCapUsdEnabled,
                            dailyTradeCapEnabled: policyDailyTradeCapEnabled,
                            maxDailyTradeCount: policyDailyTradeCapEnabled ? Number(policyMaxDailyTradeCount || '0') : null,
                            allowedTokens: policyAllowedTokens
                          }).then(() => Promise.resolve()),
                        'Policy saved.'
                      )
                    }
                  >
                    Save Policy
                  </button>
                </div>
              </article>

              <article className="management-card">
                <h3>Approval Delivery</h3>
                <p className="muted">Optional Telegram inline-button approvals for pending trades (approve-only).</p>
                <p className="muted">
                  Active chain: <strong>{activeChainLabel}</strong>
                </p>
                <div className="toolbar">
                  <label>
                    <input
                      type="checkbox"
                      checked={telegramApprovalsEnabled}
                      disabled={telegramUpdatePending}
                      onChange={(event) => {
                              const next = Boolean(event.target.checked);
                              setTelegramUpdatePending(true);
                              void (async () => {
                                await runManagementAction(
                                  async () => {
                                    await managementPost('/api/v1/management/approval-channels/update', {
                                      agentId,
                                      chainKey: activeChainKey,
                                      channel: 'telegram',
                                      enabled: next
                                    });
                                    setTelegramApprovalsEnabled(next);
                                  },
                                  next ? 'Telegram approvals enabled.' : 'Telegram approvals disabled.'
                                );
                                setTelegramUpdatePending(false);
                              })();
                            }}
                          />{' '}
                          Telegram approvals enabled
                        </label>
                        <span className="muted">{telegramApprovalsEnabled ? 'On: runtime may send approve prompts.' : 'Off: web UI only.'}</span>
                      </div>
                    </article>

              <article className="management-card">
                <h3>Usage Progress</h3>
                <p className="muted">UTC day: {management.data.dailyUsage.utcDay}</p>
                <div className="usage-row">
                  <div className="muted">Used Today USD</div>
                  <div>
                    {management.data.dailyUsage.dailySpendUsd} / {policyDailyCapUsdEnabled ? policyMaxDailyUsd : 'No cap'}
                  </div>
                  <div className="usage-bar">
                    <div
                      className="usage-bar-fill"
                      style={{
                        width: `${usagePercent(
                          Number(management.data.dailyUsage.dailySpendUsd || '0'),
                          policyMaxDailyUsd,
                          policyDailyCapUsdEnabled
                        )}%`
                      }}
                    />
                  </div>
                </div>
                <div className="usage-row">
                  <div className="muted">Filled Trades Today</div>
                  <div>
                    {management.data.dailyUsage.dailyFilledTrades} / {policyDailyTradeCapEnabled ? policyMaxDailyTradeCount : 'No cap'}
                  </div>
                  <div className="usage-bar">
                    <div
                      className="usage-bar-fill"
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
              </article>

              <article className="management-card">
                <h3>Trading Operations</h3>
                {limitOrders.length === 0 ? <p className="muted">No limit orders.</p> : null}
                {limitOrders.map((item) => (
                  <div key={item.orderId} className="queue-item">
                    <div>
                      <strong>
                        {item.side.toUpperCase()} {item.amountIn}
                      </strong>
                      <div className="muted">{item.chainKey}</div>
                      <div className="muted">Status: {item.status}</div>
                      <div className="muted">
                        {shortenAddress(item.tokenIn)} {'->'} {shortenAddress(item.tokenOut)} @ {item.limitPrice}
                      </div>
                    </div>
                    {item.status === 'open' || item.status === 'triggered' ? (
                      <button
                        type="button"
                        className="theme-toggle"
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
                    ) : null}
                  </div>
                ))}
                <p className="muted">Limit order creation is agent-driven. Owners can review and cancel orders here.</p>
              </article>

              <article className="management-card">
                <h3>Approval Queue</h3>
                {management.data.approvalsQueue.length === 0 ? <p className="muted">No pending approvals.</p> : null}
                {management.data.approvalsQueue.map((item) => (
                  <div key={item.trade_id} className="queue-item">
                    <div>
                      {(() => {
                        const symbolByAddress = new Map<string, string>();
                        for (const entry of management.data.chainTokens ?? []) {
                          symbolByAddress.set(normalizeHexAddress(entry.address), entry.symbol);
                        }
                        const tokenInLabel = item.token_in.startsWith('0x')
                          ? symbolByAddress.get(normalizeHexAddress(item.token_in)) ?? shortenAddress(item.token_in)
                          : item.token_in;
                        const tokenOutLabel = item.token_out.startsWith('0x')
                          ? symbolByAddress.get(normalizeHexAddress(item.token_out)) ?? shortenAddress(item.token_out)
                          : item.token_out;
                        return (
                          <>
                            <strong>
                              {formatDecimalText(item.amount_in)} {tokenInLabel} {'->'} {tokenOutLabel}
                            </strong>
                            <div className="muted">{shortenHex(item.trade_id, 10, 8)}</div>
                          </>
                        );
                      })()}
                      <div className="muted">{formatUtc(item.created_at)} UTC</div>
                    </div>
                    <div className="toolbar">
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
                        className="theme-toggle"
                        disabled={!management.data.chainPolicy?.chainEnabled && item.chain_key === activeChainKey}
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
                        Approve Trade
                      </button>
                      <button
                        type="button"
                        className="theme-toggle"
                        onClick={() =>
                          void runManagementAction(
                            () =>
                              managementPost('/api/v1/management/approvals/decision', {
                                agentId,
                                tradeId: item.trade_id,
                                decision: 'reject',
                                reasonCode: 'approval_rejected',
                                reasonMessage: (approvalRejectReasons[item.trade_id] ?? '').trim() || 'Rejected by owner.'
                              }).then(() => Promise.resolve()),
                            `Rejected ${item.trade_id}`
                          )
                        }
                      >
                        Reject Trade
                      </button>
                    </div>
                  </div>
                ))}
              </article>

              <article className="management-card">
                <details className="mgmt-details" open>
                  <summary>Management Audit Log</summary>
                  {management.data.auditLog.length === 0 ? <p className="muted">No audit entries.</p> : null}
                  <div className="audit-list">
                    {management.data.auditLog.map((entry) => (
                      <div className="audit-item" key={entry.audit_id}>
                        <div>
                          <strong>{entry.action_type}</strong> ({entry.action_status})
                        </div>
                        <div className="muted">{formatUtc(entry.created_at)} UTC</div>
                      </div>
                    ))}
                  </div>
                </details>
              </article>
            </div>
          ) : null}
        </section>
      </aside>
    </div>
  );
}
