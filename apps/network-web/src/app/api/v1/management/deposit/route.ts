import type { NextRequest } from 'next/server';

import { ensureAgentWalletMappings } from '@/lib/agent-wallet-mappings';
import { chainCapabilityEnabled, chainFamily, chainNativeAtomicDecimals, chainRpcUrl, getChainConfig } from '@/lib/chains';
import { dbQuery, withTransaction } from '@/lib/db';
import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import { fetchWithTimeout, upstreamFetchTimeoutMs } from '@/lib/fetch-timeout';
import { makeId } from '@/lib/ids';
import { requireCsrfToken, requireManagementSession, sessionHasAgentAccess } from '@/lib/management-auth';
import { getRequestId } from '@/lib/request-id';
import { resolveTokenDecimals } from '@/lib/token-metadata';

export const runtime = 'nodejs';

const TRANSFER_TOPIC0 = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef';
const SOLANA_TOKEN_PROGRAM_ID = 'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA';

type RpcLog = {
  blockNumber: string;
  transactionHash: string;
  logIndex: string;
  data: string;
};

type DepositSyncResult = {
  syncStatus: 'ok' | 'degraded';
  syncDetail: string | null;
  minConfirmations: number;
  discoveredTokenDecimals: Record<string, number>;
};

type SolanaSignatureRow = {
  signature?: string;
  slot?: number;
  err?: unknown;
  blockTime?: number | null;
};

type SolanaTxMeta = {
  preBalances?: number[];
  postBalances?: number[];
  preTokenBalances?: Array<{ owner?: string; mint?: string; uiTokenAmount?: { amount?: string } }>;
  postTokenBalances?: Array<{ owner?: string; mint?: string; uiTokenAmount?: { amount?: string } }>;
};

