import { chainRpcUrl } from '@/lib/chains';
import { dbQuery } from '@/lib/db';

type ResolveSource = 'config' | 'rpc' | 'cache' | 'fallback';
type ResolveStatus = 'ok' | 'rpc_error' | 'non_erc20' | 'invalid';

export type TokenMetadata = {
  symbol: string | null;
  name: string | null;
  decimals: number | null;
  source: ResolveSource;
  address: string;
  isFallbackLabel: boolean;
};

function isHexAddress(value: string): boolean {
  return /^0x[a-fA-F0-9]{40}$/.test(value);
}

function fallbackSymbol(address: string): string {
  const normalized = address.toLowerCase();
  return `${normalized.slice(0, 6)}...${normalized.slice(-4)}`;
}

async function rpcCall(rpcUrl: string, to: string, data: string): Promise<string | null> {
  const res = await fetch(rpcUrl, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({
      jsonrpc: '2.0',
      id: 1,
      method: 'eth_call',
      params: [{ to, data }, 'latest'],
    }),
  });
  if (!res.ok) {
    return null;
  }
  const body = (await res.json()) as { result?: string; error?: { message?: string } };
  if (body.error || typeof body.result !== 'string') {
    return null;
  }
  return body.result;
}

function decodeUint256Hex(result: string): number | null {
  if (!result || !result.startsWith('0x')) {
    return null;
  }
  try {
    const asNum = Number(BigInt(result));
    return Number.isFinite(asNum) ? asNum : null;
  } catch {
    return null;
  }
}

function decodeStringHex(result: string): string | null {
  if (!result || !result.startsWith('0x')) {
    return null;
  }
  const hex = result.slice(2);
  if (hex.length < 128) {
    return null;
  }
  try {
    const offset = Number.parseInt(hex.slice(0, 64), 16);
    const lenPos = offset * 2;
    if (lenPos + 64 > hex.length) {
      return null;
    }
    const length = Number.parseInt(hex.slice(lenPos, lenPos + 64), 16);
    const dataPos = lenPos + 64;
    const dataHex = hex.slice(dataPos, dataPos + length * 2);
    if (!dataHex) {
      return null;
    }
    const decoded = Buffer.from(dataHex, 'hex').toString('utf8').replace(/\u0000/g, '').trim();
    return decoded || null;
  } catch {
    return null;
  }
}

async function upsertCache(
  chainKey: string,
  address: string,
  status: ResolveStatus,
  symbol: string | null,
  name: string | null,
  decimals: number | null,
  errorMessage: string | null
): Promise<void> {
  await dbQuery(
    `
    insert into chain_token_metadata_cache (
      chain_key, token_address, symbol, name, decimals, last_resolved_at, resolve_status, resolve_error, created_at, updated_at
    ) values ($1, $2, $3, $4, $5, now(), $6, $7, now(), now())
    on conflict (chain_key, token_address)
    do update set
      symbol = excluded.symbol,
      name = excluded.name,
      decimals = excluded.decimals,
      last_resolved_at = excluded.last_resolved_at,
      resolve_status = excluded.resolve_status,
      resolve_error = excluded.resolve_error,
      updated_at = now()
    `,
    [chainKey, address, symbol, name, decimals, status, errorMessage]
  );
}

export async function resolveTokenMetadata(chainKey: string, tokenAddress: string): Promise<TokenMetadata> {
  const normalized = String(tokenAddress || '').trim().toLowerCase();
  if (!isHexAddress(normalized)) {
    return {
      symbol: fallbackSymbol(normalized || '0x0000000000000000000000000000000000000000'),
      name: null,
      decimals: 18,
      source: 'fallback',
      address: normalized,
      isFallbackLabel: true,
    };
  }

  const cached = await dbQuery<{
    symbol: string | null;
    name: string | null;
    decimals: number | null;
    resolve_status: ResolveStatus;
  }>(
    `
    select symbol, name, decimals, resolve_status
    from chain_token_metadata_cache
    where chain_key = $1 and token_address = $2
    `,
    [chainKey, normalized]
  ).catch(() => null);

  if (cached && (cached.rowCount ?? 0) > 0) {
    const row = cached.rows[0];
    return {
      symbol: row.symbol ?? fallbackSymbol(normalized),
      name: row.name,
      decimals: typeof row.decimals === 'number' ? row.decimals : 18,
      source: 'cache',
      address: normalized,
      isFallbackLabel: !row.symbol,
    };
  }

  const rpcUrl = chainRpcUrl(chainKey);
  if (!rpcUrl) {
    return {
      symbol: fallbackSymbol(normalized),
      name: null,
      decimals: 18,
      source: 'fallback',
      address: normalized,
      isFallbackLabel: true,
    };
  }

  try {
    const [symbolHex, nameHex, decimalsHex] = await Promise.all([
      rpcCall(rpcUrl, normalized, '0x95d89b41'),
      rpcCall(rpcUrl, normalized, '0x06fdde03'),
      rpcCall(rpcUrl, normalized, '0x313ce567'),
    ]);

    const symbol = symbolHex ? decodeStringHex(symbolHex) : null;
    const name = nameHex ? decodeStringHex(nameHex) : null;
    const decimals = decimalsHex ? decodeUint256Hex(decimalsHex) : null;
    const resolvedSymbol = symbol || fallbackSymbol(normalized);
    const resolvedDecimals = typeof decimals === 'number' && decimals >= 0 ? decimals : 18;

    await upsertCache(chainKey, normalized, symbol || decimals !== null ? 'ok' : 'non_erc20', symbol, name, resolvedDecimals, null).catch(
      () => undefined
    );

    return {
      symbol: resolvedSymbol,
      name,
      decimals: resolvedDecimals,
      source: 'rpc',
      address: normalized,
      isFallbackLabel: !symbol,
    };
  } catch (error) {
    await upsertCache(
      chainKey,
      normalized,
      'rpc_error',
      null,
      null,
      18,
      error instanceof Error ? error.message.slice(0, 240) : 'rpc_error'
    ).catch(() => undefined);
    return {
      symbol: fallbackSymbol(normalized),
      name: null,
      decimals: 18,
      source: 'fallback',
      address: normalized,
      isFallbackLabel: true,
    };
  }
}
