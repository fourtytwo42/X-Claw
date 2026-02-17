from __future__ import annotations

import json
import os
import pathlib
import secrets
from datetime import datetime, timezone
from typing import Any

APP_DIR = pathlib.Path(os.environ.get("XCLAW_AGENT_HOME", str(pathlib.Path.home() / ".xclaw-agent")))
X402_RUNTIME_FILE = APP_DIR / "x402-runtime.json"
X402_PENDING_PAY_FLOWS_FILE = APP_DIR / "pending-x402-pay-flows.json"


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


def default_runtime_state() -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "serve": {
            "status": "stopped",
            "network": None,
            "facilitator": None,
            "amountAtomic": None,
            "resourcePath": None,
            "localPort": None,
            "serverPid": None,
            "tunnelPid": None,
            "paymentUrl": None,
            "expiresAt": None,
            "startedAt": None,
            "updatedAt": utc_now(),
        },
    }


def load_runtime_state() -> dict[str, Any]:
    state = _read_json(X402_RUNTIME_FILE)
    if not state or int(state.get("schemaVersion") or 0) != 1:
        return default_runtime_state()
    serve = state.get("serve")
    if not isinstance(serve, dict):
        state["serve"] = default_runtime_state()["serve"]
    return state


def save_runtime_state(state: dict[str, Any]) -> None:
    state["schemaVersion"] = 1
    serve = state.get("serve")
    if not isinstance(serve, dict):
        state["serve"] = default_runtime_state()["serve"]
    state["serve"]["updatedAt"] = utc_now()
    _write_json(X402_RUNTIME_FILE, state)


def default_pending_pay_flows() -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "flows": {},
    }


def load_pending_pay_flows() -> dict[str, Any]:
    payload = _read_json(X402_PENDING_PAY_FLOWS_FILE)
    if not payload or int(payload.get("schemaVersion") or 0) != 1:
        return default_pending_pay_flows()
    flows = payload.get("flows")
    if not isinstance(flows, dict):
        payload["flows"] = {}
    return payload


def save_pending_pay_flows(payload: dict[str, Any]) -> None:
    payload["schemaVersion"] = 1
    if not isinstance(payload.get("flows"), dict):
        payload["flows"] = {}
    _write_json(X402_PENDING_PAY_FLOWS_FILE, payload)


def get_pending_pay_flow(approval_id: str) -> dict[str, Any] | None:
    flows = load_pending_pay_flows().get("flows")
    if not isinstance(flows, dict):
        return None
    item = flows.get(approval_id)
    return item if isinstance(item, dict) else None


def record_pending_pay_flow(approval_id: str, flow: dict[str, Any]) -> None:
    payload = load_pending_pay_flows()
    flows = payload.setdefault("flows", {})
    if not isinstance(flows, dict):
        flows = {}
        payload["flows"] = flows
    flow["updatedAt"] = utc_now()
    flows[approval_id] = flow
    save_pending_pay_flows(payload)


def remove_pending_pay_flow(approval_id: str) -> None:
    payload = load_pending_pay_flows()
    flows = payload.get("flows")
    if not isinstance(flows, dict):
        return
    if approval_id in flows:
        flows.pop(approval_id, None)
        save_pending_pay_flows(payload)


def make_xpay_approval_id() -> str:
    return f"xfr_{secrets.token_hex(10)}"