type SolanaTxPayload = {
  meta?: SolanaTxMeta;
  transaction?: {
    message?: {
      accountKeys?: Array<string | { pubkey?: string }>;
    };
  };
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

function parseBigInt(raw: unknown): bigint {
  try {
    return BigInt(String(raw ?? '0'));
  } catch {
    return BigInt(0);
  }
}

function topicAddress(address: string): string {
  return `0x${'0'.repeat(24)}${address.toLowerCase().slice(2)}`;
}

function nativeAtomicDecimalsForBalance(chainKey: string, token: string): number | null {
  const normalized = String(token || '').trim().toUpperCase();
  if (normalized === 'NATIVE') {
    return chainNativeAtomicDecimals(chainKey);
  }
  return null;
}

async function rpcRequest(rpcUrl: string, method: string, params: unknown[]): Promise<unknown> {
  const res = await fetchWithTimeout(
    rpcUrl,
    {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ jsonrpc: '2.0', id: 1, method, params }),
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

async function upsertBalanceSnapshot(
  agentId: string,
  chainKey: string,
  token: string,
  balance: string,
  blockNumber: number
): Promise<void> {
  await withTransaction(async (client) => {
    await client.query(
      `
      insert into wallet_balance_snapshots (
        snapshot_id, agent_id, chain_key, token, balance, block_number, observed_at, created_at,
        observed_by, observation_source, watcher_run_id
      ) values ($1, $2, $3, $4, $5, $6, now(), now(), 'legacy_server_poller', 'rpc_log', 'server_poller_dual_run')
      on conflict (agent_id, chain_key, token)
      do update set
        balance = excluded.balance,
        block_number = excluded.block_number,
        observed_at = now(),
        observed_by = excluded.observed_by,
        observation_source = excluded.observation_source,
        watcher_run_id = excluded.watcher_run_id
      `,
      [makeId('wbs'), agentId, chainKey, token, balance, blockNumber]
    );
  });
}

async function insertDepositEventEvm(
  agentId: string,
  chainKey: string,
  token: string,
  amount: string,
  txHash: string,
  logIndex: number,
  blockNumber: number
): Promise<void> {
  await withTransaction(async (client) => {
    await client.query(
      `
      insert into deposit_events (
        deposit_event_id, agent_id, chain_key, token, amount, tx_hash, log_index, block_number, confirmed_at, status, created_at,
        observed_by, observation_source, watcher_run_id
      )
      select $1, $2, $3, $4, $5, $6, $7, $8, now(), 'confirmed', now(), 'legacy_server_poller', 'rpc_log', 'server_poller_dual_run'
      where not exists (
        select 1
        from trades
        where agent_id = $9
          and chain_key = $10
          and tx_hash is not null
          and lower(tx_hash) = lower($11)
      )
      on conflict (chain_key, tx_hash, log_index, token)
      do nothing
      `,
      [makeId('dep'), agentId, chainKey, token, amount, txHash, logIndex, blockNumber, agentId, chainKey, txHash]
    );
  });
}

async function insertDepositEventSolana(
  agentId: string,
  chainKey: string,
  token: string,
  amount: string,
  signature: string,
  logIndex: number,
  slot: number,
  blockTime?: number | null
): Promise<void> {
  await withTransaction(async (client) => {
    await client.query(
      `
      insert into deposit_events (
        deposit_event_id, agent_id, chain_key, token, amount, tx_hash, log_index, block_number, confirmed_at, status, created_at,
        observed_by, observation_source, watcher_run_id
      )
      select $1, $2, $3, $4, $5, $6, $7, $8, coalesce(to_timestamp($9::double precision), now()), 'confirmed', now(), 'legacy_server_poller', 'rpc_log', 'server_poller_dual_run'
      where not exists (
        select 1
        from trades
        where agent_id = $10
          and chain_key = $11
          and tx_hash is not null
          and tx_hash = $12
      )
      on conflict (chain_key, tx_hash, log_index, token)
      do nothing
      `,
      [makeId('dep'), agentId, chainKey, token, amount, signature, logIndex, slot, blockTime ?? null, agentId, chainKey, signature]
    );
  });
}

function parseSolanaDepositEvents(tx: SolanaTxPayload, walletAddress: string): Array<{ token: string; amount: string }> {
  const meta = tx.meta;
  const message = tx.transaction?.message;
  if (!meta || !message) {
    return [];
  }
  const wallet = String(walletAddress || '').trim();
  const accountKeys = Array.isArray(message.accountKeys)
    ? message.accountKeys.map((entry) => {
        if (typeof entry === 'string') {
          return entry;
        }
        return String(entry?.pubkey || '').trim();
      })
    : [];
  const walletIndex = accountKeys.findIndex((entry) => entry === wallet);

  const events = new Map<string, bigint>();

  if (
    walletIndex >= 0 &&
    Array.isArray(meta.preBalances) &&
    Array.isArray(meta.postBalances) &&
    walletIndex < meta.preBalances.length &&
    walletIndex < meta.postBalances.length
  ) {
    const pre = parseBigInt(meta.preBalances[walletIndex]);
    const post = parseBigInt(meta.postBalances[walletIndex]);
    if (post > pre) {
      events.set('NATIVE', post - pre);
    }
  }

  const preToken = new Map<string, bigint>();
  const postToken = new Map<string, bigint>();
  for (const row of Array.isArray(meta.preTokenBalances) ? meta.preTokenBalances : []) {
    const owner = String(row?.owner || '').trim();
    const mint = String(row?.mint || '').trim();
    if (!owner || !mint || owner !== wallet) {
      continue;
    }
    preToken.set(mint, parseBigInt(row?.uiTokenAmount?.amount));
  }
  for (const row of Array.isArray(meta.postTokenBalances) ? meta.postTokenBalances : []) {
    const owner = String(row?.owner || '').trim();
    const mint = String(row?.mint || '').trim();
    if (!owner || !mint || owner !== wallet) {
      continue;
    }
    postToken.set(mint, parseBigInt(row?.uiTokenAmount?.amount));
  }

  for (const [mint, post] of postToken.entries()) {
    const pre = preToken.get(mint) ?? BigInt(0);
    if (post > pre) {
      events.set(mint, post - pre);
    }
  }

  return Array.from(events.entries()).map(([token, amount]) => ({
    token,
    amount: amount.toString(),
  }));
}

async function syncEvmDeposits(agentId: string, chainKey: string, walletAddress: string, rpcUrl: string): Promise<DepositSyncResult> {
  const cfg = getChainConfig(chainKey);
  const minConfirmations = chainKey === 'hardhat_local' ? 1 : 2;
  try {
    const latestHex = (await rpcRequest(rpcUrl, 'eth_blockNumber', [])) as string;
    const latestBlock = hexToBigInt(latestHex);

    const nativeBalHex = (await rpcRequest(rpcUrl, 'eth_getBalance', [walletAddress, 'latest'])) as string;
    const nativeBalance = hexToBigInt(nativeBalHex).toString();
    await upsertBalanceSnapshot(agentId, chainKey, 'NATIVE', nativeBalance, Number(latestBlock));

    const canonicalTokens = cfg?.canonicalTokens ?? {};
    const trackedTokens = await dbQuery<{ token_address: string }>(
      `
      select token_address
      from agent_tracked_tokens
      where agent_id = $1
        and chain_key = $2
      `,
      [agentId, chainKey]
    ).catch(() => ({ rows: [] as Array<{ token_address: string }> }));
    const fromBlock = latestBlock > BigInt(3000) ? latestBlock - BigInt(3000) : BigInt(0);
    const tokenTargets = new Map<string, string>();
    const knownAddresses = new Set<string>();
    for (const [symbol, tokenAddress] of Object.entries(canonicalTokens)) {
      const address = String(tokenAddress || '').trim().toLowerCase();
      if (/^0x[a-f0-9]{40}$/.test(address)) {
        tokenTargets.set(symbol, address);
        knownAddresses.add(address);
      }
    }
    for (const row of trackedTokens.rows ?? []) {
      const address = String(row.token_address || '').trim().toLowerCase();
      if (!/^0x[a-f0-9]{40}$/.test(address) || knownAddresses.has(address)) {
        continue;
      }
      tokenTargets.set(address, address);
      knownAddresses.add(address);
    }

    for (const [snapshotToken, tokenAddress] of tokenTargets.entries()) {
      const balanceResult = (await rpcRequest(rpcUrl, 'eth_call', [
        {
          to: tokenAddress,
          data: `0x70a08231000000000000000000000000${walletAddress.slice(2).toLowerCase()}`,
        },
        'latest',
      ])) as string;
      const tokenBalance = hexToBigInt(balanceResult).toString();
      await upsertBalanceSnapshot(agentId, chainKey, snapshotToken, tokenBalance, Number(latestBlock));

      const logs = (await rpcRequest(rpcUrl, 'eth_getLogs', [
        {
          address: tokenAddress,
          fromBlock: toHexBlock(fromBlock),
          toBlock: toHexBlock(latestBlock),
          topics: [TRANSFER_TOPIC0, null, topicAddress(walletAddress)],
        },
      ])) as RpcLog[];

      for (const entry of logs) {
        const blockNumber = Number(hexToBigInt(entry.blockNumber));
        if (Number(latestBlock) - blockNumber + 1 < minConfirmations) {
          continue;
        }
        const amount = hexToBigInt(entry.data).toString();
        const logIndex = Number(hexToBigInt(entry.logIndex));
        await insertDepositEventEvm(agentId, chainKey, snapshotToken, amount, entry.transactionHash, logIndex, blockNumber);
      }
    }

    return { syncStatus: 'ok', syncDetail: null, minConfirmations, discoveredTokenDecimals: {} };
  } catch (error) {
    return {
      syncStatus: 'degraded',
      syncDetail: error instanceof Error ? error.message : 'Unknown RPC failure',
      minConfirmations,
      discoveredTokenDecimals: {},
    };
  }
}

async function syncSolanaDeposits(agentId: string, chainKey: string, walletAddress: string, rpcUrl: string): Promise<DepositSyncResult> {
  const minConfirmations = 1;
  const discoveredTokenDecimals = new Map<string, number>();

  try {
    const latestSlotRaw = await rpcRequest(rpcUrl, 'getSlot', [{ commitment: 'confirmed' }]);
    const latestSlot = Number(latestSlotRaw || 0);

    const nativeBalanceResp = (await rpcRequest(rpcUrl, 'getBalance', [walletAddress, { commitment: 'confirmed' }])) as { value?: number };
    const nativeBalance = parseBigInt(nativeBalanceResp?.value ?? 0).toString();
    await upsertBalanceSnapshot(agentId, chainKey, 'NATIVE', nativeBalance, latestSlot);

    const tokenAccounts = (await rpcRequest(rpcUrl, 'getTokenAccountsByOwner', [
      walletAddress,
      { programId: SOLANA_TOKEN_PROGRAM_ID },
      { encoding: 'jsonParsed', commitment: 'confirmed' },
    ])) as {
      value?: Array<{
        account?: {
          data?: {
            parsed?: {
              info?: {
                mint?: string;
                tokenAmount?: { amount?: string; decimals?: number };
              };
            };
          };
        };
      }>;
    };

    for (const entry of Array.isArray(tokenAccounts?.value) ? tokenAccounts.value : []) {
      const mint = String(entry?.account?.data?.parsed?.info?.mint || '').trim();
      const tokenAmount = entry?.account?.data?.parsed?.info?.tokenAmount;
      if (!mint || !tokenAmount) {
        continue;
      }
      const amount = parseBigInt(tokenAmount.amount ?? '0').toString();
      const decimals = Number(tokenAmount.decimals ?? 0);
      await upsertBalanceSnapshot(agentId, chainKey, mint, amount, latestSlot);
      if (Number.isFinite(decimals) && decimals >= 0) {
        discoveredTokenDecimals.set(mint, Math.floor(decimals));
      }
    }

    const signatures = (await rpcRequest(rpcUrl, 'getSignaturesForAddress', [
      walletAddress,
      { limit: 25, commitment: 'confirmed' },
    ])) as SolanaSignatureRow[];

    for (const row of Array.isArray(signatures) ? signatures : []) {
      const signature = String(row?.signature || '').trim();
      const slot = Number(row?.slot || 0);
      if (!signature || row?.err != null || !Number.isFinite(slot) || slot <= 0) {
        continue;
      }

      const tx = (await rpcRequest(rpcUrl, 'getTransaction', [
        signature,
        { encoding: 'jsonParsed', maxSupportedTransactionVersion: 0, commitment: 'confirmed' },
      ])) as SolanaTxPayload | null;
      if (!tx || !tx.meta) {
        continue;
      }

      const depositEvents = parseSolanaDepositEvents(tx, walletAddress);
      let eventIndex = 0;
      for (const event of depositEvents) {
        if (parseBigInt(event.amount) <= BigInt(0)) {
          continue;
        }
        await insertDepositEventSolana(agentId, chainKey, event.token, event.amount, signature, eventIndex, slot, row.blockTime);
        eventIndex += 1;
      }
    }

    return {
      syncStatus: 'ok',
      syncDetail: null,
      minConfirmations,
      discoveredTokenDecimals: Object.fromEntries(discoveredTokenDecimals.entries()),
    };
  } catch (error) {
    return {
      syncStatus: 'degraded',
      syncDetail: error instanceof Error ? error.message : 'Unknown Solana RPC failure',
      minConfirmations,
      discoveredTokenDecimals: Object.fromEntries(discoveredTokenDecimals.entries()),
    };
  }
}

async function syncChainDeposits(agentId: string, chainKey: string, walletAddress: string): Promise<DepositSyncResult> {
  const rpcUrl = chainRpcUrl(chainKey);
  const cfg = getChainConfig(chainKey);
  if (!rpcUrl || !cfg) {
    return { syncStatus: 'degraded', syncDetail: 'Missing chain RPC config.', minConfirmations: 1, discoveredTokenDecimals: {} };
  }
  if (chainFamily(chainKey) === 'solana') {
    return syncSolanaDeposits(agentId, chainKey, walletAddress, rpcUrl);
  }
  return syncEvmDeposits(agentId, chainKey, walletAddress, rpcUrl);
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
          actionHint: 'Provide ?agentId=<agent-id>.',
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
          actionHint: 'Use the matching agent session for this route.',
        },
        requestId
      );
    }

    const chainFilter = req.nextUrl.searchParams.get('chainKey')?.trim() || null;
    if (chainFilter && !chainCapabilityEnabled(chainFilter, 'deposits')) {
      return errorResponse(
        400,
        {
          code: 'unsupported_chain',
          message: `Chain '${chainFilter}' does not support deposits.`,
          actionHint: 'Choose a chain with deposits capability enabled.',
          details: { chainKey: chainFilter, requiredCapability: 'deposits' },
        },
        requestId
      );
    }
    await ensureAgentWalletMappings(agentId, chainFilter || undefined);

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

    const eligibleWallets = wallets.rows.filter((wallet) => chainCapabilityEnabled(wallet.chain_key, 'deposits'));
    const chains = [] as Array<{
      chainKey: string;
      depositAddress: string;
      minConfirmations: number;
      watcherAuthority: 'agent_watcher';
      comparatorMode: 'legacy_server_poller_dual_run';
      lastSyncedAt: string | null;
      syncStatus: 'ok' | 'degraded';
      syncDetail: string | null;
      balances: Array<{ token: string; balance: string; decimals?: number; blockNumber: number | null; observedAt: string }>;
      recentDeposits: Array<{ token: string; amount: string; txHash: string; blockNumber: number; confirmedAt: string; status: string }>;
      explorerBaseUrl: string | null;
    }>;

    for (const wallet of eligibleWallets) {
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
        ),
      ]);

      const lastSyncedAt = balances.rows.length > 0 ? balances.rows[0].observed_at : null;
      const decimalsByToken = new Map<string, number>();
      await Promise.all(
        Array.from(new Set(balances.rows.map((row) => String(row.token).trim()).filter((token) => token.length > 0))).map(async (token) => {
          const forcedNativeAtomic = nativeAtomicDecimalsForBalance(wallet.chain_key, token);
          if (forcedNativeAtomic !== null) {
            decimalsByToken.set(token, forcedNativeAtomic);
            return;
          }
          const resolved = await resolveTokenDecimals(wallet.chain_key, token).catch(() => 18);
          decimalsByToken.set(token, resolved);
        })
      );

      chains.push({
        chainKey: wallet.chain_key,
        depositAddress: wallet.address,
        minConfirmations: sync.minConfirmations,
        watcherAuthority: 'agent_watcher',
        comparatorMode: 'legacy_server_poller_dual_run',
        lastSyncedAt,
        syncStatus: sync.syncStatus,
        syncDetail: sync.syncDetail,
        balances: balances.rows
          .filter((row) => {
            try {
              return BigInt(String(row.balance ?? '0')) > BigInt(0);
            } catch {
              return false;
            }
          })
          .map((row) => ({
            token: row.token,
            balance: row.balance,
            decimals: sync.discoveredTokenDecimals?.[row.token] ?? decimalsByToken.get(row.token) ?? 18,
            blockNumber: row.block_number ? Number(row.block_number) : null,
            observedAt: row.observed_at,
          })),
        recentDeposits: deposits.rows.map((row) => ({
          token: row.token,
          amount: row.amount,
          txHash: row.tx_hash,
          blockNumber: Number(row.block_number),
          confirmedAt: row.confirmed_at,
          status: row.status,
        })),
        explorerBaseUrl: cfg?.explorerBaseUrl ?? null,
      });
    }

    return successResponse({ ok: true, agentId, chains }, 200, requestId);
  } catch {
    return internalErrorResponse(requestId);
  }
}
