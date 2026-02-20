import { getChainConfig } from '@/lib/chains';
import { UniswapProxyError } from '@/lib/uniswap-proxy';
import { getEnv } from '@/lib/env';

export { UniswapProxyError } from '@/lib/uniswap-proxy';

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

type UniswapLpTx = {
  to: string;
  data: string;
  value: string;
};

type UniswapLpResult = {
  operation: 'approve' | 'create' | 'increase' | 'decrease' | 'claim';
  transactions: UniswapLpTx[];
  raw: Record<string, unknown>;
};

type UniswapLpInput = {
  chainKey: string;
  walletAddress: string;
  request: Record<string, unknown>;
};

function normalizeAddress(value: string): string {
  const normalized = String(value || '').trim();
  if (!/^0x[a-fA-F0-9]{40}$/.test(normalized)) {
    throw new UniswapProxyError('payload_invalid', `Invalid EVM address: ${value}`);
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
      `Chain '${chainKey}' (chainId=${chainId}) is not supported by configured Uniswap LP proxy scope.`,
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

function normalizeTx(tx: unknown, label: string): UniswapLpTx | null {
  if (!tx || typeof tx !== 'object') {
    return null;
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

async function uniswapRequest(path: string, payload: Record<string, unknown>): Promise<Record<string, unknown>> {
  const apiKey = ensureUniswapConfigured();
  let response: Response;
  try {
    response = await fetch(`${UNISWAP_BASE_URL}${path}`, {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        'x-api-key': apiKey,
      },
      body: JSON.stringify(payload),
      cache: 'no-store',
    });
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
      String(payloadObj.detail ?? payloadObj.message ?? `Uniswap upstream failed (${response.status}).`),
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

function collectTransactions(
  raw: Record<string, unknown>,
  keys: string[],
  operation: UniswapLpResult['operation'],
  allowEmpty: boolean
): UniswapLpResult {
  const transactions: UniswapLpTx[] = [];
  for (const key of keys) {
    const tx = normalizeTx(raw[key], key);
    if (tx) {
      transactions.push(tx);
    }
  }
  if (!allowEmpty && transactions.length === 0) {
    throw new UniswapProxyError('uniswap_payload_invalid', `Uniswap LP ${operation} response has no executable transactions.`, 502);
  }
  return {
    operation,
    transactions,
    raw,
  };
}

function withWalletAndChain(input: UniswapLpInput): Record<string, unknown> {
  const chainId = resolveChainId(input.chainKey);
  const walletAddress = normalizeAddress(input.walletAddress);
  return {
    ...input.request,
    chainId,
    walletAddress,
  };
}

export function isUniswapLpEligibleChain(chainKey: string): boolean {
  const cfg = getChainConfig(chainKey);
  if (!cfg || cfg.enabled === false) {
    return false;
  }
  const chainId = Number(cfg.chainId ?? 0);
  if (!Number.isInteger(chainId) || chainId <= 0 || !SUPPORTED_CHAIN_IDS.has(chainId)) {
    return false;
  }
  const swapEnabled = cfg.uniswapApi?.enabled !== false;
  const lpEnabled = cfg.uniswapApi?.liquidityEnabled === true;
  return swapEnabled && lpEnabled;
}

export async function approveLpUniswap(input: UniswapLpInput): Promise<UniswapLpResult> {
  const raw = await uniswapRequest('/lp/approve', withWalletAndChain(input));
  return collectTransactions(
    raw,
    [
      'token0Cancel',
      'token1Cancel',
      'token0Approval',
      'token1Approval',
      'positionTokenApproval',
      'token0PermitTransaction',
      'token1PermitTransaction',
      'positionTokenPermitTransaction',
    ],
    'approve',
    true
  );
}

export async function createLpUniswap(input: UniswapLpInput): Promise<UniswapLpResult> {
  const raw = await uniswapRequest('/lp/create', withWalletAndChain(input));
  return collectTransactions(raw, ['createPool', 'create'], 'create', false);
}

export async function increaseLpUniswap(input: UniswapLpInput): Promise<UniswapLpResult> {
  const raw = await uniswapRequest('/lp/increase', withWalletAndChain(input));
  return collectTransactions(raw, ['increase'], 'increase', false);
}

export async function decreaseLpUniswap(input: UniswapLpInput): Promise<UniswapLpResult> {
  const raw = await uniswapRequest('/lp/decrease', withWalletAndChain(input));
  return collectTransactions(raw, ['decrease'], 'decrease', false);
}

export async function claimLpFeesUniswap(input: UniswapLpInput): Promise<UniswapLpResult> {
  const raw = await uniswapRequest('/lp/claim', withWalletAndChain(input));
  return collectTransactions(raw, ['claim'], 'claim', false);
}
