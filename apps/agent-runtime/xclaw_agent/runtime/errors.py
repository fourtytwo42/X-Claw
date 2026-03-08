from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class RuntimeCommandFailure(Exception):
    code: str
    message: str
    action_hint: str | None = None
    details: dict[str, Any] = field(default_factory=dict)
    exit_code: int = 1

    def __post_init__(self) -> None:
        Exception.__init__(self, self.message)


def emit_failure(rt: Any, failure: RuntimeCommandFailure) -> int:
    return rt.fail(failure.code, failure.message, failure.action_hint, failure.details or None, exit_code=failure.exit_code)


def invalid_input(message: str, action_hint: str, details: dict[str, Any] | None = None, *, exit_code: int = 2) -> RuntimeCommandFailure:
    return RuntimeCommandFailure("invalid_input", message, action_hint, details or {}, exit_code)


def unsupported_mode(message: str, action_hint: str, details: dict[str, Any] | None = None, *, exit_code: int = 1) -> RuntimeCommandFailure:
    return RuntimeCommandFailure("unsupported_mode", message, action_hint, details or {}, exit_code)


def missing_dependency(message: str, dependency: str, *, exit_code: int = 1) -> RuntimeCommandFailure:
    return RuntimeCommandFailure(
        "missing_dependency",
        message,
        "Install the missing dependency and retry.",
        {"dependency": dependency},
        exit_code,
    )


def chain_config_invalid(message: str, chain: str, *, exit_code: int = 1) -> RuntimeCommandFailure:
    return RuntimeCommandFailure(
        "chain_config_invalid",
        message,
        "Repair config/chains/<chain>.json and retry.",
        {"chain": chain},
        exit_code,
    )


def chain_mismatch(trade_or_request_id: str, trade_chain: str, requested_chain: str, *, exit_code: int = 1) -> RuntimeCommandFailure:
    return RuntimeCommandFailure(
        "chain_mismatch",
        "Trade chain does not match command --chain.",
        "Use matching chain or refresh intent selection.",
        {"tradeId": trade_or_request_id, "tradeChain": trade_chain, "requestedChain": requested_chain},
        exit_code,
    )


def wallet_store_failure(
    rt: Any,
    exc: Exception,
    *,
    default_code: str,
    default_action_hint: str,
    chain: str,
    exit_code: int = 1,
    invalid_token_hint: str | None = None,
    invalid_token_details: dict[str, Any] | None = None,
    map_chain_config: bool = False,
) -> int:
    message = str(exc)
    if invalid_token_hint and "Unsupported token symbol" in message:
        return emit_failure(
            rt,
            invalid_input(
                message,
                invalid_token_hint,
                invalid_token_details or {"chain": chain},
                exit_code=2,
            ),
        )
    if "Missing dependency: cast" in message:
        return emit_failure(rt, missing_dependency(message, "cast", exit_code=1))
    if map_chain_config and "Chain config" in message:
        return emit_failure(rt, chain_config_invalid(message, chain, exit_code=1))
    return rt.fail(default_code, message, default_action_hint, {"chain": chain}, exit_code=exit_code)
