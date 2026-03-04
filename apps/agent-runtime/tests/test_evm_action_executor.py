import pathlib
import sys
import unittest

RUNTIME_ROOT = pathlib.Path("apps/agent-runtime").resolve()
if str(RUNTIME_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNTIME_ROOT))

from xclaw_agent.evm_action_executor import EvmActionExecutor  # noqa: E402
from xclaw_agent.execution_contracts import ApprovalRequirement, EvmActionPlan, EvmCall  # noqa: E402


class EvmActionExecutorTests(unittest.TestCase):
    def test_execute_plan_runs_approvals_before_calls(self) -> None:
        events: list[str] = []

        def fake_ensure(**kwargs):
            events.append(f"approve:{kwargs['token_address']}")
            return "0x" + "11" * 32

        def fake_send(rpc_url, tx_obj, private_key_hex, **kwargs):
            events.append(f"call:{tx_obj['to']}")
            return "0x" + "22" * 32

        def fake_wait(chain, tx_hash):
            events.append(f"wait:{tx_hash}")
            return {"status": "0x1"}

        executor = EvmActionExecutor(
            ensure_token_allowance=fake_ensure,
            send_transaction=fake_send,
            wait_for_receipt_success=fake_wait,
            rpc_url_for_chain=lambda chain: "https://rpc.example",
        )
        plan = EvmActionPlan(
            operation_kind="swap_exact_in",
            chain="base_sepolia",
            execution_family="amm_v2",
            execution_adapter="uniswap_fork",
            route_kind="router_path",
            approvals=[ApprovalRequirement(token="0x" + "11" * 20, spender="0x" + "22" * 20, required_units=1)],
            calls=[EvmCall(to="0x" + "33" * 20, data="0xdeadbeef", value_wei="0", label="swap")],
        )

        result = executor.execute_plan(
            plan,
            owner="0x" + "44" * 20,
            private_key_hex="11" * 32,
            wait_for_operation_receipts=True,
        )

        self.assertTrue(result.ok)
        self.assertEqual(events[0], f"approve:{'0x' + '11' * 20}")
        self.assertEqual(events[1], f"call:{'0x' + '33' * 20}")
        self.assertEqual(events[2], f"wait:{'0x' + '22' * 32}")

    def test_execute_plan_skips_approval_when_not_needed(self) -> None:
        approve_calls: list[str] = []
        call_hashes: list[str] = []

        executor = EvmActionExecutor(
            ensure_token_allowance=lambda **kwargs: approve_calls.append("approve") or None,
            send_transaction=lambda rpc_url, tx_obj, private_key_hex, **kwargs: call_hashes.append("call")
            or ("0x" + "aa" * 32),
            wait_for_receipt_success=lambda chain, tx_hash: {"status": "0x1"},
            rpc_url_for_chain=lambda chain: "https://rpc.example",
        )
        plan = EvmActionPlan(
            operation_kind="liquidity_remove_v2",
            chain="base_sepolia",
            execution_family="amm_v2",
            execution_adapter="aerodrome",
            route_kind="direct_pair",
            approvals=[],
            calls=[EvmCall(to="0x" + "33" * 20, data="0xdeadbeef", value_wei="0", label="remove")],
        )

        result = executor.execute_plan(
            plan,
            owner="0x" + "44" * 20,
            private_key_hex="11" * 32,
            wait_for_operation_receipts=False,
            liquidity_operation="remove",
        )

        self.assertEqual(approve_calls, [])
        self.assertEqual(call_hashes, ["call"])
        self.assertEqual(result.liquidity_operation, "remove")


if __name__ == "__main__":
    unittest.main()
