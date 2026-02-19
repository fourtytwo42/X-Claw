import type { NextRequest } from 'next/server';

import { Contract, JsonRpcProvider, Wallet, isAddress } from 'ethers';

import { requireAgentAuth } from '@/lib/agent-auth';
import { chainCapabilityEnabled, chainRpcUrl, getChainConfig, supportedChainHint } from '@/lib/chains';
import { dbQuery } from '@/lib/db';
import { errorResponse, successResponse, type ApiErrorCode } from '@/lib/errors';
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

const DEFAULT_ASSETS: FaucetAssetKey[] = ['native', 'wrapped', 'stable'];

const BASE_DRIP_NATIVE_WEI = '20000000000000000'; // 0.02 ETH
const BASE_DRIP_WRAPPED_WEI = '10000000000000000000'; // 10 WETH
const BASE_DRIP_STABLE_WEI = '20000000000000000000000'; // 20000 USDC

const KITE_DRIP_NATIVE_WEI = '50000000000000000'; // 0.05 KITE
const KITE_DRIP_WRAPPED_WEI = '50000000000000000'; // 0.05 WKITE
const KITE_DRIP_STABLE_WEI = '100000000000000000'; // 0.10 USDT
const HEDERA_DRIP_NATIVE_WEI = '5000000000000000000'; // 5.0 HBAR (wei-scaled)
const HEDERA_DRIP_WRAPPED_WEI = '500000000'; // 5.0 WHBAR (8 decimals)
const HEDERA_DRIP_STABLE_WEI = '10000000'; // 10.0 stable (6 decimals expected)

const GAS_BUFFER_MULTIPLIER_BPS = 12000; // 1.2x
const HEDERA_MIN_GAS_PRICE_WEI_DEFAULT = '900000000000'; // 900 gwei

const ERC20_ABI = [
  'function balanceOf(address owner) view returns (uint256)',
  'function transfer(address to, uint256 value) returns (bool)'
];
const WRAPPED_NATIVE_HELPER_ABI = ['function deposit() payable'];

type FaucetRouteErrorInput = {
  status: number;
  code: ApiErrorCode;
  message: string;
  actionHint: string;
  details?: Record<string, unknown>;
};

class FaucetRouteError extends Error {
  status: number;
  code: ApiErrorCode;
  actionHint: string;
  details: Record<string, unknown> | undefined;

