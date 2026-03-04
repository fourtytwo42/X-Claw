import { chainFamily, chainRpcUrl } from '@/lib/chains';
import type { ApiErrorCode } from '@/lib/errors';

export type X402VerificationInput = {
  chainKey: string;
  txId: string;
  expectedRecipient?: string | null;
  expectedAssetKind?: 'native' | 'token' | 'erc20' | null;
  expectedAssetAddress?: string | null;
};

export type X402VerificationResult =
  | {
      ok: true;
      code: 'ok';
      message: string;
      family: 'evm' | 'solana';
      details?: Record<string, unknown>;
    }
  | {
      ok: false;
      code: ApiErrorCode;
      message: string;
      family: 'evm' | 'solana';
      details?: Record<string, unknown>;
    };

function chainScopedEnv(base: string, chainKey: string): string | null {
  const key = `${base}_${chainKey.toUpperCase()}`;
  const value = process.env[key]?.trim();
  if (value) {
    return value;
  }
  return process.env[base]?.trim() || null;
}

async function rpcJson(
  chainKey: string,
  method: string,
  params: unknown[],
  requestId = 1
): Promise<unknown> {
  const rpcUrl = chainRpcUrl(chainKey);
  if (!rpcUrl) {
    throw new Error(`RPC URL is not configured for chain '${chainKey}'.`);
  }
  const family = chainFamily(chainKey);
  const headers: Record<string, string> = { 'content-type': 'application/json' };
  if (family === 'solana') {
    const apiKey = chainScopedEnv('XCLAW_SOLANA_RPC_API_KEY', chainKey);
    if (apiKey) {
      headers['x-api-key'] = apiKey;
    }
  }

  const res = await fetch(rpcUrl, {
    method: 'POST',
    headers,
    body: JSON.stringify({ jsonrpc: '2.0', id: requestId, method, params }),
    cache: 'no-store'
  });
  if (!res.ok) {
    throw new Error(`RPC request failed (${res.status}) for '${method}'.`);
  }
  const payload = (await res.json()) as { result?: unknown; error?: { message?: string } };
  if (payload.error) {
    throw new Error(payload.error.message || `RPC error for '${method}'.`);
  }
  return payload.result;
}

async function verifyEvm(input: X402VerificationInput): Promise<X402VerificationResult> {
  const result = (await rpcJson(input.chainKey, 'eth_getTransactionReceipt', [input.txId])) as
    | { status?: string | number; to?: string | null }
    | null;
  if (!result) {
    return {
      ok: false,
      code: 'x402_settlement_proof_invalid',
      message: 'EVM transaction receipt not found.',
      family: 'evm'
    };
  }
  const status = String(result.status ?? '').toLowerCase();
  if (!(status === '0x1' || status === '1')) {
    return {
      ok: false,
      code: 'x402_settlement_proof_invalid',
      message: 'EVM transaction receipt status is not successful.',
      family: 'evm',
      details: { status }
    };
  }

  const recipient = String(input.expectedRecipient || '').trim().toLowerCase();
  const assetKind = String(input.expectedAssetKind || '').trim().toLowerCase();
  const expectedAsset = String(input.expectedAssetAddress || '').trim().toLowerCase();
  const receiptTo = String(result.to || '').trim().toLowerCase();
  if (assetKind === 'native' && recipient && receiptTo && receiptTo !== recipient) {
    return {
      ok: false,
      code: 'x402_settlement_proof_invalid',
      message: 'EVM settlement recipient mismatch for native asset.',
      family: 'evm',
      details: { expectedRecipient: recipient, receiptTo }
    };
  }
  if ((assetKind === 'token' || assetKind === 'erc20') && expectedAsset && receiptTo && receiptTo !== expectedAsset) {
    return {
      ok: false,
      code: 'x402_settlement_proof_invalid',
      message: 'EVM settlement token contract mismatch.',
      family: 'evm',
      details: { expectedAssetAddress: expectedAsset, receiptTo }
    };
  }

  return { ok: true, code: 'ok', message: 'EVM settlement proof verified.', family: 'evm' };
}

async function verifySolana(input: X402VerificationInput): Promise<X402VerificationResult> {
  const statuses = (await rpcJson(input.chainKey, 'getSignatureStatuses', [[input.txId], { searchTransactionHistory: true }])) as {
    value?: Array<{ err?: unknown; confirmationStatus?: string | null } | null>;
  };
  const status = statuses?.value?.[0];
  if (!status) {
    return {
      ok: false,
      code: 'x402_settlement_proof_invalid',
      message: 'Solana signature status not found.',
      family: 'solana'
    };
  }
  if (status.err) {
    return {
      ok: false,
      code: 'x402_settlement_proof_invalid',
      message: 'Solana signature indicates execution error.',
      family: 'solana',
      details: { err: status.err }
    };
  }

  const recipient = String(input.expectedRecipient || '').trim();
  if (recipient) {
    const tx = (await rpcJson(input.chainKey, 'getTransaction', [input.txId, { encoding: 'jsonParsed', maxSupportedTransactionVersion: 0 }])) as
      | {
          transaction?: {
            message?: {
              accountKeys?: Array<{ pubkey?: string } | string>;
              instructions?: Array<{ parsed?: { info?: Record<string, unknown> } }>;
            };
          };
        }
      | null;
    if (!tx?.transaction?.message) {
      return {
        ok: false,
        code: 'x402_settlement_proof_invalid',
        message: 'Solana transaction payload not available for recipient verification.',
        family: 'solana'
      };
    }
    const msg = tx.transaction.message;
    const accountKeys = Array.isArray(msg.accountKeys) ? msg.accountKeys : [];
    const instructions = Array.isArray(msg.instructions) ? msg.instructions : [];
    const keyMatch = accountKeys.some((entry) => {
      if (typeof entry === 'string') {
        return entry === recipient;
      }
      return String(entry?.pubkey || '') === recipient;
    });
    const instructionMatch = instructions.some((ix) => {
      const info = ix?.parsed?.info || {};
      const destination = String(info['destination'] || info['to'] || '');
      return destination === recipient;
    });
    if (!keyMatch && !instructionMatch) {
      return {
        ok: false,
        code: 'x402_settlement_proof_invalid',
        message: 'Solana settlement recipient mismatch.',
        family: 'solana',
        details: { expectedRecipient: recipient }
      };
    }
  }

  return { ok: true, code: 'ok', message: 'Solana settlement proof verified.', family: 'solana' };
}

export async function verifyX402Settlement(input: X402VerificationInput): Promise<X402VerificationResult> {
  const family = chainFamily(input.chainKey);
  try {
    if (family === 'solana') {
      return await verifySolana(input);
    }
    return await verifyEvm(input);
  } catch (error) {
    return {
      ok: false,
      code: 'rpc_unavailable',
      message: error instanceof Error ? error.message : 'RPC verification failed.',
      family
    };
  }
}
