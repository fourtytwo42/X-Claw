import { getChainConfig } from '@/lib/chains';

export class SolanaJupiterExecutionError extends Error {
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

export type SolanaTradeQuoteInput = {
  chainKey: string;
  walletAddress: string;
  tokenIn: string;
  tokenOut: string;
  amountInUnits: string;
  slippageBps: number;
};

export type SolanaTradeQuoteResult = {
  routeKind: string;
  amountOutUnits: string;
  quote: Record<string, unknown>;
};

export type SolanaTradeBuildInput = {
  chainKey: string;
  walletAddress: string;
  quote: Record<string, unknown>;
};

export type SolanaTradeBuildResult = {
  routeKind: string;
  amountOutUnits: string | null;
  approvalTx: null;
  swapTx: {
    to: string;
    data: string;
    value: string;
  };
};

function ensureSolanaChain(chainKey: string): void {
  const cfg = getChainConfig(chainKey);
  if (!cfg || cfg.enabled === false || (cfg.family ?? 'evm') !== 'solana') {
    throw new SolanaJupiterExecutionError('unsupported_chain', `Chain '${chainKey}' is not enabled for Solana execution.`, 400, { chainKey });
  }
}

function assertPublicKey(value: string, field: string): string {
  const normalized = String(value ?? '').trim();
  if (!/^[1-9A-HJ-NP-Za-km-z]{32,44}$/.test(normalized)) {
    throw new SolanaJupiterExecutionError('payload_invalid', `${field} must be a valid Solana address.`, 400, { field, value });
  }
  return normalized;
}

function assertUint(value: string, field: string): string {
  const normalized = String(value ?? '').trim();
  if (!/^[0-9]+$/.test(normalized)) {
    throw new SolanaJupiterExecutionError('payload_invalid', `${field} must be an unsigned integer string.`, 400, { field, value });
  }
  return normalized;
}

function jupiterBaseUrl(_chainKey: string): string {
  return 'https://quote-api.jup.ag/v6';
}

export async function quoteTradeViaJupiter(input: SolanaTradeQuoteInput): Promise<SolanaTradeQuoteResult> {
  ensureSolanaChain(input.chainKey);
  const walletAddress = assertPublicKey(input.walletAddress, 'walletAddress');
  const tokenIn = assertPublicKey(input.tokenIn, 'tokenIn');
  const tokenOut = assertPublicKey(input.tokenOut, 'tokenOut');
  const amountInUnits = assertUint(input.amountInUnits, 'amountInUnits');
  const slippageBps = Number(input.slippageBps);
  if (!Number.isInteger(slippageBps) || slippageBps < 0 || slippageBps > 5000) {
    throw new SolanaJupiterExecutionError('payload_invalid', 'slippageBps must be an integer between 0 and 5000.', 400);
  }

  const query = new URLSearchParams({
    inputMint: tokenIn,
    outputMint: tokenOut,
    amount: amountInUnits,
    slippageBps: String(slippageBps),
    swapMode: 'ExactIn',
  });
  const response = await fetch(`${jupiterBaseUrl(input.chainKey)}/quote?${query.toString()}`, {
    method: 'GET',
    headers: { accept: 'application/json' },
    cache: 'no-store',
  });
  if (!response.ok) {
    throw new SolanaJupiterExecutionError('rpc_unavailable', `Jupiter quote failed with HTTP ${response.status}.`, 502, { status: response.status });
  }
  const payload = (await response.json()) as Record<string, unknown>;
  const amountOutUnits = String(payload.outAmount ?? '').trim();
  if (!/^[0-9]+$/.test(amountOutUnits) || amountOutUnits === '0') {
    throw new SolanaJupiterExecutionError('rpc_unavailable', 'Jupiter quote did not return executable outAmount.', 502);
  }
  const routePlan = Array.isArray(payload.routePlan) ? payload.routePlan : [];
  const routeKind = routePlan.length > 1 ? 'multi_hop' : 'jupiter_route';

  return {
    routeKind,
    amountOutUnits,
    quote: {
      chainKey: input.chainKey,
      walletAddress,
      tokenIn,
      tokenOut,
      amountInUnits,
      amountOutUnits,
      slippageBps,
      routeKind,
      executionFamily: 'solana_swap',
      executionAdapter: 'jupiter',
      quoteResponse: payload,
    },
  };
}

export async function buildTradeViaJupiter(input: SolanaTradeBuildInput): Promise<SolanaTradeBuildResult> {
  ensureSolanaChain(input.chainKey);
  const walletAddress = assertPublicKey(input.walletAddress, 'walletAddress');
  const quote = input.quote ?? {};
  const quoteResponse = quote.quoteResponse;
  if (!quoteResponse || typeof quoteResponse !== 'object') {
    throw new SolanaJupiterExecutionError('payload_invalid', 'quote.quoteResponse is required for Solana build.', 400);
  }
  const response = await fetch(`${jupiterBaseUrl(input.chainKey)}/swap`, {
    method: 'POST',
    headers: { 'content-type': 'application/json', accept: 'application/json' },
    body: JSON.stringify({
      quoteResponse,
      userPublicKey: walletAddress,
      wrapAndUnwrapSol: true,
      dynamicComputeUnitLimit: true,
      prioritizationFeeLamports: 'auto',
    }),
    cache: 'no-store',
  });
  if (!response.ok) {
    throw new SolanaJupiterExecutionError('rpc_unavailable', `Jupiter swap build failed with HTTP ${response.status}.`, 502, { status: response.status });
  }
  const payload = (await response.json()) as Record<string, unknown>;
  const swapTransaction = String(payload.swapTransaction ?? '').trim();
  if (!swapTransaction) {
    throw new SolanaJupiterExecutionError('rpc_unavailable', 'Jupiter swap build did not return swapTransaction.', 502);
  }
  return {
    routeKind: String(quote.routeKind ?? 'jupiter_route'),
    amountOutUnits: quote.amountOutUnits ? String(quote.amountOutUnits) : null,
    approvalTx: null,
    swapTx: {
      to: 'jupiter_v6',
      data: swapTransaction,
      value: '0',
    },
  };
}
