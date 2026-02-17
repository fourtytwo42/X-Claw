#!/usr/bin/env python3
"""X-Claw agent runtime CLI scaffold.

This CLI provides the command surface required by the X-Claw skill wrapper.
Wallet core operations are implemented with encrypted-at-rest storage.
"""

from __future__ import annotations

import argparse
import base64
import io
import getpass
import hashlib
import json
import os
import pathlib
import re
import secrets
import shutil
import socket
import stat
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_DOWN
from typing import Any

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from xclaw_agent import x402_state
from xclaw_agent.x402_policy import get_policy as x402_get_policy
from xclaw_agent.x402_policy import set_policy as x402_set_policy
from xclaw_agent.x402_runtime import list_networks as x402_list_networks
from xclaw_agent.x402_runtime import pay_create_or_execute as x402_pay_create_or_execute
from xclaw_agent.x402_runtime import pay_decide as x402_pay_decide
from xclaw_agent.x402_runtime import pay_resume as x402_pay_resume
from xclaw_agent.x402_runtime import X402RuntimeError
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
try:
    from argon2.low_level import Type, hash_secret_raw
except Exception:  # pragma: no cover - handled by runtime dependency check
    Type = None  # type: ignore[assignment]
    hash_secret_raw = None  # type: ignore[assignment]

try:
    from Crypto.Hash import keccak
except Exception:  # pragma: no cover - handled by runtime dependency check
    keccak = None  # type: ignore[assignment]

APP_DIR = pathlib.Path(os.environ.get("XCLAW_AGENT_HOME", str(pathlib.Path.home() / ".xclaw-agent")))
STATE_FILE = APP_DIR / "state.json"
WALLET_STORE_FILE = APP_DIR / "wallets.json"
POLICY_FILE = APP_DIR / "policy.json"
LIMIT_ORDER_STORE_FILE = APP_DIR / "limit_orders.json"
LIMIT_ORDER_OUTBOX_FILE = APP_DIR / "limit_orders_outbox.json"
TRADE_USAGE_OUTBOX_FILE = APP_DIR / "trade_usage_outbox.json"
APPROVAL_PROMPTS_FILE = APP_DIR / "approval_prompts.json"
PENDING_TRADE_INTENTS_FILE = APP_DIR / "pending-trade-intents.json"
PENDING_SPOT_TRADE_FLOWS_FILE = APP_DIR / "pending-spot-trade-flows.json"
PENDING_TRANSFER_FLOWS_FILE = APP_DIR / "pending-transfer-flows.json"
TRANSFER_POLICY_FILE = APP_DIR / "transfer-policy.json"
REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
CHAIN_CONFIG_DIR = REPO_ROOT / "config" / "chains"

WALLET_STORE_VERSION = 1
ARGON2_TIME_COST = 3
ARGON2_MEMORY_COST = 65536
ARGON2_PARALLELISM = 1
ARGON2_HASH_LEN = 32
CHALLENGE_TTL_SECONDS = 300
CHALLENGE_FORMAT_VERSION = "xclaw-auth-v1"
CHALLENGE_REQUIRED_KEYS = {"domain", "chain", "nonce", "timestamp", "action"}
CHALLENGE_ALLOWED_DOMAINS = {"xclaw.trade", "localhost", "127.0.0.1", "::1", "staging.xclaw.trade"}
RETRY_WINDOW_SEC = 600
MAX_TRADE_RETRIES = 3
APPROVAL_WAIT_TIMEOUT_SEC = 1800
# Poll faster while waiting so Telegram/web decisions feel instant.
APPROVAL_WAIT_POLL_SEC = 1
DEFAULT_TX_GAS_PRICE_GWEI = 5
DEFAULT_TX_SEND_MAX_ATTEMPTS = 5
TX_GAS_PRICE_BUMP_GWEI = 5
LIMIT_ORDER_STORE_VERSION = 1
AGENT_RECOVERY_ACTION = "agent_key_recovery"


class WalletStoreError(Exception):
    """Wallet store is unavailable or invalid."""


class WalletSecurityError(Exception):
    """Wallet security checks failed."""


class WalletPassphraseError(Exception):
    """Wallet passphrase input is unavailable or invalid."""


