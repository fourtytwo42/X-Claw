import pathlib
import sys
import unittest
from decimal import Decimal
from types import SimpleNamespace
from unittest import mock

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
AGENT_RUNTIME_ROOT = REPO_ROOT / "apps" / "agent-runtime"
if str(AGENT_RUNTIME_ROOT) not in sys.path:
    sys.path.insert(0, str(AGENT_RUNTIME_ROOT))

from xclaw_agent import cli  # noqa: E402
from xclaw_agent.runtime.services import mirroring, reporting, trade_caps  # noqa: E402


class RuntimeInvariantTests(unittest.TestCase):
    def test_mirroring_required_vs_best_effort_delivery_invariant(self) -> None:
        flow = {
            "approvalId": "xfr_1",
            "chainKey": "base_sepolia",
            "status": "approval_pending",
            "toAddress": "0x" + "11" * 20,
            "amountWei": "1",
        }
        failing_api = mock.Mock(return_value=(503, "bad gateway"))

        with self.assertRaises(cli.WalletStoreError) as caught:
            mirroring.mirror_transfer_approval(
                flow=dict(flow),
                require_delivery=True,
                api_request=failing_api,
                utc_now=lambda: "2026-03-08T00:00:00+00:00",
                watcher_run_id=lambda: "wrun_test",
                token_hex=lambda n: "ab" * n,
                wallet_store_error=cli.WalletStoreError,
            )
        self.assertEqual(str(caught.exception), "api_error: transfer mirror failed (503)")
        self.assertEqual(failing_api.call_count, 2)

        failing_api.reset_mock()
        ok = mirroring.mirror_transfer_approval(
            flow=dict(flow),
            require_delivery=False,
            api_request=failing_api,
            utc_now=lambda: "2026-03-08T00:00:00+00:00",
            watcher_run_id=lambda: "wrun_test",
            token_hex=lambda n: "cd" * n,
            wallet_store_error=cli.WalletStoreError,
        )
        self.assertFalse(ok)
        self.assertEqual(failing_api.call_count, 1)

    def test_reporting_payload_fields_invariant(self) -> None:
        captured = {}

        def api_request(method: str, path: str, **kwargs):
            captured["method"] = method
            captured["path"] = path
            captured["payload"] = kwargs.get("payload")
            return 200, {"ok": True}

        result = reporting.send_trade_execution_report(
            trade_id="trd_1",
            read_trade_details=lambda trade_id: {
                "tradeId": trade_id,
                "agentId": "agt_1",
                "status": "filled",
                "mode": "real",
                "chainKey": "base_sepolia",
                "reasonCode": None,
            },
            canonical_event_for_trade_status=lambda status: "trade_filled" if status == "filled" else "trade_failed",
            api_request=api_request,
            wallet_store_error=cli.WalletStoreError,
        )

        self.assertEqual(result, {"ok": True, "eventType": "trade_filled"})
        self.assertEqual(captured["method"], "POST")
        self.assertEqual(captured["path"], "/events")
        payload = captured["payload"]
        self.assertEqual(payload["schemaVersion"], 1)
        self.assertEqual(payload["agentId"], "agt_1")
        self.assertEqual(payload["tradeId"], "trd_1")
        self.assertEqual(payload["eventType"], "trade_filled")
        self.assertIn("createdAt", payload)
        self.assertEqual(
            payload["payload"],
            {
                "status": "filled",
                "mode": "real",
                "chainKey": "base_sepolia",
                "reasonCode": None,
                "reportedBy": "xclaw-agent-runtime",
            },
        )

    def test_trade_caps_replay_idempotent_recovery_invariant(self) -> None:
        outbox = [
            {"payload": {"bad": True}},
            {"idempotencyKey": "", "payload": {"bad": True}},
            {"idempotencyKey": "usage-1", "payload": {"agentId": "agt_1"}},
        ]

        def load_outbox():
            return list(outbox)

        def save_outbox(new_items):
            outbox[:] = list(new_items)

        api_request = mock.Mock(return_value=(200, {"ok": True}))
        ctx = trade_caps.TradeCapsServiceContext(
            load_state=lambda: {},
            save_state=lambda payload: None,
            utc_now=lambda: "2026-03-08T00:00:00+00:00",
            decimal_text=lambda value: str(value),
            to_non_negative_decimal=lambda value: Decimal("0"),
            to_non_negative_int=lambda value: 0,
            load_trade_usage_outbox=load_outbox,
            save_trade_usage_outbox=save_outbox,
            api_request=api_request,
            resolve_api_key=lambda: "api_key",
            resolve_agent_id=lambda api_key: "agt_1",
            token_hex=lambda n: "ab" * n,
            wallet_store_error=cli.WalletStoreError,
        )

        replayed, remaining = trade_caps.replay_trade_usage_outbox(ctx)
        self.assertEqual((replayed, remaining), (1, 0))
        self.assertEqual(outbox, [])
        self.assertEqual(api_request.call_count, 1)

        replayed_again, remaining_again = trade_caps.replay_trade_usage_outbox(ctx)
        self.assertEqual((replayed_again, remaining_again), (0, 0))
        self.assertEqual(api_request.call_count, 1)

    def test_cli_wrapper_delegations_remain_thin(self) -> None:
        ctx_transfer = object()
        ctx_approval = object()
        ctx_reporting = object()
        get_prompt = mock.Mock()
        remove_prompt = mock.Mock()

        with mock.patch.object(cli, "_build_transfer_flow_service_ctx", return_value=ctx_transfer), \
            mock.patch.object(cli, "_build_approval_prompt_service_ctx", return_value=ctx_approval), \
            mock.patch.object(cli, "_build_reporting_service_ctx", return_value=ctx_reporting), \
            mock.patch.object(cli, "_approval_prompt_store_ops", return_value=(get_prompt, remove_prompt)), \
            mock.patch.object(cli.runtime_services, "load_pending_transfer_flows", return_value={"version": 1, "flows": {}}) as load_flows, \
            mock.patch.object(cli.runtime_services, "record_pending_transfer_flow") as record_flow, \
            mock.patch.object(cli.runtime_services, "remove_pending_transfer_flow") as remove_flow, \
            mock.patch.object(cli.runtime_services, "wait_for_trade_approval", return_value={"tradeId": "trd_1"}) as wait_trade, \
            mock.patch.object(cli.runtime_services, "maybe_send_telegram_approval_prompt") as send_prompt, \
            mock.patch.object(cli.runtime_services, "clear_telegram_approval_buttons", return_value={"ok": True}) as clear_buttons, \
            mock.patch.object(cli.runtime_services, "ack_transfer_decision_inbox", return_value=(200, {"ok": True})) as ack_inbox, \
            mock.patch.object(cli.runtime_services, "publish_runtime_signing_readiness", return_value=(200, {"ok": True})) as publish_ready, \
            mock.patch.object(cli.runtime_services, "mirror_transfer_approval", return_value=True) as mirror_transfer, \
            mock.patch.object(cli.runtime_services, "mirror_x402_outbound") as mirror_x402, \
            mock.patch.object(cli.runtime_services, "post_trade_status") as post_trade, \
            mock.patch.object(cli.runtime_services, "post_liquidity_status") as post_liquidity, \
            mock.patch.object(cli.runtime_services, "read_trade_details", return_value={"tradeId": "trd_1"}) as read_trade, \
            mock.patch.object(cli.runtime_services, "send_trade_execution_report_via_context", return_value={"ok": True}) as send_report:

            self.assertEqual(cli._load_pending_transfer_flows(), {"version": 1, "flows": {}})
            cli._record_pending_transfer_flow("xfr_1", {"status": "approval_pending"})
            cli._remove_pending_transfer_flow("xfr_1")
            self.assertEqual(cli._wait_for_trade_approval("trd_1", "base_sepolia", {"tokenInSymbol": "WETH"}), {"tradeId": "trd_1"})
            cli._maybe_send_telegram_approval_prompt("trd_1", "base_sepolia", {"amountInHuman": "1"})
            self.assertEqual(cli._clear_telegram_approval_buttons("trade", "trd_1"), {"ok": True})
            self.assertEqual(cli._ack_transfer_decision_inbox("dec_1", "applied"), (200, {"ok": True}))
            self.assertEqual(cli._publish_runtime_signing_readiness("base_sepolia", {"walletSigningReady": True}), (200, {"ok": True}))
            self.assertTrue(cli._mirror_transfer_approval({"approvalId": "xfr_1", "chainKey": "base_sepolia"}))
            cli._mirror_x402_outbound({"approvalId": "xfr_1", "network": "base_sepolia", "facilitator": "fac", "url": "https://x", "amountAtomic": "1"})
            cli._post_trade_status("trd_1", "approved", "executing")
            cli._post_liquidity_status("liq 1", "failed")
            self.assertEqual(cli._read_trade_details("trd_1"), {"tradeId": "trd_1"})
            self.assertEqual(cli._send_trade_execution_report("trd_1"), {"ok": True})

        load_flows.assert_called_once_with(ctx_transfer)
        record_flow.assert_called_once_with(ctx_transfer, "xfr_1", {"status": "approval_pending"})
        remove_flow.assert_called_once_with(ctx_transfer, "xfr_1")
        wait_trade.assert_called_once_with(ctx_approval, "trd_1", "base_sepolia", {"tokenInSymbol": "WETH"})
        send_prompt.assert_called_once_with(ctx_approval, "trd_1", "base_sepolia", {"amountInHuman": "1"})
        clear_buttons.assert_called_once_with(ctx_approval, "trade", "trd_1", get_prompt=get_prompt, remove_prompt=remove_prompt)
        ack_inbox.assert_called_once_with(cli._api_request, "dec_1", "applied", reason_code=None, reason_message=None)
        publish_ready.assert_called_once_with(cli._api_request, "base_sepolia", {"walletSigningReady": True})
        mirror_transfer.assert_called_once()
        mirror_x402.assert_called_once()
        post_trade.assert_called_once_with(
            ctx_reporting,
            trade_id="trd_1",
            from_status="approved",
            to_status="executing",
            extra=None,
            idempotency_key=None,
            decision_at=None,
        )
        post_liquidity.assert_called_once_with(
            ctx_reporting,
            liquidity_intent_id="liq%201",
            to_status="failed",
            extra=None,
        )
        read_trade.assert_called_once_with(ctx_reporting, "trd_1")
        send_report.assert_called_once_with(ctx_reporting, trade_id="trd_1")


if __name__ == "__main__":
    unittest.main()
