from __future__ import annotations

import json
import os
import pathlib
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import urlparse

APP_DIR = pathlib.Path(os.environ.get("XCLAW_AGENT_HOME", str(pathlib.Path.home() / ".xclaw-agent")))
X402_POLICY_FILE = APP_DIR / "x402-policy.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_app_dir() -> None:
    APP_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    if os.name != "nt":
        os.chmod(APP_DIR, 0o700)


def _read_json(path: pathlib.Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            return payload
    except Exception:
        pass
    return {}


def _write_json(path: pathlib.Path, payload: dict[str, Any]) -> None:
    ensure_app_dir()
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    if os.name != "nt":
        os.chmod(path, 0o600)


def default_policy_state() -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "chains": {},
    }


def _normalize_decimal_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if text == "":
        return None
    try:
        parsed = Decimal(text)
    except (InvalidOperation, ValueError):
        return None
    if parsed < 0:
        return None
    return format(parsed, "f")


def _normalize_policy(chain: str, payload: dict[str, Any] | None) -> dict[str, Any]:
    row = payload or {}
    mode = str(row.get("payApprovalMode") or "per_payment").strip().lower()
    if mode not in {"auto", "per_payment"}:
        mode = "per_payment"

    max_amount = _normalize_decimal_string(row.get("maxAmountAtomic"))
    allowed_hosts: list[str] = []
    raw_hosts = row.get("allowedHosts")
    if isinstance(raw_hosts, list):
        seen: set[str] = set()
        for host in raw_hosts:
            if not isinstance(host, str):
                continue
            normalized = host.strip().lower()
            if not normalized:
                continue
            if normalized not in seen:
                seen.add(normalized)
                allowed_hosts.append(normalized)

    return {
        "chainKey": chain,
        "payApprovalMode": mode,
        "maxAmountAtomic": max_amount,
        "allowedHosts": allowed_hosts,
        "updatedAt": str(row.get("updatedAt") or "").strip() or utc_now(),
    }


def load_policy_state() -> dict[str, Any]:
    payload = _read_json(X402_POLICY_FILE)
    if not payload or int(payload.get("schemaVersion") or 0) != 1:
        return default_policy_state()
    chains = payload.get("chains")
    if not isinstance(chains, dict):
        payload["chains"] = {}
    return payload


def save_policy_state(payload: dict[str, Any]) -> None:
    payload["schemaVersion"] = 1
    if not isinstance(payload.get("chains"), dict):
        payload["chains"] = {}
    _write_json(X402_POLICY_FILE, payload)


def get_policy(chain: str) -> dict[str, Any]:
    state = load_policy_state()
    chains = state.get("chains")
    if not isinstance(chains, dict):
        chains = {}
    row = chains.get(chain)
    return _normalize_policy(chain, row if isinstance(row, dict) else None)


def set_policy(chain: str, payload: dict[str, Any]) -> dict[str, Any]:
    normalized = _normalize_policy(chain, payload)
    state = load_policy_state()
    chains = state.setdefault("chains", {})
    if not isinstance(chains, dict):
        chains = {}
        state["chains"] = chains
    chains[chain] = normalized
    save_policy_state(state)
    return normalized


def evaluate_pay_policy(chain: str, url: str, amount_atomic: str) -> tuple[bool, dict[str, Any]]:
    policy = get_policy(chain)
    parsed = urlparse(url)
    host = (parsed.hostname or "").strip().lower()
    if not host:
        return False, {
            "policy": policy,
            "blocked": True,
            "policyBlockReasonCode": "invalid_url",
            "policyBlockReasonMessage": "Pay URL is invalid.",
        }

    allowed_hosts = policy.get("allowedHosts")
    if isinstance(allowed_hosts, list) and allowed_hosts:
        if host not in {str(item).strip().lower() for item in allowed_hosts if isinstance(item, str)}:
            return False, {
                "policy": policy,
                "blocked": True,
                "policyBlockReasonCode": "host_not_allowed",
                "policyBlockReasonMessage": f"Host '{host}' is not in x402 pay allowlist.",
            }

    max_amount = policy.get("maxAmountAtomic")
    if isinstance(max_amount, str) and max_amount.strip() != "":
        try:
            requested = Decimal(str(amount_atomic).strip())
            cap = Decimal(max_amount)
            if requested > cap:
                return False, {
                    "policy": policy,
                    "blocked": True,
                    "policyBlockReasonCode": "max_amount_exceeded",
                    "policyBlockReasonMessage": "Requested amount exceeds local x402 pay maxAmountAtomic policy.",
                }
        except (InvalidOperation, ValueError):
            return False, {
                "policy": policy,
                "blocked": True,
                "policyBlockReasonCode": "invalid_amount",
                "policyBlockReasonMessage": "Amount is invalid for x402 pay policy evaluation.",
            }

    requires_approval = str(policy.get("payApprovalMode") or "per_payment") != "auto"
    return True, {
        "policy": policy,
        "blocked": False,
        "requiresApproval": requires_approval,
        "host": host,
    }
