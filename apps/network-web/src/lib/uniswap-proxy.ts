import { getEnv } from '@/lib/env';
import { fetchWithTimeout, upstreamFetchTimeoutMs } from '@/lib/fetch-timeout';
import { getChainConfig } from '@/lib/chains';

const UNISWAP_BASE_URL = 'https://trade-api.gateway.uniswap.org/v1';

const SUPPORTED_CHAIN_IDS = new Set<number>([
  1,
  10,
  56,
  130,
  137,
  143,
  324,
  8453,
  42161,
  43114,
  11155111,
]);

export class UniswapProxyError extends Error {
  code: string;
  status: number;
  details?: Record<string, unknown>;

  constructor(code: string, message: string, status = 400, details?: Record<string, unknown>) {
    super(message);
    this.code = code;
    this.status = status;
    this.details = details;
  }
}

export type UniswapQuoteInput = {
  chainKey: string;
  walletAddress: string;
  tokenIn: string;
  tokenOut: string;
  amountInUnits: string;
  slippageBps: number;
};

export type UniswapQuoteResult = {
  routeType: string;
  amountOutUnits: string;
  rawQuote: Record<string, unknown>;
};

export type UniswapBuildInput = {
  chainKey: string;
  walletAddress: string;
  quote: Record<string, unknown>;
};

export type UniswapTxPayload = {
  to: string;
  data: string;
  value?: string;
};

export type UniswapBuildResult = {
  routeType: string;
  amountOutUnits: string | null;
  approvalTx: UniswapTxPayload | null;
  swapTx: UniswapTxPayload;
  rawBuild: Record<string, unknown>;
};

function normalizeAddress(value: string): string {
  const normalized = value.trim();
  if (!/^0x[a-fA-F0-9]{40}$/.test(normalized)) {
    throw new UniswapProxyError('payload_invalid', `Invalid EVM address: ${value}`);
  }
  return normalized;
}

function normalizeUint(value: string, field: string): string {
  const normalized = value.trim();
  if (!/^[0-9]+$/.test(normalized)) {
    throw new UniswapProxyError('payload_invalid', `${field} must be an unsigned integer string.`);
  }
  return normalized;
}

function resolveChainId(chainKey: string): number {
  const cfg = getChainConfig(chainKey);
  const chainId = Number(cfg?.chainId ?? 0);
  if (!Number.isInteger(chainId) || chainId <= 0) {
    throw new UniswapProxyError(
      'unsupported_chain',
      `Chain '${chainKey}' is missing a valid chainId in config.`,
      400,
      { chainKey }
    );
  }
  if (!SUPPORTED_CHAIN_IDS.has(chainId)) {
    throw new UniswapProxyError(
      'unsupported_chain',
      `Chain '${chainKey}' (chainId=${chainId}) is not supported by configured Uniswap proxy scope.`,
      400,
      { chainKey, chainId }
    );
  }
  return chainId;
}

function ensureUniswapConfigured(): string {
  const key = (getEnv().uniswapApiKey ?? '').trim();
  if (!key) {
    throw new UniswapProxyError(
      'uniswap_proxy_not_configured',
      'XCLAW_UNISWAP_API_KEY is not configured on server runtime.',
      503,
      { env: 'XCLAW_UNISWAP_API_KEY' }
    );
  }
  return key;
}

async function uniswapRequest(path: string, payload: Record<string, unknown>): Promise<Record<string, unknown>> {
  const apiKey = ensureUniswapConfigured();
  let response: Response;
  try {
    response = await fetchWithTimeout(
      `${UNISWAP_BASE_URL}${path}`,
      {
        method: 'POST',
        headers: {
          'content-type': 'application/json',
          'x-api-key': apiKey,
        },
        body: JSON.stringify(payload),
        cache: 'no-store',
      },
      upstreamFetchTimeoutMs(),
    );
  } catch (error) {
    throw new UniswapProxyError('uniswap_upstream_unavailable', 'Uniswap upstream request failed.', 502, {
      cause: String(error ?? 'unknown_error'),
    });
  }

  let body: unknown = null;
  try {
    body = await response.json();
  } catch {
    body = null;
  }

  if (!response.ok) {
    const payloadObj = (body && typeof body === 'object') ? (body as Record<string, unknown>) : {};
    throw new UniswapProxyError(
      'uniswap_upstream_error',
      String(payloadObj.message ?? `Uniswap upstream failed (${response.status}).`),
      response.status,
      {
        path,
        upstreamStatus: response.status,
        upstreamCode: payloadObj.errorCode ?? payloadObj.code ?? null,
      }
    );
  }

  if (!body || typeof body !== 'object') {
    throw new UniswapProxyError('uniswap_payload_invalid', 'Uniswap upstream returned non-object payload.', 502, { path });
  }
  return body as Record<string, unknown>;
}

function resolveRouteType(obj: Record<string, unknown>): string {
  const quote = (obj.quote && typeof obj.quote === 'object') ? (obj.quote as Record<string, unknown>) : obj;
  const routeType = String(quote.routing ?? quote.routeType ?? '').trim().toUpperCase();
  return routeType || 'UNKNOWN';
}

