from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from xclaw_agent.chains import get_chain
from xclaw_agent.execution_contracts import EvmActionPlan
from xclaw_agent.liquidity_adapters.amm_v2 import AmmV2LiquidityExecutionAdapter
from xclaw_agent.liquidity_adapters.amm_v3 import AmmV3LiquidityExecutionAdapter

_DEX_ALIASES: dict[str, str] = {
    "uniswap": "uniswap_v2",
    "uni": "uniswap_v2",
}


class LiquidityAdapterError(Exception):
    pass


class UnsupportedLiquidityAdapter(LiquidityAdapterError):
    pass


class UnsupportedLiquidityOperation(LiquidityAdapterError):
    pass


@dataclass(frozen=True)
class LiquidityAdapter:
    chain: str
    dex: str
    protocol_family: str
    position_type: str
    router: str = ""
    factory: str = ""
    quoter: str = ""
    position_manager: str = ""
    capabilities: dict[str, bool] | None = None
    operations: dict[str, dict[str, Any]] | None = None
    adapter_metadata: dict[str, Any] | None = None

    def quote_add(self, payload: dict[str, Any]) -> dict[str, Any]:
        amount_a = _require_positive_decimal(payload.get("amountA"), "amountA")
        amount_b = _require_positive_decimal(payload.get("amountB"), "amountB")
        slippage_bps = _require_bps(payload.get("slippageBps"), "slippageBps")
        return {
            "ok": True,
            "family": self.protocol_family,
            "positionType": self.position_type,
            "dex": self.dex,
            "action": "quote_add",
            "simulation": {
                "amountA": _decimal_text(amount_a),
                "amountB": _decimal_text(amount_b),
                "minAmountA": _decimal_text(amount_a * Decimal(max(0, 10000 - slippage_bps)) / Decimal(10000)),
                "minAmountB": _decimal_text(amount_b * Decimal(max(0, 10000 - slippage_bps)) / Decimal(10000)),
                "slippageBps": slippage_bps,
            },
        }

    def quote_remove(self, payload: dict[str, Any]) -> dict[str, Any]:
        percent = _require_percent(payload.get("percent"), "percent")
        _require_non_empty(payload.get("positionId"), "positionId")
        return {
            "ok": True,
            "family": self.protocol_family,
            "positionType": self.position_type,
            "dex": self.dex,
            "action": "quote_remove",
            "simulation": {
                "percent": percent,
                "positionId": str(payload.get("positionId") or "").strip(),
            },
        }

    def add(self, payload: dict[str, Any]) -> dict[str, Any]:
        quote = self.quote_add(payload)
        return {
            "ok": True,
            "family": self.protocol_family,
            "positionType": self.position_type,
            "dex": self.dex,
            "action": "add",
            "preflight": quote.get("simulation", {}),
        }

    def remove(self, payload: dict[str, Any]) -> dict[str, Any]:
        quote = self.quote_remove(payload)
        return {
            "ok": True,
            "family": self.protocol_family,
            "positionType": self.position_type,
            "dex": self.dex,
            "action": "remove",
            "preflight": quote.get("simulation", {}),
        }

    def claim_fees(self, payload: dict[str, Any]) -> dict[str, Any]:
        raise UnsupportedLiquidityOperation("claim_fees_not_supported_for_protocol")

    def claim_rewards(self, payload: dict[str, Any]) -> dict[str, Any]:
        raise UnsupportedLiquidityOperation("claim_rewards_not_supported_for_protocol")

    def supports_operation(self, operation: str) -> bool:
        op = str(operation or "").strip().lower()
        return op in {"add", "remove", "quote_add", "quote_remove", "position_fetch"}

    def supports_reward_claim(self) -> bool:
        return self.supports_operation("claim_rewards")

    def reward_contract_required(self) -> bool:
        return True

    def position_fetch(self, payload: dict[str, Any]) -> dict[str, Any]:
        position_id = str(payload.get("positionId") or "").strip()
        if not position_id:
            raise LiquidityAdapterError("positionId is required for position fetch.")
        return {
            "ok": True,
            "family": self.protocol_family,
            "positionType": self.position_type,
            "dex": self.dex,
            "positionId": position_id,
        }

    def build_add_plan(
        self,
        payload: dict[str, Any],
        wallet_address: str,
        *,
        build_calldata: callable,
    ) -> EvmActionPlan:
        raise UnsupportedLiquidityOperation("unsupported_liquidity_execution_family")

    def build_remove_plan(
        self,
        payload: dict[str, Any],
        wallet_address: str,
        *,
        build_calldata: callable,
    ) -> EvmActionPlan:
        raise UnsupportedLiquidityOperation("unsupported_liquidity_execution_family")

    def build_increase_plan(
        self,
        payload: dict[str, Any],
        wallet_address: str,
        *,
        build_calldata: callable,
    ) -> EvmActionPlan:
        raise UnsupportedLiquidityOperation("unsupported_liquidity_execution_family")

    def build_claim_fees_plan(
        self,
        payload: dict[str, Any],
        wallet_address: str,
        *,
        build_calldata: callable,
    ) -> EvmActionPlan:
        raise UnsupportedLiquidityOperation("unsupported_liquidity_execution_family")

    def build_claim_rewards_plan(
        self,
        payload: dict[str, Any],
        wallet_address: str,
        *,
        build_calldata: callable,
    ) -> EvmActionPlan:
        raise UnsupportedLiquidityOperation("unsupported_liquidity_execution_family")

    def build_migrate_plan(
        self,
        payload: dict[str, Any],
        wallet_address: str,
        *,
        build_calldata: callable,
    ) -> EvmActionPlan:
        raise UnsupportedLiquidityOperation("unsupported_liquidity_execution_family")


