from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class EvmCall:
    to: str
    data: str
    value_wei: str
    label: str


@dataclass(frozen=True)
class ApprovalRequirement:
    token: str
    spender: str
    required_units: int
    symbol: str | None = None


@dataclass(frozen=True)
class EvmActionPlan:
    operation_kind: str
    chain: str
    execution_family: str
    execution_adapter: str
    route_kind: str | None
    approvals: list[ApprovalRequirement] = field(default_factory=list)
    calls: list[EvmCall] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EvmExecutionResult:
    ok: bool
    execution_family: str
    execution_adapter: str
    route_kind: str | None
    liquidity_operation: str | None
    approve_tx_hashes: list[str] = field(default_factory=list)
    operation_tx_hashes: list[str] = field(default_factory=list)
    tx_hash: str | None = None
    details: dict[str, Any] = field(default_factory=dict)
