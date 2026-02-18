import type { NextRequest } from 'next/server';

import { chainRpcUrl, getChainConfig } from '@/lib/chains';
import { dbQuery, withTransaction } from '@/lib/db';
import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import { makeId } from '@/lib/ids';
import { requireCsrfToken, requireManagementSession, sessionHasAgentAccess } from '@/lib/management-auth';
import { getRequestId } from '@/lib/request-id';
import { resolveTokenDecimals } from '@/lib/token-metadata';

export const runtime = 'nodejs';

const TRANSFER_TOPIC0 = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef';

type RpcLog = {
  address: string;
  blockNumber: string;
  transactionHash: string;
  logIndex: string;
  topics: string[];
  data: string;
};

function toHexBlock(blockNumber: bigint): string {
  return `0x${blockNumber.toString(16)}`;
}

function hexToBigInt(raw: string): bigint {
  if (!raw || typeof raw !== 'string') {
    return BigInt(0);
  }
  return BigInt(raw);
}

function topicAddress(address: string): string {
  return `0x${'0'.repeat(24)}${address.toLowerCase().slice(2)}`;
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

async function syncChainDeposits(agentId: string, chainKey: string, walletAddress: string) {
  const rpcUrl = chainRpcUrl(chainKey);
  const cfg = getChainConfig(chainKey);
  if (!rpcUrl || !cfg) {
    return { syncStatus: 'degraded' as const, syncDetail: 'Missing chain RPC config.', minConfirmations: 1 };
  }

  const minConfirmations = chainKey === 'hardhat_local' ? 1 : 2;

  try {
    const latestHex = (await rpcRequest(rpcUrl, 'eth_blockNumber', [])) as string;
    const latestBlock = hexToBigInt(latestHex);

    const nativeBalHex = (await rpcRequest(rpcUrl, 'eth_getBalance', [walletAddress, 'latest'])) as string;
    const nativeBalance = hexToBigInt(nativeBalHex).toString();

    await withTransaction(async (client) => {
      await client.query(
        `
        insert into wallet_balance_snapshots (
          snapshot_id, agent_id, chain_key, token, balance, block_number, observed_at, created_at
        ) values ($1, $2, $3, $4, $5, $6, now(), now())
        on conflict (agent_id, chain_key, token)
        do update set balance = excluded.balance, block_number = excluded.block_number, observed_at = now()
        `,
        [makeId('wbs'), agentId, chainKey, 'NATIVE', nativeBalance, Number(latestBlock)]
      );
    });

    const canonicalTokens = cfg.canonicalTokens ?? {};
    const fromBlock = latestBlock > BigInt(3000) ? latestBlock - BigInt(3000) : BigInt(0);

    for (const [symbol, tokenAddress] of Object.entries(canonicalTokens)) {
      const balanceResult = (await rpcRequest(rpcUrl, 'eth_call', [
        {
          to: tokenAddress,
          data: `0x70a08231000000000000000000000000${walletAddress.slice(2).toLowerCase()}`
        },
        'latest'
      ])) as string;

      const tokenBalance = hexToBigInt(balanceResult).toString();
      await withTransaction(async (client) => {
        await client.query(
          `
          insert into wallet_balance_snapshots (
            snapshot_id, agent_id, chain_key, token, balance, block_number, observed_at, created_at
          ) values ($1, $2, $3, $4, $5, $6, now(), now())
          on conflict (agent_id, chain_key, token)
          do update set balance = excluded.balance, block_number = excluded.block_number, observed_at = now()
          `,
          [makeId('wbs'), agentId, chainKey, symbol, tokenBalance, Number(latestBlock)]
        );
      });

      const logs = (await rpcRequest(rpcUrl, 'eth_getLogs', [
        {
          address: tokenAddress,
          fromBlock: toHexBlock(fromBlock),
          toBlock: toHexBlock(latestBlock),
          topics: [TRANSFER_TOPIC0, null, topicAddress(walletAddress)]
        }
      ])) as RpcLog[];

      for (const entry of logs) {
        const blockNumber = Number(hexToBigInt(entry.blockNumber));
        if (Number(latestBlock) - blockNumber + 1 < minConfirmations) {
          continue;
        }

        const amount = hexToBigInt(entry.data).toString();
        const logIndex = Number(hexToBigInt(entry.logIndex));

        await withTransaction(async (client) => {
          await client.query(
            `
            insert into deposit_events (
              deposit_event_id, agent_id, chain_key, token, amount, tx_hash, log_index, block_number, confirmed_at, status, created_at
            )
            select $1, $2, $3, $4, $5, $6, $7, $8, now(), 'confirmed', now()
            where not exists (
              select 1
              from trades
              where agent_id = $2
                and chain_key = $3
                and tx_hash is not null
                and lower(tx_hash) = lower($6)
            )
            on conflict (chain_key, tx_hash, log_index, token)
            do nothing
            `,
            [makeId('dep'), agentId, chainKey, symbol, amount, entry.transactionHash, logIndex, blockNumber]
          );
        });
      }
    }

    return { syncStatus: 'ok' as const, syncDetail: null, minConfirmations };
  } catch (error) {
    return {
      syncStatus: 'degraded' as const,
      syncDetail: error instanceof Error ? error.message : 'Unknown RPC failure',
      minConfirmations
    };
  }
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

    const csrf = requireCsrfToken(req, requestId);
    if (!csrf.ok) {
      return csrf.response;
    }

    if (!sessionHasAgentAccess(auth.session, agentId)) {
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

    const chainFilter = req.nextUrl.searchParams.get('chainKey')?.trim();

    const wallets = await dbQuery<{ chain_key: string; address: string }>(
      `
      select chain_key, address
      from agent_wallets
      where agent_id = $1
      ${chainFilter ? 'and chain_key = $2' : ''}
      order by chain_key asc
      `,
      chainFilter ? [agentId, chainFilter] : [agentId]
    );

    const chains = [] as Array<{
      chainKey: string;
      depositAddress: string;
      minConfirmations: number;
      lastSyncedAt: string | null;
      syncStatus: 'ok' | 'degraded';
      syncDetail: string | null;
      balances: Array<{ token: string; balance: string; blockNumber: number | null; observedAt: string }>;
      recentDeposits: Array<{ token: string; amount: string; txHash: string; blockNumber: number; confirmedAt: string; status: string }>;
      explorerBaseUrl: string | null;
    }>;

    for (const wallet of wallets.rows) {
      const cfg = getChainConfig(wallet.chain_key);
      const sync = await syncChainDeposits(agentId, wallet.chain_key, wallet.address);

      const [balances, deposits] = await Promise.all([
        dbQuery<{ token: string; balance: string; block_number: string | null; observed_at: string }>(
          `
          select token, balance::text, block_number::text, observed_at::text
          from wallet_balance_snapshots
          where agent_id = $1 and chain_key = $2
          order by token asc
          `,
          [agentId, wallet.chain_key]
        ),
        dbQuery<{ token: string; amount: string; tx_hash: string; block_number: string; confirmed_at: string; status: string }>(
          `
          select token, amount::text, tx_hash, block_number::text, confirmed_at::text, status
          from deposit_events
          where agent_id = $1 and chain_key = $2
          order by confirmed_at desc
          limit 25
          `,
          [agentId, wallet.chain_key]
        )
      ]);

      const lastSyncedAt = balances.rows.length > 0 ? balances.rows[0].observed_at : null;
      const decimalsByToken = new Map<string, number>();
      await Promise.all(
        Array.from(new Set(balances.rows.map((row) => String(row.token).trim()).filter((token) => token.length > 0))).map(async (token) => {
          const resolved = await resolveTokenDecimals(wallet.chain_key, token).catch(() => 18);
          decimalsByToken.set(token, resolved);
        })
      );

      chains.push({
        chainKey: wallet.chain_key,
        depositAddress: wallet.address,
        minConfirmations: sync.minConfirmations,
        lastSyncedAt,
        syncStatus: sync.syncStatus,
        syncDetail: sync.syncDetail,
        balances: balances.rows.map((row) => ({
          token: row.token,
          balance: row.balance,
          decimals: decimalsByToken.get(row.token) ?? 18,
          blockNumber: row.block_number ? Number(row.block_number) : null,
          observedAt: row.observed_at
        })),
        recentDeposits: deposits.rows.map((row) => ({
          token: row.token,
          amount: row.amount,
          txHash: row.tx_hash,
          blockNumber: Number(row.block_number),
          confirmedAt: row.confirmed_at,
          status: row.status
        })),
        explorerBaseUrl: cfg?.explorerBaseUrl ?? null
      });
    }

    return successResponse(
      {
        ok: true,
        agentId,
        chains
      },
      200,
      requestId
    );
  } catch {
    return internalErrorResponse(requestId);
  }
}
