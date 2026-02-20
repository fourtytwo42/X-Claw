import type { NextRequest } from 'next/server';

import { chainRpcUrl } from '@/lib/chains';
import { dbQuery } from '@/lib/db';
import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import { fetchWithTimeout, upstreamFetchTimeoutMs } from '@/lib/fetch-timeout';
import { requireManagementSession, sessionHasAgentAccess } from '@/lib/management-auth';
import { getRequestId } from '@/lib/request-id';
import { kickStaleTransferRecovery } from '@/lib/transfer-recovery';

export const runtime = 'nodejs';

type RpcReceipt = { blockNumber?: string | null };

function hexToBigInt(raw: string): bigint {
  if (!raw || typeof raw !== 'string') {
    return BigInt(0);
  }
  return BigInt(raw);
}

async function rpcRequest(rpcUrl: string, method: string, params: unknown[]): Promise<unknown> {
  const res = await fetchWithTimeout(
    rpcUrl,
    {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ jsonrpc: '2.0', id: 1, method, params })
    },
    upstreamFetchTimeoutMs(),
  );
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

export async function GET(req: NextRequest) {
  const requestId = getRequestId(req);
  try {
    const agentId = req.nextUrl.searchParams.get('agentId')?.trim();
    if (!agentId) {
      return errorResponse(
        400,
        { code: 'payload_invalid', message: 'agentId query parameter is required.', actionHint: 'Provide ?agentId=<agent-id>.' },
        requestId
      );
    }

    const auth = await requireManagementSession(req, requestId);
    if (!auth.ok) {
      return auth.response;
    }
    if (!sessionHasAgentAccess(auth.session, agentId)) {
      return errorResponse(
        401,
        {
          code: 'auth_invalid',
          message: 'Management session is not authorized for this agent.',
          actionHint: 'Use the matching agent management session.'
        },
        requestId
      );
    }

    const chainKey = req.nextUrl.searchParams.get('chainKey')?.trim() || 'base_sepolia';
    try {
      await kickStaleTransferRecovery(agentId, chainKey);
    } catch {}
    const [queue, history] = await Promise.all([
      dbQuery<{
        approval_id: string;
        chain_key: string;
        status: string;
        transfer_type: 'native' | 'token';
        approval_source: 'transfer' | 'x402';
        token_address: string | null;
        token_symbol: string | null;
        to_address: string;
        amount_wei: string;
        policy_blocked_at_create: boolean;
        policy_block_reason_code: string | null;
        policy_block_reason_message: string | null;
        execution_mode: 'normal' | 'policy_override' | null;
        x402_url: string | null;
        x402_network_key: string | null;
        x402_facilitator_key: string | null;
        x402_asset_kind: 'native' | 'erc20' | null;
        x402_asset_address: string | null;
        x402_amount_atomic: string | null;
        x402_payment_id: string | null;
        created_at: string;
      }>(
        `
        select
          approval_id,
          chain_key,
          status::text,
          transfer_type::text,
          approval_source::text,
          token_address,
          token_symbol,
          to_address,
          amount_wei::text,
          policy_blocked_at_create,
          policy_block_reason_code,
          policy_block_reason_message,
          execution_mode,
          x402_url,
          x402_network_key,
          x402_facilitator_key,
          x402_asset_kind::text,
          x402_asset_address,
          x402_amount_atomic::text,
          x402_payment_id,
          created_at::text
        from agent_transfer_approval_mirror
        where agent_id = $1
          and chain_key = $2
          and status = 'approval_pending'
        order by created_at asc
        limit 100
        `,
        [agentId, chainKey]
      ),
      dbQuery<{
        approval_id: string;
        chain_key: string;
        status: string;
        transfer_type: 'native' | 'token';
        approval_source: 'transfer' | 'x402';
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
        x402_url: string | null;
        x402_network_key: string | null;
        x402_facilitator_key: string | null;
        x402_asset_kind: 'native' | 'erc20' | null;
        x402_asset_address: string | null;
        x402_amount_atomic: string | null;
        x402_payment_id: string | null;
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
          approval_source::text,
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
          x402_url,
          x402_network_key,
          x402_facilitator_key,
          x402_asset_kind::text,
          x402_asset_address,
          x402_amount_atomic::text,
          x402_payment_id,
          created_at::text,
          decided_at::text,
          terminal_at::text
        from agent_transfer_approval_mirror
        where agent_id = $1
          and chain_key = $2
        order by created_at desc
        limit 100
        `,
        [agentId, chainKey]
      )
    ]);

    const transferConfirmationsByTx = await fetchTransferConfirmations(chainKey, history.rows);
    return successResponse(
      {
        ok: true,
        agentId,
        chainKey,
        queue: queue.rows.map((row) => ({ ...row, confirmations: null })),
        history: history.rows.map((row) => ({
          ...row,
          confirmations: row.tx_hash ? (transferConfirmationsByTx.get(row.tx_hash) ?? null) : null
        }))
      },
      200,
      requestId
    );
  } catch {
    return internalErrorResponse(requestId);
  }
}
