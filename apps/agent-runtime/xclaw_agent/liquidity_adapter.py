from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from xclaw_agent.chains import get_chain


class LiquidityAdapterError(Exception):
    pass


class UnsupportedLiquidityAdapter(LiquidityAdapterError):
    pass


class HederaSdkUnavailable(LiquidityAdapterError):
    pass


@dataclass(frozen=True)
class LiquidityAdapter:
    chain: str
    dex: str
    protocol_family: str
    position_type: str

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


class AmmV2LiquidityAdapter(LiquidityAdapter):
    pass


class AmmV3LiquidityAdapter(LiquidityAdapter):
    pass


class HederaHtsLiquidityAdapter(LiquidityAdapter):
    @staticmethod
    def ensure_sdk() -> None:
        try:
            __import__("hedera")
        except Exception as exc:  # pragma: no cover - dependency optional by design
            raise HederaSdkUnavailable(
                "Hedera SDK module is not installed. Install Hedera SDK extras to enable HTS-native liquidity paths."
            ) from exc

    def quote_add(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.ensure_sdk()
        return super().quote_add(payload)

    def quote_remove(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.ensure_sdk()
        return super().quote_remove(payload)


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
    if not isinstance(payload, dict) or not payload:
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
        if requested_position == "v3" and family != "amm_v3":
            raise UnsupportedLiquidityAdapter(
                f"Adapter '{requested_dex}' on chain '{chain}' does not support v3 positions."
            )
        return requested_dex, family

    desired_family = "amm_v3" if requested_position == "v3" else "amm_v2"
    for key, entry in protocols.items():
        if entry.get("enabled", True) is False:
            continue
        family = str(entry.get("family") or "").strip().lower() or "amm_v2"
        if family == desired_family:
            return key, family

    raise UnsupportedLiquidityAdapter(
        f"Chain '{chain}' has no enabled liquidity adapter for position type '{requested_position}'."
    )


def build_liquidity_adapter(chain: str, dex: str, protocol_family: str, position_type: str = "v2") -> LiquidityAdapter:
    normalized = (protocol_family or "").strip().lower() or "amm_v2"
    normalized_position = (position_type or "v2").strip().lower()
    normalized_dex = (dex or "").strip().lower() or "default"

    if normalized == "amm_v3":
        return AmmV3LiquidityAdapter(
            chain=chain,
            dex=normalized_dex,
            protocol_family=normalized,
            position_type=normalized_position,
        )
    if normalized == "hedera_hts":
        return HederaHtsLiquidityAdapter(
            chain=chain,
            dex=normalized_dex,
            protocol_family=normalized,
            position_type=normalized_position,
        )
    if normalized == "amm_v2":
        return AmmV2LiquidityAdapter(
            chain=chain,
            dex=normalized_dex,
            protocol_family=normalized,
            position_type=normalized_position,
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
