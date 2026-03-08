from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class ExecutionContractContext:
    load_chain_config: Callable[[str], dict[str, Any]]


def provider_settings(ctx: ExecutionContractContext, chain: str, execution_kind: str) -> tuple[str, str]:
    cfg = ctx.load_chain_config(chain)
    execution = cfg.get("execution")
    if isinstance(execution, dict):
        family_cfg = execution.get(execution_kind)
        if isinstance(family_cfg, dict):
            default_provider = str(family_cfg.get("defaultProvider") or "").strip().lower()
            if default_provider in {"router_adapter", "quote_only", "none"}:
                return default_provider, "none"
    return "router_adapter", "none"


def fallback_reason(code: str, message: str) -> dict[str, str]:
    return {"code": code, "message": message[:500]}


def build_provider_meta(
    provider_requested: str,
    provider_used: str,
    fallback_used: bool,
    fallback_reason_value: dict[str, str] | None,
    route_kind: str | None,
) -> dict[str, Any]:
    normalized_requested = "router_adapter" if provider_requested in {"legacy_router", "uniswap_api"} else provider_requested
    normalized_used = "router_adapter" if provider_used in {"legacy_router", "uniswap_api"} else provider_used
    return {
        "providerRequested": normalized_requested,
        "providerUsed": normalized_used,
        "fallbackUsed": bool(fallback_used),
        "fallbackReason": fallback_reason_value if fallback_used and isinstance(fallback_reason_value, dict) else None,
        "routeKind": (str(route_kind or "").strip() or None),
    }


def build_liquidity_provider_meta(
    provider_requested: str,
    provider_used: str,
    fallback_used: bool,
    fallback_reason_value: dict[str, str] | None,
    liquidity_operation: str | None,
) -> dict[str, Any]:
    normalized_requested = "router_adapter" if provider_requested in {"legacy_router", "uniswap_api"} else provider_requested
    normalized_used = "router_adapter" if provider_used in {"legacy_router", "uniswap_api"} else provider_used
    return {
        "providerRequested": normalized_requested,
        "providerUsed": normalized_used,
        "fallbackUsed": bool(fallback_used),
        "fallbackReason": fallback_reason_value if fallback_used and isinstance(fallback_reason_value, dict) else None,
        "liquidityOperation": (str(liquidity_operation or "").strip().lower() or None),
    }
