import { shortenAddress } from '@/lib/public-format';

export type AgentProfilePayload = {
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
  walletBalances?: Array<{
    chain_key: string;
    token: string;
    balance: string;
    decimals: number | null;
    observed_at: string;
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

export type TradePayload = {
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

export type ActivityPayload = {
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

export type ManagementStatePayload = {
  ok: boolean;
  agent: {
    agentId: string;
    publicStatus: string;
    metadata: Record<string, unknown>;
  };
  chainTokens?: Array<{
    symbol: string;
    address: string;
    name?: string | null;
    decimals?: number | null;
    source?: 'config' | 'rpc' | 'cache' | 'fallback' | string;
    tokenDisplay?: {
      symbol: string | null;
      name: string | null;
      decimals: number | null;
      address: string;
      isFallbackLabel: boolean;
    } | null;
  }>;
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
  approvalsHistory?: Array<{
    trade_id: string;
    chain_key: string;
    pair: string;
    amount_in: string | null;
    token_in: string;
    token_out: string;
    status: string;
    reason: string | null;
    reason_message: string | null;
    tx_hash: string | null;
    created_at: string;
    updated_at: string;
  }>;
  policyApprovalsQueue?: Array<{
    request_id: string;
    chain_key: string;
    request_type: string;
    token_address: string | null;
    created_at: string;
  }>;
  policyApprovalsHistory?: Array<{
    request_id: string;
    chain_key: string;
    request_type: string;
    token_address: string | null;
    status: string;
    reason_message: string | null;
    created_at: string;
    decided_at: string | null;
  }>;
  transferApprovalsQueue?: Array<{
    approval_id: string;
    chain_key: string;
    status: string;
    transfer_type: 'native' | 'token';
    approval_source?: 'transfer' | 'x402';
    token_address: string | null;
    token_symbol: string | null;
    to_address: string;
    amount_wei: string;
    policy_blocked_at_create: boolean;
    policy_block_reason_code: 'outbound_disabled' | 'destination_not_whitelisted' | null;
    policy_block_reason_message: string | null;
    execution_mode: 'normal' | 'policy_override' | null;
    x402_url?: string | null;
    x402_network_key?: string | null;
    x402_facilitator_key?: string | null;
    x402_asset_kind?: 'native' | 'erc20' | null;
    x402_asset_address?: string | null;
    x402_amount_atomic?: string | null;
    x402_payment_id?: string | null;
    confirmations?: number | null;
    created_at: string;
  }>;
  transferApprovalsHistory?: Array<{
    approval_id: string;
    chain_key: string;
    status: string;
    transfer_type: 'native' | 'token';
    approval_source?: 'transfer' | 'x402';
    token_address: string | null;
    token_symbol: string | null;
    to_address: string;
    amount_wei: string;
    tx_hash: string | null;
    reason_message: string | null;
    policy_blocked_at_create: boolean;
    policy_block_reason_code: 'outbound_disabled' | 'destination_not_whitelisted' | null;
    policy_block_reason_message: string | null;
    execution_mode: 'normal' | 'policy_override' | null;
    x402_url?: string | null;
    x402_network_key?: string | null;
    x402_facilitator_key?: string | null;
    x402_asset_kind?: 'native' | 'erc20' | null;
    x402_asset_address?: string | null;
    x402_amount_atomic?: string | null;
    x402_payment_id?: string | null;
    confirmations?: number | null;
    created_at: string;
    decided_at: string | null;
    terminal_at: string | null;
  }>;
  liquidityApprovalsQueue?: Array<{
    liquidity_intent_id: string;
    chain_key: string;
    dex_key: string;
    action_type: 'add' | 'remove' | string;
    position_type: 'v2' | 'v3' | string;
    token_a: string | null;
    token_b: string | null;
    amount_a: string | null;
    amount_b: string | null;
    status: string;
    reason_code: string | null;
    reason_message: string | null;
    tx_hash: string | null;
    created_at: string;
    updated_at: string;
  }>;
  liquidityApprovalsHistory?: Array<{
    liquidity_intent_id: string;
    chain_key: string;
    dex_key: string;
    action_type: 'add' | 'remove' | string;
    position_type: 'v2' | 'v3' | string;
    token_a: string | null;
    token_b: string | null;
    amount_a: string | null;
    amount_b: string | null;
    status: string;
    reason_code: string | null;
    reason_message: string | null;
    tx_hash: string | null;
    created_at: string;
    updated_at: string;
  }>;
  transferApprovalPolicy?: {
    chainKey: string;
    transferApprovalMode: 'auto' | 'per_transfer';
    nativeTransferPreapproved: boolean;
    allowedTransferTokens: string[];
    updatedAt: string | null;
  };
  liquidityPositions?: Array<{
    position_id: string;
    chain_key: string;
    dex_key: string;
    position_type: 'v2' | 'v3' | string;
    pool_ref: string;
    token_a: string;
    token_b: string;
    deposited_a: string;
    deposited_b: string;
    current_a: string;
    current_b: string;
    unclaimed_fees_a: string;
    unclaimed_fees_b: string;
    realized_fees_usd: string;
    unrealized_pnl_usd: string;
    position_value_usd: string | null;
    status: 'active' | 'closed' | 'paused' | 'deactivated' | string;
    explorer_url: string | null;
    last_synced_at: string;
    updated_at: string;
    stale?: boolean;
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
  trackedAgents?: Array<{
    trackingId: string;
    trackedAgentId: string;
    agentName: string;
    publicStatus: string;
    walletAddress: string | null;
    lastActivityAt: string | null;
    lastHeartbeatAt: string | null;
    latestMetrics: {
      pnlUsd: string | null;
      returnPct: string | null;
      volumeUsd: string | null;
      tradesCount: number;
      asOf: string | null;
    } | null;
    createdAt: string;
  }>;
  trackedRecentTrades?: Array<{
    tradeId: string;
    trackedAgentId: string;
    agentName: string;
    chainKey: string;
    status: string;
    pair: string | null;
    tokenIn: string;
    tokenOut: string;
    amountIn: string | null;
    amountOut: string | null;
    txHash: string | null;
    executedAt: string | null;
    createdAt: string;
  }>;
  managementSession: {
    sessionId: string;
    expiresAt: string;
  };
};

export type DepositPayload = {
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

export type WithdrawsPayload = {
  ok: boolean;
  agentId: string;
  chainKey: string;
  queue: Array<{
    approvalId: string;
    decisionId: string | null;
    requestKind: 'withdraw';
    chainKey: string;
    status: 'queued' | 'pending' | 'executing' | 'verifying' | 'filled' | 'failed';
    transferType: 'native' | 'token';
    tokenAddress: string | null;
    tokenSymbol: string | null;
    destination: string;
    amountWei: string;
    txHash: string | null;
    reasonCode: string | null;
    reasonMessage: string | null;
    executionMode: 'normal' | 'policy_override' | null;
    confirmations: number | null;
    createdAt: string;
    decidedAt: string | null;
    terminalAt: string | null;
  }>;
  history: Array<{
    approvalId: string;
    decisionId: string | null;
    requestKind: 'withdraw';
    chainKey: string;
    status: 'queued' | 'pending' | 'executing' | 'verifying' | 'filled' | 'failed';
    transferType: 'native' | 'token';
    tokenAddress: string | null;
    tokenSymbol: string | null;
    destination: string;
    amountWei: string;
    txHash: string | null;
    reasonCode: string | null;
    reasonMessage: string | null;
    executionMode: 'normal' | 'policy_override' | null;
    confirmations: number | null;
    createdAt: string;
    decidedAt: string | null;
    terminalAt: string | null;
  }>;
};

export type LimitOrderItem = {
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

export type ActivityRow = {
  id: string;
  at: string;
  title: string;
  subtitle: string;
  status: string;
};

export type HoldingRow = {
  token: string;
  amountRaw: string;
  decimals: number;
};

export function normalizeHexAddress(value: string): string {
  const raw = (value ?? '').trim();
  return raw.toLowerCase();
}

export function isLikelyEvmAddress(value: string): boolean {
  return /^0x[a-fA-F0-9]{40}$/.test(String(value ?? '').trim());
}

export function normalizeTokenAddressKey(value: string): string {
  const raw = String(value ?? '').trim();
  if (!raw) {
    return '';
  }
  return isLikelyEvmAddress(raw) ? raw.toLowerCase() : raw;
}

export function tokenSymbolByAddress(chainTokens?: Array<{ symbol: string; address: string }>): Map<string, string> {
  const map = new Map<string, string>();
  for (const token of chainTokens ?? []) {
    if (!token.address || !token.symbol) {
      continue;
    }
    map.set(normalizeTokenAddressKey(token.address), token.symbol);
  }
  return map;
}

export function resolveTokenLabel(value: string | null | undefined, byAddress: Map<string, string>): string {
  const raw = (value ?? '').trim();
  if (!raw) {
    return 'token';
  }
  const direct = byAddress.get(normalizeTokenAddressKey(raw));
  if (direct) {
    return direct;
  }
  // Preserve symbol-like values (e.g. "USDC") and only shorten likely address/mint strings.
  const isHexAddress = /^0x[a-fA-F0-9]{40}$/.test(raw);
  const isSolanaMint = /^[1-9A-HJ-NP-Za-km-z]{32,44}$/.test(raw);
  if (!isHexAddress && !isSolanaMint) {
    return raw;
  }
  return shortenAddress(raw);
}

export function formatActivityTitle(eventType: string): string {
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
  if (eventType === 'policy_approval_pending') {
    return 'Policy awaiting approval';
  }
  if (eventType === 'policy_approved') {
    return 'Policy approved';
  }
  if (eventType === 'policy_rejected') {
    return 'Policy rejected';
  }
  if (eventType.startsWith('trade_')) {
    return eventType.replace(/^trade_/, '').replace(/_/g, ' ');
  }
  if (eventType.startsWith('policy_')) {
    return eventType.replace(/^policy_/, '').replace(/_/g, ' ');
  }
  return eventType.replace(/_/g, ' ');
}

export function buildActivityRows(
  trades: TradePayload['items'] | null,
  activity: ActivityPayload['items'] | null,
  chainTokens?: Array<{ symbol: string; address: string }>
): ActivityRow[] {
  const symbolMap = tokenSymbolByAddress(chainTokens);
  const rows: ActivityRow[] = [];

  for (const trade of trades ?? []) {
    const tokenIn = resolveTokenLabel(trade.token_in, symbolMap);
    const tokenOut = resolveTokenLabel(trade.token_out, symbolMap);
    rows.push({
      id: `trade:${trade.trade_id}`,
      at: trade.created_at,
      title: `${tokenIn} -> ${tokenOut}`,
      subtitle: trade.reason ?? trade.reason_code ?? trade.reason_message ?? 'Trade lifecycle event',
      status: trade.status
    });
  }

  for (const event of activity ?? []) {
    const pair = event.pair_display ?? `${event.token_in_symbol ?? 'token'} / ${event.token_out_symbol ?? 'token'}`;
    rows.push({
      id: `event:${event.event_id}`,
      at: event.created_at,
      title: formatActivityTitle(event.event_type),
      subtitle: pair,
      status: event.event_type
    });
  }

  rows.sort((a, b) => new Date(b.at).getTime() - new Date(a.at).getTime());
  return rows;
}

export function buildHoldings(
  profile: AgentProfilePayload | null,
  depositData: DepositPayload | null,
  chainKey: string
): HoldingRow[] {
  const byToken = new Map<string, HoldingRow>();
  const hasPositiveBalance = (raw: string): boolean => {
    const value = String(raw ?? '').trim();
    if (!value) {
      return false;
    }
    try {
      return BigInt(value) > BigInt(0);
    } catch {
      return false;
    }
  };

  for (const item of profile?.walletBalances ?? []) {
    if (item.chain_key !== chainKey) {
      continue;
    }
    if (!hasPositiveBalance(item.balance)) {
      continue;
    }
    byToken.set(item.token, {
      token: item.token,
      amountRaw: item.balance,
      decimals: item.decimals ?? 18
    });
  }

  const chain = depositData?.chains.find((entry) => entry.chainKey === chainKey);
  for (const item of chain?.balances ?? []) {
    if (!hasPositiveBalance(item.balance)) {
      continue;
    }
    byToken.set(item.token, {
      token: item.token,
      amountRaw: item.balance,
      decimals: item.decimals ?? 18
    });
  }

  return [...byToken.values()].sort((a, b) => a.token.localeCompare(b.token));
}

export function formatDecimalText(value: string | null | undefined): string {
  const raw = (value ?? '').trim();
  if (!raw) {
    return '—';
  }
  const sign = raw.startsWith('-') ? '-' : '';
  const unsigned = sign ? raw.slice(1) : raw;
  const [intPartRaw, fracPartRaw] = unsigned.split('.', 2);
  const intPart = (intPartRaw || '0').replace(/^0+(?=\d)/, '');
  const intWithCommas = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  if (fracPartRaw && fracPartRaw.length > 0) {
    return `${sign}${intWithCommas}.${fracPartRaw}`;
  }
  return `${sign}${intWithCommas}`;
}

export function formatUnitsTruncated(raw: string | null | undefined, decimals: number, maxFraction: number): string {
  if (!raw) {
    return '—';
  }
  let value: bigint;
  try {
    value = BigInt(raw);
  } catch {
    return '—';
  }
  if (decimals <= 0) {
    return value.toString();
  }
  const neg = value < BigInt(0);
  const digits = (neg ? -value : value).toString();
  const padded = digits.padStart(decimals + 1, '0');
  const whole = padded.slice(0, -decimals) || '0';
  let frac = padded.slice(-decimals);
  frac = frac.replace(/0+$/, '');
  if (maxFraction >= 0 && frac.length > maxFraction) {
    frac = frac.slice(0, maxFraction).replace(/0+$/, '');
  }
  const core = frac.length > 0 ? `${whole}.${frac}` : whole;
  return neg ? `-${core}` : core;
}
