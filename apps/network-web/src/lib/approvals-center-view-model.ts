import { shortenAddress } from '@/lib/public-format';

export type ApprovalsCenterManagementState = {
  chainTokens?: Array<{ symbol: string; address: string }>;
  approvalsQueue?: Array<{
    trade_id: string;
    chain_key: string;
    pair: string;
    amount_in: string | null;
    token_in: string;
    token_out: string;
    reason: string | null;
    created_at: string;
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
    token_address: string | null;
    token_symbol: string | null;
    to_address: string;
    amount_wei: string;
    policy_blocked_at_create: boolean;
    policy_block_reason_code: string | null;
    policy_block_reason_message: string | null;
    execution_mode: 'normal' | 'policy_override' | null;
    created_at: string;
  }>;
  transferApprovalsHistory?: Array<{
    approval_id: string;
    chain_key: string;
    status: string;
    transfer_type: 'native' | 'token';
    token_address: string | null;
    token_symbol: string | null;
    to_address: string;
    amount_wei: string;
    tx_hash: string | null;
    reason_message: string | null;
    policy_blocked_at_create: boolean;
    policy_block_reason_code: string | null;
    policy_block_reason_message: string | null;
    execution_mode: 'normal' | 'policy_override' | null;
    created_at: string;
    decided_at: string | null;
    terminal_at: string | null;
  }>;
};

export type ApprovalRowKind = 'trade' | 'policy' | 'transfer';
export type ApprovalRowStatus = 'pending' | 'approved' | 'rejected';

export type ApprovalsCenterRow = {
  id: string;
  rowKind: ApprovalRowKind;
  chainKey: string;
  createdAt: string;
  status: ApprovalRowStatus;
  title: string;
  subtitle: string;
  requestTypeLabel: string;
  reasonLine: string;
  riskLabel: 'Low' | 'Med' | 'High';
  tokenSearch: string;
  tradeId?: string;
  policyApprovalId?: string;
  transferApprovalId?: string;
};

export type LocalDecisionMap = Record<string, { status: ApprovalRowStatus; decidedAt: string; reason?: string }>;

function normalizeAddress(value: string | null | undefined): string {
  return String(value ?? '').trim().toLowerCase();
}

function tokenMap(tokens?: Array<{ symbol: string; address: string }>): Map<string, string> {
  const out = new Map<string, string>();
  for (const token of tokens ?? []) {
    const key = normalizeAddress(token.address);
    if (!key) {
      continue;
    }
    out.set(key, token.symbol);
  }
  return out;
}

function tokenLabel(value: string | null | undefined, byAddress: Map<string, string>): string {
  const raw = String(value ?? '').trim();
  if (!raw) {
    return 'token';
  }
  if (!raw.startsWith('0x')) {
    return raw;
  }
  return byAddress.get(normalizeAddress(raw)) ?? shortenAddress(raw);
}

function classifyRisk(input: { rowKind: ApprovalRowKind; policyBlocked?: boolean; reason?: string | null }): 'Low' | 'Med' | 'High' {
  if (input.rowKind === 'transfer' && input.policyBlocked) {
    return 'High';
  }
  if ((input.reason ?? '').toLowerCase().includes('not pre-approved')) {
    return 'Med';
  }
  if (input.rowKind === 'policy') {
    return 'Med';
  }
  return 'Low';
}

function mapPolicyRequestType(requestType: string, token: string): { label: string; summary: string } {
  if (requestType === 'global_approval_enable') {
    return { label: 'Policy Approval', summary: 'Enable global approval mode' };
  }
  if (requestType === 'global_approval_disable') {
    return { label: 'Policy Approval', summary: 'Disable global approval mode' };
  }
  if (requestType === 'token_preapprove_add') {
    return { label: 'Policy Approval', summary: `Preapprove ${token}` };
  }
  if (requestType === 'token_preapprove_remove') {
    return { label: 'Policy Approval', summary: `Remove preapproval for ${token}` };
  }
  return { label: 'Policy Approval', summary: requestType.replace(/_/g, ' ') };
}

function normalizeStatus(raw: string | null | undefined): ApprovalRowStatus | null {
  if (raw === 'approval_pending') {
    return 'pending';
  }
  if (raw === 'approved') {
    return 'approved';
  }
  if (raw === 'rejected') {
    return 'rejected';
  }
  return null;
}

