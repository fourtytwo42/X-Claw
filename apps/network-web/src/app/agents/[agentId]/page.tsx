'use client';

import Link from 'next/link';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useParams, useRouter, useSearchParams } from 'next/navigation';

import { ChainHeaderControl } from '@/components/chain-header-control';
import { rememberManagedAgent } from '@/components/management-header-controls';
import { PrimaryNav } from '@/components/primary-nav';
import { PublicStatusBadge } from '@/components/public-status-badge';
import { ThemeToggle } from '@/components/theme-toggle';
import { nativeDecimalsForChainKey, nativeSymbolForChainKey, useActiveChainKey } from '@/lib/active-chain';
import { getAgentAvatarPalette, getAgentInitial } from '@/lib/agent-avatar-color';
import { fetchWithTimeout, uiFetchTimeoutMs } from '@/lib/fetch-timeout';
import {
  buildHoldings,
  formatActivityTitle,
  formatDecimalText,
  formatUnitsTruncated,
  resolveTokenLabel,
  type ActivityPayload,
  type AgentProfilePayload,
  type DepositPayload,
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

type SessionAgentsPayload = {
  managedAgents?: string[];
  activeAgentId?: string;
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
  resource_description: string | null;
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
  resourceDescription?: string | null;
  linkToken?: string | null;
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

const FAVORITES_KEY = 'xclaw_explore_favorite_agent_ids';
const MANAGED_AGENT_TOKENS_KEY = 'xclaw_managed_agent_tokens';

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
  window.dispatchEvent(new Event('xclaw:favorites-updated'));
}

function parseStoredManagedAgentTokens(): Record<string, string> {
  if (typeof window === 'undefined') {
    return {};
  }
  try {
    const raw = window.localStorage.getItem(MANAGED_AGENT_TOKENS_KEY);
    if (!raw) {
      return {};
    }
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
      return {};
    }
    const out: Record<string, string> = {};
    for (const [agentId, token] of Object.entries(parsed)) {
      if (typeof agentId !== 'string' || !agentId.trim() || typeof token !== 'string' || !token.trim()) {
        continue;
      }
      out[agentId.trim()] = token.trim();
    }
    return out;
  } catch {
    return {};
  }
}

function rememberManagedAgentToken(agentId: string, token: string) {
  if (typeof window === 'undefined') {
    return;
  }
  const normalizedAgentId = String(agentId).trim();
  const normalizedToken = String(token).trim();
  if (!normalizedAgentId || !normalizedToken) {
    return;
  }
  const current = parseStoredManagedAgentTokens();
  current[normalizedAgentId] = normalizedToken;
  window.localStorage.setItem(MANAGED_AGENT_TOKENS_KEY, JSON.stringify(current));
}

function forgetManagedAgentToken(agentId: string) {
  if (typeof window === 'undefined') {
    return;
  }
  const normalizedAgentId = String(agentId).trim();
  if (!normalizedAgentId) {
    return;
  }
  const current = parseStoredManagedAgentTokens();
  if (!current[normalizedAgentId]) {
    return;
  }
  delete current[normalizedAgentId];
  window.localStorage.setItem(MANAGED_AGENT_TOKENS_KEY, JSON.stringify(current));
}

function testIdSafePart(value: string): string {
  return String(value).trim().toLowerCase().replace(/[^a-z0-9_-]+/g, '-');
}

async function managementPost(path: string, payload: Record<string, unknown>) {
  const csrf = getCsrfToken();
  const headers: Record<string, string> = { 'content-type': 'application/json' };
  if (csrf) {
    headers['x-csrf-token'] = csrf;
  }

  const response = await fetchWithTimeout(
    path,
    {
      method: 'POST',
      credentials: 'same-origin',
      headers,
      body: JSON.stringify(payload)
    },
    uiFetchTimeoutMs(),
  );

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

  const response = await fetchWithTimeout(
    path,
    {
      method: 'GET',
      credentials: 'same-origin',
      headers,
      cache: 'no-store'
    },
    uiFetchTimeoutMs(),
  );
  const json = (await response.json().catch(() => null)) as { message?: string } | null;
  if (!response.ok) {
    throw new Error(json?.message ?? 'Management request failed.');
  }
  return json;
}

