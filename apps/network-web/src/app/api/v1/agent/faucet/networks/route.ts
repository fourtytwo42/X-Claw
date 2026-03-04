import type { NextRequest } from 'next/server';
import { isAddress } from 'ethers';

import { authenticateAgentByToken } from '@/lib/agent-auth';
import { chainCapabilityEnabled, getChainConfig, listEnabledChains } from '@/lib/chains';
import { successResponse } from '@/lib/errors';
import { getRequestId } from '@/lib/request-id';

export const runtime = 'nodejs';

type FaucetAssetKey = 'native' | 'wrapped' | 'stable';

function isLikelySolanaAddress(value: string): boolean {
  const text = String(value || '').trim();
  return /^[1-9A-HJ-NP-Za-km-z]{32,44}$/.test(text);
}

function toEnvSuffix(chainKey: string): string {
  return chainKey.replace(/[^a-zA-Z0-9]/g, '_').toUpperCase();
}

function resolveChainScopedEnv(prefix: string, chainKey: string): string {
  const suffix = toEnvSuffix(chainKey);
  const scoped = (process.env[`${prefix}_${suffix}`] || '').trim();
  if (scoped) {
    return scoped;
  }
  return (process.env[prefix] || '').trim();
}

function resolveWrapped(chainKey: string): { symbol: string; address: string } | null {
  const family = (getChainConfig(chainKey)?.family || 'evm').toLowerCase();
  const envAddress =
    resolveChainScopedEnv('XCLAW_SOLANA_FAUCET_WRAPPED_MINT', chainKey) ||
    resolveChainScopedEnv('XCLAW_TESTNET_FAUCET_WRAPPED_TOKEN_ADDRESS', chainKey);
  if (envAddress) {
    const envSymbol = resolveChainScopedEnv('XCLAW_TESTNET_FAUCET_WRAPPED_TOKEN_SYMBOL', chainKey) || 'WRAPPED';
    if (family === 'solana' ? !isLikelySolanaAddress(envAddress) : !isAddress(envAddress)) {
      return null;
    }
    return { symbol: envSymbol, address: envAddress };
  }
  const cfg = getChainConfig(chainKey);
  const tokens = cfg?.canonicalTokens || {};
  const address = (tokens.WETH || tokens.WKITE || tokens.WHBAR || tokens.WSOL || '').trim();
  if (!address) {
    return null;
  }
  const symbol = tokens.WETH ? 'WETH' : tokens.WKITE ? 'WKITE' : tokens.WHBAR ? 'WHBAR' : 'WSOL';
  if (family === 'solana' ? !isLikelySolanaAddress(address) : !isAddress(address)) {
    return null;
  }
  return { symbol, address };
}

function resolveStable(chainKey: string): { symbol: string; address: string } | null {
  const family = (getChainConfig(chainKey)?.family || 'evm').toLowerCase();
  const envAddress =
    resolveChainScopedEnv('XCLAW_SOLANA_FAUCET_STABLE_MINT', chainKey) ||
    resolveChainScopedEnv('XCLAW_TESTNET_FAUCET_STABLE_TOKEN_ADDRESS', chainKey);
  if (envAddress) {
    const envSymbol = resolveChainScopedEnv('XCLAW_TESTNET_FAUCET_STABLE_TOKEN_SYMBOL', chainKey) || 'USDC';
    if (family === 'solana' ? !isLikelySolanaAddress(envAddress) : !isAddress(envAddress)) {
      return null;
    }
    return { symbol: envSymbol, address: envAddress };
  }
  const cfg = getChainConfig(chainKey);
  const tokens = cfg?.canonicalTokens || {};
  const address = (tokens.USDC || tokens.USDT || '').trim();
  if (!address) {
    return null;
  }
  const symbol = tokens.USDC ? 'USDC' : 'USDT';
  if (family === 'solana' ? !isLikelySolanaAddress(address) : !isAddress(address)) {
    return null;
  }
  return { symbol, address };
}

export async function GET(req: NextRequest) {
  const requestId = getRequestId(req);
  const auth = authenticateAgentByToken(req, requestId);
  if (!auth.ok) {
    return auth.response;
  }

  const faucetChains = listEnabledChains().filter((cfg) => chainCapabilityEnabled(cfg.chainKey, 'faucet'));
  const networks = faucetChains.map((cfg) => {
    const chainKey = cfg.chainKey;
    const wrapped = resolveWrapped(chainKey);
    const stable = resolveStable(chainKey);
    const nativeSymbol = cfg.nativeCurrency?.symbol?.trim() || 'ETH';

    const family = String(cfg.family || 'evm').toLowerCase();
    const configured =
      family === 'solana'
        ? Boolean(
            (resolveChainScopedEnv('XCLAW_SOLANA_FAUCET_SIGNER_SECRET', chainKey) ||
              resolveChainScopedEnv('XCLAW_TESTNET_FAUCET_PRIVATE_KEY', chainKey)) &&
              (resolveChainScopedEnv('XCLAW_TESTNET_FAUCET_RPC_URL', chainKey) || cfg.rpc?.primary)
          )
        : Boolean(resolveChainScopedEnv('XCLAW_TESTNET_FAUCET_PRIVATE_KEY', chainKey));

    const supportedAssets: FaucetAssetKey[] = ['native'];
    if (wrapped) {
      supportedAssets.push('wrapped');
    }
    if (stable) {
      supportedAssets.push('stable');
    }

    return {
      chainKey,
      displayName: cfg?.displayName || chainKey,
      chainId: cfg?.chainId ?? null,
      faucetConfigured: configured,
      supportedAssets,
      native: {
        symbol: nativeSymbol,
      },
      wrapped,
      stable,
      missingConfig: {
        privateKey: !configured,
        wrappedToken: !wrapped,
        stableToken: !stable,
      },
    };
  });

  return successResponse(
    {
      ok: true,
      agentId: auth.agentId,
      networks,
    },
    200,
    requestId
  );
}
