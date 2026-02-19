import argparse
import io
import json
import pathlib
import sys
import unittest
from contextlib import redirect_stdout
from unittest import mock

RUNTIME_ROOT = pathlib.Path("apps/agent-runtime").resolve()
if str(RUNTIME_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNTIME_ROOT))

from xclaw_agent import cli  # noqa: E402
from xclaw_agent.liquidity_adapter import HederaSdkUnavailable  # noqa: E402


class LiquidityCliTests(unittest.TestCase):
    def _run(self, fn):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = fn()
        payload = json.loads(buf.getvalue().strip())
        return code, payload

    def test_quote_add_rejects_unsupported_adapter(self) -> None:
        args = argparse.Namespace(
            chain="base_sepolia",
            dex="aerodrome",
            token_a="USDC",
            token_b="WETH",
            amount_a="1",
            amount_b="1",
            position_type="v3",
            slippage_bps=100,
            json=True,
        )
        code, payload = self._run(lambda: cli.cmd_liquidity_quote_add(args))
        self.assertEqual(code, 2)
        self.assertEqual(payload.get("code"), "unsupported_liquidity_adapter")

    def test_quote_add_fails_closed_when_hedera_sdk_missing(self) -> None:
        args = argparse.Namespace(
            chain="hedera_testnet",
            dex="hedera_hts",
            token_a="HBAR",
            token_b="USDC",
            amount_a="1",
            amount_b="1",
            position_type="v2",
            slippage_bps=100,
            json=True,
        )
        with mock.patch.object(
            cli,
            "build_liquidity_adapter_for_request",
            side_effect=HederaSdkUnavailable("Hedera SDK module is not installed."),
        ):
            code, payload = self._run(lambda: cli.cmd_liquidity_quote_add(args))
        self.assertEqual(code, 2)
        self.assertEqual(payload.get("code"), "missing_dependency")

    def test_quote_add_hedera_hts_is_router_independent(self) -> None:
        args = argparse.Namespace(
            chain="hedera_testnet",
            dex="hedera_hts",
            token_a="0x" + "11" * 20,
            token_b="0x" + "22" * 20,
            amount_a="1",
            amount_b="1",
            position_type="v2",
            slippage_bps=100,
            json=True,
        )
        adapter = mock.Mock()
        adapter.dex = "hedera_hts"
        adapter.protocol_family = "hedera_hts"
        adapter.quote_add.return_value = {"simulation": {"minAmountA": "0.99", "minAmountB": "0.99"}}

        with mock.patch.object(cli, "assert_chain_capability"), mock.patch.object(
            cli, "build_liquidity_adapter_for_request", return_value=adapter
        ), mock.patch.object(
            cli, "_resolve_token_address", side_effect=["0x" + "11" * 20, "0x" + "22" * 20]
        ), mock.patch.object(
            cli, "_fetch_erc20_metadata"
        ) as mocked_meta, mock.patch.object(
            cli, "_router_get_amount_out"
        ) as mocked_quote:
            code, payload = self._run(lambda: cli.cmd_liquidity_quote_add(args))

        self.assertEqual(code, 0)
        self.assertEqual(payload.get("adapterFamily"), "hedera_hts")
        self.assertEqual(payload.get("simulationOnly"), True)
        self.assertEqual(payload.get("minAmountB"), "0.99")
        self.assertFalse(mocked_meta.called)
        self.assertFalse(mocked_quote.called)

    def test_quote_add_evm_uses_router_path(self) -> None:
        args = argparse.Namespace(
            chain="hedera_testnet",
            dex="saucerswap",
            token_a="0x" + "11" * 20,
            token_b="0x" + "22" * 20,
            amount_a="1",
            amount_b="1",
            position_type="v2",
            slippage_bps=100,
            json=True,
        )
        adapter = mock.Mock()
        adapter.dex = "saucerswap"
        adapter.protocol_family = "amm_v2"
        adapter.quote_add.return_value = {"simulation": {"minAmountA": "0.99", "minAmountB": "0.99"}}
        token_meta = {"symbol": "TOK", "decimals": 18}

        with mock.patch.object(cli, "assert_chain_capability"), mock.patch.object(
            cli, "build_liquidity_adapter_for_request", return_value=adapter
        ), mock.patch.object(
            cli, "_resolve_token_address", side_effect=["0x" + "11" * 20, "0x" + "22" * 20]
        ), mock.patch.object(
            cli, "_fetch_erc20_metadata", side_effect=[token_meta, token_meta]
        ) as mocked_meta, mock.patch.object(
            cli, "_router_get_amount_out", return_value=10**18
        ) as mocked_quote:
            code, payload = self._run(lambda: cli.cmd_liquidity_quote_add(args))

        self.assertEqual(code, 0)
        self.assertEqual(payload.get("adapterFamily"), "amm_v2")
        self.assertTrue(mocked_meta.called)
        self.assertTrue(mocked_quote.called)

    def test_liquidity_add_runs_preflight_before_propose(self) -> None:
        args = argparse.Namespace(
            chain="base_sepolia",
            dex="aerodrome",
            token_a="USDC",
            token_b="WETH",
            amount_a="10",
            amount_b="1",
            position_type="v2",
            v3_range=None,
            slippage_bps=100,
            json=True,
        )
        adapter = mock.Mock()
        adapter.dex = "aerodrome"
        adapter.protocol_family = "amm_v2"
        adapter.quote_add.return_value = {"simulation": {"minAmountA": "9.9", "minAmountB": "0.99"}}

        with mock.patch.object(cli, "assert_chain_capability"), mock.patch.object(
            cli, "_resolve_agent_id_or_fail", return_value="agt_1"
        ), mock.patch.object(
            cli, "_resolve_token_address", side_effect=["0x" + "11" * 20, "0x" + "22" * 20]
        ), mock.patch.object(
            cli, "build_liquidity_adapter_for_request", return_value=adapter
        ), mock.patch.object(
            cli, "_api_request", return_value=(200, {"liquidityIntentId": "liq_1", "status": "approved"})
        ), mock.patch.object(
            cli, "_run_liquidity_execute_inline", return_value=(0, {"ok": True, "code": "ok", "status": "filled", "txHash": "0xabc"})
        ):
            code, payload = self._run(lambda: cli.cmd_liquidity_add(args))

        self.assertEqual(code, 0)
        self.assertEqual(payload.get("status"), "filled")
        self.assertEqual(payload.get("adapterFamily"), "amm_v2")
        self.assertTrue(adapter.quote_add.called)

    def test_liquidity_add_sets_hts_native_detail(self) -> None:
        args = argparse.Namespace(
            chain="hedera_testnet",
            dex="hedera_hts",
            token_a="0x" + "11" * 20,
            token_b="0x" + "22" * 20,
            amount_a="1",
            amount_b="1",
            position_type="v2",
            v3_range="100:200",
            slippage_bps=100,
            json=True,
        )
        adapter = mock.Mock()
        adapter.dex = "hedera_hts"
        adapter.protocol_family = "hedera_hts"
        adapter.quote_add.return_value = {"simulation": {"minAmountA": "0.99", "minAmountB": "0.99"}}

        with mock.patch.object(cli, "assert_chain_capability"), mock.patch.object(
            cli, "_resolve_agent_id_or_fail", return_value="agt_1"
        ), mock.patch.object(
            cli, "_resolve_token_address", side_effect=["0x" + "11" * 20, "0x" + "22" * 20]
        ), mock.patch.object(
            cli, "build_liquidity_adapter_for_request", return_value=adapter
        ), mock.patch.object(
            cli, "_api_request", return_value=(200, {"liquidityIntentId": "liq_1", "status": "approved"})
        ) as mocked_api, mock.patch.object(
            cli, "_run_liquidity_execute_inline", return_value=(0, {"ok": True, "code": "ok", "status": "filled", "txHash": "0xabc"})
        ):
            code, payload = self._run(lambda: cli.cmd_liquidity_add(args))

        self.assertEqual(code, 0)
        self.assertEqual(payload.get("adapterFamily"), "hedera_hts")
        first_call = mocked_api.call_args_list[0]
        api_payload = first_call.kwargs.get("payload")
        if not isinstance(api_payload, dict) and len(first_call.args) >= 3 and isinstance(first_call.args[2], dict):
            api_payload = first_call.args[2]
        if not isinstance(api_payload, dict):
            api_payload = {}
        self.assertEqual(api_payload.get("details", {}).get("htsNative"), True)
        self.assertIsNone(api_payload.get("details", {}).get("v3Range"))

    def test_liquidity_add_auto_executes_when_approved(self) -> None:
        args = argparse.Namespace(
            chain="base_sepolia",
            dex="aerodrome",
            token_a="USDC",
            token_b="WETH",
            amount_a="10",
            amount_b="1",
            position_type="v2",
            v3_range=None,
            slippage_bps=100,
            json=True,
        )
        adapter = mock.Mock()
        adapter.dex = "aerodrome"
        adapter.protocol_family = "amm_v2"
        adapter.quote_add.return_value = {"simulation": {"minAmountA": "9.9", "minAmountB": "0.99"}}

        with mock.patch.object(cli, "assert_chain_capability"), mock.patch.object(
            cli, "_resolve_agent_id_or_fail", return_value="agt_1"
        ), mock.patch.object(
            cli, "_resolve_token_address", side_effect=["0x" + "11" * 20, "0x" + "22" * 20]
        ), mock.patch.object(
            cli, "build_liquidity_adapter_for_request", return_value=adapter
        ), mock.patch.object(
            cli, "_api_request", return_value=(200, {"liquidityIntentId": "liq_1", "status": "approved"})
        ), mock.patch.object(
            cli, "_run_liquidity_execute_inline", return_value=(0, {"ok": True, "code": "ok", "status": "filled", "txHash": "0xabc"})
        ) as mocked_inline:
            code, payload = self._run(lambda: cli.cmd_liquidity_add(args))

        self.assertEqual(code, 0)
        self.assertEqual(payload.get("status"), "filled")
        self.assertEqual(payload.get("txHash"), "0xabc")
        self.assertTrue(mocked_inline.called)

    def test_liquidity_discover_pairs_returns_ranked_candidates(self) -> None:
        args = argparse.Namespace(
            chain="hedera_testnet",
            dex="saucerswap",
            min_reserve=1000,
            limit=2,
            scan_max=10,
            json=True,
        )
        adapter = mock.Mock()
        adapter.protocol_family = "amm_v2"

        cast_outputs = [
            "0x000000000000000000000000000000000000fAaA",  # factory
            "3",  # pair count
            "0x0000000000000000000000000000000000001000",  # pair 0
            "0x0000000000000000000000000000000000000001",  # token0
            "0x0000000000000000000000000000000000000002",  # token1
            "(500,1000,1)",  # reserve0 below threshold -> skipped
            "0x0000000000000000000000000000000000002000",  # pair 1
            "0x0000000000000000000000000000000000000003",  # token0
            "0x0000000000000000000000000000000000000004",  # token1
            "(10000,20000,1)",  # candidate
            "0x0000000000000000000000000000000000003000",  # pair 2
            "0x0000000000000000000000000000000000000005",  # token0
            "0x0000000000000000000000000000000000000006",  # token1
            "(3000,4000,1)",  # candidate
        ]

        with mock.patch.object(cli, "assert_chain_capability"), mock.patch.object(
            cli, "build_liquidity_adapter_for_request", return_value=adapter
        ), mock.patch.object(
            cli, "_require_chain_contract_address", return_value="0x0000000000000000000000000000000000004b40"
        ), mock.patch.object(
            cli, "_cast_call_stdout", side_effect=cast_outputs
        ):
            code, payload = self._run(lambda: cli.cmd_liquidity_discover_pairs(args))

        self.assertEqual(code, 0)
        self.assertEqual(payload.get("candidateCount"), 2)
        self.assertEqual(payload.get("returnedCount"), 2)
        pairs = payload.get("pairs") or []
        self.assertEqual(len(pairs), 2)
        self.assertEqual(pairs[0]["pairAddress"], "0x0000000000000000000000000000000000002000")
        self.assertEqual(pairs[1]["pairAddress"], "0x0000000000000000000000000000000000003000")

    def test_liquidity_discover_pairs_returns_no_viable_pair(self) -> None:
        args = argparse.Namespace(
            chain="hedera_testnet",
            dex="saucerswap",
            min_reserve=1000,
            limit=5,
            scan_max=10,
            json=True,
        )
        adapter = mock.Mock()
        adapter.protocol_family = "amm_v2"

        cast_outputs = [
            "0x000000000000000000000000000000000000fAaA",  # factory
            "1",  # pair count
            "0x0000000000000000000000000000000000001000",  # pair
            "0x0000000000000000000000000000000000000001",  # token0
            "0x0000000000000000000000000000000000000002",  # token1
            "(10,20,1)",  # filtered out
        ]

        with mock.patch.object(cli, "assert_chain_capability"), mock.patch.object(
            cli, "build_liquidity_adapter_for_request", return_value=adapter
        ), mock.patch.object(
            cli, "_require_chain_contract_address", return_value="0x0000000000000000000000000000000000004b40"
        ), mock.patch.object(
            cli, "_cast_call_stdout", side_effect=cast_outputs
        ):
            code, payload = self._run(lambda: cli.cmd_liquidity_discover_pairs(args))

        self.assertEqual(code, 1)
        self.assertEqual(payload.get("code"), "liquidity_no_viable_pair")

    def test_liquidity_execute_rejects_non_actionable_status(self) -> None:
        args = argparse.Namespace(intent="liq_1", chain="hedera_testnet", json=True)
        with mock.patch.object(
            cli,
            "_read_liquidity_intent",
            return_value={"liquidityIntentId": "liq_1", "status": "approval_pending", "dex": "saucerswap", "positionType": "v2", "action": "add"},
        ):
            code, payload = self._run(lambda: cli.cmd_liquidity_execute(args))
        self.assertEqual(code, 1)
        self.assertEqual(payload.get("code"), "liquidity_not_actionable")

    def test_liquidity_execute_rejects_v3_execution_family(self) -> None:
        args = argparse.Namespace(intent="liq_1", chain="base_sepolia", json=True)
        adapter = mock.Mock()
        adapter.protocol_family = "amm_v3"
        with mock.patch.object(
            cli,
            "_read_liquidity_intent",
            return_value={"liquidityIntentId": "liq_1", "status": "approved", "dex": "uniswap_v3", "positionType": "v3", "action": "add"},
        ), mock.patch.object(cli, "build_liquidity_adapter_for_request", return_value=adapter):
            code, payload = self._run(lambda: cli.cmd_liquidity_execute(args))
        self.assertEqual(code, 2)
        self.assertEqual(payload.get("code"), "unsupported_liquidity_execution_family")

    def test_liquidity_execute_v2_add_posts_transitions(self) -> None:
        args = argparse.Namespace(intent="liq_1", chain="hedera_testnet", json=True)
        adapter = mock.Mock()
        adapter.protocol_family = "amm_v2"
        with mock.patch.object(
            cli,
            "_read_liquidity_intent",
            return_value={
                "liquidityIntentId": "liq_1",
                "status": "approved",
                "dex": "saucerswap",
                "positionType": "v2",
                "action": "add",
                "tokenA": "0x" + "11" * 20,
                "tokenB": "0x" + "22" * 20,
                "amountA": "1",
                "amountB": "1",
                "slippageBps": 100,
            },
        ), mock.patch.object(
            cli, "build_liquidity_adapter_for_request", return_value=adapter
        ), mock.patch.object(
            cli, "_execute_liquidity_v2_add", return_value={"txHash": "0xabc", "positionId": "pos_1", "details": {"x": 1}}
        ), mock.patch.object(
            cli, "_wait_for_tx_receipt_success", return_value={"status": "0x1"}
        ), mock.patch.object(
            cli, "_post_liquidity_status"
        ) as mocked_post:
            code, payload = self._run(lambda: cli.cmd_liquidity_execute(args))
        self.assertEqual(code, 0)
        self.assertEqual(payload.get("status"), "filled")
        self.assertEqual(payload.get("txHash"), "0xabc")
        self.assertEqual(mocked_post.call_count, 3)
        self.assertEqual(mocked_post.call_args_list[0].args[1], "executing")
        self.assertEqual(mocked_post.call_args_list[1].args[1], "verifying")
        self.assertEqual(mocked_post.call_args_list[2].args[1], "filled")

    def test_execute_liquidity_v2_remove_allows_pair_id_fallback_without_snapshot(self) -> None:
        adapter = mock.Mock()
        adapter.protocol_family = "amm_v2"
        adapter.dex = "saucerswap"
        adapter.quote_remove.return_value = {"ok": True}
        pair = "0x" + "bb" * 20
        lp_token = "0x" + "99" * 20
        with mock.patch.object(
            cli, "build_liquidity_adapter_for_request", return_value=adapter
        ), mock.patch.object(
            cli, "_read_liquidity_position", side_effect=cli.WalletStoreError("missing position")
        ), mock.patch.object(
            cli, "_cast_call_stdout", side_effect=["0x" + "11" * 20, "0x" + "22" * 20, lp_token]
        ), mock.patch.object(
            cli, "_require_chain_contract_address", return_value="0x" + "44" * 20
        ), mock.patch.object(
            cli, "_resolve_factory_from_router", return_value="0x" + "aa" * 20
        ), mock.patch.object(
            cli, "_execution_wallet", return_value=("0x" + "33" * 20, "11" * 32)
        ), mock.patch.object(
            cli, "_estimate_remove_amount_out_min", return_value=(1, 1)
        ), mock.patch.object(
            cli, "_ensure_token_allowance", return_value=None
        ) as mocked_allowance, mock.patch.object(
            cli, "_fetch_token_balance_wei", return_value="100000"
        ), mock.patch.object(
            cli, "_cast_rpc_send_transaction", return_value="0xabc"
        ):
            out = cli._execute_liquidity_v2_remove(
                {
                    "dex": "saucerswap",
                    "positionType": "v2",
                    "positionRef": pair,
                    "amountA": "50",
                    "slippageBps": 100,
                },
                "hedera_testnet",
            )
        self.assertEqual(mocked_allowance.call_args.kwargs.get("token_address"), lp_token)
        self.assertEqual(out.get("txHash"), "0xabc")
        self.assertEqual(out.get("positionId"), pair)

    def test_liquidity_execute_hts_missing_dependency_fails_closed(self) -> None:
        args = argparse.Namespace(intent="liq_1", chain="hedera_testnet", json=True)
        adapter = mock.Mock()
        adapter.protocol_family = "hedera_hts"
        adapter.add.side_effect = HederaSdkUnavailable("plugin missing")
        with mock.patch.object(
            cli,
            "_read_liquidity_intent",
            return_value={
                "liquidityIntentId": "liq_1",
                "status": "approved",
                "dex": "hedera_hts",
                "positionType": "v2",
                "action": "add",
                "tokenA": "0x" + "11" * 20,
                "tokenB": "0x" + "22" * 20,
                "amountA": "1",
                "amountB": "1",
                "slippageBps": 100,
            },
        ), mock.patch.object(cli, "build_liquidity_adapter_for_request", return_value=adapter), mock.patch.object(
            cli, "_post_liquidity_status"
        ):
            code, payload = self._run(lambda: cli.cmd_liquidity_execute(args))
        self.assertEqual(code, 2)
        self.assertEqual(payload.get("code"), "missing_dependency")

    def test_liquidity_execute_surfaces_deterministic_preflight_reason(self) -> None:
        args = argparse.Namespace(intent="liq_1", chain="hedera_testnet", json=True)
        adapter = mock.Mock()
        adapter.protocol_family = "amm_v2"
        with mock.patch.object(
            cli,
            "_read_liquidity_intent",
            return_value={
                "liquidityIntentId": "liq_1",
                "status": "approved",
                "dex": "saucerswap",
                "positionType": "v2",
                "action": "add",
                "tokenA": "0x" + "11" * 20,
                "tokenB": "0x" + "22" * 20,
                "amountA": "1",
                "amountB": "1",
                "slippageBps": 100,
            },
        ), mock.patch.object(
            cli, "build_liquidity_adapter_for_request", return_value=adapter
        ), mock.patch.object(
            cli,
            "_execute_liquidity_v2_add",
            side_effect=cli.LiquidityExecutionError(
                "liquidity_preflight_insufficient_token_balance",
                "Insufficient token balance preflight.",
            ),
        ), mock.patch.object(
            cli, "_post_liquidity_status"
        ):
            code, payload = self._run(lambda: cli.cmd_liquidity_execute(args))
        self.assertEqual(code, 1)
        self.assertEqual(payload.get("code"), "liquidity_execution_failed")
        self.assertEqual(
            (payload.get("details") or {}).get("reasonCode"),
            "liquidity_preflight_insufficient_token_balance",
        )

    def test_preflight_transfer_probe_token_a_failure_is_deterministic(self) -> None:
        with mock.patch.object(cli, "_fetch_token_balance_wei", side_effect=["1000", "1000"]), mock.patch.object(
            cli, "_fetch_token_allowance_wei", side_effect=["1000", "1000"]
        ), mock.patch.object(
            cli, "_fetch_native_balance_wei", return_value=str(10**18)
        ), mock.patch.object(
            cli, "_resolve_factory_from_router", return_value="0x" + "aa" * 20
        ), mock.patch.object(
            cli, "_resolve_pair_from_factory", return_value="0x" + "bb" * 20
        ), mock.patch.object(
            cli, "_cast_call_stdout", return_value="(1000,1000,1)"
        ), mock.patch.object(
            cli,
            "_probe_transfer_from_eth_call",
            side_effect=[
                {"ok": False, "kind": "revert", "token": "0x" + "11" * 20, "error": "transfer blocked"},
            ],
        ):
            with self.assertRaises(cli.LiquidityExecutionError) as ctx:
                cli._preflight_liquidity_v2_add_execution(
                    chain="hedera_testnet",
                    token_a="0x" + "11" * 20,
                    token_b="0x" + "22" * 20,
                    amount_a_units=10,
                    amount_b_units=10,
                    min_a_units=1,
                    min_b_units=1,
                    wallet_address="0x" + "33" * 20,
                    router="0x" + "44" * 20,
                    deadline="9999999999",
                )
        self.assertEqual(ctx.exception.reason_code, "liquidity_preflight_token_transfer_blocked_token_a")
        self.assertIn("tokenProbeA", ctx.exception.details)
        self.assertEqual((ctx.exception.details.get("tokenProbeA") or {}).get("kind"), "revert")

    def test_preflight_transfer_probe_token_b_failure_is_deterministic(self) -> None:
        with mock.patch.object(cli, "_fetch_token_balance_wei", side_effect=["1000", "1000"]), mock.patch.object(
            cli, "_fetch_token_allowance_wei", side_effect=["1000", "1000"]
        ), mock.patch.object(
            cli, "_fetch_native_balance_wei", return_value=str(10**18)
        ), mock.patch.object(
            cli, "_resolve_factory_from_router", return_value="0x" + "aa" * 20
        ), mock.patch.object(
            cli, "_resolve_pair_from_factory", return_value="0x" + "bb" * 20
        ), mock.patch.object(
            cli, "_cast_call_stdout", return_value="(1000,1000,1)"
        ), mock.patch.object(
            cli,
            "_probe_transfer_from_eth_call",
            side_effect=[
                {"ok": True, "kind": "ok"},
                {"ok": False, "kind": "return_false", "token": "0x" + "22" * 20},
            ],
        ):
            with self.assertRaises(cli.LiquidityExecutionError) as ctx:
                cli._preflight_liquidity_v2_add_execution(
                    chain="hedera_testnet",
                    token_a="0x" + "11" * 20,
                    token_b="0x" + "22" * 20,
                    amount_a_units=10,
                    amount_b_units=10,
                    min_a_units=1,
                    min_b_units=1,
                    wallet_address="0x" + "33" * 20,
                    router="0x" + "44" * 20,
                    deadline="9999999999",
                )
        self.assertEqual(ctx.exception.reason_code, "liquidity_preflight_token_transfer_blocked_token_b")
        self.assertEqual((ctx.exception.details.get("tokenProbeB") or {}).get("kind"), "return_false")

    def test_preflight_transfer_probe_falls_back_when_rpc_forbidden(self) -> None:
        with mock.patch.object(cli, "_fetch_token_balance_wei", side_effect=["1000", "1000"]), mock.patch.object(
            cli, "_fetch_token_allowance_wei", side_effect=["1000", "1000"]
        ), mock.patch.object(
            cli, "_fetch_native_balance_wei", return_value=str(10**18)
        ), mock.patch.object(
            cli, "_resolve_factory_from_router", return_value="0x" + "aa" * 20
        ), mock.patch.object(
            cli, "_resolve_pair_from_factory", return_value="0x" + "bb" * 20
        ), mock.patch.object(
            cli, "_cast_call_stdout", side_effect=["(1000,1000,1)", "0x1"]
        ), mock.patch.object(
            cli,
            "_probe_transfer_from_eth_call",
            side_effect=[
                {"ok": False, "kind": "rpc_forbidden", "error": "403"},
                {"ok": False, "kind": "rpc_forbidden", "error": "403"},
            ],
        ), mock.patch.object(
            cli,
            "_probe_transfer_eth_call",
            side_effect=[{"ok": True, "kind": "ok"}, {"ok": True, "kind": "ok"}],
        ):
            details = cli._preflight_liquidity_v2_add_execution(
                chain="hedera_testnet",
                token_a="0x" + "11" * 20,
                token_b="0x" + "22" * 20,
                amount_a_units=10,
                amount_b_units=10,
                min_a_units=1,
                min_b_units=1,
                wallet_address="0x" + "33" * 20,
                router="0x" + "44" * 20,
                deadline="9999999999",
            )
        self.assertEqual((details.get("tokenProbeA") or {}).get("kind"), "rpc_forbidden_fallback_transfer_ok")
        self.assertEqual((details.get("tokenProbeB") or {}).get("kind"), "rpc_forbidden_fallback_transfer_ok")

    def test_preflight_transfer_probe_forbidden_unverifiable_does_not_block(self) -> None:
        with mock.patch.object(cli, "_fetch_token_balance_wei", side_effect=["1000", "1000"]), mock.patch.object(
            cli, "_fetch_token_allowance_wei", side_effect=["1000", "1000"]
        ), mock.patch.object(
            cli, "_fetch_native_balance_wei", return_value=str(10**18)
        ), mock.patch.object(
            cli, "_resolve_factory_from_router", return_value="0x" + "aa" * 20
        ), mock.patch.object(
            cli, "_resolve_pair_from_factory", return_value="0x" + "bb" * 20
        ), mock.patch.object(
            cli, "_cast_call_stdout", side_effect=["(1000,1000,1)", "0x1"]
        ), mock.patch.object(
            cli,
            "_probe_transfer_from_eth_call",
            side_effect=[
                {"ok": False, "kind": "rpc_forbidden", "error": "HTTP Error 403"},
                {"ok": False, "kind": "rpc_forbidden", "error": "HTTP Error 403"},
            ],
        ), mock.patch.object(
            cli,
            "_probe_transfer_eth_call",
            side_effect=[
                {"ok": False, "kind": "revert", "error": "HTTP Error 403"},
                {"ok": False, "kind": "revert", "error": "HTTP Error 403"},
            ],
        ):
            details = cli._preflight_liquidity_v2_add_execution(
                chain="hedera_testnet",
                token_a="0x" + "11" * 20,
                token_b="0x" + "22" * 20,
                amount_a_units=10,
                amount_b_units=10,
                min_a_units=1,
                min_b_units=1,
                wallet_address="0x" + "33" * 20,
                router="0x" + "44" * 20,
                deadline="9999999999",
            )
        self.assertEqual((details.get("tokenProbeA") or {}).get("kind"), "rpc_forbidden_unverifiable")
        self.assertEqual((details.get("tokenProbeB") or {}).get("kind"), "rpc_forbidden_unverifiable")

    def test_preflight_hedera_simulation_bypass_enabled(self) -> None:
        sim_err = cli.WalletStoreError("execution reverted: Safe token transfer failed!")
        with mock.patch.object(cli, "_fetch_token_balance_wei", side_effect=["1000", "1000"]), mock.patch.object(
            cli, "_fetch_token_allowance_wei", side_effect=["1000", "1000"]
        ), mock.patch.object(
            cli, "_fetch_native_balance_wei", return_value=str(10**18)
        ), mock.patch.object(
            cli, "_resolve_factory_from_router", return_value="0x" + "aa" * 20
        ), mock.patch.object(
            cli, "_resolve_pair_from_factory", return_value="0x" + "bb" * 20
        ), mock.patch.object(
            cli, "_cast_call_stdout", side_effect=["(1000,1000,1)", sim_err]
        ), mock.patch.object(
            cli,
            "_probe_transfer_from_eth_call",
            side_effect=[{"ok": True, "kind": "ok"}, {"ok": True, "kind": "ok"}],
        ), mock.patch.dict(
            cli.os.environ,
            {"XCLAW_LIQUIDITY_ALLOW_SIMULATION_BYPASS": "1"},
            clear=False,
        ):
            details = cli._preflight_liquidity_v2_add_execution(
                chain="hedera_testnet",
                token_a="0x" + "11" * 20,
                token_b="0x" + "22" * 20,
                amount_a_units=10,
                amount_b_units=10,
                min_a_units=1,
                min_b_units=1,
                wallet_address="0x" + "33" * 20,
                router="0x" + "44" * 20,
                deadline="9999999999",
            )
        self.assertEqual((details.get("simulationWarning") or {}).get("code"), "liquidity_preflight_router_revert_bypassed")

    def test_preflight_hedera_simulation_bypass_disabled_raises(self) -> None:
        sim_err = cli.WalletStoreError("execution reverted: Safe token transfer failed!")
        with mock.patch.object(cli, "_fetch_token_balance_wei", side_effect=["1000", "1000"]), mock.patch.object(
            cli, "_fetch_token_allowance_wei", side_effect=["1000", "1000"]
        ), mock.patch.object(
            cli, "_fetch_native_balance_wei", return_value=str(10**18)
        ), mock.patch.object(
            cli, "_resolve_factory_from_router", return_value="0x" + "aa" * 20
        ), mock.patch.object(
            cli, "_resolve_pair_from_factory", return_value="0x" + "bb" * 20
        ), mock.patch.object(
            cli, "_cast_call_stdout", side_effect=["(1000,1000,1)", sim_err]
        ), mock.patch.object(
            cli,
            "_probe_transfer_from_eth_call",
            side_effect=[{"ok": True, "kind": "ok"}, {"ok": True, "kind": "ok"}],
        ), mock.patch.dict(
            cli.os.environ,
            {"XCLAW_LIQUIDITY_ALLOW_SIMULATION_BYPASS": "0"},
            clear=False,
        ):
            with self.assertRaises(cli.LiquidityExecutionError) as ctx:
                cli._preflight_liquidity_v2_add_execution(
                    chain="hedera_testnet",
                    token_a="0x" + "11" * 20,
                    token_b="0x" + "22" * 20,
                    amount_a_units=10,
                    amount_b_units=10,
                    min_a_units=1,
                    min_b_units=1,
                    wallet_address="0x" + "33" * 20,
                    router="0x" + "44" * 20,
                    deadline="9999999999",
                )
        self.assertEqual(ctx.exception.reason_code, "liquidity_preflight_router_revert")

    def test_resolve_token_address_applies_chain_alias_mapping(self) -> None:
        with mock.patch.object(
            cli,
            "_canonical_token_address_aliases",
            return_value={"0x" + "11" * 20: "0x" + "22" * 20},
        ):
            resolved = cli._resolve_token_address("hedera_testnet", "0x" + "11" * 20)
        self.assertEqual(resolved.lower(), "0x" + "22" * 20)

    def test_hedera_hts_readiness_reports_missing_components(self) -> None:
        missing_run = mock.Mock(returncode=1, stdout="", stderr="missing")
        with mock.patch.object(cli.shutil, "which", side_effect=[None, None]), mock.patch.object(
            cli.subprocess, "run", return_value=missing_run
        ):
            readiness = cli._hedera_hts_readiness()
        self.assertEqual(readiness.get("ready"), False)
        missing = readiness.get("missing") or []
        self.assertIn("java", missing)
        self.assertIn("javac", missing)
        self.assertIn("hedera_sdk_py", missing)


if __name__ == "__main__":
    unittest.main()
