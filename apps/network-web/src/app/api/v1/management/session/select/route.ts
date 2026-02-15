import type { NextRequest } from 'next/server';

import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import { parseJsonBody } from '@/lib/http';
import { setCsrfCookie, setManagementCookie } from '@/lib/management-cookies';
import { bootstrapManagementSession } from '@/lib/management-service';
import { getRequestId } from '@/lib/request-id';
import { validatePayload } from '@/lib/validation';

export const runtime = 'nodejs';

type SessionSelectRequest = {
  agentId: string;
  token: string;
};

export async function POST(req: NextRequest) {
  const requestId = getRequestId(req);

  try {
    const parsed = await parseJsonBody(req, requestId);
    if (!parsed.ok) {
      return parsed.response;
    }

    const validated = validatePayload<SessionSelectRequest>('management-session-select-request.schema.json', parsed.body);
    if (!validated.ok) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Session select payload does not match schema.',
          actionHint: 'Provide agentId and token.',
          details: validated.details
        },
        requestId
      );
    }

    const result = await bootstrapManagementSession({
      agentId: validated.data.agentId,
      token: validated.data.token,
      userAgent: req.headers.get('user-agent')
    });

    if (!result.ok) {
      return errorResponse(result.error.status, result.error, requestId);
    }

    const response = successResponse(
      {
        ok: true,
        activeAgentId: result.data.agentId,
        session: { expiresAt: result.data.expiresAt }
      },
      200,
      requestId
    );

    setManagementCookie(response, req, result.data.managementCookieValue);
    setCsrfCookie(response, req, result.data.csrfToken);

    return response;
  } catch {
    return internalErrorResponse(requestId);
  }
}