async function managementDelete(path: string, payload: Record<string, unknown>) {
  const csrf = getCsrfToken();
  const headers: Record<string, string> = { 'content-type': 'application/json' };
  if (csrf) {
    headers['x-csrf-token'] = csrf;
  }

  const response = await fetchWithTimeout(
    path,
    {
      method: 'DELETE',
      credentials: 'same-origin',
      headers,
      body: JSON.stringify(payload)
    },
    uiFetchTimeoutMs(),
  );
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

async function bootstrapSession(
  agentId: string,
  token: string
): Promise<{ ok: true } | { ok: false; message: string; code?: string; actionHint?: string }> {
  const response = await fetchWithTimeout(
    '/api/v1/management/session/bootstrap',
    {
      method: 'POST',
      headers: {
        'content-type': 'application/json'
      },
      credentials: 'same-origin',
      body: JSON.stringify({ agentId, token })
    },
    uiFetchTimeoutMs(),
  );

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

async function selectManagementSession(agentId: string, token: string): Promise<boolean> {
  const response = await fetchWithTimeout(
    '/api/v1/management/session/select',
    {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify({ agentId, token })
    },
    uiFetchTimeoutMs(),
  );
  return response.ok;
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
    return 'Turn on approve for all trades';
  }
  if (item.request_type === 'global_approval_disable') {
    return 'Turn off approve for all trades';
  }
  if (item.request_type === 'token_preapprove_add') {
    if (!item.token_address) {
      return 'Approve token';
    }
    return `Approve ${map.get(item.token_address.toLowerCase()) ?? shortenAddress(item.token_address)}`;
  }
  if (item.request_type === 'token_preapprove_remove') {
    if (!item.token_address) {
      return 'Remove token auto-approval';
    }
    return `Remove ${map.get(item.token_address.toLowerCase()) ?? shortenAddress(item.token_address)} auto-approval`;
  }
  return humanizeKeyLabel(item.request_type);
}

function normalizeTokenSelectionSymbol(value: string | null | undefined, nativeSymbol = 'ETH'): string {
  const raw = String(value ?? '').trim();
  if (!raw) {
    return '';
  }
  const upper = raw.toUpperCase();
  const nativeUpper = nativeSymbol.trim().toUpperCase() || 'ETH';
  if (upper === 'NATIVE' || upper === nativeUpper || upper.endsWith(` ${nativeUpper}`)) {
    return nativeUpper;
  }
  if (upper === 'ETH' || upper.endsWith(' ETH')) {
    return 'ETH';
  }
  return upper;
}

function humanizeKeyLabel(value: string | null | undefined): string {
  const normalized = String(value ?? '').trim();
  if (!normalized) {
    return 'Unknown';
  }
  return normalized
    .replace(/[_-]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .split(' ')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase())
    .join(' ');
}

function displayStatusLabel(status: string | null | undefined): string {
  const normalized = String(status ?? '').trim().toLowerCase();
  if (!normalized) {
    return 'Unknown';
  }
  const map: Record<string, string> = {
    approval_pending: 'Waiting for approval',
    pending: 'Pending',
    approved: 'Approved',
    rejected: 'Rejected',
    denied: 'Denied',
    deny: 'Denied',
    filled: 'Completed',
    executed: 'Completed',
    executing: 'Processing',
    failed: 'Failed',
    proposed: 'Created',
    open: 'Open',
    triggered: 'Triggered'
  };
  return map[normalized] ?? humanizeKeyLabel(normalized);
}

function auditEntryLabel(entry: { action_type: string; action_status: string; public_redacted_payload: Record<string, unknown> }): string {
  const base = `${entry.action_type} (${entry.action_status})`;
  if (entry.action_type !== 'transfer_approval.decision') {
    return base;
  }
  const decision = String(entry.public_redacted_payload?.decision ?? '').trim().toLowerCase();
  if (decision === 'approve') {
    return `${base} - decision: approve`;
  }
  if (decision === 'deny') {
    return `${base} - decision: deny`;
  }
  return base;
}

function formatAuditValue(value: unknown): string {
  if (value === null || value === undefined) {
    return 'null';
  }
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
    const text = String(value).trim();
    return text.length > 0 ? text : 'empty';
  }
  if (Array.isArray(value)) {
    if (value.length === 0) {
      return '[]';
    }
    return value.map((item) => formatAuditValue(item)).join(', ');
  }
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

function auditEntryDetails(entry: { public_redacted_payload: Record<string, unknown> }): string {
  const payload = entry.public_redacted_payload ?? {};
  const keys = Object.keys(payload);
  if (keys.length === 0) {
    return 'No public details recorded.';
  }
  const preferredOrder = ['decision', 'approvalId', 'tradeId', 'policyApprovalId', 'requestId', 'agentId', 'chainKey', 'reasonCode', 'reasonMessage'];
  const ordered = [
    ...preferredOrder.filter((key) => keys.includes(key)),
    ...keys.filter((key) => !preferredOrder.includes(key)).sort((a, b) => a.localeCompare(b))
  ];
  const lines = ordered.slice(0, 10).map((key) => `${humanizeKeyLabel(key)}: ${formatAuditValue(payload[key])}`);
  if (ordered.length > 10) {
    lines.push(`Additional fields: ${ordered.length - 10}`);
  }
  return lines.join(' | ');
}

export default function AgentPublicProfilePage() {
  const params = useParams<{ agentId: string }>();
  const router = useRouter();
  const searchParams = useSearchParams();
  const agentId = params.agentId;
  const bootstrapToken = searchParams.get('token')?.trim() ?? '';
  const [activeChainKey, , activeChainLabel] = useActiveChainKey();
  const activeNativeSymbol = useMemo(() => nativeSymbolForChainKey(activeChainKey), [activeChainKey]);
  const activeNativeDecimals = useMemo(() => nativeDecimalsForChainKey(activeChainKey), [activeChainKey]);
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

  const [policyApprovalMode, setPolicyApprovalMode] = useState<'per_trade' | 'auto'>('per_trade');
  const [policyMaxTradeUsd, setPolicyMaxTradeUsd] = useState('50');
  const [policyMaxDailyUsd, setPolicyMaxDailyUsd] = useState('250');
  const [policyDailyCapUsdEnabled, setPolicyDailyCapUsdEnabled] = useState(true);
  const [policyDailyTradeCapEnabled, setPolicyDailyTradeCapEnabled] = useState(true);
  const [policyMaxDailyTradeCount, setPolicyMaxDailyTradeCount] = useState('0');
  const [policyAllowedTokens, setPolicyAllowedTokens] = useState<string[]>([]);
  const toastIdRef = useRef(0);
  const toastTimersRef = useRef<Map<number, number>>(new Map());
  const [viewerTracked, setViewerTracked] = useState(false);
  const [viewerTrackingBusy, setViewerTrackingBusy] = useState(false);
  const [viewerTrackingContext, setViewerTrackingContext] = useState<{ mode: 'local' } | { mode: 'server'; activeAgentId: string }>({
    mode: 'local'
  });

  const isOwner = management.phase === 'ready';

  const refreshViewerTracked = useCallback(async () => {
    if (!agentId || isOwner) {
      return;
    }

    const localIds = parseStoredIds(FAVORITES_KEY);
    setViewerTracked(localIds.includes(agentId));
    setViewerTrackingContext({ mode: 'local' });

    try {
      const sessionResponse = await fetchWithTimeout(
        '/api/v1/management/session/agents',
        {
          credentials: 'same-origin',
          cache: 'no-store'
        },
        uiFetchTimeoutMs(),
      );
      if (!sessionResponse.ok) {
        return;
      }
      const sessionPayload = (await sessionResponse.json()) as SessionAgentsPayload;
      const activeManagedAgentId = String(sessionPayload.activeAgentId ?? '').trim();
      if (!activeManagedAgentId) {
        return;
      }
      const trackedResponse = await fetchWithTimeout(
        `/api/v1/management/tracked-agents?agentId=${encodeURIComponent(activeManagedAgentId)}&chainKey=${encodeURIComponent(activeChainKey)}`,
        {
          credentials: 'same-origin',
          cache: 'no-store'
        },
        uiFetchTimeoutMs(),
      );
      if (!trackedResponse.ok) {
        return;
      }
      const trackedPayload = (await trackedResponse.json()) as {
        items?: Array<{ trackedAgentId?: string }>;
      };
      const ids = Array.isArray(trackedPayload.items)
        ? trackedPayload.items.map((item) => String(item?.trackedAgentId ?? '').trim()).filter((item) => item.length > 0)
        : [];
      setViewerTracked(ids.includes(agentId));
      setViewerTrackingContext({ mode: 'server', activeAgentId: activeManagedAgentId });
    } catch {
      // local fallback is already applied
    }
  }, [activeChainKey, agentId, isOwner]);

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

  async function toggleViewerTracked() {
    if (isOwner || !agentId || viewerTrackingBusy) {
      return;
    }

    setViewerTrackingBusy(true);
    const nextTracked = !viewerTracked;
    try {
      if (viewerTrackingContext.mode === 'server') {
        if (nextTracked) {
          await managementPost('/api/v1/management/tracked-agents', {
            agentId: viewerTrackingContext.activeAgentId,
            trackedAgentId: agentId
          });
        } else {
          await managementDelete('/api/v1/management/tracked-agents', {
            agentId: viewerTrackingContext.activeAgentId,
            trackedAgentId: agentId
          });
        }
        setViewerTracked(nextTracked);
        window.dispatchEvent(new Event('xclaw:favorites-updated'));
      } else {
        const current = parseStoredIds(FAVORITES_KEY);
        const next = nextTracked ? Array.from(new Set([...current, agentId])) : current.filter((item) => item !== agentId);
        storeIds(FAVORITES_KEY, next);
        setViewerTracked(nextTracked);
      }
      showToast(nextTracked ? 'Agent saved for tracking.' : 'Agent removed from tracking.', 'success');
    } catch (toggleError) {
      showToast(toggleError instanceof Error ? toggleError.message : 'Failed to update tracked state.', 'error', 3200);
    } finally {
      setViewerTrackingBusy(false);
    }
  }

  useEffect(() => {
    if (!agentId) {
      return;
    }

    if (!bootstrapToken) {
      setBootstrapState({ phase: 'ready' });
      return;
    }

    setBootstrapState({ phase: 'bootstrapping' });
    void bootstrapSession(agentId, bootstrapToken).then((result) => {
      if (!result.ok) {
        setBootstrapState({
          phase: 'error',
          message: result.message,
          code: result.code,
          actionHint: result.actionHint
        });
        return;
      }

      rememberManagedAgentToken(agentId, bootstrapToken);
      rememberManagedAgent(agentId);
      router.replace(`/agents/${agentId}`);
      setBootstrapState({ phase: 'ready' });
    });
  }, [agentId, bootstrapToken, router]);

  const loadPublicData = useCallback(async () => {
    const [profileRes, tradesRes, activityRes] = await Promise.all([
      fetchWithTimeout(
        `/api/v1/public/agents/${agentId}?chainKey=${encodeURIComponent(activeChainKey)}`,
        { cache: 'no-store' },
        uiFetchTimeoutMs(),
      ),
      fetchWithTimeout(
        `/api/v1/public/agents/${agentId}/trades?limit=30&chainKey=${encodeURIComponent(activeChainKey)}`,
        { cache: 'no-store' },
        uiFetchTimeoutMs(),
      ),
      fetchWithTimeout(
        `/api/v1/public/activity?limit=30&agentId=${encodeURIComponent(agentId)}&chainKey=${encodeURIComponent(activeChainKey)}`,
        {
          cache: 'no-store'
        },
        uiFetchTimeoutMs(),
      )
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
  }, [activeChainKey, agentId]);

  const loadManagementData = useCallback(async () => {
    async function fetchManagementState() {
      return fetchWithTimeout(
        `/api/v1/management/agent-state?agentId=${encodeURIComponent(agentId)}&chainKey=${encodeURIComponent(activeChainKey)}`,
        {
          cache: 'no-store',
          credentials: 'same-origin'
        },
        uiFetchTimeoutMs(),
      );
    }

    let managementRes = await fetchManagementState();

    if (managementRes.status === 401) {
      const candidateTokens = Array.from(new Set([bootstrapToken, parseStoredManagedAgentTokens()[agentId]].filter((item) => Boolean(item))));
      for (const candidateToken of candidateTokens) {
        const restored = await selectManagementSession(agentId, candidateToken);
        if (!restored) {
          continue;
        }
        rememberManagedAgentToken(agentId, candidateToken);
        managementRes = await fetchManagementState();
        if (managementRes.status !== 401) {
          break;
        }
      }
    }

    if (managementRes.status === 401) {
      const storedToken = parseStoredManagedAgentTokens()[agentId];
      if (storedToken) {
        const restored = await selectManagementSession(agentId, storedToken);
        if (restored) {
          managementRes = await fetchManagementState();
        } else {
          forgetManagedAgentToken(agentId);
        }
      }
    }

    if (managementRes.status === 401) {
      let authMessage = 'Management session is missing, expired, or scoped to a different agent.';
      let authDetails: Record<string, unknown> | null = null;
      try {
        const payload = (await managementRes.json()) as {
          message?: string;
          actionHint?: string;
          details?: Record<string, unknown>;
        };
        if (payload?.message) {
          authMessage = payload.message;
        }
        if (payload?.details && typeof payload.details === 'object') {
          authDetails = payload.details;
        }
      } catch {
        // keep fallback message
      }

      let sessionAgentId = '';
      try {
        const sessionRes = await fetchWithTimeout(
          '/api/v1/management/session/agents',
          {
            credentials: 'same-origin',
            cache: 'no-store'
          },
          uiFetchTimeoutMs(),
        );
        if (sessionRes.ok) {
          const sessionPayload = (await sessionRes.json()) as { activeAgentId?: string };
          sessionAgentId = String(sessionPayload.activeAgentId ?? '').trim();
        }
      } catch {
        // best effort only
      }

      const expectedFromDetails = String(authDetails?.requestedAgentId ?? '').trim();
      const sessionFromDetails = String(authDetails?.sessionAgentId ?? '').trim();
      const expectedAgentId = expectedFromDetails || agentId;
      const activeAgent = sessionFromDetails || sessionAgentId || 'none';
      const debugMessage = `Owner session mismatch. Expected ${expectedAgentId}, active session ${activeAgent}. Re-open the exact owner link for this agent.`;
      console.warn('[agents-page] management unauthorized', {
        agentId,
        bootstrapTokenPresent: Boolean(bootstrapToken),
        storedTokenPresent: Boolean(parseStoredManagedAgentTokens()[agentId]),
        activeChainKey,
        authMessage,
        authDetails,
        sessionAgentId
      });
      setError(debugMessage);
      setManagement({ phase: 'unauthorized' });
      setDepositData(null);
      setX402Payments(null);
      setX402ReceiveLink(null);
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

    const [depositPayload, x402PaymentsPayload, x402ReceivePayload] = await Promise.all([
      managementGet(`/api/v1/management/deposit?agentId=${encodeURIComponent(agentId)}&chainKey=${encodeURIComponent(activeChainKey)}`),
      managementGet(`/api/v1/management/x402/payments?agentId=${encodeURIComponent(agentId)}&chainKey=${encodeURIComponent(activeChainKey)}`),
      managementGet(`/api/v1/management/x402/receive-link?agentId=${encodeURIComponent(agentId)}&chainKey=${encodeURIComponent(activeChainKey)}`)
    ]);

    setDepositData(depositPayload as DepositPayload);
    setX402Payments(x402PaymentsPayload as X402PaymentsPayload);
    setX402ReceiveLink(x402ReceivePayload as X402ReceiveLinkPayload);
  }, [activeChainKey, agentId, bootstrapToken]);

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

  useEffect(() => {
    if (!agentId || isOwner) {
      setViewerTracked(false);
      setViewerTrackingContext({ mode: 'local' });
      return;
    }

    void refreshViewerTracked();

    const onStorage = (event: StorageEvent) => {
      if (event.key === FAVORITES_KEY) {
        void refreshViewerTracked();
      }
    };
    const onFavoritesUpdated = () => {
      void refreshViewerTracked();
    };

    window.addEventListener('storage', onStorage);
    window.addEventListener('xclaw:favorites-updated', onFavoritesUpdated);
    return () => {
      window.removeEventListener('storage', onStorage);
      window.removeEventListener('xclaw:favorites-updated', onFavoritesUpdated);
    };
  }, [agentId, isOwner, refreshViewerTracked]);

  function applyOptimisticTradeDecision(tradeId: string, nextStatus: 'approved' | 'rejected') {
    setManagement((current) => {
      if (current.phase !== 'ready') {
        return current;
      }
      const nowIso = new Date().toISOString();
      const queueItem = current.data.approvalsQueue.find((item) => item.trade_id === tradeId) ?? null;
      const nextQueue = current.data.approvalsQueue.filter((item) => item.trade_id !== tradeId);
      const existingHistory = current.data.approvalsHistory ?? [];
      const already = existingHistory.find((item) => item.trade_id === tradeId);
      const nextHistoryRow =
        already ??
        (queueItem
          ? {
              trade_id: queueItem.trade_id,
              chain_key: queueItem.chain_key,
              pair: queueItem.pair,
              amount_in: queueItem.amount_in,
              token_in: queueItem.token_in,
              token_out: queueItem.token_out,
              status: nextStatus,
              reason: queueItem.reason ?? null,
              reason_message: nextStatus === 'rejected' ? 'Rejected by owner.' : null,
              tx_hash: null,
              created_at: queueItem.created_at,
              updated_at: nowIso
            }
          : null);

      let nextHistory = existingHistory;
      if (already) {
        nextHistory = existingHistory.map((item) =>
          item.trade_id === tradeId
            ? {
                ...item,
                status: nextStatus,
                reason_message: nextStatus === 'rejected' ? item.reason_message ?? 'Rejected by owner.' : item.reason_message,
                updated_at: nowIso
              }
            : item
        );
      } else if (nextHistoryRow) {
        nextHistory = [nextHistoryRow, ...existingHistory];
      }

      return {
        phase: 'ready',
        data: {
          ...current.data,
          approvalsQueue: nextQueue,
          approvalsHistory: nextHistory
        }
      };
    });
  }

  async function runManagementAction(action: () => Promise<void>, successMessage: string, onSuccess?: () => void) {
    try {
      await action();
      onSuccess?.();
      showToast(successMessage, 'success');
      // Refresh in background so transient backend stalls do not freeze action UX.
      window.setTimeout(() => {
        void refreshAll({ showLoading: false });
      }, 0);
    } catch (actionError) {
      showToast(actionError instanceof Error ? actionError.message : 'Management action failed.', 'error', 3600);
      window.setTimeout(() => {
        void refreshAll({ showLoading: false });
      }, 0);
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
  const chainTokenNameByAddress = useMemo(() => {
    const out = new Map<string, string>();
    if (management.phase !== 'ready') {
      return out;
    }
    for (const entry of management.data.chainTokens ?? []) {
      const address = String(entry?.address ?? '').trim().toLowerCase();
      if (!address) {
        continue;
      }
      const displayName = String(entry?.tokenDisplay?.name ?? entry?.name ?? '').trim();
      if (displayName) {
        out.set(address, displayName);
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
  const hasAutoApprovalsEnabled = policyApprovalMode === 'auto' || policyAllowedTokenSet.size > 0;

  function buildPolicyUpdatePayload(next: { approvalMode?: 'per_trade' | 'auto'; allowedTokens?: string[] }) {
    return {
      agentId,
      chainKey: activeChainKey,
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
  const liquidityPositions = useMemo(() => {
    if (management.phase !== 'ready') {
      return [];
    }
    return (management.data.liquidityPositions ?? []).filter((row) => row.chain_key === activeChainKey);
  }, [management, activeChainKey]);
  const withdrawAssetOptions = useMemo(() => {
    const nativeHolding =
      holdings.find((holding) => {
        const symbol = holding.token.trim().toUpperCase();
        return symbol === activeNativeSymbol.toUpperCase() || symbol === 'NATIVE';
      }) ?? null;
    const nativeBalance = nativeHolding ? formatUnitsTruncated(nativeHolding.amountRaw, activeNativeDecimals, 6) : '0';
    const opts: Array<{ label: string; value: string }> = [{ label: `${activeChainLabel} ${activeNativeSymbol} (${nativeBalance})`, value: 'NATIVE' }];
    const seen = new Set<string>(['NATIVE']);
    for (const holding of holdings) {
      const symbol = normalizeTokenSelectionSymbol(holding.token, activeNativeSymbol);
      if (!symbol || symbol === activeNativeSymbol.toUpperCase() || symbol === 'NATIVE') {
        continue;
      }
      if (!seen.has(symbol)) {
        seen.add(symbol);
        opts.push({ label: `${symbol} (${formatUnitsTruncated(holding.amountRaw, holding.decimals, 6)})`, value: symbol });
      }
    }
    return opts;
  }, [holdings, activeChainLabel, activeNativeDecimals, activeNativeSymbol]);

  const withdrawSelectedHolding = useMemo(() => {
    if (withdrawAsset === 'NATIVE') {
      return holdings.find((holding) => {
        const symbol = holding.token.trim().toUpperCase();
        return symbol === activeNativeSymbol.toUpperCase() || symbol === 'NATIVE';
      }) ?? null;
    }
    return holdings.find((holding) => holding.token.trim().toUpperCase() === withdrawAsset.trim().toUpperCase()) ?? null;
  }, [holdings, withdrawAsset, activeNativeSymbol]);

  const withdrawMaxAmount = useMemo(() => {
    if (!withdrawSelectedHolding) {
      return '';
    }
    return formatUnitsTruncated(
      withdrawSelectedHolding.amountRaw,
      normalizeTokenSelectionSymbol(withdrawSelectedHolding.token, activeNativeSymbol) === activeNativeSymbol.toUpperCase()
        ? activeNativeDecimals
        : withdrawSelectedHolding.decimals,
      18
    );
  }, [activeNativeDecimals, activeNativeSymbol, withdrawSelectedHolding]);

  useEffect(() => {
    if (!preferredWithdrawDestination) {
      return;
    }
    setWithdrawDestination((current) => (current.trim().length === 0 ? preferredWithdrawDestination : current));
  }, [preferredWithdrawDestination]);
  const tokenDecimalsBySymbol = useMemo(() => {
    const map = new Map<string, number>();
    map.set(activeNativeSymbol.toUpperCase(), activeNativeDecimals);
    if (management.phase === 'ready') {
      for (const token of management.data.chainTokens ?? []) {
        const symbol = normalizeTokenSelectionSymbol(token.symbol, activeNativeSymbol);
        if (!symbol) {
          continue;
        }
        const decimals = typeof token.decimals === 'number' && Number.isFinite(token.decimals) ? token.decimals : null;
        if (decimals !== null && decimals >= 0) {
          map.set(symbol, decimals);
        }
      }
    }
    for (const holding of holdings) {
      const symbol = normalizeTokenSelectionSymbol(holding.token, activeNativeSymbol);
      if (symbol && !map.has(symbol)) {
        map.set(symbol, holding.decimals);
      }
    }
    return map;
  }, [activeNativeDecimals, activeNativeSymbol, holdings, management]);

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
      const normalized = normalizeTokenSelectionSymbol(tokenLabel, activeNativeSymbol);
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
    [activeNativeSymbol]
  );

  const formatX402AtomicAmount = useCallback(
    (amountAtomic: string | null | undefined, assetKind: 'native' | 'erc20', assetSymbol: string | null | undefined) => {
      const symbol = assetKind === 'native' ? activeNativeSymbol : normalizeTokenSelectionSymbol(assetSymbol, activeNativeSymbol) || 'TOKEN';
      const tokenLabel = assetKind === 'native' ? `${activeChainLabel} ${activeNativeSymbol}` : symbol;
      const decimals = assetKind === 'native' ? activeNativeDecimals : tokenDecimalsBySymbol.get(symbol);
      return formatHumanAmount(amountAtomic, tokenLabel, decimals);
    },
    [activeChainLabel, activeNativeDecimals, activeNativeSymbol, formatHumanAmount, tokenDecimalsBySymbol]
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
      const normalizedIn = normalizeTokenSelectionSymbol(tokenIn, activeNativeSymbol);
      const normalizedOut = normalizeTokenSelectionSymbol(tokenOut, activeNativeSymbol);
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
      const tokenIn = normalizeTokenSelectionSymbol(event.token_in_symbol, activeNativeSymbol);
      const tokenOut = normalizeTokenSelectionSymbol(event.token_out_symbol, activeNativeSymbol);
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
      const depositSymbol = normalizeTokenSelectionSymbol(deposit.token, activeNativeSymbol);
      const depositDecimals = tokenDecimalsBySymbol.get(depositSymbol) ?? undefined;
      const depositAmount = formatHumanAmount(deposit.amount, deposit.token, depositDecimals);
      const confirmationsText = activeDepositChain?.minConfirmations
        ? `Confirmations: >= ${activeDepositChain.minConfirmations}`
        : 'Confirmations: n/a';
      items.push({
        id: `dep-${deposit.txHash}-${deposit.blockNumber}`,
        at: deposit.confirmedAt,
        kind: 'deposits',
        title: `Deposit ${depositAmount}`,
        subtitle: `Status: ${displayStatusLabel(deposit.status || 'confirmed')}; ${confirmationsText}; Block ${deposit.blockNumber}`,
        status: deposit.status || 'confirmed',
        txHash: deposit.txHash ?? null,
        txExplorerUrl: toTxExplorerUrl(deposit.txHash),
        tokenSymbols: depositSymbol ? [depositSymbol] : []
      });
    }

    if (management.phase === 'ready') {
      for (const payment of x402Payments?.history ?? []) {
        const symbol = normalizeTokenSelectionSymbol(
          payment.asset_symbol || (payment.asset_kind === 'native' ? activeNativeSymbol : 'TOKEN'),
          activeNativeSymbol
        );
        const directionLabel = payment.direction === 'inbound' ? 'Received' : 'Sent';
        const amountLabel = formatX402AtomicAmount(payment.amount_atomic, payment.asset_kind, payment.asset_symbol);
        items.push({
          id: `x402-${payment.payment_id}`,
          at: payment.terminal_at ?? payment.updated_at ?? payment.created_at,
          kind: payment.direction === 'inbound' ? 'deposits' : 'transfers',
          title: `x402 ${directionLabel} ${amountLabel}`,
          subtitle: `Status: ${displayStatusLabel(payment.status)}; Network: ${humanizeKeyLabel(payment.network_key)}; Facilitator: ${humanizeKeyLabel(payment.facilitator_key)}`,
          status: payment.status,
          txHash: payment.tx_hash ?? null,
          txExplorerUrl: toTxExplorerUrl(payment.tx_hash),
          tokenSymbols: symbol ? [symbol] : [],
          source: 'x402'
        });
      }
      for (const item of management.data.transferApprovalsHistory ?? []) {
        const transferTokenLabel = item.transfer_type === 'native' ? `${activeChainLabel} ${activeNativeSymbol}` : item.token_symbol ?? 'Token';
        const transferSymbol = item.transfer_type === 'native' ? activeNativeSymbol : normalizeTokenSelectionSymbol(item.token_symbol, activeNativeSymbol);
        const transferDecimals =
          item.transfer_type === 'native' ? activeNativeDecimals : (tokenDecimalsBySymbol.get(normalizeTokenSelectionSymbol(item.token_symbol, activeNativeSymbol)) ?? 18);
        const transferAmount = formatHumanAmount(item.amount_wei, transferTokenLabel, transferDecimals);
        const x402AmountLabel = formatX402AtomicAmount(
          item.x402_amount_atomic ?? item.amount_wei,
          item.transfer_type === 'native' ? 'native' : 'erc20',
          item.token_symbol
        );
        items.push({
          id: `xfrh-${item.approval_id}`,
          at: item.terminal_at ?? item.decided_at ?? item.created_at,
          kind: 'transfers',
          title: item.approval_source === 'x402' ? `x402 outbound approval` : `${transferTokenLabel} transfer`,
          subtitle:
            item.approval_source === 'x402'
              ? `Payment link: ${item.x402_url ?? 'n/a'}; Amount: ${x402AmountLabel}; Approved: ${transferApprovedState(item.status)}`
              : `To: ${shortenAddress(item.to_address)}; Amount: ${transferAmount}; Approved: ${transferApprovedState(item.status)}; Confirmations: ${item.confirmations ?? 'n/a'}`,
          status: item.status,
          txHash: item.tx_hash ?? null,
          txExplorerUrl: toTxExplorerUrl(item.tx_hash),
          tokenSymbols: transferSymbol ? [transferSymbol] : [],
          source: item.approval_source === 'x402' ? 'x402' : 'default'
        });
      }
      for (const item of management.data.transferApprovalsQueue ?? []) {
        const transferTokenLabel = item.transfer_type === 'native' ? `${activeChainLabel} ${activeNativeSymbol}` : item.token_symbol ?? 'Token';
        const transferSymbol = item.transfer_type === 'native' ? activeNativeSymbol : normalizeTokenSelectionSymbol(item.token_symbol, activeNativeSymbol);
        const transferDecimals =
          item.transfer_type === 'native' ? activeNativeDecimals : (tokenDecimalsBySymbol.get(normalizeTokenSelectionSymbol(item.token_symbol, activeNativeSymbol)) ?? 18);
        const transferAmount = formatHumanAmount(item.amount_wei, transferTokenLabel, transferDecimals);
        const x402AmountLabel = formatX402AtomicAmount(
          item.x402_amount_atomic ?? item.amount_wei,
          item.transfer_type === 'native' ? 'native' : 'erc20',
          item.token_symbol
        );
        items.push({
          id: `xfrq-${item.approval_id}`,
          at: item.created_at,
          kind: 'transfers',
          title: item.approval_source === 'x402' ? 'Pending x402 approval' : 'Pending transfer approval',
          subtitle:
            item.approval_source === 'x402'
              ? `Payment link: ${item.x402_url ?? 'n/a'}; Amount: ${x402AmountLabel}; Approved: Pending`
              : `To: ${shortenAddress(item.to_address)}; Amount: ${transferAmount}; Approved: Pending; Confirmations: ${item.confirmations ?? 'n/a'}`,
          status: item.status,
          txHash: null,
          txExplorerUrl: null,
          tokenSymbols: transferSymbol ? [transferSymbol] : [],
          source: item.approval_source === 'x402' ? 'x402' : 'default'
        });
      }
      for (const item of management.data.policyApprovalsHistory ?? []) {
        const policySymbol = item.token_address
          ? normalizeTokenSelectionSymbol(chainTokenSymbolByAddress.get(item.token_address.toLowerCase()) ?? '', activeNativeSymbol)
          : '';
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
        const policySymbol = item.token_address
          ? normalizeTokenSelectionSymbol(chainTokenSymbolByAddress.get(item.token_address.toLowerCase()) ?? '', activeNativeSymbol)
          : '';
        items.push({
          id: `polq-${item.request_id}`,
          at: item.created_at,
          kind: 'approvals',
          title: policyApprovalLabel(item, management.data.chainTokens),
          subtitle: 'Waiting for policy approval',
          status: 'pending',
          txHash: null,
          txExplorerUrl: null,
          tokenSymbols: policySymbol ? [policySymbol] : []
        });
      }
      for (const item of management.data.approvalsQueue) {
        const tokenInLabel = resolveTokenLabel(item.token_in, chainTokenSymbolByAddress);
        const tokenOutLabel = resolveTokenLabel(item.token_out, chainTokenSymbolByAddress);
        const tokenIn = normalizeTokenSelectionSymbol(tokenInLabel, activeNativeSymbol);
        const tokenOut = normalizeTokenSelectionSymbol(tokenOutLabel, activeNativeSymbol);
        items.push({
          id: `trdapp-${item.trade_id}`,
          at: item.created_at,
          kind: 'approvals',
          title: `${tokenInLabel} -> ${tokenOutLabel}`,
          subtitle: item.reason ?? 'Waiting for trade approval',
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
    activeNativeDecimals,
    activeNativeSymbol,
    activeDepositChain?.minConfirmations,
    activeDepositChain?.recentDeposits,
    activity,
    chainTokenSymbolByAddress,
    formatHumanAmount,
    formatX402AtomicAmount,
    management,
    toTxExplorerUrl,
    tokenDecimalsBySymbol,
    x402Payments?.history,
    trades,
    transferApprovedState
  ]);

  const selectedWalletTokenSet = useMemo(() => new Set(selectedWalletTokens), [selectedWalletTokens]);
  const activeInboundX402Requests = useMemo(
    () =>
      (x402Payments?.queue ?? [])
        .filter((row) => row.direction === 'inbound' && (row.status === 'proposed' || row.status === 'executing'))
        .sort((left, right) => Number(new Date(right.created_at)) - Number(new Date(left.created_at))),
    [x402Payments?.queue]
  );

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
    const pendingTransferQueueIds = new Set((management.data.transferApprovalsQueue ?? []).map((item) => item.approval_id));
    const formatTransferApprovalAmount = (item: {
      transfer_type: 'native' | 'token';
      token_symbol: string | null;
      amount_wei: string;
    }): string => {
      const transferTokenLabel = item.transfer_type === 'native' ? `${activeChainLabel} ${activeNativeSymbol}` : item.token_symbol ?? 'Token';
      const transferDecimals =
        item.transfer_type === 'native' ? activeNativeDecimals : (tokenDecimalsBySymbol.get(normalizeTokenSelectionSymbol(item.token_symbol, activeNativeSymbol)) ?? 18);
      return formatHumanAmount(item.amount_wei, transferTokenLabel, transferDecimals);
    };
    const pendingTradeIds = new Set((management.data.approvalsQueue ?? []).map((item) => item.trade_id));
    for (const item of management.data.approvalsQueue) {
      const tokenInLabel = resolveTokenLabel(item.token_in, chainTokenSymbolByAddress);
      const tokenOutLabel = resolveTokenLabel(item.token_out, chainTokenSymbolByAddress);
      const tokenIn = normalizeTokenSelectionSymbol(tokenInLabel, activeNativeSymbol);
      const tokenOut = normalizeTokenSelectionSymbol(tokenOutLabel, activeNativeSymbol);
      rows.push({
        id: `trade-${item.trade_id}`,
        at: item.created_at,
        title: `${tokenInLabel} -> ${tokenOutLabel}`,
        status: 'pending',
        subtitle: item.reason ?? 'Waiting for trade approval',
        type: 'trade',
        tokenSymbols: [tokenIn, tokenOut].filter(Boolean),
        raw: item
      });
    }
    for (const item of management.data.approvalsHistory ?? []) {
      if (pendingTradeIds.has(item.trade_id)) {
        continue;
      }
      const tokenInLabel = resolveTokenLabel(item.token_in, chainTokenSymbolByAddress);
      const tokenOutLabel = resolveTokenLabel(item.token_out, chainTokenSymbolByAddress);
      const tokenIn = normalizeTokenSelectionSymbol(tokenInLabel, activeNativeSymbol);
      const tokenOut = normalizeTokenSelectionSymbol(tokenOutLabel, activeNativeSymbol);
      const normalized = String(item.status ?? '').trim().toLowerCase();
      const status =
        normalized === 'approval_pending' || normalized === 'pending'
          ? 'pending'
          : normalized === 'rejected' || normalized === 'deny' || normalized === 'denied'
            ? 'rejected'
            : normalized === 'failed' || normalized === 'expired' || normalized === 'verification_timeout'
              ? 'failed'
              : normalized === 'approved' || normalized === 'executing' || normalized === 'verifying' || normalized === 'filled'
                ? normalized
                : 'approved';
      rows.push({
        id: `trade-history-${item.trade_id}`,
        at: item.updated_at ?? item.created_at,
        title: `${tokenInLabel} -> ${tokenOutLabel}`,
        status,
        subtitle: `Trade ${item.trade_id} (${item.status})`,
        type: 'trade',
        tokenSymbols: [tokenIn, tokenOut].filter(Boolean),
        raw: item
      });
    }
    for (const item of management.data.policyApprovalsQueue ?? []) {
      const policySymbol = item.token_address
        ? normalizeTokenSelectionSymbol(chainTokenSymbolByAddress.get(item.token_address.toLowerCase()) ?? '', activeNativeSymbol)
        : '';
      rows.push({
        id: `policy-pending-${item.request_id}`,
        at: item.created_at,
        title: policyApprovalLabel(item, management.data.chainTokens),
        status: 'pending',
        subtitle: 'Waiting for policy approval',
        type: 'policy',
        tokenSymbols: policySymbol ? [policySymbol] : [],
        raw: item
      });
    }
    for (const item of management.data.policyApprovalsHistory ?? []) {
      const policySymbol = item.token_address
        ? normalizeTokenSelectionSymbol(chainTokenSymbolByAddress.get(item.token_address.toLowerCase()) ?? '', activeNativeSymbol)
        : '';
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
      const transferSymbol = item.transfer_type === 'native' ? activeNativeSymbol : normalizeTokenSelectionSymbol(item.token_symbol, activeNativeSymbol);
      const x402AmountLabel = formatX402AtomicAmount(
        item.x402_amount_atomic ?? item.amount_wei,
        item.transfer_type === 'native' ? 'native' : 'erc20',
        item.token_symbol
      );
      const transferAmount = formatTransferApprovalAmount(item);
      rows.push({
        id: `transfer-pending-${item.approval_id}`,
        at: item.created_at,
        title: item.approval_source === 'x402' ? `x402 outbound payment` : `${item.token_symbol ?? activeNativeSymbol} transfer`,
        status: item.status,
        subtitle:
          item.approval_source === 'x402'
            ? `Payment link: ${item.x402_url ?? 'n/a'}; Amount: ${x402AmountLabel}; Network: ${humanizeKeyLabel(
                item.x402_network_key ?? item.chain_key
              )}`
            : `To: ${shortenAddress(item.to_address)}; Amount: ${transferAmount}; Network: ${humanizeKeyLabel(item.chain_key)}`,
        type: 'transfer',
        tokenSymbols: transferSymbol ? [transferSymbol] : [],
        raw: item
      });
    }
    for (const item of management.data.transferApprovalsHistory ?? []) {
      if ((item.status === 'pending' || item.status === 'approval_pending') && pendingTransferQueueIds.has(item.approval_id)) {
        continue;
      }
      const transferSymbol = item.transfer_type === 'native' ? activeNativeSymbol : normalizeTokenSelectionSymbol(item.token_symbol, activeNativeSymbol);
      const x402AmountLabel = formatX402AtomicAmount(
        item.x402_amount_atomic ?? item.amount_wei,
        item.transfer_type === 'native' ? 'native' : 'erc20',
        item.token_symbol
      );
      const transferAmount = formatTransferApprovalAmount(item);
      rows.push({
        id: `transfer-history-${item.approval_id}`,
        at: item.terminal_at ?? item.decided_at ?? item.created_at,
        title: item.approval_source === 'x402' ? `x402 outbound payment` : `${item.token_symbol ?? activeNativeSymbol} transfer`,
        status: item.status,
        subtitle:
          item.approval_source === 'x402'
            ? `Payment link: ${item.x402_url ?? 'n/a'}; Amount: ${x402AmountLabel}; Network: ${humanizeKeyLabel(
                item.x402_network_key ?? item.chain_key
              )}`
            : `To: ${shortenAddress(item.to_address)}; Amount: ${transferAmount}; Network: ${humanizeKeyLabel(item.chain_key)}`,
        type: 'transfer',
        tokenSymbols: transferSymbol ? [transferSymbol] : [],
        raw: item
      });
    }
    rows.sort((a, b) => Number(new Date(b.at).getTime()) - Number(new Date(a.at).getTime()));
    return rows;
  }, [activeChainLabel, activeNativeDecimals, activeNativeSymbol, chainTokenSymbolByAddress, formatHumanAmount, formatX402AtomicAmount, management, tokenDecimalsBySymbol]);

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
    return tokenFiltered.filter(
      (row) =>
        row.status === 'rejected' ||
        row.status === 'deny' ||
        row.status === 'denied' ||
        row.status === 'failed' ||
        row.status === 'expired' ||
        row.status === 'verification_timeout'
    );
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
  }, [activeNativeSymbol, filledTrades, trades]);

  const status = profile?.agent.public_status;
  const isPaused =
    (management.phase === 'ready' ? management.data.agent.publicStatus : profile?.agent.public_status) === 'paused';
  const selectedTokenSummary =
    selectedWalletTokens.length === 0 ? 'All tokens' : `${selectedWalletTokens.join(', ')} selected`;
  const displayWalletTokenLabel = (token: string): string => {
    const normalized = normalizeTokenSelectionSymbol(token, activeNativeSymbol);
    const upperNative = activeNativeSymbol.toUpperCase();
    if (normalized === upperNative) {
      return `${activeChainLabel} ${activeNativeSymbol}`;
    }
    return token;
  };
  const formatWalletHoldingAmount = (holding: { token: string; amountRaw: string; decimals: number }): string => {
    const normalized = normalizeTokenSelectionSymbol(holding.token, activeNativeSymbol);
    const decimals = normalized === activeNativeSymbol.toUpperCase() ? activeNativeDecimals : holding.decimals;
    const base = formatUnitsTruncated(holding.amountRaw, decimals, 6);
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
  useEffect(() => {
    setWalletPage(1);
  }, [walletExpanded, holdings.length]);

  useEffect(() => {
    setWalletActivityPage(1);
  }, [walletActivityExpanded, walletActivityFilter, selectedWalletTokens, filteredWalletTimeline.length]);

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
    return <main className={styles.loadingPage}>Checking your access...</main>;
  }

  if (bootstrapState.phase === 'error') {
    return (
      <main className={styles.errorPage}>
        <h1>Could not open this management page</h1>
        <p>{bootstrapState.message}</p>
        {bootstrapState.code ? <p>Code: {bootstrapState.code}</p> : null}
        {bootstrapState.actionHint ? <p>{bootstrapState.actionHint}</p> : null}
      </main>
    );
  }

  return (
    <div className={styles.root}>
      {renderToasts()}
      <PrimaryNav />

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
                  {!isOwner ? (
                    <button
                      type="button"
                      className={styles.agentTrackStar}
                      onClick={() => void toggleViewerTracked()}
                      aria-label={
                        viewerTrackingContext.mode === 'server'
                          ? viewerTracked
                            ? 'Untrack agent. Removes it from your watchlist and agent tracking feed.'
                            : 'Track agent. Adds it to your watchlist and agent tracking feed.'
                          : viewerTracked
                            ? 'Remove saved bookmark from this device.'
                            : 'Save bookmark on this device.'
                      }
                      title={
                        viewerTrackingContext.mode === 'server'
                          ? viewerTracked
                            ? 'Untrack: remove from watchlist + agent tracking feed'
                            : 'Track: add to watchlist + agent tracking feed'
                          : viewerTracked
                            ? 'Remove saved bookmark (device only)'
                            : 'Save bookmark (device only)'
                      }
                      disabled={viewerTrackingBusy}
                    >
                      {viewerTracked ? '★' : '☆'}
                    </button>
                  ) : null}
                  {status && isPublicStatus(status) ? <PublicStatusBadge status={status} /> : null}
                  {!status ? <span className={styles.muted}>Status unavailable</span> : null}
                </div>
                <div className={styles.accountMetaChips}>
                  <span className={styles.walletChip}>Chain: {activeChainLabel}</span>
                  <span className={styles.walletChip}>Wallet: {activeWallet ? shortenAddress(activeWallet.address) : '—'}</span>
                </div>
              </div>
            </div>
            {isOwner ? (
              <div className={styles.headerApprovalControl}>
                <span className={styles.globalApprovalLabel}>Approve trades</span>
                <label className={styles.iosToggle} title="When on, this agent can trade without asking every time.">
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
                        `Approve is now ${nextMode === 'auto' ? 'on' : 'off'}.`
                      );
                    }}
                  />
                  <span className={styles.iosSlider} />
                </label>
              </div>
            ) : null}

          </div>

          <div className={`${styles.walletActions} ${styles.walletActionRow}`}>
            {isOwner && management.phase === 'ready' ? (
              <>
                <button
                  type="button"
                  className={styles.dangerButton}
                  disabled={!hasAutoApprovalsEnabled}
                  onClick={() => {
                    if (!window.confirm('Turn off all auto-approvals for this agent?')) {
                      return;
                    }
                    void runManagementAction(
                      () => managementPost('/api/v1/management/revoke-all', { agentId }).then(() => Promise.resolve()),
                      'All auto-approvals turned off for this agent.'
                    );
                  }}
                >
                  {hasAutoApprovalsEnabled ? 'Turn Off Auto-Approvals' : 'Auto-Approvals Already Off'}
                </button>
                <div className={styles.withdrawInline}>
                  {withdrawDestinationPreview ? <span className={styles.withdrawPreviewLabel}>{withdrawDestinationPreview}</span> : null}
                  <button type="button" onClick={() => setWithdrawCardOpen((current) => !current)}>
                    {withdrawCardOpen ? 'Close Withdraw' : 'Withdraw'}
                  </button>
                </div>
              </>
            ) : (
              <p className={styles.muted}>View-only mode: only the owner can change settings.</p>
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
            {!isOwner ? <p className={styles.muted}>View-only mode: approval controls are read-only.</p> : null}
            {holdings.length === 0 ? <p className={styles.muted}>No balances detected for this chain.</p> : null}
            <p className={styles.muted}>Select a token to filter activity and approvals. Hold Ctrl/Cmd to select more than one.</p>
            {visibleWalletHoldings.map((holding) => (
              <div
                key={holding.token}
                className={`${styles.listRow} ${styles.walletTokenRow} ${selectedWalletTokenSet.has(normalizeTokenSelectionSymbol(holding.token, activeNativeSymbol)) ? styles.selectedWalletRow : ''}`}
                onClick={(event) => {
                  const symbol = normalizeTokenSelectionSymbol(holding.token, activeNativeSymbol);
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
                  {isOwner ? (
                    <div className={`${styles.walletTokenMetricColumn} ${styles.tokenApprovalControl}`} onClick={(event) => event.stopPropagation()}>
                      <span className={styles.walletTokenMetricLabel}>Auto-Approve</span>
                      <label className={styles.iosToggle} title="When on, this token can trade without asking each time.">
                        <input
                          type="checkbox"
                          checked={isTokenPreapproved(holding.token)}
                          onChange={(event) => {
                            const enabled = event.target.checked;
                            const allowedTokens = nextAllowedTokensForSymbol(holding.token, enabled);
                            void runManagementAction(
                              () => managementPost('/api/v1/management/policy/update', buildPolicyUpdatePayload({ allowedTokens })).then(() => Promise.resolve()),
                              `${enabled ? 'Enabled' : 'Disabled'} approve for ${holding.token}.`
                            );
                          }}
                        />
                        <span className={styles.iosSlider} />
                      </label>
                    </div>
                  ) : null}
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
              <h2>Liquidity Positions</h2>
              <span className={styles.muted}>Chain-scoped LP and concentrated positions</span>
            </div>
            {liquidityPositions.length === 0 ? <p className={styles.muted}>No liquidity positions detected for this chain.</p> : null}
            {liquidityPositions.map((position) => {
              const tokenALabel = resolveTokenLabel(position.token_a, chainTokenSymbolByAddress);
              const tokenBLabel = resolveTokenLabel(position.token_b, chainTokenSymbolByAddress);
              const tokenAName = position.token_a?.startsWith('0x')
                ? chainTokenNameByAddress.get(position.token_a.toLowerCase()) ?? null
                : null;
              const tokenBName = position.token_b?.startsWith('0x')
                ? chainTokenNameByAddress.get(position.token_b.toLowerCase()) ?? null
                : null;
              const pairAddressParts = String(position.pool_ref ?? '')
                .split('/')
                .map((value) => value.trim())
                .filter((value) => value.length > 0);
              const pairRefDisplay =
                pairAddressParts.length === 2
                  ? `${resolveTokenLabel(pairAddressParts[0], chainTokenSymbolByAddress)}/${resolveTokenLabel(pairAddressParts[1], chainTokenSymbolByAddress)}`
                  : position.pool_ref;
              return (
                <div key={position.position_id} className={styles.listRow}>
                  <div>
                    <div className={styles.listTitle}>
                      {position.chain_key} • {position.dex_key.toUpperCase()} • {tokenALabel}/{tokenBLabel}
                    </div>
                    <div className={styles.muted}>
                      Type {position.position_type.toUpperCase()} • Pool/Pair {pairRefDisplay}
                    </div>
                    <div className={styles.muted}>
                      Tokens {tokenALabel}{tokenAName ? ` (${tokenAName})` : ''} / {tokenBLabel}{tokenBName ? ` (${tokenBName})` : ''}
                    </div>
                  <div className={styles.muted}>
                    Deposited basis {position.deposited_a} / {position.deposited_b} • Current underlying {position.current_a} / {position.current_b}
                  </div>
                  <div className={styles.muted}>
                    Unclaimed fees {position.unclaimed_fees_a} / {position.unclaimed_fees_b} • Realized fees {formatUsd(position.realized_fees_usd)}
                  </div>
                  <div className={styles.muted}>
                    Unrealized PnL estimate {formatUsd(position.unrealized_pnl_usd)} • Value {formatUsd(position.position_value_usd)}
                  </div>
                  <div className={styles.muted}>Last synced {formatUtc(position.last_synced_at)} UTC</div>
                  {position.explorer_url ? (
                    <div className={styles.muted}>
                      Explorer:{' '}
                      <a href={position.explorer_url} target="_blank" rel="noreferrer" className={styles.inlineLink}>
                        View position
                      </a>
                    </div>
                  ) : null}
                </div>
                <div className={styles.listMeta}>
                  <span className={styles.statusChip}>{displayStatusLabel(position.status)}</span>
                  {position.stale ? <span className={`${styles.statusChip} ${styles.staleChip}`}>Stale</span> : null}
                  <span>{formatUtc(position.updated_at)} UTC</span>
                </div>
                </div>
              );
            })}
          </article>

            <article className={`${styles.card} ${styles.walletCard}`}>
            <div className={`${styles.cardHeader} ${styles.walletCardHeader}`}>
              <h2>Wallet Activity</h2>
              <div className={styles.inlineActions}>
                <span className={styles.muted}>Trades, transfers, deposits, and approvals</span>
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
                    {row.source === 'x402' ? <div className={styles.muted}>Source: X402 payment</div> : null}
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
                    <span className={styles.statusChip}>{displayStatusLabel(row.status)}</span>
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
                          {auditEntryLabel(entry)}
                        </div>
                        <div className={styles.muted}>{auditEntryDetails(entry)}</div>
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
            <article id="approval-history" className={`${styles.card} ${styles.walletCard}`}>
              <div className={`${styles.cardHeader} ${styles.walletCardHeader}`}>
                <h2>Approvals</h2>
                <div className={styles.inlineActions}>
                  <span className={styles.muted}>Requests waiting for a decision and past decisions</span>
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
              {!isOwner ? <p className={styles.muted}>View-only mode: only the owner can approve or deny.</p> : null}
              {filteredApprovalHistory.length === 0 ? <p className={styles.muted}>No approvals in this filter.</p> : null}
              {visibleApprovalHistory.map((row) => {
                const transferApprovalId =
                  row.type === 'transfer' && row.raw && typeof row.raw.approval_id === 'string' ? testIdSafePart(row.raw.approval_id) : null;
                const rowTestId = transferApprovalId
                  ? `approval-row-transfer-${transferApprovalId}`
                  : `approval-row-${testIdSafePart(row.type)}-${testIdSafePart(row.id)}`;
                return (
                <div key={row.id} className={styles.queueRow} data-testid={rowTestId}>
                  <div>
                    <div className={styles.listTitle}>{row.title}</div>
                    <div className={styles.muted}>{row.subtitle}</div>
                    <div className={styles.muted}>{formatUtc(row.at)} UTC</div>
                  </div>
                  <div className={styles.queueActions}>
                    <span className={styles.statusChip}>{displayStatusLabel(row.status)}</span>
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
                          placeholder="Reason (optional)"
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
                              'Trade approved.',
                              () => applyOptimisticTradeDecision(row.raw.trade_id, 'approved')
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
                              'Trade rejected.',
                              () => applyOptimisticTradeDecision(row.raw.trade_id, 'rejected')
                            )
                          }
                        >
                          Reject
                        </button>
                      </>
                    ) : null}
                    {isOwner && (row.status === 'pending' || row.status === 'approval_pending') && row.type === 'policy' ? (
                      <>
                        <input
                          value={approvalRejectReasons[row.raw.request_id] ?? ''}
                          onChange={(event) =>
                            setApprovalRejectReasons((current) => ({
                              ...current,
                              [row.raw.request_id]: event.target.value
                            }))
                          }
                          placeholder="Reason (optional)"
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
                              'Policy request approved.'
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
                              'Policy request denied.'
                            )
                          }
                        >
                          Deny
                        </button>
                      </>
                    ) : null}
                    {isOwner && (row.status === 'pending' || row.status === 'approval_pending') && row.type === 'transfer' ? (
                      <>
                        <input
                          value={approvalRejectReasons[row.raw.approval_id] ?? ''}
                          onChange={(event) =>
                            setApprovalRejectReasons((current) => ({
                              ...current,
                              [row.raw.approval_id]: event.target.value
                            }))
                          }
                          placeholder="Reason (optional)"
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
                              'Transfer decision submitted.'
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
                              'Transfer denial submitted.'
                            )
                          }
                        >
                          Deny
                        </button>
                      </>
                    ) : null}
                  </div>
                </div>
              )})}
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
                <h3>x402 Receive Requests</h3>
                <span>{activeInboundX402Requests.length} active</span>
              </div>
              {x402ReceiveLink ? (
                <>
                  <div className={styles.muted} style={{ marginTop: '0.55rem' }}>
                    Active request links
                  </div>
                  {activeInboundX402Requests.length === 0 ? <div className={styles.muted}>No active requests.</div> : null}
                  {activeInboundX402Requests.slice(0, 8).map((request) => (
                    <div key={request.payment_id} className={styles.railQueueRow}>
                      <div>
                        <div className={styles.listTitle}>
                          {formatX402AtomicAmount(request.amount_atomic, request.asset_kind, request.asset_symbol)} ·{' '}
                          {displayStatusLabel(request.status)}
                        </div>
                        <div className={styles.muted}>{formatUtc(request.created_at)} UTC</div>
                        {request.resource_description ? <div className={styles.muted}>Memo: {request.resource_description}</div> : null}
                      </div>
                      <div className={styles.inlineActions}>
                        <button
                          type="button"
                          onClick={() => void copyToClipboard(request.payment_url ?? '', 'Payment link copied.')}
                          disabled={!request.payment_url}
                        >
                          Copy URL
                        </button>
                        {isOwner ? (
                          <button
                            type="button"
                            className={`${styles.iconOnlyButton} ${styles.dangerButton}`}
                            title="Delete request"
                            aria-label={`Delete x402 request ${request.payment_id}`}
                            onClick={() =>
                              void runManagementAction(
                                () =>
                                  managementDelete('/api/v1/management/x402/receive-link', {
                                    agentId,
                                    paymentId: request.payment_id
                                  }).then(() => Promise.resolve()),
                                'Payment request deleted.'
                              )
                            }
                          >
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
                              <path d="M4 7h16" />
                              <path d="M10 11v6" />
                              <path d="M14 11v6" />
                              <path d="M6 7l1 13h10l1-13" />
                              <path d="M9 7V4h6v3" />
                            </svg>
                          </button>
                        ) : null}
                      </div>
                    </div>
                  ))}
                </>
              ) : (
                <p className={styles.muted}>Payment link setup is unavailable right now.</p>
              )}
            </article>

          </aside>
        </div>
      </section>
    </div>
  );
}
