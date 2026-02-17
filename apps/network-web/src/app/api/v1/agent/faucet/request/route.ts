import type { NextRequest } from 'next/server';

import { Contract, JsonRpcProvider, Wallet, isAddress } from 'ethers';

import { requireAgentAuth } from '@/lib/agent-auth';
import { chainRpcUrl, getChainConfig } from '@/lib/chains';
import { dbQuery } from '@/lib/db';
import { errorResponse, successResponse } from '@/lib/errors';
import { parseJsonBody } from '@/lib/http';
import { enforceAgentFaucetDailyRateLimit } from '@/lib/rate-limit';
import { getRedisClient } from '@/lib/redis';
import { getRequestId } from '@/lib/request-id';
import { validatePayload } from '@/lib/validation';

export const runtime = 'nodejs';

type FaucetAssetKey = 'native' | 'wrapped' | 'stable';

type AgentFaucetRequest = {
  schemaVersion: number;
  agentId: string;
  chainKey?: string;
  assets?: FaucetAssetKey[];
};

const SUPPORTED_FAUCET_CHAINS = new Set(['base_sepolia', 'kite_ai_testnet']);
const DEFAULT_ASSETS: FaucetAssetKey[] = ['native', 'wrapped', 'stable'];

const DRIP_NATIVE_WEI = '20000000000000000'; // 0.02 native token
const DRIP_WRAPPED_WEI = '10000000000000000000'; // 10.0 wrapped token (base units)
const DRIP_STABLE_WEI = '20000000000000000000000'; // 20000.0 stable token (base units)

const GAS_BUFFER_MULTIPLIER_BPS = 12000; // 1.2x

const ERC20_ABI = [
  'function balanceOf(address owner) view returns (uint256)',
  'function transfer(address to, uint256 value) returns (bool)'
];

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

function parseRequestedAssets(raw: FaucetAssetKey[] | undefined): FaucetAssetKey[] {
  if (!Array.isArray(raw) || raw.length === 0) {
    return [...DEFAULT_ASSETS];
  }
  const out: FaucetAssetKey[] = [];
  for (const value of raw) {
    const key = String(value || '').trim().toLowerCase();
    if (key === 'native' || key === 'wrapped' || key === 'stable') {
      if (!out.includes(key)) {
        out.push(key);
      }
    }
  }
  return out;
}

function faucetDailyRedisKey(agentId: string, chainKey: string, now: Date): { redisKey: string; ttlSeconds: number } {
  const nextUtcMidnight = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate() + 1, 0, 0, 0, 0);
  const ttlSeconds = Math.max(1, Math.floor((nextUtcMidnight - now.getTime()) / 1000));
  const keyDate = `${now.getUTCFullYear()}-${String(now.getUTCMonth() + 1).padStart(2, '0')}-${String(now.getUTCDate()).padStart(2, '0')}`;
  const redisKey = `xclaw:ratelimit:v1:agent_faucet_daily:${agentId}:${chainKey}:${keyDate}`;
  return { redisKey, ttlSeconds };
}

async function rollbackFaucetDailyLimit(agentId: string, chainKey: string): Promise<void> {
  try {
    const now = new Date();
    const { redisKey } = faucetDailyRedisKey(agentId, chainKey, now);
    const redis = await getRedisClient();
    await redis.del(redisKey);
  } catch {
    // best effort
  }
}

function buildFeeOverrides(
  feeData: Awaited<ReturnType<JsonRpcProvider['getFeeData']>>,
  attempt: number
): { maxFeePerGas: bigint; maxPriorityFeePerGas: bigint } {
  const bumpGwei = BigInt(1_000_000_000) * BigInt(attempt);
  const basePriority = feeData.maxPriorityFeePerGas ?? BigInt(1_000_000_000);
  const maxPriorityFeePerGas = basePriority + bumpGwei;
  const baseMaxFee = feeData.maxFeePerGas ?? feeData.gasPrice ?? BigInt(2_000_000_000);
  const maxFeePerGas = baseMaxFee + bumpGwei + BigInt(2_000_000_000);
  return { maxFeePerGas, maxPriorityFeePerGas };
}

