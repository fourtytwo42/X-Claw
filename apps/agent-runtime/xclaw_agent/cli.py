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
from typing import Any, Callable

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from xclaw_agent import x402_state
from xclaw_agent.chains import (
    ChainRegistryError,
    assert_capability as assert_chain_capability,
    assert_chain_supported,
    chain_enabled,
    chain_capability,
    list_chains as list_chain_registry,
    supported_chain_hint as chain_supported_hint,
)
from xclaw_agent.x402_policy import get_policy as x402_get_policy
from xclaw_agent.x402_policy import set_policy as x402_set_policy
from xclaw_agent.x402_runtime import list_networks as x402_list_networks
from xclaw_agent.x402_runtime import pay_create_or_execute as x402_pay_create_or_execute
from xclaw_agent.x402_runtime import pay_decide as x402_pay_decide
from xclaw_agent.x402_runtime import pay_resume as x402_pay_resume
from xclaw_agent.x402_runtime import X402RuntimeError
from xclaw_agent.dex_adapter import build_dex_adapter, DexAdapterError
from xclaw_agent.dex_adapter import resolve_trade_execution_adapter, TradeAdapterResolutionError
from xclaw_agent.evm_action_executor import EvmActionExecutor
from xclaw_agent.liquidity_execution import (
    build_liquidity_add_plan,
    build_liquidity_claim_fees_plan,
    build_liquidity_claim_rewards_plan,
    build_liquidity_increase_plan,
    build_liquidity_migrate_plan,
    build_liquidity_remove_plan,
    execute_liquidity_plan,
)
from xclaw_agent.liquidity_adapter import (
    build_liquidity_adapter_for_request,
    LiquidityAdapterError,
    UnsupportedLiquidityOperation,
    UnsupportedLiquidityAdapter,
)
from xclaw_agent.trade_execution import build_trade_plan, execute_trade_plan, quote_trade
from xclaw_agent.solana_runtime import (
    SolanaRuntimeError,
    generate_wallet as solana_generate_wallet,
    get_balance_lamports as solana_get_balance_lamports,
    get_token_balances as solana_get_token_balances,
    import_wallet_private_key as solana_import_wallet_private_key,
    is_solana_address,
    is_solana_chain_key,
    jupiter_execute_swap as solana_jupiter_execute_swap,
    jupiter_quote as solana_jupiter_quote,
    send_native_transfer as solana_send_native_transfer,
    send_spl_transfer as solana_send_spl_transfer,
    sign_message as solana_sign_message,
)
from xclaw_agent.solana_liquidity_local import (
    claim_fees as solana_local_claim_fees,
    claim_rewards as solana_local_claim_rewards,
    create_position as solana_local_create_position,
    increase_position as solana_local_increase_position,
    migrate_position as solana_local_migrate_position,
    quote_add as solana_local_quote_add,
    remove_position as solana_local_remove_position,
)
from xclaw_agent.solana_raydium_clmm import (
    execute_instruction as solana_raydium_execute_instruction,
    quote_add as solana_raydium_quote_add,
    quote_remove as solana_raydium_quote_remove,
)
from xclaw_agent.solana_rpc_client import (
    SolanaRpcClientError,
    select_rpc_endpoint as solana_select_rpc_endpoint,
)
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
WATCHER_STATE_FILE = APP_DIR / "watcher-state.json"
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
APPROVAL_RUN_LOOP_INTERVAL_MS = 1500
APPROVAL_RUN_LOOP_BACKOFF_MAX_MS = 15000
DEFAULT_TX_GAS_PRICE_GWEI = 30
DEFAULT_TX_SEND_MAX_ATTEMPTS = 5
TX_GAS_PRICE_BUMP_GWEI = 20
DEFAULT_TX_RETRY_BUMP_BPS = 1250
DEFAULT_TX_PRIORITY_FLOOR_GWEI = 1
DEFAULT_TX_ESTIMATE_BYPASS_GAS_LIMIT = 900000
LIMIT_ORDER_STORE_VERSION = 1
AGENT_RECOVERY_ACTION = "agent_key_recovery"
ERC8021_MAGIC_REPEAT_COUNT = 8
BASE_BUILDER_CHAINS = {"base_mainnet", "base_sepolia"}
_TX_BUILDER_ATTRIBUTION_BY_HASH: dict[str, dict[str, Any]] = {}
_WATCHER_RUN_ID_CACHE: str | None = None


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


class LiquidityExecutionError(WalletStoreError):
    """Liquidity execution failed with deterministic reason code."""

    def __init__(self, reason_code: str, message: str, *, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.reason_code = str(reason_code or "liquidity_execution_failed").strip() or "liquidity_execution_failed"
        self.details = details or {}


class TokenResolutionError(WalletStoreError):
    """Token resolution failed with deterministic code/details."""

    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = str(code or "invalid_input").strip() or "invalid_input"
        self.details = details or {}


class SubprocessTimeout(WalletStoreError):
    """A subprocess operation timed out (cast call/receipt/send/etc)."""

    def __init__(self, kind: str, timeout_sec: int, cmd: list[str]):
        super().__init__(f"Timed out after {timeout_sec}s running: {_redact_cmd_for_display(cmd)}")
        self.kind = kind
        self.timeout_sec = timeout_sec
        self.cmd = _redact_cmd_args(cmd)


def _redact_sensitive_text(value: str) -> str:
    text = str(value or "")
    # Common CLI secret forms.
    text = re.sub(r"(?i)(--private-key)\s+\S+", r"\1 <REDACTED>", text)
    text = re.sub(r"(?i)(--private-key=)\S+", r"\1<REDACTED>", text)
    # Key-like field assignments.
    text = re.sub(
        r'(?i)((?:private[_ -]?key|wallet[_ -]?private[_ -]?key)\s*[:=]\s*)(?:0x)?[a-f0-9]{64}',
        r"\1<REDACTED>",
        text,
    )
    text = re.sub(
        r'(?i)(\"(?:private[_-]?key|wallet[_-]?private[_-]?key)\"\s*:\s*\")(?:0x)?[a-f0-9]{64}(\"?)',
        r"\1<REDACTED>\2",
        text,
    )
    return text


def _redact_cmd_args(cmd: list[str]) -> list[str]:
    redacted: list[str] = []
    i = 0
    while i < len(cmd):
        part = str(cmd[i])
        if part.lower() in {"--private-key"}:
            redacted.append(part)
            if i + 1 < len(cmd):
                redacted.append("<REDACTED>")
                i += 2
                continue
            i += 1
            continue
        if part.lower().startswith("--private-key="):
            redacted.append("--private-key=<REDACTED>")
            i += 1
            continue
        redacted.append(_redact_sensitive_text(part))
        i += 1
    return redacted


def _redact_cmd_for_display(cmd: list[str]) -> str:
    return " ".join(_redact_cmd_args(cmd))


def _sanitize_output_payload(value: Any) -> Any:
    if isinstance(value, str):
        return _redact_sensitive_text(value)
    if isinstance(value, dict):
        return {k: _sanitize_output_payload(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize_output_payload(item) for item in value]
    return value


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def emit(payload: dict) -> int:
    print(json.dumps(_sanitize_output_payload(payload), separators=(",", ":")))
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


def _env_positive_int(name: str, default: int) -> int:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    if not re.fullmatch(r"[0-9]+", raw):
        raise WalletStoreError(f"{name} must be an integer.")
    parsed = int(raw)
    if parsed < 1:
        raise WalletStoreError(f"{name} must be >= 1.")
    return parsed


def _cast_call_timeout_sec() -> int:
    return _env_timeout_sec("XCLAW_CAST_CALL_TIMEOUT_SEC", 30)


def _cast_receipt_timeout_sec() -> int:
    return _env_timeout_sec("XCLAW_CAST_RECEIPT_TIMEOUT_SEC", 90)


def _cast_send_timeout_sec() -> int:
    return _env_timeout_sec("XCLAW_CAST_SEND_TIMEOUT_SEC", 90)


def _transfer_executing_stale_sec() -> int:
    return _env_positive_int("XCLAW_TRANSFER_EXECUTING_STALE_SEC", 45)


def _trade_approval_inline_wait_sec() -> int:
    # Telegram chat UX should never hang waiting for owner action.
    # Keep a tiny inline wait window for racey "already approved" updates.
    return _env_positive_int("XCLAW_TRADE_APPROVAL_INLINE_WAIT_SEC", 2)


def _trade_approval_prompt_resend_cooldown_sec() -> int:
    # Reused approval_pending trades should be able to re-prompt after a short cooldown.
    return _env_positive_int("XCLAW_TRADE_APPROVAL_PROMPT_RESEND_COOLDOWN_SEC", 120)


def _telegram_dispatch_suppressed_for_harness() -> bool:
    raw = (os.environ.get("XCLAW_TEST_HARNESS_DISABLE_TELEGRAM") or "").strip().lower()
    if not raw:
        return False
    return raw not in {"0", "false", "off", "no", "disabled"}


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


def _read_runtime_default_chain() -> str | None:
    state = load_state()
    raw = state.get("defaultChain")
    if not isinstance(raw, str):
        return None
    normalized = raw.strip()
    if not normalized:
        return None
    return normalized


def _resolve_runtime_default_chain() -> tuple[str, str]:
    stored = _read_runtime_default_chain()
    if stored and chain_enabled(stored):
        return stored, "state"

    from_env = str(os.environ.get("XCLAW_DEFAULT_CHAIN") or "").strip()
    if from_env and chain_enabled(from_env):
        return from_env, "env"

    if chain_enabled("base_sepolia"):
        return "base_sepolia", "fallback"

    enabled_rows = list_chain_registry()
    if enabled_rows:
        first = str(enabled_rows[0].get("chainKey") or "").strip()
        if first:
            return first, "fallback"
    return "base_sepolia", "fallback"


def _set_runtime_default_chain(chain: str) -> None:
    assert_chain_supported(chain)
    state = load_state()
    state["defaultChain"] = chain
    save_state(state)


def _tracked_token_limit() -> int:
    return _env_positive_int("XCLAW_TRACKED_TOKEN_LIMIT", 200)


def _tracked_tokens_state(state: dict[str, Any], create: bool = True) -> dict[str, Any]:
    bucket = state.get("trackedTokens")
    if isinstance(bucket, dict):
        return bucket
    if not create:
        return {}
    bucket = {}
    state["trackedTokens"] = bucket
    return bucket


def _normalize_tracked_token_addresses(values: list[Any]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        token = str(value or "").strip().lower()
        if not is_hex_address(token):
            continue
        if token in seen:
            continue
        seen.add(token)
        out.append(token)
    return out


def _tracked_tokens_chain_entry(state: dict[str, Any], chain: str, create: bool = True) -> dict[str, Any]:
    tracked = _tracked_tokens_state(state, create=create)
    row = tracked.get(chain)
    if isinstance(row, dict):
        return row
    if not create:
        return {}
    row = {"addresses": [], "metadata": {}}
    tracked[chain] = row
    return row


def _get_tracked_token_addresses(chain: str) -> list[str]:
    state = load_state()
    row = _tracked_tokens_chain_entry(state, chain, create=False)
    addresses = row.get("addresses")
    if not isinstance(addresses, list):
        return []
    return _normalize_tracked_token_addresses(addresses)


def _set_tracked_token_addresses(chain: str, addresses: list[str]) -> None:
    state = load_state()
    row = _tracked_tokens_chain_entry(state, chain, create=True)
    row["addresses"] = _normalize_tracked_token_addresses(addresses)
    meta = row.get("metadata")
    if not isinstance(meta, dict):
        meta = {}
    normalized = {addr.lower() for addr in row["addresses"]}
    row["metadata"] = {k: v for k, v in meta.items() if isinstance(k, str) and k.lower() in normalized}
    save_state(state)


def _tracked_token_metadata_map(chain: str) -> dict[str, dict[str, Any]]:
    state = load_state()
    row = _tracked_tokens_chain_entry(state, chain, create=False)
    meta = row.get("metadata")
    if not isinstance(meta, dict):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for token, value in meta.items():
        if not isinstance(token, str) or not is_hex_address(token):
            continue
        if isinstance(value, dict):
            out[token.lower()] = value
    return out


def _set_tracked_token_metadata(chain: str, token: str, metadata: dict[str, Any]) -> None:
    normalized = str(token or "").strip().lower()
    if not is_hex_address(normalized):
        return
    state = load_state()
    row = _tracked_tokens_chain_entry(state, chain, create=True)
    meta = row.get("metadata")
    if not isinstance(meta, dict):
        meta = {}
        row["metadata"] = meta
    meta[normalized] = metadata
    save_state(state)


def _upsert_tracked_token_local(
    chain: str,
    token: str,
    *,
    symbol: str | None,
    name: str | None,
    decimals: int | None,
) -> dict[str, Any]:
    normalized = str(token or "").strip().lower()
    if not is_hex_address(normalized):
        raise TokenResolutionError(
            "invalid_token_address",
            "Invalid token address format.",
            {"chain": chain, "token": token},
        )
    addresses = _get_tracked_token_addresses(chain)
    existed = normalized in addresses
    if not existed and len(addresses) >= _tracked_token_limit():
        raise TokenResolutionError(
            "tracked_token_limit_reached",
            "Tracked token limit reached for this chain.",
            {"chain": chain, "limit": _tracked_token_limit()},
        )
    if not existed:
        addresses.append(normalized)
        _set_tracked_token_addresses(chain, addresses)
    metadata = {
        "token": normalized,
        "symbol": str(symbol or "").strip() or None,
        "name": str(name or "").strip() or None,
        "decimals": int(decimals) if isinstance(decimals, int) else (int(decimals) if decimals is not None else None),
        "updatedAt": utc_now(),
    }
    _set_tracked_token_metadata(chain, normalized, metadata)
    metadata["created"] = not existed
    return metadata


def _remove_tracked_token_local(chain: str, token: str) -> bool:
    normalized = str(token or "").strip().lower()
    if not is_hex_address(normalized):
        raise TokenResolutionError(
            "invalid_token_address",
            "Invalid token address format.",
            {"chain": chain, "token": token},
        )
    addresses = _get_tracked_token_addresses(chain)
    if normalized not in addresses:
        return False
    remaining = [addr for addr in addresses if addr != normalized]
    _set_tracked_token_addresses(chain, remaining)
    return True


def _tracked_tokens_for_chain(chain: str) -> list[dict[str, Any]]:
    addresses = _get_tracked_token_addresses(chain)
    metadata = _tracked_token_metadata_map(chain)
    out: list[dict[str, Any]] = []
    for token in addresses:
        row = metadata.get(token, {})
        symbol = str(row.get("symbol") or "").strip() or None
        name = str(row.get("name") or "").strip() or None
        decimals_raw = row.get("decimals")
        decimals: int | None
        if isinstance(decimals_raw, int):
            decimals = decimals_raw
        elif isinstance(decimals_raw, str) and re.fullmatch(r"[0-9]+", decimals_raw):
            decimals = int(decimals_raw)
        else:
            decimals = None
        out.append({"token": token, "symbol": symbol, "name": name, "decimals": decimals})
    return out


def _mirror_tracked_tokens(chain: str) -> bool:
    try:
        api_key = _resolve_api_key()
        agent_id = _resolve_agent_id(api_key)
        if not agent_id:
            return False
        payload = {
            "agentId": agent_id,
            "chainKey": chain,
            "tokens": _tracked_tokens_for_chain(chain),
        }
        status_code, _body = _api_request(
            "POST",
            "/agent/tokens/mirror",
            payload=payload,
            include_idempotency=True,
            idempotency_key=f"rt-agent-token-mirror-{chain}-{secrets.token_hex(8)}",
        )
        return 200 <= status_code < 300
    except Exception:
        return False


def _sync_tracked_tokens_from_remote(chain: str) -> bool:
    try:
        status_code, body = _api_request("GET", f"/agent/tokens?chainKey={urllib.parse.quote(chain)}")
        if status_code < 200 or status_code >= 300:
            return False
        items = body.get("items")
        if not isinstance(items, list):
            return False
        current = _tracked_tokens_for_chain(chain)
        merged: dict[str, dict[str, Any]] = {}
        for row in current:
            token = str(row.get("token") or "").strip().lower()
            if is_hex_address(token):
                merged[token] = row
        for row in items:
            if not isinstance(row, dict):
                continue
            token = str(row.get("tokenAddress") or row.get("token") or "").strip().lower()
            if not is_hex_address(token):
                continue
            merged[token] = {
                "token": token,
                "symbol": str(row.get("symbol") or "").strip() or None,
                "name": str(row.get("name") or "").strip() or None,
                "decimals": row.get("decimals"),
            }
        _set_tracked_token_addresses(chain, list(merged.keys()))
        for token, row in merged.items():
            _set_tracked_token_metadata(
                chain,
                token,
                {
                    "token": token,
                    "symbol": row.get("symbol"),
                    "name": row.get("name"),
                    "decimals": row.get("decimals"),
                    "updatedAt": utc_now(),
                },
            )
        return True
    except Exception:
        return False


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
        _sync_tracked_tokens_from_remote(chain)
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


def _chain_family(chain: str) -> str:
    cfg = _load_chain_config(chain)
    return str(cfg.get("family") or "evm").strip().lower() or "evm"


def _is_solana_chain(chain: str) -> bool:
    if is_solana_chain_key(chain):
        return True
    return _chain_family(chain) == "solana"


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
    assert_chain_supported(chain)
    path = CHAIN_CONFIG_DIR / f"{chain}.json"
    if not path.exists():
        raise WalletStoreError(f"Chain config not found for '{chain}' at '{path}'.")
    data = _read_json(path)
    if not isinstance(data, dict):
        raise WalletStoreError(f"Chain config '{path}' must be a JSON object.")
    return data


def _is_rpc_endpoint_healthy(rpc_url: str) -> bool:
    payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "eth_blockNumber", "params": []}).encode("utf-8")
    req = urllib.request.Request(
        rpc_url,
        data=payload,
        headers={"content-type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=2.5) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        result = body.get("result") if isinstance(body, dict) else None
        return isinstance(result, str) and bool(re.fullmatch(r"0x[a-fA-F0-9]+", result))
    except Exception:
        return False


def _chain_rpc_url(chain: str) -> str:
    if _is_solana_chain(chain):
        try:
            selected = solana_select_rpc_endpoint(chain)
            return selected.endpoint
        except SolanaRpcClientError as exc:
            raise WalletStoreError(f"{exc.code}: {exc}") from exc
    candidates = _chain_rpc_candidates(chain)
    if len(candidates) == 1:
        return candidates[0]
    for candidate in candidates:
        if _is_rpc_endpoint_healthy(candidate):
            return candidate
    # If health probes fail for all, return the configured fallback endpoint first.
    return candidates[-1]


def _chain_rpc_candidates(chain: str) -> list[str]:
    cfg = _load_chain_config(chain)
    rpc = cfg.get("rpc")
    if not isinstance(rpc, dict):
        raise WalletStoreError(f"Chain config for '{chain}' is missing rpc object.")
    primary = rpc.get("primary")
    fallback = rpc.get("fallback")
    candidates: list[str] = []
    for candidate in [primary, fallback]:
        if isinstance(candidate, str) and candidate.strip():
            normalized = candidate.strip()
            if normalized not in candidates:
                candidates.append(normalized)
    if not candidates:
        raise WalletStoreError(f"Chain config for '{chain}' has no usable rpc URL.")
    return candidates


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


def _encrypt_secret_bytes(secret_bytes: bytes, passphrase: str) -> dict[str, Any]:
    salt = secrets.token_bytes(16)
    nonce = secrets.token_bytes(12)
    key = _derive_aes_key(passphrase, salt)
    cipher = AESGCM(key)
    ciphertext = cipher.encrypt(nonce, secret_bytes, None)
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


def _encrypt_private_key(private_key_hex: str, passphrase: str) -> dict[str, Any]:
    private_key_bytes = bytes.fromhex(private_key_hex)
    return _encrypt_secret_bytes(private_key_bytes, passphrase)


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
    key_scheme = str(entry.get("keyScheme") or "evm_secp256k1").strip().lower() or "evm_secp256k1"
    if not isinstance(address, str):
        raise WalletStoreError("Wallet entry address is missing or invalid.")
    if key_scheme == "solana_ed25519":
        if not is_solana_address(address):
            raise WalletStoreError("Wallet entry address is missing or invalid.")
    else:
        if not is_hex_address(address):
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

    if key_scheme not in {"evm_secp256k1", "solana_ed25519"}:
        raise WalletStoreError("Wallet entry keyScheme is invalid.")


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


def _runtime_wallet_signing_readiness(chain: str) -> dict[str, Any]:
    checked_at = utc_now()
    try:
        store = load_wallet_store()
    except Exception as exc:
        return {
            "walletSigningReady": False,
            "walletSigningReasonCode": "wallet_store_unavailable",
            "walletSigningCheckedAt": checked_at,
            "walletSigningMessage": str(exc),
        }
    _, wallet = _chain_wallet(store, chain)
    if not isinstance(wallet, dict):
        return {
            "walletSigningReady": False,
            "walletSigningReasonCode": "wallet_missing",
            "walletSigningCheckedAt": checked_at,
            "walletSigningMessage": f"No wallet configured for chain '{chain}'.",
        }
    passphrase = str(os.environ.get("XCLAW_WALLET_PASSPHRASE") or "").strip()
    if not passphrase:
        return {
            "walletSigningReady": False,
            "walletSigningReasonCode": "wallet_passphrase_missing",
            "walletSigningCheckedAt": checked_at,
            "walletSigningMessage": "XCLAW_WALLET_PASSPHRASE is missing.",
        }
    try:
        _decrypt_private_key(wallet, passphrase)
    except Exception as exc:
        return {
            "walletSigningReady": False,
            "walletSigningReasonCode": "wallet_passphrase_invalid",
            "walletSigningCheckedAt": checked_at,
            "walletSigningMessage": str(exc),
        }
    return {
        "walletSigningReady": True,
        "walletSigningReasonCode": None,
        "walletSigningCheckedAt": checked_at,
        "walletSigningMessage": None,
    }


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
        # Local fail-safe for runtime subprocesses that may not inherit web env.
        base_url = "http://127.0.0.1:3000/api/v1"
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
        chain, _ = _resolve_runtime_default_chain()
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


def cmd_auth_recover(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    chain = str(args.chain or "").strip()
    if not chain:
        return fail("invalid_input", "chain is required.", "Provide --chain <chainKey> and retry.", exit_code=2)
    try:
        base_url = _require_api_base_url()
        stale_api_key = ""
        try:
            stale_api_key = _resolve_api_key()
        except WalletStoreError:
            stale_api_key = ""
        recovered_key = _recover_api_key_with_wallet_signature(base_url, stale_api_key, chain)
        resolved_agent_id = _resolve_agent_id(recovered_key)
        return ok(
            "Agent auth recovered with wallet signature.",
            chain=chain,
            recovered=True,
            persisted=True,
            agentId=resolved_agent_id,
        )
    except WalletStoreError as exc:
        return fail(
            "auth_recovery_failed",
            str(exc),
            "Set XCLAW_API_BASE_URL, XCLAW_AGENT_ID, and XCLAW_WALLET_PASSPHRASE, then retry.",
            {"chain": chain},
            exit_code=1,
        )
    except Exception as exc:
        return fail(
            "auth_recovery_failed",
            str(exc),
            "Inspect runtime auth recovery path and retry.",
            {"chain": chain},
            exit_code=1,
        )


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
    trade_caps_payload = policy_payload.get("tradeCaps")
    trade_caps: dict[str, Any]
    if isinstance(trade_caps_payload, dict):
        trade_caps = dict(trade_caps_payload)
    else:
        # Slice 117 Hotfix D: trade caps are deprecated for execution gating.
        # Keep compatibility payload fields for downstream telemetry/output.
        trade_caps = {
            "approvalMode": "per_trade",
            "maxTradeUsd": None,
            "maxDailyUsd": None,
            "allowedTokens": [],
            "dailyCapUsdEnabled": False,
            "dailyTradeCapEnabled": False,
            "maxDailyTradeCount": None,
        }

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

    _ = projected_spend_usd
    _ = projected_filled_trades

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


def _parse_iso_utc(value: str | None) -> datetime | None:
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


def _is_stale_executing_transfer_flow(flow: dict[str, Any]) -> bool:
    status = str(flow.get("status") or "")
    if status not in {"executing", "verifying"}:
        return False
    if str(flow.get("txHash") or "").strip():
        return False
    updated_at = _parse_iso_utc(str(flow.get("updatedAt") or flow.get("decidedAt") or flow.get("createdAt") or ""))
    if updated_at is None:
        return True
    age_sec = (datetime.now(timezone.utc) - updated_at).total_seconds()
    return age_sec >= float(_transfer_executing_stale_sec())


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


def _mirror_transfer_approval(flow: dict[str, Any], *, require_delivery: bool = False) -> bool:
    try:
        approval_id = str(flow.get("approvalId") or "").strip()
        chain = str(flow.get("chainKey") or "").strip()
        if not approval_id or not chain:
            return False
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
            "observedBy": str(flow.get("observedBy") or "agent_watcher"),
            "observationSource": str(flow.get("observationSource") or "local_send_result"),
            "confirmationCount": flow.get("confirmationCount"),
            "observedAt": flow.get("observedAt") or utc_now(),
            "watcherRunId": str(flow.get("watcherRunId") or _watcher_run_id()),
            "createdAt": flow.get("createdAt") or utc_now(),
            "updatedAt": flow.get("updatedAt") or utc_now(),
            "decidedAt": flow.get("decidedAt"),
            "terminalAt": flow.get("terminalAt"),
        }

        attempts = 2 if require_delivery else 1
        last_error: str | None = None
        for attempt in range(attempts):
            status_code, body = _api_request(
                "POST",
                "/agent/transfer-approvals/mirror",
                payload=payload,
                include_idempotency=True,
                idempotency_key=f"rt-transfer-mirror-{approval_id}-{secrets.token_hex(8)}",
            )
            if 200 <= status_code < 300:
                return True
            code = str(body.get("code", "api_error"))
            message = str(body.get("message", f"transfer mirror failed ({status_code})"))
            last_error = f"{code}: {message}"
            if attempt < (attempts - 1):
                time.sleep(0.2)

        if require_delivery:
            raise WalletStoreError(last_error or "transfer approval mirror failed.")
        return False
    except Exception as exc:
        if require_delivery:
            raise WalletStoreError(str(exc) or "transfer approval mirror failed.") from exc
        return False


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
            "assetKind": "token" if str(flow.get("assetKind") or "").strip().lower() in {"erc20", "token"} else "native",
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
            "transferType": "token" if str(flow.get("assetKind") or "").strip().lower() in {"erc20", "token"} else "native",
            "tokenAddress": flow.get("assetAddress"),
            "tokenSymbol": str(flow.get("assetSymbol") or "X402"),
            "toAddress": str(flow.get("toAddress") or flow.get("recipientAddress") or ("11111111111111111111111111111111" if network.startswith("solana_") else "0x0000000000000000000000000000000000000000")),
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
            "x402AssetKind": "token" if str(flow.get("assetKind") or "").strip().lower() in {"erc20", "token"} else "native",
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


def _x402_settlement_amount_units(chain: str, asset_kind: str, amount_atomic: str, asset_address: str | None) -> int:
    kind = str(asset_kind or "native").strip().lower()
    amount_text = str(amount_atomic or "").strip()
    if not amount_text:
        raise WalletStoreError("x402 settlement amount is missing.")
    if kind == "native":
        decimals = 9 if _is_solana_chain(chain) else 18
        return int(_to_units_uint(amount_text, decimals))
    if _is_solana_chain(chain):
        if not re.fullmatch(r"[0-9]+", amount_text):
            raise WalletStoreError("Solana token x402 settlement requires integer atomic units.")
        return int(amount_text)
    token = str(asset_address or "").strip().lower()
    if not is_hex_address(token):
        raise WalletStoreError("EVM token x402 settlement requires token address.")
    meta = _fetch_erc20_metadata(chain, token)
    decimals = int(meta.get("decimals", 18))
    return int(_to_units_uint(amount_text, decimals))


def _x402_wait_evm_receipt_success(chain: str, tx_hash: str) -> None:
    cast_bin = _require_cast_bin()
    rpc_url = _chain_rpc_url(chain)
    receipt_proc = _run_subprocess(
        [cast_bin, "receipt", "--json", "--rpc-url", rpc_url, tx_hash],
        timeout_sec=_cast_receipt_timeout_sec(),
        kind="cast_receipt",
    )
    if receipt_proc.returncode != 0:
        stderr = (receipt_proc.stderr or "").strip()
        stdout = (receipt_proc.stdout or "").strip()
        raise WalletStoreError(stderr or stdout or "cast receipt failed for x402 settlement tx.")
    payload = json.loads((receipt_proc.stdout or "{}").strip() or "{}")
    status = str(payload.get("status", "0x0")).lower()
    if status not in {"0x1", "1"}:
        raise WalletStoreError(f"x402 settlement transaction failed on-chain with status '{status}'.")


def _execute_x402_settlement(request: dict[str, Any]) -> dict[str, Any]:
    chain = str(request.get("network") or "").strip()
    if not chain:
        raise WalletStoreError("x402 settlement request is missing network.")
    store = load_wallet_store()
    rpc_url = _chain_rpc_url(chain)
    recipient = str(request.get("recipientAddress") or "").strip()
    if _is_solana_chain(chain):
        if not is_solana_address(recipient):
            raise WalletStoreError("Solana x402 settlement recipient is invalid.")
        wallet_address, private_key_bytes = _execution_wallet_solana_secret(store, chain)
        asset_kind = str(request.get("assetKind") or "native").strip().lower()
        amount_units = _x402_settlement_amount_units(chain, asset_kind, str(request.get("amountAtomic") or ""), str(request.get("assetAddress") or "") or None)
        if asset_kind == "native":
            signature = solana_send_native_transfer(rpc_url, private_key_bytes, recipient, amount_units)
            return {"txId": signature, "family": "solana", "fromAddress": wallet_address, "toAddress": recipient, "assetKind": "native"}
        mint = str(request.get("assetAddress") or "").strip()
        if not is_solana_address(mint):
            raise WalletStoreError("Solana x402 token settlement requires valid mint address.")
        result = solana_send_spl_transfer(rpc_url, private_key_bytes, recipient, mint, amount_units)
        signature = str(result.get("signature") or "").strip()
        if not signature:
            raise WalletStoreError("Solana x402 token settlement returned empty signature.")
        return {
            "txId": signature,
            "family": "solana",
            "fromAddress": wallet_address,
            "toAddress": recipient,
            "assetKind": "token",
            "assetAddress": mint,
            "details": result,
        }

    if not is_hex_address(recipient):
        raise WalletStoreError("EVM x402 settlement recipient is invalid.")
    wallet_address, private_key_hex = _execution_wallet(store, chain)
    asset_kind = str(request.get("assetKind") or "native").strip().lower()
    amount_units = _x402_settlement_amount_units(chain, asset_kind, str(request.get("amountAtomic") or ""), str(request.get("assetAddress") or "") or None)
    if asset_kind == "native":
        tx_hash = _cast_rpc_send_transaction(
            rpc_url,
            {"from": wallet_address, "to": recipient, "value": hex(int(amount_units))},
            private_key_hex,
            chain=chain,
        )
        _x402_wait_evm_receipt_success(chain, tx_hash)
        return {"txId": tx_hash, "family": "evm", "fromAddress": wallet_address, "toAddress": recipient, "assetKind": "native"}

    token = str(request.get("assetAddress") or "").strip().lower()
    if not is_hex_address(token):
        raise WalletStoreError("EVM x402 token settlement requires token address.")
    data = _cast_calldata("transfer(address,uint256)(bool)", [recipient, str(int(amount_units))])
    tx_hash = _cast_rpc_send_transaction(
        rpc_url,
        {"from": wallet_address, "to": token, "data": data},
        private_key_hex,
        chain=chain,
    )
    _x402_wait_evm_receipt_success(chain, tx_hash)
    return {"txId": tx_hash, "family": "evm", "fromAddress": wallet_address, "toAddress": recipient, "assetKind": "token", "assetAddress": token}


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
        return str(amount_wei), str(token_symbol or ("NATIVE" if transfer_type == "native" else "TOKEN"))
    if amount_int < 0:
        amount_int = 0
    unit = "NATIVE" if transfer_type == "native" else (str(token_symbol or "TOKEN").strip() or "TOKEN")
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
    token_symbol = str(flow.get("tokenSymbol") or ("NATIVE" if transfer_type == "native" else "TOKEN")).strip()
    token_decimals_raw = flow.get("tokenDecimals", 18 if transfer_type == "native" else None)
    token_decimals: int | None
    try:
        token_decimals = int(token_decimals_raw) if token_decimals_raw is not None else None
    except Exception:
        token_decimals = 18 if transfer_type == "native" else None
    amount_human, amount_unit = _transfer_amount_display(amount_wei, transfer_type, token_symbol, token_decimals)
    amount_display = f"{amount_human} {amount_unit}"
    is_solana = _is_solana_chain(chain)
    if not approval_id or not chain:
        return {"ok": False, "code": "invalid_state", "message": "Missing approvalId/chain in transfer flow."}
    if not re.fullmatch(r"[0-9]+", amount_wei):
        return {"ok": False, "code": "invalid_state", "message": "Transfer flow amountWei must be uint."}
    if is_solana:
        if not is_solana_address(to_address):
            return {"ok": False, "code": "invalid_state", "message": "Transfer flow destination is invalid."}
    elif not is_hex_address(to_address):
        return {"ok": False, "code": "invalid_state", "message": "Transfer flow destination is invalid."}
    if transfer_type == "token":
        if is_solana:
            if not token_address or not is_solana_address(token_address):
                return {"ok": False, "code": "invalid_state", "message": "Transfer token address is invalid."}
        elif not token_address or not is_hex_address(token_address):
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
    flow["observedBy"] = "agent_watcher"
    flow["observationSource"] = "local_send_result"
    flow["observedAt"] = flow["updatedAt"]
    flow["watcherRunId"] = _watcher_run_id()
    flow["confirmationCount"] = None
    _record_pending_transfer_flow(approval_id, flow)
    _mirror_transfer_approval(flow)

    from_address: str | None = None
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
        from_address = str(wallet.get("address"))
        _assert_transfer_balance_preconditions(
            chain=chain,
            transfer_type=transfer_type,
            wallet_address=from_address,
            amount_wei=amount_wei,
            token_address=token_address,
            token_symbol=token_symbol,
            token_decimals=token_decimals,
        )
        passphrase = _require_wallet_passphrase_for_signing(chain)
        private_key_bytes = _decrypt_private_key(wallet, passphrase)

        tx_hash: str
        rpc_url = _chain_rpc_url(chain)
        if is_solana:
            if transfer_type == "native":
                tx_hash = solana_send_native_transfer(rpc_url, private_key_bytes, to_address, int(amount_wei))
            else:
                result = solana_send_spl_transfer(rpc_url, private_key_bytes, to_address, str(token_address), int(amount_wei))
                tx_hash = str(result.get("signature") or "")
                if token_decimals is None and isinstance(result.get("decimals"), int):
                    token_decimals = int(result.get("decimals"))
                flow["solanaTransfer"] = result
        else:
            private_key_hex = private_key_bytes.hex()
            if transfer_type == "native":
                tx_hash = _cast_rpc_send_transaction(
                    rpc_url,
                    {
                        "from": from_address,
                        "to": to_address,
                        "value": amount_wei,
                        "data": "0x",
                    },
                    private_key_hex,
                    chain=chain,
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
            else:
                data = _cast_calldata("transfer(address,uint256)(bool)", [to_address, amount_wei])
                tx_hash = _cast_rpc_send_transaction(
                    rpc_url,
                    {"from": from_address, "to": str(token_address), "data": data},
                    private_key_hex,
                    chain=chain,
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
        flow["observedBy"] = "agent_watcher"
        flow["observationSource"] = "rpc_receipt"
        flow["observedAt"] = flow["updatedAt"]
        flow["watcherRunId"] = _watcher_run_id()
        flow["confirmationCount"] = 1
        _record_pending_transfer_flow(approval_id, flow)
        _mirror_transfer_approval(flow)
        _remove_pending_transfer_flow(approval_id)
        builder_meta = _builder_output_from_hashes(chain, [tx_hash])
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
        flow["updatedAt"] = utc_now()
        flow["terminalAt"] = flow["updatedAt"]
        flow["observedBy"] = "agent_watcher"
        flow["observationSource"] = "rpc_receipt"
        flow["observedAt"] = flow["updatedAt"]
        flow["watcherRunId"] = _watcher_run_id()
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


def _wait_for_trade_approval(trade_id: str, chain: str, summary: dict[str, Any] | None = None) -> dict[str, Any]:
    # Always attempt Telegram prompt delivery when Telegram is the active chat.
    # Helper applies channel checks + de-dupe.
    try:
        _maybe_send_telegram_approval_prompt(trade_id, chain, summary or {})
    except Exception:
        pass
    wait_timeout_sec = APPROVAL_WAIT_TIMEOUT_SEC
    if _last_delivery_is_telegram():
        # Do not block active Telegram chats for owner decisions.
        wait_timeout_sec = min(wait_timeout_sec, _trade_approval_inline_wait_sec())
    deadline_ms = int(time.time() * 1000) + (wait_timeout_sec * 1000)
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
        "Approve the pending trade in Telegram or web management; execution resumes automatically after approval.",
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


def _transfer_prompt_key(approval_id: str) -> str:
    return f"xfer:{approval_id}"


def _policy_prompt_key(approval_id: str) -> str:
    return f"xpol:{approval_id}"


def _record_transfer_approval_prompt(approval_id: str, prompt: dict[str, Any]) -> None:
    _record_approval_prompt(
        _transfer_prompt_key(approval_id),
        {
            **prompt,
            "promptType": "transfer",
            "approvalId": approval_id,
        },
    )


def _get_approval_prompt(trade_id: str) -> dict[str, Any] | None:
    state = _load_approval_prompts()
    prompts = state.get("prompts")
    if not isinstance(prompts, dict):
        return None
    entry = prompts.get(trade_id)
    return entry if isinstance(entry, dict) else None


def _get_transfer_approval_prompt(approval_id: str) -> dict[str, Any] | None:
    return _get_approval_prompt(_transfer_prompt_key(approval_id))


def _record_policy_approval_prompt(approval_id: str, prompt: dict[str, Any]) -> None:
    _record_approval_prompt(
        _policy_prompt_key(approval_id),
        {
            **prompt,
            "promptType": "policy",
            "approvalId": approval_id,
        },
    )


def _get_policy_approval_prompt(approval_id: str) -> dict[str, Any] | None:
    return _get_approval_prompt(_policy_prompt_key(approval_id))


def _remove_approval_prompt(trade_id: str) -> None:
    state = _load_approval_prompts()
    prompts = state.get("prompts")
    if not isinstance(prompts, dict):
        return
    if trade_id in prompts:
        prompts.pop(trade_id, None)
        _save_approval_prompts(state)


def _remove_transfer_approval_prompt(approval_id: str) -> None:
    _remove_approval_prompt(_transfer_prompt_key(approval_id))


def _remove_policy_approval_prompt(approval_id: str) -> None:
    _remove_approval_prompt(_policy_prompt_key(approval_id))


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


def _last_delivery_is_telegram() -> bool:
    delivery = _read_openclaw_last_delivery()
    if not delivery:
        return False
    return str(delivery.get("lastChannel") or "").strip().lower() == "telegram"


def _require_openclaw_bin() -> str:
    env_path = (os.environ.get("OPENCLAW_BIN") or "").strip()
    if env_path:
        candidate = pathlib.Path(env_path).expanduser()
        if candidate.exists() and os.access(candidate, os.X_OK):
            return str(candidate)
    path = shutil.which("openclaw")
    if path:
        return path
    for candidate in (
        pathlib.Path("/usr/local/bin/openclaw"),
        pathlib.Path("/usr/bin/openclaw"),
        pathlib.Path.home() / ".local" / "bin" / "openclaw",
    ):
        if candidate.exists() and os.access(candidate, os.X_OK):
            return str(candidate)
    raise WalletStoreError("Missing dependency: openclaw (required for Telegram approval prompts).")


def _extract_openclaw_message_id(stdout: str) -> str | None:
    def _walk(value: Any) -> str | None:
        if isinstance(value, dict):
            for key in ("messageId", "message_id"):
                raw = value.get(key)
                if isinstance(raw, str) and raw.strip():
                    return raw.strip()
                if isinstance(raw, int):
                    return str(raw)
            for nested in value.values():
                found = _walk(nested)
                if found:
                    return found
        elif isinstance(value, list):
            for nested in value:
                found = _walk(nested)
                if found:
                    return found
        return None

    raw = (stdout or "").strip()
    if not raw:
        return None
    payload: Any = None
    try:
        payload = json.loads(raw)
    except Exception:
        # Some OpenClaw builds prepend transport logs before JSON.
        brace = raw.find("{")
        if brace >= 0:
            try:
                payload = json.loads(raw[brace:])
            except Exception:
                payload = None
        if payload is None:
            for line in reversed(raw.splitlines()):
                line_trimmed = line.strip()
                if not line_trimmed:
                    continue
                try:
                    payload = json.loads(line_trimmed)
                    break
                except Exception:
                    continue
    if payload is not None:
        found = _walk(payload)
        if found:
            return found

    # Fallback for non-JSON/mixed stdout variants emitted by some OpenClaw builds.
    patterns = (
        r'["\']messageId["\']\s*[:=]\s*["\']?([0-9]{1,20})["\']?',
        r'["\']message_id["\']\s*[:=]\s*["\']?([0-9]{1,20})["\']?',
        r"\bmessage[_\s-]?id\b\s*[:=]\s*([0-9]{1,20})\b",
    )
    for pattern in patterns:
        matches = list(re.finditer(pattern, raw, flags=re.IGNORECASE))
        if matches:
            value = (matches[-1].group(1) or "").strip()
            if value:
                return value
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
    if _telegram_dispatch_suppressed_for_harness():
        return
    # Avoid duplicate sends within a short cooldown window.
    existing = _get_approval_prompt(trade_id)
    if existing and str(existing.get("channel") or "") == "telegram":
        updated_at = _parse_iso_utc(str(existing.get("updatedAt") or existing.get("createdAt") or ""))
        if updated_at is not None:
            age_sec = (datetime.now(timezone.utc) - updated_at).total_seconds()
            if age_sec < float(_trade_approval_prompt_resend_cooldown_sec()):
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
        f"Chain: `{chain}`\n"
        f"Trade: `{trade_id}`\n\n"
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


def _maybe_send_telegram_transfer_approval_prompt(flow: dict[str, Any]) -> None:
    if _telegram_dispatch_suppressed_for_harness():
        return
    approval_id = str(flow.get("approvalId") or "").strip()
    chain = str(flow.get("chainKey") or "").strip()
    if not approval_id or not chain:
        return
    existing = _get_transfer_approval_prompt(approval_id)
    if existing and str(existing.get("channel") or "") == "telegram":
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

    callback_approve = f"xfer|a|{approval_id}|{chain}"
    callback_deny = f"xfer|r|{approval_id}|{chain}"
    if len(callback_approve.encode("utf-8")) > 64 or len(callback_deny.encode("utf-8")) > 64:
        return

    transfer_type = str(flow.get("transferType") or "token").strip().lower()
    token_symbol = str(flow.get("tokenSymbol") or ("ETH" if transfer_type == "native" else "TOKEN")).strip() or "TOKEN"
    token_decimals = 18
    try:
        token_decimals = int(flow.get("tokenDecimals", 18))
    except Exception:
        token_decimals = 18
    amount_wei = str(flow.get("amountWei") or "0").strip() or "0"
    amount_human, amount_unit = _transfer_amount_display(amount_wei, transfer_type, token_symbol, token_decimals)
    amount_display = f"{amount_human} {amount_unit}"
    to_address = str(flow.get("toAddress") or "").strip().lower() or "unknown"

    text = (
        "Approve transfer\n"
        f"Amount: {amount_display}\n"
        f"To: `{to_address}`\n"
        f"Chain: `{chain}`\n"
        f"Approval: `{approval_id}`\n\n"
        "Tap Approve to execute (or Deny to reject)."
    )
    if bool(flow.get("policyBlockedAtCreate")):
        reason_code = str(flow.get("policyBlockReasonCode") or "unknown")
        text += (
            f"\n\nPolicy blocked at create: {reason_code}"
            "\nApprove executes this transfer as a one-off override."
        )

    buttons = json.dumps(
        [[{"text": "Approve", "callback_data": callback_approve}, {"text": "Deny", "callback_data": callback_deny}]],
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
        message_id = "unknown"
    _record_transfer_approval_prompt(
        approval_id,
        {
            "channel": "telegram",
            "chainKey": chain,
            "to": chat_id,
            "threadId": thread_id,
            "messageId": message_id,
            "createdAt": utc_now(),
        },
    )


def _maybe_send_telegram_policy_approval_prompt(flow: dict[str, Any]) -> None:
    if _telegram_dispatch_suppressed_for_harness():
        return
    approval_id = str(flow.get("policyApprovalId") or "").strip()
    chain = str(flow.get("chainKey") or "").strip()
    if not approval_id or not chain:
        return
    existing = _get_policy_approval_prompt(approval_id)
    if existing and str(existing.get("channel") or "") == "telegram":
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

    callback_approve = f"xpol|a|{approval_id}|{chain}"
    callback_deny = f"xpol|r|{approval_id}|{chain}"
    if len(callback_approve.encode("utf-8")) > 64 or len(callback_deny.encode("utf-8")) > 64:
        return

    request_type = str(flow.get("requestType") or "").strip().lower()
    token_display = str(flow.get("tokenDisplay") or "").strip()
    request_label = "Policy update"
    if request_type == "token_preapprove_add":
        request_label = "Preapprove token for trading"
    elif request_type == "token_preapprove_remove":
        request_label = "Revoke preapproved token"
    elif request_type == "global_approval_enable":
        request_label = "Enable Approve all (global trading)"
    elif request_type == "global_approval_disable":
        request_label = "Disable Approve all (global trading)"

    lines = [
        "Approve policy change",
        f"Request: {request_label}",
    ]
    if token_display:
        lines.append(f"Token: {token_display}")
    lines.extend(
        [
            f"Chain: {chain}",
            f"Approval ID: {approval_id}",
            "Status: approval_pending",
            "",
            "Tap Approve to apply (or Deny to reject).",
        ]
    )
    text = "\n".join(lines)
    buttons = json.dumps(
        [[{"text": "Approve", "callback_data": callback_approve}, {"text": "Deny", "callback_data": callback_deny}]],
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
        message_id = "unknown"
    _record_policy_approval_prompt(
        approval_id,
        {
            "channel": "telegram",
            "chainKey": chain,
            "to": chat_id,
            "threadId": thread_id,
            "messageId": message_id,
            "createdAt": utc_now(),
        },
    )


def _maybe_send_telegram_liquidity_approval_prompt(flow: dict[str, Any]) -> None:
    if _telegram_dispatch_suppressed_for_harness():
        return
    liquidity_intent_id = str(flow.get("liquidityIntentId") or "").strip()
    chain = str(flow.get("chainKey") or "").strip()
    if not liquidity_intent_id or not chain:
        return
    existing = _get_approval_prompt(liquidity_intent_id)
    if existing and str(existing.get("channel") or "") == "telegram":
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

    callback_approve = f"xliq|a|{liquidity_intent_id}|{chain}"
    callback_deny = f"xliq|r|{liquidity_intent_id}|{chain}"
    if len(callback_approve.encode("utf-8")) > 64 or len(callback_deny.encode("utf-8")) > 64:
        return

    action = str(flow.get("action") or "remove").strip().lower()
    dex = str(flow.get("dex") or "unknown").strip().lower() or "unknown"
    token_a = str(flow.get("tokenASymbol") or _token_symbol_for_display(chain, str(flow.get("tokenA") or "")) or "TOKEN").strip() or "TOKEN"
    token_b = str(flow.get("tokenBSymbol") or _token_symbol_for_display(chain, str(flow.get("tokenB") or "")) or "TOKEN").strip() or "TOKEN"
    amount_a = str(flow.get("amountA") or "").strip()
    amount_b = str(flow.get("amountB") or "").strip()
    position_id = str(flow.get("positionId") or "").strip()
    percent = str(flow.get("percent") or "").strip()

    lines = [
        "Approve liquidity action",
        f"Action: {action}",
        f"Pair: {token_a}/{token_b}",
        f"Chain: `{chain}`",
        f"DEX: `{dex}`",
        f"Intent ID: `{liquidity_intent_id}`",
        "Status: approval_pending",
    ]
    if position_id:
        lines.append(f"Position ID: `{position_id}`")
    if percent:
        lines.append(f"Percent: {percent}%")
    if amount_a or amount_b:
        lines.append(f"Amounts: {amount_a or '?'} / {amount_b or '?'}")
    lines.extend(["", "Tap Approve to execute (or Deny to reject)."])
    text = "\n".join(lines)

    buttons = json.dumps(
        [[{"text": "Approve", "callback_data": callback_approve}, {"text": "Deny", "callback_data": callback_deny}]],
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
        message_id = "unknown"
    _record_approval_prompt(
        liquidity_intent_id,
        {
            "channel": "telegram",
            "chainKey": chain,
            "to": chat_id,
            "threadId": thread_id,
            "messageId": message_id,
            "createdAt": utc_now(),
        },
    )


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
    if _telegram_dispatch_suppressed_for_harness():
        return
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
    token_in = _token_symbol_for_display(chain, token_in)
    token_out = _token_symbol_for_display(chain, token_out)
    slip = summary.get("slippageBps")
    slip_str = ""
    try:
        if slip is not None:
            slip_str = f" (slippage {int(slip)} bps)"
    except Exception:
        slip_str = ""

    if decision == "approved":
        text = (
            "Approval received.\n\n"
            f"• Pair: {amount} {token_in} -> {token_out}{slip_str}\n"
            f"• Trade ID: `{trade_id}`\n"
            f"• Chain: `{chain}`\n\n"
            "Executing now. I will send a final success/failure update after on-chain outcome is known."
        )
    else:
        reason_code = str(trade.get("reasonCode") or "").strip()
        reason_message = str(trade.get("reasonMessage") or "").strip()
        reason = reason_message or reason_code or "Denied."
        text = (
            "Denied swap\n"
            f"{amount} {token_in} -> {token_out}{slip_str}\n"
            f"Chain: {chain}\n"
            f"Trade: {trade_id}\n\n"
            f"Reason: {reason}"
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


def _maybe_send_telegram_trade_terminal_message(
    *,
    trade_id: str,
    chain: str,
    status: str,
    tx_hash: str | None = None,
    reason_message: str | None = None,
) -> None:
    if _telegram_dispatch_suppressed_for_harness():
        return
    normalized = str(status or "").strip().lower()
    if normalized not in {"filled", "failed", "rejected", "verification_timeout"}:
        return
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

    tx_hash_clean = str(tx_hash or "").strip()
    # Fail closed for owner UX truthfulness: do not send a success terminal message
    # when runtime cannot provide a transaction hash.
    if normalized == "filled" and not tx_hash_clean:
        normalized = "failed"
        if not str(reason_message or "").strip():
            reason_message = "Execution reported filled without tx hash; treating as unverified."
    tx_line = f"\nTx: `{tx_hash_clean}`" if tx_hash_clean else ""
    if normalized == "filled":
        text = (
            "Swap completed.\n\n"
            f"Trade: `{trade_id}`\n"
            f"Chain: `{chain}`"
            f"{tx_line}"
        )
    else:
        reason = str(reason_message or "").strip() or "Execution failed."
        text = (
            "Swap failed.\n\n"
            f"Trade: `{trade_id}`\n"
            f"Chain: `{chain}`\n"
            f"Reason: {reason}"
            f"{tx_line}"
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
    # Telegram inline buttons should be cleared in callback/web paths;
    # do not delete the original message here.
    _remove_approval_prompt(trade_id)


def _normalize_telegram_target(value: str) -> str:
    raw = str(value or "").strip()
    if raw.startswith("telegram:"):
        return raw[len("telegram:") :]
    return raw


def _resolve_telegram_bot_token() -> str | None:
    for candidate in (
        os.environ.get("XCLAW_TELEGRAM_BOT_TOKEN"),
        os.environ.get("TELEGRAM_BOT_TOKEN"),
    ):
        token = str(candidate or "").strip()
        if token:
            return token

    try:
        openclaw = _require_openclaw_bin()
    except Exception:
        return None
    proc = _run_subprocess(
        [openclaw, "config", "get", "channels.telegram.botToken", "--json"],
        timeout_sec=5,
        kind="openclaw_config_get",
    )
    if proc.returncode != 0:
        return None
    raw = str(proc.stdout or "").strip()
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, str) and parsed.strip():
            return parsed.strip()
    except Exception:
        pass
    if raw.startswith('"') and raw.endswith('"'):
        raw = raw[1:-1]
    raw = raw.strip()
    return raw or None


def _approval_prompt_store_ops(subject_type: str) -> tuple[Any, Any]:
    normalized = str(subject_type or "").strip().lower()
    if normalized == "trade":
        return _get_approval_prompt, _remove_approval_prompt
    if normalized == "transfer":
        return _get_transfer_approval_prompt, _remove_transfer_approval_prompt
    if normalized == "policy":
        return _get_policy_approval_prompt, _remove_policy_approval_prompt
    raise WalletStoreError(f"Unsupported subject_type '{subject_type}'.")


def _clear_telegram_approval_buttons(subject_type: str, subject_id: str) -> dict[str, Any]:
    if _telegram_dispatch_suppressed_for_harness():
        get_prompt, remove_prompt = _approval_prompt_store_ops(subject_type)
        entry = get_prompt(subject_id)
        if entry:
            remove_prompt(subject_id)
        return {
            "ok": True,
            "code": "telegram_dispatch_suppressed",
            "subjectType": subject_type,
            "subjectId": subject_id,
            "promptCleanup": {
                "ok": True,
                "code": "telegram_dispatch_suppressed",
                "channel": "telegram",
            },
        }
    get_prompt, remove_prompt = _approval_prompt_store_ops(subject_type)
    entry = get_prompt(subject_id)
    if not entry:
        return {
            "ok": False,
            "code": "prompt_not_found",
            "subjectType": subject_type,
            "subjectId": subject_id,
            "promptCleanup": {"ok": False, "code": "prompt_not_found", "channel": "telegram"},
        }
    if str(entry.get("channel") or "") != "telegram":
        remove_prompt(subject_id)
        return {
            "ok": True,
            "code": "non_telegram_removed",
            "subjectType": subject_type,
            "subjectId": subject_id,
            "promptCleanup": {"ok": True, "code": "non_telegram_removed", "channel": str(entry.get("channel") or "")},
        }
    chat_id = _normalize_telegram_target(str(entry.get("to") or ""))
    message_id = str(entry.get("messageId") or "").strip()
    if not chat_id:
        remove_prompt(subject_id)
        return {
            "ok": False,
            "code": "missing_target",
            "subjectType": subject_type,
            "subjectId": subject_id,
            "promptCleanup": {"ok": False, "code": "missing_target", "channel": "telegram", "messageId": message_id or None},
        }
    if not message_id or message_id == "unknown":
        remove_prompt(subject_id)
        return {
            "ok": False,
            "code": "missing_message_id",
            "subjectType": subject_type,
            "subjectId": subject_id,
            "promptCleanup": {"ok": False, "code": "missing_message_id", "channel": "telegram", "messageId": message_id or None},
        }
    try:
        numeric_message_id = int(message_id)
    except Exception:
        remove_prompt(subject_id)
        return {
            "ok": False,
            "code": "invalid_message_id",
            "subjectType": subject_type,
            "subjectId": subject_id,
            "promptCleanup": {"ok": False, "code": "invalid_message_id", "channel": "telegram", "messageId": message_id},
        }
    bot_token = _resolve_telegram_bot_token()
    if not bot_token:
        openclaw_missing = shutil.which("openclaw") is None
        return {
            "ok": False,
            "code": "openclaw_missing" if openclaw_missing else "telegram_bot_token_missing",
            "subjectType": subject_type,
            "subjectId": subject_id,
            "promptCleanup": {
                "ok": False,
                "code": "openclaw_missing" if openclaw_missing else "telegram_bot_token_missing",
                "channel": "telegram",
                "messageId": message_id,
            },
        }

    endpoint = f"https://api.telegram.org/bot{urllib.parse.quote(bot_token, safe='')}/editMessageReplyMarkup"
    req_payload = {
        "chat_id": chat_id,
        "message_id": numeric_message_id,
        "reply_markup": {"inline_keyboard": []},
    }
    request = urllib.request.Request(
        url=endpoint,
        data=json.dumps(req_payload).encode("utf-8"),
        headers={"content-type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            response_body = response.read().decode("utf-8", errors="replace").strip()
        remove_prompt(subject_id)
        return {
            "ok": True,
            "code": "buttons_cleared",
            "subjectType": subject_type,
            "subjectId": subject_id,
            "promptCleanup": {
                "ok": True,
                "code": "buttons_cleared",
                "channel": "telegram",
                "messageId": message_id,
                "response": response_body[:300] if response_body else None,
            },
        }
    except urllib.error.HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            body = ""
        body_trimmed = body.strip()
        if "message is not modified" in body_trimmed.lower():
            remove_prompt(subject_id)
            return {
                "ok": True,
                "code": "already_cleared",
                "subjectType": subject_type,
                "subjectId": subject_id,
                "promptCleanup": {
                    "ok": True,
                    "code": "already_cleared",
                    "channel": "telegram",
                    "messageId": message_id,
                },
            }
        return {
            "ok": False,
            "code": "telegram_api_failed",
            "subjectType": subject_type,
            "subjectId": subject_id,
            "promptCleanup": {
                "ok": False,
                "code": "telegram_api_failed",
                "channel": "telegram",
                "messageId": message_id,
                "error": (body_trimmed or str(exc))[:300],
            },
        }
    except Exception as exc:
        return {
            "ok": False,
            "code": "telegram_api_failed",
            "subjectType": subject_type,
            "subjectId": subject_id,
            "promptCleanup": {
                "ok": False,
                "code": "telegram_api_failed",
                "channel": "telegram",
                "messageId": message_id,
                "error": str(exc)[:300],
            },
        }


def _cleanup_trade_approval_prompt(trade_id: str) -> dict[str, Any]:
    result = _clear_telegram_approval_buttons("trade", trade_id)
    return dict(result.get("promptCleanup") or {"ok": bool(result.get("ok")), "code": str(result.get("code") or "unknown")})


def _maybe_delete_telegram_transfer_approval_prompt(approval_id: str) -> None:
    _ = _clear_telegram_approval_buttons("transfer", approval_id)


def _cleanup_transfer_approval_prompt(approval_id: str) -> dict[str, Any]:
    result = _clear_telegram_approval_buttons("transfer", approval_id)
    return dict(result.get("promptCleanup") or {"ok": bool(result.get("ok")), "code": str(result.get("code") or "unknown")})


def _cleanup_policy_approval_prompt(approval_id: str) -> dict[str, Any]:
    result = _clear_telegram_approval_buttons("policy", approval_id)
    return dict(result.get("promptCleanup") or {"ok": bool(result.get("ok")), "code": str(result.get("code") or "unknown")})


def _fetch_transfer_decision_inbox(chain: str, limit: int = 20) -> list[dict[str, Any]]:
    safe_chain = str(chain or "").strip()
    safe_limit = max(1, min(int(limit), 50))
    query = urllib.parse.urlencode({"chainKey": safe_chain, "limit": str(safe_limit)})
    status_code, body = _api_request("GET", f"/agent/transfer-decisions/inbox?{query}")
    if status_code < 200 or status_code >= 300:
        raise WalletStoreError(
            f"{str(body.get('code', 'api_error'))}: {str(body.get('message', f'transfer decision inbox fetch failed ({status_code})'))}"
        )
    rows = body.get("decisions")
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def _ack_transfer_decision_inbox(
    decision_id: str,
    status: str,
    reason_code: str | None = None,
    reason_message: str | None = None,
) -> tuple[int, dict[str, Any]]:
    payload: dict[str, Any] = {
        "schemaVersion": 1,
        "decisionId": decision_id,
        "status": status,
    }
    if reason_code:
        payload["reasonCode"] = reason_code
    if reason_message:
        payload["reasonMessage"] = reason_message
    return _api_request("POST", "/agent/transfer-decisions/inbox", payload=payload, include_idempotency=True)


def _run_decide_transfer_inline(
    approval_id: str,
    decision: str,
    chain: str,
    source: str,
    reason_message: str | None,
) -> tuple[int, dict[str, Any]]:
    nested = argparse.Namespace(
        approval_id=approval_id,
        decision=decision,
        reason_message=reason_message,
        source=source,
        idempotency_key=None,
        decision_at=None,
        chain=chain,
        json=True,
    )
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = cmd_approvals_decide_transfer(nested)
    raw = buf.getvalue().strip()
    payload: dict[str, Any] = {"ok": bool(code == 0), "code": "decision_result_unavailable", "message": "Decision result unavailable."}
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                payload = parsed
        except Exception:
            payload = {"ok": False, "code": "decision_parse_failed", "message": raw[:400]}
    return code, payload


def _run_approvals_sync_inline(chain: str) -> tuple[int, dict[str, Any]]:
    nested = argparse.Namespace(chain=chain, json=True)
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = cmd_approvals_sync(nested)
    raw = buf.getvalue().strip()
    payload: dict[str, Any] = {"ok": bool(code == 0), "code": "sync_result_unavailable", "message": "Sync result unavailable."}
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                payload = parsed
        except Exception:
            payload = {"ok": False, "code": "sync_parse_failed", "message": raw[:400]}
    return code, payload


def _publish_runtime_signing_readiness(chain: str, readiness: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    payload = {
        "schemaVersion": 1,
        "chainKey": chain,
        "walletSigningReady": bool(readiness.get("walletSigningReady")),
        "walletSigningReasonCode": readiness.get("walletSigningReasonCode"),
        "walletSigningCheckedAt": readiness.get("walletSigningCheckedAt"),
    }
    return _api_request("POST", "/agent/runtime-readiness", payload=payload, include_idempotency=True)


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
    if channel == "telegram":
        return {"sent": False, "reason": "telegram_channel_skipped"}
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
        transfer_decisions_checked = 0
        transfer_decisions_applied = 0
        transfer_decisions_failed = 0
        transfer_decision_failures: list[dict[str, Any]] = []
        transfer_decisions = _fetch_transfer_decision_inbox(chain, limit=20)
        for row in transfer_decisions:
            decision_id = str(row.get("decisionId") or "").strip()
            approval_id = str(row.get("approvalId") or "").strip()
            decision = str(row.get("decision") or "").strip().lower()
            decision_chain = str(row.get("chainKey") or chain).strip()
            reason_message = str(row.get("reasonMessage") or "").strip() or None
            source = str(row.get("source") or "web").strip().lower() or "web"
            if not decision_id or not approval_id or decision not in {"approve", "deny"} or not decision_chain:
                transfer_decisions_failed += 1
                transfer_decision_failures.append(
                    {
                        "decisionId": decision_id,
                        "approvalId": approval_id,
                        "code": "invalid_inbox_row",
                        "message": "Missing required transfer decision inbox fields.",
                    }
                )
                if decision_id:
                    try:
                        _ack_transfer_decision_inbox(
                            decision_id,
                            "failed",
                            reason_code="invalid_inbox_row",
                            reason_message="Missing required transfer decision inbox fields.",
                        )
                    except Exception:
                        pass
                continue

            transfer_decisions_checked += 1
            code, payload = _run_decide_transfer_inline(
                approval_id=approval_id,
                decision=decision,
                chain=decision_chain,
                source=source,
                reason_message=reason_message,
            )
            payload_code = str(payload.get("code") or "").strip() or ("ok" if code == 0 else "runtime_decision_failed")
            payload_message = str(payload.get("message") or "").strip() or (
                "Transfer decision applied." if code == 0 else "Transfer decision failed."
            )
            ack_status = "applied" if code == 0 else "failed"
            ack_status_code = 0
            try:
                ack_status_code, _ = _ack_transfer_decision_inbox(
                    decision_id,
                    ack_status,
                    reason_code=payload_code if ack_status == "failed" else None,
                    reason_message=payload_message if ack_status == "failed" else None,
                )
            except Exception:
                ack_status_code = 0
            if ack_status_code < 200 or ack_status_code >= 300:
                transfer_decision_failures.append(
                    {
                        "decisionId": decision_id,
                        "approvalId": approval_id,
                        "code": "inbox_ack_failed",
                        "message": "Decision processing finished but inbox ack failed.",
                    }
                )
            if code == 0:
                transfer_decisions_applied += 1
            else:
                transfer_decisions_failed += 1
                transfer_decision_failures.append(
                    {
                        "decisionId": decision_id,
                        "approvalId": approval_id,
                        "code": payload_code,
                        "message": payload_message,
                    }
                )
        return ok(
            "Approval prompts synced.",
            chain=chain,
            checked=checked,
            deleted=deleted,
            skipped=skipped,
            failures=failures or None,
            transferDecisionsChecked=transfer_decisions_checked,
            transferDecisionsApplied=transfer_decisions_applied,
            transferDecisionsFailed=transfer_decisions_failed,
            transferDecisionFailures=transfer_decision_failures or None,
        )
    except Exception as exc:
        return fail("approvals_sync_failed", str(exc), "Verify API auth and OpenClaw availability, then retry.", {"chain": chain}, exit_code=1)


def cmd_approvals_run_loop(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    chain = str(args.chain or "").strip()
    if not chain:
        return fail("invalid_input", "chain is required.", "Provide --chain and retry.", exit_code=2)
    interval_ms_raw = int(args.interval_ms) if isinstance(args.interval_ms, int) else APPROVAL_RUN_LOOP_INTERVAL_MS
    interval_ms = max(250, min(interval_ms_raw, 60000))
    once = bool(getattr(args, "once", False))
    iteration = 0
    backoff_ms = interval_ms
    consecutive_failures = 0
    api_base = str(os.environ.get("XCLAW_API_BASE_URL") or "").strip()
    parsed_base = urllib.parse.urlparse(api_base) if api_base else None
    api_base_host = str(parsed_base.netloc or "").strip() if parsed_base else ""
    agent_id = str(os.environ.get("XCLAW_AGENT_ID") or "").strip()
    while True:
        iteration += 1
        cycle_started = time.time()
        readiness = _runtime_wallet_signing_readiness(chain)
        readiness_status = 0
        readiness_code = "ok"
        try:
            readiness_status, readiness_body = _publish_runtime_signing_readiness(chain, readiness)
            if readiness_status < 200 or readiness_status >= 300:
                readiness_code = str(readiness_body.get("code", "api_error"))
        except Exception as exc:
            readiness_status = 0
            readiness_code = f"publish_error:{str(exc)[:120]}"
        sync_code, sync_payload = _run_approvals_sync_inline(chain)
        cycle_ok = sync_code == 0
        if cycle_ok:
            consecutive_failures = 0
            backoff_ms = interval_ms
        else:
            consecutive_failures += 1
            backoff_ms = min(APPROVAL_RUN_LOOP_BACKOFF_MAX_MS, max(interval_ms, backoff_ms * 2))
        elapsed_ms = int((time.time() - cycle_started) * 1000)
        cycle_log = {
            "event": "approvals_run_loop_cycle",
            "chain": chain,
            "apiBaseHost": api_base_host or None,
            "agentId": agent_id or None,
            "iteration": iteration,
            "ok": cycle_ok,
            "syncCode": str(sync_payload.get("code") or ("ok" if cycle_ok else "sync_failed")),
            "transferDecisionsChecked": int(sync_payload.get("transferDecisionsChecked") or 0),
            "transferDecisionsApplied": int(sync_payload.get("transferDecisionsApplied") or 0),
            "transferDecisionsFailed": int(sync_payload.get("transferDecisionsFailed") or 0),
            "walletSigningReady": bool(readiness.get("walletSigningReady")),
            "walletSigningReasonCode": readiness.get("walletSigningReasonCode"),
            "readinessPublishStatus": readiness_status,
            "readinessPublishCode": readiness_code,
            "consecutiveFailures": consecutive_failures,
            "elapsedMs": elapsed_ms,
            "sleepMs": 0 if once else (interval_ms if cycle_ok else backoff_ms),
            "at": utc_now(),
        }
        print(json.dumps(cycle_log, separators=(",", ":")), file=sys.stderr)
        if once:
            summary = dict(sync_payload)
            summary.setdefault("ok", cycle_ok)
            summary.setdefault("code", "ok" if cycle_ok else "approvals_run_loop_cycle_failed")
            summary["chain"] = chain
            summary["iteration"] = iteration
            summary["walletSigningReady"] = bool(readiness.get("walletSigningReady"))
            summary["walletSigningReasonCode"] = readiness.get("walletSigningReasonCode")
            summary["readinessPublishStatus"] = readiness_status
            summary["readinessPublishCode"] = readiness_code
            summary["elapsedMs"] = elapsed_ms
            return emit(summary)
        time.sleep((interval_ms if cycle_ok else backoff_ms) / 1000.0)


def cmd_approvals_cleanup_spot(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    trade_id = str(args.trade_id or "").strip()
    if not trade_id:
        return fail("invalid_input", "trade_id is required.", "Provide --trade-id trd_... and retry.", exit_code=2)

    result = _clear_telegram_approval_buttons("trade", trade_id)
    cleanup = dict(result.get("promptCleanup") or {})
    if bool(result.get("ok")):
        return ok(
            "Spot approval prompt cleanup completed.",
            tradeId=trade_id,
            subjectType="trade",
            subjectId=trade_id,
            promptCleanup=cleanup,
            actionHint="No additional action required.",
        )
    return fail(
        str(result.get("code") or "approval_prompt_cleanup_failed"),
        "Spot approval prompt button clear failed.",
        "Retry approvals cleanup after prompt metadata sync.",
        {"tradeId": trade_id, "subjectType": "trade", "subjectId": trade_id, "promptCleanup": cleanup},
        exit_code=1,
    )


def cmd_approvals_clear_prompt(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    subject_type = str(args.subject_type or "").strip().lower()
    subject_id = str(args.subject_id or "").strip()
    if subject_type not in {"trade", "transfer", "policy"}:
        return fail(
            "invalid_input",
            "subject_type must be trade|transfer|policy.",
            "Use --subject-type trade|transfer|policy.",
            {"subjectType": subject_type},
            exit_code=2,
        )
    if not subject_id:
        return fail(
            "invalid_input",
            "subject_id is required.",
            "Use --subject-id <trd_|xfr_|ppr_...>.",
            {"subjectType": subject_type},
            exit_code=2,
        )
    result = _clear_telegram_approval_buttons(subject_type, subject_id)
    if bool(result.get("ok")):
        return ok(
            "Approval prompt button clear completed.",
            subjectType=subject_type,
            subjectId=subject_id,
            promptCleanup=result.get("promptCleanup"),
            actionHint="No additional action required.",
        )
    return fail(
        str(result.get("code") or "approval_prompt_cleanup_failed"),
        "Approval prompt button clear failed.",
        "Retry clear-prompt after prompt metadata sync.",
        {
            "subjectType": subject_type,
            "subjectId": subject_id,
            "promptCleanup": result.get("promptCleanup"),
        },
        exit_code=1,
    )


def _run_resume_spot_inline(trade_id: str, chain: str) -> tuple[int, dict[str, Any]]:
    nested = argparse.Namespace(trade_id=trade_id, chain=chain, json=True)
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = cmd_approvals_resume_spot(nested)
    raw = buf.getvalue().strip()
    payload: dict[str, Any] = {
        "ok": bool(code == 0),
        "code": "resume_result_unavailable",
        "message": "Resume result unavailable.",
        "tradeId": trade_id,
        "chain": chain,
    }
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                payload = parsed
        except Exception:
            payload = {"ok": False, "code": "resume_parse_failed", "message": raw[:400], "tradeId": trade_id, "chain": chain}
    return code, payload


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

        # If resume failed before any status transition, avoid leaving the trade stuck as approved.
        try:
            latest_after_fail = _read_trade_details(trade_id)
            latest_status = str(latest_after_fail.get("status") or "").strip().lower()
            if latest_status == "approved":
                reason_code = str(payload.get("code") or "resume_failed").strip() or "resume_failed"
                reason_message = str(payload.get("message") or "Spot trade resume failed before execution status transition.").strip()
                _post_trade_status(
                    trade_id,
                    "approved",
                    "failed",
                    {
                        "reasonCode": reason_code[:64],
                        "reasonMessage": reason_message[:500],
                    },
                )
                payload["statusMirrored"] = True
                payload["mirroredFromStatus"] = "approved"
                payload["mirroredToStatus"] = "failed"
            else:
                payload["statusMirrored"] = False
        except Exception:
            payload["statusMirrored"] = False

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
        cleanup = _cleanup_transfer_approval_prompt(approval_id)
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
    if status in {"executing", "verifying"}:
        if _is_stale_executing_transfer_flow(flow):
            flow["status"] = "approved"
            flow["updatedAt"] = utc_now()
            _record_pending_transfer_flow(approval_id, flow)
            _mirror_transfer_approval(flow)
            return emit(_execute_pending_transfer_flow(flow))
        return ok(
            "Transfer resume skipped: approval already in progress.",
            approvalId=approval_id,
            chain=chain,
            status=status,
            txHash=flow.get("txHash"),
            skipped=True,
            inProgress=True,
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


def cmd_approvals_decide_spot(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    trade_id = str(args.trade_id or "").strip()
    decision = str(args.decision or "").strip().lower()
    chain = str(args.chain or "").strip()
    source = str(getattr(args, "source", "") or "").strip().lower() or "runtime"
    reason_message = str(args.reason_message or "").strip()
    idempotency_key = str(getattr(args, "idempotency_key", "") or "").strip() or None
    decision_at_raw = str(getattr(args, "decision_at", "") or "").strip()
    decision_at = None
    if decision_at_raw:
        try:
            decision_at = _parse_decision_at(decision_at_raw)
        except Exception:
            return fail("invalid_input", "decision_at must be ISO-8601.", "Use --decision-at <iso8601>.", {"decisionAt": decision_at_raw}, exit_code=2)
    if not trade_id:
        return fail("invalid_input", "trade_id is required.", "Provide --trade-id trd_... and retry.", exit_code=2)
    if decision not in {"approve", "reject"}:
        return fail("invalid_input", "decision must be approve|reject.", "Use --decision approve|reject.", exit_code=2)

    trade = _read_trade_details(trade_id)
    status = str(trade.get("status") or "").strip().lower()
    if not chain:
        chain = str(trade.get("chainKey") or "").strip()
    if not chain:
        return fail("invalid_input", "chain is required.", "Provide --chain and retry.", {"tradeId": trade_id}, exit_code=2)

    if status in {"filled", "failed", "rejected", "expired", "verification_timeout"}:
        cleanup = _cleanup_trade_approval_prompt(trade_id)
        return ok(
            "Trade decision converged on terminal state.",
            subjectType="trade",
            subjectId=trade_id,
            decision=decision,
            source=source,
            chain=chain,
            fromStatus=status,
            toStatus=status,
            executionStatus=status,
            txHash=trade.get("txHash"),
            promptCleanup=cleanup,
            prodDispatch={"mode": "handled_by_web_or_callback"},
            actionHint="No additional action required.",
            converged=True,
            status=status,
            resume=None,
        )

    if decision == "reject":
        from_status = "approval_pending" if status == "approval_pending" else status
        if status == "approval_pending":
            _post_trade_status(
                trade_id,
                "approval_pending",
                "rejected",
                {
                    "reasonCode": "approval_rejected",
                    "reasonMessage": reason_message or "Denied by owner.",
                },
                idempotency_key=idempotency_key,
                decision_at=decision_at,
            )
            trade = _read_trade_details(trade_id)
            status = str(trade.get("status") or "").strip().lower()
        cleanup = _cleanup_trade_approval_prompt(trade_id)
        try:
            _maybe_send_telegram_decision_message(
                trade_id=trade_id,
                chain=chain,
                decision="rejected",
                summary=None,
                trade=trade if isinstance(trade, dict) else None,
            )
        except Exception:
            pass
        return ok(
            "Trade rejected.",
            subjectType="trade",
            subjectId=trade_id,
            decision=decision,
            source=source,
            chain=chain,
            fromStatus=from_status,
            toStatus="rejected",
            executionStatus="rejected",
            txHash=trade.get("txHash"),
            promptCleanup=cleanup,
            prodDispatch={"mode": "handled_by_web_or_callback"},
            actionHint="Trade was denied and will not execute.",
            status="rejected",
            resume=None,
        )

    from_status = status
    if status == "approval_pending":
        _post_trade_status(
            trade_id,
            "approval_pending",
            "approved",
            {"reasonCode": None, "reasonMessage": None},
            idempotency_key=idempotency_key,
            decision_at=decision_at,
        )
        status = "approved"
    cleanup = _cleanup_trade_approval_prompt(trade_id)
    try:
        _maybe_send_telegram_decision_message(
            trade_id=trade_id,
            chain=chain,
            decision="approved",
            summary=None,
            trade=_read_trade_details(trade_id),
        )
    except Exception:
        pass
    resume_code, resume_payload = _run_resume_spot_inline(trade_id, chain)
    tx_hash = str(resume_payload.get("txHash") or "").strip()
    raw_exec_status = str(
        resume_payload.get("executionStatus") or resume_payload.get("status") or ""
    ).strip().lower()
    exec_status = raw_exec_status or "failed"
    # Fail closed: never claim terminal "filled" when tx hash is missing.
    if exec_status == "filled" and not tx_hash:
        exec_status = "failed"
        resume_payload = {
            **resume_payload,
            "code": "terminal_status_unverified",
            "message": str(
                resume_payload.get("message")
                or "Runtime reported filled without tx hash; treating as failed/unverified."
            ),
            "reasonCode": str(resume_payload.get("reasonCode") or "terminal_status_unverified"),
        }
    try:
        _maybe_send_telegram_trade_terminal_message(
            trade_id=trade_id,
            chain=chain,
            status=exec_status,
            tx_hash=tx_hash or None,
            reason_message=str(resume_payload.get("message") or "").strip() or None,
        )
    except Exception:
        pass
    return emit(
        {
            "ok": bool(resume_code == 0),
            "code": str(resume_payload.get("code") or ("ok" if resume_code == 0 else "resume_failed")),
            "message": str(resume_payload.get("message") or ("Trade approved and resumed." if resume_code == 0 else "Trade resume failed.")),
            "subjectType": "trade",
            "subjectId": trade_id,
            "decision": decision,
            "source": source,
            "chain": chain,
            "fromStatus": from_status,
            "toStatus": "approved",
            "executionStatus": exec_status,
            "txHash": resume_payload.get("txHash"),
            "promptCleanup": cleanup,
            "prodDispatch": {"mode": "handled_by_web_or_callback"},
            "actionHint": "Execution resumed; monitor terminal status.",
            "status": exec_status,
            "resume": resume_payload,
        }
    )


def cmd_approvals_decide_liquidity(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    liquidity_intent_id = str(args.intent_id or "").strip()
    decision = str(args.decision or "").strip().lower()
    chain = str(args.chain or "").strip()
    source = str(getattr(args, "source", "") or "").strip().lower() or "runtime"
    reason_message = str(args.reason_message or "").strip()
    if not liquidity_intent_id:
        return fail("invalid_input", "intent_id is required.", "Provide --intent-id liq_... and retry.", exit_code=2)
    if decision not in {"approve", "reject"}:
        return fail("invalid_input", "decision must be approve|reject.", "Use --decision approve|reject.", exit_code=2)
    if not chain:
        return fail("invalid_input", "chain is required.", "Provide --chain <chainKey> and retry.", {"liquidityIntentId": liquidity_intent_id}, exit_code=2)

    try:
        intent = _read_liquidity_intent(liquidity_intent_id, chain)
        status = str(intent.get("status") or "").strip().lower()
        if status in {"filled", "failed", "rejected", "expired", "verification_timeout"}:
            return ok(
                "Liquidity decision converged on terminal state.",
                subjectType="liquidity",
                subjectId=liquidity_intent_id,
                decision=decision,
                source=source,
                chain=chain,
                status=status,
                converged=True,
                txHash=intent.get("txHash"),
            )
        if decision == "reject":
            if status == "approval_pending":
                _post_liquidity_status(
                    liquidity_intent_id,
                    "rejected",
                    {"reasonCode": "approval_rejected", "reasonMessage": reason_message or "Denied by owner."},
                )
                status = "rejected"
            return ok(
                "Liquidity intent rejected.",
                subjectType="liquidity",
                subjectId=liquidity_intent_id,
                decision=decision,
                source=source,
                chain=chain,
                status=status,
                executionStatus=status,
            )
        if status == "approval_pending":
            _post_liquidity_status(liquidity_intent_id, "approved")
            status = "approved"
        if status != "approved":
            return fail(
                "liquidity_not_actionable",
                f"Liquidity decision is not actionable from status '{status}'.",
                "Approve only approval_pending intents.",
                {"liquidityIntentId": liquidity_intent_id, "chain": chain, "status": status},
                exit_code=1,
            )
        execute_code, execute_payload = _run_liquidity_execute_inline(liquidity_intent_id, chain)
        if isinstance(execute_payload, dict):
            execute_payload.setdefault("subjectType", "liquidity")
            execute_payload.setdefault("subjectId", liquidity_intent_id)
            execute_payload.setdefault("decision", decision)
            execute_payload.setdefault("source", source)
        return emit(execute_payload) if isinstance(execute_payload, dict) else execute_code
    except WalletStoreError as exc:
        message = str(exc)
        # Convergence fallback: callback retries can race with fast terminal transitions
        # and remove the intent from the non-terminal pending scope.
        if source == "telegram" and "was not found in pending scope" in message:
            return ok(
                "Liquidity decision converged outside pending scope.",
                subjectType="liquidity",
                subjectId=liquidity_intent_id,
                decision=decision,
                source=source,
                chain=chain,
                status="converged_unknown",
                converged=True,
            )
        return fail(
            "liquidity_decision_failed",
            message,
            "Inspect liquidity decision path and retry.",
            {"liquidityIntentId": liquidity_intent_id, "chain": chain},
            exit_code=1,
        )
    except Exception as exc:
        return fail(
            "liquidity_decision_failed",
            str(exc),
            "Inspect liquidity decision path and retry.",
            {"liquidityIntentId": liquidity_intent_id, "chain": chain},
            exit_code=1,
        )


def cmd_approvals_decide_policy(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    approval_id = str(args.approval_id or "").strip()
    decision = str(args.decision or "").strip().lower()
    chain = str(args.chain or "").strip()
    source = str(getattr(args, "source", "") or "").strip().lower() or "runtime"
    reason_message = str(args.reason_message or "").strip()
    idempotency_key = str(getattr(args, "idempotency_key", "") or "").strip() or None
    decision_at_raw = str(getattr(args, "decision_at", "") or "").strip()
    try:
        decision_at = _parse_decision_at(decision_at_raw or None)
    except Exception:
        return fail("invalid_input", "decision_at must be ISO-8601.", "Use --decision-at <iso8601>.", {"decisionAt": decision_at_raw}, exit_code=2)
    if not approval_id:
        return fail("invalid_input", "approval_id is required.", "Provide --approval-id ppr_... and retry.", exit_code=2)
    if decision not in {"approve", "reject"}:
        return fail("invalid_input", "decision must be approve|reject.", "Use --decision approve|reject.", exit_code=2)

    path = f"/policy-approvals/{urllib.parse.quote(approval_id)}/decision"
    to_status = "approved" if decision == "approve" else "rejected"
    payload: dict[str, Any] = {
        "policyApprovalId": approval_id,
        "fromStatus": "approval_pending",
        "toStatus": to_status,
        "at": decision_at,
    }
    if reason_message:
        payload["reasonMessage"] = reason_message
    status_code, body = _api_request("POST", path, payload=payload, include_idempotency=True, idempotency_key=idempotency_key)
    if status_code < 200 or status_code >= 300:
        return fail(
            str(body.get("code", "api_error")),
            str(body.get("message", f"policy decision failed ({status_code})")),
            str(body.get("actionHint", "Refresh policy approvals and retry.")),
            {"approvalId": approval_id, "status": status_code, "source": source},
            exit_code=1,
        )
    cleanup = _cleanup_policy_approval_prompt(approval_id)
    return ok(
        "Policy decision applied.",
        subjectType="policy",
        subjectId=approval_id,
        decision=decision,
        source=source,
        chain=chain or body.get("chainKey"),
        fromStatus="approval_pending",
        toStatus=to_status,
        executionStatus=to_status,
        promptCleanup=cleanup,
        prodDispatch={"mode": "handled_by_web_or_callback"},
        actionHint=(
            "Policy update was applied."
            if to_status == "approved"
            else "Policy update was rejected."
        ),
        status=to_status,
        txHash=body.get("txHash"),
        resume=None,
    )


def cmd_approvals_decide_transfer(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    approval_id = str(args.approval_id or "").strip()
    decision = str(args.decision or "").strip().lower()
    source = str(getattr(args, "source", "") or "").strip().lower() or "runtime"
    decision_at_raw = str(getattr(args, "decision_at", "") or "").strip()
    if decision_at_raw:
        try:
            _parse_decision_at(decision_at_raw)
        except Exception:
            return fail("invalid_input", "decision_at must be ISO-8601.", "Use --decision-at <iso8601>.", {"decisionAt": decision_at_raw}, exit_code=2)
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
    flow_token_symbol = str(flow.get("tokenSymbol") or ("NATIVE" if flow_transfer_type == "native" else "TOKEN")).strip()
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
        cleanup = _cleanup_transfer_approval_prompt(approval_id)
        return ok(
            "Transfer decision converged on terminal approval.",
            subjectType="transfer",
            subjectId=approval_id,
            decision=decision,
            source=source,
            approvalId=approval_id,
            chain=chain,
            status=status,
            executionStatus=status,
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
            fromStatus=status,
            toStatus=status,
            promptCleanup=cleanup,
            prodDispatch={"mode": "handled_by_web_or_callback"},
            actionHint="No additional action required.",
        )
    if status in {"executing", "verifying"}:
        cleanup = _cleanup_transfer_approval_prompt(approval_id)
        return ok(
            "Transfer decision already in progress.",
            subjectType="transfer",
            subjectId=approval_id,
            decision=decision,
            source=source,
            approvalId=approval_id,
            chain=chain,
            status=status,
            executionStatus=status,
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
            inProgress=True,
            fromStatus=status,
            toStatus=status,
            promptCleanup=cleanup,
            prodDispatch={"mode": "handled_by_web_or_callback"},
            actionHint="Transfer already in progress.",
        )
    if status == "approved" and decision == "deny":
        cleanup = _cleanup_transfer_approval_prompt(approval_id)
        return ok(
            "Transfer decision converged on approved approval.",
            subjectType="transfer",
            subjectId=approval_id,
            decision=decision,
            source=source,
            approvalId=approval_id,
            chain=chain,
            status="approved",
            executionStatus="approved",
            txHash=flow.get("txHash"),
            amountWei=flow.get("amountWei"),
            amount=flow_amount_human,
            amountUnit=flow_amount_unit,
            amountDisplay=flow_amount_display,
            policyBlockedAtCreate=bool(flow.get("policyBlockedAtCreate", False)),
            policyBlockReasonCode=flow.get("policyBlockReasonCode"),
            policyBlockReasonMessage=flow.get("policyBlockReasonMessage"),
            executionMode=flow.get("executionMode"),
            converged=True,
            fromStatus="approved",
            toStatus="approved",
            promptCleanup=cleanup,
            prodDispatch={"mode": "handled_by_web_or_callback"},
            actionHint="Transfer already approved.",
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
        cleanup = _cleanup_transfer_approval_prompt(approval_id)
        return ok(
            "Transfer denied.",
            subjectType="transfer",
            subjectId=approval_id,
            decision=decision,
            source=source,
            approvalId=approval_id,
            chain=chain,
            status="rejected",
            executionStatus="rejected",
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
            fromStatus=status,
            toStatus="rejected",
            promptCleanup=cleanup,
            prodDispatch={"mode": "handled_by_web_or_callback"},
            actionHint="Transfer was denied and will not execute.",
        )

    flow["status"] = "approved"
    flow["decidedAt"] = utc_now()
    flow["updatedAt"] = flow["decidedAt"]
    _record_pending_transfer_flow(approval_id, flow)
    _mirror_transfer_approval(flow)
    cleanup = _cleanup_transfer_approval_prompt(approval_id)
    payload = _execute_pending_transfer_flow(flow)
    if isinstance(payload, dict):
        payload.setdefault("subjectType", "transfer")
        payload.setdefault("subjectId", approval_id)
        payload.setdefault("decision", decision)
        payload.setdefault("source", source)
        payload.setdefault("executionStatus", str(payload.get("status") or "unknown"))
        payload.setdefault("fromStatus", status)
        payload.setdefault("toStatus", "approved")
        payload.setdefault("promptCleanup", cleanup)
        payload.setdefault("prodDispatch", {"mode": "handled_by_web_or_callback"})
        payload.setdefault("actionHint", "Execution continued; monitor terminal status.")
    return emit(payload)


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
        prompt_sent = False
        if status == "approval_pending":
            try:
                _maybe_send_telegram_policy_approval_prompt(
                    {
                        "policyApprovalId": policy_approval_id,
                        "chainKey": args.chain,
                        "status": status,
                        "requestType": "token_preapprove_add",
                        "tokenDisplay": token_display,
                    }
                )
                prompt_sent = True
            except Exception:
                prompt_sent = False
        return ok(
            "Policy approval requested (pending).",
            chain=args.chain,
            policyApprovalId=policy_approval_id,
            status=status,
            requestType="token_preapprove_add",
            tokenAddress=token_addr,
            tokenDisplay=token_display,
            promptSent=prompt_sent,
            actionHint=(
                "Approve or deny in Telegram/management to apply this policy change."
                if prompt_sent
                else "Approve or deny in management (or active Telegram session) to apply this policy change."
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
        prompt_sent = False
        if status == "approval_pending":
            try:
                _maybe_send_telegram_policy_approval_prompt(
                    {
                        "policyApprovalId": policy_approval_id,
                        "chainKey": args.chain,
                        "status": status,
                        "requestType": "global_approval_enable",
                    }
                )
                prompt_sent = True
            except Exception:
                prompt_sent = False
        return ok(
            "Policy approval requested (pending).",
            chain=args.chain,
            policyApprovalId=policy_approval_id,
            status=status,
            requestType="global_approval_enable",
            promptSent=prompt_sent,
            actionHint=(
                "Approve or deny in Telegram/management to apply this policy change."
                if prompt_sent
                else "Approve or deny in management (or active Telegram session) to apply this policy change."
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
        prompt_sent = False
        if status == "approval_pending":
            try:
                _maybe_send_telegram_policy_approval_prompt(
                    {
                        "policyApprovalId": policy_approval_id,
                        "chainKey": args.chain,
                        "status": status,
                        "requestType": "token_preapprove_remove",
                        "tokenDisplay": token_display,
                    }
                )
                prompt_sent = True
            except Exception:
                prompt_sent = False
        return ok(
            "Policy revoke requested (pending).",
            chain=args.chain,
            policyApprovalId=policy_approval_id,
            status=status,
            requestType="token_preapprove_remove",
            tokenAddress=token_addr,
            tokenDisplay=token_display,
            promptSent=prompt_sent,
            actionHint=(
                "Approve or deny in Telegram/management to apply this policy change."
                if prompt_sent
                else "Approve or deny in management (or active Telegram session) to apply this policy change."
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
        prompt_sent = False
        if status == "approval_pending":
            try:
                _maybe_send_telegram_policy_approval_prompt(
                    {
                        "policyApprovalId": policy_approval_id,
                        "chainKey": args.chain,
                        "status": status,
                        "requestType": "global_approval_disable",
                    }
                )
                prompt_sent = True
            except Exception:
                prompt_sent = False
        return ok(
            "Policy revoke requested (pending).",
            chain=args.chain,
            policyApprovalId=policy_approval_id,
            status=status,
            requestType="global_approval_disable",
            promptSent=prompt_sent,
            actionHint=(
                "Approve or deny in Telegram/management to apply this policy change."
                if prompt_sent
                else "Approve or deny in management (or active Telegram session) to apply this policy change."
            ),
        )
    except Exception as exc:
        return fail("policy_approval_request_failed", str(exc), "Inspect runtime policy revoke request and retry.", {"chain": args.chain}, exit_code=1)


def _parse_decision_at(value: str | None) -> str:
    raw = str(value or "").strip()
    if not raw:
        return datetime.now(timezone.utc).isoformat()
    candidate = raw
    if candidate.endswith("Z"):
        candidate = candidate[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(candidate)
    except Exception as exc:
        raise WalletStoreError(f"invalid decision_at: {raw}") from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def _load_watcher_state() -> dict[str, Any]:
    ensure_app_dir()
    if not WATCHER_STATE_FILE.exists():
        return {"watcherRunId": "", "updatedAt": utc_now()}
    try:
        payload = json.loads(WATCHER_STATE_FILE.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            return payload
    except Exception:
        pass
    return {"watcherRunId": "", "updatedAt": utc_now()}


def _save_watcher_state(state: dict[str, Any]) -> None:
    ensure_app_dir()
    WATCHER_STATE_FILE.write_text(json.dumps(state, separators=(",", ":")), encoding="utf-8")
    os.chmod(WATCHER_STATE_FILE, 0o600)


def _watcher_run_id() -> str:
    global _WATCHER_RUN_ID_CACHE
    if _WATCHER_RUN_ID_CACHE:
        return _WATCHER_RUN_ID_CACHE
    state = _load_watcher_state()
    run_id = str(state.get("watcherRunId") or "").strip()
    if not run_id:
        run_id = f"wrun_{secrets.token_hex(12)}"
        state["watcherRunId"] = run_id
        state["updatedAt"] = utc_now()
        _save_watcher_state(state)
    _WATCHER_RUN_ID_CACHE = run_id
    return run_id


def _post_trade_status(
    trade_id: str,
    from_status: str,
    to_status: str,
    extra: dict[str, Any] | None = None,
    *,
    idempotency_key: str | None = None,
    decision_at: str | None = None,
) -> None:
    payload: dict[str, Any] = {
        "tradeId": trade_id,
        "fromStatus": from_status,
        "toStatus": to_status,
        "at": _parse_decision_at(decision_at),
        "observedBy": "agent_watcher",
        "observationSource": "local_send_result",
        "observedAt": utc_now(),
        "watcherRunId": _watcher_run_id(),
    }
    if extra:
        payload.update(extra)
    status_code, body = _api_request(
        "POST",
        f"/trades/{trade_id}/status",
        payload=payload,
        include_idempotency=True,
        idempotency_key=idempotency_key,
    )
    if status_code < 200 or status_code >= 300:
        code = str(body.get("code", "api_error"))
        message = str(body.get("message", f"trade status update failed ({status_code})"))
        raise WalletStoreError(f"{code}: {message}")


def _post_liquidity_status(
    liquidity_intent_id: str,
    to_status: str,
    extra: dict[str, Any] | None = None,
) -> None:
    payload: dict[str, Any] = {"status": to_status}
    if extra:
        for key, value in extra.items():
            if value is None:
                continue
            payload[key] = value
    status_code, body = _api_request(
        "POST",
        f"/liquidity/{urllib.parse.quote(liquidity_intent_id)}/status",
        payload=payload,
        include_idempotency=True,
    )
    if status_code < 200 or status_code >= 300:
        code = str(body.get("code", "api_error"))
        message = str(body.get("message", f"liquidity status update failed ({status_code})"))
        raise WalletStoreError(f"{code}: {message}")


def _read_liquidity_intent(liquidity_intent_id: str, chain: str) -> dict[str, Any]:
    status_code, body = _api_request(
        "GET",
        f"/liquidity/pending?chainKey={urllib.parse.quote(chain)}&limit=200",
    )
    if status_code < 200 or status_code >= 300:
        code = str(body.get("code", "api_error"))
        message = str(body.get("message", f"liquidity pending read failed ({status_code})"))
        raise WalletStoreError(f"{code}: {message}")
    items = body.get("items")
    if not isinstance(items, list):
        raise WalletStoreError("Liquidity pending response missing items list.")
    target = str(liquidity_intent_id or "").strip()
    for row in items:
        if not isinstance(row, dict):
            continue
        if str(row.get("liquidityIntentId") or "").strip() == target:
            return row
    raise WalletStoreError(f"Liquidity intent '{target}' was not found in pending scope for chain '{chain}'.")


def _read_liquidity_position(chain: str, position_id: str) -> dict[str, Any]:
    agent_id = _resolve_agent_id_or_fail(chain)
    status_code, body = _api_request(
        "GET",
        f"/liquidity/positions?agentId={urllib.parse.quote(agent_id)}&chainKey={urllib.parse.quote(chain)}",
    )
    if status_code < 200 or status_code >= 300:
        code = str(body.get("code", "api_error"))
        message = str(body.get("message", f"liquidity positions read failed ({status_code})"))
        raise WalletStoreError(f"{code}: {message}")
    items = body.get("items")
    if not isinstance(items, list):
        raise WalletStoreError("Liquidity positions response missing items list.")
    target = str(position_id or "").strip()
    for row in items:
        if not isinstance(row, dict):
            continue
        if str(row.get("positionId") or "").strip() == target:
            return row
    raise WalletStoreError(f"Liquidity position '{target}' was not found for chain '{chain}'.")


def _wait_for_tx_receipt_success(chain: str, tx_hash: str) -> dict[str, Any]:
    cast_bin = _require_cast_bin()
    rpc_url = _chain_rpc_url(chain)
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
    return receipt_payload


def _ensure_token_allowance(
    *,
    chain: str,
    token_address: str,
    owner: str,
    spender: str,
    required_units: int,
    private_key_hex: str,
) -> str | None:
    allowance_wei = int(_fetch_token_allowance_wei(chain, token_address, owner, spender))
    if allowance_wei >= required_units:
        return None
    approve_data = _cast_calldata("approve(address,uint256)(bool)", [spender, str(required_units)])
    tx_hash = _cast_rpc_send_transaction(
        _chain_rpc_url(chain),
        {"from": owner, "to": token_address, "data": approve_data},
        private_key_hex,
        chain=chain,
    )
    _wait_for_tx_receipt_success(chain, tx_hash)
    return tx_hash


def _resolve_factory_from_router(chain: str, router: str) -> str:
    factory_raw = _cast_call_stdout(chain, router, "factory()(address)")
    factory = _parse_address_from_cast_output(factory_raw)
    if factory.lower() == "0x0000000000000000000000000000000000000000":
        raise WalletStoreError(f"Router factory resolved to zero address for router {router}.")
    return factory


def _resolve_pair_from_factory(chain: str, factory: str, token_a: str, token_b: str) -> str:
    pair_raw = _cast_call_stdout(chain, factory, "getPair(address,address)(address)", token_a, token_b)
    pair = _parse_address_from_cast_output(pair_raw)
    if pair.lower() == "0x0000000000000000000000000000000000000000":
        raise WalletStoreError("Factory returned zero pair address for token pair.")
    return pair


def _estimate_remove_amount_out_min(
    *,
    chain: str,
    pair: str,
    token_a: str,
    token_b: str,
    liquidity_units: int,
    slippage_bps: int,
) -> tuple[int, int]:
    token0 = _parse_address_from_cast_output(_cast_call_stdout(chain, pair, "token0()(address)")).lower()
    reserves_out = _cast_call_stdout(chain, pair, "getReserves()(uint112,uint112,uint32)")
    reserve_values = _parse_uint_tuple_from_cast_output(reserves_out)
    if len(reserve_values) < 2:
        raise WalletStoreError("Unable to parse reserves for remove-liquidity estimate.")
    reserve0 = int(reserve_values[0])
    reserve1 = int(reserve_values[1])
    total_supply_raw = _cast_call_stdout(chain, pair, "totalSupply()(uint256)")
    total_supply = _parse_uint_from_cast_output(total_supply_raw)
    if total_supply <= 0:
        raise WalletStoreError("Pair totalSupply is zero; cannot estimate remove outputs.")
    amount0 = (liquidity_units * reserve0) // total_supply
    amount1 = (liquidity_units * reserve1) // total_supply
    min0 = (amount0 * max(0, 10000 - slippage_bps)) // 10000
    min1 = (amount1 * max(0, 10000 - slippage_bps)) // 10000
    token_a_is_token0 = token_a.lower() == token0
    min_a = min0 if token_a_is_token0 else min1
    min_b = min1 if token_a_is_token0 else min0
    return max(0, min_a), max(0, min_b)


def _estimate_add_amount_in_with_min(
    *,
    reserve_a: int,
    reserve_b: int,
    desired_a: int,
    desired_b: int,
    slippage_bps: int,
) -> tuple[int, int, int, int]:
    if reserve_a <= 0 or reserve_b <= 0:
        raise WalletStoreError("Pair reserves must be greater than zero for add-liquidity estimate.")
    if desired_a <= 0 or desired_b <= 0:
        raise WalletStoreError("Desired token amounts must be greater than zero for add-liquidity estimate.")
    if slippage_bps < 0 or slippage_bps > 5000:
        raise WalletStoreError("slippageBps must be between 0 and 5000 for add-liquidity estimate.")

    amount_b_optimal = (desired_a * reserve_b) // reserve_a
    if amount_b_optimal <= desired_b:
        amount_a = desired_a
        amount_b = amount_b_optimal
    else:
        amount_a_optimal = (desired_b * reserve_a) // reserve_b
        amount_a = amount_a_optimal
        amount_b = desired_b
    if amount_a <= 0 or amount_b <= 0:
        amount_a = desired_a
        amount_b = desired_b

    min_a = (amount_a * max(0, 10000 - slippage_bps)) // 10000
    min_b = (amount_b * max(0, 10000 - slippage_bps)) // 10000
    return max(0, amount_a), max(0, amount_b), max(0, min_a), max(0, min_b)


def _is_truthy_solidity_bool_output(raw_result: str) -> bool:
    text = str(raw_result or "").strip().lower()
    if text in {"0x1", "0x01"}:
        return True
    if text in {"0x", "0x0", "0x00"}:
        return False
    if not text.startswith("0x"):
        raise WalletStoreError("eth_call bool output is malformed.")
    hex_body = text[2:]
    if not re.fullmatch(r"[0-9a-f]+", hex_body):
        raise WalletStoreError("eth_call bool output is malformed.")
    try:
        return int(hex_body or "0", 16) != 0
    except Exception as exc:
        raise WalletStoreError("eth_call bool output is malformed.") from exc


def _probe_transfer_from_eth_call(
    *,
    chain: str,
    token_address: str,
    owner: str,
    recipient: str,
    amount_units: int,
    spender: str,
) -> dict[str, Any]:
    calldata = _cast_calldata(
        "transferFrom(address,address,uint256)(bool)",
        [owner, recipient, str(amount_units)],
    )
    rpc_url = _chain_rpc_url(chain)
    try:
        result = _rpc_json_call(
            rpc_url,
            "eth_call",
            [
                {"from": spender, "to": token_address, "data": calldata},
                "latest",
            ],
        )
    except WalletStoreError as exc:
        message = str(exc)
        if "403" in message.lower() or "forbidden" in message.lower():
            return {
                "ok": False,
                "kind": "rpc_forbidden",
                "error": message[:300],
                "token": token_address.lower(),
                "owner": owner.lower(),
                "recipient": recipient.lower(),
                "spender": spender.lower(),
                "amount": str(amount_units),
            }
        return {
            "ok": False,
            "kind": "revert",
            "error": message[:300],
            "token": token_address.lower(),
            "owner": owner.lower(),
            "recipient": recipient.lower(),
            "spender": spender.lower(),
            "amount": str(amount_units),
        }
    raw = str(result or "").strip()
    try:
        truthy = _is_truthy_solidity_bool_output(raw)
    except WalletStoreError as exc:
        return {
            "ok": False,
            "kind": "malformed_return",
            "error": str(exc),
            "rawResult": raw[:160],
            "token": token_address.lower(),
            "owner": owner.lower(),
            "recipient": recipient.lower(),
            "spender": spender.lower(),
            "amount": str(amount_units),
        }
    if not truthy:
        return {
            "ok": False,
            "kind": "return_false",
            "rawResult": raw[:160],
            "token": token_address.lower(),
            "owner": owner.lower(),
            "recipient": recipient.lower(),
            "spender": spender.lower(),
            "amount": str(amount_units),
        }
    return {
        "ok": True,
        "kind": "ok",
        "rawResult": raw[:160],
        "token": token_address.lower(),
        "owner": owner.lower(),
        "recipient": recipient.lower(),
        "spender": spender.lower(),
        "amount": str(amount_units),
    }


def _probe_transfer_eth_call(
    *,
    chain: str,
    token_address: str,
    owner: str,
    recipient: str,
    amount_units: int,
) -> dict[str, Any]:
    calldata = _cast_calldata(
        "transfer(address,uint256)(bool)",
        [recipient, str(amount_units)],
    )
    rpc_url = _chain_rpc_url(chain)
    try:
        result = _rpc_json_call(
            rpc_url,
            "eth_call",
            [
                {"from": owner, "to": token_address, "data": calldata},
                "latest",
            ],
        )
    except WalletStoreError as exc:
        return {
            "ok": False,
            "kind": "revert",
            "error": str(exc)[:300],
            "token": token_address.lower(),
            "owner": owner.lower(),
            "recipient": recipient.lower(),
            "amount": str(amount_units),
        }
    raw = str(result or "").strip()
    try:
        truthy = _is_truthy_solidity_bool_output(raw)
    except WalletStoreError as exc:
        return {
            "ok": False,
            "kind": "malformed_return",
            "error": str(exc),
            "rawResult": raw[:160],
            "token": token_address.lower(),
            "owner": owner.lower(),
            "recipient": recipient.lower(),
            "amount": str(amount_units),
        }
    if not truthy:
        return {
            "ok": False,
            "kind": "return_false",
            "rawResult": raw[:160],
            "token": token_address.lower(),
            "owner": owner.lower(),
            "recipient": recipient.lower(),
            "amount": str(amount_units),
        }
    return {
        "ok": True,
        "kind": "ok",
        "rawResult": raw[:160],
        "token": token_address.lower(),
        "owner": owner.lower(),
        "recipient": recipient.lower(),
        "amount": str(amount_units),
    }


def _preflight_liquidity_v2_add_execution(
    *,
    chain: str,
    token_a: str,
    token_b: str,
    amount_a_units: int,
    amount_b_units: int,
    min_a_units: int,
    min_b_units: int,
    wallet_address: str,
    router: str,
    deadline: str,
) -> dict[str, Any]:
    if min_a_units <= 0 or min_b_units <= 0:
        raise LiquidityExecutionError(
            "liquidity_preflight_min_amount_zero",
            "Computed minimum output amount is zero. Increase size or reduce slippage.",
        )

    token_a_balance = int(_fetch_token_balance_wei(chain, wallet_address, token_a))
    token_b_balance = int(_fetch_token_balance_wei(chain, wallet_address, token_b))
    token_a_allowance = int(_fetch_token_allowance_wei(chain, token_a, wallet_address, router))
    token_b_allowance = int(_fetch_token_allowance_wei(chain, token_b, wallet_address, router))
    if token_a_balance < amount_a_units:
        raise LiquidityExecutionError(
            "liquidity_preflight_insufficient_token_balance",
            "Insufficient tokenA balance for addLiquidity execution.",
        )
    if token_b_balance < amount_b_units:
        raise LiquidityExecutionError(
            "liquidity_preflight_insufficient_token_balance",
            "Insufficient tokenB balance for addLiquidity execution.",
        )

    native_balance = int(_fetch_native_balance_wei(chain, wallet_address))
    min_native_gas_wei = int(Decimal("0.001") * Decimal(10**18))
    if native_balance < min_native_gas_wei:
        raise LiquidityExecutionError(
            "liquidity_preflight_insufficient_gas_balance",
            "Native token balance is too low for addLiquidity gas fees.",
        )

    factory = _resolve_factory_from_router(chain, router)
    pair = _resolve_pair_from_factory(chain, factory, token_a, token_b)
    reserves_out = _cast_call_stdout(chain, pair, "getReserves()(uint112,uint112,uint32)")
    reserve_values = _parse_uint_tuple_from_cast_output(reserves_out)
    if len(reserve_values) < 2:
        raise LiquidityExecutionError(
            "liquidity_preflight_pair_reserve_parse_failed",
            "Unable to parse pair reserves during addLiquidity preflight.",
        )
    reserve0 = int(reserve_values[0])
    reserve1 = int(reserve_values[1])
    if reserve0 <= 0 or reserve1 <= 0:
        raise LiquidityExecutionError(
            "liquidity_preflight_empty_reserves",
            "Pair reserves are empty; choose a liquid pair before execution.",
        )

    probe_a = _probe_transfer_from_eth_call(
        chain=chain,
        token_address=token_a,
        owner=wallet_address,
        recipient=pair,
        amount_units=amount_a_units,
        spender=router,
    )
    if (not bool(probe_a.get("ok"))) and str(probe_a.get("kind") or "") == "rpc_forbidden":
        transfer_probe_a = _probe_transfer_eth_call(
            chain=chain,
            token_address=token_a,
            owner=wallet_address,
            recipient=pair,
            amount_units=amount_a_units,
        )
        probe_a["fallbackTransferProbe"] = transfer_probe_a
        if bool(transfer_probe_a.get("ok")):
            probe_a["ok"] = True
            probe_a["kind"] = "rpc_forbidden_fallback_transfer_ok"
        else:
            fallback_err = str(transfer_probe_a.get("error") or "").lower()
            if "403" in fallback_err or "forbidden" in fallback_err:
                probe_a["ok"] = True
                probe_a["kind"] = "rpc_forbidden_unverifiable"
    if not bool(probe_a.get("ok")):
        raise LiquidityExecutionError(
            "liquidity_preflight_token_transfer_blocked_token_a",
            "TokenA transferFrom probe failed before addLiquidity simulation.",
            details={
                "pair": pair.lower(),
                "factory": factory.lower(),
                "tokenProbeA": probe_a,
                "tokenProbeB": None,
                "tokenAAllowance": str(token_a_allowance),
                "tokenBAllowance": str(token_b_allowance),
                "tokenABalance": str(token_a_balance),
                "tokenBBalance": str(token_b_balance),
            },
        )

    probe_b = _probe_transfer_from_eth_call(
        chain=chain,
        token_address=token_b,
        owner=wallet_address,
        recipient=pair,
        amount_units=amount_b_units,
        spender=router,
    )
    if (not bool(probe_b.get("ok"))) and str(probe_b.get("kind") or "") == "rpc_forbidden":
        transfer_probe_b = _probe_transfer_eth_call(
            chain=chain,
            token_address=token_b,
            owner=wallet_address,
            recipient=pair,
            amount_units=amount_b_units,
        )
        probe_b["fallbackTransferProbe"] = transfer_probe_b
        if bool(transfer_probe_b.get("ok")):
            probe_b["ok"] = True
            probe_b["kind"] = "rpc_forbidden_fallback_transfer_ok"
        else:
            fallback_err = str(transfer_probe_b.get("error") or "").lower()
            if "403" in fallback_err or "forbidden" in fallback_err:
                probe_b["ok"] = True
                probe_b["kind"] = "rpc_forbidden_unverifiable"
    if not bool(probe_b.get("ok")):
        raise LiquidityExecutionError(
            "liquidity_preflight_token_transfer_blocked_token_b",
            "TokenB transferFrom probe failed before addLiquidity simulation.",
            details={
                "pair": pair.lower(),
                "factory": factory.lower(),
                "tokenProbeA": probe_a,
                "tokenProbeB": probe_b,
                "tokenAAllowance": str(token_a_allowance),
                "tokenBAllowance": str(token_b_allowance),
                "tokenABalance": str(token_a_balance),
                "tokenBBalance": str(token_b_balance),
            },
        )

    simulation_warning: dict[str, Any] | None = None
    try:
        _cast_call_stdout(
            chain,
            router,
            "addLiquidity(address,address,uint256,uint256,uint256,uint256,address,uint256)(uint256,uint256,uint256)",
            token_a,
            token_b,
            str(amount_a_units),
            str(amount_b_units),
            str(min_a_units),
            str(min_b_units),
            wallet_address,
            deadline,
        )
    except WalletStoreError as exc:
        msg_lower = str(exc).lower()
        probe_a_kind = str(probe_a.get("kind") or "").strip().lower()
        probe_b_kind = str(probe_b.get("kind") or "").strip().lower()
        probe_unverifiable = probe_a_kind == "rpc_forbidden_unverifiable" and probe_b_kind == "rpc_forbidden_unverifiable"
        if probe_unverifiable and "transferhelper::transferfrom: transferfrom failed" in msg_lower:
            retry_errors: list[str] = []
            for rpc_url in _chain_rpc_candidates(chain):
                try:
                    _cast_call_stdout_with_rpc(
                        rpc_url,
                        router,
                        "addLiquidity(address,address,uint256,uint256,uint256,uint256,address,uint256)(uint256,uint256,uint256)",
                        token_a,
                        token_b,
                        str(amount_a_units),
                        str(amount_b_units),
                        str(min_a_units),
                        str(min_b_units),
                        wallet_address,
                        deadline,
                    )
                    simulation_warning = {
                        "code": "liquidity_preflight_router_transfer_from_retry_success",
                        "message": "addLiquidity simulation passed on alternate RPC after initial transferFrom failure.",
                    }
                    break
                except WalletStoreError as retry_exc:
                    retry_errors.append(str(retry_exc)[:180])
            if simulation_warning is None and retry_errors:
                msg_lower = f"{msg_lower}; retry={'; '.join(retry_errors)}"
        allow_sepolia_transferfrom_bypass = (
            chain == "ethereum_sepolia"
            and str(os.environ.get("XCLAW_LIQUIDITY_ALLOW_SEPOLIA_TRANSFERFROM_BYPASS") or "").strip() == "1"
            and probe_unverifiable
            and "transferhelper::transferfrom: transferfrom failed" in msg_lower
        )
        if simulation_warning is not None:
            pass
        elif allow_sepolia_transferfrom_bypass:
            simulation_warning = {
                "code": "liquidity_preflight_router_transfer_from_unverifiable_bypassed",
                "message": str(exc)[:500],
            }
        else:
            reason_code = "liquidity_preflight_router_revert"
            if "transferhelper::transferfrom: transferfrom failed" in msg_lower:
                reason_code = "liquidity_preflight_router_transfer_from_failed"
            raise LiquidityExecutionError(
                reason_code,
                f"addLiquidity simulation failed before submit: {exc}",
                details={
                    "pair": pair.lower(),
                    "factory": factory.lower(),
                    "tokenProbeA": probe_a,
                    "tokenProbeB": probe_b,
                    "tokenAAllowance": str(token_a_allowance),
                    "tokenBAllowance": str(token_b_allowance),
                    "tokenABalance": str(token_a_balance),
                    "tokenBBalance": str(token_b_balance),
                },
            ) from exc

    return {
        "pair": pair.lower(),
        "factory": factory.lower(),
        "reserve0": str(reserve0),
        "reserve1": str(reserve1),
        "tokenABalance": str(token_a_balance),
        "tokenBBalance": str(token_b_balance),
        "tokenAAllowance": str(token_a_allowance),
        "tokenBAllowance": str(token_b_allowance),
        "tokenProbeA": probe_a,
        "tokenProbeB": probe_b,
        "simulationWarning": simulation_warning,
        "nativeBalanceWei": str(native_balance),
    }


def _execute_liquidity_v2_add(intent: dict[str, Any], chain: str) -> dict[str, Any]:
    dex = str(intent.get("dex") or "").strip().lower()
    position_type = str(intent.get("positionType") or "v2").strip().lower()
    adapter = build_liquidity_adapter_for_request(chain=chain, dex=dex, position_type=position_type)
    token_a = _resolve_token_address(chain, str(intent.get("tokenA") or ""))
    token_b = _resolve_token_address(chain, str(intent.get("tokenB") or ""))
    amount_a_h = _parse_positive_amount_text(str(intent.get("amountA") or ""), "amountA")
    amount_b_h = _parse_positive_amount_text(str(intent.get("amountB") or ""), "amountB")
    slippage_bps = int(intent.get("slippageBps") or 100)
    if slippage_bps < 0 or slippage_bps > 5000:
        raise WalletStoreError("slippageBps must be between 0 and 5000 for liquidity execution.")
    adapter.quote_add(
        {
            "tokenA": token_a,
            "tokenB": token_b,
            "amountA": _decimal_text(amount_a_h),
            "amountB": _decimal_text(amount_b_h),
            "slippageBps": slippage_bps,
        }
    )
    router = _require_chain_contract_address(chain, "router")
    token_a_meta = _fetch_erc20_metadata(chain, token_a)
    token_b_meta = _fetch_erc20_metadata(chain, token_b)
    token_a_decimals = int(token_a_meta.get("decimals", 18))
    token_b_decimals = int(token_b_meta.get("decimals", 18))
    amount_a_units = int(_to_units_uint(_decimal_text(amount_a_h), token_a_decimals))
    amount_b_units = int(_to_units_uint(_decimal_text(amount_b_h), token_b_decimals))
    factory = _resolve_factory_from_router(chain, router)
    pair = _resolve_pair_from_factory(chain, factory, token_a, token_b)
    token0 = _parse_address_from_cast_output(_cast_call_stdout(chain, pair, "token0()(address)")).lower()
    reserves_out = _cast_call_stdout(chain, pair, "getReserves()(uint112,uint112,uint32)")
    reserve_values = _parse_uint_tuple_from_cast_output(reserves_out)
    if len(reserve_values) < 2:
        raise WalletStoreError("Unable to parse pair reserves for add-liquidity estimate.")
    reserve0 = int(reserve_values[0])
    reserve1 = int(reserve_values[1])
    token_a_is_token0 = token_a.lower() == token0
    reserve_a = reserve0 if token_a_is_token0 else reserve1
    reserve_b = reserve1 if token_a_is_token0 else reserve0
    amount_a_estimate_units, amount_b_estimate_units, min_a_units, min_b_units = _estimate_add_amount_in_with_min(
        reserve_a=reserve_a,
        reserve_b=reserve_b,
        desired_a=amount_a_units,
        desired_b=amount_b_units,
        slippage_bps=slippage_bps,
    )

    store = load_wallet_store()
    wallet_address, private_key_hex = _execution_wallet(store, chain)
    deadline = str(int(datetime.now(timezone.utc).timestamp()) + 120)
    preflight_details = _preflight_liquidity_v2_add_execution(
        chain=chain,
        token_a=token_a,
        token_b=token_b,
        amount_a_units=amount_a_units,
        amount_b_units=amount_b_units,
        min_a_units=min_a_units,
        min_b_units=min_b_units,
        wallet_address=wallet_address,
        router=router,
        deadline=deadline,
    )
    plan = build_liquidity_add_plan(
        chain=chain,
        dex=adapter.dex,
        position_type=position_type,
        request={
            "tokenA": token_a,
            "tokenB": token_b,
            "amountAUnits": str(max(amount_a_units, amount_a_estimate_units)),
            "amountBUnits": str(max(amount_b_units, amount_b_estimate_units)),
            "minAmountAUnits": str(min_a_units),
            "minAmountBUnits": str(min_b_units),
            "deadline": deadline,
        },
        wallet_address=wallet_address,
        build_calldata=_cast_calldata,
    )
    execution = execute_liquidity_plan(
        executor=_router_action_executor(),
        plan=plan,
        wallet_address=wallet_address,
        private_key_hex=private_key_hex,
        wait_for_operation_receipts=False,
        liquidity_operation="add",
    )
    tx_hash = str(execution.tx_hash or "")
    return {
        "txHash": tx_hash,
        "positionId": tx_hash,
        "details": {
            "adapterFamily": adapter.protocol_family,
            "dex": adapter.dex,
            "action": "add",
            "executionFamily": execution.execution_family,
            "executionAdapter": execution.execution_adapter,
            "routeKind": execution.route_kind,
            "amountAEstimate": str(amount_a_estimate_units),
            "amountBEstimate": str(amount_b_estimate_units),
            "minAmountA": str(min_a_units),
            "minAmountB": str(min_b_units),
            "approveTxHashes": execution.approve_tx_hashes,
            "operationTxHashes": execution.operation_tx_hashes,
            "preflight": preflight_details,
        },
    }


def _execute_liquidity_v2_remove(intent: dict[str, Any], chain: str) -> dict[str, Any]:
    dex = str(intent.get("dex") or "").strip().lower()
    position_type = str(intent.get("positionType") or "v2").strip().lower()
    adapter = build_liquidity_adapter_for_request(chain=chain, dex=dex, position_type=position_type)
    position_id = str(intent.get("positionRef") or "").strip()
    if not position_id:
        raise WalletStoreError("Remove intent is missing positionRef.")
    percent_raw = str(intent.get("amountA") or "").strip() or "0"
    try:
        percent = int(Decimal(percent_raw).to_integral_value(rounding=ROUND_DOWN))
    except Exception as exc:
        raise WalletStoreError("Remove intent amountA is not a valid percent.") from exc
    if percent < 1 or percent > 100:
        raise WalletStoreError("Remove intent percent must be between 1 and 100.")
    slippage_bps = int(intent.get("slippageBps") or 100)
    if slippage_bps < 0 or slippage_bps > 5000:
        raise WalletStoreError("slippageBps must be between 0 and 5000 for liquidity execution.")

    snapshot: dict[str, Any] | None = None
    pair_from_position: str | None = None
    try:
        snapshot = _read_liquidity_position(chain, position_id)
    except WalletStoreError:
        if is_hex_address(position_id):
            pair_from_position = position_id
        else:
            raise
    if snapshot is not None:
        token_a_hint = str(snapshot.get("tokenA") or intent.get("tokenA") or "").strip()
        token_b_hint = str(snapshot.get("tokenB") or intent.get("tokenB") or "").strip()
        if is_hex_address(position_id) and (_is_placeholder_liquidity_token(token_a_hint) or _is_placeholder_liquidity_token(token_b_hint)):
            token_a, token_b = _resolve_liquidity_remove_tokens(chain, position_id, token_a_hint, token_b_hint)
        else:
            token_a = _resolve_token_address(chain, token_a_hint)
            token_b = _resolve_token_address(chain, token_b_hint)
    elif pair_from_position:
        token_a, token_b = _resolve_pair_tokens_from_contract(chain, pair_from_position)
    else:
        raise WalletStoreError(f"Unable to resolve liquidity position '{position_id}'.")
    adapter.quote_remove({"positionId": position_id, "percent": percent, "slippageBps": slippage_bps})

    router = _require_chain_contract_address(chain, "router")
    pair_lookup_id = pair_from_position or position_id
    remove_context = _compute_v2_remove_liquidity_units(chain, pair_lookup_id, token_a, token_b, percent)
    pair = str(remove_context.get("pair") or "").strip()
    lp_token = str(remove_context.get("lpToken") or "").strip()
    lp_balance = int(remove_context.get("lpBalance") or 0)
    liquidity_units = int(remove_context.get("liquidityUnits") or 0)
    wallet_address = str(remove_context.get("walletAddress") or "").strip()
    store = load_wallet_store()
    _, private_key_hex = _execution_wallet(store, chain)
    if liquidity_units <= 0:
        raise LiquidityExecutionError(
            "liquidity_preflight_zero_lp_balance",
            "Computed LP liquidity amount is zero; position has no removable LP token balance.",
            details={
                "positionId": position_id,
                "pair": pair.lower() if pair else pair,
                "lpToken": lp_token.lower() if lp_token else lp_token,
                "lpBalance": str(lp_balance),
                "percent": percent,
            },
        )
    min_a_units, min_b_units = _estimate_remove_amount_out_min(
        chain=chain,
        pair=pair,
        token_a=token_a,
        token_b=token_b,
        liquidity_units=liquidity_units,
        slippage_bps=slippage_bps,
    )
    deadline = str(int(datetime.now(timezone.utc).timestamp()) + 120)
    plan = build_liquidity_remove_plan(
        chain=chain,
        dex=adapter.dex,
        position_type=position_type,
        request={
            "tokenA": token_a,
            "tokenB": token_b,
            "lpToken": lp_token,
            "liquidityUnits": str(liquidity_units),
            "minAmountAUnits": str(min_a_units),
            "minAmountBUnits": str(min_b_units),
            "deadline": deadline,
        },
        wallet_address=wallet_address,
        build_calldata=_cast_calldata,
    )
    execution = execute_liquidity_plan(
        executor=_router_action_executor(),
        plan=plan,
        wallet_address=wallet_address,
        private_key_hex=private_key_hex,
        wait_for_operation_receipts=False,
        liquidity_operation="remove",
    )
    tx_hash = str(execution.tx_hash or "")
    return {
        "txHash": tx_hash,
        "positionId": position_id,
        "details": {
            "adapterFamily": adapter.protocol_family,
            "dex": adapter.dex,
            "action": "remove",
            "executionFamily": execution.execution_family,
            "executionAdapter": execution.execution_adapter,
            "routeKind": execution.route_kind,
            "pair": pair.lower(),
            "lpToken": lp_token.lower(),
            "percent": percent,
            "liquidityUnits": str(liquidity_units),
            "minAmountA": str(min_a_units),
            "minAmountB": str(min_b_units),
            "approveTxHashes": execution.approve_tx_hashes,
            "operationTxHashes": execution.operation_tx_hashes,
        },
    }


def _read_v3_position_snapshot(chain: str, position_manager: str, position_id: str) -> dict[str, Any]:
    call_data = _cast_calldata("positions(uint256)((uint96,address,address,address,uint24,int24,int24,uint128,uint256,uint256,uint128,uint128))", [position_id])
    rpc_result = _rpc_json_call(
        _chain_rpc_url(chain),
        "eth_call",
        [{"to": position_manager, "data": call_data}, "latest"],
    )
    data_hex = str(rpc_result or "").strip().lower()
    if not data_hex.startswith("0x"):
        raise WalletStoreError("v3 position lookup returned malformed eth_call data.")
    encoded = data_hex[2:]
    if len(encoded) < 64 * 8:
        raise WalletStoreError("v3 position lookup returned insufficient tuple data.")
    words = [encoded[index : index + 64] for index in range(0, len(encoded), 64)]
    if len(words) < 8:
        raise WalletStoreError("v3 position lookup returned insufficient tuple words.")
    token0_word = words[2]
    token1_word = words[3]
    token0 = "0x" + token0_word[-40:]
    token1 = "0x" + token1_word[-40:]
    liquidity_word = words[7]
    try:
        liquidity_units = int(liquidity_word, 16)
    except Exception as exc:
        raise WalletStoreError("v3 position liquidity decode failed.") from exc
    return {
        "token0": token0.lower(),
        "token1": token1.lower(),
        "liquidityUnits": str(max(0, liquidity_units)),
    }


def _execute_liquidity_v3_add(intent: dict[str, Any], chain: str) -> dict[str, Any]:
    dex = str(intent.get("dex") or "").strip().lower()
    adapter = build_liquidity_adapter_for_request(chain=chain, dex=dex, position_type="v3")
    if adapter.protocol_family not in {"position_manager_v3", "local_clmm", "raydium_clmm"}:
        raise WalletStoreError(
            f"unsupported_liquidity_execution_family: Liquidity intent execution requires a supported v3 execution family; got '{adapter.protocol_family}'."
        )
    if not adapter.supports_operation("add"):
        raise UnsupportedLiquidityOperation("unsupported_liquidity_operation")
    details = _intent_details_dict(intent)
    v3_details = _v3_details_dict(details)
    pool_id = _resolve_raydium_pool_id(adapter, str(v3_details.get("poolId") or ""))
    fee = str(v3_details.get("fee") or "").strip()
    tick_lower = str(v3_details.get("tickLower") or "").strip()
    tick_upper = str(v3_details.get("tickUpper") or "").strip()
    if not fee or not tick_lower or not tick_upper:
        raise WalletStoreError("invalid_input: v3 add intent is missing normalized v3 range metadata.")
    token_a = _resolve_token_address(chain, str(intent.get("tokenA") or ""))
    token_b = _resolve_token_address(chain, str(intent.get("tokenB") or ""))
    amount_a_h = _parse_positive_amount_text(str(intent.get("amountA") or ""), "amountA")
    amount_b_h = _parse_positive_amount_text(str(intent.get("amountB") or ""), "amountB")
    slippage_bps = int(intent.get("slippageBps") or 100)
    if slippage_bps < 0 or slippage_bps > 5000:
        raise WalletStoreError("slippageBps must be between 0 and 5000 for liquidity execution.")
    if _is_solana_chain(chain):
        store = load_wallet_store()
        wallet_address, secret = _execution_wallet_solana_secret(store, chain)
        if adapter.protocol_family == "local_clmm":
            if chain != "solana_localnet":
                raise WalletStoreError("unsupported_liquidity_adapter: local_clmm adapter is only supported on solana_localnet.")
            created = solana_local_create_position(
                chain=chain,
                dex=adapter.dex,
                owner=wallet_address,
                token_a=token_a,
                token_b=token_b,
                amount_a=_decimal_text(amount_a_h),
                amount_b=_decimal_text(amount_b_h),
                details=v3_details,
            )
            return {
                "txHash": str(created.get("txHash") or ""),
                "positionId": str(created.get("positionId") or ""),
                "details": {
                    "adapterFamily": adapter.protocol_family,
                    "dex": adapter.dex,
                    "action": "add",
                    "executionFamily": "solana_clmm",
                    "executionAdapter": adapter.dex,
                    "routeKind": "adapter_default",
                    "fee": fee,
                    "tickLower": tick_lower,
                    "tickUpper": tick_upper,
                    "amountA": _decimal_text(amount_a_h),
                    "amountB": _decimal_text(amount_b_h),
                    "slippageBps": slippage_bps,
                    "approveTxHashes": [],
                    "operationTxHashes": [str(created.get("txHash") or "")],
                    "simulationMode": True,
                },
            }
        if adapter.protocol_family == "raydium_clmm":
            if not pool_id:
                raise WalletStoreError("invalid_input: Solana Raydium add requires v3.poolId in intent details.")
            amount_a_units = int(_to_units_uint(_decimal_text(amount_a_h), 9))
            amount_b_units = int(_to_units_uint(_decimal_text(amount_b_h), 9))
            min_amount_a_units = (amount_a_units * max(0, 10000 - slippage_bps)) // 10000
            min_amount_b_units = (amount_b_units * max(0, 10000 - slippage_bps)) // 10000
            execution = solana_raydium_execute_instruction(
                chain=chain,
                rpc_url=_chain_rpc_url(chain),
                private_key_bytes=secret,
                owner=wallet_address,
                adapter_metadata=dict(adapter.adapter_metadata or {}),
                request={
                    "poolId": pool_id,
                    "tokenA": token_a,
                    "tokenB": token_b,
                    "fee": fee,
                    "amountAUnits": str(amount_a_units),
                    "amountBUnits": str(amount_b_units),
                    "minAmountAUnits": str(min_amount_a_units),
                    "minAmountBUnits": str(min_amount_b_units),
                    "slippageBps": slippage_bps,
                },
                operation_key="add",
            )
            tx_hash = str(execution.tx_hash or "")
            return {
                "txHash": tx_hash,
                "positionId": str(intent.get("positionId") or tx_hash),
                "details": {
                    "adapterFamily": adapter.protocol_family,
                    "dex": adapter.dex,
                    "action": "add",
                    "executionFamily": "solana_clmm",
                    "executionAdapter": adapter.dex,
                    "routeKind": execution.route_kind,
                    "fee": fee,
                    "tickLower": tick_lower,
                    "tickUpper": tick_upper,
                    "poolId": pool_id,
                    "amountA": _decimal_text(amount_a_h),
                    "amountB": _decimal_text(amount_b_h),
                    "slippageBps": slippage_bps,
                    "approveTxHashes": [],
                    "operationTxHashes": [tx_hash],
                    **execution.details,
                },
            }
        raise WalletStoreError(
            f"unsupported_liquidity_execution_family: Solana v3 add does not support adapter family '{adapter.protocol_family}'."
        )
    token_a_meta = _fetch_erc20_metadata(chain, token_a)
    token_b_meta = _fetch_erc20_metadata(chain, token_b)
    amount_a_units = int(_to_units_uint(_decimal_text(amount_a_h), int(token_a_meta.get("decimals", 18))))
    amount_b_units = int(_to_units_uint(_decimal_text(amount_b_h), int(token_b_meta.get("decimals", 18))))
    min_a_units = (amount_a_units * max(0, 10000 - slippage_bps)) // 10000
    min_b_units = (amount_b_units * max(0, 10000 - slippage_bps)) // 10000
    store = load_wallet_store()
    wallet_address, private_key_hex = _execution_wallet(store, chain)
    deadline_sec = int(v3_details.get("deadlineSec") or 120)
    deadline = str(int(datetime.now(timezone.utc).timestamp()) + max(1, deadline_sec))
    plan = build_liquidity_add_plan(
        chain=chain,
        dex=adapter.dex,
        position_type="v3",
        request={
            "tokenA": token_a,
            "tokenB": token_b,
            "amountAUnits": str(amount_a_units),
            "amountBUnits": str(amount_b_units),
            "minAmountAUnits": str(min_a_units),
            "minAmountBUnits": str(min_b_units),
            "fee": fee,
            "tickLower": tick_lower,
            "tickUpper": tick_upper,
            "deadline": deadline,
        },
        wallet_address=wallet_address,
        build_calldata=_cast_calldata,
    )
    execution = execute_liquidity_plan(
        executor=_router_action_executor(),
        plan=plan,
        wallet_address=wallet_address,
        private_key_hex=private_key_hex,
        wait_for_operation_receipts=False,
        liquidity_operation="add",
    )
    tx_hash = str(execution.tx_hash or "")
    return {
        "txHash": tx_hash,
        "positionId": str(intent.get("positionId") or tx_hash),
        "details": {
            "adapterFamily": adapter.protocol_family,
            "dex": adapter.dex,
            "action": "add",
            "executionFamily": execution.execution_family,
            "executionAdapter": execution.execution_adapter,
            "routeKind": execution.route_kind,
            "fee": fee,
            "tickLower": tick_lower,
            "tickUpper": tick_upper,
            "amountAUnits": str(amount_a_units),
            "amountBUnits": str(amount_b_units),
            "minAmountAUnits": str(min_a_units),
            "minAmountBUnits": str(min_b_units),
            "approveTxHashes": execution.approve_tx_hashes,
            "operationTxHashes": execution.operation_tx_hashes,
        },
    }


def _execute_liquidity_v3_remove(intent: dict[str, Any], chain: str) -> dict[str, Any]:
    dex = str(intent.get("dex") or "").strip().lower()
    adapter = build_liquidity_adapter_for_request(chain=chain, dex=dex, position_type="v3")
    if adapter.protocol_family not in {"position_manager_v3", "local_clmm", "raydium_clmm"}:
        raise WalletStoreError(
            f"unsupported_liquidity_execution_family: Liquidity intent execution requires a supported v3 execution family; got '{adapter.protocol_family}'."
        )
    if not adapter.supports_operation("remove"):
        raise UnsupportedLiquidityOperation("unsupported_liquidity_operation")
    position_id = str(intent.get("positionId") or intent.get("positionRef") or "").strip()
    if not position_id:
        raise WalletStoreError("invalid_input: v3 remove intent is missing positionId.")
    percent_raw = str(intent.get("amountA") or "").strip() or "0"
    try:
        percent = int(Decimal(percent_raw).to_integral_value(rounding=ROUND_DOWN))
    except Exception as exc:
        raise WalletStoreError("Remove intent amountA is not a valid percent.") from exc
    if percent < 1 or percent > 100:
        raise WalletStoreError("Remove intent percent must be between 1 and 100.")
    details = _intent_details_dict(intent)
    v3_details = _v3_details_dict(details)
    pool_id = _resolve_raydium_pool_id(adapter, str(v3_details.get("poolId") or intent.get("poolId") or ""))
    min_a_units = str(v3_details.get("minAmountAUnits") or "0").strip() or "0"
    min_b_units = str(v3_details.get("minAmountBUnits") or "0").strip() or "0"
    if _is_solana_chain(chain):
        store = load_wallet_store()
        wallet_address, secret = _execution_wallet_solana_secret(store, chain)
        if adapter.protocol_family == "local_clmm":
            if chain != "solana_localnet":
                raise WalletStoreError("unsupported_liquidity_adapter: local_clmm adapter is only supported on solana_localnet.")
            removed = solana_local_remove_position(
                chain=chain,
                dex=adapter.dex,
                owner=wallet_address,
                position_id=position_id,
                percent=percent,
            )
            return {
                "txHash": str(removed.get("txHash") or ""),
                "positionId": position_id,
                "details": {
                    "adapterFamily": adapter.protocol_family,
                    "dex": adapter.dex,
                    "action": "remove",
                    "executionFamily": "solana_clmm",
                    "executionAdapter": adapter.dex,
                    "routeKind": "adapter_default",
                    "percent": percent,
                    "removedAmountA": removed.get("removedAmountA"),
                    "removedAmountB": removed.get("removedAmountB"),
                    "remainingAmountA": removed.get("remainingAmountA"),
                    "remainingAmountB": removed.get("remainingAmountB"),
                    "minAmountAUnits": min_a_units,
                    "minAmountBUnits": min_b_units,
                    "approveTxHashes": [],
                    "operationTxHashes": [str(removed.get("txHash") or "")],
                    "simulationMode": True,
                },
            }
        if adapter.protocol_family == "raydium_clmm":
            if not pool_id:
                raise WalletStoreError("invalid_input: Solana Raydium remove requires v3.poolId in intent details.")
            execution = solana_raydium_execute_instruction(
                chain=chain,
                rpc_url=_chain_rpc_url(chain),
                private_key_bytes=secret,
                owner=wallet_address,
                adapter_metadata=dict(adapter.adapter_metadata or {}),
                request={
                    "poolId": pool_id,
                    "positionId": position_id,
                    "percent": percent,
                    "tokenA": str(intent.get("tokenA") or ""),
                    "tokenB": str(intent.get("tokenB") or ""),
                    "minAmountAUnits": min_a_units,
                    "minAmountBUnits": min_b_units,
                },
                operation_key="remove",
            )
            tx_hash = str(execution.tx_hash or "")
            return {
                "txHash": tx_hash,
                "positionId": position_id,
                "details": {
                    "adapterFamily": adapter.protocol_family,
                    "dex": adapter.dex,
                    "action": "remove",
                    "executionFamily": "solana_clmm",
                    "executionAdapter": adapter.dex,
                    "routeKind": execution.route_kind,
                    "percent": percent,
                    "poolId": pool_id,
                    "minAmountAUnits": min_a_units,
                    "minAmountBUnits": min_b_units,
                    "approveTxHashes": [],
                    "operationTxHashes": [tx_hash],
                    **execution.details,
                },
            }
        raise WalletStoreError(
            f"unsupported_liquidity_execution_family: Solana v3 remove does not support adapter family '{adapter.protocol_family}'."
        )
    position_manager = str(adapter.position_manager or "").strip()
    if not position_manager:
        raise WalletStoreError("chain_config_invalid: missing positionManager for v3 remove execution.")
    snapshot = _read_v3_position_snapshot(chain, position_manager, position_id)
    liquidity_total = int(snapshot.get("liquidityUnits") or 0)
    liquidity_units = (liquidity_total * percent) // 100
    if liquidity_units <= 0:
        raise LiquidityExecutionError(
            "liquidity_preflight_zero_position_liquidity",
            "Computed v3 liquidity amount is zero; position has no removable liquidity for requested percent.",
            details={"positionId": position_id, "positionManager": position_manager.lower(), "liquidityTotal": str(liquidity_total), "percent": percent},
        )
    store = load_wallet_store()
    wallet_address, private_key_hex = _execution_wallet(store, chain)
    deadline = str(int(datetime.now(timezone.utc).timestamp()) + 120)
    plan = build_liquidity_remove_plan(
        chain=chain,
        dex=adapter.dex,
        position_type="v3",
        request={
            "positionId": position_id,
            "positionRef": position_id,
            "liquidityUnits": str(liquidity_units),
            "minAmountAUnits": min_a_units,
            "minAmountBUnits": min_b_units,
            "deadline": deadline,
        },
        wallet_address=wallet_address,
        build_calldata=_cast_calldata,
    )
    execution = execute_liquidity_plan(
        executor=_router_action_executor(),
        plan=plan,
        wallet_address=wallet_address,
        private_key_hex=private_key_hex,
        wait_for_operation_receipts=False,
        liquidity_operation="remove",
    )
    tx_hash = str(execution.tx_hash or "")
    return {
        "txHash": tx_hash,
        "positionId": position_id,
        "details": {
            "adapterFamily": adapter.protocol_family,
            "dex": adapter.dex,
            "action": "remove",
            "executionFamily": execution.execution_family,
            "executionAdapter": execution.execution_adapter,
            "routeKind": execution.route_kind,
            "positionManager": position_manager.lower(),
            "percent": percent,
            "liquidityTotal": str(liquidity_total),
            "liquidityUnits": str(liquidity_units),
            "minAmountAUnits": min_a_units,
            "minAmountBUnits": min_b_units,
            "approveTxHashes": execution.approve_tx_hashes,
            "operationTxHashes": execution.operation_tx_hashes,
        },
    }


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
    adapter = build_dex_adapter(chain, cast_bin, rpc_url, router)
    try:
        return adapter.quote_token_in_per_one_token_out(
            token_out_decimals=token_out_decimals,
            token_in_decimals=token_in_decimals,
            token_out=token_out,
            token_in=token_in,
            run_call=lambda cmd: _run_subprocess(cmd, timeout_sec=_cast_call_timeout_sec(), kind="cast_call"),
            parse_uint=_parse_uint_from_cast_output,
        )
    except DexAdapterError as exc:
        raise WalletStoreError(str(exc)) from exc


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
    if _is_solana_chain(chain):
        if is_solana_address(candidate):
            return candidate
        symbol = candidate.upper()
        token_map = _canonical_token_map(chain)
        value = token_map.get(symbol)
        if value and is_solana_address(value):
            return value
        raise WalletStoreError("token must be a Solana mint address or canonical token symbol for the active chain.")

    if is_hex_address(candidate):
        alias_map = _canonical_token_address_aliases(chain)
        return str(alias_map.get(candidate.lower()) or candidate)
    symbol = candidate.upper()
    token_map = _canonical_token_map(chain)
    value = token_map.get(symbol)
    if value and is_hex_address(value):
        return value
    tracked = _tracked_tokens_for_chain(chain)
    matches: list[str] = []
    for row in tracked:
        tracked_symbol = str(row.get("symbol") or "").strip().upper()
        token = str(row.get("token") or "").strip().lower()
        if tracked_symbol == symbol and is_hex_address(token):
            matches.append(token)
    deduped = sorted(set(matches))
    if len(deduped) == 1:
        return deduped[0]
    if len(deduped) > 1:
        raise TokenResolutionError(
            "token_symbol_ambiguous",
            "Tracked token symbol matches multiple token addresses.",
            {"chain": chain, "tokenSymbol": symbol, "choices": deduped},
        )
    raise WalletStoreError("token must be a 0x address, canonical token symbol, or uniquely tracked token symbol for the active chain.")


def _is_placeholder_liquidity_token(value: str) -> bool:
    raw = str(value or "").strip()
    if not raw:
        return True
    return raw.upper() in {"POSITION", "TOKEN", "UNKNOWN", "N/A", "NA", "?"}


def _resolve_pair_tokens_from_contract(chain: str, pair_address: str) -> tuple[str, str]:
    token_a = _parse_address_from_cast_output(_cast_call_stdout(chain, pair_address, "token0()(address)"))
    token_b = _parse_address_from_cast_output(_cast_call_stdout(chain, pair_address, "token1()(address)"))
    if not is_hex_address(token_a) or not is_hex_address(token_b):
        raise WalletStoreError(f"Failed to resolve token0/token1 for pair '{pair_address}'.")
    return token_a, token_b


def _resolve_liquidity_remove_tokens(chain: str, position_id: str, token_a_hint: str, token_b_hint: str) -> tuple[str, str]:
    token_a = str(token_a_hint or "").strip()
    token_b = str(token_b_hint or "").strip()

    snapshot: dict[str, Any] | None = None
    if _is_placeholder_liquidity_token(token_a) or _is_placeholder_liquidity_token(token_b):
        try:
            snapshot = _read_liquidity_position(chain, position_id)
        except WalletStoreError:
            snapshot = None

    if snapshot is not None:
        if _is_placeholder_liquidity_token(token_a):
            token_a = str(snapshot.get("tokenA") or "").strip()
        if _is_placeholder_liquidity_token(token_b):
            token_b = str(snapshot.get("tokenB") or "").strip()
        if _is_placeholder_liquidity_token(token_a) or _is_placeholder_liquidity_token(token_b):
            pair_ref = str(
                snapshot.get("pool")
                or snapshot.get("poolRef")
                or snapshot.get("pair")
                or snapshot.get("positionRef")
                or ""
            ).strip()
            if is_hex_address(pair_ref):
                pair_token_a, pair_token_b = _resolve_pair_tokens_from_contract(chain, pair_ref)
                if _is_placeholder_liquidity_token(token_a):
                    token_a = pair_token_a
                if _is_placeholder_liquidity_token(token_b):
                    token_b = pair_token_b

    if (_is_placeholder_liquidity_token(token_a) or _is_placeholder_liquidity_token(token_b)) and is_hex_address(position_id):
        pair_token_a, pair_token_b = _resolve_pair_tokens_from_contract(chain, position_id)
        if _is_placeholder_liquidity_token(token_a):
            token_a = pair_token_a
        if _is_placeholder_liquidity_token(token_b):
            token_b = pair_token_b

    if _is_placeholder_liquidity_token(token_a) or _is_placeholder_liquidity_token(token_b):
        raise WalletStoreError(
            f"Unable to resolve liquidity token pair for position '{position_id}'. "
            "Provide --token-a/--token-b explicitly or refresh liquidity snapshots."
        )

    return _resolve_token_address(chain, token_a), _resolve_token_address(chain, token_b)


def _resolve_v2_remove_pair_and_lp_token(chain: str, position_id: str, token_a: str, token_b: str) -> tuple[str, str]:
    router = _require_chain_contract_address(chain, "router")
    factory = _resolve_factory_from_router(chain, router)
    pair = position_id if is_hex_address(position_id) else _resolve_pair_from_factory(chain, factory, token_a, token_b)
    return pair, pair


def _compute_v2_remove_liquidity_units(
    chain: str,
    position_id: str,
    token_a: str,
    token_b: str,
    percent: int,
) -> dict[str, Any]:
    pair, lp_token = _resolve_v2_remove_pair_and_lp_token(chain, position_id, token_a, token_b)
    wallet_address = _wallet_address_for_chain(chain)
    lp_balance = int(_fetch_token_balance_wei(chain, wallet_address, lp_token))
    liquidity_units = (lp_balance * percent) // 100
    return {
        "pair": pair,
        "lpToken": lp_token,
        "walletAddress": wallet_address,
        "lpBalance": lp_balance,
        "liquidityUnits": liquidity_units,
    }


def _token_symbol_for_display(chain: str, token_or_symbol: str) -> str:
    value = str(token_or_symbol or "").strip()
    if not value:
        return value
    if not is_hex_address(value):
        return value
    token_map = _canonical_token_map(chain)
    alias_map = _canonical_token_address_aliases(chain)
    normalized = str(alias_map.get(value.lower()) or value).lower()
    for symbol, address in token_map.items():
        if str(address or "").strip().lower() == normalized:
            return str(symbol or "").strip() or value
    tracked = _tracked_tokens_for_chain(chain)
    for row in tracked:
        token = str(row.get("token") or "").strip().lower()
        symbol = str(row.get("symbol") or "").strip()
        if token and token == normalized and symbol:
            return symbol
    return value


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
    adapter = build_dex_adapter(chain, cast_bin, rpc_url, router)
    try:
        return adapter.get_amount_out(
            amount_in_units=amount_in_units,
            token_in=token_in,
            token_out=token_out,
            run_call=lambda cmd: _run_subprocess(cmd, timeout_sec=_cast_call_timeout_sec(), kind="cast_call"),
            parse_uint=_parse_uint_from_cast_output,
        )
    except DexAdapterError as exc:
        raise WalletStoreError(str(exc)) from exc


def _cast_call_stdout_with_rpc(rpc_url: str, contract: str, signature: str, *args: str) -> str:
    cast_bin = _require_cast_bin()
    cmd = [cast_bin, "call", contract, signature]
    cmd.extend([str(a) for a in args])
    cmd.extend(["--rpc-url", rpc_url])
    proc = _run_subprocess(cmd, timeout_sec=_cast_call_timeout_sec(), kind="cast_call")
    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        stdout = (proc.stdout or "").strip()
        msg = stderr or stdout or "cast call failed"
        raise WalletStoreError(msg)
    return (proc.stdout or "").strip()


def _cast_call_stdout(chain: str, contract: str, signature: str, *args: str) -> str:
    return _cast_call_stdout_with_rpc(_chain_rpc_url(chain), contract, signature, *args)


def _parse_address_from_cast_output(raw: str) -> str:
    text = (raw or "").strip()
    matches = re.findall(r"0x[a-fA-F0-9]{40}", text)
    if not matches:
        raise WalletStoreError("Unable to parse address from cast output.")
    return matches[-1]


def _parse_uint_tuple_from_cast_output(raw: str) -> list[int]:
    text = (raw or "").strip()
    if not text:
        return []
    values: list[int] = []
    for token in re.findall(r"0x[a-fA-F0-9]+|\b[0-9]+\b", text):
        if token.startswith("0x") or token.startswith("0X"):
            values.append(int(token, 16))
        else:
            values.append(int(token))
    return values


def _parse_positive_amount_text(raw: str, field_name: str) -> Decimal:
    value = str(raw or "").strip()
    if not re.fullmatch(r"[0-9]+(\.[0-9]+)?", value):
        raise WalletStoreError(f"{field_name} must be a non-negative decimal string.")
    parsed = _to_non_negative_decimal(value)
    if parsed <= Decimal("0"):
        raise WalletStoreError(f"{field_name} must be greater than zero.")
    return parsed


def _parse_v3_range_text(raw: str) -> tuple[str, str, str]:
    text = str(raw or "").strip()
    parts = [part.strip() for part in text.split(":")]
    if len(parts) != 3:
        raise WalletStoreError("v3-range must use format fee:tickLower:tickUpper.")
    fee, tick_lower, tick_upper = parts
    if not re.fullmatch(r"[0-9]+", fee):
        raise WalletStoreError("v3-range fee must be a positive integer.")
    if not re.fullmatch(r"-?[0-9]+", tick_lower) or not re.fullmatch(r"-?[0-9]+", tick_upper):
        raise WalletStoreError("v3-range ticks must be signed integers.")
    if int(fee) <= 0:
        raise WalletStoreError("v3-range fee must be greater than zero.")
    if int(tick_lower) >= int(tick_upper):
        raise WalletStoreError("v3-range tickLower must be less than tickUpper.")
    return fee, tick_lower, tick_upper


def _intent_details_dict(intent: dict[str, Any]) -> dict[str, Any]:
    details = intent.get("details")
    if isinstance(details, dict):
        return details
    return {}


def _v3_details_dict(details: dict[str, Any]) -> dict[str, Any]:
    payload = details.get("v3")
    if isinstance(payload, dict):
        return payload
    return {}


def _resolve_raydium_pool_id(adapter: Any, explicit_pool_id: str) -> str:
    pool_id = str(explicit_pool_id or "").strip()
    if pool_id:
        return pool_id
    pool_registry = (adapter.adapter_metadata or {}).get("poolRegistry") if isinstance(adapter.adapter_metadata, dict) else {}
    if isinstance(pool_registry, dict) and len(pool_registry) == 1:
        only_entry = next(iter(pool_registry.values()))
        if isinstance(only_entry, dict):
            pool_id = str(only_entry.get("poolId") or "").strip()
    return pool_id


def _resolve_agent_id_or_fail(chain: str) -> str:
    api_key = _resolve_api_key()
    agent_id = _resolve_agent_id(api_key)
    if not agent_id:
        raise WalletStoreError("Agent id could not be resolved. Set XCLAW_AGENT_ID or use signed agent token format.")
    return agent_id


def cmd_liquidity_discover_pairs(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    chain = str(args.chain or "").strip()
    dex = str(args.dex or "").strip().lower()
    try:
        assert_chain_capability(chain, "liquidity")
        adapter = build_liquidity_adapter_for_request(chain=chain, dex=dex, position_type="v2")
        if adapter.protocol_family != "amm_v2":
            return fail(
                "unsupported_liquidity_adapter",
                f"Pair discovery currently supports v2-family adapters only. Resolved adapter family: {adapter.protocol_family}.",
                "Use a v2-family DEX for discovery and retry.",
                {"chain": chain, "dex": dex, "adapterFamily": adapter.protocol_family},
                exit_code=2,
            )

        min_reserve = int(str(args.min_reserve or "1"))
        limit = int(str(args.limit or "10"))
        scan_max = int(str(getattr(args, "scan_max", None) or "50"))
        if min_reserve < 0:
            return fail("invalid_input", "min-reserve must be >= 0.", "Provide a non-negative integer.", {"minReserve": args.min_reserve}, exit_code=2)
        if limit < 1 or limit > 100:
            return fail("invalid_input", "limit must be between 1 and 100.", "Use --limit in [1..100].", {"limit": args.limit}, exit_code=2)
        if scan_max < 1 or scan_max > 2000:
            return fail("invalid_input", "scan-max must be between 1 and 2000.", "Use --scan-max in [1..2000].", {"scanMax": args.scan_max}, exit_code=2)

        router = _require_chain_contract_address(chain, "router")
        factory_raw = _cast_call_stdout(chain, router, "factory()(address)")
        factory = _parse_address_from_cast_output(factory_raw)
        if factory.lower() == "0x0000000000000000000000000000000000000000":
            return fail(
                "liquidity_pair_discovery_failed",
                f"Factory address resolved to zero for router {router}.",
                "Verify chain router/factory contract metadata and retry.",
                {"chain": chain, "dex": dex, "router": router},
                exit_code=1,
            )

        pair_len_raw = _cast_call_stdout(chain, factory, "allPairsLength()(uint256)")
        pair_count = _parse_uint_from_cast_output(pair_len_raw)
        if pair_count <= 0:
            return fail(
                "liquidity_no_viable_pair",
                "Factory returned zero pairs.",
                "Try another DEX on this chain or verify deployment state.",
                {"chain": chain, "dex": dex, "factory": factory, "pairCount": pair_count},
                exit_code=1,
            )

        scan_cap = min(pair_count, scan_max)
        candidates: list[dict[str, Any]] = []
        skipped = 0
        failures = 0
        error_samples: list[str] = []
        for idx in range(scan_cap):
            try:
                pair_out = _cast_call_stdout(chain, factory, "allPairs(uint256)(address)", str(idx))
                pair_addr = _parse_address_from_cast_output(pair_out)
                token0 = _parse_address_from_cast_output(_cast_call_stdout(chain, pair_addr, "token0()(address)"))
                token1 = _parse_address_from_cast_output(_cast_call_stdout(chain, pair_addr, "token1()(address)"))
                reserves_out = _cast_call_stdout(chain, pair_addr, "getReserves()(uint112,uint112,uint32)")
                reserve_values = _parse_uint_tuple_from_cast_output(reserves_out)
                if len(reserve_values) < 2:
                    raise WalletStoreError("Unable to parse reserves from getReserves output.")
                reserve0 = int(reserve_values[0])
                reserve1 = int(reserve_values[1])
                if reserve0 < min_reserve or reserve1 < min_reserve:
                    skipped += 1
                    continue
                candidates.append(
                    {
                        "pairAddress": pair_addr.lower(),
                        "token0": token0.lower(),
                        "token1": token1.lower(),
                        "reserve0": str(reserve0),
                        "reserve1": str(reserve1),
                        "minReserve": str(min(reserve0, reserve1)),
                    }
                )
            except Exception as exc:
                failures += 1
                if len(error_samples) < 5:
                    error_samples.append(f"index={idx}: {exc}")
                continue

        if not candidates:
            return fail(
                "liquidity_no_viable_pair",
                "No viable pair matched reserve filters during discovery scan.",
                "Lower --min-reserve, try another DEX, or verify pair liquidity.",
                {
                    "chain": chain,
                    "dex": dex,
                    "factory": factory,
                    "pairCount": pair_count,
                    "scanCount": scan_cap,
                    "minReserve": str(min_reserve),
                    "skipped": skipped,
                    "failures": failures,
                    "errorSamples": error_samples,
                },
                exit_code=1,
            )

        candidates.sort(key=lambda row: int(str(row.get("minReserve") or "0")), reverse=True)
        selected = candidates[:limit]
        return ok(
            "Liquidity pair discovery complete.",
            chain=chain,
            dex=dex,
            adapterFamily=adapter.protocol_family,
            router=router.lower(),
            factory=factory.lower(),
            pairCount=pair_count,
            scanCount=scan_cap,
            minReserve=str(min_reserve),
            scanMax=scan_max,
            candidateCount=len(candidates),
            returnedCount=len(selected),
            truncated=pair_count > scan_cap,
            pairs=selected,
            errorSamples=error_samples,
        )
    except ChainRegistryError as exc:
        return fail("unsupported_chain_capability", str(exc), chain_supported_hint(), {"chain": chain, "requiredCapability": "liquidity"}, exit_code=2)
    except UnsupportedLiquidityAdapter as exc:
        return fail(
            "unsupported_liquidity_adapter",
            str(exc),
            "Choose a supported chain/dex combination and retry.",
            {"chain": chain, "dex": dex},
            exit_code=2,
        )
    except WalletStoreError as exc:
        return fail(
            "liquidity_pair_discovery_failed",
            str(exc),
            "Verify router/factory metadata, chain RPC availability, and retry.",
            {"chain": chain, "dex": dex},
            exit_code=1,
        )
    except Exception as exc:
        return fail(
            "liquidity_pair_discovery_failed",
            str(exc),
            "Inspect runtime pair discovery path and retry.",
            {"chain": chain, "dex": dex},
            exit_code=1,
        )


def cmd_liquidity_quote_add(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    chain = str(args.chain or "").strip()
    dex = str(args.dex or "").strip().lower()
    try:
        assert_chain_capability(chain, "liquidity")
        default_position_type = "v3" if _is_solana_chain(chain) else "v2"
        position_type = str(args.position_type or default_position_type).strip().lower()
        adapter = build_liquidity_adapter_for_request(chain=chain, dex=dex, position_type=position_type)
        token_a = _resolve_token_address(chain, args.token_a)
        token_b = _resolve_token_address(chain, args.token_b)
        if token_a.lower() == token_b.lower():
            return fail("invalid_input", "token-a and token-b must be different.", "Provide distinct token values.", {"chain": chain}, exit_code=2)
        amount_a_h = _parse_positive_amount_text(str(args.amount_a), "amount-a")
        amount_b_h = _parse_positive_amount_text(str(args.amount_b), "amount-b")
        slippage_bps = int(args.slippage_bps)
        if slippage_bps < 0 or slippage_bps > 5000:
            return fail("invalid_input", "slippage-bps must be between 0 and 5000.", "Use integer bps in range.", {"slippageBps": args.slippage_bps}, exit_code=2)
        v3_meta: dict[str, Any] = {}
        if position_type == "v3":
            v3_range_text = str(args.v3_range or "").strip()
            if not v3_range_text and _is_solana_chain(chain):
                v3_range_text = "100:0:0"
            try:
                fee, tick_lower, tick_upper = _parse_v3_range_text(v3_range_text)
            except WalletStoreError as exc:
                return fail("invalid_input", str(exc), "Provide --v3-range fee:tickLower:tickUpper.", {"chain": chain, "dex": dex}, exit_code=2)
            v3_meta = {
                "fee": fee,
                "tickLower": tick_lower,
                "tickUpper": tick_upper,
                "deadlineSec": 120,
            }
        preflight = adapter.quote_add(
            {
                "tokenA": token_a,
                "tokenB": token_b,
                "amountA": _decimal_text(amount_a_h),
                "amountB": _decimal_text(amount_b_h),
                "slippageBps": slippage_bps,
            }
        )
        if _is_solana_chain(chain):
            if adapter.protocol_family == "local_clmm":
                local_quote = solana_local_quote_add(
                    amount_a=_decimal_text(amount_a_h),
                    amount_b=_decimal_text(amount_b_h),
                    slippage_bps=slippage_bps,
                )
            elif adapter.protocol_family == "raydium_clmm":
                pool_id = _resolve_raydium_pool_id(adapter, str(getattr(args, "pool_id", "") or ""))
                if not pool_id:
                    return fail(
                        "invalid_input",
                        "Raydium quote-add requires --pool-id when no single default pool is configured.",
                        "Provide --pool-id for the target Raydium CLMM pool.",
                        {"chain": chain, "dex": dex},
                        exit_code=2,
                    )
                local_quote = solana_raydium_quote_add(
                    amount_a=_decimal_text(amount_a_h),
                    amount_b=_decimal_text(amount_b_h),
                    slippage_bps=slippage_bps,
                    pool_id=pool_id,
                )
            else:
                return fail(
                    "unsupported_liquidity_execution_family",
                    f"Unsupported Solana liquidity adapter family '{adapter.protocol_family}' for quote-add.",
                    "Use local_clmm or raydium_clmm adapter.",
                    {"chain": chain, "dex": dex, "positionType": position_type},
                    exit_code=2,
                )
            return ok(
                "Liquidity add quote ready.",
                chain=chain,
                dex=dex,
                positionType=position_type,
                tokenA=token_a,
                tokenB=token_b,
                amountA=_decimal_text(amount_a_h),
                amountB=_decimal_text(amount_b_h),
                quoteAmountB=local_quote.get("amountB"),
                minAmountB=local_quote.get("minAmountB"),
                slippageBps=slippage_bps,
                tokenASymbol=None,
                tokenBSymbol=None,
                tokenADecimals=9,
                tokenBDecimals=9,
                adapterFamily=adapter.protocol_family,
                preflight={**preflight.get("simulation", {}), **local_quote},
                simulationOnly=True,
            )
        token_a_meta = _fetch_erc20_metadata(chain, token_a)
        token_b_meta = _fetch_erc20_metadata(chain, token_b)
        token_a_decimals = int(token_a_meta.get("decimals", 18))
        token_b_decimals = int(token_b_meta.get("decimals", 18))
        amount_a_units = _to_units_uint(_decimal_text(amount_a_h), token_a_decimals)
        quote_out_units = _router_get_amount_out(chain, amount_a_units, token_a, token_b)
        quote_out_h = _format_units(int(quote_out_units), token_b_decimals)
        min_b_h = _decimal_text(_to_non_negative_decimal(quote_out_h) * Decimal(max(0, 10000 - slippage_bps)) / Decimal(10000))
        return ok(
            "Liquidity add quote ready.",
            chain=chain,
            dex=dex,
            positionType=position_type,
            tokenA=token_a,
            tokenB=token_b,
            amountA=_decimal_text(amount_a_h),
            amountB=_decimal_text(amount_b_h),
            quoteAmountB=quote_out_h,
            minAmountB=min_b_h,
            slippageBps=slippage_bps,
            tokenASymbol=token_a_meta.get("symbol"),
            tokenBSymbol=token_b_meta.get("symbol"),
            tokenADecimals=token_a_decimals,
            tokenBDecimals=token_b_decimals,
            adapterFamily=adapter.protocol_family,
            preflight=preflight.get("simulation", {}),
            simulationOnly=True,
        )
    except ChainRegistryError as exc:
        return fail("unsupported_chain_capability", str(exc), chain_supported_hint(), {"chain": chain, "requiredCapability": "liquidity"}, exit_code=2)
    except UnsupportedLiquidityAdapter as exc:
        return fail(
            "unsupported_liquidity_adapter",
            str(exc),
            "Choose a supported chain/dex/position-type combination and retry.",
            {"chain": chain, "dex": dex, "positionType": str(args.position_type or "v2")},
            exit_code=2,
        )
    except LiquidityAdapterError as exc:
        return fail("liquidity_preflight_failed", str(exc), "Fix the request payload and retry.", {"chain": chain, "dex": dex}, exit_code=2)
    except WalletStoreError as exc:
        return fail("liquidity_quote_add_failed", str(exc), "Verify tokens/amounts and retry.", {"chain": chain, "dex": dex}, exit_code=1)
    except Exception as exc:
        return fail("liquidity_quote_add_failed", str(exc), "Inspect runtime liquidity quote-add path and retry.", {"chain": chain, "dex": dex}, exit_code=1)


def cmd_liquidity_quote_remove(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    chain = str(args.chain or "").strip()
    dex = str(args.dex or "").strip().lower()
    try:
        assert_chain_capability(chain, "liquidity")
        default_position_type = "v3" if _is_solana_chain(chain) else "v2"
        position_type = str(args.position_type or default_position_type).strip().lower()
        adapter = build_liquidity_adapter_for_request(chain=chain, dex=dex, position_type=position_type)
        position_id = str(args.position_id or "").strip()
        if not position_id:
            return fail("invalid_input", "position-id is required.", "Provide --position-id and retry.", {"chain": chain, "dex": dex}, exit_code=2)
        percent = int(args.percent)
        if percent < 1 or percent > 100:
            return fail("invalid_input", "percent must be between 1 and 100.", "Use --percent in [1..100].", {"percent": args.percent}, exit_code=2)
        preflight = adapter.quote_remove({"positionId": position_id, "percent": percent})
        if _is_solana_chain(chain) and adapter.protocol_family == "raydium_clmm":
            pool_id = _resolve_raydium_pool_id(adapter, str(getattr(args, "pool_id", "") or ""))
            if not pool_id:
                return fail(
                    "invalid_input",
                    "Raydium quote-remove requires --pool-id when no single default pool is configured.",
                    "Provide --pool-id for the target Raydium CLMM pool.",
                    {"chain": chain, "dex": dex, "positionId": position_id},
                    exit_code=2,
                )
            preflight = {"simulation": solana_raydium_quote_remove(percent=percent, pool_id=pool_id)}
        return ok(
            "Liquidity remove quote ready.",
            chain=chain,
            dex=dex,
            positionType=position_type,
            positionId=position_id,
            percent=percent,
            adapterFamily=adapter.protocol_family,
            preflight=preflight.get("simulation", {}),
            simulationOnly=True,
            note="Exact remove outputs are adapter-specific; runtime will recompute pre-execution.",
        )
    except ChainRegistryError as exc:
        return fail("unsupported_chain_capability", str(exc), chain_supported_hint(), {"chain": chain, "requiredCapability": "liquidity"}, exit_code=2)
    except UnsupportedLiquidityAdapter as exc:
        return fail(
            "unsupported_liquidity_adapter",
            str(exc),
            "Choose a supported chain/dex/position-type combination and retry.",
            {"chain": chain, "dex": dex, "positionType": str(args.position_type or "v2")},
            exit_code=2,
        )
    except LiquidityAdapterError as exc:
        return fail("liquidity_preflight_failed", str(exc), "Fix the request payload and retry.", {"chain": chain, "dex": dex}, exit_code=2)
    except Exception as exc:
        return fail("liquidity_quote_remove_failed", str(exc), "Inspect runtime liquidity quote-remove path and retry.", {"chain": chain, "dex": dex}, exit_code=1)


def cmd_liquidity_add(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    chain = str(args.chain or "").strip()
    dex = str(args.dex or "").strip().lower()
    try:
        assert_chain_capability(chain, "liquidity")
        default_position_type = "v3" if _is_solana_chain(chain) else "v2"
        position_type = str(args.position_type or default_position_type).strip().lower()
        token_a = _resolve_token_address(chain, args.token_a)
        token_b = _resolve_token_address(chain, args.token_b)
        if token_a.lower() == token_b.lower():
            return fail("invalid_input", "token-a and token-b must be different.", "Provide distinct token values.", {"chain": chain}, exit_code=2)
        amount_a_h = _parse_positive_amount_text(str(args.amount_a), "amount-a")
        amount_b_h = _parse_positive_amount_text(str(args.amount_b), "amount-b")
        slippage_bps = int(args.slippage_bps)
        if slippage_bps < 0 or slippage_bps > 5000:
            return fail("invalid_input", "slippage-bps must be between 0 and 5000.", "Use integer bps in range.", {"slippageBps": args.slippage_bps}, exit_code=2)
        v3_meta: dict[str, Any] = {}
        if position_type == "v3":
            v3_range_text = str(args.v3_range or "").strip()
            if not v3_range_text and _is_solana_chain(chain):
                v3_range_text = "100:0:0"
            try:
                fee, tick_lower, tick_upper = _parse_v3_range_text(v3_range_text)
            except WalletStoreError as exc:
                return fail("invalid_input", str(exc), "Provide --v3-range fee:tickLower:tickUpper.", {"chain": chain, "dex": dex}, exit_code=2)
            v3_meta = {"fee": fee, "tickLower": tick_lower, "tickUpper": tick_upper, "deadlineSec": 120}

        provider_requested, _ = _liquidity_provider_settings(chain)
        adapter = build_liquidity_adapter_for_request(chain=chain, dex=dex, position_type=position_type)
        adapter_preflight = adapter.quote_add(
            {
                "tokenA": token_a,
                "tokenB": token_b,
                "amountA": _decimal_text(amount_a_h),
                "amountB": _decimal_text(amount_b_h),
                "slippageBps": slippage_bps,
            }
        )
        adapter_family = adapter.protocol_family
        adapter_dex = adapter.dex
        if _is_solana_chain(chain) and adapter.protocol_family == "raydium_clmm":
            pool_id = _resolve_raydium_pool_id(adapter, str(getattr(args, "pool_id", "") or ""))
            if not pool_id:
                return fail(
                    "invalid_input",
                    "Raydium liquidity add requires --pool-id when no single default pool is configured.",
                    "Provide --pool-id for the target Raydium CLMM pool.",
                    {"chain": chain, "dex": dex},
                    exit_code=2,
                )
            v3_meta["poolId"] = pool_id
        agent_id = _resolve_agent_id_or_fail(chain)
        preflight = adapter_preflight
        payload = {
            "schemaVersion": 1,
            "agentId": agent_id,
            "chainKey": chain,
            "dex": adapter_dex,
            "action": "add",
            "positionType": position_type,
            "tokenA": token_a,
            "tokenB": token_b,
            "amountA": _decimal_text(amount_a_h),
            "amountB": _decimal_text(amount_b_h),
            "slippageBps": slippage_bps,
            "details": {
                "v3Range": str(args.v3_range or "").strip() or None,
                "v3": v3_meta if position_type == "v3" else None,
                "adapterFamily": adapter_family,
                "preflight": preflight.get("simulation", {}) if isinstance(preflight, dict) else {},
                "providerRequested": provider_requested,
                "source": "runtime_liquidity_add",
            },
        }
        status_code, body = _api_request("POST", "/liquidity/proposed", payload=payload, include_idempotency=True)
        if status_code < 200 or status_code >= 300:
            return fail(
                str(body.get("code", "api_error")),
                str(body.get("message", f"liquidity proposed failed ({status_code})")),
                str(body.get("actionHint", "Verify policy/approval settings and retry.")),
                _api_error_details(status_code, body, "/liquidity/proposed", chain=chain),
                exit_code=1,
            )
        liquidity_intent_id = str(body.get("liquidityIntentId") or "").strip()
        status = str(body.get("status") or "")
        if status == "approval_pending":
            flow = {
                "liquidityIntentId": liquidity_intent_id,
                "chainKey": chain,
                "dex": adapter_dex,
                "action": "add",
                "tokenA": token_a,
                "tokenB": token_b,
                "amountA": _decimal_text(amount_a_h),
                "amountB": _decimal_text(amount_b_h),
            }
            try:
                _maybe_send_telegram_liquidity_approval_prompt(flow)
            except Exception:
                pass
            queued_message = (
                "Approval required (liquidity)\n\n"
                "Request: Add liquidity\n"
                f"Pair: {token_a}/{token_b}\n"
                f"Amounts: {_decimal_text(amount_a_h)} / {_decimal_text(amount_b_h)}\n"
                f"Chain: `{chain}`\n"
                f"DEX: `{adapter_dex}`\n"
                f"Intent ID: `{liquidity_intent_id}`\n"
                "Status: approval_pending\n\n"
                "Tap Approve or Deny."
            )
            return fail(
                "approval_required",
                "Liquidity add is waiting for management approval.",
                "Send queuedMessage verbatim so Telegram buttons can attach, then wait for Approve/Deny.",
                {
                    "liquidityIntentId": liquidity_intent_id,
                    "chain": chain,
                    "dex": adapter_dex,
                    "status": status,
                    "queuedMessage": queued_message,
                    "nextAction": "Post queuedMessage verbatim to the user in the active chat.",
                },
                exit_code=1,
            )
        if status == "approved":
            code, payload = _run_liquidity_execute_inline(liquidity_intent_id, chain)
            if isinstance(payload, dict):
                payload.setdefault("liquidityIntentId", liquidity_intent_id)
                payload.setdefault("chain", chain)
                payload.setdefault("dex", adapter_dex)
                payload.setdefault("adapterFamily", adapter_family)
            return emit(payload) if isinstance(payload, dict) else code
        return ok(
            "Liquidity add intent created.",
            chain=chain,
            dex=adapter_dex,
            liquidityIntentId=liquidity_intent_id,
            status=status or "approved",
            approvalMode=status != "approval_pending",
            adapterFamily=adapter_family,
            preflight=preflight.get("simulation", {}) if isinstance(preflight, dict) else {},
            providerRequested=provider_requested,
        )
    except ChainRegistryError as exc:
        return fail("unsupported_chain_capability", str(exc), chain_supported_hint(), {"chain": chain, "requiredCapability": "liquidity"}, exit_code=2)
    except UnsupportedLiquidityAdapter as exc:
        return fail(
            "unsupported_liquidity_adapter",
            str(exc),
            "Choose a supported chain/dex/position-type combination and retry.",
            {"chain": chain, "dex": dex, "positionType": str(args.position_type or "v2")},
            exit_code=2,
        )
    except LiquidityAdapterError as exc:
        return fail("liquidity_preflight_failed", str(exc), "Fix preflight parameters and retry.", {"chain": chain, "dex": dex}, exit_code=2)
    except WalletStoreError as exc:
        return fail("liquidity_add_failed", str(exc), "Verify API env/auth, chain capability, and inputs.", {"chain": chain, "dex": dex}, exit_code=1)
    except Exception as exc:
        return fail("liquidity_add_failed", str(exc), "Inspect runtime liquidity add path and retry.", {"chain": chain, "dex": dex}, exit_code=1)


def cmd_liquidity_remove(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    chain = str(args.chain or "").strip()
    dex = str(args.dex or "").strip().lower()
    try:
        assert_chain_capability(chain, "liquidity")
        default_position_type = "v3" if _is_solana_chain(chain) else "v2"
        position_type = str(args.position_type or default_position_type).strip().lower()
        provider_requested, _ = _liquidity_provider_settings(chain)
        adapter = build_liquidity_adapter_for_request(chain=chain, dex=dex, position_type=position_type)
        adapter_preflight: dict[str, Any] = {}
        adapter_dex = adapter.dex
        adapter_family = adapter.protocol_family
        agent_id = _resolve_agent_id_or_fail(chain)
        position_id = str(args.position_id or "").strip()
        if not position_id:
            return fail("invalid_input", "position-id is required.", "Provide --position-id and retry.", {"chain": chain, "dex": dex}, exit_code=2)
        percent = int(args.percent)
        if percent < 1 or percent > 100:
            return fail("invalid_input", "percent must be between 1 and 100.", "Use --percent in [1..100].", {"percent": args.percent}, exit_code=2)
        slippage_bps = int(args.slippage_bps)
        if slippage_bps < 0 or slippage_bps > 5000:
            return fail("invalid_input", "slippage-bps must be between 0 and 5000.", "Use integer bps in range.", {"slippageBps": args.slippage_bps}, exit_code=2)
        adapter_preflight = adapter.quote_remove(
            {
                "positionId": position_id,
                "percent": percent,
                "slippageBps": slippage_bps,
            }
        )
        preflight = adapter_preflight
        if _is_solana_chain(chain):
            token_a_in = str(args.token_a or "").strip()
            token_b_in = str(args.token_b or "").strip()
            if not token_a_in or not token_b_in:
                return fail(
                    "invalid_input",
                    "token-a and token-b are required for Solana liquidity remove intents.",
                    "Provide --token-a <mint> --token-b <mint> and retry.",
                    {"chain": chain, "dex": adapter_dex, "positionId": position_id},
                    exit_code=2,
                )
            resolved_token_a = _resolve_token_address(chain, token_a_in)
            resolved_token_b = _resolve_token_address(chain, token_b_in)
        elif adapter_family == "position_manager_v3":
            if not adapter.position_manager:
                return fail(
                    "chain_config_invalid",
                    "Concentrated-liquidity execution metadata is incomplete for this chain.",
                    "Add execution.liquidity adapter position-manager metadata and retry.",
                    {"chain": chain, "dex": adapter_dex, "positionId": position_id},
                    exit_code=2,
                )
            snapshot = _read_v3_position_snapshot(chain, adapter.position_manager, position_id)
            resolved_token_a = str(snapshot.get("token0") or "").strip()
            resolved_token_b = str(snapshot.get("token1") or "").strip()
        else:
            resolved_token_a, resolved_token_b = _resolve_liquidity_remove_tokens(
                chain,
                position_id,
                str(args.token_a or "").strip(),
                str(args.token_b or "").strip(),
            )
        display_token_a = _token_symbol_for_display(chain, resolved_token_a) or resolved_token_a
        display_token_b = _token_symbol_for_display(chain, resolved_token_b) or resolved_token_b
        if adapter_family == "amm_v2":
            remove_context = _compute_v2_remove_liquidity_units(
                chain=chain,
                position_id=position_id,
                token_a=resolved_token_a,
                token_b=resolved_token_b,
                percent=percent,
            )
            liquidity_units = int(remove_context.get("liquidityUnits") or 0)
            if liquidity_units <= 0:
                return fail(
                    "liquidity_preflight_zero_lp_balance",
                    "Position has no removable LP token balance for the requested percent.",
                    "Refresh liquidity positions or choose a position with non-zero LP balance.",
                    {
                        "chain": chain,
                        "dex": adapter_dex,
                        "positionId": position_id,
                        "pair": str(remove_context.get("pair") or "").lower(),
                        "lpToken": str(remove_context.get("lpToken") or "").lower(),
                        "lpBalance": str(remove_context.get("lpBalance") or "0"),
                        "percent": percent,
                    },
                    exit_code=1,
                )
        payload = {
            "schemaVersion": 1,
            "agentId": agent_id,
            "chainKey": chain,
            "dex": adapter_dex,
            "action": "remove",
            "positionType": position_type,
            "tokenA": resolved_token_a,
            "tokenB": resolved_token_b,
            "amountA": str(percent),
            "amountB": "0",
            "positionId": position_id,
            "slippageBps": slippage_bps,
            "details": {
                "percent": percent,
                "v3": {
                    "positionId": position_id,
                    "percent": percent,
                    "minAmountAUnits": "0",
                    "minAmountBUnits": "0",
                    "poolId": str(getattr(args, "pool_id", "") or "").strip() or None,
                }
                if position_type == "v3"
                else None,
                "adapterFamily": adapter_family,
                "tokenASymbol": display_token_a,
                "tokenBSymbol": display_token_b,
                "preflight": preflight.get("simulation", {}) if isinstance(preflight, dict) else {},
                "providerRequested": provider_requested,
                "source": "runtime_liquidity_remove",
            },
        }
        status_code, body = _api_request("POST", "/liquidity/proposed", payload=payload, include_idempotency=True)
        if status_code < 200 or status_code >= 300:
            return fail(
                str(body.get("code", "api_error")),
                str(body.get("message", f"liquidity proposed failed ({status_code})")),
                str(body.get("actionHint", "Verify policy/approval settings and retry.")),
                _api_error_details(status_code, body, "/liquidity/proposed", chain=chain),
                exit_code=1,
            )
        liquidity_intent_id = str(body.get("liquidityIntentId") or "").strip()
        status = str(body.get("status") or "")
        if status == "approval_pending":
            flow = {
                "liquidityIntentId": liquidity_intent_id,
                "chainKey": chain,
                "dex": adapter_dex,
                "action": "remove",
                "tokenA": resolved_token_a,
                "tokenB": resolved_token_b,
                "tokenASymbol": display_token_a,
                "tokenBSymbol": display_token_b,
                "positionId": position_id,
                "percent": percent,
                "amountA": str(percent),
                "amountB": "0",
            }
            try:
                _maybe_send_telegram_liquidity_approval_prompt(flow)
            except Exception:
                pass
            queued_message = (
                "Approval required (liquidity)\n\n"
                "Request: Remove liquidity\n"
                f"Pair: {display_token_a}/{display_token_b}\n"
                f"Position ID: `{position_id}`\n"
                f"Percent: {percent}%\n"
                f"Chain: `{chain}`\n"
                f"DEX: `{adapter_dex}`\n"
                f"Intent ID: `{liquidity_intent_id}`\n"
                "Status: approval_pending\n\n"
                "Tap Approve or Deny."
            )
            return fail(
                "approval_required",
                "Liquidity remove is waiting for management approval.",
                "Send queuedMessage verbatim so Telegram buttons can attach, then wait for Approve/Deny.",
                {
                    "liquidityIntentId": liquidity_intent_id,
                    "chain": chain,
                    "dex": adapter_dex,
                    "tokenA": resolved_token_a,
                    "tokenB": resolved_token_b,
                    "tokenASymbol": display_token_a,
                    "tokenBSymbol": display_token_b,
                    "status": status,
                    "queuedMessage": queued_message,
                    "nextAction": "Post queuedMessage verbatim to the user in the active chat.",
                },
                exit_code=1,
            )
        if status == "approved":
            code, payload = _run_liquidity_execute_inline(liquidity_intent_id, chain)
            if isinstance(payload, dict):
                payload.setdefault("liquidityIntentId", liquidity_intent_id)
                payload.setdefault("chain", chain)
                payload.setdefault("dex", adapter_dex)
                payload.setdefault("adapterFamily", adapter_family)
            return emit(payload) if isinstance(payload, dict) else code
        return ok(
            "Liquidity remove intent created.",
            chain=chain,
            dex=adapter_dex,
            liquidityIntentId=liquidity_intent_id,
            status=status or "approved",
            positionId=position_id,
            percent=percent,
            adapterFamily=adapter_family,
            preflight=preflight.get("simulation", {}) if isinstance(preflight, dict) else {},
            providerRequested=provider_requested,
        )
    except ChainRegistryError as exc:
        return fail("unsupported_chain_capability", str(exc), chain_supported_hint(), {"chain": chain, "requiredCapability": "liquidity"}, exit_code=2)
    except UnsupportedLiquidityAdapter as exc:
        return fail(
            "unsupported_liquidity_adapter",
            str(exc),
            "Choose a supported chain/dex/position-type combination and retry.",
            {"chain": chain, "dex": dex, "positionType": str(args.position_type or "v2")},
            exit_code=2,
        )
    except LiquidityAdapterError as exc:
        return fail("liquidity_preflight_failed", str(exc), "Fix preflight parameters and retry.", {"chain": chain, "dex": dex}, exit_code=2)
    except WalletStoreError as exc:
        return fail("liquidity_remove_failed", str(exc), "Verify API env/auth, chain capability, and inputs.", {"chain": chain, "dex": dex}, exit_code=1)
    except Exception as exc:
        return fail("liquidity_remove_failed", str(exc), "Inspect runtime liquidity remove path and retry.", {"chain": chain, "dex": dex}, exit_code=1)


def cmd_liquidity_increase(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    chain = str(args.chain or "").strip()
    dex = str(args.dex or "").strip().lower()
    position_id = str(args.position_id or "").strip()
    try:
        assert_chain_capability(chain, "liquidity")
        if not position_id:
            return fail("invalid_input", "position-id is required.", "Provide --position-id and retry.", {"chain": chain}, exit_code=2)
        slippage_bps = int(args.slippage_bps)
        if slippage_bps < 0 or slippage_bps > 5000:
            return fail("invalid_input", "slippage-bps must be between 0 and 5000.", "Use integer bps in range.", {"slippageBps": args.slippage_bps}, exit_code=2)

        provider_requested, _ = _liquidity_provider_settings(chain)
        adapter = build_liquidity_adapter_for_request(chain=chain, dex=dex, position_type="v3")
        if adapter.protocol_family not in {"position_manager_v3", "local_clmm", "raydium_clmm"}:
            return fail(
                "unsupported_liquidity_execution_family",
                f"Liquidity increase requires a concentrated-liquidity execution adapter, got '{adapter.protocol_family}'.",
                "Use a chain/dex with advanced concentrated-liquidity support and retry.",
                {"chain": chain, "dex": dex, "positionId": position_id},
                exit_code=2,
            )
        if not adapter.supports_operation("increase"):
            return fail(
                "unsupported_liquidity_operation",
                f"Adapter '{adapter.dex}' does not support liquidity increase on chain '{chain}'.",
                "Choose a supported chain/dex combination and retry.",
                {"chain": chain, "dex": adapter.dex, "positionId": position_id},
                exit_code=2,
            )
        token_a = _resolve_token_address(chain, str(args.token_a or ""))
        token_b = _resolve_token_address(chain, str(args.token_b or ""))
        amount_a_text = _decimal_text(_parse_positive_amount_text(str(args.amount_a), "amount-a"))
        amount_b_text = _decimal_text(_parse_positive_amount_text(str(args.amount_b), "amount-b"))
        deadline = str(int(datetime.now(timezone.utc).timestamp()) + 120)

        if _is_solana_chain(chain) and adapter.protocol_family in {"local_clmm", "raydium_clmm"}:
            store = load_wallet_store()
            wallet_address, secret = _execution_wallet_solana_secret(store, chain)
            amount_a_units = str(_to_units_uint(amount_a_text, 9))
            amount_b_units = str(_to_units_uint(amount_b_text, 9))
            min_a_units = str((int(amount_a_units) * max(0, 10000 - slippage_bps)) // 10000)
            min_b_units = str((int(amount_b_units) * max(0, 10000 - slippage_bps)) // 10000)
            if adapter.protocol_family == "local_clmm":
                if chain != "solana_localnet":
                    return fail(
                        "unsupported_liquidity_adapter",
                        "local_clmm adapter is only supported on solana_localnet.",
                        "Switch to solana_localnet or use raydium_clmm.",
                        {"chain": chain, "dex": dex, "positionId": position_id},
                        exit_code=2,
                    )
                increased = solana_local_increase_position(
                    chain=chain,
                    dex=adapter.dex,
                    owner=wallet_address,
                    position_id=position_id,
                    amount_a=amount_a_text,
                    amount_b=amount_b_text,
                )
                tx_hash = str(increased.get("txHash") or "")
                details = {
                    "amountAUnits": amount_a_units,
                    "amountBUnits": amount_b_units,
                    "minAmountAUnits": min_a_units,
                    "minAmountBUnits": min_b_units,
                    "approveTxHashes": [],
                    "operationTxHashes": [tx_hash] if tx_hash else [],
                    "simulationMode": True,
                    "routeKind": "adapter_default",
                    **increased,
                }
                return ok(
                    "Liquidity position increased.",
                    chain=chain,
                    dex=adapter.dex,
                    positionId=position_id,
                    txHash=tx_hash,
                    approveTxHashes=[],
                    operationTxHashes=[tx_hash] if tx_hash else [],
                    providerRequested=provider_requested,
                    providerUsed="router_adapter",
                    fallbackUsed=False,
                    fallbackReason=None,
                    executionFamily="solana_clmm",
                    executionAdapter=adapter.dex,
                    routeKind="adapter_default",
                    liquidityOperation="increase",
                    details=details,
                )

            pool_id = _resolve_raydium_pool_id(adapter, "")
            if not pool_id:
                return fail(
                    "invalid_input",
                    "Raydium liquidity increase requires configured pool metadata.",
                    "Provide pool metadata in chain config or include a single default pool.",
                    {"chain": chain, "dex": dex, "positionId": position_id},
                    exit_code=2,
                )
            execution = solana_raydium_execute_instruction(
                chain=chain,
                rpc_url=_chain_rpc_url(chain),
                private_key_bytes=secret,
                owner=wallet_address,
                adapter_metadata=dict(adapter.adapter_metadata or {}),
                request={
                    "poolId": pool_id,
                    "positionId": position_id,
                    "tokenA": token_a,
                    "tokenB": token_b,
                    "amountAUnits": amount_a_units,
                    "amountBUnits": amount_b_units,
                    "minAmountAUnits": min_a_units,
                    "minAmountBUnits": min_b_units,
                    "slippageBps": slippage_bps,
                },
                operation_key="increase",
            )
            tx_hash = str(execution.tx_hash or "")
            details = {
                "poolId": pool_id,
                "amountAUnits": amount_a_units,
                "amountBUnits": amount_b_units,
                "minAmountAUnits": min_a_units,
                "minAmountBUnits": min_b_units,
                "approveTxHashes": [],
                "operationTxHashes": [tx_hash] if tx_hash else [],
                **execution.details,
            }
            return ok(
                "Liquidity position increased.",
                chain=chain,
                dex=adapter.dex,
                positionId=position_id,
                txHash=tx_hash,
                approveTxHashes=[],
                operationTxHashes=[tx_hash] if tx_hash else [],
                providerRequested=provider_requested,
                providerUsed="router_adapter",
                fallbackUsed=False,
                fallbackReason=None,
                executionFamily="solana_clmm",
                executionAdapter=adapter.dex,
                routeKind=execution.route_kind,
                liquidityOperation="increase",
                details=details,
            )

        store = load_wallet_store()
        wallet_address, private_key_hex = _execution_wallet(store, chain)
        token_a_meta = _fetch_erc20_metadata(chain, token_a)
        token_b_meta = _fetch_erc20_metadata(chain, token_b)
        amount_a_units = str(_to_units_uint(amount_a_text, int(token_a_meta.get("decimals", 18))))
        amount_b_units = str(_to_units_uint(amount_b_text, int(token_b_meta.get("decimals", 18))))
        min_a_units = str((int(amount_a_units) * max(0, 10000 - slippage_bps)) // 10000)
        min_b_units = str((int(amount_b_units) * max(0, 10000 - slippage_bps)) // 10000)
        plan = build_liquidity_increase_plan(
            chain=chain,
            dex=adapter.dex,
            position_type="v3",
            request={
                "positionId": position_id,
                "tokenA": token_a,
                "tokenB": token_b,
                "amountAUnits": amount_a_units,
                "amountBUnits": amount_b_units,
                "minAmountAUnits": min_a_units,
                "minAmountBUnits": min_b_units,
                "deadline": deadline,
            },
            wallet_address=wallet_address,
            build_calldata=_cast_calldata,
        )
        execution = execute_liquidity_plan(
            executor=_router_action_executor(),
            plan=plan,
            wallet_address=wallet_address,
            private_key_hex=private_key_hex,
            wait_for_operation_receipts=False,
            liquidity_operation="increase",
        )
        tx_hash = str(execution.tx_hash or "")
        builder_meta = _builder_output_from_hashes(chain, [*execution.approve_tx_hashes, *execution.operation_tx_hashes])
        return ok(
            "Liquidity position increased.",
            chain=chain,
            dex=adapter.dex,
            positionId=position_id,
            txHash=tx_hash,
            approveTxHashes=execution.approve_tx_hashes,
            operationTxHashes=execution.operation_tx_hashes,
            providerRequested=provider_requested,
            providerUsed="router_adapter",
            fallbackUsed=False,
            fallbackReason=None,
            executionFamily=execution.execution_family,
            executionAdapter=execution.execution_adapter,
            routeKind=execution.route_kind,
            liquidityOperation="increase",
            details={**execution.details, **builder_meta},
            **builder_meta,
        )
    except ChainRegistryError as exc:
        return fail("unsupported_chain_capability", str(exc), chain_supported_hint(), {"chain": chain, "requiredCapability": "liquidity"}, exit_code=2)
    except UnsupportedLiquidityAdapter as exc:
        return fail("unsupported_liquidity_adapter", str(exc), "Choose a supported chain/dex/position-type combination and retry.", {"chain": chain, "dex": dex}, exit_code=2)
    except UnsupportedLiquidityOperation as exc:
        return fail("unsupported_liquidity_operation", str(exc), "Use a chain/dex with concentrated-liquidity increase support.", {"chain": chain, "dex": dex, "positionId": position_id}, exit_code=2)
    except ValueError as exc:
        code = str(exc)
        if code == "chain_config_invalid":
            return fail("chain_config_invalid", "Concentrated-liquidity execution metadata is incomplete for this chain.", "Add execution.liquidity adapter position-manager metadata and retry.", {"chain": chain, "dex": dex, "positionId": position_id}, exit_code=2)
        return fail("liquidity_increase_failed", str(exc), "Verify local router-adapter configuration and retry.", {"chain": chain, "dex": dex, "positionId": position_id}, exit_code=1)
    except WalletStoreError as exc:
        return fail("liquidity_increase_failed", str(exc), "Verify local router-adapter configuration and retry.", {"chain": chain, "dex": dex, "positionId": position_id}, exit_code=1)
    except Exception as exc:
        return fail("liquidity_increase_failed", str(exc), "Inspect runtime liquidity increase path and retry.", {"chain": chain, "dex": dex, "positionId": position_id}, exit_code=1)


def cmd_liquidity_claim_fees(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    chain = str(args.chain or "").strip()
    dex = str(args.dex or "").strip().lower()
    position_id = str(args.position_id or "").strip()
    provider_requested = "router_adapter"
    provider_used = "router_adapter"
    fallback_used = False
    fallback_reason: dict[str, str] | None = None

    def _claim_failure_details() -> dict[str, Any]:
        details: dict[str, Any] = {
            "chain": chain,
            "dex": dex,
            "positionId": position_id,
            "operation": "claim_fees",
            "providerRequested": provider_requested,
            "fallbackUsed": bool(fallback_used),
            "fallbackReason": fallback_reason,
        }
        if provider_used:
            details["providerUsed"] = provider_used
        return details

    try:
        assert_chain_capability(chain, "liquidity")
        if not position_id:
            return fail("invalid_input", "position-id is required.", "Provide --position-id and retry.", _claim_failure_details(), exit_code=2)
        provider_requested, _ = _liquidity_provider_settings(chain)
        adapter = build_liquidity_adapter_for_request(chain=chain, dex=dex, position_type="v3")
        if adapter.protocol_family not in {"position_manager_v3", "local_clmm", "raydium_clmm"}:
            return fail(
                "unsupported_liquidity_execution_family",
                f"Liquidity claim-fees requires a concentrated-liquidity execution adapter, got '{adapter.protocol_family}'.",
                "Use a chain/dex with advanced concentrated-liquidity support and retry.",
                _claim_failure_details(),
                exit_code=2,
            )
        if not adapter.supports_operation("claim_fees"):
            return fail(
                "unsupported_liquidity_operation",
                f"Adapter '{adapter.dex}' does not support claim-fees on chain '{chain}'.",
                "Choose a supported chain/dex combination and retry.",
                _claim_failure_details(),
                exit_code=2,
            )
        if _is_solana_chain(chain) and adapter.protocol_family in {"local_clmm", "raydium_clmm"}:
            store = load_wallet_store()
            wallet_address, secret = _execution_wallet_solana_secret(store, chain)
            if adapter.protocol_family == "local_clmm":
                if chain != "solana_localnet":
                    return fail(
                        "unsupported_liquidity_adapter",
                        "local_clmm adapter is only supported on solana_localnet.",
                        "Switch to solana_localnet or use raydium_clmm.",
                        _claim_failure_details(),
                        exit_code=2,
                    )
                claimed = solana_local_claim_fees(
                    chain=chain,
                    dex=adapter.dex,
                    owner=wallet_address,
                    position_id=position_id,
                )
                tx_hash = str(claimed.get("txHash") or "").strip()
                details = {
                    "approveTxHashes": [],
                    "operationTxHashes": [tx_hash] if tx_hash else [],
                    "routeKind": "adapter_default",
                    "simulationMode": True,
                    **claimed,
                }
                return ok(
                    "Liquidity fees claimed.",
                    chain=chain,
                    dex=adapter.dex,
                    positionId=position_id,
                    txHash=tx_hash,
                    approveTxHashes=[],
                    operationTxHashes=[tx_hash] if tx_hash else [],
                    providerRequested=provider_requested,
                    providerUsed=provider_used,
                    fallbackUsed=fallback_used,
                    fallbackReason=fallback_reason,
                    executionFamily="solana_clmm",
                    executionAdapter=adapter.dex,
                    routeKind="adapter_default",
                    liquidityOperation="claim_fees",
                    details=details,
                )
            pool_id = _resolve_raydium_pool_id(adapter, "")
            if not pool_id:
                return fail(
                    "invalid_input",
                    "Raydium claim-fees requires configured pool metadata.",
                    "Provide pool metadata in chain config or include a single default pool.",
                    _claim_failure_details(),
                    exit_code=2,
                )
            execution = solana_raydium_execute_instruction(
                chain=chain,
                rpc_url=_chain_rpc_url(chain),
                private_key_bytes=secret,
                owner=wallet_address,
                adapter_metadata=dict(adapter.adapter_metadata or {}),
                request={"poolId": pool_id, "positionId": position_id, "tokenId": position_id},
                operation_key="claim_fees",
            )
            tx_hash = str(execution.tx_hash or "").strip()
            details = {
                "poolId": pool_id,
                "approveTxHashes": [],
                "operationTxHashes": [tx_hash] if tx_hash else [],
                **execution.details,
            }
            return ok(
                "Liquidity fees claimed.",
                chain=chain,
                dex=adapter.dex,
                positionId=position_id,
                txHash=tx_hash,
                approveTxHashes=[],
                operationTxHashes=[tx_hash] if tx_hash else [],
                providerRequested=provider_requested,
                providerUsed=provider_used,
                fallbackUsed=fallback_used,
                fallbackReason=fallback_reason,
                executionFamily="solana_clmm",
                executionAdapter=adapter.dex,
                routeKind=execution.route_kind,
                liquidityOperation="claim_fees",
                details=details,
            )

        store = load_wallet_store()
        wallet_address, private_key_hex = _execution_wallet(store, chain)
        plan = build_liquidity_claim_fees_plan(
            chain=chain,
            dex=adapter.dex,
            position_type="v3",
            request={
                "positionId": position_id,
                "tokenId": position_id,
                "collectAsWeth": bool(args.collect_as_weth),
            },
            wallet_address=wallet_address,
            build_calldata=_cast_calldata,
        )
        execution = execute_liquidity_plan(
            executor=_router_action_executor(),
            plan=plan,
            wallet_address=wallet_address,
            private_key_hex=private_key_hex,
            wait_for_operation_receipts=False,
            liquidity_operation="claim_fees",
        )
        tx_hash = str(execution.tx_hash or "").strip()
        if not tx_hash:
            raise WalletStoreError("liquidity_claim_fees_failed: claim execution returned empty txHash.")
        builder_meta = _builder_output_from_hashes(chain, [*execution.approve_tx_hashes, *execution.operation_tx_hashes])
        return ok(
            "Liquidity fees claimed.",
            chain=chain,
            dex=adapter.dex,
            positionId=position_id,
            txHash=tx_hash,
            approveTxHashes=execution.approve_tx_hashes,
            operationTxHashes=execution.operation_tx_hashes,
            providerRequested=provider_requested,
            providerUsed=provider_used,
            fallbackUsed=fallback_used,
            fallbackReason=fallback_reason,
            executionFamily=execution.execution_family,
            executionAdapter=execution.execution_adapter,
            routeKind=execution.route_kind,
            liquidityOperation="claim_fees",
            details={**execution.details, **builder_meta},
            **builder_meta,
        )
    except ChainRegistryError as exc:
        return fail("unsupported_chain_capability", str(exc), chain_supported_hint(), {"chain": chain, "requiredCapability": "liquidity"}, exit_code=2)
    except UnsupportedLiquidityAdapter as exc:
        return fail("unsupported_liquidity_adapter", str(exc), "Choose a supported chain/dex/position-type combination and retry.", _claim_failure_details(), exit_code=2)
    except UnsupportedLiquidityOperation as exc:
        return fail("unsupported_liquidity_operation", str(exc), "Use a chain/dex with concentrated-liquidity fee-claim support.", _claim_failure_details(), exit_code=2)
    except ValueError as exc:
        code = str(exc)
        if code == "chain_config_invalid":
            return fail("chain_config_invalid", "Concentrated-liquidity execution metadata is incomplete for this chain.", "Add execution.liquidity adapter position-manager metadata and retry.", _claim_failure_details(), exit_code=2)
        return fail("liquidity_claim_fees_failed", str(exc), "Verify local router-adapter configuration and retry.", _claim_failure_details(), exit_code=1)
    except WalletStoreError as exc:
        err = str(exc)
        for code in {"claim_fees_not_supported_for_protocol", "unsupported_liquidity_operation", "no_execution_provider_available"}:
            if err.startswith(f"{code}:"):
                return fail(code, err.split(":", 1)[1].strip(), "Verify chain claim-fees support and retry.", _claim_failure_details(), exit_code=1)
        return fail("liquidity_claim_fees_failed", str(exc), "Verify local router-adapter configuration and retry.", _claim_failure_details(), exit_code=1)
    except Exception as exc:
        return fail("liquidity_claim_fees_failed", str(exc), "Inspect runtime liquidity fee-claim path and retry.", _claim_failure_details(), exit_code=1)


def cmd_liquidity_migrate(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    chain = str(args.chain or "").strip()
    dex = str(args.dex or "").strip().lower()
    position_id = str(args.position_id or "").strip()
    from_protocol = str(args.from_protocol or "").strip().upper()
    to_protocol = str(args.to_protocol or "").strip().upper()
    try:
        assert_chain_capability(chain, "liquidity")
        if not position_id:
            return fail("invalid_input", "position-id is required.", "Provide --position-id and retry.", {"chain": chain}, exit_code=2)
        if from_protocol not in {"V2", "V3", "V4"} or to_protocol not in {"V2", "V3", "V4"}:
            return fail(
                "invalid_input",
                "from-protocol and to-protocol must be one of V2|V3|V4.",
                "Provide valid protocol versions and retry.",
                {"fromProtocol": from_protocol, "toProtocol": to_protocol},
                exit_code=2,
            )
        slippage_bps = int(args.slippage_bps)
        if slippage_bps < 0 or slippage_bps > 5000:
            return fail("invalid_input", "slippage-bps must be between 0 and 5000.", "Use integer bps in range.", {"slippageBps": args.slippage_bps}, exit_code=2)
        provider_requested, _ = _liquidity_provider_settings(chain)
        fallback_used = False
        fallback_reason: dict[str, str] | None = None
        adapter = build_liquidity_adapter_for_request(chain=chain, dex=dex, position_type="v3")
        if adapter.protocol_family not in {"position_manager_v3", "local_clmm", "raydium_clmm"}:
            return fail(
                "unsupported_liquidity_execution_family",
                f"Liquidity migrate requires a concentrated-liquidity execution adapter, got '{adapter.protocol_family}'.",
                "Use a chain/dex with advanced concentrated-liquidity support and retry.",
                {"chain": chain, "dex": dex, "positionId": position_id},
                exit_code=2,
            )
        if not adapter.supports_operation("migrate"):
            return fail(
                "unsupported_liquidity_operation",
                f"Adapter '{adapter.dex}' does not support migrate on chain '{chain}'.",
                "Choose a supported chain/dex combination and retry.",
                {"chain": chain, "dex": adapter.dex, "positionId": position_id},
                exit_code=2,
            )

        request_json = str(args.request_json or "").strip()
        request_payload: dict[str, Any] = {}
        if request_json:
            extra = json.loads(request_json)
            if not isinstance(extra, dict):
                raise WalletStoreError("request-json must decode to an object.")
            request_payload.update(extra)

        if _is_solana_chain(chain) and adapter.protocol_family in {"local_clmm", "raydium_clmm"}:
            store = load_wallet_store()
            wallet_address, secret = _execution_wallet_solana_secret(store, chain)
            target_adapter_key = str(
                request_payload.get("targetAdapterKey")
                or ((adapter.operations or {}).get("migrate") or {}).get("targetAdapterKey")
                or ""
            ).strip()
            if not target_adapter_key:
                return fail(
                    "migration_target_not_configured",
                    "Migration target adapter is not configured for this chain/dex.",
                    "Add execution.liquidity adapter migrate target metadata and retry.",
                    {"chain": chain, "dex": dex, "positionId": position_id},
                    exit_code=2,
                )
            if adapter.protocol_family == "local_clmm":
                if chain != "solana_localnet":
                    return fail(
                        "unsupported_liquidity_adapter",
                        "local_clmm adapter is only supported on solana_localnet.",
                        "Switch to solana_localnet or use raydium_clmm.",
                        {"chain": chain, "dex": dex, "positionId": position_id},
                        exit_code=2,
                    )
                migrated = solana_local_migrate_position(
                    chain=chain,
                    dex=adapter.dex,
                    owner=wallet_address,
                    position_id=position_id,
                    target_dex=target_adapter_key,
                    recreate=bool(request_payload.get("targetRecreate")),
                )
                tx_hash = str(migrated.get("txHash") or "").strip()
                route_kind = "migration" if str(migrated.get("migrationMode") or "") == "recreate" else "position_manager"
                details = {
                    "targetAdapterKey": target_adapter_key,
                    "approveTxHashes": [],
                    "operationTxHashes": [tx_hash] if tx_hash else [],
                    "routeKind": route_kind,
                    "simulationMode": True,
                    **migrated,
                }
                return ok(
                    "Liquidity position migrated.",
                    chain=chain,
                    dex=adapter.dex,
                    positionId=position_id,
                    txHash=tx_hash,
                    approveTxHashes=[],
                    operationTxHashes=[tx_hash] if tx_hash else [],
                    providerRequested=provider_requested,
                    providerUsed="router_adapter",
                    fallbackUsed=fallback_used,
                    fallbackReason=fallback_reason,
                    executionFamily="solana_clmm",
                    executionAdapter=adapter.dex,
                    routeKind=route_kind,
                    liquidityOperation="migrate",
                    fromProtocol=from_protocol,
                    toProtocol=to_protocol,
                    details=details,
                )
            pool_id = _resolve_raydium_pool_id(adapter, str(request_payload.get("poolId") or ""))
            if not pool_id:
                return fail(
                    "invalid_input",
                    "Raydium migrate requires configured pool metadata.",
                    "Provide pool metadata in chain config or include a single default pool.",
                    {"chain": chain, "dex": dex, "positionId": position_id},
                    exit_code=2,
                )
            execution = solana_raydium_execute_instruction(
                chain=chain,
                rpc_url=_chain_rpc_url(chain),
                private_key_bytes=secret,
                owner=wallet_address,
                adapter_metadata=dict(adapter.adapter_metadata or {}),
                request={
                    "poolId": pool_id,
                    "positionId": position_id,
                    "tokenId": position_id,
                    "targetAdapterKey": target_adapter_key,
                    "targetRecreate": bool(request_payload.get("targetRecreate")),
                    **request_payload,
                },
                operation_key="migrate",
            )
            tx_hash = str(execution.tx_hash or "")
            return ok(
                "Liquidity position migrated.",
                chain=chain,
                dex=adapter.dex,
                positionId=position_id,
                txHash=tx_hash,
                approveTxHashes=[],
                operationTxHashes=[tx_hash] if tx_hash else [],
                providerRequested=provider_requested,
                providerUsed="router_adapter",
                fallbackUsed=fallback_used,
                fallbackReason=fallback_reason,
                executionFamily="solana_clmm",
                executionAdapter=adapter.dex,
                routeKind=execution.route_kind,
                liquidityOperation="migrate",
                fromProtocol=from_protocol,
                toProtocol=to_protocol,
                details={
                    "poolId": pool_id,
                    "targetAdapterKey": target_adapter_key,
                    "approveTxHashes": [],
                    "operationTxHashes": [tx_hash] if tx_hash else [],
                    **execution.details,
                },
            )

        store = load_wallet_store()
        wallet_address, private_key_hex = _execution_wallet(store, chain)
        position_snapshot = _read_v3_position_snapshot(chain, adapter.position_manager, position_id)
        liquidity_total = int(position_snapshot.get("liquidityUnits") or 0)
        if liquidity_total <= 0:
            return fail(
                "liquidity_preflight_zero_position_liquidity",
                "Position has no removable concentrated liquidity for migration.",
                "Choose a position with non-zero liquidity and retry.",
                {"chain": chain, "dex": dex, "positionId": position_id, "liquidityTotal": str(liquidity_total)},
                exit_code=1,
            )
        deadline = str(int(datetime.now(timezone.utc).timestamp()) + 120)
        request_payload: dict[str, Any] = {
            "positionId": position_id,
            "tokenId": position_id,
            "inputProtocol": from_protocol,
            "outputProtocol": to_protocol,
            "slippageTolerance": slippage_bps,
            "liquidityUnits": str(liquidity_total),
            "minAmountAUnits": "0",
            "minAmountBUnits": "0",
            "deadline": deadline,
        }
        if request_json:
            extra = json.loads(request_json)
            if not isinstance(extra, dict):
                raise WalletStoreError("request-json must decode to an object.")
            request_payload.update(extra)
        migrate_cfg = dict((adapter.operations or {}).get("migrate") or {})
        target_adapter_key = str(request_payload.get("targetAdapterKey") or migrate_cfg.get("targetAdapterKey") or "").strip()
        if target_adapter_key:
            request_payload["targetAdapterKey"] = target_adapter_key
            try:
                target_adapter = build_liquidity_adapter_for_request(chain=chain, dex=target_adapter_key, position_type="v3")
                request_payload["targetPositionManager"] = str(target_adapter.position_manager or "").strip()
                target_ops = dict(target_adapter.operations or {})
                target_add = dict(target_ops.get("add") or {})
                if target_add:
                    request_payload["targetAddMethod"] = str(target_add.get("method") or "mint").strip() or "mint"
            except Exception:
                pass
        plan = build_liquidity_migrate_plan(
            chain=chain,
            dex=adapter.dex,
            position_type="v3",
            request=request_payload,
            wallet_address=wallet_address,
            build_calldata=_cast_calldata,
        )
        execution = execute_liquidity_plan(
            executor=_router_action_executor(),
            plan=plan,
            wallet_address=wallet_address,
            private_key_hex=private_key_hex,
            wait_for_operation_receipts=False,
            liquidity_operation="migrate",
        )
        tx_hash = str(execution.tx_hash or "")
        builder_meta = _builder_output_from_hashes(chain, [*execution.approve_tx_hashes, *execution.operation_tx_hashes])
        return ok(
            "Liquidity position migrated.",
            chain=chain,
            dex=adapter.dex,
            positionId=position_id,
            txHash=tx_hash,
            approveTxHashes=execution.approve_tx_hashes,
            operationTxHashes=execution.operation_tx_hashes,
            providerRequested=provider_requested,
            providerUsed="router_adapter",
            fallbackUsed=fallback_used,
            fallbackReason=fallback_reason,
            executionFamily=execution.execution_family,
            executionAdapter=execution.execution_adapter,
            routeKind=execution.route_kind,
            liquidityOperation="migrate",
            fromProtocol=from_protocol,
            toProtocol=to_protocol,
            details={**execution.details, **builder_meta},
            **builder_meta,
        )
    except ChainRegistryError as exc:
        return fail("unsupported_chain_capability", str(exc), chain_supported_hint(), {"chain": chain, "requiredCapability": "liquidity"}, exit_code=2)
    except UnsupportedLiquidityAdapter as exc:
        return fail("unsupported_liquidity_adapter", str(exc), "Choose a supported chain/dex/position-type combination and retry.", {"chain": chain, "dex": dex, "positionId": position_id}, exit_code=2)
    except UnsupportedLiquidityOperation as exc:
        return fail("unsupported_liquidity_operation", str(exc), "Use a chain/dex with concentrated-liquidity migrate support.", {"chain": chain, "dex": dex, "positionId": position_id}, exit_code=2)
    except ValueError as exc:
        code = str(exc)
        if code == "chain_config_invalid":
            return fail("chain_config_invalid", "Concentrated-liquidity execution metadata is incomplete for this chain.", "Add execution.liquidity adapter position-manager metadata and retry.", {"chain": chain, "dex": dex, "positionId": position_id}, exit_code=2)
        if code == "migration_target_not_configured":
            return fail("migration_target_not_configured", "Migration target adapter is not configured for this chain/dex.", "Add execution.liquidity adapter migrate target metadata and retry.", {"chain": chain, "dex": dex, "positionId": position_id}, exit_code=2)
        return fail("liquidity_migrate_failed", str(exc), "Verify local router-adapter migrate configuration and retry.", {"chain": chain, "dex": dex, "positionId": position_id}, exit_code=1)
    except WalletStoreError as exc:
        return fail("liquidity_migrate_failed", str(exc), "Verify local router-adapter migrate configuration and retry.", {"chain": chain, "dex": dex, "positionId": position_id}, exit_code=1)
    except Exception as exc:
        return fail("liquidity_migrate_failed", str(exc), "Inspect runtime liquidity migrate path and retry.", {"chain": chain, "dex": dex, "positionId": position_id}, exit_code=1)


def cmd_liquidity_claim_rewards(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    chain = str(args.chain or "").strip()
    dex = str(args.dex or "").strip().lower()
    position_id = str(args.position_id or "").strip()
    provider_requested = "router_adapter"
    provider_used = "router_adapter"
    fallback_used = False
    fallback_reason: dict[str, str] | None = None

    def _claim_failure_details() -> dict[str, Any]:
        details: dict[str, Any] = {
            "chain": chain,
            "dex": dex,
            "positionId": position_id,
            "operation": "claim_rewards",
            "providerRequested": provider_requested,
            "fallbackUsed": bool(fallback_used),
            "fallbackReason": fallback_reason,
        }
        if provider_used:
            details["providerUsed"] = provider_used
        return details

    try:
        assert_chain_capability(chain, "liquidity")
        if not position_id:
            return fail("invalid_input", "position-id is required.", "Provide --position-id and retry.", _claim_failure_details(), exit_code=2)
        provider_requested, _ = _liquidity_provider_settings(chain)
        fallback_used = False
        fallback_reason = None
        adapter = build_liquidity_adapter_for_request(chain=chain, dex=dex, position_type="v3")
        if adapter.protocol_family not in {"position_manager_v3", "local_clmm", "raydium_clmm"}:
            return fail(
                "unsupported_liquidity_execution_family",
                f"Liquidity claim-rewards requires a concentrated-liquidity execution adapter, got '{adapter.protocol_family}'.",
                "Use a chain/dex with advanced concentrated-liquidity support and retry.",
                _claim_failure_details(),
                exit_code=2,
            )
        if not adapter.supports_operation("claim_rewards"):
            return fail(
                "unsupported_liquidity_operation",
                f"Adapter '{adapter.dex}' does not support claim-rewards on chain '{chain}'.",
                "Choose a supported chain/dex combination and retry.",
                _claim_failure_details(),
                exit_code=2,
            )
        request_payload: dict[str, Any] = {"positionId": position_id}
        reward_token = str(args.reward_token or "").strip()
        if reward_token:
            request_payload["tokens"] = [_resolve_token_address(chain, reward_token)]
        request_json = str(args.request_json or "").strip()
        if request_json:
            extra = json.loads(request_json)
            if not isinstance(extra, dict):
                raise WalletStoreError("request-json must decode to an object.")
            request_payload.update(extra)

        if _is_solana_chain(chain) and adapter.protocol_family in {"local_clmm", "raydium_clmm"}:
            reward_contracts: list[str] = []
            reward_cfg = ((adapter.operations or {}).get("claimRewards") or {}) if isinstance(adapter.operations, dict) else {}
            configured_rewards = reward_cfg.get("rewardContracts") if isinstance(reward_cfg, dict) else None
            if isinstance(configured_rewards, list):
                reward_contracts = [str(item or "").strip() for item in configured_rewards if str(item or "").strip()]
            if reward_token:
                reward_contracts = [str(_resolve_token_address(chain, reward_token))]
            if not reward_contracts:
                return fail(
                    "claim_rewards_not_configured",
                    "Reward contracts are not configured for this chain/dex.",
                    "Add execution.liquidity adapter claimRewards.rewardContracts and retry.",
                    _claim_failure_details(),
                    exit_code=1,
                )
            store = load_wallet_store()
            wallet_address, secret = _execution_wallet_solana_secret(store, chain)
            if adapter.protocol_family == "local_clmm":
                if chain != "solana_localnet":
                    return fail(
                        "unsupported_liquidity_adapter",
                        "local_clmm adapter is only supported on solana_localnet.",
                        "Switch to solana_localnet or use raydium_clmm.",
                        _claim_failure_details(),
                        exit_code=2,
                    )
                claimed = solana_local_claim_rewards(
                    chain=chain,
                    dex=adapter.dex,
                    owner=wallet_address,
                    position_id=position_id,
                    reward_contracts=reward_contracts,
                )
                tx_hash = str(claimed.get("txHash") or "").strip()
                details = {
                    "rewardContracts": reward_contracts,
                    "approveTxHashes": [],
                    "operationTxHashes": [tx_hash] if tx_hash else [],
                    "routeKind": "reward_claim",
                    "simulationMode": True,
                    **claimed,
                }
                return ok(
                    "Liquidity rewards claimed.",
                    chain=chain,
                    dex=adapter.dex,
                    positionId=position_id,
                    txHash=tx_hash,
                    approveTxHashes=[],
                    operationTxHashes=[tx_hash] if tx_hash else [],
                    providerRequested=provider_requested,
                    providerUsed=provider_used,
                    fallbackUsed=fallback_used,
                    fallbackReason=fallback_reason,
                    executionFamily="solana_clmm",
                    executionAdapter=adapter.dex,
                    routeKind="reward_claim",
                    liquidityOperation="claim_rewards",
                    details=details,
                )
            pool_id = _resolve_raydium_pool_id(adapter, "")
            if not pool_id:
                return fail(
                    "invalid_input",
                    "Raydium claim-rewards requires configured pool metadata.",
                    "Provide pool metadata in chain config or include a single default pool.",
                    _claim_failure_details(),
                    exit_code=2,
                )
            execution = solana_raydium_execute_instruction(
                chain=chain,
                rpc_url=_chain_rpc_url(chain),
                private_key_bytes=secret,
                owner=wallet_address,
                adapter_metadata=dict(adapter.adapter_metadata or {}),
                request={
                    "poolId": pool_id,
                    "positionId": position_id,
                    "tokenId": position_id,
                    "rewardContracts": reward_contracts,
                },
                operation_key="claim_rewards",
            )
            tx_hash = str(execution.tx_hash or "").strip()
            details = {
                "poolId": pool_id,
                "rewardContracts": reward_contracts,
                "approveTxHashes": [],
                "operationTxHashes": [tx_hash] if tx_hash else [],
                **execution.details,
            }
            return ok(
                "Liquidity rewards claimed.",
                chain=chain,
                dex=adapter.dex,
                positionId=position_id,
                txHash=tx_hash,
                approveTxHashes=[],
                operationTxHashes=[tx_hash] if tx_hash else [],
                providerRequested=provider_requested,
                providerUsed=provider_used,
                fallbackUsed=fallback_used,
                fallbackReason=fallback_reason,
                executionFamily="solana_clmm",
                executionAdapter=adapter.dex,
                routeKind=execution.route_kind,
                liquidityOperation="claim_rewards",
                details=details,
            )

        store = load_wallet_store()
        wallet_address, private_key_hex = _execution_wallet(store, chain)
        plan = build_liquidity_claim_rewards_plan(
            chain=chain,
            dex=adapter.dex,
            position_type="v3",
            request=request_payload,
            wallet_address=wallet_address,
            build_calldata=_cast_calldata,
        )
        execution = execute_liquidity_plan(
            executor=_router_action_executor(),
            plan=plan,
            wallet_address=wallet_address,
            private_key_hex=private_key_hex,
            wait_for_operation_receipts=False,
            liquidity_operation="claim_rewards",
        )
        tx_hash = str(execution.tx_hash or "").strip()
        if not tx_hash:
            raise WalletStoreError("liquidity_claim_rewards_failed: claim execution returned empty txHash.")
        builder_meta = _builder_output_from_hashes(chain, [*execution.approve_tx_hashes, *execution.operation_tx_hashes])
        return ok(
            "Liquidity rewards claimed.",
            chain=chain,
            dex=adapter.dex,
            positionId=position_id,
            txHash=tx_hash,
            approveTxHashes=execution.approve_tx_hashes,
            operationTxHashes=execution.operation_tx_hashes,
            providerRequested=provider_requested,
            providerUsed=provider_used,
            fallbackUsed=fallback_used,
            fallbackReason=fallback_reason,
            executionFamily=execution.execution_family,
            executionAdapter=execution.execution_adapter,
            routeKind=execution.route_kind,
            liquidityOperation="claim_rewards",
            details={**execution.details, **builder_meta},
            **builder_meta,
        )
    except ChainRegistryError as exc:
        return fail("unsupported_chain_capability", str(exc), chain_supported_hint(), {"chain": chain, "requiredCapability": "liquidity"}, exit_code=2)
    except UnsupportedLiquidityAdapter as exc:
        return fail("unsupported_liquidity_adapter", str(exc), "Choose a supported chain/dex/position-type combination and retry.", _claim_failure_details(), exit_code=2)
    except UnsupportedLiquidityOperation as exc:
        return fail("unsupported_liquidity_operation", str(exc), "Use a chain/dex with concentrated-liquidity rewards-claim support.", _claim_failure_details(), exit_code=2)
    except ValueError as exc:
        code = str(exc)
        if code == "chain_config_invalid":
            return fail("chain_config_invalid", "Concentrated-liquidity execution metadata is incomplete for this chain.", "Add execution.liquidity adapter position-manager metadata and retry.", _claim_failure_details(), exit_code=2)
        if code == "claim_rewards_not_configured":
            return fail("claim_rewards_not_configured", "Reward contracts are not configured for this chain/dex.", "Add execution.liquidity adapter claimRewards.rewardContracts and retry.", _claim_failure_details(), exit_code=1)
        return fail("liquidity_claim_rewards_failed", str(exc), "Verify local router-adapter claim-rewards configuration and retry.", _claim_failure_details(), exit_code=1)
    except WalletStoreError as exc:
        err = str(exc)
        for code in {"claim_rewards_not_configured", "claim_rewards_not_supported_for_protocol", "unsupported_liquidity_operation", "no_execution_provider_available"}:
            if err.startswith(f"{code}:"):
                return fail(code, err.split(":", 1)[1].strip(), "Verify chain claim-rewards support and retry.", _claim_failure_details(), exit_code=1)
        return fail("liquidity_claim_rewards_failed", str(exc), "Verify local router-adapter claim-rewards configuration and retry.", _claim_failure_details(), exit_code=1)
    except Exception as exc:
        return fail("liquidity_claim_rewards_failed", str(exc), "Inspect runtime liquidity claim-rewards path and retry.", _claim_failure_details(), exit_code=1)


def _invoke_liquidity_command_payload(command: Callable[[argparse.Namespace], int], args: argparse.Namespace) -> dict[str, Any]:
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = command(args)
    raw = buf.getvalue().strip()
    payload: dict[str, Any] = {}
    if raw:
        try:
            decoded = json.loads(raw)
            if isinstance(decoded, dict):
                payload = decoded
        except Exception:
            payload = {"ok": False, "code": "liquidity_execute_parse_failed", "message": raw[:400]}
    if code != 0:
        error_code = str(payload.get("code") or "liquidity_execution_failed")
        error_message = str(payload.get("message") or "Advanced liquidity command failed.")
        raise WalletStoreError(f"{error_code}: {error_message}")
    return payload


def _execute_liquidity_advanced_intent(intent: dict[str, Any], chain: str, action: str) -> tuple[dict[str, Any], str]:
    dex = str(intent.get("dex") or "").strip().lower()
    adapter = build_liquidity_adapter_for_request(chain=chain, dex=dex, position_type="v3")
    details = _intent_details_dict(intent)
    v3_details = _v3_details_dict(details)
    position_id = str(intent.get("positionId") or intent.get("positionRef") or "").strip()
    slippage_bps = int(intent.get("slippageBps") or details.get("slippageBps") or 100)

    if action == "increase":
        args = argparse.Namespace(
            chain=chain,
            dex=dex,
            position_id=position_id,
            token_a=str(intent.get("tokenA") or v3_details.get("tokenA") or ""),
            token_b=str(intent.get("tokenB") or v3_details.get("tokenB") or ""),
            amount_a=str(intent.get("amountA") or v3_details.get("amountA") or ""),
            amount_b=str(intent.get("amountB") or v3_details.get("amountB") or ""),
            slippage_bps=slippage_bps,
            json=True,
        )
        payload = _invoke_liquidity_command_payload(cmd_liquidity_increase, args)
        return payload, adapter.protocol_family

    if action in {"claim_fees", "claim-fees"}:
        args = argparse.Namespace(
            chain=chain,
            dex=dex,
            position_id=position_id,
            collect_as_weth=bool(details.get("collectAsWeth") or False),
            json=True,
        )
        payload = _invoke_liquidity_command_payload(cmd_liquidity_claim_fees, args)
        return payload, adapter.protocol_family

    if action in {"claim_rewards", "claim-rewards"}:
        args = argparse.Namespace(
            chain=chain,
            dex=dex,
            position_id=position_id,
            reward_token=str(details.get("rewardToken") or ""),
            request_json=json.dumps(details.get("request") or {}) if isinstance(details.get("request"), dict) else None,
            json=True,
        )
        payload = _invoke_liquidity_command_payload(cmd_liquidity_claim_rewards, args)
        return payload, adapter.protocol_family

    if action == "migrate":
        args = argparse.Namespace(
            chain=chain,
            dex=dex,
            position_id=position_id,
            from_protocol=str(details.get("fromProtocol") or "V3"),
            to_protocol=str(details.get("toProtocol") or "V3"),
            slippage_bps=slippage_bps,
            request_json=json.dumps(details.get("request") or {}) if isinstance(details.get("request"), dict) else None,
            json=True,
        )
        payload = _invoke_liquidity_command_payload(cmd_liquidity_migrate, args)
        return payload, adapter.protocol_family

    raise WalletStoreError(f"Unsupported liquidity action '{action}'.")


def _run_liquidity_execute_inline(liquidity_intent_id: str, chain: str) -> tuple[int, dict[str, Any]]:
    nested = argparse.Namespace(intent=liquidity_intent_id, chain=chain, json=True)
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = cmd_liquidity_execute(nested)
    raw = buf.getvalue().strip()
    payload: dict[str, Any] = {
        "ok": bool(code == 0),
        "code": "liquidity_execute_result_unavailable",
        "message": "Liquidity execute result unavailable.",
        "liquidityIntentId": liquidity_intent_id,
        "chain": chain,
    }
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                payload = parsed
        except Exception:
            payload = {
                "ok": False,
                "code": "liquidity_execute_parse_failed",
                "message": raw[:400],
                "liquidityIntentId": liquidity_intent_id,
                "chain": chain,
            }
    return code, payload


def cmd_liquidity_execute(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    liquidity_intent_id = str(args.intent or "").strip()
    chain = str(args.chain or "").strip()
    if not liquidity_intent_id:
        return fail("invalid_input", "intent is required.", "Provide --intent liq_... and retry.", exit_code=2)
    if not chain:
        return fail("invalid_input", "chain is required.", "Provide --chain <chainKey> and retry.", {"liquidityIntentId": liquidity_intent_id}, exit_code=2)

    transition_state = "init"
    last_tx_hash: str | None = None
    provider_requested = _liquidity_provider_settings(chain)[0]
    provider_used = "router_adapter"
    fallback_used = False
    fallback_reason: dict[str, str] | None = None
    try:
        intent = _read_liquidity_intent(liquidity_intent_id, chain)
        status = str(intent.get("status") or "").strip().lower()
        action = str(intent.get("action") or "").strip().lower()
        dex = str(intent.get("dex") or "").strip().lower()
        position_type = str(intent.get("positionType") or "v2").strip().lower()
        if status != "approved":
            return fail(
                "liquidity_not_actionable",
                f"Liquidity intent is not actionable from status '{status}'.",
                "Execute only approved liquidity intents in this slice.",
                {"liquidityIntentId": liquidity_intent_id, "chain": chain, "status": status},
                exit_code=1,
            )

        execution: dict[str, Any]
        adapter_family = "unknown"

        def _execute_local() -> tuple[dict[str, Any], str]:
            adapter = build_liquidity_adapter_for_request(chain=chain, dex=dex, position_type=position_type)
            if action == "add":
                if adapter.protocol_family == "amm_v2":
                    return _execute_liquidity_v2_add(intent, chain), adapter.protocol_family
                if adapter.protocol_family in {"position_manager_v3", "local_clmm", "raydium_clmm"}:
                    return _execute_liquidity_v3_add(intent, chain), adapter.protocol_family
                raise WalletStoreError(
                    f"unsupported_liquidity_execution_family: Liquidity intent add requires supported local execution family, got '{adapter.protocol_family}'."
                )
            if action == "remove":
                if adapter.protocol_family == "amm_v2":
                    return _execute_liquidity_v2_remove(intent, chain), adapter.protocol_family
                if adapter.protocol_family in {"position_manager_v3", "local_clmm", "raydium_clmm"}:
                    return _execute_liquidity_v3_remove(intent, chain), adapter.protocol_family
                raise WalletStoreError(
                    f"unsupported_liquidity_execution_family: Liquidity intent remove requires supported local execution family, got '{adapter.protocol_family}'."
                )
            if action in {"increase", "claim_fees", "claim-fees", "claim_rewards", "claim-rewards", "migrate"}:
                return _execute_liquidity_advanced_intent(intent, chain, action)
            raise WalletStoreError(f"Unsupported liquidity action '{action}'.")

        _post_liquidity_status(liquidity_intent_id, "executing")
        transition_state = "executing"

        execution, adapter_family = _execute_local()
        provider_used = "router_adapter"

        tx_hash = str(execution.get("txHash") or "").strip()
        if not tx_hash:
            raise WalletStoreError("Liquidity execution did not return txHash.")
        last_tx_hash = tx_hash
        liquidity_operation = str(execution.get("liquidityOperation") or action).strip().lower() or None
        provider_meta = _build_liquidity_provider_meta(
            provider_requested=provider_requested,
            provider_used=provider_used,
            fallback_used=fallback_used,
            fallback_reason=fallback_reason,
            liquidity_operation=liquidity_operation,
        )
        status_details = execution.get("details") if isinstance(execution.get("details"), dict) else {}
        if execution.get("executionFamily"):
            status_details["executionFamily"] = execution.get("executionFamily")
        if execution.get("executionAdapter"):
            status_details["executionAdapter"] = execution.get("executionAdapter")
        if execution.get("routeKind"):
            status_details["routeKind"] = execution.get("routeKind")
        builder_hashes: list[str | None] = [tx_hash]
        approve_hashes = status_details.get("approveTxHashes")
        if isinstance(approve_hashes, list):
            builder_hashes.extend([str(item or "").strip() for item in approve_hashes if str(item or "").strip()])
        operation_hashes = status_details.get("operationTxHashes")
        if isinstance(operation_hashes, list):
            builder_hashes.extend([str(item or "").strip() for item in operation_hashes if str(item or "").strip()])
        builder_meta = _builder_output_from_hashes(chain, builder_hashes)
        status_details = {**status_details, **builder_meta}
        status_details = {**status_details, **provider_meta}

        _post_liquidity_status(
            liquidity_intent_id,
            "verifying",
            {
                "txHash": tx_hash,
                "positionId": execution.get("positionId"),
                "details": status_details,
            },
        )
        transition_state = "verifying"

        if adapter_family in {"amm_v2", "position_manager_v3"}:
            _wait_for_tx_receipt_success(chain, tx_hash)

        _post_liquidity_status(
            liquidity_intent_id,
            "filled",
            {
                "txHash": tx_hash,
                "positionId": execution.get("positionId"),
                "details": status_details,
            },
        )
        return ok(
            "Liquidity intent executed.",
            liquidityIntentId=liquidity_intent_id,
            chain=chain,
            dex=dex,
            action=action,
            positionType=position_type,
            adapterFamily=adapter_family,
            status="filled",
            txHash=tx_hash,
            positionId=execution.get("positionId"),
            details=status_details,
            providerRequested=provider_requested,
            providerUsed=provider_used,
            fallbackUsed=fallback_used,
            fallbackReason=fallback_reason,
            liquidityOperation=liquidity_operation,
            **builder_meta,
        )
    except SubprocessTimeout as exc:
        if transition_state == "verifying":
            try:
                _post_liquidity_status(
                    liquidity_intent_id,
                    "verification_timeout",
                    {"reasonCode": "verification_timeout", "reasonMessage": str(exc), "txHash": last_tx_hash},
                )
            except Exception:
                pass
        return fail(
            "liquidity_verification_failed",
            str(exc),
            "Receipt timed out; inspect explorer and retry if needed.",
            {"liquidityIntentId": liquidity_intent_id, "chain": chain, "txHash": last_tx_hash},
            exit_code=1,
        )
    except LiquidityExecutionError as exc:
        reason_code = str(exc.reason_code or "liquidity_execution_failed")
        failure_details = exc.details if isinstance(getattr(exc, "details", None), dict) else {}
        if transition_state in {"executing", "verifying"}:
            try:
                _post_liquidity_status(
                    liquidity_intent_id,
                    "failed",
                    {
                        "reasonCode": reason_code,
                        "reasonMessage": str(exc),
                        "txHash": last_tx_hash,
                        "details": failure_details if failure_details else None,
                    },
                )
            except Exception:
                pass
        return fail(
            "liquidity_execution_failed",
            str(exc),
            "Verify intent payload, wallet balances, pair liquidity, and chain contracts, then retry.",
            {
                "liquidityIntentId": liquidity_intent_id,
                "chain": chain,
                "txHash": last_tx_hash,
                "reasonCode": reason_code,
                "preflight": failure_details if failure_details else None,
            },
            exit_code=1,
        )
    except (LiquidityAdapterError, WalletStoreError) as exc:
        err_text = str(exc)
        if err_text.startswith("invalid_input:"):
            return fail(
                "invalid_input",
                err_text.split(":", 1)[1].strip(),
                "Update intent payload and retry.",
                {"liquidityIntentId": liquidity_intent_id, "chain": chain, "txHash": last_tx_hash},
                exit_code=2,
            )
        if err_text.startswith("unsupported_liquidity_execution_family:"):
            return fail(
                "unsupported_liquidity_execution_family",
                err_text.split(":", 1)[1].strip(),
                "Use a supported liquidity execution family and retry.",
                {"liquidityIntentId": liquidity_intent_id, "chain": chain, "txHash": last_tx_hash},
                exit_code=2,
            )
        if err_text.startswith("unsupported_liquidity_operation"):
            return fail(
                "unsupported_liquidity_operation",
                "Requested liquidity operation is not supported by the resolved adapter.",
                "Use a chain/dex with matching operation capability and retry.",
                {"liquidityIntentId": liquidity_intent_id, "chain": chain, "txHash": last_tx_hash},
                exit_code=2,
            )
        if transition_state in {"executing", "verifying"}:
            fail_status = "failed" if transition_state == "executing" else "failed"
            try:
                _post_liquidity_status(liquidity_intent_id, fail_status, {"reasonCode": "liquidity_execution_failed", "reasonMessage": err_text, "txHash": last_tx_hash})
            except Exception:
                pass
        return fail(
            "liquidity_execution_failed",
            err_text,
            "Verify intent payload, wallet configuration, and chain contracts, then retry.",
            {"liquidityIntentId": liquidity_intent_id, "chain": chain, "txHash": last_tx_hash},
            exit_code=1,
        )
    except Exception as exc:
        if transition_state in {"executing", "verifying"}:
            try:
                _post_liquidity_status(liquidity_intent_id, "failed", {"reasonCode": "liquidity_execution_failed", "reasonMessage": str(exc), "txHash": last_tx_hash})
            except Exception:
                pass
        return fail(
            "liquidity_execution_failed",
            str(exc),
            "Inspect runtime liquidity execution path and retry.",
            {"liquidityIntentId": liquidity_intent_id, "chain": chain, "txHash": last_tx_hash},
            exit_code=1,
        )


def cmd_liquidity_resume(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    liquidity_intent_id = str(args.intent or "").strip()
    chain = str(args.chain or "").strip()
    nested = argparse.Namespace(intent=liquidity_intent_id, chain=chain, json=True)
    return cmd_liquidity_execute(nested)


def cmd_liquidity_positions(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    chain = str(args.chain or "").strip()
    dex = str(args.dex or "").strip().lower()
    status_filter = str(args.status or "").strip().lower()
    status_aliases = {
        "open": "active",
        "opened": "active",
        "live": "active",
    }
    status_filter = status_aliases.get(status_filter, status_filter)
    try:
        assert_chain_capability(chain, "liquidity")
        agent_id = _resolve_agent_id_or_fail(chain)
        status_code, body = _api_request(
            "GET",
            f"/liquidity/positions?agentId={urllib.parse.quote(agent_id)}&chainKey={urllib.parse.quote(chain)}",
        )
        if status_code < 200 or status_code >= 300:
            return fail(
                str(body.get("code", "api_error")),
                str(body.get("message", f"liquidity positions request failed ({status_code})")),
                str(body.get("actionHint", "Verify API auth and retry.")),
                _api_error_details(status_code, body, "/liquidity/positions", chain=chain),
                exit_code=1,
            )
        items = body.get("items")
        if not isinstance(items, list):
            items = []
        normalized_items: list[dict[str, Any]] = []
        for row in items:
            if not isinstance(row, dict):
                continue
            item = dict(row)
            token_a_raw = str(item.get("tokenA") or "").strip()
            token_b_raw = str(item.get("tokenB") or "").strip()
            token_a = token_a_raw
            token_b = token_b_raw
            if _is_placeholder_liquidity_token(token_a_raw) or _is_placeholder_liquidity_token(token_b_raw):
                pair_ref = str(item.get("pool") or item.get("poolRef") or item.get("pair") or "").strip()
                if is_hex_address(pair_ref):
                    try:
                        pair_token_a, pair_token_b = _resolve_pair_tokens_from_contract(chain, pair_ref)
                        if _is_placeholder_liquidity_token(token_a_raw):
                            token_a = pair_token_a
                        if _is_placeholder_liquidity_token(token_b_raw):
                            token_b = pair_token_b
                    except Exception:
                        pass
            token_a_symbol = _token_symbol_for_display(chain, token_a) or token_a
            token_b_symbol = _token_symbol_for_display(chain, token_b) or token_b
            item["tokenA"] = token_a
            item["tokenB"] = token_b
            item["tokenASymbol"] = token_a_symbol
            item["tokenBSymbol"] = token_b_symbol
            item["pairDisplay"] = f"{token_a_symbol}/{token_b_symbol}"
            normalized_items.append(item)
        items = normalized_items
        if dex:
            items = [row for row in items if str((row or {}).get("dex") or "").strip().lower() == dex]
        if status_filter:
            items = [row for row in items if str((row or {}).get("status") or "").strip().lower() == status_filter]
        return ok(
            "Liquidity positions loaded.",
            chain=chain,
            dex=dex or None,
            status=status_filter or None,
            count=len(items),
            positions=items,
        )
    except ChainRegistryError as exc:
        return fail("unsupported_chain_capability", str(exc), chain_supported_hint(), {"chain": chain, "requiredCapability": "liquidity"}, exit_code=2)
    except WalletStoreError as exc:
        return fail("liquidity_positions_failed", str(exc), "Verify API env/auth and retry.", {"chain": chain, "dex": dex}, exit_code=1)
    except Exception as exc:
        return fail("liquidity_positions_failed", str(exc), "Inspect runtime liquidity positions path and retry.", {"chain": chain, "dex": dex}, exit_code=1)


def _trade_provider_settings(chain: str) -> tuple[str, str]:
    cfg = _load_chain_config(chain)
    execution = cfg.get("execution")
    if isinstance(execution, dict):
        trade_cfg = execution.get("trade")
        if isinstance(trade_cfg, dict):
            default_provider = str(trade_cfg.get("defaultProvider") or "").strip().lower()
            if default_provider in {"router_adapter", "quote_only", "none"}:
                return default_provider, "none"
    return "router_adapter", "none"


def _liquidity_provider_settings(chain: str) -> tuple[str, str]:
    cfg = _load_chain_config(chain)
    execution = cfg.get("execution")
    if isinstance(execution, dict):
        liquidity_cfg = execution.get("liquidity")
        if isinstance(liquidity_cfg, dict):
            default_provider = str(liquidity_cfg.get("defaultProvider") or "").strip().lower()
            if default_provider in {"router_adapter", "quote_only", "none"}:
                return default_provider, "none"
    return "router_adapter", "none"


def _fallback_reason(code: str, message: str) -> dict[str, str]:
    return {"code": code, "message": message[:500]}


def _build_provider_meta(
    provider_requested: str,
    provider_used: str,
    fallback_used: bool,
    fallback_reason: dict[str, str] | None,
    route_kind: str | None,
) -> dict[str, Any]:
    normalized_requested = "router_adapter" if provider_requested in {"legacy_router", "uniswap_api"} else provider_requested
    normalized_used = "router_adapter" if provider_used in {"legacy_router", "uniswap_api"} else provider_used
    return {
        "providerRequested": normalized_requested,
        "providerUsed": normalized_used,
        "fallbackUsed": bool(fallback_used),
        "fallbackReason": fallback_reason if fallback_used and isinstance(fallback_reason, dict) else None,
        "routeKind": (str(route_kind or "").strip() or None),
    }


def _build_liquidity_provider_meta(
    provider_requested: str,
    provider_used: str,
    fallback_used: bool,
    fallback_reason: dict[str, str] | None,
    liquidity_operation: str | None,
) -> dict[str, Any]:
    normalized_requested = "router_adapter" if provider_requested in {"legacy_router", "uniswap_api"} else provider_requested
    normalized_used = "router_adapter" if provider_used in {"legacy_router", "uniswap_api"} else provider_used
    return {
        "providerRequested": normalized_requested,
        "providerUsed": normalized_used,
        "fallbackUsed": bool(fallback_used),
        "fallbackReason": fallback_reason if fallback_used and isinstance(fallback_reason, dict) else None,
        "liquidityOperation": (str(liquidity_operation or "").strip().lower() or None),
    }


def _router_action_executor() -> EvmActionExecutor:
    return EvmActionExecutor(
        ensure_token_allowance=_ensure_token_allowance,
        send_transaction=_cast_rpc_send_transaction,
        wait_for_receipt_success=_wait_for_tx_receipt_success,
        rpc_url_for_chain=_chain_rpc_url,
    )


def _resolve_trade_adapter_key(chain: str, requested: str = "") -> str:
    resolved_key, _ = resolve_trade_execution_adapter(chain, requested)
    return resolved_key


def _quote_trade_via_router_adapter(
    *,
    chain: str,
    adapter_key: str,
    token_in: str,
    token_out: str,
    amount_in_units: str,
) -> dict[str, Any]:
    return quote_trade(
        chain=chain,
        adapter_key=adapter_key,
        request={
            "tokenIn": token_in,
            "tokenOut": token_out,
            "amountInUnits": amount_in_units,
        },
        get_amount_out=lambda value, token_a, token_b: _router_get_amount_out(chain, value, token_a, token_b),
    )


def _execute_trade_via_router_adapter(
    *,
    chain: str,
    adapter_key: str,
    wallet_address: str,
    private_key_hex: str,
    token_in: str,
    token_out: str,
    amount_in_units: str,
    min_out_units: str,
    deadline: str,
    recipient: str,
    wait_for_receipt: bool,
) -> dict[str, Any]:
    plan = build_trade_plan(
        chain=chain,
        adapter_key=adapter_key,
        request={
            "tokenIn": token_in,
            "tokenOut": token_out,
            "amountInUnits": amount_in_units,
            "amountOutMinUnits": min_out_units,
            "recipient": recipient,
            "deadline": deadline,
            "routeKind": "router_path",
        },
        wallet_address=wallet_address,
        build_calldata=_cast_calldata,
    )
    execution = execute_trade_plan(
        executor=_router_action_executor(),
        plan=plan,
        wallet_address=wallet_address,
        private_key_hex=private_key_hex,
        wait_for_operation_receipts=wait_for_receipt,
    )
    return {
        "txHash": execution.tx_hash,
        "approveTxHashes": execution.approve_tx_hashes,
        "operationTxHashes": execution.operation_tx_hashes,
        "executionFamily": execution.execution_family,
        "executionAdapter": execution.execution_adapter,
        "routeKind": execution.route_kind,
    }


def _uniswap_quote_via_proxy(
    chain: str,
    wallet_address: str,
    token_in: str,
    token_out: str,
    amount_in_units: str,
    slippage_bps: int,
) -> dict[str, Any]:
    agent_id = _resolve_agent_id_or_fail(chain)
    payload = {
        "agentId": agent_id,
        "chainKey": chain,
        "walletAddress": wallet_address,
        "tokenIn": token_in,
        "tokenOut": token_out,
        "amountInUnits": str(amount_in_units),
        "slippageBps": int(slippage_bps),
    }
    status_code, body = _api_request("POST", "/agent/trade/uniswap/quote", payload=payload)
    if status_code < 200 or status_code >= 300:
        code = str(body.get("code", "uniswap_quote_failed"))
        message = str(body.get("message", f"Uniswap quote failed ({status_code})"))
        raise WalletStoreError(f"{code}: {message}")
    amount_out_units = str(body.get("amountOutUnits") or "").strip()
    if not re.fullmatch(r"[0-9]+", amount_out_units):
        raise WalletStoreError("uniswap_payload_invalid: quote response missing amountOutUnits.")
    quote = body.get("quote")
    if not isinstance(quote, dict):
        raise WalletStoreError("uniswap_payload_invalid: quote response missing quote object.")
    return {
        "amountOutUnits": amount_out_units,
        "routeType": str(body.get("routeType") or "").strip().upper() or "UNKNOWN",
        "quote": quote,
    }


def _uniswap_build_via_proxy(chain: str, wallet_address: str, quote_payload: dict[str, Any]) -> dict[str, Any]:
    agent_id = _resolve_agent_id_or_fail(chain)
    payload = {"agentId": agent_id, "chainKey": chain, "walletAddress": wallet_address, "quote": quote_payload}
    status_code, body = _api_request("POST", "/agent/trade/uniswap/build", payload=payload)
    if status_code < 200 or status_code >= 300:
        code = str(body.get("code", "uniswap_build_failed"))
        message = str(body.get("message", f"Uniswap build failed ({status_code})"))
        raise WalletStoreError(f"{code}: {message}")
    swap_tx = body.get("swapTx")
    if not isinstance(swap_tx, dict):
        raise WalletStoreError("uniswap_payload_invalid: build response missing swapTx object.")
    approval_tx = body.get("approvalTx")
    if approval_tx is not None and not isinstance(approval_tx, dict):
        raise WalletStoreError("uniswap_payload_invalid: build response approvalTx must be object or null.")
    route_type = str(body.get("routeType") or "").strip().upper() or "UNKNOWN"
    amount_out_units = str(body.get("amountOutUnits") or "").strip()
    if amount_out_units and not re.fullmatch(r"[0-9]+", amount_out_units):
        amount_out_units = ""
    return {
        "routeType": route_type,
        "amountOutUnits": amount_out_units or None,
        "approvalTx": approval_tx,
        "swapTx": swap_tx,
    }


def _normalize_uniswap_tx_payload(tx_payload: dict[str, Any], label: str) -> dict[str, str]:
    to_addr = str(tx_payload.get("to") or "").strip()
    data = str(tx_payload.get("data") or "").strip()
    value = str(tx_payload.get("value") or "0").strip() or "0"
    if not is_hex_address(to_addr):
        raise WalletStoreError(f"uniswap_payload_invalid: {label}.to is invalid.")
    if not re.fullmatch(r"0x[a-fA-F0-9]+", data):
        raise WalletStoreError(f"uniswap_payload_invalid: {label}.data is invalid.")
    if not re.fullmatch(r"[0-9]+", value):
        raise WalletStoreError(f"uniswap_payload_invalid: {label}.value must be an unsigned integer string.")
    return {"to": to_addr, "data": data, "value": value}


def _execute_uniswap_swap_via_proxy(
    chain: str,
    wallet_address: str,
    private_key_hex: str,
    token_in: str,
    token_out: str,
    amount_in_units: str,
    slippage_bps: int,
) -> dict[str, Any]:
    rpc_url = _chain_rpc_url(chain)
    cast_bin = _require_cast_bin()
    quoted = _uniswap_quote_via_proxy(chain, wallet_address, token_in, token_out, amount_in_units, slippage_bps)
    built = _uniswap_build_via_proxy(chain, wallet_address, quoted["quote"])
    route_type = str(built.get("routeType") or quoted.get("routeType") or "UNKNOWN").upper()
    approval_tx_hash: str | None = None
    swap_tx_hash: str | None = None

    approval_payload = built.get("approvalTx")
    if isinstance(approval_payload, dict):
        approval_tx = _normalize_uniswap_tx_payload(approval_payload, "approvalTx")
        approval_tx_hash = _cast_rpc_send_transaction(
            rpc_url,
            {"from": wallet_address, "to": approval_tx["to"], "data": approval_tx["data"], "value": approval_tx["value"]},
            private_key_hex,
            chain=chain,
        )
        approval_receipt = _run_subprocess(
            [cast_bin, "receipt", "--json", "--rpc-url", rpc_url, approval_tx_hash],
            timeout_sec=_cast_receipt_timeout_sec(),
            kind="cast_receipt",
        )
        if approval_receipt.returncode != 0:
            stderr = (approval_receipt.stderr or "").strip()
            stdout = (approval_receipt.stdout or "").strip()
            raise WalletStoreError(stderr or stdout or "cast receipt failed for uniswap approval tx.")
        approval_receipt_payload = json.loads((approval_receipt.stdout or "{}").strip() or "{}")
        approval_status = str(approval_receipt_payload.get("status", "0x0")).lower()
        if approval_status not in {"0x1", "1"}:
            raise WalletStoreError(f"Uniswap approval receipt indicates failure status '{approval_status}'.")

    swap_tx = _normalize_uniswap_tx_payload(built["swapTx"], "swapTx")
    swap_tx_hash = _cast_rpc_send_transaction(
        rpc_url,
        {"from": wallet_address, "to": swap_tx["to"], "data": swap_tx["data"], "value": swap_tx["value"]},
        private_key_hex,
        chain=chain,
    )
    receipt_proc = _run_subprocess(
        [cast_bin, "receipt", "--json", "--rpc-url", rpc_url, swap_tx_hash],
        timeout_sec=_cast_receipt_timeout_sec(),
        kind="cast_receipt",
    )
    if receipt_proc.returncode != 0:
        stderr = (receipt_proc.stderr or "").strip()
        stdout = (receipt_proc.stdout or "").strip()
        raise WalletStoreError(stderr or stdout or "cast receipt failed for uniswap swap tx.")
    receipt_payload = json.loads((receipt_proc.stdout or "{}").strip() or "{}")
    receipt_status = str(receipt_payload.get("status", "0x0")).lower()
    if receipt_status not in {"0x1", "1"}:
        raise WalletStoreError(f"Uniswap on-chain receipt indicates failure status '{receipt_status}'.")
    return {
        "approveTxHash": approval_tx_hash,
        "txHash": swap_tx_hash,
        "amountOutUnits": built.get("amountOutUnits") or quoted.get("amountOutUnits"),
        "routeType": route_type,
        **_builder_output_from_hashes(chain, [approval_tx_hash, swap_tx_hash]),
    }


def _solana_amount_units_or_fail(amount_in: str) -> str:
    raw = str(amount_in or "").strip()
    if not re.fullmatch(r"[0-9]+", raw):
        raise WalletStoreError("For Solana trade execution, amountIn must be base-unit integer (lamports/token units).")
    return raw


def _execute_solana_trade(
    *,
    chain: str,
    trade_id: str,
    token_in: str,
    token_out: str,
    amount_in_units: str,
    slippage_bps: int,
    from_status: str,
) -> dict[str, Any]:
    quote = solana_jupiter_quote(
        chain_key=chain,
        input_mint=token_in,
        output_mint=token_out,
        amount_units=amount_in_units,
        slippage_bps=slippage_bps,
    )
    store = load_wallet_store()
    wallet_address, private_key_bytes, key_scheme = _execution_wallet_secret(store, chain)
    if key_scheme != "solana_ed25519":
        raise WalletStoreError(f"Wallet keyScheme '{key_scheme}' is not compatible with Solana execution on chain '{chain}'.")
    tx = solana_jupiter_execute_swap(
        chain_key=chain,
        rpc_url=_chain_rpc_url(chain),
        private_key_bytes=private_key_bytes,
        quote_payload=quote.quote_payload,
        user_address=wallet_address,
    )
    signature = str(tx.get("signature") or "")
    provider_meta = _build_provider_meta("router_adapter", "router_adapter", False, None, quote.route_kind)
    _post_trade_status(trade_id, from_status, "executing", {"txHash": signature, **provider_meta})
    _post_trade_status(trade_id, "executing", "verifying", {"txHash": signature, **provider_meta})
    _post_trade_status(
        trade_id,
        "verifying",
        "filled",
        {
            "txHash": signature,
            "amountOut": quote.amount_out_units,
            "observationSource": "rpc_receipt",
            "confirmationCount": 1,
            "observedAt": utc_now(),
            **provider_meta,
        },
    )
    return {
        "txHash": signature,
        "signature": signature,
        "amountOutUnits": quote.amount_out_units,
        "routeKind": quote.route_kind,
        "providerRequested": "router_adapter",
        "providerUsed": "router_adapter",
        "fallbackUsed": False,
        "fallbackReason": None,
        "executionFamily": "solana_swap",
        "executionAdapter": "jupiter",
    }


def cmd_trade_spot(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk

    chain = args.chain
    trade_id: str | None = None
    transition_state = "init"
    last_tx_hash: str | None = None
    last_approve_tx_hash: str | None = None
    provider_requested, _ = _trade_provider_settings(chain)
    provider_used = "router_adapter"
    fallback_used = False
    fallback_reason: dict[str, str] | None = None
    uniswap_route_type: str | None = None
    try:
        if _is_solana_chain(chain):
            token_in = _resolve_token_address(chain, args.token_in)
            token_out = _resolve_token_address(chain, args.token_out)
            if token_in == token_out:
                return fail(
                    "invalid_input",
                    "token-in and token-out must be different.",
                    "Provide two distinct token mint addresses (or symbols).",
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
            amount_in_units = _solana_amount_units_or_fail(str(args.amount_in))
            amount_in_int = int(amount_in_units)
            state, day_key, current_spend, max_daily_wei = _enforce_spend_preconditions(chain, amount_in_int, enforce_native_cap=False)
            summary = {
                "tradeId": None,
                "chainKey": chain,
                "tokenInSymbol": str(args.token_in),
                "tokenOutSymbol": str(args.token_out),
                "amountInHuman": _normalize_amount_human_text(amount_in_units),
                "slippageBps": slippage_bps,
            }
            proposed = _post_trade_proposed(
                chain,
                token_in,
                token_out,
                amount_in_units,
                slippage_bps,
                amount_out_human=None,
                reason="trade_spot_solana",
            )
            trade_id = str(proposed.get("tradeId") or "")
            if not trade_id:
                raise WalletStoreError("Trade proposal did not return a tradeId.")
            summary["tradeId"] = trade_id
            if str(proposed.get("status") or "") != "approved":
                _wait_for_trade_approval(trade_id, chain, summary)
            execution = _execute_solana_trade(
                chain=chain,
                trade_id=trade_id,
                token_in=token_in,
                token_out=token_out,
                amount_in_units=amount_in_units,
                slippage_bps=slippage_bps,
                from_status="approved",
            )
            _record_spend(state, chain, day_key, current_spend + amount_in_int)
            return ok(
                "Spot swap executed on-chain via runtime-local Solana adapter.",
                chain=chain,
                tokenIn=token_in,
                tokenOut=token_out,
                amountInUnits=amount_in_units,
                expectedOutUnits=str(execution.get("amountOutUnits") or "0"),
                txHash=execution.get("txHash"),
                signature=execution.get("signature"),
                providerRequested=execution.get("providerRequested"),
                providerUsed=execution.get("providerUsed"),
                fallbackUsed=execution.get("fallbackUsed"),
                fallbackReason=execution.get("fallbackReason"),
                executionFamily=execution.get("executionFamily"),
                executionAdapter=execution.get("executionAdapter"),
                routeKind=execution.get("routeKind"),
                day=day_key,
                dailySpendWei=str(current_spend + amount_in_int),
                maxDailyNativeWei=str(max_daily_wei),
            )

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
        adapter_key, adapter_entry = resolve_trade_execution_adapter(chain, "")
        router = str(adapter_entry.get("router") or "").strip()
        if not router:
            raise WalletStoreError(f"chain_config_invalid: trade adapter '{adapter_key}' on chain '{chain}' is missing router.")

        token_in_meta = _fetch_erc20_metadata(chain, token_in)
        token_out_meta = _fetch_erc20_metadata(chain, token_out)
        token_in_decimals = int(token_in_meta.get("decimals", 18))
        token_out_decimals = int(token_out_meta.get("decimals", 18))

        amount_in_units, amount_in_mode = _parse_amount_in_units(str(args.amount_in), token_in_decimals)
        amount_in_int = int(amount_in_units)
        state, day_key, current_spend, max_daily_wei = _enforce_spend_preconditions(chain, amount_in_int, enforce_native_cap=False)

        quote_payload = _quote_trade_via_router_adapter(
            chain=chain,
            adapter_key=adapter_key,
            token_in=token_in,
            token_out=token_out,
            amount_in_units=amount_in_units,
        )
        expected_out_int = int(str(quote_payload.get("amountOutUnits") or "0"))
        uniswap_route_type = str(quote_payload.get("routeKind") or "").strip() or None
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
        quote_payload = _quote_trade_via_router_adapter(
            chain=chain,
            adapter_key=adapter_key,
            token_in=token_in,
            token_out=token_out,
            amount_in_units=amount_in_units,
        )
        expected_out_int = int(str(quote_payload.get("amountOutUnits") or "0"))
        uniswap_route_type = str(quote_payload.get("routeKind") or "").strip() or uniswap_route_type
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

        to_addr = str(args.to or "").strip() or wallet_address
        if not is_hex_address(to_addr):
            return fail(
                "invalid_input",
                "to must be a valid 0x address.",
                "Provide a 0x-prefixed 20-byte hex address or omit to default to the execution wallet.",
                {"to": args.to},
                exit_code=2,
            )

        execution = _execute_trade_via_router_adapter(
            chain=chain,
            adapter_key=adapter_key,
            wallet_address=wallet_address,
            private_key_hex=private_key_hex,
            token_in=token_in,
            token_out=token_out,
            amount_in_units=amount_in_units,
            min_out_units=str(min_out_int),
            deadline=deadline,
            recipient=to_addr,
            wait_for_receipt=False,
        )
        provider_used = "router_adapter"
        approve_tx_hashes = execution.get("approveTxHashes") or []
        if isinstance(approve_tx_hashes, list) and approve_tx_hashes:
            approve_tx_hash = str(approve_tx_hashes[-1] or "") or None
        tx_hash = str(execution.get("txHash") or "")
        if not re.fullmatch(r"0x[a-fA-F0-9]{64}", tx_hash):
            raise WalletStoreError("trade_execution_failed: missing txHash from router adapter execution.")
        if approve_tx_hash:
            last_approve_tx_hash = approve_tx_hash
        uniswap_route_type = str(execution.get("routeKind") or "").strip() or uniswap_route_type
        execution_family = str(execution.get("executionFamily") or "").strip() or "amm_v2"
        execution_adapter = str(execution.get("executionAdapter") or "").strip() or adapter_key
        last_tx_hash = tx_hash
        provider_meta = _build_provider_meta(provider_requested, provider_used, fallback_used, fallback_reason, uniswap_route_type)
        _post_trade_status(trade_id, "approved", "executing", {"txHash": tx_hash, **provider_meta})
        transition_state = "executing"
        _post_trade_status(trade_id, "executing", "verifying", {"txHash": tx_hash, **provider_meta})
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
        _post_trade_status(
            trade_id,
            "verifying",
            "filled",
            {
                "txHash": tx_hash,
                "amountOut": _format_units(int(expected_out_int), token_out_decimals),
                "observationSource": "rpc_receipt",
                "confirmationCount": 1,
                "observedAt": utc_now(),
                **provider_meta,
            },
        )
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

        builder_meta = _builder_output_from_hashes(chain, [approve_tx_hash, tx_hash])
        return ok(
            "Spot swap executed on-chain via runtime-local router adapter.",
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
            providerRequested=provider_requested,
            providerUsed=provider_used,
            fallbackUsed=fallback_used,
            fallbackReason=fallback_reason,
            executionFamily=execution_family,
            executionAdapter=execution_adapter,
            routeKind=uniswap_route_type,
            **builder_meta,
        )
    except SubprocessTimeout as exc:
        details: dict[str, Any] = {
            "chain": chain,
            "timeoutSec": exc.timeout_sec,
            "kind": exc.kind,
            "providerRequested": provider_requested,
            "providerUsed": provider_used,
            "fallbackUsed": fallback_used,
            "fallbackReason": fallback_reason,
            "routeKind": uniswap_route_type,
        }
        if last_tx_hash:
            details["txHash"] = last_tx_hash
        if last_approve_tx_hash:
            details["approveTxHash"] = last_approve_tx_hash
        if trade_id and transition_state in {"executing", "verifying"}:
            try:
                from_status = "executing" if transition_state == "executing" else "verifying"
                provider_meta = _build_provider_meta(provider_requested, provider_used, fallback_used, fallback_reason, uniswap_route_type)
                _post_trade_status(
                    trade_id,
                    from_status,
                    "failed",
                    {"reasonCode": "verification_timeout", "reasonMessage": str(exc), "txHash": last_tx_hash, **provider_meta},
                )
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
                provider_meta = _build_provider_meta(provider_requested, provider_used, fallback_used, fallback_reason, uniswap_route_type)
                _post_trade_status(
                    trade_id,
                    from_status,
                    "failed",
                    {"reasonCode": "policy_denied", "reasonMessage": str(exc), "txHash": last_tx_hash, **provider_meta},
                )
                _remove_pending_spot_trade_flow(trade_id)
            except Exception:
                pass
        details = dict(exc.details or {})
        details.update(_build_provider_meta(provider_requested, provider_used, fallback_used, fallback_reason, uniswap_route_type))
        return fail(exc.code, str(exc), exc.action_hint, details, exit_code=1)
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
        return fail(
            "trade_spot_failed",
            msg,
            "Verify wallet, RPC, token addresses, and retry.",
            {
                "chain": chain,
                "providerRequested": provider_requested,
                "providerUsed": provider_used,
                "fallbackUsed": fallback_used,
                "fallbackReason": fallback_reason,
                "routeKind": uniswap_route_type,
            },
            exit_code=1,
        )
    except Exception as exc:
        msg = (str(exc) or "").strip()
        if not msg:
            msg = f"{type(exc).__name__}: (no message)"
        return fail(
            "trade_spot_failed",
            msg,
            "Inspect runtime trade spot path and retry.",
            {
                "chain": chain,
                "exceptionType": type(exc).__name__,
                "providerRequested": provider_requested,
                "providerUsed": provider_used,
                "fallbackUsed": fallback_used,
                "fallbackReason": fallback_reason,
                "routeKind": uniswap_route_type,
            },
            exit_code=1,
        )


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
    key_scheme = str(wallet.get("keyScheme") or "evm_secp256k1").strip().lower() or "evm_secp256k1"
    if key_scheme != "evm_secp256k1":
        raise WalletStoreError(f"Wallet keyScheme '{key_scheme}' is not compatible with EVM execution on chain '{chain}'.")
    address = str(wallet.get("address"))
    passphrase = _require_wallet_passphrase_for_signing(chain)
    private_key_hex = _decrypt_private_key(wallet, passphrase).hex()
    return address, private_key_hex


def _execution_wallet_secret(store: dict[str, Any], chain: str) -> tuple[str, bytes, str]:
    _, wallet = _chain_wallet(store, chain)
    if wallet is None:
        raise WalletStoreError(f"No wallet configured for chain '{chain}'.")
    _validate_wallet_entry_shape(wallet)
    address = str(wallet.get("address"))
    key_scheme = str(wallet.get("keyScheme") or "evm_secp256k1").strip().lower() or "evm_secp256k1"
    passphrase = _require_wallet_passphrase_for_signing(chain)
    secret = _decrypt_private_key(wallet, passphrase)
    return address, secret, key_scheme


def _execution_wallet_solana_secret(store: dict[str, Any], chain: str) -> tuple[str, bytes]:
    address, secret, key_scheme = _execution_wallet_secret(store, chain)
    if key_scheme != "solana_ed25519":
        raise WalletStoreError(f"Wallet keyScheme '{key_scheme}' is not compatible with Solana execution on chain '{chain}'.")
    return address, secret


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
        "temporary internal error",
        '"code":19',
        "error code 19",
    )
    return any(fragment in normalized for fragment in retryable_fragments)


def _send_error_requires_estimate_bypass(stderr: str) -> bool:
    normalized = str(stderr or "").strip().lower()
    if not normalized:
        return False
    bypass_fragments = (
        "failed to estimate gas",
        "eth_estimategas",
        "execution reverted: ds-math-sub-underflow",
    )
    return any(fragment in normalized for fragment in bypass_fragments)


def _tx_estimate_bypass_gas_limit(chain: str | None) -> int | None:
    raw = (os.environ.get("XCLAW_TX_ESTIMATE_BYPASS_GAS_LIMIT") or "").strip()
    if raw:
        if not re.fullmatch(r"[0-9]+", raw):
            raise WalletStoreError("XCLAW_TX_ESTIMATE_BYPASS_GAS_LIMIT must be an integer >= 21000.")
        parsed = int(raw)
        if parsed < 21000:
            raise WalletStoreError("XCLAW_TX_ESTIMATE_BYPASS_GAS_LIMIT must be >= 21000.")
        return parsed
    chain_key = str(chain or "").strip().lower()
    if chain_key in {"ethereum_sepolia", "base_sepolia"}:
        return DEFAULT_TX_ESTIMATE_BYPASS_GAS_LIMIT
    return None


def _legacy_gas_price_multiplier(chain: str | None) -> int:
    return 1


def _parse_min_gas_price_wei_from_error(stderr: str) -> int | None:
    normalized = str(stderr or "")
    match = re.search(r"minimum gas price '([0-9]+)'", normalized, flags=re.IGNORECASE)
    if not match:
        return None
    try:
        value = int(match.group(1))
    except Exception:
        return None
    return value if value > 0 else None


def _is_base_builder_chain(chain: str) -> bool:
    return str(chain or "").strip() in BASE_BUILDER_CHAINS


def _erc8021_magic_hex() -> str:
    return "8021" * ERC8021_MAGIC_REPEAT_COUNT


def _resolve_builder_code_for_chain(chain: str) -> tuple[str, str]:
    chain_key = str(chain or "").strip()
    scoped_env_key = f"XCLAW_BUILDER_CODE_{_chain_env_suffix(chain_key)}"
    scoped = str(os.environ.get(scoped_env_key) or "").strip()
    if scoped:
        return scoped, scoped_env_key
    default_env_key = "XCLAW_BUILDER_CODE_BASE"
    default_value = str(os.environ.get(default_env_key) or "").strip()
    if default_value:
        return default_value, default_env_key
    return "", ""


def _encode_erc8021_suffix(builder_codes: list[str]) -> str:
    cleaned: list[str] = []
    for raw in builder_codes:
        code = str(raw or "").strip()
        if not code:
            raise WalletStoreError("builder_code_invalid: empty builder code.")
        if "," in code:
            raise WalletStoreError("builder_code_invalid: builder code must not contain commas.")
        if not code.isascii():
            raise WalletStoreError("builder_code_invalid: builder code must be ASCII.")
        cleaned.append(code)
    if not cleaned:
        raise WalletStoreError("builder_code_invalid: at least one builder code is required.")
    payload_text = ",".join(cleaned)
    payload_bytes = payload_text.encode("utf-8")
    payload_len = len(payload_bytes)
    if payload_len > 255:
        raise WalletStoreError("builder_code_invalid: encoded builder code payload exceeds 255 bytes.")
    schema_hex = "00"
    length_hex = f"{payload_len:02x}"
    payload_hex = payload_bytes.hex()
    return f"0x{schema_hex}{length_hex}{payload_hex}{_erc8021_magic_hex()}"


def _has_erc8021_suffix(data_hex: str) -> bool:
    text = str(data_hex or "").strip().lower()
    if not re.fullmatch(r"0x[a-f0-9]*", text):
        return False
    return text.endswith(_erc8021_magic_hex())


def _default_builder_attribution(chain: str) -> dict[str, Any]:
    eligible = _is_base_builder_chain(chain)
    return {
        "builderCodeChainEligible": eligible,
        "builderCodeApplied": False,
        "builderCodeSkippedReason": "non_base_chain" if not eligible else "not_evaluated",
        "builderCodeSource": None,
        "builderCodeValue": None,
        "builderCodeStandard": "erc8021" if eligible else None,
    }


def _apply_builder_code_suffix_if_needed(chain: str, data_hex: str) -> tuple[str, dict[str, Any]]:
    chain_key = str(chain or "").strip()
    text = str(data_hex or "").strip()
    if text == "":
        text = "0x"
    if not re.fullmatch(r"0x[a-fA-F0-9]*", text):
        raise WalletStoreError("builder_code_invalid: tx data must be hex calldata.")
    if len(text) % 2 != 0:
        raise WalletStoreError("builder_code_invalid: tx data must use even-length hex bytes.")

    meta = _default_builder_attribution(chain_key)
    if not meta["builderCodeChainEligible"]:
        return text, meta
    if text == "0x":
        meta["builderCodeSkippedReason"] = "empty_calldata_safe_mode"
        return text, meta
    if _has_erc8021_suffix(text):
        meta["builderCodeSkippedReason"] = "already_tagged"
        return text, meta

    builder_code, source_key = _resolve_builder_code_for_chain(chain_key)
    if not builder_code:
        raise WalletStoreError(
            f"builder_code_missing: configure XCLAW_BUILDER_CODE_{_chain_env_suffix(chain_key)} or XCLAW_BUILDER_CODE_BASE."
        )
    suffix = _encode_erc8021_suffix([builder_code])
    tagged = f"0x{text[2:]}{suffix[2:]}"
    meta.update(
        {
            "builderCodeApplied": True,
            "builderCodeSkippedReason": None,
            "builderCodeSource": source_key,
            "builderCodeValue": builder_code,
            "builderCodeStandard": "erc8021",
        }
    )
    return tagged, meta


def _record_tx_builder_attribution(tx_hash: str, metadata: dict[str, Any]) -> None:
    tx = str(tx_hash or "").strip().lower()
    if not re.fullmatch(r"0x[a-f0-9]{64}", tx):
        return
    _TX_BUILDER_ATTRIBUTION_BY_HASH[tx] = dict(metadata or {})


def _tx_builder_attribution(tx_hash: str | None) -> dict[str, Any] | None:
    tx = str(tx_hash or "").strip().lower()
    if not tx:
        return None
    row = _TX_BUILDER_ATTRIBUTION_BY_HASH.get(tx)
    return dict(row) if isinstance(row, dict) else None


def _builder_output_from_hashes(chain: str, tx_hashes: list[str | None]) -> dict[str, Any]:
    eligible = _is_base_builder_chain(chain)
    defaults = {
        "builderCodeChainEligible": eligible,
        "builderCodeApplied": False,
        "builderCodeSkippedReason": "non_base_chain" if not eligible else None,
        "builderCodeSource": None,
        "builderCodeStandard": "erc8021" if eligible else None,
    }
    if not eligible:
        return defaults
    rows = [_tx_builder_attribution(tx_hash) for tx_hash in tx_hashes]
    rows = [row for row in rows if isinstance(row, dict)]
    if not rows:
        return defaults
    applied = any(bool(row.get("builderCodeApplied")) for row in rows)
    source = next((row.get("builderCodeSource") for row in rows if row.get("builderCodeSource")), None)
    skipped = None if applied else next((row.get("builderCodeSkippedReason") for row in rows if row.get("builderCodeSkippedReason")), None)
    return {
        "builderCodeChainEligible": True,
        "builderCodeApplied": applied,
        "builderCodeSkippedReason": skipped,
        "builderCodeSource": source,
        "builderCodeStandard": "erc8021",
    }


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


def _tx_fee_mode() -> str:
    raw = (os.environ.get("XCLAW_TX_FEE_MODE") or "").strip().lower()
    if raw == "":
        return "rpc"
    if raw not in {"rpc", "legacy"}:
        raise WalletStoreError("XCLAW_TX_FEE_MODE must be rpc|legacy.")
    return raw


def _tx_retry_bump_bps() -> int:
    raw = (os.environ.get("XCLAW_TX_RETRY_BUMP_BPS") or "").strip()
    if raw == "":
        return DEFAULT_TX_RETRY_BUMP_BPS
    if not re.fullmatch(r"[0-9]+", raw):
        raise WalletStoreError("XCLAW_TX_RETRY_BUMP_BPS must be an integer >= 0.")
    value = int(raw)
    if value < 0:
        raise WalletStoreError("XCLAW_TX_RETRY_BUMP_BPS must be >= 0.")
    return value


def _tx_priority_floor_gwei() -> int:
    raw = (os.environ.get("XCLAW_TX_PRIORITY_FLOOR_GWEI") or "").strip()
    if raw == "":
        return DEFAULT_TX_PRIORITY_FLOOR_GWEI
    if not re.fullmatch(r"[0-9]+", raw):
        raise WalletStoreError("XCLAW_TX_PRIORITY_FLOOR_GWEI must be an integer >= 0.")
    value = int(raw)
    if value < 0:
        raise WalletStoreError("XCLAW_TX_PRIORITY_FLOOR_GWEI must be >= 0.")
    return value


def _rpc_hex_to_int(value: Any, field_name: str) -> int:
    if isinstance(value, int):
        if value < 0:
            raise WalletStoreError(f"RPC field '{field_name}' must be non-negative.")
        return value
    text = str(value or "").strip()
    if text == "":
        raise WalletStoreError(f"RPC field '{field_name}' is missing.")
    try:
        if text.lower().startswith("0x"):
            return int(text, 16)
        return int(text)
    except Exception as exc:
        raise WalletStoreError(f"RPC field '{field_name}' is not a valid integer.") from exc


def _rpc_json_call(rpc_url: str, method: str, params: list[Any]) -> Any:
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    req = urllib.request.Request(
        rpc_url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        timeout_sec = max(2, _cast_call_timeout_sec())
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except Exception as exc:
        raise WalletStoreError(f"RPC call failed for {method}: {exc}") from exc
    try:
        body = json.loads(raw or "{}")
    except Exception as exc:
        raise WalletStoreError(f"RPC call returned invalid JSON for {method}.") from exc
    if not isinstance(body, dict):
        raise WalletStoreError(f"RPC call returned invalid payload for {method}.")
    if isinstance(body.get("error"), dict):
        err = body.get("error") or {}
        code = err.get("code")
        message = err.get("message")
        raise WalletStoreError(f"RPC {method} error ({code}): {message}")
    if "result" not in body:
        raise WalletStoreError(f"RPC response missing result for {method}.")
    return body.get("result")


def _apply_retry_bump_wei(value_wei: int, attempt_index: int, bump_bps: int) -> int:
    if value_wei < 0:
        raise WalletStoreError("fee value must be non-negative.")
    if attempt_index <= 0 or bump_bps <= 0:
        return value_wei
    multiplier = 10_000 + (bump_bps * attempt_index)
    return (value_wei * multiplier + 9_999) // 10_000


def _estimate_legacy_gas_price_wei(rpc_url: str, attempt_index: int) -> int:
    bump_bps = _tx_retry_bump_bps()
    try:
        rpc_gas_price = _rpc_json_call(rpc_url, "eth_gasPrice", [])
        base_wei = _rpc_hex_to_int(rpc_gas_price, "gasPrice")
    except Exception:
        base_wei = _tx_gas_price_gwei(attempt_index=0) * (10**9)
    return _apply_retry_bump_wei(base_wei, attempt_index, bump_bps)


def _estimate_tx_fees(rpc_url: str, attempt_index: int) -> dict[str, Any]:
    if attempt_index < 0:
        raise WalletStoreError("attempt_index must be >= 0.")
    mode = _tx_fee_mode()
    if mode == "legacy":
        gas_price_wei = _tx_gas_price_gwei(attempt_index) * (10**9)
        return {"mode": "legacy", "gasPrice": gas_price_wei}

    bump_bps = _tx_retry_bump_bps()
    priority_floor_wei = _tx_priority_floor_gwei() * (10**9)

    try:
        history = _rpc_json_call(rpc_url, "eth_feeHistory", ["0x5", "latest", [10, 50, 90]])
        if not isinstance(history, dict):
            raise WalletStoreError("eth_feeHistory returned invalid payload.")

        base_fee_values = history.get("baseFeePerGas")
        if not isinstance(base_fee_values, list) or len(base_fee_values) == 0:
            raise WalletStoreError("eth_feeHistory missing baseFeePerGas.")
        latest_base_fee_wei = _rpc_hex_to_int(base_fee_values[-1], "baseFeePerGas")

        observed_priority_wei: int
        try:
            max_priority = _rpc_json_call(rpc_url, "eth_maxPriorityFeePerGas", [])
            observed_priority_wei = _rpc_hex_to_int(max_priority, "maxPriorityFeePerGas")
        except Exception:
            rewards = history.get("reward")
            if not isinstance(rewards, list) or len(rewards) == 0 or not isinstance(rewards[-1], list) or len(rewards[-1]) == 0:
                raise WalletStoreError("eth_feeHistory missing reward fallback values.")
            reward_sample = rewards[-1]
            reward_values = [_rpc_hex_to_int(item, "reward") for item in reward_sample]
            observed_priority_wei = max(reward_values)

        max_priority_fee_per_gas_wei = max(priority_floor_wei, observed_priority_wei)
        max_fee_per_gas_wei = (latest_base_fee_wei * 2) + max_priority_fee_per_gas_wei

        max_priority_fee_per_gas_wei = _apply_retry_bump_wei(max_priority_fee_per_gas_wei, attempt_index, bump_bps)
        max_fee_per_gas_wei = _apply_retry_bump_wei(max_fee_per_gas_wei, attempt_index, bump_bps)

        return {
            "mode": "eip1559",
            "maxFeePerGas": max_fee_per_gas_wei,
            "maxPriorityFeePerGas": max_priority_fee_per_gas_wei,
        }
    except Exception:
        gas_price_wei = _estimate_legacy_gas_price_wei(rpc_url, attempt_index)
        return {"mode": "legacy", "gasPrice": gas_price_wei}


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


def _cast_rpc_send_transaction(
    rpc_url: str, tx_obj: dict[str, Any], private_key_hex: str | None = None, chain: str | None = None
) -> str:
    cast_bin = _require_cast_bin()
    if private_key_hex:
        from_addr = tx_obj.get("from")
        to_addr = tx_obj.get("to")
        data_raw = tx_obj.get("data")
        data = str(data_raw).strip() if data_raw is not None else "0x"
        if data == "":
            data = "0x"
        value_raw = tx_obj.get("value")
        value_wei: str | None = None
        if value_raw is not None:
            value_text = str(value_raw).strip()
            if value_text == "":
                value_text = "0"
            if not re.fullmatch(r"[0-9]+", value_text):
                raise WalletStoreError("cast send requires tx_obj.value as uint string.")
            value_wei = value_text
        if not isinstance(from_addr, str) or not is_hex_address(from_addr):
            raise WalletStoreError("cast send requires tx_obj.from as hex address.")
        if not isinstance(to_addr, str) or not is_hex_address(to_addr):
            raise WalletStoreError("cast send requires tx_obj.to as hex address.")
        if not re.fullmatch(r"0x[a-fA-F0-9]*", data):
            raise WalletStoreError("cast send requires tx_obj.data as hex calldata.")
        attribution_meta: dict[str, Any] = _default_builder_attribution(str(chain or "").strip())
        if chain:
            data, attribution_meta = _apply_builder_code_suffix_if_needed(str(chain), data)
        attempts = _tx_send_max_attempts()
        last_err = "cast send failed."
        rpc_candidates = [rpc_url]
        if chain:
            for candidate in _chain_rpc_candidates(str(chain)):
                if candidate not in rpc_candidates:
                    rpc_candidates.append(candidate)
        for rpc_index, rpc_candidate in enumerate(rpc_candidates):
            nonce_override: int | None = None
            forced_legacy_gas_price_wei: int | None = None
            forced_gas_limit: int | None = None
            for attempt in range(attempts):
                nonce: int | None
                if nonce_override is not None:
                    nonce = nonce_override
                elif attempt == 0:
                    # Let the RPC assign nonce for first submit to avoid accidental
                    # replacement races with concurrent in-flight txs.
                    nonce = None
                else:
                    nonce_pending = _cast_nonce(cast_bin, rpc_candidate, from_addr, "pending")
                    nonce_latest = _cast_nonce(cast_bin, rpc_candidate, from_addr, "latest")
                    nonce_candidates = [value for value in (nonce_pending, nonce_latest) if value is not None]
                    nonce = max(nonce_candidates) if nonce_candidates else None

                fee_plan = _estimate_tx_fees(rpc_candidate, attempt)
                send_cmd = [
                    cast_bin,
                    "send",
                    "--json",
                    "--rpc-url",
                    rpc_candidate,
                    "--private-key",
                    private_key_hex,
                ]
                if str(fee_plan.get("mode")) == "eip1559":
                    max_fee = int(fee_plan.get("maxFeePerGas", 0))
                    max_priority = int(fee_plan.get("maxPriorityFeePerGas", 0))
                    send_cmd.extend(["--max-fee-per-gas", str(max_fee), "--priority-gas-price", str(max_priority)])
                else:
                    gas_price = int(fee_plan.get("gasPrice", 0))
                    gas_price *= _legacy_gas_price_multiplier(chain)
                    if forced_legacy_gas_price_wei is not None:
                        gas_price = max(gas_price, forced_legacy_gas_price_wei)
                    if gas_price <= 0:
                        raise WalletStoreError("Legacy fee estimation returned invalid gas price.")
                    send_cmd.extend(["--gas-price", str(gas_price)])
                if forced_gas_limit is not None:
                    send_cmd.extend(["--gas-limit", str(forced_gas_limit)])
                if nonce is not None:
                    send_cmd.extend(["--nonce", str(nonce)])
                send_cmd.extend(
                    [
                        "--from",
                        from_addr,
                        to_addr,
                    ]
                )
                if data != "0x":
                    send_cmd.append(data)
                if value_wei is not None and value_wei != "0":
                    send_cmd.extend(["--value", value_wei])
                proc = _run_subprocess(send_cmd, timeout_sec=_cast_send_timeout_sec(), kind="cast_send")
                if proc.returncode == 0:
                    tx_hash = _extract_tx_hash(proc.stdout)
                    _record_tx_builder_attribution(tx_hash, attribution_meta)
                    return tx_hash

                stderr = (proc.stderr or "").strip()
                stdout = (proc.stdout or "").strip()
                last_err = stderr or stdout or "cast send failed."
                min_gas_price = _parse_min_gas_price_wei_from_error(last_err)
                if min_gas_price is not None:
                    forced_legacy_gas_price_wei = max(forced_legacy_gas_price_wei or 0, min_gas_price)
                if attempt < (attempts - 1) and min_gas_price is not None:
                    time.sleep(0.25)
                    continue
                if attempt < (attempts - 1) and forced_gas_limit is None and _send_error_requires_estimate_bypass(last_err):
                    bypass_gas_limit = _tx_estimate_bypass_gas_limit(chain)
                    if bypass_gas_limit is not None:
                        forced_gas_limit = bypass_gas_limit
                        time.sleep(0.2)
                        continue
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
            if rpc_index < (len(rpc_candidates) - 1) and (
                _retryable_send_error(last_err) or _send_error_requires_estimate_bypass(last_err)
            ):
                time.sleep(0.25)
                continue
            break

        raise WalletStoreError(f"{last_err} (after {attempts} attempts across {len(rpc_candidates)} rpc candidate(s))")
    else:
        tx_payload = dict(tx_obj or {})
        attribution_meta = _default_builder_attribution(str(chain or "").strip())
        if chain:
            payload_data_raw = tx_payload.get("data")
            payload_data = str(payload_data_raw).strip() if payload_data_raw is not None else "0x"
            if payload_data == "":
                payload_data = "0x"
            payload_data, attribution_meta = _apply_builder_code_suffix_if_needed(str(chain), payload_data)
            tx_payload["data"] = payload_data
        proc = _run_subprocess(
            [cast_bin, "rpc", "--rpc-url", rpc_url, "eth_sendTransaction", json.dumps(tx_payload, separators=(",", ":"))],
            timeout_sec=_cast_send_timeout_sec(),
            kind="cast_send",
        )
    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        stdout = (proc.stdout or "").strip()
        raise WalletStoreError(stderr or stdout or "cast rpc eth_sendTransaction failed.")
    tx_hash = _extract_tx_hash(proc.stdout)
    if chain:
        _record_tx_builder_attribution(tx_hash, attribution_meta)
    return tx_hash


def cmd_status(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    default_chain, default_chain_source = _resolve_runtime_default_chain()
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
        defaultChainSource=default_chain_source,
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
    provider_requested, _ = _trade_provider_settings(args.chain)
    provider_used = "router_adapter"
    fallback_used = False
    fallback_reason: dict[str, str] | None = None
    uniswap_route_type: str | None = None
    try:
        if _is_solana_chain(args.chain):
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
            if status not in {"approved", "failed"}:
                return fail(
                    "approval_required",
                    f"Trade is not executable from status '{status}'.",
                    "Execute only approved trades or failed trades within retry policy.",
                    {"tradeId": args.intent, "status": status},
                    exit_code=1,
                )
            token_in = _resolve_token_address(args.chain, str(trade.get("tokenIn") or ""))
            token_out = _resolve_token_address(args.chain, str(trade.get("tokenOut") or ""))
            amount_in_units = _solana_amount_units_or_fail(str(trade.get("amountIn") or ""))
            slippage_bps = int(trade.get("slippageBps", 100) or 100)
            execution = _execute_solana_trade(
                chain=args.chain,
                trade_id=args.intent,
                token_in=token_in,
                token_out=token_out,
                amount_in_units=amount_in_units,
                slippage_bps=slippage_bps,
                from_status=status,
            )
            return ok(
                "Trade executed in real mode via runtime-local Solana adapter.",
                tradeId=args.intent,
                chain=args.chain,
                status="filled",
                txHash=execution.get("txHash"),
                signature=execution.get("signature"),
                providerRequested=execution.get("providerRequested"),
                providerUsed=execution.get("providerUsed"),
                fallbackUsed=execution.get("fallbackUsed"),
                fallbackReason=execution.get("fallbackReason"),
                executionFamily=execution.get("executionFamily"),
                executionAdapter=execution.get("executionAdapter"),
                routeKind=execution.get("routeKind"),
            )

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
                "Execute network trades with mode=real on a configured chain.",
                {"tradeId": args.intent, "mode": mode, "supportedMode": "real", "chain": args.chain},
                exit_code=1,
            )

        store = load_wallet_store()
        wallet_address, private_key_hex = _execution_wallet(store, args.chain)
        adapter_key, adapter_entry = resolve_trade_execution_adapter(args.chain, "")
        router = str(adapter_entry.get("router") or "").strip()
        if not router:
            raise WalletStoreError(
                f"chain_config_invalid: trade adapter '{adapter_key}' on chain '{args.chain}' is missing router."
            )

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
        execution = _execute_trade_via_router_adapter(
            chain=args.chain,
            adapter_key=adapter_key,
            wallet_address=wallet_address,
            private_key_hex=private_key_hex,
            token_in=token_in,
            token_out=token_out,
            amount_in_units=amount_wei_str,
            min_out_units="1",
            deadline=deadline,
            recipient=wallet_address,
            wait_for_receipt=False,
        )
        approve_tx_hashes = execution.get("approveTxHashes") or []
        approve_tx_hash = str(approve_tx_hashes[-1]) if isinstance(approve_tx_hashes, list) and approve_tx_hashes else None
        tx_hash = str(execution.get("txHash") or "")
        if not re.fullmatch(r"0x[a-fA-F0-9]{64}", tx_hash):
            raise WalletStoreError("trade_execution_failed: missing txHash from router adapter execution.")
        uniswap_route_type = str(execution.get("routeKind") or "").strip() or None
        execution_family = str(execution.get("executionFamily") or "").strip() or "amm_v2"
        execution_adapter = str(execution.get("executionAdapter") or "").strip() or adapter_key
        provider_meta = _build_provider_meta(provider_requested, provider_used, fallback_used, fallback_reason, uniswap_route_type)
        _post_trade_status(args.intent, previous_status, "executing", {"txHash": tx_hash, **provider_meta})
        transition_state = "executing"
        _post_trade_status(args.intent, "executing", "verifying", {"txHash": tx_hash, **provider_meta})
        transition_state = "verifying"

        # Do not block foreground chat/tool execution on confirmation latency.
        # Real-mode terminal status is tracked asynchronously via server-side watcher paths.
        report_result = {
            "ok": False,
            "skipped": True,
            "reason": "real_mode_server_tracked",
            "message": "Real-mode trade reports are server-tracked via wallet/RPC and are not sent by runtime."
        }
        builder_meta = _builder_output_from_hashes(args.chain, [approve_tx_hash, tx_hash])
        return ok(
            "Trade broadcast in real mode via runtime-local router adapter; confirmation is asynchronous.",
            tradeId=args.intent,
            chain=args.chain,
            mode=mode,
            status="verifying",
            txHash=tx_hash,
            day=day_key,
            dailySpendUsd=_decimal_text(current_spend_usd),
            maxDailyUsd=trade_caps.get("maxDailyUsd"),
            dailyFilledTrades=int(current_filled_trades),
            maxDailyTradeCount=trade_caps.get("maxDailyTradeCount"),
            dailySpendWei=str(current_spend),
            maxDailyNativeWei=str(max_daily_wei),
            providerRequested=provider_requested,
            providerUsed=provider_used,
            fallbackUsed=fallback_used,
            fallbackReason=fallback_reason,
            executionFamily=execution_family,
            executionAdapter=execution_adapter,
            routeKind=uniswap_route_type,
            report=report_result,
            actionHint="Execution is in verifying state; watcher will publish terminal filled/failed status.",
            **builder_meta,
        )
    except WalletPolicyError as exc:
        if transition_state == "executing":
            try:
                provider_meta = _build_provider_meta(provider_requested, provider_used, fallback_used, fallback_reason, uniswap_route_type)
                _post_trade_status(args.intent, "executing", "failed", {"reasonCode": "policy_denied", "reasonMessage": str(exc), **provider_meta})
            except Exception:
                pass
        details = dict(exc.details or {})
        details.update(_build_provider_meta(provider_requested, provider_used, fallback_used, fallback_reason, uniswap_route_type))
        return fail(exc.code, str(exc), exc.action_hint, details, exit_code=1)
    except WalletStoreError as exc:
        if transition_state == "executing":
            try:
                provider_meta = _build_provider_meta(provider_requested, provider_used, fallback_used, fallback_reason, uniswap_route_type)
                _post_trade_status(args.intent, "executing", "failed", {"reasonCode": "rpc_unavailable", "reasonMessage": str(exc), **provider_meta})
            except Exception:
                pass
        elif transition_state == "init":
            try:
                provider_meta = _build_provider_meta(provider_requested, provider_used, fallback_used, fallback_reason, uniswap_route_type)
                _post_trade_status(args.intent, previous_status, "failed", {"reasonCode": "rpc_unavailable", "reasonMessage": str(exc), **provider_meta})
            except Exception:
                pass
        elif transition_state == "verifying":
            try:
                provider_meta = _build_provider_meta(provider_requested, provider_used, fallback_used, fallback_reason, uniswap_route_type)
                _post_trade_status(args.intent, "verifying", "failed", {"reasonCode": "verification_timeout", "reasonMessage": str(exc), **provider_meta})
            except Exception:
                pass
        return fail(
            "trade_execute_failed",
            str(exc),
            "Verify approval state, wallet setup, and local chain connectivity.",
            {
                "tradeId": args.intent,
                "chain": args.chain,
                "providerRequested": provider_requested,
                "providerUsed": provider_used,
                "fallbackUsed": fallback_used,
                "fallbackReason": fallback_reason,
                "routeKind": uniswap_route_type,
            },
            exit_code=1,
        )
    except Exception as exc:
        return fail(
            "trade_execute_failed",
            str(exc),
            "Inspect runtime trade execute path and retry.",
            {
                "tradeId": args.intent,
                "chain": args.chain,
                "providerRequested": provider_requested,
                "providerUsed": provider_used,
                "fallbackUsed": fallback_used,
                "fallbackReason": fallback_reason,
                "routeKind": uniswap_route_type,
            },
            exit_code=1,
        )


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


def cmd_tracked_list(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    try:
        chain = str(args.chain).strip()
        path = f"/agent/tracked-agents?chainKey={urllib.parse.quote(chain)}"
        status_code, body = _api_request("GET", path)
        if status_code < 200 or status_code >= 300:
            return fail(
                str(body.get("code", "tracked_list_failed")),
                str(body.get("message", f"tracked agents read failed ({status_code})")),
                str(body.get("actionHint", "Verify API auth and tracked-agents availability, then retry.")),
                _api_error_details(status_code, body, path, chain=chain),
                exit_code=1,
            )
        items = body.get("items")
        if not isinstance(items, list):
            items = []
        return ok("Tracked agents loaded.", chain=chain, count=len(items), items=[item for item in items if isinstance(item, dict)])
    except WalletStoreError as exc:
        return fail("tracked_list_failed", str(exc), "Verify API env/auth and retry.", {"chain": args.chain}, exit_code=1)
    except Exception as exc:
        return fail("tracked_list_failed", str(exc), "Inspect runtime tracked-agents path and retry.", {"chain": args.chain}, exit_code=1)


def cmd_tracked_trades(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    try:
        chain = str(args.chain).strip()
        limit_raw = str(args.limit).strip()
        if not re.fullmatch(r"[0-9]+", limit_raw):
            return fail("invalid_input", "limit must be an integer.", "Use --limit <1-100>.", {"limit": args.limit}, exit_code=2)
        limit = int(limit_raw)
        if limit < 1 or limit > 100:
            return fail("invalid_input", "limit must be between 1 and 100.", "Use --limit <1-100>.", {"limit": limit}, exit_code=2)

        path = f"/agent/tracked-trades?chainKey={urllib.parse.quote(chain)}&limit={limit}"
        tracked_agent_id = str(args.agent or "").strip()
        if tracked_agent_id:
            path += f"&trackedAgentId={urllib.parse.quote(tracked_agent_id)}"

        status_code, body = _api_request("GET", path)
        if status_code < 200 or status_code >= 300:
            return fail(
                str(body.get("code", "tracked_trades_failed")),
                str(body.get("message", f"tracked trades read failed ({status_code})")),
                str(body.get("actionHint", "Verify API auth and tracked-trades availability, then retry.")),
                _api_error_details(status_code, body, path, chain=chain),
                exit_code=1,
            )
        items = body.get("items")
        if not isinstance(items, list):
            items = []
        return ok("Tracked trades loaded.", chain=chain, count=len(items), items=[item for item in items if isinstance(item, dict)])
    except WalletStoreError as exc:
        return fail("tracked_trades_failed", str(exc), "Verify API env/auth and retry.", {"chain": args.chain}, exit_code=1)
    except Exception as exc:
        return fail("tracked_trades_failed", str(exc), "Inspect runtime tracked-trades path and retry.", {"chain": args.chain}, exit_code=1)


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
        wallets: list[dict[str, str]] = [{"chainKey": args.chain, "address": wallet_address}]
        seen_chains = {str(args.chain).strip().lower()}
        try:
            state = load_wallet_store()
            chain_map = state.get("chains")
            chain_keys = sorted(chain_map.keys()) if isinstance(chain_map, dict) else []
            for chain_key in chain_keys:
                key = str(chain_key or "").strip()
                if not key or key.lower() in seen_chains:
                    continue
                if not chain_enabled(key):
                    continue
                try:
                    address = _wallet_address_for_chain(key)
                except WalletStoreError:
                    continue
                wallets.append({"chainKey": key, "address": address})
                seen_chains.add(key.lower())
        except WalletStoreError:
            # Keep primary chain registration usable even when auxiliary bindings are malformed.
            pass

        payload = {
            "schemaVersion": 1,
            "agentId": agent_id,
            "agentName": requested_name,
            "runtimePlatform": _runtime_platform_name(),
            "wallets": wallets,
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
    chain = str(args.chain or "").strip()
    try:
        assert_chain_capability(chain, "faucet")
    except ChainRegistryError as exc:
        return fail("unsupported_chain_capability", str(exc), chain_supported_hint(), {"chain": chain}, exit_code=2)
    try:
        api_key = _resolve_api_key()
        agent_id = _resolve_agent_id(api_key)
        if not agent_id:
            return fail(
                "auth_invalid",
                "Agent id could not be resolved for faucet request.",
                "Set XCLAW_AGENT_ID or use signed agent token format.",
                {"chain": chain},
                exit_code=1,
            )
        payload = {
            "schemaVersion": 1,
            "agentId": agent_id,
            "chainKey": chain,
        }
        requested_assets: list[str] = []
        for asset in list(getattr(args, "asset", []) or []):
            normalized = str(asset or "").strip().lower()
            if normalized in {"native", "wrapped", "stable"} and normalized not in requested_assets:
                requested_assets.append(normalized)
        if requested_assets:
            payload["assets"] = requested_assets
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

            details = _api_error_details(status_code, body, "/agent/faucet/request", chain=chain)
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
            chain=chain,
            amountWei=str(body.get("amountWei", "50000000000000000")),
            txHash=body.get("txHash"),
            to=body.get("to"),
            tokenDrips=token_drips,
            requestedAssets=body.get("requestedAssets"),
            fulfilledAssets=body.get("fulfilledAssets"),
            nativeSymbol=body.get("nativeSymbol"),
            assetPlan=body.get("assetPlan"),
            pending=True,
            recommendedDelaySec=20,
            nextAction="Wait ~1-2 blocks, then run dashboard. Balances may not update immediately after tx submission.",
        )
    except WalletStoreError as exc:
        return fail("faucet_request_failed", str(exc), "Verify API env/auth and retry.", {"chain": chain}, exit_code=1)
    except Exception as exc:
        return fail("faucet_request_failed", str(exc), "Inspect runtime faucet request path and retry.", {"chain": chain}, exit_code=1)


def cmd_faucet_networks(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    try:
        api_key = _resolve_api_key()
        agent_id = _resolve_agent_id(api_key)
        if not agent_id:
            return fail(
                "auth_invalid",
                "Agent id could not be resolved for faucet networks.",
                "Set XCLAW_AGENT_ID or use signed agent token format.",
                exit_code=1,
            )
        status_code, body = _api_request("GET", f"/agent/faucet/networks?agentId={urllib.parse.quote(agent_id)}")
        if status_code < 200 or status_code >= 300:
            return fail(
                str(body.get("code", "api_error")),
                str(body.get("message", f"faucet networks request failed ({status_code})")),
                str(body.get("actionHint", "Retry later or check faucet availability.")),
                _api_error_details(status_code, body, "/agent/faucet/networks"),
                exit_code=1,
            )
        networks = body.get("networks")
        if not isinstance(networks, list):
            networks = []
        return ok("Faucet networks fetched.", agentId=agent_id, count=len(networks), networks=networks)
    except WalletStoreError as exc:
        return fail("faucet_networks_failed", str(exc), "Verify API env/auth and retry.", exit_code=1)
    except Exception as exc:
        return fail("faucet_networks_failed", str(exc), "Inspect runtime faucet networks path and retry.", exit_code=1)


def cmd_chains(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    try:
        rows = []
        for cfg in list_chain_registry(include_disabled=bool(getattr(args, "include_disabled", False))):
            chain_key = str(cfg.get("chainKey") or "").strip()
            native = cfg.get("nativeCurrency") if isinstance(cfg.get("nativeCurrency"), dict) else {}
            rows.append(
                {
                    "chainKey": chain_key,
                    "displayName": cfg.get("displayName") or chain_key,
                    "family": cfg.get("family") or "evm",
                    "enabled": cfg.get("enabled", True) is not False,
                    "uiVisible": cfg.get("uiVisible", True) is not False,
                    "nativeCurrency": {
                        "name": native.get("name") if isinstance(native, dict) else None,
                        "symbol": (native.get("symbol") if isinstance(native, dict) else None) or "ETH",
                        "decimals": (native.get("decimals") if isinstance(native, dict) else None) or 18,
                    },
                    "capabilities": {
                        "wallet": chain_capability(chain_key, "wallet"),
                        "trade": chain_capability(chain_key, "trade"),
                        "liquidity": chain_capability(chain_key, "liquidity"),
                        "limitOrders": chain_capability(chain_key, "limitOrders"),
                        "x402": chain_capability(chain_key, "x402"),
                        "faucet": chain_capability(chain_key, "faucet"),
                        "deposits": chain_capability(chain_key, "deposits"),
                    },
                }
            )
        return ok("Chains loaded.", chains=rows, count=len(rows))
    except ChainRegistryError as exc:
        return fail("chain_registry_error", str(exc), "Verify config/chains/*.json and retry.", exit_code=1)


def cmd_default_chain_get(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    chain, source = _resolve_runtime_default_chain()
    stored = _read_runtime_default_chain()
    return ok(
        "Runtime default chain loaded.",
        chainKey=chain,
        source=source,
        persistedChainKey=stored,
    )


def cmd_default_chain_set(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    chain = str(args.chain or "").strip()
    if not chain:
        return fail("invalid_input", "chain is required.", "Provide --chain <chainKey> and retry.", exit_code=2)
    try:
        _set_runtime_default_chain(chain)
    except ChainRegistryError as exc:
        return fail("unsupported_chain", str(exc), chain_supported_hint(), {"chain": chain}, exit_code=2)
    return ok("Runtime default chain updated.", chainKey=chain, source="state")


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


def _assert_transfer_balance_preconditions(
    *,
    chain: str,
    transfer_type: str,
    wallet_address: str,
    amount_wei: str,
    token_address: str | None,
    token_symbol: str,
    token_decimals: int | None,
) -> None:
    amount_int = int(amount_wei)
    is_solana = _is_solana_chain(chain)
    if is_solana:
        rpc_url = _chain_rpc_url(chain)
        if transfer_type == "native":
            balance_lamports = int(solana_get_balance_lamports(rpc_url, wallet_address))
            if balance_lamports < amount_int:
                native_symbol = _native_symbol_for_chain(chain)
                raise WalletStoreError(
                    f"Insufficient {native_symbol} balance for transfer: "
                    f"have {_format_units_pretty(balance_lamports, 9)} {native_symbol}, "
                    f"need {_format_units_pretty(amount_int, 9)} {native_symbol} "
                    f"(wallet {wallet_address})."
                )
            return
        if transfer_type == "token":
            if not token_address or not is_solana_address(token_address):
                raise WalletStoreError("Transfer token address is invalid.")
            tokens, _ = solana_get_token_balances(rpc_url, wallet_address)
            match = next((row for row in tokens if str(row.get("token") or "") == token_address), None)
            balance_units = int(str((match or {}).get("balanceWei") or "0"))
            decimals = int(token_decimals if token_decimals is not None else int((match or {}).get("decimals") or 0))
            symbol = token_symbol.strip() or "TOKEN"
            if balance_units < amount_int:
                raise WalletStoreError(
                    f"Insufficient {symbol} balance for transfer: "
                    f"have {_format_units_pretty(balance_units, decimals)} {symbol}, "
                    f"need {_format_units_pretty(amount_int, decimals)} {symbol} "
                    f"(wallet {wallet_address}, token {token_address})."
                )
            return

    if transfer_type == "native":
        native_balance_wei = int(_fetch_native_balance_wei(chain, wallet_address))
        if native_balance_wei < amount_int:
            native_symbol = _native_symbol_for_chain(chain)
            raise WalletStoreError(
                f"Insufficient {native_symbol} balance for transfer: "
                f"have {_format_units_pretty(native_balance_wei, 18)} {native_symbol}, "
                f"need {_format_units_pretty(amount_int, 18)} {native_symbol} "
                f"(wallet {wallet_address})."
            )
        return

    if transfer_type != "token":
        return
    if not token_address or not is_hex_address(token_address):
        raise WalletStoreError("Transfer token address is invalid.")

    token_balance_wei = int(_fetch_token_balance_wei(chain, wallet_address, token_address))
    decimals = int(token_decimals) if token_decimals is not None else 18
    symbol = token_symbol.strip() or "TOKEN"
    if token_balance_wei < amount_int:
        raise WalletStoreError(
            f"Insufficient {symbol} balance for transfer: "
            f"have {_format_units_pretty(token_balance_wei, decimals)} {symbol}, "
            f"need {_format_units_pretty(amount_int, decimals)} {symbol} "
            f"(wallet {wallet_address}, token {token_address})."
        )


def _canonical_token_map(chain: str) -> dict[str, str]:
    cfg = _load_chain_config(chain)
    tokens = cfg.get("canonicalTokens")
    if not isinstance(tokens, dict):
        return {}
    is_solana = _is_solana_chain(chain)
    out: dict[str, str] = {}
    for symbol, address in tokens.items():
        valid_address = is_solana_address(address) if is_solana else is_hex_address(address)
        if isinstance(symbol, str) and isinstance(address, str) and valid_address:
            out[symbol] = address
    return out


def _chain_env_suffix(chain: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "_", str(chain or "").strip()).upper()


def _http_get_json_object(url: str, *, timeout_sec: float = 20.0) -> dict[str, Any]:
    req = urllib.request.Request(
        url=url,
        method="GET",
        headers={
            "Accept": "application/json",
            "User-Agent": "xclaw-agent-runtime/1.0 (+https://xclaw.trade/skill.md)",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8") if exc.fp else ""
        raise WalletStoreError(f"HTTP {exc.code} for {url}: {body or exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise WalletStoreError(f"HTTP request failed for {url}: {exc.reason}") from exc
    try:
        parsed = json.loads(body) if body else {}
    except Exception as exc:
        raise WalletStoreError(f"Non-JSON response from {url}.") from exc
    if not isinstance(parsed, dict):
        raise WalletStoreError(f"JSON response from {url} is not an object.")
    return parsed


def _canonical_token_address_aliases(chain: str) -> dict[str, str]:
    cfg = _load_chain_config(chain)
    aliases = cfg.get("canonicalTokenAddressAliases")
    if not isinstance(aliases, dict):
        return {}
    out: dict[str, str] = {}
    for alias, canonical in aliases.items():
        if (
            isinstance(alias, str)
            and isinstance(canonical, str)
            and is_hex_address(alias)
            and is_hex_address(canonical)
        ):
            out[alias.lower()] = canonical
    return out


def _native_symbol_for_chain(chain: str) -> str:
    cfg = _load_chain_config(chain)
    native = cfg.get("nativeCurrency")
    if isinstance(native, dict):
        symbol = native.get("symbol")
        if isinstance(symbol, str) and symbol.strip():
            return symbol.strip().upper()
    return "ETH"


def _native_decimals_for_chain(chain: str) -> int:
    cfg = _load_chain_config(chain)
    native = cfg.get("nativeCurrency")
    if isinstance(native, dict):
        decimals = native.get("decimals")
        if isinstance(decimals, int) and decimals > 0:
            return decimals
    return 18


_WRAPPED_NATIVE_ALIAS_BY_NATIVE_SYMBOL: dict[str, tuple[str, ...]] = {
    "ETH": ("WETH",),
    "HBAR": ("WHBAR",),
    "KITE": ("WKITE",),
    "BNB": ("WBNB",),
    "AVAX": ("WAVAX",),
    "POL": ("WPOL",),
    "MATIC": ("WMATIC", "WPOL"),
    "MON": ("WMON",),
}


def _suggest_wrapped_native_symbols(chain: str) -> list[str]:
    native_symbol = _native_symbol_for_chain(chain).strip().upper()
    candidates: list[str] = []
    if native_symbol:
        if native_symbol.startswith("W") and len(native_symbol) > 1:
            candidates.append(native_symbol)
        else:
            candidates.append(f"W{native_symbol}")
        aliases = _WRAPPED_NATIVE_ALIAS_BY_NATIVE_SYMBOL.get(native_symbol, ())
        for alias in aliases:
            if alias not in candidates:
                candidates.append(alias)
    return candidates


def _resolve_wrapped_native_target(chain: str) -> tuple[str | None, str, str]:
    cfg = _load_chain_config(chain)
    contracts = cfg.get("coreContracts")
    if isinstance(contracts, dict) and "wrappedNativeHelper" in contracts:
        helper = contracts.get("wrappedNativeHelper")
        if not isinstance(helper, str) or not is_hex_address(helper):
            raise WalletStoreError(f"Chain config for '{chain}' has invalid coreContracts.wrappedNativeHelper.")
        for symbol in _suggest_wrapped_native_symbols(chain):
            token = _canonical_token_map(chain).get(symbol)
            if isinstance(token, str) and is_hex_address(token):
                return helper, token, symbol
        raise WalletStoreError(
            f"Chain config for '{chain}' has no canonical wrapped native token for native symbol '{_native_symbol_for_chain(chain)}'."
        )

    for symbol in _suggest_wrapped_native_symbols(chain):
        token = _canonical_token_map(chain).get(symbol)
        if isinstance(token, str) and is_hex_address(token):
            return None, token, symbol
    raise WalletStoreError(
        f"Chain config for '{chain}' has no canonical wrapped native token for native symbol '{_native_symbol_for_chain(chain)}'."
    )


def _fetch_wallet_holdings(chain: str) -> dict[str, Any]:
    store = load_wallet_store()
    _, wallet = _chain_wallet(store, chain)
    if wallet is None:
        raise WalletStoreError(f"No wallet configured for chain '{chain}'.")
    _validate_wallet_entry_shape(wallet)
    address = str(wallet.get("address"))
    if _is_solana_chain(chain):
        rpc_url = _chain_rpc_url(chain)
        native_balance_lamports = int(solana_get_balance_lamports(rpc_url, address))
        tokens, token_errors = solana_get_token_balances(rpc_url, address)
        return {
            "address": address,
            "native": {
                "symbol": _native_symbol_for_chain(chain),
                "balanceWei": str(native_balance_lamports),
                "balance": _format_units(native_balance_lamports, 9),
                "balancePretty": _format_units_pretty(native_balance_lamports, 9),
                "decimals": 9,
            },
            "tokens": tokens,
            "tokenErrors": token_errors,
        }
    native_balance_wei = _fetch_native_balance_wei(chain, address)
    native_balance_eth = _format_units(int(native_balance_wei), 18)
    token_map = _canonical_token_map(chain)
    token_balances: list[dict[str, Any]] = []
    token_errors: list[dict[str, Any]] = []
    for symbol, token_address in token_map.items():
        try:
            balance_wei = _fetch_token_balance_wei(chain, address, token_address)
            balance_int = int(balance_wei)
            if balance_int <= 0:
                continue
            meta = _fetch_erc20_metadata(chain, token_address)
            decimals = int(meta.get("decimals", 18))
            token_balances.append(
                {
                    "symbol": str(meta.get("symbol") or symbol),
                    "token": token_address,
                    "balanceWei": balance_wei,
                    "balance": _format_units(balance_int, decimals),
                    "balancePretty": _format_units_pretty(balance_int, decimals),
                    "decimals": decimals,
                }
            )
        except Exception as exc:
            token_errors.append({"symbol": symbol, "token": token_address, "message": str(exc)})
    known_tokens = {str(item.get("token") or "").lower() for item in token_balances if isinstance(item, dict)}
    for row in _tracked_tokens_for_chain(chain):
        token_address = str(row.get("token") or "").strip().lower()
        if not is_hex_address(token_address) or token_address in known_tokens:
            continue
        try:
            balance_wei = _fetch_token_balance_wei(chain, address, token_address)
            balance_int = int(balance_wei)
            if balance_int <= 0:
                continue
            meta = _fetch_erc20_metadata(chain, token_address)
            decimals = int(meta.get("decimals", row.get("decimals") or 18))
            symbol = str(meta.get("symbol") or row.get("symbol") or token_address)
            token_balances.append(
                {
                    "symbol": symbol,
                    "token": token_address,
                    "balanceWei": balance_wei,
                    "balance": _format_units(balance_int, decimals),
                    "balancePretty": _format_units_pretty(balance_int, decimals),
                    "decimals": decimals,
                }
            )
            known_tokens.add(token_address)
        except Exception as exc:
            token_errors.append({"source": "tracked", "token": token_address, "message": str(exc)})
    return {
        "address": address,
        "native": {
            "symbol": _native_symbol_for_chain(chain),
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
        tracked_agents: list[dict[str, Any]] = []
        tracked_recent_trades: list[dict[str, Any]] = []

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

        tracked_agents_status, tracked_agents_body = _api_request("GET", f"/agent/tracked-agents?chainKey={chain_escaped}")
        if 200 <= tracked_agents_status < 300:
            items = tracked_agents_body.get("items")
            if isinstance(items, list):
                tracked_agents = [item for item in items if isinstance(item, dict)]
        else:
            section_errors.append(
                {
                    "section": "trackedAgents",
                    "code": str(tracked_agents_body.get("code", "api_error")),
                    "message": str(tracked_agents_body.get("message", f"tracked agents read failed ({tracked_agents_status})")),
                    "requestId": str(tracked_agents_body.get("requestId") or ""),
                }
            )

        tracked_trades_status, tracked_trades_body = _api_request("GET", f"/agent/tracked-trades?chainKey={chain_escaped}&limit=20")
        if 200 <= tracked_trades_status < 300:
            items = tracked_trades_body.get("items")
            if isinstance(items, list):
                tracked_recent_trades = [item for item in items if isinstance(item, dict)]
        else:
            section_errors.append(
                {
                    "section": "trackedRecentTrades",
                    "code": str(tracked_trades_body.get("code", "api_error")),
                    "message": str(tracked_trades_body.get("message", f"tracked trades read failed ({tracked_trades_status})")),
                    "requestId": str(tracked_trades_body.get("requestId") or ""),
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
            trackedAgents=tracked_agents,
            trackedRecentTrades=tracked_recent_trades,
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
        chain=chain,
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
        chain=chain,
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
                "Use network mode (`real`) on a configured chain.",
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
                key_scheme = str(wallet.get("keyScheme") or "evm_secp256k1").strip().lower() or "evm_secp256k1"
                if key_scheme == "solana_ed25519":
                    derived = str(wallet.get("address") or "")
                    if not is_solana_address(derived):
                        raise WalletStoreError("Wallet encrypted payload does not match stored address.")
                else:
                    derived = _derive_address(plaintext.hex())
                if str(derived).lower() != str(address).lower():
                    raise WalletStoreError("Wallet encrypted payload does not match stored address.")
                integrity_checked = True
        else:
            # Legacy fallback for Slice 03 state shape.
            _, legacy_wallet = ensure_wallet_entry(chain)
            legacy_address = legacy_wallet.get("address")
            if isinstance(legacy_address, str) and (is_hex_address(legacy_address) or is_solana_address(legacy_address)):
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

    has_cast = cast_exists() if not _is_solana_chain(chain) else True
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
        chain = args.chain
        passphrase = _create_import_passphrase(chain)
        store = load_wallet_store()
        wallet_id, wallet = _chain_wallet(store, chain)
        if wallet_id and wallet:
            return fail(
                "wallet_exists",
                f"Wallet already configured for chain '{chain}'.",
                "Use wallet address/health or wallet remove before creating again.",
                {"chain": chain, "address": wallet.get("address")},
                exit_code=1,
            )

        if _is_solana_chain(chain):
            generated = solana_generate_wallet()
            address = str(generated.get("address") or "")
            private_key = str(generated.get("private_key") or "")
            imported = solana_import_wallet_private_key(private_key)
            secret_bytes = imported["secret_bytes"]
            wallet_id = _new_wallet_id()
            encrypted = _encrypt_secret_bytes(secret_bytes, passphrase)
            store.setdefault("wallets", {})[wallet_id] = {
                "walletId": wallet_id,
                "address": address,
                "createdAt": utc_now(),
                "keyScheme": "solana_ed25519",
                "crypto": encrypted,
            }
            _bind_chain_to_wallet(store, chain, wallet_id)
            save_wallet_store(store)
            set_wallet_entry(chain, {"address": address, "walletId": wallet_id})
            return ok("Wallet created.", chain=chain, address=address, created=True, family="solana")

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
            "keyScheme": "evm_secp256k1",
            "crypto": encrypted,
        }
        store["defaultWalletId"] = wallet_id
        _bind_chain_to_wallet(store, chain, wallet_id)

        save_wallet_store(store)
        set_wallet_entry(chain, {"address": address, "walletId": wallet_id})
        return ok("Wallet created.", chain=chain, address=address, created=True, family="evm")

    except WalletPassphraseError as exc:
        return fail("non_interactive", str(exc), "Set XCLAW_WALLET_PASSPHRASE or run with TTY attached.", {"chain": args.chain}, exit_code=2)
    except ValueError as exc:
        return fail("invalid_input", str(exc), "Provide matching non-empty passphrase values.", {"chain": args.chain}, exit_code=2)
    except WalletSecurityError as exc:
        return fail("unsafe_permissions", str(exc), "Restrict permissions to owner-only (0700/0600) and retry.", {"chain": args.chain}, exit_code=1)
    except WalletStoreError as exc:
        return fail("wallet_store_invalid", str(exc), "Repair wallet store metadata and retry.", {"chain": args.chain}, exit_code=1)
    except SolanaRuntimeError as exc:
        return fail(exc.code, str(exc), "Install Solana runtime dependencies and verify RPC configuration.", {"chain": args.chain, **exc.details}, exit_code=1)
    except Exception as exc:
        return fail("wallet_create_failed", str(exc), "Inspect runtime wallet dependencies/configuration and retry.", {"chain": args.chain}, exit_code=1)


def cmd_wallet_import(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk

    try:
        chain = args.chain
        private_key_input = _import_private_key_input(chain)
        passphrase = _create_import_passphrase(chain)

        store = load_wallet_store()
        existing_id, existing_wallet = _chain_wallet(store, chain)
        if existing_id and existing_wallet:
            return fail(
                "wallet_exists",
                f"Wallet already configured for chain '{chain}'.",
                "Use wallet remove first if you want to replace the chain binding.",
                {"chain": chain, "address": existing_wallet.get("address")},
                exit_code=1,
            )

        if _is_solana_chain(chain):
            imported = solana_import_wallet_private_key(private_key_input)
            address = str(imported.get("address") or "")
            secret_bytes = imported["secret_bytes"]
            wallet_id = _new_wallet_id()
            encrypted = _encrypt_secret_bytes(secret_bytes, passphrase)
            store.setdefault("wallets", {})[wallet_id] = {
                "walletId": wallet_id,
                "address": address,
                "createdAt": utc_now(),
                "keyScheme": "solana_ed25519",
                "crypto": encrypted,
            }
            _bind_chain_to_wallet(store, chain, wallet_id)
            save_wallet_store(store)
            set_wallet_entry(chain, {"address": address, "walletId": wallet_id})
            return ok("Wallet imported.", chain=chain, address=address, imported=True, family="solana")

        private_key_hex = _normalize_private_key_hex(private_key_input)
        if private_key_hex is None:
            return fail(
                "invalid_input",
                "Private key must be 32-byte hex (64 chars, optional 0x prefix).",
                "Provide a valid EVM private key hex string.",
                {"chain": chain},
                exit_code=2,
            )
        address = _derive_address(private_key_hex)

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
            "keyScheme": "evm_secp256k1",
            "crypto": encrypted,
        }
        store["defaultWalletId"] = wallet_id
        _bind_chain_to_wallet(store, chain, wallet_id)

        save_wallet_store(store)
        set_wallet_entry(chain, {"address": address, "walletId": wallet_id})
        return ok("Wallet imported.", chain=chain, address=address, imported=True, family="evm")

    except WalletPassphraseError as exc:
        return fail("non_interactive", str(exc), "Set XCLAW_WALLET_PASSPHRASE/XCLAW_WALLET_IMPORT_PRIVATE_KEY or run with TTY attached.", {"chain": args.chain}, exit_code=2)
    except ValueError as exc:
        return fail("invalid_input", str(exc), "Provide matching non-empty passphrase values.", {"chain": args.chain}, exit_code=2)
    except WalletSecurityError as exc:
        return fail("unsafe_permissions", str(exc), "Restrict permissions to owner-only (0700/0600) and retry.", {"chain": args.chain}, exit_code=1)
    except WalletStoreError as exc:
        return fail("wallet_store_invalid", str(exc), "Repair wallet store metadata and retry.", {"chain": args.chain}, exit_code=1)
    except SolanaRuntimeError as exc:
        return fail(exc.code, str(exc), "Provide a valid Solana private key and retry.", {"chain": args.chain, **exc.details}, exit_code=2 if exc.code == "invalid_input" else 1)
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
            if isinstance(address, str) and (is_hex_address(address) or is_solana_address(address)):
                return ok("Wallet address fetched.", chain=chain, address=address)

    except (WalletStoreError, WalletSecurityError) as exc:
        return fail("wallet_store_invalid", str(exc), "Repair wallet store metadata and retry.", {"chain": chain}, exit_code=1)

    _, legacy_wallet = ensure_wallet_entry(chain)
    addr = legacy_wallet.get("address")
    if not isinstance(addr, str) or (not is_hex_address(addr) and not is_solana_address(addr)):
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
        key_scheme = str(wallet.get("keyScheme") or "evm_secp256k1").strip().lower() or "evm_secp256k1"
        if key_scheme == "solana_ed25519" or _is_solana_chain(chain):
            signature = solana_sign_message(private_key_bytes, args.message)
            scheme = "solana_ed25519"
        else:
            signature = _cast_sign_message(private_key_bytes.hex(), args.message)
            scheme = "eip191_personal_sign"
        return ok(
            "Challenge signed.",
            chain=chain,
            address=wallet.get("address"),
            signature=signature,
            scheme=scheme,
            challengeFormat=CHALLENGE_FORMAT_VERSION,
        )

    except WalletPassphraseError as exc:
        return fail("non_interactive", str(exc), "Set XCLAW_WALLET_PASSPHRASE or run with TTY attached.", {"chain": chain}, exit_code=2)
    except WalletSecurityError as exc:
        return fail("unsafe_permissions", str(exc), "Restrict permissions to owner-only (0700/0600) and retry.", {"chain": chain}, exit_code=1)
    except WalletStoreError as exc:
        msg = str(exc)
        if "Unsupported token symbol" in msg:
            return fail(
                "invalid_input",
                msg,
                "Use a canonical token symbol (for example USDC) or 0x token address.",
                {"chain": chain, "token": str(args.token or "")},
                exit_code=2,
            )
        if "Missing dependency: cast" in msg:
            return fail(
                "missing_dependency",
                msg,
                "Install Foundry and ensure `cast` is on PATH.",
                {"dependency": "cast"},
                exit_code=1,
            )
        return fail("sign_failed", msg, "Verify wallet passphrase and cast runtime, then retry.", {"chain": chain}, exit_code=1)
    except SolanaRuntimeError as exc:
        return fail(exc.code, str(exc), "Install Solana runtime dependencies and retry.", {"chain": chain, **exc.details}, exit_code=1)
    except Exception as exc:
        return fail("sign_failed", str(exc), "Inspect runtime wallet/signing configuration and retry.", {"chain": chain}, exit_code=1)


def cmd_wallet_send(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    if _is_solana_chain(args.chain):
        if not is_solana_address(args.to):
            return fail("invalid_input", "Invalid recipient address format.", "Use a valid Solana base58 address.", {"to": args.to}, exit_code=2)
    elif not is_hex_address(args.to):
        return fail("invalid_input", "Invalid recipient address format.", "Use 0x-prefixed 20-byte hex address.", {"to": args.to}, exit_code=2)
    if not re.fullmatch(r"[0-9]+", args.amount_wei):
        return fail("invalid_input", "Invalid amount-wei format.", "Use base-unit integer string.", {"amountWei": args.amount_wei}, exit_code=2)

    chain = args.chain
    amount_wei = int(args.amount_wei)
    try:
        _enforce_spend_preconditions(chain, amount_wei)
        outbound_eval = _evaluate_outbound_transfer_policy(chain, args.to)

        approval_required, transfer_policy = _transfer_requires_approval(chain, "native", None)
        native_symbol = _native_symbol_for_chain(chain)
        amount_human, amount_unit = _transfer_amount_display(str(args.amount_wei), "native", native_symbol, _native_decimals_for_chain(chain))
        amount_display = f"{amount_human} {amount_unit}"
        if not bool(outbound_eval.get("allowed")):
            approval_required = True
        to_address_store = args.to if _is_solana_chain(chain) else args.to.lower()
        approval_id = _make_transfer_approval_id()
        flow = {
            "approvalId": approval_id,
            "chainKey": chain,
            "status": "approval_pending" if approval_required else "approved",
            "transferType": "native",
            "tokenAddress": None,
            "tokenSymbol": native_symbol,
            "tokenDecimals": _native_decimals_for_chain(chain),
            "toAddress": to_address_store,
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
        try:
            _mirror_transfer_approval(flow, require_delivery=approval_required)
        except WalletStoreError as exc:
            _remove_pending_transfer_flow(approval_id)
            return fail(
                "approval_sync_failed",
                "Transfer approval could not be synced to management inbox.",
                "Retry once. If this persists, run auth-recover and verify API connectivity before retrying send.",
                {"approvalId": approval_id, "chain": chain, "error": str(exc)},
                exit_code=1,
            )

        if approval_required:
            try:
                _maybe_send_telegram_transfer_approval_prompt(flow)
            except Exception:
                pass
            queued_message = (
                "Approval required (transfer)\n\n"
                "Request: Send native token\n"
                f"Amount: {amount_display} ({args.amount_wei} base units)\n"
                f"To: `{to_address_store}`\n"
                f"Chain: `{chain}`\n"
                f"Approval ID: `{approval_id}`\n"
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


def cmd_wallet_track_token(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    chain = str(args.chain or "").strip()
    token = str(args.token or "").strip().lower()
    valid_token = is_solana_address(token) if _is_solana_chain(chain) else is_hex_address(token)
    if not valid_token:
        return fail(
            "invalid_token_address",
            "Invalid token address format.",
            "Use a chain-valid token address.",
            {"chain": chain, "token": token},
            exit_code=2,
        )
    try:
        _sync_tracked_tokens_from_remote(chain)
        symbol: str | None = None
        name: str | None = None
        decimals: int | None = None
        if not _is_solana_chain(chain):
            try:
                meta = _fetch_erc20_metadata(chain, token)
                symbol = str(meta.get("symbol") or "").strip() or None
                name = str(meta.get("name") or "").strip() or None
                decimals = int(meta.get("decimals", 18))
            except Exception:
                pass
        row = _upsert_tracked_token_local(chain, token, symbol=symbol, name=name, decimals=decimals)
        mirror_synced = _mirror_tracked_tokens(chain)
        return ok(
            "Tracked token registered.",
            chain=chain,
            token=row.get("token"),
            symbol=row.get("symbol"),
            name=row.get("name"),
            decimals=row.get("decimals"),
            created=bool(row.get("created")),
            trackedCount=len(_get_tracked_token_addresses(chain)),
            mirrorSynced=mirror_synced,
        )
    except TokenResolutionError as exc:
        return fail(exc.code, str(exc), "Fix token input and retry.", exc.details, exit_code=2)
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
        return fail("track_token_failed", msg, "Verify wallet and chain configuration, then retry.", {"chain": chain}, exit_code=1)
    except Exception as exc:
        return fail("track_token_failed", str(exc), "Inspect token tracking configuration and retry.", {"chain": chain}, exit_code=1)


def cmd_wallet_untrack_token(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    chain = str(args.chain or "").strip()
    token = str(args.token or "").strip().lower()
    valid_token = is_solana_address(token) if _is_solana_chain(chain) else is_hex_address(token)
    if not valid_token:
        return fail(
            "invalid_token_address",
            "Invalid token address format.",
            "Use a chain-valid token address.",
            {"chain": chain, "token": token},
            exit_code=2,
        )
    try:
        _sync_tracked_tokens_from_remote(chain)
        removed = _remove_tracked_token_local(chain, token)
        if not removed:
            return fail(
                "token_not_tracked",
                "Token is not currently tracked for this chain.",
                "Track the token first or verify the token address and chain.",
                {"chain": chain, "token": token},
                exit_code=1,
            )
        mirror_synced = _mirror_tracked_tokens(chain)
        return ok(
            "Tracked token removed.",
            chain=chain,
            token=token,
            trackedCount=len(_get_tracked_token_addresses(chain)),
            mirrorSynced=mirror_synced,
        )
    except TokenResolutionError as exc:
        return fail(exc.code, str(exc), "Fix token input and retry.", exc.details, exit_code=2)
    except Exception as exc:
        return fail("untrack_token_failed", str(exc), "Inspect token tracking configuration and retry.", {"chain": chain}, exit_code=1)


def cmd_wallet_tracked_tokens(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    chain = str(args.chain or "").strip()
    synced = _sync_tracked_tokens_from_remote(chain)
    items = _tracked_tokens_for_chain(chain)
    return ok(
        "Tracked tokens fetched.",
        chain=chain,
        count=len(items),
        items=items,
        remoteSync=bool(synced),
    )


def cmd_wallet_send_token(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    if _is_solana_chain(args.chain):
        if not is_solana_address(args.to):
            return fail("invalid_input", "Invalid recipient address format.", "Use a valid Solana base58 address.", {"to": args.to}, exit_code=2)
    elif not is_hex_address(args.to):
        return fail("invalid_input", "Invalid recipient address format.", "Use 0x-prefixed 20-byte hex address.", {"to": args.to}, exit_code=2)
    if not re.fullmatch(r"[0-9]+", args.amount_wei):
        return fail("invalid_input", "Invalid amount-wei format.", "Use base-unit integer string.", {"amountWei": args.amount_wei}, exit_code=2)

    chain = args.chain
    amount_wei = int(args.amount_wei)
    try:
        token_input = str(args.token or "").strip()
        token_address = _resolve_token_address(chain, token_input)
        token_symbol = str(token_input or "").strip().upper() or "TOKEN"
        token_decimals = 18
        if _is_solana_chain(chain):
            token_decimals = 9
        else:
            token_meta = _fetch_erc20_metadata(chain, token_address)
            token_symbol = str(token_meta.get("symbol") or "").strip() or token_symbol
            try:
                token_decimals = int(token_meta.get("decimals", 18))
            except Exception:
                token_decimals = 18
        if not _is_solana_chain(chain) and not is_hex_address(token_input):
            # Guard against common natural-language mistakes where "10 USDC" is sent as amount_wei=10.
            min_symbol_wei = 10 ** max(token_decimals - 6, 0)
            if amount_wei < min_symbol_wei:
                one_token_wei = 10**max(token_decimals, 0)
                return fail(
                    "invalid_input",
                    "Amount is too small for symbol-based transfer and looks like a base-unit mistake.",
                    "Use base-unit integer amount. Example: 10 tokens => 10 * (10^decimals) wei. "
                    f"For {token_symbol}, 1 token = {one_token_wei} wei.",
                    {
                        "chain": chain,
                        "token": token_input,
                        "tokenAddress": token_address,
                        "tokenSymbol": token_symbol,
                        "tokenDecimals": token_decimals,
                        "amountWei": str(amount_wei),
                        "minSuggestedWeiForSymbolInput": str(min_symbol_wei),
                    },
                    exit_code=2,
                )
        _enforce_spend_preconditions(chain, amount_wei)
        outbound_eval = _evaluate_outbound_transfer_policy(chain, args.to)

        amount_human, amount_unit = _transfer_amount_display(str(args.amount_wei), "token", token_symbol, token_decimals)
        amount_display = f"{amount_human} {amount_unit}"
        approval_required, transfer_policy = _transfer_requires_approval(chain, "token", token_address)
        if not bool(outbound_eval.get("allowed")):
            approval_required = True
        token_address_store = token_address if _is_solana_chain(chain) else token_address.lower()
        to_address_store = args.to if _is_solana_chain(chain) else args.to.lower()
        approval_id = _make_transfer_approval_id()
        flow = {
            "approvalId": approval_id,
            "chainKey": chain,
            "status": "approval_pending" if approval_required else "approved",
            "transferType": "token",
            "tokenAddress": token_address_store,
            "tokenSymbol": token_symbol,
            "tokenDecimals": token_decimals,
            "toAddress": to_address_store,
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
        try:
            _mirror_transfer_approval(flow, require_delivery=approval_required)
        except WalletStoreError as exc:
            _remove_pending_transfer_flow(approval_id)
            return fail(
                "approval_sync_failed",
                "Transfer approval could not be synced to management inbox.",
                "Retry once. If this persists, run auth-recover and verify API connectivity before retrying send.",
                {"approvalId": approval_id, "chain": chain, "error": str(exc)},
                exit_code=1,
            )

        if approval_required:
            try:
                _maybe_send_telegram_transfer_approval_prompt(flow)
            except Exception:
                pass
            queued_message = (
                "Approval required (transfer)\n\n"
                "Request: Send token\n"
                f"Token: {token_symbol} ({token_address_store})\n"
                f"Amount: {amount_display} ({args.amount_wei} wei)\n"
                f"To: `{to_address_store}`\n"
                f"Chain: `{chain}`\n"
                f"Approval ID: `{approval_id}`\n"
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
    except TokenResolutionError as exc:
        return fail(exc.code, str(exc), "Use a token address or a unique tracked symbol.", exc.details, exit_code=2)
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
        holdings = _fetch_wallet_holdings(chain)
        native = holdings.get("native") if isinstance(holdings, dict) else None
        if not isinstance(native, dict):
            raise WalletStoreError("Wallet holdings payload missing native balance.")
        balance_wei = str(native.get("balanceWei") or "0")
        parsed = _parse_uint_text(balance_wei)
        native_decimals = int(native.get("decimals", _native_decimals_for_chain(chain)) or _native_decimals_for_chain(chain))
        tokens = holdings.get("tokens", [])
        if not isinstance(tokens, list):
            tokens = []
        token_errors = holdings.get("tokenErrors", [])
        if not isinstance(token_errors, list):
            token_errors = []
        return ok(
            "Wallet balance fetched.",
            chain=chain,
            address=address,
            balanceWei=str(parsed),
            balanceEth=_format_units(int(parsed), native_decimals),
            decimals=native_decimals,
            symbol=_native_symbol_for_chain(chain),
            tokens=tokens,
            tokenErrors=token_errors,
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
    chain = args.chain
    if _is_solana_chain(chain):
        if not is_solana_address(args.token):
            return fail("invalid_input", "Invalid token address format.", "Use a Solana mint address.", {"token": args.token}, exit_code=2)
    elif not is_hex_address(args.token):
        return fail("invalid_input", "Invalid token address format.", "Use 0x-prefixed 20-byte hex address.", {"token": args.token}, exit_code=2)
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
        if _is_solana_chain(chain):
            holdings = _fetch_wallet_holdings(chain)
            tokens = holdings.get("tokens", [])
            if not isinstance(tokens, list):
                tokens = []
            row = next((item for item in tokens if str((item or {}).get("token") or "").strip().lower() == str(args.token).strip().lower()), None)
            if not isinstance(row, dict):
                return ok(
                    "Wallet token balance fetched.",
                    chain=chain,
                    address=address,
                    token=args.token,
                    balanceWei="0",
                    balance="0",
                    decimals=0,
                    symbol=None,
                )
            decimals = int(row.get("decimals", 0))
            return ok(
                "Wallet token balance fetched.",
                chain=chain,
                address=address,
                token=args.token,
                balanceWei=str(row.get("balanceWei") or "0"),
                balance=str(row.get("balance") or "0"),
                decimals=decimals,
                symbol=row.get("symbol"),
            )
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


def cmd_wallet_wrap_native(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    chain = args.chain
    if _is_solana_chain(chain):
        return fail(
            "unsupported_chain_capability",
            "wallet wrap-native is EVM-only.",
            "Use spot trade on Solana for SOL -> wrapped SOL routing.",
            {"chain": chain},
            exit_code=2,
        )
    native_symbol = _native_symbol_for_chain(chain)
    wrapped_candidates = _suggest_wrapped_native_symbols(chain)
    wrapped_symbol_hint = wrapped_candidates[0] if wrapped_candidates else "wrapped native token"
    try:
        amount_in_units, amount_mode = _parse_amount_in_units(str(args.amount), 18)
        amount_in_int = int(amount_in_units)
        if amount_in_int <= 0:
            return fail("invalid_amount", "Amount must be positive.", "Provide an amount > 0.", {"amount": str(args.amount)}, exit_code=2)

        store = load_wallet_store()
        wallet_address, private_key_hex = _execution_wallet(store, chain)
        helper, wrapped_token, wrapped_symbol_hint = _resolve_wrapped_native_target(chain)
        cast_bin = _require_cast_bin()
        rpc_url = _chain_rpc_url(chain)

        wrapped_before = int(_fetch_token_balance_wei(chain, wallet_address, wrapped_token))
        calldata = _cast_calldata("deposit()", [])
        target = helper if isinstance(helper, str) and is_hex_address(helper) else wrapped_token
        tx_hash = _cast_rpc_send_transaction(
            rpc_url,
            {
                "from": wallet_address,
                "to": target,
                "data": calldata,
                "value": amount_in_units,
            },
            private_key_hex,
            chain=chain,
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

        wrapped_after = int(_fetch_token_balance_wei(chain, wallet_address, wrapped_token))
        wrapped_delta = max(0, wrapped_after - wrapped_before)
        wrapped_meta = _fetch_erc20_metadata(chain, wrapped_token)
        wrapped_decimals = int(wrapped_meta.get("decimals", 18))
        wrapped_symbol = str(wrapped_meta.get("symbol") or wrapped_symbol_hint).strip() or wrapped_symbol_hint
        success_message = "Native asset wrapped via official helper contract." if target == helper else "Native asset wrapped via canonical wrapped token contract."
        payload: dict[str, Any] = {
            "chain": chain,
            "address": wallet_address,
            "wrappedToken": wrapped_token,
            "txHash": tx_hash,
            "amountInWei": amount_in_units,
            "amountIn": _format_units(int(amount_in_units), 18),
            "amountInInputMode": amount_mode,
            "amountWrappedUnits": str(wrapped_delta),
            "amountWrapped": _format_units(int(wrapped_delta), wrapped_decimals),
            "wrappedDecimals": wrapped_decimals,
            "wrappedSymbol": wrapped_symbol,
        }
        if target == helper:
            payload["helper"] = helper
        return ok(success_message, **payload)
    except WalletSecurityError as exc:
        return fail("unsafe_permissions", str(exc), "Restrict permissions to owner-only (0700/0600) and retry.", {"chain": chain}, exit_code=1)
    except WalletStoreError as exc:
        msg = str(exc)
        if "coreContracts.wrappedNativeHelper" in msg:
            return fail(
                "wrapped_native_helper_missing",
                msg,
                "Set coreContracts.wrappedNativeHelper in config/chains/<chain>.json and retry.",
                {"chain": chain},
                exit_code=1,
            )
        if "no canonical wrapped native token" in msg:
            return fail(
                "wrapped_native_token_missing",
                msg,
                f"Set canonicalTokens.{wrapped_symbol_hint} for this chain, or run a swap trade ({native_symbol}->{wrapped_symbol_hint}).",
                {"chain": chain, "nativeSymbol": native_symbol, "wrappedSymbolHint": wrapped_symbol_hint},
                exit_code=1,
            )
        if "Amount" in msg and ("too small" in msg or "must be positive" in msg):
            return fail("invalid_amount", msg, "Provide a positive amount and retry.", {"amount": str(args.amount), "chain": chain}, exit_code=2)
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
        return fail(
            "wrap_native_failed",
            msg,
            f"Verify wallet/RPC/wrapped contract connectivity, then retry. You can swap {native_symbol}->{wrapped_symbol_hint} as fallback.",
            {"chain": chain, "nativeSymbol": native_symbol, "wrappedSymbolHint": wrapped_symbol_hint},
            exit_code=1,
        )
    except Exception as exc:
        return fail(
            "wrap_native_failed",
            str(exc),
            f"Inspect runtime wrap-native path and retry. You can swap {native_symbol}->{wrapped_symbol_hint} as fallback.",
            {"chain": chain, "nativeSymbol": native_symbol, "wrappedSymbolHint": wrapped_symbol_hint},
            exit_code=1,
        )


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
    try:
        assert_chain_capability(network, "x402")
    except ChainRegistryError as exc:
        return fail("unsupported_chain_capability", str(exc), chain_supported_hint(), {"network": network}, exit_code=2)
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

    asset_kind_raw = str(args.asset_kind or "native").strip().lower()
    if asset_kind_raw not in {"native", "token", "erc20"}:
        return fail("invalid_input", "asset_kind must be native|token.", "Use --asset-kind native or --asset-kind token.", exit_code=2)
    asset_kind = "token" if asset_kind_raw in {"token", "erc20"} else "native"
    asset_symbol = str(args.asset_symbol or "").strip()
    asset_address = str(args.asset_address or "").strip() or None
    if asset_kind == "token" and not asset_symbol and not asset_address:
        return fail(
            "invalid_input",
            "Token receive requests require asset symbol or asset address.",
            "Set --asset-symbol (USDC|WETH|WKITE|USDT) or --asset-address <token-address>.",
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
        "resourceDescription": str(args.resource_description or "").strip() or None,
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
            resourceDescription=body.get("resourceDescription"),
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
    network = str(args.network or "").strip()
    try:
        assert_chain_capability(network, "x402")
    except ChainRegistryError as exc:
        return fail("unsupported_chain_capability", str(exc), chain_supported_hint(), {"network": network}, exit_code=2)
    try:
        payload = x402_pay_create_or_execute(
            url=str(args.url or "").strip(),
            network=network,
            facilitator=str(args.facilitator or "").strip(),
            amount_atomic=str(args.amount_atomic or "").strip(),
            memo=str(args.memo or "").strip() or None,
            settle_payment=_execute_x402_settlement,
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
        payload = x402_pay_resume(approval_id, settle_payment=_execute_x402_settlement)
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
        payload = x402_pay_decide(
            approval_id,
            decision,
            str(args.reason_message or "").strip() or None,
            settle_payment=_execute_x402_settlement,
        )
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

    auth = sub.add_parser("auth")
    auth_sub = auth.add_subparsers(dest="auth_cmd")
    auth_recover = auth_sub.add_parser("recover")
    auth_recover.add_argument("--chain", required=True)
    auth_recover.add_argument("--json", action="store_true")
    auth_recover.set_defaults(func=cmd_auth_recover)

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

    approvals_run_loop = approvals_sub.add_parser("run-loop")
    approvals_run_loop.add_argument("--chain", required=True)
    approvals_run_loop.add_argument("--interval-ms", type=int, default=APPROVAL_RUN_LOOP_INTERVAL_MS)
    approvals_run_loop.add_argument("--once", action="store_true")
    approvals_run_loop.add_argument("--json", action="store_true")
    approvals_run_loop.set_defaults(func=cmd_approvals_run_loop)

    approvals_cleanup_spot = approvals_sub.add_parser("cleanup-spot")
    approvals_cleanup_spot.add_argument("--trade-id", required=True)
    approvals_cleanup_spot.add_argument("--json", action="store_true")
    approvals_cleanup_spot.set_defaults(func=cmd_approvals_cleanup_spot)

    approvals_clear_prompt = approvals_sub.add_parser("clear-prompt")
    approvals_clear_prompt.add_argument("--subject-type", required=True, choices=["trade", "transfer", "policy"])
    approvals_clear_prompt.add_argument("--subject-id", required=True)
    approvals_clear_prompt.add_argument("--chain")
    approvals_clear_prompt.add_argument("--json", action="store_true")
    approvals_clear_prompt.set_defaults(func=cmd_approvals_clear_prompt)

    approvals_resume_spot = approvals_sub.add_parser("resume-spot")
    approvals_resume_spot.add_argument("--trade-id", required=True)
    approvals_resume_spot.add_argument("--chain")
    approvals_resume_spot.add_argument("--json", action="store_true")
    approvals_resume_spot.set_defaults(func=cmd_approvals_resume_spot)

    approvals_decide_spot = approvals_sub.add_parser("decide-spot")
    approvals_decide_spot.add_argument("--trade-id", required=True)
    approvals_decide_spot.add_argument("--decision", required=True, choices=["approve", "reject"])
    approvals_decide_spot.add_argument("--reason-message")
    approvals_decide_spot.add_argument("--source")
    approvals_decide_spot.add_argument("--idempotency-key")
    approvals_decide_spot.add_argument("--decision-at")
    approvals_decide_spot.add_argument("--chain")
    approvals_decide_spot.add_argument("--json", action="store_true")
    approvals_decide_spot.set_defaults(func=cmd_approvals_decide_spot)

    approvals_decide_liquidity = approvals_sub.add_parser("decide-liquidity")
    approvals_decide_liquidity.add_argument("--intent-id", required=True)
    approvals_decide_liquidity.add_argument("--decision", required=True, choices=["approve", "reject"])
    approvals_decide_liquidity.add_argument("--reason-message")
    approvals_decide_liquidity.add_argument("--source")
    approvals_decide_liquidity.add_argument("--chain", required=True)
    approvals_decide_liquidity.add_argument("--json", action="store_true")
    approvals_decide_liquidity.set_defaults(func=cmd_approvals_decide_liquidity)

    approvals_resume_transfer = approvals_sub.add_parser("resume-transfer")
    approvals_resume_transfer.add_argument("--approval-id", required=True)
    approvals_resume_transfer.add_argument("--chain")
    approvals_resume_transfer.add_argument("--json", action="store_true")
    approvals_resume_transfer.set_defaults(func=cmd_approvals_resume_transfer)

    approvals_decide_policy = approvals_sub.add_parser("decide-policy")
    approvals_decide_policy.add_argument("--approval-id", required=True)
    approvals_decide_policy.add_argument("--decision", required=True, choices=["approve", "reject"])
    approvals_decide_policy.add_argument("--reason-message")
    approvals_decide_policy.add_argument("--source")
    approvals_decide_policy.add_argument("--idempotency-key")
    approvals_decide_policy.add_argument("--decision-at")
    approvals_decide_policy.add_argument("--chain")
    approvals_decide_policy.add_argument("--json", action="store_true")
    approvals_decide_policy.set_defaults(func=cmd_approvals_decide_policy)

    approvals_decide_transfer = approvals_sub.add_parser("decide-transfer")
    approvals_decide_transfer.add_argument("--approval-id", required=True)
    approvals_decide_transfer.add_argument("--decision", required=True, choices=["approve", "deny"])
    approvals_decide_transfer.add_argument("--reason-message")
    approvals_decide_transfer.add_argument("--source")
    approvals_decide_transfer.add_argument("--idempotency-key")
    approvals_decide_transfer.add_argument("--decision-at")
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

    liquidity = sub.add_parser("liquidity")
    liquidity_sub = liquidity.add_subparsers(dest="liquidity_cmd")

    liquidity_add = liquidity_sub.add_parser("add")
    liquidity_add.add_argument("--chain", required=True)
    liquidity_add.add_argument("--dex", required=True)
    liquidity_add.add_argument("--token-a", required=True)
    liquidity_add.add_argument("--token-b", required=True)
    liquidity_add.add_argument("--amount-a", required=True)
    liquidity_add.add_argument("--amount-b", required=True)
    liquidity_add.add_argument("--position-type", default="v2", choices=["v2", "v3"])
    liquidity_add.add_argument("--v3-range")
    liquidity_add.add_argument("--pool-id")
    liquidity_add.add_argument("--slippage-bps", default=100)
    liquidity_add.add_argument("--json", action="store_true")
    liquidity_add.set_defaults(func=cmd_liquidity_add)

    liquidity_remove = liquidity_sub.add_parser("remove")
    liquidity_remove.add_argument("--chain", required=True)
    liquidity_remove.add_argument("--dex", required=True)
    liquidity_remove.add_argument("--position-id", required=True)
    liquidity_remove.add_argument("--percent", default=100)
    liquidity_remove.add_argument("--slippage-bps", default=100)
    liquidity_remove.add_argument("--position-type", default="v2", choices=["v2", "v3"])
    liquidity_remove.add_argument("--pool-id")
    liquidity_remove.add_argument("--token-a")
    liquidity_remove.add_argument("--token-b")
    liquidity_remove.add_argument("--json", action="store_true")
    liquidity_remove.set_defaults(func=cmd_liquidity_remove)

    liquidity_increase = liquidity_sub.add_parser("increase")
    liquidity_increase.add_argument("--chain", required=True)
    liquidity_increase.add_argument("--dex", required=True)
    liquidity_increase.add_argument("--position-id", required=True)
    liquidity_increase.add_argument("--token-a", required=True)
    liquidity_increase.add_argument("--token-b", required=True)
    liquidity_increase.add_argument("--amount-a", required=True)
    liquidity_increase.add_argument("--amount-b", required=True)
    liquidity_increase.add_argument("--slippage-bps", default=100)
    liquidity_increase.add_argument("--json", action="store_true")
    liquidity_increase.set_defaults(func=cmd_liquidity_increase)

    liquidity_claim_fees = liquidity_sub.add_parser("claim-fees")
    liquidity_claim_fees.add_argument("--chain", required=True)
    liquidity_claim_fees.add_argument("--dex", required=True)
    liquidity_claim_fees.add_argument("--position-id", required=True)
    liquidity_claim_fees.add_argument("--collect-as-weth", action="store_true")
    liquidity_claim_fees.add_argument("--json", action="store_true")
    liquidity_claim_fees.set_defaults(func=cmd_liquidity_claim_fees)

    liquidity_migrate = liquidity_sub.add_parser("migrate")
    liquidity_migrate.add_argument("--chain", required=True)
    liquidity_migrate.add_argument("--dex", required=True)
    liquidity_migrate.add_argument("--position-id", required=True)
    liquidity_migrate.add_argument("--from-protocol", required=True)
    liquidity_migrate.add_argument("--to-protocol", required=True)
    liquidity_migrate.add_argument("--slippage-bps", default=100)
    liquidity_migrate.add_argument("--request-json")
    liquidity_migrate.add_argument("--json", action="store_true")
    liquidity_migrate.set_defaults(func=cmd_liquidity_migrate)

    liquidity_claim_rewards = liquidity_sub.add_parser("claim-rewards")
    liquidity_claim_rewards.add_argument("--chain", required=True)
    liquidity_claim_rewards.add_argument("--dex", required=True)
    liquidity_claim_rewards.add_argument("--position-id", required=True)
    liquidity_claim_rewards.add_argument("--reward-token")
    liquidity_claim_rewards.add_argument("--request-json")
    liquidity_claim_rewards.add_argument("--json", action="store_true")
    liquidity_claim_rewards.set_defaults(func=cmd_liquidity_claim_rewards)

    liquidity_positions = liquidity_sub.add_parser("positions")
    liquidity_positions.add_argument("--chain", required=True)
    liquidity_positions.add_argument("--dex")
    liquidity_positions.add_argument("--status")
    liquidity_positions.add_argument("--json", action="store_true")
    liquidity_positions.set_defaults(func=cmd_liquidity_positions)

    liquidity_quote_add = liquidity_sub.add_parser("quote-add")
    liquidity_quote_add.add_argument("--chain", required=True)
    liquidity_quote_add.add_argument("--dex", required=True)
    liquidity_quote_add.add_argument("--token-a", required=True)
    liquidity_quote_add.add_argument("--token-b", required=True)
    liquidity_quote_add.add_argument("--amount-a", required=True)
    liquidity_quote_add.add_argument("--amount-b", required=True)
    liquidity_quote_add.add_argument("--position-type", default="v2", choices=["v2", "v3"])
    liquidity_quote_add.add_argument("--pool-id")
    liquidity_quote_add.add_argument("--slippage-bps", default=100)
    liquidity_quote_add.add_argument("--json", action="store_true")
    liquidity_quote_add.set_defaults(func=cmd_liquidity_quote_add)

    liquidity_quote_remove = liquidity_sub.add_parser("quote-remove")
    liquidity_quote_remove.add_argument("--chain", required=True)
    liquidity_quote_remove.add_argument("--dex", required=True)
    liquidity_quote_remove.add_argument("--position-id", required=True)
    liquidity_quote_remove.add_argument("--percent", default=100)
    liquidity_quote_remove.add_argument("--position-type", default="v2", choices=["v2", "v3"])
    liquidity_quote_remove.add_argument("--pool-id")
    liquidity_quote_remove.add_argument("--json", action="store_true")
    liquidity_quote_remove.set_defaults(func=cmd_liquidity_quote_remove)

    liquidity_discover_pairs = liquidity_sub.add_parser("discover-pairs")
    liquidity_discover_pairs.add_argument("--chain", required=True)
    liquidity_discover_pairs.add_argument("--dex", required=True)
    liquidity_discover_pairs.add_argument("--min-reserve", default=1)
    liquidity_discover_pairs.add_argument("--limit", default=10)
    liquidity_discover_pairs.add_argument("--scan-max", default=50)
    liquidity_discover_pairs.add_argument("--json", action="store_true")
    liquidity_discover_pairs.set_defaults(func=cmd_liquidity_discover_pairs)

    liquidity_execute = liquidity_sub.add_parser("execute")
    liquidity_execute.add_argument("--intent", required=True)
    liquidity_execute.add_argument("--chain", required=True)
    liquidity_execute.add_argument("--json", action="store_true")
    liquidity_execute.set_defaults(func=cmd_liquidity_execute)

    liquidity_resume = liquidity_sub.add_parser("resume")
    liquidity_resume.add_argument("--intent", required=True)
    liquidity_resume.add_argument("--chain", required=True)
    liquidity_resume.add_argument("--json", action="store_true")
    liquidity_resume.set_defaults(func=cmd_liquidity_resume)

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

    tracked = sub.add_parser("tracked")
    tracked_sub = tracked.add_subparsers(dest="tracked_cmd")

    tracked_list = tracked_sub.add_parser("list")
    tracked_list.add_argument("--chain", required=True)
    tracked_list.add_argument("--json", action="store_true")
    tracked_list.set_defaults(func=cmd_tracked_list)

    tracked_trades = tracked_sub.add_parser("trades")
    tracked_trades.add_argument("--chain", required=True)
    tracked_trades.add_argument("--agent")
    tracked_trades.add_argument("--limit", default="20")
    tracked_trades.add_argument("--json", action="store_true")
    tracked_trades.set_defaults(func=cmd_tracked_trades)

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
    faucet_request.add_argument("--asset", action="append", default=[])
    faucet_request.add_argument("--json", action="store_true")
    faucet_request.set_defaults(func=cmd_faucet_request)

    faucet_networks = sub.add_parser("faucet-networks")
    faucet_networks.add_argument("--json", action="store_true")
    faucet_networks.set_defaults(func=cmd_faucet_networks)

    chains_cmd = sub.add_parser("chains")
    chains_cmd.add_argument("--include-disabled", action="store_true")
    chains_cmd.add_argument("--json", action="store_true")
    chains_cmd.set_defaults(func=cmd_chains)

    default_chain = sub.add_parser("default-chain")
    default_chain_sub = default_chain.add_subparsers(dest="default_chain_cmd")

    default_chain_get = default_chain_sub.add_parser("get")
    default_chain_get.add_argument("--json", action="store_true")
    default_chain_get.set_defaults(func=cmd_default_chain_get)

    default_chain_set = default_chain_sub.add_parser("set")
    default_chain_set.add_argument("--chain", required=True)
    default_chain_set.add_argument("--json", action="store_true")
    default_chain_set.set_defaults(func=cmd_default_chain_set)

    x402 = sub.add_parser("x402")
    x402_sub = x402.add_subparsers(dest="x402_cmd")

    x402_receive_request = x402_sub.add_parser("receive-request")
    x402_receive_request.add_argument("--network", required=True)
    x402_receive_request.add_argument("--facilitator", required=True)
    x402_receive_request.add_argument("--amount-atomic", required=True)
    x402_receive_request.add_argument("--asset-kind", default="native", choices=["native", "token", "erc20"])
    x402_receive_request.add_argument("--asset-address")
    x402_receive_request.add_argument("--asset-symbol")
    x402_receive_request.add_argument("--resource-description")
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

    w_track_token = wallet_sub.add_parser("track-token")
    w_track_token.add_argument("--token", required=True)
    w_track_token.add_argument("--chain", required=True)
    w_track_token.add_argument("--json", action="store_true")
    w_track_token.set_defaults(func=cmd_wallet_track_token)

    w_untrack_token = wallet_sub.add_parser("untrack-token")
    w_untrack_token.add_argument("--token", required=True)
    w_untrack_token.add_argument("--chain", required=True)
    w_untrack_token.add_argument("--json", action="store_true")
    w_untrack_token.set_defaults(func=cmd_wallet_untrack_token)

    w_tracked_tokens = wallet_sub.add_parser("tracked-tokens")
    w_tracked_tokens.add_argument("--chain", required=True)
    w_tracked_tokens.add_argument("--json", action="store_true")
    w_tracked_tokens.set_defaults(func=cmd_wallet_tracked_tokens)

    w_wrap = wallet_sub.add_parser("wrap-native")
    w_wrap.add_argument("--amount", required=True)
    w_wrap.add_argument("--chain", required=True)
    w_wrap.add_argument("--json", action="store_true")
    w_wrap.set_defaults(func=cmd_wallet_wrap_native)

    # Wallet lifecycle commands are intentionally not exposed via the OpenClaw skill wrapper,
    # but the installer/bootstrap flow relies on the runtime being able to create a wallet
    # non-interactively when missing.
    w_create = wallet_sub.add_parser("create")
    w_create.add_argument("--chain", required=True)
    w_create.add_argument("--json", action="store_true")
    w_create.set_defaults(func=cmd_wallet_create)

    w_import = wallet_sub.add_parser("import")
    w_import.add_argument("--chain", required=True)
    w_import.add_argument("--json", action="store_true")
    w_import.set_defaults(func=cmd_wallet_import)

    w_remove = wallet_sub.add_parser("remove")
    w_remove.add_argument("--chain", required=True)
    w_remove.add_argument("--json", action="store_true")
    w_remove.set_defaults(func=cmd_wallet_remove)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 2
    chain = getattr(args, "chain", None)
    if isinstance(chain, str) and chain.strip():
        normalized_chain = chain.strip()
        try:
            assert_chain_supported(normalized_chain)
        except ChainRegistryError as exc:
            return fail("unsupported_chain", str(exc), chain_supported_hint(), {"chain": normalized_chain}, exit_code=2)

        top = str(getattr(args, "top", "") or "")
        capability = "wallet"
        if top == "trade":
            capability = "trade"
        elif top == "liquidity":
            capability = "liquidity"
        elif top == "limit-orders":
            capability = "limitOrders"
        elif top == "faucet-request":
            capability = "faucet"
        try:
            assert_chain_capability(normalized_chain, capability)
        except ChainRegistryError as exc:
            return fail(
                "unsupported_chain_capability",
                str(exc),
                "Select a chain that supports this command capability.",
                {"chain": normalized_chain, "requiredCapability": capability},
                exit_code=2,
            )
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
