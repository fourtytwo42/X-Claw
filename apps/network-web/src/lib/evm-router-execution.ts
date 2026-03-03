import { Interface, isAddress } from 'ethers';

import { chainCapabilityEnabled, chainRpcUrl, getChainConfig } from '@/lib/chains';

export class EvmRouterExecutionError extends Error {
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

export type TradeQuoteInput = {
  chainKey: string;
  walletAddress: string;
  tokenIn: string;
  tokenOut: string;
  amountInUnits: string;
  slippageBps: number;
  adapterKey?: string | null;
};

export type TradeQuoteResult = {
  routeKind: string;
  amountOutUnits: string;
  quote: Record<string, unknown>;
};

export type TradeBuildInput = {
  chainKey: string;
  walletAddress: string;
  quote: Record<string, unknown>;
};

export type TxPayload = {
  to: string;
  data: string;
  value: string;
};

export type TradeBuildResult = {
  routeKind: string;
  amountOutUnits: string | null;
  approvalTx: TxPayload;
  swapTx: TxPayload;
};

const V2_IFACE = new Interface([
  'function getAmountsOut(uint256 amountIn, address[] memory path) view returns (uint256[] memory amounts)',
  'function swapExactTokensForTokens(uint256 amountIn,uint256 amountOutMin,address[] calldata path,address to,uint256 deadline) returns (uint256[] memory amounts)',
  'function approve(address spender,uint256 value) returns (bool)',
]);

function normalizeAddress(value: string, field: string): string {
  const normalized = String(value || '').trim();
  if (!isAddress(normalized)) {
    throw new EvmRouterExecutionError('payload_invalid', `${field} must be a valid EVM address.`, 400, { field, value });
  }
  return normalized;
}

function normalizeUint(value: string, field: string): string {
  const normalized = String(value || '').trim();
  if (!/^[0-9]+$/.test(normalized)) {
    throw new EvmRouterExecutionError('payload_invalid', `${field} must be an unsigned integer string.`, 400, { field, value });
  }
  return normalized;
}

function resolveTradeAdapter(chainKey: string, requestedAdapterKey?: string | null): {
  adapterKey: string;
  family: string;
  router: string;
} {
  const cfg = getChainConfig(chainKey);
  if (!cfg || cfg.enabled === false || (cfg.family ?? 'evm') !== 'evm') {
    throw new EvmRouterExecutionError('unsupported_chain', `Chain '${chainKey}' is not enabled for EVM execution.`, 400, {
      chainKey,
    });
  }
  if (!chainCapabilityEnabled(chainKey, 'trade')) {
    throw new EvmRouterExecutionError('unsupported_chain', `Chain '${chainKey}' does not support trade execution.`, 400, {
      chainKey,
    });
  }

  const adapters = cfg.execution?.trade?.adapters ?? {};
  const requested = String(requestedAdapterKey ?? '').trim().toLowerCase();
  const resolvedKey = requested || 'default';
  const adapter = adapters[resolvedKey] ?? adapters.default;
  const router = String(adapter?.router ?? cfg.coreContracts?.dexRouter ?? cfg.coreContracts?.router ?? '').trim();
  const family = String(adapter?.family ?? 'amm_v2').trim().toLowerCase() || 'amm_v2';
  const adapterKey = String(adapter?.adapterKey ?? resolvedKey).trim().toLowerCase() || resolvedKey;

  if (!router || !isAddress(router)) {
    throw new EvmRouterExecutionError(
      'unsupported_chain',
      `Chain '${chainKey}' does not define a usable router adapter.`,
      400,
      { chainKey, adapterKey }
    );
  }
  if (family !== 'amm_v2') {
    throw new EvmRouterExecutionError(
      'unsupported_chain',
      `Chain '${chainKey}' adapter '${adapterKey}' is not yet supported for generic server-side quoting/building.`,
      400,
      { chainKey, adapterKey, family }
    );
  }

  return { adapterKey, family, router };
}

async function rpcCall(chainKey: string, method: string, params: unknown[]): Promise<unknown> {
  const rpcUrl = chainRpcUrl(chainKey);
  if (!rpcUrl) {
    throw new EvmRouterExecutionError('rpc_unavailable', `Chain '${chainKey}' is missing RPC configuration.`, 503, { chainKey });
  }
  const res = await fetch(rpcUrl, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ jsonrpc: '2.0', id: 1, method, params }),
    cache: 'no-store',
  });
  if (!res.ok) {
    throw new EvmRouterExecutionError('rpc_unavailable', `RPC ${method} failed with HTTP ${res.status}.`, 502, {
      chainKey,
      method,
      status: res.status,
    });
  }
  const parsed = (await res.json()) as { result?: unknown; error?: { message?: string } };
  if (parsed.error) {
    throw new EvmRouterExecutionError('rpc_unavailable', parsed.error.message ?? `RPC ${method} returned an error.`, 502, {
      chainKey,
      method,
    });
  }
  return parsed.result;
}

