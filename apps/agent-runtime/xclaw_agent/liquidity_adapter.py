from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class LiquidityAdapterError(Exception):
    pass


class HederaSdkUnavailable(LiquidityAdapterError):
    pass


@dataclass(frozen=True)
class LiquidityAdapter:
    chain: str
    dex: str
    protocol_family: str

    def quote_add(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"ok": True, "family": self.protocol_family, "action": "quote_add", "payload": payload}

    def quote_remove(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"ok": True, "family": self.protocol_family, "action": "quote_remove", "payload": payload}


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


def build_liquidity_adapter(chain: str, dex: str, protocol_family: str) -> LiquidityAdapter:
    normalized = (protocol_family or "").strip().lower()
    if normalized == "amm_v3":
        return AmmV3LiquidityAdapter(chain=chain, dex=dex, protocol_family=normalized)
    if normalized == "hedera_hts":
        return HederaHtsLiquidityAdapter(chain=chain, dex=dex, protocol_family=normalized)
    return AmmV2LiquidityAdapter(chain=chain, dex=dex, protocol_family=(normalized or "amm_v2"))
