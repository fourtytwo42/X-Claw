from __future__ import annotations

import hashlib
import struct
import time
from decimal import Decimal
from typing import Any

from xclaw_agent.solana_clmm_types import (
    RaydiumExecutionPlan,
    RaydiumPoolRef,
    RaydiumQuote,
    SolanaAccountMetaSpec,
    SolanaClmmExecutionResult,
    SolanaInstructionPlan,
)
from xclaw_agent.solana_rpc_client import SolanaRpcClientError, rpc_post as solana_rpc_post
from xclaw_agent.solana_runtime import SolanaRuntimeError

try:
    from solders.hash import Hash
    from solders.instruction import AccountMeta, Instruction
    from solders.keypair import Keypair
    from solders.pubkey import Pubkey
    from solders.transaction import Transaction
except Exception:  # pragma: no cover
    Hash = None  # type: ignore[assignment]
    AccountMeta = None  # type: ignore[assignment]
    Instruction = None  # type: ignore[assignment]
    Keypair = None  # type: ignore[assignment]
    Pubkey = None  # type: ignore[assignment]
    Transaction = None  # type: ignore[assignment]


def _require_deps() -> None:
    if not all([Hash, AccountMeta, Instruction, Keypair, Pubkey, Transaction]):
        raise SolanaRuntimeError("missing_dependency", "Raydium CLMM runtime dependency is missing.")


def _anchor_discriminator(method: str) -> bytes:
    name = str(method or "").strip()
    if not name:
        name = "unknown"
    digest = hashlib.sha256(f"global:{name}".encode("utf-8")).digest()
    return digest[:8]


def _parse_u64(value: Any, *, field: str) -> int:
    text = str(value or "").strip()
    if not text:
        return 0
    try:
        parsed = int(text)
    except Exception as exc:
        raise SolanaRuntimeError("invalid_input", f"{field} must be a uint64-compatible integer.") from exc
    if parsed < 0 or parsed > (2**64 - 1):
        raise SolanaRuntimeError("invalid_input", f"{field} is out of uint64 range.", {"field": field, "value": text})
    return parsed


def _resolve_pool_ref(adapter_metadata: dict[str, Any], request: dict[str, Any]) -> RaydiumPoolRef:
    requested_pool = str(request.get("poolId") or "").strip()
    token_a = str(request.get("tokenA") or "").strip().lower()
    token_b = str(request.get("tokenB") or "").strip().lower()
    fee_value = request.get("fee")
    fee_bps = int(fee_value) if str(fee_value or "").strip() else None

    pool_registry = adapter_metadata.get("poolRegistry")
    if not isinstance(pool_registry, dict) or not pool_registry:
        if requested_pool:
            return RaydiumPoolRef(pool_id=requested_pool, token_a=token_a, token_b=token_b, fee_bps=fee_bps)
        raise SolanaRuntimeError("chain_config_invalid", "Missing raydium_clmm.poolRegistry metadata.")

    candidates: list[dict[str, Any]] = []
    for _, entry in pool_registry.items():
        if isinstance(entry, dict):
            candidates.append(entry)
    if requested_pool:
        candidates = [entry for entry in candidates if str(entry.get("poolId") or "").strip() == requested_pool]
    if token_a and token_b:
        token_set = {token_a, token_b}
        candidates = [
            entry
            for entry in candidates
            if {str(entry.get("tokenA") or "").strip().lower(), str(entry.get("tokenB") or "").strip().lower()} == token_set
        ]
    if fee_bps is not None:
        candidates = [entry for entry in candidates if int(entry.get("feeBps") or -1) == fee_bps]
    if not candidates:
        raise SolanaRuntimeError(
            "pool_not_found",
            "Raydium pool was not found in configured registry for request.",
            {"poolId": requested_pool or None, "tokenA": token_a or None, "tokenB": token_b or None, "fee": fee_bps},
        )
    selected = candidates[0]
    pool_id = str(selected.get("poolId") or "").strip()
    if not pool_id:
        raise SolanaRuntimeError("chain_config_invalid", "Raydium pool registry entry is missing poolId.")
    return RaydiumPoolRef(
        pool_id=pool_id,
        token_a=str(selected.get("tokenA") or token_a).strip(),
        token_b=str(selected.get("tokenB") or token_b).strip(),
        fee_bps=int(selected.get("feeBps")) if selected.get("feeBps") is not None else fee_bps,
    )


