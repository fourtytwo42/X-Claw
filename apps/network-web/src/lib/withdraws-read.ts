import { dbQuery } from '@/lib/db';
import { fetchChainTransactionConfirmations } from '@/lib/tx-confirmations';

export type WithdrawStatus = 'queued' | 'pending' | 'executing' | 'verifying' | 'filled' | 'failed';

type MirrorRow = {
  approval_id: string;
  chain_key: string;
  status: string;
  transfer_type: 'native' | 'token';
  token_address: string | null;
  token_symbol: string | null;
  to_address: string;
  amount_wei: string;
  tx_hash: string | null;
  reason_code: string | null;
  reason_message: string | null;
  execution_mode: 'normal' | 'policy_override' | null;
  created_at: string;
  decided_at: string | null;
  terminal_at: string | null;
  decision_id: string | null;
};

export type WithdrawReadItem = {
  approvalId: string;
  decisionId: string | null;
  requestKind: 'withdraw';
  chainKey: string;
  status: WithdrawStatus;
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
};

export function normalizeWithdrawStatus(raw: string): WithdrawStatus {
  const normalized = String(raw || '').trim().toLowerCase();
  if (normalized === 'approved') {
    return 'queued';
  }
  if (normalized === 'approval_pending') {
    return 'pending';
  }
  if (normalized === 'executing') {
    return 'executing';
  }
  if (normalized === 'verifying') {
    return 'verifying';
  }
  if (normalized === 'filled') {
    return 'filled';
  }
  return 'failed';
}

export function isWithdrawQueueStatus(status: WithdrawStatus): boolean {
  return status === 'queued' || status === 'pending' || status === 'executing' || status === 'verifying';
}

export async function readWithdrawRows(agentId: string, chainKey: string, limit = 200): Promise<WithdrawReadItem[]> {
  const rows = await dbQuery<MirrorRow>(
    `
    select
      m.approval_id,
      m.chain_key,
      m.status::text,
      m.transfer_type::text,
      m.token_address,
      m.token_symbol,
      m.to_address,
      m.amount_wei::text,
      m.tx_hash,
      m.reason_code,
      m.reason_message,
      m.execution_mode,
      m.created_at::text,
      m.decided_at::text,
      m.terminal_at::text,
      d.decision_id
    from agent_transfer_approval_mirror m
    left join lateral (
      select decision_id
      from agent_transfer_decision_inbox
      where approval_id = m.approval_id
        and request_kind = 'withdraw'
      order by created_at desc
      limit 1
    ) d on true
    where m.agent_id = $1
      and m.chain_key = $2
      and m.request_kind = 'withdraw'
    order by m.created_at desc
    limit $3
    `,
    [agentId, chainKey, Math.max(1, Math.min(limit, 500))]
  );

  const confirmationsByTx = await fetchChainTransactionConfirmations(
    chainKey,
    rows.rows.map((row) => row.tx_hash)
  );

  return rows.rows.map((row) => {
    const status = normalizeWithdrawStatus(row.status);
    return {
      approvalId: row.approval_id,
      decisionId: row.decision_id,
      requestKind: 'withdraw',
      chainKey: row.chain_key,
      status,
      transferType: row.transfer_type,
      tokenAddress: row.token_address,
      tokenSymbol: row.token_symbol,
      destination: row.to_address,
      amountWei: row.amount_wei,
      txHash: row.tx_hash,
      reasonCode: row.reason_code,
      reasonMessage: row.reason_message,
      executionMode: row.execution_mode,
      confirmations: row.tx_hash ? (confirmationsByTx.get(row.tx_hash) ?? null) : null,
      createdAt: row.created_at,
      decidedAt: row.decided_at,
      terminalAt: row.terminal_at
    };
  });
}
