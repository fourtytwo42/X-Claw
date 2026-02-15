import type { NextRequest } from 'next/server';

import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import { parseJsonBody } from '@/lib/http';
import { requireManagementWriteAuth } from '@/lib/management-auth';
import { clearAllManagementCookies } from '@/lib/management-cookies';
import { revokeAllAndRotateManagementToken } from '@/lib/management-service';
import { getRequestId } from '@/lib/request-id';
import { validatePayload } from '@/lib/validation';

export const runtime = 'nodejs';

type AgentScopedRequest = {
  agentId: string;
};

export async function POST(req: NextRequest) {
  const requestId = getRequestId(req);

  try {
    const parsed = await parseJsonBody(req, requestId);
    if (!parsed.ok) {
      return parsed.response;
    }

    const validated = validatePayload<AgentScopedRequest>('agent-scoped-request.schema.json', parsed.body);
    if (!validated.ok) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Agent-scoped management payload does not match schema.',
          actionHint: 'Provide a valid agentId in request body.',
          details: validated.details
        },
        requestId
      );
    }

    const auth = await requireManagementWriteAuth(req, requestId, validated.data.agentId);
    if (!auth.ok) {
      return auth.response;
    }

    const result = await revokeAllAndRotateManagementToken({
      agentId: validated.data.agentId,
      managementSessionId: auth.session.sessionId,
      userAgent: req.headers.get('user-agent')
    });

    if (!result.ok) {
      return errorResponse(result.error.status, result.error, requestId);
    }

    const response = successResponse(
      {
        ok: true,
        agentId: result.data.agentId,
        revokedManagementSessions: result.data.revokedManagementSessions,
        newManagementToken: result.data.newManagementToken
      },
      200,
      requestId
    );

    clearAllManagementCookies(response, req);
    return response;
  } catch {
    return internalErrorResponse(requestId);
  }
}