  constructor(input: FaucetRouteErrorInput) {
    super(input.message);
    this.status = input.status;
    this.code = input.code;
    this.actionHint = input.actionHint;
    this.details = input.details;
  }
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

function isHederaChain(chainKey: string): boolean {
  return chainKey.startsWith('hedera_');
}

function parsePositiveWei(value: string, field: string): bigint {
  try {
    const parsed = BigInt(String(value || '').trim());
    if (parsed <= BigInt(0)) {
      throw new Error('non_positive');
    }
    return parsed;
  } catch {
    throw new FaucetRouteError({
      status: 503,
      code: 'faucet_config_invalid',
      message: `Faucet configuration for ${field} is invalid.`,
      actionHint: `Set ${field} to a positive integer amount in wei units.`,
      details: { field, value },
    });
  }
}

function resolveHederaMinGasPriceWei(chainKey: string): bigint {
  const configured =
    resolveChainScopedEnv('XCLAW_TESTNET_FAUCET_MIN_GAS_PRICE_WEI', chainKey) || HEDERA_MIN_GAS_PRICE_WEI_DEFAULT;
  return parsePositiveWei(configured, `XCLAW_TESTNET_FAUCET_MIN_GAS_PRICE_WEI_${toEnvSuffix(chainKey)}`);
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
  chainKey: string,
  feeData: Awaited<ReturnType<JsonRpcProvider['getFeeData']>>,
  attempt: number
): { gasPrice: bigint } | { maxFeePerGas: bigint; maxPriorityFeePerGas: bigint } {
  const bumpGwei = BigInt(1_000_000_000) * BigInt(attempt);
  if (isHederaChain(chainKey)) {
    const configuredGasPrice = resolveChainScopedEnv('XCLAW_TESTNET_FAUCET_GAS_PRICE_WEI', chainKey);
    const minGasPrice = resolveHederaMinGasPriceWei(chainKey);
    const proposedBase = configuredGasPrice ? parsePositiveWei(configuredGasPrice, `XCLAW_TESTNET_FAUCET_GAS_PRICE_WEI_${toEnvSuffix(chainKey)}`) : feeData.gasPrice ?? minGasPrice;
    if (proposedBase < minGasPrice) {
      throw new FaucetRouteError({
        status: 503,
        code: 'faucet_fee_too_low_for_chain',
        message: `Configured faucet gas price is below Hedera minimum floor for ${chainKey}.`,
        actionHint: `Set XCLAW_TESTNET_FAUCET_GAS_PRICE_WEI_${toEnvSuffix(chainKey)} >= ${minGasPrice.toString()}.`,
        details: {
          chainKey,
          requiredMinGasPriceWei: minGasPrice.toString(),
          proposedGasPriceWei: proposedBase.toString(),
        },
      });
    }
    const gasPrice = (proposedBase < minGasPrice ? minGasPrice : proposedBase) + bumpGwei;
    return { gasPrice };
  }
  const basePriority = feeData.maxPriorityFeePerGas ?? BigInt(1_000_000_000);
  const maxPriorityFeePerGas = basePriority + bumpGwei;
  const baseMaxFee = feeData.maxFeePerGas ?? feeData.gasPrice ?? BigInt(2_000_000_000);
  const maxFeePerGas = baseMaxFee + bumpGwei + BigInt(2_000_000_000);
  return { maxFeePerGas, maxPriorityFeePerGas };
}

function resolveWrappedToken(chainKey: string): { symbol: string; address: string } | null {
  const envAddress = resolveChainScopedEnv('XCLAW_TESTNET_FAUCET_WRAPPED_TOKEN_ADDRESS', chainKey);
  if (envAddress) {
    const envSymbol = resolveChainScopedEnv('XCLAW_TESTNET_FAUCET_WRAPPED_TOKEN_SYMBOL', chainKey) || 'WRAPPED';
    return { symbol: envSymbol, address: envAddress };
  }
  const cfg = getChainConfig(chainKey);
  const tokens = cfg?.canonicalTokens || {};
  const wrapped = (tokens.WETH || tokens.WKITE || tokens.WHBAR || '').trim();
  if (!wrapped) {
    return null;
  }
  const symbol = (tokens.WETH ? 'WETH' : tokens.WKITE ? 'WKITE' : 'WHBAR') as string;
  return { symbol, address: wrapped };
}

function resolveStableToken(chainKey: string): { symbol: string; address: string } | null {
  const envAddress = resolveChainScopedEnv('XCLAW_TESTNET_FAUCET_STABLE_TOKEN_ADDRESS', chainKey);
  if (envAddress) {
    const envSymbol = resolveChainScopedEnv('XCLAW_TESTNET_FAUCET_STABLE_TOKEN_SYMBOL', chainKey) || 'USDC';
    return { symbol: envSymbol, address: envAddress };
  }
  const cfg = getChainConfig(chainKey);
  const tokens = cfg?.canonicalTokens || {};
  const stable = (tokens.USDC || tokens.USDT || '').trim();
  if (!stable) {
    return null;
  }
  const symbol = (tokens.USDC ? 'USDC' : 'USDT') as string;
  return { symbol, address: stable };
}

function resolveWrappedNativeHelper(chainKey: string): string | null {
  const envAddress = resolveChainScopedEnv('XCLAW_TESTNET_FAUCET_WRAPPED_NATIVE_HELPER', chainKey);
  if (envAddress && isAddress(envAddress)) {
    return envAddress;
  }
  const cfg = getChainConfig(chainKey);
  const contracts = cfg?.coreContracts || {};
  const helper = typeof contracts?.wrappedNativeHelper === 'string' ? contracts.wrappedNativeHelper.trim() : '';
  if (helper && isAddress(helper)) {
    return helper;
  }
  return null;
}

function resolveDripAmounts(chainKey: string): { nativeWei: string; wrappedWei: string; stableWei: string } {
  const nativeOverride = resolveChainScopedEnv('XCLAW_TESTNET_FAUCET_DRIP_NATIVE_WEI', chainKey);
  const wrappedOverride = resolveChainScopedEnv('XCLAW_TESTNET_FAUCET_DRIP_WRAPPED_WEI', chainKey);
  const stableOverride = resolveChainScopedEnv('XCLAW_TESTNET_FAUCET_DRIP_STABLE_WEI', chainKey);
  if (nativeOverride || wrappedOverride || stableOverride) {
    return {
      nativeWei: nativeOverride || BASE_DRIP_NATIVE_WEI,
      wrappedWei: wrappedOverride || BASE_DRIP_WRAPPED_WEI,
      stableWei: stableOverride || BASE_DRIP_STABLE_WEI,
    };
  }
  if (chainKey === 'kite_ai_testnet') {
    return {
      nativeWei: KITE_DRIP_NATIVE_WEI,
      wrappedWei: KITE_DRIP_WRAPPED_WEI,
      stableWei: KITE_DRIP_STABLE_WEI,
    };
  }
  if (chainKey === 'hedera_testnet') {
    return {
      nativeWei: HEDERA_DRIP_NATIVE_WEI,
      wrappedWei: HEDERA_DRIP_WRAPPED_WEI,
      stableWei: HEDERA_DRIP_STABLE_WEI,
    };
  }
  return {
    nativeWei: BASE_DRIP_NATIVE_WEI,
    wrappedWei: BASE_DRIP_WRAPPED_WEI,
    stableWei: BASE_DRIP_STABLE_WEI,
  };
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
    if (!getChainConfig(chainKey) || !chainCapabilityEnabled(chainKey, 'faucet')) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Faucet is not available on the requested chain.',
          actionHint: supportedChainHint(),
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
          code: 'faucet_config_invalid',
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
          code: 'faucet_config_invalid',
          message: 'Faucet RPC is not configured.',
          actionHint: `Set XCLAW_TESTNET_FAUCET_RPC_URL_${toEnvSuffix(chainKey)} (or XCLAW_TESTNET_FAUCET_RPC_URL), or configure chain RPC.`
        },
        requestId
      );
    }

    const wrappedToken = requestedAssets.includes('wrapped') ? resolveWrappedToken(chainKey) : null;
    const stableToken = requestedAssets.includes('stable') ? resolveStableToken(chainKey) : null;
    const wrappedNativeHelper = isHederaChain(chainKey) ? resolveWrappedNativeHelper(chainKey) : null;

    if (requestedAssets.includes('wrapped') && !wrappedToken) {
      return errorResponse(
        503,
        {
          code: 'faucet_config_invalid',
          message: 'Wrapped token faucet asset is not configured for this chain.',
          actionHint: 'Configure canonicalTokens.WETH, canonicalTokens.WKITE, or canonicalTokens.WHBAR for the selected chain.',
          details: { chainKey }
        },
        requestId
      );
    }

    if (requestedAssets.includes('stable') && !stableToken) {
      return errorResponse(
        503,
        {
          code: 'faucet_config_invalid',
          message: 'Stable token faucet asset is not configured for this chain.',
          actionHint: 'Configure canonicalTokens.USDC or canonicalTokens.USDT for the selected chain.',
          details: { chainKey }
        },
        requestId
      );
    }

    if (wrappedToken && !isAddress(wrappedToken.address)) {
      return errorResponse(
        503,
        {
          code: 'faucet_config_invalid',
          message: 'Wrapped token address is invalid for faucet configuration.',
          actionHint: `Set XCLAW_TESTNET_FAUCET_WRAPPED_TOKEN_ADDRESS_${toEnvSuffix(chainKey)} to a valid EVM address.`,
          details: { chainKey, field: 'wrappedToken.address', value: wrappedToken.address }
        },
        requestId
      );
    }
    if (stableToken && !isAddress(stableToken.address)) {
      return errorResponse(
        503,
        {
          code: 'faucet_config_invalid',
          message: 'Stable token address is invalid for faucet configuration.',
          actionHint: `Set XCLAW_TESTNET_FAUCET_STABLE_TOKEN_ADDRESS_${toEnvSuffix(chainKey)} to a valid EVM address.`,
          details: { chainKey, field: 'stableToken.address', value: stableToken.address }
        },
        requestId
      );
    }

    const provider = new JsonRpcProvider(rpcUrl);
    const signer = new Wallet(faucetPrivateKey, provider);
    const faucetAddressLower = signer.address.toLowerCase();
    if (trimmedRecipient.toLowerCase() === faucetAddressLower) {
      return errorResponse(
        400,
        {
          code: 'faucet_recipient_not_eligible',
          message: 'Recipient wallet is not eligible for faucet funds.',
          actionHint: `Register a non-faucet wallet for ${chainKey} and retry.`,
          details: {
            chainKey,
            recipient: trimmedRecipient,
            faucetAddress: signer.address,
          }
        },
        requestId
      );
    }

    const nativeSymbol = getChainConfig(chainKey)?.nativeCurrency?.symbol?.trim() || 'ETH';
    const dripAmounts = resolveDripAmounts(chainKey);
    const dripNative = parsePositiveWei(dripAmounts.nativeWei, `XCLAW_TESTNET_FAUCET_DRIP_NATIVE_WEI_${toEnvSuffix(chainKey)}`);
    const dripWrapped = parsePositiveWei(dripAmounts.wrappedWei, `XCLAW_TESTNET_FAUCET_DRIP_WRAPPED_WEI_${toEnvSuffix(chainKey)}`);
    const dripStable = parsePositiveWei(dripAmounts.stableWei, `XCLAW_TESTNET_FAUCET_DRIP_STABLE_WEI_${toEnvSuffix(chainKey)}`);

    const wrapped = wrappedToken ? new Contract(wrappedToken.address, ERC20_ABI, signer) : null;
    const stable = stableToken ? new Contract(stableToken.address, ERC20_ABI, signer) : null;
    const wrappedNativeHelperContract = wrappedNativeHelper ? new Contract(wrappedNativeHelper, WRAPPED_NATIVE_HELPER_ABI, signer) : null;
    let wrappedAutoWrapDeficit = BigInt(0);
    let wrappedAutoWrapEstimate = BigInt(0);
    let wrappedAutoWrapTxHash: string | null = null;

    try {
      if (wrapped) {
        const wrappedBal = (await wrapped.balanceOf(signer.address)) as bigint;
        if (wrappedBal < dripWrapped) {
          wrappedAutoWrapDeficit = dripWrapped - wrappedBal;
          if (!isHederaChain(chainKey)) {
            throw new FaucetRouteError({
              status: 503,
              code: 'faucet_wrapped_insufficient',
              message: 'Faucet wrapped-token balance is insufficient.',
              actionHint: `Top up faucet ${wrappedToken?.symbol || 'wrapped'} balance and retry.`,
              details: { tokenAddress: wrappedToken?.address, requiredWei: dripWrapped.toString(), balanceWei: wrappedBal.toString() },
            });
          }
          if (!wrappedNativeHelper || !wrappedNativeHelperContract) {
            throw new FaucetRouteError({
              status: 503,
              code: 'faucet_wrapped_autowrap_failed',
              message: 'Wrapped token balance is insufficient and no wrapped-native helper is configured.',
              actionHint: `Set XCLAW_TESTNET_FAUCET_WRAPPED_NATIVE_HELPER_${toEnvSuffix(chainKey)} or coreContracts.wrappedNativeHelper.`,
              details: {
                chainKey,
                helperAddress: wrappedNativeHelper,
                requiredWei: dripWrapped.toString(),
                balanceWei: wrappedBal.toString(),
                deficitWei: wrappedAutoWrapDeficit.toString(),
              },
            });
          }
          try {
            wrappedAutoWrapEstimate = await signer.estimateGas(
              await wrappedNativeHelperContract.deposit.populateTransaction({ value: wrappedAutoWrapDeficit })
            );
          } catch (error) {
            throw new FaucetRouteError({
              status: 503,
              code: 'faucet_wrapped_autowrap_failed',
              message: error instanceof Error ? error.message : 'Auto-wrap preflight failed.',
              actionHint: 'Verify wrapped-native helper contract and faucet signer permissions, then retry.',
              details: {
                chainKey,
                helperAddress: wrappedNativeHelper,
                requiredWei: dripWrapped.toString(),
                balanceWei: wrappedBal.toString(),
                deficitWei: wrappedAutoWrapDeficit.toString(),
              },
            });
          }
        }
      }
      if (stable) {
        const stableBal = (await stable.balanceOf(signer.address)) as bigint;
        if (stableBal < dripStable) {
          throw new FaucetRouteError({
            status: 503,
            code: 'faucet_stable_insufficient',
            message: 'Faucet stable-token balance is insufficient.',
            actionHint: `Top up faucet ${stableToken?.symbol || 'stable'} balance and retry.`,
            details: { tokenAddress: stableToken?.address, requiredWei: dripStable.toString(), balanceWei: stableBal.toString() },
          });
        }
      }
    } catch (error) {
      if (error instanceof FaucetRouteError) {
        throw error;
      }
      throw new FaucetRouteError({
        status: 503,
        code: 'faucet_rpc_unavailable',
        message: 'Faucet token preflight failed while checking token balances.',
        actionHint: 'Verify RPC health and token contract configuration, then retry.',
        details: { chainKey },
      });
    }

    let feeData: Awaited<ReturnType<JsonRpcProvider['getFeeData']>>;
    try {
      feeData = await provider.getFeeData();
    } catch {
      throw new FaucetRouteError({
        status: 503,
        code: 'faucet_rpc_unavailable',
        message: 'Failed to resolve faucet fee data from chain RPC.',
        actionHint: 'Verify faucet RPC connectivity and retry.',
        details: { chainKey, rpcUrl },
      });
    }
    const initialFeeOverrides = buildFeeOverrides(chainKey, feeData, 0);
    const preflightGasPrice = 'gasPrice' in initialFeeOverrides ? initialFeeOverrides.gasPrice : initialFeeOverrides.maxFeePerGas;

    const estimates: bigint[] = [];
    try {
      if (wrappedAutoWrapEstimate > BigInt(0)) {
        estimates.push(wrappedAutoWrapEstimate);
      }
      if (wrapped) {
        estimates.push(await signer.estimateGas(await wrapped.transfer.populateTransaction(trimmedRecipient, dripWrapped)));
      }
      if (stable) {
        estimates.push(await signer.estimateGas(await stable.transfer.populateTransaction(trimmedRecipient, dripStable)));
      }
      if (requestedAssets.includes('native')) {
        estimates.push(await signer.estimateGas({ to: trimmedRecipient, value: dripNative }));
      }
    } catch (error) {
      throw new FaucetRouteError({
        status: 503,
        code: 'faucet_send_preflight_failed',
        message: error instanceof Error ? error.message : 'Faucet transfer preflight failed.',
        actionHint: 'Verify faucet token contracts and requested assets, then retry.',
        details: { chainKey, recipient: trimmedRecipient },
      });
    }

    const gasSum = estimates.reduce((acc, next) => acc + next, BigInt(0));
    const gasCost = (gasSum * preflightGasPrice * BigInt(GAS_BUFFER_MULTIPLIER_BPS)) / BigInt(10000);
    const nativeValue = requestedAssets.includes('native') ? dripNative : BigInt(0);
    const requiredNative = nativeValue + gasCost;
    let faucetBalance = BigInt(0);
    try {
      faucetBalance = await provider.getBalance(signer.address);
    } catch {
      throw new FaucetRouteError({
        status: 503,
        code: 'faucet_rpc_unavailable',
        message: 'Faucet preflight failed while reading native balance.',
        actionHint: 'Verify RPC health and retry.',
        details: { chainKey, faucetAddress: signer.address },
      });
    }
    if (faucetBalance < requiredNative) {
      throw new FaucetRouteError({
        status: 503,
        code: 'faucet_native_insufficient',
        message: 'Faucet wallet has insufficient native balance to cover drip plus gas.',
        actionHint: `Top up faucet wallet on ${chainKey}, then retry.`,
        details: {
          faucetAddress: signer.address,
          requiredWei: requiredNative.toString(),
          balanceWei: faucetBalance.toString()
        },
      });
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
        const fees = buildFeeOverrides(chainKey, feeData, attempt);
        try {
          let nonceOffset = 0;
          if (wrappedAutoWrapDeficit > BigInt(0) && wrappedNativeHelperContract) {
            const wrapTx = (await wrappedNativeHelperContract.deposit({
              value: wrappedAutoWrapDeficit,
              nonce: baseNonce + nonceOffset,
              ...fees,
            })) as { hash: string };
            wrappedAutoWrapTxHash = wrapTx.hash;
            nonceOffset += 1;
          }
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
          if (wrappedAutoWrapDeficit > BigInt(0)) {
            throw new FaucetRouteError({
              status: 503,
              code: 'faucet_wrapped_autowrap_failed',
              message: msg,
              actionHint: 'Auto-wrap was attempted but wrapped transfer still failed. Verify helper/token contracts and retry.',
              details: {
                chainKey,
                helperAddress: wrappedNativeHelper,
                wrappedAutoWrapTxHash,
                requiredWei: dripWrapped.toString(),
              },
            });
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
          amountWei: dripAmounts.wrappedWei,
          txHash: txByAsset.wrapped,
        });
    }
    if (stable && txByAsset.stable) {
      tokenDrips.push({
        token: stableToken?.symbol || 'STABLE',
        tokenAddress: stableToken?.address || '',
        amountWei: dripAmounts.stableWei,
        txHash: txByAsset.stable,
      });
    }

    return successResponse(
      {
        ok: true,
        agentId: auth.agentId,
        chainKey,
        recipientAddress: trimmedRecipient,
        faucetAddress: signer.address,
        amountWei: requestedAssets.includes('native') ? dripAmounts.nativeWei : '0',
        to: trimmedRecipient,
        txHash: primaryTxHash,
        tokenDrips,
        requestedAssets,
        fulfilledAssets,
        nativeSymbol,
        assetPlan: {
          native: requestedAssets.includes('native') ? { symbol: nativeSymbol, amountWei: dripAmounts.nativeWei } : null,
          wrapped: wrappedToken ? { symbol: wrappedToken.symbol, tokenAddress: wrappedToken.address, amountWei: dripAmounts.wrappedWei } : null,
          stable: stableToken ? { symbol: stableToken.symbol, tokenAddress: stableToken.address, amountWei: dripAmounts.stableWei } : null,
        },
      },
      200,
      requestId
    );
  } catch (error) {
    if (error instanceof FaucetRouteError) {
      return errorResponse(
        error.status,
        {
          code: error.code,
          message: error.message,
          actionHint: error.actionHint,
          details: error.details
        },
        requestId
      );
    }
    return errorResponse(
      500,
      {
        code: 'faucet_send_preflight_failed',
        message: error instanceof Error ? error.message : 'Faucet request failed.',
        actionHint: 'Retry later or check faucet funding/configuration and RPC health.'
      },
      requestId
    );
  }
}
