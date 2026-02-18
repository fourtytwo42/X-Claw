import json
import io
import pathlib
import sys
import unittest
from contextlib import redirect_stdout
from unittest import mock

SKILL_SCRIPTS = pathlib.Path("skills/xclaw-agent/scripts").resolve()
if str(SKILL_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SKILL_SCRIPTS))

import xclaw_agent_skill as skill  # noqa: E402


class X402SkillWrapperTests(unittest.TestCase):
    _ENV = {
        "XCLAW_API_BASE_URL": "https://xclaw.trade/api/v1",
        "XCLAW_AGENT_API_KEY": "test-key",
        "XCLAW_DEFAULT_CHAIN": "base_sepolia",
    }

    def _capture(self, argv):
        with mock.patch.object(skill, "_print_json") as print_json:
            code = skill.main(argv)
            payload = None
            if print_json.call_args:
                payload = print_json.call_args.args[0]
        return code, payload

    def test_request_x402_payment_calls_hosted_receive_request(self) -> None:
        with mock.patch.object(skill, "_run_agent", return_value=0) as run_mock:
            code = skill.main(["xclaw_agent_skill.py", "request-x402-payment"])
        self.assertEqual(code, 0)
        run_mock.assert_called_once_with(
            [
                "x402",
                "receive-request",
                "--network",
                "base_sepolia",
                "--facilitator",
                "cdp",
                "--amount-atomic",
                "0.01",
                "--asset-kind",
                "native",
                "--json",
            ]
        )

    def test_request_x402_payment_rejects_positional_text(self) -> None:
        code, payload = self._capture(["xclaw_agent_skill.py", "request-x402-payment", "please", "request", "$5", "usdc"])
        self.assertEqual(code, 2)
        self.assertIsInstance(payload, dict)
        self.assertEqual(payload.get("code"), "invalid_input")
        self.assertIn("rejects positional text", str(payload.get("message")))

    def test_request_x402_payment_supports_explicit_flag_overrides(self) -> None:
        with mock.patch.object(skill, "_run_agent", return_value=0) as run_mock:
            code = skill.main(
                [
                    "xclaw_agent_skill.py",
                    "request-x402-payment",
                    "--network",
                    "base_sepolia",
                    "--facilitator",
                    "cdp",
                    "--amount-atomic",
                    "5000000",
                    "--asset-kind",
                    "erc20",
                    "--asset-symbol",
                    "USDC",
                    "--resource-description",
                    "Invoice #42",
                ]
            )
        self.assertEqual(code, 0)
        run_mock.assert_called_once_with(
            [
                "x402",
                "receive-request",
                "--network",
                "base_sepolia",
                "--facilitator",
                "cdp",
                "--amount-atomic",
                "5000000",
                "--asset-kind",
                "erc20",
                "--json",
                "--asset-symbol",
                "USDC",
                "--resource-description",
                "Invoice #42",
            ]
        )

    def test_x402_pay_decide_rejects_invalid_decision(self) -> None:
        code, payload = self._capture(["xclaw_agent_skill.py", "x402-pay-decide", "xfr_1", "maybe"])
        self.assertEqual(code, 2)
        self.assertIsInstance(payload, dict)
        self.assertEqual(payload.get("code"), "invalid_input")

    def test_x402_networks_delegates_to_runtime(self) -> None:
        with mock.patch.object(skill, "_run_agent", return_value=0) as run_mock:
            code = skill.main(["xclaw_agent_skill.py", "x402-networks"])
        self.assertEqual(code, 0)
        run_mock.assert_called_once_with(["x402", "networks", "--json"])

    def test_tracked_list_delegates_to_runtime(self) -> None:
        with mock.patch.dict("os.environ", self._ENV, clear=False):
            with mock.patch.object(skill, "_run_agent", return_value=0) as run_mock:
                code = skill.main(["xclaw_agent_skill.py", "tracked-list"])
        self.assertEqual(code, 0)
        run_mock.assert_called_once_with(["tracked", "list", "--chain", "base_sepolia", "--json"])

    def test_tracked_trades_with_agent_and_limit(self) -> None:
        with mock.patch.dict("os.environ", self._ENV, clear=False):
            with mock.patch.object(skill, "_run_agent", return_value=0) as run_mock:
                code = skill.main(["xclaw_agent_skill.py", "tracked-trades", "ag_test", "15"])
        self.assertEqual(code, 0)
        run_mock.assert_called_once_with(["tracked", "trades", "--chain", "base_sepolia", "--json", "--agent", "ag_test", "--limit", "15"])

    def test_run_agent_normalizes_pending_approval_to_success(self) -> None:
        pending_payload = {
            "ok": False,
            "code": "approval_required",
            "message": "Transfer is waiting for management approval.",
            "actionHint": "Send queuedMessage verbatim so Telegram buttons can attach, then wait for Approve/Deny.",
            "details": {
                "approvalId": "xfr_123",
                "chain": "base_sepolia",
                "status": "approval_pending",
                "queuedMessage": "Approval required (transfer)\nStatus: approval_pending"
            }
        }
        proc = mock.Mock(returncode=1, stdout=json.dumps(pending_payload), stderr="")
        with mock.patch.object(skill, "_resolve_agent_binary", return_value="/usr/bin/xclaw-agent"):
            with mock.patch.object(skill, "_maybe_patch_openclaw_gateway"):
                with mock.patch.object(skill.subprocess, "run", return_value=proc):
                    buf = io.StringIO()
                    with redirect_stdout(buf):
                        code = skill._run_agent(["wallet", "send-token"])
        self.assertEqual(code, 0)
        emitted = json.loads(buf.getvalue().strip())
        self.assertTrue(emitted.get("ok"))
        self.assertEqual(emitted.get("code"), "approval_pending")
        self.assertEqual(emitted.get("details", {}).get("approvalId"), "xfr_123")

    def test_run_agent_keeps_non_approval_error_nonzero(self) -> None:
        payload = {"ok": False, "code": "send_failed", "message": "boom"}
        proc = mock.Mock(returncode=1, stdout=json.dumps(payload), stderr="")
        with mock.patch.object(skill, "_resolve_agent_binary", return_value="/usr/bin/xclaw-agent"):
            with mock.patch.object(skill, "_maybe_patch_openclaw_gateway"):
                with mock.patch.object(skill.subprocess, "run", return_value=proc):
                    buf = io.StringIO()
                    with redirect_stdout(buf):
                        code = skill._run_agent(["wallet", "send-token"])
        self.assertEqual(code, 1)
        emitted = json.loads(buf.getvalue().strip())
        self.assertEqual(emitted.get("code"), "send_failed")

if __name__ == "__main__":
    unittest.main()