export async function quoteTradeViaRouter(input: TradeQuoteInput): Promise<TradeQuoteResult> {
  const walletAddress = normalizeAddress(input.walletAddress, 'walletAddress');
  const tokenIn = normalizeAddress(input.tokenIn, 'tokenIn');
  const tokenOut = normalizeAddress(input.tokenOut, 'tokenOut');
  const amountInUnits = normalizeUint(input.amountInUnits, 'amountInUnits');
  const slippageBps = Number(input.slippageBps);
  if (!Number.isInteger(slippageBps) || slippageBps < 0 || slippageBps > 5000) {
    throw new EvmRouterExecutionError('payload_invalid', 'slippageBps must be an integer between 0 and 5000.', 400, {
      slippageBps: input.slippageBps,
    });
  }

  const adapter = resolveTradeAdapter(input.chainKey, input.adapterKey);
  const data = V2_IFACE.encodeFunctionData('getAmountsOut', [amountInUnits, [tokenIn, tokenOut]]);
  const raw = (await rpcCall(input.chainKey, 'eth_call', [{ to: adapter.router, data }, 'latest'])) as string;
  let decoded: bigint[];
  try {
    const [amounts] = V2_IFACE.decodeFunctionResult('getAmountsOut', raw);
    decoded = Array.from(amounts) as bigint[];
  } catch (error) {
    throw new EvmRouterExecutionError('rpc_unavailable', 'Router quote decoding failed.', 502, {
      chainKey: input.chainKey,
      adapterKey: adapter.adapterKey,
      cause: String(error),
    });
  }
  const amountOutUnits = String(decoded[decoded.length - 1] ?? BigInt(0));
  if (!/^[0-9]+$/.test(amountOutUnits) || amountOutUnits === '0') {
    throw new EvmRouterExecutionError('rpc_unavailable', 'Router quote returned no executable output amount.', 502, {
      chainKey: input.chainKey,
      adapterKey: adapter.adapterKey,
    });
  }

  return {
    routeKind: 'DIRECT_V2',
    amountOutUnits,
    quote: {
      chainKey: input.chainKey,
      walletAddress,
      tokenIn,
      tokenOut,
      amountInUnits,
      amountOutUnits,
      slippageBps,
      routeKind: 'DIRECT_V2',
      executionFamily: adapter.family,
      executionAdapter: adapter.adapterKey,
      router: adapter.router,
    },
  };
}

export async function buildTradeViaRouter(input: TradeBuildInput): Promise<TradeBuildResult> {
  const walletAddress = normalizeAddress(input.walletAddress, 'walletAddress');
  const quote = input.quote ?? {};
  const chainKey = String(input.chainKey || '').trim();
  const tokenIn = normalizeAddress(String(quote.tokenIn ?? ''), 'quote.tokenIn');
  const tokenOut = normalizeAddress(String(quote.tokenOut ?? ''), 'quote.tokenOut');
  const amountInUnits = normalizeUint(String(quote.amountInUnits ?? ''), 'quote.amountInUnits');
  const amountOutUnits = normalizeUint(String(quote.amountOutUnits ?? ''), 'quote.amountOutUnits');
  const slippageBps = Number(quote.slippageBps ?? 0);
  if (!Number.isInteger(slippageBps) || slippageBps < 0 || slippageBps > 5000) {
    throw new EvmRouterExecutionError('payload_invalid', 'quote.slippageBps must be an integer between 0 and 5000.', 400);
  }

  const adapter = resolveTradeAdapter(chainKey, String(quote.executionAdapter ?? '').trim() || null);
  const amountOut = BigInt(amountOutUnits);
  const amountOutMin = (amountOut * BigInt(10000 - slippageBps)) / BigInt(10000);
  const deadline = BigInt(Math.floor(Date.now() / 1000) + 120);

  return {
    routeKind: String(quote.routeKind ?? 'DIRECT_V2').trim().toUpperCase() || 'DIRECT_V2',
    amountOutUnits,
    approvalTx: {
      to: tokenIn,
      data: V2_IFACE.encodeFunctionData('approve', [adapter.router, amountInUnits]),
      value: '0',
    },
    swapTx: {
      to: adapter.router,
      data: V2_IFACE.encodeFunctionData('swapExactTokensForTokens', [
        amountInUnits,
        amountOutMin.toString(),
        [tokenIn, tokenOut],
        walletAddress,
        deadline.toString(),
      ]),
      value: '0',
    },
  };
}