def _ensure_pool_exists(chain: str, rpc_url: str, pool: RaydiumPoolRef, *, expected_owner_program: str) -> None:
    try:
        info = solana_rpc_post(
            "getAccountInfo",
            [pool.pool_id, {"encoding": "base64", "commitment": "confirmed"}],
            chain_key=chain,
            rpc_url=rpc_url,
            timeout_sec=20.0,
        )
    except SolanaRpcClientError as exc:
        raise SolanaRuntimeError(exc.code, str(exc), dict(exc.details or {})) from exc
    value = info.get("value") if isinstance(info, dict) else None
    if not isinstance(value, dict):
        raise SolanaRuntimeError("pool_not_found", "Configured Raydium pool account does not exist on RPC.", {"poolId": pool.pool_id, "chain": chain})
    owner = str(value.get("owner") or "").strip()
    if owner and expected_owner_program and owner != expected_owner_program:
        raise SolanaRuntimeError(
            "chain_config_invalid",
            "Configured pool owner program does not match configured Raydium CLMM program.",
            {"poolId": pool.pool_id, "poolOwner": owner, "expectedProgramId": expected_owner_program},
        )


def quote_add(amount_a: str, amount_b: str, slippage_bps: int, *, pool_id: str) -> RaydiumQuote:
    a = Decimal(str(amount_a or "0"))
    b = Decimal(str(amount_b or "0"))
    if a <= 0 or b <= 0:
        raise SolanaRuntimeError("invalid_input", "Raydium quote-add requires positive amounts.")
    if slippage_bps < 0 or slippage_bps > 5000:
        raise SolanaRuntimeError("invalid_input", "slippageBps must be 0..5000.")
    multiplier = Decimal(max(0, 10000 - slippage_bps)) / Decimal(10000)
    return RaydiumQuote(
        amount_a=str(a.normalize()),
        amount_b=str(b.normalize()),
        min_amount_a=str((a * multiplier).normalize()),
        min_amount_b=str((b * multiplier).normalize()),
        slippage_bps=slippage_bps,
        pool_id=pool_id,
    )


def quote_remove(percent: int, *, pool_id: str) -> dict[str, Any]:
    if percent < 1 or percent > 100:
        raise SolanaRuntimeError("invalid_input", "percent must be 1..100.")
    return {"percent": percent, "poolId": pool_id}


def _build_instruction_data(operation: dict[str, Any], request: dict[str, Any], operation_key: str) -> str:
    discriminator_hex = str(operation.get("discriminatorHex") or "").strip().lower()
    if not discriminator_hex.startswith("0x") or len(discriminator_hex) != 18:
        raise SolanaRuntimeError(
            "chain_config_invalid",
            f"Raydium operation '{operation_key}' requires discriminatorHex as 8-byte hex (0x + 16 chars).",
            {"operationKey": operation_key, "discriminatorHex": discriminator_hex or None},
        )
    prefix = bytes.fromhex(discriminator_hex[2:18])

    if operation_key == "add":
        amount_a_units = _parse_u64(request.get("amountAUnits"), field="amountAUnits")
        amount_b_units = _parse_u64(request.get("amountBUnits"), field="amountBUnits")
        min_amount_a_units = _parse_u64(request.get("minAmountAUnits"), field="minAmountAUnits")
        min_amount_b_units = _parse_u64(request.get("minAmountBUnits"), field="minAmountBUnits")
        payload = struct.pack("<QQQQ", amount_a_units, amount_b_units, min_amount_a_units, min_amount_b_units)
    else:
        percent = _parse_u64(request.get("percent"), field="percent")
        payload = struct.pack("<Q", percent)
    return "0x" + (prefix + payload).hex()


