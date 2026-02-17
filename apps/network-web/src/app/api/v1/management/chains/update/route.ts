import type { NextRequest } from 'next/server';

import { withTransaction } from '@/lib/db';
import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import { parseJsonBody } from '@/lib/http';
import { makeId } from '@/lib/ids';
import { requireManagementWriteAuth } from '@/lib/management-auth';
import { getRequestId } from '@/lib/request-id';
import { validatePayload } from '@/lib/validation';
import { getChainConfig } from '@/lib/chains';

export const runtime = 'nodejs';

type ManagementChainUpdateRequest = {
  agentId: string;
  chainKey: string;
  chainEnabled: boolean;
};

export async function POST(req: NextRequest) {
  const requestId = getRequestId(req);

  try {
    const parsed = await parseJsonBody(req, requestId);
    if (!parsed.ok) {
      return parsed.response;
    }

    const validated = validatePayload<ManagementChainUpdateRequest>('management-chain-update-request.schema.json', parsed.body);
    if (!validated.ok) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Chain update payload does not match schema.',
          actionHint: 'Provide agentId, chainKey, and chainEnabled.',
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

    const chainPolicyId = makeId('chn');

    const result = await withTransaction(async (client) => {
      await client.query(
        `
        insert into agent_chain_policies (
          chain_policy_id,
          agent_id,
          chain_key,
          chain_enabled,
          updated_by_management_session_id,
          created_at,
          updated_at
        ) values ($1, $2, $3, $4, $5, now(), now())
        on conflict (agent_id, chain_key) do update
          set chain_enabled = excluded.chain_enabled,
              updated_by_management_session_id = excluded.updated_by_management_session_id,
              updated_at = now()
        `,
        [chainPolicyId, body.agentId, body.chainKey, body.chainEnabled, auth.session.sessionId]
      );

      const row = await client.query<{ chain_enabled: boolean; updated_at: string }>(
        `
        select chain_enabled, updated_at::text
        from agent_chain_policies
        where agent_id = $1
          and chain_key = $2
        limit 1
        `,
        [body.agentId, body.chainKey]
      );
      return row.rows[0] ?? null;
    });

    return successResponse(
      {
        ok: true,
        agentId: body.agentId,
        chainKey: body.chainKey,
        chainEnabled: result?.chain_enabled ?? body.chainEnabled,
        updatedAt: result?.updated_at ?? null
      },
      200,
      requestId
    );
  } catch {
    return internalErrorResponse(requestId);
  }
}
