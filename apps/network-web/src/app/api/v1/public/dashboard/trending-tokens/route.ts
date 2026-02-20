import type { NextRequest } from 'next/server';

import { listEnabledChains } from '@/lib/chains';
import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import { enforcePublicReadRateLimit } from '@/lib/rate-limit';
import { getRequestId } from '@/lib/request-id';

export const runtime = 'nodejs';

const CACHE_TTL_MS = 60_000;
const FETCH_TIMEOUT_MS = 8_000;
const DEFAULT_LIMIT = 10;
const MAX_LIMIT = 10;
const ADDRESS_RE = /^0x[a-fA-F0-9]{40}$/;

type DexTxn = {
  buys: number;
  sells: number;
  total: number;
};

type NormalizedRow = {
  chainId: string;
  dexId: string;
  pairAddress: string;
  pairUrl: string;
  tokenAddress: string;
  tokenSymbol: string;
  tokenName: string;
  quoteSymbol: string;
  pairLabel: string | null;
  priceUsd: string | null;
  ageMinutes: number | null;
  txnsM5: DexTxn | null;
  txnsH1: DexTxn | null;
  txnsH6: DexTxn | null;
  txnsH24: DexTxn | null;
  volumeM5Usd: string | null;
  volumeH1Usd: string | null;
  volumeH6Usd: string | null;
  volumeH24Usd: string;
  priceChangeM5Pct: string | null;
  priceChangeH1Pct: string | null;
  priceChangeH6Pct: string | null;
  priceChangeH24Pct: string | null;
  scoreVolumeH24: number;
};

type CacheEntry = {
  expiresAt: number;
  rows: NormalizedRow[];
  warning?: string;
};

const tokenPairCache = new Map<string, CacheEntry>();

function parseLimit(raw: string | null): number {
  if (!raw) {
    return DEFAULT_LIMIT;
  }
  const parsed = Number(raw);
  if (!Number.isFinite(parsed) || parsed < 1) {
    return DEFAULT_LIMIT;
  }
  return Math.min(Math.floor(parsed), MAX_LIMIT);
}

function toStringNumber(value: unknown, digits = 2): string | null {
  const num = Number(value);
  if (!Number.isFinite(num)) {
    return null;
  }
  return num.toFixed(digits);
}

function toScore(value: unknown): number {
  const num = Number(value);
  return Number.isFinite(num) ? num : 0;
}

function normalizeTxns(value: unknown): DexTxn | null {
  if (!value || typeof value !== 'object') {
    return null;
  }
  const source = value as { buys?: unknown; sells?: unknown };
  const buys = Number(source.buys);
  const sells = Number(source.sells);
  if (!Number.isFinite(buys) && !Number.isFinite(sells)) {
    return null;
  }
  const safeBuys = Number.isFinite(buys) ? Math.max(0, Math.floor(buys)) : 0;
  const safeSells = Number.isFinite(sells) ? Math.max(0, Math.floor(sells)) : 0;
  return {
    buys: safeBuys,
    sells: safeSells,
    total: safeBuys + safeSells,
  };
}