def _resolve_account_pubkey(value: str, *, owner: str, pool: RaydiumPoolRef, request: dict[str, Any]) -> str:
    token_a = str(request.get("tokenA") or pool.token_a or "").strip()
    token_b = str(request.get("tokenB") or pool.token_b or "").strip()
    lookup = {
        "$OWNER": owner,
        "$POOL": pool.pool_id,
        "$TOKEN_A": token_a,
        "$TOKEN_B": token_b,
    }
    if value in lookup and lookup[value]:
        return lookup[value]
    return value


def _build_accounts(operation: dict[str, Any], *, owner: str, pool: RaydiumPoolRef, request: dict[str, Any]) -> list[SolanaAccountMetaSpec]:
    templates = operation.get("accountsTemplate")
    if not isinstance(templates, list) or not templates:
        templates = operation.get("accounts")
    if not isinstance(templates, list) or not templates:
        raise SolanaRuntimeError("chain_config_invalid", "Raydium operation is missing accountsTemplate metadata.")
    accounts: list[SolanaAccountMetaSpec] = []
    for row in templates:
        if not isinstance(row, dict):
            continue
        pubkey = _resolve_account_pubkey(str(row.get("pubkey") or "").strip(), owner=owner, pool=pool, request=request).strip()
        if not pubkey:
            continue
        accounts.append(
            SolanaAccountMetaSpec(
                pubkey=pubkey,
                is_signer=bool(row.get("isSigner")),
                is_writable=bool(row.get("isWritable")),
            )
        )
    if not accounts:
        raise SolanaRuntimeError("chain_config_invalid", "Raydium operation has no usable account metas.")
    return accounts


def build_execution_plan(
    *,
    chain: str,
    rpc_url: str,
    owner: str,
    adapter_metadata: dict[str, Any],
    request: dict[str, Any],
    operation_key: str,
) -> RaydiumExecutionPlan:
    operations = adapter_metadata.get("operations")
    if not isinstance(operations, dict):
        raise SolanaRuntimeError("chain_config_invalid", "Raydium adapter metadata missing operations.")
    operation = operations.get(operation_key)
    if not isinstance(operation, dict):
        raise SolanaRuntimeError("unsupported_liquidity_operation", f"Raydium operation '{operation_key}' is not configured.")

    program_ids = adapter_metadata.get("programIds") if isinstance(adapter_metadata.get("programIds"), dict) else {}
    program_id = str(operation.get("programId") or program_ids.get("clmm") or "").strip()
    if not program_id:
        raise SolanaRuntimeError("chain_config_invalid", f"Raydium {operation_key} is missing programId/programIds.clmm.")
    pool = _resolve_pool_ref(adapter_metadata, request)
    _ensure_pool_exists(chain, rpc_url, pool, expected_owner_program=program_id)

    ix = SolanaInstructionPlan(
        program_id=program_id,
        accounts=_build_accounts(operation, owner=owner, pool=pool, request=request),
        data_hex=_build_instruction_data(operation, request, operation_key),
        operation_key=operation_key,
        route_kind="pool_direct",
    )
    return RaydiumExecutionPlan(
        pool=pool,
        instructions=[ix],
        details={
            "poolId": pool.pool_id,
            "tokenA": pool.token_a,
            "tokenB": pool.token_b,
            "feeBps": pool.fee_bps,
            "operationKey": operation_key,
        },
    )


