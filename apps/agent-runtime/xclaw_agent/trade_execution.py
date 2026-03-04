from __future__ import annotations

from typing import Any, Callable

from xclaw_agent.dex_adapter import TradeAdapterResolutionError, build_trade_execution_adapter
from xclaw_agent.evm_action_executor import EvmActionExecutor


def quote_trade(
    *,
    chain: str,
    adapter_key: str,
    request: dict[str, Any],
    get_amount_out: Callable[[str, str, str], int],
) -> dict[str, Any]:
    adapter = build_trade_execution_adapter(chain=chain, adapter_key=adapter_key)
    return adapter.quote(request, get_amount_out=get_amount_out)


def build_trade_plan(
    *,
    chain: str,
    adapter_key: str,
    request: dict[str, Any],
    wallet_address: str,
    build_calldata: Callable[[str, list[object]], str],
):
    adapter = build_trade_execution_adapter(chain=chain, adapter_key=adapter_key)
    return adapter.build_action_plan(request, wallet_address, build_calldata=build_calldata)


def execute_trade_plan(
    *,
    executor: EvmActionExecutor,
    plan,
    wallet_address: str,
    private_key_hex: str,
    wait_for_operation_receipts: bool,
):
    return executor.execute_plan(
        plan,
        owner=wallet_address,
        private_key_hex=private_key_hex,
        wait_for_operation_receipts=wait_for_operation_receipts,
    )


__all__ = [
    "TradeAdapterResolutionError",
    "build_trade_plan",
    "execute_trade_plan",
    "quote_trade",
]
