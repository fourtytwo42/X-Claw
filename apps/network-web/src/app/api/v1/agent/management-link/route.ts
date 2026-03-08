import type { NextRequest } from 'next/server';

import { requireAgentAuth } from '@/lib/agent-auth';
import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import { parseJsonBody } from '@/lib/http';
import { issueOwnerManagementLink } from '@/lib/management-service';
import { getRequestId } from '@/lib/request-id';
import { validatePayload } from '@/lib/validation';

export const runtime = 'nodejs';

type ManagementLinkRequest = {
  schemaVersion: number;
  agentId: string;
  ttlSeconds?: number;
};

function resolvePublicBaseUrl(req: NextRequest): string {
  const configured = process.env.XCLAW_PUBLIC_BASE_URL?.trim();
  if (configured) {
    return configured.replace(/\/+$/, '');
  }
  return req.nextUrl.origin.replace(/\/+$/, '');
}

export async function POST(req: NextRequest) {
  const requestId = getRequestId(req);

  try {
    const parsed = await parseJsonBody(req, requestId);
    if (!parsed.ok) {
      return parsed.response;
    }

    const validated = validatePayload<ManagementLinkRequest>('agent-management-link-request.schema.json', parsed.body);
    if (!validated.ok) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Owner management-link payload does not match schema.',
          actionHint: 'Provide schemaVersion, agentId, and optional ttlSeconds.',
          details: validated.details
        },
        requestId
      );
    }

    const body = validated.data;
    const auth = requireAgentAuth(req, body.agentId, requestId);
    if (!auth.ok) {
      return auth.response;
    }

    const issued = await issueOwnerManagementLink({
      agentId: body.agentId,
      ttlSeconds: body.ttlSeconds ?? 600
    });
    if (!issued.ok) {
      return errorResponse(issued.error.status, issued.error, requestId);
    }

    const origin = resolvePublicBaseUrl(req);
    const managementUrl = `${origin}/agents/${encodeURIComponent(body.agentId)}?token=${encodeURIComponent(issued.data.token)}`;
    return successResponse(
      {
        ok: true,
        agentId: body.agentId,
        managementUrl,
        issuedAt: issued.data.issuedAt,
        expiresAt: issued.data.expiresAt
      },
      200,
      requestId
    );
  } catch {
    return internalErrorResponse(requestId);
  }
}
