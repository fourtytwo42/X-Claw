import type { NextRequest } from 'next/server';

import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import { requireCsrfToken, requireManagementSession } from '@/lib/management-auth';
import { parseJsonBody } from '@/lib/http';
import { detachAgentFromManagementSession } from '@/lib/management-service';
import { getRequestId } from '@/lib/request-id';
import { validatePayload } from '@/lib/validation';

export const runtime = 'nodejs';

type ManagementSessionAgentDetachRequest = {
  agentId: string;
};

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

export async function DELETE(req: NextRequest) {
  const requestId = getRequestId(req);

  try {
    const auth = await requireManagementSession(req, requestId);
    if (!auth.ok) {
      return auth.response;
    }

    const csrf = requireCsrfToken(req, requestId);
    if (!csrf.ok) {
      return csrf.response;
    }

    const parsed = await parseJsonBody(req, requestId);
    if (!parsed.ok) {
      return parsed.response;
    }

    const validated = validatePayload<ManagementSessionAgentDetachRequest>(
      'management-session-agent-detach-request.schema.json',
      parsed.body
    );
    if (!validated.ok) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Session agent detach payload does not match schema.',
          actionHint: 'Provide a valid agentId.',
          details: validated.details
        },
        requestId
      );
    }

    const detached = await detachAgentFromManagementSession({
      sessionId: auth.session.sessionId,
      targetAgentId: validated.data.agentId,
      userAgent: req.headers.get('user-agent')
    });
    if (!detached.ok) {
      return errorResponse(detached.error.status, detached.error, requestId);
    }

    return successResponse(
      {
        ok: true,
        activeAgentId: detached.data.activeAgentId,
        detachedAgentId: detached.data.detachedAgentId,
        managedAgents: detached.data.managedAgents
      },
      200,
      requestId
    );
  } catch {
    return internalErrorResponse(requestId);
  }
}
