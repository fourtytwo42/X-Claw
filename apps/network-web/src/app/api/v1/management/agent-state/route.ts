import type { NextRequest } from 'next/server';

import { dbQuery } from '@/lib/db';
import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import { chainRpcUrl, getChainConfig } from '@/lib/chains';
import { requireManagementSession } from '@/lib/management-auth';
import { getRequestId } from '@/lib/request-id';

export const runtime = 'nodejs';

type RpcReceipt = { blockNumber?: string | null };

function hexToBigInt(raw: string): bigint {
  if (!raw || typeof raw !== 'string') {
    return BigInt(0);
  }
  return BigInt(raw);
}

async function rpcRequest(rpcUrl: string, method: string, params: unknown[]): Promise<unknown> {
  const res = await fetch(rpcUrl, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ jsonrpc: '2.0', id: 1, method, params })
  });
  if (!res.ok) {
    throw new Error(`RPC ${method} failed with HTTP ${res.status}`);
  }
  const parsed = (await res.json()) as { result?: unknown; error?: { message?: string } };
  if (parsed.error) {
    throw new Error(parsed.error.message ?? `RPC ${method} returned error`);
  }
  return parsed.result;
}

async function fetchTransferConfirmations(
  chainKey: string,
  historyRows: Array<{ tx_hash: string | null }>
): Promise<Map<string, number | null>> {
  const byHash = new Map<string, number | null>();
  const rpcUrl = chainRpcUrl(chainKey);
  if (!rpcUrl) {
    return byHash;
  }
  const txHashes = Array.from(new Set(historyRows.map((row) => row.tx_hash).filter((hash): hash is string => Boolean(hash))));
  if (txHashes.length === 0) {
    return byHash;
  }
  try {
    const latestHex = (await rpcRequest(rpcUrl, 'eth_blockNumber', [])) as string;
    const latest = hexToBigInt(latestHex);
    await Promise.all(
      txHashes.map(async (txHash) => {
        try {
          const receipt = (await rpcRequest(rpcUrl, 'eth_getTransactionReceipt', [txHash])) as RpcReceipt | null;
          if (!receipt?.blockNumber) {
            byHash.set(txHash, null);
            return;
          }
          const txBlock = hexToBigInt(receipt.blockNumber);
          const confirmations = latest >= txBlock ? Number(latest - txBlock + BigInt(1)) : 0;
          byHash.set(txHash, confirmations);
        } catch {
          byHash.set(txHash, null);
        }
      })
    );
  } catch {
    return byHash;
  }
  return byHash;
}

function isMissingTransferMirrorSchema(error: unknown): boolean {
  if (!error || typeof error !== 'object') {
    return false;
  }
  const code = 'code' in error ? String((error as { code?: unknown }).code ?? '') : '';
  if (code === '42703' || code === '42P01') {
    return true;
  }
  const message = 'message' in error ? String((error as { message?: unknown }).message ?? '') : '';
  return (
    message.includes('agent_transfer_approval_mirror') ||
    message.includes('agent_transfer_policy_mirror') ||
    message.includes('policy_blocked_at_create') ||
    message.includes('policy_block_reason_code') ||
    message.includes('policy_block_reason_message') ||
    message.includes('execution_mode')
  );
}

