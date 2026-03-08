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
from xclaw_agent.commands import liquidity as liquidity_commands  # noqa: E402
from xclaw_agent.commands import x402 as x402_commands  # noqa: E402
from xclaw_agent.runtime.adapters import LiquidityRuntimeAdapter, X402RuntimeAdapter  # noqa: E402


class RuntimeAdapterTests(unittest.TestCase):
    def test_cli_builds_typed_liquidity_adapter(self) -> None:
        adapter = cli._build_liquidity_runtime_adapter()
        self.assertIsInstance(adapter, LiquidityRuntimeAdapter)

    def test_cli_builds_typed_x402_adapter(self) -> None:
        adapter = cli._build_x402_runtime_adapter()
        self.assertIsInstance(adapter, X402RuntimeAdapter)

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
