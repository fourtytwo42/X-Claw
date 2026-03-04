from __future__ import annotations

import json
import pathlib
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Callable

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
    return {
        "X-Payment": "x402-runtime-settlement",
        "X-X402-Network": str(flow.get("network") or ""),
        "X-X402-Facilitator": str(flow.get("facilitator") or ""),
        "X-X402-Amount": str(flow.get("amountAtomic") or ""),
        "X-X402-Approval": str(flow.get("approvalId") or ""),
    }


def _normalize_asset_kind(value: str | None) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"erc20", "token"}:
        return "token"
    return "native"


def _json_from_http_error(exc: urllib.error.HTTPError) -> dict[str, Any]:
    try:
        text = (exc.read() or b"").decode("utf-8", errors="replace")
        payload = json.loads(text)
        if isinstance(payload, dict):
            return payload
    except Exception:
        return {}
    return {}


def _fetch_payment_challenge(url: str) -> dict[str, Any]:
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=20):
            raise X402RuntimeError("Payment endpoint returned success before challenge; expected 402.")
    except urllib.error.HTTPError as exc:
        if int(exc.code) != 402:
            body = (exc.read() or b"").decode("utf-8", errors="replace")
            raise X402RuntimeError(f"Expected HTTP 402 challenge, received HTTP {exc.code}: {body[:400]}")
        payload = _json_from_http_error(exc)
        details = payload.get("details")
        if not isinstance(details, dict):
            raise X402RuntimeError("Invalid payment challenge details payload.")
        return details


def _post_settlement(url: str, flow: dict[str, Any], tx_id: str) -> dict[str, Any]:
    req = urllib.request.Request(url, method="POST")
    for key, value in _payment_headers(flow).items():
        req.add_header(key, value)
    req.add_header("X-Tx-Id", tx_id)
    req.add_header("X-Tx-Hash", tx_id)
    req.add_header("Content-Type", "application/json")
    payload = json.dumps({"txId": tx_id}).encode("utf-8")
    try:
        with urllib.request.urlopen(req, data=payload, timeout=25) as resp:
            body = (resp.read() or b"").decode("utf-8", errors="replace")
            status_code = int(resp.getcode())
        if status_code < 200 or status_code >= 300:
            raise X402RuntimeError(f"Settlement endpoint returned status {status_code}.")
        parsed = json.loads(body) if body.strip() else {}
        if not isinstance(parsed, dict):
            parsed = {}
        return parsed
    except urllib.error.HTTPError as exc:
        code = int(exc.code)
        body = (exc.read() or b"").decode("utf-8", errors="replace")
        raise X402RuntimeError(f"Settlement endpoint rejected payment (HTTP {code}): {body[:400]}")


