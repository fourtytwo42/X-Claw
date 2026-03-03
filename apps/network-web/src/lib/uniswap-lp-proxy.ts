import { chainCapabilityEnabled, getChainConfig } from '@/lib/chains';

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

type UniswapLpTx = {
  to: string;
  data: string;
  value: string;
};

type UniswapLpResult = {
  operation: 'approve' | 'create' | 'increase' | 'decrease' | 'claim' | 'migrate' | 'claim_rewards';
  transactions: UniswapLpTx[];
  raw: Record<string, unknown>;
};

type UniswapLpInput = {
  chainKey: string;
  walletAddress: string;
  request: Record<string, unknown>;
};

function ensureEligibleChain(chainKey: string): void {
  const cfg = getChainConfig(chainKey);
  if (!cfg || cfg.enabled === false || (cfg.family ?? 'evm') !== 'evm' || !chainCapabilityEnabled(chainKey, 'liquidity')) {
    throw new UniswapProxyError('unsupported_chain', `Chain '${chainKey}' is not enabled for EVM liquidity execution.`, 400, {
      chainKey,
    });
  }
}

function compatibilityResult(operation: UniswapLpResult['operation'], input: UniswapLpInput): UniswapLpResult {
  ensureEligibleChain(input.chainKey);
  return {
    operation,
    transactions: [],
    raw: {
      compatibilityMode: true,
      executionMode: 'runtime_local_router_adapter',
      request: input.request,
    },
  };
}

export function isUniswapLpEligibleChain(chainKey: string): boolean {
  try {
    ensureEligibleChain(chainKey);
    return true;
  } catch {
    return false;
  }
}

export function isUniswapLpOperationEnabled(chainKey: string, _operation: 'migrate' | 'claim_rewards'): boolean {
  return isUniswapLpEligibleChain(chainKey);
}

export async function approveLpUniswap(input: UniswapLpInput): Promise<UniswapLpResult> {
  return compatibilityResult('approve', input);
}

export async function createLpUniswap(input: UniswapLpInput): Promise<UniswapLpResult> {
  return compatibilityResult('create', input);
}

export async function increaseLpUniswap(input: UniswapLpInput): Promise<UniswapLpResult> {
  return compatibilityResult('increase', input);
}

export async function decreaseLpUniswap(input: UniswapLpInput): Promise<UniswapLpResult> {
  return compatibilityResult('decrease', input);
}

export async function claimLpFeesUniswap(input: UniswapLpInput): Promise<UniswapLpResult> {
  return compatibilityResult('claim', input);
}

export async function migrateLpUniswap(input: UniswapLpInput): Promise<UniswapLpResult> {
  return compatibilityResult('migrate', input);
}

export async function claimLpRewardsUniswap(input: UniswapLpInput): Promise<UniswapLpResult> {
  return compatibilityResult('claim_rewards', input);
}
