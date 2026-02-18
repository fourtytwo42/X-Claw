import type { NextRequest } from 'next/server';

import { internalErrorResponse, successResponse } from '@/lib/errors';
import { requireManagementSession } from '@/lib/management-auth';
import { getRequestId } from '@/lib/request-id';

export const runtime = 'nodejs';

export async function GET(req: NextRequest) {
  const requestId = getRequestId(req);

  try {
    const auth = await requireManagementSession(req, requestId);
    if (!auth.ok) {
      return auth.response;
    }

    return successResponse(
      {
        ok: true,
        managedAgents: auth.session.managedAgentIds,
        activeAgentId: auth.session.agentId
      },
      200,
      requestId
    );
  } catch {
    return internalErrorResponse(requestId);
  }
}
