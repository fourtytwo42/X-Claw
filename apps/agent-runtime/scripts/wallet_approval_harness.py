#!/usr/bin/env python3
"""Slice 96+117 wallet/approval E2E harness.

This harness executes real runtime + management API flows with Telegram dispatch
suppressed via XCLAW_TEST_HARNESS_DISABLE_TELEGRAM=1.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import random
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from http import cookiejar
from typing import Any

SOLANA_WRAPPED_NATIVE_MINT = "So11111111111111111111111111111111111111112"
SOLANA_USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
SOLANA_LOCALNET_BOOTSTRAP_ENV_FILE = pathlib.Path(
    os.environ.get(
        "XCLAW_SOLANA_LOCALNET_BOOTSTRAP_ENV_FILE",
        pathlib.Path("infrastructure/seed-data/solana-localnet-faucet.env").resolve().as_posix(),
    )
)
SOLANA_CHAIN_SCOPED_MINT_ENV = {
    "solana_localnet": {
        "stable": "XCLAW_SOLANA_FAUCET_STABLE_MINT_SOLANA_LOCALNET",
        "wrapped": "XCLAW_SOLANA_FAUCET_WRAPPED_MINT_SOLANA_LOCALNET",
    },
    "solana_devnet": {
        "stable": "XCLAW_SOLANA_FAUCET_STABLE_MINT_SOLANA_DEVNET",
        "wrapped": "XCLAW_SOLANA_FAUCET_WRAPPED_MINT_SOLANA_DEVNET",
    },
}
SOLANA_DEVNET_QUOTE_ALLOWLIST: list[tuple[str, str]] = [
    ("SOL", "USDC"),
    ("USDC", "SOL"),
]


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _read_json(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_env_file(path: pathlib.Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key:
            out[key] = value.strip()
    return out


def _is_likely_solana_address(value: str) -> bool:
    text = str(value or "").strip()
    return bool(text) and 32 <= len(text) <= 44 and all(ch in "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz" for ch in text)


def _safe_num(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0")


def _trim_text(value: Any, max_len: int = 480) -> str:
    text = str(value or "").strip()
    if len(text) <= max_len:
        return text
    return f"{text[:max_len]}..."


def _payload_hash(payload: dict[str, Any] | None) -> str:
    if payload is None:
        return ""
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _recover_local_passphrase_backup() -> str:
    backup_path = pathlib.Path(os.environ.get("XCLAW_AGENT_APP_DIR", "~/.xclaw-agent")).expanduser() / "passphrase.backup.v1.json"
    if not backup_path.exists():
        return ""
    try:
        payload = _read_json(backup_path)
        nonce_b64 = str(payload.get("nonceB64") or "")
        ciphertext_b64 = str(payload.get("ciphertextB64") or "")
        if not nonce_b64 or not ciphertext_b64:
            return ""

        import base64

        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        from cryptography.hazmat.primitives.kdf.hkdf import HKDF

        machine_id = ""
        for candidate in ("/etc/machine-id", "/var/lib/dbus/machine-id"):
            path = pathlib.Path(candidate)
            if not path.exists():
                continue
            raw = path.read_text(encoding="utf-8").strip()
            if raw:
                machine_id = raw
                break

        ikm = hashlib.sha256(("|".join([machine_id, str(os.getuid()), str(pathlib.Path.home())])).encode("utf-8")).digest()
        hkdf = HKDF(algorithm=hashes.SHA256(), length=32, salt=b"xclaw-passphrase-backup-v1", info=b"xclaw")
        key = hkdf.derive(ikm)

        nonce = base64.b64decode(nonce_b64)
        ciphertext = base64.b64decode(ciphertext_b64)
        plaintext = AESGCM(key).decrypt(nonce, ciphertext, b"xclaw-passphrase-backup-v1")
        return plaintext.decode("utf-8").strip()
    except Exception:
        return ""


def _agent_app_dir() -> pathlib.Path:
    return pathlib.Path(os.environ.get("XCLAW_AGENT_APP_DIR", "~/.xclaw-agent")).expanduser()


def _openclaw_skill_env() -> dict[str, str]:
    config_path = pathlib.Path.home() / ".openclaw" / "openclaw.json"
    if not config_path.exists():
        return {}
    try:
        payload = _read_json(config_path)
    except Exception:
        return {}
    skills = payload.get("skills")
    if not isinstance(skills, dict):
        return {}
    entries = skills.get("entries")
    if not isinstance(entries, dict):
        return {}
    entry = entries.get("xclaw-agent")
    if not isinstance(entry, dict):
        return {}
    env = entry.get("env")
    if not isinstance(env, dict):
        return {}
    out: dict[str, str] = {}
    for key, value in env.items():
        if isinstance(key, str) and isinstance(value, str):
            out[key] = value
    return out


def _resolve_harness_passphrase(*, explicit: str = "", env_values: dict[str, str] | None = None) -> tuple[str, str]:
    direct = str(explicit or "").strip()
    if direct:
        return direct, "arg"
    runtime_env = env_values if isinstance(env_values, dict) else os.environ
    env_passphrase = str(runtime_env.get("XCLAW_WALLET_PASSPHRASE") or "").strip()
    if env_passphrase:
        return env_passphrase, "env"
    skill_passphrase = str(_openclaw_skill_env().get("XCLAW_WALLET_PASSPHRASE") or "").strip()
    if skill_passphrase:
        return skill_passphrase, "skill_config"
    recovered = _recover_local_passphrase_backup()
    if recovered:
        return recovered, "backup"
    return "", "missing"


def _canonical_challenge_message(chain: str) -> str:
    nonce = f"harness{int(time.time())}"
    timestamp = _now_iso().replace("Z", "+00:00")
    return "\n".join(
        [
            "domain=xclaw.trade",
            f"chain={chain}",
            f"nonce={nonce}",
            f"timestamp={timestamp}",
            "action=wallet_health_probe",
        ]
    )


def _extract_trade_id(payload: dict[str, Any]) -> str:
    direct = str(payload.get("tradeId") or "").strip()
    if direct:
        return direct
    details = payload.get("details")
    if isinstance(details, dict):
        nested = str(details.get("tradeId") or "").strip()
        if nested:
            return nested
    trade = payload.get("trade")
    if isinstance(trade, dict):
        nested = str(trade.get("tradeId") or "").strip()
        if nested:
            return nested
    return ""


def _extract_transfer_approval_id(payload: dict[str, Any]) -> str:
    direct = str(payload.get("approvalId") or "").strip()
    if direct:
        return direct
    details = payload.get("details")
    if isinstance(details, dict):
        nested = str(details.get("approvalId") or "").strip()
        if nested:
            return nested
    approval = payload.get("approval")
    if isinstance(approval, dict):
        nested = str(approval.get("approvalId") or "").strip()
        if nested:
            return nested
    return ""


def _extract_liquidity_intent_id(payload: dict[str, Any]) -> str:
    direct = str(payload.get("liquidityIntentId") or "").strip()
    if direct:
        return direct
    details = payload.get("details")
    if isinstance(details, dict):
        nested = str(details.get("liquidityIntentId") or "").strip()
        if nested:
            return nested
    return ""


def _within_tolerance(before: Decimal, after: Decimal, bps: int, floor: Decimal) -> tuple[bool, Decimal, Decimal]:
    delta = abs(after - before)
    pct_window = abs(before) * Decimal(bps) / Decimal(10000)
    window = pct_window if pct_window > floor else floor
    return delta <= window, delta, window


@dataclass
class ScenarioResult:
    name: str
    ok: bool
    message: str
    details: dict[str, Any]


class HarnessError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        code: str = "harness_failed",
        category: str = "runtime_trade_failure",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.code = code
        self.category = category
        self.details = details or {}


class WalletApprovalHarness:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.base_url = args.base_url.rstrip("/")
        self.api_base = f"{self.base_url}/api/v1"
        self.agent_id = args.agent_id
        self.chain = args.chain
        self.runtime_bin = args.runtime_bin
        self.api_key = (args.agent_api_key or os.environ.get("XCLAW_AGENT_API_KEY") or "").strip()
        if not self.api_key:
            raise HarnessError("Missing agent API key. Provide --agent-api-key or XCLAW_AGENT_API_KEY.")
        self.wallet_passphrase = (args.wallet_passphrase or os.environ.get("XCLAW_WALLET_PASSPHRASE") or "").strip()
        self.cookie_jar = cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cookie_jar))
        self.csrf_token = ""
        self.results: list[ScenarioResult] = []
        self.created_trade_ids: list[str] = []
        self.created_transfer_approval_ids: list[str] = []
        self.created_liquidity_intent_ids: list[str] = []
        self.created_x402_approval_ids: list[str] = []
        self.trade_token_in: str = "USDC"
        self.trade_token_out: str = "WETH"
        self.trade_amounts: dict[str, str] = {
            "pending_approve": "0.5",
            "reject": "0.3",
            "dedupe": "0.2",
            "global_auto": "0.1",
            "allowlist": "0.15",
            "rebalance": "0.05",
        }
        self.preflight: dict[str, Any] = {
            "hardhatRpc": {"ok": True},
            "walletDecryptProbe": {"ok": False},
            "managementSession": {"ok": False},
            "solanaLocalnetBootstrap": {"ok": True, "skipped": True},
        }
        self.retry_failures: list[dict[str, Any]] = []
        self.unresolved_pending: list[dict[str, Any]] = []
        self.initial_state: dict[str, Any] = {}
        self._chain_config_cache: dict[str, Any] | None = None
        self._skill_env_cache: dict[str, str] | None = None
        self._solana_localnet_bootstrap_env_cache: dict[str, str] | None = None
        self._solana_devnet_trade_pair_discovery: dict[str, Any] | None = None

    def _solana_devnet_custom_mint_trade_details(self) -> dict[str, Any]:
        return {
            "chain": self.chain,
            "walletAddress": self._wallet_address(),
            "stableMint": self._solana_chain_mint("stable"),
            "wrappedMint": self._solana_chain_mint("wrapped"),
            "tokenIn": self.trade_token_in,
            "tokenOut": self.trade_token_out,
        }

    def _jupiter_base_urls(self, chain_key: str) -> list[str]:
        chain_env_key = f"XCLAW_JUPITER_BASE_URLS_{str(chain_key or '').strip().upper()}"
        raw = str(os.environ.get(chain_env_key) or os.environ.get("XCLAW_JUPITER_BASE_URLS") or "").strip()
        candidates: list[str] = []
        if raw:
            for item in raw.split(","):
                candidate = str(item or "").strip().rstrip("/")
                if candidate:
                    candidates.append(candidate)
        for default_url in ("https://lite-api.jup.ag/swap/v1", "https://quote-api.jup.ag/v6"):
            if default_url not in candidates:
                candidates.append(default_url)
        deduped: list[str] = []
        for item in candidates:
            if item not in deduped:
                deduped.append(item)
        return deduped

    def _probe_jupiter_quoteability(self, *, token_in: str, token_out: str, amount_units: str) -> dict[str, Any]:
        endpoints = self._jupiter_base_urls(self.chain)
        query = urllib.parse.urlencode(
            {
                "inputMint": token_in,
                "outputMint": token_out,
                "amount": str(amount_units),
                "slippageBps": "100",
                "swapMode": "ExactIn",
                "onlyDirectRoutes": "false",
            }
        )
        attempts: list[dict[str, Any]] = []
        for endpoint in endpoints:
            req = urllib.request.Request(
                f"{endpoint}/quote?{query}",
                method="GET",
                headers={"accept": "application/json"},
            )
            try:
                with urllib.request.urlopen(req, timeout=20) as resp:
                    payload = json.loads(resp.read().decode("utf-8"))
                out_amount = str((payload if isinstance(payload, dict) else {}).get("outAmount") or "").strip()
                if out_amount.isdigit() and out_amount != "0":
                    return {
                        "quoteable": True,
                        "endpoint": endpoint,
                        "payload": payload if isinstance(payload, dict) else {},
                        "outAmount": out_amount,
                    }
                attempts.append(
                    {
                        "endpoint": endpoint,
                        "status": 200,
                        "error": "no_executable_out_amount",
                        "payload": payload if isinstance(payload, dict) else {},
                    }
                )
            except urllib.error.HTTPError as exc:
                body = ""
                try:
                    body = exc.read().decode("utf-8", errors="replace").strip()
                except Exception:
                    body = ""
                attempts.append({"endpoint": endpoint, "status": int(exc.code or 0), "error": _trim_text(body or exc)})
            except Exception as exc:
                attempts.append({"endpoint": endpoint, "status": None, "error": _trim_text(exc)})
        return {"quoteable": False, "attempts": attempts}

    def _solana_balance_for_token(self, balances: dict[str, Decimal], token: str) -> Decimal:
        normalized = str(token or "").strip()
        if not normalized:
            return Decimal("0")
        if normalized.upper() == "SOL":
            return balances.get("NATIVE", Decimal("0"))
        return balances.get(normalized.lower(), Decimal("0")) or balances.get(normalized.upper(), Decimal("0"))

    def _solana_trade_amounts_for_token(self, token_in: str) -> dict[str, str]:
        normalized = str(token_in or "").strip()
        stable_mint = str(self._solana_chain_mint("stable") or "").strip().lower()
        wrapped_mint = str(self._solana_chain_mint("wrapped") or "").strip().lower()
        if normalized.upper() == "SOL" or normalized.lower() == wrapped_mint or normalized.upper() == "WETH":
            return {
                "pending_approve": "0.001",
                "reject": "0.0008",
                "dedupe": "0.0007",
                "global_auto": "0.0006",
                "allowlist": "0.0005",
                "rebalance": "0.0004",
            }
        return {
            "pending_approve": "0.5",
            "reject": "0.4",
            "dedupe": "0.3",
            "global_auto": "0.2",
            "allowlist": "0.15",
            "rebalance": "0.1",
        }

    def _discover_solana_devnet_trade_pair(self, balances: dict[str, Decimal]) -> dict[str, Any]:
        stable_mint = str(self._solana_chain_mint("stable") or "").strip()
        wrapped_mint = str(self._solana_chain_mint("wrapped") or "").strip()
        candidates: list[dict[str, Any]] = []
        seen: set[tuple[str, str, str]] = set()

        def _add_candidate(token_in: str, token_out: str, source: str) -> None:
            key = (str(token_in).strip(), str(token_out).strip(), str(source).strip())
            if key in seen or not key[0] or not key[1]:
                return
            seen.add(key)
            candidates.append({"tokenIn": key[0], "tokenOut": key[1], "tradePairSource": key[2]})

        if stable_mint:
            _add_candidate("SOL", stable_mint, "env_scoped")
            _add_candidate(stable_mint, "SOL", "env_scoped")
        if stable_mint and wrapped_mint:
            _add_candidate(wrapped_mint, stable_mint, "env_scoped")
            _add_candidate(stable_mint, wrapped_mint, "env_scoped")
        for token_in, token_out in SOLANA_DEVNET_QUOTE_ALLOWLIST:
            resolved_in = self._canonical_token_address(token_in) if token_in != "SOL" else "SOL"
            resolved_out = self._canonical_token_address(token_out) if token_out != "SOL" else "SOL"
            _add_candidate(resolved_in, resolved_out, "allowlist")

        results: list[dict[str, Any]] = []
        for candidate in candidates:
            token_in = candidate["tokenIn"]
            token_out = candidate["tokenOut"]
            input_balance = self._solana_balance_for_token(balances, token_in)
            result = {
                "tradePairSource": candidate["tradePairSource"],
                "tokenIn": token_in,
                "tokenOut": token_out,
                "inputBalanceAtomic": str(input_balance),
                "quoteable": False,
            }
            if input_balance <= 0:
                result["skippedReason"] = "input_balance_missing"
                results.append(result)
                continue
            amount_units = "10000" if token_in == "SOL" or token_in.lower() == wrapped_mint.lower() else "1000"
            probe = self._probe_jupiter_quoteability(
                token_in=SOLANA_WRAPPED_NATIVE_MINT if token_in == "SOL" else token_in,
                token_out=SOLANA_WRAPPED_NATIVE_MINT if token_out == "SOL" else token_out,
                amount_units=amount_units,
            )
            result["amountUnits"] = amount_units
            result["probe"] = probe
            result["quoteable"] = bool(probe.get("quoteable"))
            results.append(result)
            if result["quoteable"]:
                return {
                    "quoteable": True,
                    "tradePairSource": result["tradePairSource"],
                    "tokenIn": token_in,
                    "tokenOut": token_out,
                    "quoteableResults": results,
                }
        return {
            "quoteable": False,
            "reason": "solana_devnet_trade_pair_unavailable",
            "walletAddress": self._wallet_address(),
            "stableMint": stable_mint,
            "wrappedMint": wrapped_mint,
            "candidatePairs": results,
        }

    def _raise_if_solana_devnet_trade_pair_unavailable(self) -> None:
        if str(self.chain).strip().lower() != "solana_devnet":
            return
        if self._solana_devnet_trade_pair_discovery is None:
            return
        discovery = self._solana_devnet_trade_pair_discovery or {}
        if bool(discovery.get("quoteable")):
            return
        raise HarnessError(
            "No Jupiter-quotable Solana devnet trade pair is available for truthful live evidence.",
            code="solana_devnet_trade_pair_unavailable",
            category="unsupported_live_evidence",
            details=discovery if isinstance(discovery, dict) else {},
        )

    def _raise_if_solana_devnet_custom_mint_trade_preflight_unsupported(self, *, phase: str) -> None:
        if str(self.chain).strip().lower() != "solana_devnet":
            return
        if self._solana_devnet_trade_pair_discovery is not None:
            return
        stable_mint = str(self._solana_chain_mint("stable") or "").strip()
        wrapped_mint = str(self._solana_chain_mint("wrapped") or "").strip()
        if not stable_mint and not wrapped_mint:
            return
        details = self._solana_devnet_custom_mint_trade_details()
        details.update({"phase": phase, "reason": "solana_devnet_custom_mint_trade_unsupported"})
        raise HarnessError(
            "Solana devnet custom-mint trade routing is not supported for truthful live evidence.",
            code="solana_devnet_custom_mint_trade_unsupported",
            category="unsupported_live_evidence",
            details=details,
        )

    def _raise_if_solana_devnet_custom_mint_quote_unsupported(
        self,
        payload: dict[str, Any] | None,
        *,
        phase: str,
        trade_id: str = "",
        stderr: str = "",
    ) -> None:
        if str(self.chain).strip().lower() != "solana_devnet":
            return
        if self._solana_devnet_trade_pair_discovery is not None:
            return
        stable_mint = str(self._solana_chain_mint("stable") or "").strip()
        wrapped_mint = str(self._solana_chain_mint("wrapped") or "").strip()
        if not stable_mint and not wrapped_mint:
            return
        body = payload if isinstance(payload, dict) else {}
        scan = json.dumps(body, sort_keys=True, default=str).lower()
        if "jupiter quote request failed" not in scan:
            return
        details = self._solana_devnet_custom_mint_trade_details()
        details.update(
            {
                "phase": phase,
                "tradeId": str(trade_id or "").strip(),
                "payload": body,
                "stderr": _trim_text(stderr),
                "reason": "solana_devnet_custom_mint_trade_unsupported",
            }
        )
        raise HarnessError(
            "Solana devnet custom-mint trade routing is not supported for truthful live evidence.",
            code="solana_devnet_custom_mint_trade_unsupported",
            category="unsupported_live_evidence",
            details=details,
        )

    def _record(self, name: str, ok: bool, message: str, details: dict[str, Any] | None = None) -> None:
        payload = details or {}
        self.results.append(ScenarioResult(name=name, ok=ok, message=message, details=payload))
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {name}: {message}")

    def _http(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
        auth_mode: str = "management",
        timeout: int = 30,
    ) -> tuple[int, dict[str, Any]]:
        url = f"{self.api_base}{path}"
        data = None
        headers = {"content-type": "application/json"}
        if body is not None:
            data = json.dumps(body).encode("utf-8")
        if auth_mode == "management":
            if self.csrf_token:
                headers["X-CSRF-Token"] = self.csrf_token
        elif auth_mode == "agent":
            headers["Authorization"] = f"Bearer {self.api_key}"
        req = urllib.request.Request(url=url, data=data, method=method.upper())
        for k, v in headers.items():
            req.add_header(k, v)
        try:
            with self.opener.open(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                parsed = json.loads(raw) if raw.strip() else {}
                return int(resp.status), parsed if isinstance(parsed, dict) else {"raw": parsed}
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
            parsed = {}
            if raw.strip():
                try:
                    parsed = json.loads(raw)
                except json.JSONDecodeError:
                    parsed = {"raw": raw}
            return int(exc.code), parsed if isinstance(parsed, dict) else {"raw": parsed}
        except urllib.error.URLError as exc:
            return 0, {"code": "network_error", "message": _trim_text(getattr(exc, "reason", exc))}
        except TimeoutError as exc:
            return 0, {"code": "network_error", "message": _trim_text(exc)}

    def _runtime(self, args: list[str], *, timeout: int = 240) -> tuple[int, dict[str, Any], str, str]:
        cmd = [self.runtime_bin, *args, "--json"]
        skill_env = self._skill_env()
        env = {
            **os.environ,
            "XCLAW_API_BASE_URL": self.api_base,
            "XCLAW_AGENT_ID": self.agent_id,
            "XCLAW_DEFAULT_CHAIN": self.chain,
            "XCLAW_AGENT_API_KEY": self.api_key,
            "XCLAW_TEST_HARNESS_DISABLE_TELEGRAM": "1",
        }
        if self.wallet_passphrase:
            env["XCLAW_WALLET_PASSPHRASE"] = self.wallet_passphrase
        for key in ("XCLAW_BUILDER_CODE_BASE", f"XCLAW_BUILDER_CODE_{self.chain.strip().upper()}"):
            if str(env.get(key) or "").strip():
                continue
            fallback = str(skill_env.get(key) or "").strip()
            if fallback:
                env[key] = fallback
        proc = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout, env=env)
        out = (proc.stdout or "").strip()
        payload: dict[str, Any] = {}
        for line in reversed(out.splitlines()):
            line = line.strip()
            if not line:
                continue
            try:
                candidate = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(candidate, dict):
                payload = candidate
                break
        return proc.returncode, payload, proc.stdout or "", proc.stderr or ""

    def _skill_env(self) -> dict[str, str]:
        if self._skill_env_cache is None:
            self._skill_env_cache = _openclaw_skill_env()
        return self._skill_env_cache

    def _load_bootstrap_token(self) -> str:
        data = _read_json(pathlib.Path(self.args.bootstrap_token_file))
        token = str(data.get("token") or "").strip()
        if not token:
            raise HarnessError("Bootstrap token file does not contain a token field.")
        return token

    def _bootstrap_management(self) -> None:
        token = self._load_bootstrap_token()
        status, body = self._http(
            "POST",
            "/management/session/bootstrap",
            body={"agentId": self.agent_id, "token": token},
            auth_mode="none",
        )
        if status != 200:
            raise HarnessError(f"Management bootstrap failed ({status}): {body}")
        csrf = ""
        for cookie in self.cookie_jar:
            if cookie.name == "xclaw_csrf":
                csrf = cookie.value
                break
        if not csrf:
            raise HarnessError("Management bootstrap succeeded but xclaw_csrf cookie is missing.")
        self.csrf_token = csrf
        self.preflight["managementSession"] = {"ok": True}

    def _probe_hardhat_rpc(self) -> None:
        if str(self.chain).strip().lower() != "hardhat_local":
            self.preflight["hardhatRpc"] = {"ok": True, "skipped": True}
            return
        payload = {"jsonrpc": "2.0", "id": 1, "method": "eth_chainId", "params": []}
        request = urllib.request.Request(
            url=str(self.args.hardhat_rpc_url),
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={"content-type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=6) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
            parsed = json.loads(raw) if raw else {}
            chain_id = str(parsed.get("result") or "")
            self.preflight["hardhatRpc"] = {"ok": bool(chain_id), "chainId": chain_id}
        except Exception as exc:
            self.preflight["hardhatRpc"] = {"ok": False, "error": _trim_text(exc)}
            raise HarnessError(
                "Hardhat RPC preflight failed.",
                code="hardhat_rpc_unavailable",
                category="preflight_failure",
                details={"hardhatRpcUrl": self.args.hardhat_rpc_url, "error": _trim_text(exc)},
            )

    def _probe_solana_localnet_bootstrap(self) -> None:
        if str(self.chain).strip().lower() != "solana_localnet":
            self.preflight["solanaLocalnetBootstrap"] = {"ok": True, "skipped": True}
            return
        env_path = pathlib.Path(str(os.environ.get("XCLAW_SOLANA_LOCALNET_BOOTSTRAP_ENV_FILE") or SOLANA_LOCALNET_BOOTSTRAP_ENV_FILE))
        env_values = self._solana_localnet_bootstrap_env()
        signer_secret = str(env_values.get("XCLAW_SOLANA_FAUCET_SIGNER_SECRET_SOLANA_LOCALNET") or "").strip()
        wrapped_mint = str(env_values.get("XCLAW_SOLANA_FAUCET_WRAPPED_MINT_SOLANA_LOCALNET") or "").strip()
        stable_mint = str(env_values.get("XCLAW_SOLANA_FAUCET_STABLE_MINT_SOLANA_LOCALNET") or "").strip()
        payload = {
            "ok": bool(signer_secret and _is_likely_solana_address(wrapped_mint) and _is_likely_solana_address(stable_mint)),
            "bootstrapEnvFile": str(env_path),
            "signerConfigured": bool(signer_secret),
            "wrappedMintConfigured": _is_likely_solana_address(wrapped_mint),
            "stableMintConfigured": _is_likely_solana_address(stable_mint),
        }
        self.preflight["solanaLocalnetBootstrap"] = payload
        if payload["ok"]:
            return
        raise HarnessError(
            "Solana localnet bootstrap env is missing or invalid.",
            code="solana_localnet_bootstrap_missing",
            category="preflight_failure",
            details=payload,
        )

    def _solana_localnet_bootstrap_env(self) -> dict[str, str]:
        if self._solana_localnet_bootstrap_env_cache is not None:
            return self._solana_localnet_bootstrap_env_cache
        env_path = pathlib.Path(str(os.environ.get("XCLAW_SOLANA_LOCALNET_BOOTSTRAP_ENV_FILE") or SOLANA_LOCALNET_BOOTSTRAP_ENV_FILE))
        env_values = _read_env_file(env_path)
        env_values["XCLAW_SOLANA_LOCALNET_BOOTSTRAP_ENV_FILE"] = str(env_path)
        self._solana_localnet_bootstrap_env_cache = env_values
        return env_values

    def _solana_localnet_bootstrap_mint(self, kind: str) -> str:
        env_values = self._solana_localnet_bootstrap_env()
        key = {
            "stable": "XCLAW_SOLANA_FAUCET_STABLE_MINT_SOLANA_LOCALNET",
            "wrapped": "XCLAW_SOLANA_FAUCET_WRAPPED_MINT_SOLANA_LOCALNET",
        }.get(kind)
        if not key:
            return ""
        return str(env_values.get(key) or "").strip()

    def _chain_scoped_env(self, key: str) -> str:
        value = str(os.environ.get(key) or "").strip()
        if value:
            return value
        return str(self._skill_env().get(key) or "").strip()

    def _solana_chain_mint(self, kind: str) -> str:
        chain_normalized = str(self.chain).strip().lower()
        if chain_normalized == "solana_localnet":
            return self._solana_localnet_bootstrap_mint(kind)
        key = SOLANA_CHAIN_SCOPED_MINT_ENV.get(chain_normalized, {}).get(kind, "")
        if not key:
            return ""
        return self._chain_scoped_env(key)

    def _assert_hardhat_evidence_gate(self) -> None:
        if str(self.chain).strip().lower() == "hardhat_local":
            return
        report_path = pathlib.Path(str(self.args.hardhat_evidence_report))
        if not report_path.exists():
            raise HarnessError(
                "Hardhat evidence report missing; Base Sepolia run is blocked.",
                code="hardhat_evidence_missing",
                category="preflight_failure",
                details={"requiredReportPath": str(report_path)},
            )
        report = _read_json(report_path)
        if not bool(report.get("ok")):
            raise HarnessError(
                "Hardhat evidence report is not green; Base Sepolia run is blocked.",
                code="hardhat_evidence_not_green",
                category="preflight_failure",
                details={"requiredReportPath": str(report_path), "reportOk": bool(report.get("ok"))},
            )

    def _wallet_decrypt_probe(self) -> None:
        self.wallet_passphrase, passphrase_source = _resolve_harness_passphrase(explicit=str(self.args.wallet_passphrase or ""))
        wallet_store_path = str((pathlib.Path(os.environ.get("XCLAW_AGENT_APP_DIR", "~/.xclaw-agent")).expanduser() / "wallets.json"))

        def _require_ok(label: str, cmd: list[str]) -> dict[str, Any]:
            code, payload, stdout, stderr = self._runtime(cmd, timeout=90)
            if code != 0 or not bool(payload.get("ok")):
                raise HarnessError(
                    f"{label} preflight failed.",
                    code="wallet_passphrase_mismatch",
                    category="preflight_failure",
                    details={
                        "chain": self.chain,
                        "walletStorePath": wallet_store_path,
                        "passphraseSource": passphrase_source,
                        "payload": payload,
                        "stderr": _trim_text(stderr),
                        "stdout": _trim_text(stdout),
                    },
                )
            return payload

        recovery_attempted = False
        while True:
            try:
                _ = _require_ok("wallet address", ["wallet", "address", "--chain", self.chain])
                health_payload: dict[str, Any] | None = None
                code_h, payload_h, stdout_h, stderr_h = self._runtime(["wallet", "health", "--chain", self.chain], timeout=90)
                if code_h != 0 or not bool(payload_h.get("ok")):
                    hardhat_health_soft_fail = (
                        str(self.chain).strip().lower() == "hardhat_local"
                        and str(payload_h.get("code") or "") == "wallet_health_failed"
                    )
                    if not hardhat_health_soft_fail:
                        raise HarnessError(
                            "wallet health preflight failed.",
                            code="wallet_passphrase_mismatch",
                            category="preflight_failure",
                            details={
                                "chain": self.chain,
                                "walletStorePath": wallet_store_path,
                                "passphraseSource": passphrase_source,
                                "payload": payload_h,
                                "stderr": _trim_text(stderr_h),
                                "stdout": _trim_text(stdout_h),
                            },
                        )
                else:
                    health_payload = payload_h
                sign_soft_fail_accepted = False
                code_s, payload_s, stdout_s, stderr_s = self._runtime(
                    ["wallet", "sign-challenge", "--message", _canonical_challenge_message(self.chain), "--chain", self.chain],
                    timeout=90,
                )
                if code_s != 0 or not bool(payload_s.get("ok")):
                    hardhat_sign_soft_fail = (
                        str(self.chain).strip().lower() == "hardhat_local"
                        and str(payload_s.get("code") or "") == "sign_failed"
                    )
                    if not hardhat_sign_soft_fail:
                        raise HarnessError(
                            "wallet sign-challenge preflight failed.",
                            code="wallet_passphrase_mismatch",
                            category="preflight_failure",
                            details={
                                "chain": self.chain,
                                "walletStorePath": wallet_store_path,
                                "passphraseSource": passphrase_source,
                                "payload": payload_s,
                                "stderr": _trim_text(stderr_s),
                                "stdout": _trim_text(stdout_s),
                            },
                        )
                    sign_soft_fail_accepted = True
                self.preflight["walletDecryptProbe"] = {
                    "ok": True,
                    "walletStorePath": wallet_store_path,
                    "passphraseSource": passphrase_source,
                    "chain": self.chain,
                    "walletHealthSoftFailAccepted": bool(
                        str(self.chain).strip().lower() == "hardhat_local"
                        and not isinstance(health_payload, dict)
                    ),
                    "signChallengeSoftFailAccepted": sign_soft_fail_accepted,
                    "passphraseRecoveredFromBackup": recovery_attempted,
                }
                return
            except HarnessError as exc:
                can_retry_recovery = (
                    (not recovery_attempted)
                    and (not bool(getattr(self.args, "disable_passphrase_recovery", False)))
                    and str(exc.code or "") == "wallet_passphrase_mismatch"
                )
                if can_retry_recovery:
                    recovered = _recover_local_passphrase_backup()
                    if recovered and recovered != self.wallet_passphrase:
                        self.wallet_passphrase = recovered
                        passphrase_source = "backup"
                        recovery_attempted = True
                        continue
                self.preflight["walletDecryptProbe"] = {
                    "ok": False,
                    "error": str(exc),
                    "walletStorePath": wallet_store_path,
                    "passphraseSource": passphrase_source,
                    "chain": self.chain,
                    "passphraseRecoveredFromBackup": recovery_attempted,
                }
                raise

    def _management_state(self) -> dict[str, Any]:
        status, body = self._http(
            "GET",
            f"/management/agent-state?agentId={urllib.parse.quote(self.agent_id)}&chainKey={urllib.parse.quote(self.chain)}",
            auth_mode="management",
        )
        if status != 200 or not bool(body.get("ok")):
            raise HarnessError(f"management agent-state failed ({status}): {body}")
        return body

    def _wait_for_transfer_approval_actionable(self, approval_id: str, *, timeout_sec: int = 30) -> dict[str, Any]:
        deadline = time.time() + timeout_sec
        last: dict[str, Any] = {}
        path = (
            f"/management/transfer-approvals?agentId={urllib.parse.quote(self.agent_id)}"
            f"&chainKey={urllib.parse.quote(self.chain)}"
        )
        while time.time() < deadline:
            status, body = self._http("GET", path, auth_mode="management")
            if status == 200 and bool(body.get("ok")):
                queue = body.get("queue") if isinstance(body.get("queue"), list) else []
                history = body.get("history") if isinstance(body.get("history"), list) else []
                for collection in (queue, history):
                    for item in collection:
                        if not isinstance(item, dict):
                            continue
                        if str(item.get("approval_id") or item.get("approvalId") or "").strip() != approval_id:
                            continue
                        current_status = str(item.get("status") or "").strip().lower()
                        last = item
                        if current_status in {"approval_pending", "approved"}:
                            return item
            time.sleep(1)
        raise HarnessError(
            f"Timed out waiting for transfer approval {approval_id} to become actionable; last={last}",
            code="transfer_approval_visibility_timeout",
            category="runtime_trade_failure",
            details={"approvalId": approval_id, "chain": self.chain, "last": last},
        )

    def _trade_read(self, trade_id: str) -> dict[str, Any]:
        status, body = self._http("GET", f"/trades/{urllib.parse.quote(trade_id)}", auth_mode="agent")
        if status != 200 or not bool(body.get("ok")):
            raise HarnessError(f"trade read failed ({status}) for {trade_id}: {body}")
        trade = body.get("trade")
        if not isinstance(trade, dict):
            raise HarnessError(f"trade read missing trade object: {body}")
        return trade

    def _wait_for_trade_status(self, trade_id: str, allowed: set[str], timeout_sec: int = 240) -> dict[str, Any]:
        deadline = time.time() + timeout_sec
        last: dict[str, Any] = {}
        while time.time() < deadline:
            trade = self._trade_read(trade_id)
            status = str(trade.get("status") or "").strip().lower()
            last = trade
            if status in allowed:
                return trade
            if "filled" in allowed and status == "verifying":
                tx_hash = str(trade.get("txHash") or "").strip()
                if tx_hash and self._trade_receipt_succeeded(tx_hash):
                    fallback = dict(trade)
                    fallback["status"] = "filled"
                    fallback["statusSource"] = "tx_receipt_fallback"
                    return fallback
            time.sleep(2)
        # For harness determinism, accept on-chain success as terminal "filled" when requested.
        if "filled" in allowed and str(last.get("status") or "").strip().lower() == "verifying":
            tx_hash = str(last.get("txHash") or "").strip()
            if tx_hash and self._trade_receipt_succeeded(tx_hash):
                fallback = dict(last)
                fallback["status"] = "filled"
                fallback["statusSource"] = "tx_receipt_fallback"
                return fallback
        raise HarnessError(f"Timed out waiting for trade {trade_id} status in {sorted(allowed)}; last={last}")

    def _trade_receipt_succeeded(self, tx_hash: str) -> bool:
        rpc_url = str((((self._chain_config().get("rpc") or {}) if isinstance(self._chain_config(), dict) else {}).get("primary")) or "").strip()
        if not rpc_url:
            return False
        proc = subprocess.run(
            ["cast", "receipt", tx_hash, "--rpc-url", rpc_url, "--json"],
            text=True,
            capture_output=True,
            timeout=45,
        )
        if proc.returncode == 0:
            try:
                payload = json.loads((proc.stdout or "{}").strip() or "{}")
            except Exception:
                payload = {}
            status = str(payload.get("status") or "").strip().lower()
            if status in {"0x1", "1"}:
                return True
        try:
            req = urllib.request.Request(
                rpc_url,
                data=json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "eth_getTransactionReceipt",
                        "params": [tx_hash],
                    }
                ).encode("utf-8"),
                headers={"content-type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                payload = json.loads((resp.read() or b"{}").decode("utf-8", errors="replace"))
        except Exception:
            return False
        result = payload.get("result") if isinstance(payload, dict) else None
        if not isinstance(result, dict):
            return False
        status = str(result.get("status") or "").strip().lower()
        return status in {"0x1", "1"}

    def _management_post_with_retry(
        self,
        path: str,
        payload: dict[str, Any],
        *,
        label: str,
        accepted_conflict_codes: set[str] | None = None,
    ) -> dict[str, Any]:
        attempts = max(1, int(self.args.max_api_retries))
        base_ms = max(1, int(self.args.api_retry_base_ms))
        payload_digest = _payload_hash(payload)
        failures: list[dict[str, Any]] = []
        accepted = accepted_conflict_codes or set()
        for attempt in range(1, attempts + 1):
            status, body = self._http("POST", path, body=payload, auth_mode="management")
            ok = status in {200, 202} and bool(body.get("ok"))
            if ok:
                return body
            request_id = str(body.get("requestId") or "").strip()
            code = str(body.get("code") or "")
            if status == 409 and code in accepted:
                accepted_body = dict(body)
                accepted_body["acceptedConflict"] = True
                return accepted_body
            failure = {
                "label": label,
                "path": path,
                "attempt": attempt,
                "status": status,
                "code": code,
                "requestId": request_id,
                "payloadHash": payload_digest,
                "body": _trim_text(body),
            }
            failures.append(failure)
            retryable = status in {0, 429, 500, 502, 503, 504}
            if (not retryable) or attempt >= attempts:
                self.retry_failures.extend(failures)
                raise HarnessError(
                    f"{label} failed after {attempt} attempt(s).",
                    code="management_api_retry_exhausted",
                    category="transient_api_failure",
                    details={"attempts": failures, "path": path, "payloadHash": payload_digest},
                )
            retry_after_sec = 0.0
            details = body.get("details")
            if status == 429 and isinstance(details, dict):
                raw_retry = details.get("retryAfterSeconds")
                try:
                    retry_after_sec = float(raw_retry)
                except Exception:
                    retry_after_sec = 0.0
            sleep_sec = retry_after_sec if retry_after_sec > 0 else (base_ms * (2 ** (attempt - 1))) / 1000.0
            sleep_sec += sleep_sec * random.uniform(0.0, 0.3)
            time.sleep(sleep_sec)
        raise HarnessError(f"{label} failed unexpectedly.", code="management_api_retry_exhausted", category="transient_api_failure")

    def _post_permissions_update(self, payload: dict[str, Any]) -> dict[str, Any]:
        transfer_keys = {"transferApprovalMode", "nativeTransferPreapproved", "allowedTransferTokens"}
        trade_outbound_keys = {
            "tradeApprovalMode",
            "allowedTokens",
            "outboundTransfersEnabled",
            "outboundMode",
            "outboundWhitelistAddresses",
        }
        result: dict[str, Any] = {"ok": True}

        has_transfer = any(key in payload for key in transfer_keys)
        if has_transfer:
            transfer_payload = {
                "agentId": payload.get("agentId"),
                "chainKey": payload.get("chainKey"),
                "transferApprovalMode": payload.get("transferApprovalMode", "per_transfer"),
                "nativeTransferPreapproved": bool(payload.get("nativeTransferPreapproved", False)),
                "allowedTransferTokens": payload.get("allowedTransferTokens", []),
            }
            transfer_result = self._management_post_with_retry(
                "/management/transfer-policy/update",
                transfer_payload,
                label="transfer_policy_update",
            )
            result["transferPolicy"] = transfer_result.get("transferPolicy")

        has_trade_or_outbound = any(key in payload for key in trade_outbound_keys)
        if has_trade_or_outbound:
            permissions_payload = {
                "agentId": payload.get("agentId"),
                "chainKey": payload.get("chainKey"),
            }
            for key in trade_outbound_keys:
                if key in payload:
                    permissions_payload[key] = payload[key]
            try:
                permissions_result = self._management_post_with_retry(
                    "/management/permissions/update",
                    permissions_payload,
                    label="permissions_update",
                )
            except HarnessError as exc:
                if not self._is_policy_snapshot_missing(exc):
                    raise
                self._seed_policy_snapshot(permissions_payload)
                permissions_result = self._management_post_with_retry(
                    "/management/permissions/update",
                    permissions_payload,
                    label="permissions_update",
                )
            result.update(permissions_result)

        return result

    def _is_policy_snapshot_missing(self, exc: HarnessError) -> bool:
        attempts = (exc.details or {}).get("attempts")
        if not isinstance(attempts, list) or not attempts:
            return False
        first = attempts[0]
        if not isinstance(first, dict):
            return False
        return int(first.get("status") or 0) == 409 and str(first.get("code") or "") == "policy_denied"

    def _seed_policy_snapshot(self, permissions_payload: dict[str, Any]) -> None:
        latest_policy = self.initial_state.get("latestPolicy") if isinstance(self.initial_state.get("latestPolicy"), dict) else {}
        raw_mode = str(latest_policy.get("mode") or "real").strip().lower()
        mode = raw_mode if raw_mode in {"mock", "real"} else "real"
        raw_approval_mode = str(latest_policy.get("approval_mode") or "per_trade").strip().lower()
        approval_mode = raw_approval_mode if raw_approval_mode in {"per_trade", "auto"} else "per_trade"
        allowed_tokens = latest_policy.get("allowed_tokens") if isinstance(latest_policy.get("allowed_tokens"), list) else []
        max_trade_usd = str(latest_policy.get("max_trade_usd") or "1000")
        max_daily_usd = str(latest_policy.get("max_daily_usd") or "10000")
        daily_cap_usd_enabled = bool(latest_policy.get("daily_cap_usd_enabled", True))
        daily_trade_cap_enabled = bool(latest_policy.get("daily_trade_cap_enabled", True))
        max_daily_trade_count = latest_policy.get("max_daily_trade_count")
        if max_daily_trade_count is not None:
            try:
                max_daily_trade_count = int(max_daily_trade_count)
            except Exception:
                max_daily_trade_count = None

        outbound_enabled = bool(permissions_payload.get("outboundTransfersEnabled", True))
        outbound_mode = str(permissions_payload.get("outboundMode") or "allow_all").strip().lower()
        if outbound_mode not in {"disabled", "allow_all", "whitelist"}:
            outbound_mode = "allow_all"
        outbound_whitelist = (
            permissions_payload.get("outboundWhitelistAddresses")
            if isinstance(permissions_payload.get("outboundWhitelistAddresses"), list)
            else []
        )

        seed_payload = {
            "agentId": self.agent_id,
            "chainKey": self.chain,
            "mode": mode,
            "approvalMode": approval_mode,
            "maxTradeUsd": max_trade_usd,
            "maxDailyUsd": max_daily_usd,
            "allowedTokens": allowed_tokens,
            "dailyCapUsdEnabled": daily_cap_usd_enabled,
            "dailyTradeCapEnabled": daily_trade_cap_enabled,
            "maxDailyTradeCount": max_daily_trade_count,
            "outboundTransfersEnabled": outbound_enabled,
            "outboundMode": outbound_mode,
            "outboundWhitelistAddresses": outbound_whitelist,
        }
        _ = self._management_post_with_retry("/management/policy/update", seed_payload, label="policy_snapshot_seed")

    def _restore_permissions(self) -> None:
        state = self.initial_state
        latest_policy = state.get("latestPolicy") if isinstance(state.get("latestPolicy"), dict) else {}
        transfer_policy = state.get("transferApprovalPolicy") if isinstance(state.get("transferApprovalPolicy"), dict) else {}
        trade_approval_mode = str(latest_policy.get("approval_mode") or "per_trade")
        allowed_tokens = latest_policy.get("allowed_tokens") if isinstance(latest_policy.get("allowed_tokens"), list) else []
        transfer_approval_mode = str(transfer_policy.get("transferApprovalMode") or "per_transfer")
        native_pre = bool(transfer_policy.get("nativeTransferPreapproved"))
        allowed_transfer_tokens = transfer_policy.get("allowedTransferTokens") if isinstance(transfer_policy.get("allowedTransferTokens"), list) else []
        payload = {
            "agentId": self.agent_id,
            "chainKey": self.chain,
            "tradeApprovalMode": trade_approval_mode,
            "allowedTokens": allowed_tokens,
            "transferApprovalMode": transfer_approval_mode,
            "nativeTransferPreapproved": native_pre,
            "allowedTransferTokens": allowed_transfer_tokens,
            "outboundTransfersEnabled": True,
            "outboundMode": "allow_all",
            "outboundWhitelistAddresses": [],
        }
        self._post_permissions_update(payload)

    def _set_chain_enabled(self, enabled: bool, *, label: str) -> None:
        _ = self._management_post_with_retry(
            "/management/chains/update",
            {
                "agentId": self.agent_id,
                "chainKey": self.chain,
                "chainEnabled": bool(enabled),
            },
            label=label,
        )

    def _balance_snapshot(self) -> dict[str, Decimal]:
        code, payload, _, stderr = self._runtime(["wallet", "balance", "--chain", self.chain], timeout=120)
        if code != 0 or not bool(payload.get("ok")):
            raise HarnessError(f"wallet balance failed: code={code} payload={payload} stderr={stderr}")
        out: dict[str, Decimal] = {}
        out["NATIVE"] = _safe_num(payload.get("balanceWei"))
        tokens = payload.get("tokens")
        if isinstance(tokens, list):
            for token in tokens:
                if not isinstance(token, dict):
                    continue
                symbol = str(token.get("symbol") or "").strip().upper()
                address = str(token.get("address") or "").strip().lower()
                balance = _safe_num(token.get("balanceWei"))
                if symbol:
                    out[symbol] = balance
                if address:
                    out[address] = balance
        return out

    def _wallet_address(self) -> str:
        code, payload, _, stderr = self._runtime(["wallet", "address", "--chain", self.chain], timeout=60)
        if code != 0 or not bool(payload.get("ok")):
            raise HarnessError(f"wallet address failed: code={code} payload={payload} stderr={stderr}")
        addr = str(payload.get("address") or "").strip()
        if not addr:
            raise HarnessError("wallet address response missing address")
        return addr

    def _ensure_local_wallet_policy_chain_enabled(self) -> None:
        policy_path = _agent_app_dir() / "policy.json"
        payload: dict[str, Any] = {}
        if policy_path.exists():
            try:
                existing = _read_json(policy_path)
            except Exception as exc:
                raise HarnessError(
                    "Local wallet policy file is unreadable.",
                    code="preflight_policy_invalid",
                    category="preflight_failure",
                    details={"path": str(policy_path), "error": _trim_text(exc)},
                )
            if not isinstance(existing, dict):
                raise HarnessError(
                    "Local wallet policy file must be a JSON object.",
                    code="preflight_policy_invalid",
                    category="preflight_failure",
                    details={"path": str(policy_path)},
                )
            payload = dict(existing)

        chains = payload.get("chains")
        if not isinstance(chains, dict):
            chains = {}
        chain_policy = chains.get(self.chain)
        if not isinstance(chain_policy, dict):
            chain_policy = {}
        chain_policy["chain_enabled"] = True
        chains[self.chain] = chain_policy
        payload["chains"] = chains

        spend = payload.get("spend")
        if not isinstance(spend, dict):
            spend = {}
        spend.setdefault("approval_required", False)
        spend.setdefault("approval_granted", True)
        spend.setdefault("max_daily_native_wei", "1000000000000000000000")
        payload["spend"] = spend
        if not isinstance(payload.get("paused"), bool):
            payload["paused"] = False

        policy_path.parent.mkdir(parents=True, exist_ok=True)
        policy_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def _assert_expected_wallet_address(self) -> None:
        expected = str(self.args.expected_wallet_address or "").strip().lower()
        if not expected:
            return
        actual = self._wallet_address().strip().lower()
        if actual != expected:
            raise HarnessError(
                "Runtime wallet address does not match expected address for this run.",
                code="wallet_address_mismatch",
                category="preflight_failure",
                details={"chain": self.chain, "expected": expected, "actual": actual},
            )

    def _chain_config(self) -> dict[str, Any]:
        if isinstance(self._chain_config_cache, dict):
            return self._chain_config_cache
        path = pathlib.Path("config/chains") / f"{self.chain}.json"
        if not path.exists():
            raise HarnessError(
                "Chain config is missing for harness chain.",
                code="chain_config_missing",
                category="preflight_failure",
                details={"chain": self.chain, "path": str(path)},
            )
        payload = _read_json(path)
        self._chain_config_cache = payload
        return payload

    def _canonical_token_address(self, symbol: str) -> str:
        cfg = self._chain_config()
        tokens = cfg.get("canonicalTokens")
        if not isinstance(tokens, dict):
            raise HarnessError(
                "Chain config canonicalTokens is invalid.",
                code="chain_config_invalid",
                category="preflight_failure",
                details={"chain": self.chain, "field": "canonicalTokens"},
            )
        raw = str(tokens.get(symbol) or "").strip()
        chain_normalized = str(self.chain).strip().lower()
        if not raw and chain_normalized in {"solana_localnet", "solana_devnet"}:
            if symbol == "USDC":
                raw = self._solana_chain_mint("stable")
            elif symbol in {"WETH", "WSOL"}:
                raw = self._solana_chain_mint("wrapped")
        if not raw and symbol == "USDC" and chain_normalized == "solana_localnet":
            raw = SOLANA_USDC_MINT
        if not raw:
            raise HarnessError(
                f"Chain config missing canonical token address for {symbol}.",
                code="chain_config_invalid",
                category="preflight_failure",
                details={"chain": self.chain, "symbol": symbol},
            )
        return raw

    def _trade_args(self, amount_in: str) -> list[str]:
        amount_value = str(amount_in).strip()
        chain_normalized = str(self.chain).strip().lower()
        if chain_normalized.startswith("solana_"):
            token_in = str(self.trade_token_in or "").strip()
            stable_mint = self._solana_chain_mint("stable")
            wrapped_mint = self._solana_chain_mint("wrapped")
            decimals = 9
            if token_in.upper() == "SOL":
                decimals = 9
            elif token_in.lower() in {SOLANA_USDC_MINT.lower(), stable_mint.lower(), "usdc"}:
                decimals = 6
            elif token_in.lower() in {wrapped_mint.lower(), "weth"}:
                decimals = 9
            amount_value = str(int((_safe_num(amount_value) * (Decimal(10) ** decimals)).to_integral_value()))
        return [
            "trade",
            "spot",
            "--chain",
            self.chain,
            "--token-in",
            self.trade_token_in,
            "--token-out",
            self.trade_token_out,
            "--amount-in",
            amount_value,
            "--slippage-bps",
            "100",
        ]

    def _has_chain_capability(self, capability: str) -> bool:
        cfg = self._chain_config()
        caps = cfg.get("capabilities")
        if not isinstance(caps, dict):
            return capability == "wallet"
        raw = caps.get(capability)
        if raw is None:
            return capability == "wallet"
        return bool(raw)

    def _liquidity_dex(self) -> str:
        cfg = self._chain_config()
        core = cfg.get("coreContracts")
        if isinstance(core, dict):
            dex = str(core.get("dex") or "").strip()
            if dex:
                return dex
        chain_normalized = str(self.chain).strip().lower()
        if chain_normalized == "solana_localnet":
            return "local_clmm"
        if chain_normalized.startswith("solana_"):
            return "raydium_clmm"
        return "uniswap_v2"

    def _attempt_faucet_topup(self, *, require_native_topup: bool = False) -> None:
        chain_normalized = str(self.chain).strip().lower()
        if not self._has_chain_capability("faucet"):
            return
        baseline_native = Decimal("0")
        if require_native_topup:
            baseline_native = self._balance_snapshot().get("NATIVE", Decimal("0"))
        assets = ["native"]
        wrapped_key = ""
        stable_key = ""
        if chain_normalized == "base_sepolia":
            assets = ["stable", "wrapped", "native"]
        elif chain_normalized in {"solana_localnet", "solana_devnet"}:
            assets = ["native", "stable", "wrapped"]
            stable_key = self._solana_chain_mint("stable").lower()
            wrapped_key = self._solana_chain_mint("wrapped").lower()
        faucet_args = ["faucet-request", "--chain", self.chain]
        for asset in assets:
            faucet_args.extend(["--asset", asset])
        _ = self._runtime(faucet_args, timeout=120)
        for _i in range(6):
            bal = self._balance_snapshot()
            if require_native_topup and bal.get("NATIVE", Decimal("0")) > baseline_native:
                return
            if chain_normalized == "solana_localnet":
                if bal.get("NATIVE", Decimal("0")) > baseline_native:
                    return
                if stable_key and bal.get(stable_key, Decimal("0")) > 0:
                    return
                if wrapped_key and bal.get(wrapped_key, Decimal("0")) > 0:
                    return
            if bal.get("USDC", Decimal("0")) > 0 or bal.get("WETH", Decimal("0")) > 0:
                return
            if chain_normalized.startswith("solana_") and bal.get("NATIVE", Decimal("0")) > baseline_native:
                return
            time.sleep(8)

    def _bootstrap_hardhat_local_token_funding(self) -> None:
        if str(self.chain).strip().lower() != "hardhat_local":
            return
        recipient = self._wallet_address()
        rpc_url = str(self.args.hardhat_rpc_url).strip() or "http://127.0.0.1:8545"
        signer_pk = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
        for symbol, amount in (("WETH", "1000000000000000"), ("USDC", "1000000000000000000")):
            token = self._canonical_token_address(symbol)
            cmd = [
                "cast",
                "send",
                token,
                "transfer(address,uint256)",
                recipient,
                amount,
                "--private-key",
                signer_pk,
                "--rpc-url",
                rpc_url,
            ]
            proc = subprocess.run(cmd, text=True, capture_output=True, timeout=60)
            if proc.returncode != 0:
                raise HarnessError(
                    f"hardhat_local token bootstrap transfer failed for {symbol}.",
                    code="scenario_funding_missing",
                    category="preflight_failure",
                    details={"chain": self.chain, "symbol": symbol, "stderr": _trim_text(proc.stderr), "stdout": _trim_text(proc.stdout)},
                )
        for _i in range(5):
            bal = self._balance_snapshot()
            if bal.get("USDC", Decimal("0")) > 0 or bal.get("WETH", Decimal("0")) > 0:
                return
            time.sleep(2)

    def _bootstrap_ethereum_sepolia_funding(self) -> None:
        chain_normalized = str(self.chain).strip().lower()
        if chain_normalized not in {"ethereum_sepolia", "hardhat_local"}:
            return
        self._ensure_local_wallet_policy_chain_enabled()
        bal = self._balance_snapshot()
        usdc = bal.get("USDC", Decimal("0"))
        weth = bal.get("WETH", Decimal("0"))
        native = bal.get("NATIVE", Decimal("0"))
        if usdc > 0 or weth > 0:
            return
        if native <= 0:
            raise HarnessError(
                "No usable native ETH balance detected for chain bootstrap.",
                code="scenario_funding_missing",
                category="preflight_failure",
                details={"chain": self.chain, "nativeWei": str(native)},
            )

        # Ensure transfer policy is permissive so wrap executes immediately without resume.
        self._post_permissions_update(
            {
                "agentId": self.agent_id,
                "chainKey": self.chain,
                "transferApprovalMode": "auto",
                "nativeTransferPreapproved": True,
                "allowedTransferTokens": [],
                "outboundTransfersEnabled": True,
                "outboundMode": "allow_all",
                "outboundWhitelistAddresses": [],
            }
        )

        # Wrap a small ETH amount by sending native ETH to canonical WETH.
        reserve_wei = Decimal("100000000000000")  # 0.0001 ETH gas reserve
        target_wrap_wei = Decimal("200000000000000")  # 0.0002 ETH
        wrap_wei = min(target_wrap_wei, native - reserve_wei)
        if wrap_wei <= 0:
            raise HarnessError(
                "Insufficient ETH to reserve gas and bootstrap WETH funding.",
                code="scenario_funding_missing",
                category="preflight_failure",
                details={"chain": self.chain, "nativeWei": str(native), "requiredReserveWei": str(reserve_wei)},
            )

        wrap_to = self._canonical_token_address("WETH")
        c_wrap, p_wrap, _, e_wrap = self._runtime(
            ["wallet", "send", "--to", wrap_to, "--amount-wei", str(int(wrap_wei)), "--chain", self.chain],
            timeout=240,
        )
        if c_wrap != 0 or not bool(p_wrap.get("ok")):
            raise HarnessError(f"eth->weth bootstrap send failed: {p_wrap} stderr={e_wrap}")

        for _i in range(6):
            bal = self._balance_snapshot()
            if bal.get("WETH", Decimal("0")) > 0:
                break
            time.sleep(4)
        bal = self._balance_snapshot()
        if bal.get("WETH", Decimal("0")) <= 0:
            raise HarnessError(
                "Chain bootstrap did not produce WETH balance.",
                code="scenario_funding_missing",
                category="preflight_failure",
                details={"chain": self.chain, "wethWei": str(bal.get("WETH", Decimal("0")))},
            )

        self._post_permissions_update(
            {
                "agentId": self.agent_id,
                "chainKey": self.chain,
                "tradeApprovalMode": "auto",
            }
        )
        c_trade, p_trade, _, e_trade = self._runtime(
            [
                "trade",
                "spot",
                "--chain",
                self.chain,
                "--token-in",
                "WETH",
                "--token-out",
                "USDC",
                "--amount-in",
                "0.00005",
                "--slippage-bps",
                "100",
            ],
            timeout=300,
        )
        pending_codes = {"approval_required", "approval_pending"}
        status = str(p_trade.get("status") or "").strip().lower()
        if c_trade != 0 and str(p_trade.get("code") or "") not in pending_codes:
            raise HarnessError(f"weth->usdc bootstrap trade failed: {p_trade} stderr={e_trade}")
        trade_id = _extract_trade_id(p_trade)
        if trade_id:
            self.created_trade_ids.append(trade_id)
        if (c_trade != 0 or status == "approval_pending") and str(p_trade.get("code") or "") in pending_codes:
            if not trade_id:
                raise HarnessError(f"bootstrap trade missing tradeId for approval flow: {p_trade}")
            _ = self._management_post_with_retry(
                "/management/approvals/decision",
                {"agentId": self.agent_id, "tradeId": trade_id, "decision": "approve"},
                label="bootstrap_trade_decision_approve",
            )
            code, resume_payload, _, resume_stderr = self._runtime(
                ["approvals", "resume-spot", "--trade-id", trade_id, "--chain", self.chain], timeout=420
            )
            if code != 0 or not bool(resume_payload.get("ok")):
                raise HarnessError(f"bootstrap trade resume failed: {resume_payload} stderr={resume_stderr}")
            terminal = self._wait_for_trade_status(trade_id, {"filled", "failed", "rejected"}, timeout_sec=420)
            if str(terminal.get("status") or "").strip().lower() != "filled":
                raise HarnessError(f"bootstrap trade terminal status expected filled, got {terminal}")

        for _i in range(6):
            bal = self._balance_snapshot()
            if bal.get("USDC", Decimal("0")) > 0 or bal.get("WETH", Decimal("0")) > 0:
                return
            time.sleep(4)

    def _prepare_trade_pair_and_amounts(self) -> None:
        chain_normalized = str(self.chain).strip().lower()
        if chain_normalized.startswith("solana_"):
            bal = self._balance_snapshot()
            native = bal.get("NATIVE", Decimal("0"))
            stable_mint = self._canonical_token_address("USDC")
            wrapped_mint = self._solana_chain_mint("wrapped")
            stable = bal.get(stable_mint.lower(), Decimal("0")) or bal.get("USDC", Decimal("0"))
            wrapped = bal.get(wrapped_mint.lower(), Decimal("0")) if wrapped_mint else Decimal("0")
            if native <= 0 and self._has_chain_capability("faucet"):
                self._attempt_faucet_topup(require_native_topup=True)
                bal = self._balance_snapshot()
                native = bal.get("NATIVE", Decimal("0"))
                stable = bal.get(stable_mint.lower(), Decimal("0")) or bal.get("USDC", Decimal("0"))
                wrapped = bal.get(wrapped_mint.lower(), Decimal("0")) if wrapped_mint else Decimal("0")
            if chain_normalized == "solana_devnet":
                self._solana_devnet_trade_pair_discovery = self._discover_solana_devnet_trade_pair(bal)
                self.preflight["solanaDevnetTradePair"] = self._solana_devnet_trade_pair_discovery
                if bool(self._solana_devnet_trade_pair_discovery.get("quoteable")):
                    self.trade_token_in = str(self._solana_devnet_trade_pair_discovery.get("tokenIn") or "SOL")
                    self.trade_token_out = str(self._solana_devnet_trade_pair_discovery.get("tokenOut") or stable_mint)
                    self.trade_amounts = self._solana_trade_amounts_for_token(self.trade_token_in)
                    return
                if native > 0 or stable > 0 or wrapped > 0:
                    self.trade_token_in = stable_mint or wrapped_mint or "SOL"
                    self.trade_token_out = "SOL"
                    self.trade_amounts = self._solana_trade_amounts_for_token(self.trade_token_in)
                    return
            if native > 0:
                self.trade_token_in = "SOL"
                self.trade_token_out = stable_mint
                self.trade_amounts = {
                    "pending_approve": "0.001",
                    "reject": "0.0008",
                    "dedupe": "0.0007",
                    "global_auto": "0.0006",
                    "allowlist": "0.0005",
                    "rebalance": "0.0004",
                }
                return
            if stable > 0:
                self.trade_token_in = stable_mint
                self.trade_token_out = "SOL"
                self.trade_amounts = {
                    "pending_approve": "0.5",
                    "reject": "0.4",
                    "dedupe": "0.3",
                    "global_auto": "0.2",
                    "allowlist": "0.15",
                    "rebalance": "0.1",
                }
                return
            raise HarnessError(
                "No usable Solana trade funding detected for configured trade pair.",
                code="scenario_funding_missing",
                category="preflight_failure",
                details={
                    "chain": self.chain,
                    "walletAddress": self._wallet_address(),
                    "nativeAtomic": str(native),
                    "stableAtomic": str(stable),
                    "wrappedAtomic": str(wrapped),
                    "stableMint": stable_mint,
                    "wrappedMint": wrapped_mint,
                },
            )
        bal = self._balance_snapshot()
        usdc = bal.get("USDC", Decimal("0"))
        weth = bal.get("WETH", Decimal("0"))
        if usdc <= 0 and weth <= 0:
            self._attempt_faucet_topup()
            self._bootstrap_ethereum_sepolia_funding()
            self._bootstrap_hardhat_local_token_funding()
            bal = self._balance_snapshot()
            usdc = bal.get("USDC", Decimal("0"))
            weth = bal.get("WETH", Decimal("0"))

        if chain_normalized == "ethereum_sepolia" and weth > 0:
            self.trade_token_in = "WETH"
            self.trade_token_out = "USDC"
            self.trade_amounts = {
                "pending_approve": "0.00005",
                "reject": "0.00003",
                "dedupe": "0.00002",
                "global_auto": "0.00005",
                "allowlist": "0.00005",
                "rebalance": "0.00001",
            }
            return
        if usdc > 0:
            self.trade_token_in = "USDC"
            self.trade_token_out = "WETH"
            self.trade_amounts = {
                "pending_approve": "0.05",
                "reject": "0.03",
                "dedupe": "0.02",
                "global_auto": "0.01",
                "allowlist": "0.015",
                "rebalance": "0.005",
            }
            return
        if weth > 0:
            self.trade_token_in = "WETH"
            self.trade_token_out = "USDC"
            self.trade_amounts = {
                "pending_approve": "0.00005",
                "reject": "0.00003",
                "dedupe": "0.00002",
                "global_auto": "0.00001",
                "allowlist": "0.00001",
                "rebalance": "0.000005",
            }
            return
        raise HarnessError(
            "No usable trade funding detected for configured chain trade pair.",
            code="scenario_funding_missing",
            category="preflight_failure",
            details={
                "chain": self.chain,
                "usdcWei": str(usdc),
                "wethWei": str(weth),
            },
        )

    def _scenario_trade_pending_approve(self) -> dict[str, Any]:
        self._raise_if_solana_devnet_trade_pair_unavailable()
        self._raise_if_solana_devnet_custom_mint_trade_preflight_unsupported(phase="trade_pending_approve_preflight")
        self._post_permissions_update(
            {
                "agentId": self.agent_id,
                "chainKey": self.chain,
                "tradeApprovalMode": "per_trade",
                "allowedTokens": [],
            }
        )
        code, payload, _, stderr = self._runtime(
            self._trade_args(self.trade_amounts["pending_approve"])
        )
        if code == 0 and str(payload.get("status") or "").strip().lower() != "approval_pending":
            raise HarnessError(f"trade expected approval_pending but command succeeded: {payload}")
        if code != 0 and str(payload.get("code") or "") not in {"approval_required", "approval_pending"}:
            raise HarnessError(f"trade proposal failed unexpectedly: {payload} stderr={stderr}")
        trade_id = _extract_trade_id(payload)
        if not trade_id:
            raise HarnessError(f"trade proposal missing tradeId: {payload}")
        self.created_trade_ids.append(trade_id)

        _ = self._management_post_with_retry(
            "/management/approvals/decision",
            {"agentId": self.agent_id, "tradeId": trade_id, "decision": "approve"},
            label="trade_decision_approve",
        )

        resume_code, resume_payload, _, resume_stderr = self._runtime(
            ["approvals", "resume-spot", "--trade-id", trade_id, "--chain", self.chain],
            timeout=420,
        )
        resume_payload_code = str(resume_payload.get("code") or "").strip().lower()
        self._raise_if_solana_devnet_custom_mint_quote_unsupported(
            resume_payload,
            phase="resume_after_approve",
            trade_id=trade_id,
            stderr=resume_stderr,
        )
        if (resume_code != 0 or not bool(resume_payload.get("ok"))) and resume_payload_code != "not_actionable":
            raise HarnessError(f"trade resume failed after approval: {resume_payload} stderr={resume_stderr}")

        terminal = self._wait_for_trade_status(trade_id, {"filled", "failed", "rejected"}, timeout_sec=420)
        self._raise_if_solana_devnet_custom_mint_quote_unsupported(
            terminal,
            phase="terminal_after_approve",
            trade_id=trade_id,
        )
        if str(terminal.get("status") or "") != "filled":
            raise HarnessError(f"trade terminal status expected filled, got {terminal}")
        return {"tradeId": trade_id, "terminalStatus": terminal.get("status"), "txHash": terminal.get("txHash")}

    def _scenario_trade_reject(self) -> dict[str, Any]:
        self._raise_if_solana_devnet_trade_pair_unavailable()
        self._post_permissions_update(
            {
                "agentId": self.agent_id,
                "chainKey": self.chain,
                "tradeApprovalMode": "per_trade",
                "allowedTokens": [],
            }
        )
        code, payload, _, stderr = self._runtime(
            self._trade_args(self.trade_amounts["reject"])
        )
        if code != 0 and str(payload.get("code") or "") not in {"approval_required", "approval_pending"}:
            raise HarnessError(f"trade reject scenario proposal failed: {payload} stderr={stderr}")
        trade_id = _extract_trade_id(payload)
        if not trade_id:
            raise HarnessError("trade reject scenario missing tradeId")
        self.created_trade_ids.append(trade_id)

        _ = self._management_post_with_retry(
            "/management/approvals/decision",
            {"agentId": self.agent_id, "tradeId": trade_id, "decision": "reject", "reasonMessage": "harness reject path"},
            label="trade_decision_reject",
        )

        terminal = self._wait_for_trade_status(trade_id, {"rejected"}, timeout_sec=180)
        if terminal.get("txHash"):
            raise HarnessError(f"rejected trade should not have txHash: {terminal}")
        return {"tradeId": trade_id, "terminalStatus": terminal.get("status")}

    def _scenario_trade_dedupe(self) -> dict[str, Any]:
        self._raise_if_solana_devnet_trade_pair_unavailable()
        self._post_permissions_update(
            {
                "agentId": self.agent_id,
                "chainKey": self.chain,
                "tradeApprovalMode": "per_trade",
                "allowedTokens": [],
            }
        )
        args = [
            *self._trade_args(self.trade_amounts["dedupe"]),
        ]
        c1, p1, _, _ = self._runtime(args)
        c2, p2, _, _ = self._runtime(args)
        if c1 != 0 and str(p1.get("code") or "") not in {"approval_required", "approval_pending"}:
            raise HarnessError(f"dedupe first proposal failed: {p1}")
        if c2 != 0 and str(p2.get("code") or "") not in {"approval_required", "approval_pending"}:
            raise HarnessError(f"dedupe second proposal failed: {p2}")
        t1 = _extract_trade_id(p1)
        t2 = _extract_trade_id(p2)
        if not t1 or not t2:
            raise HarnessError(f"dedupe trade ids missing: t1={t1} t2={t2}")
        if t1 != t2:
            if str(self.chain).strip().lower().startswith("solana_"):
                _ = self._management_post_with_retry(
                    "/management/approvals/decision",
                    {"agentId": self.agent_id, "tradeId": t1, "decision": "reject", "reasonMessage": "solana dedupe cleanup 1"},
                    label="trade_decision_dedupe_reject_sol_1",
                )
                _ = self._management_post_with_retry(
                    "/management/approvals/decision",
                    {"agentId": self.agent_id, "tradeId": t2, "decision": "reject", "reasonMessage": "solana dedupe cleanup 2"},
                    label="trade_decision_dedupe_reject_sol_2",
                )
                _ = self._wait_for_trade_status(t1, {"rejected"}, timeout_sec=180)
                _ = self._wait_for_trade_status(t2, {"rejected"}, timeout_sec=180)
                return {
                    "dedupeSupported": False,
                    "reason": "solana_pending_trade_reuse_unsupported",
                    "firstTradeId": t1,
                    "secondTradeId": t2,
                }
            raise HarnessError(f"dedupe expected same pending trade id, got {t1} vs {t2}")
        self.created_trade_ids.append(t1)

        _ = self._management_post_with_retry(
            "/management/approvals/decision",
            {"agentId": self.agent_id, "tradeId": t1, "decision": "reject", "reasonMessage": "dedupe cleanup"},
            label="trade_decision_dedupe_reject_1",
        )
        _ = self._wait_for_trade_status(t1, {"rejected"}, timeout_sec=180)

        c3, p3, _, _ = self._runtime(args)
        if c3 != 0 and str(p3.get("code") or "") not in {"approval_required", "approval_pending"}:
            raise HarnessError(f"dedupe post-terminal proposal failed: {p3}")
        t3 = _extract_trade_id(p3)
        if not t3:
            raise HarnessError(f"dedupe post-terminal missing trade id: {p3}")
        if t3 == t1:
            raise HarnessError("dedupe expected new trade id after terminal state")
        self.created_trade_ids.append(t3)
        # cleanup
        _ = self._management_post_with_retry(
            "/management/approvals/decision",
            {"agentId": self.agent_id, "tradeId": t3, "decision": "reject", "reasonMessage": "dedupe cleanup 2"},
            label="trade_decision_dedupe_reject_2",
        )
        _ = self._wait_for_trade_status(t3, {"rejected"}, timeout_sec=180)
        return {"firstTradeId": t1, "secondTradeId": t3}

    def _scenario_global_and_allowlist(self) -> dict[str, Any]:
        self._raise_if_solana_devnet_trade_pair_unavailable()
        self._raise_if_solana_devnet_custom_mint_trade_preflight_unsupported(phase="global_auto_preflight")
        # Global auto on
        self._post_permissions_update(
            {
                "agentId": self.agent_id,
                "chainKey": self.chain,
                "tradeApprovalMode": "auto",
            }
        )
        c_auto, p_auto, _, err_auto = self._runtime(
            self._trade_args(self.trade_amounts["global_auto"])
        )
        self._raise_if_solana_devnet_custom_mint_quote_unsupported(
            p_auto,
            phase="global_auto",
            stderr=err_auto,
        )
        if c_auto != 0:
            raise HarnessError(f"global auto trade failed: {p_auto} stderr={err_auto}")

        # per-trade + allowlist via approve-allowlist-token
        self._post_permissions_update(
            {
                "agentId": self.agent_id,
                "chainKey": self.chain,
                "tradeApprovalMode": "per_trade",
                "allowedTokens": [],
            }
        )
        c2, p2, _, err2 = self._runtime(
            self._trade_args(self.trade_amounts["allowlist"])
        )
        if c2 != 0 and str(p2.get("code") or "") not in {"approval_required", "approval_pending"}:
            raise HarnessError(f"allowlist proposal failed: {p2} stderr={err2}")
        trade_id = _extract_trade_id(p2)
        if not trade_id:
            raise HarnessError("allowlist proposal missing trade id")
        self.created_trade_ids.append(trade_id)

        body = self._management_post_with_retry(
            "/management/approvals/approve-allowlist-token",
            {"agentId": self.agent_id, "tradeId": trade_id},
            label="trade_allowlist_approve",
        )

        code, resume_payload, _, resume_err = self._runtime(
            ["approvals", "resume-spot", "--trade-id", trade_id, "--chain", self.chain], timeout=420
        )
        self._raise_if_solana_devnet_custom_mint_quote_unsupported(
            resume_payload,
            phase="allowlist_resume",
            trade_id=trade_id,
            stderr=resume_err,
        )
        if code != 0 or not bool(resume_payload.get("ok")):
            raise HarnessError(f"allowlist resume failed: {resume_payload} stderr={resume_err}")

        state = self._management_state()
        latest_policy = state.get("latestPolicy") if isinstance(state.get("latestPolicy"), dict) else {}
        allowed_tokens = latest_policy.get("allowed_tokens") if isinstance(latest_policy.get("allowed_tokens"), list) else []
        if not any(str(v).lower() == str(body.get("allowlistedToken") or "").lower() for v in allowed_tokens):
            raise HarnessError(f"allowlisted token missing from latest policy: {allowed_tokens}")
        return {"tradeId": trade_id, "allowlistedToken": body.get("allowlistedToken")}

    def _scenario_transfer_only(self) -> dict[str, Any]:
        recipient = (self.args.recipient_address or self._wallet_address()).strip()
        native_transfer_amount = "1000" if str(self.chain).strip().lower().startswith("solana_") else "1000000000000000"
        token_transfer_amount = "1000" if str(self.chain).strip().lower().startswith("solana_") else "1000000000000000000"
        transfer_token = self.trade_token_in
        if str(self.chain).strip().lower().startswith("solana_") and str(transfer_token).strip().upper() == "SOL":
            transfer_token = self._solana_chain_mint("stable") or self._solana_chain_mint("wrapped") or transfer_token
        self._post_permissions_update(
            {
                "agentId": self.agent_id,
                "chainKey": self.chain,
                "transferApprovalMode": "per_transfer",
                "nativeTransferPreapproved": False,
                "allowedTransferTokens": [],
                "outboundTransfersEnabled": True,
                "outboundMode": "allow_all",
                "outboundWhitelistAddresses": [],
            }
        )

        # Native transfer approve
        c1, p1, _, e1 = self._runtime(
            ["wallet", "send", "--to", recipient, "--amount-wei", native_transfer_amount, "--chain", self.chain]
        )
        if c1 != 0 and str(p1.get("code") or "") not in {"approval_required", "approval_pending"}:
            raise HarnessError(f"native transfer proposal failed: {p1} stderr={e1}")
        appr1 = _extract_transfer_approval_id(p1)
        if not appr1:
            raise HarnessError(f"native transfer missing approval id: {p1}")
        self.created_transfer_approval_ids.append(appr1)

        _ = self._management_post_with_retry(
            "/management/transfer-approvals/decision",
            {"agentId": self.agent_id, "approvalId": appr1, "decision": "approve", "chainKey": self.chain},
            label="transfer_decision_native_approve",
            accepted_conflict_codes={"not_actionable"},
        )
        _ = self._runtime(["approvals", "resume-transfer", "--approval-id", appr1, "--chain", self.chain], timeout=240)

        # ERC20 deny
        c2, p2, _, e2 = self._runtime(
            [
                "wallet",
                "send-token",
                "--token",
                transfer_token,
                "--to",
                recipient,
                "--amount-wei",
                token_transfer_amount,
                "--chain",
                self.chain,
            ]
        )
        if c2 != 0 and str(p2.get("code") or "") not in {"approval_required", "approval_pending"}:
            raise HarnessError(f"erc20 transfer proposal failed: {p2} stderr={e2}")
        appr2 = _extract_transfer_approval_id(p2)
        if not appr2:
            raise HarnessError(f"erc20 transfer missing approval id: {p2}")
        self.created_transfer_approval_ids.append(appr2)

        _ = self._management_post_with_retry(
            "/management/transfer-approvals/decision",
            {"agentId": self.agent_id, "approvalId": appr2, "decision": "deny", "chainKey": self.chain, "reasonMessage": "harness deny path"},
            label="transfer_decision_erc20_deny",
            accepted_conflict_codes={"not_actionable"},
        )
        return {"nativeApprovalId": appr1, "erc20ApprovalId": appr2}

    def _scenario_solana_devnet_trade_evidence_boundary(self) -> dict[str, Any]:
        self._raise_if_solana_devnet_trade_pair_unavailable()
        return {"quoteable": True}

    def _scenario_x402_or_capability_assertion(self) -> dict[str, Any]:
        if not self._has_chain_capability("x402"):
            c_recv, p_recv, _, _ = self._runtime(
                [
                    "x402",
                    "receive-request",
                    "--network",
                    self.chain,
                    "--facilitator",
                    "cdp",
                    "--amount-atomic",
                    "1",
                    "--asset-kind",
                    "native",
                    "--resource-description",
                    "slice117 capability assertion",
                ]
            )
            if c_recv == 0 or str(p_recv.get("code") or "") != "unsupported_chain_capability":
                raise HarnessError(f"x402 expected unsupported_chain_capability, got {p_recv}")
            return {"assertedUnsupportedCode": "unsupported_chain_capability", "network": self.chain}

        # x402 receive + pay approve
        c_recv, p_recv, _, e_recv = self._runtime(
            [
                "x402",
                "receive-request",
                "--network",
                self.chain,
                "--facilitator",
                "cdp",
                "--amount-atomic",
                "1",
                "--asset-kind",
                "native",
                "--resource-description",
                "slice96 harness loopback",
            ]
        )
        if (
            str(self.chain).strip().lower() == "solana_localnet"
            and c_recv != 0
            and str(p_recv.get("code") or "") == "x402_runtime_error"
            and "not configured" in str(p_recv.get("message") or "").lower()
        ):
            return {"assertedUnsupportedCode": "x402_facilitator_unconfigured", "network": self.chain}
        if c_recv != 0 or not bool(p_recv.get("ok")):
            raise HarnessError(f"x402 receive request failed: {p_recv} stderr={e_recv}")
        payment_url = str(p_recv.get("paymentUrl") or "").strip()
        if not payment_url:
            raise HarnessError(f"x402 receive request missing paymentUrl: {p_recv}")

        code_pay, pay_payload, _, pay_err = self._runtime(
            [
                "x402",
                "pay",
                "--url",
                payment_url,
                "--network",
                self.chain,
                "--facilitator",
                "cdp",
                "--amount-atomic",
                "1",
            ]
        )
        if (
            str(self.chain).strip().lower().startswith("solana_")
            and code_pay != 0
            and str(pay_payload.get("code") or "") == "x402_runtime_error"
            and "not configured" in str(pay_payload.get("message") or "").lower()
        ):
            return {"assertedUnsupportedCode": "x402_facilitator_unconfigured", "network": self.chain}
        if code_pay != 0 and str(pay_payload.get("code") or "") not in {"approval_required", "approval_pending"}:
            raise HarnessError(f"x402 pay proposal failed: {pay_payload} stderr={pay_err}")
        approval = pay_payload.get("approval") if isinstance(pay_payload.get("approval"), dict) else {}
        approval_id = str(approval.get("approvalId") or "").strip()
        if not approval_id:
            raise HarnessError(f"x402 pay approval id missing: {pay_payload}")
        self.created_x402_approval_ids.append(approval_id)
        _ = self._wait_for_transfer_approval_actionable(approval_id)

        _ = self._management_post_with_retry(
            "/management/transfer-approvals/decision",
            {"agentId": self.agent_id, "approvalId": approval_id, "decision": "approve", "chainKey": self.chain},
            label="x402_decision_approve",
            accepted_conflict_codes={"not_actionable"},
        )
        _ = self._runtime(["x402", "pay-resume", "--approval-id", approval_id], timeout=240)
        return {"x402ApprovalId": approval_id}

    def _scenario_liquidity_and_pause(self) -> dict[str, Any]:
        if str(self.chain).strip().lower() == "solana_localnet":
            localnet_preflight = self.preflight.get("solanaLocalnetBootstrap")
            if isinstance(localnet_preflight, dict) and not bool(localnet_preflight.get("ok")):
                return {
                    "liquiditySupported": False,
                    "liquidityUnsupportedReason": "solana_localnet_preflight_blocked",
                    "liquidityUnsupportedDetails": localnet_preflight,
                }
        self._post_permissions_update(
            {
                "agentId": self.agent_id,
                "chainKey": self.chain,
                "tradeApprovalMode": "per_trade",
            }
        )
        c_add, p_add, _, e_add = self._runtime(
            [
                "liquidity",
                "add",
                "--chain",
                self.chain,
                "--dex",
                self._liquidity_dex(),
                "--token-a",
                self.trade_token_in,
                "--token-b",
                self.trade_token_out,
                "--amount-a",
                self.trade_amounts.get("allowlist", "0.015"),
                "--amount-b",
                self.trade_amounts.get("global_auto", "0.01"),
                "--slippage-bps",
                "100",
            ],
            timeout=300,
        )
        code = str(p_add.get("code") or "")
        if c_add != 0 and code not in {"approval_required", "approval_pending", "liquidity_preflight_failed", "unsupported_liquidity_adapter", "unsupported_liquidity_execution_family", "chain_config_invalid"}:
            raise HarnessError(f"liquidity add proposal failed: {p_add} stderr={e_add}")
        liq_id = _extract_liquidity_intent_id(p_add)
        liq_status = str(p_add.get("status") or "").strip().lower()
        if not liq_id and code in {"liquidity_preflight_failed", "unsupported_liquidity_adapter", "unsupported_liquidity_execution_family", "chain_config_invalid"}:
            return {
                "liquiditySupported": False,
                "liquidityUnsupportedReason": code,
                "liquidityUnsupportedDetails": (p_add.get("details") if isinstance(p_add.get("details"), dict) else {}),
            }
        if liq_id:
            self.created_liquidity_intent_ids.append(liq_id)
            if liq_status in {"", "approval_pending", "pending"}:
                _ = self._management_post_with_retry(
                    "/management/approvals/decision",
                    {
                        "agentId": self.agent_id,
                        "subjectType": "liquidity",
                        "liquidityIntentId": liq_id,
                        "decision": "approve",
                    },
                    label="liquidity_decision_approve",
                    accepted_conflict_codes={"liquidity_invalid_transition"},
                )
                _ = self._runtime(["liquidity", "resume", "--intent", liq_id, "--chain", self.chain], timeout=420)

        # Pause -> spend blocked
        _ = self._management_post_with_retry("/management/pause", {"agentId": self.agent_id}, label="pause_agent")
        c_send, p_send, _, _ = self._runtime(
            ["wallet", "send", "--to", self._wallet_address(), "--amount-wei", "100000000000000", "--chain", self.chain]
        )
        pause_code = str(p_send.get("code") or "")
        if c_send == 0 or pause_code not in {"agent_paused", "approval_required", "approval_pending"}:
            raise HarnessError(f"paused spend expected pause/blocked code, got code={c_send} payload={p_send}")

        _ = self._management_post_with_retry("/management/resume", {"agentId": self.agent_id}, label="resume_agent")
        return {"liquidityIntentId": liq_id}

    def _scenario_balance_reversion(self, baseline: dict[str, Decimal]) -> dict[str, Any]:
        # Best-effort rebalance via reverse swap.
        self._post_permissions_update(
            {
                "agentId": self.agent_id,
                "chainKey": self.chain,
                "tradeApprovalMode": "auto",
            }
        )
        _ = self._runtime(
            [
                "trade",
                "spot",
                "--chain",
                self.chain,
                "--token-in",
                self.trade_token_out,
                "--token-out",
                self.trade_token_in,
                "--amount-in",
                self.trade_amounts.get("rebalance", "0.05"),
                "--slippage-bps",
                "150",
            ],
            timeout=300,
        )

        after = self._balance_snapshot()
        bps = int(self.args.balance_tolerance_bps)
        native_floor_native = Decimal(str(self.args.balance_tolerance_floor_native))
        native_floor_wei = Decimal("1000000000000000000") * native_floor_native
        stable_floor_wei = Decimal("1000000000000000000") * Decimal(str(self.args.balance_tolerance_floor_stable))

        keys = {"NATIVE", str(self.trade_token_in).upper(), str(self.trade_token_out).upper()}
        failures: dict[str, Any] = {}
        deltas: dict[str, Any] = {}
        for key in sorted(keys):
            before_v = baseline.get(key, Decimal("0"))
            after_v = after.get(key, Decimal("0"))
            floor = native_floor_wei if key == "NATIVE" else stable_floor_wei
            ok, delta, allowed = _within_tolerance(before_v, after_v, bps=bps, floor=floor)
            deltas[key] = {
                "before": str(before_v),
                "after": str(after_v),
                "delta": str(delta),
                "allowed": str(allowed),
                "ok": ok,
            }
            if not ok:
                failures[key] = {
                    "before": str(before_v),
                    "after": str(after_v),
                    "delta": str(delta),
                    "allowed": str(allowed),
                }
        if failures:
            raise HarnessError(f"balance tolerance exceeded: {failures}")
        return {"deltas": deltas}

    def _scenario_hardhat_local_gate(self) -> dict[str, Any]:
        if str(self.chain).strip().lower() != "hardhat_local":
            return {}
        return {"chain": self.chain, "walletAddress": self._wallet_address(), "gate": "preflight_only"}

    def _resolve_pending_best_effort(self) -> list[dict[str, Any]]:
        unresolved: list[dict[str, Any]] = []
        for trade_id in self.created_trade_ids:
            try:
                trade = self._trade_read(trade_id)
                status = str(trade.get("status") or "").strip().lower()
                if status == "approval_pending":
                    self._management_post_with_retry(
                        "/management/approvals/decision",
                        {"agentId": self.agent_id, "tradeId": trade_id, "decision": "reject", "reasonMessage": "harness cleanup"},
                        label="trade_cleanup_reject",
                    )
                    trade = self._wait_for_trade_status(trade_id, {"rejected", "filled", "failed"}, timeout_sec=120)
                    status = str(trade.get("status") or "").strip().lower()
                if status == "approval_pending":
                    unresolved.append({"type": "trade", "id": trade_id, "status": status})
            except Exception as exc:
                unresolved.append({"type": "trade", "id": trade_id, "error": _trim_text(exc)})

        unresolved.extend({"type": "transfer", "id": item, "status": "unknown"} for item in self.created_transfer_approval_ids)
        unresolved.extend({"type": "x402", "id": item, "status": "unknown"} for item in self.created_x402_approval_ids)
        self.unresolved_pending = unresolved
        return unresolved

    def _classify_error(self, exc: Exception, *, fallback: str = "runtime_trade_failure") -> str:
        if isinstance(exc, HarnessError):
            return str(exc.category or fallback)
        text = str(exc).lower()
        if "permissions" in text and ("500" in text or "retry" in text):
            return "transient_api_failure"
        if "preflight" in text:
            return "preflight_failure"
        if "restore" in text:
            return "policy_restore_failure"
        return fallback

    def run(self) -> int:
        if self.args.approve_driver != "management_api":
            raise HarnessError("Slice 96 harness only supports --approve-driver management_api", category="preflight_failure")

        hardhat_smoke = str(self.chain).strip().lower() == "hardhat_local" and self.args.scenario_set == "smoke"
        self._record("bootstrap", True, "starting harness", {"at": _now_iso(), "chain": self.chain, "agentId": self.agent_id})
        self._assert_hardhat_evidence_gate()
        self._probe_hardhat_rpc()
        self._wallet_decrypt_probe()
        self._assert_expected_wallet_address()
        self._probe_solana_localnet_bootstrap()
        self._bootstrap_management()
        state = self._management_state()
        self.initial_state = {
            "latestPolicy": state.get("latestPolicy") if isinstance(state.get("latestPolicy"), dict) else {},
            "transferApprovalPolicy": state.get("transferApprovalPolicy") if isinstance(state.get("transferApprovalPolicy"), dict) else {},
            "publicStatus": ((state.get("agent") or {}).get("publicStatus") if isinstance(state.get("agent"), dict) else None),
            "chainPolicy": state.get("chainPolicy") if isinstance(state.get("chainPolicy"), dict) else {},
        }
        baseline_chain_enabled = bool((self.initial_state.get("chainPolicy") or {}).get("chainEnabled", True))
        if str(self.chain).strip().lower() != "hardhat_local" and not baseline_chain_enabled:
            self._set_chain_enabled(True, label="enable_chain_for_harness")
            self._record("enable_chain", True, "enabled chain policy for harness run", {"class": "ok", "chain": self.chain})
        baseline_balances: dict[str, Decimal] = {}
        if not hardhat_smoke:
            self._ensure_local_wallet_policy_chain_enabled()
            baseline_balances = self._balance_snapshot()
            self._prepare_trade_pair_and_amounts()

        devnet_trade_pair_unavailable = (
            str(self.chain).strip().lower() == "solana_devnet"
            and isinstance(self._solana_devnet_trade_pair_discovery, dict)
            and not bool(self._solana_devnet_trade_pair_discovery.get("quoteable"))
        )
        scenario_funcs: list[tuple[str, Any]] = []
        if hardhat_smoke:
            scenario_funcs = [("hardhat_local_gate", self._scenario_hardhat_local_gate)]
        else:
            if devnet_trade_pair_unavailable:
                scenario_funcs = [("solana_devnet_trade_evidence_boundary", self._scenario_solana_devnet_trade_evidence_boundary)]
            else:
                scenario_funcs = [
                    ("trade_pending_approve", self._scenario_trade_pending_approve),
                    ("trade_reject", self._scenario_trade_reject),
                    ("trade_dedupe", self._scenario_trade_dedupe),
                ]
        if self.args.scenario_set == "full":
            if devnet_trade_pair_unavailable:
                scenario_funcs.extend(
                    [
                        ("transfer_only", self._scenario_transfer_only),
                        ("x402_or_capability_assertion", self._scenario_x402_or_capability_assertion),
                    ]
                )
            else:
                scenario_funcs.extend(
                    [
                        ("global_and_allowlist", self._scenario_global_and_allowlist),
                        ("transfer_only", self._scenario_transfer_only),
                        ("x402_or_capability_assertion", self._scenario_x402_or_capability_assertion),
                        ("liquidity_and_pause", self._scenario_liquidity_and_pause),
                    ]
                )

        stop_after_unsupported = False
        for name, fn in scenario_funcs:
            if stop_after_unsupported:
                break
            try:
                details = fn()
                payload = {"class": "ok"}
                if isinstance(details, dict):
                    payload.update(details)
                self._record(name, True, "scenario passed", payload)
            except Exception as exc:
                failure_class = self._classify_error(exc)
                failure_payload: dict[str, Any] = {"error": str(exc), "class": failure_class}
                if isinstance(exc, HarnessError):
                    failure_payload["code"] = str(exc.code or "")
                    if isinstance(exc.details, dict) and exc.details:
                        failure_payload["details"] = exc.details
                self._record(name, False, "scenario failed", failure_payload)
                if failure_class == "unsupported_live_evidence":
                    if not (devnet_trade_pair_unavailable and name == "solana_devnet_trade_evidence_boundary"):
                        stop_after_unsupported = True

        if not hardhat_smoke and not stop_after_unsupported and not devnet_trade_pair_unavailable:
            try:
                details = self._scenario_balance_reversion(baseline_balances)
                self._record("balance_reversion", True, "within tolerance window", {"class": "ok", **details})
            except Exception as exc:
                self._record(
                    "balance_reversion",
                    False,
                    "tolerance check failed",
                    {"error": str(exc), "class": self._classify_error(exc, fallback="runtime_trade_failure")},
                )

        try:
            self._restore_permissions()
            self._record("restore_permissions", True, "restored baseline policies", {"class": "ok"})
        except Exception as exc:
            self._record("restore_permissions", False, "restore failed", {"error": str(exc), "class": "policy_restore_failure"})

        if str(self.initial_state.get("publicStatus") or "").lower() == "paused":
            try:
                self._management_post_with_retry("/management/pause", {"agentId": self.agent_id}, label="restore_pause_baseline")
                self._record("restore_public_status", True, "re-paused agent to baseline", {"class": "ok"})
            except Exception as exc:
                self._record(
                    "restore_public_status",
                    False,
                    "failed to restore pause status",
                    {"error": str(exc), "class": "policy_restore_failure"},
                )

        if str(self.chain).strip().lower() != "hardhat_local" and not baseline_chain_enabled:
            try:
                self._set_chain_enabled(False, label="restore_chain_policy")
                self._record("restore_chain_policy", True, "restored chain enabled flag to baseline", {"class": "ok", "chain": self.chain})
            except Exception as exc:
                self._record(
                    "restore_chain_policy",
                    False,
                    "failed to restore chain enabled flag",
                    {"error": str(exc), "class": "policy_restore_failure"},
                )

        unresolved = self._resolve_pending_best_effort()

        report = {
            "ok": all(result.ok for result in self.results),
            "generatedAt": _now_iso(),
            "chain": self.chain,
            "agentId": self.agent_id,
            "scenarioSet": self.args.scenario_set,
            "approveDriver": self.args.approve_driver,
            "telegramSuppressed": True,
            "preflight": self.preflight,
            "retryFailures": self.retry_failures,
            "unresolvedPending": unresolved,
            "results": [
                {
                    "name": item.name,
                    "ok": item.ok,
                    "message": item.message,
                    "details": item.details,
                }
                for item in self.results
            ],
        }

        out_path = pathlib.Path(self.args.json_report)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

        print(json.dumps(report, separators=(",", ":")))
        return 0 if bool(report.get("ok")) else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Slice 96 wallet/approval harness")
    parser.add_argument("--base-url", default=os.environ.get("XCLAW_HARNESS_BASE_URL", "http://127.0.0.1:3000"))
    parser.add_argument("--chain", default="base_sepolia")
    parser.add_argument("--agent-id", required=True)
    parser.add_argument("--bootstrap-token-file", required=True)
    parser.add_argument("--runtime-bin", default="apps/agent-runtime/bin/xclaw-agent")
    parser.add_argument("--agent-api-key", default=os.environ.get("XCLAW_AGENT_API_KEY", ""))
    parser.add_argument("--wallet-passphrase", default=os.environ.get("XCLAW_WALLET_PASSPHRASE", ""))
    parser.add_argument("--disable-passphrase-recovery", action="store_true")
    parser.add_argument("--mode", choices=["full"], default="full")
    parser.add_argument("--scenario-set", choices=["smoke", "full"], default="full")
    parser.add_argument("--approve-driver", choices=["management_api"], default="management_api")
    parser.add_argument("--hardhat-rpc-url", default="http://127.0.0.1:8545")
    parser.add_argument("--hardhat-evidence-report", default="/tmp/xclaw-slice96-hardhat-smoke.json")
    parser.add_argument("--max-api-retries", type=int, default=4)
    parser.add_argument("--api-retry-base-ms", type=int, default=400)
    parser.add_argument("--balance-tolerance-bps", type=int, default=40)
    parser.add_argument("--balance-tolerance-floor-native", type=str, default="0.0005")
    parser.add_argument("--balance-tolerance-floor-stable", type=str, default="5")
    parser.add_argument("--recipient-address", default=os.environ.get("XCLAW_HARNESS_RECIPIENT", ""))
    parser.add_argument("--expected-wallet-address", default="")
    parser.add_argument("--json-report", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        runner = WalletApprovalHarness(args)
        return runner.run()
    except HarnessError as exc:
        payload = {
            "ok": False,
            "code": str(exc.code or "harness_failed"),
            "message": str(exc),
            "category": str(exc.category or "runtime_trade_failure"),
            "details": exc.details,
            "at": _now_iso(),
        }
        print(json.dumps(payload, separators=(",", ":")))
        return 1


if __name__ == "__main__":
    sys.exit(main())
