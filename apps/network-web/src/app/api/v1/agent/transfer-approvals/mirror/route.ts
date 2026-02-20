import type { NextRequest } from 'next/server';

import { authenticateAgentByToken } from '@/lib/agent-auth';
import { dbQuery } from '@/lib/db';
import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import { parseJsonBody } from '@/lib/http';
import { getRequestId } from '@/lib/request-id';
import { isTransferMirrorSchemaUnavailableError, transferMirrorSchemaErrorDetails } from '@/lib/transfer-mirror-schema';
import { validatePayload } from '@/lib/validation';

export const runtime = 'nodejs';

type AgentTransferApprovalsMirrorRequest = {
  schemaVersion: 1;
  approvalId: string;
  chainKey: string;
  approvalSource?: 'transfer' | 'x402';
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
  x402Url?: string | null;
  x402NetworkKey?: string | null;
  x402FacilitatorKey?: string | null;
  x402AssetKind?: 'native' | 'erc20' | null;
  x402AssetAddress?: string | null;
  x402AmountAtomic?: string | null;
  x402PaymentId?: string | null;
  observedBy?: 'agent_watcher' | 'legacy_server_poller' | null;
  observationSource?: 'rpc_receipt' | 'rpc_log' | 'local_send_result' | 'reorg_reconciliation' | null;
  confirmationCount?: number | null;
  observedAt?: string | null;
  watcherRunId?: string | null;
  createdAt: string;
  updatedAt: string;
  decidedAt?: string | null;
  terminalAt?: string | null;
};

export async function POST(req: NextRequest) {
  const requestId = getRequestId(req);
  let requestApprovalId: string | null = null;
  let requestAgentId: string | null = null;
  let requestChainKey: string | null = null;
  try {
    const auth = authenticateAgentByToken(req, requestId);
    if (!auth.ok) {
      return auth.response;
    }
    requestAgentId = auth.agentId;

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
    requestApprovalId = body.approvalId;
    requestChainKey = body.chainKey;
    const prior = await dbQuery<{ status: string }>(
      `
      select status::text
      from agent_transfer_approval_mirror
      where approval_id = $1
        and agent_id = $2
      limit 1
      `,
      [body.approvalId, auth.agentId]
    );
    const priorStatus = (prior.rowCount ?? 0) > 0 ? String(prior.rows[0].status ?? '').trim().toLowerCase() : '';

    await dbQuery(
      `
      insert into agent_transfer_approval_mirror (
        approval_id,
        agent_id,
        chain_key,
        status,
        transfer_type,
        approval_source,
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
        x402_url,
        x402_network_key,
        x402_facilitator_key,
        x402_asset_kind,
        x402_asset_address,
        x402_amount_atomic,
        x402_payment_id,
        observed_by,
        observation_source,
        confirmation_count,
        observed_at,
        watcher_run_id,
        created_at,
        updated_at,
        decided_at,
        terminal_at
      ) values (
        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10::numeric, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23::numeric, $24, $25, $26, $27, $28::timestamptz, $29, $30::timestamptz, $31::timestamptz, $32::timestamptz, $33::timestamptz
      )
      on conflict (approval_id)
      do update set
        status = excluded.status,
        transfer_type = excluded.transfer_type,
        approval_source = excluded.approval_source,
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
        x402_url = excluded.x402_url,
        x402_network_key = excluded.x402_network_key,
        x402_facilitator_key = excluded.x402_facilitator_key,
        x402_asset_kind = excluded.x402_asset_kind,
        x402_asset_address = excluded.x402_asset_address,
        x402_amount_atomic = excluded.x402_amount_atomic,
        x402_payment_id = excluded.x402_payment_id,
        observed_by = excluded.observed_by,
        observation_source = excluded.observation_source,
        confirmation_count = excluded.confirmation_count,
        observed_at = excluded.observed_at,
        watcher_run_id = excluded.watcher_run_id,
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
        body.approvalSource ?? 'transfer',
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
        body.x402Url ?? null,
        body.x402NetworkKey ?? null,
        body.x402FacilitatorKey ?? null,
        body.x402AssetKind ?? null,
        body.x402AssetAddress ?? null,
        body.x402AmountAtomic ?? null,
        body.x402PaymentId ?? null,
        body.observedBy ?? null,
        body.observationSource ?? null,
        body.confirmationCount ?? null,
        body.observedAt ?? null,
        body.watcherRunId ?? null,
        body.createdAt,
        body.updatedAt,
        body.decidedAt ?? null,
        body.terminalAt ?? null
      ]
    );

    return successResponse(
      {
        ok: true,
        approvalId: body.approvalId,
        status: body.status,
        priorStatus,
        agentProdTerminal: {
          attempted: false,
          skipped: true,
          reason: 'agent_canonical_terminal_delivery'
        }
      },
      200,
      requestId
    );
  } catch (error) {
    const schemaUnavailable = isTransferMirrorSchemaUnavailableError(error);
    const { dbCode, dbMessage } = transferMirrorSchemaErrorDetails(error);
    console.error('[agent/transfer-approvals/mirror] write failed', {
      requestId,
      approvalId: requestApprovalId,
      agentId: requestAgentId,
      chainKey: requestChainKey,
      schemaUnavailable,
      dbCode,
      dbMessage
    });
    if (schemaUnavailable) {
      return errorResponse(
        503,
        {
          code: 'transfer_mirror_unavailable',
          message: 'Transfer approval mirror storage is unavailable.',
          actionHint: 'Run DB parity/migrations for transfer mirror tables and retry.',
          details: {
            approvalId: requestApprovalId,
            chainKey: requestChainKey,
            dbCode
          }
        },
        requestId
      );
    }
    return internalErrorResponse(requestId);
  }
}