function resolveWrappedToken(chainKey: string): { symbol: string; address: string } | null {
  const cfg = getChainConfig(chainKey);
  const tokens = cfg?.canonicalTokens || {};
  const wrapped = (tokens.WETH || tokens.WKITE || '').trim();
  if (!wrapped) {
    return null;
  }
  const symbol = (tokens.WETH ? 'WETH' : 'WKITE') as string;
  return { symbol, address: wrapped };
}

function resolveStableToken(chainKey: string): { symbol: string; address: string } | null {
  const cfg = getChainConfig(chainKey);
  const tokens = cfg?.canonicalTokens || {};
  const stable = (tokens.USDC || tokens.USDT || '').trim();
  if (!stable) {
    return null;
  }
  const symbol = (tokens.USDC ? 'USDC' : 'USDT') as string;
  return { symbol, address: stable };
}

export async function POST(req: NextRequest) {
  const requestId = getRequestId(req);

  try {
    const parsed = await parseJsonBody(req, requestId);
    if (!parsed.ok) {
      return parsed.response;
    }

    const validated = validatePayload<AgentFaucetRequest>('agent-faucet-request.schema.json', parsed.body);
    if (!validated.ok) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Faucet request payload does not match schema.',
          actionHint: 'Provide schemaVersion, agentId, chainKey, and optional assets array.',
          details: validated.details
        },
        requestId
      );
    }

    const body = validated.data;
    const auth = requireAgentAuth(req, body.agentId, requestId);
    if (!auth.ok) {
      return auth.response;
    }

    const agentId = auth.agentId;
    if (agentId === 'ag_slice7' || agentId.startsWith('ag_slice') || agentId.startsWith('ag_demo')) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Faucet is not available for demo agents.',
          actionHint: 'Register a non-demo agent with a real wallet address, then retry.'
        },
        requestId
      );
    }

    const chainKey = (body.chainKey || 'base_sepolia').trim();
    if (!SUPPORTED_FAUCET_CHAINS.has(chainKey)) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Faucet is only available on base_sepolia and kite_ai_testnet.',
          actionHint: 'Retry with chainKey=base_sepolia or chainKey=kite_ai_testnet.',
          details: { chainKey }
        },
        requestId
      );
    }

    const requestedAssets = parseRequestedAssets(body.assets);
    if (requestedAssets.length === 0) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'assets contains unsupported values.',
          actionHint: 'Use assets from: native, wrapped, stable.'
        },
        requestId
      );
    }

    const faucetPrivateKey = resolveChainScopedEnv('XCLAW_TESTNET_FAUCET_PRIVATE_KEY', chainKey);
    if (!faucetPrivateKey) {
      return errorResponse(
        503,
        {
          code: 'internal_error',
          message: 'Faucet is not configured.',
          actionHint: `Set XCLAW_TESTNET_FAUCET_PRIVATE_KEY_${toEnvSuffix(chainKey)} (or XCLAW_TESTNET_FAUCET_PRIVATE_KEY).`
        },
        requestId
      );
    }

    const walletResult = await dbQuery<{ address: string }>(
      `
      select address
      from agent_wallets
      where agent_id = $1
        and chain_key = $2
      limit 1
      `,
      [auth.agentId, chainKey]
    );
    if ((walletResult.rowCount ?? 0) === 0) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Agent wallet is not registered for requested chain.',
          actionHint: `Register agent wallet on ${chainKey} and retry.`
        },
        requestId
      );
    }

    const recipient = walletResult.rows[0].address;
    const trimmedRecipient = recipient.trim();
    if (!isAddress(trimmedRecipient)) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Agent wallet address is not a valid EVM address.',
          actionHint: 'Re-register the agent wallet address and retry.'
        },
        requestId
      );
    }

    const lower = trimmedRecipient.toLowerCase();
    if (
      lower === '0x0000000000000000000000000000000000000000' ||
      lower === '0x1111111111111111111111111111111111111111'
    ) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Recipient wallet address is not eligible for faucet funds.',
          actionHint: 'Register a real agent wallet address and retry.'
        },
        requestId
      );
    }

    const rpcUrl = resolveChainScopedEnv('XCLAW_TESTNET_FAUCET_RPC_URL', chainKey) || chainRpcUrl(chainKey);
    if (!rpcUrl) {
      return errorResponse(
        503,
        {
          code: 'internal_error',
          message: 'Faucet RPC is not configured.',
          actionHint: `Set XCLAW_TESTNET_FAUCET_RPC_URL_${toEnvSuffix(chainKey)} (or XCLAW_TESTNET_FAUCET_RPC_URL), or configure chain RPC.`
        },
        requestId
      );
    }

    const wrappedToken = requestedAssets.includes('wrapped') ? resolveWrappedToken(chainKey) : null;
    const stableToken = requestedAssets.includes('stable') ? resolveStableToken(chainKey) : null;

    if (requestedAssets.includes('wrapped') && !wrappedToken) {
      return errorResponse(
        503,
        {
          code: 'internal_error',
          message: 'Wrapped token faucet asset is not configured for this chain.',
          actionHint: 'Configure canonicalTokens.WETH or canonicalTokens.WKITE for the selected chain.',
          details: { chainKey }
        },
        requestId
      );
    }

    if (requestedAssets.includes('stable') && !stableToken) {
      return errorResponse(
        503,
        {
          code: 'internal_error',
          message: 'Stable token faucet asset is not configured for this chain.',
          actionHint: 'Configure canonicalTokens.USDC or canonicalTokens.USDT for the selected chain.',
          details: { chainKey }
        },
        requestId
      );
    }

    const provider = new JsonRpcProvider(rpcUrl);
    const signer = new Wallet(faucetPrivateKey, provider);

    const nativeSymbol = chainKey === 'kite_ai_testnet' ? 'KITE' : 'ETH';
    const dripNative = BigInt(DRIP_NATIVE_WEI);
    const dripWrapped = BigInt(DRIP_WRAPPED_WEI);
    const dripStable = BigInt(DRIP_STABLE_WEI);

    const wrapped = wrappedToken ? new Contract(wrappedToken.address, ERC20_ABI, signer) : null;
    const stable = stableToken ? new Contract(stableToken.address, ERC20_ABI, signer) : null;

    if (wrapped) {
      const wrappedBal = (await wrapped.balanceOf(signer.address)) as bigint;
      if (wrappedBal < dripWrapped) {
        return errorResponse(
          503,
          {
            code: 'internal_error',
            message: 'Faucet wrapped-token balance is insufficient.',
            actionHint: `Top up faucet ${wrappedToken?.symbol || 'wrapped'} balance and retry.`,
            details: { tokenAddress: wrappedToken?.address }
          },
          requestId
        );
      }
    }

    if (stable) {
      const stableBal = (await stable.balanceOf(signer.address)) as bigint;
      if (stableBal < dripStable) {
        return errorResponse(
          503,
          {
            code: 'internal_error',
            message: 'Faucet stable-token balance is insufficient.',
            actionHint: `Top up faucet ${stableToken?.symbol || 'stable'} balance and retry.`,
            details: { tokenAddress: stableToken?.address }
          },
          requestId
        );
      }
    }

    const feeData = await provider.getFeeData();
    const maxFeePerGas = feeData.maxFeePerGas ?? feeData.gasPrice ?? BigInt(1_000_000_000);

    const estimates: bigint[] = [];
    if (wrapped) {
      estimates.push(await signer.estimateGas(await wrapped.transfer.populateTransaction(trimmedRecipient, dripWrapped)));
    }
    if (stable) {
      estimates.push(await signer.estimateGas(await stable.transfer.populateTransaction(trimmedRecipient, dripStable)));
    }
    if (requestedAssets.includes('native')) {
      estimates.push(await signer.estimateGas({ to: trimmedRecipient, value: dripNative }));
    }

    const gasSum = estimates.reduce((acc, next) => acc + next, BigInt(0));
    const gasCost = (gasSum * maxFeePerGas * BigInt(GAS_BUFFER_MULTIPLIER_BPS)) / BigInt(10000);
    const nativeValue = requestedAssets.includes('native') ? dripNative : BigInt(0);
    const requiredNative = nativeValue + gasCost;
    const faucetBalance = await provider.getBalance(signer.address);
    if (faucetBalance < requiredNative) {
      return errorResponse(
        503,
        {
          code: 'internal_error',
          message: 'Faucet wallet has insufficient native balance to cover drip plus gas.',
          actionHint: `Top up faucet wallet on ${chainKey}, then retry.`,
          details: {
            faucetAddress: signer.address,
            requiredWei: requiredNative.toString(),
            balanceWei: faucetBalance.toString()
          }
        },
        requestId
      );
    }

    const limiter = await enforceAgentFaucetDailyRateLimit(requestId, auth.agentId, chainKey);
    if (!limiter.ok) {
      return limiter.response;
    }

    const baseNonce = await provider.getTransactionCount(signer.address, 'pending');
    const sendAttempts = 3;

    const txByAsset: Partial<Record<FaucetAssetKey, string>> = {};

    try {
      for (let attempt = 0; attempt < sendAttempts; attempt += 1) {
        const fees = buildFeeOverrides(feeData, attempt);
        try {
          let nonceOffset = 0;
          if (wrapped) {
            const tx = (await wrapped.transfer(trimmedRecipient, dripWrapped, { nonce: baseNonce + nonceOffset, ...fees })) as { hash: string };
            txByAsset.wrapped = tx.hash;
            nonceOffset += 1;
          }
          if (stable) {
            const tx = (await stable.transfer(trimmedRecipient, dripStable, { nonce: baseNonce + nonceOffset, ...fees })) as { hash: string };
            txByAsset.stable = tx.hash;
            nonceOffset += 1;
          }
          if (requestedAssets.includes('native')) {
            const tx = (await signer.sendTransaction({ to: trimmedRecipient, value: dripNative, nonce: baseNonce + nonceOffset, ...fees })) as {
              hash: string;
            };
            txByAsset.native = tx.hash;
          }
          break;
        } catch (err) {
          const msg = err instanceof Error ? err.message : String(err);
          const retryable =
            msg.includes('REPLACEMENT_UNDERPRICED') ||
            msg.includes('replacement transaction underpriced') ||
            msg.includes('nonce too low') ||
            msg.includes('already known');
          if (attempt < sendAttempts - 1 && retryable) {
            continue;
          }
          throw err;
        }
      }
    } catch (sendError) {
      await rollbackFaucetDailyLimit(auth.agentId, chainKey);
      throw sendError;
    }

    const fulfilledAssets = (Object.keys(txByAsset) as FaucetAssetKey[]).filter((asset) => Boolean(txByAsset[asset]));
    if (fulfilledAssets.length === 0) {
      await rollbackFaucetDailyLimit(auth.agentId, chainKey);
      throw new Error('Faucet send failed (no tx hashes).');
    }

    const primaryTxHash = txByAsset.native || txByAsset.wrapped || txByAsset.stable || '';

    const tokenDrips: Array<{ token: string; tokenAddress: string; amountWei: string; txHash: string }> = [];
    if (wrapped && txByAsset.wrapped) {
      tokenDrips.push({
        token: wrappedToken?.symbol || 'WRAPPED',
        tokenAddress: wrappedToken?.address || '',
        amountWei: DRIP_WRAPPED_WEI,
        txHash: txByAsset.wrapped,
      });
    }
    if (stable && txByAsset.stable) {
      tokenDrips.push({
        token: stableToken?.symbol || 'STABLE',
        tokenAddress: stableToken?.address || '',
        amountWei: DRIP_STABLE_WEI,
        txHash: txByAsset.stable,
      });
    }

    return successResponse(
      {
        ok: true,
        agentId: auth.agentId,
        chainKey,
        amountWei: requestedAssets.includes('native') ? DRIP_NATIVE_WEI : '0',
        to: trimmedRecipient,
        txHash: primaryTxHash,
        tokenDrips,
        requestedAssets,
        fulfilledAssets,
        nativeSymbol,
        assetPlan: {
          native: requestedAssets.includes('native') ? { symbol: nativeSymbol, amountWei: DRIP_NATIVE_WEI } : null,
          wrapped: wrappedToken ? { symbol: wrappedToken.symbol, tokenAddress: wrappedToken.address, amountWei: DRIP_WRAPPED_WEI } : null,
          stable: stableToken ? { symbol: stableToken.symbol, tokenAddress: stableToken.address, amountWei: DRIP_STABLE_WEI } : null,
        },
      },
      200,
      requestId
    );
  } catch (error) {
    return errorResponse(
      500,
      {
        code: 'internal_error',
        message: error instanceof Error ? error.message : 'Faucet request failed.',
        actionHint: 'Retry later or check faucet funding/configuration.'
      },
      requestId
    );
  }
}
