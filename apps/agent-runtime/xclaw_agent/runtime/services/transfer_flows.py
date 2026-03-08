from __future__ import annotations

import json
import os
import pathlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable


@dataclass(frozen=True)
class TransferFlowContext:
    ensure_app_dir: Callable[[], None]
    flows_file: pathlib.Path
    json_module: Any
    os_module: Any
    pathlib_module: Any
    utc_now: Callable[[], str]
    is_solana_chain: Callable[[str], bool]
    is_solana_address: Callable[[str], bool]
    is_hex_address: Callable[[str], bool]
    transfer_executing_stale_sec: Callable[[], int]
    evaluate_outbound_transfer_policy: Callable[[str, str], dict[str, Any]]
    watcher_run_id: Callable[[], str]
    record_pending_transfer_flow: Callable[[str, dict[str, Any]], None]
    mirror_transfer_approval: Callable[[dict[str, Any]], bool]
    remove_pending_transfer_flow: Callable[[str], None]
    transfer_amount_display: Callable[[str | int, str, str | None, int | None], tuple[str, str]]
    enforce_spend_preconditions: Callable[..., Any]
    load_wallet_store: Callable[[], dict[str, Any]]
    chain_wallet: Callable[[dict[str, Any], str], tuple[str | None, dict[str, Any] | None]]
    validate_wallet_entry_shape: Callable[[dict[str, Any]], None]
    fetch_token_balance_wei: Callable[[str, str, str], str]
    fetch_native_balance_wei: Callable[[str, str], str]
    assert_transfer_balance_preconditions: Callable[..., None]
    require_wallet_passphrase_for_signing: Callable[[str], str]
    decrypt_private_key: Callable[[dict[str, Any], str], bytes]
    chain_rpc_url: Callable[[str], str]
    solana_send_native_transfer: Callable[..., str]
    solana_send_spl_transfer: Callable[..., dict[str, Any]]
    cast_rpc_send_transaction: Callable[..., str]
    require_cast_bin: Callable[[], str]
    run_subprocess: Callable[..., Any]
    cast_receipt_timeout_sec: Callable[[], int]
    cast_calldata: Callable[..., str]
    record_spend: Callable[..., None]
    builder_output_from_hashes: Callable[[str, list[str]], dict[str, Any]]
    re_module: Any
    json_loads: Callable[[str], Any]
    wallet_store_error: type[BaseException]


def load_pending_transfer_flows(ctx: TransferFlowContext) -> dict[str, Any]:
    try:
        ctx.ensure_app_dir()
        if not ctx.flows_file.exists():
            return {"version": 1, "flows": {}}
        raw = ctx.flows_file.read_text(encoding="utf-8")
        payload = ctx.json_module.loads(raw or "{}")
        if not isinstance(payload, dict):
            return {"version": 1, "flows": {}}
        flows = payload.get("flows")
        if not isinstance(flows, dict):
            payload["flows"] = {}
        if payload.get("version") != 1:
            return {"version": 1, "flows": {}}
        return payload
    except Exception:
        return {"version": 1, "flows": {}}



