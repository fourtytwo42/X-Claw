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
from xclaw_agent.liquidity_adapter import HederaSdkUnavailable, LiquidityAdapter, HederaHtsLiquidityAdapter  # noqa: E402


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

    def test_quote_add_ethereum_sepolia_uniswap_alias_resolves(self) -> None:
        args = argparse.Namespace(
            chain="ethereum_sepolia",
            dex="uniswap",
            token_a="WETH",
            token_b="USDC",
            amount_a="0.1",
            amount_b="300",
            position_type="v2",
            slippage_bps=100,
            json=True,
        )
        token_meta = {"symbol": "TOK", "decimals": 18}
        with mock.patch.object(cli, "assert_chain_capability"), mock.patch.object(
            cli, "_resolve_token_address", side_effect=["0x" + "11" * 20, "0x" + "22" * 20]
        ), mock.patch.object(
            cli, "_fetch_erc20_metadata", side_effect=[token_meta, token_meta]
        ), mock.patch.object(
            cli, "_router_get_amount_out", return_value=10**18
        ):
            code, payload = self._run(lambda: cli.cmd_liquidity_quote_add(args))

        self.assertEqual(code, 0)
        self.assertEqual(payload.get("adapterFamily"), "amm_v2")
        self.assertEqual(payload.get("dex"), "uniswap")

    def test_quote_add_ethereum_sepolia_unknown_dex_rejected(self) -> None:
        args = argparse.Namespace(
            chain="ethereum_sepolia",
            dex="uniswapx",
            token_a="WETH",
            token_b="USDC",
            amount_a="0.1",
            amount_b="300",
            position_type="v2",
            slippage_bps=100,
            json=True,
        )
        with mock.patch.object(cli, "assert_chain_capability"):
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

    def test_approvals_decide_liquidity_converges_when_missing_from_pending_scope(self) -> None:
        args = argparse.Namespace(
            intent_id="liq_1",
            decision="approve",
            reason_message="",
            source="telegram",
            chain="hedera_testnet",
            json=True,
        )

        with mock.patch.object(
            cli,
            "_read_liquidity_intent",
            side_effect=cli.WalletStoreError("Liquidity intent 'liq_1' was not found in pending scope for chain 'hedera_testnet'."),
        ):
            code, payload = self._run(lambda: cli.cmd_approvals_decide_liquidity(args))

        self.assertEqual(code, 0)
        self.assertTrue(payload.get("ok"))
        self.assertEqual(payload.get("subjectType"), "liquidity")
        self.assertEqual(payload.get("subjectId"), "liq_1")
        self.assertEqual(payload.get("status"), "converged_unknown")
        self.assertTrue(payload.get("converged"))

    def test_approvals_decide_liquidity_missing_pending_scope_non_telegram_fails(self) -> None:
        args = argparse.Namespace(
            intent_id="liq_1",
            decision="approve",
            reason_message="",
            source="web",
            chain="hedera_testnet",
            json=True,
        )

        with mock.patch.object(
            cli,
            "_read_liquidity_intent",
            side_effect=cli.WalletStoreError("Liquidity intent 'liq_1' was not found in pending scope for chain 'hedera_testnet'."),
        ):
            code, payload = self._run(lambda: cli.cmd_approvals_decide_liquidity(args))

        self.assertEqual(code, 1)
        self.assertFalse(payload.get("ok"))
        self.assertEqual(payload.get("code"), "liquidity_decision_failed")

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

    def test_estimate_add_amount_in_with_min_uses_pool_ratio(self) -> None:
        amount_a, amount_b, min_a, min_b = cli._estimate_add_amount_in_with_min(
            reserve_a=1_000,
            reserve_b=2_000,
            desired_a=100,
            desired_b=250,
            slippage_bps=100,
        )
        self.assertEqual(amount_a, 100)
        self.assertEqual(amount_b, 200)
        self.assertEqual(min_a, 99)
        self.assertEqual(min_b, 198)

    def test_estimate_add_amount_in_with_min_falls_back_when_optimal_rounds_zero(self) -> None:
        amount_a, amount_b, min_a, min_b = cli._estimate_add_amount_in_with_min(
            reserve_a=1_000_000_000,
            reserve_b=1,
            desired_a=10,
            desired_b=100,
            slippage_bps=100,
        )
        self.assertEqual(amount_a, 10)
        self.assertEqual(amount_b, 100)
        self.assertEqual(min_a, 9)
        self.assertEqual(min_b, 99)

    def test_execute_liquidity_v2_add_approves_desired_max_units(self) -> None:
        adapter = mock.Mock()
        adapter.protocol_family = "amm_v2"
        adapter.dex = "uniswap_v2"
        adapter.quote_add.return_value = {"ok": True}

        with mock.patch.object(
            cli, "build_liquidity_adapter_for_request", return_value=adapter
        ), mock.patch.object(
            cli, "_resolve_token_address", side_effect=["0x" + "11" * 20, "0x" + "22" * 20]
        ), mock.patch.object(
            cli, "_fetch_erc20_metadata", side_effect=[{"decimals": 6}, {"decimals": 6}]
        ), mock.patch.object(
            cli, "_to_units_uint", side_effect=["100", "200"]
        ), mock.patch.object(
            cli, "_require_chain_contract_address", return_value="0x" + "44" * 20
        ), mock.patch.object(
            cli, "_resolve_factory_from_router", return_value="0x" + "55" * 20
        ), mock.patch.object(
            cli, "_resolve_pair_from_factory", return_value="0x" + "66" * 20
        ), mock.patch.object(
            cli, "_cast_call_stdout", side_effect=["0x" + "11" * 20, "(1000,1000,1)"]
        ), mock.patch.object(
            cli, "_estimate_add_amount_in_with_min", return_value=(80, 150, 79, 149)
        ), mock.patch.object(
            cli, "load_wallet_store", return_value=object()
        ), mock.patch.object(
            cli, "_execution_wallet", return_value=("0x" + "33" * 20, "11" * 32)
        ), mock.patch.object(
            cli, "_ensure_token_allowance", return_value=None
        ) as mocked_allowance, mock.patch.object(
            cli, "_preflight_liquidity_v2_add_execution", return_value={}
        ), mock.patch.object(
            cli, "_cast_calldata", return_value="0xdeadbeef"
        ), mock.patch.object(
            cli, "_cast_rpc_send_transaction", return_value="0xabc"
        ):
            out = cli._execute_liquidity_v2_add(
                {
                    "dex": "uniswap_v2",
                    "positionType": "v2",
                    "tokenA": "USDC",
                    "tokenB": "WETH",
                    "amountA": "100",
                    "amountB": "200",
                    "slippageBps": 100,
                },
                "ethereum_sepolia",
            )

        self.assertEqual(mocked_allowance.call_count, 2)
        first_required = mocked_allowance.call_args_list[0].kwargs.get("required_units")
        second_required = mocked_allowance.call_args_list[1].kwargs.get("required_units")
        self.assertEqual(first_required, 100)
        self.assertEqual(second_required, 200)
        self.assertEqual(out.get("txHash"), "0xabc")

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

    def test_execute_liquidity_v2_remove_zero_lp_balance_is_deterministic(self) -> None:
        adapter = mock.Mock()
        adapter.protocol_family = "amm_v2"
        adapter.dex = "saucerswap"
        adapter.quote_remove.return_value = {"ok": True}
        with mock.patch.object(
            cli, "build_liquidity_adapter_for_request", return_value=adapter
        ), mock.patch.object(
            cli,
            "_read_liquidity_position",
            return_value={"tokenA": "0x" + "11" * 20, "tokenB": "0x" + "22" * 20},
        ), mock.patch.object(
            cli, "_resolve_token_address", side_effect=lambda _chain, token: token
        ), mock.patch.object(
            cli, "_require_chain_contract_address", return_value="0x" + "44" * 20
        ), mock.patch.object(
            cli,
            "_compute_v2_remove_liquidity_units",
            return_value={
                "pair": "0x" + "bb" * 20,
                "lpToken": "0x" + "99" * 20,
                "walletAddress": "0x" + "33" * 20,
                "lpBalance": 0,
                "liquidityUnits": 0,
            },
        ), mock.patch.object(
            cli, "_execution_wallet", return_value=("0x" + "33" * 20, "11" * 32)
        ):
            with self.assertRaises(cli.LiquidityExecutionError) as ctx:
                cli._execute_liquidity_v2_remove(
                    {
                        "dex": "saucerswap",
                        "positionType": "v2",
                        "positionRef": "0x" + "aa" * 20,
                        "amountA": "100",
                        "slippageBps": 100,
                    },
                    "hedera_testnet",
                )
        self.assertEqual(ctx.exception.reason_code, "liquidity_preflight_zero_lp_balance")
        self.assertEqual((ctx.exception.details or {}).get("lpBalance"), "0")

    def test_liquidity_remove_blocks_zero_lp_balance_before_proposal(self) -> None:
        args = argparse.Namespace(
            chain="hedera_testnet",
            dex="saucerswap",
            position_id="0x" + "aa" * 20,
            token_a="",
            token_b="",
            percent=100,
            slippage_bps=100,
            position_type="v2",
            json=True,
        )
        adapter = mock.Mock()
        adapter.dex = "saucerswap"
        adapter.protocol_family = "amm_v2"
        adapter.quote_remove.return_value = {"simulation": {"minAmountA": "1", "minAmountB": "1"}}
        with mock.patch.object(cli, "assert_chain_capability"), mock.patch.object(
            cli, "build_liquidity_adapter_for_request", return_value=adapter
        ), mock.patch.object(
            cli, "_liquidity_provider_settings", return_value=("legacy_router", {"provider": "legacy_router"})
        ), mock.patch.object(
            cli, "_resolve_agent_id_or_fail", return_value="agt_1"
        ), mock.patch.object(
            cli, "_resolve_liquidity_remove_tokens", return_value=("0x" + "11" * 20, "0x" + "22" * 20)
        ), mock.patch.object(
            cli, "_token_symbol_for_display", side_effect=["USDC", "SAUCE"]
        ), mock.patch.object(
            cli,
            "_compute_v2_remove_liquidity_units",
            return_value={
                "pair": "0x" + "bb" * 20,
                "lpToken": "0x" + "99" * 20,
                "walletAddress": "0x" + "33" * 20,
                "lpBalance": 0,
                "liquidityUnits": 0,
            },
        ), mock.patch.object(
            cli, "_api_request"
        ) as mocked_api:
            code, payload = self._run(lambda: cli.cmd_liquidity_remove(args))
        self.assertEqual(code, 1)
        self.assertEqual(payload.get("code"), "liquidity_preflight_zero_lp_balance")
        self.assertEqual((payload.get("details") or {}).get("lpBalance"), "0")
        mocked_api.assert_not_called()

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

    def test_preflight_router_transferfrom_revert_maps_specific_reason_code(self) -> None:
        sim_err = cli.WalletStoreError("execution reverted: TransferHelper::transferFrom: transferFrom failed")
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
        ):
            with self.assertRaises(cli.LiquidityExecutionError) as ctx:
                cli._preflight_liquidity_v2_add_execution(
                    chain="ethereum_sepolia",
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
        self.assertEqual(ctx.exception.reason_code, "liquidity_preflight_router_transfer_from_failed")

    def test_preflight_router_transferfrom_revert_retries_alternate_rpc_when_probes_unverifiable(self) -> None:
        sim_err = cli.WalletStoreError("execution reverted: TransferHelper::transferFrom: transferFrom failed")
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
            cli, "_chain_rpc_candidates", return_value=["https://rpc-1", "https://rpc-2"]
        ), mock.patch.object(
            cli,
            "_cast_call_stdout_with_rpc",
            side_effect=[sim_err, "(10,10,10)"],
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
                chain="ethereum_sepolia",
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
        self.assertEqual(
            (details.get("simulationWarning") or {}).get("code"),
            "liquidity_preflight_router_transfer_from_retry_success",
        )

    def test_preflight_sepolia_transferfrom_unverifiable_bypass_enabled(self) -> None:
        sim_err = cli.WalletStoreError("execution reverted: TransferHelper::transferFrom: transferFrom failed")
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
            cli, "_chain_rpc_candidates", return_value=["https://rpc-1"]
        ), mock.patch.object(
            cli,
            "_cast_call_stdout_with_rpc",
            side_effect=[sim_err],
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
        ), mock.patch.dict(
            cli.os.environ,
            {"XCLAW_LIQUIDITY_ALLOW_SEPOLIA_TRANSFERFROM_BYPASS": "1"},
            clear=False,
        ):
            details = cli._preflight_liquidity_v2_add_execution(
                chain="ethereum_sepolia",
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
        self.assertEqual(
            (details.get("simulationWarning") or {}).get("code"),
            "liquidity_preflight_router_transfer_from_unverifiable_bypassed",
        )

    def test_preflight_sepolia_transferfrom_unverifiable_bypass_disabled_raises(self) -> None:
        sim_err = cli.WalletStoreError("execution reverted: TransferHelper::transferFrom: transferFrom failed")
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
            cli, "_chain_rpc_candidates", return_value=["https://rpc-1"]
        ), mock.patch.object(
            cli,
            "_cast_call_stdout_with_rpc",
            side_effect=[sim_err],
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
        ), mock.patch.dict(
            cli.os.environ,
            {"XCLAW_LIQUIDITY_ALLOW_SEPOLIA_TRANSFERFROM_BYPASS": "0"},
            clear=False,
        ):
            with self.assertRaises(cli.LiquidityExecutionError) as ctx:
                cli._preflight_liquidity_v2_add_execution(
                    chain="ethereum_sepolia",
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
        self.assertEqual(ctx.exception.reason_code, "liquidity_preflight_router_transfer_from_failed")

    def test_preflight_hedera_simulation_bypass_auto_when_probes_unverifiable(self) -> None:
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
        ), mock.patch.dict(
            cli.os.environ,
            {"XCLAW_LIQUIDITY_ALLOW_SIMULATION_BYPASS": "0"},
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

    def test_resolve_token_address_applies_chain_alias_mapping(self) -> None:
        with mock.patch.object(
            cli,
            "_canonical_token_address_aliases",
            return_value={"0x" + "11" * 20: "0x" + "22" * 20},
        ):
            resolved = cli._resolve_token_address("hedera_testnet", "0x" + "11" * 20)
        self.assertEqual(resolved.lower(), "0x" + "22" * 20)

    def test_resolve_liquidity_remove_tokens_falls_back_to_pair_contract_when_snapshot_has_placeholders(self) -> None:
        position_id = "0x" + "aa" * 20
        with mock.patch.object(
            cli,
            "_read_liquidity_position",
            return_value={"tokenA": "POSITION", "tokenB": "POSITION"},
        ), mock.patch.object(
            cli,
            "_resolve_pair_tokens_from_contract",
            return_value=("0x" + "11" * 20, "0x" + "22" * 20),
        ), mock.patch.object(
            cli,
            "_resolve_token_address",
            side_effect=lambda _chain, token: str(token),
        ):
            token_a, token_b = cli._resolve_liquidity_remove_tokens("hedera_testnet", position_id, "", "")
        self.assertEqual(token_a, "0x" + "11" * 20)
        self.assertEqual(token_b, "0x" + "22" * 20)

    def test_liquidity_remove_pending_message_uses_resolved_pair_symbols(self) -> None:
        args = argparse.Namespace(
            chain="hedera_testnet",
            dex="saucerswap",
            position_id="0x" + "aa" * 20,
            percent=100,
            slippage_bps=100,
            position_type="v2",
            token_a=None,
            token_b=None,
            json=True,
        )
        with mock.patch.object(cli, "assert_chain_capability"), mock.patch.object(
            cli, "_liquidity_provider_settings", return_value=("legacy_router", "legacy_router")
        ), mock.patch.object(
            cli, "build_liquidity_adapter_for_request"
        ) as mocked_adapter_builder, mock.patch.object(
            cli, "_resolve_agent_id_or_fail", return_value="agt_1"
        ), mock.patch.object(
            cli,
            "_resolve_liquidity_remove_tokens",
            return_value=("0x" + "11" * 20, "0x" + "22" * 20),
        ), mock.patch.object(
            cli,
            "_token_symbol_for_display",
            side_effect=lambda _chain, token: "USDC" if str(token).endswith("11" * 20) else "SAUCE",
        ), mock.patch.object(
            cli,
            "_compute_v2_remove_liquidity_units",
            return_value={
                "pair": "0x" + "bb" * 20,
                "lpToken": "0x" + "99" * 20,
                "walletAddress": "0x" + "33" * 20,
                "lpBalance": 100000,
                "liquidityUnits": 100000,
            },
        ), mock.patch.object(
            cli,
            "_api_request",
            return_value=(200, {"liquidityIntentId": "liq_1", "status": "approval_pending"}),
        ), mock.patch.object(
            cli,
            "_maybe_send_telegram_liquidity_approval_prompt",
        ):
            mocked_adapter = mock.Mock()
            mocked_adapter.dex = "saucerswap"
            mocked_adapter.protocol_family = "amm_v2"
            mocked_adapter.quote_remove.return_value = {"simulation": {}}
            mocked_adapter_builder.return_value = mocked_adapter
            code, payload = self._run(lambda: cli.cmd_liquidity_remove(args))

        self.assertEqual(code, 1)
        self.assertEqual(payload.get("code"), "approval_required")
        details = payload.get("details") or {}
        queued = str(details.get("queuedMessage") or "")
        self.assertIn("Pair: USDC/SAUCE", queued)

    def test_resolve_liquidity_remove_tokens_uses_snapshot_pool_when_position_id_not_pair(self) -> None:
        position_id = "0x" + "aa" * 32
        pool = "0x" + "bb" * 20
        with mock.patch.object(
            cli,
            "_read_liquidity_position",
            return_value={"tokenA": "POSITION", "tokenB": "POSITION", "pool": pool},
        ), mock.patch.object(
            cli,
            "_resolve_pair_tokens_from_contract",
            return_value=("0x" + "11" * 20, "0x" + "22" * 20),
        ), mock.patch.object(
            cli,
            "_resolve_token_address",
            side_effect=lambda _chain, token: str(token),
        ):
            token_a, token_b = cli._resolve_liquidity_remove_tokens("hedera_testnet", position_id, "", "")
        self.assertEqual(token_a, "0x" + "11" * 20)
        self.assertEqual(token_b, "0x" + "22" * 20)

    def test_liquidity_positions_normalizes_placeholder_pair_with_pool_symbols(self) -> None:
        args = argparse.Namespace(chain="hedera_testnet", dex=None, status=None, json=True)
        with mock.patch.object(cli, "assert_chain_capability"), mock.patch.object(
            cli, "_resolve_agent_id_or_fail", return_value="agt_1"
        ), mock.patch.object(
            cli,
            "_api_request",
            return_value=(
                200,
                {
                    "items": [
                        {
                            "positionId": "0x" + "aa" * 32,
                            "pool": "0x" + "bb" * 20,
                            "tokenA": "POSITION",
                            "tokenB": "POSITION",
                            "dex": "saucerswap",
                            "status": "active",
                        }
                    ]
                },
            ),
        ), mock.patch.object(
            cli,
            "_resolve_pair_tokens_from_contract",
            return_value=("0x" + "11" * 20, "0x" + "22" * 20),
        ), mock.patch.object(
            cli,
            "_token_symbol_for_display",
            side_effect=lambda _chain, token: "USDC" if str(token).endswith("11" * 20) else "SAUCE",
        ):
            code, payload = self._run(lambda: cli.cmd_liquidity_positions(args))

        self.assertEqual(code, 0)
        positions = payload.get("positions") or []
        self.assertEqual(len(positions), 1)
        row = positions[0]
        self.assertEqual(row.get("tokenASymbol"), "USDC")
        self.assertEqual(row.get("tokenBSymbol"), "SAUCE")
        self.assertEqual(row.get("pairDisplay"), "USDC/SAUCE")

    def test_liquidity_positions_open_status_alias_maps_to_active(self) -> None:
        args = argparse.Namespace(chain="hedera_testnet", dex=None, status="open", json=True)
        with mock.patch.object(cli, "assert_chain_capability"), mock.patch.object(
            cli, "_resolve_agent_id_or_fail", return_value="agt_1"
        ), mock.patch.object(
            cli,
            "_api_request",
            return_value=(
                200,
                {
                    "items": [
                        {"positionId": "p1", "dex": "saucerswap", "status": "active", "tokenA": "USDC", "tokenB": "SAUCE"},
                        {"positionId": "p2", "dex": "saucerswap", "status": "closed", "tokenA": "USDC", "tokenB": "SAUCE"},
                    ]
                },
            ),
        ), mock.patch.object(
            cli, "_token_symbol_for_display", side_effect=lambda _chain, token: str(token)
        ):
            code, payload = self._run(lambda: cli.cmd_liquidity_positions(args))
        self.assertEqual(code, 0)
        self.assertEqual(payload.get("status"), "active")
        self.assertEqual(payload.get("count"), 1)

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

    def test_hedera_hts_readiness_uses_default_bridge_source(self) -> None:
        ok_run = mock.Mock(returncode=0, stdout="1", stderr="")
        with mock.patch.object(cli.shutil, "which", side_effect=["/usr/bin/java", "/usr/bin/javac"]), mock.patch.object(
            cli.subprocess, "run", return_value=ok_run
        ), mock.patch.object(cli.pathlib.Path, "exists", return_value=True), mock.patch.dict(
            cli.os.environ, {"XCLAW_HEDERA_HTS_BRIDGE_CMD": ""}, clear=False
        ):
            readiness = cli._hedera_hts_readiness()
        checks = readiness.get("checks") or {}
        self.assertEqual(checks.get("bridgeCommandSource"), "default")
        self.assertEqual(checks.get("bridgeCommandConfigured"), True)

    def test_liquidity_migrate_success_uniswap(self) -> None:
        args = argparse.Namespace(
            chain="ethereum_sepolia",
            dex="uniswap_v3",
            position_id="123",
            from_protocol="V3",
            to_protocol="V4",
            slippage_bps=100,
            request_json="",
            json=True,
        )
        with mock.patch.object(cli, "assert_chain_capability"), mock.patch.object(
            cli, "_uniswap_lp_operation_enabled", return_value=True
        ), mock.patch.object(
            cli, "_liquidity_provider_settings", return_value=("uniswap_api", "legacy_router")
        ), mock.patch.object(
            cli, "load_wallet_store", return_value={}
        ), mock.patch.object(
            cli, "_execution_wallet", return_value=("0x" + "11" * 20, "0x" + "22" * 32)
        ), mock.patch.object(
            cli, "_uniswap_lp_call_via_proxy", return_value={"transactions": [{"to": "0x" + "33" * 20, "data": "0xdead", "value": "0"}]}
        ), mock.patch.object(
            cli, "_execute_uniswap_lp_transactions", return_value=["0x" + "ab" * 32]
        ):
            code, payload = self._run(lambda: cli.cmd_liquidity_migrate(args))
        self.assertEqual(code, 0)
        self.assertEqual(payload.get("providerUsed"), "uniswap_api")
        self.assertEqual(payload.get("uniswapLpOperation"), "migrate")

    def test_liquidity_migrate_not_enabled_on_chain(self) -> None:
        args = argparse.Namespace(
            chain="base_mainnet",
            dex="uniswap_v3",
            position_id="123",
            from_protocol="V3",
            to_protocol="V4",
            slippage_bps=100,
            request_json="",
            json=True,
        )
        with mock.patch.object(cli, "assert_chain_capability"), mock.patch.object(
            cli, "_uniswap_lp_operation_enabled", return_value=False
        ):
            code, payload = self._run(lambda: cli.cmd_liquidity_migrate(args))
        self.assertEqual(code, 2)
        self.assertEqual(payload.get("code"), "uniswap_migrate_not_supported_on_chain")

    def test_liquidity_claim_rewards_success_uniswap(self) -> None:
        args = argparse.Namespace(
            chain="ethereum_sepolia",
            dex="uniswap_v3",
            position_id="123",
            reward_token="USDC",
            request_json="",
            json=True,
        )
        with mock.patch.object(cli, "assert_chain_capability"), mock.patch.object(
            cli, "_uniswap_lp_operation_enabled", return_value=True
        ), mock.patch.object(
            cli, "_liquidity_provider_settings", return_value=("uniswap_api", "legacy_router")
        ), mock.patch.object(
            cli, "load_wallet_store", return_value={}
        ), mock.patch.object(
            cli, "_execution_wallet", return_value=("0x" + "11" * 20, "0x" + "22" * 32)
        ), mock.patch.object(
            cli, "_resolve_token_address", return_value="0x" + "44" * 20
        ), mock.patch.object(
            cli, "_uniswap_lp_call_via_proxy", return_value={"transactions": [{"to": "0x" + "33" * 20, "data": "0xdead", "value": "0"}]}
        ), mock.patch.object(
            cli, "_execute_uniswap_lp_transactions", return_value=["0x" + "ab" * 32]
        ):
            code, payload = self._run(lambda: cli.cmd_liquidity_claim_rewards(args))
        self.assertEqual(code, 0)
        self.assertEqual(payload.get("providerUsed"), "uniswap_api")
        self.assertEqual(payload.get("uniswapLpOperation"), "claim_rewards")

    def test_liquidity_claim_fees_falls_back_to_legacy_when_uniswap_fails(self) -> None:
        args = argparse.Namespace(
            chain="ethereum_sepolia",
            dex="uniswap_v3",
            position_id="123",
            collect_as_weth=False,
            json=True,
        )
        with mock.patch.object(cli, "assert_chain_capability"), mock.patch.object(
            cli, "_liquidity_provider_settings", return_value=("uniswap_api", "legacy_router")
        ), mock.patch.object(
            cli, "load_wallet_store", return_value={}
        ), mock.patch.object(
            cli, "_execution_wallet", return_value=("0x" + "11" * 20, "0x" + "22" * 32)
        ), mock.patch.object(
            cli, "_uniswap_lp_call_via_proxy", side_effect=RuntimeError("upstream down")
        ), mock.patch.object(
            cli, "_legacy_liquidity_operation_available", return_value=True
        ), mock.patch.object(
            cli, "_execute_legacy_liquidity_operation", return_value={"txHash": "0x" + "aa" * 32}
        ):
            code, payload = self._run(lambda: cli.cmd_liquidity_claim_fees(args))
        self.assertEqual(code, 0)
        self.assertEqual(payload.get("providerUsed"), "legacy_router")
        self.assertEqual(payload.get("fallbackUsed"), True)

    def test_liquidity_claim_fees_non_uniswap_unsupported(self) -> None:
        args = argparse.Namespace(
            chain="base_sepolia",
            dex="aerodrome",
            position_id="123",
            collect_as_weth=False,
            json=True,
        )
        with mock.patch.object(cli, "assert_chain_capability"), mock.patch.object(
            cli, "_liquidity_provider_settings", return_value=("legacy_router", "legacy_router")
        ), mock.patch.object(
            cli,
            "_execute_legacy_liquidity_operation",
            side_effect=cli.WalletStoreError("claim_fees_not_supported_for_protocol: legacy claim-fees is not enabled for this chain."),
        ):
            code, payload = self._run(lambda: cli.cmd_liquidity_claim_fees(args))
        self.assertEqual(code, 1)
        self.assertEqual(payload.get("code"), "claim_fees_not_supported_for_protocol")

    def test_liquidity_claim_rewards_falls_back_to_legacy_when_uniswap_fails(self) -> None:
        args = argparse.Namespace(
            chain="ethereum_sepolia",
            dex="uniswap_v3",
            position_id="123",
            reward_token="USDC",
            request_json="",
            json=True,
        )
        with mock.patch.object(cli, "assert_chain_capability"), mock.patch.object(
            cli, "_uniswap_lp_operation_enabled", return_value=True
        ), mock.patch.object(
            cli, "_liquidity_provider_settings", return_value=("uniswap_api", "legacy_router")
        ), mock.patch.object(
            cli, "load_wallet_store", return_value={}
        ), mock.patch.object(
            cli, "_execution_wallet", return_value=("0x" + "11" * 20, "0x" + "22" * 32)
        ), mock.patch.object(
            cli, "_resolve_token_address", return_value="0x" + "44" * 20
        ), mock.patch.object(
            cli, "_uniswap_lp_call_via_proxy", side_effect=RuntimeError("upstream down")
        ), mock.patch.object(
            cli, "_legacy_liquidity_operation_available", return_value=True
        ), mock.patch.object(
            cli, "_execute_legacy_liquidity_operation", return_value={"txHash": "0x" + "bb" * 32}
        ):
            code, payload = self._run(lambda: cli.cmd_liquidity_claim_rewards(args))
        self.assertEqual(code, 0)
        self.assertEqual(payload.get("providerUsed"), "legacy_router")
        self.assertEqual(payload.get("fallbackUsed"), True)

    def test_liquidity_claim_rewards_non_uniswap_not_configured(self) -> None:
        args = argparse.Namespace(
            chain="hedera_testnet",
            dex="hedera_hts",
            position_id="123",
            reward_token="",
            request_json="",
            json=True,
        )
        with mock.patch.object(cli, "assert_chain_capability"), mock.patch.object(
            cli, "_liquidity_provider_settings", return_value=("legacy_router", "legacy_router")
        ), mock.patch.object(
            cli,
            "_execute_legacy_liquidity_operation",
            side_effect=cli.WalletStoreError("claim_rewards_not_configured: legacy claim-rewards is not configured for this chain."),
        ):
            code, payload = self._run(lambda: cli.cmd_liquidity_claim_rewards(args))
        self.assertEqual(code, 1)
        self.assertEqual(payload.get("code"), "claim_rewards_not_configured")

    def test_liquidity_claim_fees_failure_payload_has_provider_provenance(self) -> None:
        args = argparse.Namespace(
            chain="ethereum_sepolia",
            dex="uniswap_v3",
            position_id="123",
            collect_as_weth=False,
            json=True,
        )
        with mock.patch.object(cli, "assert_chain_capability"), mock.patch.object(
            cli, "_liquidity_provider_settings", return_value=("uniswap_api", "legacy_router")
        ), mock.patch.object(
            cli, "load_wallet_store", return_value={}
        ), mock.patch.object(
            cli, "_execution_wallet", return_value=("0x" + "11" * 20, "0x" + "22" * 32)
        ), mock.patch.object(
            cli, "_uniswap_lp_call_via_proxy", side_effect=RuntimeError("upstream down")
        ), mock.patch.object(
            cli, "_legacy_liquidity_operation_available", return_value=False
        ):
            code, payload = self._run(lambda: cli.cmd_liquidity_claim_fees(args))
        self.assertEqual(code, 1)
        self.assertEqual(payload.get("code"), "no_execution_provider_available")
        details = payload.get("details") or {}
        self.assertEqual(details.get("operation"), "claim_fees")
        self.assertEqual(details.get("providerRequested"), "uniswap_api")
        self.assertEqual(details.get("providerUsed"), "uniswap_api")
        self.assertEqual(details.get("fallbackUsed"), False)

    def test_liquidity_claim_rewards_invalid_input_payload_has_provider_provenance(self) -> None:
        args = argparse.Namespace(
            chain="ethereum_sepolia",
            dex="uniswap_v3",
            position_id="123",
            reward_token="",
            request_json="",
            json=True,
        )
        with mock.patch.object(cli, "assert_chain_capability"), mock.patch.object(
            cli, "_liquidity_provider_settings", return_value=("uniswap_api", "legacy_router")
        ), mock.patch.object(
            cli, "_uniswap_lp_operation_enabled", return_value=True
        ):
            code, payload = self._run(lambda: cli.cmd_liquidity_claim_rewards(args))
        self.assertEqual(code, 2)
        self.assertEqual(payload.get("code"), "invalid_input")
        details = payload.get("details") or {}
        self.assertEqual(details.get("operation"), "claim_rewards")
        self.assertEqual(details.get("providerRequested"), "uniswap_api")
        self.assertEqual(details.get("fallbackUsed"), False)

    def test_liquidity_adapter_claim_methods_are_fail_closed(self) -> None:
        adapter = LiquidityAdapter(chain="base_sepolia", dex="aerodrome", protocol_family="amm_v2", position_type="v2")
        with self.assertRaisesRegex(Exception, "claim_fees_not_supported_for_protocol"):
            adapter.claim_fees({"positionId": "1"})
        with self.assertRaisesRegex(Exception, "claim_rewards_not_supported_for_protocol"):
            adapter.claim_rewards({"positionId": "1"})
        hts = HederaHtsLiquidityAdapter(chain="hedera_testnet", dex="hedera_hts", protocol_family="hedera_hts", position_type="v2")
        self.assertTrue(hts.supports_operation("claim_fees"))

    def test_send_error_requires_estimate_bypass_detection(self) -> None:
        self.assertTrue(cli._send_error_requires_estimate_bypass("Failed to estimate gas: execution reverted"))
        self.assertTrue(cli._send_error_requires_estimate_bypass('error code 3: execution reverted: ds-math-sub-underflow'))
        self.assertFalse(cli._send_error_requires_estimate_bypass("nonce too low"))

    def test_cast_rpc_send_transaction_retries_with_gas_limit_after_estimate_failure(self) -> None:
        tx_hash = "0x" + "ab" * 32
        call_cmds: list[list[str]] = []

        def _fake_run_subprocess(cmd, **kwargs):
            call_cmds.append(list(cmd))
            index = len(call_cmds)
            if index == 1:
                return mock.Mock(returncode=1, stdout="", stderr="Failed to estimate gas: execution reverted: ds-math-sub-underflow")
            return mock.Mock(returncode=0, stdout=json.dumps({"transactionHash": tx_hash}), stderr="")

        with mock.patch.object(cli, "_require_cast_bin", return_value="cast"), mock.patch.object(
            cli, "_chain_rpc_candidates", return_value=["https://rpc.one"]
        ), mock.patch.object(
            cli, "_estimate_tx_fees", return_value={"mode": "legacy", "gasPrice": 1}
        ), mock.patch.object(
            cli, "_run_subprocess", side_effect=_fake_run_subprocess
        ):
            result = cli._cast_rpc_send_transaction(
                "https://rpc.one",
                {"from": "0x" + "11" * 20, "to": "0x" + "22" * 20, "data": "0xdeadbeef"},
                private_key_hex="0x" + "33" * 32,
                chain="ethereum_sepolia",
            )

        self.assertEqual(result, tx_hash)
        send_cmds = [cmd for cmd in call_cmds if len(cmd) > 1 and cmd[1] == "send"]
        self.assertEqual(len(send_cmds), 2)
        self.assertNotIn("--gas-limit", send_cmds[0])
        self.assertIn("--gas-limit", send_cmds[1])
        gas_limit_index = send_cmds[1].index("--gas-limit")
        self.assertEqual(send_cmds[1][gas_limit_index + 1], str(cli.DEFAULT_TX_ESTIMATE_BYPASS_GAS_LIMIT))


if __name__ == "__main__":
    unittest.main()
