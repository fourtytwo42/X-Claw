import type { NextRequest } from 'next/server';

import { requireAgentAuth } from '@/lib/agent-auth';
import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import { parseJsonBody } from '@/lib/http';
import { getRequestId } from '@/lib/request-id';
import { quoteUniswap, UniswapProxyError, isUniswapEligibleChain } from '@/lib/uniswap-proxy';
import { validatePayload } from '@/lib/validation';

type UniswapQuoteRequest = {
  agentId: string;
  chainKey: string;
  walletAddress: string;
  tokenIn: string;
  tokenOut: string;
  amountInUnits: string;
  slippageBps: number;
};

export const runtime = 'nodejs';

export async function POST(req: NextRequest) {
  const requestId = getRequestId(req);
  try {
    const parsed = await parseJsonBody(req, requestId);
    if (!parsed.ok) {
      return parsed.response;
    }

    const validated = validatePayload<UniswapQuoteRequest>('uniswap-quote-request.schema.json', parsed.body);
    if (!validated.ok) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Uniswap quote payload does not match schema.',
          actionHint: 'Check required fields and address/amount formats.',
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

    const quoted = await quoteUniswap({
      chainKey: body.chainKey,
      walletAddress: body.walletAddress,
      tokenIn: body.tokenIn,
      tokenOut: body.tokenOut,
      amountInUnits: body.amountInUnits,
      slippageBps: body.slippageBps,
    });

    return successResponse(
      {
        ok: true,
        chainKey: body.chainKey,
        routeType: quoted.routeType,
        amountOutUnits: quoted.amountOutUnits,
        quote: quoted.rawQuote,
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
