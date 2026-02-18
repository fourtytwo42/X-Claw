import type { NextRequest } from 'next/server';

import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import type { ApiErrorCode } from '@/lib/errors';
import { parseJsonBody } from '@/lib/http';
import { getRequestId } from '@/lib/request-id';
import { validatePayload } from '@/lib/validation';
import { setCsrfCookie, setManagementCookie } from '@/lib/management-cookies';
import { bootstrapManagementSession, linkAgentToManagementSession } from '@/lib/management-service';
import { requireManagementSession } from '@/lib/management-auth';

export const runtime = 'nodejs';

type ManagementBootstrapRequest = {
  agentId: string;
  token: string;
};

function augmentBootstrapAuthError(input: { code: ApiErrorCode; message: string; actionHint?: string }) {
  if (input.code !== 'auth_invalid') {
    return input;
  }
  return {
    ...input,
    actionHint:
      'Owner links are one-time and host-scoped. Generate a fresh link and open it directly on https://xclaw.trade.'
  };
}

export async function POST(req: NextRequest) {
  const requestId = getRequestId(req);

  try {
    const parsed = await parseJsonBody(req, requestId);
    if (!parsed.ok) {
      return parsed.response;
    }

    const validated = validatePayload<ManagementBootstrapRequest>('management-bootstrap-request.schema.json', parsed.body);
    if (!validated.ok) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Management bootstrap payload does not match schema.',
          actionHint: 'Provide both agentId and bootstrap token.',
          details: validated.details
        },
        requestId
      );
    }

    const linkedSession = await requireManagementSession(req, requestId);
    if (linkedSession.ok) {
      const linked = await linkAgentToManagementSession({
        sessionId: linkedSession.session.sessionId,
        agentId: validated.data.agentId,
        token: validated.data.token,
        userAgent: req.headers.get('user-agent')
      });
      if (!linked.ok) {
        return errorResponse(linked.error.status, augmentBootstrapAuthError(linked.error), requestId);
      }

      return successResponse(
        {
          ok: true,
          agentId: linked.data.activeAgentId,
          linkedAgentId: linked.data.linkedAgentId,
          managedAgents: linked.data.managedAgents,
          session: {
            expiresAt: linkedSession.session.expiresAt
          }
        },
        200,
        requestId
      );
    }

    const result = await bootstrapManagementSession({
      agentId: validated.data.agentId,
      token: validated.data.token,
      userAgent: req.headers.get('user-agent')
    });

    if (!result.ok) {
      return errorResponse(result.error.status, augmentBootstrapAuthError(result.error), requestId);
    }

    const responseBody = {
      ok: true,
      agentId: result.data.agentId,
      session: {
        expiresAt: result.data.expiresAt
      }
    };

    const response = successResponse(responseBody, 200, requestId);
    setManagementCookie(response, req, result.data.managementCookieValue);
    setCsrfCookie(response, req, result.data.csrfToken);
    return response;
  } catch {
    return internalErrorResponse(requestId);
  }
}
