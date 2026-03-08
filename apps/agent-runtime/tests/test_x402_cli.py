import argparse
import io
import json
import pathlib
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
AGENT_RUNTIME_ROOT = REPO_ROOT / "apps" / "agent-runtime"
if str(AGENT_RUNTIME_ROOT) not in sys.path:
    sys.path.insert(0, str(AGENT_RUNTIME_ROOT))

from xclaw_agent import cli  # noqa: E402


class X402CliTests(unittest.TestCase):
    def _run_and_parse_stdout(self, func):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = func()
        self.assertEqual(code, 0)
        return json.loads(buf.getvalue().strip())

    def test_x402_pay_emits_and_mirrors_approval(self) -> None:
        args = argparse.Namespace(
            url="https://example.com/pay",
            network="base_sepolia",
            facilitator="cdp",
            amount_atomic="1",
            memo=None,
            json=True,
        )
        payload = {"ok": True, "approval": {"approvalId": "xfr_1", "status": "approval_pending"}}
        with mock.patch.object(cli, "x402_pay_create_or_execute", return_value=payload), mock.patch.object(
            cli, "_mirror_x402_outbound"
        ) as mirror_mock:
            result = self._run_and_parse_stdout(lambda: cli.cmd_x402_pay(args))
        self.assertTrue(result.get("ok"))
        mirror_mock.assert_called_once_with(payload["approval"])

    def test_x402_pay_best_effort_mirror_failure_does_not_change_payload(self) -> None:
        args = argparse.Namespace(
            url="https://example.com/pay",
            network="base_sepolia",
            facilitator="cdp",
            amount_atomic="1",
            memo=None,
            json=True,
        )
        payload = {
            "ok": True,
            "approval": {
                "approvalId": "xfr_1",
                "status": "approval_pending",
                "network": "base_sepolia",
                "facilitator": "cdp",
                "url": "https://example.com/pay",
                "amountAtomic": "1",
            },
        }
        with mock.patch.object(cli, "x402_pay_create_or_execute", return_value=payload), mock.patch.object(
            cli, "_api_request", side_effect=RuntimeError("mirror down")
        ):
            result = self._run_and_parse_stdout(lambda: cli.cmd_x402_pay(args))
        self.assertTrue(result.get("ok"))
        approval = result.get("approval") or {}
        self.assertEqual(approval.get("approvalId"), "xfr_1")
        self.assertEqual(approval.get("status"), "approval_pending")

    def test_x402_receive_request_rejects_token_without_symbol_or_address(self) -> None:
        args = argparse.Namespace(
            network="base_sepolia",
            facilitator="cdp",
            amount_atomic="1",
            asset_kind="token",
            asset_symbol=None,
            asset_address=None,
            resource_description=None,
            json=True,
        )
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = cli.cmd_x402_receive_request(args)
        self.assertEqual(code, 2)
        payload = json.loads(buf.getvalue().strip())
        self.assertEqual(payload.get("code"), "invalid_input")

    def test_x402_policy_get_returns_loaded_policy(self) -> None:
        args = argparse.Namespace(network="base_sepolia", json=True)
        with tempfile.TemporaryDirectory() as tmpdir:
            policy = {"payApprovalMode": "auto", "allowedHosts": ["example.com"]}
            with mock.patch.object(cli, "x402_get_policy", return_value=policy):
                payload = self._run_and_parse_stdout(lambda: cli.cmd_x402_policy_get(args))
        self.assertEqual(payload.get("x402Policy"), policy)


if __name__ == "__main__":
    unittest.main()