export function buildApprovalsCenterRows(
  payload: ApprovalsCenterManagementState,
  decisions: LocalDecisionMap = {}
): ApprovalsCenterRow[] {
  const byAddress = tokenMap(payload.chainTokens);
  const out: ApprovalsCenterRow[] = [];

  for (const item of payload.approvalsQueue ?? []) {
    const decision = decisions[item.trade_id];
    out.push({
      id: `trade:${item.trade_id}`,
      rowKind: 'trade',
      chainKey: item.chain_key,
      createdAt: decision?.decidedAt ?? item.created_at,
      status: decision?.status ?? 'pending',
      title: item.pair.replace('/', ' -> '),
      subtitle: `Trade ${item.trade_id}`,
      requestTypeLabel: 'Trade Approval',
      reasonLine: item.reason?.trim() || 'Token not pre-approved',
      riskLabel: classifyRisk({ rowKind: 'trade', reason: item.reason }),
      tokenSearch: `${item.pair} ${item.token_in} ${item.token_out}`.toLowerCase(),
      tradeId: item.trade_id
    });
  }

  for (const item of payload.policyApprovalsQueue ?? []) {
    const token = tokenLabel(item.token_address, byAddress);
    const copy = mapPolicyRequestType(item.request_type, token);
    const decision = decisions[item.request_id];
    out.push({
      id: `policy:${item.request_id}`,
      rowKind: 'policy',
      chainKey: item.chain_key,
      createdAt: decision?.decidedAt ?? item.created_at,
      status: decision?.status ?? 'pending',
      title: copy.summary,
      subtitle: `Request ${item.request_id}`,
      requestTypeLabel: copy.label,
      reasonLine: 'Policy change requires owner confirmation.',
      riskLabel: classifyRisk({ rowKind: 'policy' }),
      tokenSearch: `${item.request_type} ${token}`.toLowerCase(),
      policyApprovalId: item.request_id
    });
  }

  for (const item of payload.transferApprovalsQueue ?? []) {
    const token = item.transfer_type === 'native' ? 'Native' : tokenLabel(item.token_symbol || item.token_address, byAddress);
    const summary = item.transfer_type === 'native' ? `Transfer native asset to ${shortenAddress(item.to_address)}` : `Transfer ${token} to ${shortenAddress(item.to_address)}`;
    const decision = decisions[item.approval_id];
    out.push({
      id: `transfer:${item.approval_id}`,
      rowKind: 'transfer',
      chainKey: item.chain_key,
      createdAt: decision?.decidedAt ?? item.created_at,
      status: decision?.status ?? 'pending',
      title: summary,
      subtitle: `Transfer approval ${item.approval_id}`,
      requestTypeLabel: 'Withdraw Approval',
      reasonLine: item.policy_block_reason_message || 'Transfer requires owner confirmation.',
      riskLabel: classifyRisk({ rowKind: 'transfer', policyBlocked: item.policy_blocked_at_create }),
      tokenSearch: `${token} ${item.to_address} ${item.token_address ?? ''}`.toLowerCase(),
      transferApprovalId: item.approval_id
    });
  }

  for (const item of payload.policyApprovalsHistory ?? []) {
    const mapped = normalizeStatus(item.status);
    if (!mapped || mapped === 'pending') {
      continue;
    }
    const token = tokenLabel(item.token_address, byAddress);
    const copy = mapPolicyRequestType(item.request_type, token);
    out.push({
      id: `policy-history:${item.request_id}`,
      rowKind: 'policy',
      chainKey: item.chain_key,
      createdAt: item.decided_at ?? item.created_at,
      status: mapped,
      title: copy.summary,
      subtitle: `Request ${item.request_id}`,
      requestTypeLabel: copy.label,
      reasonLine: item.reason_message?.trim() || 'Historical entry (session scope).',
      riskLabel: classifyRisk({ rowKind: 'policy' }),
      tokenSearch: `${item.request_type} ${token}`.toLowerCase(),
      policyApprovalId: item.request_id
    });
  }

  for (const item of payload.transferApprovalsHistory ?? []) {
    const mapped = normalizeStatus(item.status);
    if (!mapped || mapped === 'pending') {
      continue;
    }
    const token = item.transfer_type === 'native' ? 'Native' : tokenLabel(item.token_symbol || item.token_address, byAddress);
    out.push({
      id: `transfer-history:${item.approval_id}`,
      rowKind: 'transfer',
      chainKey: item.chain_key,
      createdAt: item.decided_at ?? item.terminal_at ?? item.created_at,
      status: mapped,
      title: `Transfer ${token} to ${shortenAddress(item.to_address)}`,
      subtitle: `Transfer approval ${item.approval_id}`,
      requestTypeLabel: 'Withdraw Approval',
      reasonLine: item.reason_message?.trim() || 'Historical entry (session scope).',
      riskLabel: classifyRisk({ rowKind: 'transfer', policyBlocked: item.policy_blocked_at_create }),
      tokenSearch: `${token} ${item.to_address} ${item.token_address ?? ''}`.toLowerCase(),
      transferApprovalId: item.approval_id
    });
  }

  out.sort((left, right) => new Date(right.createdAt).getTime() - new Date(left.createdAt).getTime());
  return out;
}
