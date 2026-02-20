#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import pathlib
import sys
import urllib.request
from typing import Any


def _bootstrap_runtime_imports() -> None:
    runtime_root = pathlib.Path(__file__).resolve().parents[2]
    if str(runtime_root) not in sys.path:
        sys.path.insert(0, str(runtime_root))


_bootstrap_runtime_imports()

from hedera import AccountId, Client, Hbar, PrivateKey, TransferTransaction  # noqa: E402
from xclaw_agent import cli as runtime_cli  # noqa: E402


class BridgeError(Exception):
    pass


def _as_json_input(raw: str) -> dict[str, Any]:
    try:
        payload = json.loads(raw or "{}")
    except Exception as exc:
        raise BridgeError("invalid_bridge_input_json") from exc
    if not isinstance(payload, dict):
        raise BridgeError("bridge_input_must_be_object")
    return payload


def _network_client(chain: str, operator: AccountId, private_key: PrivateKey) -> Client:
    chain_key = str(chain or "").strip().lower()
    if chain_key.endswith("testnet"):
        client = Client.forTestnet()
    elif chain_key.endswith("mainnet"):
        client = Client.forMainnet()
    elif chain_key.endswith("previewnet"):
        client = Client.forPreviewnet()
    else:
        raise BridgeError(f"unsupported_chain:{chain_key}")
    client.setOperator(operator, private_key)
    return client


def _operator_from_wallet(chain: str) -> tuple[AccountId, PrivateKey, str]:
    store = runtime_cli.load_wallet_store()
    wallet_address, private_key_hex = runtime_cli._execution_wallet(store, chain)
    account_id = _resolve_account_id_for_evm(chain, wallet_address)
    private_key = PrivateKey.fromStringECDSA(private_key_hex)
    return account_id, private_key, wallet_address


def _mirror_base_url(chain: str) -> str:
    key = str(chain or "").strip().lower()
    if key.endswith("testnet"):
        return "https://testnet.mirrornode.hedera.com"
    if key.endswith("mainnet"):
        return "https://mainnet-public.mirrornode.hedera.com"
    if key.endswith("previewnet"):
        return "https://previewnet.mirrornode.hedera.com"
    raise BridgeError(f"unsupported_chain:{chain}")


def _resolve_account_id_for_evm(chain: str, wallet_address: str) -> AccountId:
    override = str(os.environ.get("XCLAW_HEDERA_ACCOUNT_ID") or "").strip()
    if override:
        try:
            return AccountId.fromString(override)
        except Exception as exc:
            raise BridgeError("invalid_operator_account_id") from exc

    url = f"{_mirror_base_url(chain)}/api/v1/accounts/{wallet_address}"
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise BridgeError("mirror_account_lookup_failed") from exc
    account_text = str(payload.get("account") or "").strip()
    if not account_text:
        raise BridgeError("missing_operator_account_id")
    try:
        return AccountId.fromString(account_text)
    except Exception as exc:
        raise BridgeError("invalid_operator_account_id") from exc


def _tx_hash_hex(transaction_hash: Any) -> str:
    if transaction_hash is None:
        return ""
    if isinstance(transaction_hash, bytes):
        return transaction_hash.hex()
    if isinstance(transaction_hash, bytearray):
        return bytes(transaction_hash).hex()
    if isinstance(transaction_hash, list):
        try:
            return bytes(int(v) & 0xFF for v in transaction_hash).hex()
        except Exception:
            return ""
    if hasattr(transaction_hash, "tolist"):
        try:
            values = transaction_hash.tolist()
            return bytes(int(v) & 0xFF for v in values).hex()
        except Exception:
            return ""
    text = str(transaction_hash).strip()
    if text.startswith("0x") and len(text) > 2:
        return text[2:]
    return ""


def _target_account() -> AccountId:
    raw = str(os.environ.get("XCLAW_HEDERA_HTS_BRIDGE_TARGET_ACCOUNT") or "0.0.3").strip()
    try:
        return AccountId.fromString(raw)
    except Exception as exc:
        raise BridgeError("invalid_target_account") from exc


def _transfer_tinybar_amount(action: str) -> int:
    if action == "add":
        key = "XCLAW_HEDERA_HTS_BRIDGE_ADD_TINYBAR"
    elif action == "remove":
        key = "XCLAW_HEDERA_HTS_BRIDGE_REMOVE_TINYBAR"
    elif action == "claim_fees":
        key = "XCLAW_HEDERA_HTS_BRIDGE_CLAIM_FEES_TINYBAR"
    else:
        key = "XCLAW_HEDERA_HTS_BRIDGE_CLAIM_REWARDS_TINYBAR"
    raw = str(os.environ.get(key) or os.environ.get("XCLAW_HEDERA_HTS_BRIDGE_TINYBAR") or "1").strip()
    try:
        amount = int(raw)
    except Exception as exc:
        raise BridgeError("invalid_tinybar_amount") from exc
    if amount <= 0:
        raise BridgeError("invalid_tinybar_amount")
    return amount


def _execute_hts_action(request: dict[str, Any]) -> dict[str, Any]:
    action = str(request.get("action") or "").strip().lower()
    if action not in {"add", "remove", "claim_fees", "claim_rewards"}:
        raise BridgeError("unsupported_action")
    chain = str(request.get("chain") or "").strip()
    if not chain:
        raise BridgeError("missing_chain")

    operator, private_key, wallet_address = _operator_from_wallet(chain)
    client = _network_client(chain, operator, private_key)
    target = _target_account()
    amount = _transfer_tinybar_amount(action)
    memo = f"xclaw_hts_{action}"

    tx = (
        TransferTransaction()
        .addHbarTransfer(operator, Hbar.fromTinybars(-amount))
        .addHbarTransfer(target, Hbar.fromTinybars(amount))
        .setTransactionMemo(memo)
    )

    response = tx.execute(client)
    receipt = response.getReceipt(client)
    status_obj = getattr(receipt, "status", None)
    if status_obj is None:
        raise BridgeError("missing_receipt_status")
    status_text = str(status_obj.toString()).strip().upper() if hasattr(status_obj, "toString") else str(status_obj).strip().upper()
    if status_text != "SUCCESS":
        raise BridgeError(f"hedera_status:{status_text}")

    tx_hash = _tx_hash_hex(getattr(response, "transactionHash", None))
    if not tx_hash:
        tx_id_obj = getattr(response, "transactionId", None)
        tx_hash = tx_id_obj.toString() if hasattr(tx_id_obj, "toString") else str(tx_id_obj or "").strip()
    if not tx_hash:
        raise BridgeError("missing_tx_hash")

    details = {
        "mode": "hts_native",
        "action": action,
        "chain": chain,
        "memo": memo,
        "walletAddress": wallet_address.lower(),
        "targetAccount": target.toString() if hasattr(target, "toString") else str(target),
        "tinybarAmount": amount,
        "transactionId": (
            response.transactionId.toString()
            if hasattr(getattr(response, "transactionId", None), "toString")
            else str(getattr(response, "transactionId", "")).strip()
        ),
    }
    out: dict[str, Any] = {"txHash": tx_hash, "details": details}
    if action == "add":
        out["positionId"] = tx_hash
    return out


def main() -> int:
    try:
        request = _as_json_input(sys.stdin.read())
        out = _execute_hts_action(request)
        sys.stdout.write(json.dumps(out, separators=(",", ":")) + "\n")
        return 0
    except BridgeError as exc:
        sys.stderr.write(f"{exc}\n")
        return 1
    except Exception:
        sys.stderr.write("bridge_internal_error\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
