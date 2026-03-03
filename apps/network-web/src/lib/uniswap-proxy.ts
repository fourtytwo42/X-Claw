import {
  buildTradeViaRouter,
  EvmRouterExecutionError,
  quoteTradeViaRouter,
} from '@/lib/evm-router-execution';
import { chainCapabilityEnabled, getChainConfig } from '@/lib/chains';

export class UniswapProxyError extends EvmRouterExecutionError {}

export type UniswapQuoteInput = Parameters<typeof quoteTradeViaRouter>[0];
export type UniswapBuildInput = Parameters<typeof buildTradeViaRouter>[0];
export type UniswapQuoteResult = Awaited<ReturnType<typeof quoteTradeViaRouter>>;
export type UniswapBuildResult = Awaited<ReturnType<typeof buildTradeViaRouter>>;

export function isUniswapEligibleChain(chainKey: string): boolean {
  const cfg = getChainConfig(chainKey);
  return Boolean(cfg && cfg.enabled !== false && (cfg.family ?? 'evm') === 'evm' && chainCapabilityEnabled(chainKey, 'trade'));
}

export async function quoteUniswap(input: UniswapQuoteInput): Promise<UniswapQuoteResult> {
  return quoteTradeViaRouter(input);
}

export async function buildUniswap(input: UniswapBuildInput): Promise<UniswapBuildResult> {
  return buildTradeViaRouter(input);
}
