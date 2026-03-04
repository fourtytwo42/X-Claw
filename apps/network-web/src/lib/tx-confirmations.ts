import { chainFamily, chainRpcUrl } from '@/lib/chains';
import { fetchWithTimeout, upstreamFetchTimeoutMs } from '@/lib/fetch-timeout';

type EvmReceipt = { blockNumber?: string | null };
type SolanaSignatureStatus = {
  confirmations?: number | null;
  confirmationStatus?: string | null;
  err?: unknown;
};

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

async function fetchEvmConfirmations(rpcUrl: string, txIds: string[]): Promise<Map<string, number | null>> {
  const byHash = new Map<string, number | null>();
  if (txIds.length === 0) {
    return byHash;
  }
  const latestHex = (await rpcRequest(rpcUrl, 'eth_blockNumber', [])) as string;
  const latest = hexToBigInt(latestHex);
  await Promise.all(
    txIds.map(async (txId) => {
      try {
        const receipt = (await rpcRequest(rpcUrl, 'eth_getTransactionReceipt', [txId])) as EvmReceipt | null;
        if (!receipt?.blockNumber) {
          byHash.set(txId, null);
          return;
        }
        const txBlock = hexToBigInt(receipt.blockNumber);
        byHash.set(txId, latest >= txBlock ? Number(latest - txBlock + BigInt(1)) : 0);
      } catch {
        byHash.set(txId, null);
      }
    })
  );
  return byHash;
}

async function fetchSolanaConfirmations(rpcUrl: string, txIds: string[]): Promise<Map<string, number | null>> {
  const bySignature = new Map<string, number | null>();
  if (txIds.length === 0) {
    return bySignature;
  }
  const result = (await rpcRequest(rpcUrl, 'getSignatureStatuses', [txIds, { searchTransactionHistory: true }])) as {
    value?: Array<SolanaSignatureStatus | null>;
  };
  const rows = Array.isArray(result?.value) ? result.value : [];
  for (let i = 0; i < txIds.length; i += 1) {
    const txId = txIds[i];
    const row = rows[i];
    if (!row || typeof row !== 'object') {
      bySignature.set(txId, null);
      continue;
    }
    const confirmationsRaw = row.confirmations;
    if (typeof confirmationsRaw === 'number' && Number.isFinite(confirmationsRaw)) {
      bySignature.set(txId, Math.max(0, confirmationsRaw));
      continue;
    }
    if (row.err != null) {
      bySignature.set(txId, 0);
      continue;
    }
    const status = String(row.confirmationStatus || '').toLowerCase();
    if (status === 'confirmed' || status === 'finalized' || confirmationsRaw === null) {
      bySignature.set(txId, 1);
      continue;
    }
    bySignature.set(txId, null);
  }
  return bySignature;
}

export async function fetchChainTransactionConfirmations(
  chainKey: string,
  txIdsRaw: Array<string | null | undefined>
): Promise<Map<string, number | null>> {
  const txIds = Array.from(
    new Set(
      txIdsRaw
        .map((value) => String(value || '').trim())
        .filter((value) => value.length > 0)
    )
  );
  const byId = new Map<string, number | null>();
  if (txIds.length === 0) {
    return byId;
  }
  const rpcUrl = chainRpcUrl(chainKey);
  if (!rpcUrl) {
    return byId;
  }
  try {
    if (chainFamily(chainKey) === 'solana') {
      return await fetchSolanaConfirmations(rpcUrl, txIds);
    }
    return await fetchEvmConfirmations(rpcUrl, txIds);
  } catch {
    return byId;
  }
}
