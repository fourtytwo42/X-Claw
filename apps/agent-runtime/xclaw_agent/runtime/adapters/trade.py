from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class TradeRuntimeAdapter:
    require_json_flag: Callable[..., Any]
    fail: Callable[..., int]
    ok: Callable[..., int]
    json: Any
    re: Any
    utc_now: Callable[..., str]
    load_wallet_store: Callable[..., dict[str, Any]]
    MAX_TRADE_RETRIES: int
    RETRY_WINDOW_SEC: int
    is_hex_address: Callable[..., bool]
    WalletPolicyError: type[BaseException]
    WalletStoreError: type[BaseException]
    _trade_provider_settings: Callable[..., Any]
    _is_solana_chain: Callable[..., bool]
    _resolve_token_address: Callable[..., str]
    _enforce_spend_preconditions: Callable[..., Any]
    _normalize_amount_human_text: Callable[..., str]
    _solana_mint_decimals: Callable[..., int]
    _format_units: Callable[..., str]
    _replay_trade_usage_outbox: Callable[..., Any]
    _fetch_erc20_metadata: Callable[..., dict[str, Any]]
    _parse_amount_in_units: Callable[..., tuple[str, str]]
    _quote_trade_via_router_adapter: Callable[..., dict[str, Any]]
    _to_non_negative_decimal: Callable[..., Any]
    _projected_trade_spend_usd: Callable[..., Any]
    _enforce_trade_caps: Callable[..., Any]
    _trade_intent_key: Callable[..., str]
    _get_pending_trade_intent: Callable[..., dict[str, Any] | None]
    _read_trade_details: Callable[..., dict[str, Any]]
    _record_pending_spot_trade_flow: Callable[..., Any]
    _wait_for_trade_approval: Callable[..., Any]
    _remove_pending_trade_intent: Callable[..., Any]
    _post_trade_proposed: Callable[..., dict[str, Any]]
    _record_pending_trade_intent: Callable[..., Any]
    _require_cast_bin: Callable[..., str]
    _chain_rpc_url: Callable[..., str]
    _execution_wallet: Callable[..., tuple[str, str]]
    _execution_wallet_secret: Callable[..., tuple[str, bytes, str]]
    _execute_trade_via_router_adapter: Callable[..., dict[str, Any]]
    solana_jupiter_quote: Callable[..., Any]
    solana_jupiter_execute_swap: Callable[..., dict[str, Any]]
    resolve_trade_execution_adapter: Callable[..., Any]
    _build_provider_meta: Callable[..., dict[str, Any]]
    _post_trade_status: Callable[..., Any]
    _run_subprocess: Callable[..., Any]
    _cast_receipt_timeout_sec: Callable[..., int]
    _record_spend: Callable[..., Any]
    _record_trade_cap_ledger: Callable[..., Any]
    _post_trade_usage: Callable[..., Any]
    _builder_output_from_hashes: Callable[..., dict[str, Any]]
    _format_units_pretty: Callable[..., str]
    _decimal_text: Callable[..., str]
    _to_units_uint: Callable[..., str]
    _remove_pending_spot_trade_flow: Callable[..., Any]