export async function GET(req: NextRequest) {
  const requestId = getRequestId(req);

  try {
    const agentId = req.nextUrl.searchParams.get('agentId');
    if (!agentId) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'agentId query parameter is required.',
          actionHint: 'Provide ?agentId=<agent-id>.'
        },
        requestId
      );
    }

    const auth = await requireManagementSession(req, requestId);
    if (!auth.ok) {
      return auth.response;
    }

    if (auth.session.agentId !== agentId) {
      return errorResponse(
        401,
        {
          code: 'auth_invalid',
          message: 'Management session is not authorized for this agent.',
          actionHint: 'Use the matching agent session for this route.'
        },
        requestId
      );
    }

    const chainKey = req.nextUrl.searchParams.get('chainKey')?.trim() || 'base_sepolia';
    const chainCfg = getChainConfig(chainKey);
    if (!chainCfg) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Invalid chainKey query parameter value.',
          actionHint: 'Provide a supported chainKey (for example base_sepolia).',
          details: { chainKey }
        },
        requestId
      );
    }

    const chainTokens = Object.entries(chainCfg.canonicalTokens ?? {}).map(([symbol, address]) => ({
      symbol,
      address
    }));

    const [
      agent,
      approvals,
      policyApprovals,
      policyApprovalsHistory,
      policy,
      audit,
      outboundPolicy,
      dailyUsage,
      chainPolicy,
      approvalChannel,
      transferApprovalsQueue,
      transferApprovalsHistory,
      transferPolicyMirror,
      trackedAgents,
      trackedRecentTrades
    ] = await Promise.all([
      dbQuery<{
        agent_id: string;
        public_status: string;
        openclaw_metadata: Record<string, unknown> | null;
      }>(
        `
        select agent_id, public_status, openclaw_metadata
        from agents
        where agent_id = $1
        limit 1
        `,
        [agentId]
      ),
      dbQuery<{
        trade_id: string;
        chain_key: string;
        pair: string;
        amount_in: string | null;
        token_in: string;
        token_out: string;
        reason: string | null;
        created_at: string;
      }>(
        `
        select trade_id, chain_key, pair, amount_in::text, token_in, token_out, reason, created_at::text
        from trades
        where agent_id = $1
          and status = 'approval_pending'
        order by created_at asc
        limit 50
        `,
        [agentId]
      ),
      dbQuery<{
        request_id: string;
        chain_key: string;
        request_type: string;
        token_address: string | null;
        created_at: string;
      }>(
        `
        select request_id, chain_key, request_type, token_address, created_at::text
        from agent_policy_approval_requests
        where agent_id = $1
          and status = 'approval_pending'
        order by created_at asc
        limit 50
        `,
        [agentId]
      ),
      dbQuery<{
        request_id: string;
        chain_key: string;
        request_type: string;
        token_address: string | null;
        status: string;
        reason_message: string | null;
        created_at: string;
        decided_at: string | null;
      }>(
        `
        select
          request_id,
          chain_key,
          request_type,
          token_address,
          status::text,
          reason_message,
          created_at::text,
          decided_at::text
        from agent_policy_approval_requests
        where agent_id = $1
        order by created_at desc
        limit 50
        `,
        [agentId]
      ),
      dbQuery<{
        mode: 'mock' | 'real';
        approval_mode: 'per_trade' | 'auto';
        max_trade_usd: string | null;
        max_daily_usd: string | null;
        allowed_tokens: string[];
        daily_cap_usd_enabled: boolean;
        daily_trade_cap_enabled: boolean;
        max_daily_trade_count: string | null;
        created_at: string;
      }>(
        `
        select
          mode,
          approval_mode,
          max_trade_usd::text,
          max_daily_usd::text,
          allowed_tokens,
          daily_cap_usd_enabled,
          daily_trade_cap_enabled,
          max_daily_trade_count::text,
          created_at::text
        from agent_policy_snapshots
        where agent_id = $1
        order by created_at desc
        limit 1
        `,
        [agentId]
      ),
      dbQuery<{
        audit_id: string;
        action_type: string;
        action_status: string;
        public_redacted_payload: Record<string, unknown>;
        created_at: string;
      }>(
        `
        select audit_id, action_type, action_status, public_redacted_payload, created_at::text
        from management_audit_log
        where agent_id = $1
        order by created_at desc
        limit 25
        `,
        [agentId]
      ),
      dbQuery<{
        outbound_transfers_enabled: boolean;
        outbound_mode: 'disabled' | 'allow_all' | 'whitelist';
        outbound_whitelist_addresses: unknown;
        updated_at: string;
      }>(
        `
        select outbound_transfers_enabled, outbound_mode::text, outbound_whitelist_addresses, updated_at::text
        from agent_transfer_policies
        where agent_id = $1
          and chain_key = $2
        limit 1
        `,
        [agentId, chainKey]
      ),
      dbQuery<{
        utc_day: string;
        daily_spend_usd: string;
        daily_filled_trades: string;
      }>(
        `
        select utc_day::text, daily_spend_usd::text, daily_filled_trades::text
        from agent_daily_trade_usage
        where agent_id = $1
          and chain_key = $2
          and utc_day = (now() at time zone 'utc')::date
        limit 1
        `,
        [agentId, chainKey]
      ),
      dbQuery<{ chain_enabled: boolean; updated_at: string }>(
        `
        select chain_enabled, updated_at::text
        from agent_chain_policies
        where agent_id = $1
          and chain_key = $2
        limit 1
        `,
        [agentId, chainKey]
      ),
      dbQuery<{ enabled: boolean; updated_at: string }>(
        `
        select enabled, updated_at::text
        from agent_chain_approval_channels
        where agent_id = $1
          and chain_key = $2
          and channel = 'telegram'
        limit 1
        `,
        [agentId, chainKey]
      ),
      dbQuery<{
        approval_id: string;
        chain_key: string;
        status: string;
        transfer_type: string;
        token_address: string | null;
        token_symbol: string | null;
        to_address: string;
        amount_wei: string;
        policy_blocked_at_create: boolean;
        policy_block_reason_code: string | null;
        policy_block_reason_message: string | null;
        execution_mode: 'normal' | 'policy_override' | null;
        created_at: string;
      }>(
        `
        select
          approval_id,
          chain_key,
          status::text,
          transfer_type::text,
          token_address,
          token_symbol,
          to_address,
          amount_wei::text,
          policy_blocked_at_create,
          policy_block_reason_code,
          policy_block_reason_message,
          execution_mode,
          created_at::text
        from agent_transfer_approval_mirror
        where agent_id = $1
          and chain_key = $2
          and status = 'approval_pending'
        order by created_at asc
        limit 50
        `,
        [agentId, chainKey]
      ).catch((error) => {
        if (isMissingTransferMirrorSchema(error)) {
          return { rowCount: 0, rows: [] };
        }
        throw error;
      }),
      dbQuery<{
        approval_id: string;
        chain_key: string;
        status: string;
        transfer_type: string;
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
      }>(
        `
        select
          approval_id,
          chain_key,
          status::text,
          transfer_type::text,
          token_address,
          token_symbol,
          to_address,
          amount_wei::text,
          tx_hash,
          reason_message,
          policy_blocked_at_create,
          policy_block_reason_code,
          policy_block_reason_message,
          execution_mode,
          created_at::text,
          decided_at::text,
          terminal_at::text
        from agent_transfer_approval_mirror
        where agent_id = $1
          and chain_key = $2
        order by created_at desc
        limit 50
        `,
        [agentId, chainKey]
      ).catch((error) => {
        if (isMissingTransferMirrorSchema(error)) {
          return { rowCount: 0, rows: [] };
        }
        throw error;
      }),
      dbQuery<{
        transfer_approval_mode: 'auto' | 'per_transfer';
        native_transfer_preapproved: boolean;
        allowed_transfer_tokens: unknown;
        updated_at: string;
      }>(
        `
        select
          transfer_approval_mode::text,
          native_transfer_preapproved,
          allowed_transfer_tokens,
          updated_at::text
        from agent_transfer_policy_mirror
        where agent_id = $1
          and chain_key = $2
        limit 1
        `,
        [agentId, chainKey]
      ).catch((error) => {
        if (isMissingTransferMirrorSchema(error)) {
          return { rowCount: 0, rows: [] };
        }
        throw error;
      }),
      dbQuery<{
        tracking_id: string;
        tracked_agent_id: string;
        agent_name: string;
        public_status: string;
        wallet_address: string | null;
        last_activity_at: string | null;
        last_heartbeat_at: string | null;
        metrics_pnl_usd: string | null;
        metrics_return_pct: string | null;
        metrics_volume_usd: string | null;
        metrics_trades_count: number | null;
        metrics_as_of: string | null;
        created_at: string;
      }>(
        `
        select
          ata.tracking_id,
          ata.tracked_agent_id,
          a.agent_name,
          a.public_status::text,
          aw.address as wallet_address,
          a.last_activity_at::text,
          a.last_heartbeat_at::text,
          ps.pnl_usd::text as metrics_pnl_usd,
          ps.return_pct::text as metrics_return_pct,
          ps.volume_usd::text as metrics_volume_usd,
          ps.trades_count as metrics_trades_count,
          ps.created_at::text as metrics_as_of,
          ata.created_at::text
        from agent_tracked_agents ata
        inner join agents a on a.agent_id = ata.tracked_agent_id
        left join agent_wallets aw
          on aw.agent_id = ata.tracked_agent_id
          and aw.chain_key = $2
        left join lateral (
          select
            ps.pnl_usd,
            ps.return_pct,
            ps.volume_usd,
            ps.trades_count,
            ps.created_at
          from performance_snapshots ps
          where ps.agent_id = ata.tracked_agent_id
            and ps.window = '24h'
            and ps.mode = 'real'
            and ps.chain_key = $2
          order by ps.created_at desc
          limit 1
        ) ps on true
        where ata.agent_id = $1
        order by ata.created_at desc
        limit 100
        `,
        [agentId, chainKey]
      ),
      dbQuery<{
        trade_id: string;
        tracked_agent_id: string;
        agent_name: string;
        chain_key: string;
        status: string;
        pair: string | null;
        token_in: string;
        token_out: string;
        amount_in: string | null;
        amount_out: string | null;
        tx_hash: string | null;
        executed_at: string | null;
        created_at: string;
      }>(
        `
        select
          t.trade_id,
          t.agent_id as tracked_agent_id,
          a.agent_name,
          t.chain_key,
          t.status::text,
          t.pair,
          t.token_in,
          t.token_out,
          t.amount_in::text,
          t.amount_out::text,
          t.tx_hash,
          t.executed_at::text,
          t.created_at::text
        from trades t
        inner join agent_tracked_agents ata
          on ata.agent_id = $1
         and ata.tracked_agent_id = t.agent_id
        inner join agents a
          on a.agent_id = t.agent_id
        where t.status = 'filled'
          and ($2::text = 'all' or t.chain_key = $2)
        order by coalesce(t.executed_at, t.created_at) desc, t.created_at desc
        limit 20
        `,
        [agentId, chainKey]
      )
    ]);

    if (agent.rowCount === 0) {
      return errorResponse(
        404,
        {
          code: 'payload_invalid',
          message: 'Agent was not found.',
          actionHint: 'Verify agentId and retry.'
        },
        requestId
      );
    }

    const telegramApprovalEnabled = (approvalChannel.rowCount ?? 0) > 0 ? Boolean(approvalChannel.rows[0].enabled) : false;
    const telegramApprovalUpdatedAt = (approvalChannel.rowCount ?? 0) > 0 ? approvalChannel.rows[0].updated_at ?? null : null;
    const transferConfirmationsByTx = await fetchTransferConfirmations(chainKey, transferApprovalsHistory.rows);

    return successResponse(
      {
        ok: true,
        agent: {
          agentId: agent.rows[0].agent_id,
          publicStatus: agent.rows[0].public_status,
          metadata: agent.rows[0].openclaw_metadata ?? {}
        },
        chainTokens,
        approvalChannels: {
          telegram: { enabled: telegramApprovalEnabled, updatedAt: telegramApprovalUpdatedAt }
        },
        approvalsQueue: approvals.rows,
        policyApprovalsQueue: policyApprovals.rows,
        policyApprovalsHistory: policyApprovalsHistory.rows,
        transferApprovalsQueue: transferApprovalsQueue.rows.map((row) => ({ ...row, confirmations: null })),
        transferApprovalsHistory: transferApprovalsHistory.rows.map((row) => ({
          ...row,
          confirmations: row.tx_hash ? (transferConfirmationsByTx.get(row.tx_hash) ?? null) : null
        })),
        transferApprovalPolicy:
          (transferPolicyMirror.rowCount ?? 0) > 0
            ? {
                chainKey,
                transferApprovalMode: transferPolicyMirror.rows[0].transfer_approval_mode,
                nativeTransferPreapproved: transferPolicyMirror.rows[0].native_transfer_preapproved,
                allowedTransferTokens: Array.isArray(transferPolicyMirror.rows[0].allowed_transfer_tokens)
                  ? transferPolicyMirror.rows[0].allowed_transfer_tokens
                  : [],
                updatedAt: transferPolicyMirror.rows[0].updated_at
              }
            : {
                chainKey,
                transferApprovalMode: 'per_transfer',
                nativeTransferPreapproved: false,
                allowedTransferTokens: [],
                updatedAt: null
              },
        latestPolicy: policy.rows[0] ?? null,
        tradeCaps: policy.rows[0]
          ? {
              dailyCapUsdEnabled: policy.rows[0].daily_cap_usd_enabled,
              dailyTradeCapEnabled: policy.rows[0].daily_trade_cap_enabled,
              maxDailyTradeCount:
                policy.rows[0].max_daily_trade_count === null ? null : Number.parseInt(policy.rows[0].max_daily_trade_count, 10)
            }
          : {
              dailyCapUsdEnabled: true,
              dailyTradeCapEnabled: true,
              maxDailyTradeCount: null
            },
        dailyUsage:
          (dailyUsage.rowCount ?? 0) > 0
            ? {
                utcDay: dailyUsage.rows[0].utc_day,
                dailySpendUsd: dailyUsage.rows[0].daily_spend_usd,
                dailyFilledTrades: Number.parseInt(dailyUsage.rows[0].daily_filled_trades, 10)
              }
            : {
                utcDay: new Date().toISOString().slice(0, 10),
                dailySpendUsd: '0',
                dailyFilledTrades: 0
              },
        outboundTransfersPolicy:
          (outboundPolicy.rowCount ?? 0) > 0
            ? {
                outboundTransfersEnabled: outboundPolicy.rows[0].outbound_transfers_enabled,
                outboundMode: outboundPolicy.rows[0].outbound_mode,
                outboundWhitelistAddresses: Array.isArray(outboundPolicy.rows[0].outbound_whitelist_addresses)
                  ? outboundPolicy.rows[0].outbound_whitelist_addresses
                  : [],
                updatedAt: outboundPolicy.rows[0].updated_at
              }
            : {
                outboundTransfersEnabled: false,
                outboundMode: 'disabled',
                outboundWhitelistAddresses: [],
                updatedAt: null
              },
        chainPolicy:
          (chainPolicy.rowCount ?? 0) > 0
            ? { chainKey, chainEnabled: Boolean(chainPolicy.rows[0].chain_enabled), updatedAt: chainPolicy.rows[0].updated_at ?? null }
            : { chainKey, chainEnabled: true, updatedAt: null },
        auditLog: audit.rows,
        trackedAgents: trackedAgents.rows.map((row) => ({
          trackingId: row.tracking_id,
          trackedAgentId: row.tracked_agent_id,
          agentName: row.agent_name,
          publicStatus: row.public_status,
          walletAddress: row.wallet_address,
          lastActivityAt: row.last_activity_at,
          lastHeartbeatAt: row.last_heartbeat_at,
          latestMetrics:
            row.metrics_pnl_usd !== null ||
            row.metrics_return_pct !== null ||
            row.metrics_volume_usd !== null ||
            row.metrics_trades_count !== null
              ? {
                  pnlUsd: row.metrics_pnl_usd,
                  returnPct: row.metrics_return_pct,
                  volumeUsd: row.metrics_volume_usd,
                  tradesCount: Number.isFinite(Number(row.metrics_trades_count)) ? Number(row.metrics_trades_count) : 0,
                  asOf: row.metrics_as_of
                }
              : null,
          createdAt: row.created_at
        })),
        trackedRecentTrades: trackedRecentTrades.rows.map((row) => ({
          tradeId: row.trade_id,
          trackedAgentId: row.tracked_agent_id,
          agentName: row.agent_name,
          chainKey: row.chain_key,
          status: row.status,
          pair: row.pair,
          tokenIn: row.token_in,
          tokenOut: row.token_out,
          amountIn: row.amount_in,
          amountOut: row.amount_out,
          txHash: row.tx_hash,
          executedAt: row.executed_at,
          createdAt: row.created_at
        })),
        managementSession: {
          sessionId: auth.session.sessionId,
          expiresAt: auth.session.expiresAt
        }
      },
      200,
      requestId
    );
  } catch (error) {
    console.error('[management/agent-state] unhandled error', {
      requestId,
      error: error instanceof Error ? error.message : String(error)
    });
    return internalErrorResponse(requestId);
  }
}
