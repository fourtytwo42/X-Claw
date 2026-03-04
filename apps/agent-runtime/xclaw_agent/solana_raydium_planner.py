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


def _operation_entry(operations: dict[str, Any], key: str) -> dict[str, Any] | None:
    entry = operations.get(key)
    if isinstance(entry, dict):
        return entry
    if key == "claim_fees":
        entry = operations.get("claimFees")
    elif key == "claim_rewards":
        entry = operations.get("claimRewards")
    elif key == "remove":
        entry = operations.get("decrease")
    if isinstance(entry, dict):
        return entry
    return None


def _resolve_discriminator_prefix(operation: dict[str, Any], operation_key: str) -> bytes:
    discriminator_hex = str(operation.get("discriminatorHex") or "").strip().lower()
    if discriminator_hex.startswith("0x") and len(discriminator_hex) == 18:
        return bytes.fromhex(discriminator_hex[2:18])
    method = str(operation.get("method") or "").strip()
    if method:
        return _anchor_discriminator(method)
    raise SolanaRuntimeError(
        "chain_config_invalid",
        f"Raydium operation '{operation_key}' requires discriminatorHex or method.",
        {"operationKey": operation_key},
    )


def _build_instruction_data(operation: dict[str, Any], request: dict[str, Any], operation_key: str) -> str:
    prefix = _resolve_discriminator_prefix(operation, operation_key)

    if operation_key in {"add", "increase"}:
        amount_a_units = _parse_u64(request.get("amountAUnits"), field="amountAUnits")
        amount_b_units = _parse_u64(request.get("amountBUnits"), field="amountBUnits")
        min_amount_a_units = _parse_u64(request.get("minAmountAUnits"), field="minAmountAUnits")
        min_amount_b_units = _parse_u64(request.get("minAmountBUnits"), field="minAmountBUnits")
        payload = struct.pack("<QQQQ", amount_a_units, amount_b_units, min_amount_a_units, min_amount_b_units)
    elif operation_key == "remove":
        liquidity_units = str(request.get("liquidityUnits") or "").strip()
        if liquidity_units:
            payload = struct.pack("<Q", _parse_u64(liquidity_units, field="liquidityUnits"))
        else:
            percent = _parse_u64(request.get("percent"), field="percent")
            payload = struct.pack("<Q", percent)
    elif operation_key in {"claim_fees", "claim_rewards"}:
        token_id = str(request.get("positionId") or request.get("tokenId") or "").strip()
        if not token_id:
            raise SolanaRuntimeError("invalid_input", "positionId is required for claim operations.")
        payload = struct.pack("<Q", _parse_u64(token_id, field="positionId"))
    else:
        payload = b""
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
    program_ids = adapter_metadata.get("programIds") if isinstance(adapter_metadata.get("programIds"), dict) else {}
    pool = _resolve_pool_ref(adapter_metadata, request)
    route_kind = "pool_direct"
    migration_mode = "single_step"

    def _build_single(op_key: str, *, op_request: dict[str, Any] | None = None) -> SolanaInstructionPlan:
        operation = _operation_entry(operations, op_key)
        if not isinstance(operation, dict):
            raise SolanaRuntimeError("unsupported_liquidity_operation", f"Raydium operation '{op_key}' is not configured.")
        program_id = str(operation.get("programId") or program_ids.get("clmm") or "").strip()
        if not program_id:
            raise SolanaRuntimeError("chain_config_invalid", f"Raydium {op_key} is missing programId/programIds.clmm.")
        _ensure_pool_exists(chain, rpc_url, pool, expected_owner_program=program_id)
        req = dict(request)
        if isinstance(op_request, dict):
            req.update(op_request)
        if op_key == "claim_rewards":
            rewards = req.get("rewardContracts")
            if not isinstance(rewards, list) or not [str(item or "").strip() for item in rewards if str(item or "").strip()]:
                rewards = operation.get("rewardContracts")
            normalized_rewards = [str(item or "").strip() for item in (rewards or []) if str(item or "").strip()]
            if not normalized_rewards:
                raise SolanaRuntimeError("claim_rewards_not_configured", "Raydium claim-rewards requires rewardContracts metadata.")
            req["rewardContracts"] = normalized_rewards
        return SolanaInstructionPlan(
            program_id=program_id,
            accounts=_build_accounts(operation, owner=owner, pool=pool, request=req),
            data_hex=_build_instruction_data(operation, req, op_key),
            operation_key=op_key,
            route_kind="pool_direct",
        )

    instructions: list[SolanaInstructionPlan]
    if operation_key == "migrate":
        target_adapter_key = str(request.get("targetAdapterKey") or "").strip()
        if not target_adapter_key:
            migrate_cfg = _operation_entry(operations, "migrate") or {}
            target_adapter_key = str(migrate_cfg.get("targetAdapterKey") or "").strip()
        if not target_adapter_key:
            raise SolanaRuntimeError("migration_target_not_configured", "Raydium migrate targetAdapterKey is not configured.")
        instructions = [_build_single("remove"), _build_single("claim_fees")]
        target_recreate = bool(request.get("targetRecreate"))
        if target_recreate:
            instructions.append(_build_single("increase"))
            route_kind = "migration"
            migration_mode = "decrease_collect_recreate"
        else:
            route_kind = "position_manager"
            migration_mode = "withdraw_only"
    else:
        instructions = [_build_single(operation_key)]

    for index, entry in enumerate(instructions):
        instructions[index] = SolanaInstructionPlan(
            program_id=entry.program_id,
            accounts=entry.accounts,
            data_hex=entry.data_hex,
            operation_key=entry.operation_key,
            route_kind=route_kind,
        )

    return RaydiumExecutionPlan(
        pool=pool,
        instructions=instructions,
        details={
            "poolId": pool.pool_id,
            "tokenA": pool.token_a,
            "tokenB": pool.token_b,
            "feeBps": pool.fee_bps,
            "operationKey": operation_key,
            "migrationMode": migration_mode if operation_key == "migrate" else None,
            "instructionOps": [item.operation_key for item in instructions],
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
