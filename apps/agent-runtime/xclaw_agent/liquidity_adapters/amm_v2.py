from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from xclaw_agent.execution_contracts import ApprovalRequirement, EvmActionPlan, EvmCall


@dataclass(frozen=True)
class AmmV2LiquidityExecutionAdapter:
    chain: str
    adapter_key: str
    router: str
    factory: str
    quoter: str

    def build_add_plan(
        self,
        request: dict[str, Any],
        wallet_address: str,
        *,
        build_calldata: Callable[[str, list[object]], str],
    ) -> EvmActionPlan:
        token_a = str(request.get("tokenA") or "").strip()
        token_b = str(request.get("tokenB") or "").strip()
        amount_a_units = str(request.get("amountAUnits") or "").strip()
        amount_b_units = str(request.get("amountBUnits") or "").strip()
        min_a_units = str(request.get("minAmountAUnits") or "").strip()
        min_b_units = str(request.get("minAmountBUnits") or "").strip()
        deadline = str(request.get("deadline") or "").strip()
        calldata = build_calldata(
            "addLiquidity(address,address,uint256,uint256,uint256,uint256,address,uint256)(uint256,uint256,uint256)",
            [token_a, token_b, amount_a_units, amount_b_units, min_a_units, min_b_units, wallet_address, deadline],
        )
        return EvmActionPlan(
            operation_kind="liquidity_add_v2",
            chain=self.chain,
            execution_family="amm_v2",
            execution_adapter=self.adapter_key,
            route_kind="direct_pair",
            approvals=[
                ApprovalRequirement(token=token_a, spender=self.router, required_units=int(amount_a_units)),
                ApprovalRequirement(token=token_b, spender=self.router, required_units=int(amount_b_units)),
            ],
            calls=[EvmCall(to=self.router, data=calldata, value_wei="0", label="add_liquidity_v2")],
            details={
                "tokenA": token_a.lower(),
                "tokenB": token_b.lower(),
                "amountAUnits": amount_a_units,
                "amountBUnits": amount_b_units,
                "minAmountAUnits": min_a_units,
                "minAmountBUnits": min_b_units,
            },
        )

    def build_remove_plan(
        self,
        request: dict[str, Any],
        wallet_address: str,
        *,
        build_calldata: Callable[[str, list[object]], str],
    ) -> EvmActionPlan:
        token_a = str(request.get("tokenA") or "").strip()
        token_b = str(request.get("tokenB") or "").strip()
        lp_token = str(request.get("lpToken") or "").strip()
        liquidity_units = str(request.get("liquidityUnits") or "").strip()
        min_a_units = str(request.get("minAmountAUnits") or "").strip()
        min_b_units = str(request.get("minAmountBUnits") or "").strip()
        deadline = str(request.get("deadline") or "").strip()
        calldata = build_calldata(
            "removeLiquidity(address,address,uint256,uint256,uint256,address,uint256)(uint256,uint256)",
            [token_a, token_b, liquidity_units, min_a_units, min_b_units, wallet_address, deadline],
        )
        return EvmActionPlan(
            operation_kind="liquidity_remove_v2",
            chain=self.chain,
            execution_family="amm_v2",
            execution_adapter=self.adapter_key,
            route_kind="direct_pair",
            approvals=[
                ApprovalRequirement(token=lp_token, spender=self.router, required_units=int(liquidity_units))
            ],
            calls=[EvmCall(to=self.router, data=calldata, value_wei="0", label="remove_liquidity_v2")],
            details={
                "tokenA": token_a.lower(),
                "tokenB": token_b.lower(),
                "lpToken": lp_token.lower(),
                "liquidityUnits": liquidity_units,
                "minAmountAUnits": min_a_units,
                "minAmountBUnits": min_b_units,
            },
        )
