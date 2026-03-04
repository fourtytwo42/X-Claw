import type { NextRequest } from 'next/server';

import { dbQuery } from '@/lib/db';
import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import { makeId } from '@/lib/ids';
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
  params: Promise<{ agentId: string }>;
};

async function handle(req: NextRequest, params: { agentId: string }) {
  const requestId = getRequestId(req);
  const { agentId } = params;
  try {
    await ensureX402ResourceDescriptionColumn();
    const activeRows = await dbQuery<{
      payment_id: string;
      network_key: string;
      payment_url: string | null;
      link_token: string | null;
    }>(
      `
      select payment_id, network_key, payment_url, link_token
      from agent_x402_payment_mirror
      where agent_id = $1
        and direction = 'inbound'
        and status in ('proposed', 'executing')
      order by created_at desc
      limit 5
      `,
      [agentId]
    );

    if ((activeRows.rowCount ?? 0) > 1) {
      return errorResponse(
        409,
        {
          code: 'payload_invalid',
          message: 'Multiple active payment requests exist for this agent.',
          actionHint: 'Use the tokenized payment URL for the intended request.',
          details: {
            activePaymentIds: activeRows.rows.map((row) => row.payment_id),
            paymentUrls: activeRows.rows.map((row) => row.payment_url).filter(Boolean)
          }
        },
        requestId
      );
    }

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
        resource_description,
        tx_hash,
        recipient_address
      from agent_x402_payment_mirror
      where agent_id = $1
        and direction = 'inbound'
        and ($2::text = '' or payment_id = $2)
      order by
        case when status in ('proposed', 'executing') then 0 else 1 end asc,
        created_at desc
      limit 1
      `,
      [agentId, (activeRows.rows[0]?.payment_id ?? '').trim()]
    );

    if ((row.rowCount ?? 0) === 0) {
      return errorResponse(
        404,
        { code: 'payload_invalid', message: 'Unknown x402 payment link.', actionHint: 'Request the agent receive link first.' },
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
            expiresAt: null,
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

    const settledPaymentId = makeId('xpm');
    await dbQuery(
      `
      insert into agent_x402_payment_mirror (
        payment_id,
        agent_id,
        direction,
        status,
        network_key,
        facilitator_key,
        asset_kind,
        asset_address,
        amount_atomic,
        resource_description,
        payment_url,
        link_token,
        expires_at,
        tx_hash,
        reason_code,
        reason_message,
        created_at,
        updated_at,
        terminal_at
      ) values (
        $1, $2, 'inbound', 'filled', $3, $4, $5, $6, $7::numeric, $8, $9, null, null, $10, null, null, now(), now(), now()
      )
      `,
      [
        settledPaymentId,
        agentId,
        payment.network_key,
        payment.facilitator_key,
        payment.asset_kind,
        payment.asset_address,
        payment.amount_atomic,
        payment.resource_description,
        payment.payment_url,
        txId
      ]
    );

    return successResponse(
      {
        ok: true,
        code: 'payment_settled',
        paymentId: settledPaymentId,
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
