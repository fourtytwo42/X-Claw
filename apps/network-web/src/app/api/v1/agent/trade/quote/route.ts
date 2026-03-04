import type { NextRequest } from 'next/server';

import { requireAgentAuth } from '@/lib/agent-auth';
import { getChainConfig } from '@/lib/chains';
import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import { quoteTradeViaRouter, EvmRouterExecutionError } from '@/lib/evm-router-execution';
import { parseJsonBody } from '@/lib/http';
import { getRequestId } from '@/lib/request-id';
import { quoteTradeViaJupiter, SolanaJupiterExecutionError } from '@/lib/solana-jupiter-execution';
import { validatePayload } from '@/lib/validation';

type TradeQuoteRequest = {
  agentId: string;
  chainKey: string;
  walletAddress: string;
  tokenIn: string;
  tokenOut: string;
  amountInUnits: string;
  slippageBps: number;
  adapterKey?: string;
  protocolFamily?: string;
};

export const runtime = 'nodejs';

export async function POST(req: NextRequest) {
  const requestId = getRequestId(req);
  try {
    const parsed = await parseJsonBody(req, requestId);
    if (!parsed.ok) {
      return parsed.response;
    }
    const validated = validatePayload<TradeQuoteRequest>('trade-quote-request.schema.json', parsed.body);
    if (!validated.ok) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Trade quote payload does not match schema.',
          actionHint: 'Check required fields and address/amount formats.',
          details: validated.details,
        },
        requestId,
      );
    }
    const body = validated.data;
    const auth = requireAgentAuth(req, body.agentId, requestId);
    if (!auth.ok) {
      return auth.response;
    }

    const family = (getChainConfig(body.chainKey)?.family ?? 'evm') as string;
    const quoted =
      family === 'solana'
        ? await quoteTradeViaJupiter(body)
        : await quoteTradeViaRouter(body);
    return successResponse(
      {
        ok: true,
        chainKey: body.chainKey,
        routeKind: quoted.routeKind,
        amountOutUnits: quoted.amountOutUnits,
        quote: quoted.quote,
      },
      200,
      requestId,
    );
  } catch (error) {
    if (error instanceof EvmRouterExecutionError || error instanceof SolanaJupiterExecutionError) {
      return errorResponse(
        (error as EvmRouterExecutionError | SolanaJupiterExecutionError).status,
        {
          code: (error as EvmRouterExecutionError | SolanaJupiterExecutionError).code as 'unsupported_chain',
          message: (error as Error).message,
          actionHint: 'Use an enabled chain with a configured trade adapter.',
          details: (error as EvmRouterExecutionError | SolanaJupiterExecutionError).details,
        },
        requestId,
      );
    }
    return internalErrorResponse(requestId);
  }
}
