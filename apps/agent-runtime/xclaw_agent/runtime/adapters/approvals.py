from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class ApprovalsRuntimeAdapter:
    require_json_flag: Callable[..., Any]
    fail: Callable[..., int]
    ok: Callable[..., int]
    emit: Callable[..., int]
    json: Any
    sys: Any
    re: Any
    utc_now: Callable[..., str]
    APPROVAL_RUN_LOOP_INTERVAL_MS: int
    APPROVAL_RUN_LOOP_BACKOFF_MAX_MS: int
    WalletStoreError: type[BaseException]
    X402RuntimeError: type[BaseException]
    _load_approval_prompts: Callable[..., dict[str, Any]]
    _read_trade_details: Callable[..., dict[str, Any]]
    _maybe_delete_telegram_approval_prompt: Callable[..., Any]
    _fetch_transfer_decision_inbox: Callable[..., list[dict[str, Any]]]
    _ack_transfer_decision_inbox: Callable[..., tuple[int, dict[str, Any]]]
    _run_decide_transfer_inline: Callable[..., tuple[int, dict[str, Any]]]
    _run_approvals_sync_inline: Callable[..., tuple[int, dict[str, Any]]]
    _run_resume_spot_inline: Callable[..., tuple[int, dict[str, Any]]]
    _runtime_wallet_signing_readiness: Callable[..., dict[str, Any]]
    _publish_runtime_signing_readiness: Callable[..., tuple[int, dict[str, Any]]]
    _clear_telegram_approval_buttons: Callable[..., dict[str, Any]]
    _cleanup_trade_approval_prompt: Callable[..., dict[str, Any]]
    _cleanup_transfer_approval_prompt: Callable[..., dict[str, Any]]
    _cleanup_policy_approval_prompt: Callable[..., dict[str, Any]]
    _get_pending_spot_trade_flow: Callable[..., dict[str, Any] | None]
    _remove_pending_spot_trade_flow: Callable[..., Any]
    _get_pending_transfer_flow: Callable[..., dict[str, Any] | None]
    _is_stale_executing_transfer_flow: Callable[..., bool]
    _record_pending_transfer_flow: Callable[..., Any]
    _mirror_transfer_approval: Callable[..., Any]
    _execute_pending_transfer_flow: Callable[..., dict[str, Any]]
    _post_trade_status: Callable[..., Any]
    _post_liquidity_status: Callable[..., Any]
    _read_liquidity_intent: Callable[..., dict[str, Any]]
    _run_liquidity_execute_inline: Callable[..., tuple[int, dict[str, Any]]]
    cmd_approvals_sync: Callable[..., int]
    cmd_approvals_resume_spot: Callable[..., int]
    cmd_approvals_decide_transfer: Callable[..., int]
    cmd_trade_execute: Callable[..., int]
    _maybe_send_telegram_decision_message: Callable[..., Any]
    _maybe_send_telegram_trade_terminal_message: Callable[..., Any]
    _maybe_send_telegram_policy_approval_prompt: Callable[..., Any]
    _normalize_address: Callable[..., str]
    _resolve_token_address: Callable[..., str]
    _transfer_amount_display: Callable[..., tuple[str, str]]
    _native_symbol_for_chain: Callable[..., str]
    _native_decimals_for_chain: Callable[..., int]
    _is_solana_chain: Callable[..., bool]
    is_solana_address: Callable[..., bool]
    is_hex_address: Callable[..., bool]
    _api_request: Callable[..., tuple[int, dict[str, Any]]]
    x402_state: Any
    x402_pay_resume: Callable[..., dict[str, Any]]
    x402_pay_decide: Callable[..., dict[str, Any]]
    _mirror_x402_outbound: Callable[..., Any]
