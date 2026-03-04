import type { NextRequest } from 'next/server';

import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import { requireManagementSession, sessionHasAgentAccess } from '@/lib/management-auth';
import { getRequestId } from '@/lib/request-id';
import { isWithdrawQueueStatus, readWithdrawRows } from '@/lib/withdraws-read';

export const runtime = 'nodejs';

export async function GET(req: NextRequest) {
  const requestId = getRequestId(req);
  try {
    const agentId = req.nextUrl.searchParams.get('agentId')?.trim();
    if (!agentId) {
      return errorResponse(
        400,
        { code: 'payload_invalid', message: 'agentId query parameter is required.', actionHint: 'Provide ?agentId=<agent-id>.' },
        requestId
      );
    }

    const auth = await requireManagementSession(req, requestId);
    if (!auth.ok) {
      return auth.response;
    }
    if (!sessionHasAgentAccess(auth.session, agentId)) {
      return errorResponse(
        401,
        {
          code: 'auth_invalid',
          message: 'Management session is not authorized for this agent.',
          actionHint: 'Use the matching agent management session.'
        },
        requestId
      );
    }

    const chainKey = req.nextUrl.searchParams.get('chainKey')?.trim() || 'base_sepolia';
    const items = await readWithdrawRows(agentId, chainKey, 200);

    return successResponse(
      {
        ok: true,
        agentId,
        chainKey,
        queue: items.filter((item) => isWithdrawQueueStatus(item.status)),
        history: items
      },
      200,
      requestId
    );
  } catch {
    return internalErrorResponse(requestId);
  }
}
