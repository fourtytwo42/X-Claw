import type { NextRequest } from 'next/server';

import { requireAgentAuth } from '@/lib/agent-auth';
import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import { parseJsonBody } from '@/lib/http';
import { getRequestId } from '@/lib/request-id';
import { decreaseLpUniswap, isUniswapLpEligibleChain, UniswapProxyError } from '@/lib/uniswap-lp-proxy';
import { validatePayload } from '@/lib/validation';

type UniswapLpDecreaseRequest = {
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
    const validated = validatePayload<UniswapLpDecreaseRequest>('uniswap-lp-decrease-request.schema.json', parsed.body);
    if (!validated.ok) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Uniswap LP decrease payload does not match schema.',
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
    if (!isUniswapLpEligibleChain(body.chainKey)) {
      return errorResponse(
        400,
        {
          code: 'unsupported_chain',
          message: `Chain '${body.chainKey}' is not enabled for Uniswap LP proxy execution.`,
          actionHint: 'Use an LP-enabled Uniswap chain or run the legacy liquidity path.',
          details: { chainKey: body.chainKey },
        },
        requestId
      );
    }
    const result = await decreaseLpUniswap(body);
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
          code: 'unsupported_execution_adapter',
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
