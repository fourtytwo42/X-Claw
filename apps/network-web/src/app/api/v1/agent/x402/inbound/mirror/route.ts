import type { NextRequest } from 'next/server';

import { authenticateAgentByToken } from '@/lib/agent-auth';
import { dbQuery } from '@/lib/db';
import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import { parseJsonBody } from '@/lib/http';
import { getRequestId } from '@/lib/request-id';
import { validatePayload } from '@/lib/validation';

export const runtime = 'nodejs';

type AgentX402InboundMirrorRequest = {
  schemaVersion: 1;
  paymentId: string;
  networkKey: string;
  facilitatorKey: string;
  status: 'proposed' | 'executing' | 'filled' | 'failed' | 'expired';
  assetKind: 'native' | 'token' | 'erc20';
  assetAddress?: string | null;
  assetSymbol?: string | null;
  amountAtomic: string;
  url: string;
  linkToken: string;
  expiresAt: string;
  txHash?: string | null;
  reasonCode?: string | null;
  reasonMessage?: string | null;
  createdAt: string;
  updatedAt: string;
  terminalAt?: string | null;
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

    const validated = validatePayload<AgentX402InboundMirrorRequest>('agent-x402-inbound-mirror-request.schema.json', parsed.body);
    if (!validated.ok) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'x402 inbound mirror payload does not match schema.',
          actionHint: 'Provide canonical x402 inbound mirror fields.',
          details: validated.details
        },
        requestId
      );
    }

    const body = validated.data;
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
        asset_symbol,
        amount_atomic,
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
        $1, $2, 'inbound', $3, $4, $5, $6, $7, $8, $9::numeric, $10, $11, $12::timestamptz, $13, $14, $15, $16::timestamptz, $17::timestamptz, $18::timestamptz
      )
      on conflict (payment_id)
      do update set
        status = excluded.status,
        network_key = excluded.network_key,
        facilitator_key = excluded.facilitator_key,
        asset_kind = excluded.asset_kind,
        asset_address = excluded.asset_address,
        asset_symbol = excluded.asset_symbol,
        amount_atomic = excluded.amount_atomic,
        payment_url = excluded.payment_url,
        link_token = excluded.link_token,
        expires_at = excluded.expires_at,
        tx_hash = excluded.tx_hash,
        reason_code = excluded.reason_code,
        reason_message = excluded.reason_message,
        updated_at = excluded.updated_at,
        terminal_at = excluded.terminal_at
      `,
      [
        body.paymentId,
        auth.agentId,
        body.status,
        body.networkKey,
        body.facilitatorKey,
        body.assetKind,
        body.assetAddress ?? null,
        body.assetSymbol ?? null,
        body.amountAtomic,
        body.url,
        body.linkToken,
        body.expiresAt,
        body.txHash ?? null,
        body.reasonCode ?? null,
        body.reasonMessage ?? null,
        body.createdAt,
        body.updatedAt,
        body.terminalAt ?? null
      ]
    );

    return successResponse({ ok: true, paymentId: body.paymentId, status: body.status, direction: 'inbound' }, 200, requestId);
  } catch {
    return internalErrorResponse(requestId);
  }
}
