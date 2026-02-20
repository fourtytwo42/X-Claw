import type { NextRequest } from 'next/server';

import { requireAgentAuth } from '@/lib/agent-auth';
import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import { parseJsonBody } from '@/lib/http';
import { getRequestId } from '@/lib/request-id';
import { buildUniswap, UniswapProxyError, isUniswapEligibleChain } from '@/lib/uniswap-proxy';
import { validatePayload } from '@/lib/validation';

type UniswapBuildRequest = {
  agentId: string;
  chainKey: string;
  walletAddress: string;
  quote: Record<string, unknown>;
};

export const runtime = 'nodejs';

export async function POST(req: NextRequest) {
  const requestId = getRequestId(req);
  try {
    const parsed = await parseJsonBody(req, requestId);
    if (!parsed.ok) {
      return parsed.response;
    }

    const validated = validatePayload<UniswapBuildRequest>('uniswap-build-request.schema.json', parsed.body);
    if (!validated.ok) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Uniswap build payload does not match schema.',
          actionHint: 'Check required fields and quote object formatting.',
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

    if (!isUniswapEligibleChain(body.chainKey)) {
      return errorResponse(
        400,
        {
          code: 'unsupported_chain',
          message: `Chain '${body.chainKey}' is not enabled for Uniswap proxy execution.`,
          actionHint: 'Use a Uniswap-enabled chain or run legacy execution path.',
          details: { chainKey: body.chainKey },
        },
        requestId
      );
    }

    const built = await buildUniswap({
      chainKey: body.chainKey,
      walletAddress: body.walletAddress,
      quote: body.quote,
    });

    return successResponse(
      {
        ok: true,
        chainKey: body.chainKey,
        routeType: built.routeType,
        amountOutUnits: built.amountOutUnits,
        approvalTx: built.approvalTx,
        swapTx: built.swapTx,
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
