import type { NextRequest } from 'next/server';

import { dbQuery } from '@/lib/db';
import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import { requireManagementSession } from '@/lib/management-auth';
import { getRequestId } from '@/lib/request-id';

export const runtime = 'nodejs';

export async function GET(req: NextRequest) {
  const requestId = getRequestId(req);
  try {
    const agentId = req.nextUrl.searchParams.get('agentId')?.trim();
    if (!agentId) {
      return errorResponse(
        400,
        { code: 'payload_invalid', message: 'agentId query parameter is required.', actionHint: 'Provide ?agentId=<agent-id>.' },
        requestId
      );
    }

    const auth = await requireManagementSession(req, requestId);
    if (!auth.ok) {
      return auth.response;
    }
    if (auth.session.agentId !== agentId) {
      return errorResponse(
        401,
        {
          code: 'auth_invalid',
          message: 'Management session is not authorized for this agent.',
          actionHint: 'Use the matching agent management session.'
        },
        requestId
      );
    }

    const chainKey = req.nextUrl.searchParams.get('chainKey')?.trim() || 'base_sepolia';
    const [queue, history] = await Promise.all([
      dbQuery<{
        approval_id: string;
        chain_key: string;
        status: string;
        transfer_type: 'native' | 'token';
        token_address: string | null;
        token_symbol: string | null;
        to_address: string;
        amount_wei: string;
        policy_blocked_at_create: boolean;
        policy_block_reason_code: string | null;
        policy_block_reason_message: string | null;
        execution_mode: 'normal' | 'policy_override' | null;
        created_at: string;
      }>(
        `
        select
          approval_id,
          chain_key,
          status::text,
          transfer_type::text,
          token_address,
          token_symbol,
          to_address,
          amount_wei::text,
          policy_blocked_at_create,
          policy_block_reason_code,
          policy_block_reason_message,
          execution_mode,
          created_at::text
        from agent_transfer_approval_mirror
        where agent_id = $1
          and chain_key = $2
          and status = 'approval_pending'
        order by created_at asc
        limit 100
        `,
        [agentId, chainKey]
      ),
      dbQuery<{
        approval_id: string;
        chain_key: string;
        status: string;
        transfer_type: 'native' | 'token';
        token_address: string | null;
        token_symbol: string | null;
        to_address: string;
        amount_wei: string;
        tx_hash: string | null;
        reason_message: string | null;
        policy_blocked_at_create: boolean;
        policy_block_reason_code: string | null;
        policy_block_reason_message: string | null;
        execution_mode: 'normal' | 'policy_override' | null;
        created_at: string;
        decided_at: string | null;
        terminal_at: string | null;
      }>(
        `
        select
          approval_id,
          chain_key,
          status::text,
          transfer_type::text,
          token_address,
          token_symbol,
          to_address,
          amount_wei::text,
          tx_hash,
          reason_message,
          policy_blocked_at_create,
          policy_block_reason_code,
          policy_block_reason_message,
          execution_mode,
          created_at::text,
          decided_at::text,
          terminal_at::text
        from agent_transfer_approval_mirror
        where agent_id = $1
          and chain_key = $2
        order by created_at desc
        limit 100
        `,
        [agentId, chainKey]
      )
    ]);

    return successResponse(
      {
        ok: true,
        agentId,
        chainKey,
        queue: queue.rows,
        history: history.rows
      },
      200,
      requestId
    );
  } catch {
    return internalErrorResponse(requestId);
  }
}