def _latest_blockhash(chain: str, rpc_url: str) -> str:
    try:
        result = solana_rpc_post(
            "getLatestBlockhash",
            [{"commitment": "confirmed"}],
            chain_key=chain,
            rpc_url=rpc_url,
            timeout_sec=20.0,
        )
    except SolanaRpcClientError as exc:
        raise SolanaRuntimeError(exc.code, str(exc), dict(exc.details or {})) from exc
    value = result.get("value") if isinstance(result, dict) else {}
    blockhash = str((value or {}).get("blockhash") or "").strip()
    if not blockhash:
        raise SolanaRuntimeError("rpc_unavailable", "Missing blockhash from RPC.")
    return blockhash


def _wait_signature(chain: str, rpc_url: str, signature: str, timeout_sec: int = 45) -> None:
    start = time.time()
    while True:
        try:
            result = solana_rpc_post(
                "getSignatureStatuses",
                [[signature], {"searchTransactionHistory": True}],
                chain_key=chain,
                rpc_url=rpc_url,
                timeout_sec=20.0,
            )
        except SolanaRpcClientError as exc:
            raise SolanaRuntimeError(exc.code, str(exc), dict(exc.details or {})) from exc
        value = result.get("value") if isinstance(result, dict) else []
        row = value[0] if isinstance(value, list) and value else None
        if isinstance(row, dict):
            if row.get("err") is not None:
                raise SolanaRuntimeError("transaction_failed", "Raydium transaction failed.", {"signature": signature, "err": row.get("err")})
            status = str(row.get("confirmationStatus") or "")
            if status in {"confirmed", "finalized"}:
                return
        if (time.time() - start) > timeout_sec:
            raise SolanaRuntimeError("tx_receipt_timeout", "Timed out waiting for Raydium transaction confirmation.", {"signature": signature})
        time.sleep(1.0)


def _send_raw_tx(chain: str, rpc_url: str, tx_bytes: bytes) -> str:
    import base64

    encoded = base64.b64encode(tx_bytes).decode("ascii")
    try:
        sig = solana_rpc_post(
            "sendTransaction",
            [
                encoded,
                {
                    "encoding": "base64",
                    "skipPreflight": False,
                    "preflightCommitment": "confirmed",
                    "maxRetries": 3,
                },
            ],
            chain_key=chain,
            rpc_url=rpc_url,
            timeout_sec=20.0,
        )
    except SolanaRpcClientError as exc:
        raise SolanaRuntimeError(exc.code, str(exc), dict(exc.details or {})) from exc
    signature = str(sig or "").strip()
    if not signature:
        raise SolanaRuntimeError("rpc_unavailable", "sendTransaction returned empty signature.")
    _wait_signature(chain, rpc_url, signature)
    return signature


def execute_plan(
    *,
    chain: str,
    rpc_url: str,
    private_key_bytes: bytes,
    plan: RaydiumExecutionPlan,
) -> SolanaClmmExecutionResult:
    _require_deps()
    keypair = Keypair.from_bytes(private_key_bytes)
    payer = keypair.pubkey()
    instructions = []
    for entry in plan.instructions:
        metas = [
            AccountMeta(
                pubkey=Pubkey.from_string(meta.pubkey),
                is_signer=meta.is_signer,
                is_writable=meta.is_writable,
            )
            for meta in entry.accounts
        ]
        instructions.append(
            Instruction(
                program_id=Pubkey.from_string(entry.program_id),
                accounts=metas,
                data=bytes.fromhex(entry.data_hex[2:]),
            )
        )
    blockhash = Hash.from_string(_latest_blockhash(chain, rpc_url))
    tx = Transaction.new_signed_with_payer(instructions, payer, [keypair], blockhash)
    signature = _send_raw_tx(chain, rpc_url, bytes(tx))
    route_kind = plan.instructions[0].route_kind if plan.instructions else "pool_direct"
    return SolanaClmmExecutionResult(
        tx_hash=signature,
        route_kind=route_kind,
        details={
            **plan.details,
            "instructionCount": len(plan.instructions),
            "programId": plan.instructions[0].program_id if plan.instructions else None,
        },
    )