class AmmV2LiquidityAdapter(LiquidityAdapter):
    def build_add_plan(
        self,
        payload: dict[str, Any],
        wallet_address: str,
        *,
        build_calldata: callable,
    ) -> EvmActionPlan:
        planner = AmmV2LiquidityExecutionAdapter(
            chain=self.chain,
            adapter_key=self.dex,
            router=self.router,
            factory=self.factory,
            quoter=self.quoter,
        )
        return planner.build_add_plan(payload, wallet_address, build_calldata=build_calldata)

    def build_remove_plan(
        self,
        payload: dict[str, Any],
        wallet_address: str,
        *,
        build_calldata: callable,
    ) -> EvmActionPlan:
        planner = AmmV2LiquidityExecutionAdapter(
            chain=self.chain,
            adapter_key=self.dex,
            router=self.router,
            factory=self.factory,
            quoter=self.quoter,
        )
        return planner.build_remove_plan(payload, wallet_address, build_calldata=build_calldata)


class AmmV3LiquidityAdapter(LiquidityAdapter):
    def _planner(self) -> AmmV3LiquidityExecutionAdapter:
        return AmmV3LiquidityExecutionAdapter(
            chain=self.chain,
            adapter_key=self.dex,
            router=self.router,
            factory=self.factory,
            quoter=self.quoter,
            position_manager=self.position_manager,
            capabilities=dict(self.capabilities or {}),
            operations=dict(self.operations or {}),
        )

    def supports_operation(self, operation: str) -> bool:
        return self._planner().supports_operation(operation)

    def build_increase_plan(
        self,
        payload: dict[str, Any],
        wallet_address: str,
        *,
        build_calldata: callable,
    ) -> EvmActionPlan:
        return self._planner().build_increase_plan(payload, wallet_address, build_calldata=build_calldata)

    def build_claim_fees_plan(
        self,
        payload: dict[str, Any],
        wallet_address: str,
        *,
        build_calldata: callable,
    ) -> EvmActionPlan:
        return self._planner().build_claim_fees_plan(payload, wallet_address, build_calldata=build_calldata)

    def build_claim_rewards_plan(
        self,
        payload: dict[str, Any],
        wallet_address: str,
        *,
        build_calldata: callable,
    ) -> EvmActionPlan:
        return self._planner().build_claim_rewards_plan(payload, wallet_address, build_calldata=build_calldata)

    def build_migrate_plan(
        self,
        payload: dict[str, Any],
        wallet_address: str,
        *,
        build_calldata: callable,
    ) -> EvmActionPlan:
        return self._planner().build_migrate_plan(payload, wallet_address, build_calldata=build_calldata)

    def build_remove_plan(
        self,
        payload: dict[str, Any],
        wallet_address: str,
        *,
        build_calldata: callable,
    ) -> EvmActionPlan:
        return self._planner().build_remove_plan(payload, wallet_address, build_calldata=build_calldata)

    def build_add_plan(
        self,
        payload: dict[str, Any],
        wallet_address: str,
        *,
        build_calldata: callable,
    ) -> EvmActionPlan:
        return self._planner().build_add_plan(payload, wallet_address, build_calldata=build_calldata)


