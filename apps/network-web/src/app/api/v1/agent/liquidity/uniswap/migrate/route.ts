import type { NextRequest } from 'next/server';

import { requireAgentAuth } from '@/lib/agent-auth';
import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import { parseJsonBody } from '@/lib/http';
import { getRequestId } from '@/lib/request-id';
import { isUniswapLpOperationEnabled, migrateLpUniswap, UniswapProxyError } from '@/lib/uniswap-lp-proxy';
import { validatePayload } from '@/lib/validation';

type UniswapLpMigrateRequest = {
  agentId: string;
  chainKey: string;
  walletAddress: string;
  request: Record<string, unknown>;
};

export const runtime = 'nodejs';

export async function POST(req: NextRequest) {
  const requestId = getRequestId(req);
  try {
    const parsed = await parseJsonBody(req, requestId);
    if (!parsed.ok) {
      return parsed.response;
    }
    const validated = validatePayload<UniswapLpMigrateRequest>('uniswap-lp-migrate-request.schema.json', parsed.body);
    if (!validated.ok) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Uniswap LP migrate payload does not match schema.',
          actionHint: 'Check required fields and request object formatting.',
          details: validated.details,
        },
        requestId
      );
    }
    const body = validated.data;
    const auth = requireAgentAuth(req, body.agentId, requestId);
    if (!auth.ok) {
      return auth.response;
    }
    if (!isUniswapLpOperationEnabled(body.chainKey, 'migrate')) {
      return errorResponse(
        400,
        {
          code: 'uniswap_migrate_not_supported_on_chain',
          message: `Chain '${body.chainKey}' is not enabled for Uniswap LP migrate.`,
          actionHint: 'Use ethereum_sepolia or a chain with migrate enabled.',
          details: { chainKey: body.chainKey },
        },
        requestId
      );
    }
    const result = await migrateLpUniswap(body);
    return successResponse(
      {
        ok: true,
        chainKey: body.chainKey,
        operation: result.operation,
        transactions: result.transactions,
        raw: result.raw,
      },
      200,
      requestId
    );
  } catch (error) {
    if (error instanceof UniswapProxyError) {
      return errorResponse(
        error.status,
        {
          code: error.code as 'uniswap_upstream_error',
          message: error.message,
          actionHint: 'Retry with legacy fallback if this persists.',
          details: error.details,
        },
        requestId
      );
    }
    return internalErrorResponse(requestId);
  }
}