function normalizePair(input: unknown): NormalizedRow | null {
  if (!input || typeof input !== 'object') {
    return null;
  }

  const row = input as {
    chainId?: unknown;
    dexId?: unknown;
    pairAddress?: unknown;
    url?: unknown;
    labels?: unknown;
    baseToken?: { address?: unknown; symbol?: unknown; name?: unknown };
    quoteToken?: { symbol?: unknown };
    priceUsd?: unknown;
    txns?: { m5?: unknown; h1?: unknown; h6?: unknown; h24?: unknown };
    volume?: { m5?: unknown; h1?: unknown; h6?: unknown; h24?: unknown };
    priceChange?: { m5?: unknown; h1?: unknown; h6?: unknown; h24?: unknown };
    pairCreatedAt?: unknown;
  };

  const chainId = String(row.chainId ?? '').trim().toLowerCase();
  const dexId = String(row.dexId ?? '').trim();
  const pairAddress = String(row.pairAddress ?? '').trim();
  const pairUrl = String(row.url ?? '').trim();
  const tokenAddress = String(row.baseToken?.address ?? '').trim();
  const tokenSymbol = String(row.baseToken?.symbol ?? '').trim();
  const tokenName = String(row.baseToken?.name ?? tokenSymbol).trim();
  const quoteSymbol = String(row.quoteToken?.symbol ?? '').trim();

  if (!chainId || !dexId || !pairAddress || !pairUrl || !tokenAddress || !tokenSymbol || !quoteSymbol) {
    return null;
  }

  const labels = Array.isArray(row.labels) ? row.labels.filter((label) => typeof label === 'string' && label.trim()) : [];
  const pairLabel = labels.length > 0 ? labels.join(', ') : null;

  const scoreVolumeH24 = toScore(row.volume?.h24);
  const priceUsd = toStringNumber(row.priceUsd, 8);
  const volumeM5Usd = toStringNumber(row.volume?.m5, 2);
  const volumeH1Usd = toStringNumber(row.volume?.h1, 2);
  const volumeH6Usd = toStringNumber(row.volume?.h6, 2);
  const volumeH24Usd = toStringNumber(row.volume?.h24, 2) ?? '0.00';
  const priceChangeM5Pct = toStringNumber(row.priceChange?.m5, 2);
  const priceChangeH1Pct = toStringNumber(row.priceChange?.h1, 2);
  const priceChangeH6Pct = toStringNumber(row.priceChange?.h6, 2);
  const priceChangeH24Pct = toStringNumber(row.priceChange?.h24, 2);

  const createdAtMs = Number(row.pairCreatedAt);
  const ageMinutes = Number.isFinite(createdAtMs) && createdAtMs > 0 ? Math.max(0, Math.floor((Date.now() - createdAtMs) / 60_000)) : null;

  return {
    chainId,
    dexId,
    pairAddress,
    pairUrl,
    tokenAddress,
    tokenSymbol,
    tokenName,
    quoteSymbol,
    pairLabel,
    priceUsd,
    ageMinutes,
    txnsM5: normalizeTxns(row.txns?.m5),
    txnsH1: normalizeTxns(row.txns?.h1),
    txnsH6: normalizeTxns(row.txns?.h6),
    txnsH24: normalizeTxns(row.txns?.h24),
    volumeM5Usd,
    volumeH1Usd,
    volumeH6Usd,
    volumeH24Usd,
    priceChangeM5Pct,
    priceChangeH1Pct,
    priceChangeH6Pct,
    priceChangeH24Pct,
    scoreVolumeH24,
  };
}

async function fetchDexTokenPairs(dexChainId: string, tokenAddress: string): Promise<{ rows: NormalizedRow[]; warning?: string }> {
  const key = `${dexChainId}:${tokenAddress.toLowerCase()}`;
  const cached = tokenPairCache.get(key);
  if (cached && cached.expiresAt > Date.now()) {
    return { rows: cached.rows, warning: cached.warning };
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);

  try {
    const response = await fetch(
      `https://api.dexscreener.com/token-pairs/v1/${encodeURIComponent(dexChainId)}/${encodeURIComponent(tokenAddress)}`,
      {
        method: 'GET',
        headers: {
          accept: 'application/json',
          'user-agent': 'xclaw-network-web/1.0',
        },
        cache: 'no-store',
        signal: controller.signal,
      }
    );

    if (!response.ok) {
      const warning = `Dexscreener ${dexChainId}:${tokenAddress} failed with HTTP ${response.status}.`;
      tokenPairCache.set(key, { expiresAt: Date.now() + CACHE_TTL_MS, rows: [], warning });
      return { rows: [], warning };
    }

    const payload = (await response.json()) as unknown;
    const pairs = Array.isArray(payload)
      ? payload
      : payload && typeof payload === 'object' && Array.isArray((payload as { pairs?: unknown[] }).pairs)
        ? ((payload as { pairs: unknown[] }).pairs ?? [])
        : [];

    const rows = pairs
      .map((pair) => normalizePair(pair))
      .filter((row): row is NormalizedRow => row !== null && row.chainId === dexChainId);

    tokenPairCache.set(key, { expiresAt: Date.now() + CACHE_TTL_MS, rows });
    return { rows };
  } catch {
    const warning = `Dexscreener ${dexChainId}:${tokenAddress} fetch failed.`;
    tokenPairCache.set(key, { expiresAt: Date.now() + CACHE_TTL_MS, rows: [], warning });
    return { rows: [], warning };
  } finally {
    clearTimeout(timeout);
  }
}

function collectCanonicalTokenAddresses(chains: Array<{ canonicalTokens?: Record<string, string> }>): string[] {
  const out = new Set<string>();
  for (const cfg of chains) {
    const tokens = cfg.canonicalTokens ?? {};
    for (const value of Object.values(tokens)) {
      const normalized = String(value ?? '').trim();
      if (ADDRESS_RE.test(normalized)) {
        out.add(normalized);
      }
    }
  }
  return Array.from(out);
}

