import json
import io
import os
import pathlib
import sys
import tempfile
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

    def test_resolve_agent_binary_prefers_configured_runtime_bin(self) -> None:
        with tempfile.NamedTemporaryFile(delete=False) as f:
            p = pathlib.Path(f.name)
        p.chmod(0o755)
        self.addCleanup(lambda: p.unlink(missing_ok=True))
        with mock.patch.dict(skill.os.environ, {"XCLAW_AGENT_RUNTIME_BIN": str(p)}, clear=False):
            resolved = skill._resolve_agent_binary()
        self.assertEqual(resolved, str(p))

    def test_resolve_agent_binary_falls_back_when_configured_bin_not_executable(self) -> None:
        with tempfile.NamedTemporaryFile(delete=False) as f:
            p = pathlib.Path(f.name)
        p.chmod(0o644)
        self.addCleanup(lambda: p.unlink(missing_ok=True))
        with mock.patch.dict(skill.os.environ, {"XCLAW_AGENT_RUNTIME_BIN": str(p)}, clear=False):
            with mock.patch.object(skill.os, "access", return_value=False):
                with mock.patch.object(skill.shutil, "which", return_value="/usr/bin/xclaw-agent"):
                    resolved = skill._resolve_agent_binary()
        self.assertEqual(resolved, "/usr/bin/xclaw-agent")

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

    def test_version_emits_skill_metadata_without_runtime_call(self) -> None:
        expected = {
            "ok": True,
            "code": "skill_version",
            "skillScriptSha256": "abc123",
            "patchState": {"schemaVersion": 43, "lastError": None},
        }
        with mock.patch.object(skill, "_skill_version_payload", return_value=expected), mock.patch.object(
            skill, "_run_agent"
        ) as run_mock:
            code, payload = self._capture(["xclaw_agent_skill.py", "version"])
        self.assertEqual(code, 0)
        self.assertEqual(payload, expected)
        run_mock.assert_not_called()

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

    def test_api_commands_accept_runtime_state_api_key_when_env_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_dir = pathlib.Path(tmp_dir) / ".xclaw-agent"
            state_dir.mkdir(parents=True, exist_ok=True)
            (state_dir / "state.json").write_text(json.dumps({"agentApiKey": "state-key", "agentId": "ag_state"}), encoding="utf-8")
            env = {
                "XCLAW_API_BASE_URL": "https://xclaw.trade/api/v1",
                "XCLAW_DEFAULT_CHAIN": "base_sepolia",
                "HOME": tmp_dir,
            }
            with mock.patch.dict(os.environ, env, clear=True):
                with mock.patch.object(skill, "_run_agent", return_value=0) as run_mock:
                    code = skill.main(["xclaw_agent_skill.py", "tracked-list"])
        self.assertEqual(code, 0)
        run_mock.assert_called_once_with(["tracked", "list", "--chain", "base_sepolia", "--json"])

    def test_wallet_send_token_accepts_symbol_and_delegates(self) -> None:
        with mock.patch.dict("os.environ", self._ENV, clear=False):
            with mock.patch.object(skill, "_run_agent", return_value=0) as run_mock:
                code = skill.main(
                    [
                        "xclaw_agent_skill.py",
                        "wallet-send-token",
                        "USDC",
                        "0x9099d24D55c105818b4e9eE117d87BC11063CF10",
                        "10000000",
                    ]
                )
        self.assertEqual(code, 0)
        run_mock.assert_called_once_with(
            [
                "wallet",
                "send-token",
                "--token",
                "USDC",
                "--to",
                "0x9099d24D55c105818b4e9eE117d87BC11063CF10",
                "--amount-wei",
                "10000000",
                "--chain",
                "base_sepolia",
                "--json",
            ]
        )

    def test_wallet_create_delegates_to_runtime(self) -> None:
        with mock.patch.dict("os.environ", {"XCLAW_DEFAULT_CHAIN": "hedera_testnet"}, clear=False):
            with mock.patch.object(skill, "_run_agent", return_value=0) as run_mock:
                code = skill.main(["xclaw_agent_skill.py", "wallet-create"])
        self.assertEqual(code, 0)
        run_mock.assert_called_once_with(["wallet", "create", "--chain", "hedera_testnet", "--json"])

    def test_wallet_wrap_native_delegates_to_runtime(self) -> None:
        with mock.patch.dict("os.environ", {"XCLAW_DEFAULT_CHAIN": "hedera_testnet"}, clear=False):
            with mock.patch.object(skill, "_run_agent", return_value=0) as run_mock:
                code = skill.main(["xclaw_agent_skill.py", "wallet-wrap-native", "1"])
        self.assertEqual(code, 0)
        run_mock.assert_called_once_with(["wallet", "wrap-native", "--amount", "1", "--chain", "hedera_testnet", "--json"])

    def test_auth_recover_delegates_to_runtime(self) -> None:
        env = {
            "XCLAW_API_BASE_URL": "https://xclaw.trade/api/v1",
            "XCLAW_DEFAULT_CHAIN": "hedera_testnet",
            "XCLAW_AGENT_ID": "ag_demo",
        }
        with mock.patch.dict("os.environ", env, clear=False):
            with mock.patch.object(skill, "_run_agent", return_value=0) as run_mock:
                code = skill.main(["xclaw_agent_skill.py", "auth-recover"])
        self.assertEqual(code, 0)
        run_mock.assert_called_once_with(["auth", "recover", "--chain", "hedera_testnet", "--json"])

    def test_agent_register_delegates_to_profile_set_name(self) -> None:
        env = {
            "XCLAW_API_BASE_URL": "https://xclaw.trade/api/v1",
            "XCLAW_DEFAULT_CHAIN": "hedera_testnet",
            "XCLAW_AGENT_API_KEY": "test-key",
        }
        with mock.patch.dict("os.environ", env, clear=False):
            with mock.patch.object(skill, "_run_agent", return_value=0) as run_mock:
                code = skill.main(["xclaw_agent_skill.py", "agent-register", "Slice95Runner"])
        self.assertEqual(code, 0)
        run_mock.assert_called_once_with(["profile", "set-name", "--name", "Slice95Runner", "--chain", "hedera_testnet", "--json"])

    def test_wallet_send_token_rejects_empty_token(self) -> None:
        with mock.patch.dict("os.environ", self._ENV, clear=False):
            code, payload = self._capture(
                [
                    "xclaw_agent_skill.py",
                    "wallet-send-token",
                    "",
                    "0x9099d24D55c105818b4e9eE117d87BC11063CF10",
                    "10000000",
                ]
            )
        self.assertEqual(code, 2)
        self.assertIsInstance(payload, dict)
        self.assertEqual(payload.get("code"), "invalid_input")
        self.assertIn("token", (payload.get("details") or {}))

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
        child = mock.Mock()
        child.returncode = 1
        child.communicate.return_value = (json.dumps(pending_payload), "")
        with mock.patch.object(skill, "_resolve_agent_binary", return_value="/usr/bin/xclaw-agent"):
            with mock.patch.object(skill, "_maybe_patch_openclaw_gateway"):
                with mock.patch.object(skill.subprocess, "Popen", return_value=child), mock.patch.object(
                    skill, "_fetch_owner_link_payload", return_value=None
                ):
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
        child = mock.Mock()
        child.returncode = 1
        child.communicate.return_value = (json.dumps(payload), "")
        with mock.patch.object(skill, "_resolve_agent_binary", return_value="/usr/bin/xclaw-agent"):
            with mock.patch.object(skill, "_maybe_patch_openclaw_gateway"):
                with mock.patch.object(skill.subprocess, "Popen", return_value=child):
                    buf = io.StringIO()
                    with redirect_stdout(buf):
                        code = skill._run_agent(["wallet", "send-token"])
        self.assertEqual(code, 1)
        emitted = json.loads(buf.getvalue().strip())
        self.assertEqual(emitted.get("code"), "send_failed")

    def test_run_agent_normalizes_symbol_unit_mismatch_to_nonfatal(self) -> None:
        payload = {
            "ok": False,
            "code": "invalid_input",
            "message": "Amount is too small for symbol-based transfer and looks like a base-unit mistake.",
            "details": {"token": "USDC", "amountWei": "10000000"},
        }
        child = mock.Mock()
        child.returncode = 1
        child.communicate.return_value = (json.dumps(payload), "")
        with mock.patch.object(skill, "_resolve_agent_binary", return_value="/usr/bin/xclaw-agent"):
            with mock.patch.object(skill, "_maybe_patch_openclaw_gateway"):
                with mock.patch.object(skill.subprocess, "Popen", return_value=child):
                    buf = io.StringIO()
                    with redirect_stdout(buf):
                        code = skill._run_agent(["wallet", "send-token", "--token", "USDC"])
        self.assertEqual(code, 0)
        emitted = json.loads(buf.getvalue().strip())
        self.assertTrue(emitted.get("ok"))
        self.assertEqual(emitted.get("code"), "input_guarded")

    def test_run_agent_normalizes_pending_approval_even_when_exit_zero(self) -> None:
        pending_payload = {
            "ok": False,
            "code": "approval_required",
            "message": "Transfer is waiting for management approval.",
            "details": {"approvalId": "xfr_999", "status": "approval_pending"},
        }
        child = mock.Mock()
        child.returncode = 0
        child.communicate.return_value = (json.dumps(pending_payload), "")
        with mock.patch.object(skill, "_resolve_agent_binary", return_value="/usr/bin/xclaw-agent"):
            with mock.patch.object(skill, "_maybe_patch_openclaw_gateway"):
                with mock.patch.object(skill.subprocess, "Popen", return_value=child), mock.patch.object(
                    skill, "_fetch_owner_link_payload", return_value=None
                ):
                    buf = io.StringIO()
                    with redirect_stdout(buf):
                        code = skill._run_agent(["wallet", "send-token"])
        self.assertEqual(code, 0)
        emitted = json.loads(buf.getvalue().strip())
        self.assertTrue(emitted.get("ok"))
        self.assertEqual(emitted.get("code"), "approval_pending")
        self.assertEqual(emitted.get("details", {}).get("approvalId"), "xfr_999")
        self.assertNotIn("queuedMessage", emitted.get("details", {}))
        self.assertIn("management approval", str(emitted.get("message", "")).lower())

    def test_run_agent_normalizes_trade_pending_with_last_status(self) -> None:
        pending_payload = {
            "ok": False,
            "code": "approval_required",
            "message": "Trade is waiting for management approval.",
            "details": {"tradeId": "trd_abc", "chain": "base_sepolia", "lastStatus": "approval_pending"},
        }
        child = mock.Mock()
        child.returncode = 1
        child.communicate.return_value = (json.dumps(pending_payload), "")
        with mock.patch.object(skill, "_resolve_agent_binary", return_value="/usr/bin/xclaw-agent"):
            with mock.patch.object(skill, "_maybe_patch_openclaw_gateway"):
                with mock.patch.object(skill.subprocess, "Popen", return_value=child):
                    buf = io.StringIO()
                    with redirect_stdout(buf):
                        code = skill._run_agent(["trade", "spot"])
        self.assertEqual(code, 0)
        emitted = json.loads(buf.getvalue().strip())
        self.assertTrue(emitted.get("ok"))
        self.assertEqual(emitted.get("code"), "approval_pending")
        self.assertEqual(emitted.get("details", {}).get("tradeId"), "trd_abc")

    def test_run_agent_sanitizes_transfer_queued_message(self) -> None:
        pending_payload = {
            "ok": False,
            "code": "approval_required",
            "message": "Transfer is waiting for management approval.",
            "actionHint": "Send queuedMessage verbatim so Telegram buttons can attach, then wait for Approve/Deny.",
            "details": {
                "approvalId": "xfr_abc",
                "status": "approval_pending",
                "queuedMessage": "Approval required (transfer)\nStatus: approval_pending",
            },
        }
        child = mock.Mock()
        child.returncode = 1
        child.communicate.return_value = (json.dumps(pending_payload), "")
        with mock.patch.object(skill, "_resolve_agent_binary", return_value="/usr/bin/xclaw-agent"):
            with mock.patch.object(skill, "_maybe_patch_openclaw_gateway"):
                with mock.patch.object(skill.subprocess, "Popen", return_value=child), mock.patch.object(
                    skill, "_fetch_owner_link_payload", return_value=None
                ):
                    buf = io.StringIO()
                    with redirect_stdout(buf):
                        code = skill._run_agent(["wallet", "send-token"])
        self.assertEqual(code, 0)
        emitted = json.loads(buf.getvalue().strip())
        self.assertEqual(emitted.get("code"), "approval_pending")
        self.assertEqual(emitted.get("message"), "Transfer queued for management approval.")
        self.assertNotIn("queuedMessage", emitted.get("details", {}))
        self.assertIn("wait for owner approve/deny", str(emitted.get("actionHint", "")).lower())

    def test_run_agent_transfer_pending_includes_management_url(self) -> None:
        pending_payload = {
            "ok": False,
            "code": "approval_required",
            "message": "Transfer is waiting for management approval.",
            "details": {"approvalId": "xfr_mgmt", "status": "approval_pending"},
        }
        owner_link = {
            "ok": True,
            "code": "ok",
            "managementUrl": "https://xclaw.trade/agents/ag_1?token=ol_abc",
        }
        child = mock.Mock()
        child.returncode = 1
        child.communicate.return_value = (json.dumps(pending_payload), "")
        with mock.patch.object(skill, "_resolve_agent_binary", return_value="/usr/bin/xclaw-agent"):
            with mock.patch.object(skill, "_maybe_patch_openclaw_gateway"):
                with mock.patch.object(skill.subprocess, "Popen", return_value=child), mock.patch.object(
                    skill, "_fetch_owner_link_payload", return_value=owner_link
                ), mock.patch.object(
                    skill, "_last_delivery_is_telegram", return_value=False
                ):
                    buf = io.StringIO()
                    with redirect_stdout(buf):
                        code = skill._run_agent(["wallet", "send-token"])
        self.assertEqual(code, 0)
        emitted = json.loads(buf.getvalue().strip())
        self.assertEqual(emitted.get("code"), "approval_pending")
        self.assertEqual(
            (emitted.get("details") or {}).get("managementUrl"),
            "https://xclaw.trade/agents/ag_1?token=ol_abc",
        )
        self.assertIn("share managementurl", str(emitted.get("actionHint", "")).lower())

    def test_run_agent_transfer_pending_skips_owner_link_lookup_when_telegram_active(self) -> None:
        pending_payload = {
            "ok": False,
            "code": "approval_required",
            "message": "Transfer is waiting for management approval.",
            "details": {"approvalId": "xfr_tg", "status": "approval_pending"},
        }
        child = mock.Mock()
        child.returncode = 1
        child.communicate.return_value = (json.dumps(pending_payload), "")
        with mock.patch.object(skill, "_resolve_agent_binary", return_value="/usr/bin/xclaw-agent"):
            with mock.patch.object(skill, "_maybe_patch_openclaw_gateway"):
                with mock.patch.object(skill.subprocess, "Popen", return_value=child), mock.patch.object(
                    skill, "_last_delivery_is_telegram", return_value=True
                ), mock.patch.object(
                    skill, "_fetch_owner_link_payload"
                ) as owner_link_mock:
                    buf = io.StringIO()
                    with redirect_stdout(buf):
                        code = skill._run_agent(["wallet", "send-token"])
        self.assertEqual(code, 0)
        owner_link_mock.assert_not_called()
        emitted = json.loads(buf.getvalue().strip())
        self.assertEqual(emitted.get("code"), "approval_pending")
        self.assertNotIn("managementUrl", emitted.get("details", {}))
        self.assertIn("wait for owner approve/deny", str(emitted.get("actionHint", "")).lower())

    def test_run_agent_transfer_pending_forces_management_flow_when_configured(self) -> None:
        pending_payload = {
            "ok": False,
            "code": "approval_required",
            "message": "Transfer is waiting for management approval.",
            "details": {"approvalId": "xfr_force", "status": "approval_pending"},
        }
        owner_link = {
            "ok": True,
            "code": "ok",
            "managementUrl": "https://xclaw.trade/agents/ag_1?token=ol_force",
        }
        child = mock.Mock()
        child.returncode = 1
        child.communicate.return_value = (json.dumps(pending_payload), "")
        with mock.patch.dict(skill.os.environ, {"XCLAW_TELEGRAM_APPROVALS_FORCE_MANAGEMENT": "1"}, clear=False):
            with mock.patch.object(skill, "_resolve_agent_binary", return_value="/usr/bin/xclaw-agent"):
                with mock.patch.object(skill, "_maybe_patch_openclaw_gateway"):
                    with mock.patch.object(skill.subprocess, "Popen", return_value=child), mock.patch.object(
                        skill, "_last_delivery_is_telegram", return_value=True
                    ), mock.patch.object(
                        skill, "_fetch_owner_link_payload", return_value=owner_link
                    ):
                        buf = io.StringIO()
                        with redirect_stdout(buf):
                            code = skill._run_agent(["wallet", "send-token"])
        self.assertEqual(code, 0)
        emitted = json.loads(buf.getvalue().strip())
        self.assertEqual(emitted.get("code"), "approval_pending")
        self.assertEqual(
            (emitted.get("details") or {}).get("managementUrl"),
            "https://xclaw.trade/agents/ag_1?token=ol_force",
        )
        self.assertIn("share managementurl", str(emitted.get("actionHint", "")).lower())

    def test_run_agent_timeout_kills_process_group(self) -> None:
        child = mock.Mock()
        child.pid = 12345
        child.communicate.side_effect = [
            skill.subprocess.TimeoutExpired(cmd=["xclaw-agent", "trade", "spot"], timeout=1),
            ("", ""),
        ]
        with mock.patch.object(skill, "_resolve_agent_binary", return_value="/usr/bin/xclaw-agent"):
            with mock.patch.object(skill, "_maybe_patch_openclaw_gateway"):
                with mock.patch.object(skill.subprocess, "Popen", return_value=child):
                    with mock.patch.object(skill.os, "killpg") as killpg_mock:
                        buf = io.StringIO()
                        with redirect_stdout(buf):
                            code = skill._run_agent(["trade", "spot"])
        self.assertEqual(code, 124)
        killpg_mock.assert_called_once_with(12345, skill.signal.SIGKILL)
        emitted = json.loads(buf.getvalue().strip())
        self.assertEqual(emitted.get("code"), "timeout")

    def test_extract_json_payload_handles_prefixed_line_noise(self) -> None:
        payload = {"ok": False, "code": "approval_required", "details": {"status": "approval_pending"}}
        raw = "warning: transient rpc error\n" + json.dumps(payload)
        extracted = skill._extract_json_payload(raw)
        self.assertIsInstance(extracted, dict)
        self.assertEqual(extracted.get("code"), "approval_required")

    def test_limit_orders_are_not_exposed_in_skill_wrapper(self) -> None:
        code, payload = self._capture(["xclaw_agent_skill.py", "limit-orders-list"])
        self.assertEqual(code, 2)
        self.assertIsInstance(payload, dict)
        self.assertEqual(payload.get("code"), "unknown_command")

if __name__ == "__main__":
    unittest.main()