def save_pending_transfer_flows(ctx: TransferFlowContext, payload: dict[str, Any]) -> None:
    ctx.ensure_app_dir()
    if payload.get("version") != 1:
        payload["version"] = 1
    if not isinstance(payload.get("flows"), dict):
        payload["flows"] = {}
    tmp = f"{ctx.flows_file}.{ctx.os_module.getpid()}.tmp"
    ctx.pathlib_module.Path(tmp).write_text(ctx.json_module.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    if ctx.os_module.name != "nt":
        ctx.os_module.chmod(tmp, 0o600)
    ctx.pathlib_module.Path(tmp).replace(ctx.flows_file)
    if ctx.os_module.name != "nt":
        ctx.os_module.chmod(ctx.flows_file, 0o600)



def get_pending_transfer_flow(ctx: TransferFlowContext, approval_id: str) -> dict[str, Any] | None:
    state = load_pending_transfer_flows(ctx)
    flows = state.get("flows")
    if not isinstance(flows, dict):
        return None
    entry = flows.get(approval_id)
    return entry if isinstance(entry, dict) else None



def record_pending_transfer_flow(ctx: TransferFlowContext, approval_id: str, entry: dict[str, Any]) -> None:
    state = load_pending_transfer_flows(ctx)
    flows = state.get("flows")
    if not isinstance(flows, dict):
        flows = {}
        state["flows"] = flows
    flows[approval_id] = {**entry, "updatedAt": ctx.utc_now()}
    save_pending_transfer_flows(ctx, state)



def remove_pending_transfer_flow(ctx: TransferFlowContext, approval_id: str) -> None:
    state = load_pending_transfer_flows(ctx)
    flows = state.get("flows")
    if not isinstance(flows, dict):
        return
    if approval_id in flows:
        flows.pop(approval_id, None)
        save_pending_transfer_flows(ctx, state)



def parse_iso_utc(value: str | None) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    normalized = raw.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except Exception:
        return None



def is_stale_executing_transfer_flow(ctx: TransferFlowContext, flow: dict[str, Any]) -> bool:
    status = str(flow.get("status") or "")
    if status not in {"executing", "verifying"}:
        return False
    if str(flow.get("txHash") or "").strip():
        return False
    updated_at = parse_iso_utc(str(flow.get("updatedAt") or flow.get("decidedAt") or flow.get("createdAt") or ""))
    if updated_at is None:
        return True
    age_sec = (datetime.now(timezone.utc) - updated_at).total_seconds()
    return age_sec >= float(ctx.transfer_executing_stale_sec())



def assert_transfer_balance_preconditions(
    ctx: TransferFlowContext,
    *,
    chain: str,
    transfer_type: str,
    wallet_address: str,
    amount_wei: str,
    token_address: str | None,
    token_symbol: str | None,
    token_decimals: int | None,
) -> None:
    amount_int = int(str(amount_wei).strip())
    if amount_int <= 0:
        raise ctx.wallet_store_error("Transfer amount must be greater than zero.")
    if transfer_type == "token":
        if not token_address:
            raise ctx.wallet_store_error("Transfer token address is required.")
        balance_wei = int(ctx.fetch_token_balance_wei(chain, wallet_address, token_address))
        if balance_wei < amount_int:
            amount_human, amount_unit = ctx.transfer_amount_display(amount_wei, transfer_type, token_symbol, token_decimals)
            raise ctx.wallet_store_error(f"Insufficient {amount_unit} balance for transfer of {amount_human} {amount_unit}.")
        return
    native_balance = int(ctx.fetch_native_balance_wei(chain, wallet_address))
    if native_balance < amount_int:
        amount_human, amount_unit = ctx.transfer_amount_display(amount_wei, transfer_type, token_symbol, token_decimals)
        raise ctx.wallet_store_error(f"Insufficient {amount_unit} balance for transfer of {amount_human} {amount_unit}.")



def execute_pending_transfer_flow(ctx: TransferFlowContext, flow: dict[str, Any]) -> dict[str, Any]:
    approval_id = str(flow.get("approvalId") or "").strip()
    chain = str(flow.get("chainKey") or "").strip()
    transfer_type = str(flow.get("transferType") or "native").strip().lower()
    amount_wei = str(flow.get("amountWei") or "0").strip()
    to_address = str(flow.get("toAddress") or "").strip()
    token_address = str(flow.get("tokenAddress") or "").strip().lower() if transfer_type == "token" else None
    token_symbol = str(flow.get("tokenSymbol") or ("NATIVE" if transfer_type == "native" else "TOKEN")).strip()
    token_decimals_raw = flow.get("tokenDecimals", 18 if transfer_type == "native" else None)
    try:
        token_decimals = int(token_decimals_raw) if token_decimals_raw is not None else None
    except Exception:
        token_decimals = 18 if transfer_type == "native" else None
    amount_human, amount_unit = ctx.transfer_amount_display(amount_wei, transfer_type, token_symbol, token_decimals)
    amount_display = f"{amount_human} {amount_unit}"
    is_solana = ctx.is_solana_chain(chain)
    if not approval_id or not chain:
        return {"ok": False, "code": "invalid_state", "message": "Missing approvalId/chain in transfer flow."}
    if not ctx.re_module.fullmatch(r"[0-9]+", amount_wei):
        return {"ok": False, "code": "invalid_state", "message": "Transfer flow amountWei must be uint."}
    if is_solana:
        if not ctx.is_solana_address(to_address):
            return {"ok": False, "code": "invalid_state", "message": "Transfer flow destination is invalid."}
    elif not ctx.is_hex_address(to_address):
        return {"ok": False, "code": "invalid_state", "message": "Transfer flow destination is invalid."}
    if transfer_type == "token":
        if is_solana:
            if not token_address or not ctx.is_solana_address(token_address):
                return {"ok": False, "code": "invalid_state", "message": "Transfer token address is invalid."}
        elif not token_address or not ctx.is_hex_address(token_address):
            return {"ok": False, "code": "invalid_state", "message": "Transfer token address is invalid."}

    outbound_eval = ctx.evaluate_outbound_transfer_policy(chain, to_address)
    policy_blocked_now = not bool(outbound_eval.get("allowed"))
    policy_blocked_at_create = bool(flow.get("policyBlockedAtCreate", False))
    force_policy_override = bool(flow.get("forcePolicyOverride", False))
    execution_mode = "policy_override" if force_policy_override else "normal"
    if not force_policy_override and policy_blocked_now:
        if not policy_blocked_at_create:
            return {
                "ok": False,
                "code": "not_actionable",
                "message": "Transfer is no longer actionable because outbound transfer policy now blocks it.",
                "approvalId": approval_id,
                "chain": chain,
                "status": str(flow.get("status") or "approval_pending"),
                "policyBlockedAtCreate": policy_blocked_at_create,
                "policyBlockReasonCode": outbound_eval.get("policyBlockReasonCode"),
                "policyBlockReasonMessage": outbound_eval.get("policyBlockReasonMessage"),
            }
        execution_mode = "policy_override"
    flow["executionMode"] = execution_mode
    flow["status"] = "executing"
    flow["updatedAt"] = ctx.utc_now()
    flow["observedBy"] = "agent_watcher"
    flow["observationSource"] = "local_send_result"
    flow["observedAt"] = flow["updatedAt"]
    flow["watcherRunId"] = ctx.watcher_run_id()
    flow["confirmationCount"] = None
    ctx.record_pending_transfer_flow(approval_id, flow)
    ctx.mirror_transfer_approval(flow)

    from_address: str | None = None
    try:
        amount_int = int(amount_wei)
        state, day_key, current_spend, max_daily_wei = ctx.enforce_spend_preconditions(chain, amount_int)
        transfer_policy = {
            "outboundTransfersEnabled": bool(outbound_eval.get("outboundTransfersEnabled")),
            "outboundMode": str(outbound_eval.get("outboundMode") or "disabled"),
            "outboundWhitelistAddresses": list(outbound_eval.get("outboundWhitelistAddresses") or []),
            "updatedAt": outbound_eval.get("updatedAt"),
            "policyBlockedAtCreate": policy_blocked_at_create,
            "policyBlockReasonCode": flow.get("policyBlockReasonCode") or outbound_eval.get("policyBlockReasonCode"),
            "policyBlockReasonMessage": flow.get("policyBlockReasonMessage") or outbound_eval.get("policyBlockReasonMessage"),
            "executionMode": execution_mode,
            "forcePolicyOverride": force_policy_override,
        }
        store = ctx.load_wallet_store()
        _, wallet = ctx.chain_wallet(store, chain)
        if wallet is None:
            raise ctx.wallet_store_error(f"No wallet configured for chain '{chain}'.")
        ctx.validate_wallet_entry_shape(wallet)
        from_address = str(wallet.get("address"))
        ctx.assert_transfer_balance_preconditions(
            chain=chain,
            transfer_type=transfer_type,
            wallet_address=from_address,
            amount_wei=amount_wei,
            token_address=token_address,
            token_symbol=token_symbol,
            token_decimals=token_decimals,
        )
        passphrase = ctx.require_wallet_passphrase_for_signing(chain)
        private_key_bytes = ctx.decrypt_private_key(wallet, passphrase)

        if is_solana:
            rpc_url = ctx.chain_rpc_url(chain)
            if transfer_type == "native":
                tx_hash = ctx.solana_send_native_transfer(rpc_url, private_key_bytes, to_address, int(amount_wei))
            else:
                result = ctx.solana_send_spl_transfer(rpc_url, private_key_bytes, to_address, str(token_address), int(amount_wei))
                tx_hash = str(result.get("signature") or "")
                if token_decimals is None and isinstance(result.get("decimals"), int):
                    token_decimals = int(result.get("decimals"))
                flow["solanaTransfer"] = result
        else:
            rpc_url = ctx.chain_rpc_url(chain)
            private_key_hex = private_key_bytes.hex()
            if transfer_type == "native":
                tx_hash = ctx.cast_rpc_send_transaction(
                    rpc_url,
                    {"from": from_address, "to": to_address, "value": amount_wei, "data": "0x"},
                    private_key_hex,
                    chain=chain,
                )
                cast_bin = ctx.require_cast_bin()
                receipt_proc = ctx.run_subprocess(
                    [cast_bin, "receipt", "--json", "--rpc-url", rpc_url, tx_hash],
                    timeout_sec=ctx.cast_receipt_timeout_sec(),
                    kind="cast_receipt",
                )
                if receipt_proc.returncode != 0:
                    stderr = (receipt_proc.stderr or "").strip()
                    stdout = (receipt_proc.stdout or "").strip()
                    raise ctx.wallet_store_error(stderr or stdout or "cast receipt failed.")
            else:
                data = ctx.cast_calldata("transfer(address,uint256)(bool)", [to_address, amount_wei])
                tx_hash = ctx.cast_rpc_send_transaction(
                    rpc_url,
                    {"from": from_address, "to": str(token_address), "data": data},
                    private_key_hex,
                    chain=chain,
                )
                cast_bin = ctx.require_cast_bin()
                receipt_proc = ctx.run_subprocess(
                    [cast_bin, "receipt", "--json", "--rpc-url", rpc_url, tx_hash],
                    timeout_sec=ctx.cast_receipt_timeout_sec(),
                    kind="cast_receipt",
                )
                if receipt_proc.returncode != 0:
                    stderr = (receipt_proc.stderr or "").strip()
                    stdout = (receipt_proc.stdout or "").strip()
                    raise ctx.wallet_store_error(stderr or stdout or "cast receipt failed.")
                receipt_payload = ctx.json_loads((receipt_proc.stdout or "{}").strip() or "{}")
                receipt_status = str(receipt_payload.get("status", "0x0")).lower()
                if receipt_status not in {"0x1", "1"}:
                    raise ctx.wallet_store_error(f"On-chain receipt indicates failure status '{receipt_status}'.")

        ctx.record_spend(state, chain, day_key, current_spend + amount_int)
        flow["status"] = "filled"
        flow["txHash"] = tx_hash
        flow["updatedAt"] = ctx.utc_now()
        flow["terminalAt"] = flow["updatedAt"]
        flow["observedBy"] = "agent_watcher"
        flow["observationSource"] = "rpc_receipt"
        flow["observedAt"] = flow["updatedAt"]
        flow["watcherRunId"] = ctx.watcher_run_id()
        flow["confirmationCount"] = 1
        ctx.record_pending_transfer_flow(approval_id, flow)
        ctx.mirror_transfer_approval(flow)
        ctx.remove_pending_transfer_flow(approval_id)
        builder_meta = ctx.builder_output_from_hashes(chain, [tx_hash])
        return {
            "ok": True,
            "code": "ok",
            "message": "Transfer executed.",
            "approvalId": approval_id,
            "chain": chain,
            "status": "filled",
            "transferType": transfer_type,
            "tokenAddress": token_address,
            "tokenSymbol": token_symbol,
            "tokenDecimals": token_decimals,
            "to": to_address,
            "amountWei": amount_wei,
            "amount": amount_human,
            "amountUnit": amount_unit,
            "amountDisplay": amount_display,
            "from": from_address,
            "txHash": tx_hash,
            "signature": tx_hash if is_solana else None,
            "day": day_key,
            "dailySpendWei": str(current_spend + amount_int),
            "maxDailyNativeWei": str(max_daily_wei),
            "transferPolicy": transfer_policy,
            "policyBlockedAtCreate": policy_blocked_at_create,
            "policyBlockReasonCode": flow.get("policyBlockReasonCode"),
            "policyBlockReasonMessage": flow.get("policyBlockReasonMessage"),
            "executionMode": execution_mode,
            **builder_meta,
        }
    except Exception as exc:
        message = str(exc) or "Transfer execution failed."
        flow["status"] = "failed"
        flow["reasonCode"] = "transfer_execution_failed"
        flow["reasonMessage"] = message
        flow["updatedAt"] = ctx.utc_now()
        flow["terminalAt"] = flow["updatedAt"]
        flow["observedBy"] = "agent_watcher"
        flow["observationSource"] = "rpc_receipt"
        flow["observedAt"] = flow["updatedAt"]
        flow["watcherRunId"] = ctx.watcher_run_id()
        ctx.record_pending_transfer_flow(approval_id, flow)
        ctx.mirror_transfer_approval(flow)
        return {
            "ok": False,
            "code": "transfer_execution_failed",
            "message": message,
            "approvalId": approval_id,
            "chain": chain,
            "status": "failed",
            "transferType": transfer_type,
            "tokenAddress": token_address,
            "tokenSymbol": token_symbol,
            "tokenDecimals": token_decimals,
            "to": to_address,
            "amountWei": amount_wei,
            "amount": amount_human,
            "amountUnit": amount_unit,
            "amountDisplay": amount_display,
            "from": from_address,
            "txHash": flow.get("txHash"),
            "signature": flow.get("txHash") if is_solana else None,
            "reasonCode": "transfer_execution_failed",
            "reasonMessage": message,
            "policyBlockedAtCreate": policy_blocked_at_create,
            "policyBlockReasonCode": flow.get("policyBlockReasonCode"),
            "policyBlockReasonMessage": flow.get("policyBlockReasonMessage"),
            "executionMode": execution_mode,
        }
