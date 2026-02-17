import json
import pathlib
import socket
import sys
import tempfile
import threading
import unittest
from contextlib import ExitStack
from contextlib import redirect_stdout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import StringIO
from unittest import mock

RUNTIME_ROOT = pathlib.Path("apps/agent-runtime").resolve()
if str(RUNTIME_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNTIME_ROOT))

from xclaw_agent import x402_policy, x402_runtime, x402_state  # noqa: E402


class _OkHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):  # noqa: A003
        return

    def do_GET(self):  # noqa: N802
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        body = b'{"ok":true}'
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class X402RuntimeTests(unittest.TestCase):
    def _with_temp_home(self):
        return tempfile.TemporaryDirectory()

    def _run_cli_fn(self, fn):
        buf = StringIO()
        with redirect_stdout(buf):
            code = fn()
        raw = buf.getvalue().strip()
        payload = json.loads(raw) if raw else {}
        return code, payload

    def test_list_networks_includes_base_and_kite_enabled(self) -> None:
        payload = x402_runtime.list_networks()
        items = {item.get("network"): item for item in payload.get("networks", [])}
        self.assertIn("base_sepolia", items)
        self.assertIn("base", items)
        self.assertIn("kite_ai_testnet", items)
        self.assertTrue(bool(items["kite_ai_testnet"].get("enabled")))

    def test_pay_creates_approval_pending_under_per_payment_policy(self) -> None:
        with self._with_temp_home() as home:
            app_dir = pathlib.Path(home)
            with ExitStack() as stack:
                stack.enter_context(mock.patch.object(x402_policy, "APP_DIR", app_dir))
                stack.enter_context(mock.patch.object(x402_policy, "X402_POLICY_FILE", app_dir / "x402-policy.json"))
                stack.enter_context(mock.patch.object(x402_state, "APP_DIR", app_dir))
                stack.enter_context(mock.patch.object(x402_state, "X402_RUNTIME_FILE", app_dir / "x402-runtime.json"))
                stack.enter_context(
                    mock.patch.object(x402_state, "X402_PENDING_PAY_FLOWS_FILE", app_dir / "pending-x402-pay-flows.json")
                )
                policy = x402_policy.set_policy(
                    "base_sepolia",
                    {"payApprovalMode": "per_payment", "allowedHosts": ["example.com"], "updatedAt": x402_policy.utc_now()},
                )
                self.assertEqual(policy["payApprovalMode"], "per_payment")
                result = x402_runtime.pay_create_or_execute(
                    url="https://example.com/pay",
                    network="base_sepolia",
                    facilitator="cdp",
                    amount_atomic="1",
                    memo="test",
                )
                self.assertTrue(result.get("ok"))
                self.assertEqual(result.get("code"), "approval_required")
                approval = result.get("approval") or {}
                self.assertTrue(str(approval.get("approvalId") or "").startswith("xfr_"))
                self.assertEqual(approval.get("status"), "approval_pending")

    def test_pay_decide_deny_terminal(self) -> None:
        with self._with_temp_home() as home:
            app_dir = pathlib.Path(home)
            with ExitStack() as stack:
                stack.enter_context(mock.patch.object(x402_policy, "APP_DIR", app_dir))
                stack.enter_context(mock.patch.object(x402_policy, "X402_POLICY_FILE", app_dir / "x402-policy.json"))
                stack.enter_context(mock.patch.object(x402_state, "APP_DIR", app_dir))
                stack.enter_context(mock.patch.object(x402_state, "X402_RUNTIME_FILE", app_dir / "x402-runtime.json"))
                stack.enter_context(
                    mock.patch.object(x402_state, "X402_PENDING_PAY_FLOWS_FILE", app_dir / "pending-x402-pay-flows.json")
                )
                x402_policy.set_policy(
                    "base_sepolia",
                    {"payApprovalMode": "per_payment", "allowedHosts": ["example.com"], "updatedAt": x402_policy.utc_now()},
                )
                created = x402_runtime.pay_create_or_execute(
                    url="https://example.com/pay",
                    network="base_sepolia",
                    facilitator="cdp",
                    amount_atomic="2",
                )
                approval_id = str((created.get("approval") or {}).get("approvalId"))
                decided = x402_runtime.pay_decide(approval_id, "deny", "owner denied")
                self.assertEqual(decided.get("status"), "rejected")
                self.assertEqual(decided.get("reasonCode"), "approval_rejected")

    def test_pay_auto_executes_when_policy_auto(self) -> None:
        with self._with_temp_home() as home:
            app_dir = pathlib.Path(home)
            with ExitStack() as stack:
                stack.enter_context(mock.patch.object(x402_policy, "APP_DIR", app_dir))
                stack.enter_context(mock.patch.object(x402_policy, "X402_POLICY_FILE", app_dir / "x402-policy.json"))
                stack.enter_context(mock.patch.object(x402_state, "APP_DIR", app_dir))
                stack.enter_context(mock.patch.object(x402_state, "X402_RUNTIME_FILE", app_dir / "x402-runtime.json"))
                stack.enter_context(
                    mock.patch.object(x402_state, "X402_PENDING_PAY_FLOWS_FILE", app_dir / "pending-x402-pay-flows.json")
                )
                x402_policy.set_policy(
                    "base_sepolia",
                    {"payApprovalMode": "auto", "allowedHosts": ["127.0.0.1"], "updatedAt": x402_policy.utc_now()},
                )

                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.bind(("127.0.0.1", 0))
                port = int(sock.getsockname()[1])
                sock.close()

                server = ThreadingHTTPServer(("127.0.0.1", port), _OkHandler)
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                try:
                    result = x402_runtime.pay_create_or_execute(
                        url=f"http://127.0.0.1:{port}/pay",
                        network="base_sepolia",
                        facilitator="cdp",
                        amount_atomic="3",
                    )
                finally:
                    server.shutdown()
                    server.server_close()

                self.assertTrue(result.get("ok"))
                self.assertIn(result.get("code"), {"ok", "payment_failed"})
                approval = result.get("approval") or {}
                self.assertIn(approval.get("status"), {"filled", "failed"})

    def test_unsupported_network_rejected(self) -> None:
        with self.assertRaises(x402_runtime.X402RuntimeError):
            x402_runtime.pay_create_or_execute(
                url="https://example.com/pay",
                network="unknown_network",
                facilitator="cdp",
                amount_atomic="1",
            )

if __name__ == "__main__":
    unittest.main()
