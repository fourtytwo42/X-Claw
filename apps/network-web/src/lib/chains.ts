import fs from 'node:fs';
import path from 'node:path';

export type ChainConfig = {
  chainKey: string;
  family?: 'evm' | 'solana';
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
    dex?: string;
    dexRouter?: string;
    factory?: string;
    router?: string;
    quoter?: string;
    nonfungiblePositionManager?: string;
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
  execution?: {
    trade?: {
      defaultProvider?: 'router_adapter' | 'quote_only' | 'none';
      adapters?: Record<
        string,
        {
          adapterKey?: string;
          family?: 'amm_v2' | 'amm_v3' | 'position_manager_v3' | string;
          router?: string;
          factory?: string;
          quoter?: string;
          positionManager?: string;
          capabilities?: {
            add?: boolean;
            remove?: boolean;
            increase?: boolean;
            claimFees?: boolean;
            claimRewards?: boolean;
            migrate?: boolean;
          };
          operations?: Record<string, Record<string, unknown>>;
        }
      >;
    };
    liquidity?: {
      defaultProvider?: 'router_adapter' | 'quote_only' | 'none';
      adapters?: Record<
        string,
        {
          adapterKey?: string;
          family?: 'amm_v2' | 'amm_v3' | 'position_manager_v3' | string;
          router?: string;
          factory?: string;
          quoter?: string;
          positionManager?: string;
          capabilities?: {
            add?: boolean;
            remove?: boolean;
            increase?: boolean;
            claimFees?: boolean;
            claimRewards?: boolean;
            migrate?: boolean;
          };
          operations?: Record<string, Record<string, unknown>>;
        }
      >;
    };
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
  return readChainConfigs().filter((cfg) => {
    if (!isChainEnabled(cfg)) {
      return false;
    }
    const family = (cfg.family ?? 'evm') as string;
    return family === 'evm' || family === 'solana';
  });
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

export function chainFamily(chainKey: string): 'evm' | 'solana' {
  const raw = String(getChainConfig(chainKey)?.family || '').trim().toLowerCase();
  return raw === 'solana' ? 'solana' : 'evm';
}

export function chainTxExplorerUrl(chainKey: string, txId: string | null | undefined): string | null {
  const id = String(txId || '').trim();
  if (!id) {
    return null;
  }
  const cfg = getChainConfig(chainKey);
  const base = String(cfg?.explorerBaseUrl || '').trim();
  if (!base) {
    return null;
  }

  if (chainFamily(chainKey) === 'solana') {
    if (!base.includes('explorer.solana.com')) {
      return null;
    }
    const clusterMatch = /[?&]cluster=([^&]+)/i.exec(base);
    const cluster = clusterMatch?.[1] ? decodeURIComponent(clusterMatch[1]) : '';
    const prefix = `https://explorer.solana.com/tx/${encodeURIComponent(id)}`;
    return cluster ? `${prefix}?cluster=${encodeURIComponent(cluster)}` : prefix;
  }

  return `${base.replace(/\/+$/, '')}/tx/${id}`;
}

export function chainNativeSymbol(chainKey: string): string {
  const symbol = getChainConfig(chainKey)?.nativeCurrency?.symbol;
  if (typeof symbol === 'string' && symbol.trim()) {
    return symbol.trim();
  }
  if (chainKey.startsWith('solana_')) {
    return 'SOL';
  }
  return chainKey === 'kite_ai_testnet' ? 'KITE' : 'ETH';
}

// Native EVM balances and amounts are expressed in wei-like base units.
export function chainNativeAtomicDecimals(chainKey: string): number {
  const decimals = getChainConfig(chainKey)?.nativeCurrency?.decimals;
  if (typeof decimals === 'number' && Number.isFinite(decimals) && decimals > 0) {
    return Math.floor(decimals);
  }
  if (chainKey.startsWith('solana_')) {
    return 9;
  }
  return 18;
}
