from __future__ import annotations

from typing import Any, Callable

from xclaw_agent.evm_action_executor import EvmActionExecutor
from xclaw_agent.liquidity_adapter import build_liquidity_adapter_for_request


def build_liquidity_add_plan(
    *,
    chain: str,
    dex: str,
    position_type: str,
    request: dict[str, Any],
    wallet_address: str,
    build_calldata: Callable[[str, list[object]], str],
):
    adapter = build_liquidity_adapter_for_request(chain=chain, dex=dex, position_type=position_type)
    return adapter.build_add_plan(request, wallet_address, build_calldata=build_calldata)


def build_liquidity_remove_plan(
    *,
    chain: str,
    dex: str,
    position_type: str,
    request: dict[str, Any],
    wallet_address: str,
    build_calldata: Callable[[str, list[object]], str],
):
    adapter = build_liquidity_adapter_for_request(chain=chain, dex=dex, position_type=position_type)
    return adapter.build_remove_plan(request, wallet_address, build_calldata=build_calldata)


def execute_liquidity_plan(
    *,
    executor: EvmActionExecutor,
    plan,
    wallet_address: str,
    private_key_hex: str,
    wait_for_operation_receipts: bool,
    liquidity_operation: str,
):
    return executor.execute_plan(
        plan,
        owner=wallet_address,
        private_key_hex=private_key_hex,
        wait_for_operation_receipts=wait_for_operation_receipts,
        liquidity_operation=liquidity_operation,
    )
