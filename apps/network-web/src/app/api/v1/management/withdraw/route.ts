import type { NextRequest } from 'next/server';

import { requireAgentChainEnabled } from '@/lib/agent-chain-policy';
import { chainCapabilityEnabled, chainFamily, chainNativeAtomicDecimals, chainNativeSymbol, getChainConfig } from '@/lib/chains';
import { withTransaction } from '@/lib/db';
import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import { parseJsonBody } from '@/lib/http';
import { makeId } from '@/lib/ids';
import { requireManagementWriteAuth } from '@/lib/management-auth';
import { buildWebTransferDecisionProdMessage, dispatchNonTelegramAgentProd } from '@/lib/non-telegram-agent-prod';
import { getRequestId } from '@/lib/request-id';
import { resolveTokenDecimals } from '@/lib/token-metadata';
import { validatePayload } from '@/lib/validation';

export const runtime = 'nodejs';

type WithdrawRequest = {
  agentId: string;
  chainKey: string;
  asset: string;
  amount: string;
  destination: string;
  assetKind?: 'native' | 'token' | 'erc20';
  tokenAddress?: string | null;
};

function redactAddress(address: string): string {
  return `${address.slice(0, 6)}...${address.slice(-4)}`;
}

function isHexAddress(value: string): boolean {
  return /^0x[a-fA-F0-9]{40}$/.test(value);
}

function isSolanaAddress(value: string): boolean {
  return /^[1-9A-HJ-NP-Za-km-z]{32,64}$/.test(value);
}

function pow10(decimals: number): bigint {
  let out = BigInt(1);
  for (let i = 0; i < decimals; i += 1) {
    out *= BigInt(10);
  }
  return out;
}

function decimalToUnits(amount: string, decimals: number): string {
  const raw = String(amount || '').trim();
  if (!/^[0-9]+(\.[0-9]{1,18})?$/.test(raw)) {
    throw new Error('invalid_amount_format');
  }
  const [wholeRaw, fracRaw = ''] = raw.split('.');
  const whole = wholeRaw || '0';
  if (fracRaw.length > decimals) {
    throw new Error('amount_precision_exceeds_token_decimals');
  }
  const wholeUnits = BigInt(whole) * pow10(decimals);
  const fracPadded = fracRaw.padEnd(decimals, '0');
  const fracUnits = fracPadded.length > 0 ? BigInt(fracPadded) : BigInt(0);
  const units = wholeUnits + fracUnits;
  if (units <= BigInt(0)) {
    throw new Error('amount_must_be_positive');
  }
  return units.toString();
}

function normalizeTokenAddressByFamily(value: string, family: 'evm' | 'solana'): string {
  return family === 'evm' ? value.toLowerCase() : value;
}

class ChainDisabledError extends Error {
  readonly violation: {
    code: 'chain_disabled';
    message: string;
    actionHint: string;
    details: Record<string, unknown>;
  };

  constructor(violation: { code: 'chain_disabled'; message: string; actionHint: string; details: Record<string, unknown> }) {
    super(violation.message);
    this.name = 'ChainDisabledError';
    this.violation = violation;
  }
}

