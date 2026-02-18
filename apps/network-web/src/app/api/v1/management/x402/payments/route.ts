import type { NextRequest } from 'next/server';

import { dbQuery } from '@/lib/db';
import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import { requireManagementSession, sessionHasAgentAccess } from '@/lib/management-auth';
import { getRequestId } from '@/lib/request-id';

export const runtime = 'nodejs';

async function ensureX402ResourceDescriptionColumn(): Promise<void> {
  await dbQuery(`
    alter table if exists agent_x402_payment_mirror
    add column if not exists resource_description text
  `);
}

export async function GET(req: NextRequest) {
  const requestId = getRequestId(req);
  try {
    await ensureX402ResourceDescriptionColumn();
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
    if (!sessionHasAgentAccess(auth.session, agentId)) {
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
        payment_id: string;
        approval_id: string | null;
        direction: 'inbound' | 'outbound';
        status: string;
        network_key: string;
        facilitator_key: string;
        asset_kind: 'native' | 'erc20';
        asset_address: string | null;
        asset_symbol: string | null;
        amount_atomic: string;
        payment_url: string | null;
        link_token: string | null;
        tx_hash: string | null;
        reason_code: string | null;
        reason_message: string | null;
        resource_description: string | null;
        created_at: string;
        updated_at: string;
        terminal_at: string | null;
      }>(
        `
        select
          payment_id,
          approval_id,
          direction::text,
          status::text,
          network_key,
          facilitator_key,
          asset_kind::text,
          asset_address,
          asset_symbol,
          amount_atomic::text,
          payment_url,
          link_token,
          tx_hash,
          reason_code,
          reason_message,
          resource_description,
          created_at::text,
          updated_at::text,
          terminal_at::text
        from agent_x402_payment_mirror
        where agent_id = $1
          and network_key = $2
          and status in ('proposed', 'approval_pending', 'approved', 'executing')
        order by created_at asc
        limit 100
        `,
        [agentId, chainKey]
      ),
      dbQuery<{
        payment_id: string;
        approval_id: string | null;
        direction: 'inbound' | 'outbound';
        status: string;
        network_key: string;
        facilitator_key: string;
        asset_kind: 'native' | 'erc20';
        asset_address: string | null;
        asset_symbol: string | null;
        amount_atomic: string;
        payment_url: string | null;
        link_token: string | null;
        tx_hash: string | null;
        reason_code: string | null;
        reason_message: string | null;
        resource_description: string | null;
        created_at: string;
        updated_at: string;
        terminal_at: string | null;
      }>(
        `
        select
          payment_id,
          approval_id,
          direction::text,
          status::text,
          network_key,
          facilitator_key,
          asset_kind::text,
          asset_address,
          asset_symbol,
          amount_atomic::text,
          payment_url,
          link_token,
          tx_hash,
          reason_code,
          reason_message,
          resource_description,
          created_at::text,
          updated_at::text,
          terminal_at::text
        from agent_x402_payment_mirror
        where agent_id = $1
          and network_key = $2
        order by created_at desc
        limit 200
        `,
        [agentId, chainKey]
      )
    ]);

    return successResponse({ ok: true, agentId, chainKey, queue: queue.rows, history: history.rows }, 200, requestId);
  } catch {
    return internalErrorResponse(requestId);
  }
}
