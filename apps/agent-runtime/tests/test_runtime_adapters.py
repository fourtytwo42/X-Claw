import argparse
import io
import json
import pathlib
import sys
import unittest
from contextlib import redirect_stdout
from unittest import mock

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
AGENT_RUNTIME_ROOT = REPO_ROOT / "apps" / "agent-runtime"
if str(AGENT_RUNTIME_ROOT) not in sys.path:
    sys.path.insert(0, str(AGENT_RUNTIME_ROOT))

from xclaw_agent import cli  # noqa: E402
from xclaw_agent.commands import approvals as approvals_commands  # noqa: E402
from xclaw_agent.commands import limit_orders as limit_order_commands  # noqa: E402
from xclaw_agent.commands import liquidity as liquidity_commands  # noqa: E402
from xclaw_agent.commands import trade as trade_commands  # noqa: E402
from xclaw_agent.commands import wallet as wallet_commands  # noqa: E402
from xclaw_agent.commands import x402 as x402_commands  # noqa: E402
from xclaw_agent.runtime.adapters import (  # noqa: E402
    ApprovalsRuntimeAdapter,
    LimitOrdersRuntimeAdapter,
    LiquidityRuntimeAdapter,
    TradeRuntimeAdapter,
    WalletRuntimeAdapter,
    X402RuntimeAdapter,
)


class RuntimeAdapterTests(unittest.TestCase):
    def test_cli_builds_typed_liquidity_adapter(self) -> None:
        adapter = cli._build_liquidity_runtime_adapter()
        self.assertIsInstance(adapter, LiquidityRuntimeAdapter)

    def test_cli_builds_typed_x402_adapter(self) -> None:
        adapter = cli._build_x402_runtime_adapter()
        self.assertIsInstance(adapter, X402RuntimeAdapter)

    def test_cli_builds_typed_approvals_adapter(self) -> None:
        adapter = cli._build_approvals_runtime_adapter()
        self.assertIsInstance(adapter, ApprovalsRuntimeAdapter)

    def test_cli_builds_typed_trade_adapter(self) -> None:
        adapter = cli._build_trade_runtime_adapter()
        self.assertIsInstance(adapter, TradeRuntimeAdapter)

    def test_cli_builds_typed_wallet_adapter(self) -> None:
        adapter = cli._build_wallet_runtime_adapter()
        self.assertIsInstance(adapter, WalletRuntimeAdapter)

    def test_cli_builds_typed_limit_orders_adapter(self) -> None:
        adapter = cli._build_limit_orders_runtime_adapter()
        self.assertIsInstance(adapter, LimitOrdersRuntimeAdapter)

    def test_liquidity_module_globals_do_not_mutate_during_command(self) -> None:
        self.assertFalse(hasattr(liquidity_commands, "_bind_runtime"))
        before_keys = set(liquidity_commands.__dict__.keys())
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
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = cli.cmd_liquidity_quote_add(args)
        self.assertEqual(code, 2)
        payload = json.loads(buf.getvalue().strip())
        self.assertEqual(payload.get("code"), "unsupported_liquidity_adapter")
        self.assertEqual(before_keys, set(liquidity_commands.__dict__.keys()))
        self.assertFalse(hasattr(liquidity_commands, "require_json_flag"))

    def test_x402_module_globals_do_not_mutate_during_command(self) -> None:
        self.assertFalse(hasattr(x402_commands, "_bind_runtime"))
        before_keys = set(x402_commands.__dict__.keys())
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
        self.assertEqual(before_keys, set(x402_commands.__dict__.keys()))
        self.assertFalse(hasattr(x402_commands, "require_json_flag"))

    def test_trade_wrapper_passes_typed_adapter(self) -> None:
        args = argparse.Namespace(chain="base_sepolia", token_in="USDC", token_out="WETH", amount_in="1", slippage_bps=100, deadline_sec=120, to=None, json=True)
        with mock.patch.object(trade_commands, "cmd_trade_spot", return_value=0) as mocked:
            cli.cmd_trade_spot(args)
        adapter = mocked.call_args.args[0]
        self.assertIsInstance(adapter, TradeRuntimeAdapter)

    def test_approvals_wrapper_passes_typed_adapter(self) -> None:
        args = argparse.Namespace(chain="base_sepolia", json=True)
        with mock.patch.object(approvals_commands, "cmd_approvals_sync", return_value=0) as mocked:
            cli.cmd_approvals_sync(args)
        adapter = mocked.call_args.args[0]
        self.assertIsInstance(adapter, ApprovalsRuntimeAdapter)

    def test_wallet_wrapper_passes_typed_adapter(self) -> None:
        args = argparse.Namespace(chain="solana_devnet", json=True)
        with mock.patch.object(wallet_commands, "cmd_wallet_rpc_health", return_value=0) as mocked:
            cli.cmd_wallet_rpc_health(args)
        adapter = mocked.call_args.args[0]
        self.assertIsInstance(adapter, WalletRuntimeAdapter)

    def test_limit_orders_wrapper_passes_typed_adapter(self) -> None:
        args = argparse.Namespace(chain="base_sepolia", limit=10, status=None, json=True)
        with mock.patch.object(limit_order_commands, "cmd_limit_orders_list", return_value=0) as mocked:
            cli.cmd_limit_orders_list(args)
        adapter = mocked.call_args.args[0]
        self.assertIsInstance(adapter, LimitOrdersRuntimeAdapter)

    def test_approvals_transfer_x402_fallback_uses_cli_patch_surface(self) -> None:
        approval_id = "xfr_x402_1"
        args = argparse.Namespace(approval_id=approval_id, decision="approve", reason_message=None, chain="base_sepolia", json=True)
        with mock.patch.object(cli, "_get_pending_transfer_flow", return_value=None), mock.patch.object(
            cli.x402_state, "get_pending_pay_flow", return_value={"approvalId": approval_id, "status": "approval_pending"}
        ), mock.patch.object(
            cli,
            "x402_pay_decide",
            return_value={"approvalId": approval_id, "status": "filled", "network": "base_sepolia", "facilitator": "cdp"},
        ), mock.patch.object(cli, "_mirror_x402_outbound"), redirect_stdout(io.StringIO()) as buf:
            code = cli.cmd_approvals_decide_transfer(args)
        payload = json.loads(buf.getvalue().strip())
        self.assertEqual(code, 0)
        self.assertEqual((payload.get("approval") or {}).get("approvalId"), approval_id)


if __name__ == "__main__":
    unittest.main()
