import type { NextRequest } from 'next/server';

import { authenticateAgentByToken } from '@/lib/agent-auth';
import { dbQuery } from '@/lib/db';
import { internalErrorResponse, successResponse } from '@/lib/errors';
import { getRequestId } from '@/lib/request-id';

export const runtime = 'nodejs';

export async function GET(req: NextRequest) {
  const requestId = getRequestId(req);
  try {
    const auth = authenticateAgentByToken(req, requestId);
    if (!auth.ok) {
      return auth.response;
    }

    const chainKey = req.nextUrl.searchParams.get('chainKey')?.trim() || 'base_sepolia';
    const row = await dbQuery<{
      transfer_approval_mode: 'auto' | 'per_transfer';
      native_transfer_preapproved: boolean;
      allowed_transfer_tokens: unknown;
      updated_at: string;
    }>(
      `
      select
        transfer_approval_mode::text,
        native_transfer_preapproved,
        allowed_transfer_tokens,
        updated_at::text
      from agent_transfer_policy_mirror
      where agent_id = $1
        and chain_key = $2
      limit 1
      `,
      [auth.agentId, chainKey]
    );

    const payload =
      (row.rowCount ?? 0) > 0
        ? {
            chainKey,
            transferApprovalMode: row.rows[0].transfer_approval_mode,
            nativeTransferPreapproved: Boolean(row.rows[0].native_transfer_preapproved),
            allowedTransferTokens: Array.isArray(row.rows[0].allowed_transfer_tokens) ? row.rows[0].allowed_transfer_tokens : [],
            updatedAt: row.rows[0].updated_at
          }
        : {
            chainKey,
            transferApprovalMode: 'per_transfer',
            nativeTransferPreapproved: false,
            allowedTransferTokens: [],
            updatedAt: new Date().toISOString()
          };

    return successResponse({ ok: true, agentId: auth.agentId, chainKey, transferPolicy: payload }, 200, requestId);
  } catch {
    return internalErrorResponse(requestId);
  }
}
