import type { NextRequest } from 'next/server';

import { authenticateAgentByToken } from '@/lib/agent-auth';
import { dbQuery } from '@/lib/db';
import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import { parseJsonBody } from '@/lib/http';
import { getRequestId } from '@/lib/request-id';
import { validatePayload } from '@/lib/validation';

export const runtime = 'nodejs';

type AgentTransferApprovalsMirrorRequest = {
  schemaVersion: 1;
  approvalId: string;
  chainKey: string;
  status: 'proposed' | 'approval_pending' | 'approved' | 'rejected' | 'executing' | 'filled' | 'failed';
  transferType: 'native' | 'token';
  tokenAddress?: string | null;
  tokenSymbol?: string | null;
  toAddress: string;
  amountWei: string;
  txHash?: string | null;
  reasonCode?: string | null;
  reasonMessage?: string | null;
  policyBlockedAtCreate?: boolean;
  policyBlockReasonCode?: 'outbound_disabled' | 'destination_not_whitelisted' | null;
  policyBlockReasonMessage?: string | null;
  executionMode?: 'normal' | 'policy_override' | null;
  createdAt: string;
  updatedAt: string;
  decidedAt?: string | null;
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

    const validated = validatePayload<AgentTransferApprovalsMirrorRequest>('agent-transfer-approvals-mirror-request.schema.json', parsed.body);
    if (!validated.ok) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Transfer approvals mirror payload does not match schema.',
          actionHint: 'Provide canonical transfer approval mirror fields.',
          details: validated.details
        },
        requestId
      );
    }

    const body = validated.data;
    await dbQuery(
      `
      insert into agent_transfer_approval_mirror (
        approval_id,
        agent_id,
        chain_key,
        status,
        transfer_type,
        token_address,
        token_symbol,
        to_address,
        amount_wei,
        tx_hash,
        reason_code,
        reason_message,
        policy_blocked_at_create,
        policy_block_reason_code,
        policy_block_reason_message,
        execution_mode,
        created_at,
        updated_at,
        decided_at,
        terminal_at
      ) values (
        $1, $2, $3, $4, $5, $6, $7, $8, $9::numeric, $10, $11, $12, $13, $14, $15, $16, $17::timestamptz, $18::timestamptz, $19::timestamptz, $20::timestamptz
      )
      on conflict (approval_id)
      do update set
        status = excluded.status,
        transfer_type = excluded.transfer_type,
        token_address = excluded.token_address,
        token_symbol = excluded.token_symbol,
        to_address = excluded.to_address,
        amount_wei = excluded.amount_wei,
        tx_hash = excluded.tx_hash,
        reason_code = excluded.reason_code,
        reason_message = excluded.reason_message,
        policy_blocked_at_create = excluded.policy_blocked_at_create,
        policy_block_reason_code = excluded.policy_block_reason_code,
        policy_block_reason_message = excluded.policy_block_reason_message,
        execution_mode = excluded.execution_mode,
        updated_at = excluded.updated_at,
        decided_at = excluded.decided_at,
        terminal_at = excluded.terminal_at
      `,
      [
        body.approvalId,
        auth.agentId,
        body.chainKey,
        body.status,
        body.transferType,
        body.tokenAddress ?? null,
        body.tokenSymbol ?? null,
        body.toAddress.toLowerCase(),
        body.amountWei,
        body.txHash ?? null,
        body.reasonCode ?? null,
        body.reasonMessage ?? null,
        Boolean(body.policyBlockedAtCreate),
        body.policyBlockReasonCode ?? null,
        body.policyBlockReasonMessage ?? null,
        body.executionMode ?? null,
        body.createdAt,
        body.updatedAt,
        body.decidedAt ?? null,
        body.terminalAt ?? null
      ]
    );

    return successResponse({ ok: true, approvalId: body.approvalId, status: body.status }, 200, requestId);
  } catch {
    return internalErrorResponse(requestId);
  }
}
