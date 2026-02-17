from __future__ import annotations

import json
import pathlib
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from . import x402_policy
from . import x402_state

NETWORKS_PATH = pathlib.Path(__file__).resolve().parents[3] / "config" / "x402" / "networks.json"


class X402RuntimeError(Exception):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_networks() -> dict[str, Any]:
    if not NETWORKS_PATH.exists():
        raise X402RuntimeError(f"Missing x402 network config: {NETWORKS_PATH}")
    try:
        payload = json.loads(NETWORKS_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        raise X402RuntimeError(f"Invalid x402 network config JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise X402RuntimeError("x402 network config must be a JSON object.")
    return payload


def list_networks() -> dict[str, Any]:
    payload = _load_networks()
    networks = payload.get("networks")
    if not isinstance(networks, dict):
        raise X402RuntimeError("x402 network config is missing networks map.")
    out: list[dict[str, Any]] = []
    for key, value in networks.items():
        if not isinstance(value, dict):
            continue
        out.append(
            {
                "network": str(key),
                "enabled": bool(value.get("enabled", False)),
                "chainId": value.get("chainId"),
                "displayName": value.get("displayName"),
                "facilitators": value.get("facilitators") if isinstance(value.get("facilitators"), dict) else {},
            }
        )
    out.sort(key=lambda item: str(item.get("network")))
    return {
        "schemaVersion": int(payload.get("schemaVersion") or 1),
        "defaultNetwork": payload.get("defaultNetwork"),
        "networks": out,
    }


def _resolve_network(network: str, facilitator: str) -> dict[str, Any]:
    payload = _load_networks()
    networks = payload.get("networks")
    if not isinstance(networks, dict):
        raise X402RuntimeError("x402 network config is missing networks map.")
    row = networks.get(network)
    if not isinstance(row, dict):
        raise X402RuntimeError(f"Unsupported x402 network '{network}'.")
    if not bool(row.get("enabled", False)):
        raise X402RuntimeError(f"Network '{network}' is disabled in x402 config.")
    facilitators = row.get("facilitators")
    if not isinstance(facilitators, dict):
        raise X402RuntimeError(f"Network '{network}' has no facilitator config.")
    fac = facilitators.get(facilitator)
    if not isinstance(fac, dict):
        raise X402RuntimeError(f"Facilitator '{facilitator}' is not configured for network '{network}'.")
    return {
        "network": network,
        "chainId": row.get("chainId"),
        "displayName": row.get("displayName"),
        "facilitator": facilitator,
        "facilitatorConfig": fac,
    }


def _require_amount_atomic(value: str) -> str:
    try:
        parsed = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        raise X402RuntimeError("amountAtomic must be numeric.")
    if parsed <= 0:
        raise X402RuntimeError("amountAtomic must be > 0.")
    return format(parsed, "f")


def _is_url(value: str) -> bool:
    parsed = urllib.parse.urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _payment_headers(flow: dict[str, Any]) -> dict[str, str]:
    # Header shape is intentionally deterministic for now; adapter can replace later.
    return {
        "X-Payment": "x402-local-simulated",
        "X-X402-Network": str(flow.get("network") or ""),
        "X-X402-Facilitator": str(flow.get("facilitator") or ""),
        "X-X402-Amount": str(flow.get("amountAtomic") or ""),
        "X-X402-Approval": str(flow.get("approvalId") or ""),
    }


def _execute_pay_flow(flow: dict[str, Any]) -> dict[str, Any]:
    url = str(flow.get("url") or "").strip()
    if not _is_url(url):
        flow["status"] = "failed"
        flow["reasonCode"] = "invalid_url"
        flow["reasonMessage"] = "Pay URL is invalid."
        flow["terminalAt"] = utc_now()
        x402_state.record_pending_pay_flow(str(flow.get("approvalId") or ""), flow)
        return flow

    flow["status"] = "executing"
    x402_state.record_pending_pay_flow(str(flow.get("approvalId") or ""), flow)

    req = urllib.request.Request(url, method="GET")
    for key, value in _payment_headers(flow).items():
        req.add_header(key, value)

    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = (resp.read() or b"").decode("utf-8", errors="replace")
            status_code = int(resp.getcode())
        if status_code < 200 or status_code >= 300:
            flow["status"] = "failed"
            flow["reasonCode"] = "payment_failed"
            flow["reasonMessage"] = f"Payment endpoint returned status {status_code}."
        else:
            flow["status"] = "filled"
            flow["receipt"] = {
                "statusCode": status_code,
                "responseBody": body[:2000],
                "settledAt": utc_now(),
            }
    except urllib.error.HTTPError as exc:
        status_code = int(exc.code)
        body = (exc.read() or b"").decode("utf-8", errors="replace")
        flow["status"] = "failed"
        flow["reasonCode"] = "payment_challenge_unresolved"
        flow["reasonMessage"] = f"Payment failed with HTTP {status_code}."
        flow["httpResponse"] = {"statusCode": status_code, "body": body[:2000]}
    except Exception as exc:
        flow["status"] = "failed"
        flow["reasonCode"] = "payment_failed"
        flow["reasonMessage"] = str(exc)

    flow["terminalAt"] = utc_now()
    x402_state.record_pending_pay_flow(str(flow.get("approvalId") or ""), flow)
    return flow


def pay_create_or_execute(url: str, network: str, facilitator: str, amount_atomic: str, memo: str | None = None) -> dict[str, Any]:
    _resolve_network(network, facilitator)
    amount = _require_amount_atomic(amount_atomic)
    if not _is_url(url):
        raise X402RuntimeError("Invalid URL for x402 pay.")

    allowed, policy_eval = x402_policy.evaluate_pay_policy(network, url, amount)
    if not allowed:
        return {
            "ok": False,
            "code": str(policy_eval.get("policyBlockReasonCode") or "policy_blocked"),
            "message": str(policy_eval.get("policyBlockReasonMessage") or "x402 pay blocked by local policy."),
            "policy": policy_eval.get("policy"),
        }

    approval_id = x402_state.make_xpay_approval_id()
    flow = {
        "approvalId": approval_id,
        "status": "approval_pending" if bool(policy_eval.get("requiresApproval")) else "approved",
        "network": network,
        "facilitator": facilitator,
        "url": url,
        "amountAtomic": amount,
        "memo": (memo or "").strip() or None,
        "policy": policy_eval.get("policy"),
        "createdAt": utc_now(),
        "updatedAt": utc_now(),
    }
    x402_state.record_pending_pay_flow(approval_id, flow)

    if flow["status"] == "approved":
        executed = _execute_pay_flow(flow)
        return {
            "ok": True,
            "code": "ok" if executed.get("status") == "filled" else "payment_failed",
            "message": "x402 payment executed." if executed.get("status") == "filled" else "x402 payment failed.",
            "approval": executed,
        }

    return {
        "ok": True,
        "code": "approval_required",
        "message": "x402 payment requires approval.",
        "approval": flow,
        "queuedMessage": (
            "X402 Payment Request\n"
            f"Status: approval_pending\n"
            f"Approval ID: {approval_id}\n"
            f"Network: {network}\n"
            f"Facilitator: {facilitator}\n"
            f"Amount: {amount}\n"
            f"URL: {url}"
        ),
    }


def pay_decide(approval_id: str, decision: str, reason_message: str | None = None) -> dict[str, Any]:
    flow = x402_state.get_pending_pay_flow(approval_id)
    if not flow:
        raise X402RuntimeError("x402 pay approval was not found.")

    status = str(flow.get("status") or "")
    if status in {"filled", "failed", "rejected"}:
        return flow

    normalized = decision.strip().lower()
    if normalized not in {"approve", "deny"}:
        raise X402RuntimeError("decision must be approve|deny")

    if normalized == "deny":
        flow["status"] = "rejected"
        flow["reasonCode"] = "approval_rejected"
        flow["reasonMessage"] = (reason_message or "Denied by owner").strip()
        flow["terminalAt"] = utc_now()
        x402_state.record_pending_pay_flow(approval_id, flow)
        return flow

    flow["status"] = "approved"
    x402_state.record_pending_pay_flow(approval_id, flow)
    return _execute_pay_flow(flow)


def pay_resume(approval_id: str) -> dict[str, Any]:
    flow = x402_state.get_pending_pay_flow(approval_id)
    if not flow:
        raise X402RuntimeError("x402 pay approval was not found.")
    status = str(flow.get("status") or "")
    if status in {"filled", "failed", "rejected"}:
        return flow
    if status != "approved":
        raise X402RuntimeError(f"x402 pay resume is not actionable from status '{status}'.")
    return _execute_pay_flow(flow)

