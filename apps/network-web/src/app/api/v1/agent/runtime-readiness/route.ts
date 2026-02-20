import type { NextRequest } from 'next/server';

import { authenticateAgentByToken } from '@/lib/agent-auth';
import { dbQuery } from '@/lib/db';
import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import { parseJsonBody } from '@/lib/http';
import { getRequestId } from '@/lib/request-id';
import { validatePayload } from '@/lib/validation';

export const runtime = 'nodejs';

type AgentRuntimeReadinessRequest = {
  schemaVersion: 1;
  chainKey: string;
  walletSigningReady: boolean;
  walletSigningReasonCode?: string | null;
  walletSigningCheckedAt?: string | null;
};

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

    const validated = validatePayload<AgentRuntimeReadinessRequest>('agent-runtime-readiness-request.schema.json', parsed.body);
    if (!validated.ok) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Runtime readiness payload does not match schema.',
          actionHint: 'Provide chainKey and walletSigning readiness fields.',
          details: validated.details,
        },
        requestId
      );
    }

    const body = validated.data;
    const chainKey = String(body.chainKey ?? '').trim();
    if (!chainKey) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'chainKey is required.',
          actionHint: 'Provide a non-empty chainKey.',
        },
        requestId
      );
    }

    const chainReadiness = {
      walletSigningReady: Boolean(body.walletSigningReady),
      walletSigningReasonCode: String(body.walletSigningReasonCode ?? '').trim() || null,
      walletSigningCheckedAt: body.walletSigningCheckedAt ?? null,
      updatedAt: new Date().toISOString(),
    };

    await dbQuery(
      `
      update agents
      set openclaw_metadata = jsonb_set(
            coalesce(openclaw_metadata, '{}'::jsonb),
            array['runtimeReadiness', 'chains', $1::text],
            $2::jsonb,
            true
          ),
          updated_at = now()
      where agent_id = $3
      `,
      [chainKey, JSON.stringify(chainReadiness), auth.agentId]
    );

    return successResponse(
      {
        ok: true,
        agentId: auth.agentId,
        chainKey,
        runtimeReadiness: chainReadiness,
      },
      200,
      requestId
    );
  } catch {
    return internalErrorResponse(requestId);
  }
}