function resolveAmountOutUnits(obj: Record<string, unknown>): string | null {
  const quote = (obj.quote && typeof obj.quote === 'object') ? (obj.quote as Record<string, unknown>) : obj;
  const output = quote.output;
  if (output && typeof output === 'object') {
    const amount = String((output as Record<string, unknown>).amount ?? '').trim();
    if (/^[0-9]+$/.test(amount)) {
      return amount;
    }
  }
  const amountOut = String(quote.amountOut ?? quote.amountOutUnits ?? '').trim();
  if (/^[0-9]+$/.test(amountOut)) {
    return amountOut;
  }
  return null;
}

function normalizeTx(tx: unknown, label: string): UniswapTxPayload {
  if (!tx || typeof tx !== 'object') {
    throw new UniswapProxyError('uniswap_payload_invalid', `Uniswap ${label} payload missing.`, 502, { label });
  }
  const obj = tx as Record<string, unknown>;
  const to = String(obj.to ?? '').trim();
  const data = String(obj.data ?? '').trim();
  const valueRaw = String(obj.value ?? '').trim();
  if (!/^0x[a-fA-F0-9]{40}$/.test(to)) {
    throw new UniswapProxyError('uniswap_payload_invalid', `Uniswap ${label}.to is invalid.`, 502, { to });
  }
  if (!/^0x[a-fA-F0-9]+$/.test(data)) {
    throw new UniswapProxyError('uniswap_payload_invalid', `Uniswap ${label}.data is invalid.`, 502, { dataLength: data.length });
  }
  const value = valueRaw === '' ? '0' : valueRaw;
  if (!/^[0-9]+$/.test(value)) {
    throw new UniswapProxyError('uniswap_payload_invalid', `Uniswap ${label}.value is invalid.`, 502, { value: valueRaw });
  }
  return { to, data, value };
}

export function isUniswapEligibleChain(chainKey: string): boolean {
  const cfg = getChainConfig(chainKey);
  if (!cfg || cfg.enabled === false) {
    return false;
  }
  const chainId = Number(cfg.chainId ?? 0);
  if (!Number.isInteger(chainId) || chainId <= 0) {
    return false;
  }
  const enabledByConfig = cfg.uniswapApi?.enabled !== false;
  return enabledByConfig && SUPPORTED_CHAIN_IDS.has(chainId);
}

export async function quoteUniswap(input: UniswapQuoteInput): Promise<UniswapQuoteResult> {
  const chainId = resolveChainId(input.chainKey);
  const swapper = normalizeAddress(input.walletAddress);
  const tokenIn = normalizeAddress(input.tokenIn);
  const tokenOut = normalizeAddress(input.tokenOut);
  const amount = normalizeUint(input.amountInUnits, 'amountInUnits');
  const slippageTolerance = Number(input.slippageBps);
  if (!Number.isInteger(slippageTolerance) || slippageTolerance < 0 || slippageTolerance > 5000) {
    throw new UniswapProxyError('payload_invalid', 'slippageBps must be an integer between 0 and 5000.');
  }

  const payload = {
    type: 'EXACT_INPUT',
    amount,
    tokenIn,
    tokenInChainId: chainId,
    tokenOut,
    tokenOutChainId: chainId,
    swapper,
    urgency: 'normal',
    protocols: ['V2', 'V3', 'V4'],
    slippageTolerance,
  };

  const raw = await uniswapRequest('/quote', payload);
  const amountOutUnits = resolveAmountOutUnits(raw);
  if (!amountOutUnits) {
    throw new UniswapProxyError('uniswap_payload_invalid', 'Uniswap quote is missing output amount.', 502);
  }

  return {
    routeType: resolveRouteType(raw),
    amountOutUnits,
    rawQuote: raw,
  };
}

export async function buildUniswap(input: UniswapBuildInput): Promise<UniswapBuildResult> {
  const chainId = resolveChainId(input.chainKey);
  const swapper = normalizeAddress(input.walletAddress);

  const quoteObj = input.quote;
  const quote = (quoteObj.quote && typeof quoteObj.quote === 'object')
    ? (quoteObj.quote as Record<string, unknown>)
    : quoteObj;

  const raw = await uniswapRequest('/swap', {
    quote,
    swapper,
    chainId,
  });

  const swapContainer = (raw.swap && typeof raw.swap === 'object') ? (raw.swap as Record<string, unknown>) : raw;
  const approvalRaw = swapContainer.approval;
  const swapTxRaw = swapContainer.tx ?? swapContainer.transaction;

  if (!swapTxRaw) {
    throw new UniswapProxyError('uniswap_payload_invalid', 'Uniswap swap response is missing tx payload.', 502);
  }

  return {
    routeType: resolveRouteType(raw),
    amountOutUnits: resolveAmountOutUnits(raw),
    approvalTx: approvalRaw ? normalizeTx(approvalRaw, 'approval') : null,
    swapTx: normalizeTx(swapTxRaw, 'swap.tx'),
    rawBuild: raw,
  };
}
