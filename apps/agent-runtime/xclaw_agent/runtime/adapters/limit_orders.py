from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class LimitOrdersRuntimeAdapter:
    require_json_flag: Callable[..., Any]
    fail: Callable[..., int]
    ok: Callable[..., int]
    emit: Callable[..., int]
    utc_now: Callable[..., str]
    WalletPolicyError: type[BaseException]
    WalletStoreError: type[BaseException]
    _resolve_token_address: Callable[..., str]
    _is_valid_limit_order_token: Callable[..., bool]
    _limit_order_token_format_hint: Callable[..., str]
    _resolve_api_key: Callable[..., str]
    _resolve_agent_id: Callable[..., str]
    _api_request: Callable[..., tuple[int, dict[str, Any]]]
    _api_error_details: Callable[..., dict[str, Any]]
    _sync_limit_orders: Callable[..., tuple[int, int]]
    load_limit_order_store: Callable[..., dict[str, Any]]
    load_limit_order_outbox: Callable[..., list[dict[str, Any]]]
    _replay_limit_order_outbox: Callable[..., tuple[int, int]]
    _replay_trade_usage_outbox: Callable[..., tuple[int, int]]
    _post_limit_order_status: Callable[..., Any]
    _quote_limit_order_price: Callable[..., Any]
    _limit_order_triggered: Callable[..., bool]
    _execute_limit_order_real: Callable[..., str]
