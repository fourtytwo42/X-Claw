import type { NextRequest } from 'next/server';

import { requireAgentAuth } from '@/lib/agent-auth';
import { buildTradeViaRouter, EvmRouterExecutionError } from '@/lib/evm-router-execution';
import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import { parseJsonBody } from '@/lib/http';
import { getRequestId } from '@/lib/request-id';
import { validatePayload } from '@/lib/validation';

type TradeBuildRequest = {
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
    const validated = validatePayload<TradeBuildRequest>('trade-build-request.schema.json', parsed.body);
    if (!validated.ok) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Trade build payload does not match schema.',
          actionHint: 'Check required fields and quote formatting.',
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

    const built = await buildTradeViaRouter(body);
    return successResponse(
      {
        ok: true,
        chainKey: body.chainKey,
        routeKind: built.routeKind,
        amountOutUnits: built.amountOutUnits,
        approvalTx: built.approvalTx,
        swapTx: built.swapTx,
      },
      200,
      requestId,
    );
  } catch (error) {
    if (error instanceof EvmRouterExecutionError) {
      return errorResponse(
        error.status,
        {
          code: error.code as 'unsupported_chain',
          message: error.message,
          actionHint: 'Use an enabled EVM chain with a configured router adapter.',
          details: error.details,
        },
        requestId,
      );
    }
    return internalErrorResponse(requestId);
  }
}
