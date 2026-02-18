import type { NextRequest } from 'next/server';

import { dbQuery } from '@/lib/db';
import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import { parseIntQuery } from '@/lib/http';
import { requireManagementSession, sessionHasAgentAccess } from '@/lib/management-auth';
import { getRequestId } from '@/lib/request-id';

export const runtime = 'nodejs';

export async function GET(req: NextRequest) {
  const requestId = getRequestId(req);

  try {
    const agentId = req.nextUrl.searchParams.get('agentId');
    if (!agentId) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'agentId query parameter is required.',
          actionHint: 'Provide ?agentId=<agent-id>.'
        },
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
          actionHint: 'Use the matching agent session for this route.'
        },
        requestId
      );
    }

    const limit = parseIntQuery(req.nextUrl.searchParams.get('limit'), 25, 1, 100);
    const offset = parseIntQuery(req.nextUrl.searchParams.get('offset'), 0, 0, 10000);

    const audit = await dbQuery<{
      audit_id: string;
      action_type: string;
      action_status: string;
      public_redacted_payload: Record<string, unknown>;
      created_at: string;
    }>(
      `
      select audit_id, action_type, action_status, public_redacted_payload, created_at::text
      from management_audit_log
      where agent_id = $1
      order by created_at desc
      limit $2
      offset $3
      `,
      [agentId, limit, offset]
    );

    return successResponse(
      {
        ok: true,
        items: audit.rows,
        paging: { limit, offset }
      },
      200,
      requestId
    );
  } catch {
    return internalErrorResponse(requestId);
  }
}
