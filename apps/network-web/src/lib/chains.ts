import fs from 'node:fs';
import path from 'node:path';

export type ChainConfig = {
  chainKey: string;
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

export function chainRpcUrl(chainKey: string): string | null {
  const cfg = getChainConfig(chainKey);
  if (!cfg) {
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
