import type { NextRequest } from 'next/server';

import { authenticateAgentByToken } from '@/lib/agent-auth';
import { dbQuery } from '@/lib/db';
import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import { parseJsonBody } from '@/lib/http';
import { getRequestId } from '@/lib/request-id';
import { validatePayload } from '@/lib/validation';

export const runtime = 'nodejs';

type AgentX402OutboundMirrorRequest = {
  schemaVersion: 1;
  paymentId: string;
  approvalId: string;
  networkKey: string;
  facilitatorKey: string;
  status: 'proposed' | 'approval_pending' | 'approved' | 'executing' | 'filled' | 'failed' | 'rejected';
  assetKind: 'native' | 'token' | 'erc20';
  assetAddress?: string | null;
  assetSymbol?: string | null;
  amountAtomic: string;
  url: string;
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

    const validated = validatePayload<AgentX402OutboundMirrorRequest>('agent-x402-outbound-mirror-request.schema.json', parsed.body);
    if (!validated.ok) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'x402 outbound mirror payload does not match schema.',
          actionHint: 'Provide canonical x402 outbound mirror fields.',
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
        approval_id,
        tx_hash,
        reason_code,
        reason_message,
        created_at,
        updated_at,
        terminal_at
      ) values (
        $1, $2, 'outbound', $3, $4, $5, $6, $7, $8, $9::numeric, $10, $11, $12, $13, $14, $15::timestamptz, $16::timestamptz, $17::timestamptz
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
        approval_id = excluded.approval_id,
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
        body.approvalId,
        body.txHash ?? null,
        body.reasonCode ?? null,
        body.reasonMessage ?? null,
        body.createdAt,
        body.updatedAt,
        body.terminalAt ?? null
      ]
    );

    return successResponse({ ok: true, paymentId: body.paymentId, status: body.status, direction: 'outbound' }, 200, requestId);
  } catch {
    return internalErrorResponse(requestId);
  }
}
