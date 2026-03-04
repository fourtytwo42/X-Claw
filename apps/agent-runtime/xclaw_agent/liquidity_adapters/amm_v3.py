from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AmmV3LiquidityExecutionAdapter:
    chain: str
    adapter_key: str
    router: str
    factory: str
    quoter: str
