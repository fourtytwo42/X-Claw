from __future__ import annotations

import base64
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

try:
    from solders.hash import Hash
    from solders.keypair import Keypair
    from solders.pubkey import Pubkey
    from solders.system_program import TransferParams, transfer
    from solders.transaction import Transaction, VersionedTransaction
except Exception:  # pragma: no cover - runtime dependency gate
    Hash = None  # type: ignore[assignment]
    Keypair = None  # type: ignore[assignment]
    Pubkey = None  # type: ignore[assignment]
    TransferParams = None  # type: ignore[assignment]
    Transaction = None  # type: ignore[assignment]
    VersionedTransaction = None  # type: ignore[assignment]
    transfer = None  # type: ignore[assignment]

try:
    from spl.token.constants import TOKEN_PROGRAM_ID
    from spl.token.instructions import (
        TransferCheckedParams,
        create_associated_token_account,
        get_associated_token_address,
        transfer_checked,
    )
except Exception:  # pragma: no cover - runtime dependency gate
    TOKEN_PROGRAM_ID = None  # type: ignore[assignment]
    TransferCheckedParams = None  # type: ignore[assignment]
    create_associated_token_account = None  # type: ignore[assignment]
    get_associated_token_address = None  # type: ignore[assignment]
    transfer_checked = None  # type: ignore[assignment]

SOLANA_CHAIN_KEYS = {"solana_devnet", "solana_testnet", "solana_mainnet_beta"}


class SolanaRuntimeError(Exception):
    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = str(code or "solana_runtime_error").strip() or "solana_runtime_error"
        self.details = details or {}


@dataclass(frozen=True)
class SolanaQuote:
    amount_out_units: str
    route_kind: str
    quote_payload: dict[str, Any]


def _require_solana_dependencies() -> None:
    if Keypair is None or Pubkey is None or Hash is None or Transaction is None or VersionedTransaction is None:
        raise SolanaRuntimeError(
            "missing_dependency",
            "Solana runtime dependencies are missing (solders).",
            {"dependency": "solders"},
        )
    if (
        TOKEN_PROGRAM_ID is None
        or TransferCheckedParams is None
        or create_associated_token_account is None
        or get_associated_token_address is None
        or transfer_checked is None
    ):
        raise SolanaRuntimeError(
            "missing_dependency",
            "SPL token runtime dependencies are missing (solana/spl-token Python packages).",
            {"dependency": "solana"},
        )


def is_solana_chain_key(chain_key: str) -> bool:
    return str(chain_key or "").strip().lower() in SOLANA_CHAIN_KEYS


def is_solana_address(value: str) -> bool:
    try:
        _require_solana_dependencies()
        Pubkey.from_string(str(value or "").strip())
        return True
    except Exception:
        return False


