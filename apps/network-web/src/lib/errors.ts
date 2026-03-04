import { NextResponse } from 'next/server';

export type ApiErrorCode =
  | 'auth_invalid'
  | 'auth_expired'
  | 'csrf_invalid'
  | 'rate_limited'
  | 'approval_required'
  | 'approval_expired'
  | 'approval_rejected'
  | 'payment_required'
  | 'payment_expired'
  | 'not_actionable'
  | 'policy_denied'
  | 'daily_usd_cap_exceeded'
  | 'daily_trade_count_cap_exceeded'
  | 'chain_disabled'
  | 'chain_mismatch'
  | 'rpc_unavailable'
  | 'unsupported_chain_capability'
  | 'trade_invalid_transition'
  | 'liquidity_invalid_transition'
  | 'unsupported_chain'
  | 'unsupported_execution_adapter'
  | 'unsupported_liquidity_operation'
  | 'x402_settlement_proof_invalid'
  | 'transfer_mirror_unavailable'
  | 'runtime_signing_unavailable'
  | 'token_resolution_failed'
  | 'withdraw_queue_failed'
  | 'faucet_config_invalid'
  | 'faucet_fee_too_low_for_chain'
  | 'faucet_native_insufficient'
  | 'faucet_recipient_not_eligible'
  | 'faucet_wrapped_insufficient'
  | 'faucet_wrapped_autowrap_failed'
  | 'faucet_stable_insufficient'
  | 'faucet_send_preflight_failed'
  | 'faucet_rpc_unavailable'
  | 'idempotency_conflict'
  | 'payload_invalid'
  | 'internal_error';

export type ApiErrorPayload = {
  code: ApiErrorCode;
  message: string;
  requestId: string;
  actionHint?: string;
  details?: unknown;
};

export function errorResponse(
  status: number,
  payload: Omit<ApiErrorPayload, 'requestId'>,
  requestId: string,
  headers?: Record<string, string>
): NextResponse<ApiErrorPayload> {
  return NextResponse.json(
    {
      code: payload.code,
      message: payload.message,
      actionHint: payload.actionHint,
      details: payload.details,
      requestId
    },
    { status, headers: { 'x-request-id': requestId, ...(headers ?? {}) } }
  );
}

export function internalErrorResponse(requestId: string, details?: unknown): NextResponse<ApiErrorPayload> {
  return errorResponse(
    500,
    {
      code: 'internal_error',
      message: 'An unexpected server error occurred.',
      actionHint: 'Retry once. If the issue persists, check server logs with requestId.',
      details
    },
    requestId
  );
}

export function successResponse<T>(payload: T, status: number, requestId: string): NextResponse<T> {
  return NextResponse.json(payload, { status, headers: { 'x-request-id': requestId } });
}
