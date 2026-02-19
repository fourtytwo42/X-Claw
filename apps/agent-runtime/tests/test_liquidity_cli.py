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
        ):
            code, payload = self._run(lambda: cli.cmd_liquidity_add(args))

        self.assertEqual(code, 0)
        self.assertEqual(payload.get("status"), "approved")
        self.assertEqual(payload.get("adapterFamily"), "amm_v2")
        self.assertEqual(payload.get("preflight", {}).get("minAmountA"), "9.9")
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
        ) as mocked_api:
            code, payload = self._run(lambda: cli.cmd_liquidity_add(args))

        self.assertEqual(code, 0)
        self.assertEqual(payload.get("adapterFamily"), "hedera_hts")
        api_payload = mocked_api.call_args.kwargs.get("payload", {})
        self.assertEqual(api_payload.get("details", {}).get("htsNative"), True)
        self.assertIsNone(api_payload.get("details", {}).get("v3Range"))

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


if __name__ == "__main__":
    unittest.main()
