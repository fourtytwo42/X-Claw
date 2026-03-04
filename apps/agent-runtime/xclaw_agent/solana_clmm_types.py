from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SolanaAccountMetaSpec:
    pubkey: str
    is_signer: bool = False
    is_writable: bool = False


@dataclass(frozen=True)
class SolanaInstructionSpec:
    program_id: str
    accounts: list[SolanaAccountMetaSpec]
    data_hex: str


@dataclass(frozen=True)
class RaydiumPoolRef:
    pool_id: str
    token_a: str
    token_b: str
    fee_bps: int | None = None


@dataclass(frozen=True)
class RaydiumQuote:
    amount_a: str
    amount_b: str
    min_amount_a: str
    min_amount_b: str
    slippage_bps: int
    pool_id: str


@dataclass(frozen=True)
class SolanaInstructionPlan:
    program_id: str
    accounts: list[SolanaAccountMetaSpec]
    data_hex: str
    operation_key: str
    route_kind: str = "pool_direct"


@dataclass(frozen=True)
class RaydiumExecutionPlan:
    pool: RaydiumPoolRef
    instructions: list[SolanaInstructionPlan]
    details: dict[str, Any]


@dataclass(frozen=True)
class SolanaClmmExecutionResult:
    tx_hash: str
    route_kind: str
    details: dict[str, Any]
