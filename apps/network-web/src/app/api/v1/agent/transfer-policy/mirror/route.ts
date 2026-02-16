import type { NextRequest } from 'next/server';

import { authenticateAgentByToken } from '@/lib/agent-auth';
import { dbQuery } from '@/lib/db';
import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import { parseJsonBody } from '@/lib/http';
import { makeId } from '@/lib/ids';
import { getRequestId } from '@/lib/request-id';
import { validatePayload } from '@/lib/validation';

export const runtime = 'nodejs';

type AgentTransferPolicyMirrorRequest = {
  agentId: string;
  chainKey: string;
  transferPolicy: {
    chainKey: string;
    transferApprovalMode: 'auto' | 'per_transfer';
    nativeTransferPreapproved: boolean;
    allowedTransferTokens: string[];
    updatedAt: string;
  };
};

function normalizeTokens(values: string[]): string[] {
  const out = new Set<string>();
  for (const token of values) {
    const normalized = String(token || '').trim().toLowerCase();
    if (/^0x[a-f0-9]{40}$/.test(normalized)) {
      out.add(normalized);
    }
  }
  return [...out];
}

export async function POST(req: NextRequest) {
  const requestId = getRequestId(req);
  try {
    const auth = authenticateAgentByToken(req, requestId);
    if (!auth.ok) {
      return auth.response;
    }

    const parsed = await parseJsonBody(req, requestId);
    if (!parsed.ok) {
      return parsed.response;
    }

    const validated = validatePayload<AgentTransferPolicyMirrorRequest>('agent-transfer-policy-mirror-request.schema.json', parsed.body);
    if (!validated.ok) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Transfer policy mirror payload does not match schema.',
          actionHint: 'Provide agentId, chainKey, and transferPolicy.',
          details: validated.details
        },
        requestId
      );
    }

    const body = validated.data;
    if (body.agentId !== auth.agentId) {
      return errorResponse(
        401,
        { code: 'auth_invalid', message: 'agentId does not match authenticated agent.', actionHint: 'Use the authenticated agentId.' },
        requestId
      );
    }

    const tokens = normalizeTokens(body.transferPolicy.allowedTransferTokens ?? []);
    await dbQuery(
      `
      insert into agent_transfer_policy_mirror (
        policy_id,
        agent_id,
        chain_key,
        transfer_approval_mode,
        native_transfer_preapproved,
        allowed_transfer_tokens,
        updated_by_management_session_id,
        created_at,
        updated_at
      ) values ($1, $2, $3, $4, $5, $6::jsonb, null, now(), $7::timestamptz)
      on conflict (agent_id, chain_key)
      do update set
        transfer_approval_mode = excluded.transfer_approval_mode,
        native_transfer_preapproved = excluded.native_transfer_preapproved,
        allowed_transfer_tokens = excluded.allowed_transfer_tokens,
        updated_at = excluded.updated_at
      `,
      [
        makeId('tpm'),
        auth.agentId,
        body.chainKey,
        body.transferPolicy.transferApprovalMode,
        body.transferPolicy.nativeTransferPreapproved,
        JSON.stringify(tokens),
        body.transferPolicy.updatedAt
      ]
    );

    return successResponse(
      {
        ok: true,
        agentId: auth.agentId,
        chainKey: body.chainKey,
        transferPolicy: {
          chainKey: body.chainKey,
          transferApprovalMode: body.transferPolicy.transferApprovalMode,
          nativeTransferPreapproved: body.transferPolicy.nativeTransferPreapproved,
          allowedTransferTokens: tokens,
          updatedAt: body.transferPolicy.updatedAt
        }
      },
      200,
      requestId
    );
  } catch {
    return internalErrorResponse(requestId);
  }
}
