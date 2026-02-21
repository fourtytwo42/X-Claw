import argparse
import io
import json
import os
import tempfile
import unittest
from unittest import mock
from decimal import Decimal
from datetime import datetime, timedelta, timezone

from contextlib import ExitStack, redirect_stdout

import pathlib
import sys

RUNTIME_ROOT = pathlib.Path("apps/agent-runtime").resolve()
if str(RUNTIME_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNTIME_ROOT))

from xclaw_agent import cli  # noqa: E402


class TradePathRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        # Prevent unit tests from reading the operator's real OpenClaw session state.
        self._openclaw_state_tmp = tempfile.TemporaryDirectory()
        self._openclaw_state_patcher = mock.patch.dict(
            cli.os.environ, {"OPENCLAW_STATE_DIR": self._openclaw_state_tmp.name}, clear=False
        )
        self._openclaw_state_patcher.start()
        cli._TX_BUILDER_ATTRIBUTION_BY_HASH.clear()

    def tearDown(self) -> None:
        self._openclaw_state_patcher.stop()
        self._openclaw_state_tmp.cleanup()

    def _run_and_parse_stdout(self, fn) -> dict:
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = fn()
        self.assertIsInstance(code, int)
        raw = buf.getvalue().strip()
        self.assertTrue(raw, "expected JSON on stdout")
        return json.loads(raw)

    def test_cast_send_retries_underpriced_then_succeeds(self) -> None:
        tx_obj = {
            "from": "0x1111111111111111111111111111111111111111",
            "to": "0x2222222222222222222222222222222222222222",
            "data": "0xdeadbeef",
        }
        commands: list[list[str]] = []

        def fake_run(cmd: list[str], text: bool = True, capture_output: bool = True, **kwargs):  # type: ignore[override]
            commands.append(cmd)
            if cmd[1] == "nonce":
                return mock.Mock(returncode=0, stdout="0x1", stderr="")
            if cmd[1] == "send":
                send_index = len([entry for entry in commands if len(entry) > 1 and entry[1] == "send"])
                if send_index == 1:
                    return mock.Mock(returncode=1, stdout="", stderr="replacement transaction underpriced")
                return mock.Mock(returncode=0, stdout='{"transactionHash":"0x' + "ab" * 32 + '"}', stderr="")
            raise AssertionError(f"Unexpected command {cmd}")

        with mock.patch.dict(cli.os.environ, {"XCLAW_TX_FEE_MODE": "legacy"}, clear=False), mock.patch.object(
            cli, "_require_cast_bin", return_value="cast"
        ), mock.patch.object(
            cli.subprocess, "run", side_effect=fake_run
        ), mock.patch.object(cli.time, "sleep") as sleep_mock:
            tx_hash = cli._cast_rpc_send_transaction("https://rpc.example", tx_obj, "0x" + "11" * 32)

        self.assertEqual(tx_hash, "0x" + "ab" * 32)
        send_cmds = [entry for entry in commands if len(entry) > 1 and entry[1] == "send"]
        self.assertEqual(len(send_cmds), 2)
        self.assertNotIn("--nonce", send_cmds[0])
        self.assertIn("--nonce", send_cmds[1])
        self.assertIn("1", send_cmds[1])
        self.assertIn(str(30 * (10**9)), send_cmds[0])
        self.assertIn(str(50 * (10**9)), send_cmds[1])
        sleep_mock.assert_called_once_with(0.25)

    def test_chain_rpc_url_prefers_primary_when_healthy(self) -> None:
        with mock.patch.object(
            cli,
            "_load_chain_config",
            return_value={"rpc": {"primary": "https://rpc-primary.example", "fallback": "https://rpc-fallback.example"}},
        ), mock.patch.object(
            cli,
            "_is_rpc_endpoint_healthy",
            side_effect=lambda url: url == "https://rpc-primary.example",
        ):
            selected = cli._chain_rpc_url("base_sepolia")
        self.assertEqual(selected, "https://rpc-primary.example")

    def test_chain_rpc_url_falls_back_when_primary_unhealthy(self) -> None:
        with mock.patch.object(
            cli,
            "_load_chain_config",
            return_value={"rpc": {"primary": "https://rpc-primary.example", "fallback": "https://rpc-fallback.example"}},
        ), mock.patch.object(
            cli,
            "_is_rpc_endpoint_healthy",
            side_effect=lambda url: url == "https://rpc-fallback.example",
        ):
            selected = cli._chain_rpc_url("base_sepolia")
        self.assertEqual(selected, "https://rpc-fallback.example")

    def test_cast_send_non_retryable_error_fails_immediately(self) -> None:
        tx_obj = {
            "from": "0x1111111111111111111111111111111111111111",
            "to": "0x2222222222222222222222222222222222222222",
            "data": "0xdeadbeef",
        }
        commands: list[list[str]] = []

        def fake_run(cmd: list[str], text: bool = True, capture_output: bool = True, **kwargs):  # type: ignore[override]
            commands.append(cmd)
            if cmd[1] == "nonce":
                return mock.Mock(returncode=0, stdout="0x2", stderr="")
            if cmd[1] == "send":
                return mock.Mock(returncode=1, stdout="", stderr="execution reverted")
            raise AssertionError(f"Unexpected command {cmd}")

        with mock.patch.dict(cli.os.environ, {"XCLAW_TX_FEE_MODE": "legacy"}, clear=False), mock.patch.object(
            cli, "_require_cast_bin", return_value="cast"
        ), mock.patch.object(
            cli.subprocess, "run", side_effect=fake_run
        ):
            with self.assertRaises(cli.WalletStoreError):
                cli._cast_rpc_send_transaction("https://rpc.example", tx_obj, "0x" + "22" * 32)

        send_cmds = [entry for entry in commands if len(entry) > 1 and entry[1] == "send"]
        self.assertEqual(len(send_cmds), 1)

    def test_cast_send_retry_budget_exhausted(self) -> None:
        tx_obj = {
            "from": "0x1111111111111111111111111111111111111111",
            "to": "0x2222222222222222222222222222222222222222",
            "data": "0xdeadbeef",
        }

        def fake_run(cmd: list[str], text: bool = True, capture_output: bool = True, **kwargs):  # type: ignore[override]
            if cmd[1] == "nonce":
                return mock.Mock(returncode=0, stdout="0x3", stderr="")
            if cmd[1] == "send":
                return mock.Mock(returncode=1, stdout="", stderr="nonce too low")
            raise AssertionError(f"Unexpected command {cmd}")

        with mock.patch.dict(
            cli.os.environ, {"XCLAW_TX_SEND_MAX_ATTEMPTS": "2", "XCLAW_TX_FEE_MODE": "legacy"}, clear=False
        ), mock.patch.object(
            cli, "_require_cast_bin", return_value="cast"
        ), mock.patch.object(cli.subprocess, "run", side_effect=fake_run):
            with self.assertRaises(cli.WalletStoreError) as ctx:
                cli._cast_rpc_send_transaction("https://rpc.example", tx_obj, "0x" + "33" * 32)

        self.assertIn("after 2 attempts", str(ctx.exception))

    def test_estimate_tx_fees_eip1559_happy_path(self) -> None:
        with mock.patch.dict(
            cli.os.environ,
            {"XCLAW_TX_FEE_MODE": "rpc", "XCLAW_TX_RETRY_BUMP_BPS": "1250", "XCLAW_TX_PRIORITY_FLOOR_GWEI": "1"},
            clear=False,
        ), mock.patch.object(
            cli,
            "_rpc_json_call",
            side_effect=[
                {"baseFeePerGas": ["0x3b9aca00"], "reward": [["0x59682f00"]]},
                "0x77359400",
                {"baseFeePerGas": ["0x3b9aca00"], "reward": [["0x59682f00"]]},
                "0x77359400",
            ],
        ):
            fee0 = cli._estimate_tx_fees("https://rpc.example", 0)
            fee1 = cli._estimate_tx_fees("https://rpc.example", 1)

        self.assertEqual(fee0.get("mode"), "eip1559")
        self.assertEqual(fee0.get("maxPriorityFeePerGas"), int("0x77359400", 16))
        self.assertEqual(fee0.get("maxFeePerGas"), int("0x3b9aca00", 16) * 2 + int("0x77359400", 16))
        self.assertGreater(int(fee1.get("maxFeePerGas", 0)), int(fee0.get("maxFeePerGas", 0)))
        self.assertGreater(int(fee1.get("maxPriorityFeePerGas", 0)), int(fee0.get("maxPriorityFeePerGas", 0)))

    def test_estimate_tx_fees_falls_back_to_legacy_rpc_gas_price(self) -> None:
        with mock.patch.dict(cli.os.environ, {"XCLAW_TX_FEE_MODE": "rpc"}, clear=False), mock.patch.object(
            cli,
            "_rpc_json_call",
            side_effect=[cli.WalletStoreError("fee history unsupported"), "0x3b9aca00"],
        ):
            fee = cli._estimate_tx_fees("https://rpc.example", 2)
        self.assertEqual(fee.get("mode"), "legacy")
        self.assertGreater(int(fee.get("gasPrice", 0)), int("0x3b9aca00", 16))

    def test_cast_send_uses_eip1559_flags(self) -> None:
        tx_obj = {
            "from": "0x1111111111111111111111111111111111111111",
            "to": "0x2222222222222222222222222222222222222222",
            "data": "0xdeadbeef",
        }
        commands: list[list[str]] = []

        def fake_run(cmd: list[str], text: bool = True, capture_output: bool = True, **kwargs):  # type: ignore[override]
            commands.append(cmd)
            if cmd[1] == "send":
                return mock.Mock(returncode=0, stdout='{"transactionHash":"0x' + "ab" * 32 + '"}', stderr="")
            raise AssertionError(f"Unexpected command {cmd}")

        with mock.patch.object(cli, "_require_cast_bin", return_value="cast"), mock.patch.object(
            cli.subprocess, "run", side_effect=fake_run
        ), mock.patch.object(
            cli,
            "_estimate_tx_fees",
            return_value={"mode": "eip1559", "maxFeePerGas": 123, "maxPriorityFeePerGas": 77},
        ):
            tx_hash = cli._cast_rpc_send_transaction("https://rpc.example", tx_obj, "0x" + "11" * 32)

        self.assertEqual(tx_hash, "0x" + "ab" * 32)
        send_cmd = [entry for entry in commands if len(entry) > 1 and entry[1] == "send"][0]
        self.assertIn("--max-fee-per-gas", send_cmd)
        self.assertIn("123", send_cmd)
        self.assertIn("--priority-gas-price", send_cmd)
        self.assertIn("77", send_cmd)
        self.assertNotIn("--gas-price", send_cmd)

    def test_builder_code_suffix_applies_for_base_non_empty_calldata(self) -> None:
        tx_obj = {
            "from": "0x1111111111111111111111111111111111111111",
            "to": "0x2222222222222222222222222222222222222222",
            "data": "0xdeadbeef",
        }
        commands: list[list[str]] = []
        tx_hash = "0x" + "ab" * 32

        def fake_run(cmd: list[str], text: bool = True, capture_output: bool = True, **kwargs):  # type: ignore[override]
            commands.append(cmd)
            if cmd[1] == "send":
                return mock.Mock(returncode=0, stdout='{"transactionHash":"' + tx_hash + '"}', stderr="")
            raise AssertionError(f"Unexpected command {cmd}")

        with mock.patch.dict(cli.os.environ, {"XCLAW_BUILDER_CODE_BASE": "bc_test", "XCLAW_TX_FEE_MODE": "legacy"}, clear=False), mock.patch.object(
            cli, "_require_cast_bin", return_value="cast"
        ), mock.patch.object(
            cli.subprocess, "run", side_effect=fake_run
        ), mock.patch.object(
            cli, "_estimate_tx_fees", return_value={"mode": "legacy", "gasPrice": 1}
        ):
            out_hash = cli._cast_rpc_send_transaction("https://rpc.example", tx_obj, "0x" + "11" * 32, chain="base_mainnet")

        self.assertEqual(out_hash, tx_hash)
        send_cmd = [entry for entry in commands if len(entry) > 1 and entry[1] == "send"][0]
        calldata = next((part for part in send_cmd if isinstance(part, str) and part.startswith("0xdeadbeef")), "")
        self.assertTrue(calldata.endswith(cli._erc8021_magic_hex()))
        meta = cli._builder_output_from_hashes("base_mainnet", [tx_hash])
        self.assertTrue(meta.get("builderCodeApplied"))
        self.assertEqual(meta.get("builderCodeSource"), "XCLAW_BUILDER_CODE_BASE")
        self.assertEqual(meta.get("builderCodeStandard"), "erc8021")

    def test_builder_code_suffix_skips_empty_calldata_safe_mode(self) -> None:
        tx_obj = {
            "from": "0x1111111111111111111111111111111111111111",
            "to": "0x2222222222222222222222222222222222222222",
            "data": "0x",
        }
        commands: list[list[str]] = []
        tx_hash = "0x" + "cd" * 32

        def fake_run(cmd: list[str], text: bool = True, capture_output: bool = True, **kwargs):  # type: ignore[override]
            commands.append(cmd)
            if cmd[1] == "send":
                return mock.Mock(returncode=0, stdout='{"transactionHash":"' + tx_hash + '"}', stderr="")
            raise AssertionError(f"Unexpected command {cmd}")

        with mock.patch.dict(cli.os.environ, {"XCLAW_BUILDER_CODE_BASE": "bc_test", "XCLAW_TX_FEE_MODE": "legacy"}, clear=False), mock.patch.object(
            cli, "_require_cast_bin", return_value="cast"
        ), mock.patch.object(
            cli.subprocess, "run", side_effect=fake_run
        ), mock.patch.object(
            cli, "_estimate_tx_fees", return_value={"mode": "legacy", "gasPrice": 1}
        ):
            out_hash = cli._cast_rpc_send_transaction("https://rpc.example", tx_obj, "0x" + "11" * 32, chain="base_mainnet")

        self.assertEqual(out_hash, tx_hash)
        send_cmd = [entry for entry in commands if len(entry) > 1 and entry[1] == "send"][0]
        self.assertFalse(any(isinstance(part, str) and part.startswith("0x") and part.endswith(cli._erc8021_magic_hex()) for part in send_cmd))
        meta = cli._builder_output_from_hashes("base_mainnet", [tx_hash])
        self.assertEqual(meta.get("builderCodeSkippedReason"), "empty_calldata_safe_mode")
        self.assertFalse(meta.get("builderCodeApplied"))

    def test_builder_code_suffix_missing_env_fails_closed(self) -> None:
        tx_obj = {
            "from": "0x1111111111111111111111111111111111111111",
            "to": "0x2222222222222222222222222222222222222222",
            "data": "0xdeadbeef",
        }
        with mock.patch.dict(cli.os.environ, {}, clear=True), mock.patch.object(cli, "_require_cast_bin", return_value="cast"):
            with self.assertRaises(cli.WalletStoreError) as ctx:
                cli._cast_rpc_send_transaction("https://rpc.example", tx_obj, "0x" + "11" * 32, chain="base_mainnet")
        self.assertIn("builder_code_missing", str(ctx.exception))

    def test_builder_code_suffix_skips_non_base_chain(self) -> None:
        tx_obj = {
            "from": "0x1111111111111111111111111111111111111111",
            "to": "0x2222222222222222222222222222222222222222",
            "data": "0xdeadbeef",
        }
        commands: list[list[str]] = []
        tx_hash = "0x" + "ef" * 32

        def fake_run(cmd: list[str], text: bool = True, capture_output: bool = True, **kwargs):  # type: ignore[override]
            commands.append(cmd)
            if cmd[1] == "send":
                return mock.Mock(returncode=0, stdout='{"transactionHash":"' + tx_hash + '"}', stderr="")
            raise AssertionError(f"Unexpected command {cmd}")

        with mock.patch.dict(cli.os.environ, {"XCLAW_TX_FEE_MODE": "legacy"}, clear=False), mock.patch.object(
            cli, "_require_cast_bin", return_value="cast"
        ), mock.patch.object(
            cli.subprocess, "run", side_effect=fake_run
        ), mock.patch.object(
            cli, "_estimate_tx_fees", return_value={"mode": "legacy", "gasPrice": 1}
        ):
            out_hash = cli._cast_rpc_send_transaction("https://rpc.example", tx_obj, "0x" + "11" * 32, chain="ethereum_sepolia")

        self.assertEqual(out_hash, tx_hash)
        send_cmd = [entry for entry in commands if len(entry) > 1 and entry[1] == "send"][0]
        self.assertIn("0xdeadbeef", send_cmd)
        self.assertFalse(any(isinstance(part, str) and part.endswith(cli._erc8021_magic_hex()) for part in send_cmd))
        meta = cli._builder_output_from_hashes("ethereum_sepolia", [tx_hash])
        self.assertFalse(meta.get("builderCodeChainEligible"))

    def test_builder_code_suffix_already_tagged_not_double_appended(self) -> None:
        suffix = cli._encode_erc8021_suffix(["bc_test"])
        tagged_data = "0xdeadbeef" + suffix[2:]
        tx_obj = {
            "from": "0x1111111111111111111111111111111111111111",
            "to": "0x2222222222222222222222222222222222222222",
            "data": tagged_data,
        }
        commands: list[list[str]] = []
        tx_hash = "0x" + "12" * 32

        def fake_run(cmd: list[str], text: bool = True, capture_output: bool = True, **kwargs):  # type: ignore[override]
            commands.append(cmd)
            if cmd[1] == "send":
                return mock.Mock(returncode=0, stdout='{"transactionHash":"' + tx_hash + '"}', stderr="")
            raise AssertionError(f"Unexpected command {cmd}")

        with mock.patch.dict(cli.os.environ, {"XCLAW_BUILDER_CODE_BASE": "bc_test", "XCLAW_TX_FEE_MODE": "legacy"}, clear=False), mock.patch.object(
            cli, "_require_cast_bin", return_value="cast"
        ), mock.patch.object(
            cli.subprocess, "run", side_effect=fake_run
        ), mock.patch.object(
            cli, "_estimate_tx_fees", return_value={"mode": "legacy", "gasPrice": 1}
        ):
            out_hash = cli._cast_rpc_send_transaction("https://rpc.example", tx_obj, "0x" + "11" * 32, chain="base_mainnet")

        self.assertEqual(out_hash, tx_hash)
        send_cmd = [entry for entry in commands if len(entry) > 1 and entry[1] == "send"][0]
        calldata = next((part for part in send_cmd if isinstance(part, str) and part.startswith("0xdeadbeef")), "")
        self.assertEqual(calldata, tagged_data)
        meta = cli._builder_output_from_hashes("base_mainnet", [tx_hash])
        self.assertEqual(meta.get("builderCodeSkippedReason"), "already_tagged")

    def test_builder_code_env_precedence_scoped_then_base_default(self) -> None:
        with mock.patch.dict(
            cli.os.environ,
            {
                "XCLAW_BUILDER_CODE_BASE": "bc_base",
                "XCLAW_BUILDER_CODE_BASE_MAINNET": "bc_mainnet",
            },
            clear=False,
        ):
            value_mainnet, source_mainnet = cli._resolve_builder_code_for_chain("base_mainnet")
            value_sepolia, source_sepolia = cli._resolve_builder_code_for_chain("base_sepolia")
        self.assertEqual((value_mainnet, source_mainnet), ("bc_mainnet", "XCLAW_BUILDER_CODE_BASE_MAINNET"))
        self.assertEqual((value_sepolia, source_sepolia), ("bc_base", "XCLAW_BUILDER_CODE_BASE"))

    def test_wait_for_trade_approval_telegram_returns_quick_pending(self) -> None:
        with mock.patch.object(cli, "_maybe_send_telegram_approval_prompt"), mock.patch.object(
            cli, "_last_delivery_is_telegram", return_value=True
        ), mock.patch.object(cli, "_trade_approval_inline_wait_sec", return_value=1), mock.patch.object(
            cli, "_read_trade_details", return_value={"tradeId": "trd_1", "status": "approval_pending"}
        ), mock.patch.object(cli.time, "sleep"), mock.patch.object(cli.time, "time", side_effect=[0, 0, 2]):
            with self.assertRaises(cli.WalletPolicyError) as ctx:
                cli._wait_for_trade_approval("trd_1", "base_sepolia", {"tokenInSymbol": "WETH", "tokenOutSymbol": "USDC"})
        self.assertEqual(ctx.exception.code, "approval_required")
        self.assertEqual(ctx.exception.details.get("lastStatus"), "approval_pending")
        self.assertIn("resumes automatically", str(ctx.exception.action_hint or "").lower())

    def test_wait_for_trade_approval_approved_path_returns_trade(self) -> None:
        with mock.patch.object(cli, "_maybe_send_telegram_approval_prompt"), mock.patch.object(
            cli, "_last_delivery_is_telegram", return_value=False
        ), mock.patch.object(
            cli,
            "_read_trade_details",
            side_effect=[
                {"tradeId": "trd_1", "status": "approval_pending"},
                {"tradeId": "trd_1", "status": "approved"},
            ],
        ), mock.patch.object(cli.time, "sleep"), mock.patch.object(
            cli.time, "time", side_effect=[0, 0, 1]
        ), mock.patch.object(cli, "_maybe_delete_telegram_approval_prompt"), mock.patch.object(
            cli, "_maybe_send_telegram_decision_message"
        ), mock.patch.object(cli, "_remove_pending_spot_trade_flow"), mock.patch.object(
            cli, "_remove_approval_prompt"
        ):
            trade = cli._wait_for_trade_approval("trd_1", "base_sepolia", {"tokenInSymbol": "WETH", "tokenOutSymbol": "USDC"})
        self.assertEqual(str(trade.get("status")), "approved")

    def test_intents_poll_success(self) -> None:
        args = argparse.Namespace(chain="hardhat_local", json=True)
        with mock.patch.object(
            cli,
            "_api_request",
            return_value=(200, {"items": [{"tradeId": "trd_1", "status": "approved"}]})
        ):
            code = cli.cmd_intents_poll(args)
        self.assertEqual(code, 0)

    def test_approvals_check_pending_rejected(self) -> None:
        args = argparse.Namespace(intent="trd_1", chain="hardhat_local", json=True)
        with mock.patch.object(
            cli,
            "_read_trade_details",
            return_value={"tradeId": "trd_1", "chainKey": "hardhat_local", "status": "approval_pending", "retry": {"eligible": False}},
        ):
            code = cli.cmd_approvals_check(args)
        self.assertEqual(code, 1)

    def test_trade_execute_rejects_mock_mode(self) -> None:
        args = argparse.Namespace(intent="trd_1", chain="hardhat_local", json=True)
        trade_payload = {
            "tradeId": "trd_1",
            "chainKey": "hardhat_local",
            "status": "approved",
            "mode": "mock",
            "retry": {"eligible": False},
        }
        with mock.patch.object(cli, "_read_trade_details", return_value=trade_payload), mock.patch.object(
            cli, "_post_trade_status"
        ) as post_mock:
            payload = self._run_and_parse_stdout(lambda: cli.cmd_trade_execute(args))
        self.assertFalse(payload.get("ok"))
        self.assertEqual(payload.get("code"), "unsupported_mode")
        post_mock.assert_not_called()

    def test_trade_execute_retry_not_eligible_denied(self) -> None:
        args = argparse.Namespace(intent="trd_1", chain="hardhat_local", json=True)
        trade_payload = {
            "tradeId": "trd_1",
            "chainKey": "hardhat_local",
            "status": "failed",
            "mode": "mock",
            "retry": {"eligible": False, "failedAttempts": 3, "maxRetries": 3},
        }

        with mock.patch.object(cli, "_read_trade_details", return_value=trade_payload):
            code = cli.cmd_trade_execute(args)

        self.assertEqual(code, 1)

    def test_report_send_deprecated(self) -> None:
        args = argparse.Namespace(trade="trd_1", json=True)
        with mock.patch.object(
            cli,
            "_read_trade_details",
            return_value={"tradeId": "trd_1", "agentId": "agt_1", "status": "filled", "mode": "mock", "chainKey": "hardhat_local", "reasonCode": None},
        ), mock.patch.object(cli, "_api_request") as api_mock:
            payload = self._run_and_parse_stdout(lambda: cli.cmd_report_send(args))
        self.assertFalse(payload.get("ok"))
        self.assertEqual(payload.get("code"), "report_send_deprecated")
        api_mock.assert_not_called()

    def test_report_send_rejects_real_trade(self) -> None:
        args = argparse.Namespace(trade="trd_real_1", json=True)
        with mock.patch.object(
            cli,
            "_read_trade_details",
            return_value={"tradeId": "trd_real_1", "agentId": "agt_1", "status": "filled", "mode": "real", "chainKey": "base_sepolia"},
        ), mock.patch.object(cli, "_api_request") as api_mock:
            code = cli.cmd_report_send(args)
        self.assertEqual(code, 1)
        api_mock.assert_not_called()

    def test_chat_poll_success(self) -> None:
        args = argparse.Namespace(chain="hardhat_local", json=True)
        with mock.patch.object(
            cli,
            "_api_request",
            return_value=(200, {"items": [{"messageId": "msg_1", "agentId": "ag_1", "message": "Watching WETH/USDC"}]}),
        ):
            code = cli.cmd_chat_poll(args)
        self.assertEqual(code, 0)

    def test_chat_post_success(self) -> None:
        args = argparse.Namespace(message=" Watching WETH/USDC ", chain="hardhat_local", tags="idea,alpha", json=True)
        with mock.patch.object(
            cli,
            "_resolve_api_key",
            return_value="xak1.ag_1.sig.payload",
        ), mock.patch.object(
            cli,
            "_resolve_agent_id",
            return_value="ag_1",
        ), mock.patch.object(
            cli,
            "_api_request",
            return_value=(200, {"item": {"messageId": "msg_1"}}),
        ):
            code = cli.cmd_chat_post(args)
        self.assertEqual(code, 0)

    def test_chat_post_rejects_empty_message(self) -> None:
        args = argparse.Namespace(message="   ", chain="hardhat_local", tags=None, json=True)
        code = cli.cmd_chat_post(args)
        self.assertEqual(code, 1)

    def test_faucet_request_success(self) -> None:
        args = argparse.Namespace(chain="base_sepolia", asset=[], json=True)
        with mock.patch.object(cli, "_resolve_api_key", return_value="xak1.ag_1.sig.payload"), mock.patch.object(
            cli, "_resolve_agent_id", return_value="ag_1"
        ), mock.patch.object(
            cli, "_api_request", return_value=(200, {"amountWei": "50000000000000000", "txHash": "0x" + "ab" * 32})
        ):
            payload = self._run_and_parse_stdout(lambda: cli.cmd_faucet_request(args))
        self.assertTrue(payload.get("ok"))
        self.assertEqual(payload.get("code"), "ok")
        self.assertEqual(payload.get("chain"), "base_sepolia")
        self.assertEqual(payload.get("pending"), True)
        self.assertIsInstance(payload.get("recommendedDelaySec"), int)
        self.assertIsInstance(payload.get("nextAction"), str)

    def test_faucet_request_with_assets_passes_payload(self) -> None:
        args = argparse.Namespace(chain="kite_ai_testnet", asset=["native", "stable"], json=True)
        captured: dict[str, object] = {}

        def fake_api_request(method: str, path: str, payload=None, include_idempotency=False):
            captured["method"] = method
            captured["path"] = path
            captured["payload"] = payload
            captured["include_idempotency"] = include_idempotency
            return 200, {"amountWei": "20000000000000000", "txHash": "0x" + "cd" * 32, "requestedAssets": ["native", "stable"]}

        with mock.patch.object(cli, "_resolve_api_key", return_value="xak1.ag_1.sig.payload"), mock.patch.object(
            cli, "_resolve_agent_id", return_value="ag_1"
        ), mock.patch.object(cli, "_api_request", side_effect=fake_api_request):
            payload = self._run_and_parse_stdout(lambda: cli.cmd_faucet_request(args))

        self.assertTrue(payload.get("ok"))
        request_payload = captured.get("payload")
        self.assertIsInstance(request_payload, dict)
        self.assertEqual((request_payload or {}).get("chainKey"), "kite_ai_testnet")
        self.assertEqual((request_payload or {}).get("assets"), ["native", "stable"])

    def test_faucet_networks_success(self) -> None:
        args = argparse.Namespace(json=True)
        with mock.patch.object(cli, "_resolve_api_key", return_value="xak1.ag_1.sig.payload"), mock.patch.object(
            cli, "_resolve_agent_id", return_value="ag_1"
        ), mock.patch.object(
            cli,
            "_api_request",
            return_value=(
                200,
                {"networks": [{"chainKey": "base_sepolia"}, {"chainKey": "kite_ai_testnet"}]},
            ),
        ):
            payload = self._run_and_parse_stdout(lambda: cli.cmd_faucet_networks(args))
        self.assertTrue(payload.get("ok"))
        self.assertEqual(payload.get("count"), 2)

    def test_faucet_request_rejects_chain_without_faucet_capability(self) -> None:
        args = argparse.Namespace(chain="hardhat_local", asset=[], json=True)
        payload = self._run_and_parse_stdout(lambda: cli.cmd_faucet_request(args))
        self.assertFalse(payload.get("ok"))
        self.assertEqual(payload.get("code"), "unsupported_chain_capability")

    def test_chains_command_success(self) -> None:
        args = argparse.Namespace(include_disabled=False, json=True)
        payload = self._run_and_parse_stdout(lambda: cli.cmd_chains(args))
        self.assertTrue(payload.get("ok"))
        self.assertGreaterEqual(int(payload.get("count") or 0), 1)
        first = (payload.get("chains") or [None])[0]
        self.assertIsInstance(first, dict)
        self.assertIn("capabilities", first)

    def test_status_includes_agent_name_best_effort(self) -> None:
        args = argparse.Namespace(json=True)
        with mock.patch.dict(cli.os.environ, {"XCLAW_DEFAULT_CHAIN": "base_sepolia", "XCLAW_API_BASE_URL": "https://xclaw.trade"}, clear=False), mock.patch.object(
            cli, "_resolve_api_key", return_value="xak1.ag_1.sig.payload"
        ), mock.patch.object(cli, "_resolve_agent_id", return_value="ag_1"), mock.patch.object(
            cli, "_wallet_address_for_chain", return_value="0x" + "11" * 20
        ), mock.patch.object(
            cli,
            "_http_json_request",
            return_value=(200, {"agent": {"agent_id": "ag_1", "agent_name": "harvey-ops"}}),
        ):
            payload = self._run_and_parse_stdout(lambda: cli.cmd_status(args))
        self.assertTrue(payload.get("ok"))
        self.assertEqual(payload.get("agentId"), "ag_1")
        self.assertEqual(payload.get("agentName"), "harvey-ops")

    def test_limit_orders_run_loop_emits_single_json(self) -> None:
        args = argparse.Namespace(chain="base_sepolia", sync=False, interval_sec=1, iterations=1, json=True)

        def fake_run_once(nested):
            return cli.ok("Limit-order run completed.", chain=nested.chain, synced=False, replayed=0, outboxRemaining=0, executed=0, skipped=0)

        with mock.patch.object(cli, "cmd_limit_orders_run_once", side_effect=fake_run_once):
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = cli.cmd_limit_orders_run_loop(args)
        self.assertEqual(code, 0)
        raw_lines = [line for line in buf.getvalue().splitlines() if line.strip()]
        self.assertEqual(len(raw_lines), 1)
        parsed = json.loads(raw_lines[0])
        self.assertTrue(parsed.get("ok"))

    def test_trade_spot_blocks_when_approval_pending(self) -> None:
        args = argparse.Namespace(
            chain="base_sepolia",
            token_in="WETH",
            token_out="USDC",
            amount_in="1",
            slippage_bps=50,
            deadline_sec=120,
            to=None,
            json=True,
        )

        with tempfile.TemporaryDirectory() as tmpdir, mock.patch.object(
            cli, "APP_DIR", pathlib.Path(tmpdir)
        ), mock.patch.object(
            cli, "PENDING_TRADE_INTENTS_FILE", pathlib.Path(tmpdir) / "pending-trade-intents.json"
        ), mock.patch.object(cli, "_replay_trade_usage_outbox"), mock.patch.object(
            cli, "_resolve_token_address", side_effect=["0x" + "11" * 20, "0x" + "22" * 20]
        ), mock.patch.object(
            cli, "load_wallet_store", return_value={}
        ), mock.patch.object(
            cli, "_execution_wallet", return_value=("0x" + "33" * 20, "0x" + "44" * 32)
        ), mock.patch.object(
            cli, "_require_cast_bin", return_value="cast"
        ), mock.patch.object(
            cli, "_chain_rpc_url", return_value="https://rpc.example"
        ), mock.patch.object(
            cli, "_require_chain_contract_address", return_value="0x" + "55" * 20
        ), mock.patch.object(
            cli,
            "_fetch_erc20_metadata",
            side_effect=[{"symbol": "WETH", "decimals": 18}, {"symbol": "USDC", "decimals": 6}],
        ), mock.patch.object(
            cli, "_enforce_spend_preconditions", return_value=({}, "2026-02-15", 0, 0)
        ), mock.patch.object(
            cli, "_router_get_amount_out", return_value=123
        ), mock.patch.object(
            cli, "_enforce_trade_caps", return_value=({}, "2026-02-15", Decimal("0"), 0, {"maxDailyUsd": "250", "maxDailyTradeCount": 50})
        ), mock.patch.object(
            cli, "_post_trade_proposed", return_value={"ok": True, "tradeId": "trd_1", "status": "approval_pending"}
        ), mock.patch.object(
            cli,
            "_wait_for_trade_approval",
            side_effect=cli.WalletPolicyError(
                "approval_required",
                "Trade is waiting for management approval.",
                "Approve trade from authorized management view, then retry.",
                {"tradeId": "trd_1", "chain": "base_sepolia"},
            ),
        ), mock.patch.object(
            cli, "_cast_rpc_send_transaction"
        ) as send_mock:
            payload = self._run_and_parse_stdout(lambda: cli.cmd_trade_spot(args))
        self.assertFalse(payload.get("ok"))
        self.assertEqual(payload.get("code"), "approval_required")
        send_mock.assert_not_called()

    def test_trade_spot_records_pending_spot_flow_context(self) -> None:
        args = argparse.Namespace(
            chain="base_sepolia",
            token_in="WETH",
            token_out="USDC",
            amount_in="1",
            slippage_bps=50,
            deadline_sec=120,
            to=None,
            json=True,
        )

        with tempfile.TemporaryDirectory() as tmpdir, mock.patch.object(cli, "APP_DIR", pathlib.Path(tmpdir)), mock.patch.object(
            cli, "PENDING_TRADE_INTENTS_FILE", pathlib.Path(tmpdir) / "pending-trade-intents.json"
        ), mock.patch.object(
            cli, "PENDING_SPOT_TRADE_FLOWS_FILE", pathlib.Path(tmpdir) / "pending-spot-trade-flows.json"
        ), mock.patch.object(cli, "_replay_trade_usage_outbox"), mock.patch.object(
            cli, "_resolve_token_address", side_effect=["0x" + "11" * 20, "0x" + "22" * 20]
        ), mock.patch.object(
            cli, "load_wallet_store", return_value={}
        ), mock.patch.object(
            cli, "_execution_wallet", return_value=("0x" + "33" * 20, "0x" + "44" * 32)
        ), mock.patch.object(
            cli, "_require_cast_bin", return_value="cast"
        ), mock.patch.object(
            cli, "_chain_rpc_url", return_value="https://rpc.example"
        ), mock.patch.object(
            cli, "_require_chain_contract_address", return_value="0x" + "55" * 20
        ), mock.patch.object(
            cli,
            "_fetch_erc20_metadata",
            side_effect=[{"symbol": "WETH", "decimals": 18}, {"symbol": "USDC", "decimals": 6}],
        ), mock.patch.object(
            cli, "_enforce_spend_preconditions", return_value=({}, "2026-02-15", 0, 0)
        ), mock.patch.object(
            cli, "_router_get_amount_out", return_value=123
        ), mock.patch.object(
            cli, "_enforce_trade_caps", return_value=({}, "2026-02-15", Decimal("0"), 0, {"maxDailyUsd": "250", "maxDailyTradeCount": 50})
        ), mock.patch.object(
            cli, "_post_trade_proposed", return_value={"ok": True, "tradeId": "trd_1", "status": "approval_pending"}
        ), mock.patch.object(
            cli,
            "_wait_for_trade_approval",
            side_effect=cli.WalletPolicyError(
                "approval_required",
                "Trade is waiting for management approval.",
                "Approve trade from authorized management view, then retry.",
                {"tradeId": "trd_1", "chain": "base_sepolia"},
            ),
        ):
            payload = self._run_and_parse_stdout(lambda: cli.cmd_trade_spot(args))
            flow = cli._get_pending_spot_trade_flow("trd_1")

        self.assertFalse(payload.get("ok"))
        self.assertEqual(payload.get("code"), "approval_required")
        self.assertIsInstance(flow, dict)
        self.assertEqual((flow or {}).get("tradeId"), "trd_1")
        self.assertEqual((flow or {}).get("chainKey"), "base_sepolia")
        self.assertEqual((flow or {}).get("tokenInSymbol"), "WETH")
        self.assertEqual((flow or {}).get("tokenOutSymbol"), "USDC")

    def test_approvals_resume_spot_blocks_when_trade_not_actionable(self) -> None:
        args = argparse.Namespace(trade_id="trd_1", chain="base_sepolia", json=True)
        with tempfile.TemporaryDirectory() as tmpdir, mock.patch.object(
            cli, "APP_DIR", pathlib.Path(tmpdir)
        ), mock.patch.object(
            cli, "PENDING_SPOT_TRADE_FLOWS_FILE", pathlib.Path(tmpdir) / "pending-spot-trade-flows.json"
        ), mock.patch.object(
            cli, "_read_trade_details", return_value={"tradeId": "trd_1", "chainKey": "base_sepolia", "status": "approval_pending"}
        ):
            payload = self._run_and_parse_stdout(lambda: cli.cmd_approvals_resume_spot(args))

        self.assertFalse(payload.get("ok"))
        self.assertEqual(payload.get("code"), "not_actionable")

    def test_approvals_resume_spot_executes_and_clears_saved_flow(self) -> None:
        args = argparse.Namespace(trade_id="trd_1", chain="base_sepolia", json=True)
        with tempfile.TemporaryDirectory() as tmpdir, mock.patch.object(
            cli, "APP_DIR", pathlib.Path(tmpdir)
        ), mock.patch.object(
            cli, "PENDING_SPOT_TRADE_FLOWS_FILE", pathlib.Path(tmpdir) / "pending-spot-trade-flows.json"
        ), mock.patch.object(
            cli, "_read_trade_details", return_value={"tradeId": "trd_1", "chainKey": "base_sepolia", "status": "approved"}
        ), mock.patch.object(
            cli, "cmd_trade_execute", return_value=0
        ):
            cli._record_pending_spot_trade_flow(
                "trd_1",
                {
                    "tradeId": "trd_1",
                    "chainKey": "base_sepolia",
                    "tokenInSymbol": "USDC",
                    "tokenOutSymbol": "WETH",
                    "amountInHuman": "50",
                    "slippageBps": 50,
                },
            )
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = cli.cmd_approvals_resume_spot(args)
            out = json.loads(buf.getvalue().strip())
            flow_after = cli._get_pending_spot_trade_flow("trd_1")

        self.assertEqual(code, 0)
        self.assertTrue(out.get("ok"))
        self.assertEqual(out.get("tradeId"), "trd_1")
        self.assertIsNone(flow_after)

    def test_trade_spot_reuses_existing_pending_trade_intent(self) -> None:
        args = argparse.Namespace(
            chain="base_sepolia",
            token_in="WETH",
            token_out="USDC",
            amount_in="5",
            slippage_bps=50,
            deadline_sec=120,
            to=None,
            json=True,
        )

        with tempfile.TemporaryDirectory() as tmpdir, mock.patch.object(cli, "APP_DIR", pathlib.Path(tmpdir)), mock.patch.object(
            cli, "PENDING_TRADE_INTENTS_FILE", pathlib.Path(tmpdir) / "pending-trade-intents.json"
        ), mock.patch.object(cli, "_replay_trade_usage_outbox"), mock.patch.object(
            cli, "_resolve_token_address", side_effect=["0x" + "11" * 20, "0x" + "22" * 20] * 2
        ), mock.patch.object(
            cli, "load_wallet_store", return_value={}
        ), mock.patch.object(
            cli, "_execution_wallet", return_value=("0x" + "33" * 20, "0x" + "44" * 32)
        ), mock.patch.object(
            cli, "_require_cast_bin", return_value="cast"
        ), mock.patch.object(
            cli, "_chain_rpc_url", return_value="https://rpc.example"
        ), mock.patch.object(
            cli, "_require_chain_contract_address", return_value="0x" + "55" * 20
        ), mock.patch.object(
            cli,
            "_fetch_erc20_metadata",
            side_effect=[
                {"symbol": "WETH", "decimals": 18},
                {"symbol": "USDC", "decimals": 6},
                {"symbol": "WETH", "decimals": 18},
                {"symbol": "USDC", "decimals": 6},
            ],
        ), mock.patch.object(
            cli, "_enforce_spend_preconditions", return_value=({}, "2026-02-15", 0, 0)
        ), mock.patch.object(
            cli, "_router_get_amount_out", return_value=123
        ), mock.patch.object(
            cli, "_enforce_trade_caps", return_value=({}, "2026-02-15", Decimal("0"), 0, {"maxDailyUsd": "250", "maxDailyTradeCount": 50})
        ), mock.patch.object(
            cli, "_read_trade_details", return_value={"tradeId": "trd_1", "chainKey": "base_sepolia", "status": "approval_pending"}
        ), mock.patch.object(
            cli, "_wait_for_trade_approval",
            side_effect=cli.WalletPolicyError(
                "approval_required",
                "Trade is waiting for management approval.",
                "Approve the pending trade (Telegram or web), then re-run the same trade command to resume without creating a new approval.",
                {"tradeId": "trd_1", "chain": "base_sepolia"},
            ),
        ) as wait_mock, mock.patch.object(
            cli, "_post_trade_proposed", return_value={"ok": True, "tradeId": "trd_1", "status": "approval_pending"}
        ) as propose_mock, mock.patch.object(cli, "_cast_rpc_send_transaction") as send_mock:
            first = self._run_and_parse_stdout(lambda: cli.cmd_trade_spot(args))
            second = self._run_and_parse_stdout(lambda: cli.cmd_trade_spot(args))

        self.assertFalse(first.get("ok"))
        self.assertEqual(first.get("code"), "approval_required")
        self.assertFalse(second.get("ok"))
        self.assertEqual(second.get("code"), "approval_required")
        self.assertEqual(propose_mock.call_count, 1, "should propose once then reuse the pending tradeId")
        self.assertGreaterEqual(wait_mock.call_count, 2, "should wait on both invocations")
        send_mock.assert_not_called()

    def test_trade_spot_requotes_after_approval_wait_for_min_out(self) -> None:
        args = argparse.Namespace(
            chain="base_sepolia",
            token_in="USDC",
            token_out="WETH",
            amount_in="50",
            slippage_bps="500",
            deadline_sec=120,
            to=None,
            json=True,
        )
        captured: dict[str, object] = {}

        def fake_calldata(signature: str, values: list[object]) -> str:
            if signature.startswith("swapExactTokensForTokens("):
                captured["swapValues"] = values
            return "0xdeadbeef"

        with mock.patch.object(cli, "_resolve_token_address", side_effect=["0x" + "11" * 20, "0x" + "22" * 20]), mock.patch.object(
            cli, "_execution_wallet", return_value=("0x" + "aa" * 20, "0x" + "33" * 32)
        ), mock.patch.object(
            cli, "_require_cast_bin", return_value="cast"
        ), mock.patch.object(cli, "_chain_rpc_url", return_value="https://rpc.example"), mock.patch.object(
            cli, "_require_chain_contract_address", return_value="0x" + "44" * 20
        ), mock.patch.object(cli, "_fetch_erc20_metadata", side_effect=[{"decimals": 18, "symbol": "USDC"}, {"decimals": 18, "symbol": "WETH"}]), mock.patch.object(
            cli, "_fetch_token_allowance_wei", return_value=str(10**30)
        ), mock.patch.object(
            cli, "_enforce_spend_preconditions", return_value=({}, "2026-02-14", 0, 10**30)
        ), mock.patch.object(
            cli, "_replay_trade_usage_outbox", return_value=(0, 0)
        ), mock.patch.object(
            cli, "_enforce_trade_caps", return_value=({}, "2026-02-14", cli.Decimal("0"), 0, {"maxDailyUsd": "1000", "maxDailyTradeCount": 10})
        ), mock.patch.object(
            cli, "_router_get_amount_out", side_effect=[1000, 600]
        ), mock.patch.object(
            cli, "_post_trade_proposed", return_value={"ok": True, "tradeId": "trd_1", "status": "approval_pending"}
        ), mock.patch.object(
            cli, "_wait_for_trade_approval", return_value={"tradeId": "trd_1", "status": "approved"}
        ), mock.patch.object(
            cli, "_post_trade_status"
        ), mock.patch.object(
            cli, "_record_trade_cap_ledger"
        ), mock.patch.object(
            cli, "_post_trade_usage"
        ), mock.patch.object(
            cli, "_record_spend"
        ), mock.patch.object(
            cli, "_cast_calldata", side_effect=fake_calldata
        ), mock.patch.object(
            cli, "_cast_rpc_send_transaction", return_value="0x" + "ab" * 32
        ), mock.patch.object(
            cli.subprocess, "run", return_value=mock.Mock(returncode=0, stdout='{"status":"0x1"}', stderr="")
        ):
            code = cli.cmd_trade_spot(args)

        self.assertEqual(code, 0)
        swap_values = captured.get("swapValues")
        self.assertIsInstance(swap_values, list)
        self.assertEqual(str(swap_values[0]), str(50 * 10**18))
        # Re-quoted output is 600, with 5% slippage => minOut=570.
        self.assertEqual(str(swap_values[1]), "570")

    def test_telegram_prompt_includes_swap_details(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir, mock.patch.object(cli, "APP_DIR", pathlib.Path(tmpdir)), mock.patch.object(
            cli, "APPROVAL_PROMPTS_FILE", pathlib.Path(tmpdir) / "approval_prompts.json"
        ), mock.patch.object(
            cli, "_get_approval_prompt", return_value=None
        ), mock.patch.object(
            cli, "_fetch_outbound_transfer_policy", return_value={"approvalChannels": {"telegram": {"enabled": True}}}
        ), mock.patch.object(
            cli, "_read_openclaw_last_delivery", return_value={"lastChannel": "telegram", "lastTo": "123", "lastThreadId": None}
        ), mock.patch.object(
            cli, "_require_openclaw_bin", return_value="openclaw"
        ) as _bin_mock:
            captured: dict[str, object] = {}

            def fake_run(cmd: list[str], timeout_sec: int, kind: str):
                captured["cmd"] = cmd
                return mock.Mock(returncode=0, stdout='{"payload":{"messageId":"777"}}', stderr="")

            with mock.patch.object(cli, "_run_subprocess", side_effect=fake_run), mock.patch.object(cli, "_post_approval_prompt_metadata"), mock.patch.object(
                cli, "_record_approval_prompt"
            ):
                cli._maybe_send_telegram_approval_prompt(
                    "trd_abc",
                    "base_sepolia",
                    {"amountInHuman": "5", "tokenInSymbol": "WETH", "tokenOutSymbol": "USDC", "slippageBps": 50},
                )

            cmd = captured.get("cmd") or []
            joined = " ".join(cmd)
            self.assertIn("--message", joined)
            # Message text is a separate arg; find it and assert on content.
            message_arg = None
            for idx, part in enumerate(cmd):
                if part == "--message" and idx + 1 < len(cmd):
                    message_arg = cmd[idx + 1]
                    break
            self.assertIsNotNone(message_arg)
            self.assertIn("Approve swap", message_arg)
            self.assertIn("5 WETH -> USDC", message_arg)
            self.assertIn("Trade: `trd_abc`", message_arg)

            # Buttons include both Approve and Deny.
            buttons_arg = None
            for idx, part in enumerate(cmd):
                if part == "--buttons" and idx + 1 < len(cmd):
                    buttons_arg = cmd[idx + 1]
                    break
            self.assertIsNotNone(buttons_arg)
            buttons = json.loads(buttons_arg or "[]")
            self.assertIsInstance(buttons, list)
            self.assertGreaterEqual(len(buttons), 1)
            row0 = buttons[0]
            self.assertIsInstance(row0, list)
            texts = [b.get("text") for b in row0 if isinstance(b, dict)]
            self.assertIn("Approve", texts)
            self.assertIn("Deny", texts)
            callback_data = [b.get("callback_data") for b in row0 if isinstance(b, dict)]
            self.assertIn("xappr|a|trd_abc|base_sepolia", callback_data)
            self.assertIn("xappr|r|trd_abc|base_sepolia", callback_data)

    def test_telegram_prompt_resends_when_existing_prompt_is_stale(self) -> None:
        stale = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
        with tempfile.TemporaryDirectory() as tmpdir, mock.patch.object(cli, "APP_DIR", pathlib.Path(tmpdir)), mock.patch.object(
            cli, "APPROVAL_PROMPTS_FILE", pathlib.Path(tmpdir) / "approval_prompts.json"
        ), mock.patch.object(
            cli, "_get_approval_prompt", return_value={"channel": "telegram", "updatedAt": stale}
        ), mock.patch.object(
            cli, "_trade_approval_prompt_resend_cooldown_sec", return_value=60
        ), mock.patch.object(
            cli, "_read_openclaw_last_delivery", return_value={"lastChannel": "telegram", "lastTo": "123", "lastThreadId": None}
        ), mock.patch.object(
            cli, "_require_openclaw_bin", return_value="openclaw"
        ):
            with mock.patch.object(cli, "_run_subprocess", return_value=mock.Mock(returncode=0, stdout='{"payload":{"messageId":"777"}}', stderr="")) as run_mock:
                cli._maybe_send_telegram_approval_prompt(
                    "trd_abc",
                    "base_sepolia",
                    {"amountInHuman": "5", "tokenInSymbol": "WETH", "tokenOutSymbol": "USDC"},
                )
            self.assertEqual(run_mock.call_count, 1)

    def test_telegram_prompt_skips_when_existing_prompt_within_cooldown(self) -> None:
        fresh = datetime.now(timezone.utc).isoformat()
        with tempfile.TemporaryDirectory() as tmpdir, mock.patch.object(cli, "APP_DIR", pathlib.Path(tmpdir)), mock.patch.object(
            cli, "APPROVAL_PROMPTS_FILE", pathlib.Path(tmpdir) / "approval_prompts.json"
        ), mock.patch.object(
            cli, "_get_approval_prompt", return_value={"channel": "telegram", "updatedAt": fresh}
        ), mock.patch.object(
            cli, "_trade_approval_prompt_resend_cooldown_sec", return_value=120
        ), mock.patch.object(
            cli, "_read_openclaw_last_delivery", return_value={"lastChannel": "telegram", "lastTo": "123", "lastThreadId": None}
        ), mock.patch.object(
            cli, "_require_openclaw_bin", return_value="openclaw"
        ):
            with mock.patch.object(cli, "_run_subprocess") as run_mock:
                cli._maybe_send_telegram_approval_prompt(
                    "trd_abc",
                    "base_sepolia",
                    {"amountInHuman": "5", "tokenInSymbol": "WETH", "tokenOutSymbol": "USDC"},
                )
            self.assertEqual(run_mock.call_count, 0)

    def test_telegram_transfer_prompt_includes_details_and_callbacks(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir, mock.patch.object(cli, "APP_DIR", pathlib.Path(tmpdir)), mock.patch.object(
            cli, "APPROVAL_PROMPTS_FILE", pathlib.Path(tmpdir) / "approval_prompts.json"
        ), mock.patch.object(
            cli, "_read_openclaw_last_delivery", return_value={"lastChannel": "telegram", "lastTo": "123", "lastThreadId": None}
        ), mock.patch.object(
            cli, "_require_openclaw_bin", return_value="openclaw"
        ):
            captured: dict[str, object] = {}

            def fake_run(cmd: list[str], timeout_sec: int, kind: str):
                captured["cmd"] = cmd
                return mock.Mock(returncode=0, stdout='{"payload":{"messageId":"777"}}', stderr="")

            with mock.patch.object(cli, "_run_subprocess", side_effect=fake_run):
                cli._maybe_send_telegram_transfer_approval_prompt(
                    {
                        "approvalId": "xfr_abc",
                        "chainKey": "base_sepolia",
                        "transferType": "token",
                        "tokenSymbol": "WETH",
                        "tokenDecimals": 18,
                        "amountWei": "1000000000000000",
                        "toAddress": "0x9099d24d55c105818b4e9ee117d87bc11063cf10",
                    }
                )

            cmd = captured.get("cmd") or []
            self.assertIn("--channel", cmd)
            self.assertIn("telegram", cmd)
            message_arg = None
            buttons_arg = None
            for idx, part in enumerate(cmd):
                if part == "--message" and idx + 1 < len(cmd):
                    message_arg = cmd[idx + 1]
                if part == "--buttons" and idx + 1 < len(cmd):
                    buttons_arg = cmd[idx + 1]
            self.assertIsNotNone(message_arg)
            self.assertIn("Approve transfer", message_arg)
            self.assertIn("Amount: 0.001 WETH", message_arg)
            self.assertIn("Approval: `xfr_abc`", message_arg)
            self.assertIsNotNone(buttons_arg)
            buttons = json.loads(buttons_arg or "[]")
            row0 = buttons[0]
            callback_data = [b.get("callback_data") for b in row0 if isinstance(b, dict)]
            self.assertIn("xfer|a|xfr_abc|base_sepolia", callback_data)
            self.assertIn("xfer|r|xfr_abc|base_sepolia", callback_data)
            entry = cli._get_transfer_approval_prompt("xfr_abc")
            self.assertIsInstance(entry, dict)
            self.assertEqual((entry or {}).get("messageId"), "777")
            self.assertEqual((entry or {}).get("channel"), "telegram")

    def test_telegram_transfer_prompt_skips_when_last_channel_not_telegram(self) -> None:
        with mock.patch.object(cli, "_read_openclaw_last_delivery", return_value={"lastChannel": "web", "lastTo": "123", "lastThreadId": None}), mock.patch.object(
            cli, "_run_subprocess"
        ) as run_mock:
            cli._maybe_send_telegram_transfer_approval_prompt(
                {
                    "approvalId": "xfr_abc",
                    "chainKey": "base_sepolia",
                    "transferType": "token",
                    "tokenSymbol": "WETH",
                    "tokenDecimals": 18,
                    "amountWei": "1000000000000000",
                    "toAddress": "0x9099d24d55c105818b4e9ee117d87bc11063cf10",
                }
            )
        run_mock.assert_not_called()

    def test_telegram_policy_prompt_includes_details_and_callbacks(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir, mock.patch.object(cli, "APP_DIR", pathlib.Path(tmpdir)), mock.patch.object(
            cli, "APPROVAL_PROMPTS_FILE", pathlib.Path(tmpdir) / "approval_prompts.json"
        ), mock.patch.object(
            cli, "_read_openclaw_last_delivery", return_value={"lastChannel": "telegram", "lastTo": "123", "lastThreadId": None}
        ), mock.patch.object(
            cli, "_require_openclaw_bin", return_value="openclaw"
        ):
            captured: dict[str, object] = {}

            def fake_run(cmd: list[str], timeout_sec: int, kind: str):
                captured["cmd"] = cmd
                return mock.Mock(returncode=0, stdout='{"payload":{"messageId":"777"}}', stderr="")

            with mock.patch.object(cli, "_run_subprocess", side_effect=fake_run):
                cli._maybe_send_telegram_policy_approval_prompt(
                    {
                        "policyApprovalId": "ppr_abc",
                        "chainKey": "base_sepolia",
                        "requestType": "token_preapprove_add",
                        "tokenDisplay": "USDC (0x" + "11" * 20 + ")",
                    }
                )

            cmd = captured.get("cmd") or []
            self.assertIn("--channel", cmd)
            self.assertIn("telegram", cmd)
            message_arg = None
            buttons_arg = None
            for idx, part in enumerate(cmd):
                if part == "--message" and idx + 1 < len(cmd):
                    message_arg = cmd[idx + 1]
                if part == "--buttons" and idx + 1 < len(cmd):
                    buttons_arg = cmd[idx + 1]
            self.assertIsNotNone(message_arg)
            self.assertIn("Approve policy change", message_arg)
            self.assertIn("Approval ID: ppr_abc", message_arg)
            self.assertIn("Status: approval_pending", message_arg)
            self.assertIsNotNone(buttons_arg)
            buttons = json.loads(buttons_arg or "[]")
            row0 = buttons[0]
            callback_data = [b.get("callback_data") for b in row0 if isinstance(b, dict)]
            self.assertIn("xpol|a|ppr_abc|base_sepolia", callback_data)
            self.assertIn("xpol|r|ppr_abc|base_sepolia", callback_data)
            entry = cli._get_policy_approval_prompt("ppr_abc")
            self.assertIsInstance(entry, dict)
            self.assertEqual((entry or {}).get("messageId"), "777")
            self.assertEqual((entry or {}).get("channel"), "telegram")

    def test_telegram_policy_prompt_skips_when_last_channel_not_telegram(self) -> None:
        with mock.patch.object(cli, "_read_openclaw_last_delivery", return_value={"lastChannel": "web", "lastTo": "123", "lastThreadId": None}), mock.patch.object(
            cli, "_run_subprocess"
        ) as run_mock:
            cli._maybe_send_telegram_policy_approval_prompt(
                {
                    "policyApprovalId": "ppr_abc",
                    "chainKey": "base_sepolia",
                    "requestType": "global_approval_enable",
                }
            )
        run_mock.assert_not_called()

    def test_telegram_prompt_skips_when_harness_suppression_enabled(self) -> None:
        with mock.patch.dict(os.environ, {"XCLAW_TEST_HARNESS_DISABLE_TELEGRAM": "1"}, clear=False), mock.patch.object(
            cli, "_run_subprocess"
        ) as run_mock:
            cli._maybe_send_telegram_approval_prompt(
                "trd_abc",
                "base_sepolia",
                {"amountInHuman": "5", "tokenInSymbol": "WETH", "tokenOutSymbol": "USDC"},
            )
        run_mock.assert_not_called()

    def test_telegram_transfer_prompt_skips_when_harness_suppression_enabled(self) -> None:
        with mock.patch.dict(os.environ, {"XCLAW_TEST_HARNESS_DISABLE_TELEGRAM": "1"}, clear=False), mock.patch.object(
            cli, "_run_subprocess"
        ) as run_mock:
            cli._maybe_send_telegram_transfer_approval_prompt(
                {
                    "approvalId": "xfr_abc",
                    "chainKey": "base_sepolia",
                    "transferType": "token",
                    "tokenSymbol": "WETH",
                    "tokenDecimals": 18,
                    "amountWei": "1000000000000000",
                    "toAddress": "0x9099d24d55c105818b4e9ee117d87bc11063cf10",
                }
            )
        run_mock.assert_not_called()

    def test_telegram_policy_prompt_skips_when_harness_suppression_enabled(self) -> None:
        with mock.patch.dict(os.environ, {"XCLAW_TEST_HARNESS_DISABLE_TELEGRAM": "1"}, clear=False), mock.patch.object(
            cli, "_run_subprocess"
        ) as run_mock:
            cli._maybe_send_telegram_policy_approval_prompt(
                {
                    "policyApprovalId": "ppr_abc",
                    "chainKey": "base_sepolia",
                    "requestType": "global_approval_enable",
                }
            )
        run_mock.assert_not_called()

    def test_extract_openclaw_message_id_accepts_nested_snake_case(self) -> None:
        stdout = json.dumps(
            {
                "ok": True,
                "payload": {
                    "result": {
                        "message": {
                            "message_id": 4242,
                        }
                    }
                },
            }
        )
        self.assertEqual(cli._extract_openclaw_message_id(stdout), "4242")

    def test_extract_openclaw_message_id_accepts_prefixed_log_output(self) -> None:
        stdout = (
            "[telegram] autoSelectFamily=true (default-node22)\n"
            + json.dumps({"action": "send", "payload": {"ok": True, "messageId": "1162", "chatId": "6321549254"}})
        )
        self.assertEqual(cli._extract_openclaw_message_id(stdout), "1162")

    def test_extract_openclaw_message_id_accepts_non_json_fallback_pattern(self) -> None:
        stdout = "openclaw send complete :: message_id=99887766 channel=telegram"
        self.assertEqual(cli._extract_openclaw_message_id(stdout), "99887766")

    def test_require_api_base_url_defaults_to_localhost_when_missing(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(cli._require_api_base_url(), "http://127.0.0.1:3000/api/v1")

    def test_clear_telegram_transfer_prompt_uses_saved_message_id_without_delete(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir, mock.patch.object(cli, "APP_DIR", pathlib.Path(tmpdir)), mock.patch.object(
            cli, "APPROVAL_PROMPTS_FILE", pathlib.Path(tmpdir) / "approval_prompts.json"
        ):
            cli._record_transfer_approval_prompt(
                "xfr_abc",
                {
                    "channel": "telegram",
                    "to": "123",
                    "threadId": None,
                    "messageId": "777",
                    "createdAt": "2026-02-18T00:00:00.000Z",
                },
            )
            fake_resp = mock.MagicMock()
            fake_ctx = mock.MagicMock()
            fake_ctx.__enter__.return_value = fake_resp
            fake_resp.read.return_value = b'{"ok":true}'

            with mock.patch.dict(os.environ, {"XCLAW_TELEGRAM_BOT_TOKEN": "token"}, clear=False), mock.patch(
                "urllib.request.urlopen", return_value=fake_ctx
            ), mock.patch.object(
                cli, "_run_subprocess"
            ) as run_subprocess:
                cli._maybe_delete_telegram_transfer_approval_prompt("xfr_abc")

            run_subprocess.assert_not_called()
            self.assertIsNone(cli._get_transfer_approval_prompt("xfr_abc"))

    def test_owner_link_direct_send_skips_telegram_channel(self) -> None:
        with mock.patch.object(
            cli, "_read_openclaw_last_delivery", return_value={"lastChannel": "telegram", "lastTo": "123", "lastThreadId": None}
        ), mock.patch.object(
            cli, "_run_subprocess"
        ) as run_mock:
            result = cli._maybe_send_owner_link_to_active_chat("https://xclaw.trade/agents/ag_1?token=ol1.test", "2026-02-18T16:39:52.313Z")
        self.assertFalse(bool(result.get("sent")))
        self.assertEqual(str(result.get("reason")), "telegram_channel_skipped")
        run_mock.assert_not_called()

    def test_telegram_decision_message_prefers_symbols_over_addresses(self) -> None:
        captured: dict[str, object] = {}

        def fake_run(cmd: list[str], timeout_sec: int, kind: str):
            captured["cmd"] = cmd
            return mock.Mock(returncode=0, stdout='{"ok":true}', stderr="")

        with mock.patch.object(
            cli, "_get_approval_prompt", return_value={"channel": "telegram", "to": "123", "threadId": None}
        ), mock.patch.object(
            cli, "_canonical_token_map", return_value={
                "WETH": "0xC97e903056f679ea1Db80893008A92578aDfE609",
                "USDC": "0x39A0C0D1b3dDcE1B49fAa5c6e1D300C14012F4E2",
            }
        ), mock.patch.object(
            cli.shutil, "which", return_value="openclaw"
        ), mock.patch.object(
            cli, "_run_subprocess", side_effect=fake_run
        ):
            cli._maybe_send_telegram_decision_message(
                trade_id="trd_1",
                chain="base_sepolia",
                decision="approved",
                summary=None,
                trade={
                    "amountIn": "0.11",
                    "tokenIn": "0xC97e903056f679ea1Db80893008A92578aDfE609",
                    "tokenOut": "0x39A0C0D1b3dDcE1B49fAa5c6e1D300C14012F4E2",
                },
            )

        cmd = captured.get("cmd") or []
        self.assertIn("--message", cmd)
        message = str(cmd[cmd.index("--message") + 1])
        self.assertIn("0.11 WETH -> USDC", message)
        self.assertIn("Approved — swap accepted ✅", message)
        self.assertIn("• Trade ID: `trd_1`", message)
        self.assertIn("• Chain: `base_sepolia`", message)
        self.assertNotIn("0xC97e903056f679ea1Db80893008A92578aDfE609", message)
        self.assertNotIn("0x39A0C0D1b3dDcE1B49fAa5c6e1D300C14012F4E2", message)

    def test_telegram_decision_message_skips_when_harness_suppression_enabled(self) -> None:
        with mock.patch.dict(os.environ, {"XCLAW_TEST_HARNESS_DISABLE_TELEGRAM": "1"}, clear=False), mock.patch.object(
            cli, "_run_subprocess"
        ) as run_mock:
            cli._maybe_send_telegram_decision_message(
                trade_id="trd_1",
                chain="base_sepolia",
                decision="approved",
                summary={"amountInHuman": "1", "tokenInSymbol": "WETH", "tokenOutSymbol": "USDC"},
                trade={"amountIn": "1", "tokenIn": "WETH", "tokenOut": "USDC"},
            )
        run_mock.assert_not_called()

    def test_trade_spot_does_not_reuse_after_approval(self) -> None:
        # De-dupe only applies while approval is pending; once approved, a repeated identical request
        # should propose a new tradeId.
        args = argparse.Namespace(
            chain="base_sepolia",
            token_in="WETH",
            token_out="USDC",
            amount_in="1",
            slippage_bps="100",
            deadline_sec="120",
            to=None,
            json=True,
        )
        with mock.patch.object(cli, "_resolve_token_address", side_effect=["0x1111111111111111111111111111111111111111", "0x2222222222222222222222222222222222222222"]), mock.patch.object(
            cli, "_fetch_erc20_metadata", side_effect=[{"decimals": 18, "symbol": "WETH"}, {"decimals": 6, "symbol": "USDC"}]
        ), mock.patch.object(
            cli, "load_wallet_store", return_value={"wallets": {"base_sepolia": {"address": "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "privateKey": "0x" + "11" * 32}}}
        ), mock.patch.object(
            cli, "_execution_wallet", return_value=("0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "0x" + "11" * 32)
        ), mock.patch.object(
            cli, "_require_cast_bin", return_value="cast"
        ), mock.patch.object(
            cli, "_chain_rpc_url", return_value="http://127.0.0.1:8545"
        ), mock.patch.object(
            cli, "_require_chain_contract_address", return_value="0x4444444444444444444444444444444444444444"
        ), mock.patch.object(
            cli, "_enforce_spend_preconditions", return_value=({}, "2026-02-15", 0, 0)
        ), mock.patch.object(
            cli, "_router_get_amount_out", return_value=10000
        ), mock.patch.object(
            cli, "_enforce_trade_caps", return_value=({}, "2026-02-15", Decimal("0"), 0, {"maxDailyUsd": "250", "maxDailyTradeCount": 50})
        ), mock.patch.object(
            cli, "_get_pending_trade_intent", return_value={"tradeId": "trd_old"}
        ), mock.patch.object(
            cli, "_read_trade_details", return_value={"tradeId": "trd_old", "chainKey": "base_sepolia", "status": "approved"}
        ), mock.patch.object(
            cli, "_post_trade_proposed", return_value={"ok": True, "tradeId": "trd_new", "status": "approval_pending"}
        ) as propose_mock, mock.patch.object(
            cli, "_wait_for_trade_approval",
            side_effect=cli.WalletPolicyError(
                "approval_required",
                "Trade is waiting for management approval.",
                "Approve the pending trade (Telegram or web), then re-run the same trade command to resume without creating a new approval.",
                {"tradeId": "trd_new", "chain": "base_sepolia"},
            ),
        ):
            out = self._run_and_parse_stdout(lambda: cli.cmd_trade_spot(args))

        self.assertFalse(out.get("ok"))
        self.assertEqual(out.get("code"), "approval_required")
        self.assertEqual(propose_mock.call_count, 1, "should propose a new tradeId after the old one was approved")

    def test_trade_caps_blocked_when_owner_chain_disabled(self) -> None:
        policy_payload = {
            "ok": True,
            "agentId": "ag_1",
            "chainKey": "base_sepolia",
            "chainEnabled": False,
            "outboundTransfersEnabled": True,
            "outboundMode": "allow_all",
            "outboundWhitelistAddresses": [],
            "updatedAt": "2026-02-15T00:00:00Z",
            "tradeCaps": {
                "approvalMode": "auto",
                "maxTradeUsd": "1000",
                "maxDailyUsd": "1000",
                "allowedTokens": [],
                "dailyCapUsdEnabled": True,
                "dailyTradeCapEnabled": True,
                "maxDailyTradeCount": 10,
                "updatedAt": "2026-02-15T00:00:00Z",
            },
            "dailyUsage": {"utcDay": "2026-02-15", "dailySpendUsd": "0", "dailyFilledTrades": 0},
        }
        with mock.patch.object(cli, "_api_request", return_value=(200, policy_payload)):
            with self.assertRaises(cli.WalletPolicyError) as ctx:
                cli._enforce_trade_caps("base_sepolia", Decimal("10"), 1)
        self.assertEqual(ctx.exception.code, "chain_disabled")

    def test_wallet_send_policy_blocked_when_owner_chain_disabled(self) -> None:
        policy_payload = {
            "ok": True,
            "agentId": "ag_1",
            "chainKey": "base_sepolia",
            "chainEnabled": False,
            "outboundTransfersEnabled": True,
            "outboundMode": "allow_all",
            "outboundWhitelistAddresses": [],
            "updatedAt": "2026-02-15T00:00:00Z",
            "tradeCaps": None,
            "dailyUsage": {"utcDay": "2026-02-15", "dailySpendUsd": "0", "dailyFilledTrades": 0},
        }
        with mock.patch.object(cli, "_api_request", return_value=(200, policy_payload)):
            with self.assertRaises(cli.WalletPolicyError) as ctx:
                cli._enforce_outbound_transfer_policy("base_sepolia", "0x" + "11" * 20)
        self.assertEqual(ctx.exception.code, "chain_disabled")

    def test_wallet_balance_includes_canonical_token_balances(self) -> None:
        args = argparse.Namespace(chain="base_sepolia", json=True)
        wallet_entry = {"address": "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}
        holdings = {
            "address": "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "native": {
                "symbol": "ETH",
                "balanceWei": "123000000000000000",
                "balance": "0.123",
                "balancePretty": "0.123",
                "decimals": 18,
            },
            "tokens": [
                {
                    "symbol": "USDC",
                    "token": "0x39A0C0D1b3dDcE1B49fAa5c6e1D300C14012F4E2",
                    "balanceWei": "186727950026975000137164",
                    "balance": "186727.950026975000137164",
                    "balancePretty": "186,727.95",
                    "decimals": 18,
                },
                {
                    "symbol": "WETH",
                    "token": "0xC97e903056f679ea1Db80893008A92578aDfE609",
                    "balanceWei": "86898428135396339692",
                    "balance": "86.898428135396339692",
                    "balancePretty": "86.8984",
                    "decimals": 18,
                },
            ],
            "tokenErrors": [],
        }
        with mock.patch.object(cli, "load_wallet_store", return_value={}), mock.patch.object(
            cli, "_chain_wallet", return_value=("base_sepolia", wallet_entry)
        ), mock.patch.object(
            cli, "_validate_wallet_entry_shape", return_value=None
        ), mock.patch.object(
            cli, "_fetch_wallet_holdings", return_value=holdings
        ):
            payload = self._run_and_parse_stdout(lambda: cli.cmd_wallet_balance(args))
        self.assertTrue(payload.get("ok"))
        self.assertEqual(payload.get("symbol"), "ETH")
        self.assertEqual(payload.get("balanceWei"), "123000000000000000")
        self.assertEqual(len(payload.get("tokens", [])), 2)
        self.assertEqual(payload.get("tokens", [])[0].get("symbol"), "USDC")

    def test_wallet_send_token_requires_transfer_approval(self) -> None:
        args = argparse.Namespace(
            token="0x" + "11" * 20,
            to="0x" + "22" * 20,
            amount_wei="100",
            chain="base_sepolia",
            json=True,
        )
        with mock.patch.object(
            cli,
            "_evaluate_outbound_transfer_policy",
            return_value={
                "allowed": True,
                "policyBlockedAtCreate": False,
                "policyBlockReasonCode": None,
                "policyBlockReasonMessage": None,
            },
        ), mock.patch.object(
            cli, "_enforce_spend_preconditions", return_value=({}, "2026-02-16", 0, 10**30)
        ), mock.patch.object(
            cli, "_sync_transfer_policy_from_remote", return_value={"transferApprovalMode": "per_transfer", "nativeTransferPreapproved": False, "allowedTransferTokens": []}
        ), mock.patch.object(
            cli, "_fetch_erc20_metadata", return_value={"symbol": "USDC", "decimals": 18}
        ), mock.patch.object(
            cli, "_resolve_token_address", return_value="0x" + "11" * 20
        ), mock.patch.object(
            cli, "_mirror_transfer_approval"
        ):
            payload = self._run_and_parse_stdout(lambda: cli.cmd_wallet_send_token(args))
        self.assertEqual(payload.get("ok"), False)
        self.assertEqual(payload.get("code"), "approval_required")
        details = payload.get("details") or {}
        approval_id = str(details.get("approvalId") or "")
        self.assertTrue(approval_id.startswith("xfr_"))
        queued = str(details.get("queuedMessage") or "")
        self.assertIn("Approval ID:", queued)
        self.assertIn("Status: approval_pending", queued)
        self.assertIn("Amount: 0.0000000000000001 USDC (100 wei)", queued)

    def test_wallet_send_token_accepts_symbol_and_resolves_address(self) -> None:
        args = argparse.Namespace(
            token="usdc",
            to="0x" + "22" * 20,
            amount_wei="1000000000000",
            chain="base_sepolia",
            json=True,
        )
        with mock.patch.object(
            cli,
            "_evaluate_outbound_transfer_policy",
            return_value={
                "allowed": True,
                "policyBlockedAtCreate": False,
                "policyBlockReasonCode": None,
                "policyBlockReasonMessage": None,
            },
        ), mock.patch.object(
            cli, "_enforce_spend_preconditions", return_value=({}, "2026-02-16", 0, 10**30)
        ), mock.patch.object(
            cli, "_sync_transfer_policy_from_remote", return_value={"transferApprovalMode": "per_transfer", "nativeTransferPreapproved": False, "allowedTransferTokens": []}
        ), mock.patch.object(
            cli, "_fetch_erc20_metadata", return_value={"symbol": "USDC", "decimals": 18}
        ), mock.patch.object(
            cli, "_resolve_token_address", return_value="0x" + "11" * 20
        ) as resolve_mock, mock.patch.object(
            cli, "_mirror_transfer_approval"
        ):
            payload = self._run_and_parse_stdout(lambda: cli.cmd_wallet_send_token(args))
        self.assertEqual(payload.get("code"), "approval_required")
        resolve_mock.assert_called_once_with("base_sepolia", "usdc")
        details = payload.get("details") or {}
        self.assertIn("(0x1111111111111111111111111111111111111111)", str(details.get("queuedMessage") or ""))

    def test_wallet_send_token_rejects_suspicious_tiny_symbol_amount(self) -> None:
        args = argparse.Namespace(
            token="USDC",
            to="0x" + "22" * 20,
            amount_wei="10",
            chain="base_sepolia",
            json=True,
        )
        with mock.patch.object(
            cli, "_resolve_token_address", return_value="0x" + "11" * 20
        ) as resolve_mock, mock.patch.object(
            cli, "_fetch_erc20_metadata", return_value={"symbol": "USDC", "decimals": 18}
        ), mock.patch.object(
            cli, "_enforce_spend_preconditions"
        ) as spend_mock, mock.patch.object(
            cli, "_evaluate_outbound_transfer_policy"
        ) as policy_mock:
            payload = self._run_and_parse_stdout(lambda: cli.cmd_wallet_send_token(args))
        self.assertEqual(payload.get("ok"), False)
        self.assertEqual(payload.get("code"), "invalid_input")
        resolve_mock.assert_called_once_with("base_sepolia", "USDC")
        spend_mock.assert_not_called()
        policy_mock.assert_not_called()
        details = payload.get("details") or {}
        self.assertEqual(details.get("amountWei"), "10")
        self.assertEqual(details.get("tokenSymbol"), "USDC")
        self.assertEqual(details.get("tokenDecimals"), 18)

    def test_wallet_send_token_policy_blocked_routes_to_transfer_approval(self) -> None:
        args = argparse.Namespace(
            token="0x" + "11" * 20,
            to="0x" + "22" * 20,
            amount_wei="100",
            chain="base_sepolia",
            json=True,
        )
        with mock.patch.object(
            cli,
            "_evaluate_outbound_transfer_policy",
            return_value={
                "allowed": False,
                "policyBlockedAtCreate": True,
                "policyBlockReasonCode": "outbound_disabled",
                "policyBlockReasonMessage": "Outbound transfers are disabled by owner policy.",
            },
        ), mock.patch.object(
            cli, "_enforce_spend_preconditions", return_value=({}, "2026-02-16", 0, 10**30)
        ), mock.patch.object(
            cli, "_sync_transfer_policy_from_remote", return_value={"transferApprovalMode": "auto", "nativeTransferPreapproved": True, "allowedTransferTokens": []}
        ), mock.patch.object(
            cli, "_fetch_erc20_metadata", return_value={"symbol": "USDC", "decimals": 18}
        ), mock.patch.object(
            cli, "_mirror_transfer_approval"
        ):
            payload = self._run_and_parse_stdout(lambda: cli.cmd_wallet_send_token(args))
        self.assertEqual(payload.get("ok"), False)
        self.assertEqual(payload.get("code"), "approval_required")
        details = payload.get("details") or {}
        self.assertEqual(details.get("policyBlockedAtCreate"), True)
        self.assertEqual(details.get("policyBlockReasonCode"), "outbound_disabled")
        self.assertIn("one-off override", str(details.get("queuedMessage") or "").lower())

    def test_wallet_send_token_fails_when_approval_sync_missing(self) -> None:
        args = argparse.Namespace(
            token="0x" + "11" * 20,
            to="0x" + "22" * 20,
            amount_wei="100",
            chain="base_sepolia",
            json=True,
        )
        with mock.patch.object(
            cli,
            "_evaluate_outbound_transfer_policy",
            return_value={
                "allowed": False,
                "policyBlockedAtCreate": True,
                "policyBlockReasonCode": "outbound_disabled",
                "policyBlockReasonMessage": "Outbound transfers are disabled by owner policy.",
            },
        ), mock.patch.object(
            cli, "_enforce_spend_preconditions", return_value=({}, "2026-02-16", 0, 10**30)
        ), mock.patch.object(
            cli, "_sync_transfer_policy_from_remote", return_value={"transferApprovalMode": "auto", "nativeTransferPreapproved": True, "allowedTransferTokens": []}
        ), mock.patch.object(
            cli, "_fetch_erc20_metadata", return_value={"symbol": "USDC", "decimals": 18}
        ), mock.patch.object(
            cli, "_resolve_token_address", return_value="0x" + "11" * 20
        ), mock.patch.object(
            cli, "_mirror_transfer_approval", side_effect=cli.WalletStoreError("mirror failed")
        ):
            payload = self._run_and_parse_stdout(lambda: cli.cmd_wallet_send_token(args))
        self.assertFalse(payload.get("ok"))
        self.assertEqual(payload.get("code"), "approval_sync_failed")
        details = payload.get("details") or {}
        self.assertTrue(str(details.get("approvalId") or "").startswith("xfr_"))

    def test_wallet_send_token_redacts_private_key_in_error_payload(self) -> None:
        args = argparse.Namespace(
            token="0x" + "11" * 20,
            to="0x" + "22" * 20,
            amount_wei="100",
            chain="base_sepolia",
            json=True,
        )
        leaked_key = "97d95b56039c758bbee53449741de26fc2dc76ae2a82506bbb90e5a9e7a14972"
        with mock.patch.object(
            cli,
            "_evaluate_outbound_transfer_policy",
            return_value={
                "allowed": True,
                "policyBlockedAtCreate": False,
                "policyBlockReasonCode": None,
                "policyBlockReasonMessage": None,
            },
        ), mock.patch.object(
            cli, "_enforce_spend_preconditions", return_value=({}, "2026-02-16", 0, 10**30)
        ), mock.patch.object(
            cli, "_sync_transfer_policy_from_remote", return_value={"transferApprovalMode": "auto", "nativeTransferPreapproved": True, "allowedTransferTokens": []}
        ), mock.patch.object(
            cli, "_fetch_erc20_metadata", return_value={"symbol": "USDC", "decimals": 18}
        ), mock.patch.object(
            cli, "_mirror_transfer_approval"
        ), mock.patch.object(
            cli,
            "_execute_pending_transfer_flow",
            side_effect=cli.WalletStoreError(
                f"Timed out after 30s running: cast send --private-key {leaked_key} --rpc-url https://sepolia.base.org"
            ),
        ):
            payload = self._run_and_parse_stdout(lambda: cli.cmd_wallet_send_token(args))
        self.assertEqual(payload.get("ok"), False)
        self.assertEqual(payload.get("code"), "send_failed")
        serialized = json.dumps(payload)
        self.assertNotIn(leaked_key, serialized)
        self.assertIn("<REDACTED>", serialized)

    def test_wallet_send_success_exposes_builder_metadata_fields(self) -> None:
        args = argparse.Namespace(
            to="0x" + "22" * 20,
            amount_wei="100",
            chain="base_sepolia",
            json=True,
        )
        with mock.patch.object(cli, "_enforce_spend_preconditions"), mock.patch.object(
            cli,
            "_evaluate_outbound_transfer_policy",
            return_value={"allowed": True, "policyBlockedAtCreate": False, "policyBlockReasonCode": None, "policyBlockReasonMessage": None},
        ), mock.patch.object(
            cli,
            "_transfer_requires_approval",
            return_value=(False, {"transferApprovalMode": "auto", "nativeTransferPreapproved": True, "allowedTransferTokens": []}),
        ), mock.patch.object(
            cli, "_mirror_transfer_approval"
        ), mock.patch.object(
            cli,
            "_execute_pending_transfer_flow",
            return_value={
                "ok": True,
                "code": "ok",
                "message": "Transfer executed.",
                "txHash": "0x" + "ab" * 32,
                "builderCodeChainEligible": True,
                "builderCodeApplied": False,
                "builderCodeSkippedReason": "empty_calldata_safe_mode",
                "builderCodeSource": None,
                "builderCodeStandard": "erc8021",
            },
        ):
            payload = self._run_and_parse_stdout(lambda: cli.cmd_wallet_send(args))
        self.assertTrue(payload.get("ok"))
        self.assertIn("builderCodeChainEligible", payload)
        self.assertIn("builderCodeApplied", payload)
        self.assertIn("builderCodeSkippedReason", payload)
        self.assertIn("builderCodeSource", payload)
        self.assertIn("builderCodeStandard", payload)

    def test_approvals_decide_transfer_approve_executes(self) -> None:
        approval_id = "xfr_test_1"
        cli._record_pending_transfer_flow(
            approval_id,
            {
                "approvalId": approval_id,
                "chainKey": "base_sepolia",
                "status": "approval_pending",
                "transferType": "native",
                "toAddress": "0x" + "22" * 20,
                "amountWei": "1",
                "createdAt": cli.utc_now(),
            },
        )
        args = argparse.Namespace(approval_id=approval_id, decision="approve", reason_message=None, chain="base_sepolia", json=True)
        with mock.patch.object(
            cli,
            "_execute_pending_transfer_flow",
            return_value={
                "ok": True,
                "code": "ok",
                "approvalId": approval_id,
                "status": "filled",
                "txHash": "0x" + "ab" * 32,
                "executionMode": "policy_override",
            },
        ), mock.patch.object(cli, "_mirror_transfer_approval"):
            payload = self._run_and_parse_stdout(lambda: cli.cmd_approvals_decide_transfer(args))
        self.assertEqual(payload.get("ok"), True)
        self.assertEqual(payload.get("status"), "filled")
        self.assertEqual(payload.get("executionMode"), "policy_override")

    def test_approvals_decide_transfer_deny_sets_rejected(self) -> None:
        approval_id = "xfr_test_2"
        cli._record_pending_transfer_flow(
            approval_id,
            {
                "approvalId": approval_id,
                "chainKey": "base_sepolia",
                "status": "approval_pending",
                "transferType": "token",
                "tokenAddress": "0x" + "11" * 20,
                "tokenSymbol": "USDC",
                "toAddress": "0x" + "22" * 20,
                "amountWei": "1",
                "createdAt": cli.utc_now(),
            },
        )
        args = argparse.Namespace(
            approval_id=approval_id,
            decision="deny",
            reason_message="No",
            chain="base_sepolia",
            json=True,
        )
        with mock.patch.object(cli, "_mirror_transfer_approval"):
            payload = self._run_and_parse_stdout(lambda: cli.cmd_approvals_decide_transfer(args))
        self.assertEqual(payload.get("ok"), True)
        self.assertEqual(payload.get("status"), "rejected")
        self.assertEqual(payload.get("amountDisplay"), "0.000000000000000001 USDC")
        saved = cli._get_pending_transfer_flow(approval_id)
        self.assertIsNotNone(saved)
        self.assertEqual(str((saved or {}).get("status")), "rejected")

    def test_approvals_decide_transfer_executing_is_idempotent(self) -> None:
        approval_id = "xfr_test_executing"
        cli._record_pending_transfer_flow(
            approval_id,
            {
                "approvalId": approval_id,
                "chainKey": "base_sepolia",
                "status": "executing",
                "transferType": "token",
                "tokenAddress": "0x" + "11" * 20,
                "tokenSymbol": "WETH",
                "tokenDecimals": 18,
                "toAddress": "0x" + "22" * 20,
                "amountWei": "1000000000000000",
                "createdAt": cli.utc_now(),
                "updatedAt": cli.utc_now(),
            },
        )
        args = argparse.Namespace(approval_id=approval_id, decision="approve", reason_message=None, chain="base_sepolia", json=True)
        payload = self._run_and_parse_stdout(lambda: cli.cmd_approvals_decide_transfer(args))
        self.assertTrue(payload.get("ok"))
        self.assertEqual(payload.get("status"), "executing")
        self.assertEqual(payload.get("inProgress"), True)
        self.assertEqual(payload.get("converged"), True)

    def test_approvals_decide_transfer_falls_back_to_x402_flow(self) -> None:
        approval_id = "xfr_x402_1"
        args = argparse.Namespace(approval_id=approval_id, decision="approve", reason_message=None, chain="base_sepolia", json=True)
        with mock.patch.object(cli, "_get_pending_transfer_flow", return_value=None), mock.patch.object(
            cli.x402_state, "get_pending_pay_flow", return_value={"approvalId": approval_id, "status": "approval_pending"}
        ), mock.patch.object(
            cli,
            "x402_pay_decide",
            return_value={"approvalId": approval_id, "status": "filled", "network": "base_sepolia", "facilitator": "cdp"},
        ), mock.patch.object(cli, "_mirror_x402_outbound"):
            payload = self._run_and_parse_stdout(lambda: cli.cmd_approvals_decide_transfer(args))
        self.assertTrue(payload.get("ok"))
        approval = payload.get("approval") or {}
        self.assertEqual(approval.get("approvalId"), approval_id)
        self.assertEqual(approval.get("status"), "filled")

    def test_approvals_resume_transfer_recovers_stale_executing_without_txhash(self) -> None:
        approval_id = "xfr_resume_stale"
        cli._record_pending_transfer_flow(
            approval_id,
            {
                "approvalId": approval_id,
                "chainKey": "base_sepolia",
                "status": "executing",
                "transferType": "token",
                "tokenAddress": "0x" + "11" * 20,
                "tokenSymbol": "WETH",
                "tokenDecimals": 18,
                "toAddress": "0x" + "22" * 20,
                "amountWei": "1000000000000000",
                "createdAt": "2026-02-18T00:00:00+00:00",
                "updatedAt": "2026-02-18T00:00:00+00:00",
            },
        )
        args = argparse.Namespace(approval_id=approval_id, chain="base_sepolia", json=True)
        with mock.patch.object(cli, "_is_stale_executing_transfer_flow", return_value=True), mock.patch.object(
            cli,
            "_execute_pending_transfer_flow",
            return_value={"ok": True, "code": "ok", "status": "filled", "approvalId": approval_id, "txHash": "0x" + "ab" * 32},
        ), mock.patch.object(cli, "_mirror_transfer_approval"):
            payload = self._run_and_parse_stdout(lambda: cli.cmd_approvals_resume_transfer(args))
        self.assertTrue(payload.get("ok"))
        self.assertEqual(payload.get("status"), "filled")

    def test_approvals_resume_transfer_skips_recent_executing_without_txhash(self) -> None:
        approval_id = "xfr_resume_recent"
        now = cli.utc_now()
        cli._record_pending_transfer_flow(
            approval_id,
            {
                "approvalId": approval_id,
                "chainKey": "base_sepolia",
                "status": "executing",
                "transferType": "token",
                "tokenAddress": "0x" + "11" * 20,
                "tokenSymbol": "WETH",
                "tokenDecimals": 18,
                "toAddress": "0x" + "22" * 20,
                "amountWei": "1000000000000000",
                "createdAt": now,
                "updatedAt": now,
            },
        )
        args = argparse.Namespace(approval_id=approval_id, chain="base_sepolia", json=True)
        with mock.patch.object(cli, "_transfer_executing_stale_sec", return_value=9999):
            payload = self._run_and_parse_stdout(lambda: cli.cmd_approvals_resume_transfer(args))
        self.assertTrue(payload.get("ok"))
        self.assertEqual(payload.get("status"), "executing")
        self.assertEqual(payload.get("inProgress"), True)

    def test_execute_pending_transfer_flow_blocks_without_override_when_policy_now_blocked(self) -> None:
        flow = {
            "approvalId": "xfr_test_3",
            "chainKey": "base_sepolia",
            "status": "approved",
            "transferType": "native",
            "toAddress": "0x" + "22" * 20,
            "amountWei": "1",
            "policyBlockedAtCreate": False,
            "createdAt": cli.utc_now(),
        }
        with mock.patch.object(
            cli,
            "_evaluate_outbound_transfer_policy",
            return_value={"allowed": False, "policyBlockReasonCode": "destination_not_whitelisted", "policyBlockReasonMessage": "blocked"},
        ):
            out = cli._execute_pending_transfer_flow(flow)
        self.assertEqual(out.get("ok"), False)
        self.assertEqual(out.get("code"), "not_actionable")

    def test_transfer_balance_precondition_blocks_insufficient_token_balance(self) -> None:
        with mock.patch.object(cli, "_fetch_token_balance_wei", return_value="500"):
            with self.assertRaises(cli.WalletStoreError) as ctx:
                cli._assert_transfer_balance_preconditions(
                    chain="base_sepolia",
                    transfer_type="token",
                    wallet_address="0x" + "11" * 20,
                    amount_wei="1000",
                    token_address="0x" + "22" * 20,
                    token_symbol="WETH",
                    token_decimals=18,
                )
        self.assertIn("Insufficient WETH balance", str(ctx.exception))

    def test_transfer_balance_precondition_allows_sufficient_token_balance(self) -> None:
        with mock.patch.object(cli, "_fetch_token_balance_wei", return_value="1000"):
            cli._assert_transfer_balance_preconditions(
                chain="base_sepolia",
                transfer_type="token",
                wallet_address="0x" + "11" * 20,
                amount_wei="1000",
                token_address="0x" + "22" * 20,
                token_symbol="WETH",
                token_decimals=18,
            )

    def test_trade_spot_builds_quote_and_swap_calls(self) -> None:
        args = argparse.Namespace(
            chain="base_sepolia",
            token_in="0x" + "11" * 20,
            token_out="0x" + "22" * 20,
            amount_in="500",
            slippage_bps="50",
            to=None,
            deadline_sec=120,
            json=True,
        )

        commands: list[list[str]] = []

        def fake_run(cmd: list[str], text: bool = True, capture_output: bool = True, **kwargs):  # type: ignore[override]
            commands.append(cmd)
            # Quote call
            if cmd[:3] == ["cast", "call", "--rpc-url"] and "getAmountsOut(uint256,address[])(uint256[])" in cmd:
                # last uint is treated as amountOut by parser.
                return mock.Mock(returncode=0, stdout="(uint256[]) [500000000000000000000,20000000000000000000]\n", stderr="")
            # Approve receipt
            if len(cmd) >= 2 and cmd[1] == "receipt":
                return mock.Mock(returncode=0, stdout='{"status":"0x1"}', stderr="")
            raise AssertionError(f"Unexpected command {cmd}")

        def fake_send(rpc_url: str, tx_obj: dict, private_key_hex: str, **kwargs) -> str:
            # First send = approve, second send = swap
            return "0x" + ("ab" * 32)

        with mock.patch.object(cli, "_execution_wallet", return_value=("0x" + "aa" * 20, "0x" + "33" * 32)), mock.patch.object(
            cli, "_require_cast_bin", return_value="cast"
        ), mock.patch.object(cli, "_chain_rpc_url", return_value="https://rpc.example"), mock.patch.object(
            cli, "_require_chain_contract_address", return_value="0x" + "44" * 20
        ), mock.patch.object(cli, "_fetch_erc20_metadata", side_effect=[{"decimals": 18, "symbol": "USDC"}, {"decimals": 18, "symbol": "WETH"}]), mock.patch.object(
            cli, "_fetch_token_allowance_wei", return_value=str(10**30)
        ), mock.patch.object(
            cli, "_enforce_spend_preconditions", return_value=({}, "2026-02-14", 0, 10**30)
        ), mock.patch.object(
            cli, "_replay_trade_usage_outbox", return_value=(0, 0)
        ), mock.patch.object(
            cli, "_enforce_trade_caps", return_value=({}, "2026-02-14", cli.Decimal("0"), 0, {"maxDailyUsd": "1000", "maxDailyTradeCount": 10})
        ), mock.patch.object(
            cli, "_post_trade_proposed", return_value={"ok": True, "tradeId": "trd_1", "status": "approved"}
        ), mock.patch.object(
            cli, "_wait_for_trade_approval", side_effect=AssertionError("trade-spot should not wait when proposal is already approved")
        ), mock.patch.object(
            cli, "_post_trade_status"
        ), mock.patch.object(
            cli, "_record_trade_cap_ledger"
        ), mock.patch.object(
            cli, "_post_trade_usage"
        ), mock.patch.object(
            cli, "_record_spend"
        ), mock.patch.object(
            cli, "_cast_calldata", return_value="0xdeadbeef"
        ), mock.patch.object(
            cli, "_cast_rpc_send_transaction", side_effect=fake_send
        ), mock.patch.object(
            cli.subprocess, "run", side_effect=fake_run
        ):
            code = cli.cmd_trade_spot(args)

        self.assertEqual(code, 0)
        # Ensure we quoted via getAmountsOut at least once.
        self.assertTrue(any("getAmountsOut(uint256,address[])(uint256[])" in " ".join(cmd) for cmd in commands))

    def test_trade_spot_rejects_bad_slippage(self) -> None:
        args = argparse.Namespace(
            chain="base_sepolia",
            token_in="0x" + "11" * 20,
            token_out="0x" + "22" * 20,
            amount_in="500",
            slippage_bps="9001",
            to=None,
            deadline_sec=120,
            json=True,
        )
        code = cli.cmd_trade_spot(args)
        self.assertEqual(code, 2)

    def test_trade_spot_proposes_with_token_addresses_for_policy_matching(self) -> None:
        args = argparse.Namespace(
            chain="base_sepolia",
            token_in="USDC",
            token_out="WETH",
            amount_in="10",
            slippage_bps="50",
            to=None,
            deadline_sec=120,
            json=True,
        )

        with mock.patch.object(cli, "_resolve_token_address", side_effect=["0x" + "11" * 20, "0x" + "22" * 20]), mock.patch.object(
            cli, "_execution_wallet", return_value=("0x" + "aa" * 20, "0x" + "33" * 32)
        ), mock.patch.object(
            cli, "_require_cast_bin", return_value="cast"
        ), mock.patch.object(cli, "_chain_rpc_url", return_value="https://rpc.example"), mock.patch.object(
            cli, "_require_chain_contract_address", return_value="0x" + "44" * 20
        ), mock.patch.object(cli, "_fetch_erc20_metadata", side_effect=[{"decimals": 18, "symbol": "USDC"}, {"decimals": 18, "symbol": "WETH"}]), mock.patch.object(
            cli, "_fetch_token_allowance_wei", return_value=str(10**30)
        ), mock.patch.object(
            cli, "_enforce_spend_preconditions", return_value=({}, "2026-02-14", 0, 10**30)
        ), mock.patch.object(
            cli, "_replay_trade_usage_outbox", return_value=(0, 0)
        ), mock.patch.object(
            cli, "_enforce_trade_caps", return_value=({}, "2026-02-14", cli.Decimal("0"), 0, {"maxDailyUsd": "1000", "maxDailyTradeCount": 10})
        ), mock.patch.object(
            cli, "_router_get_amount_out", return_value=10**18
        ), mock.patch.object(
            cli, "_post_trade_proposed", return_value={"ok": True, "tradeId": "trd_1", "status": "approved"}
        ) as propose_mock, mock.patch.object(
            cli, "_wait_for_trade_approval", side_effect=AssertionError("trade-spot should not wait when proposal is already approved")
        ), mock.patch.object(
            cli, "_post_trade_status"
        ), mock.patch.object(
            cli, "_record_trade_cap_ledger"
        ), mock.patch.object(
            cli, "_post_trade_usage"
        ), mock.patch.object(
            cli, "_record_spend"
        ), mock.patch.object(
            cli, "_cast_calldata", return_value="0xdeadbeef"
        ), mock.patch.object(
            cli, "_cast_rpc_send_transaction", return_value="0x" + "ab" * 32
        ), mock.patch.object(
            cli.subprocess, "run", return_value=mock.Mock(returncode=0, stdout='{"status":"0x1"}', stderr="")
        ):
            code = cli.cmd_trade_spot(args)

        self.assertEqual(code, 0)
        called = propose_mock.call_args
        self.assertIsNotNone(called)
        self.assertEqual(called.args[1], "0x" + "11" * 20)
        self.assertEqual(called.args[2], "0x" + "22" * 20)

    def test_faucet_request_daily_limited(self) -> None:
        args = argparse.Namespace(chain="base_sepolia", asset=[], json=True)
        with mock.patch.object(cli, "_resolve_api_key", return_value="xak1.ag_1.sig.payload"), mock.patch.object(
            cli, "_resolve_agent_id", return_value="ag_1"
        ), mock.patch.object(
            cli,
            "_api_request",
            return_value=(
                429,
                {
                    "code": "rate_limited",
                    "message": "Faucet request limit reached for today.",
                    "actionHint": "Retry after next UTC day begins.",
                    "details": {"retryAfterSeconds": 123},
                },
            ),
        ):
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = cli.cmd_faucet_request(args)
        self.assertEqual(code, 1)
        out = json.loads(buf.getvalue().strip())
        self.assertFalse(out.get("ok"))
        self.assertEqual(out.get("code"), "rate_limited")
        self.assertEqual(out.get("retryAfterSec"), 123)
        details = out.get("details") or {}
        self.assertEqual((details.get("apiDetails") or {}).get("retryAfterSeconds"), 123)

    def test_limit_orders_create_omits_expires_at_when_missing(self) -> None:
        args = argparse.Namespace(
            chain="base_sepolia",
            mode="real",
            side="buy",
            token_in="USDC",
            token_out="WETH",
            amount_in="10",
            limit_price="2500",
            slippage_bps="300",
            expires_at=None,
            json=True,
        )

        captured: dict = {}

        def fake_api_request(method: str, path: str, payload: dict | None = None, include_idempotency: bool = False):
            captured["method"] = method
            captured["path"] = path
            captured["payload"] = payload
            return 200, {"orderId": "lmt_1", "status": "open"}

        with mock.patch.object(cli, "_resolve_token_address", side_effect=["0x" + "11" * 20, "0x" + "22" * 20]), mock.patch.object(
            cli, "_resolve_api_key", return_value="xak1.ag_1.sig.payload"
        ), mock.patch.object(cli, "_resolve_agent_id", return_value="ag_1"), mock.patch.object(cli, "_api_request", side_effect=fake_api_request):
            payload = self._run_and_parse_stdout(lambda: cli.cmd_limit_orders_create(args))

        self.assertTrue(payload.get("ok"))
        sent = captured.get("payload") or {}
        self.assertNotIn("expiresAt", sent)

    def test_limit_orders_create_surfaces_api_details(self) -> None:
        args = argparse.Namespace(
            chain="base_sepolia",
            mode="real",
            side="buy",
            token_in="USDC",
            token_out="WETH",
            amount_in="10",
            limit_price="2500",
            slippage_bps="300",
            expires_at="not-a-date",
            json=True,
        )

        api_body = {
            "code": "payload_invalid",
            "message": "Limit-order create payload does not match schema.",
            "actionHint": "Provide valid fields.",
            "requestId": "req_123",
            "details": {"issues": [{"path": "/expiresAt", "message": "must be date-time"}]},
        }

        def fake_api_request(method: str, path: str, payload: dict | None = None, include_idempotency: bool = False):
            return 400, api_body

        with mock.patch.object(cli, "_resolve_token_address", side_effect=["0x" + "11" * 20, "0x" + "22" * 20]), mock.patch.object(
            cli, "_resolve_api_key", return_value="xak1.ag_1.sig.payload"
        ), mock.patch.object(cli, "_resolve_agent_id", return_value="ag_1"), mock.patch.object(cli, "_api_request", side_effect=fake_api_request):
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = cli.cmd_limit_orders_create(args)
        self.assertEqual(code, 1)
        out = json.loads(buf.getvalue().strip())
        self.assertFalse(out.get("ok"))
        self.assertEqual(out.get("code"), "payload_invalid")
        details = out.get("details") or {}
        self.assertEqual(details.get("requestId"), "req_123")
        self.assertIn("apiDetails", details)

    def test_profile_set_name_success(self) -> None:
        args = argparse.Namespace(name="harvey-ops", chain="hardhat_local", json=True)
        captured: dict = {}

        def fake_api_request(method: str, path: str, payload: dict | None = None, include_idempotency: bool = False):
            captured["method"] = method
            captured["path"] = path
            captured["payload"] = payload
            return 200, {"agentName": "harvey-ops"}

        with mock.patch.object(cli, "_resolve_api_key", return_value="xak1.ag_1.sig.payload"), mock.patch.object(
            cli, "_resolve_agent_id", return_value="ag_1"
        ), mock.patch.object(
            cli,
            "_wallet_address_for_chain",
            side_effect=[
                "0x1111111111111111111111111111111111111111",
                "0x1111111111111111111111111111111111111111",
            ],
        ), mock.patch.object(
            cli,
            "load_wallet_store",
            return_value={"version": 2, "wallets": {"w1": {}}, "chains": {"hardhat_local": "w1", "ethereum_sepolia": "w1"}},
        ), mock.patch.object(cli, "chain_enabled", return_value=True), mock.patch.object(
            cli, "_api_request", side_effect=fake_api_request
        ):
            code = cli.cmd_profile_set_name(args)
        self.assertEqual(code, 0)
        payload = captured.get("payload") or {}
        self.assertEqual(
            payload.get("wallets"),
            [
                {"chainKey": "hardhat_local", "address": "0x1111111111111111111111111111111111111111"},
                {"chainKey": "ethereum_sepolia", "address": "0x1111111111111111111111111111111111111111"},
            ],
        )

    def test_profile_set_name_rejects_empty_name(self) -> None:
        args = argparse.Namespace(name="   ", chain="hardhat_local", json=True)
        code = cli.cmd_profile_set_name(args)
        self.assertEqual(code, 1)

    def test_profile_set_name_rate_limited(self) -> None:
        args = argparse.Namespace(name="new-name", chain="hardhat_local", json=True)
        with mock.patch.object(cli, "_resolve_api_key", return_value="xak1.ag_1.sig.payload"), mock.patch.object(
            cli, "_resolve_agent_id", return_value="ag_1"
        ), mock.patch.object(cli, "_wallet_address_for_chain", return_value="0x1111111111111111111111111111111111111111"), mock.patch.object(
            cli,
            "load_wallet_store",
            return_value={"version": 2, "wallets": {}, "chains": {"hardhat_local": "w1"}},
        ), mock.patch.object(
            cli, "chain_enabled", return_value=True
        ), mock.patch.object(
            cli,
            "_api_request",
            return_value=(
                429,
                {
                    "code": "rate_limited",
                    "message": "Agent name can only be changed once every 7 days.",
                    "actionHint": "Retry after cooldown.",
                },
            ),
        ):
            code = cli.cmd_profile_set_name(args)
        self.assertEqual(code, 1)

    def test_policy_preapprove_token_rejects_non_address(self) -> None:
        args = argparse.Namespace(chain="base_sepolia", token="NOT_A_TOKEN", json=True)
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = cli.cmd_approvals_request_token(args)
        # Invalid user input should return exit code 2.
        self.assertEqual(code, 2)
        out = json.loads(buf.getvalue().strip())
        self.assertFalse(out.get("ok"))
        self.assertEqual(out.get("code"), "invalid_input")

    def test_policy_preapprove_token_requests_policy_approval(self) -> None:
        args = argparse.Namespace(chain="base_sepolia", token="0x" + "11" * 20, json=True)
        captured: dict = {}

        def fake_api_request(
            method: str,
            path: str,
            payload: dict | None = None,
            include_idempotency: bool = False,
            idempotency_key: str | None = None,
            allow_auth_recovery: bool = True,
        ):
            captured["method"] = method
            captured["path"] = path
            captured["payload"] = payload
            captured["include_idempotency"] = include_idempotency
            captured["idempotency_key"] = idempotency_key
            return 200, {"ok": True, "policyApprovalId": "ppr_1", "status": "approval_pending"}

        with mock.patch.object(cli, "_resolve_api_key", return_value="xak1.ag_1.sig.payload"), mock.patch.object(
            cli, "_resolve_agent_id", return_value="ag_1"
        ), mock.patch.object(cli, "_api_request", side_effect=fake_api_request), mock.patch.object(
            cli, "_maybe_send_telegram_policy_approval_prompt"
        ) as prompt_mock:
            payload = self._run_and_parse_stdout(lambda: cli.cmd_approvals_request_token(args))

        self.assertTrue(payload.get("ok"))
        self.assertEqual(payload.get("policyApprovalId"), "ppr_1")
        self.assertEqual(payload.get("chain"), "base_sepolia")
        self.assertNotIn("queuedMessage", payload)
        self.assertEqual(payload.get("promptSent"), True)
        prompt_mock.assert_called_once()
        self.assertEqual(captured.get("method"), "POST")
        self.assertEqual(captured.get("path"), "/agent/policy-approvals/proposed")
        sent = captured.get("payload") or {}
        self.assertEqual(sent.get("requestType"), "token_preapprove_add")
        self.assertEqual(sent.get("chainKey"), "base_sepolia")
        self.assertRegex(str(captured.get("idempotency_key") or ""), r"^rt-polreq-token-base_sepolia-0x[0-9a-f]{40}-[0-9a-f]{16}$")

    def test_policy_preapprove_token_accepts_symbol(self) -> None:
        args = argparse.Namespace(chain="base_sepolia", token="USDC", json=True)
        captured: dict = {}

        def fake_api_request(
            method: str,
            path: str,
            payload: dict | None = None,
            include_idempotency: bool = False,
            idempotency_key: str | None = None,
            allow_auth_recovery: bool = True,
        ):
            captured["method"] = method
            captured["path"] = path
            captured["payload"] = payload
            captured["include_idempotency"] = include_idempotency
            captured["idempotency_key"] = idempotency_key
            return 200, {"ok": True, "policyApprovalId": "ppr_sym", "status": "approval_pending"}

        expected_addr = cli._resolve_token_address("base_sepolia", "USDC")

        with mock.patch.object(cli, "_resolve_api_key", return_value="xak1.ag_1.sig.payload"), mock.patch.object(
            cli, "_resolve_agent_id", return_value="ag_1"
        ), mock.patch.object(cli, "_api_request", side_effect=fake_api_request):
            payload = self._run_and_parse_stdout(lambda: cli.cmd_approvals_request_token(args))

        self.assertTrue(payload.get("ok"))
        sent = captured.get("payload") or {}
        self.assertEqual(sent.get("tokenAddress"), expected_addr)

    def test_policy_revoke_token_requests_policy_approval(self) -> None:
        args = argparse.Namespace(chain="base_sepolia", token="0x" + "22" * 20, json=True)
        captured: dict = {}

        def fake_api_request(
            method: str,
            path: str,
            payload: dict | None = None,
            include_idempotency: bool = False,
            idempotency_key: str | None = None,
            allow_auth_recovery: bool = True,
        ):
            captured["method"] = method
            captured["path"] = path
            captured["payload"] = payload
            captured["include_idempotency"] = include_idempotency
            captured["idempotency_key"] = idempotency_key
            return 200, {"ok": True, "policyApprovalId": "ppr_2", "status": "approval_pending"}

        with mock.patch.object(cli, "_resolve_api_key", return_value="xak1.ag_1.sig.payload"), mock.patch.object(
            cli, "_resolve_agent_id", return_value="ag_1"
        ), mock.patch.object(cli, "_api_request", side_effect=fake_api_request), mock.patch.object(
            cli, "_maybe_send_telegram_policy_approval_prompt"
        ) as prompt_mock:
            payload = self._run_and_parse_stdout(lambda: cli.cmd_approvals_revoke_token(args))

        self.assertTrue(payload.get("ok"))
        self.assertEqual(payload.get("policyApprovalId"), "ppr_2")
        self.assertNotIn("queuedMessage", payload)
        self.assertEqual(payload.get("promptSent"), True)
        prompt_mock.assert_called_once()
        self.assertEqual(captured.get("method"), "POST")
        self.assertEqual(captured.get("path"), "/agent/policy-approvals/proposed")
        sent = captured.get("payload") or {}
        self.assertEqual(sent.get("requestType"), "token_preapprove_remove")
        self.assertEqual(sent.get("chainKey"), "base_sepolia")
        self.assertRegex(str(captured.get("idempotency_key") or ""), r"^rt-polrev-token-base_sepolia-0x[0-9a-f]{40}-[0-9a-f]{16}$")

    def test_policy_preapprove_global_uses_nonce_idempotency_key(self) -> None:
        args = argparse.Namespace(chain="base_sepolia", json=True)
        captured: dict = {}

        def fake_api_request(
            method: str,
            path: str,
            payload: dict | None = None,
            include_idempotency: bool = False,
            idempotency_key: str | None = None,
            allow_auth_recovery: bool = True,
        ):
            captured["method"] = method
            captured["path"] = path
            captured["payload"] = payload
            captured["idempotency_key"] = idempotency_key
            return 200, {"ok": True, "policyApprovalId": "ppr_3", "status": "approval_pending"}

        with mock.patch.object(cli, "_resolve_api_key", return_value="xak1.ag_1.sig.payload"), mock.patch.object(
            cli, "_resolve_agent_id", return_value="ag_1"
        ), mock.patch.object(cli, "_api_request", side_effect=fake_api_request), mock.patch.object(
            cli, "_maybe_send_telegram_policy_approval_prompt"
        ) as prompt_mock:
            payload = self._run_and_parse_stdout(lambda: cli.cmd_approvals_request_global(args))

        self.assertTrue(payload.get("ok"))
        self.assertNotIn("queuedMessage", payload)
        self.assertEqual(payload.get("promptSent"), True)
        prompt_mock.assert_called_once()
        self.assertEqual(captured.get("method"), "POST")
        self.assertEqual(captured.get("path"), "/agent/policy-approvals/proposed")
        self.assertEqual((captured.get("payload") or {}).get("requestType"), "global_approval_enable")
        self.assertRegex(str(captured.get("idempotency_key") or ""), r"^rt-polreq-global-base_sepolia-[0-9a-f]{16}$")

    def test_policy_revoke_global_uses_nonce_idempotency_key(self) -> None:
        args = argparse.Namespace(chain="base_sepolia", json=True)
        captured: dict = {}

        def fake_api_request(
            method: str,
            path: str,
            payload: dict | None = None,
            include_idempotency: bool = False,
            idempotency_key: str | None = None,
            allow_auth_recovery: bool = True,
        ):
            captured["method"] = method
            captured["path"] = path
            captured["payload"] = payload
            captured["idempotency_key"] = idempotency_key
            return 200, {"ok": True, "policyApprovalId": "ppr_4", "status": "approval_pending"}

        with mock.patch.object(cli, "_resolve_api_key", return_value="xak1.ag_1.sig.payload"), mock.patch.object(
            cli, "_resolve_agent_id", return_value="ag_1"
        ), mock.patch.object(cli, "_api_request", side_effect=fake_api_request), mock.patch.object(
            cli, "_maybe_send_telegram_policy_approval_prompt"
        ) as prompt_mock:
            payload = self._run_and_parse_stdout(lambda: cli.cmd_approvals_revoke_global(args))

        self.assertTrue(payload.get("ok"))
        self.assertNotIn("queuedMessage", payload)
        self.assertEqual(payload.get("promptSent"), True)
        prompt_mock.assert_called_once()
        self.assertEqual(captured.get("method"), "POST")
        self.assertEqual(captured.get("path"), "/agent/policy-approvals/proposed")
        self.assertEqual((captured.get("payload") or {}).get("requestType"), "global_approval_disable")
        self.assertRegex(str(captured.get("idempotency_key") or ""), r"^rt-polrev-global-base_sepolia-[0-9a-f]{16}$")

    def test_policy_request_pending_survives_prompt_send_failure(self) -> None:
        args = argparse.Namespace(chain="base_sepolia", token="USDC", json=True)

        def fake_api_request(
            method: str,
            path: str,
            payload: dict | None = None,
            include_idempotency: bool = False,
            idempotency_key: str | None = None,
            allow_auth_recovery: bool = True,
        ):
            return 200, {"ok": True, "policyApprovalId": "ppr_fail", "status": "approval_pending"}

        with mock.patch.object(cli, "_resolve_api_key", return_value="xak1.ag_1.sig.payload"), mock.patch.object(
            cli, "_resolve_agent_id", return_value="ag_1"
        ), mock.patch.object(cli, "_api_request", side_effect=fake_api_request), mock.patch.object(
            cli, "_maybe_send_telegram_policy_approval_prompt", side_effect=RuntimeError("send failed")
        ):
            payload = self._run_and_parse_stdout(lambda: cli.cmd_approvals_request_token(args))

        self.assertTrue(payload.get("ok"))
        self.assertEqual(payload.get("policyApprovalId"), "ppr_fail")
        self.assertEqual(payload.get("promptSent"), False)

    def test_approvals_decide_spot_approve_emits_runtime_envelope(self) -> None:
        args = argparse.Namespace(
            trade_id="trd_1",
            decision="approve",
            chain="base_sepolia",
            source="web",
            idempotency_key="tg-cb-123",
            decision_at="2026-02-19T20:00:00Z",
            reason_message="",
            json=True,
        )
        with mock.patch.object(
            cli, "_read_trade_details", return_value={"tradeId": "trd_1", "status": "approval_pending", "chainKey": "base_sepolia"}
        ), mock.patch.object(
            cli, "_post_trade_status"
        ) as post_status_mock, mock.patch.object(
            cli, "_cleanup_trade_approval_prompt", return_value={"ok": True, "code": "buttons_cleared"}
        ), mock.patch.object(
            cli, "_maybe_send_telegram_decision_message"
        ), mock.patch.object(
            cli, "_run_resume_spot_inline", return_value=(0, {"ok": True, "code": "ok", "status": "filled", "txHash": "0x" + "ab" * 32})
        ):
            payload = self._run_and_parse_stdout(lambda: cli.cmd_approvals_decide_spot(args))
        self.assertTrue(payload.get("ok"))
        self.assertEqual(payload.get("subjectType"), "trade")
        self.assertEqual(payload.get("subjectId"), "trd_1")
        self.assertEqual(payload.get("decision"), "approve")
        self.assertEqual(payload.get("source"), "web")
        self.assertEqual(payload.get("toStatus"), "approved")
        self.assertEqual(payload.get("executionStatus"), "filled")
        post_status_mock.assert_called_once()
        _, kwargs = post_status_mock.call_args
        self.assertEqual(kwargs.get("idempotency_key"), "tg-cb-123")
        self.assertEqual(kwargs.get("decision_at"), "2026-02-19T20:00:00+00:00")

    def test_approvals_decide_policy_posts_decision_and_envelope(self) -> None:
        args = argparse.Namespace(
            approval_id="ppr_1",
            decision="reject",
            chain="base_sepolia",
            source="web",
            idempotency_key="tg-cb-456",
            decision_at="2026-02-19T20:01:00Z",
            reason_message="Denied",
            json=True,
        )

        captured: dict[str, object] = {}

        def fake_api_request(
            method: str,
            path: str,
            payload: dict | None = None,
            include_idempotency: bool = False,
            idempotency_key: str | None = None,
            allow_auth_recovery: bool = True,
        ):
            captured["idempotency_key"] = idempotency_key
            captured["payload"] = payload or {}
            return 200, {"ok": True, "policyApprovalId": "ppr_1", "status": "rejected", "chainKey": "base_sepolia"}

        with mock.patch.object(cli, "_api_request", side_effect=fake_api_request), mock.patch.object(
            cli, "_cleanup_policy_approval_prompt", return_value={"ok": False, "code": "prompt_not_found"}
        ):
            payload = self._run_and_parse_stdout(lambda: cli.cmd_approvals_decide_policy(args))
        self.assertTrue(payload.get("ok"))
        self.assertEqual(payload.get("subjectType"), "policy")
        self.assertEqual(payload.get("subjectId"), "ppr_1")
        self.assertEqual(payload.get("decision"), "reject")
        self.assertEqual(payload.get("source"), "web")
        self.assertEqual(payload.get("toStatus"), "rejected")
        self.assertEqual(captured.get("idempotency_key"), "tg-cb-456")
        self.assertEqual((captured.get("payload") or {}).get("at"), "2026-02-19T20:01:00+00:00")

    def test_approvals_cleanup_spot_returns_buttons_cleared_when_prompt_removed(self) -> None:
        args = argparse.Namespace(trade_id="trd_1", json=True)
        with mock.patch.object(
            cli,
            "_clear_telegram_approval_buttons",
            return_value={"ok": True, "code": "buttons_cleared", "promptCleanup": {"ok": True, "code": "buttons_cleared"}},
        ):
            payload = self._run_and_parse_stdout(lambda: cli.cmd_approvals_cleanup_spot(args))
        self.assertTrue(payload.get("ok"))
        self.assertEqual(payload.get("tradeId"), "trd_1")
        prompt_cleanup = payload.get("promptCleanup") or {}
        self.assertEqual(prompt_cleanup.get("code"), "buttons_cleared")

    def test_approvals_clear_prompt_returns_cleanup_payload(self) -> None:
        args = argparse.Namespace(subject_type="transfer", subject_id="xfr_1", chain="base_sepolia", json=True)
        with mock.patch.object(
            cli,
            "_clear_telegram_approval_buttons",
            return_value={"ok": True, "code": "buttons_cleared", "promptCleanup": {"ok": True, "code": "buttons_cleared"}},
        ):
            payload = self._run_and_parse_stdout(lambda: cli.cmd_approvals_clear_prompt(args))
        self.assertTrue(payload.get("ok"))
        self.assertEqual(payload.get("subjectType"), "transfer")
        self.assertEqual(payload.get("subjectId"), "xfr_1")
        self.assertEqual((payload.get("promptCleanup") or {}).get("code"), "buttons_cleared")

    def test_clear_telegram_approval_buttons_uses_non_destructive_api_path(self) -> None:
        entry = {"channel": "telegram", "to": "telegram:123456", "messageId": "777"}
        fake_resp = mock.MagicMock()
        fake_ctx = mock.MagicMock()
        fake_ctx.__enter__.return_value = fake_resp
        fake_resp.read.return_value = b'{"ok":true}'

        with mock.patch.dict(os.environ, {"XCLAW_TELEGRAM_BOT_TOKEN": "token"}, clear=False), mock.patch.object(
            cli, "_get_approval_prompt", return_value=entry
        ), mock.patch.object(
            cli, "_remove_approval_prompt"
        ) as remove_prompt, mock.patch(
            "urllib.request.urlopen", return_value=fake_ctx
        ), mock.patch.object(
            cli, "_run_subprocess"
        ) as run_subprocess:
            result = cli._clear_telegram_approval_buttons("trade", "trd_1")
        self.assertTrue(result.get("ok"))
        self.assertEqual(result.get("code"), "buttons_cleared")
        remove_prompt.assert_called_once_with("trd_1")
        run_subprocess.assert_not_called()

    def test_clear_telegram_approval_buttons_suppressed_in_harness_mode(self) -> None:
        with mock.patch.dict(os.environ, {"XCLAW_TEST_HARNESS_DISABLE_TELEGRAM": "1"}, clear=False), mock.patch.object(
            cli, "_get_approval_prompt", return_value={"channel": "telegram", "to": "telegram:123456", "messageId": "777"}
        ), mock.patch.object(
            cli, "_remove_approval_prompt"
        ) as remove_prompt, mock.patch(
            "urllib.request.urlopen"
        ) as urlopen_mock:
            result = cli._clear_telegram_approval_buttons("trade", "trd_1")
        self.assertTrue(bool(result.get("ok")))
        self.assertEqual(str(result.get("code")), "telegram_dispatch_suppressed")
        self.assertEqual(str((result.get("promptCleanup") or {}).get("code")), "telegram_dispatch_suppressed")
        remove_prompt.assert_called_once_with("trd_1")
        urlopen_mock.assert_not_called()

    def test_approvals_decide_spot_invalid_decision_at_rejected(self) -> None:
        args = argparse.Namespace(
            trade_id="trd_1",
            decision="approve",
            chain="base_sepolia",
            source="telegram",
            idempotency_key="tg-cb-1",
            decision_at="not-an-iso",
            reason_message="",
            json=True,
        )
        payload = self._run_and_parse_stdout(lambda: cli.cmd_approvals_decide_spot(args))
        self.assertFalse(payload.get("ok"))
        self.assertEqual(payload.get("code"), "invalid_input")

    def test_management_link_normalizes_loopback_host_to_public_domain(self) -> None:
        args = argparse.Namespace(ttl_seconds=600, json=True)
        with mock.patch.object(cli, "_resolve_api_key", return_value="xak1.ag_1.sig.payload"), mock.patch.object(
            cli, "_resolve_agent_id", return_value="ag_1"
        ), mock.patch.object(
            cli,
            "_api_request",
            return_value=(
                200,
                {
                    "agentId": "ag_1",
                    "managementUrl": "https://127.0.0.1:3000/agents/ag_1?token=ol1.test.token",
                    "issuedAt": "2026-02-14T22:00:00.000Z",
                    "expiresAt": "2026-02-14T22:10:00.000Z",
                },
            ),
        ), mock.patch.object(
            cli, "_maybe_send_owner_link_to_active_chat", return_value={"sent": True, "channel": "telegram", "messageId": "m1"}
        ):
            payload = self._run_and_parse_stdout(lambda: cli.cmd_management_link(args))
        self.assertEqual(payload.get("ok"), True)
        self.assertEqual(payload.get("ownerHandoffRequired"), True)
        self.assertNotIn("sensitiveFields", payload)
        self.assertEqual(payload.get("deliveredToActiveChat"), True)
        self.assertEqual((payload.get("delivery") or {}).get("channel"), "telegram")
        self.assertEqual(payload.get("managementUrlOmitted"), True)
        self.assertNotIn("managementUrl", payload)

    def test_dashboard_success(self) -> None:
        args = argparse.Namespace(chain="hardhat_local", json=True)

        def fake_api_request(method: str, path: str, payload=None, include_idempotency: bool = False, allow_auth_recovery: bool = True):
            if path.startswith("/public/agents/ag_1/trades"):
                return (200, {"items": [{"trade_id": "trd_1"}]})
            if path == "/public/agents/ag_1":
                return (200, {"agent": {"agent_id": "ag_1", "agent_name": "harvey"}})
            if path.startswith("/trades/pending"):
                return (200, {"items": [{"tradeId": "trd_pending_1"}]})
            if path.startswith("/limit-orders?"):
                return (200, {"items": [{"orderId": "ord_1"}]})
            if path.startswith("/chat/messages"):
                return (200, {"items": [{"messageId": "msg_1"}]})
            return (500, {"code": "api_error", "message": path})

        with mock.patch.object(cli, "_resolve_api_key", return_value="xak1.ag_1.sig.payload"), mock.patch.object(
            cli, "_resolve_agent_id", return_value="ag_1"
        ), mock.patch.object(
            cli, "_fetch_wallet_holdings", return_value={"address": "0x1111111111111111111111111111111111111111"}
        ), mock.patch.object(
            cli, "_api_request", side_effect=fake_api_request
        ):
            code = cli.cmd_dashboard(args)
        self.assertEqual(code, 0)

    def test_dashboard_handles_holdings_failure(self) -> None:
        args = argparse.Namespace(chain="hardhat_local", json=True)

        def fake_api_request(method: str, path: str, payload=None, include_idempotency: bool = False, allow_auth_recovery: bool = True):
            if path == "/public/agents/ag_1":
                return (200, {"agent": {"agent_id": "ag_1", "agent_name": "harvey"}})
            return (200, {"items": []})

        with mock.patch.object(cli, "_resolve_api_key", return_value="xak1.ag_1.sig.payload"), mock.patch.object(
            cli, "_resolve_agent_id", return_value="ag_1"
        ), mock.patch.object(
            cli, "_fetch_wallet_holdings", side_effect=cli.WalletStoreError("wallet missing")
        ), mock.patch.object(
            cli, "_api_request", side_effect=fake_api_request
        ):
            code = cli.cmd_dashboard(args)
        self.assertEqual(code, 0)

    def test_trade_execute_real_does_not_auto_report(self) -> None:
        args = argparse.Namespace(intent="trd_real_1", chain="base_sepolia", json=True)
        trade_payload = {
            "tradeId": "trd_real_1",
            "chainKey": "base_sepolia",
            "status": "approved",
            "mode": "real",
            "retry": {"eligible": False},
            "tokenIn": "0x1111111111111111111111111111111111111111",
            "tokenOut": "0x2222222222222222222222222222222222222222",
            "amountIn": "1",
            "slippageBps": 50,
        }
        with mock.patch.object(cli, "_read_trade_details", return_value=trade_payload), mock.patch.object(
            cli, "_enforce_spend_preconditions", return_value=({}, "2026-02-14", 0, 1000000000)
        ), mock.patch.object(
            cli, "_replay_trade_usage_outbox", return_value=(0, 0)
        ), mock.patch.object(
            cli, "_enforce_trade_caps", return_value=({}, "2026-02-14", cli.Decimal("0"), 0, {"maxDailyUsd": "1000", "maxDailyTradeCount": 10})
        ), mock.patch.object(
            cli, "_record_trade_cap_ledger"
        ), mock.patch.object(
            cli, "_post_trade_usage"
        ), mock.patch.object(
            cli, "_execution_wallet", return_value=("0x1111111111111111111111111111111111111111", "11" * 32)
        ), mock.patch.object(
            cli, "_require_chain_contract_address", return_value="0x3333333333333333333333333333333333333333"
        ), mock.patch.object(
            cli, "_cast_calldata", return_value="0xdeadbeef"
        ), mock.patch.object(
            cli, "_cast_rpc_send_transaction", return_value="0x" + "ab" * 32
        ), mock.patch.object(
            cli.subprocess, "run", return_value=mock.Mock(returncode=0, stdout='{"status":"0x1"}', stderr="")
        ), mock.patch.object(
            cli, "_post_trade_status"
        ), mock.patch.object(
            cli, "_record_spend"
        ), mock.patch.object(
            cli, "_send_trade_execution_report"
        ) as report_mock:
            code = cli.cmd_trade_execute(args)
        self.assertEqual(code, 0)
        report_mock.assert_not_called()

    def test_trade_execute_success_includes_builder_metadata_fields(self) -> None:
        args = argparse.Namespace(intent="trd_real_builder", chain="base_sepolia", json=True)
        trade_payload = {
            "tradeId": "trd_real_builder",
            "chainKey": "base_sepolia",
            "status": "approved",
            "mode": "real",
            "retry": {"eligible": False},
            "tokenIn": "0x1111111111111111111111111111111111111111",
            "tokenOut": "0x2222222222222222222222222222222222222222",
            "amountIn": "1",
            "slippageBps": 50,
        }
        with mock.patch.object(cli, "_read_trade_details", return_value=trade_payload), mock.patch.object(
            cli, "_enforce_spend_preconditions", return_value=({}, "2026-02-14", 0, 1000000000)
        ), mock.patch.object(
            cli, "_replay_trade_usage_outbox", return_value=(0, 0)
        ), mock.patch.object(
            cli, "_enforce_trade_caps", return_value=({}, "2026-02-14", cli.Decimal("0"), 0, {"maxDailyUsd": "1000", "maxDailyTradeCount": 10})
        ), mock.patch.object(
            cli, "_record_trade_cap_ledger"
        ), mock.patch.object(
            cli, "_post_trade_usage"
        ), mock.patch.object(
            cli, "_execution_wallet", return_value=("0x1111111111111111111111111111111111111111", "11" * 32)
        ), mock.patch.object(
            cli, "_require_chain_contract_address", return_value="0x3333333333333333333333333333333333333333"
        ), mock.patch.object(
            cli, "_cast_calldata", return_value="0xdeadbeef"
        ), mock.patch.object(
            cli, "_cast_rpc_send_transaction", return_value="0x" + "ab" * 32
        ), mock.patch.object(
            cli.subprocess, "run", return_value=mock.Mock(returncode=0, stdout='{"status":"0x1"}', stderr="")
        ), mock.patch.object(
            cli, "_post_trade_status"
        ), mock.patch.object(
            cli, "_record_spend"
        ):
            payload = self._run_and_parse_stdout(lambda: cli.cmd_trade_execute(args))
        self.assertTrue(payload.get("ok"))
        self.assertIn("builderCodeChainEligible", payload)
        self.assertIn("builderCodeApplied", payload)
        self.assertIn("builderCodeSkippedReason", payload)
        self.assertIn("builderCodeSource", payload)
        self.assertIn("builderCodeStandard", payload)

    def test_trade_execute_real_returns_verifying_without_receipt_wait(self) -> None:
        args = argparse.Namespace(intent="trd_real_async", chain="base_sepolia", json=True)
        trade_payload = {
            "tradeId": "trd_real_async",
            "chainKey": "base_sepolia",
            "status": "approved",
            "mode": "real",
            "retry": {"eligible": False},
            "tokenIn": "0x1111111111111111111111111111111111111111",
            "tokenOut": "0x2222222222222222222222222222222222222222",
            "amountIn": "1",
            "slippageBps": 50,
        }
        with mock.patch.object(cli, "_read_trade_details", return_value=trade_payload), mock.patch.object(
            cli, "_trade_provider_settings", return_value=("uniswap_api", {})
        ), mock.patch.object(
            cli, "_replay_trade_usage_outbox", return_value=(0, 0)
        ), mock.patch.object(
            cli, "_enforce_spend_preconditions", return_value=({}, "2026-02-14", 0, 1000000000)
        ), mock.patch.object(
            cli, "_enforce_trade_caps", return_value=({}, "2026-02-14", cli.Decimal("0"), 0, {"maxDailyUsd": "1000", "maxDailyTradeCount": 10})
        ), mock.patch.object(
            cli, "_execution_wallet", return_value=("0x1111111111111111111111111111111111111111", "11" * 32)
        ), mock.patch.object(
            cli, "_resolve_token_address", side_effect=["0x" + "11" * 20, "0x" + "22" * 20]
        ), mock.patch.object(
            cli, "_fetch_erc20_metadata", return_value={"decimals": 18, "symbol": "USDC"}
        ), mock.patch.object(
            cli, "_execute_uniswap_swap_via_proxy", return_value={"txHash": "0x" + "ab" * 32, "routeType": "EXACT_INPUT"}
        ), mock.patch.object(
            cli, "_post_trade_status"
        ), mock.patch.object(
            cli, "_run_subprocess"
        ) as run_subprocess_mock, mock.patch.object(
            cli, "_record_spend"
        ) as record_spend_mock, mock.patch.object(
            cli, "_record_trade_cap_ledger"
        ) as record_cap_mock, mock.patch.object(
            cli, "_post_trade_usage"
        ) as post_usage_mock:
            payload = self._run_and_parse_stdout(lambda: cli.cmd_trade_execute(args))

        self.assertTrue(payload.get("ok"))
        self.assertEqual(payload.get("status"), "verifying")
        run_subprocess_mock.assert_not_called()
        record_spend_mock.assert_not_called()
        record_cap_mock.assert_not_called()
        post_usage_mock.assert_not_called()

    def test_trade_execute_blocks_on_daily_trade_cap(self) -> None:
        args = argparse.Namespace(intent="trd_real_2", chain="base_sepolia", json=True)
        trade_payload = {
            "tradeId": "trd_real_2",
            "chainKey": "base_sepolia",
            "status": "approved",
            "mode": "real",
            "retry": {"eligible": False},
            "tokenIn": "0x1111111111111111111111111111111111111111",
            "tokenOut": "0x2222222222222222222222222222222222222222",
            "amountIn": "250",
            "slippageBps": 50,
        }
        with mock.patch.object(cli, "_read_trade_details", return_value=trade_payload), mock.patch.object(
            cli, "_replay_trade_usage_outbox", return_value=(0, 0)
        ), mock.patch.object(
            cli, "_enforce_spend_preconditions", return_value=({}, "2026-02-14", 0, 1000000000)
        ), mock.patch.object(
            cli, "_execution_wallet", return_value=("0x1111111111111111111111111111111111111111", "11" * 32)
        ), mock.patch.object(
            cli,
            "_enforce_trade_caps",
            side_effect=cli.WalletPolicyError(
                "daily_trade_count_cap_exceeded",
                "Trade blocked because daily filled-trade cap would be exceeded.",
                "Raise maxDailyTradeCount.",
                {"maxDailyTradeCount": 1},
            ),
        ):
            payload = self._run_and_parse_stdout(lambda: cli.cmd_trade_execute(args))
        self.assertFalse(payload.get("ok"))
        self.assertEqual(payload.get("code"), "daily_trade_count_cap_exceeded")

    def test_trade_execute_resolves_symbol_tokens_before_approve_and_swap(self) -> None:
        args = argparse.Namespace(intent="trd_real_sym", chain="base_sepolia", json=True)
        trade_payload = {
            "tradeId": "trd_real_sym",
            "chainKey": "base_sepolia",
            "status": "approved",
            "mode": "real",
            "retry": {"eligible": False},
            "tokenIn": "USDC",
            "tokenOut": "WETH",
            "amountIn": "5",
            "slippageBps": 50,
        }
        sent_txs: list[dict] = []
        captured: dict[str, list[object]] = {}

        def fake_send(rpc_url: str, tx_obj: dict, private_key_hex: str, **kwargs) -> str:
            sent_txs.append(tx_obj)
            return "0x" + "ab" * 32

        def fake_calldata(signature: str, values: list[object]) -> str:
            if signature.startswith("approve("):
                captured["approveValues"] = values
            if signature.startswith("swapExactTokensForTokens("):
                captured["swapValues"] = values
            return "0xdeadbeef"

        with mock.patch.object(cli, "_read_trade_details", return_value=trade_payload), mock.patch.object(
            cli, "_resolve_token_address", side_effect=["0x" + "11" * 20, "0x" + "22" * 20]
        ), mock.patch.object(
            cli, "_fetch_erc20_metadata", return_value={"decimals": 18, "symbol": "USDC"}
        ), mock.patch.object(
            cli, "_enforce_spend_preconditions", return_value=({}, "2026-02-14", 0, 1000000000)
        ), mock.patch.object(
            cli, "_replay_trade_usage_outbox", return_value=(0, 0)
        ), mock.patch.object(
            cli, "_enforce_trade_caps", return_value=({}, "2026-02-14", cli.Decimal("0"), 0, {"maxDailyUsd": "1000", "maxDailyTradeCount": 10})
        ), mock.patch.object(
            cli, "_record_trade_cap_ledger"
        ), mock.patch.object(
            cli, "_post_trade_usage"
        ), mock.patch.object(
            cli, "_execution_wallet", return_value=("0x1111111111111111111111111111111111111111", "11" * 32)
        ), mock.patch.object(
            cli, "_require_chain_contract_address", return_value="0x3333333333333333333333333333333333333333"
        ), mock.patch.object(
            cli, "_cast_calldata", side_effect=fake_calldata
        ), mock.patch.object(
            cli, "_cast_rpc_send_transaction", side_effect=fake_send
        ), mock.patch.object(
            cli.subprocess, "run", return_value=mock.Mock(returncode=0, stdout='{"status":"0x1"}', stderr="")
        ), mock.patch.object(
            cli, "_post_trade_status"
        ), mock.patch.object(
            cli, "_record_spend"
        ), mock.patch.object(
            cli, "_send_trade_execution_report"
        ):
            code = cli.cmd_trade_execute(args)

        self.assertEqual(code, 0)
        self.assertGreaterEqual(len(sent_txs), 2)
        # First tx is token approval; it must target resolved tokenIn (USDC), not a hardcoded fallback token.
        self.assertEqual(str(sent_txs[0].get("to")), "0x" + "11" * 20)
        # amountIn "5" must be interpreted as 5.0 tokens => 5e18 units for 18-decimals mock USDC.
        self.assertEqual(str((captured.get("approveValues") or [None, None])[1]), str(5 * 10**18))
        self.assertEqual(str((captured.get("swapValues") or [None])[0]), str(5 * 10**18))

    def test_removed_offdex_command_is_not_available(self) -> None:
        with self.assertRaises(SystemExit):
            cli.main(["offdex"])

    def test_wallet_create_command_is_not_available(self) -> None:
        # Wallet create exists for installer/bootstrap, but should fail in non-interactive
        # mode when passphrase is not provided.
        args = argparse.Namespace(chain="hardhat_local", json=True)
        code = cli.cmd_wallet_create(args)
        self.assertNotEqual(code, 0)

    def test_wallet_import_command_parses_and_is_guarded_non_interactive(self) -> None:
        with mock.patch.object(cli, "cmd_wallet_import", return_value=2) as cmd_mock:
            code = cli.main(["wallet", "import", "--chain", "hardhat_local", "--json"])
        self.assertEqual(code, 2)
        cmd_mock.assert_called_once()

    def test_wallet_remove_command_parses_and_dispatches(self) -> None:
        with mock.patch.object(cli, "cmd_wallet_remove", return_value=0) as cmd_mock:
            code = cli.main(["wallet", "remove", "--chain", "hardhat_local", "--json"])
        self.assertEqual(code, 0)
        cmd_mock.assert_called_once()

    def test_wallet_send_token_command_parses(self) -> None:
        with mock.patch.object(cli, "cmd_wallet_send_token", return_value=0):
            code = cli.main(
                [
                    "wallet",
                    "send-token",
                    "--token",
                    "0x1111111111111111111111111111111111111111",
                    "--to",
                    "0x2222222222222222222222222222222222222222",
                    "--amount-wei",
                    "1",
                    "--chain",
                    "hardhat_local",
                    "--json",
                ]
            )
        self.assertEqual(code, 0)

    def test_x402_receive_request_parser_defaults(self) -> None:
        parser = cli.build_parser()
        args = parser.parse_args(
            [
                "x402",
                "receive-request",
                "--network",
                "base_sepolia",
                "--facilitator",
                "cdp",
                "--amount-atomic",
                "1",
                "--json",
            ]
        )
        self.assertEqual(str(args.asset_kind), "native")

    def test_limit_orders_sync_success(self) -> None:
        args = argparse.Namespace(chain="hardhat_local", json=True)
        with mock.patch.object(
            cli,
            "_api_request",
            return_value=(200, {"items": [{"orderId": "lmt_1", "chainKey": "hardhat_local", "status": "open"}]}),
        ), mock.patch.object(cli, "save_limit_order_store") as save_store:
            code = cli.cmd_limit_orders_sync(args)
        self.assertEqual(code, 0)
        save_store.assert_called_once()

    def test_limit_orders_run_once_mock_fill(self) -> None:
        args = argparse.Namespace(chain="hardhat_local", json=True, sync=False)
        store = {
            "version": 1,
            "orders": [
                {
                    "orderId": "lmt_1",
                    "chainKey": "hardhat_local",
                    "status": "open",
                    "side": "buy",
                    "mode": "mock",
                    "tokenIn": "0x1111111111111111111111111111111111111111",
                    "tokenOut": "0x2222222222222222222222222222222222222222",
                    "amountIn": "1",
                    "limitPrice": "20",
                }
            ],
        }
        statuses: list[dict[str, str]] = []
        with mock.patch.object(cli, "_replay_limit_order_outbox", return_value=(0, 0)), mock.patch.object(
            cli, "load_limit_order_store", return_value=store
        ), mock.patch.object(cli, "_quote_router_price", return_value=Decimal("10")), mock.patch.object(
            cli,
            "_post_limit_order_status",
            side_effect=lambda order_id, payload, queue_on_failure=True: statuses.append({"orderId": order_id, "status": str(payload.get("status"))}),
        ):
            code = cli.cmd_limit_orders_run_once(args)
        self.assertEqual(code, 0)
        self.assertEqual([entry["status"] for entry in statuses], ["failed"])

    def test_limit_orders_run_once_real_failure_reports_failed(self) -> None:
        args = argparse.Namespace(chain="hardhat_local", json=True, sync=False)
        store = {
            "version": 1,
            "orders": [
                {
                    "orderId": "lmt_1",
                    "chainKey": "hardhat_local",
                    "status": "open",
                    "side": "sell",
                    "mode": "real",
                    "tokenIn": "0x1111111111111111111111111111111111111111",
                    "tokenOut": "0x2222222222222222222222222222222222222222",
                    "amountIn": "1",
                    "limitPrice": "1",
                }
            ],
        }
        statuses: list[str] = []
        with mock.patch.object(cli, "_replay_limit_order_outbox", return_value=(0, 0)), mock.patch.object(
            cli, "load_limit_order_store", return_value=store
        ), mock.patch.object(cli, "_quote_router_price", return_value=Decimal("2")), mock.patch.object(
            cli, "_execute_limit_order_real", side_effect=cli.WalletStoreError("rpc down")
        ), mock.patch.object(
            cli,
            "_post_limit_order_status",
            side_effect=lambda order_id, payload, queue_on_failure=True: statuses.append(str(payload.get("status"))),
        ):
            code = cli.cmd_limit_orders_run_once(args)
        self.assertEqual(code, 0)
        self.assertEqual(statuses, ["triggered", "failed"])

    def test_trade_spot_prefers_uniswap_proxy_when_enabled(self) -> None:
        args = argparse.Namespace(
            chain="ethereum_sepolia",
            token_in="WETH",
            token_out="USDC",
            amount_in="1",
            slippage_bps=50,
            deadline_sec=120,
            to=None,
            json=True,
        )
        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(cli, "_replay_trade_usage_outbox"))
            stack.enter_context(mock.patch.object(cli, "_trade_provider_settings", return_value=("uniswap_api", "legacy_router")))
            stack.enter_context(mock.patch.object(cli, "_resolve_token_address", side_effect=["0x" + "11" * 20, "0x" + "22" * 20]))
            stack.enter_context(mock.patch.object(cli, "load_wallet_store", return_value={}))
            stack.enter_context(mock.patch.object(cli, "_execution_wallet", return_value=("0x" + "33" * 20, "0x" + "44" * 32)))
            stack.enter_context(mock.patch.object(cli, "_require_cast_bin", return_value="cast"))
            stack.enter_context(mock.patch.object(cli, "_chain_rpc_url", return_value="https://rpc.example"))
            stack.enter_context(mock.patch.object(cli, "_legacy_router_available", return_value=False))
            stack.enter_context(
                mock.patch.object(cli, "_fetch_erc20_metadata", side_effect=[{"symbol": "WETH", "decimals": 18}, {"symbol": "USDC", "decimals": 6}])
            )
            stack.enter_context(mock.patch.object(cli, "_enforce_spend_preconditions", return_value=({}, "2026-02-20", 0, 10**30)))
            stack.enter_context(
                mock.patch.object(cli, "_uniswap_quote_via_proxy", return_value={"amountOutUnits": str(10**6), "routeType": "CLASSIC", "quote": {"k": "v"}})
            )
            stack.enter_context(
                mock.patch.object(cli, "_enforce_trade_caps", return_value=({}, "2026-02-20", Decimal("0"), 0, {"maxDailyUsd": "1000", "maxDailyTradeCount": 10}))
            )
            stack.enter_context(mock.patch.object(cli, "_post_trade_proposed", return_value={"ok": True, "tradeId": "trd_1", "status": "approved"}))
            stack.enter_context(
                mock.patch.object(
                    cli,
                    "_execute_uniswap_swap_via_proxy",
                    return_value={"txHash": "0x" + "ab" * 32, "approveTxHash": None, "amountOutUnits": str(10**6), "routeType": "CLASSIC"},
                )
            )
            stack.enter_context(mock.patch.object(cli.subprocess, "run", return_value=mock.Mock(returncode=0, stdout='{\"status\":\"0x1\"}', stderr="")))
            stack.enter_context(mock.patch.object(cli, "_post_trade_status"))
            stack.enter_context(mock.patch.object(cli, "_record_spend"))
            stack.enter_context(mock.patch.object(cli, "_record_trade_cap_ledger"))
            stack.enter_context(mock.patch.object(cli, "_post_trade_usage"))
            payload = self._run_and_parse_stdout(lambda: cli.cmd_trade_spot(args))
        self.assertTrue(payload.get("ok"))
        self.assertEqual(payload.get("providerUsed"), "uniswap_api")
        self.assertEqual(payload.get("fallbackUsed"), False)
        self.assertEqual(payload.get("uniswapRouteType"), "CLASSIC")
        self.assertIn("builderCodeChainEligible", payload)
        self.assertIn("builderCodeApplied", payload)
        self.assertIn("builderCodeSkippedReason", payload)
        self.assertIn("builderCodeSource", payload)
        self.assertIn("builderCodeStandard", payload)

    def test_trade_spot_falls_back_to_legacy_when_uniswap_quote_fails(self) -> None:
        args = argparse.Namespace(
            chain="ethereum_sepolia",
            token_in="WETH",
            token_out="USDC",
            amount_in="1",
            slippage_bps=50,
            deadline_sec=120,
            to=None,
            json=True,
        )
        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(cli, "_replay_trade_usage_outbox"))
            stack.enter_context(mock.patch.object(cli, "_trade_provider_settings", return_value=("uniswap_api", "legacy_router")))
            stack.enter_context(mock.patch.object(cli, "_resolve_token_address", side_effect=["0x" + "11" * 20, "0x" + "22" * 20]))
            stack.enter_context(mock.patch.object(cli, "load_wallet_store", return_value={}))
            stack.enter_context(mock.patch.object(cli, "_execution_wallet", return_value=("0x" + "33" * 20, "0x" + "44" * 32)))
            stack.enter_context(mock.patch.object(cli, "_require_cast_bin", return_value="cast"))
            stack.enter_context(mock.patch.object(cli, "_chain_rpc_url", return_value="https://rpc.example"))
            stack.enter_context(mock.patch.object(cli, "_legacy_router_available", return_value=True))
            stack.enter_context(mock.patch.object(cli, "_require_chain_contract_address", return_value="0x" + "66" * 20))
            stack.enter_context(
                mock.patch.object(cli, "_fetch_erc20_metadata", side_effect=[{"symbol": "WETH", "decimals": 18}, {"symbol": "USDC", "decimals": 6}])
            )
            stack.enter_context(mock.patch.object(cli, "_enforce_spend_preconditions", return_value=({}, "2026-02-20", 0, 10**30)))
            stack.enter_context(mock.patch.object(cli, "_uniswap_quote_via_proxy", side_effect=cli.WalletStoreError("proxy down")))
            stack.enter_context(mock.patch.object(cli, "_router_get_amount_out", return_value=10**6))
            stack.enter_context(
                mock.patch.object(cli, "_enforce_trade_caps", return_value=({}, "2026-02-20", Decimal("0"), 0, {"maxDailyUsd": "1000", "maxDailyTradeCount": 10}))
            )
            stack.enter_context(mock.patch.object(cli, "_post_trade_proposed", return_value={"ok": True, "tradeId": "trd_1", "status": "approved"}))
            stack.enter_context(mock.patch.object(cli, "_fetch_token_allowance_wei", return_value=str(10**30)))
            stack.enter_context(mock.patch.object(cli, "_cast_calldata", return_value="0xdeadbeef"))
            stack.enter_context(mock.patch.object(cli, "_cast_rpc_send_transaction", return_value="0x" + "ab" * 32))
            stack.enter_context(mock.patch.object(cli.subprocess, "run", return_value=mock.Mock(returncode=0, stdout='{\"status\":\"0x1\"}', stderr="")))
            stack.enter_context(mock.patch.object(cli, "_post_trade_status"))
            stack.enter_context(mock.patch.object(cli, "_record_spend"))
            stack.enter_context(mock.patch.object(cli, "_record_trade_cap_ledger"))
            stack.enter_context(mock.patch.object(cli, "_post_trade_usage"))
            payload = self._run_and_parse_stdout(lambda: cli.cmd_trade_spot(args))
        self.assertTrue(payload.get("ok"))
        self.assertEqual(payload.get("providerUsed"), "legacy_router")
        self.assertEqual(payload.get("fallbackUsed"), True)

    def test_liquidity_provider_settings_prefers_chain_config(self) -> None:
        with mock.patch.object(
            cli,
            "_load_chain_config",
            return_value={
                "liquidityProviders": {"primary": "uniswap_api", "fallback": "legacy_router"},
                "uniswapApi": {"enabled": True, "liquidityEnabled": True},
            },
        ):
            primary, fallback = cli._liquidity_provider_settings("ethereum_sepolia")
        self.assertEqual(primary, "uniswap_api")
        self.assertEqual(fallback, "legacy_router")

    def test_liquidity_provider_settings_uniswap_flag_defaults_to_uniswap(self) -> None:
        with mock.patch.object(
            cli,
            "_load_chain_config",
            return_value={"uniswapApi": {"enabled": True, "liquidityEnabled": True}},
        ):
            primary, fallback = cli._liquidity_provider_settings("ethereum_sepolia")
        self.assertEqual(primary, "uniswap_api")
        self.assertEqual(fallback, "legacy_router")

    def test_liquidity_provider_meta_contains_expected_fields(self) -> None:
        meta = cli._build_liquidity_provider_meta(
            provider_requested="uniswap_api",
            provider_used="legacy_router",
            fallback_used=True,
            fallback_reason={"code": "uniswap_lp_failed", "message": "boom"},
            uniswap_lp_operation="decrease",
        )
        self.assertEqual(meta.get("providerRequested"), "uniswap_api")
        self.assertEqual(meta.get("providerUsed"), "legacy_router")
        self.assertTrue(meta.get("fallbackUsed"))
        self.assertEqual(meta.get("fallbackReason"), {"code": "uniswap_lp_failed", "message": "boom"})
        self.assertEqual(meta.get("uniswapLpOperation"), "decrease")

    def test_trade_provider_settings_uses_chain_config_for_promoted_v2_fallback(self) -> None:
        with mock.patch.object(
            cli,
            "_load_chain_config",
            return_value={
                "tradeProviders": {"primary": "uniswap_api", "fallback": "legacy_router"},
                "tradeOperations": {"legacyEnabled": True, "adapter": "legacy_router"},
                "coreContracts": {"router": "0x" + "11" * 20},
            },
        ):
            primary, fallback = cli._trade_provider_settings("base_mainnet")
        self.assertEqual(primary, "uniswap_api")
        self.assertEqual(fallback, "legacy_router")

    def test_trade_provider_settings_keeps_fallback_disabled_when_legacy_not_enabled(self) -> None:
        with mock.patch.object(
            cli,
            "_load_chain_config",
            return_value={
                "tradeProviders": {"primary": "uniswap_api", "fallback": "legacy_router"},
                "tradeOperations": {"legacyEnabled": False, "adapter": "none"},
            },
        ):
            primary, fallback = cli._trade_provider_settings("zksync_mainnet")
        self.assertEqual(primary, "uniswap_api")
        self.assertEqual(fallback, "none")


if __name__ == "__main__":
    unittest.main()