export async function GET(req: NextRequest) {
  const requestId = getRequestId(req);

  try {
    const rateLimited = await enforcePublicReadRateLimit(req, requestId);
    if (!rateLimited.ok) {
      return rateLimited.response;
    }

    const chainKey = (req.nextUrl.searchParams.get('chainKey') ?? 'all').trim() || 'all';
    const limit = parseLimit(req.nextUrl.searchParams.get('limit'));

    const visibleChains = listEnabledChains().filter((cfg) => cfg.uiVisible !== false);
    const validChainKeys = new Set(visibleChains.map((cfg) => cfg.chainKey));

    if (chainKey !== 'all' && !validChainKeys.has(chainKey)) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'chainKey query parameter is invalid.',
          actionHint: `Use all or one of: ${Array.from(validChainKeys).join(', ')}.`,
        },
        requestId
      );
    }

    const mappedChainIds = chainKey === 'all'
      ? Array.from(
          new Set(
            visibleChains
              .map((cfg) => String(cfg.marketData?.dexscreenerChainId ?? '').trim().toLowerCase())
              .filter((value) => value.length > 0)
          )
        )
      : (() => {
          const selected = visibleChains.find((cfg) => cfg.chainKey === chainKey);
          const mapped = String(selected?.marketData?.dexscreenerChainId ?? '').trim().toLowerCase();
          return mapped ? [mapped] : [];
        })();

    if (mappedChainIds.length === 0) {
      return successResponse({ ok: true, chainKey, generatedAt: new Date().toISOString(), items: [] }, 200, requestId);
    }

    const workItems = mappedChainIds.flatMap((dexChainId) => {
      const relatedChains = visibleChains.filter(
        (cfg) => String(cfg.marketData?.dexscreenerChainId ?? '').trim().toLowerCase() === dexChainId
      );
      const tokenAddresses = collectCanonicalTokenAddresses(relatedChains);
      return tokenAddresses.map((tokenAddress) => ({ dexChainId, tokenAddress }));
    });

    if (workItems.length === 0) {
      return successResponse({ ok: true, chainKey, generatedAt: new Date().toISOString(), items: [] }, 200, requestId);
    }

    const pairResults = await Promise.all(workItems.map((item) => fetchDexTokenPairs(item.dexChainId, item.tokenAddress)));

    const warnings = pairResults.map((result) => result.warning).filter((value): value is string => Boolean(value));

    const deduped = new Map<string, NormalizedRow>();
    for (const result of pairResults) {
      for (const row of result.rows) {
        const key = `${row.chainId}:${row.tokenAddress.toLowerCase()}`;
        const current = deduped.get(key);
        if (!current || row.scoreVolumeH24 > current.scoreVolumeH24) {
          deduped.set(key, row);
        }
      }
    }

    const ranked = Array.from(deduped.values())
      .sort((a, b) => b.scoreVolumeH24 - a.scoreVolumeH24)
      .slice(0, limit)
      .map((row, index) => ({
        rank: index + 1,
        chainId: row.chainId,
        dexId: row.dexId,
        pairAddress: row.pairAddress,
        pairUrl: row.pairUrl,
        tokenAddress: row.tokenAddress,
        tokenSymbol: row.tokenSymbol,
        tokenName: row.tokenName,
        quoteSymbol: row.quoteSymbol,
        pairLabel: row.pairLabel,
        priceUsd: row.priceUsd,
        ageMinutes: row.ageMinutes,
        txnsM5: row.txnsM5,
        txnsH1: row.txnsH1,
        txnsH6: row.txnsH6,
        txnsH24: row.txnsH24,
        volumeM5Usd: row.volumeM5Usd,
        volumeH1Usd: row.volumeH1Usd,
        volumeH6Usd: row.volumeH6Usd,
        volumeH24Usd: row.volumeH24Usd,
        priceChangeM5Pct: row.priceChangeM5Pct,
        priceChangeH1Pct: row.priceChangeH1Pct,
        priceChangeH6Pct: row.priceChangeH6Pct,
        priceChangeH24Pct: row.priceChangeH24Pct,
      }));

    return successResponse(
      {
        ok: true,
        chainKey,
        generatedAt: new Date().toISOString(),
        warnings: warnings.length > 0 ? warnings : undefined,
        items: ranked,
      },
      200,
      requestId
    );
  } catch {
    return internalErrorResponse(requestId);
  }
}
