import fs from 'node:fs';
import path from 'node:path';

export type ChainConfig = {
  chainKey: string;
  family?: 'evm' | string;
  enabled?: boolean;
  uiVisible?: boolean;
  chainId?: number;
  displayName?: string;
  nativeCurrency?: {
    name?: string;
    symbol?: string;
    decimals?: number;
  } | null;
  explorerBaseUrl?: string | null;
  rpc?: {
    primary?: string | null;
    fallback?: string | null;
  };
  coreContracts?: {
    router?: string;
    quoter?: string;
    wrappedNativeHelper?: string;
  };
  capabilities?: {
    wallet?: boolean;
    trade?: boolean;
    liquidity?: boolean;
    limitOrders?: boolean;
    x402?: boolean;
    faucet?: boolean;
    deposits?: boolean;
  };
  tradeProviders?: {
    primary?: 'uniswap_api' | 'legacy_router' | string;
    fallback?: 'legacy_router' | 'none' | string;
  };
  liquidityProviders?: {
    primary?: 'uniswap_api' | 'legacy_router' | string;
    fallback?: 'legacy_router' | 'none' | string;
  };
  uniswapApi?: {
    enabled?: boolean;
    liquidityEnabled?: boolean;
    migrateEnabled?: boolean;
    claimRewardsEnabled?: boolean;
  };
  marketData?: {
    dexscreenerChainId?: string;
  };
  canonicalTokens?: Record<string, string>;
};

let cached: ChainConfig[] | null = null;

export function readChainConfigs(): ChainConfig[] {
  if (cached) {
    return cached;
  }

  const root = process.cwd();
  const dir = path.join(root, 'config', 'chains');
  const files = fs.readdirSync(dir).filter((file) => file.endsWith('.json')).sort();
  cached = files
    .map((file) => {
      const raw = fs.readFileSync(path.join(dir, file), 'utf8');
      return JSON.parse(raw) as ChainConfig;
    })
    .filter((cfg) => typeof cfg.chainKey === 'string' && cfg.chainKey.length > 0);

  return cached;
}

export function getChainConfig(chainKey: string): ChainConfig | null {
  return readChainConfigs().find((cfg) => cfg.chainKey === chainKey) ?? null;
}

function isChainEnabled(cfg: ChainConfig): boolean {
  return cfg.enabled !== false;
}

export function listEnabledChains(): ChainConfig[] {
  return readChainConfigs().filter(isChainEnabled);
}

export function listVisibleEnabledChains(): ChainConfig[] {
  return listEnabledChains().filter((cfg) => cfg.uiVisible !== false);
}

export function isSupportedChainKey(chainKey: string): boolean {
  return listEnabledChains().some((cfg) => cfg.chainKey === chainKey);
}

export function chainCapabilityEnabled(
  chainKey: string,
  capability: 'wallet' | 'trade' | 'liquidity' | 'limitOrders' | 'x402' | 'faucet' | 'deposits'
): boolean {
  const cfg = getChainConfig(chainKey);
  if (!cfg || !isChainEnabled(cfg)) {
    return false;
  }
  const caps = cfg.capabilities;
  if (!caps || typeof caps !== 'object') {
    return capability === 'wallet';
  }
  const value = caps[capability];
  if (typeof value === 'boolean') {
    return value;
  }
  return capability === 'wallet';
}

export function supportedChainHint(sampleSize = 6): string {
  const keys = listEnabledChains()
    .map((cfg) => cfg.chainKey)
    .slice(0, sampleSize);
  if (keys.length === 0) {
    return 'No enabled chains are configured.';
  }
  return `Use one of: ${keys.join(', ')}.`;
}

export function chainRpcUrl(chainKey: string): string | null {
  const cfg = getChainConfig(chainKey);
  if (!cfg || !isChainEnabled(cfg)) {
    return null;
  }

  const primary = cfg.rpc?.primary;
  if (primary && typeof primary === 'string') {
    return primary;
  }

  const fallback = cfg.rpc?.fallback;
  if (fallback && typeof fallback === 'string') {
    return fallback;
  }

  return null;
}

export function chainDisplayName(chainKey: string): string {
  return getChainConfig(chainKey)?.displayName ?? chainKey;
}

export function chainNativeSymbol(chainKey: string): string {
  const symbol = getChainConfig(chainKey)?.nativeCurrency?.symbol;
  if (typeof symbol === 'string' && symbol.trim()) {
    return symbol.trim();
  }
  return chainKey === 'kite_ai_testnet' ? 'KITE' : 'ETH';
}
