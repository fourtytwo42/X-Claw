import type { NextRequest } from 'next/server';

import { authenticateAgentByToken } from '@/lib/agent-auth';
import { getChainConfig } from '@/lib/chains';
import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import { parseJsonBody } from '@/lib/http';
import { getRequestId } from '@/lib/request-id';
import { validatePayload } from '@/lib/validation';

export const runtime = 'nodejs';

type AgentSolanaRpcRequest = {
  schemaVersion: 1;
  chainKey: string;
  method:
    | 'getLatestBlockhash'
    | 'getBalance'
    | 'getTokenAccountsByOwner'
    | 'getSignatureStatuses'
    | 'sendTransaction'
    | 'getTokenSupply'
    | 'getAccountInfo';
  params: unknown[];
};

const ALLOWED_METHODS = new Set<string>([
  'getLatestBlockhash',
  'getBalance',
  'getTokenAccountsByOwner',
  'getSignatureStatuses',
  'sendTransaction',
  'getTokenSupply',
  'getAccountInfo'
]);

function envSuffix(chainKey: string): string {
  return String(chainKey || '').trim().replace(/-/g, '_').toUpperCase();
}

function resolveTatumRpcUrl(chainKey: string): string {
  const suffix = envSuffix(chainKey);
  const scoped = String(process.env[`XCLAW_SOLANA_TATUM_RPC_URL_${suffix}`] || '').trim();
  if (scoped) {
    return scoped;
  }
  return String(process.env.XCLAW_SOLANA_TATUM_RPC_URL || '').trim();
}

function resolveTatumApiKey(chainKey: string): string {
  const suffix = envSuffix(chainKey);
  const scoped = String(process.env[`XCLAW_SOLANA_TATUM_RPC_API_KEY_${suffix}`] || '').trim();
  if (scoped) {
    return scoped;
  }
  return String(process.env.XCLAW_SOLANA_TATUM_RPC_API_KEY || '').trim();
}

export async function POST(req: NextRequest) {
  const requestId = getRequestId(req);
  try {
    const auth = authenticateAgentByToken(req, requestId);
    if (!auth.ok) {
      return auth.response;
    }

    const parsed = await parseJsonBody(req, requestId);
    if (!parsed.ok) {
      return parsed.response;
    }

    const validated = validatePayload<AgentSolanaRpcRequest>('agent-solana-rpc-request.schema.json', parsed.body);
    if (!validated.ok) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Solana RPC proxy payload does not match schema.',
          actionHint: 'Provide schemaVersion, chainKey, method, and params.',
          details: validated.details
        },
        requestId
      );
    }

    const body = validated.data;
    const chainKey = String(body.chainKey || '').trim();
    const method = String(body.method || '').trim();
    const params = Array.isArray(body.params) ? body.params : [];

    if (!ALLOWED_METHODS.has(method)) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: `Unsupported Solana RPC method '${method}'.`,
          actionHint: 'Use one of the allowlisted Solana RPC methods.'
        },
        requestId
      );
    }

    const chain = getChainConfig(chainKey);
    const family = String(chain?.family || '').trim().toLowerCase();
    if (!chain || family !== 'solana') {
      return errorResponse(
        400,
        {
          code: 'unsupported_chain',
          message: `Unsupported Solana chain '${chainKey}'.`,
          actionHint: 'Use a supported Solana chain key.'
        },
        requestId
      );
    }

    const tatumUrl = resolveTatumRpcUrl(chainKey);
    const tatumApiKey = resolveTatumApiKey(chainKey);
    if (!tatumUrl || !tatumApiKey) {
      return errorResponse(
        400,
        {
          code: 'rpc_unavailable',
          message: `Tatum fallback RPC is not configured for '${chainKey}'.`,
          actionHint: 'Set XCLAW_SOLANA_TATUM_RPC_URL[_<CHAIN>] and XCLAW_SOLANA_TATUM_RPC_API_KEY[_<CHAIN>] on the server.'
        },
        requestId
      );
    }

    const upstream = await fetch(tatumUrl, {
      method: 'POST',
      headers: {
        accept: 'application/json',
        'content-type': 'application/json',
        'x-api-key': tatumApiKey
      },
      body: JSON.stringify({ jsonrpc: '2.0', id: 1, method, params })
    });
    const raw = await upstream.text();
    let payload: unknown = null;
    try {
      payload = JSON.parse(raw || '{}');
    } catch {
      payload = null;
    }

    if (!upstream.ok) {
      return errorResponse(
        502,
        {
          code: 'rpc_unavailable',
          message: `Solana Tatum fallback RPC returned HTTP ${upstream.status}.`,
          actionHint: 'Retry request; if persistent, inspect server-side RPC fallback configuration.',
          details: { chainKey, method, status: upstream.status }
        },
        requestId
      );
    }

    if (payload && typeof payload === 'object' && (payload as Record<string, unknown>).error) {
      const rpcError = (payload as Record<string, unknown>).error as Record<string, unknown>;
      return errorResponse(
        502,
        {
          code: 'rpc_unavailable',
          message: String(rpcError?.message || 'Solana fallback RPC returned error payload.'),
          actionHint: 'Retry request; if persistent, inspect RPC health and method params.',
          details: { chainKey, method, rpcError }
        },
        requestId
      );
    }

    if (!payload || typeof payload !== 'object' || !Object.prototype.hasOwnProperty.call(payload, 'result')) {
      return errorResponse(
        502,
        {
          code: 'rpc_unavailable',
          message: 'Solana fallback RPC returned malformed payload.',
          actionHint: 'Retry request; if persistent, inspect RPC provider response format.',
          details: { chainKey, method }
        },
        requestId
      );
    }

    return successResponse(
      {
        ok: true,
        chainKey,
        method,
        providerUsed: 'tatum_fallback',
        result: (payload as Record<string, unknown>).result
      },
      200,
      requestId
    );
  } catch {
    return internalErrorResponse(requestId);
  }
}
