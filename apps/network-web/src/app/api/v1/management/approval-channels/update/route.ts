import type { NextRequest } from 'next/server';

import { withTransaction } from '@/lib/db';
import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import { parseJsonBody } from '@/lib/http';
import { makeId } from '@/lib/ids';
import { getChainConfig } from '@/lib/chains';
import { requireManagementWriteAuth } from '@/lib/management-auth';
import { getRequestId } from '@/lib/request-id';
import { validatePayload } from '@/lib/validation';

export const runtime = 'nodejs';

type ManagementApprovalChannelUpdateRequest = {
  agentId: string;
  chainKey: string;
  channel: 'telegram';
  enabled: boolean;
};

export async function POST(req: NextRequest) {
  const requestId = getRequestId(req);

  try {
    const parsed = await parseJsonBody(req, requestId);
    if (!parsed.ok) {
      return parsed.response;
    }

    const validated = validatePayload<ManagementApprovalChannelUpdateRequest>(
      'management-approval-channel-update-request.schema.json',
      parsed.body
    );
    if (!validated.ok) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Approval channel update payload does not match schema.',
          actionHint: 'Provide agentId, chainKey, channel, and enabled.',
          details: validated.details
        },
        requestId
      );
    }

    const body = validated.data;
    if (!getChainConfig(body.chainKey)) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Invalid chainKey value.',
          actionHint: 'Use a supported chain key (for example base_sepolia or kite_ai_testnet).',
          details: { chainKey: body.chainKey }
        },
        requestId
      );
    }

    const auth = await requireManagementWriteAuth(req, requestId, body.agentId);
    if (!auth.ok) {
      return auth.response;
    }

    const channelPolicyId = makeId('acp');

    const result = await withTransaction(async (client) => {
      await client.query(
        `
        insert into agent_chain_approval_channels (
          channel_policy_id,
          agent_id,
          chain_key,
          channel,
          enabled,
          secret_hash,
          created_by_management_session_id,
          created_at,
          updated_at
        ) values ($1, $2, $3, $4, $5, $6, $7, now(), now())
        on conflict (agent_id, chain_key, channel) do update
          set enabled = excluded.enabled,
              secret_hash = null,
              created_by_management_session_id = excluded.created_by_management_session_id,
              updated_at = now()
        `,
        [
          channelPolicyId,
          body.agentId,
          body.chainKey,
          body.channel,
          body.enabled,
          null,
          auth.session.sessionId
        ]
      );

      const row = await client.query<{ enabled: boolean; updated_at: string }>(
        `
        select enabled, updated_at::text
        from agent_chain_approval_channels
        where agent_id = $1
          and chain_key = $2
          and channel = $3
        limit 1
        `,
        [body.agentId, body.chainKey, body.channel]
      );
      return row.rows[0] ?? null;
    });

    return successResponse(
      {
        ok: true,
        agentId: body.agentId,
        chainKey: body.chainKey,
        channel: body.channel,
        enabled: result?.enabled ?? body.enabled,
        updatedAt: result?.updated_at ?? null
      },
      200,
      requestId
    );
  } catch {
    return internalErrorResponse(requestId);
  }
}
