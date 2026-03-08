from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class X402RuntimeAdapter:
    require_json_flag: Callable[..., Any]
    fail: Callable[..., int]
    ok: Callable[..., int]
    emit: Callable[..., int]
    assert_chain_capability: Callable[..., Any]
    chain_supported_hint: Callable[..., str]
    ChainRegistryError: type[BaseException]
    WalletStoreError: type[BaseException]
    X402RuntimeError: type[BaseException]
    _api_request: Callable[..., Any]
    _api_error_details: Callable[..., dict[str, Any]]
    _execute_x402_settlement: Callable[..., Any]
    _mirror_x402_outbound: Callable[..., Any]
    x402_pay_create_or_execute: Callable[..., dict[str, Any]]
    x402_pay_resume: Callable[..., dict[str, Any]]
    x402_pay_decide: Callable[..., dict[str, Any]]
    x402_get_policy: Callable[..., dict[str, Any]]
    x402_set_policy: Callable[..., dict[str, Any]]
    x402_list_networks: Callable[..., dict[str, Any]]
    utc_now: Callable[..., str]
