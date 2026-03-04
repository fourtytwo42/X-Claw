from __future__ import annotations

from typing import Any

from xclaw_agent.solana_raydium_planner import (
    build_execution_plan,
    execute_plan,
    quote_add as planner_quote_add,
    quote_remove as planner_quote_remove,
)
from xclaw_agent.solana_runtime import SolanaRuntimeError


def quote_add(amount_a: str, amount_b: str, slippage_bps: int, *, pool_id: str = "") -> dict[str, Any]:
    quote = planner_quote_add(amount_a=amount_a, amount_b=amount_b, slippage_bps=slippage_bps, pool_id=pool_id or "unknown")
    return {
        "amountA": quote.amount_a,
        "amountB": quote.amount_b,
        "minAmountA": quote.min_amount_a,
        "minAmountB": quote.min_amount_b,
        "slippageBps": quote.slippage_bps,
        "poolId": quote.pool_id,
    }


def quote_remove(percent: int, *, pool_id: str = "") -> dict[str, Any]:
    return planner_quote_remove(percent=percent, pool_id=pool_id or "unknown")


def execute_instruction(
    *,
    chain: str,
    rpc_url: str,
    private_key_bytes: bytes,
    owner: str,
    adapter_metadata: dict[str, Any],
    request: dict[str, Any],
    operation_key: str,
) -> Any:
    if operation_key not in {"add", "remove"}:
        raise SolanaRuntimeError("unsupported_liquidity_operation", f"Unsupported Raydium operation '{operation_key}'.")
    plan = build_execution_plan(
        chain=chain,
        rpc_url=rpc_url,
        owner=owner,
        adapter_metadata=adapter_metadata,
        request=request,
        operation_key=operation_key,
    )
    return execute_plan(
        chain=chain,
        rpc_url=rpc_url,
        private_key_bytes=private_key_bytes,
        plan=plan,
    )
