from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from xclaw_agent.execution_contracts import ApprovalRequirement, EvmActionPlan, EvmCall


@dataclass(frozen=True)
class AmmV2TradeAdapter:
    chain: str
    adapter_key: str
    router: str
    factory: str
    quoter: str

    def quote(self, request: dict[str, Any], *, get_amount_out: Callable[[str, str, str], int]) -> dict[str, Any]:
        amount_in_units = str(request.get("amountInUnits") or "").strip()
        token_in = str(request.get("tokenIn") or "").strip()
        token_out = str(request.get("tokenOut") or "").strip()
        if not amount_in_units or not token_in or not token_out:
            raise ValueError("trade quote request is missing token or amount fields")
        amount_out_units = int(get_amount_out(amount_in_units, token_in, token_out))
        route_kind = "direct_pair"
        if token_in.lower() != token_out.lower():
            route_kind = "router_path"
        return {
            "amountOutUnits": str(amount_out_units),
            "routeKind": route_kind,
            "executionFamily": "amm_v2",
            "executionAdapter": self.adapter_key,
        }

    def build_action_plan(
        self,
        request: dict[str, Any],
        wallet_address: str,
        *,
        build_calldata: Callable[[str, list[object]], str],
    ) -> EvmActionPlan:
        amount_in_units = str(request.get("amountInUnits") or "").strip()
        min_out_units = str(request.get("amountOutMinUnits") or "").strip()
        token_in = str(request.get("tokenIn") or "").strip()
        token_out = str(request.get("tokenOut") or "").strip()
        recipient = str(request.get("recipient") or wallet_address).strip()
        deadline = str(request.get("deadline") or "").strip()
        route_kind = str(request.get("routeKind") or "router_path").strip() or None
        calldata = build_calldata(
            "swapExactTokensForTokens(uint256,uint256,address[],address,uint256)(uint256[])",
            [amount_in_units, min_out_units, f"[{token_in},{token_out}]", recipient, deadline],
        )
        return EvmActionPlan(
            operation_kind="swap_exact_in",
            chain=self.chain,
            execution_family="amm_v2",
            execution_adapter=self.adapter_key,
            route_kind=route_kind,
            approvals=[
                ApprovalRequirement(
                    token=token_in,
                    spender=self.router,
                    required_units=int(amount_in_units),
                )
            ],
            calls=[EvmCall(to=self.router, data=calldata, value_wei="0", label="swap_exact_in")],
            details={
                "amountInUnits": amount_in_units,
                "amountOutMinUnits": min_out_units,
                "tokenIn": token_in.lower(),
                "tokenOut": token_out.lower(),
                "recipient": recipient.lower(),
            },
        )
