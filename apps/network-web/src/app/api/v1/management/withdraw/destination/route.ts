import type { NextRequest } from 'next/server';

import { withTransaction } from '@/lib/db';
import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import { parseJsonBody } from '@/lib/http';
import { makeId } from '@/lib/ids';
import { requireManagementWriteAuth } from '@/lib/management-auth';
import { getRequestId } from '@/lib/request-id';
import { validatePayload } from '@/lib/validation';

export const runtime = 'nodejs';

type WithdrawDestinationRequest = {
  agentId: string;
  chainKey: string;
  destination: string;
};

function redactAddress(address: string): string {
  return `${address.slice(0, 6)}...${address.slice(-4)}`;
}

export async function POST(req: NextRequest) {
  const requestId = getRequestId(req);

  try {
    const parsed = await parseJsonBody(req, requestId);
    if (!parsed.ok) {
      return parsed.response;
    }

    const validated = validatePayload<WithdrawDestinationRequest>('management-withdraw-destination-request.schema.json', parsed.body);
    if (!validated.ok) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Withdraw destination payload does not match schema.',
          actionHint: 'Provide agentId, chainKey, and destination address.',
          details: validated.details
        },
        requestId
      );
    }

    const body = validated.data;
    const auth = await requireManagementWriteAuth(req, requestId, body.agentId);
    if (!auth.ok) {
      return auth.response;
    }

    await withTransaction(async (client) => {
      await client.query(
        `
        update agents
        set openclaw_metadata = jsonb_set(
          coalesce(openclaw_metadata, '{}'::jsonb),
          $2::text[],
          to_jsonb($3::text),
          true
        ),
        updated_at = now()
        where agent_id = $1
        `,
        [body.agentId, ['management', 'withdrawDestinations', body.chainKey], body.destination]
      );

      await client.query(
        `
        insert into management_audit_log (
          audit_id, agent_id, management_session_id, action_type, action_status,
          public_redacted_payload, private_payload, user_agent, created_at
        ) values ($1, $2, $3, 'withdraw.destination', 'accepted', $4::jsonb, $5::jsonb, $6, now())
        `,
        [
          makeId('aud'),
          body.agentId,
          auth.session.sessionId,
          JSON.stringify({ chainKey: body.chainKey, destination: redactAddress(body.destination) }),
          JSON.stringify({ destination: body.destination }),
          req.headers.get('user-agent')
        ]
      );
    });

    return successResponse({ ok: true, chainKey: body.chainKey, destination: body.destination }, 200, requestId);
  } catch {
    return internalErrorResponse(requestId);
  }
}
