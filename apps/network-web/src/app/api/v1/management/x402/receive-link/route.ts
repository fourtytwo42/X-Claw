import type { NextRequest } from 'next/server';

import { dbQuery } from '@/lib/db';
import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import { parseJsonBody } from '@/lib/http';
import { requireManagementSession, requireManagementWriteAuth } from '@/lib/management-auth';
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
    const facilitatorKey = req.nextUrl.searchParams.get('facilitatorKey')?.trim() || 'cdp';
    const active = await dbQuery<{
      payment_id: string;
      network_key: string;
      facilitator_key: string;
      asset_kind: 'native' | 'erc20';
      asset_address: string | null;
      asset_symbol: string | null;
      amount_atomic: string;
      payment_url: string | null;
      link_token: string | null;
      status: string;
      terminal_at: string | null;
      created_at: string;
      updated_at: string;
      resource_description: string | null;
    }>(
      `
      select
        payment_id,
        network_key,
        facilitator_key,
        asset_kind::text,
        asset_address,
        asset_symbol,
        amount_atomic::text,
        payment_url,
        link_token,
        status::text,
        terminal_at::text,
        created_at::text,
        updated_at::text,
        resource_description
      from agent_x402_payment_mirror
      where agent_id = $1
        and direction = 'inbound'
        and network_key = $2
        and status in ('proposed', 'executing')
      order by created_at desc
      limit 1
      `,
      [agentId, chainKey]
    );
    if ((active.rowCount ?? 0) === 0) {
      return successResponse(
        {
          ok: true,
          agentId,
          chainKey,
          paymentId: '',
          networkKey: chainKey,
          facilitatorKey,
          assetKind: 'native',
          assetAddress: null,
          assetSymbol: chainKey === 'kite_ai_testnet' ? 'KITE' : 'ETH',
          amountAtomic: '0',
          paymentUrl: '',
          resourceDescription: null,
          ttlSeconds: null,
          expiresAt: null,
          timeLimitNotice: 'No active receive requests.',
          status: 'unavailable'
        },
        200,
        requestId
      );
    }

    const paymentId = active.rows[0].payment_id;
    const paymentUrl = active.rows[0].payment_url ?? '';
    const status = active.rows[0].status;
    const resourceDescription = active.rows[0].resource_description;
    const assetKind = active.rows[0].asset_kind;
    const assetAddress = active.rows[0].asset_address;
    const assetSymbol = (active.rows[0].asset_symbol ?? (chainKey === 'kite_ai_testnet' ? 'KITE' : 'ETH')) as
      | 'ETH'
      | 'KITE'
      | 'USDC'
      | 'WETH'
      | 'WKITE'
      | 'USDT';
    const amountAtomic = active.rows[0].amount_atomic;

    return successResponse(
      {
        ok: true,
        agentId,
        chainKey,
        paymentId,
        networkKey: chainKey,
        facilitatorKey,
        assetKind,
        assetAddress,
        assetSymbol,
        amountAtomic,
        paymentUrl,
        resourceDescription,
        ttlSeconds: null,
        expiresAt: null,
        timeLimitNotice: 'This payment link does not expire.',
        status
      },
      200,
      requestId
    );
  } catch {
    return internalErrorResponse(requestId);
  }
}

type DeleteReceiveRequestBody = {
  agentId?: string;
  paymentId?: string;
};

export async function POST(req: NextRequest) {
  const requestId = getRequestId(req);
  try {
    return errorResponse(
      403,
      {
        code: 'payload_invalid',
        message: 'x402 receive requests can only be created by the agent runtime.',
        actionHint: 'Use agent x402 commands to create receive requests.'
      },
      requestId
    );
  } catch {
    return internalErrorResponse(requestId);
  }
}

export async function DELETE(req: NextRequest) {
  const requestId = getRequestId(req);
  try {
    await ensureX402ResourceDescriptionColumn();
    const parsed = await parseJsonBody(req, requestId);
    if (!parsed.ok) {
      return parsed.response;
    }
    const body = (parsed.body ?? {}) as DeleteReceiveRequestBody;
    const agentId = String(body.agentId ?? '').trim();
    const paymentId = String(body.paymentId ?? '').trim();
    if (!agentId || !paymentId) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'agentId and paymentId are required.',
          actionHint: 'Provide both agentId and paymentId in request body.'
        },
        requestId
      );
    }

    const auth = await requireManagementWriteAuth(req, requestId, agentId);
    if (!auth.ok) {
      return auth.response;
    }

    const updated = await dbQuery(
      `
      update agent_x402_payment_mirror
      set
        status = 'expired',
        reason_code = 'request_deleted',
        reason_message = 'Deleted by owner.',
        updated_at = now(),
        terminal_at = now()
      where payment_id = $1
        and agent_id = $2
        and direction = 'inbound'
        and status in ('proposed', 'executing')
      returning payment_id
      `,
      [paymentId, agentId]
    );

    if ((updated.rowCount ?? 0) === 0) {
      return errorResponse(
        404,
        {
          code: 'payload_invalid',
          message: 'Active x402 receive request not found.',
          actionHint: 'Refresh receive requests and retry.'
        },
        requestId
      );
    }

    return successResponse(
      {
        ok: true,
        agentId,
        paymentId,
        status: 'expired',
        message: 'x402 receive request removed from active queue.'
      },
      200,
      requestId
    );
  } catch {
    return internalErrorResponse(requestId);
  }
}
