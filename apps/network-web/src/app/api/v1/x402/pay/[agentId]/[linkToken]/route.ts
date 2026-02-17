import type { NextRequest } from 'next/server';

import { dbQuery } from '@/lib/db';
import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import { getRequestId } from '@/lib/request-id';

export const runtime = 'nodejs';

async function ensureX402ResourceDescriptionColumn(): Promise<void> {
  await dbQuery(`
    alter table if exists agent_x402_payment_mirror
    add column if not exists resource_description text
  `);
}

type RouteParams = {
  params: Promise<{ agentId: string; linkToken: string }>;
};

async function handle(req: NextRequest, params: { agentId: string; linkToken: string }) {
  const requestId = getRequestId(req);
  const { agentId, linkToken } = params;
  try {
    await ensureX402ResourceDescriptionColumn();
    const row = await dbQuery<{
      payment_id: string;
      status: string;
      network_key: string;
      facilitator_key: string;
      asset_kind: 'native' | 'erc20';
      asset_address: string | null;
      amount_atomic: string;
      payment_url: string | null;
      expires_at: string | null;
      resource_description: string | null;
      tx_hash: string | null;
    }>(
      `
      select
        payment_id,
        status::text,
        network_key,
        facilitator_key,
        asset_kind::text,
        asset_address,
        amount_atomic::text,
        payment_url,
        expires_at::text,
        resource_description,
        tx_hash
      from agent_x402_payment_mirror
      where agent_id = $1
        and direction = 'inbound'
        and link_token = $2
      order by created_at desc
      limit 1
      `,
      [agentId, linkToken]
    );

    if ((row.rowCount ?? 0) === 0) {
      return errorResponse(
        404,
        { code: 'payload_invalid', message: 'Unknown x402 payment link.', actionHint: 'Request a fresh payment link.' },
        requestId
      );
    }

    const payment = row.rows[0];
    const paymentHeader = req.headers.get('x-payment');
    if (!paymentHeader) {
      return errorResponse(
        402,
        {
          code: 'payment_required',
          message: 'x402 payment header required.',
          actionHint: 'Submit payment header and retry.',
          details: {
            paymentId: payment.payment_id,
            networkKey: payment.network_key,
            facilitatorKey: payment.facilitator_key,
            amountAtomic: payment.amount_atomic,
            requiredHeader: 'X-Payment',
            paymentUrl: payment.payment_url,
            expiresAt: payment.expires_at,
            resource: {
              description: payment.resource_description
            }
          }
        },
        requestId
      );
    }

    const txHashHeader = req.headers.get('x-tx-hash');
    const txHash = txHashHeader && /^0x[a-fA-F0-9]{64}$/.test(txHashHeader) ? txHashHeader : null;
    await dbQuery(
      `
      update agent_x402_payment_mirror
      set status = 'filled',
          tx_hash = coalesce($1, tx_hash),
          reason_code = null,
          reason_message = null,
          updated_at = now(),
          terminal_at = now()
      where payment_id = $2
      `,
      [txHash, payment.payment_id]
    );

    return successResponse(
      {
        ok: true,
        code: 'payment_settled',
        paymentId: payment.payment_id,
        networkKey: payment.network_key,
        facilitatorKey: payment.facilitator_key,
        amountAtomic: payment.amount_atomic,
        txHash
      },
      200,
      requestId
    );
  } catch {
    return internalErrorResponse(requestId);
  }
}

export async function GET(req: NextRequest, context: RouteParams) {
  const params = await context.params;
  return handle(req, params);
}

export async function POST(req: NextRequest, context: RouteParams) {
  const params = await context.params;
  return handle(req, params);
}
