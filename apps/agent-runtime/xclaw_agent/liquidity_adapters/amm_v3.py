from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from xclaw_agent.execution_contracts import ApprovalRequirement, EvmActionPlan, EvmCall

MAX_UINT128 = str((1 << 128) - 1)


def _tuple_text(values: list[object]) -> str:
    return "(" + ",".join(str(value) for value in values) + ")"


def _list_text(values: list[object]) -> str:
    return "[" + ",".join(str(value) for value in values) + "]"


@dataclass(frozen=True)
class AmmV3LiquidityExecutionAdapter:
    chain: str
    adapter_key: str
    router: str
    factory: str
    quoter: str
    position_manager: str
    capabilities: dict[str, bool]
    operations: dict[str, dict[str, Any]]

    def _require_position_manager(self) -> str:
        position_manager = str(self.position_manager or "").strip()
        if not position_manager:
            raise ValueError("chain_config_invalid")
        return position_manager

    def supports_operation(self, operation: str) -> bool:
        op = str(operation or "").strip().lower()
        if not op:
            return False
        if op in {"claim_fees", "claim-fees"}:
            return bool(self.capabilities.get("claimFees"))
        if op in {"claim_rewards", "claim-rewards"}:
            return bool(self.capabilities.get("claimRewards"))
        return bool(self.capabilities.get(op))

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
        fee = str(request.get("fee") or "").strip()
        tick_lower = str(request.get("tickLower") or "").strip()
        tick_upper = str(request.get("tickUpper") or "").strip()
        deadline = str(request.get("deadline") or "").strip()
        position_manager = self._require_position_manager()
        mint_method = str((self.operations.get("add") or {}).get("method") or "mint").strip() or "mint"
        mint_params = _tuple_text(
            [
                token_a,
                token_b,
                fee,
                tick_lower,
                tick_upper,
                amount_a_units,
                amount_b_units,
                min_a_units,
                min_b_units,
                wallet_address,
                deadline,
            ]
        )
        calldata = build_calldata(
            f"{mint_method}((address,address,uint24,int24,int24,uint256,uint256,uint256,uint256,address,uint256))",
            [mint_params],
        )
        return EvmActionPlan(
            operation_kind="liquidity_add_v3",
            chain=self.chain,
            execution_family="position_manager_v3",
            execution_adapter=self.adapter_key,
            route_kind="position_manager",
            approvals=[
                ApprovalRequirement(token=token_a, spender=position_manager, required_units=int(amount_a_units)),
                ApprovalRequirement(token=token_b, spender=position_manager, required_units=int(amount_b_units)),
            ],
            calls=[EvmCall(to=position_manager, data=calldata, value_wei="0", label="add_liquidity_v3")],
            details={
                "tokenA": token_a.lower(),
                "tokenB": token_b.lower(),
                "amountAUnits": amount_a_units,
                "amountBUnits": amount_b_units,
                "minAmountAUnits": min_a_units,
                "minAmountBUnits": min_b_units,
                "fee": fee,
                "tickLower": tick_lower,
                "tickUpper": tick_upper,
                "deadline": deadline,
            },
        )

    def build_remove_plan(
        self,
        request: dict[str, Any],
        wallet_address: str,
        *,
        build_calldata: Callable[[str, list[object]], str],
    ) -> EvmActionPlan:
        position_id = str(request.get("positionId") or request.get("positionRef") or "").strip()
        position_manager = self._require_position_manager()
        liquidity_units = str(request.get("liquidityUnits") or "").strip()
        min_a_units = str(request.get("minAmountAUnits") or "").strip()
        min_b_units = str(request.get("minAmountBUnits") or "").strip()
        deadline = str(request.get("deadline") or "").strip()
        decrease_method = str((self.operations.get("decrease") or {}).get("method") or "decreaseLiquidity").strip() or "decreaseLiquidity"
        collect_method = str((self.operations.get("claimFees") or {}).get("method") or "collect").strip() or "collect"
        decrease_params = _tuple_text([position_id, liquidity_units, min_a_units, min_b_units, deadline])
        collect_params = _tuple_text([position_id, wallet_address, MAX_UINT128, MAX_UINT128])
        decrease_calldata = build_calldata(
            f"{decrease_method}((uint256,uint128,uint256,uint256,uint256))",
            [decrease_params],
        )
        collect_calldata = build_calldata(
            f"{collect_method}((uint256,address,uint128,uint128))",
            [collect_params],
        )
        return EvmActionPlan(
            operation_kind="liquidity_decrease_v3",
            chain=self.chain,
            execution_family="position_manager_v3",
            execution_adapter=self.adapter_key,
            route_kind="position_manager",
            calls=[
                EvmCall(to=position_manager, data=decrease_calldata, value_wei="0", label="decrease_liquidity_v3"),
                EvmCall(to=position_manager, data=collect_calldata, value_wei="0", label="collect_after_decrease_v3"),
            ],
            details={
                "positionId": position_id,
                "liquidityUnits": liquidity_units,
                "minAmount0": min_a_units,
                "minAmount1": min_b_units,
                "deadline": deadline,
                "collectFees": True,
                "recipient": wallet_address.lower(),
            },
        )

    def build_increase_plan(
        self,
        request: dict[str, Any],
        wallet_address: str,
        *,
        build_calldata: Callable[[str, list[object]], str],
    ) -> EvmActionPlan:
        position_id = str(request.get("positionId") or request.get("positionRef") or "").strip()
        position_manager = self._require_position_manager()
        token_a = str(request.get("tokenA") or "").strip()
        token_b = str(request.get("tokenB") or "").strip()
        amount_a_units = str(request.get("amountAUnits") or "").strip()
        amount_b_units = str(request.get("amountBUnits") or "").strip()
        min_a_units = str(request.get("minAmountAUnits") or "").strip()
        min_b_units = str(request.get("minAmountBUnits") or "").strip()
        deadline = str(request.get("deadline") or "").strip()
        method = str((self.operations.get("increase") or {}).get("method") or "increaseLiquidity").strip() or "increaseLiquidity"
        params = _tuple_text([position_id, amount_a_units, amount_b_units, min_a_units, min_b_units, deadline])
        calldata = build_calldata(
            f"{method}((uint256,uint256,uint256,uint256,uint256,uint256))",
            [params],
        )
        return EvmActionPlan(
            operation_kind="liquidity_increase_v3",
            chain=self.chain,
            execution_family="position_manager_v3",
            execution_adapter=self.adapter_key,
            route_kind="position_manager",
            approvals=[
                ApprovalRequirement(token=token_a, spender=position_manager, required_units=int(amount_a_units)),
                ApprovalRequirement(token=token_b, spender=position_manager, required_units=int(amount_b_units)),
            ],
            calls=[EvmCall(to=position_manager, data=calldata, value_wei="0", label="increase_liquidity_v3")],
            details={
                "positionId": position_id,
                "tokenA": token_a.lower(),
                "tokenB": token_b.lower(),
                "amountAUnits": amount_a_units,
                "amountBUnits": amount_b_units,
                "minAmount0": min_a_units,
                "minAmount1": min_b_units,
                "deadline": deadline,
                "liquidityDelta": request.get("liquidityDelta"),
            },
        )

    def build_claim_fees_plan(
        self,
        request: dict[str, Any],
        wallet_address: str,
        *,
        build_calldata: Callable[[str, list[object]], str],
    ) -> EvmActionPlan:
        position_id = str(request.get("positionId") or request.get("positionRef") or "").strip()
        position_manager = self._require_position_manager()
        method = str((self.operations.get("claimFees") or {}).get("method") or "collect").strip() or "collect"
        amount0_max = str(request.get("token0CollectAmount") or MAX_UINT128).strip() or MAX_UINT128
        amount1_max = str(request.get("token1CollectAmount") or MAX_UINT128).strip() or MAX_UINT128
        params = _tuple_text([position_id, wallet_address, amount0_max, amount1_max])
        calldata = build_calldata(f"{method}((uint256,address,uint128,uint128))", [params])
        return EvmActionPlan(
            operation_kind="liquidity_claim_fees_v3",
            chain=self.chain,
            execution_family="position_manager_v3",
            execution_adapter=self.adapter_key,
            route_kind="reward_claim",
            calls=[EvmCall(to=position_manager, data=calldata, value_wei="0", label="claim_fees_v3")],
            details={
                "positionId": position_id,
                "collectFees": True,
                "recipient": wallet_address.lower(),
                "token0CollectAmount": amount0_max,
                "token1CollectAmount": amount1_max,
            },
        )

    def build_claim_rewards_plan(
        self,
        request: dict[str, Any],
        wallet_address: str,
        *,
        build_calldata: Callable[[str, list[object]], str],
    ) -> EvmActionPlan:
        position_id = str(request.get("positionId") or request.get("positionRef") or "").strip()
        self._require_position_manager()
        reward_cfg = self.operations.get("claimRewards") or {}
        reward_contracts = reward_cfg.get("rewardContracts")
        if not isinstance(reward_contracts, list) or len(reward_contracts) == 0:
            raise ValueError("claim_rewards_not_configured")
        method = str(reward_cfg.get("method") or "claimRewards(uint256,address[])").strip() or "claimRewards(uint256,address[])"
        tokens = request.get("tokens")
        token_list: list[str] = []
        if isinstance(tokens, list):
            token_list = [str(item or "").strip() for item in tokens if str(item or "").strip()]
        token_arg = _list_text(token_list)
        calls: list[EvmCall] = []
        for index, reward_contract in enumerate(reward_contracts):
            to_addr = str(reward_contract or "").strip()
            calldata = build_calldata(method, [position_id, token_arg])
            calls.append(EvmCall(to=to_addr, data=calldata, value_wei="0", label=f"claim_rewards_v3_{index}"))
        return EvmActionPlan(
            operation_kind="liquidity_claim_rewards_v3",
            chain=self.chain,
            execution_family="position_manager_v3",
            execution_adapter=self.adapter_key,
            route_kind="reward_claim",
            calls=calls,
            details={
                "positionId": position_id,
                "rewardContracts": [str(item).lower() for item in reward_contracts],
                "rewardTokens": [token.lower() for token in token_list],
                "recipient": wallet_address.lower(),
            },
        )

    def build_migrate_plan(
        self,
        request: dict[str, Any],
        wallet_address: str,
        *,
        build_calldata: Callable[[str, list[object]], str],
    ) -> EvmActionPlan:
        migrate_cfg = self.operations.get("migrate") or {}
        position_manager = self._require_position_manager()
        target_adapter_key = str(migrate_cfg.get("targetAdapterKey") or request.get("targetAdapterKey") or "").strip()
        if not target_adapter_key:
            raise ValueError("migration_target_not_configured")
        calls = request.get("calls")
        if not isinstance(calls, list) or len(calls) == 0:
            raise ValueError("migrate_request_calls_required")
        built_calls: list[EvmCall] = []
        for index, item in enumerate(calls):
            if not isinstance(item, dict):
                raise ValueError("migrate_request_calls_invalid")
            to_addr = str(item.get("to") or position_manager).strip()
            data = str(item.get("data") or "").strip()
            value_wei = str(item.get("value") or "0").strip() or "0"
            label = str(item.get("label") or f"migrate_step_{index}").strip() or f"migrate_step_{index}"
            built_calls.append(EvmCall(to=to_addr, data=data, value_wei=value_wei, label=label))
        approvals: list[ApprovalRequirement] = []
        raw_approvals = request.get("approvals")
        if isinstance(raw_approvals, list):
            for item in raw_approvals:
                if not isinstance(item, dict):
                    continue
                token = str(item.get("token") or "").strip()
                spender = str(item.get("spender") or position_manager).strip()
                required_units = int(str(item.get("requiredUnits") or "0").strip() or "0")
                if token and required_units > 0:
                    approvals.append(ApprovalRequirement(token=token, spender=spender, required_units=required_units))
        return EvmActionPlan(
            operation_kind="liquidity_migrate_v3",
            chain=self.chain,
            execution_family="position_manager_v3",
            execution_adapter=self.adapter_key,
            route_kind="migration",
            approvals=approvals,
            calls=built_calls,
            details={
                "positionId": str(request.get("positionId") or request.get("positionRef") or "").strip(),
                "migrationSourceAdapter": self.adapter_key,
                "migrationTargetAdapter": target_adapter_key,
                "rewardContracts": [],
                "recipient": wallet_address.lower(),
            },
        )