export async function POST(req: NextRequest) {
  const requestId = getRequestId(req);

  try {
    const parsed = await parseJsonBody(req, requestId);
    if (!parsed.ok) {
      return parsed.response;
    }

    const validated = validatePayload<WithdrawRequest>('management-withdraw-request.schema.json', parsed.body);
    if (!validated.ok) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Withdraw payload does not match schema.',
          actionHint: 'Provide agentId, chainKey, asset, amount, and destination.',
          details: validated.details
        },
        requestId
      );
    }

    const body = validated.data;
    const auth = await requireManagementWriteAuth(req, requestId, body.agentId);
    if (!auth.ok) {
      return auth.response;
    }

    const chainCfg = getChainConfig(body.chainKey);
    if (!chainCfg || chainCfg.enabled === false) {
      return errorResponse(
        400,
        {
          code: 'unsupported_chain',
          message: `Chain '${body.chainKey}' is not supported.`,
          actionHint: 'Choose an enabled chain and retry.',
          details: { chainKey: body.chainKey }
        },
        requestId
      );
    }
    if (!chainCapabilityEnabled(body.chainKey, 'wallet')) {
      return errorResponse(
        400,
        {
          code: 'unsupported_chain_capability',
          message: `Chain '${body.chainKey}' does not support wallet transfers.`,
          actionHint: 'Choose a chain with wallet capability enabled.',
          details: { chainKey: body.chainKey, requiredCapability: 'wallet' }
        },
        requestId
      );
    }

    const family = chainFamily(body.chainKey);
    const destination = String(body.destination || '').trim();
    if (family === 'solana' ? !isSolanaAddress(destination) : !isHexAddress(destination)) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Destination is not a valid address for the selected chain.',
          actionHint: family === 'solana' ? 'Use a valid Solana base58 address.' : 'Use a valid 0x EVM address.',
          details: { chainKey: body.chainKey, destination: body.destination }
        },
        requestId
      );
    }

    const assetRaw = String(body.asset || '').trim();
    const assetKindRaw = String(body.assetKind || '').trim().toLowerCase();
    const nativeSymbol = chainNativeSymbol(body.chainKey).toUpperCase();
    const requestedTokenAddress = String(body.tokenAddress || '').trim();
    const isNativeRequested =
      assetKindRaw === 'native' ||
      (!assetKindRaw &&
        ['NATIVE', nativeSymbol].includes(assetRaw.toUpperCase()));

    let transferType: 'native' | 'token' = isNativeRequested ? 'native' : 'token';
    let tokenAddress: string | null = null;
    let tokenSymbol: string | null = transferType === 'native' ? nativeSymbol : null;
    let tokenDecimals = chainNativeAtomicDecimals(body.chainKey);
    if (transferType === 'token') {
      const cfgTokens = chainCfg.canonicalTokens ?? {};
      let resolvedToken = requestedTokenAddress;
      if (!resolvedToken) {
        if (family === 'solana' ? isSolanaAddress(assetRaw) : isHexAddress(assetRaw)) {
          resolvedToken = assetRaw;
        } else {
          const matched = Object.entries(cfgTokens).find(([symbol]) => symbol.toUpperCase() === assetRaw.toUpperCase())?.[1];
          if (matched) {
            resolvedToken = matched;
          }
        }
      }
      if (!resolvedToken || !(family === 'solana' ? isSolanaAddress(resolvedToken) : isHexAddress(resolvedToken))) {
        return errorResponse(
          400,
          {
            code: 'token_resolution_failed',
            message: 'Token withdraw requires a valid token address or canonical token symbol.',
            actionHint: 'Provide tokenAddress or use a canonical symbol configured on this chain.',
            details: { chainKey: body.chainKey, asset: body.asset, tokenAddress: body.tokenAddress }
          },
          requestId
        );
      }
      tokenAddress = normalizeTokenAddressByFamily(resolvedToken, family);
      tokenSymbol =
        Object.entries(cfgTokens).find(([, address]) => String(address || '').toLowerCase() === tokenAddress?.toLowerCase())?.[0] ??
        (isHexAddress(assetRaw) || isSolanaAddress(assetRaw) ? null : assetRaw.toUpperCase());
      tokenDecimals =
        family === 'evm'
          ? await resolveTokenDecimals(body.chainKey, tokenAddress).catch(() => 18)
          : chainNativeAtomicDecimals(body.chainKey);
    }

    let amountWei: string;
    try {
      amountWei = decimalToUnits(String(body.amount || ''), tokenDecimals);
    } catch (error) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Withdraw amount is invalid for the selected asset.',
          actionHint: 'Use a positive decimal amount within supported precision.',
          details: { chainKey: body.chainKey, amount: body.amount, tokenDecimals, error: String((error as Error).message || error) }
        },
        requestId
      );
    }

    const withdrawRequestId = makeId('wdr');
    const approvalId = makeId('xfr');
    const decisionId = makeId('tdi');
    const createdAtIso = new Date().toISOString();
    const decisionPayload = {
      kind: 'management_withdraw_v1',
      chainKey: body.chainKey,
      transferType,
      toAddress: family === 'evm' ? destination.toLowerCase() : destination,
      amountWei,
      tokenAddress,
      tokenSymbol,
      tokenDecimals,
      forcePolicyOverride: true,
      createdAt: createdAtIso
    };

    try {
      await withTransaction(async (client) => {
        const chainEnabled = await requireAgentChainEnabled(client, { agentId: body.agentId, chainKey: body.chainKey });
        if (!chainEnabled.ok) {
          throw new ChainDisabledError(chainEnabled.violation);
        }

        await client.query(
          `
          insert into agent_transfer_approval_mirror (
            approval_id,
            agent_id,
            chain_key,
            request_kind,
            status,
            transfer_type,
            approval_source,
            token_address,
            token_symbol,
            to_address,
            amount_wei,
            tx_hash,
            reason_code,
            reason_message,
            policy_blocked_at_create,
            policy_block_reason_code,
            policy_block_reason_message,
            execution_mode,
            created_at,
            updated_at,
            decided_at
          ) values (
            $1, $2, $3, 'withdraw', 'approved', $4, 'transfer', $5, $6, $7, $8::numeric, null, null, null, true, null, null, 'policy_override', now(), now(), now()
          )
          on conflict (approval_id)
          do update set
            status = excluded.status,
            updated_at = now(),
            decided_at = excluded.decided_at
          `,
          [approvalId, body.agentId, body.chainKey, transferType, tokenAddress, tokenSymbol, decisionPayload.toAddress, amountWei]
        );

        await client.query(
          `
          insert into agent_transfer_decision_inbox (
            decision_id, approval_id, agent_id, chain_key, request_kind, decision, reason_message, decision_payload, source, status, created_at
          ) values ($1, $2, $3, $4, 'withdraw', 'approve', null, $5::jsonb, 'web', 'pending', now())
          `,
          [decisionId, approvalId, body.agentId, body.chainKey, JSON.stringify(decisionPayload)]
        );

        await client.query(
          `
          insert into management_audit_log (
            audit_id, agent_id, management_session_id, action_type, action_status,
            public_redacted_payload, private_payload, user_agent, created_at
          ) values ($1, $2, $3, 'withdraw.request', 'accepted', $4::jsonb, $5::jsonb, $6, now())
          `,
          [
            makeId('aud'),
            body.agentId,
            auth.session.sessionId,
            JSON.stringify({
              withdrawRequestId,
              approvalId,
              decisionId,
              chainKey: body.chainKey,
              asset: body.asset,
              amount: body.amount,
              destination: redactAddress(body.destination)
            }),
            JSON.stringify({ ...body, amountWei, transferType, tokenAddress, tokenSymbol, tokenDecimals, executionMode: 'policy_override' }),
            req.headers.get('user-agent')
          ]
        );
      });
    } catch (error) {
      if (error instanceof ChainDisabledError) {
        throw error;
      }
      return errorResponse(
        500,
        {
          code: 'withdraw_queue_failed',
          message: 'Withdraw request could not be queued for runtime execution.',
          actionHint: 'Retry once. If this persists, inspect management and database logs.',
          details: { chainKey: body.chainKey }
        },
        requestId
      );
    }

    setImmediate(() => {
      void dispatchNonTelegramAgentProd({
        allowTelegramLastChannel: true,
        message: buildWebTransferDecisionProdMessage({
          decision: 'approve',
          approvalId,
          chainKey: body.chainKey,
          source: 'web_management_withdraw_submit',
          reasonMessage: 'Owner withdraw requested via management.'
        })
      }).catch(() => undefined);
    });

    return successResponse(
      {
        ok: true,
        withdrawRequestId,
        approvalId,
        decisionId,
        chainKey: body.chainKey,
        transferType,
        tokenAddress,
        tokenSymbol,
        tokenDecimals,
        amountWei,
        destination: decisionPayload.toAddress,
        status: 'queued',
        executionMode: 'policy_override',
        requestKind: 'withdraw'
      },
      200,
      requestId
    );
  } catch (error) {
    if (error instanceof ChainDisabledError) {
      return errorResponse(
        409,
        {
          code: error.violation.code,
          message: error.violation.message,
          actionHint: error.violation.actionHint,
          details: error.violation.details
        },
        requestId
      );
    }
    return internalErrorResponse(requestId);
  }
}
