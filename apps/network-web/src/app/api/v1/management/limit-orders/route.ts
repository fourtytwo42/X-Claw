import type { NextRequest } from 'next/server';

import { dbQuery, withTransaction } from '@/lib/db';
import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import { parseIntQuery, parseJsonBody } from '@/lib/http';
import { makeId } from '@/lib/ids';
import { requireManagementSession, requireManagementWriteAuth, sessionHasAgentAccess } from '@/lib/management-auth';
import { getRequestId } from '@/lib/request-id';
import { validatePayload } from '@/lib/validation';

export const runtime = 'nodejs';

type CreateLimitOrderRequest = {
  agentId: string;
  chainKey: string;
  mode: 'mock' | 'real';
  side: 'buy' | 'sell';
  tokenIn: string;
  tokenOut: string;
  amountIn: string;
  limitPrice: string;
  slippageBps: number;
  expiresAt?: string;
};

export async function POST(req: NextRequest) {
  const requestId = getRequestId(req);

  try {
    const parsed = await parseJsonBody(req, requestId);
    if (!parsed.ok) {
      return parsed.response;
    }

    const validated = validatePayload<CreateLimitOrderRequest>('management-limit-order-create-request.schema.json', parsed.body);
    if (!validated.ok) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Limit-order create payload does not match schema.',
          actionHint: 'Provide valid fields for chain, side, pair, amount, and limit price.',
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

    const orderId = makeId('lmt');

    await withTransaction(async (client) => {
      await client.query(
        `
        insert into limit_orders (
          order_id, agent_id, chain_key, mode, side, token_in, token_out,
          amount_in, limit_price, slippage_bps, status, expires_at, trigger_source, created_at, updated_at
        ) values ($1, $2, $3, $4::policy_mode, $5::limit_order_side, $6, $7, $8, $9, $10, 'open', $11, 'management_api', now(), now())
        `,
        [
          orderId,
          body.agentId,
          body.chainKey,
          body.mode,
          body.side,
          body.tokenIn,
          body.tokenOut,
          body.amountIn,
          body.limitPrice,
          body.slippageBps,
          body.expiresAt ?? null
        ]
      );

      await client.query(
        `
        insert into management_audit_log (
          audit_id, agent_id, management_session_id, action_type, action_status,
          public_redacted_payload, private_payload, user_agent, created_at
        ) values ($1, $2, $3, 'limit_order.create', 'accepted', $4::jsonb, $5::jsonb, $6, now())
        `,
        [
          makeId('aud'),
          body.agentId,
          auth.session.sessionId,
          JSON.stringify({ orderId, chainKey: body.chainKey, side: body.side, tokenIn: body.tokenIn, tokenOut: body.tokenOut }),
          JSON.stringify(body),
          req.headers.get('user-agent')
        ]
      );
    });

    return successResponse({ ok: true, orderId, status: 'open' }, 200, requestId);
  } catch {
    return internalErrorResponse(requestId);
  }
}

export async function GET(req: NextRequest) {
  const requestId = getRequestId(req);

  try {
    const auth = await requireManagementSession(req, requestId);
    if (!auth.ok) {
      return auth.response;
    }

    const agentId = req.nextUrl.searchParams.get('agentId');
    if (!agentId) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'agentId query parameter is required.',
          actionHint: 'Provide ?agentId=<agent-id>.'
        },
        requestId
      );
    }

    if (!sessionHasAgentAccess(auth.session, agentId)) {
      return errorResponse(
        401,
        {
          code: 'auth_invalid',
          message: 'Management session is not authorized for this agent.',
          actionHint: 'Use the matching agent session for this route.'
        },
        requestId
      );
    }

    const status = req.nextUrl.searchParams.get('status')?.trim();
    const chainKey = req.nextUrl.searchParams.get('chainKey')?.trim();
    const limit = parseIntQuery(req.nextUrl.searchParams.get('limit'), 50, 1, 200);

    const params: unknown[] = [agentId];
    let where = 'where agent_id = $1';
    if (status) {
      params.push(status);
      where += ` and status = $${params.length}::limit_order_status`;
    }
    if (chainKey) {
      params.push(chainKey);
      where += ` and chain_key = $${params.length}`;
    }
    params.push(limit);

    const orders = await dbQuery<{
      order_id: string;
      agent_id: string;
      chain_key: string;
      mode: 'mock' | 'real';
      side: 'buy' | 'sell';
      token_in: string;
      token_out: string;
      amount_in: string;
      limit_price: string;
      slippage_bps: number;
      status: string;
      expires_at: string | null;
      cancelled_at: string | null;
      trigger_source: string;
      created_at: string;
      updated_at: string;
    }>(
      `
      select
        order_id,
        agent_id,
        chain_key,
        mode,
        side,
        token_in,
        token_out,
        amount_in::text,
        limit_price::text,
        slippage_bps,
        status::text,
        expires_at::text,
        cancelled_at::text,
        trigger_source::text,
        created_at::text,
        updated_at::text
      from limit_orders
      ${where}
      order by created_at desc
      limit $${params.length}
      `,
      params
    );

    return successResponse(
      {
        ok: true,
        agentId,
        items: orders.rows.map((row) => ({
          orderId: row.order_id,
          agentId: row.agent_id,
          chainKey: row.chain_key,
          mode: row.mode,
          side: row.side,
          tokenIn: row.token_in,
          tokenOut: row.token_out,
          amountIn: row.amount_in,
          limitPrice: row.limit_price,
          slippageBps: row.slippage_bps,
          status: row.status,
          expiresAt: row.expires_at,
          cancelledAt: row.cancelled_at,
          triggerSource: row.trigger_source,
          createdAt: row.created_at,
          updatedAt: row.updated_at
        }))
      },
      200,
      requestId
    );
  } catch {
    return internalErrorResponse(requestId);
  }
}
