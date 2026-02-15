import type { NextRequest } from 'next/server';

import { withTransaction } from '@/lib/db';
import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import { parseJsonBody } from '@/lib/http';
import { makeId } from '@/lib/ids';
import { requireManagementWriteAuth } from '@/lib/management-auth';
import { getRequestId } from '@/lib/request-id';
import { validatePayload } from '@/lib/validation';

export const runtime = 'nodejs';

type WithdrawRequest = {
  agentId: string;
  chainKey: string;
  asset: string;
  amount: string;
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

    const validated = validatePayload<WithdrawRequest>('management-withdraw-request.schema.json', parsed.body);
    if (!validated.ok) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Withdraw payload does not match schema.',
          actionHint: 'Provide agentId, chainKey, asset, amount, and destination.',
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

    const withdrawRequestId = makeId('wdr');

    await withTransaction(async (client) => {
      await client.query(
        `
        insert into management_audit_log (
          audit_id, agent_id, management_session_id, action_type, action_status,
          public_redacted_payload, private_payload, user_agent, created_at
        ) values ($1, $2, $3, 'withdraw.request', 'accepted', $4::jsonb, $5::jsonb, $6, now())
        `,
        [
          makeId('aud'),
          body.agentId,
          auth.session.sessionId,
          JSON.stringify({
            withdrawRequestId,
            chainKey: body.chainKey,
            asset: body.asset,
            amount: body.amount,
            destination: redactAddress(body.destination)
          }),
          JSON.stringify(body),
          req.headers.get('user-agent')
        ]
      );
    });

    return successResponse(
      {
        ok: true,
        withdrawRequestId,
        status: 'accepted'
      },
      200,
      requestId
    );
  } catch {
    return internalErrorResponse(requestId);
  }
}
