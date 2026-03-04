import type { NextRequest } from 'next/server';

import { authenticateAgentByToken } from '@/lib/agent-auth';
import { internalErrorResponse, successResponse } from '@/lib/errors';
import { getRequestId } from '@/lib/request-id';
import { isWithdrawQueueStatus, readWithdrawRows } from '@/lib/withdraws-read';

export const runtime = 'nodejs';

export async function GET(req: NextRequest) {
  const requestId = getRequestId(req);
  try {
    const auth = authenticateAgentByToken(req, requestId);
    if (!auth.ok) {
      return auth.response;
    }

    const chainKey = String(req.nextUrl.searchParams.get('chainKey') ?? '').trim() || 'base_sepolia';
    const items = await readWithdrawRows(auth.agentId, chainKey, 200);

    return successResponse(
      {
        ok: true,
        agentId: auth.agentId,
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