def _rpc_post(rpc_url: str, method: str, params: list[Any]) -> Any:
    payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode("utf-8")
    req = urllib.request.Request(
        rpc_url,
        data=payload,
        headers={"content-type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            parsed = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise SolanaRuntimeError(
            "rpc_unavailable",
            f"Solana RPC {method} failed with HTTP {exc.code}.",
            {"method": method, "status": int(exc.code)},
        ) from exc
    except Exception as exc:
        raise SolanaRuntimeError(
            "rpc_unavailable",
            f"Solana RPC {method} request failed.",
            {"method": method, "error": str(exc)},
        ) from exc
    if isinstance(parsed, dict) and parsed.get("error"):
        msg = str(parsed["error"].get("message") or f"RPC {method} returned an error.")
        raise SolanaRuntimeError("rpc_unavailable", msg, {"method": method, "error": parsed.get("error")})
    if not isinstance(parsed, dict) or "result" not in parsed:
        raise SolanaRuntimeError("rpc_unavailable", f"Solana RPC {method} returned malformed payload.", {"method": method})
    return parsed.get("result")


def generate_wallet() -> dict[str, str]:
    _require_solana_dependencies()
    kp = Keypair()
    return {
        "address": str(kp.pubkey()),
        "private_key": str(kp),
        "format": "base58_64byte_secret",
    }


def import_wallet_private_key(value: str) -> dict[str, Any]:
    _require_solana_dependencies()
    raw = str(value or "").strip()
    if not raw:
        raise SolanaRuntimeError("invalid_input", "Solana private key input is required.")

    if raw.startswith("[") and raw.endswith("]"):
        try:
            arr = json.loads(raw)
        except Exception as exc:
            raise SolanaRuntimeError("invalid_input", "Invalid Solana key array JSON.") from exc
        if not isinstance(arr, list) or len(arr) != 64 or any(not isinstance(x, int) or x < 0 or x > 255 for x in arr):
            raise SolanaRuntimeError("invalid_input", "Solana key array must contain exactly 64 byte integers.")
        keypair = Keypair.from_bytes(bytes(arr))
    else:
        try:
            keypair = Keypair.from_base58_string(raw)
        except Exception as exc:
            raise SolanaRuntimeError(
                "invalid_input",
                "Solana private key must be a base58 secret key string or 64-byte JSON array.",
            ) from exc

    return {
        "address": str(keypair.pubkey()),
        "secret_bytes": bytes(keypair),
    }


def sign_message(private_key_bytes: bytes, message: str) -> str:
    _require_solana_dependencies()
    keypair = Keypair.from_bytes(private_key_bytes)
    signature = keypair.sign_message(message.encode("utf-8"))
    return str(signature)


def get_latest_blockhash(rpc_url: str) -> str:
    result = _rpc_post(rpc_url, "getLatestBlockhash", [{"commitment": "confirmed"}])
    value = result.get("value") if isinstance(result, dict) else None
    blockhash = str((value or {}).get("blockhash") or "").strip()
    if not blockhash:
        raise SolanaRuntimeError("rpc_unavailable", "Solana RPC getLatestBlockhash did not return blockhash.")
    return blockhash


def get_balance_lamports(rpc_url: str, address: str) -> int:
    result = _rpc_post(rpc_url, "getBalance", [address, {"commitment": "confirmed"}])
    lamports = int((result or {}).get("value") or 0)
    return max(0, lamports)


def get_token_balances(rpc_url: str, owner_address: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    result = _rpc_post(
        rpc_url,
        "getTokenAccountsByOwner",
        [owner_address, {"programId": str(TOKEN_PROGRAM_ID)}, {"encoding": "jsonParsed", "commitment": "confirmed"}],
    )
    rows = result.get("value") if isinstance(result, dict) else []
    if not isinstance(rows, list):
        rows = []
    tokens: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for row in rows:
        try:
            parsed = (((row or {}).get("account") or {}).get("data") or {}).get("parsed") or {}
            info = parsed.get("info") or {}
            mint = str(info.get("mint") or "").strip()
            token_amount = info.get("tokenAmount") or {}
            amount = str(token_amount.get("amount") or "0")
            decimals = int(token_amount.get("decimals") or 0)
            ui_amount_string = str(token_amount.get("uiAmountString") or "0")
            if not mint:
                continue
            tokens.append(
                {
                    "token": mint,
                    "symbol": None,
                    "name": None,
                    "decimals": decimals,
                    "balanceWei": amount,
                    "balance": ui_amount_string,
                }
            )
        except Exception as exc:
            errors.append({"error": str(exc)})
    return tokens, errors


def _wait_signature_status(rpc_url: str, signature: str, timeout_sec: int = 45) -> None:
    start = time.time()
    while True:
        result = _rpc_post(
            rpc_url,
            "getSignatureStatuses",
            [[signature], {"searchTransactionHistory": True}],
        )
        value = result.get("value") if isinstance(result, dict) else None
        status = value[0] if isinstance(value, list) and value else None
        if isinstance(status, dict):
            if status.get("err") is not None:
                raise SolanaRuntimeError("transaction_failed", "Solana transaction execution failed.", {"signature": signature, "err": status.get("err")})
            confirmation_status = str(status.get("confirmationStatus") or "")
            if confirmation_status in {"confirmed", "finalized"}:
                return
        if time.time() - start > timeout_sec:
            raise SolanaRuntimeError("tx_receipt_timeout", "Timed out waiting for Solana transaction confirmation.", {"signature": signature})
        time.sleep(1.0)


def _send_raw_tx(rpc_url: str, tx_bytes: bytes) -> str:
    encoded = base64.b64encode(tx_bytes).decode("ascii")
    result = _rpc_post(
        rpc_url,
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
    )
    signature = str(result or "").strip()
    if not signature:
        raise SolanaRuntimeError("rpc_unavailable", "Solana sendTransaction returned empty signature.")
    _wait_signature_status(rpc_url, signature)
    return signature


def send_native_transfer(rpc_url: str, private_key_bytes: bytes, to_address: str, lamports: int) -> str:
    _require_solana_dependencies()
    if lamports <= 0:
        raise SolanaRuntimeError("invalid_amount", "Transfer amount must be positive.")
    keypair = Keypair.from_bytes(private_key_bytes)
    destination = Pubkey.from_string(str(to_address or "").strip())
    source = keypair.pubkey()
    blockhash = Hash.from_string(get_latest_blockhash(rpc_url))
    ix = transfer(TransferParams(from_pubkey=source, to_pubkey=destination, lamports=lamports))
    tx = Transaction.new_signed_with_payer([ix], source, [keypair], blockhash)
    return _send_raw_tx(rpc_url, bytes(tx))


def _mint_decimals(rpc_url: str, mint: Pubkey) -> int:
    result = _rpc_post(rpc_url, "getTokenSupply", [str(mint), {"commitment": "confirmed"}])
    value = result.get("value") if isinstance(result, dict) else {}
    decimals = int((value or {}).get("decimals") or 0)
    if decimals < 0 or decimals > 18:
        raise SolanaRuntimeError("chain_config_invalid", "Invalid mint decimals from RPC.", {"mint": str(mint), "decimals": decimals})
    return decimals


def _account_exists(rpc_url: str, address: Pubkey) -> bool:
    result = _rpc_post(rpc_url, "getAccountInfo", [str(address), {"encoding": "base64", "commitment": "confirmed"}])
    return bool((result or {}).get("value"))


def send_spl_transfer(rpc_url: str, private_key_bytes: bytes, to_address: str, mint_address: str, amount_units: int) -> dict[str, Any]:
    _require_solana_dependencies()
    if amount_units <= 0:
        raise SolanaRuntimeError("invalid_amount", "Token transfer amount must be positive.")

    signer = Keypair.from_bytes(private_key_bytes)
    owner = signer.pubkey()
    recipient = Pubkey.from_string(str(to_address or "").strip())
    mint = Pubkey.from_string(str(mint_address or "").strip())
    decimals = _mint_decimals(rpc_url, mint)
    source_ata = get_associated_token_address(owner, mint)
    dest_ata = get_associated_token_address(recipient, mint)

    instructions: list[Any] = []
    if not _account_exists(rpc_url, dest_ata):
        instructions.append(create_associated_token_account(owner, recipient, mint))

    instructions.append(
        transfer_checked(
            TransferCheckedParams(
                program_id=TOKEN_PROGRAM_ID,
                source=source_ata,
                mint=mint,
                dest=dest_ata,
                owner=owner,
                amount=amount_units,
                decimals=decimals,
                signers=[],
            )
        )
    )
    blockhash = Hash.from_string(get_latest_blockhash(rpc_url))
    tx = Transaction.new_signed_with_payer(instructions, owner, [signer], blockhash)
    signature = _send_raw_tx(rpc_url, bytes(tx))
    return {
        "signature": signature,
        "sourceAta": str(source_ata),
        "destinationAta": str(dest_ata),
        "mint": str(mint),
        "decimals": decimals,
    }


def _jupiter_base_url(chain_key: str) -> str:
    normalized = str(chain_key or "").strip().lower()
    if normalized == "solana_mainnet_beta":
        return "https://quote-api.jup.ag/v6"
    return "https://quote-api.jup.ag/v6"


def jupiter_quote(
    *,
    chain_key: str,
    input_mint: str,
    output_mint: str,
    amount_units: str,
    slippage_bps: int,
) -> SolanaQuote:
    if not re.fullmatch(r"[0-9]+", str(amount_units or "").strip()):
        raise SolanaRuntimeError("invalid_input", "amountInUnits must be an unsigned integer string.")
    if not isinstance(slippage_bps, int) or slippage_bps < 0 or slippage_bps > 5000:
        raise SolanaRuntimeError("invalid_input", "slippageBps must be an integer between 0 and 5000.")
    if not is_solana_address(input_mint) or not is_solana_address(output_mint):
        raise SolanaRuntimeError("invalid_input", "inputMint/outputMint must be valid Solana addresses.")

    query = urllib.parse.urlencode(
        {
            "inputMint": input_mint,
            "outputMint": output_mint,
            "amount": str(amount_units),
            "slippageBps": str(slippage_bps),
            "swapMode": "ExactIn",
            "onlyDirectRoutes": "false",
        }
    )
    url = f"{_jupiter_base_url(chain_key)}/quote?{query}"
    req = urllib.request.Request(url, method="GET", headers={"accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        raise SolanaRuntimeError("rpc_unavailable", "Jupiter quote request failed.", {"error": str(exc)}) from exc

    out_amount = str(payload.get("outAmount") or "").strip()
    if not re.fullmatch(r"[0-9]+", out_amount) or out_amount == "0":
        raise SolanaRuntimeError("rpc_unavailable", "Jupiter quote returned no executable outAmount.", {"payload": payload})
    route_kind = "jupiter_route"
    route_plan = payload.get("routePlan")
    if isinstance(route_plan, list) and len(route_plan) > 1:
        route_kind = "multi_hop"
    return SolanaQuote(amount_out_units=out_amount, route_kind=route_kind, quote_payload=payload)


def jupiter_execute_swap(*, chain_key: str, rpc_url: str, private_key_bytes: bytes, quote_payload: dict[str, Any], user_address: str) -> dict[str, Any]:
    _require_solana_dependencies()
    if not is_solana_address(user_address):
        raise SolanaRuntimeError("invalid_input", "userAddress must be a valid Solana address.")

    base_url = _jupiter_base_url(chain_key)
    request_payload = {
        "quoteResponse": quote_payload,
        "userPublicKey": user_address,
        "wrapAndUnwrapSol": True,
        "dynamicComputeUnitLimit": True,
        "prioritizationFeeLamports": "auto",
    }
    req = urllib.request.Request(
        f"{base_url}/swap",
        method="POST",
        headers={"content-type": "application/json", "accept": "application/json"},
        data=json.dumps(request_payload).encode("utf-8"),
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        raise SolanaRuntimeError("rpc_unavailable", "Jupiter swap build request failed.", {"error": str(exc)}) from exc

    swap_tx_b64 = str(payload.get("swapTransaction") or "").strip()
    if not swap_tx_b64:
        raise SolanaRuntimeError("rpc_unavailable", "Jupiter swap response missing swapTransaction.", {"payload": payload})

    try:
        tx = VersionedTransaction.from_bytes(base64.b64decode(swap_tx_b64))
        signer = Keypair.from_bytes(private_key_bytes)
        signed = VersionedTransaction(tx.message, [signer])
    except Exception as exc:
        raise SolanaRuntimeError("rpc_unavailable", "Failed to sign Jupiter swap transaction.", {"error": str(exc)}) from exc

    signature = _send_raw_tx(rpc_url, bytes(signed))
    return {
        "signature": signature,
        "swapTransactionSize": len(bytes(signed)),
        "prioritizationFeeLamports": payload.get("prioritizationFeeLamports"),
        "computeUnitLimit": payload.get("computeUnitLimit"),
    }
