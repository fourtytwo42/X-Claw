import argparse
import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest
from decimal import Decimal
from unittest import mock
import urllib.error

HARNESS_PATH = pathlib.Path("apps/agent-runtime/scripts/wallet_approval_harness.py").resolve()
spec = importlib.util.spec_from_file_location("wallet_approval_harness", HARNESS_PATH)
assert spec and spec.loader
harness = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = harness
spec.loader.exec_module(harness)


class WalletApprovalHarnessUnitTests(unittest.TestCase):
    def test_extract_trade_id_prefers_direct_then_nested(self) -> None:
        self.assertEqual(harness._extract_trade_id({"tradeId": "trd_1"}), "trd_1")
        self.assertEqual(harness._extract_trade_id({"details": {"tradeId": "trd_2"}}), "trd_2")
        self.assertEqual(harness._extract_trade_id({"trade": {"tradeId": "trd_3"}}), "trd_3")
        self.assertEqual(harness._extract_trade_id({}), "")

    def test_within_tolerance_uses_max_of_pct_and_floor(self) -> None:
        ok, delta, allowed = harness._within_tolerance(Decimal("100"), Decimal("100.2"), bps=40, floor=Decimal("0.1"))
        self.assertTrue(ok)
        self.assertEqual(delta, Decimal("0.2"))
        self.assertEqual(allowed, Decimal("0.4"))

        ok2, delta2, allowed2 = harness._within_tolerance(Decimal("0"), Decimal("0.05"), bps=40, floor=Decimal("0.01"))
        self.assertFalse(ok2)
        self.assertEqual(delta2, Decimal("0.05"))
        self.assertEqual(allowed2, Decimal("0.01"))

    def _args(self) -> argparse.Namespace:
        return argparse.Namespace(
            base_url="http://127.0.0.1:3000",
            chain="base_sepolia",
            agent_id="ag_test",
            bootstrap_token_file="/tmp/bootstrap-token.json",
            runtime_bin="apps/agent-runtime/bin/xclaw-agent",
            agent_api_key="xak_test",
            wallet_passphrase="",
            mode="full",
            scenario_set="smoke",
            approve_driver="management_api",
            hardhat_rpc_url="http://127.0.0.1:8545",
            hardhat_evidence_report="/tmp/xclaw-slice96-hardhat-smoke.json",
            max_api_retries=4,
            api_retry_base_ms=1,
            balance_tolerance_bps=40,
            balance_tolerance_floor_native="0.0005",
            balance_tolerance_floor_stable="5",
            recipient_address="",
            json_report="/tmp/report.json",
        )

    def test_runtime_parses_last_json_line(self) -> None:
        runner = harness.WalletApprovalHarness(self._args())
        proc = mock.Mock(returncode=0, stdout='noise\n{"ok":true,"code":"ok","tradeId":"trd_1"}\n', stderr="")
        with mock.patch.object(harness.subprocess, "run", return_value=proc) as run_mock:
            code, payload, _, _ = runner._runtime(["trade", "spot", "--chain", "base_sepolia", "--token-in", "USDC", "--token-out", "WETH", "--amount-in", "1", "--slippage-bps", "100"])
        self.assertEqual(code, 0)
        self.assertTrue(payload.get("ok"))
        self.assertEqual(payload.get("tradeId"), "trd_1")
        called_env = run_mock.call_args.kwargs.get("env") or {}
        self.assertEqual(str(called_env.get("XCLAW_TEST_HARNESS_DISABLE_TELEGRAM")), "1")

    def test_main_returns_nonzero_on_harness_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            token_file = pathlib.Path(tmpdir) / "bootstrap-token.json"
            token_file.write_text(json.dumps({"token": ""}), encoding="utf-8")
            rc = harness.main(
                [
                    "--agent-id",
                    "ag_test",
                    "--bootstrap-token-file",
                    str(token_file),
                    "--json-report",
                    str(pathlib.Path(tmpdir) / "report.json"),
                    "--agent-api-key",
                    "xak_test",
                ]
            )
        self.assertEqual(rc, 1)

    def test_hardhat_rpc_preflight_fails_when_unavailable(self) -> None:
        args = self._args()
        args.chain = "hardhat_local"
        runner = harness.WalletApprovalHarness(args)
        with mock.patch.object(harness.urllib.request, "urlopen", side_effect=urllib.error.URLError("refused")):
            with self.assertRaises(harness.HarnessError) as ctx:
                runner._probe_hardhat_rpc()
        self.assertEqual(ctx.exception.code, "hardhat_rpc_unavailable")
        self.assertFalse(bool(runner.preflight["hardhatRpc"]["ok"]))

    def test_base_sepolia_requires_green_hardhat_report(self) -> None:
        args = self._args()
        args.chain = "base_sepolia"
        args.hardhat_evidence_report = "/tmp/nonexistent-hardhat-report.json"
        runner = harness.WalletApprovalHarness(args)
        with self.assertRaises(harness.HarnessError) as ctx:
            runner._assert_hardhat_evidence_gate()
        self.assertEqual(ctx.exception.code, "hardhat_evidence_missing")

    def test_management_post_with_retry_succeeds_after_transient_500s(self) -> None:
        runner = harness.WalletApprovalHarness(self._args())
        with mock.patch.object(
            runner,
            "_http",
            side_effect=[
                (500, {"ok": False, "code": "internal_error", "requestId": "req_1"}),
                (500, {"ok": False, "code": "internal_error", "requestId": "req_2"}),
                (200, {"ok": True}),
            ],
        ):
            out = runner._management_post_with_retry("/management/permissions/update", {"agentId": "ag_test"}, label="permissions_update")
        self.assertTrue(out.get("ok"))
        self.assertEqual(runner.retry_failures, [])

    def test_management_post_with_retry_exhaustion_contains_attempts(self) -> None:
        args = self._args()
        args.max_api_retries = 2
        runner = harness.WalletApprovalHarness(args)
        with mock.patch.object(
            runner,
            "_http",
            side_effect=[
                (500, {"ok": False, "code": "internal_error", "requestId": "req_1"}),
                (500, {"ok": False, "code": "internal_error", "requestId": "req_2"}),
            ],
        ):
            with self.assertRaises(harness.HarnessError) as ctx:
                runner._management_post_with_retry("/management/permissions/update", {"agentId": "ag_test"}, label="permissions_update")
        self.assertEqual(ctx.exception.code, "management_api_retry_exhausted")
        self.assertGreaterEqual(len((ctx.exception.details or {}).get("attempts", [])), 2)

    def test_wallet_decrypt_probe_fails_fast_with_mismatch_code(self) -> None:
        runner = harness.WalletApprovalHarness(self._args())
        with mock.patch.object(
            runner,
            "_runtime",
            side_effect=[
                (0, {"ok": True, "address": "0x1111111111111111111111111111111111111111"}, "", ""),
                (0, {"ok": True}, "", ""),
                (1, {"ok": False, "code": "sign_failed"}, "", "InvalidTag"),
            ],
        ):
            with self.assertRaises(harness.HarnessError) as ctx:
                runner._wallet_decrypt_probe()
        self.assertEqual(ctx.exception.code, "wallet_passphrase_mismatch")
        self.assertFalse(bool(runner.preflight["walletDecryptProbe"]["ok"]))


if __name__ == "__main__":
    unittest.main()
