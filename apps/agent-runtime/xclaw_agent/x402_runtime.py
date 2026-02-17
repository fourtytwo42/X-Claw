from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import secrets
import signal
import socket
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from . import x402_policy
from . import x402_state
from . import x402_tunnel

NETWORKS_PATH = pathlib.Path(__file__).resolve().parents[3] / "config" / "x402" / "networks.json"


class X402RuntimeError(Exception):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def _is_process_alive(pid: int | None) -> bool:
    if not isinstance(pid, int) or pid <= 0:
        return False
    try:
        if os.name == "nt":
            proc = subprocess.run(["tasklist", "/FI", f"PID eq {pid}"], capture_output=True, text=True, check=False)
            return str(pid) in (proc.stdout or "")
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        s.listen(1)
        return int(s.getsockname()[1])


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


def _resource_path() -> str:
    return f"/x402/pay/{secrets.token_hex(8)}"


def _is_url(value: str) -> bool:
    parsed = urllib.parse.urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _is_expired(expires_at: str | None) -> bool:
    parsed = _parse_iso(expires_at)
    if parsed is None:
        return False
    return datetime.now(timezone.utc) >= parsed


def serve_status() -> dict[str, Any]:
    state = x402_state.load_runtime_state()
    serve = state.get("serve") if isinstance(state.get("serve"), dict) else {}
    server_alive = _is_process_alive(serve.get("serverPid"))
    tunnel_alive = _is_process_alive(serve.get("tunnelPid"))
    status = "running" if server_alive and tunnel_alive else "stopped"
    expires_at = serve.get("expiresAt")
    return {
        "status": status,
        "network": serve.get("network"),
        "facilitator": serve.get("facilitator"),
        "amountAtomic": serve.get("amountAtomic"),
        "ttlSeconds": serve.get("ttlSeconds"),
        "localPort": serve.get("localPort"),
        "serverPid": serve.get("serverPid"),
        "tunnelPid": serve.get("tunnelPid"),
        "paymentUrl": serve.get("paymentUrl"),
        "resourcePath": serve.get("resourcePath"),
        "expiresAt": expires_at,
        "expired": _is_expired(expires_at),
        "timeLimitNotice": serve.get("timeLimitNotice"),
        "startedAt": serve.get("startedAt"),
        "updatedAt": serve.get("updatedAt"),
    }


def serve_stop() -> dict[str, Any]:
    state = x402_state.load_runtime_state()
    serve = state.get("serve") if isinstance(state.get("serve"), dict) else {}
    x402_tunnel.stop_process(serve.get("tunnelPid"))
    x402_tunnel.stop_process(serve.get("serverPid"))

    state["serve"] = {
        "status": "stopped",
        "network": None,
        "facilitator": None,
        "amountAtomic": None,
        "ttlSeconds": None,
        "resourcePath": None,
        "localPort": None,
        "serverPid": None,
        "tunnelPid": None,
        "paymentUrl": None,
        "expiresAt": None,
        "timeLimitNotice": None,
        "startedAt": None,
        "updatedAt": utc_now(),
    }
    x402_state.save_runtime_state(state)
    return serve_status()


def serve_start(network: str, facilitator: str, amount_atomic: str, ttl_seconds: int = 1800, local_port: int | None = None) -> dict[str, Any]:
    resolved = _resolve_network(network, facilitator)
    amount = _require_amount_atomic(amount_atomic)

    # Always converge to one active server/tunnel.
    serve_stop()

    port = int(local_port or _find_free_port())
    resource_path = _resource_path()
    now = datetime.now(timezone.utc)
    ttl_final = max(60, int(ttl_seconds))
    expires_at = (now + timedelta(seconds=ttl_final)).isoformat()
    time_limit_notice = f"Payment link expires in {ttl_final} seconds (at {expires_at})."

    worker_cmd = [
        sys.executable,
        "-m",
        "xclaw_agent.x402_runtime",
        "serve-worker",
        "--port",
        str(port),
        "--network",
        network,
        "--facilitator",
        facilitator,
        "--amount-atomic",
        amount,
        "--resource-path",
        resource_path,
        "--expires-at",
        expires_at,
    ]
    worker = subprocess.Popen(worker_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    tunnel = x402_tunnel.start_quick_tunnel(port)
    public_url = str(tunnel.get("publicUrl") or "").rstrip("/")
    payment_url = f"{public_url}{resource_path}"

    state = x402_state.load_runtime_state()
    state["serve"] = {
        "status": "running",
        "network": network,
        "facilitator": facilitator,
        "facilitatorConfig": resolved.get("facilitatorConfig"),
        "amountAtomic": amount,
        "ttlSeconds": ttl_final,
        "resourcePath": resource_path,
        "localPort": port,
        "serverPid": worker.pid,
        "tunnelPid": tunnel.get("pid"),
        "paymentUrl": payment_url,
        "expiresAt": expires_at,
        "timeLimitNotice": time_limit_notice,
        "startedAt": now.isoformat(),
        "updatedAt": now.isoformat(),
    }
    x402_state.save_runtime_state(state)
    return serve_status()


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


def serve_worker_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="x402-serve-worker")
    parser.add_argument("--port", required=True)
    parser.add_argument("--network", required=True)
    parser.add_argument("--facilitator", required=True)
    parser.add_argument("--amount-atomic", required=True)
    parser.add_argument("--resource-path", required=True)
    parser.add_argument("--expires-at", required=True)
    args = parser.parse_args(argv)

    port = int(args.port)
    network = str(args.network)
    facilitator = str(args.facilitator)
    amount_atomic = str(args.amount_atomic)
    resource_path = str(args.resource_path)
    expires_at = str(args.expires_at)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
            return

        def _json(self, code: int, payload: dict[str, Any]) -> None:
            raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self) -> None:  # noqa: N802
            if self.path == "/x402/meta":
                self._json(
                    200,
                    {
                        "ok": True,
                        "network": network,
                        "facilitator": facilitator,
                        "amountAtomic": amount_atomic,
                        "resourcePath": resource_path,
                        "expiresAt": expires_at,
                        "expired": _is_expired(expires_at),
                    },
                )
                return

            if self.path == resource_path:
                if _is_expired(expires_at):
                    self._json(
                        410,
                        {
                            "ok": False,
                            "code": "payment_expired",
                            "network": network,
                            "facilitator": facilitator,
                            "amountAtomic": amount_atomic,
                            "resourcePath": resource_path,
                            "expiresAt": expires_at,
                        },
                    )
                    return
                payment_header = self.headers.get("X-Payment")
                if payment_header:
                    self._json(
                        200,
                        {
                            "ok": True,
                            "code": "payment_settled",
                            "network": network,
                            "facilitator": facilitator,
                            "amountAtomic": amount_atomic,
                        },
                    )
                    return
                self._json(
                    402,
                    {
                        "ok": False,
                        "code": "payment_required",
                        "network": network,
                        "facilitator": facilitator,
                        "amountAtomic": amount_atomic,
                        "resourcePath": resource_path,
                        "requiredHeader": "X-Payment",
                    },
                )
                return

            self._json(404, {"ok": False, "code": "not_found", "message": "Unknown x402 path."})

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)

    def _shutdown(_signum: int, _frame: Any) -> None:
        try:
            server.shutdown()
        except Exception:
            pass

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)
    server.serve_forever(poll_interval=0.5)
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    if not argv:
        return 2
    cmd = argv[0]
    if cmd == "serve-worker":
        return serve_worker_main(argv[1:])
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