class SolanaClmmLiquidityAdapter(LiquidityAdapter):
    def supports_operation(self, operation: str) -> bool:
        op = str(operation or "").strip().lower()
        return op in {"add", "remove", "quote_add", "quote_remove", "position_fetch"}


def _require_non_empty(value: Any, field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise LiquidityAdapterError(f"{field_name} is required.")
    return text


def _require_positive_decimal(value: Any, field_name: str) -> Decimal:
    text = str(value or "").strip()
    try:
        parsed = Decimal(text)
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise LiquidityAdapterError(f"{field_name} must be a positive decimal.") from exc
    if parsed <= 0:
        raise LiquidityAdapterError(f"{field_name} must be greater than zero.")
    return parsed


def _require_bps(value: Any, field_name: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise LiquidityAdapterError(f"{field_name} must be an integer.") from exc
    if parsed < 0 or parsed > 5000:
        raise LiquidityAdapterError(f"{field_name} must be between 0 and 5000.")
    return parsed


def _require_percent(value: Any, field_name: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise LiquidityAdapterError(f"{field_name} must be an integer.") from exc
    if parsed < 1 or parsed > 100:
        raise LiquidityAdapterError(f"{field_name} must be between 1 and 100.")
    return parsed


def _decimal_text(value: Decimal) -> str:
    normalized = value.normalize()
    if normalized == normalized.to_integral():
        return str(normalized.quantize(Decimal("1")))
    return format(normalized, "f")


def _protocols_for_chain(chain: str) -> dict[str, dict[str, Any]]:
    cfg = get_chain(chain, include_disabled=True)
    if not cfg:
        raise UnsupportedLiquidityAdapter(f"Unsupported chain '{chain}' for liquidity adapter selection.")
    payload = cfg.get("liquidityProtocols")
    base_protocols: dict[str, dict[str, Any]] = {}
    if isinstance(payload, dict):
        for key, value in payload.items():
            if not isinstance(value, dict):
                continue
            base_protocols[str(key).strip().lower()] = dict(value)

    execution = cfg.get("execution") or {}
    liquidity = execution.get("liquidity") if isinstance(execution, dict) else {}
    adapters = liquidity.get("adapters") if isinstance(liquidity, dict) else {}
    if isinstance(adapters, dict):
        for key, value in adapters.items():
            if not isinstance(value, dict):
                continue
            adapter_key = str(value.get("adapterKey") or key).strip().lower() or str(key).strip().lower()
            merged = dict(base_protocols.get(adapter_key, {}))
            merged.update(
                {
                    "enabled": value.get("enabled", merged.get("enabled", True)),
                    "family": str(value.get("family") or merged.get("family") or "amm_v2").strip().lower() or "amm_v2",
                    "router": str(value.get("router") or merged.get("router") or "").strip(),
                    "factory": str(value.get("factory") or merged.get("factory") or "").strip(),
                    "quoter": str(value.get("quoter") or merged.get("quoter") or "").strip(),
                    "positionManager": str(value.get("positionManager") or merged.get("positionManager") or "").strip(),
                    "capabilities": value.get("capabilities") if isinstance(value.get("capabilities"), dict) else merged.get("capabilities") or {},
                    "operations": value.get("operations") if isinstance(value.get("operations"), dict) else merged.get("operations") or {},
                    "programIds": value.get("programIds") if isinstance(value.get("programIds"), dict) else merged.get("programIds") or {},
                    "poolRegistry": value.get("poolRegistry") if isinstance(value.get("poolRegistry"), dict) else merged.get("poolRegistry") or {},
                }
            )
            base_protocols[adapter_key] = merged
    payload = base_protocols
    if not payload:
        raise UnsupportedLiquidityAdapter(f"Chain '{chain}' does not define liquidity protocols.")

    out: dict[str, dict[str, Any]] = {}
    for key, value in payload.items():
        if not isinstance(value, dict):
            continue
        out[str(key).strip().lower()] = value
    if not out:
        raise UnsupportedLiquidityAdapter(f"Chain '{chain}' does not define usable liquidity protocols.")
    return out


def _resolve_protocol(chain: str, dex: str, position_type: str) -> tuple[str, str]:
    protocols = _protocols_for_chain(chain)
    requested_dex = str(dex or "").strip().lower()
    requested_dex = _DEX_ALIASES.get(requested_dex, requested_dex)
    requested_position = str(position_type or "v2").strip().lower()

    if requested_position not in {"v2", "v3"}:
        raise UnsupportedLiquidityAdapter(f"Unsupported position type '{position_type}'.")

    if requested_dex:
        matched = protocols.get(requested_dex)
        if not matched or matched.get("enabled", True) is False:
            raise UnsupportedLiquidityAdapter(
                f"Liquidity adapter '{requested_dex}' is not enabled for chain '{chain}'."
            )
        family = str(matched.get("family") or "").strip().lower() or "amm_v2"
        if requested_position == "v3" and family not in {"amm_v3", "position_manager_v3", "local_clmm", "raydium_clmm"}:
            raise UnsupportedLiquidityAdapter(
                f"Adapter '{requested_dex}' on chain '{chain}' does not support v3 positions."
            )
        return requested_dex, family

    desired_family = {"amm_v3", "position_manager_v3", "local_clmm", "raydium_clmm"} if requested_position == "v3" else {"amm_v2"}
    for key, entry in protocols.items():
        if entry.get("enabled", True) is False:
            continue
        family = str(entry.get("family") or "").strip().lower() or "amm_v2"
        if family in desired_family:
            return key, family

    raise UnsupportedLiquidityAdapter(
        f"Chain '{chain}' has no enabled liquidity adapter for position type '{requested_position}'."
    )


def build_liquidity_adapter(chain: str, dex: str, protocol_family: str, position_type: str = "v2") -> LiquidityAdapter:
    normalized = (protocol_family or "").strip().lower() or "amm_v2"
    normalized_position = (position_type or "v2").strip().lower()
    normalized_dex = (dex or "").strip().lower() or "default"
    protocols = _protocols_for_chain(chain)
    protocol_entry = protocols.get(normalized_dex, {})
    router = str(protocol_entry.get("router") or "").strip()
    factory = str(protocol_entry.get("factory") or "").strip()
    quoter = str(protocol_entry.get("quoter") or "").strip()
    position_manager = str(protocol_entry.get("positionManager") or "").strip()
    capabilities = protocol_entry.get("capabilities")
    operations = protocol_entry.get("operations")

    if normalized in {"amm_v3", "position_manager_v3"}:
        return AmmV3LiquidityAdapter(
            chain=chain,
            dex=normalized_dex,
            protocol_family="position_manager_v3",
            position_type=normalized_position,
            router=router,
            factory=factory,
            quoter=quoter,
            position_manager=position_manager,
            capabilities=dict(capabilities) if isinstance(capabilities, dict) else {},
            operations=dict(operations) if isinstance(operations, dict) else {},
            adapter_metadata=dict(protocol_entry),
        )
    if normalized == "amm_v2":
        return AmmV2LiquidityAdapter(
            chain=chain,
            dex=normalized_dex,
            protocol_family=normalized,
            position_type=normalized_position,
            router=router,
            factory=factory,
            quoter=quoter,
            capabilities=dict(capabilities) if isinstance(capabilities, dict) else {},
            operations=dict(operations) if isinstance(operations, dict) else {},
            adapter_metadata=dict(protocol_entry),
        )
    if normalized in {"local_clmm", "raydium_clmm"}:
        if normalized == "local_clmm" and chain != "solana_localnet":
            raise UnsupportedLiquidityAdapter("local_clmm adapter is restricted to solana_localnet.")
        return SolanaClmmLiquidityAdapter(
            chain=chain,
            dex=normalized_dex,
            protocol_family=normalized,
            position_type=normalized_position,
            router=router,
            factory=factory,
            quoter=quoter,
            position_manager=position_manager,
            capabilities=dict(capabilities) if isinstance(capabilities, dict) else {},
            operations=dict(operations) if isinstance(operations, dict) else {},
            adapter_metadata=dict(protocol_entry),
        )

    raise UnsupportedLiquidityAdapter(
        f"Unsupported liquidity protocol family '{normalized}' for chain '{chain}' and dex '{normalized_dex}'."
    )


def build_liquidity_adapter_for_request(chain: str, dex: str, position_type: str = "v2") -> LiquidityAdapter:
    resolved_dex, resolved_family = _resolve_protocol(chain=chain, dex=dex, position_type=position_type)
    return build_liquidity_adapter(
        chain=chain,
        dex=resolved_dex,
        protocol_family=resolved_family,
        position_type=position_type,
    )
