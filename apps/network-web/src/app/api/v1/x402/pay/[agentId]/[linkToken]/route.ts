import type { NextRequest } from 'next/server';

import { dbQuery } from '@/lib/db';
import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import { getRequestId } from '@/lib/request-id';
import { verifyX402Settlement } from '@/lib/x402-verification';

export const runtime = 'nodejs';

async function ensureX402ResourceDescriptionColumn(): Promise<void> {
  await dbQuery(`
    alter table if exists agent_x402_payment_mirror
    add column if not exists resource_description text
  `);
  await dbQuery(`
    alter table if exists agent_x402_payment_mirror
    add column if not exists recipient_address varchar(128)
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
      asset_kind: 'native' | 'erc20' | 'token';
      asset_address: string | null;
      asset_symbol: string | null;
      amount_atomic: string;
      payment_url: string | null;
      expires_at: string | null;
      resource_description: string | null;
      tx_hash: string | null;
      recipient_address: string | null;
    }>(
      `
      select
        payment_id,
        status::text,
        network_key,
        facilitator_key,
        asset_kind::text,
        asset_address,
        asset_symbol,
        amount_atomic::text,
        payment_url,
        expires_at::text,
        resource_description,
        tx_hash,
        recipient_address
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
    const recipientLookup = await dbQuery<{ address: string }>(
      `
      select address
      from agent_wallets
      where agent_id = $1
        and chain_key = $2
      limit 1
      `,
      [agentId, payment.network_key]
    );
    const challengeRecipient = payment.recipient_address || recipientLookup.rows[0]?.address || null;

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
            assetKind: payment.asset_kind,
            assetAddress: payment.asset_address,
            assetSymbol: payment.asset_symbol,
            recipientAddress: challengeRecipient,
            requiredHeader: 'X-Payment',
            requiredTxHeader: 'X-Tx-Id',
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

    const txId = String(req.headers.get('x-tx-id') || req.headers.get('x-tx-hash') || '').trim();
    if (!txId) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'x402 settlement tx id is required.',
          actionHint: 'Provide X-Tx-Id (or compatibility X-Tx-Hash) and retry.'
        },
        requestId
      );
    }

    const expectedRecipient = challengeRecipient;

    const verification = await verifyX402Settlement({
      chainKey: payment.network_key,
      txId,
      expectedRecipient,
      expectedAssetKind: payment.asset_kind,
      expectedAssetAddress: payment.asset_address
    });
    if (!verification.ok) {
      return errorResponse(
        400,
        {
          code: verification.code,
          message: verification.message,
          actionHint: 'Submit a valid chain-confirmed settlement tx id and retry.',
          details: verification.details || null
        },
        requestId
      );
    }

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
      [txId, payment.payment_id]
    );

    return successResponse(
      {
        ok: true,
        code: 'payment_settled',
        paymentId: payment.payment_id,
        networkKey: payment.network_key,
        facilitatorKey: payment.facilitator_key,
        amountAtomic: payment.amount_atomic,
        txHash: txId
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