def _execute_pay_flow(flow: dict[str, Any], settle_payment: Callable[[dict[str, Any]], dict[str, Any]] | None = None) -> dict[str, Any]:
    url = str(flow.get("url") or "").strip()
    if not _is_url(url):
        flow["status"] = "failed"
        flow["reasonCode"] = "invalid_url"
        flow["reasonMessage"] = "Pay URL is invalid."
        flow["terminalAt"] = utc_now()
        x402_state.record_pending_pay_flow(str(flow.get("approvalId") or ""), flow)
        return flow

    flow["status"] = "executing"
    flow["updatedAt"] = utc_now()
    x402_state.record_pending_pay_flow(str(flow.get("approvalId") or ""), flow)

    try:
        if settle_payment is None:
            raise X402RuntimeError("No x402 settlement executor was provided by runtime.")
        challenge = _fetch_payment_challenge(url)
        challenge_network = str(challenge.get("networkKey") or "").strip()
        challenge_facilitator = str(challenge.get("facilitatorKey") or "").strip()
        challenge_amount = str(challenge.get("amountAtomic") or "").strip()
        challenge_asset_kind = _normalize_asset_kind(str(challenge.get("assetKind") or "native"))

        if challenge_network and challenge_network != str(flow.get("network") or ""):
            raise X402RuntimeError("Payment challenge network mismatch.")
        if challenge_facilitator and challenge_facilitator != str(flow.get("facilitator") or ""):
            raise X402RuntimeError("Payment challenge facilitator mismatch.")
        if challenge_amount and challenge_amount != str(flow.get("amountAtomic") or ""):
            raise X402RuntimeError("Payment challenge amount mismatch.")

        settlement_request = {
            "network": str(flow.get("network") or ""),
            "facilitator": str(flow.get("facilitator") or ""),
            "amountAtomic": str(flow.get("amountAtomic") or ""),
            "assetKind": challenge_asset_kind,
            "assetAddress": challenge.get("assetAddress"),
            "assetSymbol": challenge.get("assetSymbol"),
            "recipientAddress": challenge.get("recipientAddress"),
            "paymentId": challenge.get("paymentId"),
            "approvalId": flow.get("approvalId"),
            "url": url,
        }
        settlement = settle_payment(settlement_request)
        tx_id = str((settlement or {}).get("txId") or "").strip()
        if not tx_id:
            raise X402RuntimeError("x402 settlement execution did not return tx id.")
        flow["assetKind"] = challenge_asset_kind
        flow["assetAddress"] = challenge.get("assetAddress")
        flow["assetSymbol"] = challenge.get("assetSymbol")
        flow["recipientAddress"] = challenge.get("recipientAddress")
        flow["toAddress"] = challenge.get("recipientAddress")

        settled_response = _post_settlement(url, flow, tx_id)
        flow["status"] = "filled"
        flow["txHash"] = tx_id
        flow["receipt"] = {
            "txId": tx_id,
            "settledAt": utc_now(),
            "response": settled_response,
        }
        flow["paymentChallenge"] = {
            "networkKey": challenge_network,
            "facilitatorKey": challenge_facilitator,
            "amountAtomic": challenge_amount,
            "assetKind": challenge_asset_kind,
            "assetAddress": challenge.get("assetAddress"),
            "assetSymbol": challenge.get("assetSymbol"),
            "recipientAddress": challenge.get("recipientAddress"),
        }
    except Exception as exc:
        flow["status"] = "failed"
        flow["reasonCode"] = "x402_settlement_transfer_failed"
        flow["reasonMessage"] = str(exc)

    flow["terminalAt"] = utc_now()
    flow["updatedAt"] = flow["terminalAt"]
    x402_state.record_pending_pay_flow(str(flow.get("approvalId") or ""), flow)
    return flow


def pay_create_or_execute(
    url: str,
    network: str,
    facilitator: str,
    amount_atomic: str,
    memo: str | None = None,
    settle_payment: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
) -> dict[str, Any]:
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
        "assetKind": "native",
        "memo": (memo or "").strip() or None,
        "policy": policy_eval.get("policy"),
        "createdAt": utc_now(),
        "updatedAt": utc_now(),
    }
    x402_state.record_pending_pay_flow(approval_id, flow)

    if flow["status"] == "approved":
        executed = _execute_pay_flow(flow, settle_payment=settle_payment)
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


def pay_decide(
    approval_id: str,
    decision: str,
    reason_message: str | None = None,
    settle_payment: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
) -> dict[str, Any]:
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
    flow["updatedAt"] = utc_now()
    x402_state.record_pending_pay_flow(approval_id, flow)
    return _execute_pay_flow(flow, settle_payment=settle_payment)


def pay_resume(
    approval_id: str,
    settle_payment: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    flow = x402_state.get_pending_pay_flow(approval_id)
    if not flow:
        raise X402RuntimeError("x402 pay approval was not found.")
    status = str(flow.get("status") or "")
    if status in {"filled", "failed", "rejected"}:
        return flow
    if status != "approved":
        raise X402RuntimeError(f"x402 pay resume is not actionable from status '{status}'.")
    return _execute_pay_flow(flow, settle_payment=settle_payment)