class WalletPolicyError(Exception):
    """Wallet policy precondition checks failed."""

    def __init__(self, code: str, message: str, action_hint: str | None = None, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.action_hint = action_hint
        self.details = details or {}


class SubprocessTimeout(WalletStoreError):
    """A subprocess operation timed out (cast call/receipt/send/etc)."""

    def __init__(self, kind: str, timeout_sec: int, cmd: list[str]):
        super().__init__(f"Timed out after {timeout_sec}s running: {' '.join(cmd)}")
        self.kind = kind
        self.timeout_sec = timeout_sec
        self.cmd = cmd


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def emit(payload: dict) -> int:
    print(json.dumps(payload, separators=(",", ":")))
    return 0


def ok(message: str, **extra: object) -> int:
    payload = {"ok": True, "code": "ok", "message": message}
    payload.update(extra)
    return emit(payload)


def fail(code: str, message: str, action_hint: str | None = None, details: dict | None = None, exit_code: int = 1) -> int:
    payload: dict[str, object] = {"ok": False, "code": code, "message": message}
    if action_hint:
        payload["actionHint"] = action_hint
    if details:
        payload["details"] = details
    emit(payload)
    return exit_code


def require_json_flag(args: argparse.Namespace) -> int | None:
    if getattr(args, "json", False):
        return None
    return fail("missing_flag", "This command requires --json output mode.", "Re-run with --json.", exit_code=2)


def _env_timeout_sec(name: str, default: int) -> int:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    if not re.fullmatch(r"[0-9]+", raw):
        raise WalletStoreError(f"{name} must be an integer number of seconds.")
    value = int(raw)
    if value < 1:
        raise WalletStoreError(f"{name} must be >= 1.")
    return value


def _cast_call_timeout_sec() -> int:
    return _env_timeout_sec("XCLAW_CAST_CALL_TIMEOUT_SEC", 30)


def _cast_receipt_timeout_sec() -> int:
    return _env_timeout_sec("XCLAW_CAST_RECEIPT_TIMEOUT_SEC", 90)


def _cast_send_timeout_sec() -> int:
    return _env_timeout_sec("XCLAW_CAST_SEND_TIMEOUT_SEC", 30)


def _run_subprocess(cmd: list[str], *, timeout_sec: int, kind: str) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(cmd, text=True, capture_output=True, timeout=timeout_sec)
    except subprocess.TimeoutExpired as exc:
        raise SubprocessTimeout(kind=kind, timeout_sec=timeout_sec, cmd=cmd) from exc


def ensure_app_dir() -> None:
    APP_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    if os.name != "nt":
        os.chmod(APP_DIR, 0o700)


def _is_secure_permissions(path: pathlib.Path, expected_mode: int) -> bool:
    if os.name == "nt":
        return True
    mode = stat.S_IMODE(path.stat().st_mode)
    return mode == expected_mode


def _assert_secure_permissions(path: pathlib.Path, expected_mode: int, kind: str) -> None:
    if not path.exists():
        return
    if not _is_secure_permissions(path, expected_mode):
        raise WalletSecurityError(
            f"Unsafe {kind} permissions for '{path}'. Expected {oct(expected_mode)} owner-only permissions."
        )


def _read_json(path: pathlib.Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise WalletStoreError(f"Invalid JSON in '{path}': {exc}") from exc


def _write_json(path: pathlib.Path, payload: dict[str, Any]) -> None:
    ensure_app_dir()
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    if os.name != "nt":
        os.chmod(path, 0o600)


def load_state() -> dict[str, Any]:
    if not STATE_FILE.exists():
        return {}
    return _read_json(STATE_FILE)


def save_state(state: dict[str, Any]) -> None:
    _write_json(STATE_FILE, state)


def _default_wallet_store() -> dict[str, Any]:
    return {
        "version": WALLET_STORE_VERSION,
        "defaultWalletId": None,
        "wallets": {},
        "chains": {},
    }


def load_wallet_store() -> dict[str, Any]:
    ensure_app_dir()
    _assert_secure_permissions(APP_DIR, 0o700, "directory")
    if not WALLET_STORE_FILE.exists():
        return _default_wallet_store()
    _assert_secure_permissions(WALLET_STORE_FILE, 0o600, "wallet store file")
    data = _read_json(WALLET_STORE_FILE)
    if not isinstance(data, dict):
        raise WalletStoreError("Wallet store must be a JSON object.")
    version = data.get("version")
    if version != WALLET_STORE_VERSION:
        raise WalletStoreError(f"Unsupported wallet store version: {version}")
    if not isinstance(data.get("wallets"), dict) or not isinstance(data.get("chains"), dict):
        raise WalletStoreError("Wallet store missing required maps: wallets/chains.")
    return data


def save_wallet_store(store: dict[str, Any]) -> None:
    _write_json(WALLET_STORE_FILE, store)


def ensure_wallet_entry(chain: str) -> tuple[dict[str, Any], dict[str, Any]]:
    state = load_state()
    wallets = state.setdefault("wallets", {})
    wallet = wallets.get(chain)
    return state, wallet or {}


def set_wallet_entry(chain: str, wallet: dict[str, Any]) -> None:
    state = load_state()
    wallets = state.setdefault("wallets", {})
    wallets[chain] = wallet
    save_state(state)


def remove_wallet_entry(chain: str) -> bool:
    existed = False

    state = load_state()
    wallets = state.setdefault("wallets", {})
    if chain in wallets:
        wallets.pop(chain, None)
        save_state(state)
        existed = True

    try:
        store = load_wallet_store()
    except (WalletStoreError, WalletSecurityError):
        return existed

    chains = store.setdefault("chains", {})
    wallet_id = chains.pop(chain, None)
    if wallet_id:
        existed = True
        in_use = wallet_id in chains.values()
        if not in_use:
            store.setdefault("wallets", {}).pop(wallet_id, None)
            if store.get("defaultWalletId") == wallet_id:
                store["defaultWalletId"] = None
        save_wallet_store(store)

    return existed


def _default_limit_order_store() -> dict[str, Any]:
    return {
        "version": LIMIT_ORDER_STORE_VERSION,
        "updatedAt": utc_now(),
        "orders": [],
    }


def load_limit_order_store() -> dict[str, Any]:
    ensure_app_dir()
    _assert_secure_permissions(APP_DIR, 0o700, "directory")
    if not LIMIT_ORDER_STORE_FILE.exists():
        return _default_limit_order_store()
    _assert_secure_permissions(LIMIT_ORDER_STORE_FILE, 0o600, "limit order store file")
    payload = _read_json(LIMIT_ORDER_STORE_FILE)
    if not isinstance(payload, dict):
        raise WalletStoreError("Limit-order store must be a JSON object.")
    version = payload.get("version")
    if version != LIMIT_ORDER_STORE_VERSION:
        raise WalletStoreError(f"Unsupported limit-order store version: {version}")
    orders = payload.get("orders")
    if not isinstance(orders, list):
        raise WalletStoreError("Limit-order store missing orders array.")
    return payload


def save_limit_order_store(store: dict[str, Any]) -> None:
    store["version"] = LIMIT_ORDER_STORE_VERSION
    store["updatedAt"] = utc_now()
    _write_json(LIMIT_ORDER_STORE_FILE, store)


def load_limit_order_outbox() -> list[dict[str, Any]]:
    ensure_app_dir()
    if not LIMIT_ORDER_OUTBOX_FILE.exists():
        return []
    _assert_secure_permissions(LIMIT_ORDER_OUTBOX_FILE, 0o600, "limit-order outbox file")
    payload = _read_json(LIMIT_ORDER_OUTBOX_FILE)
    if not isinstance(payload, dict):
        raise WalletStoreError("Limit-order outbox must be a JSON object.")
    items = payload.get("items")
    if not isinstance(items, list):
        return []
    return [entry for entry in items if isinstance(entry, dict)]


def save_limit_order_outbox(items: list[dict[str, Any]]) -> None:
    _write_json(LIMIT_ORDER_OUTBOX_FILE, {"items": items, "updatedAt": utc_now()})


def load_trade_usage_outbox() -> list[dict[str, Any]]:
    ensure_app_dir()
    if not TRADE_USAGE_OUTBOX_FILE.exists():
        return []
    _assert_secure_permissions(TRADE_USAGE_OUTBOX_FILE, 0o600, "trade-usage outbox file")
    payload = _read_json(TRADE_USAGE_OUTBOX_FILE)
    if not isinstance(payload, dict):
        raise WalletStoreError("Trade-usage outbox must be a JSON object.")
    items = payload.get("items")
    if not isinstance(items, list):
        return []
    return [entry for entry in items if isinstance(entry, dict)]


def save_trade_usage_outbox(items: list[dict[str, Any]]) -> None:
    _write_json(TRADE_USAGE_OUTBOX_FILE, {"items": items, "updatedAt": utc_now()})


def is_hex_address(value: str) -> bool:
    return bool(re.fullmatch(r"0x[a-fA-F0-9]{40}", value))


def _normalize_private_key_hex(value: str) -> str | None:
    stripped = value.strip()
    if stripped.startswith("0x"):
        stripped = stripped[2:]
    if re.fullmatch(r"[a-fA-F0-9]{64}", stripped):
        return stripped.lower()
    return None


def cast_exists() -> bool:
    return _find_cast_bin() is not None


def _find_cast_bin() -> str | None:
    # OpenClaw/systemd user services often run with a minimal PATH; Foundry installs
    # to user-space (~/.foundry/bin). Prefer PATH if available, but fall back to the
    # default install location so dashboard/holdings work after bootstrap installs.
    candidates: list[str] = []
    explicit = (os.environ.get("XCLAW_CAST_BIN") or "").strip()
    if explicit:
        candidates.append(explicit)

    foundry_bin = (os.environ.get("FOUNDRY_BIN") or "").strip()
    if foundry_bin:
        candidates.append(str(pathlib.Path(foundry_bin) / "cast"))

    which_cast = shutil.which("cast")
    if which_cast:
        candidates.append(which_cast)

    candidates.append(str(pathlib.Path.home() / ".foundry" / "bin" / "cast"))

    for entry in candidates:
        try:
            path = pathlib.Path(entry).expanduser()
            if path.is_file() and os.access(path, os.X_OK):
                return str(path)
        except Exception:
            continue
    return None


def _require_cast_bin() -> str:
    cast_bin = _find_cast_bin()
    if not cast_bin:
        raise WalletStoreError("Missing dependency: cast.")
    return cast_bin


def _load_chain_config(chain: str) -> dict[str, Any]:
    path = CHAIN_CONFIG_DIR / f"{chain}.json"
    if not path.exists():
        raise WalletStoreError(f"Chain config not found for '{chain}' at '{path}'.")
    data = _read_json(path)
    if not isinstance(data, dict):
        raise WalletStoreError(f"Chain config '{path}' must be a JSON object.")
    return data


def _chain_rpc_url(chain: str) -> str:
    cfg = _load_chain_config(chain)
    rpc = cfg.get("rpc")
    if not isinstance(rpc, dict):
        raise WalletStoreError(f"Chain config for '{chain}' is missing rpc object.")
    primary = rpc.get("primary")
    fallback = rpc.get("fallback")
    for candidate in [primary, fallback]:
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    raise WalletStoreError(f"Chain config for '{chain}' has no usable rpc URL.")


def _utc_day_key(now_utc: datetime | None = None) -> str:
    reference = now_utc or datetime.now(timezone.utc)
    return reference.astimezone(timezone.utc).strftime("%Y-%m-%d")


def _parse_uint_text(value: str) -> int:
    raw = value.strip()
    if re.fullmatch(r"[0-9]+", raw):
        return int(raw)
    if re.fullmatch(r"0x[a-fA-F0-9]+", raw):
        return int(raw, 16)
    # cast outputs sometimes include a scientific-notation hint in brackets, e.g.
    # "20000000000000000000000 [2e22]". Accept the leading integer/hex portion.
    prefix = re.match(r"^(0x[a-fA-F0-9]+|[0-9]+)", raw)
    if prefix:
        token = prefix.group(1)
        if token.startswith("0x") or token.startswith("0X"):
            return int(token, 16)
        return int(token)
    raise WalletStoreError(f"Unable to parse uint value: '{value}'.")


def _extract_tx_hash(output: str) -> str:
    trimmed = (output or "").strip()
    if not trimmed:
        raise WalletStoreError("cast send returned empty output.")
    try:
        parsed = json.loads(trimmed)
    except json.JSONDecodeError:
        parsed = None

    candidates: list[Any] = []
    if isinstance(parsed, dict):
        candidates.extend([parsed.get("transactionHash"), parsed.get("txHash"), parsed.get("hash")])
    elif isinstance(parsed, list):
        for item in parsed:
            if isinstance(item, dict):
                candidates.extend([item.get("transactionHash"), item.get("txHash"), item.get("hash")])

    for value in candidates:
        if isinstance(value, str) and re.fullmatch(r"0x[a-fA-F0-9]{64}", value):
            return value

    match = re.search(r"0x[a-fA-F0-9]{64}", trimmed)
    if match:
        return match.group(0)
    raise WalletStoreError("cast send output did not include a transaction hash.")


def _load_policy_for_chain(chain: str) -> dict[str, Any]:
    ensure_app_dir()
    _assert_secure_permissions(APP_DIR, 0o700, "directory")
    if not POLICY_FILE.exists():
        raise WalletPolicyError(
            "policy_blocked",
            f"Policy file is missing for chain '{chain}'.",
            "Create ~/.xclaw-agent/policy.json with chain and spend preconditions before sending funds.",
            {"chain": chain, "policyFile": str(POLICY_FILE)},
        )
    _assert_secure_permissions(POLICY_FILE, 0o600, "policy file")
    payload = _read_json(POLICY_FILE)
    if not isinstance(payload, dict):
        raise WalletPolicyError(
            "policy_blocked",
            "Policy file must be a JSON object.",
            "Repair ~/.xclaw-agent/policy.json and retry.",
            {"policyFile": str(POLICY_FILE)},
        )
    return payload


def _enforce_spend_preconditions(chain: str, amount_wei: int, *, enforce_native_cap: bool = True) -> tuple[dict[str, Any], str, int, int]:
    policy = _load_policy_for_chain(chain)

    paused = policy.get("paused")
    if not isinstance(paused, bool):
        raise WalletPolicyError(
            "policy_blocked",
            "Policy field 'paused' must be boolean.",
            "Set paused=true/false in ~/.xclaw-agent/policy.json.",
            {"field": "paused", "policyFile": str(POLICY_FILE)},
        )
    if paused:
        raise WalletPolicyError(
            "agent_paused",
            "Spend blocked because agent is paused.",
            "Resume the agent before sending funds.",
            {"chain": chain},
        )

    chains = policy.get("chains")
    if not isinstance(chains, dict):
        raise WalletPolicyError(
            "policy_blocked",
            "Policy field 'chains' must be an object.",
            "Configure chain-level policy under chains.<chain>.",
            {"field": "chains", "policyFile": str(POLICY_FILE)},
        )
    chain_policy = chains.get(chain)
    if not isinstance(chain_policy, dict):
        raise WalletPolicyError(
            "chain_disabled",
            f"Spend blocked because chain '{chain}' is not configured in policy.",
            "Add chains.<chain>.chain_enabled=true to policy.",
            {"chain": chain},
        )
    chain_enabled = chain_policy.get("chain_enabled")
    if not isinstance(chain_enabled, bool):
        raise WalletPolicyError(
            "policy_blocked",
            "Policy field chains.<chain>.chain_enabled must be boolean.",
            "Set chain_enabled=true/false for the active chain.",
            {"chain": chain, "field": "chain_enabled"},
        )
    if not chain_enabled:
        raise WalletPolicyError(
            "chain_disabled",
            f"Spend blocked because chain '{chain}' is disabled by policy.",
            "Enable the chain in policy before spending.",
            {"chain": chain},
        )

    spend = policy.get("spend")
    if not isinstance(spend, dict):
        raise WalletPolicyError(
            "policy_blocked",
            "Policy field 'spend' must be an object.",
            "Configure spend preconditions in policy.",
            {"field": "spend", "policyFile": str(POLICY_FILE)},
        )
    approval_required = spend.get("approval_required")
    approval_granted = spend.get("approval_granted")
    max_daily_native_wei = spend.get("max_daily_native_wei")

    if not isinstance(approval_required, bool) or not isinstance(approval_granted, bool):
        raise WalletPolicyError(
            "policy_blocked",
            "Policy fields spend.approval_required and spend.approval_granted must be boolean.",
            "Set approval_required and approval_granted in policy.",
            {"field": "spend"},
        )
    if approval_required and not approval_granted:
        raise WalletPolicyError(
            "approval_required",
            "Spend blocked because approval is required but not granted.",
            "Grant approval before sending funds.",
            {"chain": chain},
        )
    if not isinstance(max_daily_native_wei, str) or not re.fullmatch(r"[0-9]+", max_daily_native_wei):
        raise WalletPolicyError(
            "policy_blocked",
            "Policy field spend.max_daily_native_wei must be a uint string.",
            "Set max_daily_native_wei as a base-unit integer string.",
            {"field": "spend.max_daily_native_wei"},
        )

    max_daily_wei = int(max_daily_native_wei)
    day_key = _utc_day_key()
    state = load_state()
    ledger = state.setdefault("spendLedger", {})
    if not isinstance(ledger, dict):
        raise WalletStoreError("State field 'spendLedger' must be an object.")
    chain_ledger = ledger.setdefault(chain, {})
    if not isinstance(chain_ledger, dict):
        raise WalletStoreError(f"State spend ledger for chain '{chain}' must be an object.")
    current_raw = chain_ledger.get(day_key, "0")
    if not isinstance(current_raw, str) or not re.fullmatch(r"[0-9]+", current_raw):
        raise WalletStoreError(f"State spend ledger value for '{chain}' '{day_key}' must be uint string.")
    current_spend = int(current_raw)

    projected = current_spend + amount_wei
    if enforce_native_cap and projected > max_daily_wei:
        raise WalletPolicyError(
            "daily_cap_exceeded",
            "Spend blocked because daily native cap would be exceeded.",
            "Reduce amount or increase max_daily_native_wei policy cap.",
            {
                "chain": chain,
                "day": day_key,
                "currentSpendWei": str(current_spend),
                "amountWei": str(amount_wei),
                "maxDailyNativeWei": str(max_daily_wei),
            },
        )
    return state, day_key, current_spend, max_daily_wei


def _record_spend(state: dict[str, Any], chain: str, day_key: str, new_spend_wei: int) -> None:
    ledger = state.setdefault("spendLedger", {})
    if not isinstance(ledger, dict):
        raise WalletStoreError("State field 'spendLedger' must be an object.")
    chain_ledger = ledger.setdefault(chain, {})
    if not isinstance(chain_ledger, dict):
        raise WalletStoreError(f"State spend ledger for chain '{chain}' must be an object.")
    chain_ledger[day_key] = str(new_spend_wei)
    save_state(state)


def _derive_address(private_key_hex: str) -> str:
    if keccak is None:
        raise WalletStoreError("Missing dependency: pycryptodome (Crypto.Hash.keccak).")
    private_key_bytes = bytes.fromhex(private_key_hex)
    private_value = int.from_bytes(private_key_bytes, byteorder="big")
    # cryptography validates private key range for secp256k1.
    private_key = ec.derive_private_key(private_value, ec.SECP256K1())
    public_key_bytes = private_key.public_key().public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
    digest = keccak.new(digest_bits=256)
    digest.update(public_key_bytes[1:])
    return "0x" + digest.digest()[-20:].hex()


def _derive_aes_key(passphrase: str, salt: bytes) -> bytes:
    if hash_secret_raw is None or Type is None:
        raise WalletStoreError("Missing dependency: argon2-cffi.")
    return hash_secret_raw(
        secret=passphrase.encode("utf-8"),
        salt=salt,
        time_cost=ARGON2_TIME_COST,
        memory_cost=ARGON2_MEMORY_COST,
        parallelism=ARGON2_PARALLELISM,
        hash_len=ARGON2_HASH_LEN,
        type=Type.ID,
    )


def _encrypt_private_key(private_key_hex: str, passphrase: str) -> dict[str, Any]:
    private_key_bytes = bytes.fromhex(private_key_hex)
    salt = secrets.token_bytes(16)
    nonce = secrets.token_bytes(12)
    key = _derive_aes_key(passphrase, salt)
    cipher = AESGCM(key)
    ciphertext = cipher.encrypt(nonce, private_key_bytes, None)
    return {
        "version": 1,
        "enc": "aes-256-gcm",
        "kdf": "argon2id",
        "kdfParams": {
            "timeCost": ARGON2_TIME_COST,
            "memoryCost": ARGON2_MEMORY_COST,
            "parallelism": ARGON2_PARALLELISM,
            "hashLen": ARGON2_HASH_LEN,
        },
        "saltB64": base64.b64encode(salt).decode("ascii"),
        "nonceB64": base64.b64encode(nonce).decode("ascii"),
        "ciphertextB64": base64.b64encode(ciphertext).decode("ascii"),
    }


def _decrypt_private_key(entry: dict[str, Any], passphrase: str) -> bytes:
    crypto = entry.get("crypto")
    if not isinstance(crypto, dict):
        raise WalletStoreError("Wallet entry missing crypto object.")

    try:
        salt = base64.b64decode(crypto["saltB64"])
        nonce = base64.b64decode(crypto["nonceB64"])
        ciphertext = base64.b64decode(crypto["ciphertextB64"])
    except Exception as exc:
        raise WalletStoreError("Wallet crypto payload is not valid base64.") from exc

    if len(salt) != 16 or len(nonce) != 12 or len(ciphertext) < 16:
        raise WalletStoreError("Wallet crypto payload has invalid lengths.")

    key = _derive_aes_key(passphrase, salt)
    cipher = AESGCM(key)
    return cipher.decrypt(nonce, ciphertext, None)


def _validate_wallet_entry_shape(entry: dict[str, Any]) -> None:
    if not isinstance(entry, dict):
        raise WalletStoreError("Wallet entry is not an object.")
    address = entry.get("address")
    if not isinstance(address, str) or not is_hex_address(address):
        raise WalletStoreError("Wallet entry address is missing or invalid.")
    crypto = entry.get("crypto")
    if not isinstance(crypto, dict):
        raise WalletStoreError("Wallet entry crypto payload is missing.")

    required_crypto_fields = ["enc", "kdf", "kdfParams", "saltB64", "nonceB64", "ciphertextB64"]
    missing = [k for k in required_crypto_fields if k not in crypto]
    if missing:
        raise WalletStoreError(f"Wallet entry crypto payload missing fields: {', '.join(missing)}")

    if crypto.get("enc") != "aes-256-gcm" or crypto.get("kdf") != "argon2id":
        raise WalletStoreError("Wallet entry crypto algorithm metadata is invalid.")
    try:
        salt = base64.b64decode(str(crypto.get("saltB64", "")))
        nonce = base64.b64decode(str(crypto.get("nonceB64", "")))
        ciphertext = base64.b64decode(str(crypto.get("ciphertextB64", "")))
    except Exception as exc:
        raise WalletStoreError("Wallet crypto payload is not valid base64.") from exc
    if len(salt) != 16 or len(nonce) != 12 or len(ciphertext) < 16:
        raise WalletStoreError("Wallet crypto payload has invalid lengths.")


def _interactive_required() -> bool:
    return sys.stdin.isatty() and sys.stderr.isatty()


def _prompt_passphrase() -> str:
    first = getpass.getpass("Wallet passphrase: ").strip()
    second = getpass.getpass("Confirm wallet passphrase: ").strip()
    if not first:
        raise ValueError("Passphrase cannot be empty.")
    if first != second:
        raise ValueError("Passphrase confirmation mismatch.")
    return first


def _prompt_existing_passphrase() -> str:
    value = getpass.getpass("Wallet passphrase: ").strip()
    if not value:
        raise WalletPassphraseError("Passphrase cannot be empty.")
    return value


def _create_import_passphrase(chain: str) -> str:
    env_passphrase = (os.environ.get("XCLAW_WALLET_PASSPHRASE") or "").strip()
    if env_passphrase:
        return env_passphrase
    if not _interactive_required():
        raise WalletPassphraseError(
            f"wallet create/import requires XCLAW_WALLET_PASSPHRASE in non-interactive mode for chain '{chain}'."
        )
    return _prompt_passphrase()


def _import_private_key_input(chain: str) -> str:
    env_private_key = (os.environ.get("XCLAW_WALLET_IMPORT_PRIVATE_KEY") or "").strip()
    if env_private_key:
        return env_private_key
    if not _interactive_required():
        raise WalletPassphraseError(
            f"wallet.import requires XCLAW_WALLET_IMPORT_PRIVATE_KEY in non-interactive mode for chain '{chain}'."
        )
    return getpass.getpass("Private key (hex, optional 0x): ")


def _chain_wallet(store: dict[str, Any], chain: str) -> tuple[str | None, dict[str, Any] | None]:
    wallet_id = store.setdefault("chains", {}).get(chain)
    if not wallet_id:
        return None, None
    wallet = store.setdefault("wallets", {}).get(wallet_id)
    if not isinstance(wallet, dict):
        return wallet_id, None
    return wallet_id, wallet


def _bind_chain_to_wallet(store: dict[str, Any], chain: str, wallet_id: str) -> None:
    store.setdefault("chains", {})[chain] = wallet_id


def _new_wallet_id() -> str:
    return f"wlt_{secrets.token_hex(10)}"


def _require_wallet_passphrase_for_signing(chain: str) -> str:
    env_passphrase = os.environ.get("XCLAW_WALLET_PASSPHRASE")
    if isinstance(env_passphrase, str) and env_passphrase.strip():
        return env_passphrase
    if not _interactive_required():
        raise WalletPassphraseError(
            f"wallet.sign-challenge requires XCLAW_WALLET_PASSPHRASE in non-interactive mode for chain '{chain}'."
        )
    return _prompt_existing_passphrase()


def _parse_challenge_timestamp(value: str) -> datetime:
    parsed_raw = value.strip()
    if parsed_raw.endswith("Z"):
        parsed_raw = parsed_raw[:-1] + "+00:00"
    parsed = datetime.fromisoformat(parsed_raw)
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include timezone.")
    if parsed.utcoffset() != timedelta(0):
        raise ValueError("timestamp must be UTC (Z or +00:00).")
    parsed_utc = parsed.astimezone(timezone.utc)
    return parsed_utc


def _validate_challenge_timestamp(timestamp_value: str, now_utc: datetime | None = None) -> datetime:
    parsed = _parse_challenge_timestamp(timestamp_value)
    reference = now_utc or datetime.now(timezone.utc)
    delta_seconds = abs((reference - parsed).total_seconds())
    if delta_seconds > CHALLENGE_TTL_SECONDS:
        raise ValueError("timestamp is outside 5-minute nonce TTL window.")
    return parsed


def _parse_canonical_challenge(message: str, expected_chain: str) -> dict[str, str]:
    pairs: dict[str, str] = {}
    for idx, raw_line in enumerate(message.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        if "=" not in line:
            raise ValueError(f"line {idx} must use key=value format.")
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key in pairs:
            raise ValueError(f"duplicate key '{key}'.")
        if key not in CHALLENGE_REQUIRED_KEYS:
            raise ValueError(f"unexpected key '{key}'.")
        pairs[key] = value

    missing = sorted(CHALLENGE_REQUIRED_KEYS - set(pairs.keys()))
    if missing:
        raise ValueError(f"missing required keys: {', '.join(missing)}")

    domain = pairs["domain"]
    if domain not in CHALLENGE_ALLOWED_DOMAINS:
        raise ValueError("domain is not in the allowlist.")

    if pairs["chain"] != expected_chain:
        raise ValueError("chain does not match command --chain.")

    nonce = pairs["nonce"]
    if not re.fullmatch(r"[A-Za-z0-9_-]{16,128}", nonce):
        raise ValueError("nonce must be 16..128 chars of [A-Za-z0-9_-].")

    if not pairs["action"].strip():
        raise ValueError("action cannot be empty.")

    _validate_challenge_timestamp(pairs["timestamp"])
    return pairs


def _cast_sign_message(private_key_hex: str, message: str) -> str:
    cast_bin = _require_cast_bin()

    proc = _run_subprocess(
        [cast_bin, "wallet", "sign", "--private-key", private_key_hex, message],
        timeout_sec=_cast_call_timeout_sec(),
        kind="cast_call",
    )
    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        raise WalletStoreError(stderr or "cast wallet sign failed.")

    signature = (proc.stdout or "").strip()
    if not re.fullmatch(r"0x[a-fA-F0-9]{130}", signature):
        raise WalletStoreError("cast returned malformed signature output.")
    return signature


def _require_api_base_url() -> str:
    base_url = (os.environ.get("XCLAW_API_BASE_URL") or "").strip()
    if not base_url:
        raise WalletStoreError("Missing required env: XCLAW_API_BASE_URL.")
    normalized = base_url.rstrip("/")
    parsed = urllib.parse.urlparse(normalized)
    path = (parsed.path or "").rstrip("/")
    if path in ("", "/"):
        normalized = f"{normalized}/api/v1"
    return normalized


def _extract_agent_id_from_signed_key(api_key: str) -> str | None:
    parts = api_key.split(".")
    if len(parts) == 4 and parts[0] == "xak1" and parts[1]:
        return parts[1]
    return None


def _load_agent_runtime_auth() -> tuple[str | None, str | None]:
    state = load_state()
    state_agent_id = state.get("agentId")
    state_api_key = state.get("agentApiKey")
    agent_id = str(state_agent_id).strip() if isinstance(state_agent_id, str) else None
    api_key = str(state_api_key).strip() if isinstance(state_api_key, str) else None
    return agent_id, api_key


def _save_agent_runtime_auth(agent_id: str | None, api_key: str) -> None:
    state = load_state()
    state["agentApiKey"] = api_key
    if agent_id:
        state["agentId"] = agent_id
    save_state(state)


def _resolve_api_key() -> str:
    env_api_key = (os.environ.get("XCLAW_AGENT_API_KEY") or "").strip()
    if env_api_key:
        return env_api_key
    _, state_api_key = _load_agent_runtime_auth()
    if state_api_key:
        return state_api_key
    raise WalletStoreError("Missing required auth: XCLAW_AGENT_API_KEY (or recovered key in runtime state).")


def _resolve_agent_id(api_key: str) -> str | None:
    env_agent_id = (os.environ.get("XCLAW_AGENT_ID") or "").strip()
    if env_agent_id:
        return env_agent_id
    state_agent_id, _ = _load_agent_runtime_auth()
    if state_agent_id:
        return state_agent_id
    return _extract_agent_id_from_signed_key(api_key)


def _http_json_request(
    method: str,
    url: str,
    payload: dict[str, Any] | None = None,
    api_key: str | None = None,
    include_idempotency: bool = False,
    idempotency_key: str | None = None,
) -> tuple[int, dict[str, Any]]:
    headers: dict[str, str] = {
        "Accept": "application/json",
        "User-Agent": "xclaw-agent-runtime/1.0 (+https://xclaw.trade/skill.md)"
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    if include_idempotency:
        headers["Idempotency-Key"] = idempotency_key or f"rt-{secrets.token_hex(16)}"

    raw_data: bytes | None = None
    if payload is not None:
        raw_data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(url=url, data=raw_data, headers=headers, method=method.upper())
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            body = response.read().decode("utf-8")
            parsed = json.loads(body) if body else {}
            if not isinstance(parsed, dict):
                raise WalletStoreError("API returned non-object JSON payload.")
            return int(response.status), parsed
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8") if exc.fp else ""
        try:
            parsed = json.loads(body) if body else {}
            if not isinstance(parsed, dict):
                parsed = {"message": body}
        except Exception:
            parsed = {"message": body or str(exc)}
        return int(exc.code), parsed
    except urllib.error.URLError as exc:
        raise WalletStoreError(f"API request failed: {exc.reason}") from exc


def _api_error_details(status: int, body: dict[str, Any], path: str, chain: str | None = None) -> dict[str, Any]:
    details: dict[str, Any] = {"status": int(status), "path": path}
    request_id = body.get("requestId")
    if isinstance(request_id, str) and request_id.strip():
        details["requestId"] = request_id.strip()
    api_details = body.get("details")
    # Preserve server-side validation details (schema errors, field hints) when present.
    if api_details is not None:
        details["apiDetails"] = api_details
    if chain:
        details["chain"] = chain
    return details


def _normalize_management_url(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    raw = value.strip()
    if not raw:
        return None
    try:
        parsed = urllib.parse.urlsplit(raw)
    except Exception:
        return raw
    host = (parsed.hostname or "").strip().lower()
    if host in {"0.0.0.0", "::", "::1", "127.0.0.1", "localhost"}:
        base = (os.environ.get("XCLAW_PUBLIC_BASE_URL") or "").strip().rstrip("/")
        if not base:
            base = "https://xclaw.trade"
        replacement = urllib.parse.urlsplit(base)
        parsed = parsed._replace(scheme=replacement.scheme or "https", netloc=replacement.netloc)
    return urllib.parse.urlunsplit(parsed)


def _wallet_address_for_chain(chain: str) -> str:
    store = load_wallet_store()
    _, wallet = _chain_wallet(store, chain)
    if not wallet:
        raise WalletStoreError(f"No wallet configured for chain '{chain}'.")
    _validate_wallet_entry_shape(wallet)
    address = wallet.get("address")
    if not isinstance(address, str) or not is_hex_address(address):
        raise WalletStoreError(f"Wallet address is missing/invalid for chain '{chain}'.")
    return address


def _recover_api_key_with_wallet_signature(base_url: str, stale_api_key: str, chain: str) -> str:
    agent_id = _resolve_agent_id(stale_api_key)
    if not agent_id:
        raise WalletStoreError("Agent id is required for key recovery. Set XCLAW_AGENT_ID or use signed token format.")

    wallet_address = _wallet_address_for_chain(chain)
    challenge_status, challenge_body = _http_json_request(
        "POST",
        f"{base_url}/agent/auth/challenge",
        payload={
            "agentId": agent_id,
            "chainKey": chain,
            "walletAddress": wallet_address,
            "action": AGENT_RECOVERY_ACTION,
        },
    )
    if challenge_status < 200 or challenge_status >= 300:
        code = str(challenge_body.get("code", "auth_recovery_failed"))
        message = str(challenge_body.get("message", f"challenge request failed ({challenge_status})"))
        raise WalletStoreError(f"{code}: {message}")

    challenge_id = challenge_body.get("challengeId")
    challenge_message = challenge_body.get("challengeMessage")
    if not isinstance(challenge_id, str) or not challenge_id.strip():
        raise WalletStoreError("Challenge response missing challengeId.")
    if not isinstance(challenge_message, str) or not challenge_message.strip():
        raise WalletStoreError("Challenge response missing challengeMessage.")

    passphrase = _require_wallet_passphrase_for_signing(chain)
    store = load_wallet_store()
    _, wallet = _chain_wallet(store, chain)
    if not wallet:
        raise WalletStoreError(f"No wallet configured for chain '{chain}'.")
    private_key_bytes = _decrypt_private_key(wallet, passphrase)
    signature = _cast_sign_message(private_key_bytes.hex(), challenge_message)

    recover_status, recover_body = _http_json_request(
        "POST",
        f"{base_url}/agent/auth/recover",
        payload={
            "agentId": agent_id,
            "chainKey": chain,
            "walletAddress": wallet_address,
            "challengeId": challenge_id,
            "signature": signature,
        },
    )
    if recover_status < 200 or recover_status >= 300:
        code = str(recover_body.get("code", "auth_recovery_failed"))
        message = str(recover_body.get("message", f"recover request failed ({recover_status})"))
        raise WalletStoreError(f"{code}: {message}")

    recovered_key = recover_body.get("agentApiKey")
    if not isinstance(recovered_key, str) or not recovered_key.strip():
        raise WalletStoreError("Recovery response missing agentApiKey.")
    _save_agent_runtime_auth(agent_id, recovered_key)
    return recovered_key


def _api_request(
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
    include_idempotency: bool = False,
    idempotency_key: str | None = None,
    allow_auth_recovery: bool = True,
) -> tuple[int, dict[str, Any]]:
    base_url = _require_api_base_url()
    api_key = _resolve_api_key()
    if path.startswith("http://") or path.startswith("https://"):
        url = path
    else:
        normalized = path if path.startswith("/") else f"/{path}"
        url = f"{base_url}{normalized}"
    status, body = _http_json_request(
        method,
        url,
        payload=payload,
        api_key=api_key,
        include_idempotency=include_idempotency,
        idempotency_key=idempotency_key,
    )

    is_auth_failure = status == 401 and str(body.get("code", "")) == "auth_invalid"
    is_recovery_endpoint = url.endswith("/agent/auth/challenge") or url.endswith("/agent/auth/recover")
    if allow_auth_recovery and is_auth_failure and not is_recovery_endpoint:
        chain = (os.environ.get("XCLAW_DEFAULT_CHAIN") or "").strip() or "base_sepolia"
        recovered_key = _recover_api_key_with_wallet_signature(base_url, api_key, chain)
        status, body = _http_json_request(
            method,
            url,
            payload=payload,
            api_key=recovered_key,
            include_idempotency=include_idempotency,
            idempotency_key=idempotency_key,
        )
    return status, body


def _normalize_address(value: str) -> str:
    return value.strip().lower()


def _fetch_outbound_transfer_policy(chain: str) -> dict[str, Any]:
    path = f"/agent/transfers/policy?chainKey={urllib.parse.quote(chain)}"
    try:
        status_code, body = _api_request("GET", path)
        if status_code < 200 or status_code >= 300:
            code = str(body.get("code", "api_error"))
            message = str(body.get("message", f"transfer policy read failed ({status_code})"))
            raise WalletStoreError(f"{code}: {message}")
        # Cache last-known policy so runtime can fail-closed deterministically during API outages.
        try:
            state = load_state()
            cache = state.get("transferPolicyCache")
            if not isinstance(cache, dict):
                cache = {}
            cache[chain] = {"cachedAt": utc_now(), "policy": body}
            state["transferPolicyCache"] = cache
            save_state(state)
        except Exception:
            pass
        return body
    except Exception:
        # Fallback to cached policy when server/API is unavailable.
        state = load_state()
        cache = state.get("transferPolicyCache")
        if isinstance(cache, dict):
            cached = cache.get(chain)
            if isinstance(cached, dict):
                policy = cached.get("policy")
                if isinstance(policy, dict):
                    return policy
        raise WalletPolicyError(
            "transfer_policy_unavailable",
            "Outbound transfer policy could not be fetched (API unavailable) and no cached policy exists.",
            "Verify XCLAW_API_BASE_URL and XCLAW_AGENT_API_KEY, then retry; outbound transfers fail closed when policy is unavailable.",
            {"chain": chain, "path": path},
        )


def _enforce_owner_chain_enabled(chain: str, policy_payload: dict[str, Any], *, action: str) -> None:
    # Back-compat: if chainEnabled is missing, treat as enabled.
    enabled = policy_payload.get("chainEnabled", True)
    if isinstance(enabled, bool) and enabled:
        return
    if not isinstance(enabled, bool):
        raise WalletPolicyError(
            "policy_blocked",
            "Owner chain policy payload was invalid.",
            "Retry later; if this persists, update server/runtime schema alignment.",
            {"chain": chain, "field": "chainEnabled", "action": action},
        )
    raise WalletPolicyError(
        "chain_disabled",
        f"{action} blocked because chain '{chain}' is disabled by owner policy.",
        "Ask the bot owner to enable this chain on the agent management page.",
        {"chain": chain, "chainEnabled": False, "action": action},
    )


def _enforce_outbound_transfer_policy(chain: str, destination: str) -> dict[str, Any]:
    evaluated = _evaluate_outbound_transfer_policy(chain, destination)
    if not bool(evaluated.get("allowed")):
        code = str(evaluated.get("policyBlockReasonCode") or "transfer_policy_blocked")
        message = str(evaluated.get("policyBlockReasonMessage") or "Outbound transfer policy blocked this destination.")
        details = {
            "chain": chain,
            "destination": destination,
            "outboundMode": evaluated.get("outboundMode"),
            "policyBlockReasonCode": evaluated.get("policyBlockReasonCode"),
        }
        if code == "outbound_disabled":
            raise WalletPolicyError(
                "transfer_policy_blocked",
                message,
                "Ask the bot owner to enable outbound transfers on the agent management page.",
                details,
            )
        raise WalletPolicyError(
            "transfer_policy_blocked",
            message,
            "Ask the bot owner to add this destination address to the whitelist.",
            details,
        )
    return {
        "outboundTransfersEnabled": bool(evaluated.get("outboundTransfersEnabled")),
        "outboundMode": str(evaluated.get("outboundMode") or "disabled"),
        "outboundWhitelistAddresses": list(evaluated.get("outboundWhitelistAddresses") or []),
        "updatedAt": evaluated.get("updatedAt"),
    }


def _evaluate_outbound_transfer_policy(chain: str, destination: str) -> dict[str, Any]:
    policy = _fetch_outbound_transfer_policy(chain)
    _enforce_owner_chain_enabled(chain, policy, action="Spend")
    enabled = bool(policy.get("outboundTransfersEnabled"))
    mode = str(policy.get("outboundMode") or "disabled")
    whitelist_raw = policy.get("outboundWhitelistAddresses")
    whitelist = {_normalize_address(str(item)) for item in whitelist_raw if isinstance(item, str)} if isinstance(whitelist_raw, list) else set()

    policy_blocked = False
    policy_block_reason_code: str | None = None
    policy_block_reason_message: str | None = None
    if not enabled or mode == "disabled":
        policy_blocked = True
        policy_block_reason_code = "outbound_disabled"
        policy_block_reason_message = "Outbound transfers are disabled by owner policy."
    elif mode == "whitelist" and _normalize_address(destination) not in whitelist:
        policy_blocked = True
        policy_block_reason_code = "destination_not_whitelisted"
        policy_block_reason_message = "Destination is not in the outbound transfer whitelist."

    return {
        "outboundTransfersEnabled": enabled,
        "outboundMode": mode,
        "outboundWhitelistAddresses": sorted(list(whitelist)),
        "updatedAt": policy.get("updatedAt"),
        "allowed": not policy_blocked,
        "policyBlockedAtCreate": policy_blocked,
        "policyBlockReasonCode": policy_block_reason_code,
        "policyBlockReasonMessage": policy_block_reason_message,
    }


def _to_non_negative_decimal(raw: Any) -> Decimal:
    try:
        value = Decimal(str(raw))
    except Exception:
        return Decimal("0")
    if value < 0:
        return Decimal("0")
    return value


def _decimal_text(value: Decimal) -> str:
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def _to_non_negative_int(raw: Any) -> int:
    try:
        value = int(str(raw))
    except Exception:
        return 0
    return value if value >= 0 else 0


def _load_trade_cap_ledger(state: dict[str, Any], chain: str, day_key: str) -> tuple[Decimal, int]:
    ledger = state.get("tradeCapLedger")
    if not isinstance(ledger, dict):
        return Decimal("0"), 0
    chain_ledger = ledger.get(chain)
    if not isinstance(chain_ledger, dict):
        return Decimal("0"), 0
    row = chain_ledger.get(day_key)
    if not isinstance(row, dict):
        return Decimal("0"), 0
    spend = _to_non_negative_decimal(row.get("dailySpendUsd", "0"))
    filled = _to_non_negative_int(row.get("dailyFilledTrades", 0))
    return spend, filled


def _record_trade_cap_ledger(state: dict[str, Any], chain: str, day_key: str, spend_usd: Decimal, filled_trades: int) -> None:
    ledger = state.setdefault("tradeCapLedger", {})
    if not isinstance(ledger, dict):
        raise WalletStoreError("State field 'tradeCapLedger' must be an object.")
    chain_ledger = ledger.setdefault(chain, {})
    if not isinstance(chain_ledger, dict):
        raise WalletStoreError(f"State trade cap ledger for chain '{chain}' must be an object.")
    chain_ledger[day_key] = {
        "dailySpendUsd": _decimal_text(spend_usd),
        "dailyFilledTrades": int(max(0, filled_trades)),
        "updatedAt": utc_now(),
    }
    save_state(state)


def _queue_trade_usage_report(item: dict[str, Any]) -> None:
    outbox = load_trade_usage_outbox()
    outbox.append(item)
    save_trade_usage_outbox(outbox)


def _replay_trade_usage_outbox() -> tuple[int, int]:
    queued = load_trade_usage_outbox()
    if not queued:
        return 0, 0
    remaining: list[dict[str, Any]] = []
    replayed = 0
    for entry in queued:
        payload = entry.get("payload")
        idempotency_key = entry.get("idempotencyKey")
        if not isinstance(payload, dict) or not isinstance(idempotency_key, str) or not idempotency_key.strip():
            continue
        status_code, body = _api_request(
            "POST",
            "/agent/trade-usage",
            payload=payload,
            include_idempotency=True,
            idempotency_key=idempotency_key,
        )
        if status_code < 200 or status_code >= 300:
            remaining.append(entry)
            continue
        replayed += 1
    save_trade_usage_outbox(remaining)
    return replayed, len(remaining)


def _enforce_trade_caps(chain: str, projected_spend_usd: Decimal, projected_filled_trades: int) -> tuple[dict[str, Any], str, Decimal, int, dict[str, Any]]:
    policy_payload = _fetch_outbound_transfer_policy(chain)
    _enforce_owner_chain_enabled(chain, policy_payload, action="Trade")
    trade_caps = policy_payload.get("tradeCaps")
    if not isinstance(trade_caps, dict):
        raise WalletPolicyError(
            "policy_blocked",
            "Trade caps are unavailable from owner policy.",
            "Ask the bot owner to save policy settings on the agent management page and retry.",
            {"chain": chain},
        )

    day_key = _utc_day_key()
    state = load_state()

    usage_payload = policy_payload.get("dailyUsage")
    server_spend = Decimal("0")
    server_filled = 0
    if isinstance(usage_payload, dict) and str(usage_payload.get("utcDay") or "") == day_key:
        server_spend = _to_non_negative_decimal(usage_payload.get("dailySpendUsd", "0"))
        server_filled = _to_non_negative_int(usage_payload.get("dailyFilledTrades", 0))

    local_spend, local_filled = _load_trade_cap_ledger(state, chain, day_key)
    current_spend = server_spend if server_spend >= local_spend else local_spend
    current_filled = server_filled if server_filled >= local_filled else local_filled

    daily_cap_usd_enabled = bool(trade_caps.get("dailyCapUsdEnabled", True))
    daily_trade_cap_enabled = bool(trade_caps.get("dailyTradeCapEnabled", True))
    max_daily_usd = _to_non_negative_decimal(trade_caps.get("maxDailyUsd", "0"))
    max_daily_trade_count_raw = trade_caps.get("maxDailyTradeCount")
    max_daily_trade_count = _to_non_negative_int(max_daily_trade_count_raw) if max_daily_trade_count_raw is not None else None

    if daily_cap_usd_enabled and max_daily_usd > 0:
        projected_total = current_spend + max(Decimal("0"), projected_spend_usd)
        if projected_total > max_daily_usd:
            raise WalletPolicyError(
                "daily_usd_cap_exceeded",
                "Trade blocked because daily USD cap would be exceeded.",
                "Reduce amount, disable daily USD cap, or raise maxDailyUsd in owner policy.",
                {
                    "chain": chain,
                    "utcDay": day_key,
                    "currentSpendUsd": str(current_spend),
                    "projectedSpendUsd": str(max(Decimal("0"), projected_spend_usd)),
                    "maxDailyUsd": str(max_daily_usd),
                    "dailyCapUsdEnabled": True,
                },
            )

    if daily_trade_cap_enabled and max_daily_trade_count is not None:
        projected_count = max(0, int(projected_filled_trades))
        if (current_filled + projected_count) > max_daily_trade_count:
            raise WalletPolicyError(
                "daily_trade_count_cap_exceeded",
                "Trade blocked because daily filled-trade cap would be exceeded.",
                "Wait for next UTC day, disable trade-count cap, or raise maxDailyTradeCount in owner policy.",
                {
                    "chain": chain,
                    "utcDay": day_key,
                    "currentFilledTrades": int(current_filled),
                    "projectedFilledTrades": int(projected_count),
                    "maxDailyTradeCount": int(max_daily_trade_count),
                    "dailyTradeCapEnabled": True,
                },
            )

    return state, day_key, current_spend, current_filled, trade_caps


def _post_trade_usage(chain: str, utc_day: str, spend_usd_delta: Decimal, filled_trades_delta: int) -> None:
    if spend_usd_delta < 0:
        spend_usd_delta = Decimal("0")
    if filled_trades_delta < 0:
        filled_trades_delta = 0
    if spend_usd_delta == 0 and filled_trades_delta == 0:
        return

    api_key = _resolve_api_key()
    agent_id = _resolve_agent_id(api_key)
    if not agent_id:
        raise WalletStoreError("Agent id could not be resolved for trade-usage reporting.")

    idempotency_key = f"rt-usage-{chain}-{utc_day}-{secrets.token_hex(8)}"
    payload = {
        "schemaVersion": 1,
        "agentId": agent_id,
        "chainKey": chain,
        "utcDay": utc_day,
        "spendUsdDelta": _decimal_text(spend_usd_delta),
        "filledTradesDelta": int(filled_trades_delta),
    }

    status_code, body = _api_request(
        "POST",
        "/agent/trade-usage",
        payload=payload,
        include_idempotency=True,
        idempotency_key=idempotency_key,
    )
    if status_code < 200 or status_code >= 300:
        _queue_trade_usage_report({"idempotencyKey": idempotency_key, "payload": payload, "queuedAt": utc_now()})
        code = str(body.get("code", "api_error"))
        message = str(body.get("message", f"trade usage report failed ({status_code})"))
        raise WalletStoreError(f"{code}: {message}")


def _canonical_event_for_trade_status(status: str) -> str:
    mapping = {
        "proposed": "trade_proposed",
        "approval_pending": "trade_approval_pending",
        "approved": "trade_approved",
        "rejected": "trade_rejected",
        "executing": "trade_executing",
        "verifying": "trade_verifying",
        "filled": "trade_filled",
        "failed": "trade_failed",
        "expired": "trade_expired",
        "verification_timeout": "trade_verification_timeout",
    }
    return mapping.get(status, "trade_failed")


def _post_trade_proposed(
    chain: str,
    token_in: str,
    token_out: str,
    amount_in_human: str,
    slippage_bps: int,
    amount_out_human: str | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    api_key = _resolve_api_key()
    agent_id = _resolve_agent_id(api_key)
    if not agent_id:
        raise WalletStoreError("Agent id could not be resolved for trade proposal.")

    payload: dict[str, Any] = {
        "schemaVersion": 1,
        "agentId": agent_id,
        "chainKey": chain,
        "mode": "real",
        "tokenIn": token_in,
        "tokenOut": token_out,
        "amountIn": str(amount_in_human),
        "slippageBps": int(slippage_bps),
    }
    if amount_out_human is not None:
        payload["amountOut"] = str(amount_out_human)
    if reason:
        payload["reason"] = str(reason)[:140]

    idempotency_key = f"rt-propose-{chain}-{secrets.token_hex(8)}"
    status_code, body = _api_request(
        "POST",
        "/trades/proposed",
        payload=payload,
        include_idempotency=True,
        idempotency_key=idempotency_key,
    )
    if status_code < 200 or status_code >= 300:
        code = str(body.get("code", "api_error"))
        message = str(body.get("message", f"trade proposed failed ({status_code})"))
        raise WalletStoreError(f"{code}: {message}")
    if not isinstance(body, dict) or not body.get("tradeId"):
        raise WalletStoreError("Trade proposed response is missing tradeId.")
    return body


def _normalize_amount_human_text(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        return "0"
    try:
        dec = Decimal(raw)
    except (InvalidOperation, ValueError):
        # Preserve raw for hashing determinism (still stable string input).
        return raw
    if dec.is_nan() or dec.is_infinite():
        return raw
    if dec < 0:
        dec = abs(dec)
    # Bound precision to 18 decimals, then strip trailing zeros for canonical text.
    quantum = Decimal(1) / (Decimal(10) ** 18)
    try:
        dec = dec.quantize(quantum, rounding=ROUND_DOWN)
    except Exception:
        pass
    text = format(dec, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def _trade_intent_key(chain: str, token_in: str, token_out: str, amount_in_human: str, slippage_bps: int) -> str:
    canonical_amount = _normalize_amount_human_text(amount_in_human)
    payload = f"{chain}|{token_in.lower()}|{token_out.lower()}|{canonical_amount}|{int(slippage_bps)}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _load_pending_trade_intents() -> dict[str, Any]:
    try:
        ensure_app_dir()
        if not PENDING_TRADE_INTENTS_FILE.exists():
            return {"version": 1, "intents": {}}
        raw = PENDING_TRADE_INTENTS_FILE.read_text(encoding="utf-8")
        payload = json.loads(raw or "{}")
        if not isinstance(payload, dict):
            return {"version": 1, "intents": {}}
        intents = payload.get("intents")
        if not isinstance(intents, dict):
            payload["intents"] = {}
        if payload.get("version") != 1:
            return {"version": 1, "intents": {}}
        return payload
    except Exception:
        return {"version": 1, "intents": {}}


def _save_pending_trade_intents(payload: dict[str, Any]) -> None:
    ensure_app_dir()
    if payload.get("version") != 1:
        payload["version"] = 1
    if not isinstance(payload.get("intents"), dict):
        payload["intents"] = {}
    tmp = f"{PENDING_TRADE_INTENTS_FILE}.{os.getpid()}.tmp"
    pathlib.Path(tmp).write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    if os.name != "nt":
        os.chmod(tmp, 0o600)
    pathlib.Path(tmp).replace(PENDING_TRADE_INTENTS_FILE)
    if os.name != "nt":
        os.chmod(PENDING_TRADE_INTENTS_FILE, 0o600)


def _get_pending_trade_intent(intent_key: str) -> dict[str, Any] | None:
    state = _load_pending_trade_intents()
    intents = state.get("intents")
    if not isinstance(intents, dict):
        return None
    entry = intents.get(intent_key)
    return entry if isinstance(entry, dict) else None


def _record_pending_trade_intent(intent_key: str, entry: dict[str, Any]) -> None:
    state = _load_pending_trade_intents()
    intents = state.get("intents")
    if not isinstance(intents, dict):
        intents = {}
        state["intents"] = intents
    intents[intent_key] = {**entry, "updatedAt": utc_now()}
    _save_pending_trade_intents(state)


def _remove_pending_trade_intent(intent_key: str) -> None:
    state = _load_pending_trade_intents()
    intents = state.get("intents")
    if not isinstance(intents, dict):
        return
    if intent_key in intents:
        intents.pop(intent_key, None)
        _save_pending_trade_intents(state)


def _load_pending_spot_trade_flows() -> dict[str, Any]:
    try:
        ensure_app_dir()
        if not PENDING_SPOT_TRADE_FLOWS_FILE.exists():
            return {"version": 1, "flows": {}}
        raw = PENDING_SPOT_TRADE_FLOWS_FILE.read_text(encoding="utf-8")
        payload = json.loads(raw or "{}")
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


def _save_pending_spot_trade_flows(payload: dict[str, Any]) -> None:
    ensure_app_dir()
    if payload.get("version") != 1:
        payload["version"] = 1
    if not isinstance(payload.get("flows"), dict):
        payload["flows"] = {}
    tmp = f"{PENDING_SPOT_TRADE_FLOWS_FILE}.{os.getpid()}.tmp"
    pathlib.Path(tmp).write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    if os.name != "nt":
        os.chmod(tmp, 0o600)
    pathlib.Path(tmp).replace(PENDING_SPOT_TRADE_FLOWS_FILE)
    if os.name != "nt":
        os.chmod(PENDING_SPOT_TRADE_FLOWS_FILE, 0o600)


def _get_pending_spot_trade_flow(trade_id: str) -> dict[str, Any] | None:
    state = _load_pending_spot_trade_flows()
    flows = state.get("flows")
    if not isinstance(flows, dict):
        return None
    entry = flows.get(trade_id)
    return entry if isinstance(entry, dict) else None


def _record_pending_spot_trade_flow(trade_id: str, entry: dict[str, Any]) -> None:
    state = _load_pending_spot_trade_flows()
    flows = state.get("flows")
    if not isinstance(flows, dict):
        flows = {}
        state["flows"] = flows
    flows[trade_id] = {**entry, "updatedAt": utc_now()}
    _save_pending_spot_trade_flows(state)


def _remove_pending_spot_trade_flow(trade_id: str) -> None:
    state = _load_pending_spot_trade_flows()
    flows = state.get("flows")
    if not isinstance(flows, dict):
        return
    if trade_id in flows:
        flows.pop(trade_id, None)
        _save_pending_spot_trade_flows(state)


def _load_pending_transfer_flows() -> dict[str, Any]:
    try:
        ensure_app_dir()
        if not PENDING_TRANSFER_FLOWS_FILE.exists():
            return {"version": 1, "flows": {}}
        raw = PENDING_TRANSFER_FLOWS_FILE.read_text(encoding="utf-8")
        payload = json.loads(raw or "{}")
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


def _save_pending_transfer_flows(payload: dict[str, Any]) -> None:
    ensure_app_dir()
    if payload.get("version") != 1:
        payload["version"] = 1
    if not isinstance(payload.get("flows"), dict):
        payload["flows"] = {}
    tmp = f"{PENDING_TRANSFER_FLOWS_FILE}.{os.getpid()}.tmp"
    pathlib.Path(tmp).write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    if os.name != "nt":
        os.chmod(tmp, 0o600)
    pathlib.Path(tmp).replace(PENDING_TRANSFER_FLOWS_FILE)
    if os.name != "nt":
        os.chmod(PENDING_TRANSFER_FLOWS_FILE, 0o600)


def _get_pending_transfer_flow(approval_id: str) -> dict[str, Any] | None:
    state = _load_pending_transfer_flows()
    flows = state.get("flows")
    if not isinstance(flows, dict):
        return None
    entry = flows.get(approval_id)
    return entry if isinstance(entry, dict) else None


def _record_pending_transfer_flow(approval_id: str, entry: dict[str, Any]) -> None:
    state = _load_pending_transfer_flows()
    flows = state.get("flows")
    if not isinstance(flows, dict):
        flows = {}
        state["flows"] = flows
    flows[approval_id] = {**entry, "updatedAt": utc_now()}
    _save_pending_transfer_flows(state)


def _remove_pending_transfer_flow(approval_id: str) -> None:
    state = _load_pending_transfer_flows()
    flows = state.get("flows")
    if not isinstance(flows, dict):
        return
    if approval_id in flows:
        flows.pop(approval_id, None)
        _save_pending_transfer_flows(state)


def _default_transfer_policy() -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "chains": {},
    }


def _load_transfer_policy_state() -> dict[str, Any]:
    try:
        ensure_app_dir()
        if not TRANSFER_POLICY_FILE.exists():
            return _default_transfer_policy()
        payload = _read_json(TRANSFER_POLICY_FILE)
        if not isinstance(payload, dict):
            return _default_transfer_policy()
        if payload.get("schemaVersion") != 1:
            return _default_transfer_policy()
        chains = payload.get("chains")
        if not isinstance(chains, dict):
            payload["chains"] = {}
        return payload
    except Exception:
        return _default_transfer_policy()


def _save_transfer_policy_state(payload: dict[str, Any]) -> None:
    if payload.get("schemaVersion") != 1:
        payload["schemaVersion"] = 1
    chains = payload.get("chains")
    if not isinstance(chains, dict):
        payload["chains"] = {}
    _write_json(TRANSFER_POLICY_FILE, payload)


def _normalize_transfer_policy(chain: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    mode = str(payload.get("transferApprovalMode") or "per_transfer").strip().lower()
    if mode not in {"auto", "per_transfer"}:
        mode = "per_transfer"
    native_preapproved = bool(payload.get("nativeTransferPreapproved", False))
    raw_tokens = payload.get("allowedTransferTokens")
    out_tokens: list[str] = []
    if isinstance(raw_tokens, list):
        seen: set[str] = set()
        for token in raw_tokens:
            if not isinstance(token, str):
                continue
            normalized = token.strip().lower()
            if re.fullmatch(r"0x[a-f0-9]{40}", normalized) and normalized not in seen:
                seen.add(normalized)
                out_tokens.append(normalized)
    updated_at = str(payload.get("updatedAt") or "").strip() or utc_now()
    return {
        "chainKey": chain,
        "transferApprovalMode": mode,
        "nativeTransferPreapproved": native_preapproved,
        "allowedTransferTokens": out_tokens,
        "updatedAt": updated_at,
    }


def _get_transfer_policy(chain: str) -> dict[str, Any]:
    state = _load_transfer_policy_state()
    chains = state.get("chains")
    if not isinstance(chains, dict):
        chains = {}
    row = chains.get(chain)
    if not isinstance(row, dict):
        row = {}
    return _normalize_transfer_policy(chain, row)


def _set_transfer_policy(chain: str, policy: dict[str, Any]) -> dict[str, Any]:
    normalized = _normalize_transfer_policy(chain, policy)
    state = _load_transfer_policy_state()
    chains = state.get("chains")
    if not isinstance(chains, dict):
        chains = {}
        state["chains"] = chains
    chains[chain] = normalized
    _save_transfer_policy_state(state)
    return normalized


def _sync_transfer_policy_from_remote(chain: str) -> dict[str, Any]:
    local = _get_transfer_policy(chain)
    try:
        status_code, body = _api_request("GET", f"/agent/transfer-policy?chainKey={urllib.parse.quote(chain)}")
        if status_code < 200 or status_code >= 300:
            return local
        remote_raw = body.get("transferPolicy")
        if not isinstance(remote_raw, dict):
            return local
        remote = _normalize_transfer_policy(chain, remote_raw)
        try:
            local_updated = datetime.fromisoformat(str(local.get("updatedAt")).replace("Z", "+00:00"))
            remote_updated = datetime.fromisoformat(str(remote.get("updatedAt")).replace("Z", "+00:00"))
            if remote_updated <= local_updated:
                return local
        except Exception:
            pass
        return _set_transfer_policy(chain, remote)
    except Exception:
        return local


def _mirror_transfer_approval(flow: dict[str, Any]) -> None:
    try:
        approval_id = str(flow.get("approvalId") or "").strip()
        chain = str(flow.get("chainKey") or "").strip()
        if not approval_id or not chain:
            return
        payload = {
            "schemaVersion": 1,
            "approvalId": approval_id,
            "chainKey": chain,
            "status": str(flow.get("status") or "approval_pending"),
            "transferType": str(flow.get("transferType") or "native"),
            "tokenAddress": flow.get("tokenAddress"),
            "tokenSymbol": flow.get("tokenSymbol"),
            "toAddress": flow.get("toAddress"),
            "amountWei": str(flow.get("amountWei") or "0"),
            "txHash": flow.get("txHash"),
            "reasonCode": flow.get("reasonCode"),
            "reasonMessage": flow.get("reasonMessage"),
            "policyBlockedAtCreate": bool(flow.get("policyBlockedAtCreate", False)),
            "policyBlockReasonCode": flow.get("policyBlockReasonCode"),
            "policyBlockReasonMessage": flow.get("policyBlockReasonMessage"),
            "executionMode": flow.get("executionMode"),
            "createdAt": flow.get("createdAt") or utc_now(),
            "updatedAt": flow.get("updatedAt") or utc_now(),
            "decidedAt": flow.get("decidedAt"),
            "terminalAt": flow.get("terminalAt"),
        }
        _api_request(
            "POST",
            "/agent/transfer-approvals/mirror",
            payload=payload,
            include_idempotency=True,
            idempotency_key=f"rt-transfer-mirror-{approval_id}-{secrets.token_hex(8)}",
        )
    except Exception:
        pass


def _mirror_transfer_policy(chain: str, policy: dict[str, Any]) -> None:
    try:
        payload = {
            "agentId": _resolve_agent_id(_resolve_api_key()),
            "chainKey": chain,
            "transferPolicy": _normalize_transfer_policy(chain, policy),
        }
        _api_request(
            "POST",
            "/agent/transfer-policy/mirror",
            payload=payload,
            include_idempotency=True,
            idempotency_key=f"rt-transfer-policy-{chain}-{secrets.token_hex(8)}",
        )
    except Exception:
        pass


def _mirror_x402_outbound(flow: dict[str, Any]) -> None:
    try:
        approval_id = str(flow.get("approvalId") or "").strip()
        network = str(flow.get("network") or "").strip()
        facilitator = str(flow.get("facilitator") or "").strip()
        url = str(flow.get("url") or "").strip()
        amount_atomic = str(flow.get("amountAtomic") or "").strip()
        if not approval_id or not network or not facilitator or not url or not amount_atomic:
            return

        payment_id = str(flow.get("paymentId") or "").strip() or f"xpm_{secrets.token_hex(10)}"
        flow["paymentId"] = payment_id
        payload = {
            "schemaVersion": 1,
            "paymentId": payment_id,
            "approvalId": approval_id,
            "networkKey": network,
            "facilitatorKey": facilitator,
            "status": str(flow.get("status") or "approval_pending"),
            "assetKind": str(flow.get("assetKind") or "native"),
            "assetAddress": flow.get("assetAddress"),
            "assetSymbol": flow.get("assetSymbol"),
            "amountAtomic": amount_atomic,
            "url": url,
            "txHash": flow.get("txHash"),
            "reasonCode": flow.get("reasonCode"),
            "reasonMessage": flow.get("reasonMessage"),
            "createdAt": flow.get("createdAt") or utc_now(),
            "updatedAt": flow.get("updatedAt") or utc_now(),
            "terminalAt": flow.get("terminalAt"),
        }
        _api_request(
            "POST",
            "/agent/x402/outbound/mirror",
            payload=payload,
            include_idempotency=True,
            idempotency_key=f"rt-x402-mirror-{approval_id}-{secrets.token_hex(8)}",
        )

        approval_payload = {
            "schemaVersion": 1,
            "approvalId": approval_id,
            "chainKey": network,
            "approvalSource": "x402",
            "status": str(flow.get("status") or "approval_pending"),
            "transferType": "native",
            "tokenAddress": None,
            "tokenSymbol": str(flow.get("assetSymbol") or "X402"),
            "toAddress": "0x0000000000000000000000000000000000000000",
            "amountWei": amount_atomic,
            "txHash": flow.get("txHash"),
            "reasonCode": flow.get("reasonCode"),
            "reasonMessage": flow.get("reasonMessage"),
            "policyBlockedAtCreate": False,
            "policyBlockReasonCode": None,
            "policyBlockReasonMessage": None,
            "executionMode": "normal",
            "x402Url": url,
            "x402NetworkKey": network,
            "x402FacilitatorKey": facilitator,
            "x402AssetKind": str(flow.get("assetKind") or "native"),
            "x402AssetAddress": flow.get("assetAddress"),
            "x402AmountAtomic": amount_atomic,
            "x402PaymentId": payment_id,
            "createdAt": flow.get("createdAt") or utc_now(),
            "updatedAt": flow.get("updatedAt") or utc_now(),
            "decidedAt": flow.get("decidedAt"),
            "terminalAt": flow.get("terminalAt"),
        }
        _api_request(
            "POST",
            "/agent/transfer-approvals/mirror",
            payload=approval_payload,
            include_idempotency=True,
            idempotency_key=f"rt-x402-transfer-mirror-{approval_id}-{secrets.token_hex(8)}",
        )
    except Exception:
        pass


def _transfer_requires_approval(chain: str, transfer_type: str, token_address: str | None) -> tuple[bool, dict[str, Any]]:
    policy = _sync_transfer_policy_from_remote(chain)
    mode = str(policy.get("transferApprovalMode") or "per_transfer")
    if mode == "auto":
        return False, policy
    if transfer_type == "native":
        return (not bool(policy.get("nativeTransferPreapproved", False))), policy
    if token_address:
        normalized = token_address.strip().lower()
        allowed = policy.get("allowedTransferTokens")
        if isinstance(allowed, list):
            for item in allowed:
                if isinstance(item, str) and item.strip().lower() == normalized:
                    return False, policy
    return True, policy


def _make_transfer_approval_id() -> str:
    return f"xfr_{secrets.token_hex(10)}"


def _transfer_amount_display(
    amount_wei: str | int,
    transfer_type: str,
    token_symbol: str | None,
    token_decimals: int | None,
) -> tuple[str, str]:
    try:
        amount_int = int(str(amount_wei).strip())
    except Exception:
        return str(amount_wei), str(token_symbol or ("ETH" if transfer_type == "native" else "TOKEN"))
    if amount_int < 0:
        amount_int = 0
    unit = "ETH" if transfer_type == "native" else (str(token_symbol or "TOKEN").strip() or "TOKEN")
    decimals = 18
    if transfer_type == "token":
        try:
            decimals = int(token_decimals if token_decimals is not None else 18)
        except Exception:
            decimals = 18
        if decimals < 0:
            decimals = 18
    return _format_units(amount_int, decimals), unit


def _execute_pending_transfer_flow(flow: dict[str, Any]) -> dict[str, Any]:
    approval_id = str(flow.get("approvalId") or "").strip()
    chain = str(flow.get("chainKey") or "").strip()
    transfer_type = str(flow.get("transferType") or "native").strip().lower()
    amount_wei = str(flow.get("amountWei") or "0").strip()
    to_address = str(flow.get("toAddress") or "").strip()
    token_address = str(flow.get("tokenAddress") or "").strip().lower() if transfer_type == "token" else None
    token_symbol = str(flow.get("tokenSymbol") or ("ETH" if transfer_type == "native" else "TOKEN")).strip()
    token_decimals_raw = flow.get("tokenDecimals", 18 if transfer_type == "native" else None)
    token_decimals: int | None
    try:
        token_decimals = int(token_decimals_raw) if token_decimals_raw is not None else None
    except Exception:
        token_decimals = 18 if transfer_type == "native" else None
    amount_human, amount_unit = _transfer_amount_display(amount_wei, transfer_type, token_symbol, token_decimals)
    amount_display = f"{amount_human} {amount_unit}"
    if not approval_id or not chain:
        return {"ok": False, "code": "invalid_state", "message": "Missing approvalId/chain in transfer flow."}
    if not re.fullmatch(r"[0-9]+", amount_wei):
        return {"ok": False, "code": "invalid_state", "message": "Transfer flow amountWei must be uint."}
    if not is_hex_address(to_address):
        return {"ok": False, "code": "invalid_state", "message": "Transfer flow destination is invalid."}
    if transfer_type == "token" and (not token_address or not is_hex_address(token_address)):
        return {"ok": False, "code": "invalid_state", "message": "Transfer token address is invalid."}

    outbound_eval = _evaluate_outbound_transfer_policy(chain, to_address)
    policy_blocked_now = not bool(outbound_eval.get("allowed"))
    policy_blocked_at_create = bool(flow.get("policyBlockedAtCreate", False))
    execution_mode = "normal"
    if policy_blocked_now:
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
    flow["updatedAt"] = utc_now()
    _record_pending_transfer_flow(approval_id, flow)
    _mirror_transfer_approval(flow)

    try:
        amount_int = int(amount_wei)
        state, day_key, current_spend, max_daily_wei = _enforce_spend_preconditions(chain, amount_int)
        transfer_policy = {
            "outboundTransfersEnabled": bool(outbound_eval.get("outboundTransfersEnabled")),
            "outboundMode": str(outbound_eval.get("outboundMode") or "disabled"),
            "outboundWhitelistAddresses": list(outbound_eval.get("outboundWhitelistAddresses") or []),
            "updatedAt": outbound_eval.get("updatedAt"),
            "policyBlockedAtCreate": policy_blocked_at_create,
            "policyBlockReasonCode": flow.get("policyBlockReasonCode") or outbound_eval.get("policyBlockReasonCode"),
            "policyBlockReasonMessage": flow.get("policyBlockReasonMessage") or outbound_eval.get("policyBlockReasonMessage"),
            "executionMode": execution_mode,
        }

        store = load_wallet_store()
        _, wallet = _chain_wallet(store, chain)
        if wallet is None:
            raise WalletStoreError(f"No wallet configured for chain '{chain}'.")
        _validate_wallet_entry_shape(wallet)
        passphrase = _require_wallet_passphrase_for_signing(chain)
        private_key_hex = _decrypt_private_key(wallet, passphrase).hex()

        tx_hash: str
        if transfer_type == "native":
            cast_bin = _require_cast_bin()
            rpc_url = _chain_rpc_url(chain)
            proc = _run_subprocess(
                [cast_bin, "send", "--json", "--rpc-url", rpc_url, "--private-key", private_key_hex, to_address, amount_wei],
                timeout_sec=_cast_send_timeout_sec(),
                kind="cast_send",
            )
            if proc.returncode != 0:
                stderr = (proc.stderr or "").strip()
                stdout = (proc.stdout or "").strip()
                raise WalletStoreError(stderr or stdout or "cast send failed.")
            tx_hash = _extract_tx_hash(proc.stdout)
        else:
            from_address = str(wallet.get("address"))
            rpc_url = _chain_rpc_url(chain)
            data = _cast_calldata("transfer(address,uint256)(bool)", [to_address, amount_wei])
            tx_hash = _cast_rpc_send_transaction(
                rpc_url,
                {"from": from_address, "to": str(token_address), "data": data},
                private_key_hex,
            )
            cast_bin = _require_cast_bin()
            receipt_proc = _run_subprocess(
                [cast_bin, "receipt", "--json", "--rpc-url", rpc_url, tx_hash],
                timeout_sec=_cast_receipt_timeout_sec(),
                kind="cast_receipt",
            )
            if receipt_proc.returncode != 0:
                stderr = (receipt_proc.stderr or "").strip()
                stdout = (receipt_proc.stdout or "").strip()
                raise WalletStoreError(stderr or stdout or "cast receipt failed.")
            receipt_payload = json.loads((receipt_proc.stdout or "{}").strip() or "{}")
            receipt_status = str(receipt_payload.get("status", "0x0")).lower()
            if receipt_status not in {"0x1", "1"}:
                raise WalletStoreError(f"On-chain receipt indicates failure status '{receipt_status}'.")

        _record_spend(state, chain, day_key, current_spend + amount_int)
        flow["status"] = "filled"
        flow["txHash"] = tx_hash
        flow["updatedAt"] = utc_now()
        flow["terminalAt"] = flow["updatedAt"]
        _record_pending_transfer_flow(approval_id, flow)
        _mirror_transfer_approval(flow)
        _remove_pending_transfer_flow(approval_id)
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
            "txHash": tx_hash,
            "day": day_key,
            "dailySpendWei": str(current_spend + amount_int),
            "maxDailyNativeWei": str(max_daily_wei),
            "transferPolicy": transfer_policy,
            "policyBlockedAtCreate": policy_blocked_at_create,
            "policyBlockReasonCode": flow.get("policyBlockReasonCode"),
            "policyBlockReasonMessage": flow.get("policyBlockReasonMessage"),
            "executionMode": execution_mode,
        }
    except Exception as exc:
        message = str(exc) or "Transfer execution failed."
        flow["status"] = "failed"
        flow["reasonCode"] = "transfer_execution_failed"
        flow["reasonMessage"] = message
        flow["updatedAt"] = utc_now()
        flow["terminalAt"] = flow["updatedAt"]
        _record_pending_transfer_flow(approval_id, flow)
        _mirror_transfer_approval(flow)
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
            "txHash": flow.get("txHash"),
            "reasonCode": "transfer_execution_failed",
            "reasonMessage": message,
            "policyBlockedAtCreate": policy_blocked_at_create,
            "policyBlockReasonCode": flow.get("policyBlockReasonCode"),
            "policyBlockReasonMessage": flow.get("policyBlockReasonMessage"),
            "executionMode": execution_mode,
        }


def _wait_for_trade_approval(trade_id: str, chain: str, summary: dict[str, Any] | None = None) -> dict[str, Any]:
    # Telegram approval prompts can be delivered either:
    # - inline in the agent's chat response (preferred; no extra prompt message), or
    # - out-of-band via `openclaw message send --buttons` (legacy).
    #
    # Default is inline (do not send an extra prompt message). Set
    # `XCLAW_TELEGRAM_OUT_OF_BAND_APPROVAL_PROMPT=1` to re-enable legacy prompting.
    if (os.environ.get("XCLAW_TELEGRAM_OUT_OF_BAND_APPROVAL_PROMPT") or "").strip() == "1":
        try:
            _maybe_send_telegram_approval_prompt(trade_id, chain, summary or {})
        except Exception:
            pass
    deadline_ms = int(time.time() * 1000) + (APPROVAL_WAIT_TIMEOUT_SEC * 1000)
    last_status: str | None = None
    while int(time.time() * 1000) <= deadline_ms:
        trade = _read_trade_details(trade_id)
        status = str(trade.get("status") or "")
        last_status = status
        if status == "approved":
            try:
                _maybe_delete_telegram_approval_prompt(trade_id)
            except Exception:
                pass
            _remove_approval_prompt(trade_id)
            try:
                _maybe_send_telegram_decision_message(
                    trade_id=trade_id,
                    chain=chain,
                    decision="approved",
                    summary=summary,
                    trade=trade,
                )
            except Exception:
                pass
            _remove_pending_spot_trade_flow(trade_id)
            return trade
        if status == "approval_pending":
            time.sleep(APPROVAL_WAIT_POLL_SEC)
            continue
        if status == "rejected":
            try:
                _maybe_delete_telegram_approval_prompt(trade_id)
            except Exception:
                pass
            _remove_approval_prompt(trade_id)
            try:
                _maybe_send_telegram_decision_message(
                    trade_id=trade_id,
                    chain=chain,
                    decision="rejected",
                    summary=summary,
                    trade=trade,
                )
            except Exception:
                pass
            _remove_pending_spot_trade_flow(trade_id)
            reason_code = trade.get("reasonCode")
            reason_message = trade.get("reasonMessage")
            raise WalletPolicyError(
                "approval_rejected",
                "Trade approval was rejected.",
                "Review rejection reason and create a new trade if needed.",
                {"tradeId": trade_id, "chain": chain, "reasonCode": reason_code, "reasonMessage": reason_message},
            )
        if status == "expired":
            try:
                _maybe_delete_telegram_approval_prompt(trade_id)
            except Exception:
                pass
            _remove_approval_prompt(trade_id)
            _remove_pending_spot_trade_flow(trade_id)
            raise WalletPolicyError(
                "approval_expired",
                "Trade approval has expired.",
                "Re-propose trade and request approval again.",
                {"tradeId": trade_id, "chain": chain},
            )
        # Any other status is not actionable for approval gating; fail closed.
        try:
            _maybe_delete_telegram_approval_prompt(trade_id)
        except Exception:
            pass
        _remove_approval_prompt(trade_id)
        _remove_pending_spot_trade_flow(trade_id)
        raise WalletPolicyError(
            "policy_denied",
            f"Trade is not executable from status '{status}'.",
            "Poll intents and execute only actionable trades.",
            {"tradeId": trade_id, "chain": chain, "status": status},
        )

    raise WalletPolicyError(
        "approval_required",
        "Trade is waiting for management approval.",
        "Approve the pending trade (Telegram or web), then re-run the same trade command to resume without creating a new approval.",
        {"tradeId": trade_id, "chain": chain, "lastStatus": last_status},
    )


def _load_approval_prompts() -> dict[str, Any]:
    try:
        ensure_app_dir()
        if not APPROVAL_PROMPTS_FILE.exists():
            return {"prompts": {}}
        raw = APPROVAL_PROMPTS_FILE.read_text(encoding="utf-8")
        payload = json.loads(raw or "{}")
        if not isinstance(payload, dict):
            return {"prompts": {}}
        prompts = payload.get("prompts")
        if not isinstance(prompts, dict):
            payload["prompts"] = {}
        return payload
    except Exception:
        return {"prompts": {}}


def _save_approval_prompts(payload: dict[str, Any]) -> None:
    ensure_app_dir()
    if not isinstance(payload.get("prompts"), dict):
        payload["prompts"] = {}
    tmp = f"{APPROVAL_PROMPTS_FILE}.{os.getpid()}.tmp"
    pathlib.Path(tmp).write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    os.chmod(tmp, 0o600)
    pathlib.Path(tmp).replace(APPROVAL_PROMPTS_FILE)
    os.chmod(APPROVAL_PROMPTS_FILE, 0o600)


def _record_approval_prompt(trade_id: str, prompt: dict[str, Any]) -> None:
    state = _load_approval_prompts()
    prompts = state.get("prompts")
    if not isinstance(prompts, dict):
        prompts = {}
        state["prompts"] = prompts
    prompts[trade_id] = {**prompt, "updatedAt": utc_now()}
    _save_approval_prompts(state)


def _get_approval_prompt(trade_id: str) -> dict[str, Any] | None:
    state = _load_approval_prompts()
    prompts = state.get("prompts")
    if not isinstance(prompts, dict):
        return None
    entry = prompts.get(trade_id)
    return entry if isinstance(entry, dict) else None


def _remove_approval_prompt(trade_id: str) -> None:
    state = _load_approval_prompts()
    prompts = state.get("prompts")
    if not isinstance(prompts, dict):
        return
    if trade_id in prompts:
        prompts.pop(trade_id, None)
        _save_approval_prompts(state)


def _approval_channels_enabled(policy_payload: dict[str, Any], channel: str) -> bool:
    channels = policy_payload.get("approvalChannels")
    if not isinstance(channels, dict):
        return False
    entry = channels.get(channel)
    if not isinstance(entry, dict):
        return False
    enabled = entry.get("enabled", False)
    return bool(enabled)


def _openclaw_state_dir() -> pathlib.Path:
    raw = (os.environ.get("OPENCLAW_STATE_DIR") or "").strip()
    if raw:
        return pathlib.Path(raw).expanduser()
    return pathlib.Path.home() / ".openclaw"


def _sanitize_openclaw_agent_id(value: str | None) -> str:
    raw = (value or "").strip() or "main"
    if re.fullmatch(r"[A-Za-z0-9_-]{1,64}", raw):
        return raw.lower()
    return "main"


def _read_openclaw_last_delivery() -> dict[str, Any] | None:
    """
    Read OpenClaw session store and return best-effort last delivery context:
      { lastChannel, lastTo, lastThreadId }
    """
    agent_id = _sanitize_openclaw_agent_id(os.environ.get("XCLAW_OPENCLAW_AGENT_ID"))
    store_path = _openclaw_state_dir() / "agents" / agent_id / "sessions" / "sessions.json"
    if not store_path.exists():
        return None
    try:
        raw = store_path.read_text(encoding="utf-8")
        payload = json.loads(raw or "{}")
        if not isinstance(payload, dict):
            return None
        best: dict[str, Any] | None = None
        best_updated = -1
        for _, entry in payload.items():
            if not isinstance(entry, dict):
                continue
            updated = entry.get("updatedAt")
            try:
                updated_ms = int(updated) if updated is not None else 0
            except Exception:
                updated_ms = 0
            last_channel = str(entry.get("lastChannel") or "").strip().lower()
            last_to = str(entry.get("lastTo") or "").strip()
            if not last_channel or not last_to:
                continue
            if updated_ms >= best_updated:
                best_updated = updated_ms
                best = {
                    "lastChannel": last_channel,
                    "lastTo": last_to,
                    "lastThreadId": entry.get("lastThreadId"),
                }
        return best
    except Exception:
        return None


def _require_openclaw_bin() -> str:
    path = shutil.which("openclaw")
    if not path:
        raise WalletStoreError("Missing dependency: openclaw (required for Telegram approval prompts).")
    return path


def _extract_openclaw_message_id(stdout: str) -> str | None:
    try:
        payload = json.loads((stdout or "").strip() or "{}")
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    inner = payload.get("payload")
    if isinstance(inner, dict):
        direct = inner.get("messageId")
        if isinstance(direct, str) and direct.strip():
            return direct.strip()
        nested = inner.get("result")
        if isinstance(nested, dict):
            nested_id = nested.get("messageId")
            if isinstance(nested_id, str) and nested_id.strip():
                return nested_id.strip()
    return None


def _post_approval_prompt_metadata(trade_id: str, chain: str, to_addr: str, thread_id: str | None, message_id: str) -> None:
    payload: dict[str, Any] = {
        "schemaVersion": 1,
        "tradeId": trade_id,
        "chainKey": chain,
        "channel": "telegram",
        "to": to_addr,
        "messageId": message_id,
    }
    if thread_id:
        payload["threadId"] = thread_id
    status_code, body = _api_request(
        "POST",
        "/agent/approvals/prompt",
        payload=payload,
        include_idempotency=True,
        idempotency_key=f"rt-appr-prompt-{trade_id}-{secrets.token_hex(8)}",
    )
    if status_code < 200 or status_code >= 300:
        code = str(body.get("code", "api_error"))
        message = str(body.get("message", f"prompt report failed ({status_code})"))
        raise WalletStoreError(f"{code}: {message}")

def _maybe_send_telegram_approval_prompt(trade_id: str, chain: str, summary: dict[str, Any] | None = None) -> None:
    # Avoid duplicate sends.
    existing = _get_approval_prompt(trade_id)
    if existing and str(existing.get("channel") or "") == "telegram":
        return

    policy = _fetch_outbound_transfer_policy(chain)
    if not _approval_channels_enabled(policy, "telegram"):
        return

    delivery = _read_openclaw_last_delivery()
    if not delivery or str(delivery.get("lastChannel") or "").lower() != "telegram":
        return

    chat_id = str(delivery.get("lastTo") or "").strip()
    if not chat_id:
        return

    thread_raw = delivery.get("lastThreadId")
    thread_id: str | None = None
    if isinstance(thread_raw, int):
        thread_id = str(thread_raw)
    elif isinstance(thread_raw, str) and thread_raw.strip():
        thread_id = thread_raw.strip()

    callback_approve = f"xappr|a|{trade_id}|{chain}"
    callback_reject = f"xappr|r|{trade_id}|{chain}"
    if len(callback_approve.encode("utf-8")) > 64 or len(callback_reject.encode("utf-8")) > 64:
        # Fail closed: do not send a prompt we can't action safely.
        return

    summary = summary or {}
    amount = str(summary.get("amountInHuman") or "").strip() or "?"
    token_in_symbol = str(summary.get("tokenInSymbol") or "").strip() or "TOKEN_IN"
    token_out_symbol = str(summary.get("tokenOutSymbol") or "").strip() or "TOKEN_OUT"
    text = (
        "Approve swap\n"
        f"{amount} {token_in_symbol} -> {token_out_symbol}\n"
        f"Chain: {chain}\n"
        f"Trade: {trade_id}\n\n"
        "Tap Approve to continue (or Deny to reject). This will submit an on-chain transaction from the agent wallet."
    )
    # Telegram does not support per-button colors; use text labels only.
    buttons = json.dumps(
        [[{"text": "Approve", "callback_data": callback_approve}, {"text": "Deny", "callback_data": callback_reject}]],
        separators=(",", ":"),
    )
    openclaw = _require_openclaw_bin()
    cmd = [openclaw, "message", "send", "--channel", "telegram", "--target", chat_id, "--message", text, "--buttons", buttons, "--json"]
    if thread_id:
        cmd.extend(["--thread-id", thread_id])
    proc = _run_subprocess(cmd, timeout_sec=30, kind="openclaw_send")
    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        stdout = (proc.stdout or "").strip()
        raise WalletStoreError(stderr or stdout or "openclaw message send failed.")

    message_id = _extract_openclaw_message_id(proc.stdout or "")
    if not message_id:
        # We still record a stub so sync can handle later; without messageId delete won't work.
        message_id = "unknown"

    _record_approval_prompt(
        trade_id,
        {
            "channel": "telegram",
            "chainKey": chain,
            "to": chat_id,
            "threadId": thread_id,
            "messageId": message_id,
            "createdAt": utc_now(),
        },
    )

    # Best-effort server sync; failures should not block local wait loop.
    try:
        _post_approval_prompt_metadata(trade_id, chain, chat_id, thread_id, message_id)
    except Exception:
        pass


def _maybe_send_telegram_decision_message(
    *,
    trade_id: str,
    chain: str,
    decision: str,
    summary: dict[str, Any] | None,
    trade: dict[str, Any] | None,
) -> None:
    """
    Best-effort acknowledgement into the active Telegram chat when an approval is decided.
    This is advisory UX only and must never gate execution.
    """
    # Prefer the exact prompt destination when available; session-store "last delivery" can drift.
    chat_id = ""
    thread_id: str | None = None
    prompt = _get_approval_prompt(trade_id)
    if prompt and str(prompt.get("channel") or "") == "telegram":
        chat_id = str(prompt.get("to") or "").strip()
        thread_raw = prompt.get("threadId")
        if isinstance(thread_raw, int):
            thread_id = str(thread_raw)
        elif isinstance(thread_raw, str) and thread_raw.strip():
            thread_id = thread_raw.strip()
    if not chat_id:
        delivery = _read_openclaw_last_delivery()
        if not delivery or str(delivery.get("lastChannel") or "").lower() != "telegram":
            return
        chat_id = str(delivery.get("lastTo") or "").strip()
        if not chat_id:
            return
        thread_raw = delivery.get("lastThreadId")
        if isinstance(thread_raw, int):
            thread_id = str(thread_raw)
        elif isinstance(thread_raw, str) and thread_raw.strip():
            thread_id = thread_raw.strip()

    summary = summary or {}
    trade = trade or {}
    amount = str(summary.get("amountInHuman") or "").strip() or str(trade.get("amountIn") or "").strip() or "?"
    token_in = str(summary.get("tokenInSymbol") or "").strip() or str(trade.get("tokenIn") or "").strip() or "TOKEN_IN"
    token_out = str(summary.get("tokenOutSymbol") or "").strip() or str(trade.get("tokenOut") or "").strip() or "TOKEN_OUT"
    slip = summary.get("slippageBps")
    slip_str = ""
    try:
        if slip is not None:
            slip_str = f" (slippage {int(slip)} bps)"
    except Exception:
        slip_str = ""

    if decision == "approved":
        title = "Approved"
        suffix = "Executing now."
    else:
        title = "Denied"
        reason_code = str(trade.get("reasonCode") or "").strip()
        reason_message = str(trade.get("reasonMessage") or "").strip()
        reason = reason_message or reason_code or "Denied."
        suffix = f"Reason: {reason}"

    text = (
        f"{title} swap\n"
        f"{amount} {token_in} -> {token_out}{slip_str}\n"
        f"Chain: {chain}\n"
        f"Trade: {trade_id}\n\n"
        f"{suffix}"
    )

    openclaw = shutil.which("openclaw")
    if not openclaw:
        return
    cmd = [openclaw, "message", "send", "--channel", "telegram", "--target", chat_id, "--message", text, "--json"]
    if thread_id:
        cmd.extend(["--thread-id", thread_id])
    proc = _run_subprocess(cmd, timeout_sec=20, kind="openclaw_send")
    if proc.returncode != 0:
        return


def _maybe_delete_telegram_approval_prompt(trade_id: str) -> None:
    entry = _get_approval_prompt(trade_id)
    if not entry or str(entry.get("channel") or "") != "telegram":
        return
    chat_id = str(entry.get("to") or "").strip()
    message_id = str(entry.get("messageId") or "").strip()
    if not chat_id or not message_id or message_id == "unknown":
        _remove_approval_prompt(trade_id)
        return
    openclaw = shutil.which("openclaw")
    if not openclaw:
        return
    cmd = [openclaw, "message", "delete", "--channel", "telegram", "--target", chat_id, "--message-id", message_id, "--json"]
    proc = _run_subprocess(cmd, timeout_sec=20, kind="openclaw_delete")
    if proc.returncode == 0:
        _remove_approval_prompt(trade_id)


def _maybe_send_owner_link_to_active_chat(management_url: str, expires_at: str | None) -> dict[str, Any]:
    """
    Best-effort direct owner-link handoff into the currently active chat channel.
    This path is intentionally non-blocking: failures should not prevent returning the link payload.
    """
    delivery = _read_openclaw_last_delivery()
    if not delivery:
        return {"sent": False, "reason": "no_active_delivery"}
    channel = str(delivery.get("lastChannel") or "").strip().lower()
    target = str(delivery.get("lastTo") or "").strip()
    if not channel or not target:
        return {"sent": False, "reason": "missing_channel_or_target"}
    openclaw = shutil.which("openclaw")
    if not openclaw:
        return {"sent": False, "reason": "openclaw_missing"}

    message = f"Owner management link:\n{management_url}"
    if isinstance(expires_at, str) and expires_at.strip():
        message += f"\nExpires: {expires_at.strip()}"
    message += "\nShort-lived one-time link. Do not forward."

    cmd = [openclaw, "message", "send", "--channel", channel, "--target", target, "--message", message, "--json"]
    thread_raw = delivery.get("lastThreadId")
    if channel == "telegram":
        if isinstance(thread_raw, int):
            cmd.extend(["--thread-id", str(thread_raw)])
        elif isinstance(thread_raw, str) and thread_raw.strip():
            cmd.extend(["--thread-id", thread_raw.strip()])
    proc = _run_subprocess(cmd, timeout_sec=20, kind="openclaw_send")
    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        stdout = (proc.stdout or "").strip()
        return {"sent": False, "reason": "send_failed", "error": stderr or stdout or "openclaw message send failed"}
    message_id = _extract_openclaw_message_id(proc.stdout or "")
    return {"sent": True, "channel": channel, "messageId": message_id}


def cmd_approvals_sync(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    chain = args.chain
    try:
        state = _load_approval_prompts()
        prompts = state.get("prompts")
        if not isinstance(prompts, dict):
            prompts = {}
        checked = 0
        deleted = 0
        skipped = 0
        failures: list[dict[str, Any]] = []
        for trade_id, entry in list(prompts.items()):
            if not isinstance(entry, dict):
                continue
            if str(entry.get("chainKey") or "") != chain:
                skipped += 1
                continue
            checked += 1
            try:
                trade = _read_trade_details(str(trade_id))
                status = str(trade.get("status") or "")
                if status == "approval_pending":
                    skipped += 1
                    continue
                _maybe_delete_telegram_approval_prompt(str(trade_id))
                deleted += 1
            except Exception as exc:
                failures.append({"tradeId": str(trade_id), "error": str(exc)})
        return ok("Approval prompts synced.", chain=chain, checked=checked, deleted=deleted, skipped=skipped, failures=failures or None)
    except Exception as exc:
        return fail("approvals_sync_failed", str(exc), "Verify API auth and OpenClaw availability, then retry.", {"chain": chain}, exit_code=1)


def cmd_approvals_resume_spot(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    trade_id = str(args.trade_id or "").strip()
    if not trade_id:
        return fail("invalid_input", "trade_id is required.", "Provide --trade-id trd_... and retry.", {"tradeId": trade_id}, exit_code=2)

    flow = _get_pending_spot_trade_flow(trade_id) or {}
    flow_chain = str(flow.get("chainKey") or "").strip()
    chain = str(args.chain or flow_chain).strip()
    if not chain:
        return fail(
            "invalid_input",
            "chain is required when no saved spot-flow exists for this trade.",
            "Provide --chain <chainKey> and retry.",
            {"tradeId": trade_id},
            exit_code=2,
        )

    try:
        trade = _read_trade_details(trade_id)
        status = str(trade.get("status") or "")
        terminal = {"filled", "failed", "rejected", "expired"}
        non_actionable = {"approval_pending", "proposed", "executing", "verifying"}
        if status in terminal:
            _remove_pending_spot_trade_flow(trade_id)
            return ok(
                "Spot trade resume skipped: trade already terminal.",
                tradeId=trade_id,
                chain=chain,
                status=status,
                skipped=True,
                reason="already_terminal",
                txHash=trade.get("txHash"),
                reasonCode=trade.get("reasonCode"),
                reasonMessage=trade.get("reasonMessage"),
                flow=flow or None,
            )
        if status in non_actionable:
            if status != "approval_pending":
                _remove_pending_spot_trade_flow(trade_id)
            return fail(
                "not_actionable",
                f"Spot trade resume is not actionable from status '{status}'.",
                "Resume only when the trade is approved (or retry-eligible failed).",
                {"tradeId": trade_id, "chain": chain, "status": status, "flow": flow or None},
                exit_code=1,
            )

        nested = argparse.Namespace(intent=trade_id, chain=chain, json=True)
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = cmd_trade_execute(nested)
        raw = buf.getvalue().strip()
        payload: dict[str, Any] = {"ok": bool(code == 0), "code": "resume_result_unavailable", "message": "Resume result unavailable."}
        if raw:
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    payload = parsed
            except Exception:
                payload = {"ok": False, "code": "resume_parse_failed", "message": raw[:400]}

        # Enrich with flow context to make deterministic callback reporting easier.
        if isinstance(payload, dict):
            payload.setdefault("tradeId", trade_id)
            payload.setdefault("chain", chain)
            if flow:
                payload.setdefault("flowSummary", flow)
        if code == 0:
            _remove_pending_spot_trade_flow(trade_id)
            payload["ok"] = True
            payload["code"] = "ok"
            payload["message"] = str(payload.get("message") or "Spot trade resumed and executed.")
            return emit(payload)

        # Keep flow only if still pending; otherwise clear stale entry.
        try:
            latest = _read_trade_details(trade_id)
            if str(latest.get("status") or "") != "approval_pending":
                _remove_pending_spot_trade_flow(trade_id)
        except Exception:
            pass
        return emit(payload)
    except Exception as exc:
        return fail(
            "spot_resume_failed",
            str(exc),
            "Inspect trade status and runtime execution path, then retry.",
            {"tradeId": trade_id, "chain": chain, "flow": flow or None},
            exit_code=1,
        )


def cmd_approvals_resume_transfer(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    approval_id = str(args.approval_id or "").strip()
    if not approval_id:
        return fail("invalid_input", "approval_id is required.", "Provide --approval-id xfr_... and retry.", exit_code=2)
    flow = _get_pending_transfer_flow(approval_id)
    if not flow:
        x402_flow = x402_state.get_pending_pay_flow(approval_id)
        if isinstance(x402_flow, dict):
            try:
                payload = x402_pay_resume(approval_id)
                if isinstance(payload, dict):
                    _mirror_x402_outbound(payload)
                return ok("x402 payment resume processed.", approval=payload)
            except X402RuntimeError as exc:
                return fail("x402_runtime_error", str(exc), "Use a valid pending approved x402 approval id and retry.", exit_code=1)
            except Exception as exc:
                return fail("x402_runtime_error", str(exc), "Inspect runtime x402 pay resume flow and retry.", exit_code=1)
        return fail(
            "not_found",
            "Transfer approval flow was not found.",
            "Use a pending approval ID from the latest transfer request.",
            {"approvalId": approval_id},
            exit_code=1,
        )
    chain = str(args.chain or flow.get("chainKey") or "").strip()
    if not chain:
        return fail("invalid_input", "chain is required.", "Provide --chain and retry.", {"approvalId": approval_id}, exit_code=2)
    status = str(flow.get("status") or "")
    if status in {"filled", "failed", "rejected"}:
        return ok(
            "Transfer resume skipped: approval already terminal.",
            approvalId=approval_id,
            chain=chain,
            status=status,
            txHash=flow.get("txHash"),
            reasonCode=flow.get("reasonCode"),
            reasonMessage=flow.get("reasonMessage"),
            skipped=True,
        )
    if status == "approved":
        return emit(_execute_pending_transfer_flow(flow))
    return fail(
        "not_actionable",
        f"Transfer resume is not actionable from status '{status}'.",
        "Resume only when transfer approval is approved.",
        {"approvalId": approval_id, "chain": chain, "status": status},
        exit_code=1,
    )


def cmd_approvals_decide_transfer(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    approval_id = str(args.approval_id or "").strip()
    decision = str(args.decision or "").strip().lower()
    if not approval_id:
        return fail("invalid_input", "approval_id is required.", "Provide --approval-id xfr_... and retry.", exit_code=2)
    if decision not in {"approve", "deny"}:
        return fail("invalid_input", "decision must be approve|deny.", "Use --decision approve or --decision deny.", exit_code=2)

    flow = _get_pending_transfer_flow(approval_id)
    if not flow:
        x402_flow = x402_state.get_pending_pay_flow(approval_id)
        if isinstance(x402_flow, dict):
            try:
                payload = x402_pay_decide(approval_id, decision, str(args.reason_message or "").strip() or None)
                if isinstance(payload, dict):
                    _mirror_x402_outbound(payload)
                return ok("x402 payment decision applied.", approval=payload)
            except X402RuntimeError as exc:
                return fail("x402_runtime_error", str(exc), "Use a valid pending x402 approval id and retry.", exit_code=1)
            except Exception as exc:
                return fail("x402_runtime_error", str(exc), "Inspect runtime x402 pay decision flow and retry.", exit_code=1)
        return fail(
            "not_found",
            "Transfer approval flow was not found.",
            "Use a pending approval ID from the latest transfer request.",
            {"approvalId": approval_id},
            exit_code=1,
        )
    status = str(flow.get("status") or "")
    chain = str(args.chain or flow.get("chainKey") or "").strip()
    flow_transfer_type = str(flow.get("transferType") or "native").strip().lower()
    flow_token_symbol = str(flow.get("tokenSymbol") or ("ETH" if flow_transfer_type == "native" else "TOKEN")).strip()
    flow_token_decimals_raw = flow.get("tokenDecimals", 18 if flow_transfer_type == "native" else None)
    try:
        flow_token_decimals = int(flow_token_decimals_raw) if flow_token_decimals_raw is not None else None
    except Exception:
        flow_token_decimals = 18 if flow_transfer_type == "native" else None
    flow_amount_human, flow_amount_unit = _transfer_amount_display(
        str(flow.get("amountWei") or "0"),
        flow_transfer_type,
        flow_token_symbol,
        flow_token_decimals,
    )
    flow_amount_display = f"{flow_amount_human} {flow_amount_unit}"
    if status in {"filled", "failed", "rejected"}:
        return ok(
            "Transfer decision converged on terminal approval.",
            approvalId=approval_id,
            chain=chain,
            status=status,
            txHash=flow.get("txHash"),
            reasonCode=flow.get("reasonCode"),
            reasonMessage=flow.get("reasonMessage"),
            amountWei=flow.get("amountWei"),
            amount=flow_amount_human,
            amountUnit=flow_amount_unit,
            amountDisplay=flow_amount_display,
            policyBlockedAtCreate=bool(flow.get("policyBlockedAtCreate", False)),
            policyBlockReasonCode=flow.get("policyBlockReasonCode"),
            policyBlockReasonMessage=flow.get("policyBlockReasonMessage"),
            executionMode=flow.get("executionMode"),
            converged=True,
        )
    if status not in {"approval_pending", "approved"}:
        return fail(
            "not_actionable",
            f"Transfer decision is not actionable from status '{status}'.",
            "Use a pending transfer approval.",
            {"approvalId": approval_id, "chain": chain, "status": status},
            exit_code=1,
        )

    if decision == "deny":
        flow["status"] = "rejected"
        flow["reasonCode"] = "approval_rejected"
        flow["reasonMessage"] = str(args.reason_message or "Denied via management/telegram").strip()
        flow["decidedAt"] = utc_now()
        flow["updatedAt"] = flow["decidedAt"]
        flow["terminalAt"] = flow["decidedAt"]
        _record_pending_transfer_flow(approval_id, flow)
        _mirror_transfer_approval(flow)
        return ok(
            "Transfer denied.",
            approvalId=approval_id,
            chain=chain,
            status="rejected",
            reasonCode=flow.get("reasonCode"),
            reasonMessage=flow.get("reasonMessage"),
            transferType=flow.get("transferType"),
            tokenAddress=flow.get("tokenAddress"),
            tokenSymbol=flow_token_symbol,
            tokenDecimals=flow_token_decimals,
            to=flow.get("toAddress"),
            amountWei=flow.get("amountWei"),
            amount=flow_amount_human,
            amountUnit=flow_amount_unit,
            amountDisplay=flow_amount_display,
            policyBlockedAtCreate=bool(flow.get("policyBlockedAtCreate", False)),
            policyBlockReasonCode=flow.get("policyBlockReasonCode"),
            policyBlockReasonMessage=flow.get("policyBlockReasonMessage"),
            executionMode=flow.get("executionMode"),
        )

    flow["status"] = "approved"
    flow["decidedAt"] = utc_now()
    flow["updatedAt"] = flow["decidedAt"]
    _record_pending_transfer_flow(approval_id, flow)
    _mirror_transfer_approval(flow)
    return emit(_execute_pending_transfer_flow(flow))


def cmd_transfers_policy_get(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    chain = str(args.chain or "").strip()
    if not chain:
        return fail("invalid_input", "chain is required.", "Provide --chain and retry.", exit_code=2)
    policy = _sync_transfer_policy_from_remote(chain)
    return ok("Transfer approval policy loaded.", chain=chain, transferPolicy=policy)


def cmd_transfers_policy_set(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    chain = str(args.chain or "").strip()
    mode = str(args.global_mode or "").strip().lower()
    if not chain:
        return fail("invalid_input", "chain is required.", "Provide --chain and retry.", exit_code=2)
    if mode not in {"auto", "per_transfer"}:
        return fail("invalid_input", "global mode must be auto|per_transfer.", "Use --global auto|per_transfer.", exit_code=2)
    native_preapproved = str(args.native_preapproved or "0").strip() in {"1", "true", "yes"}
    tokens: list[str] = []
    for token in list(args.allowed_token or []):
        if not isinstance(token, str):
            continue
        normalized = token.strip().lower()
        if not re.fullmatch(r"0x[a-f0-9]{40}", normalized):
            return fail(
                "invalid_input",
                "allowed-token must be a 0x address.",
                "Use --allowed-token 0x... for ERC-20 token preapproval.",
                {"token": token},
                exit_code=2,
            )
        if normalized not in tokens:
            tokens.append(normalized)
    policy = _set_transfer_policy(
        chain,
        {
            "transferApprovalMode": mode,
            "nativeTransferPreapproved": native_preapproved,
            "allowedTransferTokens": tokens,
            "updatedAt": utc_now(),
        },
    )
    _mirror_transfer_policy(chain, policy)
    return ok("Transfer approval policy saved.", chain=chain, transferPolicy=policy)


def cmd_approvals_request_token(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    token = str(args.token or "").strip()
    if token == "":
        return fail("invalid_input", "token is required.", "Provide a token address (0x...) and retry.", {"token": token}, exit_code=2)
    token_symbol = None
    token_address = None
    try:
        token_address = _resolve_token_address(args.chain, token)
        if not is_hex_address(token):
            token_symbol = token.strip().upper()
    except Exception as exc:
        return fail(
            "invalid_input",
            "token must be a 0x address or a canonical token symbol for the active chain.",
            "Use a token address like 0xabc... or a symbol like USDC/WETH, then retry.",
            {"token": token, "chain": args.chain, "error": str(exc)},
            exit_code=2,
        )
    try:
        payload = {"schemaVersion": 1, "chainKey": args.chain, "requestType": "token_preapprove_add", "tokenAddress": token_address}
        status_code, body = _api_request(
            "POST",
            "/agent/policy-approvals/proposed",
            payload=payload,
            include_idempotency=True,
            idempotency_key=f"rt-polreq-token-{args.chain}-{_normalize_address(token_address)}-{secrets.token_hex(8)}",
        )
        if status_code < 200 or status_code >= 300:
            return fail(
                str(body.get("code", "api_error")),
                str(body.get("message", f"policy approval request failed ({status_code})")),
                str(body.get("actionHint", "Verify API auth and retry.")),
                {"status": status_code, "chain": args.chain, "token": token},
                exit_code=1,
            )
        policy_approval_id = str(body.get("policyApprovalId", ""))
        status = str(body.get("status", "approval_pending"))
        token_addr = _normalize_address(token_address)
        token_display = f"{token_symbol} ({token_addr})" if token_symbol else token_addr
        queued_message = (
            "Approval required (policy)\n\n"
            "Request: Preapprove token for trading\n"
            f"Token: {token_display}\n"
            f"Chain: {args.chain}\n"
            f"Approval ID: {policy_approval_id}\n"
            f"Status: {status}\n\n"
            "Tap Approve or Deny.\n"
        )
        return ok(
            "Policy approval requested (pending). Post queuedMessage to the owner verbatim so Telegram buttons can attach.",
            chain=args.chain,
            policyApprovalId=policy_approval_id,
            status=status,
            requestType="token_preapprove_add",
            tokenAddress=token_addr,
            queuedMessage=queued_message,
            agentInstructions=(
                "Send queuedMessage verbatim to the owner in the active chat. "
                "Do not reformat the 'Approval ID:' and 'Status:' lines; Telegram button auto-attach depends on them. "
                "Use only the Approval ID returned in this command result; never reuse a historical Approval ID from memory/chat."
            ),
        )
    except Exception as exc:
        return fail(
            "policy_approval_request_failed",
            str(exc),
            "Inspect runtime policy approval request and retry.",
            {"chain": args.chain, "token": token},
            exit_code=1,
        )


def cmd_approvals_request_global(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    try:
        payload = {"schemaVersion": 1, "chainKey": args.chain, "requestType": "global_approval_enable", "tokenAddress": None}
        status_code, body = _api_request(
            "POST",
            "/agent/policy-approvals/proposed",
            payload=payload,
            include_idempotency=True,
            idempotency_key=f"rt-polreq-global-{args.chain}-{secrets.token_hex(8)}",
        )
        if status_code < 200 or status_code >= 300:
            return fail(
                str(body.get("code", "api_error")),
                str(body.get("message", f"policy approval request failed ({status_code})")),
                str(body.get("actionHint", "Verify API auth and retry.")),
                {"status": status_code, "chain": args.chain},
                exit_code=1,
            )
        policy_approval_id = str(body.get("policyApprovalId", ""))
        status = str(body.get("status", "approval_pending"))
        queued_message = (
            "Approval required (policy)\n\n"
            "Request: Enable Approve all (global trading)\n"
            f"Chain: {args.chain}\n"
            f"Approval ID: {policy_approval_id}\n"
            f"Status: {status}\n\n"
            "Tap Approve or Deny.\n"
        )
        return ok(
            "Policy approval requested (pending). Post queuedMessage to the owner verbatim so Telegram buttons can attach.",
            chain=args.chain,
            policyApprovalId=policy_approval_id,
            status=status,
            requestType="global_approval_enable",
            queuedMessage=queued_message,
            agentInstructions=(
                "Send queuedMessage verbatim to the owner in the active chat. "
                "Do not reformat the 'Approval ID:' and 'Status:' lines; Telegram button auto-attach depends on them. "
                "Use only the Approval ID returned in this command result; never reuse a historical Approval ID from memory/chat."
            ),
        )
    except Exception as exc:
        return fail("policy_approval_request_failed", str(exc), "Inspect runtime policy approval request and retry.", {"chain": args.chain}, exit_code=1)


def cmd_approvals_revoke_token(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    token = str(args.token or "").strip()
    if token == "":
        return fail("invalid_input", "token is required.", "Provide a token address (0x...) and retry.", {"token": token}, exit_code=2)
    token_symbol = None
    token_address = None
    try:
        token_address = _resolve_token_address(args.chain, token)
        if not is_hex_address(token):
            token_symbol = token.strip().upper()
    except Exception as exc:
        return fail(
            "invalid_input",
            "token must be a 0x address or a canonical token symbol for the active chain.",
            "Use a token address like 0xabc... or a symbol like USDC/WETH, then retry.",
            {"token": token, "chain": args.chain, "error": str(exc)},
            exit_code=2,
        )
    try:
        payload = {"schemaVersion": 1, "chainKey": args.chain, "requestType": "token_preapprove_remove", "tokenAddress": token_address}
        status_code, body = _api_request(
            "POST",
            "/agent/policy-approvals/proposed",
            payload=payload,
            include_idempotency=True,
            idempotency_key=f"rt-polrev-token-{args.chain}-{_normalize_address(token_address)}-{secrets.token_hex(8)}",
        )
        if status_code < 200 or status_code >= 300:
            return fail(
                str(body.get("code", "api_error")),
                str(body.get("message", f"policy approval request failed ({status_code})")),
                str(body.get("actionHint", "Verify API auth and retry.")),
                {"status": status_code, "chain": args.chain, "token": token},
                exit_code=1,
            )
        policy_approval_id = str(body.get("policyApprovalId", ""))
        status = str(body.get("status", "approval_pending"))
        token_addr = _normalize_address(token_address)
        token_display = f"{token_symbol} ({token_addr})" if token_symbol else token_addr
        queued_message = (
            "Approval required (policy)\n\n"
            "Request: Revoke preapproved token\n"
            f"Token: {token_display}\n"
            f"Chain: {args.chain}\n"
            f"Approval ID: {policy_approval_id}\n"
            f"Status: {status}\n\n"
            "Tap Approve or Deny.\n"
        )
        return ok(
            "Policy revoke requested (pending). Post queuedMessage to the owner verbatim so Telegram buttons can attach.",
            chain=args.chain,
            policyApprovalId=policy_approval_id,
            status=status,
            requestType="token_preapprove_remove",
            tokenAddress=token_addr,
            queuedMessage=queued_message,
            agentInstructions=(
                "Send queuedMessage verbatim to the owner in the active chat. "
                "Do not reformat the 'Approval ID:' and 'Status:' lines; Telegram button auto-attach depends on them. "
                "Use only the Approval ID returned in this command result; never reuse a historical Approval ID from memory/chat."
            ),
        )
    except Exception as exc:
        return fail(
            "policy_approval_request_failed",
            str(exc),
            "Inspect runtime policy revoke request and retry.",
            {"chain": args.chain, "token": token},
            exit_code=1,
        )


def cmd_approvals_revoke_global(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    try:
        payload = {"schemaVersion": 1, "chainKey": args.chain, "requestType": "global_approval_disable", "tokenAddress": None}
        status_code, body = _api_request(
            "POST",
            "/agent/policy-approvals/proposed",
            payload=payload,
            include_idempotency=True,
            idempotency_key=f"rt-polrev-global-{args.chain}-{secrets.token_hex(8)}",
        )
        if status_code < 200 or status_code >= 300:
            return fail(
                str(body.get("code", "api_error")),
                str(body.get("message", f"policy approval request failed ({status_code})")),
                str(body.get("actionHint", "Verify API auth and retry.")),
                {"status": status_code, "chain": args.chain},
                exit_code=1,
            )
        policy_approval_id = str(body.get("policyApprovalId", ""))
        status = str(body.get("status", "approval_pending"))
        queued_message = (
            "Approval required (policy)\n\n"
            "Request: Disable Approve all (global trading)\n"
            f"Chain: {args.chain}\n"
            f"Approval ID: {policy_approval_id}\n"
            f"Status: {status}\n\n"
            "Tap Approve or Deny.\n"
        )
        return ok(
            "Policy revoke requested (pending). Post queuedMessage to the owner verbatim so Telegram buttons can attach.",
            chain=args.chain,
            policyApprovalId=policy_approval_id,
            status=status,
            requestType="global_approval_disable",
            queuedMessage=queued_message,
            agentInstructions=(
                "Send queuedMessage verbatim to the owner in the active chat. "
                "Do not reformat the 'Approval ID:' and 'Status:' lines; Telegram button auto-attach depends on them. "
                "Use only the Approval ID returned in this command result; never reuse a historical Approval ID from memory/chat."
            ),
        )
    except Exception as exc:
        return fail("policy_approval_request_failed", str(exc), "Inspect runtime policy revoke request and retry.", {"chain": args.chain}, exit_code=1)


def _post_trade_status(trade_id: str, from_status: str, to_status: str, extra: dict[str, Any] | None = None) -> None:
    payload: dict[str, Any] = {
        "tradeId": trade_id,
        "fromStatus": from_status,
        "toStatus": to_status,
        "at": datetime.now(timezone.utc).isoformat(),
    }
    if extra:
        payload.update(extra)
    status_code, body = _api_request("POST", f"/trades/{trade_id}/status", payload=payload, include_idempotency=True)
    if status_code < 200 or status_code >= 300:
        code = str(body.get("code", "api_error"))
        message = str(body.get("message", f"trade status update failed ({status_code})"))
        raise WalletStoreError(f"{code}: {message}")


def _parse_uint_from_cast_output(raw: str) -> int:
    text = (raw or "").strip()
    if not text:
        raise WalletStoreError("Unable to parse uint value from cast output.")

    # Prefer values before the scientific notation hint brackets: "<uint> [<sci>]".
    bracketed = re.findall(r"([0-9]+)\s*\[", text)
    if bracketed:
        return int(bracketed[-1])

    # Fallback: plain uint output, or hex.
    if re.fullmatch(r"0x[a-fA-F0-9]+", text):
        return int(text, 16)
    plain = re.findall(r"\b[0-9]+\b", text)
    if plain:
        return int(plain[-1])

    raise WalletStoreError("Unable to parse uint value from cast output.")


def _format_units(amount_wei: int, decimals: int) -> str:
    if decimals <= 0:
        return str(amount_wei)
    if amount_wei == 0:
        return "0"
    s = str(amount_wei)
    if len(s) <= decimals:
        s = s.rjust(decimals + 1, "0")
    whole = s[:-decimals]
    frac = s[-decimals:].rstrip("0")
    if not frac:
        return whole
    return f"{whole}.{frac}"


def _fetch_erc20_metadata(chain: str, token_address: str) -> dict[str, Any]:
    cast_bin = _require_cast_bin()
    rpc_url = _chain_rpc_url(chain)

    decimals: int | None = None
    symbol: str | None = None

    dec_proc = _run_subprocess(
        [cast_bin, "call", token_address, "decimals()(uint8)", "--rpc-url", rpc_url],
        timeout_sec=_cast_call_timeout_sec(),
        kind="cast_call",
    )
    if dec_proc.returncode == 0:
        out = (dec_proc.stdout or "").strip().splitlines()
        try:
            decimals = int(_parse_uint_text(out[-1] if out else ""))
        except Exception:
            decimals = None

    sym_proc = _run_subprocess(
        [cast_bin, "call", token_address, "symbol()(string)", "--rpc-url", rpc_url],
        timeout_sec=_cast_call_timeout_sec(),
        kind="cast_call",
    )
    if sym_proc.returncode == 0:
        out = (sym_proc.stdout or "").strip()
        # cast may return quoted strings, or raw tokens depending on version.
        trimmed = out.strip().strip('"').strip("'")
        if trimmed:
            symbol = trimmed

    payload: dict[str, Any] = {}
    if decimals is not None:
        payload["decimals"] = decimals
    if symbol is not None:
        payload["symbol"] = symbol
    return payload


def _quote_router_price(chain: str, token_in: str, token_out: str) -> Decimal:
    """Return current price in 'tokenIn per 1 tokenOut' human units.

    Example: token_in=USDC, token_out=WETH => returns ~2000 (USDC per 1 WETH).
    """
    cast_bin = _require_cast_bin()
    router = _require_chain_contract_address(chain, "router")
    rpc_url = _chain_rpc_url(chain)

    token_in_meta = _fetch_erc20_metadata(chain, token_in)
    token_out_meta = _fetch_erc20_metadata(chain, token_out)
    token_in_decimals = int(token_in_meta.get("decimals", 18))
    token_out_decimals = int(token_out_meta.get("decimals", 18))

    one_token_out_units = str(10**token_out_decimals)
    proc = _run_subprocess(
        [
            cast_bin,
            "call",
            "--rpc-url",
            rpc_url,
            router,
            "getAmountsOut(uint256,address[])(uint256[])",
            one_token_out_units,
            f"[{token_out},{token_in}]",
        ],
        timeout_sec=_cast_call_timeout_sec(),
        kind="cast_call",
    )
    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        stdout = (proc.stdout or "").strip()
        raise WalletStoreError(stderr or stdout or "cast call getAmountsOut failed.")

    # Output is amounts[]; final element is token_in units for 1 token_out.
    token_in_units = _parse_uint_from_cast_output(proc.stdout)
    return Decimal(token_in_units) / (Decimal(10) ** Decimal(token_in_decimals))


def _limit_order_triggered(side: str, current_price: Decimal, limit_price: Decimal) -> bool:
    if side == "buy":
        return current_price <= limit_price
    if side == "sell":
        return current_price >= limit_price
    return False


def _queue_limit_order_action(method: str, path: str, payload: dict[str, Any]) -> None:
    items = load_limit_order_outbox()
    items.append({"method": method, "path": path, "payload": payload, "queuedAt": utc_now()})
    save_limit_order_outbox(items)


def _post_limit_order_status(order_id: str, payload: dict[str, Any], queue_on_failure: bool = True) -> None:
    try:
        status_code, body = _api_request("POST", f"/limit-orders/{order_id}/status", payload=payload, include_idempotency=True)
        if status_code < 200 or status_code >= 300:
            code = str(body.get("code", "api_error"))
            message = str(body.get("message", f"limit-order status update failed ({status_code})"))
            raise WalletStoreError(f"{code}: {message}")
    except Exception:
        if queue_on_failure:
            _queue_limit_order_action("POST", f"/limit-orders/{order_id}/status", payload)
            return
        raise


def _replay_limit_order_outbox() -> tuple[int, int]:
    queued = load_limit_order_outbox()
    if not queued:
        return 0, 0
    sent = 0
    remaining: list[dict[str, Any]] = []
    for idx, entry in enumerate(queued):
        method = str(entry.get("method") or "POST")
        path = str(entry.get("path") or "")
        payload = entry.get("payload")
        if not path or not isinstance(payload, dict):
            continue
        try:
            status_code, _ = _api_request(method, path, payload=payload, include_idempotency=True)
            if status_code < 200 or status_code >= 300:
                remaining.append(entry)
                remaining.extend(queued[idx + 1 :])
                break
            sent += 1
        except Exception:
            remaining.append(entry)
            remaining.extend(queued[idx + 1 :])
            break

    save_limit_order_outbox(remaining)
    return sent, len(remaining)


def _require_chain_contract_address(chain: str, key: str) -> str:
    cfg = _load_chain_config(chain)
    contracts = cfg.get("coreContracts")
    if not isinstance(contracts, dict):
        raise WalletStoreError(f"Chain config for '{chain}' is missing coreContracts.")
    value = contracts.get(key)
    if not isinstance(value, str) or not is_hex_address(value):
        raise WalletStoreError(f"Chain config for '{chain}' has invalid coreContracts.{key}.")
    return value


def _chain_token_address(chain: str, token_symbol: str) -> str:
    cfg = _load_chain_config(chain)
    tokens = cfg.get("canonicalTokens")
    if not isinstance(tokens, dict):
        raise WalletStoreError(f"Chain config for '{chain}' is missing canonicalTokens.")
    value = tokens.get(token_symbol)
    if not isinstance(value, str) or not is_hex_address(value):
        raise WalletStoreError(f"Chain config for '{chain}' has invalid canonicalTokens.{token_symbol}.")
    return value


def _to_wei_uint(raw: str | None) -> str:
    if raw is None:
        return str(10**15)
    trimmed = str(raw).strip()
    if re.fullmatch(r"[0-9]+", trimmed):
        return trimmed
    try:
        decimal_value = Decimal(trimmed)
    except InvalidOperation as exc:
        raise WalletStoreError(f"Invalid amount format '{raw}' for trade execution.") from exc
    if decimal_value <= 0:
        raise WalletStoreError("Trade amount must be positive.")
    wei = int(decimal_value * Decimal(10**18))
    if wei <= 0:
        raise WalletStoreError("Trade amount is too small after wei conversion.")
    return str(wei)


def _to_units_uint(raw: str, decimals: int) -> str:
    """Convert a human token amount string to base units.

    IMPORTANT: This function treats inputs as human token units (e.g. "1" means
    1.0 tokens, not 1 base unit). If callers need to accept raw base units, use
    an explicit prefix such as "wei:<uint>" and handle it before calling here.
    """
    trimmed = str(raw).strip()
    if not trimmed:
        raise WalletStoreError("Amount must not be empty.")
    if decimals < 0 or decimals > 255:
        raise WalletStoreError("Token decimals must be 0..255.")
    if "e" in trimmed.lower():
        raise WalletStoreError("Scientific notation is not supported for amounts. Use a normal decimal string.")

    try:
        decimal_value = Decimal(trimmed)
    except InvalidOperation as exc:
        raise WalletStoreError(f"Invalid amount format '{raw}'.") from exc
    if decimal_value <= 0:
        raise WalletStoreError("Amount must be positive.")

    scale = Decimal(10) ** Decimal(decimals)
    units = decimal_value * scale
    # Must be an integer number of base units.
    if units != units.to_integral_value():
        raise WalletStoreError("Amount has too many decimal places for token.")
    value = int(units)
    if value <= 0:
        raise WalletStoreError("Amount is too small after base-unit conversion.")
    # uint256 bounds check (avoid generating transactions that will revert).
    if value >= 2**256:
        raise WalletStoreError("Amount is too large (exceeds uint256).")
    return str(value)


def _parse_amount_in_units(raw: str, decimals: int) -> tuple[str, str]:
    """Return (amount_units, input_mode). input_mode is 'human' or 'base_units'."""
    trimmed = str(raw or "").strip()
    if not trimmed:
        raise WalletStoreError("Amount must not be empty.")
    match = re.fullmatch(r"(wei|base|units):([0-9]+)", trimmed, flags=re.IGNORECASE)
    if match:
        value = match.group(2)
        if not value or not re.fullmatch(r"[0-9]+", value):
            raise WalletStoreError("Invalid base-units amount format.")
        if int(value) <= 0:
            raise WalletStoreError("Amount must be positive.")
        if int(value) >= 2**256:
            raise WalletStoreError("Amount is too large (exceeds uint256).")
        return value, "base_units"
    return _to_units_uint(trimmed, decimals), "human"


def _format_units_pretty(amount_wei: int, decimals: int, max_frac: int = 6) -> str:
    # Human-readable display helper; informational only.
    raw = _format_units(amount_wei, decimals)
    if raw in {"0", ""}:
        return "0"
    if "." in raw:
        whole, frac = raw.split(".", 1)
        frac = frac[:max_frac].rstrip("0")
    else:
        whole, frac = raw, ""
    # comma-group whole part
    sign = ""
    if whole.startswith("-"):
        sign = "-"
        whole = whole[1:]
    grouped = ""
    for i, ch in enumerate(reversed(whole)):
        if i and (i % 3) == 0:
            grouped = "," + grouped
        grouped = ch + grouped
    whole = sign + grouped
    return f"{whole}.{frac}" if frac else whole


def _format_eth_cost_from_wei(cost_wei: int | None) -> str | None:
    if cost_wei is None:
        return None
    if cost_wei <= 0:
        return "0"
    # Show tiny costs as a threshold rather than rounding to zero.
    threshold_wei = 10**12  # 0.000001 ETH
    if cost_wei < threshold_wei:
        return "<0.000001"
    return _format_units_pretty(int(cost_wei), 18, max_frac=12)


def _resolve_token_address(chain: str, token_or_symbol: str) -> str:
    candidate = str(token_or_symbol or "").strip()
    if is_hex_address(candidate):
        return candidate
    symbol = candidate.upper()
    token_map = _canonical_token_map(chain)
    value = token_map.get(symbol)
    if value and is_hex_address(value):
        return value
    raise WalletStoreError("token must be a 0x address or a canonical token symbol for the active chain.")


def _projected_trade_spend_usd(
    token_in_symbol: str | None,
    token_out_symbol: str | None,
    amount_in_human: Decimal,
    expected_out_human: Decimal,
) -> Decimal:
    stable = {"USDC", "USDT", "DAI"}
    sym_in = (token_in_symbol or "").strip().upper()
    sym_out = (token_out_symbol or "").strip().upper()
    if sym_in in stable:
        return max(Decimal("0"), amount_in_human)
    if sym_out in stable:
        return max(Decimal("0"), expected_out_human)
    return max(Decimal("0"), amount_in_human)


def _router_get_amount_out(chain: str, amount_in_units: str, token_in: str, token_out: str) -> int:
    cast_bin = _require_cast_bin()
    router = _require_chain_contract_address(chain, "router")
    rpc_url = _chain_rpc_url(chain)
    proc = _run_subprocess(
        [cast_bin, "call", "--rpc-url", rpc_url, router, "getAmountsOut(uint256,address[])(uint256[])", amount_in_units, f"[{token_in},{token_out}]"],
        timeout_sec=_cast_call_timeout_sec(),
        kind="cast_call",
    )
    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        stdout = (proc.stdout or "").strip()
        raise WalletStoreError(stderr or stdout or "cast call getAmountsOut failed.")
    return int(_parse_uint_from_cast_output(proc.stdout))


def cmd_trade_spot(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk

    chain = args.chain
    trade_id: str | None = None
    transition_state = "init"
    last_tx_hash: str | None = None
    last_approve_tx_hash: str | None = None
    try:
        # Best-effort: usage outbox replay should not block input validation or proposing.
        try:
            _replay_trade_usage_outbox()
        except Exception:
            pass
        token_in = _resolve_token_address(chain, args.token_in)
        token_out = _resolve_token_address(chain, args.token_out)
        if token_in.lower() == token_out.lower():
            return fail(
                "invalid_input",
                "token-in and token-out must be different.",
                "Provide two distinct token addresses (or symbols).",
                {"tokenIn": token_in, "tokenOut": token_out, "chain": chain},
                exit_code=2,
            )

        slippage_bps = int(args.slippage_bps)
        if slippage_bps < 0 or slippage_bps > 5000:
            return fail(
                "invalid_input",
                "slippage-bps must be between 0 and 5000.",
                "Use a value like 50 for 0.5% or 500 for 5%.",
                {"slippageBps": args.slippage_bps},
                exit_code=2,
            )

        store = load_wallet_store()
        wallet_address, private_key_hex = _execution_wallet(store, chain)
        cast_bin = _require_cast_bin()
        rpc_url = _chain_rpc_url(chain)
        router = _require_chain_contract_address(chain, "router")

        token_in_meta = _fetch_erc20_metadata(chain, token_in)
        token_out_meta = _fetch_erc20_metadata(chain, token_out)
        token_in_decimals = int(token_in_meta.get("decimals", 18))
        token_out_decimals = int(token_out_meta.get("decimals", 18))

        amount_in_units, amount_in_mode = _parse_amount_in_units(str(args.amount_in), token_in_decimals)
        amount_in_int = int(amount_in_units)
        state, day_key, current_spend, max_daily_wei = _enforce_spend_preconditions(chain, amount_in_int, enforce_native_cap=False)

        expected_out_int = _router_get_amount_out(chain, amount_in_units, token_in, token_out)
        min_out_int = (expected_out_int * (10000 - slippage_bps)) // 10000
        if min_out_int <= 0:
            raise WalletStoreError("Computed amountOutMin is zero; reduce slippage or increase amount.")
        amount_in_human = _to_non_negative_decimal(_format_units(int(amount_in_units), token_in_decimals))
        expected_out_human = _to_non_negative_decimal(_format_units(int(expected_out_int), token_out_decimals))
        projected_spend_usd = _projected_trade_spend_usd(
            token_in_meta.get("symbol"),
            token_out_meta.get("symbol"),
            amount_in_human,
            expected_out_human,
        )
        cap_state, _, current_spend_usd, current_filled_trades, trade_caps = _enforce_trade_caps(chain, projected_spend_usd, 1)

        # Slice 33: server-first trade-spot. Propose before any on-chain tx so owner policy can gate approvals.
        amount_in_for_server = str(args.amount_in).strip()
        if amount_in_mode == "base_units":
            amount_in_for_server = _format_units(int(amount_in_units), token_in_decimals)

        summary = {
            "tradeId": None,
            "chainKey": chain,
            "tokenInSymbol": str(token_in_meta.get("symbol") or "").strip() or str(token_in),
            "tokenOutSymbol": str(token_out_meta.get("symbol") or "").strip() or str(token_out),
            "amountInHuman": _normalize_amount_human_text(amount_in_for_server),
            "slippageBps": slippage_bps,
        }

        intent_key = _trade_intent_key(chain, token_in, token_out, amount_in_for_server, slippage_bps)
        existing_intent = _get_pending_trade_intent(intent_key)
        if existing_intent:
            existing_trade_id = str(existing_intent.get("tradeId") or "").strip()
            if existing_trade_id:
                try:
                    existing_trade = _read_trade_details(existing_trade_id)
                except Exception:
                    existing_trade = None
                status = str((existing_trade or {}).get("status") or "")
                if status == "approval_pending":
                    trade_id = existing_trade_id
                    summary["tradeId"] = trade_id
                    _record_pending_spot_trade_flow(
                        trade_id,
                        {
                            "tradeId": trade_id,
                            "chainKey": chain,
                            "tokenIn": token_in.lower(),
                            "tokenOut": token_out.lower(),
                            "tokenInSymbol": str(token_in_meta.get("symbol") or "").strip() or str(token_in),
                            "tokenOutSymbol": str(token_out_meta.get("symbol") or "").strip() or str(token_out),
                            "amountInHuman": _normalize_amount_human_text(amount_in_for_server),
                            "slippageBps": slippage_bps,
                            "source": "trade_spot_existing_pending",
                            "createdAt": utc_now(),
                        },
                    )
                    _wait_for_trade_approval(trade_id, chain, summary)
                    _remove_pending_trade_intent(intent_key)
                else:
                    # De-dupe applies only while still awaiting approval.
                    # If the matching trade has been approved/rejected/filled/etc, a repeated identical request
                    # must propose a new tradeId.
                    _remove_pending_trade_intent(intent_key)

        if not trade_id:
            proposed = _post_trade_proposed(
                chain,
                token_in,
                token_out,
                amount_in_for_server,
                slippage_bps,
                amount_out_human=_decimal_text(expected_out_human),
                reason="trade_spot",
            )
            trade_id = str(proposed.get("tradeId") or "")
            if not trade_id:
                raise WalletStoreError("Trade proposal did not return a tradeId.")
            summary["tradeId"] = trade_id
            proposed_status = str(proposed.get("status") or "")
            if proposed_status != "approved":
                _record_pending_trade_intent(
                    intent_key,
                    {
                        "tradeId": trade_id,
                        "chainKey": chain,
                        "tokenIn": token_in.lower(),
                        "tokenOut": token_out.lower(),
                        "amountInHuman": _normalize_amount_human_text(amount_in_for_server),
                        "slippageBps": slippage_bps,
                        "createdAt": utc_now(),
                        "lastSeenStatus": proposed_status,
                    },
                )
                _record_pending_spot_trade_flow(
                    trade_id,
                    {
                        "tradeId": trade_id,
                        "chainKey": chain,
                        "tokenIn": token_in.lower(),
                        "tokenOut": token_out.lower(),
                        "tokenInSymbol": str(token_in_meta.get("symbol") or "").strip() or str(token_in),
                        "tokenOutSymbol": str(token_out_meta.get("symbol") or "").strip() or str(token_out),
                        "amountInHuman": _normalize_amount_human_text(amount_in_for_server),
                        "slippageBps": slippage_bps,
                        "source": "trade_spot_proposed_pending",
                        "createdAt": utc_now(),
                    },
                )
                _wait_for_trade_approval(trade_id, chain, summary)
                _remove_pending_trade_intent(intent_key)
            else:
                # Ensure we don't keep stale pending intents for already-approved trades.
                _remove_pending_trade_intent(intent_key)

        # Re-quote right before execution so amountOutMin reflects post-approval market state.
        # Approval waits can be long enough that an earlier quote becomes stale and causes SLIPPAGE_NET.
        expected_out_int = _router_get_amount_out(chain, amount_in_units, token_in, token_out)
        min_out_int = (expected_out_int * (10000 - slippage_bps)) // 10000
        if min_out_int <= 0:
            raise WalletStoreError("Computed amountOutMin is zero after approval; reduce slippage or increase amount.")
        expected_out_human = _to_non_negative_decimal(_format_units(int(expected_out_int), token_out_decimals))

        deadline_sec = int(args.deadline_sec)
        if deadline_sec < 30 or deadline_sec > 3600:
            return fail(
                "invalid_input",
                "deadline-sec must be between 30 and 3600.",
                "Use a value like 120.",
                {"deadlineSec": args.deadline_sec},
                exit_code=2,
            )
        deadline = str(int(datetime.now(timezone.utc).timestamp()) + deadline_sec)

        approve_tx_hash: str | None = None
        approve_receipt_payload: dict[str, Any] | None = None
        # Approve router (proxy) to spend tokenIn if needed.
        allowance_wei = int(_fetch_token_allowance_wei(chain, token_in, wallet_address, router))
        if allowance_wei < int(amount_in_units):
            approve_data = _cast_calldata("approve(address,uint256)(bool)", [router, amount_in_units])
            approve_tx_hash = _cast_rpc_send_transaction(
                rpc_url,
                {
                    "from": wallet_address,
                    "to": token_in,
                    "data": approve_data,
                },
                private_key_hex,
            )
            last_approve_tx_hash = approve_tx_hash
            approve_receipt = _run_subprocess(
                [cast_bin, "receipt", "--json", "--rpc-url", rpc_url, approve_tx_hash],
                timeout_sec=_cast_receipt_timeout_sec(),
                kind="cast_receipt",
            )
            if approve_receipt.returncode != 0:
                stderr = (approve_receipt.stderr or "").strip()
                stdout = (approve_receipt.stdout or "").strip()
                raise WalletStoreError(stderr or stdout or "cast receipt failed for approve tx.")
            approve_receipt_payload = json.loads((approve_receipt.stdout or "{}").strip() or "{}")
            approve_status = str(approve_receipt_payload.get("status", "0x0")).lower()
            if approve_status not in {"0x1", "1"}:
                raise WalletStoreError(f"Approve receipt indicates failure status '{approve_status}'.")

        to_addr = str(args.to or "").strip() or wallet_address
        if not is_hex_address(to_addr):
            return fail(
                "invalid_input",
                "to must be a valid 0x address.",
                "Provide a 0x-prefixed 20-byte hex address or omit to default to the execution wallet.",
                {"to": args.to},
                exit_code=2,
            )

        swap_data = _cast_calldata(
            "swapExactTokensForTokens(uint256,uint256,address[],address,uint256)(uint256[])",
            [amount_in_units, str(min_out_int), f"[{token_in},{token_out}]", to_addr, deadline],
        )
        tx_hash = _cast_rpc_send_transaction(
            rpc_url,
            {
                "from": wallet_address,
                "to": router,
                "data": swap_data,
            },
            private_key_hex,
        )
        last_tx_hash = tx_hash
        _post_trade_status(trade_id, "approved", "executing", {"txHash": tx_hash})
        transition_state = "executing"
        _post_trade_status(trade_id, "executing", "verifying", {"txHash": tx_hash})
        transition_state = "verifying"

        receipt_proc = _run_subprocess(
            [cast_bin, "receipt", "--json", "--rpc-url", rpc_url, tx_hash],
            timeout_sec=_cast_receipt_timeout_sec(),
            kind="cast_receipt",
        )
        if receipt_proc.returncode != 0:
            stderr = (receipt_proc.stderr or "").strip()
            stdout = (receipt_proc.stdout or "").strip()
            raise WalletStoreError(stderr or stdout or "cast receipt failed.")
        receipt_payload = json.loads((receipt_proc.stdout or "{}").strip() or "{}")
        receipt_status = str(receipt_payload.get("status", "0x0")).lower()
        if receipt_status not in {"0x1", "1"}:
            raise WalletStoreError(f"On-chain receipt indicates failure status '{receipt_status}'.")

        _record_spend(state, chain, day_key, current_spend + amount_in_int)
        _record_trade_cap_ledger(
            cap_state,
            chain,
            day_key,
            current_spend_usd + projected_spend_usd,
            current_filled_trades + 1,
        )
        try:
            _post_trade_usage(chain, day_key, projected_spend_usd, 1)
        except Exception:
            pass
        _post_trade_status(trade_id, "verifying", "filled", {"txHash": tx_hash})
        _remove_pending_spot_trade_flow(trade_id)

        def _parse_receipt_uint(field: str, payload: dict[str, Any]) -> int | None:
            value = payload.get(field)
            if value is None:
                return None
            try:
                if isinstance(value, str):
                    return _parse_uint_text(value)
                if isinstance(value, int):
                    return value
            except Exception:
                return None
            return None

        approve_gas_used = _parse_receipt_uint("gasUsed", approve_receipt_payload) if approve_receipt_payload else None
        approve_gas_price = _parse_receipt_uint("effectiveGasPrice", approve_receipt_payload) if approve_receipt_payload else None
        approve_cost_wei = (approve_gas_used * approve_gas_price) if (approve_gas_used is not None and approve_gas_price is not None) else None

        swap_gas_used = _parse_receipt_uint("gasUsed", receipt_payload)
        swap_gas_price = _parse_receipt_uint("effectiveGasPrice", receipt_payload)
        swap_cost_wei = (swap_gas_used * swap_gas_price) if (swap_gas_used is not None and swap_gas_price is not None) else None

        total_cost_wei: int | None = None
        if approve_cost_wei is not None and swap_cost_wei is not None:
            total_cost_wei = approve_cost_wei + swap_cost_wei
        elif swap_cost_wei is not None:
            total_cost_wei = swap_cost_wei

        total_gas_cost_eth_exact = _format_units(int(total_cost_wei or 0), 18) if total_cost_wei is not None else None

        return ok(
            "Spot swap executed on-chain via configured router (fee proxy).",
            chain=chain,
            router=router,
            fromAddress=wallet_address,
            toAddress=to_addr,
            tokenIn=token_in,
            tokenOut=token_out,
            amountInUnits=amount_in_units,
            expectedOutUnits=str(expected_out_int),
            amountOutMinUnits=str(min_out_int),
            slippageBps=slippage_bps,
            deadline=deadline,
            approveTxHash=approve_tx_hash,
            txHash=tx_hash,
            # Provide formatted hints for agent readability (best-effort, informational only).
            amountIn=_format_units(int(amount_in_units), token_in_decimals),
            expectedOut=_format_units(int(expected_out_int), token_out_decimals),
            amountOutMin=_format_units(int(min_out_int), token_out_decimals),
            amountInPretty=_format_units_pretty(int(amount_in_units), token_in_decimals),
            expectedOutPretty=_format_units_pretty(int(expected_out_int), token_out_decimals),
            amountOutMinPretty=_format_units_pretty(int(min_out_int), token_out_decimals),
            amountInInputMode=amount_in_mode,
            tokenInDecimals=token_in_decimals,
            tokenOutDecimals=token_out_decimals,
            tokenInSymbol=token_in_meta.get("symbol"),
            tokenOutSymbol=token_out_meta.get("symbol"),
            dailySpendUsd=_decimal_text(current_spend_usd + projected_spend_usd),
            maxDailyUsd=trade_caps.get("maxDailyUsd"),
            dailyFilledTrades=int(current_filled_trades + 1),
            maxDailyTradeCount=trade_caps.get("maxDailyTradeCount"),
            day=day_key,
            dailySpendWei=str(current_spend + amount_in_int),
            maxDailyNativeWei=str(max_daily_wei),
            approveGasUsed=str(approve_gas_used) if approve_gas_used is not None else None,
            approveEffectiveGasPriceWei=str(approve_gas_price) if approve_gas_price is not None else None,
            approveGasCostWei=str(approve_cost_wei) if approve_cost_wei is not None else None,
            swapGasUsed=str(swap_gas_used) if swap_gas_used is not None else None,
            swapEffectiveGasPriceWei=str(swap_gas_price) if swap_gas_price is not None else None,
            swapGasCostWei=str(swap_cost_wei) if swap_cost_wei is not None else None,
            totalGasCostWei=str(total_cost_wei) if total_cost_wei is not None else None,
            totalGasCostEth=total_gas_cost_eth_exact,
            totalGasCostEthExact=total_gas_cost_eth_exact,
            totalGasCostEthPretty=_format_eth_cost_from_wei(total_cost_wei),
        )
    except SubprocessTimeout as exc:
        details: dict[str, Any] = {"chain": chain, "timeoutSec": exc.timeout_sec, "kind": exc.kind}
        if last_tx_hash:
            details["txHash"] = last_tx_hash
        if last_approve_tx_hash:
            details["approveTxHash"] = last_approve_tx_hash
        if trade_id and transition_state in {"executing", "verifying"}:
            try:
                from_status = "executing" if transition_state == "executing" else "verifying"
                _post_trade_status(trade_id, from_status, "failed", {"reasonCode": "verification_timeout", "reasonMessage": str(exc), "txHash": last_tx_hash})
                _remove_pending_spot_trade_flow(trade_id)
            except Exception:
                pass
        if exc.kind == "cast_receipt":
            return fail(
                "tx_receipt_timeout",
                "Timed out waiting for on-chain receipt.",
                "Tx may still be pending. Check explorer/receipt later or re-run dashboard, then retry if needed.",
                details,
                exit_code=1,
            )
        return fail(
            "rpc_timeout",
            "Timed out waiting for RPC response.",
            "Verify RPC connectivity and cast health, then retry.",
            details,
            exit_code=1,
        )
    except WalletPolicyError as exc:
        if trade_id and transition_state in {"executing", "verifying"}:
            try:
                from_status = "executing" if transition_state == "executing" else "verifying"
                _post_trade_status(trade_id, from_status, "failed", {"reasonCode": "policy_denied", "reasonMessage": str(exc), "txHash": last_tx_hash})
                _remove_pending_spot_trade_flow(trade_id)
            except Exception:
                pass
        return fail(exc.code, str(exc), exc.action_hint, exc.details, exit_code=1)
    except WalletSecurityError as exc:
        return fail("unsafe_permissions", str(exc), "Restrict permissions to owner-only (0700/0600) and retry.", {"chain": chain}, exit_code=1)
    except WalletStoreError as exc:
        msg = (str(exc) or "").strip()
        if not msg:
            msg = f"{type(exc).__name__}: (no message)"
        if "Missing dependency: cast" in msg:
            return fail("missing_dependency", msg, "Install Foundry and ensure `cast` is on PATH.", {"dependency": "cast"}, exit_code=1)
        if "Chain config" in msg:
            return fail("chain_config_invalid", msg, "Repair config/chains/<chain>.json and retry.", {"chain": chain}, exit_code=1)
        if trade_id and transition_state in {"executing", "verifying"}:
            try:
                from_status = "executing" if transition_state == "executing" else "verifying"
                _post_trade_status(trade_id, from_status, "failed", {"reasonCode": "rpc_unavailable", "reasonMessage": msg, "txHash": last_tx_hash})
                _remove_pending_spot_trade_flow(trade_id)
            except Exception:
                pass
        return fail("trade_spot_failed", msg, "Verify wallet, RPC, token addresses, and retry.", {"chain": chain}, exit_code=1)
    except Exception as exc:
        msg = (str(exc) or "").strip()
        if not msg:
            msg = f"{type(exc).__name__}: (no message)"
        return fail("trade_spot_failed", msg, "Inspect runtime trade spot path and retry.", {"chain": chain, "exceptionType": type(exc).__name__}, exit_code=1)


def _read_trade_details(trade_id: str) -> dict[str, Any]:
    status_code, body = _api_request("GET", f"/trades/{trade_id}")
    if status_code < 200 or status_code >= 300:
        code = str(body.get("code", "api_error"))
        message = str(body.get("message", f"trade read failed ({status_code})"))
        raise WalletStoreError(f"{code}: {message}")
    trade = body.get("trade")
    if not isinstance(trade, dict):
        raise WalletStoreError("Trade details response missing trade object.")
    return trade


def _execution_wallet(store: dict[str, Any], chain: str) -> tuple[str, str]:
    _, wallet = _chain_wallet(store, chain)
    if wallet is None:
        raise WalletStoreError(f"No wallet configured for chain '{chain}'.")
    _validate_wallet_entry_shape(wallet)
    address = str(wallet.get("address"))
    passphrase = _require_wallet_passphrase_for_signing(chain)
    private_key_hex = _decrypt_private_key(wallet, passphrase).hex()
    return address, private_key_hex


def _cast_calldata(signature: str, args: list[str]) -> str:
    cast_bin = _require_cast_bin()
    proc = _run_subprocess([cast_bin, "calldata", signature, *args], timeout_sec=_cast_call_timeout_sec(), kind="cast_call")
    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        stdout = (proc.stdout or "").strip()
        raise WalletStoreError(stderr or stdout or f"cast calldata failed for {signature}.")
    data = (proc.stdout or "").strip()
    if not re.fullmatch(r"0x[a-fA-F0-9]+", data):
        raise WalletStoreError(f"cast calldata returned malformed output for {signature}.")
    return data


def _retryable_send_error(stderr: str) -> bool:
    normalized = stderr.lower()
    retryable_fragments = (
        "replacement transaction underpriced",
        "nonce too low",
        "already known",
        "temporarily underpriced",
        "transaction underpriced",
    )
    return any(fragment in normalized for fragment in retryable_fragments)


def _parse_next_nonce_from_error(stderr: str) -> int | None:
    # Example: "nonce too low: next nonce 5, tx nonce 4"
    match = re.search(r"nonce too low: next nonce ([0-9]+), tx nonce ([0-9]+)", stderr.lower())
    if not match:
        return None
    try:
        return int(match.group(1))
    except Exception:
        return None


def _tx_send_max_attempts() -> int:
    raw = (os.environ.get("XCLAW_TX_SEND_MAX_ATTEMPTS") or "").strip()
    if not raw:
        return DEFAULT_TX_SEND_MAX_ATTEMPTS
    if not re.fullmatch(r"[0-9]+", raw):
        raise WalletStoreError("XCLAW_TX_SEND_MAX_ATTEMPTS must be an integer >= 1.")
    value = int(raw)
    if value < 1:
        raise WalletStoreError("XCLAW_TX_SEND_MAX_ATTEMPTS must be >= 1.")
    return value


def _tx_gas_price_bump_gwei() -> int:
    raw = (os.environ.get("XCLAW_TX_GAS_PRICE_BUMP_GWEI") or "").strip()
    if not raw:
        return TX_GAS_PRICE_BUMP_GWEI
    if not re.fullmatch(r"[0-9]+", raw):
        raise WalletStoreError("XCLAW_TX_GAS_PRICE_BUMP_GWEI must be an integer >= 1.")
    value = int(raw)
    if value < 1:
        raise WalletStoreError("XCLAW_TX_GAS_PRICE_BUMP_GWEI must be >= 1.")
    return value


def _tx_gas_price_gwei(attempt_index: int) -> int:
    raw = (os.environ.get("XCLAW_TX_GAS_PRICE_GWEI") or "").strip()
    if raw:
        if not re.fullmatch(r"[0-9]+", raw):
            raise WalletStoreError("XCLAW_TX_GAS_PRICE_GWEI must be a positive integer in gwei.")
        base = int(raw)
    else:
        base = DEFAULT_TX_GAS_PRICE_GWEI
    if base < 1:
        raise WalletStoreError("XCLAW_TX_GAS_PRICE_GWEI must be >= 1.")
    bump = _tx_gas_price_bump_gwei()
    # Exponential escalation helps clear "replacement transaction underpriced"
    # when another pending tx already occupies the nonce with a higher gas price.
    return base + ((2**attempt_index - 1) * bump)


def _cast_nonce(cast_bin: str, rpc_url: str, from_addr: str, block_tag: str) -> int | None:
    nonce_proc = _run_subprocess(
        [cast_bin, "nonce", "--rpc-url", rpc_url, from_addr, "--block", block_tag],
        timeout_sec=_cast_call_timeout_sec(),
        kind="cast_call",
    )
    if nonce_proc.returncode != 0:
        return None
    nonce_raw = (nonce_proc.stdout or "").strip()
    try:
        return _parse_uint_text(nonce_raw)
    except WalletStoreError:
        return None


def _cast_rpc_send_transaction(rpc_url: str, tx_obj: dict[str, str], private_key_hex: str | None = None) -> str:
    cast_bin = _require_cast_bin()
    if private_key_hex:
        from_addr = tx_obj.get("from")
        to_addr = tx_obj.get("to")
        data = tx_obj.get("data")
        if not isinstance(from_addr, str) or not is_hex_address(from_addr):
            raise WalletStoreError("cast send requires tx_obj.from as hex address.")
        if not isinstance(to_addr, str) or not is_hex_address(to_addr):
            raise WalletStoreError("cast send requires tx_obj.to as hex address.")
        if not isinstance(data, str) or not re.fullmatch(r"0x[a-fA-F0-9]*", data):
            raise WalletStoreError("cast send requires tx_obj.data as hex calldata.")
        attempts = _tx_send_max_attempts()
        last_err = "cast send failed."
        nonce_override: int | None = None
        for attempt in range(attempts):
            nonce: int | None
            if nonce_override is not None:
                nonce = nonce_override
            else:
                nonce_pending = _cast_nonce(cast_bin, rpc_url, from_addr, "pending")
                nonce_latest = _cast_nonce(cast_bin, rpc_url, from_addr, "latest")
                nonce_candidates = [value for value in (nonce_pending, nonce_latest) if value is not None]
                nonce = max(nonce_candidates) if nonce_candidates else None

            send_cmd = [
                cast_bin,
                "send",
                "--json",
                "--rpc-url",
                rpc_url,
                "--private-key",
                private_key_hex,
                "--gas-price",
                f"{_tx_gas_price_gwei(attempt)}gwei",
            ]
            if nonce is not None:
                send_cmd.extend(["--nonce", str(nonce)])
            send_cmd.extend(
                [
                    "--from",
                    from_addr,
                    to_addr,
                    data,
                ]
            )
            proc = _run_subprocess(send_cmd, timeout_sec=_cast_send_timeout_sec(), kind="cast_send")
            if proc.returncode == 0:
                return _extract_tx_hash(proc.stdout)

            stderr = (proc.stderr or "").strip()
            stdout = (proc.stdout or "").strip()
            last_err = stderr or stdout or "cast send failed."
            next_nonce = _parse_next_nonce_from_error(last_err)
            if attempt < (attempts - 1) and next_nonce is not None:
                nonce_override = next_nonce
                time.sleep(0.25)
                continue
            if attempt < (attempts - 1) and _retryable_send_error(last_err):
                time.sleep(0.25)
                continue
            if attempt < (attempts - 1):
                raise WalletStoreError(last_err)

        raise WalletStoreError(f"{last_err} (after {attempts} attempts)")
    else:
        proc = _run_subprocess(
            [cast_bin, "rpc", "--rpc-url", rpc_url, "eth_sendTransaction", json.dumps(tx_obj, separators=(",", ":"))],
            timeout_sec=_cast_send_timeout_sec(),
            kind="cast_send",
        )
    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        stdout = (proc.stdout or "").strip()
        raise WalletStoreError(stderr or stdout or "cast rpc eth_sendTransaction failed.")
    return _extract_tx_hash(proc.stdout)


def cmd_status(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    default_chain = (os.environ.get("XCLAW_DEFAULT_CHAIN") or "").strip() or None
    has_cast = cast_exists()
    hostname: str | None
    try:
        hostname = socket.gethostname()
    except Exception:
        hostname = None

    agent_id: str | None = None
    wallet_address: str | None = None
    agent_name: str | None = None
    identity_warnings: list[dict[str, str]] = []
    if default_chain:
        try:
            agent_id = _resolve_agent_id(_resolve_api_key())
        except Exception:
            agent_id = None
        try:
            wallet_address = _wallet_address_for_chain(default_chain)
        except Exception:
            wallet_address = None
        if agent_id:
            try:
                base_url = _require_api_base_url()
                status_code, body = _http_json_request("GET", f"{base_url}/public/agents/{urllib.parse.quote(agent_id)}")
                if 200 <= status_code < 300:
                    agent_obj = body.get("agent")
                    if isinstance(agent_obj, dict):
                        raw_name = agent_obj.get("agent_name") or agent_obj.get("agentName")
                        if isinstance(raw_name, str) and raw_name.strip():
                            agent_name = raw_name.strip()
                else:
                    identity_warnings.append(
                        {"code": str(body.get("code", "api_error")), "message": str(body.get("message", f"profile read failed ({status_code})"))}
                    )
            except Exception as exc:
                identity_warnings.append({"code": "agent_name_unavailable", "message": str(exc)})

    return ok(
        "Agent runtime scaffold is healthy.",
        status="ready",
        timestamp=utc_now(),
        scaffold=True,
        defaultChain=default_chain,
        agentId=agent_id,
        agentName=agent_name,
        walletAddress=wallet_address,
        hostname=hostname,
        hasCast=has_cast,
        identityWarnings=identity_warnings or None,
    )


def cmd_not_implemented(args: argparse.Namespace, name: str) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    return fail(
        "not_implemented",
        f"{name} is scaffolded but not fully implemented yet.",
        "Implement runtime handler in apps/agent-runtime/xclaw_agent/cli.py and re-test.",
        {"command": name, "scaffold": True},
        exit_code=1,
    )


def cmd_intents_poll(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    try:
        status_code, body = _api_request("GET", f"/trades/pending?chainKey={urllib.parse.quote(args.chain)}&limit=25")
        if status_code < 200 or status_code >= 300:
            return fail(
                str(body.get("code", "api_error")),
                str(body.get("message", f"intents poll failed ({status_code})")),
                str(body.get("actionHint", "Verify API auth and retry.")),
                {"status": status_code, "chain": args.chain},
                exit_code=1,
            )
        items = body.get("items", [])
        if not isinstance(items, list):
            raise WalletStoreError("Trade pending response 'items' is not a list.")
        if len(items) == 0:
            return ok("No pending trade intents.", chain=args.chain, count=0, intents=[], nextAction="Wait for new intents or run dashboard.")
        return ok("Trade intents polled.", chain=args.chain, count=len(items), intents=items)
    except WalletStoreError as exc:
        return fail("intents_poll_failed", str(exc), "Verify API env, auth, and endpoint availability.", {"chain": args.chain}, exit_code=1)
    except Exception as exc:
        return fail("intents_poll_failed", str(exc), "Inspect runtime intents poll path and retry.", {"chain": args.chain}, exit_code=1)


def cmd_approvals_check(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    try:
        trade = _read_trade_details(args.intent)
        if str(trade.get("chainKey")) != args.chain:
            return fail(
                "chain_mismatch",
                "Trade chain does not match command --chain.",
                "Use matching chain or refresh intent selection.",
                {"tradeId": args.intent, "tradeChain": trade.get("chainKey"), "requestedChain": args.chain},
                exit_code=1,
            )

        status = str(trade.get("status"))
        retry = trade.get("retry") if isinstance(trade.get("retry"), dict) else {}
        retry_eligible = bool(retry.get("eligible", False))
        if status == "approved" or (status == "failed" and retry_eligible):
            return ok("Approval check passed.", tradeId=args.intent, chain=args.chain, approved=True, status=status, retry=retry)
        if status == "approval_pending":
            return fail("approval_required", "Trade is waiting for management approval.", "Approve trade from authorized management view.", {"tradeId": args.intent}, exit_code=1)
        if status == "rejected":
            return fail("approval_rejected", "Trade approval was rejected.", "Review rejection reason and create a new trade if needed.", {"tradeId": args.intent, "reasonCode": trade.get("reasonCode")}, exit_code=1)
        if status == "expired":
            return fail("approval_expired", "Trade approval has expired.", "Re-propose trade and request approval again.", {"tradeId": args.intent}, exit_code=1)
        return fail(
            "policy_denied",
            f"Trade is not executable from status '{status}'.",
            "Poll intents and execute only actionable trades.",
            {"tradeId": args.intent, "status": status, "retry": retry},
            exit_code=1,
        )
    except WalletStoreError as exc:
        return fail("approval_check_failed", str(exc), "Verify API env, auth, and trade visibility.", {"tradeId": args.intent, "chain": args.chain}, exit_code=1)
    except Exception as exc:
        return fail("approval_check_failed", str(exc), "Inspect runtime approval-check path and retry.", {"tradeId": args.intent, "chain": args.chain}, exit_code=1)


def cmd_trade_execute(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk

    transition_state = "init"
    previous_status = "approved"
    try:
        # Best-effort: usage outbox replay should not block intent validation/execution.
        try:
            _replay_trade_usage_outbox()
        except Exception:
            pass
        trade = _read_trade_details(args.intent)
        status = str(trade.get("status"))
        if str(trade.get("chainKey")) != args.chain:
            return fail(
                "chain_mismatch",
                "Trade chain does not match command --chain.",
                "Use matching chain or refresh intent selection.",
                {"tradeId": args.intent, "tradeChain": trade.get("chainKey"), "requestedChain": args.chain},
                exit_code=1,
            )

        previous_status = status
        retry = trade.get("retry") if isinstance(trade.get("retry"), dict) else {}
        retry_eligible = bool(retry.get("eligible", False))
        if status not in ("approved", "failed"):
            return fail(
                "approval_required",
                f"Trade is not executable from status '{status}'.",
                "Execute only approved trades or failed trades within retry policy.",
                {"tradeId": args.intent, "status": status},
                exit_code=1,
            )
        if status == "failed" and not retry_eligible:
            return fail(
                "policy_denied",
                "Retry policy does not allow this failed trade to execute.",
                "Re-propose trade or retry within policy window/limits.",
                {"tradeId": args.intent, "retry": retry, "maxRetries": MAX_TRADE_RETRIES, "retryWindowSec": RETRY_WINDOW_SEC},
                exit_code=1,
            )

        mode = str(trade.get("mode"))
        if mode != "real":
            return fail(
                "unsupported_mode",
                "Mock mode is deprecated for runtime trade execution.",
                "Execute network trades only on base_sepolia (`mode=real`).",
                {"tradeId": args.intent, "mode": mode, "supportedMode": "real", "chain": args.chain},
                exit_code=1,
            )

        store = load_wallet_store()
        wallet_address, private_key_hex = _execution_wallet(store, args.chain)
        cast_bin = _require_cast_bin()
        rpc_url = _chain_rpc_url(args.chain)
        router = _require_chain_contract_address(args.chain, "router")

        token_in_raw = str(trade.get("tokenIn") or "").strip()
        token_out_raw = str(trade.get("tokenOut") or "").strip()
        if token_in_raw == "" or token_out_raw == "":
            raise WalletStoreError("Trade payload is missing tokenIn/tokenOut.")
        try:
            token_in = _resolve_token_address(args.chain, token_in_raw)
            token_out = _resolve_token_address(args.chain, token_out_raw)
        except Exception as exc:
            raise WalletStoreError(
                f"Could not resolve trade token addresses for execution ({token_in_raw} -> {token_out_raw}): {exc}"
            ) from exc

        token_in_meta = _fetch_erc20_metadata(args.chain, token_in)
        token_in_decimals = int(token_in_meta.get("decimals", 18))
        amount_wei_str = _to_units_uint(str(trade.get("amountIn") or ""), token_in_decimals)
        amount_wei = int(amount_wei_str)
        state, day_key, current_spend, max_daily_wei = _enforce_spend_preconditions(args.chain, amount_wei, enforce_native_cap=False)
        projected_spend_usd = _to_non_negative_decimal(trade.get("amountIn") or "0")
        cap_state, _, current_spend_usd, current_filled_trades, trade_caps = _enforce_trade_caps(args.chain, projected_spend_usd, 1)
        deadline = str(int(datetime.now(timezone.utc).timestamp()) + 120)

        approve_data = _cast_calldata("approve(address,uint256)(bool)", [router, amount_wei_str])
        approve_tx_hash = _cast_rpc_send_transaction(
            rpc_url,
            {
                "from": wallet_address,
                "to": token_in,
                "data": approve_data,
            },
            private_key_hex,
        )
        approve_receipt = _run_subprocess(
            [cast_bin, "receipt", "--json", "--rpc-url", rpc_url, approve_tx_hash],
            timeout_sec=_cast_receipt_timeout_sec(),
            kind="cast_receipt",
        )
        if approve_receipt.returncode != 0:
            stderr = (approve_receipt.stderr or "").strip()
            stdout = (approve_receipt.stdout or "").strip()
            raise WalletStoreError(stderr or stdout or "cast receipt failed for approve tx.")
        approve_payload = json.loads((approve_receipt.stdout or "{}").strip() or "{}")
        approve_status = str(approve_payload.get("status", "0x0")).lower()
        if approve_status not in {"0x1", "1"}:
            raise WalletStoreError(f"Approve receipt indicates failure status '{approve_status}'.")

        swap_data = _cast_calldata(
            "swapExactTokensForTokens(uint256,uint256,address[],address,uint256)(uint256[])",
            [amount_wei_str, "1", f"[{token_in},{token_out}]", wallet_address, deadline],
        )
        tx_hash = _cast_rpc_send_transaction(
            rpc_url,
            {
                "from": wallet_address,
                "to": router,
                "data": swap_data,
            },
            private_key_hex,
        )
        _post_trade_status(args.intent, previous_status, "executing", {"txHash": tx_hash})
        transition_state = "executing"
        _post_trade_status(args.intent, "executing", "verifying", {"txHash": tx_hash})
        transition_state = "verifying"

        receipt_proc = _run_subprocess(
            [cast_bin, "receipt", "--json", "--rpc-url", rpc_url, tx_hash],
            timeout_sec=_cast_receipt_timeout_sec(),
            kind="cast_receipt",
        )
        if receipt_proc.returncode != 0:
            stderr = (receipt_proc.stderr or "").strip()
            stdout = (receipt_proc.stdout or "").strip()
            raise WalletStoreError(stderr or stdout or "cast receipt failed.")
        receipt_payload = json.loads((receipt_proc.stdout or "{}").strip() or "{}")
        receipt_status = str(receipt_payload.get("status", "0x0")).lower()
        if receipt_status not in {"0x1", "1"}:
            raise WalletStoreError(f"On-chain receipt indicates failure status '{receipt_status}'.")

        _record_spend(state, args.chain, day_key, current_spend + amount_wei)
        _record_trade_cap_ledger(
            cap_state,
            args.chain,
            day_key,
            current_spend_usd + projected_spend_usd,
            current_filled_trades + 1,
        )
        try:
            _post_trade_usage(args.chain, day_key, projected_spend_usd, 1)
        except Exception:
            pass
        _post_trade_status(args.intent, "verifying", "filled", {"txHash": tx_hash})
        report_result = {
            "ok": False,
            "skipped": True,
            "reason": "real_mode_server_tracked",
            "message": "Real-mode trade reports are server-tracked via wallet/RPC and are not sent by runtime."
        }
        return ok(
            "Trade executed in real mode.",
            tradeId=args.intent,
            chain=args.chain,
            mode=mode,
            status="filled",
            txHash=tx_hash,
            day=day_key,
            dailySpendUsd=_decimal_text(current_spend_usd + projected_spend_usd),
            maxDailyUsd=trade_caps.get("maxDailyUsd"),
            dailyFilledTrades=int(current_filled_trades + 1),
            maxDailyTradeCount=trade_caps.get("maxDailyTradeCount"),
            dailySpendWei=str(current_spend + amount_wei),
            maxDailyNativeWei=str(max_daily_wei),
            report=report_result,
        )
    except WalletPolicyError as exc:
        if transition_state == "executing":
            try:
                _post_trade_status(args.intent, "executing", "failed", {"reasonCode": "policy_denied", "reasonMessage": str(exc)})
            except Exception:
                pass
        return fail(exc.code, str(exc), exc.action_hint, exc.details, exit_code=1)
    except WalletStoreError as exc:
        if transition_state == "executing":
            try:
                _post_trade_status(args.intent, "executing", "failed", {"reasonCode": "rpc_unavailable", "reasonMessage": str(exc)})
            except Exception:
                pass
        elif transition_state == "init":
            try:
                _post_trade_status(args.intent, previous_status, "failed", {"reasonCode": "rpc_unavailable", "reasonMessage": str(exc)})
            except Exception:
                pass
        elif transition_state == "verifying":
            try:
                _post_trade_status(args.intent, "verifying", "failed", {"reasonCode": "verification_timeout", "reasonMessage": str(exc)})
            except Exception:
                pass
        return fail("trade_execute_failed", str(exc), "Verify approval state, wallet setup, and local chain connectivity.", {"tradeId": args.intent, "chain": args.chain}, exit_code=1)
    except Exception as exc:
        return fail("trade_execute_failed", str(exc), "Inspect runtime trade execute path and retry.", {"tradeId": args.intent, "chain": args.chain}, exit_code=1)


def _send_trade_execution_report(trade_id: str) -> dict[str, Any]:
    trade = _read_trade_details(trade_id)
    event_type = _canonical_event_for_trade_status(str(trade.get("status")))
    payload = {
        "schemaVersion": 1,
        "agentId": trade.get("agentId"),
        "tradeId": trade_id,
        "eventType": event_type,
        "payload": {
            "status": trade.get("status"),
            "mode": trade.get("mode"),
            "chainKey": trade.get("chainKey"),
            "reasonCode": trade.get("reasonCode"),
            "reportedBy": "xclaw-agent-runtime",
        },
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    status_code, body = _api_request("POST", "/events", payload=payload, include_idempotency=True)
    if status_code < 200 or status_code >= 300:
        code = str(body.get("code", "api_error"))
        message = str(body.get("message", f"report send failed ({status_code})"))
        raise WalletStoreError(f"{code}: {message}")
    return {"ok": True, "eventType": event_type}


def cmd_report_send(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    try:
        trade = _read_trade_details(args.trade)
        mode = str(trade.get("mode") or "")
        return fail(
            "report_send_deprecated",
            "Manual report-send is deprecated for network mode.",
            "Do not call report-send; execution status is tracked server-side.",
            {"tradeId": args.trade, "mode": mode or None},
            exit_code=1,
        )
    except WalletStoreError as exc:
        return fail("report_send_failed", str(exc), "Verify API env/auth and trade visibility, then retry.", {"tradeId": args.trade}, exit_code=1)
    except Exception as exc:
        return fail("report_send_failed", str(exc), "Inspect runtime report-send path and retry.", {"tradeId": args.trade}, exit_code=1)


def _chat_messages_query(limit: int = 25) -> list[dict[str, Any]]:
    query = f"/chat/messages?limit={limit}"
    status_code, body = _api_request("GET", query)
    if status_code < 200 or status_code >= 300:
        code = str(body.get("code", "api_error"))
        message = str(body.get("message", f"chat messages read failed ({status_code})"))
        raise WalletStoreError(f"{code}: {message}")
    items = body.get("items", [])
    if not isinstance(items, list):
        raise WalletStoreError("Chat messages response missing items list.")
    return [item for item in items if isinstance(item, dict)]


def cmd_chat_poll(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    try:
        path = "/chat/messages?limit=25"
        status_code, body = _api_request("GET", path)
        if status_code < 200 or status_code >= 300:
            code = str(body.get("code", "api_error"))
            message = str(body.get("message", f"chat messages read failed ({status_code})"))
            return fail(
                "chat_poll_failed",
                f"{code}: {message}",
                str(body.get("actionHint", "Retry once. If it persists, use requestId to inspect server logs.")),
                _api_error_details(status_code, body, path, chain=args.chain),
                exit_code=1,
            )
        items = body.get("items", [])
        if not isinstance(items, list):
            items = []
        return ok("Trade room messages polled.", chain=args.chain, count=len(items), messages=[item for item in items if isinstance(item, dict)])
    except WalletStoreError as exc:
        return fail("chat_poll_failed", str(exc), "Verify API env/auth and chat endpoint availability.", {"chain": args.chain}, exit_code=1)
    except Exception as exc:
        return fail("chat_poll_failed", str(exc), "Inspect runtime chat poll path and retry.", {"chain": args.chain}, exit_code=1)


def cmd_chat_post(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    try:
        message = str(args.message).strip()
        if not message:
            return fail("payload_invalid", "Chat message cannot be empty.", "Provide a non-empty message.", {"chain": args.chain}, exit_code=1)
        if len(message) > 500:
            return fail("payload_invalid", "Chat message exceeds 500 characters.", "Shorten message and retry.", {"chain": args.chain}, exit_code=1)

        tags: list[str] = []
        if args.tags:
            parsed_tags = [tag.strip().lower() for tag in str(args.tags).split(",") if tag.strip()]
            if len(parsed_tags) > 8:
                return fail("payload_invalid", "Chat tags exceed 8 values.", "Limit tags to 8 and retry.", {"chain": args.chain}, exit_code=1)
            tags = list(dict.fromkeys(parsed_tags))

        api_key = _resolve_api_key()
        agent_id = _resolve_agent_id(api_key)
        if not agent_id:
            return fail("auth_invalid", "Agent id could not be resolved for chat post.", "Set XCLAW_AGENT_ID or use signed agent token format.", {"chain": args.chain}, exit_code=1)

        payload = {
            "schemaVersion": 1,
            "agentId": agent_id,
            "message": message,
            "chainKey": args.chain,
            "tags": tags,
        }
        path = "/chat/messages"
        status_code, body = _api_request("POST", path, payload=payload)
        if status_code < 200 or status_code >= 300:
            return fail(
                str(body.get("code", "api_error")),
                str(body.get("message", f"chat post failed ({status_code})")),
                str(body.get("actionHint", "Refresh auth/session state and retry.")),
                _api_error_details(status_code, body, path, chain=args.chain),
                exit_code=1,
            )
        item = body.get("item")
        if not isinstance(item, dict):
            item = {}
        return ok("Trade room message posted.", chain=args.chain, item=item)
    except WalletStoreError as exc:
        return fail("chat_post_failed", str(exc), "Verify API env/auth and retry.", {"chain": args.chain}, exit_code=1)
    except Exception as exc:
        return fail("chat_post_failed", str(exc), "Inspect runtime chat post path and retry.", {"chain": args.chain}, exit_code=1)


def _runtime_platform_name() -> str:
    platform_value = sys.platform.lower()
    if platform_value.startswith("win"):
        return "windows"
    if platform_value == "darwin":
        return "macos"
    return "linux"


def cmd_profile_set_name(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    try:
        requested_name = str(args.name).strip()
        if not requested_name:
            return fail(
                "payload_invalid",
                "Username cannot be empty.",
                "Provide a non-empty username and retry.",
                {"field": "name"},
                exit_code=1,
            )
        if len(requested_name) > 32:
            return fail(
                "payload_invalid",
                "Username exceeds 32 characters.",
                "Shorten username to 32 characters or fewer and retry.",
                {"field": "name", "maxLength": 32},
                exit_code=1,
            )

        api_key = _resolve_api_key()
        agent_id = _resolve_agent_id(api_key)
        if not agent_id:
            return fail(
                "auth_invalid",
                "Agent id could not be resolved for username change.",
                "Set XCLAW_AGENT_ID or use signed agent token format.",
                {"chain": args.chain},
                exit_code=1,
            )

        wallet_address = _wallet_address_for_chain(args.chain)
        payload = {
            "schemaVersion": 1,
            "agentId": agent_id,
            "agentName": requested_name,
            "runtimePlatform": _runtime_platform_name(),
            "wallets": [{"chainKey": args.chain, "address": wallet_address}],
        }
        status_code, body = _api_request("POST", "/agent/register", payload=payload, include_idempotency=True)
        if status_code < 200 or status_code >= 300:
            return fail(
                str(body.get("code", "api_error")),
                str(body.get("message", f"profile set-name failed ({status_code})")),
                str(
                    body.get(
                        "actionHint",
                        "Retry with a unique username. If recently renamed, wait for cooldown to expire and retry.",
                    )
                ),
                {"status": status_code, "chain": args.chain, "agentId": agent_id, "requestedName": requested_name},
                exit_code=1,
            )

        updated_name = body.get("agentName")
        if not isinstance(updated_name, str) or not updated_name.strip():
            updated_name = requested_name
        return ok("Agent username updated.", chain=args.chain, agentId=agent_id, agentName=updated_name)
    except WalletStoreError as exc:
        return fail(
            "profile_set_name_failed",
            str(exc),
            "Verify API env/auth, local wallet availability, and retry.",
            {"chain": args.chain},
            exit_code=1,
        )
    except Exception as exc:
        return fail("profile_set_name_failed", str(exc), "Inspect runtime profile set-name path and retry.", {"chain": args.chain}, exit_code=1)


def cmd_management_link(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    try:
        api_key = _resolve_api_key()
        agent_id = _resolve_agent_id(api_key)
        if not agent_id:
            return fail(
                "auth_invalid",
                "Agent id could not be resolved for management-link command.",
                "Set XCLAW_AGENT_ID or use signed agent token format.",
                exit_code=1,
            )
        payload = {
            "schemaVersion": 1,
            "agentId": agent_id,
            "ttlSeconds": int(args.ttl_seconds),
        }
        status_code, body = _api_request("POST", "/agent/management-link", payload=payload, include_idempotency=True)
        if status_code < 200 or status_code >= 300:
            return fail(
                str(body.get("code", "api_error")),
                str(body.get("message", f"management-link failed ({status_code})")),
                str(body.get("actionHint", "Refresh auth/session state and retry.")),
                {"status": status_code},
                exit_code=1,
            )
        management_url = _normalize_management_url(body.get("managementUrl"))
        delivery = _maybe_send_owner_link_to_active_chat(management_url, body.get("expiresAt"))
        delivered = bool(delivery.get("sent"))
        payload: dict[str, Any] = {
            "agentId": body.get("agentId", agent_id),
            "issuedAt": body.get("issuedAt"),
            "expiresAt": body.get("expiresAt"),
            "ownerHandoffRequired": True,
            "securityNote": "Short-lived one-time link; send only to the requesting owner.",
            "deliveredToActiveChat": delivered,
            "delivery": delivery,
        }
        if delivered:
            payload["managementUrlOmitted"] = True
            payload["nextAction"] = "Owner link was sent directly to active chat; do not echo link again."
            return ok("Owner management link sent to active chat.", **payload)
        payload["managementUrl"] = management_url
        payload["nextAction"] = "Direct chat delivery failed; paste managementUrl to the requesting owner."
        return ok("Owner management link generated (manual handoff required).", **payload)
    except WalletStoreError as exc:
        return fail("management_link_failed", str(exc), "Verify API env/auth and retry.", exit_code=1)
    except Exception as exc:
        return fail("management_link_failed", str(exc), "Inspect runtime management-link path and retry.", exit_code=1)


def cmd_faucet_request(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    try:
        api_key = _resolve_api_key()
        agent_id = _resolve_agent_id(api_key)
        if not agent_id:
            return fail(
                "auth_invalid",
                "Agent id could not be resolved for faucet request.",
                "Set XCLAW_AGENT_ID or use signed agent token format.",
                {"chain": args.chain},
                exit_code=1,
            )
        payload = {
            "schemaVersion": 1,
            "agentId": agent_id,
            "chainKey": args.chain,
        }
        status_code, body = _api_request("POST", "/agent/faucet/request", payload=payload, include_idempotency=True)
        if status_code < 200 or status_code >= 300:
            retry_after_sec: int | None = None
            api_details = body.get("details")
            if isinstance(api_details, dict):
                raw_retry = api_details.get("retryAfterSeconds")
                try:
                    if raw_retry is not None:
                        retry_after_sec = int(raw_retry)
                except Exception:
                    retry_after_sec = None

            details = _api_error_details(status_code, body, "/agent/faucet/request", chain=args.chain)
            payload = {
                "ok": False,
                "code": str(body.get("code", "api_error")),
                "message": str(body.get("message", f"faucet request failed ({status_code})")),
                "actionHint": str(body.get("actionHint", "Retry later or check faucet availability.")),
                "details": details,
            }
            if retry_after_sec is not None:
                payload["retryAfterSec"] = retry_after_sec
            emit(payload)
            return 1
        token_drips = body.get("tokenDrips")
        if not isinstance(token_drips, list):
            token_drips = None
        return ok(
            "Faucet request submitted.",
            agentId=agent_id,
            chain=args.chain,
            amountWei=str(body.get("amountWei", "50000000000000000")),
            txHash=body.get("txHash"),
            to=body.get("to"),
            tokenDrips=token_drips,
            pending=True,
            recommendedDelaySec=20,
            nextAction="Wait ~1-2 blocks, then run dashboard. Balances may not update immediately after tx submission.",
        )
    except WalletStoreError as exc:
        return fail("faucet_request_failed", str(exc), "Verify API env/auth and retry.", {"chain": args.chain}, exit_code=1)
    except Exception as exc:
        return fail("faucet_request_failed", str(exc), "Inspect runtime faucet request path and retry.", {"chain": args.chain}, exit_code=1)


def _fetch_native_balance_wei(chain: str, address: str) -> str:
    cast_bin = _require_cast_bin()
    rpc_url = _chain_rpc_url(chain)
    proc = _run_subprocess(
        [cast_bin, "balance", address, "--rpc-url", rpc_url],
        timeout_sec=_cast_call_timeout_sec(),
        kind="cast_call",
    )
    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        stdout = (proc.stdout or "").strip()
        raise WalletStoreError(stderr or stdout or "cast balance failed.")
    output = (proc.stdout or "").strip().splitlines()
    parsed = _parse_uint_text(output[-1] if output else "")
    return str(parsed)


def _fetch_token_balance_wei(chain: str, address: str, token_address: str) -> str:
    cast_bin = _require_cast_bin()
    rpc_url = _chain_rpc_url(chain)
    proc = _run_subprocess(
        [cast_bin, "call", token_address, "balanceOf(address)(uint256)", address, "--rpc-url", rpc_url],
        timeout_sec=_cast_call_timeout_sec(),
        kind="cast_call",
    )
    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        stdout = (proc.stdout or "").strip()
        raise WalletStoreError(stderr or stdout or "cast call balanceOf failed.")
    output = (proc.stdout or "").strip().splitlines()
    parsed = _parse_uint_text(output[-1] if output else "")
    return str(parsed)


def _fetch_token_allowance_wei(chain: str, token_address: str, owner: str, spender: str) -> str:
    cast_bin = _require_cast_bin()
    rpc_url = _chain_rpc_url(chain)
    proc = _run_subprocess(
        [cast_bin, "call", token_address, "allowance(address,address)(uint256)", owner, spender, "--rpc-url", rpc_url],
        timeout_sec=_cast_call_timeout_sec(),
        kind="cast_call",
    )
    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        stdout = (proc.stdout or "").strip()
        raise WalletStoreError(stderr or stdout or "cast call allowance failed.")
    output = (proc.stdout or "").strip().splitlines()
    parsed = _parse_uint_text(output[-1] if output else "")
    return str(parsed)


def _canonical_token_map(chain: str) -> dict[str, str]:
    cfg = _load_chain_config(chain)
    tokens = cfg.get("canonicalTokens")
    if not isinstance(tokens, dict):
        return {}
    out: dict[str, str] = {}
    for symbol, address in tokens.items():
        if isinstance(symbol, str) and isinstance(address, str) and is_hex_address(address):
            out[symbol] = address
    return out


def _fetch_wallet_holdings(chain: str) -> dict[str, Any]:
    store = load_wallet_store()
    _, wallet = _chain_wallet(store, chain)
    if wallet is None:
        raise WalletStoreError(f"No wallet configured for chain '{chain}'.")
    _validate_wallet_entry_shape(wallet)
    address = str(wallet.get("address"))
    native_balance_wei = _fetch_native_balance_wei(chain, address)
    native_balance_eth = _format_units(int(native_balance_wei), 18)
    token_map = _canonical_token_map(chain)
    token_balances: list[dict[str, Any]] = []
    token_errors: list[dict[str, Any]] = []
    for symbol, token_address in token_map.items():
        try:
            balance_wei = _fetch_token_balance_wei(chain, address, token_address)
            meta = _fetch_erc20_metadata(chain, token_address)
            decimals = int(meta.get("decimals", 18))
            token_balances.append(
                {
                    "symbol": str(meta.get("symbol") or symbol),
                    "token": token_address,
                    "balanceWei": balance_wei,
                    "balance": _format_units(int(balance_wei), decimals),
                    "balancePretty": _format_units_pretty(int(balance_wei), decimals),
                    "decimals": decimals,
                }
            )
        except Exception as exc:
            token_errors.append({"symbol": symbol, "token": token_address, "message": str(exc)})
    return {
        "address": address,
        "native": {
            "symbol": "ETH",
            "balanceWei": native_balance_wei,
            "balance": native_balance_eth,
            "balancePretty": _format_units_pretty(int(native_balance_wei), 18),
            "decimals": 18,
        },
        "tokens": token_balances,
        "tokenErrors": token_errors,
    }


def cmd_dashboard(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    try:
        api_key = _resolve_api_key()
        agent_id = _resolve_agent_id(api_key)
        if not agent_id:
            return fail(
                "auth_invalid",
                "Agent id could not be resolved for dashboard command.",
                "Set XCLAW_AGENT_ID or use signed agent token format.",
                {"chain": args.chain},
                exit_code=1,
            )

        chain_escaped = urllib.parse.quote(args.chain)
        agent_escaped = urllib.parse.quote(agent_id)
        section_errors: list[dict[str, str]] = []

        profile: dict[str, Any] | None = None
        recent_trades: list[dict[str, Any]] = []
        pending_intents: list[dict[str, Any]] = []
        open_orders: list[dict[str, Any]] = []
        recent_room_messages: list[dict[str, Any]] = []

        profile_status, profile_body = _api_request("GET", f"/public/agents/{agent_escaped}")
        if 200 <= profile_status < 300:
            profile_payload = profile_body.get("agent")
            if isinstance(profile_payload, dict):
                profile = profile_payload
        else:
            section_errors.append(
                {
                    "section": "profile",
                    "code": str(profile_body.get("code", "api_error")),
                    "message": str(profile_body.get("message", f"profile read failed ({profile_status})")),
                    "requestId": str(profile_body.get("requestId") or ""),
                }
            )

        trades_status, trades_body = _api_request("GET", f"/public/agents/{agent_escaped}/trades?limit=20")
        if 200 <= trades_status < 300:
            items = trades_body.get("items")
            if isinstance(items, list):
                recent_trades = [item for item in items if isinstance(item, dict)]
        else:
            section_errors.append(
                {
                    "section": "recentTrades",
                    "code": str(trades_body.get("code", "api_error")),
                    "message": str(trades_body.get("message", f"trade history read failed ({trades_status})")),
                    "requestId": str(trades_body.get("requestId") or ""),
                }
            )

        intents_status, intents_body = _api_request("GET", f"/trades/pending?chainKey={chain_escaped}&limit=25")
        if 200 <= intents_status < 300:
            items = intents_body.get("items")
            if isinstance(items, list):
                pending_intents = [item for item in items if isinstance(item, dict)]
        else:
            section_errors.append(
                {
                    "section": "pendingIntents",
                    "code": str(intents_body.get("code", "api_error")),
                    "message": str(intents_body.get("message", f"pending intents read failed ({intents_status})")),
                    "requestId": str(intents_body.get("requestId") or ""),
                }
            )

        orders_status, orders_body = _api_request("GET", f"/limit-orders?chainKey={chain_escaped}&status=open&limit=50")
        if 200 <= orders_status < 300:
            items = orders_body.get("items")
            if isinstance(items, list):
                open_orders = [item for item in items if isinstance(item, dict)]
        else:
            section_errors.append(
                {
                    "section": "openOrders",
                    "code": str(orders_body.get("code", "api_error")),
                    "message": str(orders_body.get("message", f"open orders read failed ({orders_status})")),
                    "requestId": str(orders_body.get("requestId") or ""),
                }
            )

        chat_status, chat_body = _api_request("GET", "/chat/messages?limit=8")
        if 200 <= chat_status < 300:
            items = chat_body.get("items")
            if isinstance(items, list):
                recent_room_messages = [item for item in items if isinstance(item, dict)]
        else:
            section_errors.append(
                {
                    "section": "recentRoomMessages",
                    "code": str(chat_body.get("code", "api_error")),
                    "message": str(chat_body.get("message", f"chat read failed ({chat_status})")),
                    "requestId": str(chat_body.get("requestId") or ""),
                }
            )

        holdings: dict[str, Any] | None = None
        try:
            holdings = _fetch_wallet_holdings(args.chain)
        except Exception as exc:
            section_errors.append({"section": "holdings", "code": "holdings_unavailable", "message": str(exc)})

        return ok(
            "Agent dashboard snapshot ready.",
            chain=args.chain,
            generatedAt=utc_now(),
            agentId=agent_id,
            profile=profile,
            holdings=holdings,
            pendingIntents=pending_intents,
            openOrders=open_orders,
            recentTrades=recent_trades,
            recentRoomMessages=recent_room_messages,
            sectionErrors=section_errors,
        )
    except WalletStoreError as exc:
        return fail("dashboard_failed", str(exc), "Verify API env/auth and retry dashboard.", {"chain": args.chain}, exit_code=1)
    except Exception as exc:
        return fail("dashboard_failed", str(exc), "Inspect runtime dashboard path and retry.", {"chain": args.chain}, exit_code=1)


def _sync_limit_orders(chain: str) -> tuple[int, int]:
    status_code, body = _api_request("GET", f"/limit-orders?chainKey={urllib.parse.quote(chain)}&status=open&limit=200")
    if status_code < 200 or status_code >= 300:
        code = str(body.get("code", "api_error"))
        message = str(body.get("message", f"limit-orders pending failed ({status_code})"))
        raise WalletStoreError(f"{code}: {message}")
    items = body.get("items", [])
    if not isinstance(items, list):
        raise WalletStoreError("Limit-order pending response 'items' is not a list.")
    orders = [item for item in items if isinstance(item, dict)]
    store = _default_limit_order_store()
    store["orders"] = orders
    save_limit_order_store(store)
    return len(orders), len([item for item in orders if str(item.get("status")) == "open"])


def _execute_limit_order_real(order: dict[str, Any], chain: str) -> str:
    store = load_wallet_store()
    wallet_address, private_key_hex = _execution_wallet(store, chain)
    cast_bin = _require_cast_bin()
    rpc_url = _chain_rpc_url(chain)
    router = _require_chain_contract_address(chain, "router")

    token_in = str(order.get("tokenIn") or "")
    token_out = str(order.get("tokenOut") or "")
    if not is_hex_address(token_in) or not is_hex_address(token_out):
        raise WalletStoreError("Limit-order tokenIn/tokenOut must be 0x addresses.")

    amount_wei_str = _to_wei_uint(str(order.get("amountIn") or "0"))
    amount_wei = int(amount_wei_str)
    state, day_key, current_spend, _ = _enforce_spend_preconditions(chain, amount_wei, enforce_native_cap=False)
    projected_spend_usd = _to_non_negative_decimal(order.get("amountIn") or "0")
    cap_state, _, current_spend_usd, current_filled_trades, _ = _enforce_trade_caps(chain, projected_spend_usd, 1)
    deadline = str(int(datetime.now(timezone.utc).timestamp()) + 120)

    approve_data = _cast_calldata("approve(address,uint256)(bool)", [router, amount_wei_str])
    approve_tx_hash = _cast_rpc_send_transaction(
        rpc_url,
        {
            "from": wallet_address,
            "to": token_in,
            "data": approve_data,
        },
        private_key_hex,
    )
    approve_receipt = _run_subprocess(
        [cast_bin, "receipt", "--json", "--rpc-url", rpc_url, approve_tx_hash],
        timeout_sec=_cast_receipt_timeout_sec(),
        kind="cast_receipt",
    )
    if approve_receipt.returncode != 0:
        stderr = (approve_receipt.stderr or "").strip()
        stdout = (approve_receipt.stdout or "").strip()
        raise WalletStoreError(stderr or stdout or "cast receipt failed for approve tx.")

    swap_data = _cast_calldata(
        "swapExactTokensForTokens(uint256,uint256,address[],address,uint256)(uint256[])",
        [amount_wei_str, "1", f"[{token_in},{token_out}]", wallet_address, deadline],
    )
    tx_hash = _cast_rpc_send_transaction(
        rpc_url,
        {
            "from": wallet_address,
            "to": router,
            "data": swap_data,
        },
        private_key_hex,
    )

    receipt_proc = _run_subprocess(
        [cast_bin, "receipt", "--json", "--rpc-url", rpc_url, tx_hash],
        timeout_sec=_cast_receipt_timeout_sec(),
        kind="cast_receipt",
    )
    if receipt_proc.returncode != 0:
        stderr = (receipt_proc.stderr or "").strip()
        stdout = (receipt_proc.stdout or "").strip()
        raise WalletStoreError(stderr or stdout or "cast receipt failed.")
    receipt_payload = json.loads((receipt_proc.stdout or "{}").strip() or "{}")
    receipt_status = str(receipt_payload.get("status", "0x0")).lower()
    if receipt_status not in {"0x1", "1"}:
        raise WalletStoreError(f"On-chain receipt indicates failure status '{receipt_status}'.")

    _record_spend(state, chain, day_key, current_spend + amount_wei)
    _record_trade_cap_ledger(
        cap_state,
        chain,
        day_key,
        current_spend_usd + projected_spend_usd,
        current_filled_trades + 1,
    )
    try:
        _post_trade_usage(chain, day_key, projected_spend_usd, 1)
    except Exception:
        pass
    return tx_hash


def cmd_limit_orders_create(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    try:
        if str(args.mode).strip().lower() == "mock":
            return fail(
                "unsupported_mode",
                "Mock mode is deprecated for limit orders.",
                "Use network mode (`real`) on base_sepolia.",
                {"mode": args.mode, "supportedMode": "real", "chain": args.chain},
                exit_code=1,
            )
        token_in = _resolve_token_address(args.chain, args.token_in)
        token_out = _resolve_token_address(args.chain, args.token_out)
        if not is_hex_address(token_in) or not is_hex_address(token_out):
            return fail("invalid_input", "token-in and token-out must be valid 0x addresses (or canonical symbols).", "Use symbols like WETH/USDC or 0x addresses.", {"tokenIn": args.token_in, "tokenOut": args.token_out}, exit_code=2)
        payload = {
            "schemaVersion": 1,
            "agentId": _resolve_agent_id(_resolve_api_key()),
            "chainKey": args.chain,
            "mode": args.mode,
            "side": args.side,
            "tokenIn": token_in,
            "tokenOut": token_out,
            "amountIn": args.amount_in,
            "limitPrice": args.limit_price,
            "slippageBps": int(args.slippage_bps),
        }
        if args.expires_at:
            payload["expiresAt"] = args.expires_at
        if not payload["agentId"]:
            return fail(
                "auth_invalid",
                "Agent id could not be resolved for limit-order create.",
                "Set XCLAW_AGENT_ID or use signed agent token format.",
                {"chain": args.chain},
                exit_code=1,
            )

        path = "/limit-orders"
        status_code, body = _api_request("POST", path, payload=payload, include_idempotency=True)
        if status_code < 200 or status_code >= 300:
            code = str(body.get("code", "api_error"))
            message = str(body.get("message", f"limit-order create failed ({status_code})"))
            return fail(code, message, str(body.get("actionHint", "Review payload and retry.")), _api_error_details(status_code, body, path, chain=args.chain), exit_code=1)
        return ok("Limit order created.", chain=args.chain, orderId=body.get("orderId"), status=body.get("status", "open"))
    except WalletStoreError as exc:
        return fail("limit_orders_create_failed", str(exc), "Verify API env/auth and retry.", {"chain": args.chain}, exit_code=1)
    except Exception as exc:
        return fail("limit_orders_create_failed", str(exc), "Inspect runtime limit-order create path and retry.", {"chain": args.chain}, exit_code=1)


def cmd_limit_orders_cancel(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    try:
        agent_id = _resolve_agent_id(_resolve_api_key())
        if not agent_id:
            return fail(
                "auth_invalid",
                "Agent id could not be resolved for limit-order cancel.",
                "Set XCLAW_AGENT_ID or use signed agent token format.",
                {"chain": args.chain},
                exit_code=1,
            )
        payload = {"schemaVersion": 1, "agentId": agent_id}
        status_code, body = _api_request("POST", f"/limit-orders/{args.order_id}/cancel", payload=payload, include_idempotency=True)
        if status_code < 200 or status_code >= 300:
            code = str(body.get("code", "api_error"))
            message = str(body.get("message", f"limit-order cancel failed ({status_code})"))
            return fail(code, message, str(body.get("actionHint", "Verify order id and retry.")), {"chain": args.chain}, exit_code=1)
        return ok("Limit order cancelled.", chain=args.chain, orderId=body.get("orderId"), status=body.get("status"))
    except WalletStoreError as exc:
        return fail("limit_orders_cancel_failed", str(exc), "Verify API env/auth and retry.", {"chain": args.chain}, exit_code=1)
    except Exception as exc:
        return fail("limit_orders_cancel_failed", str(exc), "Inspect runtime limit-order cancel path and retry.", {"chain": args.chain}, exit_code=1)


def cmd_limit_orders_list(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    try:
        query = f"/limit-orders?chainKey={urllib.parse.quote(args.chain)}&limit={int(args.limit)}"
        if args.status:
            query += f"&status={urllib.parse.quote(str(args.status))}"
        status_code, body = _api_request("GET", query)
        if status_code < 200 or status_code >= 300:
            code = str(body.get("code", "api_error"))
            message = str(body.get("message", f"limit-orders list failed ({status_code})"))
            raise WalletStoreError(f"{code}: {message}")
        items = body.get("items", [])
        if not isinstance(items, list):
            items = []
        return ok("Limit orders listed.", chain=args.chain, count=len(items), items=items)
    except WalletStoreError as exc:
        return fail("limit_orders_list_failed", str(exc), "Verify API env/auth and retry.", {"chain": args.chain}, exit_code=1)
    except Exception as exc:
        return fail("limit_orders_list_failed", str(exc), "Inspect runtime limit-order list path and retry.", {"chain": args.chain}, exit_code=1)


def cmd_limit_orders_sync(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    try:
        total, open_count = _sync_limit_orders(args.chain)
        return ok("Limit orders synced.", chain=args.chain, total=total, open=open_count)
    except WalletStoreError as exc:
        return fail("limit_orders_sync_failed", str(exc), "Verify API env/auth and retry.", {"chain": args.chain}, exit_code=1)
    except Exception as exc:
        return fail("limit_orders_sync_failed", str(exc), "Inspect runtime limit-order sync path and retry.", {"chain": args.chain}, exit_code=1)


def cmd_limit_orders_status(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    try:
        store = load_limit_order_store()
        orders = [entry for entry in store.get("orders", []) if isinstance(entry, dict)]
        by_status: dict[str, int] = {}
        for entry in orders:
            status = str(entry.get("status") or "unknown")
            by_status[status] = by_status.get(status, 0) + 1
        outbox = load_limit_order_outbox()
        return ok("Limit-order local state loaded.", chain=args.chain, count=len(orders), byStatus=by_status, outboxCount=len(outbox))
    except WalletStoreError as exc:
        return fail("limit_orders_status_failed", str(exc), "Repair local limit-order store metadata and retry.", {"chain": args.chain}, exit_code=1)
    except Exception as exc:
        return fail("limit_orders_status_failed", str(exc), "Inspect runtime limit-order status path and retry.", {"chain": args.chain}, exit_code=1)


def cmd_limit_orders_run_once(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk

    def _limit_orders_run_once_result(chain: str, sync: bool) -> dict[str, Any]:
        replayed, remaining = _replay_limit_order_outbox()
        # Best-effort: usage outbox replay should not block limit-order processing.
        try:
            trade_usage_replayed, trade_usage_remaining = _replay_trade_usage_outbox()
        except Exception:
            trade_usage_replayed, trade_usage_remaining = 0, 0
        synced = False
        if sync:
            _sync_limit_orders(chain)
            synced = True
        store = load_limit_order_store()
        orders = [entry for entry in store.get("orders", []) if isinstance(entry, dict)]
        executed = 0
        skipped = 0
        now = datetime.now(timezone.utc)
        for order in orders:
            if str(order.get("chainKey")) != chain:
                skipped += 1
                continue
            if str(order.get("status")) != "open":
                skipped += 1
                continue
            expires_at = order.get("expiresAt")
            if isinstance(expires_at, str) and expires_at:
                try:
                    expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                    if expiry <= now:
                        _post_limit_order_status(str(order.get("orderId")), {"status": "expired", "triggerAt": utc_now()})
                        skipped += 1
                        continue
                except Exception:
                    pass

            side = str(order.get("side") or "")
            limit_price = Decimal(str(order.get("limitPrice") or "0"))
            mode = str(order.get("mode") or "real")
            if mode != "real":
                _post_limit_order_status(
                    str(order.get("orderId")),
                    {
                        "status": "failed",
                        "triggerAt": utc_now(),
                        "reasonCode": "unsupported_mode",
                        "reasonMessage": "Mock mode is deprecated; network mode only."
                    },
                )
                skipped += 1
                continue
            current_price = _quote_router_price(chain, str(order.get("tokenIn")), str(order.get("tokenOut")))
            if not _limit_order_triggered(side, current_price, limit_price):
                skipped += 1
                continue

            order_id = str(order.get("orderId"))
            _post_limit_order_status(order_id, {"status": "triggered", "triggerPrice": str(current_price), "triggerAt": utc_now()})
            try:
                tx_hash = _execute_limit_order_real(order, chain)
                _post_limit_order_status(order_id, {"status": "filled", "triggerPrice": str(current_price), "triggerAt": utc_now(), "txHash": tx_hash})
                executed += 1
            except WalletPolicyError as exc:
                _post_limit_order_status(
                    order_id,
                    {
                        "status": "failed",
                        "triggerPrice": str(current_price),
                        "triggerAt": utc_now(),
                        "reasonCode": exc.code,
                        "reasonMessage": str(exc),
                    },
                )
            except WalletStoreError as exc:
                _post_limit_order_status(
                    order_id,
                    {
                        "status": "failed",
                        "triggerPrice": str(current_price),
                        "triggerAt": utc_now(),
                        "reasonCode": "rpc_unavailable",
                        "reasonMessage": str(exc),
                    },
                )

        return {
            "synced": synced,
            "replayed": replayed,
            "outboxRemaining": remaining,
            "tradeUsageReplayed": trade_usage_replayed,
            "tradeUsageOutboxRemaining": trade_usage_remaining,
            "executed": executed,
            "skipped": skipped,
        }

    try:
        result = _limit_orders_run_once_result(args.chain, bool(args.sync))
        return ok("Limit-order run completed.", chain=args.chain, **result)
    except WalletStoreError as exc:
        return fail("limit_orders_run_failed", str(exc), "Verify local wallet/policy/chain setup and retry.", {"chain": args.chain}, exit_code=1)
    except Exception as exc:
        return fail("limit_orders_run_failed", str(exc), "Inspect runtime limit-order loop and retry.", {"chain": args.chain}, exit_code=1)


def cmd_limit_orders_run_loop(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    iterations = int(args.iterations)
    interval_sec = int(args.interval_sec)
    if iterations < 0:
        return fail("invalid_input", "--iterations must be >= 0.", "Use 0 for infinite loop or positive count.", {"iterations": iterations}, exit_code=2)
    if iterations == 0:
        return fail(
            "invalid_input",
            "--iterations 0 (infinite loop) is not allowed in JSON skill mode.",
            "Provide --iterations >= 1 (or use run-once).",
            {"iterations": iterations},
            exit_code=2,
        )
    if interval_sec < 1:
        return fail("invalid_input", "--interval-sec must be >= 1.", "Provide interval in seconds >= 1.", {"intervalSec": interval_sec}, exit_code=2)

    completed = 0
    totals = {"executed": 0, "skipped": 0, "replayed": 0}
    last_run: dict[str, Any] | None = None
    try:
        while True:
            nested = argparse.Namespace(chain=args.chain, json=True, sync=args.sync)
            # Call the underlying handler directly to keep output single-JSON.
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = cmd_limit_orders_run_once(nested)
            if code != 0:
                # cmd_limit_orders_run_once already emitted a structured JSON error; forward it.
                print(buf.getvalue().strip())
                return code
            run_payload = json.loads(buf.getvalue().strip() or "{}")
            if not isinstance(run_payload, dict):
                return fail("limit_orders_run_failed", "Unexpected run-once output shape.", "Inspect runtime output and retry.", {"chain": args.chain}, exit_code=1)
            last_run = run_payload
            totals["executed"] += int(run_payload.get("executed") or 0)
            totals["skipped"] += int(run_payload.get("skipped") or 0)
            totals["replayed"] += int(run_payload.get("replayed") or 0)
            completed += 1
            if iterations > 0 and completed >= iterations:
                break
            time.sleep(interval_sec)
        return ok(
            "Limit-order loop finished.",
            chain=args.chain,
            iterations=completed,
            intervalSec=interval_sec,
            totals=totals,
            lastRun=last_run,
        )
    except KeyboardInterrupt:
        return ok("Limit-order loop interrupted.", chain=args.chain, iterations=completed, interrupted=True, totals=totals, lastRun=last_run)


def cmd_wallet_health(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk

    chain = args.chain
    has_wallet = False
    address: str | None = None
    metadata_valid = True
    permission_safe = True
    integrity_checked = False

    try:
        ensure_app_dir()
        _assert_secure_permissions(APP_DIR, 0o700, "directory")
        if STATE_FILE.exists():
            _assert_secure_permissions(STATE_FILE, 0o600, "state file")
        if WALLET_STORE_FILE.exists():
            _assert_secure_permissions(WALLET_STORE_FILE, 0o600, "wallet store file")

        store = load_wallet_store()
        wallet_id, wallet = _chain_wallet(store, chain)
        if wallet_id:
            if wallet is None:
                raise WalletStoreError(f"Chain '{chain}' points to missing wallet id '{wallet_id}'.")
            _validate_wallet_entry_shape(wallet)
            has_wallet = True
            address = wallet.get("address")

            probe_passphrase = os.environ.get("XCLAW_WALLET_PASSPHRASE")
            if probe_passphrase:
                plaintext = _decrypt_private_key(wallet, probe_passphrase)
                derived = _derive_address(plaintext.hex())
                if derived.lower() != str(address).lower():
                    raise WalletStoreError("Wallet encrypted payload does not match stored address.")
                integrity_checked = True
        else:
            # Legacy fallback for Slice 03 state shape.
            _, legacy_wallet = ensure_wallet_entry(chain)
            legacy_address = legacy_wallet.get("address")
            if isinstance(legacy_address, str) and is_hex_address(legacy_address):
                has_wallet = True
                address = legacy_address

    except WalletSecurityError as exc:
        permission_safe = False
        return fail("unsafe_permissions", str(exc), "Restrict permissions to owner-only (0700/0600) and retry.", {"chain": chain}, exit_code=1)
    except WalletStoreError as exc:
        metadata_valid = False
        return fail("wallet_store_invalid", str(exc), "Repair or remove invalid wallet metadata and retry.", {"chain": chain}, exit_code=1)
    except Exception as exc:
        metadata_valid = False
        return fail("wallet_health_failed", str(exc), "Inspect wallet files and retry wallet health.", {"chain": chain}, exit_code=1)

    has_cast = cast_exists()
    next_action = "No action needed."
    if not has_cast:
        next_action = "Install Foundry so `cast` is available, then rerun wallet-health."
    elif not has_wallet:
        next_action = "Wallet not found. Re-run hosted installer/bootstrap (wallet creation is installer-managed), then rerun wallet-health."
    elif not permission_safe or not metadata_valid:
        next_action = "Fix wallet metadata/permissions per message, then rerun wallet-health."
    elif not integrity_checked:
        next_action = "Integrity check skipped (no passphrase provided). If available, set XCLAW_WALLET_PASSPHRASE to enable deeper verification; do not share it."

    return ok(
        "Wallet health checked.",
        chain=chain,
        hasCast=has_cast,
        hasWallet=has_wallet,
        address=address,
        metadataValid=metadata_valid,
        filePermissionsSafe=permission_safe,
        integrityChecked=integrity_checked,
        actionHint=next_action,
        nextAction=next_action,
        timestamp=utc_now(),
    )


def cmd_wallet_create(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk

    try:
        passphrase = _create_import_passphrase(args.chain)
        store = load_wallet_store()

        chain = args.chain
        wallet_id, wallet = _chain_wallet(store, chain)
        if wallet_id and wallet:
            return fail(
                "wallet_exists",
                f"Wallet already configured for chain '{chain}'.",
                "Use wallet address/health or wallet remove before creating again.",
                {"chain": chain, "address": wallet.get("address")},
                exit_code=1,
            )

        default_wallet_id = store.get("defaultWalletId")
        if isinstance(default_wallet_id, str) and default_wallet_id:
            default_wallet = store.setdefault("wallets", {}).get(default_wallet_id)
            if not isinstance(default_wallet, dict):
                raise WalletStoreError("defaultWalletId points to a missing wallet record.")
            _validate_wallet_entry_shape(default_wallet)
            _bind_chain_to_wallet(store, chain, default_wallet_id)
            save_wallet_store(store)
            set_wallet_entry(chain, {"address": default_wallet.get("address"), "walletId": default_wallet_id})
            return ok("Existing portable wallet bound to chain.", chain=chain, address=default_wallet.get("address"), created=False)

        private_key = ec.generate_private_key(ec.SECP256K1())
        private_value = private_key.private_numbers().private_value
        private_key_hex = private_value.to_bytes(32, "big").hex()
        address = _derive_address(private_key_hex)

        wallet_id = _new_wallet_id()
        encrypted = _encrypt_private_key(private_key_hex, passphrase)
        store.setdefault("wallets", {})[wallet_id] = {
            "walletId": wallet_id,
            "address": address,
            "createdAt": utc_now(),
            "crypto": encrypted,
        }
        store["defaultWalletId"] = wallet_id
        _bind_chain_to_wallet(store, chain, wallet_id)

        save_wallet_store(store)
        set_wallet_entry(chain, {"address": address, "walletId": wallet_id})
        return ok("Wallet created.", chain=chain, address=address, created=True)

    except WalletPassphraseError as exc:
        return fail("non_interactive", str(exc), "Set XCLAW_WALLET_PASSPHRASE or run with TTY attached.", {"chain": args.chain}, exit_code=2)
    except ValueError as exc:
        return fail("invalid_input", str(exc), "Provide matching non-empty passphrase values.", {"chain": args.chain}, exit_code=2)
    except WalletSecurityError as exc:
        return fail("unsafe_permissions", str(exc), "Restrict permissions to owner-only (0700/0600) and retry.", {"chain": args.chain}, exit_code=1)
    except WalletStoreError as exc:
        return fail("wallet_store_invalid", str(exc), "Repair wallet store metadata and retry.", {"chain": args.chain}, exit_code=1)
    except Exception as exc:
        return fail("wallet_create_failed", str(exc), "Inspect runtime wallet dependencies/configuration and retry.", {"chain": args.chain}, exit_code=1)


def cmd_wallet_import(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk

    try:
        private_key_input = _import_private_key_input(args.chain)
        private_key_hex = _normalize_private_key_hex(private_key_input)
        if private_key_hex is None:
            return fail(
                "invalid_input",
                "Private key must be 32-byte hex (64 chars, optional 0x prefix).",
                "Provide a valid EVM private key hex string.",
                {"chain": args.chain},
                exit_code=2,
            )

        address = _derive_address(private_key_hex)
        passphrase = _create_import_passphrase(args.chain)

        store = load_wallet_store()
        chain = args.chain
        existing_id, existing_wallet = _chain_wallet(store, chain)
        if existing_id and existing_wallet:
            return fail(
                "wallet_exists",
                f"Wallet already configured for chain '{chain}'.",
                "Use wallet remove first if you want to replace the chain binding.",
                {"chain": chain, "address": existing_wallet.get("address")},
                exit_code=1,
            )

        default_wallet_id = store.get("defaultWalletId")
        if isinstance(default_wallet_id, str) and default_wallet_id:
            default_wallet = store.setdefault("wallets", {}).get(default_wallet_id)
            if not isinstance(default_wallet, dict):
                raise WalletStoreError("defaultWalletId points to a missing wallet record.")
            _validate_wallet_entry_shape(default_wallet)
            default_address = str(default_wallet.get("address", "")).lower()
            if default_address != address.lower():
                return fail(
                    "portable_wallet_conflict",
                    "Imported private key does not match existing portable default wallet.",
                    "Import the same portable key or remove existing wallet bindings first.",
                    {"chain": chain, "existingAddress": default_wallet.get("address"), "importAddress": address},
                    exit_code=1,
                )
            _bind_chain_to_wallet(store, chain, default_wallet_id)
            save_wallet_store(store)
            set_wallet_entry(chain, {"address": default_wallet.get("address"), "walletId": default_wallet_id})
            return ok("Portable wallet bound to chain.", chain=chain, address=default_wallet.get("address"), imported=True)

        wallet_id = _new_wallet_id()
        encrypted = _encrypt_private_key(private_key_hex, passphrase)
        store.setdefault("wallets", {})[wallet_id] = {
            "walletId": wallet_id,
            "address": address,
            "createdAt": utc_now(),
            "crypto": encrypted,
        }
        store["defaultWalletId"] = wallet_id
        _bind_chain_to_wallet(store, chain, wallet_id)

        save_wallet_store(store)
        set_wallet_entry(chain, {"address": address, "walletId": wallet_id})
        return ok("Wallet imported.", chain=chain, address=address, imported=True)

    except WalletPassphraseError as exc:
        return fail("non_interactive", str(exc), "Set XCLAW_WALLET_PASSPHRASE/XCLAW_WALLET_IMPORT_PRIVATE_KEY or run with TTY attached.", {"chain": args.chain}, exit_code=2)
    except ValueError as exc:
        return fail("invalid_input", str(exc), "Provide matching non-empty passphrase values.", {"chain": args.chain}, exit_code=2)
    except WalletSecurityError as exc:
        return fail("unsafe_permissions", str(exc), "Restrict permissions to owner-only (0700/0600) and retry.", {"chain": args.chain}, exit_code=1)
    except WalletStoreError as exc:
        return fail("wallet_store_invalid", str(exc), "Repair wallet store metadata and retry.", {"chain": args.chain}, exit_code=1)
    except Exception as exc:
        return fail("wallet_import_failed", str(exc), "Inspect runtime wallet dependencies/configuration and retry.", {"chain": args.chain}, exit_code=1)


def cmd_wallet_address(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk

    chain = args.chain
    try:
        store = load_wallet_store()
        _, wallet = _chain_wallet(store, chain)
        if wallet:
            address = wallet.get("address")
            if isinstance(address, str) and is_hex_address(address):
                return ok("Wallet address fetched.", chain=chain, address=address)

    except (WalletStoreError, WalletSecurityError) as exc:
        return fail("wallet_store_invalid", str(exc), "Repair wallet store metadata and retry.", {"chain": chain}, exit_code=1)

    _, legacy_wallet = ensure_wallet_entry(chain)
    addr = legacy_wallet.get("address")
    if not isinstance(addr, str) or not is_hex_address(addr):
        return fail(
            "wallet_missing",
            f"No wallet configured for chain '{chain}'.",
            "Run hosted bootstrap installer to initialize wallet.",
            {"chain": chain},
            exit_code=1,
        )
    return ok("Wallet address fetched.", chain=chain, address=addr)


def cmd_wallet_sign_challenge(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    if not args.message.strip():
        return fail(
            "invalid_input",
            "Challenge message cannot be empty.",
            "Provide a non-empty message string.",
            {"message": args.message},
            exit_code=2,
        )
    chain = args.chain
    try:
        store = load_wallet_store()
        _, wallet = _chain_wallet(store, chain)
        if wallet:
            _validate_wallet_entry_shape(wallet)
        else:
            return fail(
                "wallet_missing",
                f"No wallet configured for chain '{chain}'.",
                "Run hosted bootstrap installer to initialize wallet.",
                {"chain": chain},
                exit_code=1,
            )

        try:
            _parse_canonical_challenge(args.message, chain)
        except ValueError as exc:
            return fail(
                "invalid_challenge_format",
                str(exc),
                "Provide canonical challenge lines: domain, chain, nonce, timestamp, action.",
                {"format": CHALLENGE_FORMAT_VERSION, "chain": chain},
                exit_code=2,
            )

        passphrase = _require_wallet_passphrase_for_signing(chain)
        private_key_bytes = _decrypt_private_key(wallet, passphrase)
        signature = _cast_sign_message(private_key_bytes.hex(), args.message)
        return ok(
            "Challenge signed.",
            chain=chain,
            address=wallet.get("address"),
            signature=signature,
            scheme="eip191_personal_sign",
            challengeFormat=CHALLENGE_FORMAT_VERSION,
        )

    except WalletPassphraseError as exc:
        return fail("non_interactive", str(exc), "Set XCLAW_WALLET_PASSPHRASE or run with TTY attached.", {"chain": chain}, exit_code=2)
    except WalletSecurityError as exc:
        return fail("unsafe_permissions", str(exc), "Restrict permissions to owner-only (0700/0600) and retry.", {"chain": chain}, exit_code=1)
    except WalletStoreError as exc:
        msg = str(exc)
        if "Missing dependency: cast" in msg:
            return fail(
                "missing_dependency",
                msg,
                "Install Foundry and ensure `cast` is on PATH.",
                {"dependency": "cast"},
                exit_code=1,
            )
        return fail("sign_failed", msg, "Verify wallet passphrase and cast runtime, then retry.", {"chain": chain}, exit_code=1)
    except Exception as exc:
        return fail("sign_failed", str(exc), "Inspect runtime wallet/signing configuration and retry.", {"chain": chain}, exit_code=1)


def cmd_wallet_send(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    if not is_hex_address(args.to):
        return fail("invalid_input", "Invalid recipient address format.", "Use 0x-prefixed 20-byte hex address.", {"to": args.to}, exit_code=2)
    if not re.fullmatch(r"[0-9]+", args.amount_wei):
        return fail("invalid_input", "Invalid amount-wei format.", "Use base-unit integer string.", {"amountWei": args.amount_wei}, exit_code=2)

    chain = args.chain
    amount_wei = int(args.amount_wei)
    try:
        _enforce_spend_preconditions(chain, amount_wei)
        outbound_eval = _evaluate_outbound_transfer_policy(chain, args.to)

        approval_required, transfer_policy = _transfer_requires_approval(chain, "native", None)
        amount_human, amount_unit = _transfer_amount_display(str(args.amount_wei), "native", "ETH", 18)
        amount_display = f"{amount_human} {amount_unit}"
        if not bool(outbound_eval.get("allowed")):
            approval_required = True
        approval_id = _make_transfer_approval_id()
        flow = {
            "approvalId": approval_id,
            "chainKey": chain,
            "status": "approval_pending" if approval_required else "approved",
            "transferType": "native",
            "tokenAddress": None,
            "tokenSymbol": "ETH",
            "tokenDecimals": 18,
            "toAddress": args.to.lower(),
            "amountWei": str(args.amount_wei),
            "reasonCode": None,
            "reasonMessage": None,
            "createdAt": utc_now(),
            "updatedAt": utc_now(),
            "transferPolicy": transfer_policy,
            "policyBlockedAtCreate": bool(outbound_eval.get("policyBlockedAtCreate", False)),
            "policyBlockReasonCode": outbound_eval.get("policyBlockReasonCode"),
            "policyBlockReasonMessage": outbound_eval.get("policyBlockReasonMessage"),
            "executionMode": None,
        }
        _record_pending_transfer_flow(approval_id, flow)
        _mirror_transfer_approval(flow)

        if approval_required:
            queued_message = (
                "Approval required (transfer)\n\n"
                "Request: Send native token\n"
                f"Amount: {amount_display} ({args.amount_wei} wei)\n"
                f"To: {args.to.lower()}\n"
                f"Chain: {chain}\n"
                f"Approval ID: {approval_id}\n"
                "Status: approval_pending\n\n"
                "Tap Approve or Deny."
            )
            if bool(outbound_eval.get("policyBlockedAtCreate")):
                queued_message += (
                    f"\n\nPolicy blocked at create: {str(outbound_eval.get('policyBlockReasonCode') or 'unknown')}"
                    "\nApprove to execute this transfer as a one-off override."
                )
            return fail(
                "approval_required",
                "Transfer is waiting for management approval.",
                "Send queuedMessage verbatim so Telegram buttons can attach, then wait for Approve/Deny.",
                {
                    "approvalId": approval_id,
                    "chain": chain,
                    "status": "approval_pending",
                    "queuedMessage": queued_message,
                    "amount": amount_human,
                    "amountUnit": amount_unit,
                    "amountDisplay": amount_display,
                    "nextAction": "Post queuedMessage verbatim to the user in the active chat.",
                    "policyBlockedAtCreate": bool(outbound_eval.get("policyBlockedAtCreate", False)),
                    "policyBlockReasonCode": outbound_eval.get("policyBlockReasonCode"),
                    "policyBlockReasonMessage": outbound_eval.get("policyBlockReasonMessage"),
                },
                exit_code=1,
            )

        return emit(_execute_pending_transfer_flow(flow))
    except WalletPolicyError as exc:
        return fail(exc.code, str(exc), exc.action_hint, exc.details, exit_code=1)
    except WalletPassphraseError as exc:
        return fail("non_interactive", str(exc), "Set XCLAW_WALLET_PASSPHRASE or run with TTY attached.", {"chain": chain}, exit_code=2)
    except WalletSecurityError as exc:
        return fail("unsafe_permissions", str(exc), "Restrict permissions to owner-only (0700/0600) and retry.", {"chain": chain}, exit_code=1)
    except WalletStoreError as exc:
        msg = str(exc)
        if "Missing dependency: cast" in msg:
            return fail(
                "missing_dependency",
                msg,
                "Install Foundry and ensure `cast` is on PATH.",
                {"dependency": "cast"},
                exit_code=1,
            )
        if "Chain config" in msg:
            return fail("chain_config_invalid", msg, "Repair config/chains/<chain>.json and retry.", {"chain": chain}, exit_code=1)
        return fail("send_failed", msg, "Verify wallet passphrase, policy, RPC connectivity, and retry.", {"chain": chain}, exit_code=1)
    except Exception as exc:
        return fail("send_failed", str(exc), "Inspect runtime send configuration and retry.", {"chain": chain}, exit_code=1)


def cmd_wallet_send_token(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    if not is_hex_address(args.to):
        return fail("invalid_input", "Invalid recipient address format.", "Use 0x-prefixed 20-byte hex address.", {"to": args.to}, exit_code=2)
    if not is_hex_address(args.token):
        return fail("invalid_input", "Invalid token address format.", "Use 0x-prefixed 20-byte hex address.", {"token": args.token}, exit_code=2)
    if not re.fullmatch(r"[0-9]+", args.amount_wei):
        return fail("invalid_input", "Invalid amount-wei format.", "Use base-unit integer string.", {"amountWei": args.amount_wei}, exit_code=2)

    chain = args.chain
    amount_wei = int(args.amount_wei)
    try:
        _enforce_spend_preconditions(chain, amount_wei)
        outbound_eval = _evaluate_outbound_transfer_policy(chain, args.to)

        token_meta = _fetch_erc20_metadata(chain, args.token)
        token_symbol = str(token_meta.get("symbol") or "").strip() or "TOKEN"
        try:
            token_decimals = int(token_meta.get("decimals", 18))
        except Exception:
            token_decimals = 18
        amount_human, amount_unit = _transfer_amount_display(str(args.amount_wei), "token", token_symbol, token_decimals)
        amount_display = f"{amount_human} {amount_unit}"
        approval_required, transfer_policy = _transfer_requires_approval(chain, "token", args.token)
        if not bool(outbound_eval.get("allowed")):
            approval_required = True
        approval_id = _make_transfer_approval_id()
        flow = {
            "approvalId": approval_id,
            "chainKey": chain,
            "status": "approval_pending" if approval_required else "approved",
            "transferType": "token",
            "tokenAddress": args.token.lower(),
            "tokenSymbol": token_symbol,
            "tokenDecimals": token_decimals,
            "toAddress": args.to.lower(),
            "amountWei": str(args.amount_wei),
            "reasonCode": None,
            "reasonMessage": None,
            "createdAt": utc_now(),
            "updatedAt": utc_now(),
            "transferPolicy": transfer_policy,
            "policyBlockedAtCreate": bool(outbound_eval.get("policyBlockedAtCreate", False)),
            "policyBlockReasonCode": outbound_eval.get("policyBlockReasonCode"),
            "policyBlockReasonMessage": outbound_eval.get("policyBlockReasonMessage"),
            "executionMode": None,
        }
        _record_pending_transfer_flow(approval_id, flow)
        _mirror_transfer_approval(flow)

        if approval_required:
            queued_message = (
                "Approval required (transfer)\n\n"
                "Request: Send token\n"
                f"Token: {token_symbol} ({args.token.lower()})\n"
                f"Amount: {amount_display} ({args.amount_wei} wei)\n"
                f"To: {args.to.lower()}\n"
                f"Chain: {chain}\n"
                f"Approval ID: {approval_id}\n"
                "Status: approval_pending\n\n"
                "Tap Approve or Deny."
            )
            if bool(outbound_eval.get("policyBlockedAtCreate")):
                queued_message += (
                    f"\n\nPolicy blocked at create: {str(outbound_eval.get('policyBlockReasonCode') or 'unknown')}"
                    "\nApprove to execute this transfer as a one-off override."
                )
            return fail(
                "approval_required",
                "Transfer is waiting for management approval.",
                "Send queuedMessage verbatim so Telegram buttons can attach, then wait for Approve/Deny.",
                {
                    "approvalId": approval_id,
                    "chain": chain,
                    "status": "approval_pending",
                    "queuedMessage": queued_message,
                    "amount": amount_human,
                    "amountUnit": amount_unit,
                    "amountDisplay": amount_display,
                    "nextAction": "Post queuedMessage verbatim to the user in the active chat.",
                    "policyBlockedAtCreate": bool(outbound_eval.get("policyBlockedAtCreate", False)),
                    "policyBlockReasonCode": outbound_eval.get("policyBlockReasonCode"),
                    "policyBlockReasonMessage": outbound_eval.get("policyBlockReasonMessage"),
                },
                exit_code=1,
            )

        return emit(_execute_pending_transfer_flow(flow))
    except WalletPolicyError as exc:
        return fail(exc.code, str(exc), exc.action_hint, exc.details, exit_code=1)
    except WalletPassphraseError as exc:
        return fail("non_interactive", str(exc), "Set XCLAW_WALLET_PASSPHRASE or run with TTY attached.", {"chain": chain}, exit_code=2)
    except WalletSecurityError as exc:
        return fail("unsafe_permissions", str(exc), "Restrict permissions to owner-only (0700/0600) and retry.", {"chain": chain}, exit_code=1)
    except WalletStoreError as exc:
        msg = str(exc)
        if "Missing dependency: cast" in msg:
            return fail(
                "missing_dependency",
                msg,
                "Install Foundry and ensure `cast` is on PATH.",
                {"dependency": "cast"},
                exit_code=1,
            )
        if "Chain config" in msg:
            return fail("chain_config_invalid", msg, "Repair config/chains/<chain>.json and retry.", {"chain": chain}, exit_code=1)
        return fail("send_failed", msg, "Verify wallet passphrase, policy, RPC connectivity, and retry.", {"chain": chain}, exit_code=1)
    except Exception as exc:
        return fail("send_failed", str(exc), "Inspect runtime token-send configuration and retry.", {"chain": chain}, exit_code=1)


def cmd_wallet_balance(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    chain = args.chain
    try:
        store = load_wallet_store()
        _, wallet = _chain_wallet(store, chain)
        if wallet is None:
            return fail(
                "wallet_missing",
                f"No wallet configured for chain '{chain}'.",
                "Run hosted bootstrap installer to initialize wallet.",
                {"chain": chain},
                exit_code=1,
            )
        _validate_wallet_entry_shape(wallet)
        address = str(wallet.get("address"))
        cast_bin = _require_cast_bin()
        rpc_url = _chain_rpc_url(chain)
        proc = _run_subprocess(
            [cast_bin, "balance", address, "--rpc-url", rpc_url],
            timeout_sec=_cast_call_timeout_sec(),
            kind="cast_call",
        )
        if proc.returncode != 0:
            stderr = (proc.stderr or "").strip()
            stdout = (proc.stdout or "").strip()
            raise WalletStoreError(stderr or stdout or "cast balance failed.")
        output = (proc.stdout or "").strip().splitlines()
        parsed = _parse_uint_text(output[-1] if output else "")
        return ok(
            "Wallet balance fetched.",
            chain=chain,
            address=address,
            balanceWei=str(parsed),
            balanceEth=_format_units(int(parsed), 18),
            decimals=18,
            symbol="ETH",
        )
    except WalletSecurityError as exc:
        return fail("unsafe_permissions", str(exc), "Restrict permissions to owner-only (0700/0600) and retry.", {"chain": chain}, exit_code=1)
    except WalletStoreError as exc:
        msg = str(exc)
        if "Missing dependency: cast" in msg:
            return fail(
                "missing_dependency",
                msg,
                "Install Foundry and ensure `cast` is on PATH.",
                {"dependency": "cast"},
                exit_code=1,
            )
        if "Chain config" in msg:
            return fail("chain_config_invalid", msg, "Repair config/chains/<chain>.json and retry.", {"chain": chain}, exit_code=1)
        return fail("balance_failed", msg, "Verify wallet and RPC connectivity, then retry.", {"chain": chain}, exit_code=1)
    except Exception as exc:
        return fail("balance_failed", str(exc), "Inspect runtime balance configuration and retry.", {"chain": chain}, exit_code=1)


def cmd_wallet_token_balance(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    if not is_hex_address(args.token):
        return fail("invalid_input", "Invalid token address format.", "Use 0x-prefixed 20-byte hex address.", {"token": args.token}, exit_code=2)
    chain = args.chain
    try:
        store = load_wallet_store()
        _, wallet = _chain_wallet(store, chain)
        if wallet is None:
            return fail(
                "wallet_missing",
                f"No wallet configured for chain '{chain}'.",
                "Run hosted bootstrap installer to initialize wallet.",
                {"chain": chain},
                exit_code=1,
            )
        _validate_wallet_entry_shape(wallet)
        address = str(wallet.get("address"))
        cast_bin = _require_cast_bin()
        rpc_url = _chain_rpc_url(chain)
        proc = _run_subprocess(
            [cast_bin, "call", args.token, "balanceOf(address)(uint256)", address, "--rpc-url", rpc_url],
            timeout_sec=_cast_call_timeout_sec(),
            kind="cast_call",
        )
        if proc.returncode != 0:
            stderr = (proc.stderr or "").strip()
            stdout = (proc.stdout or "").strip()
            raise WalletStoreError(stderr or stdout or "cast call balanceOf failed.")
        output = (proc.stdout or "").strip().splitlines()
        parsed = _parse_uint_text(output[-1] if output else "")
        meta = _fetch_erc20_metadata(chain, args.token)
        decimals = int(meta.get("decimals", 18))
        symbol = str(meta.get("symbol") or "")
        return ok(
            "Wallet token balance fetched.",
            chain=chain,
            address=address,
            token=args.token,
            balanceWei=str(parsed),
            balance=_format_units(int(parsed), decimals),
            decimals=decimals,
            symbol=symbol or None,
        )
    except WalletSecurityError as exc:
        return fail("unsafe_permissions", str(exc), "Restrict permissions to owner-only (0700/0600) and retry.", {"chain": chain}, exit_code=1)
    except WalletStoreError as exc:
        msg = str(exc)
        if "Missing dependency: cast" in msg:
            return fail(
                "missing_dependency",
                msg,
                "Install Foundry and ensure `cast` is on PATH.",
                {"dependency": "cast"},
                exit_code=1,
            )
        if "Chain config" in msg:
            return fail("chain_config_invalid", msg, "Repair config/chains/<chain>.json and retry.", {"chain": chain}, exit_code=1)
        return fail("token_balance_failed", msg, "Verify wallet, token, and RPC connectivity, then retry.", {"chain": chain, "token": args.token}, exit_code=1)
    except Exception as exc:
        return fail("token_balance_failed", str(exc), "Inspect runtime token balance configuration and retry.", {"chain": chain, "token": args.token}, exit_code=1)


def cmd_wallet_remove(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    existed = remove_wallet_entry(args.chain)
    return ok("Wallet removed." if existed else "No wallet existed for chain.", chain=args.chain, removed=existed)


def cmd_x402_receive_request(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    network = str(args.network or "").strip()
    facilitator = str(args.facilitator or "").strip()
    amount_atomic = str(args.amount_atomic or "").strip()
    if not network:
        return fail("invalid_input", "network is required.", "Provide --network and retry.", exit_code=2)
    if not facilitator:
        return fail("invalid_input", "facilitator is required.", "Provide --facilitator and retry.", exit_code=2)
    if not amount_atomic:
        return fail("invalid_input", "amount_atomic is required.", "Provide --amount-atomic and retry.", exit_code=2)
    try:
        amount = Decimal(amount_atomic)
    except Exception:
        return fail("invalid_input", "amount_atomic must be numeric.", "Use values like 0.01 or 1.", exit_code=2)
    if amount <= 0:
        return fail("invalid_input", "amount_atomic must be > 0.", "Use values like 0.01 or 1.", exit_code=2)

    asset_kind = str(args.asset_kind or "native").strip().lower()
    if asset_kind not in {"native", "erc20"}:
        return fail("invalid_input", "asset_kind must be native|erc20.", "Use --asset-kind native or --asset-kind erc20.", exit_code=2)
    asset_symbol = str(args.asset_symbol or "").strip()
    asset_address = str(args.asset_address or "").strip().lower() or None
    if asset_kind == "erc20" and not asset_symbol and not asset_address:
        return fail(
            "invalid_input",
            "ERC-20 receive requests require asset symbol or asset address.",
            "Set --asset-symbol USDC|WETH (or --asset-address 0x...).",
            exit_code=2,
        )

    payload = {
        "schemaVersion": 1,
        "networkKey": network,
        "facilitatorKey": facilitator,
        "assetKind": asset_kind,
        "assetAddress": asset_address,
        "assetSymbol": asset_symbol or None,
        "amountAtomic": format(amount, "f"),
    }
    try:
        status_code, body = _api_request("POST", "/agent/x402/inbound/proposed", payload=payload, include_idempotency=True)
        if status_code < 200 or status_code >= 300:
            return fail(
                str(body.get("code", "api_error")),
                str(body.get("message", f"x402 receive request failed ({status_code})")),
                str(body.get("actionHint", "Verify x402 receive request inputs and retry.")),
                _api_error_details(status_code, body, "/agent/x402/inbound/proposed", network=network),
                exit_code=1,
            )
        return ok(
            "Hosted x402 receive request created.",
            paymentId=body.get("paymentId"),
            paymentUrl=body.get("paymentUrl"),
            network=body.get("networkKey", network),
            facilitator=body.get("facilitatorKey", facilitator),
            assetKind=body.get("assetKind", asset_kind),
            assetAddress=body.get("assetAddress"),
            assetSymbol=body.get("assetSymbol"),
            amountAtomic=body.get("amountAtomic", format(amount, "f")),
            status=body.get("status"),
            timeLimitNotice=body.get("timeLimitNotice"),
            requestSource="hosted",
        )
    except WalletStoreError as exc:
        return fail("x402_receive_request_failed", str(exc), "Verify API env/auth and retry.", {"network": network}, exit_code=1)
    except Exception as exc:
        return fail("x402_receive_request_failed", str(exc), "Inspect hosted x402 receive flow and retry.", {"network": network}, exit_code=1)


def cmd_x402_pay(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    try:
        payload = x402_pay_create_or_execute(
            url=str(args.url or "").strip(),
            network=str(args.network or "").strip(),
            facilitator=str(args.facilitator or "").strip(),
            amount_atomic=str(args.amount_atomic or "").strip(),
            memo=str(args.memo or "").strip() or None,
        )
        if not bool(payload.get("ok", False)):
            emit(payload)
            return 1
        approval = payload.get("approval")
        if isinstance(approval, dict):
            _mirror_x402_outbound(approval)
        return emit(payload)
    except X402RuntimeError as exc:
        return fail("x402_runtime_error", str(exc), "Verify x402 pay inputs and retry.", exit_code=1)
    except Exception as exc:
        return fail("x402_runtime_error", str(exc), "Inspect runtime x402 pay flow and retry.", exit_code=1)


def cmd_x402_pay_resume(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    approval_id = str(args.approval_id or "").strip()
    if not approval_id:
        return fail("invalid_input", "approval_id is required.", "Provide --approval-id xfr_... and retry.", exit_code=2)
    try:
        payload = x402_pay_resume(approval_id)
        if isinstance(payload, dict):
            _mirror_x402_outbound(payload)
        return ok("x402 payment resume processed.", approval=payload)
    except X402RuntimeError as exc:
        return fail("x402_runtime_error", str(exc), "Use a valid pending approved xfr_... id and retry.", exit_code=1)
    except Exception as exc:
        return fail("x402_runtime_error", str(exc), "Inspect runtime x402 pay resume flow and retry.", exit_code=1)


def cmd_x402_pay_decide(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    approval_id = str(args.approval_id or "").strip()
    decision = str(args.decision or "").strip().lower()
    if not approval_id:
        return fail("invalid_input", "approval_id is required.", "Provide --approval-id xfr_... and retry.", exit_code=2)
    if decision not in {"approve", "deny"}:
        return fail("invalid_input", "decision must be approve|deny.", "Use --decision approve or --decision deny.", exit_code=2)
    try:
        payload = x402_pay_decide(approval_id, decision, str(args.reason_message or "").strip() or None)
        if isinstance(payload, dict):
            _mirror_x402_outbound(payload)
        return ok("x402 payment decision applied.", approval=payload)
    except X402RuntimeError as exc:
        return fail("x402_runtime_error", str(exc), "Use a valid pending xfr_... id and retry.", exit_code=1)
    except Exception as exc:
        return fail("x402_runtime_error", str(exc), "Inspect runtime x402 pay decision flow and retry.", exit_code=1)


def cmd_x402_policy_get(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    network = str(args.network or "").strip()
    if not network:
        return fail("invalid_input", "network is required.", "Provide --network and retry.", exit_code=2)
    try:
        policy = x402_get_policy(network)
        return ok("x402 pay policy loaded.", network=network, x402Policy=policy)
    except Exception as exc:
        return fail("x402_runtime_error", str(exc), "Inspect x402 pay policy state and retry.", exit_code=1)


def cmd_x402_policy_set(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    network = str(args.network or "").strip()
    mode = str(args.mode or "").strip().lower()
    if not network:
        return fail("invalid_input", "network is required.", "Provide --network and retry.", exit_code=2)
    if mode not in {"auto", "per_payment"}:
        return fail("invalid_input", "mode must be auto|per_payment.", "Use --mode auto or --mode per_payment.", exit_code=2)
    allowed_hosts: list[str] = []
    for host in list(args.allowed_host or []):
        if not isinstance(host, str):
            continue
        normalized = host.strip().lower()
        if normalized:
            allowed_hosts.append(normalized)
    payload = {
        "payApprovalMode": mode,
        "maxAmountAtomic": str(args.max_amount_atomic).strip() if args.max_amount_atomic is not None else None,
        "allowedHosts": allowed_hosts,
        "updatedAt": utc_now(),
    }
    try:
        policy = x402_set_policy(network, payload)
        return ok("x402 pay policy saved.", network=network, x402Policy=policy)
    except Exception as exc:
        return fail("x402_runtime_error", str(exc), "Inspect x402 pay policy input and retry.", exit_code=1)


def cmd_x402_networks(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    try:
        payload = x402_list_networks()
        return ok("x402 networks loaded.", x402Networks=payload.get("networks"), defaultNetwork=payload.get("defaultNetwork"))
    except Exception as exc:
        return fail("x402_runtime_error", str(exc), "Inspect config/x402/networks.json and retry.", exit_code=1)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="xclaw-agent", add_help=True)
    sub = p.add_subparsers(dest="top")

    st = sub.add_parser("status")
    st.add_argument("--json", action="store_true")
    st.set_defaults(func=cmd_status)

    dashboard = sub.add_parser("dashboard")
    dashboard.add_argument("--chain", required=True)
    dashboard.add_argument("--json", action="store_true")
    dashboard.set_defaults(func=cmd_dashboard)

    intents = sub.add_parser("intents")
    intents_sub = intents.add_subparsers(dest="intents_cmd")
    intents_poll = intents_sub.add_parser("poll")
    intents_poll.add_argument("--chain", required=True)
    intents_poll.add_argument("--json", action="store_true")
    intents_poll.set_defaults(func=cmd_intents_poll)

    approvals = sub.add_parser("approvals")
    approvals_sub = approvals.add_subparsers(dest="approvals_cmd")
    approvals_check = approvals_sub.add_parser("check")
    approvals_check.add_argument("--intent", required=True)
    approvals_check.add_argument("--chain", required=True)
    approvals_check.add_argument("--json", action="store_true")
    approvals_check.set_defaults(func=cmd_approvals_check)

    approvals_sync = approvals_sub.add_parser("sync")
    approvals_sync.add_argument("--chain", required=True)
    approvals_sync.add_argument("--json", action="store_true")
    approvals_sync.set_defaults(func=cmd_approvals_sync)

    approvals_resume_spot = approvals_sub.add_parser("resume-spot")
    approvals_resume_spot.add_argument("--trade-id", required=True)
    approvals_resume_spot.add_argument("--chain")
    approvals_resume_spot.add_argument("--json", action="store_true")
    approvals_resume_spot.set_defaults(func=cmd_approvals_resume_spot)

    approvals_resume_transfer = approvals_sub.add_parser("resume-transfer")
    approvals_resume_transfer.add_argument("--approval-id", required=True)
    approvals_resume_transfer.add_argument("--chain")
    approvals_resume_transfer.add_argument("--json", action="store_true")
    approvals_resume_transfer.set_defaults(func=cmd_approvals_resume_transfer)

    approvals_decide_transfer = approvals_sub.add_parser("decide-transfer")
    approvals_decide_transfer.add_argument("--approval-id", required=True)
    approvals_decide_transfer.add_argument("--decision", required=True, choices=["approve", "deny"])
    approvals_decide_transfer.add_argument("--reason-message")
    approvals_decide_transfer.add_argument("--chain")
    approvals_decide_transfer.add_argument("--json", action="store_true")
    approvals_decide_transfer.set_defaults(func=cmd_approvals_decide_transfer)

    approvals_req_token = approvals_sub.add_parser("request-token")
    approvals_req_token.add_argument("--chain", required=True)
    approvals_req_token.add_argument("--token", required=True)
    approvals_req_token.add_argument("--json", action="store_true")
    approvals_req_token.set_defaults(func=cmd_approvals_request_token)

    approvals_req_global = approvals_sub.add_parser("request-global")
    approvals_req_global.add_argument("--chain", required=True)
    approvals_req_global.add_argument("--json", action="store_true")
    approvals_req_global.set_defaults(func=cmd_approvals_request_global)

    approvals_rev_token = approvals_sub.add_parser("revoke-token")
    approvals_rev_token.add_argument("--chain", required=True)
    approvals_rev_token.add_argument("--token", required=True)
    approvals_rev_token.add_argument("--json", action="store_true")
    approvals_rev_token.set_defaults(func=cmd_approvals_revoke_token)

    approvals_rev_global = approvals_sub.add_parser("revoke-global")
    approvals_rev_global.add_argument("--chain", required=True)
    approvals_rev_global.add_argument("--json", action="store_true")
    approvals_rev_global.set_defaults(func=cmd_approvals_revoke_global)

    trade = sub.add_parser("trade")
    trade_sub = trade.add_subparsers(dest="trade_cmd")
    trade_exec = trade_sub.add_parser("execute")
    trade_exec.add_argument("--intent", required=True)
    trade_exec.add_argument("--chain", required=True)
    trade_exec.add_argument("--json", action="store_true")
    trade_exec.set_defaults(func=cmd_trade_execute)

    trade_spot = trade_sub.add_parser("spot")
    trade_spot.add_argument("--chain", required=True)
    trade_spot.add_argument("--token-in", required=True)
    trade_spot.add_argument("--token-out", required=True)
    trade_spot.add_argument("--amount-in", required=True)
    trade_spot.add_argument("--slippage-bps", required=True)
    trade_spot.add_argument("--to")
    trade_spot.add_argument("--deadline-sec", default=120)
    trade_spot.add_argument("--json", action="store_true")
    trade_spot.set_defaults(func=cmd_trade_spot)

    transfers = sub.add_parser("transfers")
    transfers_sub = transfers.add_subparsers(dest="transfers_cmd")

    transfers_policy_get = transfers_sub.add_parser("policy-get")
    transfers_policy_get.add_argument("--chain", required=True)
    transfers_policy_get.add_argument("--json", action="store_true")
    transfers_policy_get.set_defaults(func=cmd_transfers_policy_get)

    transfers_policy_set = transfers_sub.add_parser("policy-set")
    transfers_policy_set.add_argument("--chain", required=True)
    transfers_policy_set.add_argument("--global", dest="global_mode", required=True, choices=["auto", "per_transfer"])
    transfers_policy_set.add_argument("--native-preapproved", default="0")
    transfers_policy_set.add_argument("--allowed-token", action="append", default=[])
    transfers_policy_set.add_argument("--json", action="store_true")
    transfers_policy_set.set_defaults(func=cmd_transfers_policy_set)

    report = sub.add_parser("report")
    report_sub = report.add_subparsers(dest="report_cmd")
    report_send = report_sub.add_parser("send")
    report_send.add_argument("--trade", required=True)
    report_send.add_argument("--json", action="store_true")
    report_send.set_defaults(func=cmd_report_send)

    chat = sub.add_parser("chat")
    chat_sub = chat.add_subparsers(dest="chat_cmd")

    chat_poll = chat_sub.add_parser("poll")
    chat_poll.add_argument("--chain", required=True)
    chat_poll.add_argument("--json", action="store_true")
    chat_poll.set_defaults(func=cmd_chat_poll)

    chat_post = chat_sub.add_parser("post")
    chat_post.add_argument("--message", required=True)
    chat_post.add_argument("--chain", required=True)
    chat_post.add_argument("--tags")
    chat_post.add_argument("--json", action="store_true")
    chat_post.set_defaults(func=cmd_chat_post)

    profile = sub.add_parser("profile")
    profile_sub = profile.add_subparsers(dest="profile_cmd")

    profile_set_name = profile_sub.add_parser("set-name")
    profile_set_name.add_argument("--name", required=True)
    profile_set_name.add_argument("--chain", required=True)
    profile_set_name.add_argument("--json", action="store_true")
    profile_set_name.set_defaults(func=cmd_profile_set_name)

    management_link = sub.add_parser("management-link")
    management_link.add_argument("--ttl-seconds", default=600)
    management_link.add_argument("--json", action="store_true")
    management_link.set_defaults(func=cmd_management_link)

    faucet_request = sub.add_parser("faucet-request")
    faucet_request.add_argument("--chain", required=True)
    faucet_request.add_argument("--json", action="store_true")
    faucet_request.set_defaults(func=cmd_faucet_request)

    x402 = sub.add_parser("x402")
    x402_sub = x402.add_subparsers(dest="x402_cmd")

    x402_receive_request = x402_sub.add_parser("receive-request")
    x402_receive_request.add_argument("--network", required=True)
    x402_receive_request.add_argument("--facilitator", required=True)
    x402_receive_request.add_argument("--amount-atomic", required=True)
    x402_receive_request.add_argument("--asset-kind", default="native", choices=["native", "erc20"])
    x402_receive_request.add_argument("--asset-address")
    x402_receive_request.add_argument("--asset-symbol")
    x402_receive_request.add_argument("--json", action="store_true")
    x402_receive_request.set_defaults(func=cmd_x402_receive_request)

    x402_pay = x402_sub.add_parser("pay")
    x402_pay.add_argument("--url", required=True)
    x402_pay.add_argument("--network", required=True)
    x402_pay.add_argument("--facilitator", required=True)
    x402_pay.add_argument("--amount-atomic", required=True)
    x402_pay.add_argument("--memo")
    x402_pay.add_argument("--json", action="store_true")
    x402_pay.set_defaults(func=cmd_x402_pay)

    x402_pay_resume = x402_sub.add_parser("pay-resume")
    x402_pay_resume.add_argument("--approval-id", required=True)
    x402_pay_resume.add_argument("--json", action="store_true")
    x402_pay_resume.set_defaults(func=cmd_x402_pay_resume)

    x402_pay_decide = x402_sub.add_parser("pay-decide")
    x402_pay_decide.add_argument("--approval-id", required=True)
    x402_pay_decide.add_argument("--decision", required=True, choices=["approve", "deny"])
    x402_pay_decide.add_argument("--reason-message")
    x402_pay_decide.add_argument("--json", action="store_true")
    x402_pay_decide.set_defaults(func=cmd_x402_pay_decide)

    x402_policy_get = x402_sub.add_parser("policy-get")
    x402_policy_get.add_argument("--network", required=True)
    x402_policy_get.add_argument("--json", action="store_true")
    x402_policy_get.set_defaults(func=cmd_x402_policy_get)

    x402_policy_set = x402_sub.add_parser("policy-set")
    x402_policy_set.add_argument("--network", required=True)
    x402_policy_set.add_argument("--mode", required=True, choices=["auto", "per_payment"])
    x402_policy_set.add_argument("--max-amount-atomic")
    x402_policy_set.add_argument("--allowed-host", action="append", default=[])
    x402_policy_set.add_argument("--json", action="store_true")
    x402_policy_set.set_defaults(func=cmd_x402_policy_set)

    x402_networks = x402_sub.add_parser("networks")
    x402_networks.add_argument("--json", action="store_true")
    x402_networks.set_defaults(func=cmd_x402_networks)

    limit_orders = sub.add_parser("limit-orders")
    limit_orders_sub = limit_orders.add_subparsers(dest="limit_orders_cmd")

    lo_create = limit_orders_sub.add_parser("create")
    lo_create.add_argument("--chain", required=True)
    lo_create.add_argument("--mode", required=True, choices=["mock", "real"])
    lo_create.add_argument("--side", required=True, choices=["buy", "sell"])
    lo_create.add_argument("--token-in", required=True)
    lo_create.add_argument("--token-out", required=True)
    lo_create.add_argument("--amount-in", required=True)
    lo_create.add_argument("--limit-price", required=True)
    lo_create.add_argument("--slippage-bps", required=True)
    lo_create.add_argument("--expires-at")
    lo_create.add_argument("--json", action="store_true")
    lo_create.set_defaults(func=cmd_limit_orders_create)

    lo_cancel = limit_orders_sub.add_parser("cancel")
    lo_cancel.add_argument("--order-id", required=True)
    lo_cancel.add_argument("--chain", required=True)
    lo_cancel.add_argument("--json", action="store_true")
    lo_cancel.set_defaults(func=cmd_limit_orders_cancel)

    lo_list = limit_orders_sub.add_parser("list")
    lo_list.add_argument("--chain", required=True)
    lo_list.add_argument("--status")
    lo_list.add_argument("--limit", default=50)
    lo_list.add_argument("--json", action="store_true")
    lo_list.set_defaults(func=cmd_limit_orders_list)

    lo_sync = limit_orders_sub.add_parser("sync")
    lo_sync.add_argument("--chain", required=True)
    lo_sync.add_argument("--json", action="store_true")
    lo_sync.set_defaults(func=cmd_limit_orders_sync)

    lo_status = limit_orders_sub.add_parser("status")
    lo_status.add_argument("--chain", required=True)
    lo_status.add_argument("--json", action="store_true")
    lo_status.set_defaults(func=cmd_limit_orders_status)

    lo_run_once = limit_orders_sub.add_parser("run-once")
    lo_run_once.add_argument("--chain", required=True)
    lo_run_once.add_argument("--sync", action="store_true")
    lo_run_once.add_argument("--json", action="store_true")
    lo_run_once.set_defaults(func=cmd_limit_orders_run_once)

    lo_run_loop = limit_orders_sub.add_parser("run-loop")
    lo_run_loop.add_argument("--chain", required=True)
    lo_run_loop.add_argument("--sync", action="store_true")
    lo_run_loop.add_argument("--interval-sec", default=10)
    lo_run_loop.add_argument("--iterations", default=0)
    lo_run_loop.add_argument("--json", action="store_true")
    lo_run_loop.set_defaults(func=cmd_limit_orders_run_loop)

    wallet = sub.add_parser("wallet")
    wallet_sub = wallet.add_subparsers(dest="wallet_cmd")

    w_health = wallet_sub.add_parser("health")
    w_health.add_argument("--chain", required=True)
    w_health.add_argument("--json", action="store_true")
    w_health.set_defaults(func=cmd_wallet_health)

    w_addr = wallet_sub.add_parser("address")
    w_addr.add_argument("--chain", required=True)
    w_addr.add_argument("--json", action="store_true")
    w_addr.set_defaults(func=cmd_wallet_address)

    w_sign = wallet_sub.add_parser("sign-challenge")
    w_sign.add_argument("--message", required=True)
    w_sign.add_argument("--chain", required=True)
    w_sign.add_argument("--json", action="store_true")
    w_sign.set_defaults(func=cmd_wallet_sign_challenge)

    w_send = wallet_sub.add_parser("send")
    w_send.add_argument("--to", required=True)
    w_send.add_argument("--amount-wei", required=True)
    w_send.add_argument("--chain", required=True)
    w_send.add_argument("--json", action="store_true")
    w_send.set_defaults(func=cmd_wallet_send)

    w_send_token = wallet_sub.add_parser("send-token")
    w_send_token.add_argument("--token", required=True)
    w_send_token.add_argument("--to", required=True)
    w_send_token.add_argument("--amount-wei", required=True)
    w_send_token.add_argument("--chain", required=True)
    w_send_token.add_argument("--json", action="store_true")
    w_send_token.set_defaults(func=cmd_wallet_send_token)

    w_bal = wallet_sub.add_parser("balance")
    w_bal.add_argument("--chain", required=True)
    w_bal.add_argument("--json", action="store_true")
    w_bal.set_defaults(func=cmd_wallet_balance)

    w_tbal = wallet_sub.add_parser("token-balance")
    w_tbal.add_argument("--token", required=True)
    w_tbal.add_argument("--chain", required=True)
    w_tbal.add_argument("--json", action="store_true")
    w_tbal.set_defaults(func=cmd_wallet_token_balance)

    # Wallet lifecycle commands are intentionally not exposed via the OpenClaw skill wrapper,
    # but the installer/bootstrap flow relies on the runtime being able to create a wallet
    # non-interactively when missing.
    w_create = wallet_sub.add_parser("create")
    w_create.add_argument("--chain", required=True)
    w_create.add_argument("--json", action="store_true")
    w_create.set_defaults(func=cmd_wallet_create)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 2
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
