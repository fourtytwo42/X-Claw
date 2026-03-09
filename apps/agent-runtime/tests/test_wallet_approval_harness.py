import argparse
import importlib.util
import json
import os
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
            disable_passphrase_recovery=False,
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
            expected_wallet_address="",
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

    def test_runtime_inherits_builder_code_from_skill_env(self) -> None:
        runner = harness.WalletApprovalHarness(self._args())
        proc = mock.Mock(returncode=0, stdout='{"ok":true}\n', stderr="")
        with mock.patch.object(harness, "_openclaw_skill_env", return_value={"XCLAW_BUILDER_CODE_BASE_SEPOLIA": "xclaw"}), mock.patch.object(
            harness.subprocess, "run", return_value=proc
        ) as run_mock:
            runner._runtime(["trade", "execute", "--trade-id", "trd_1"])
        called_env = run_mock.call_args.kwargs.get("env") or {}
        self.assertEqual(str(called_env.get("XCLAW_BUILDER_CODE_BASE_SEPOLIA")), "xclaw")

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

    def test_solana_localnet_bootstrap_preflight_uses_env_file(self) -> None:
        args = self._args()
        args.chain = "solana_localnet"
        runner = harness.WalletApprovalHarness(args)
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = pathlib.Path(tmpdir) / "solana-localnet-faucet.env"
            env_path.write_text(
                "\n".join(
                    [
                        "XCLAW_SOLANA_FAUCET_SIGNER_SECRET_SOLANA_LOCALNET=secret",
                        "XCLAW_SOLANA_FAUCET_WRAPPED_MINT_SOLANA_LOCALNET=So11111111111111111111111111111111111111112",
                        "XCLAW_SOLANA_FAUCET_STABLE_MINT_SOLANA_LOCALNET=EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                    ]
                ),
                encoding="utf-8",
            )
            with mock.patch.dict(os.environ, {"XCLAW_SOLANA_LOCALNET_BOOTSTRAP_ENV_FILE": str(env_path)}, clear=False):
                runner._probe_solana_localnet_bootstrap()
        self.assertTrue(bool(runner.preflight["solanaLocalnetBootstrap"]["ok"]))

    def test_solana_localnet_canonical_token_resolution_prefers_bootstrap_env(self) -> None:
        args = self._args()
        args.chain = "solana_localnet"
        runner = harness.WalletApprovalHarness(args)
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = pathlib.Path(tmpdir) / "solana-localnet-faucet.env"
            env_path.write_text(
                "\n".join(
                    [
                        "XCLAW_SOLANA_FAUCET_SIGNER_SECRET_SOLANA_LOCALNET=secret",
                        "XCLAW_SOLANA_FAUCET_WRAPPED_MINT_SOLANA_LOCALNET=BDPkyPPmKVtQw1Xg7WF3yrUz5SLXu2u7pp3wAyfusPA6",
                        "XCLAW_SOLANA_FAUCET_STABLE_MINT_SOLANA_LOCALNET=BZvD2GmhsV3iDsRdiSECWcZX3JpVAKTE4rrFAqnuTCw3",
                    ]
                ),
                encoding="utf-8",
            )
            with mock.patch.dict(os.environ, {"XCLAW_SOLANA_LOCALNET_BOOTSTRAP_ENV_FILE": str(env_path)}, clear=False):
                self.assertEqual(runner._canonical_token_address("USDC"), "BZvD2GmhsV3iDsRdiSECWcZX3JpVAKTE4rrFAqnuTCw3")
                self.assertEqual(runner._canonical_token_address("WETH"), "BDPkyPPmKVtQw1Xg7WF3yrUz5SLXu2u7pp3wAyfusPA6")

    def test_solana_localnet_bootstrap_preflight_fails_when_env_missing(self) -> None:
        args = self._args()
        args.chain = "solana_localnet"
        runner = harness.WalletApprovalHarness(args)
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = pathlib.Path(tmpdir) / "solana-localnet-faucet.env"
            env_path.write_text("XCLAW_SOLANA_FAUCET_SIGNER_SECRET_SOLANA_LOCALNET=secret\n", encoding="utf-8")
            with mock.patch.dict(os.environ, {"XCLAW_SOLANA_LOCALNET_BOOTSTRAP_ENV_FILE": str(env_path)}, clear=False):
                with self.assertRaises(harness.HarnessError) as ctx:
                    runner._probe_solana_localnet_bootstrap()
        self.assertEqual(ctx.exception.code, "solana_localnet_bootstrap_missing")

    def test_solana_localnet_liquidity_returns_preflight_blocked_when_bootstrap_invalid(self) -> None:
        args = self._args()
        args.chain = "solana_localnet"
        runner = harness.WalletApprovalHarness(args)
        runner.preflight["solanaLocalnetBootstrap"] = {"ok": False, "bootstrapEnvFile": "/tmp/missing.env"}
        out = runner._scenario_liquidity_and_pause()
        self.assertFalse(out.get("liquiditySupported"))
        self.assertEqual(out.get("liquidityUnsupportedReason"), "solana_localnet_preflight_blocked")

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

    def test_management_post_with_retry_accepts_async_202_success(self) -> None:
        runner = harness.WalletApprovalHarness(self._args())
        with mock.patch.object(
            runner,
            "_http",
            return_value=(202, {"ok": True, "status": "approved", "decisionInbox": {"status": "pending"}}),
        ):
            out = runner._management_post_with_retry(
                "/management/transfer-approvals/decision",
                {"agentId": "ag_test", "approvalId": "xfr_1", "decision": "approve"},
                label="transfer_decision_native_approve",
            )
        self.assertTrue(out.get("ok"))

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

    def test_management_post_with_retry_accepts_not_actionable_conflict(self) -> None:
        runner = harness.WalletApprovalHarness(self._args())
        with mock.patch.object(
            runner,
            "_http",
            return_value=(409, {"ok": False, "code": "not_actionable", "requestId": "req_1"}),
        ):
            out = runner._management_post_with_retry(
                "/management/transfer-approvals/decision",
                {"agentId": "ag_test"},
                label="transfer_decision",
                accepted_conflict_codes={"not_actionable"},
            )
        self.assertTrue(bool(out.get("acceptedConflict")))

    def test_wallet_decrypt_probe_fails_fast_with_mismatch_code(self) -> None:
        args = self._args()
        args.disable_passphrase_recovery = True
        runner = harness.WalletApprovalHarness(args)
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

    def test_wallet_decrypt_probe_allows_hardhat_wallet_health_soft_fail(self) -> None:
        args = self._args()
        args.chain = "hardhat_local"
        runner = harness.WalletApprovalHarness(args)
        with mock.patch.object(
            runner,
            "_runtime",
            side_effect=[
                (0, {"ok": True, "address": "0x1111111111111111111111111111111111111111"}, "", ""),
                (1, {"ok": False, "code": "wallet_health_failed"}, "", ""),
                (0, {"ok": True, "signature": "0x" + "aa" * 65}, "", ""),
            ],
        ):
            runner._wallet_decrypt_probe()
        self.assertTrue(bool(runner.preflight["walletDecryptProbe"]["ok"]))
        self.assertTrue(bool(runner.preflight["walletDecryptProbe"].get("walletHealthSoftFailAccepted")))

    def test_wallet_decrypt_probe_allows_hardhat_sign_soft_fail(self) -> None:
        args = self._args()
        args.chain = "hardhat_local"
        runner = harness.WalletApprovalHarness(args)
        with mock.patch.object(
            runner,
            "_runtime",
            side_effect=[
                (0, {"ok": True, "address": "0x1111111111111111111111111111111111111111"}, "", ""),
                (0, {"ok": True, "hasWallet": True}, "", ""),
                (1, {"ok": False, "code": "sign_failed"}, "", ""),
            ],
        ):
            runner._wallet_decrypt_probe()
        self.assertTrue(bool(runner.preflight["walletDecryptProbe"]["ok"]))
        self.assertTrue(bool(runner.preflight["walletDecryptProbe"].get("signChallengeSoftFailAccepted")))

    def test_post_permissions_update_splits_transfer_policy_calls(self) -> None:
        runner = harness.WalletApprovalHarness(self._args())
        calls: list[tuple[str, str]] = []

        def fake_post(path: str, payload: dict[str, object], *, label: str) -> dict[str, object]:
            calls.append((path, label))
            if path.endswith("/transfer-policy/update"):
                return {"ok": True, "transferPolicy": {"transferApprovalMode": "per_transfer"}}
            return {"ok": True, "updatedTradePolicy": True}

        with mock.patch.object(runner, "_management_post_with_retry", side_effect=fake_post):
            out = runner._post_permissions_update(
                {
                    "agentId": "ag_test",
                    "chainKey": "hardhat_local",
                    "tradeApprovalMode": "per_trade",
                    "allowedTokens": [],
                    "transferApprovalMode": "per_transfer",
                    "nativeTransferPreapproved": False,
                    "allowedTransferTokens": [],
                }
            )
        self.assertTrue(out.get("ok"))
        self.assertIn(("/management/transfer-policy/update", "transfer_policy_update"), calls)
        self.assertIn(("/management/permissions/update", "permissions_update"), calls)

    def test_post_permissions_update_seeds_snapshot_on_policy_denied(self) -> None:
        runner = harness.WalletApprovalHarness(self._args())
        runner.initial_state = {"latestPolicy": {}}
        calls: list[tuple[str, str]] = []

        def fake_post(path: str, payload: dict[str, object], *, label: str, accepted_conflict_codes=None) -> dict[str, object]:
            calls.append((path, label))
            if path == "/management/permissions/update" and len([c for c in calls if c[0] == "/management/permissions/update"]) == 1:
                raise harness.HarnessError(
                    "permissions failed",
                    code="management_api_retry_exhausted",
                    details={"attempts": [{"status": 409, "code": "policy_denied"}]},
                )
            if path == "/management/policy/update":
                return {"ok": True}
            if path == "/management/permissions/update":
                return {"ok": True, "updatedTradePolicy": True}
            return {"ok": True}

        with mock.patch.object(runner, "_management_post_with_retry", side_effect=fake_post):
            out = runner._post_permissions_update(
                {
                    "agentId": "ag_test",
                    "chainKey": "ethereum_sepolia",
                    "tradeApprovalMode": "auto",
                    "allowedTokens": [],
                    "outboundTransfersEnabled": True,
                    "outboundMode": "allow_all",
                    "outboundWhitelistAddresses": [],
                }
            )
        self.assertTrue(out.get("ok"))
        self.assertIn(("/management/policy/update", "policy_snapshot_seed"), calls)
        self.assertEqual(calls.count(("/management/permissions/update", "permissions_update")), 2)

    def test_http_timeout_maps_to_network_error(self) -> None:
        runner = harness.WalletApprovalHarness(self._args())
        with mock.patch.object(runner.opener, "open", side_effect=TimeoutError("timed out")):
            status, body = runner._http("GET", "/management/agent-state", auth_mode="management")
        self.assertEqual(status, 0)
        self.assertEqual(body.get("code"), "network_error")

    def test_wallet_decrypt_probe_recovers_passphrase_from_backup(self) -> None:
        args = self._args()
        args.chain = "base_sepolia"
        runner = harness.WalletApprovalHarness(args)
        with mock.patch.object(
            runner,
            "_runtime",
            side_effect=[
                (0, {"ok": True, "address": "0x1111111111111111111111111111111111111111"}, "", ""),
                (0, {"ok": True, "integrityChecked": False}, "", ""),
                (1, {"ok": False, "code": "non_interactive"}, "", ""),
                (0, {"ok": True, "address": "0x1111111111111111111111111111111111111111"}, "", ""),
                (0, {"ok": True, "integrityChecked": True}, "", ""),
                (0, {"ok": True, "signature": "0x" + "aa" * 65}, "", ""),
            ],
        ), mock.patch.object(harness, "_recover_local_passphrase_backup", return_value="recovered-passphrase"):
            runner._wallet_decrypt_probe()
        self.assertEqual(runner.wallet_passphrase, "recovered-passphrase")
        self.assertTrue(bool(runner.preflight["walletDecryptProbe"]["ok"]))
        self.assertTrue(bool(runner.preflight["walletDecryptProbe"].get("passphraseRecoveredFromBackup")))

    def test_wallet_decrypt_probe_recovery_can_be_disabled(self) -> None:
        args = self._args()
        args.chain = "base_sepolia"
        args.disable_passphrase_recovery = True
        runner = harness.WalletApprovalHarness(args)
        with mock.patch.object(
            runner,
            "_runtime",
            side_effect=[
                (0, {"ok": True, "address": "0x1111111111111111111111111111111111111111"}, "", ""),
                (0, {"ok": True, "integrityChecked": False}, "", ""),
                (1, {"ok": False, "code": "non_interactive"}, "", ""),
            ],
        ), mock.patch.object(harness, "_recover_local_passphrase_backup", return_value="recovered-passphrase"):
            with self.assertRaises(harness.HarnessError):
                runner._wallet_decrypt_probe()

    def test_bootstrap_ethereum_sepolia_funding_wraps_then_trades(self) -> None:
        args = self._args()
        args.chain = "ethereum_sepolia"
        runner = harness.WalletApprovalHarness(args)
        with mock.patch.object(
            runner,
            "_balance_snapshot",
            side_effect=[
                {"NATIVE": Decimal("500000000000000"), "USDC": Decimal("0"), "WETH": Decimal("0")},
                {"NATIVE": Decimal("300000000000000"), "USDC": Decimal("0"), "WETH": Decimal("1")},
                {"NATIVE": Decimal("300000000000000"), "USDC": Decimal("0"), "WETH": Decimal("1")},
                {"NATIVE": Decimal("300000000000000"), "USDC": Decimal("1"), "WETH": Decimal("1")},
            ],
        ), mock.patch.object(runner, "_canonical_token_address", return_value="0x" + "11" * 20), mock.patch.object(
            runner,
            "_runtime",
            side_effect=[
                (0, {"ok": True, "txHash": "0x" + "ab" * 32}, "", ""),
                (0, {"ok": True, "status": "filled"}, "", ""),
            ],
        ), mock.patch.object(runner, "_post_permissions_update", return_value={"ok": True}):
            runner._bootstrap_ethereum_sepolia_funding()

    def test_bootstrap_ethereum_sepolia_funding_fails_without_native(self) -> None:
        args = self._args()
        args.chain = "ethereum_sepolia"
        runner = harness.WalletApprovalHarness(args)
        with mock.patch.object(
            runner,
            "_balance_snapshot",
            return_value={"NATIVE": Decimal("0"), "USDC": Decimal("0"), "WETH": Decimal("0")},
        ):
            with self.assertRaises(harness.HarnessError) as ctx:
                runner._bootstrap_ethereum_sepolia_funding()
        self.assertEqual(ctx.exception.code, "scenario_funding_missing")

    def test_prepare_trade_pair_prefers_weth_route_on_ethereum_sepolia_when_both_balances_present(self) -> None:
        args = self._args()
        args.chain = "ethereum_sepolia"
        runner = harness.WalletApprovalHarness(args)
        with mock.patch.object(
            runner,
            "_balance_snapshot",
            return_value={"NATIVE": Decimal("1"), "USDC": Decimal("528.730904"), "WETH": Decimal("0.080263155302424032")},
        ):
            runner._prepare_trade_pair_and_amounts()
        self.assertEqual(runner.trade_token_in, "WETH")
        self.assertEqual(runner.trade_token_out, "USDC")
        self.assertEqual(runner.trade_amounts["global_auto"], "0.00005")

    def test_global_and_allowlist_uses_bootstrap_weth_route_on_ethereum_sepolia(self) -> None:
        args = self._args()
        args.chain = "ethereum_sepolia"
        runner = harness.WalletApprovalHarness(args)
        runner.trade_token_in = "WETH"
        runner.trade_token_out = "USDC"
        runner.trade_amounts = {
            "global_auto": "0.00005",
            "allowlist": "0.00005",
        }
        with mock.patch.object(runner, "_post_permissions_update"), mock.patch.object(
            runner,
            "_runtime",
            side_effect=[
                (0, {"ok": True, "status": "filled"}, "", ""),
                (1, {"ok": False, "code": "approval_required", "tradeId": "trd_1"}, "", ""),
                (0, {"ok": True}, "", ""),
            ],
        ) as runtime_mock, mock.patch.object(
            runner,
            "_management_post_with_retry",
            side_effect=[
                {"ok": True, "allowlistedToken": "0x1c7d4b196cb0c7b01d743fbc6116a902379c7238"},
            ],
        ), mock.patch.object(
            runner,
            "_management_state",
            return_value={"latestPolicy": {"allowed_tokens": ["0x1c7d4b196cb0c7b01d743fbc6116a902379c7238"]}},
        ):
            out = runner._scenario_global_and_allowlist()
        first_cmd = runtime_mock.call_args_list[0].args[0]
        second_cmd = runtime_mock.call_args_list[1].args[0]
        self.assertEqual(first_cmd[first_cmd.index("--token-in") + 1], "WETH")
        self.assertEqual(first_cmd[first_cmd.index("--token-out") + 1], "USDC")
        self.assertEqual(second_cmd[second_cmd.index("--token-in") + 1], "WETH")
        self.assertEqual(second_cmd[second_cmd.index("--token-out") + 1], "USDC")
        self.assertEqual(out.get("allowlistedToken"), "0x1c7d4b196cb0c7b01d743fbc6116a902379c7238")

    def test_trade_args_convert_solana_localnet_human_amount_to_atomic_units(self) -> None:
        args = self._args()
        args.chain = "solana_localnet"
        runner = harness.WalletApprovalHarness(args)
        runner.trade_token_in = "SOL"
        runner.trade_token_out = "SomeStableMint"
        runner._solana_localnet_bootstrap_env_cache = {
            "XCLAW_SOLANA_FAUCET_STABLE_MINT_SOLANA_LOCALNET": "SomeStableMint",
            "XCLAW_SOLANA_FAUCET_WRAPPED_MINT_SOLANA_LOCALNET": "SomeWrappedMint",
        }
        out = runner._trade_args("0.001")
        self.assertEqual(out[out.index("--amount-in") + 1], "1000000")

    def test_x402_asserts_unsupported_on_ethereum_sepolia(self) -> None:
        args = self._args()
        args.chain = "ethereum_sepolia"
        runner = harness.WalletApprovalHarness(args)
        with mock.patch.object(runner, "_runtime", return_value=(1, {"ok": False, "code": "unsupported_chain_capability"}, "", "")):
            out = runner._scenario_x402_or_capability_assertion()
        self.assertEqual(out.get("assertedUnsupportedCode"), "unsupported_chain_capability")

    def test_x402_treats_unconfigured_facilitator_as_truthful_unsupported_on_solana_localnet(self) -> None:
        args = self._args()
        args.chain = "solana_localnet"
        runner = harness.WalletApprovalHarness(args)
        with mock.patch.object(
            runner,
            "_runtime",
            return_value=(
                1,
                {
                    "ok": False,
                    "code": "x402_runtime_error",
                    "message": "Facilitator 'cdp' is not configured for network 'solana_localnet'.",
                },
                "",
                "",
            ),
        ):
            out = runner._scenario_x402_or_capability_assertion()
        self.assertEqual(out.get("assertedUnsupportedCode"), "x402_facilitator_unconfigured")
        self.assertEqual(out.get("network"), "solana_localnet")

    def test_x402_treats_unconfigured_pay_facilitator_as_truthful_unsupported_on_solana_localnet(self) -> None:
        args = self._args()
        args.chain = "solana_localnet"
        runner = harness.WalletApprovalHarness(args)
        with mock.patch.object(
            runner,
            "_runtime",
            side_effect=[
                (0, {"ok": True, "paymentUrl": "https://example.test/pay"}, "", ""),
                (
                    1,
                    {
                        "ok": False,
                        "code": "x402_runtime_error",
                        "message": "Facilitator 'cdp' is not configured for network 'solana_localnet'.",
                    },
                    "",
                    "",
                ),
            ],
        ):
            out = runner._scenario_x402_or_capability_assertion()
        self.assertEqual(out.get("assertedUnsupportedCode"), "x402_facilitator_unconfigured")
        self.assertEqual(out.get("network"), "solana_localnet")

    def test_trade_dedupe_returns_truthful_unsupported_on_solana_when_ids_diverge(self) -> None:
        args = self._args()
        args.chain = "solana_localnet"
        runner = harness.WalletApprovalHarness(args)
        runner.trade_token_in = "So11111111111111111111111111111111111111112"
        runner.trade_token_out = "683EFdYHRacRvbvmuUfRUMoGzkRqDAMkG9FW91FxMB4S"
        runner.trade_amounts = {"dedupe": "1000000"}
        with mock.patch.object(runner, "_post_permissions_update"), mock.patch.object(
            runner,
            "_runtime",
            side_effect=[
                (1, {"ok": False, "code": "approval_required", "tradeId": "trd_1"}, "", ""),
                (1, {"ok": False, "code": "approval_required", "tradeId": "trd_2"}, "", ""),
            ],
        ), mock.patch.object(
            runner,
            "_management_post_with_retry",
            return_value={"ok": True},
        ) as decision_mock, mock.patch.object(
            runner,
            "_wait_for_trade_status",
            return_value={"status": "rejected"},
        ):
            out = runner._scenario_trade_dedupe()
        self.assertFalse(out.get("dedupeSupported"))
        self.assertEqual(out.get("reason"), "solana_pending_trade_reuse_unsupported")
        self.assertEqual(decision_mock.call_count, 2)

    def test_wait_for_transfer_approval_actionable_polls_management_queue(self) -> None:
        runner = harness.WalletApprovalHarness(self._args())
        with mock.patch.object(
            runner,
            "_http",
            side_effect=[
                (200, {"ok": True, "queue": [], "history": []}),
                (200, {"ok": True, "queue": [{"approval_id": "xfr_1", "status": "approval_pending"}], "history": []}),
            ],
        ), mock.patch.object(harness.time, "sleep", return_value=None):
            result = runner._wait_for_transfer_approval_actionable("xfr_1", timeout_sec=2)
        self.assertEqual(str(result.get("approval_id")), "xfr_1")

    def test_scenario_x402_waits_for_actionable_approval_before_decision(self) -> None:
        runner = harness.WalletApprovalHarness(self._args())
        with mock.patch.object(runner, "_has_chain_capability", return_value=True), mock.patch.object(
            runner,
            "_runtime",
            side_effect=[
                (0, {"ok": True, "paymentUrl": "https://example.test/pay"}, "", ""),
                (1, {"ok": False, "code": "approval_required", "approval": {"approvalId": "xfr_x402"}}, "", ""),
                (0, {"ok": True}, "", ""),
            ],
        ) as runtime_mock, mock.patch.object(
            runner,
            "_wait_for_transfer_approval_actionable",
            return_value={"approval_id": "xfr_x402", "status": "approval_pending"},
        ) as wait_mock, mock.patch.object(
            runner,
            "_management_post_with_retry",
            return_value={"ok": True},
        ) as decision_mock:
            out = runner._scenario_x402_or_capability_assertion()
        wait_mock.assert_called_once_with("xfr_x402")
        self.assertEqual(str(out.get("x402ApprovalId")), "xfr_x402")
        self.assertEqual(decision_mock.call_args.args[0], "/management/transfer-approvals/decision")
        receive_cmd = runtime_mock.call_args_list[0].args[0]
        pay_cmd = runtime_mock.call_args_list[1].args[0]
        self.assertEqual(receive_cmd[receive_cmd.index("--amount-atomic") + 1], "1")
        self.assertEqual(pay_cmd[pay_cmd.index("--amount-atomic") + 1], "1")

    def test_prepare_trade_pair_sets_solana_defaults_from_native_balance(self) -> None:
        args = self._args()
        args.chain = "solana_devnet"
        runner = harness.WalletApprovalHarness(args)
        with mock.patch.object(
            runner,
            "_balance_snapshot",
            return_value={"NATIVE": Decimal("1000"), harness.SOLANA_USDC_MINT.lower(): Decimal("0")},
        ):
            runner._prepare_trade_pair_and_amounts()
        self.assertEqual(runner.trade_token_in, "SOL")
        self.assertEqual(runner.trade_token_out, harness.SOLANA_USDC_MINT)
        self.assertEqual(runner.trade_amounts["pending_approve"], "0.001")

    def test_attempt_faucet_topup_uses_native_only_for_solana_localnet(self) -> None:
        args = self._args()
        args.chain = "solana_localnet"
        runner = harness.WalletApprovalHarness(args)
        runner._solana_localnet_bootstrap_env_cache = {
            "XCLAW_SOLANA_FAUCET_WRAPPED_MINT_SOLANA_LOCALNET": "BDPkyPPmKVtQw1Xg7WF3yrUz5SLXu2u7pp3wAyfusPA6",
            "XCLAW_SOLANA_FAUCET_STABLE_MINT_SOLANA_LOCALNET": "BZvD2GmhsV3iDsRdiSECWcZX3JpVAKTE4rrFAqnuTCw3",
        }
        with mock.patch.object(
            runner,
            "_runtime",
            return_value=(0, {"ok": True}, "", ""),
        ) as runtime_mock, mock.patch.object(
            runner,
            "_balance_snapshot",
            side_effect=[
                {"NATIVE": Decimal("0")},
                {"NATIVE": Decimal("0"), "bzvd2gmhsv3idsrdisecwczx3jpvakte4rrfaqnutcw3": Decimal("1000")},
            ],
        ):
            runner._attempt_faucet_topup(require_native_topup=True)
        faucet_cmd = runtime_mock.call_args_list[0].args[0]
        self.assertEqual(
            faucet_cmd,
            ["faucet-request", "--chain", "solana_localnet", "--asset", "native", "--asset", "stable", "--asset", "wrapped"],
        )

    def test_prepare_trade_pair_uses_localnet_bootstrap_stable_balance(self) -> None:
        args = self._args()
        args.chain = "solana_localnet"
        runner = harness.WalletApprovalHarness(args)
        runner._solana_localnet_bootstrap_env_cache = {
            "XCLAW_SOLANA_FAUCET_STABLE_MINT_SOLANA_LOCALNET": "BZvD2GmhsV3iDsRdiSECWcZX3JpVAKTE4rrFAqnuTCw3",
            "XCLAW_SOLANA_FAUCET_WRAPPED_MINT_SOLANA_LOCALNET": "BDPkyPPmKVtQw1Xg7WF3yrUz5SLXu2u7pp3wAyfusPA6",
        }
        with mock.patch.object(
            runner,
            "_balance_snapshot",
            return_value={
                "NATIVE": Decimal("0"),
                "bzvd2gmhsv3idsrdisecwczx3jpvakte4rrfaqnutcw3": Decimal("25"),
            },
        ):
            runner._prepare_trade_pair_and_amounts()
        self.assertEqual(runner.trade_token_in, "BZvD2GmhsV3iDsRdiSECWcZX3JpVAKTE4rrFAqnuTCw3")
        self.assertEqual(runner.trade_token_out, "SOL")

    def test_prepare_trade_pair_reports_localnet_bootstrap_funding_details(self) -> None:
        args = self._args()
        args.chain = "solana_localnet"
        runner = harness.WalletApprovalHarness(args)
        runner._solana_localnet_bootstrap_env_cache = {
            "XCLAW_SOLANA_FAUCET_STABLE_MINT_SOLANA_LOCALNET": "BZvD2GmhsV3iDsRdiSECWcZX3JpVAKTE4rrFAqnuTCw3",
            "XCLAW_SOLANA_FAUCET_WRAPPED_MINT_SOLANA_LOCALNET": "BDPkyPPmKVtQw1Xg7WF3yrUz5SLXu2u7pp3wAyfusPA6",
        }
        with mock.patch.object(runner, "_balance_snapshot", return_value={"NATIVE": Decimal("0")}), mock.patch.object(
            runner, "_wallet_address", return_value="9F4znU1PsW5yBK5TAfR9x8C9q3yVGNHUMuaXY35uCEXT"
        ), mock.patch.object(
            runner, "_attempt_faucet_topup", return_value=None
        ):
            with self.assertRaises(harness.HarnessError) as ctx:
                runner._prepare_trade_pair_and_amounts()
        self.assertEqual(ctx.exception.code, "scenario_funding_missing")
        self.assertEqual(ctx.exception.details.get("walletAddress"), "9F4znU1PsW5yBK5TAfR9x8C9q3yVGNHUMuaXY35uCEXT")
        self.assertEqual(ctx.exception.details.get("stableMint"), "BZvD2GmhsV3iDsRdiSECWcZX3JpVAKTE4rrFAqnuTCw3")
        self.assertEqual(ctx.exception.details.get("wrappedMint"), "BDPkyPPmKVtQw1Xg7WF3yrUz5SLXu2u7pp3wAyfusPA6")

    def test_solana_liquidity_reports_truthful_unsupported_reason(self) -> None:
        args = self._args()
        args.chain = "solana_devnet"
        runner = harness.WalletApprovalHarness(args)
        with mock.patch.object(runner, "_post_permissions_update", return_value={"ok": True}), mock.patch.object(
            runner,
            "_runtime",
            side_effect=[
                (
                    1,
                    {
                        "ok": False,
                        "code": "liquidity_preflight_failed",
                        "details": {"reasonCode": "liquidity_preflight_router_transfer_from_failed"},
                    },
                    "",
                    "",
                ),
                (1, {"ok": False, "code": "agent_paused"}, "", ""),
            ],
        ), mock.patch.object(runner, "_management_post_with_retry", return_value={"ok": True}), mock.patch.object(
            runner, "_wallet_address", return_value="So11111111111111111111111111111111111111112"
        ):
            out = runner._scenario_liquidity_and_pause()
        self.assertFalse(out.get("liquiditySupported"))
        self.assertEqual(out.get("liquidityUnsupportedReason"), "liquidity_preflight_failed")

    def test_trade_pending_approve_raises_when_terminal_status_is_not_filled(self) -> None:
        args = self._args()
        args.chain = "ethereum_sepolia"
        runner = harness.WalletApprovalHarness(args)
        with mock.patch.object(runner, "_post_permissions_update"), mock.patch.object(
            runner,
            "_runtime",
            return_value=(1, {"ok": False, "code": "approval_required", "status": "approval_pending", "tradeId": "trd_1"}, "", ""),
        ), mock.patch.object(runner, "_management_post_with_retry", return_value={"ok": True}), mock.patch.object(
            runner,
            "_wait_for_trade_status",
            return_value={"tradeId": "trd_1", "status": "failed"},
        ):
            with self.assertRaises(harness.HarnessError):
                runner._scenario_trade_pending_approve()

    def test_global_and_allowlist_raises_when_auto_trade_fails(self) -> None:
        args = self._args()
        args.chain = "ethereum_sepolia"
        runner = harness.WalletApprovalHarness(args)
        with mock.patch.object(runner, "_post_permissions_update"), mock.patch.object(
            runner,
            "_runtime",
            return_value=(
                1,
                {
                    "ok": False,
                    "code": "trade_spot_failed",
                    "details": {"fallbackReason": {"message": "unsupported_execution_adapter: no router adapter available"}},
                },
                "",
                "",
            ),
        ):
            with self.assertRaises(harness.HarnessError):
                runner._scenario_global_and_allowlist()

    def test_bootstrap_hardhat_local_token_funding_success(self) -> None:
        args = self._args()
        args.chain = "hardhat_local"
        runner = harness.WalletApprovalHarness(args)
        proc_ok = mock.Mock(returncode=0, stdout="ok", stderr="")
        with mock.patch.object(runner, "_wallet_address", return_value="0x582f6f293e0f49855bb752ae29d6b0565c500d87"), mock.patch.object(
            runner, "_canonical_token_address", side_effect=["0x" + "11" * 20, "0x" + "22" * 20]
        ), mock.patch.object(
            harness.subprocess, "run", return_value=proc_ok
        ), mock.patch.object(
            runner, "_balance_snapshot", return_value={"USDC": Decimal("1"), "WETH": Decimal("1"), "NATIVE": Decimal("1")}
        ):
            runner._bootstrap_hardhat_local_token_funding()

    def test_set_chain_enabled_posts_expected_payload(self) -> None:
        args = self._args()
        args.chain = "ethereum_sepolia"
        runner = harness.WalletApprovalHarness(args)
        with mock.patch.object(runner, "_management_post_with_retry", return_value={"ok": True}) as post_mock:
            runner._set_chain_enabled(True, label="enable_chain_for_harness")
        post_mock.assert_called_once_with(
            "/management/chains/update",
            {"agentId": "ag_test", "chainKey": "ethereum_sepolia", "chainEnabled": True},
            label="enable_chain_for_harness",
        )

    def test_run_enables_chain_when_baseline_disabled(self) -> None:
        args = self._args()
        args.chain = "ethereum_sepolia"
        args.scenario_set = "smoke"
        with tempfile.TemporaryDirectory() as tmpdir:
            args.json_report = str(pathlib.Path(tmpdir) / "report.json")
            runner = harness.WalletApprovalHarness(args)
            with mock.patch.object(runner, "_assert_hardhat_evidence_gate"), mock.patch.object(
                runner, "_probe_hardhat_rpc"
            ), mock.patch.object(runner, "_wallet_decrypt_probe"), mock.patch.object(
                runner, "_assert_expected_wallet_address"
            ), mock.patch.object(
                runner, "_bootstrap_management"
            ), mock.patch.object(
                runner,
                "_management_state",
                return_value={
                    "latestPolicy": {},
                    "transferApprovalPolicy": {},
                    "agent": {"publicStatus": "active"},
                    "chainPolicy": {"chainEnabled": False},
                },
            ), mock.patch.object(
                runner, "_balance_snapshot", return_value={"NATIVE": Decimal("1"), "USDC": Decimal("1"), "WETH": Decimal("0")}
            ), mock.patch.object(
                runner, "_prepare_trade_pair_and_amounts"
            ), mock.patch.object(
                runner, "_scenario_trade_pending_approve", return_value={}
            ), mock.patch.object(
                runner, "_scenario_trade_reject", return_value={}
            ), mock.patch.object(
                runner, "_scenario_trade_dedupe", return_value={}
            ), mock.patch.object(
                runner, "_scenario_balance_reversion", return_value={}
            ), mock.patch.object(
                runner, "_restore_permissions"
            ), mock.patch.object(
                runner, "_resolve_pending_best_effort", return_value=[]
            ), mock.patch.object(
                runner, "_set_chain_enabled"
            ) as set_chain_mock:
                rc = runner.run()
        self.assertEqual(rc, 0)
        self.assertEqual(set_chain_mock.call_count, 2)
        self.assertEqual(set_chain_mock.call_args_list[0].kwargs, {"label": "enable_chain_for_harness"})
        self.assertEqual(set_chain_mock.call_args_list[0].args, (True,))
        self.assertEqual(set_chain_mock.call_args_list[1].kwargs, {"label": "restore_chain_policy"})
        self.assertEqual(set_chain_mock.call_args_list[1].args, (False,))

    def test_ensure_local_wallet_policy_chain_enabled_adds_chain(self) -> None:
        args = self._args()
        args.chain = "ethereum_sepolia"
        runner = harness.WalletApprovalHarness(args)
        with tempfile.TemporaryDirectory() as tmpdir, mock.patch.dict(os.environ, {"XCLAW_AGENT_APP_DIR": tmpdir}, clear=False):
            policy_path = pathlib.Path(tmpdir) / "policy.json"
            policy_path.write_text(
                json.dumps(
                    {
                        "paused": False,
                        "chains": {"base_sepolia": {"chain_enabled": True}},
                        "spend": {
                            "approval_required": False,
                            "approval_granted": True,
                            "max_daily_native_wei": "1000000000000000000000",
                        },
                    }
                ),
                encoding="utf-8",
            )
            runner._ensure_local_wallet_policy_chain_enabled()
            payload = json.loads(policy_path.read_text(encoding="utf-8"))
        self.assertTrue(bool(payload["chains"]["ethereum_sepolia"]["chain_enabled"]))

    def test_wait_for_trade_status_uses_receipt_fallback_for_verifying_trade(self) -> None:
        args = self._args()
        args.chain = "ethereum_sepolia"
        runner = harness.WalletApprovalHarness(args)
        with mock.patch.object(
            runner,
            "_trade_read",
            side_effect=[
                {"tradeId": "trd_1", "status": "verifying", "txHash": "0x" + "aa" * 32},
                {"tradeId": "trd_1", "status": "verifying", "txHash": "0x" + "aa" * 32},
            ],
        ), mock.patch.object(runner, "_trade_receipt_succeeded", return_value=True), mock.patch.object(
            harness.time, "time", side_effect=[0, 1, 999]
        ), mock.patch.object(harness.time, "sleep", return_value=None):
            out = runner._wait_for_trade_status("trd_1", {"filled", "failed"}, timeout_sec=3)
        self.assertEqual(str(out.get("status")), "filled")
        self.assertEqual(str(out.get("statusSource")), "tx_receipt_fallback")

    def test_wait_for_trade_status_raises_when_receipt_fallback_not_available(self) -> None:
        args = self._args()
        args.chain = "ethereum_sepolia"
        runner = harness.WalletApprovalHarness(args)
        with mock.patch.object(
            runner,
            "_trade_read",
            side_effect=[
                {"tradeId": "trd_2", "status": "verifying", "txHash": "0x" + "bb" * 32},
                {"tradeId": "trd_2", "status": "verifying", "txHash": "0x" + "bb" * 32},
            ],
        ), mock.patch.object(runner, "_trade_receipt_succeeded", return_value=False), mock.patch.object(
            harness.time, "time", side_effect=[0, 1, 999]
        ), mock.patch.object(harness.time, "sleep", return_value=None):
            with self.assertRaises(harness.HarnessError):
                runner._wait_for_trade_status("trd_2", {"filled", "failed"}, timeout_sec=3)

    def test_trade_receipt_succeeded_falls_back_to_rpc_when_cast_fails(self) -> None:
        args = self._args()
        args.chain = "base_sepolia"
        runner = harness.WalletApprovalHarness(args)
        urlopen_mock = mock.MagicMock()
        urlopen_mock.__enter__.return_value = urlopen_mock
        urlopen_mock.read.return_value = b'{"jsonrpc":"2.0","id":1,"result":{"status":"0x1"}}'
        with mock.patch.object(
            runner,
            "_chain_config",
            return_value={"rpc": {"primary": "https://rpc.example.test"}},
        ), mock.patch.object(
            harness.subprocess,
            "run",
            return_value=mock.Mock(returncode=1, stdout="", stderr="cast failed"),
        ), mock.patch.object(
            harness.urllib.request,
            "urlopen",
            return_value=urlopen_mock,
        ):
            self.assertTrue(runner._trade_receipt_succeeded("0x" + "11" * 32))

    def test_prepare_trade_pair_prefers_usdc_over_weth_when_available(self) -> None:
        args = self._args()
        args.chain = "base_sepolia"
        runner = harness.WalletApprovalHarness(args)
        with mock.patch.object(
            runner,
            "_balance_snapshot",
            return_value={
                "USDC": Decimal("20000000"),
                "WETH": Decimal("900000000"),
            },
        ):
            runner._prepare_trade_pair_and_amounts()
        self.assertEqual(runner.trade_token_in, "USDC")
        self.assertEqual(runner.trade_token_out, "WETH")

    def test_prepare_trade_pair_requests_faucet_when_native_low_and_assets_missing(self) -> None:
        args = self._args()
        args.chain = "base_sepolia"
        runner = harness.WalletApprovalHarness(args)
        with mock.patch.object(
            runner,
            "_balance_snapshot",
            side_effect=[
                {"NATIVE": Decimal("0"), "USDC": Decimal("0"), "WETH": Decimal("0")},
                {"NATIVE": Decimal("2"), "USDC": Decimal("10"), "WETH": Decimal("0")},
                {"NATIVE": Decimal("2"), "USDC": Decimal("10"), "WETH": Decimal("0")},
            ],
        ), mock.patch.object(runner, "_attempt_faucet_topup") as faucet_mock:
            runner._prepare_trade_pair_and_amounts()
        faucet_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
