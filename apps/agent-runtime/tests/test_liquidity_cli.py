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

    def test_liquidity_remove_blocks_zero_lp_balance_before_proposal(self) -> None:
        args = argparse.Namespace(
            chain="base_sepolia",
            dex="aerodrome",
            position_id="0x" + "aa" * 20,
            token_a="",
            token_b="",
            percent=100,
            slippage_bps=100,
            position_type="v2",
            json=True,
        )
        adapter = mock.Mock()
        adapter.dex = "aerodrome"
        adapter.protocol_family = "amm_v2"
        adapter.quote_remove.return_value = {"simulation": {"minAmountA": "1", "minAmountB": "1"}}
        with mock.patch.object(cli, "assert_chain_capability"), mock.patch.object(
            cli, "build_liquidity_adapter_for_request", return_value=adapter
        ), mock.patch.object(
            cli, "_liquidity_provider_settings", return_value=("router_adapter", {"provider": "router_adapter"})
        ), mock.patch.object(
            cli, "_resolve_agent_id_or_fail", return_value="agt_1"
        ), mock.patch.object(
            cli, "_resolve_liquidity_remove_tokens", return_value=("0x" + "11" * 20, "0x" + "22" * 20)
        ), mock.patch.object(
            cli, "_token_symbol_for_display", side_effect=["USDC", "WETH"]
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

    def test_approvals_decide_liquidity_converges_when_missing_from_pending_scope(self) -> None:
        args = argparse.Namespace(
            intent_id="liq_1",
            decision="approve",
            reason_message="",
            source="telegram",
            chain="base_sepolia",
            json=True,
        )

        with mock.patch.object(
            cli,
            "_read_liquidity_intent",
            side_effect=cli.WalletStoreError("Liquidity intent 'liq_1' was not found in pending scope for chain 'base_sepolia'."),
        ):
            code, payload = self._run(lambda: cli.cmd_approvals_decide_liquidity(args))

        self.assertEqual(code, 0)
        self.assertTrue(payload.get("ok"))
        self.assertEqual(payload.get("status"), "converged_unknown")
        self.assertTrue(payload.get("converged"))

    def test_liquidity_discover_pairs_returns_ranked_candidates(self) -> None:
        args = argparse.Namespace(
            chain="base_sepolia",
            dex="aerodrome",
            min_reserve=1000,
            limit=2,
            scan_max=10,
            json=True,
        )
        adapter = mock.Mock()
        adapter.protocol_family = "amm_v2"

        cast_outputs = [
            "0x000000000000000000000000000000000000fAaA",
            "3",
            "0x0000000000000000000000000000000000001000",
            "0x0000000000000000000000000000000000000001",
            "0x0000000000000000000000000000000000000002",
            "(500,1000,1)",
            "0x0000000000000000000000000000000000002000",
            "0x0000000000000000000000000000000000000003",
            "0x0000000000000000000000000000000000000004",
            "(10000,20000,1)",
            "0x0000000000000000000000000000000000003000",
            "0x0000000000000000000000000000000000000005",
            "0x0000000000000000000000000000000000000006",
            "(3000,4000,1)",
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
        pairs = payload.get("pairs") or []
        self.assertEqual(pairs[0]["pairAddress"], "0x0000000000000000000000000000000000002000")
        self.assertEqual(pairs[1]["pairAddress"], "0x0000000000000000000000000000000000003000")

    def test_liquidity_execute_supports_v3_add_execution_family(self) -> None:
        args = argparse.Namespace(intent="liq_1", chain="base_sepolia", json=True)
        adapter = mock.Mock()
        adapter.protocol_family = "position_manager_v3"
        adapter.dex = "uniswap_v3"
        adapter.supports_operation.return_value = True
        with mock.patch.object(
            cli,
            "_read_liquidity_intent",
            return_value={"liquidityIntentId": "liq_1", "status": "approved", "dex": "uniswap_v3", "positionType": "v3", "action": "add"},
        ), mock.patch.object(cli, "build_liquidity_adapter_for_request", return_value=adapter), mock.patch.object(
            cli, "_post_liquidity_status"
        ), mock.patch.object(
            cli, "_execute_liquidity_v3_add", return_value={"txHash": "0xabc", "positionId": "123", "details": {"executionFamily": "position_manager_v3"}}
        ), mock.patch.object(
            cli, "_wait_for_tx_receipt_success", return_value={"status": "0x1"}
        ):
            code, payload = self._run(lambda: cli.cmd_liquidity_execute(args))
        self.assertEqual(code, 0)
        self.assertEqual(payload.get("status"), "filled")
        self.assertEqual(payload.get("adapterFamily"), "position_manager_v3")

    def test_liquidity_quote_add_solana_raydium_uses_planner_quote(self) -> None:
        args = argparse.Namespace(
            chain="solana_devnet",
            dex="raydium_clmm",
            token_a="SOL",
            token_b="USDC",
            amount_a="1",
            amount_b="2",
            position_type="v3",
            slippage_bps=100,
            v3_range="100:-10:10",
            json=True,
        )
        adapter = mock.Mock()
        adapter.protocol_family = "raydium_clmm"
        adapter.adapter_metadata = {
            "poolRegistry": {
                "default": {
                    "poolId": "So11111111111111111111111111111111111111112",
                }
            }
        }
        adapter.quote_add.return_value = {"simulation": {}}
        with mock.patch.object(cli, "assert_chain_capability"), mock.patch.object(
            cli, "build_liquidity_adapter_for_request", return_value=adapter
        ), mock.patch.object(
            cli, "_resolve_token_address", side_effect=["So11111111111111111111111111111111111111112", "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"]
        ), mock.patch.object(
            cli, "solana_raydium_quote_add", return_value={"amountB": "2", "minAmountB": "1.98", "poolId": "So11111111111111111111111111111111111111112"}
        ):
            code, payload = self._run(lambda: cli.cmd_liquidity_quote_add(args))
        self.assertEqual(code, 0)
        self.assertEqual(payload.get("adapterFamily"), "raydium_clmm")
        self.assertEqual((payload.get("preflight") or {}).get("poolId"), "So11111111111111111111111111111111111111112")

    def test_liquidity_execute_supports_v3_remove_execution_family(self) -> None:
        args = argparse.Namespace(intent="liq_2", chain="base_sepolia", json=True)
        adapter = mock.Mock()
        adapter.protocol_family = "position_manager_v3"
        adapter.dex = "uniswap_v3"
        adapter.supports_operation.return_value = True
        with mock.patch.object(
            cli,
            "_read_liquidity_intent",
            return_value={"liquidityIntentId": "liq_2", "status": "approved", "dex": "uniswap_v3", "positionType": "v3", "action": "remove"},
        ), mock.patch.object(cli, "build_liquidity_adapter_for_request", return_value=adapter), mock.patch.object(
            cli, "_post_liquidity_status"
        ), mock.patch.object(
            cli, "_execute_liquidity_v3_remove", return_value={"txHash": "0xdef", "positionId": "123", "details": {"executionFamily": "position_manager_v3"}}
        ), mock.patch.object(
            cli, "_wait_for_tx_receipt_success", return_value={"status": "0x1"}
        ):
            code, payload = self._run(lambda: cli.cmd_liquidity_execute(args))
        self.assertEqual(code, 0)
        self.assertEqual(payload.get("status"), "filled")
        self.assertEqual(payload.get("adapterFamily"), "position_manager_v3")

    def test_liquidity_increase_uses_local_position_manager_plan(self) -> None:
        args = argparse.Namespace(
            chain="ethereum_sepolia",
            dex="uniswap_v3",
            position_id="123",
            token_a="WETH",
            token_b="USDC",
            amount_a="0.1",
            amount_b="100",
            slippage_bps=100,
            json=True,
        )
        adapter = mock.Mock()
        adapter.protocol_family = "position_manager_v3"
        adapter.dex = "uniswap_v3"
        adapter.supports_operation.return_value = True
        with mock.patch.object(cli, "assert_chain_capability"), mock.patch.object(
            cli, "build_liquidity_adapter_for_request", return_value=adapter
        ), mock.patch.object(
            cli, "load_wallet_store", return_value=object()
        ), mock.patch.object(
            cli, "_execution_wallet", return_value=("0x" + "33" * 20, "11" * 32)
        ), mock.patch.object(
            cli, "_resolve_token_address", side_effect=["0x" + "11" * 20, "0x" + "22" * 20]
        ), mock.patch.object(
            cli, "_fetch_erc20_metadata", side_effect=[{"decimals": 18}, {"decimals": 6}]
        ), mock.patch.object(
            cli, "_to_units_uint", side_effect=["100", "200"]
        ), mock.patch.object(
            cli, "build_liquidity_increase_plan", return_value=mock.Mock()
        ) as mocked_build, mock.patch.object(
            cli,
            "execute_liquidity_plan",
            return_value=mock.Mock(
                tx_hash="0xabc",
                approve_tx_hashes=["0xappr"],
                operation_tx_hashes=["0xabc"],
                execution_family="position_manager_v3",
                execution_adapter="uniswap_v3",
                route_kind="position_manager",
                details={"positionId": "123"},
            ),
        ):
            code, payload = self._run(lambda: cli.cmd_liquidity_increase(args))
        self.assertEqual(code, 0)
        self.assertEqual(payload.get("providerUsed"), "router_adapter")
        self.assertEqual(payload.get("executionFamily"), "position_manager_v3")
        self.assertEqual(payload.get("routeKind"), "position_manager")
        mocked_build.assert_called_once()

    def test_liquidity_claim_rewards_fails_when_not_configured(self) -> None:
        args = argparse.Namespace(
            chain="ethereum_sepolia",
            dex="uniswap_v3",
            position_id="123",
            reward_token="",
            request_json="",
            json=True,
        )
        adapter = mock.Mock()
        adapter.protocol_family = "position_manager_v3"
        adapter.dex = "uniswap_v3"
        adapter.supports_operation.return_value = True
        with mock.patch.object(cli, "assert_chain_capability"), mock.patch.object(
            cli, "build_liquidity_adapter_for_request", return_value=adapter
        ), mock.patch.object(
            cli, "load_wallet_store", return_value=object()
        ), mock.patch.object(
            cli, "_execution_wallet", return_value=("0x" + "33" * 20, "11" * 32)
        ), mock.patch.object(
            cli, "build_liquidity_claim_rewards_plan", side_effect=ValueError("claim_rewards_not_configured")
        ):
            code, payload = self._run(lambda: cli.cmd_liquidity_claim_rewards(args))
        self.assertEqual(code, 1)
        self.assertEqual(payload.get("code"), "claim_rewards_not_configured")

    def test_liquidity_add_v3_rejects_malformed_range(self) -> None:
        args = argparse.Namespace(
            chain="base_sepolia",
            dex="uniswap_v3",
            token_a="USDC",
            token_b="WETH",
            amount_a="10",
            amount_b="1",
            position_type="v3",
            v3_range="3000:bad",
            slippage_bps=100,
            json=True,
        )
        with mock.patch.object(cli, "assert_chain_capability"), mock.patch.object(
            cli, "_resolve_token_address", side_effect=["0x" + "11" * 20, "0x" + "22" * 20]
        ):
            code, payload = self._run(lambda: cli.cmd_liquidity_add(args))
        self.assertEqual(code, 2)
        self.assertEqual(payload.get("code"), "invalid_input")

    def test_liquidity_migrate_succeeds_without_request_calls(self) -> None:
        args = argparse.Namespace(
            chain="ethereum_sepolia",
            dex="uniswap_v3",
            position_id="123",
            from_protocol="V3",
            to_protocol="V3",
            slippage_bps=100,
            request_json="",
            json=True,
        )
        adapter = mock.Mock()
        adapter.protocol_family = "position_manager_v3"
        adapter.dex = "uniswap_v3"
        adapter.position_manager = "0x" + "44" * 20
        adapter.supports_operation.return_value = True
        adapter.operations = {"migrate": {"targetAdapterKey": "uniswap_v3"}}
        with mock.patch.object(cli, "assert_chain_capability"), mock.patch.object(
            cli, "build_liquidity_adapter_for_request", return_value=adapter
        ), mock.patch.object(
            cli, "_read_v3_position_snapshot", return_value={"liquidityUnits": "1000", "token0": "0x" + "11" * 20, "token1": "0x" + "22" * 20}
        ), mock.patch.object(
            cli, "load_wallet_store", return_value=object()
        ), mock.patch.object(
            cli, "_execution_wallet", return_value=("0x" + "33" * 20, "11" * 32)
        ), mock.patch.object(
            cli, "build_liquidity_migrate_plan", return_value=mock.Mock()
        ), mock.patch.object(
            cli,
            "execute_liquidity_plan",
            return_value=mock.Mock(
                tx_hash="0xabc",
                approve_tx_hashes=[],
                operation_tx_hashes=["0xabc"],
                execution_family="position_manager_v3",
                execution_adapter="uniswap_v3",
                route_kind="position_manager",
                details={"migrationMode": "withdraw_only"},
            ),
        ):
            code, payload = self._run(lambda: cli.cmd_liquidity_migrate(args))
        self.assertEqual(code, 0)
        self.assertEqual(payload.get("providerUsed"), "router_adapter")
        self.assertEqual(payload.get("executionFamily"), "position_manager_v3")

    def test_liquidity_increase_solana_local_clmm(self) -> None:
        args = argparse.Namespace(
            chain="solana_localnet",
            dex="local_clmm",
            position_id="solpos_1",
            token_a="SOL",
            token_b="USDC",
            amount_a="1",
            amount_b="2",
            slippage_bps=100,
            json=True,
        )
        adapter = mock.Mock()
        adapter.protocol_family = "local_clmm"
        adapter.dex = "local_clmm"
        adapter.supports_operation.return_value = True
        with mock.patch.object(cli, "assert_chain_capability"), mock.patch.object(
            cli, "build_liquidity_adapter_for_request", return_value=adapter
        ), mock.patch.object(
            cli, "_resolve_token_address", side_effect=["So11111111111111111111111111111111111111112", "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"]
        ), mock.patch.object(
            cli, "load_wallet_store", return_value=object()
        ), mock.patch.object(
            cli, "_execution_wallet_solana_secret", return_value=("Owner1111111111111111111111111111111111", b"\x01" * 64)
        ), mock.patch.object(
            cli, "solana_local_increase_position", return_value={"txHash": "solsig_inc", "positionId": "solpos_1"}
        ):
            code, payload = self._run(lambda: cli.cmd_liquidity_increase(args))
        self.assertEqual(code, 0)
        self.assertEqual(payload.get("executionFamily"), "solana_clmm")
        self.assertEqual(payload.get("executionAdapter"), "local_clmm")
        self.assertEqual(payload.get("liquidityOperation"), "increase")

    def test_liquidity_claim_rewards_solana_requires_reward_config(self) -> None:
        args = argparse.Namespace(
            chain="solana_devnet",
            dex="raydium_clmm",
            position_id="123",
            reward_token="",
            request_json="",
            json=True,
        )
        adapter = mock.Mock()
        adapter.protocol_family = "raydium_clmm"
        adapter.dex = "raydium_clmm"
        adapter.supports_operation.return_value = True
        adapter.operations = {"claimRewards": {"rewardContracts": []}}
        with mock.patch.object(cli, "assert_chain_capability"), mock.patch.object(
            cli, "build_liquidity_adapter_for_request", return_value=adapter
        ):
            code, payload = self._run(lambda: cli.cmd_liquidity_claim_rewards(args))
        self.assertEqual(code, 1)
        self.assertEqual(payload.get("code"), "claim_rewards_not_configured")

    def test_liquidity_migrate_solana_local_clmm(self) -> None:
        args = argparse.Namespace(
            chain="solana_localnet",
            dex="local_clmm",
            position_id="solpos_1",
            from_protocol="V3",
            to_protocol="V3",
            slippage_bps=100,
            request_json="",
            json=True,
        )
        adapter = mock.Mock()
        adapter.protocol_family = "local_clmm"
        adapter.dex = "local_clmm"
        adapter.supports_operation.return_value = True
        adapter.operations = {"migrate": {"targetAdapterKey": "local_clmm"}}
        with mock.patch.object(cli, "assert_chain_capability"), mock.patch.object(
            cli, "build_liquidity_adapter_for_request", return_value=adapter
        ), mock.patch.object(
            cli, "load_wallet_store", return_value=object()
        ), mock.patch.object(
            cli, "_execution_wallet_solana_secret", return_value=("Owner1111111111111111111111111111111111", b"\x01" * 64)
        ), mock.patch.object(
            cli, "solana_local_migrate_position", return_value={"txHash": "solsig_mig", "migrationMode": "withdraw_only", "positionId": "solpos_1"}
        ):
            code, payload = self._run(lambda: cli.cmd_liquidity_migrate(args))
        self.assertEqual(code, 0)
        self.assertEqual(payload.get("executionFamily"), "solana_clmm")
        self.assertEqual(payload.get("liquidityOperation"), "migrate")

    def test_liquidity_execute_supports_advanced_intent_actions(self) -> None:
        args = argparse.Namespace(intent="liq_advanced", chain="solana_localnet", json=True)
        adapter = mock.Mock()
        adapter.protocol_family = "local_clmm"
        adapter.dex = "local_clmm"
        with mock.patch.object(
            cli,
            "_read_liquidity_intent",
            return_value={"liquidityIntentId": "liq_advanced", "status": "approved", "dex": "local_clmm", "positionType": "v3", "action": "increase"},
        ), mock.patch.object(
            cli, "build_liquidity_adapter_for_request", return_value=adapter
        ), mock.patch.object(
            cli, "_post_liquidity_status"
        ), mock.patch.object(
            cli,
            "_execute_liquidity_advanced_intent",
            return_value=(
                {
                    "txHash": "solsig_advanced",
                    "positionId": "solpos_1",
                    "executionFamily": "solana_clmm",
                    "executionAdapter": "local_clmm",
                    "routeKind": "adapter_default",
                    "liquidityOperation": "increase",
                    "details": {"operationTxHashes": ["solsig_advanced"]},
                },
                "local_clmm",
            ),
        ):
            code, payload = self._run(lambda: cli.cmd_liquidity_execute(args))
        self.assertEqual(code, 0)
        self.assertEqual(payload.get("status"), "filled")
        self.assertEqual(payload.get("adapterFamily"), "local_clmm")

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
        self.assertEqual(mocked_allowance.call_args_list[0].kwargs.get("required_units"), 100)
        self.assertEqual(mocked_allowance.call_args_list[1].kwargs.get("required_units"), 200)
        self.assertEqual(out.get("txHash"), "0xabc")

    def test_execute_liquidity_v2_remove_zero_lp_balance_is_deterministic(self) -> None:
        adapter = mock.Mock()
        adapter.protocol_family = "amm_v2"
        adapter.dex = "aerodrome"
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
                        "dex": "aerodrome",
                        "positionType": "v2",
                        "positionRef": "0x" + "aa" * 20,
                        "amountA": "100",
                        "slippageBps": 100,
                    },
                    "base_sepolia",
                )
        self.assertEqual(ctx.exception.reason_code, "liquidity_preflight_zero_lp_balance")
        self.assertEqual((ctx.exception.details or {}).get("lpBalance"), "0")


if __name__ == "__main__":
    unittest.main()
