import type { NextRequest } from 'next/server';

import { dbQuery } from '@/lib/db';
import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import { parseJsonBody } from '@/lib/http';
import { makeId } from '@/lib/ids';
import { requireManagementWriteAuth } from '@/lib/management-auth';
import { getRequestId } from '@/lib/request-id';
import { validatePayload } from '@/lib/validation';

export const runtime = 'nodejs';

type ManagementTransferPolicyUpdateRequest = {
  agentId: string;
  chainKey: string;
  transferApprovalMode: 'auto' | 'per_transfer';
  nativeTransferPreapproved: boolean;
  allowedTransferTokens: string[];
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
    const parsed = await parseJsonBody(req, requestId);
    if (!parsed.ok) {
      return parsed.response;
    }

    const validated = validatePayload<ManagementTransferPolicyUpdateRequest>('management-transfer-policy-update-request.schema.json', parsed.body);
    if (!validated.ok) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Transfer policy update payload does not match schema.',
          actionHint: 'Provide agentId, chainKey, transferApprovalMode, nativeTransferPreapproved, allowedTransferTokens.',
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

    const tokens = normalizeTokens(body.allowedTransferTokens ?? []);
    const nowIso = new Date().toISOString();
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
      ) values ($1, $2, $3, $4, $5, $6::jsonb, $7, now(), $8::timestamptz)
      on conflict (agent_id, chain_key)
      do update set
        transfer_approval_mode = excluded.transfer_approval_mode,
        native_transfer_preapproved = excluded.native_transfer_preapproved,
        allowed_transfer_tokens = excluded.allowed_transfer_tokens,
        updated_by_management_session_id = excluded.updated_by_management_session_id,
        updated_at = excluded.updated_at
      `,
      [
        makeId('tpm'),
        body.agentId,
        body.chainKey,
        body.transferApprovalMode,
        body.nativeTransferPreapproved,
        JSON.stringify(tokens),
        auth.session.sessionId,
        nowIso
      ]
    );

    await dbQuery(
      `
      insert into management_audit_log (
        audit_id, agent_id, management_session_id, action_type, action_status,
        public_redacted_payload, private_payload, user_agent, created_at
      ) values ($1, $2, $3, 'transfer_policy.update', 'accepted', $4::jsonb, $5::jsonb, $6, now())
      `,
      [
        makeId('aud'),
        body.agentId,
        auth.session.sessionId,
        JSON.stringify({ chainKey: body.chainKey, transferApprovalMode: body.transferApprovalMode }),
        JSON.stringify({
          nativeTransferPreapproved: body.nativeTransferPreapproved,
          allowedTransferTokens: tokens
        }),
        req.headers.get('user-agent')
      ]
    );

    return successResponse(
      {
        ok: true,
        agentId: body.agentId,
        chainKey: body.chainKey,
        transferPolicy: {
          chainKey: body.chainKey,
          transferApprovalMode: body.transferApprovalMode,
          nativeTransferPreapproved: body.nativeTransferPreapproved,
          allowedTransferTokens: tokens,
          updatedAt: nowIso
        }
      },
      200,
      requestId
    );
  } catch {
    return internalErrorResponse(requestId);
  }
}
