import os
import pathlib
import sys
import tempfile
import unittest
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest import mock

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
AGENT_RUNTIME_ROOT = REPO_ROOT / "apps" / "agent-runtime"
if str(AGENT_RUNTIME_ROOT) not in sys.path:
    sys.path.insert(0, str(AGENT_RUNTIME_ROOT))

from xclaw_agent.runtime.services import agent_api, approval_prompts, execution_contracts, liquidity_execution, mirroring, owner_link_delivery, reporting, runtime_state, telegram_delivery, trade_caps, trade_execution, transfer_flows, transfer_policy  # noqa: E402
from xclaw_agent import cli  # noqa: E402


class RuntimeServicesTests(unittest.TestCase):
    def test_transfer_flow_service_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = pathlib.Path(tmpdir) / "pending-transfer-flows.json"
            ctx = transfer_flows.TransferFlowContext(
                ensure_app_dir=lambda: None,
                flows_file=path,
                json_module=cli.json,
                os_module=cli.os,
                pathlib_module=cli.pathlib,
                utc_now=cli.utc_now,
                is_solana_chain=cli._is_solana_chain,
                is_solana_address=cli.is_solana_address,
                is_hex_address=cli.is_hex_address,
                transfer_executing_stale_sec=lambda: 60,
                evaluate_outbound_transfer_policy=lambda chain, to: {"allowed": True},
                watcher_run_id=lambda: "wrun_test",
                record_pending_transfer_flow=lambda approval_id, flow: transfer_flows.record_pending_transfer_flow(ctx, approval_id, flow),
                mirror_transfer_approval=lambda flow: True,
                remove_pending_transfer_flow=lambda approval_id: transfer_flows.remove_pending_transfer_flow(ctx, approval_id),
                transfer_amount_display=cli._transfer_amount_display,
                enforce_spend_preconditions=lambda chain, amount: ({}, "2026-03-08", 0, 100),
                load_wallet_store=lambda: {},
                chain_wallet=lambda store, chain: (None, None),
                validate_wallet_entry_shape=lambda wallet: None,
                fetch_token_balance_wei=lambda chain, wallet, token: "100",
                fetch_native_balance_wei=lambda chain, wallet: "100",
                assert_transfer_balance_preconditions=lambda **kwargs: None,
                require_wallet_passphrase_for_signing=lambda chain: "pw",
                decrypt_private_key=lambda wallet, pw: b"\x11" * 32,
                chain_rpc_url=lambda chain: "https://rpc.example",
                solana_send_native_transfer=lambda *args: "sig",
                solana_send_spl_transfer=lambda *args: {"signature": "sig"},
                cast_rpc_send_transaction=lambda *args, **kwargs: "0x" + "ab" * 32,
                require_cast_bin=lambda: "cast",
                run_subprocess=lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout='{"status":"0x1"}', stderr=""),
                cast_receipt_timeout_sec=lambda: 5,
                cast_calldata=lambda *args, **kwargs: "0xdeadbeef",
                record_spend=lambda *args, **kwargs: None,
                builder_output_from_hashes=lambda chain, hashes: {"builderCodeApplied": False},
                re_module=cli.re,
                json_loads=cli.json.loads,
                wallet_store_error=cli.WalletStoreError,
            )
            transfer_flows.record_pending_transfer_flow(ctx, "xfr_1", {"approvalId": "xfr_1", "status": "approval_pending"})
            saved = transfer_flows.get_pending_transfer_flow(ctx, "xfr_1")
            self.assertEqual((saved or {}).get("approvalId"), "xfr_1")
            transfer_flows.remove_pending_transfer_flow(ctx, "xfr_1")
            self.assertIsNone(transfer_flows.get_pending_transfer_flow(ctx, "xfr_1"))

    def test_transfer_flow_service_stale_executing_detection(self) -> None:
        ctx = SimpleNamespace(transfer_executing_stale_sec=lambda: 60)
        old = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
        self.assertTrue(transfer_flows.is_stale_executing_transfer_flow(ctx, {"status": "executing", "updatedAt": old}))
        self.assertFalse(transfer_flows.is_stale_executing_transfer_flow(ctx, {"status": "executing", "updatedAt": cli.utc_now(), "txHash": "0x1"}))

    def test_transfer_flow_service_invalid_state_file_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = pathlib.Path(tmpdir) / "pending-transfer-flows.json"
            path.write_text('["bad"]', encoding="utf-8")
            ctx = SimpleNamespace(
                ensure_app_dir=lambda: None,
                flows_file=path,
                json_module=cli.json,
            )
            loaded = transfer_flows.load_pending_transfer_flows(ctx)
            self.assertEqual(loaded, {"version": 1, "flows": {}})

    def test_transfer_flow_service_execute_propagates_pre_execution_mirror_failure(self) -> None:
        ctx = transfer_flows.TransferFlowContext(
            ensure_app_dir=lambda: None,
            flows_file=pathlib.Path("/tmp/unused-transfer-flows.json"),
            json_module=cli.json,
            os_module=cli.os,
            pathlib_module=cli.pathlib,
            utc_now=lambda: "2026-03-08T00:00:00+00:00",
            is_solana_chain=lambda chain: False,
            is_solana_address=cli.is_solana_address,
            is_hex_address=cli.is_hex_address,
            transfer_executing_stale_sec=lambda: 60,
            evaluate_outbound_transfer_policy=lambda chain, to: {"allowed": True},
            watcher_run_id=lambda: "wrun_test",
            record_pending_transfer_flow=lambda approval_id, flow: None,
            mirror_transfer_approval=lambda flow: (_ for _ in ()).throw(cli.WalletStoreError("mirror failed")),
            remove_pending_transfer_flow=lambda approval_id: None,
            transfer_amount_display=lambda amount, transfer_type, symbol, decimals: ("1", "ETH"),
            enforce_spend_preconditions=lambda chain, amount: ({}, "2026-03-08", 0, 100),
            load_wallet_store=lambda: {},
            chain_wallet=lambda store, chain: (None, {"address": "0x" + "11" * 20}),
            validate_wallet_entry_shape=lambda wallet: None,
            fetch_token_balance_wei=lambda chain, wallet, token: "100",
            fetch_native_balance_wei=lambda chain, wallet: "100",
            assert_transfer_balance_preconditions=lambda **kwargs: None,
            require_wallet_passphrase_for_signing=lambda chain: "pw",
            decrypt_private_key=lambda wallet, pw: b"\x11" * 32,
            chain_rpc_url=lambda chain: "https://rpc.example",
            solana_send_native_transfer=lambda *args: "sig",
            solana_send_spl_transfer=lambda *args: {"signature": "sig"},
            cast_rpc_send_transaction=lambda *args, **kwargs: "0x" + "ab" * 32,
            require_cast_bin=lambda: "cast",
            run_subprocess=lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout='{"status":"0x1"}', stderr=""),
            cast_receipt_timeout_sec=lambda: 5,
            cast_calldata=lambda *args, **kwargs: "0xdeadbeef",
            record_spend=lambda *args, **kwargs: None,
            builder_output_from_hashes=lambda chain, hashes: {"builderCodeApplied": False},
            re_module=cli.re,
            json_loads=cli.json.loads,
            wallet_store_error=cli.WalletStoreError,
        )
        with self.assertRaises(cli.WalletStoreError) as caught:
            transfer_flows.execute_pending_transfer_flow(
                ctx,
                {
                    "approvalId": "xfr_1",
                    "chainKey": "base_sepolia",
                    "transferType": "native",
                    "amountWei": "1",
                    "toAddress": "0x" + "22" * 20,
                },
            )
        self.assertEqual(str(caught.exception), "mirror failed")

    def test_approval_prompt_service_uses_injected_patch_surfaces(self) -> None:
        ctx = approval_prompts.ApprovalPromptContext(
            ensure_app_dir=lambda: None,
            prompts_file=pathlib.Path("/tmp/approval_prompts_unused.json"),
            json_module=cli.json,
            os_module=cli.os,
            pathlib_module=cli.pathlib,
            utc_now=cli.utc_now,
            parse_iso_utc=cli._parse_iso_utc,
            get_approval_prompt=lambda trade_id: {"channel": "telegram", "updatedAt": (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()},
            record_approval_prompt=mock.Mock(),
            post_approval_prompt_metadata=mock.Mock(),
            read_openclaw_last_delivery=lambda: {"lastChannel": "telegram", "lastTo": "123", "lastThreadId": None},
            maybe_send_telegram_approval_prompt=mock.Mock(),
            trade_approval_prompt_resend_cooldown_sec=lambda: 60,
            telegram_dispatch_suppressed_for_harness=lambda: False,
            display_chain_key=cli._display_chain_key,
            transfer_amount_display=cli._transfer_amount_display,
            token_symbol_for_display=cli._token_symbol_for_display,
            is_solana_chain=cli._is_solana_chain,
            is_solana_address=cli.is_solana_address,
            solana_mint_decimals=cli._solana_mint_decimals,
            normalize_amount_human_text=cli._normalize_amount_human_text,
            format_units=cli._format_units,
            require_openclaw_bin=lambda: "openclaw",
            run_subprocess=lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout='{"payload":{"messageId":"777"}}', stderr=""),
            extract_openclaw_message_id=lambda stdout: "777",
            api_request=lambda *args, **kwargs: (200, {"ok": True}),
            wallet_store_error=cli.WalletStoreError,
            openclaw_state_dir=cli._openclaw_state_dir,
            sanitize_openclaw_agent_id=cli._sanitize_openclaw_agent_id,
            approval_wait_timeout_sec=2,
            approval_wait_poll_sec=0,
            last_delivery_is_telegram=lambda: True,
            trade_approval_inline_wait_sec=lambda: 1,
            read_trade_details=lambda trade_id: {"tradeId": trade_id, "status": "approval_pending"},
            maybe_delete_telegram_approval_prompt=lambda trade_id: None,
            maybe_send_telegram_decision_message=lambda **kwargs: None,
            remove_pending_spot_trade_flow=lambda trade_id: None,
            remove_approval_prompt=lambda trade_id: None,
            time_module=SimpleNamespace(time=mock.Mock(side_effect=[0, 0, 2]), sleep=lambda _: None),
            wallet_policy_error=cli.WalletPolicyError,
        )
        approval_prompts.maybe_send_telegram_approval_prompt(ctx, "trd_1", "base_sepolia", {"amountInHuman": "5", "tokenInSymbol": "WETH", "tokenOutSymbol": "USDC"})
        ctx.record_approval_prompt.assert_called_once()
        with self.assertRaises(cli.WalletPolicyError) as caught:
            approval_prompts.wait_for_trade_approval(ctx, "trd_1", "base_sepolia", {"tokenInSymbol": "WETH", "tokenOutSymbol": "USDC"})
        self.assertEqual(caught.exception.code, "approval_required")
        ctx.maybe_send_telegram_approval_prompt.assert_called_once()

    def test_approval_prompt_service_resend_cooldown_skips_send(self) -> None:
        sender = mock.Mock()
        recorder = mock.Mock()
        ctx = approval_prompts.ApprovalPromptContext(
            ensure_app_dir=lambda: None,
            prompts_file=pathlib.Path("/tmp/approval_prompts_unused.json"),
            json_module=cli.json,
            os_module=cli.os,
            pathlib_module=cli.pathlib,
            utc_now=cli.utc_now,
            parse_iso_utc=cli._parse_iso_utc,
            get_approval_prompt=lambda trade_id: {"channel": "telegram", "updatedAt": datetime.now(timezone.utc).isoformat()},
            record_approval_prompt=recorder,
            post_approval_prompt_metadata=mock.Mock(),
            read_openclaw_last_delivery=lambda: {"lastChannel": "telegram", "lastTo": "123", "lastThreadId": None},
            maybe_send_telegram_approval_prompt=sender,
            trade_approval_prompt_resend_cooldown_sec=lambda: 600,
            telegram_dispatch_suppressed_for_harness=lambda: False,
            display_chain_key=cli._display_chain_key,
            transfer_amount_display=cli._transfer_amount_display,
            token_symbol_for_display=cli._token_symbol_for_display,
            is_solana_chain=cli._is_solana_chain,
            is_solana_address=cli.is_solana_address,
            solana_mint_decimals=cli._solana_mint_decimals,
            normalize_amount_human_text=cli._normalize_amount_human_text,
            format_units=cli._format_units,
            require_openclaw_bin=lambda: "openclaw",
            run_subprocess=mock.Mock(),
            extract_openclaw_message_id=lambda stdout: "777",
            api_request=lambda *args, **kwargs: (200, {"ok": True}),
            wallet_store_error=cli.WalletStoreError,
            openclaw_state_dir=cli._openclaw_state_dir,
            sanitize_openclaw_agent_id=cli._sanitize_openclaw_agent_id,
            approval_wait_timeout_sec=2,
            approval_wait_poll_sec=0,
            last_delivery_is_telegram=lambda: True,
            trade_approval_inline_wait_sec=lambda: 1,
            read_trade_details=lambda trade_id: {"tradeId": trade_id, "status": "approval_pending"},
            maybe_delete_telegram_approval_prompt=lambda trade_id: None,
            maybe_send_telegram_decision_message=lambda **kwargs: None,
            remove_pending_spot_trade_flow=lambda trade_id: None,
            remove_approval_prompt=lambda trade_id: None,
            time_module=SimpleNamespace(time=lambda: 0, sleep=lambda _: None),
            wallet_policy_error=cli.WalletPolicyError,
        )
        approval_prompts.maybe_send_telegram_approval_prompt(ctx, "trd_1", "base_sepolia", {"amountInHuman": "1"})
        recorder.assert_not_called()

    def test_approval_prompt_service_wait_timeout_returns_approval_required(self) -> None:
        ctx = approval_prompts.ApprovalPromptContext(
            ensure_app_dir=lambda: None,
            prompts_file=pathlib.Path("/tmp/approval_prompts_unused.json"),
            json_module=cli.json,
            os_module=cli.os,
            pathlib_module=cli.pathlib,
            utc_now=cli.utc_now,
            parse_iso_utc=cli._parse_iso_utc,
            get_approval_prompt=lambda trade_id: None,
            record_approval_prompt=mock.Mock(),
            post_approval_prompt_metadata=mock.Mock(),
            read_openclaw_last_delivery=lambda: {"lastChannel": "telegram", "lastTo": "123", "lastThreadId": None},
            maybe_send_telegram_approval_prompt=mock.Mock(),
            trade_approval_prompt_resend_cooldown_sec=lambda: 60,
            telegram_dispatch_suppressed_for_harness=lambda: False,
            display_chain_key=cli._display_chain_key,
            transfer_amount_display=cli._transfer_amount_display,
            token_symbol_for_display=cli._token_symbol_for_display,
            is_solana_chain=cli._is_solana_chain,
            is_solana_address=cli.is_solana_address,
            solana_mint_decimals=cli._solana_mint_decimals,
            normalize_amount_human_text=cli._normalize_amount_human_text,
            format_units=cli._format_units,
            require_openclaw_bin=lambda: "openclaw",
            run_subprocess=lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout='{"payload":{"messageId":"777"}}', stderr=""),
            extract_openclaw_message_id=lambda stdout: "777",
            api_request=lambda *args, **kwargs: (200, {"ok": True}),
            wallet_store_error=cli.WalletStoreError,
            openclaw_state_dir=cli._openclaw_state_dir,
            sanitize_openclaw_agent_id=cli._sanitize_openclaw_agent_id,
            approval_wait_timeout_sec=1,
            approval_wait_poll_sec=0,
            last_delivery_is_telegram=lambda: False,
            trade_approval_inline_wait_sec=lambda: 1,
            read_trade_details=lambda trade_id: {"tradeId": trade_id, "status": "approval_pending"},
            maybe_delete_telegram_approval_prompt=lambda trade_id: None,
            maybe_send_telegram_decision_message=lambda **kwargs: None,
            remove_pending_spot_trade_flow=lambda trade_id: None,
            remove_approval_prompt=lambda trade_id: None,
            time_module=SimpleNamespace(time=mock.Mock(side_effect=[0, 0, 2]), sleep=lambda _: None),
            wallet_policy_error=cli.WalletPolicyError,
        )
        with self.assertRaises(cli.WalletPolicyError) as caught:
            approval_prompts.wait_for_trade_approval(ctx, "trd_1", "base_sepolia", {"tokenInSymbol": "WETH"})
        self.assertEqual(caught.exception.code, "approval_required")

    def test_trade_execution_service_builds_router_quote_request(self) -> None:
        quote_mock = mock.Mock(return_value={"amountOutUnits": "123", "routeKind": "router_path"})
        ctx = trade_execution.TradeExecutionServiceContext(
            require_cast_bin=lambda: "cast",
            chain_rpc_url=lambda chain: "https://rpc.example",
            run_subprocess=lambda *args, **kwargs: None,
            cast_receipt_timeout_sec=lambda: 5,
            json_module=cli.json,
            wallet_store_error=cli.WalletStoreError,
            fetch_token_allowance_wei=lambda *args: "0",
            cast_calldata=lambda *args, **kwargs: "0xdeadbeef",
            cast_rpc_send_transaction=lambda *args, **kwargs: "0x" + "ab" * 32,
            quote_trade=quote_mock,
            build_trade_plan=lambda **kwargs: kwargs,
            execute_trade_plan=lambda **kwargs: SimpleNamespace(
                tx_hash="0x" + "ab" * 32,
                approve_tx_hashes=[],
                operation_tx_hashes=["0x" + "ab" * 32],
                execution_family="amm_v2",
                execution_adapter="router",
                route_kind="router_path",
            ),
            router_get_amount_out=lambda chain, value, token_a, token_b: 123,
        )
        out = trade_execution.quote_trade_via_router_adapter(
            ctx,
            chain="base_sepolia",
            adapter_key="router",
            token_in="0x" + "11" * 20,
            token_out="0x" + "22" * 20,
            amount_in_units="100",
        )
        self.assertEqual(out.get("amountOutUnits"), "123")
        self.assertEqual(quote_mock.call_args.kwargs["chain"], "base_sepolia")

    def test_trade_execution_wait_for_receipt_success_parses_status(self) -> None:
        ctx = trade_execution.TradeExecutionServiceContext(
            require_cast_bin=lambda: "cast",
            chain_rpc_url=lambda chain: "https://rpc.example",
            run_subprocess=lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout='{\"status\":\"0x1\"}', stderr=""),
            cast_receipt_timeout_sec=lambda: 5,
            json_module=cli.json,
            wallet_store_error=cli.WalletStoreError,
            fetch_token_allowance_wei=lambda *args: "0",
            cast_calldata=lambda *args, **kwargs: "0xdeadbeef",
            cast_rpc_send_transaction=lambda *args, **kwargs: "0x" + "ab" * 32,
            quote_trade=lambda **kwargs: {},
            build_trade_plan=lambda **kwargs: kwargs,
            execute_trade_plan=lambda **kwargs: None,
            router_get_amount_out=lambda chain, value, token_a, token_b: 0,
        )
        receipt = trade_execution.wait_for_tx_receipt_success(ctx, "base_sepolia", "0x" + "ab" * 32)
        self.assertEqual(receipt.get("status"), "0x1")

    def test_execution_contracts_provider_meta_normalizes_legacy_values(self) -> None:
        provider_meta = execution_contracts.build_provider_meta(
            provider_requested="legacy_router",
            provider_used="uniswap_api",
            fallback_used=True,
            fallback_reason_value={"code": "quote_failed", "message": "x" * 600},
            route_kind="router_path",
        )
        self.assertEqual(provider_meta["providerRequested"], "router_adapter")
        self.assertEqual(provider_meta["providerUsed"], "router_adapter")
        self.assertEqual(provider_meta["routeKind"], "router_path")
        reason = execution_contracts.fallback_reason("quote_failed", "y" * 700)
        self.assertEqual(reason["code"], "quote_failed")
        self.assertEqual(len(reason["message"]), 500)

    def test_liquidity_execution_service_dispatches_advanced_intent(self) -> None:
        def claim_fees_cmd(args: object) -> int:
            print('{"txHash":"sig","liquidityOperation":"claim_fees"}')
            return 0

        ctx = liquidity_execution.LiquidityExecutionServiceContext(
            argparse_module=cli.argparse,
            json_module=cli.json,
            wallet_store_error=cli.WalletStoreError,
            build_liquidity_adapter_for_request=lambda **kwargs: SimpleNamespace(protocol_family="raydium_clmm"),
            intent_details_dict=lambda intent: {"collectAsWeth": True},
            v3_details_dict=lambda details: {},
            cmd_liquidity_increase=mock.Mock(),
            cmd_liquidity_claim_fees=claim_fees_cmd,
            cmd_liquidity_claim_rewards=mock.Mock(),
            cmd_liquidity_migrate=mock.Mock(),
        )
        payload, family = liquidity_execution.execute_liquidity_advanced_intent(
            ctx,
            {"dex": "raydium", "positionId": "pos_1"},
            "solana_mainnet_beta",
            "claim_fees",
        )
        self.assertEqual(family, "raydium_clmm")
        self.assertEqual(payload["txHash"], "sig")

    def test_runtime_state_service_round_trip_and_resolve(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            state: dict[str, object] = {}

            def load_state() -> dict[str, object]:
                return dict(state)

            def save_state(payload: dict[str, object]) -> None:
                state.clear()
                state.update(payload)

            ctx = runtime_state.RuntimeStateServiceContext(
                os_module=os,
                pathlib_module=pathlib,
                json_module=cli.json,
                ensure_app_dir=lambda: None,
                load_state=load_state,
                save_state=save_state,
                utc_now=cli.utc_now,
                pending_trade_intents_file=pathlib.Path(tmpdir) / "pending-trade-intents.json",
                pending_spot_trade_flows_file=pathlib.Path(tmpdir) / "pending-spot-trade-flows.json",
                state_file=pathlib.Path(tmpdir) / "state.json",
                env_get=lambda key: None,
                extract_agent_id_from_signed_key=lambda api_key: "ag_signed",
                wallet_store_error=cli.WalletStoreError,
            )
            runtime_state.save_agent_runtime_auth(ctx, "ag_1", "xak_test")
            self.assertEqual(runtime_state.load_agent_runtime_auth(ctx), ("ag_1", "xak_test"))
            self.assertEqual(runtime_state.resolve_api_key(ctx), "xak_test")
            self.assertEqual(runtime_state.resolve_agent_id(ctx, "xak1.ag_signed.sig.x"), "ag_1")

            runtime_state.record_pending_trade_intent(ctx, "intent_1", {"tradeId": "trd_1"})
            self.assertEqual(runtime_state.get_pending_trade_intent(ctx, "intent_1")["tradeId"], "trd_1")
            runtime_state.remove_pending_trade_intent(ctx, "intent_1")
            self.assertIsNone(runtime_state.get_pending_trade_intent(ctx, "intent_1"))

            runtime_state.record_pending_spot_trade_flow(ctx, "trd_1", {"tradeId": "trd_1"})
            self.assertEqual(runtime_state.get_pending_spot_trade_flow(ctx, "trd_1")["tradeId"], "trd_1")
            runtime_state.remove_pending_spot_trade_flow(ctx, "trd_1")
            self.assertIsNone(runtime_state.get_pending_spot_trade_flow(ctx, "trd_1"))

    def test_transfer_policy_service_normalizes_and_syncs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = pathlib.Path(tmpdir) / "transfer-policy.json"
            api_request = mock.Mock(
                return_value=(
                    200,
                    {
                        "transferPolicy": {
                            "transferApprovalMode": "AUTO",
                            "nativeTransferPreapproved": True,
                            "allowedTransferTokens": ["0x" + "11" * 20, "bad-token"],
                            "updatedAt": "2099-03-08T18:00:00+00:00",
                        }
                    },
                )
            )
            ctx = transfer_policy.TransferPolicyServiceContext(
                transfer_policy_file=path,
                read_json=lambda p: cli.json.loads(p.read_text(encoding="utf-8")),
                write_json=lambda p, payload: p.write_text(cli.json.dumps(payload), encoding="utf-8"),
                utc_now=cli.utc_now,
                re_module=cli.re,
                api_request=api_request,
                urllib_parse=cli.urllib.parse,
                datetime_cls=datetime,
            )
            normalized = transfer_policy.normalize_transfer_policy(ctx, "base_sepolia", {"allowedTransferTokens": ["0x" + "22" * 20, "BAD"]})
            self.assertEqual(normalized["allowedTransferTokens"], ["0x" + "22" * 20])
            synced = transfer_policy.sync_transfer_policy_from_remote(ctx, "base_sepolia")
            self.assertEqual(synced["transferApprovalMode"], "auto")
            self.assertTrue(synced["nativeTransferPreapproved"])
            self.assertEqual(synced["allowedTransferTokens"], ["0x" + "11" * 20])

    def test_trade_caps_service_records_and_queues_usage(self) -> None:
        state_store: dict[str, object] = {}
        outbox: list[dict[str, object]] = []

        def load_state() -> dict[str, object]:
            return dict(state_store)

        def save_state(payload: dict[str, object]) -> None:
            state_store.clear()
            state_store.update(payload)

        ctx = trade_caps.TradeCapsServiceContext(
            load_state=load_state,
            save_state=save_state,
            utc_now=cli.utc_now,
            decimal_text=cli._decimal_text,
            to_non_negative_decimal=cli._to_non_negative_decimal,
            to_non_negative_int=cli._to_non_negative_int,
            load_trade_usage_outbox=lambda: list(outbox),
            save_trade_usage_outbox=lambda items: (outbox.clear(), outbox.extend(items)),
            api_request=lambda *args, **kwargs: (500, {"code": "api_error", "message": "down"}),
            resolve_api_key=lambda: "xak_test",
            resolve_agent_id=lambda api_key: "ag_1",
            token_hex=lambda n: "abcd1234",
            wallet_store_error=cli.WalletStoreError,
        )
        state = load_state()
        trade_caps.record_trade_cap_ledger(ctx, state, "base_sepolia", "2026-03-08", Decimal("12.5"), 2)
        spend, filled = trade_caps.load_trade_cap_ledger(ctx, state_store, "base_sepolia", "2026-03-08")
        self.assertEqual(spend, Decimal("12.5"))
        self.assertEqual(filled, 2)
        with self.assertRaises(cli.WalletStoreError):
            trade_caps.post_trade_usage(ctx, "base_sepolia", "2026-03-08", Decimal("1.25"), 1)
        self.assertEqual(len(outbox), 1)

    def test_trade_caps_service_replay_partial_success_keeps_remaining(self) -> None:
        outbox = [
            {"idempotencyKey": "idem_1", "payload": {"a": 1}},
            {"idempotencyKey": "idem_2", "payload": {"a": 2}},
            {"payload": {"bad": 1}},
        ]
        ctx = trade_caps.TradeCapsServiceContext(
            load_state=lambda: {},
            save_state=lambda payload: None,
            utc_now=cli.utc_now,
            decimal_text=cli._decimal_text,
            to_non_negative_decimal=cli._to_non_negative_decimal,
            to_non_negative_int=cli._to_non_negative_int,
            load_trade_usage_outbox=lambda: list(outbox),
            save_trade_usage_outbox=lambda items: (outbox.clear(), outbox.extend(items)),
            api_request=mock.Mock(side_effect=[(200, {"ok": True}), (503, {"message": "down"})]),
            resolve_api_key=lambda: "xak_test",
            resolve_agent_id=lambda api_key: "ag_1",
            token_hex=lambda n: "abcd1234",
            wallet_store_error=cli.WalletStoreError,
        )
        replayed, remaining = trade_caps.replay_trade_usage_outbox(ctx)
        self.assertEqual((replayed, remaining), (1, 1))
        self.assertEqual(len(outbox), 1)
        self.assertEqual(outbox[0]["idempotencyKey"], "idem_2")

    def test_trade_caps_service_post_usage_missing_agent_id_fails_closed(self) -> None:
        ctx = trade_caps.TradeCapsServiceContext(
            load_state=lambda: {},
            save_state=lambda payload: None,
            utc_now=cli.utc_now,
            decimal_text=cli._decimal_text,
            to_non_negative_decimal=cli._to_non_negative_decimal,
            to_non_negative_int=cli._to_non_negative_int,
            load_trade_usage_outbox=lambda: [],
            save_trade_usage_outbox=lambda items: None,
            api_request=lambda *args, **kwargs: (200, {"ok": True}),
            resolve_api_key=lambda: "xak_test",
            resolve_agent_id=lambda api_key: "",
            token_hex=lambda n: "abcd1234",
            wallet_store_error=cli.WalletStoreError,
        )
        with self.assertRaises(cli.WalletStoreError) as caught:
            trade_caps.post_trade_usage(ctx, "base_sepolia", "2026-03-08", Decimal("1"), 1)
        self.assertIn("could not be resolved", str(caught.exception))

    def test_trade_caps_service_post_usage_malformed_error_body_is_deterministic(self) -> None:
        outbox: list[dict[str, object]] = []
        ctx = trade_caps.TradeCapsServiceContext(
            load_state=lambda: {},
            save_state=lambda payload: None,
            utc_now=cli.utc_now,
            decimal_text=cli._decimal_text,
            to_non_negative_decimal=cli._to_non_negative_decimal,
            to_non_negative_int=cli._to_non_negative_int,
            load_trade_usage_outbox=lambda: list(outbox),
            save_trade_usage_outbox=lambda items: (outbox.clear(), outbox.extend(items)),
            api_request=lambda *args, **kwargs: (500, "bad-body"),
            resolve_api_key=lambda: "xak_test",
            resolve_agent_id=lambda api_key: "ag_1",
            token_hex=lambda n: "abcd1234",
            wallet_store_error=cli.WalletStoreError,
        )
        with self.assertRaises(cli.WalletStoreError) as caught:
            trade_caps.post_trade_usage(ctx, "base_sepolia", "2026-03-08", Decimal("1"), 1)
        self.assertIn("trade usage report failed (500)", str(caught.exception))
        self.assertEqual(len(outbox), 1)

    def test_telegram_delivery_resolves_bot_token_from_env(self) -> None:
        ctx = telegram_delivery.TelegramDeliveryServiceContext(
            telegram_dispatch_suppressed_for_harness=lambda: False,
            read_openclaw_last_delivery=lambda: None,
            get_approval_prompt=lambda trade_id: None,
            get_transfer_approval_prompt=lambda approval_id: None,
            get_policy_approval_prompt=lambda approval_id: None,
            record_approval_prompt=lambda *args, **kwargs: None,
            record_transfer_approval_prompt=lambda *args, **kwargs: None,
            record_policy_approval_prompt=lambda *args, **kwargs: None,
            require_openclaw_bin=lambda: "openclaw",
            run_subprocess=lambda *args, **kwargs: None,
            wallet_store_error=cli.WalletStoreError,
            extract_openclaw_message_id=lambda stdout: None,
            utc_now=cli.utc_now,
            display_chain_key=cli._display_chain_key,
            token_symbol_for_display=cli._token_symbol_for_display,
            is_solana_chain=cli._is_solana_chain,
            is_solana_address=cli.is_solana_address,
            solana_mint_decimals=cli._solana_mint_decimals,
            normalize_amount_human_text=cli._normalize_amount_human_text,
            format_units=cli._format_units,
            canonical_token_map=cli._canonical_token_map,
            shutil_module=cli.shutil,
            re_module=cli.re,
            clear_telegram_approval_buttons=lambda subject_type, subject_id: {},
            remove_approval_prompt=lambda trade_id: None,
            remove_transfer_approval_prompt=lambda approval_id: None,
            remove_policy_approval_prompt=lambda approval_id: None,
        )
        with mock.patch.dict(os.environ, {"XCLAW_TELEGRAM_BOT_TOKEN": "tok_1"}, clear=False):
            self.assertEqual(telegram_delivery.resolve_telegram_bot_token(ctx), "tok_1")

    def test_owner_link_delivery_skips_telegram(self) -> None:
        ctx = owner_link_delivery.OwnerLinkDeliveryServiceContext(
            read_openclaw_last_delivery=lambda: {"lastChannel": "telegram", "lastTo": "123", "lastThreadId": None},
            shutil_module=cli.shutil,
            run_subprocess=lambda *args, **kwargs: None,
            extract_openclaw_message_id=lambda stdout: None,
        )
        result = owner_link_delivery.maybe_send_owner_link_to_active_chat(ctx, "https://xclaw.trade/agents/ag_1?token=ol1.test", "2026-02-18T16:39:52.313Z")
        self.assertFalse(bool(result.get("sent")))
        self.assertEqual(result.get("reason"), "telegram_channel_skipped")

    def test_agent_api_ack_transfer_decision_inbox_includes_reason_fields(self) -> None:
        api_request = mock.Mock(return_value=(200, {"ok": True}))
        agent_api.ack_transfer_decision_inbox(api_request, "dec_1", "applied", "ok", "done")
        self.assertEqual(api_request.call_args.args[:2], ("POST", "/agent/transfer-decisions/inbox"))
        payload = api_request.call_args.kwargs["payload"]
        self.assertEqual(payload["decisionId"], "dec_1")
        self.assertEqual(payload["reasonCode"], "ok")
        self.assertEqual(payload["reasonMessage"], "done")

    def test_agent_api_publish_runtime_signing_readiness_normalizes_fields(self) -> None:
        api_request = mock.Mock(return_value=(200, {"ok": True}))
        agent_api.publish_runtime_signing_readiness(
            api_request,
            "base_sepolia",
            {"walletSigningReady": 1, "walletSigningReasonCode": "missing_passphrase", "walletSigningCheckedAt": "2026-03-08T00:00:00+00:00"},
        )
        self.assertEqual(api_request.call_args.args[:2], ("POST", "/agent/runtime-readiness"))
        payload = api_request.call_args.kwargs["payload"]
        self.assertTrue(payload["walletSigningReady"])
        self.assertEqual(payload["walletSigningReasonCode"], "missing_passphrase")

    def test_agent_api_resolve_agent_id_or_fail_raises_when_missing(self) -> None:
        with self.assertRaises(cli.WalletStoreError):
            agent_api.resolve_agent_id_or_fail(lambda: "xak_test", lambda api_key: "", cli.WalletStoreError)

    def test_mirroring_required_delivery_retries_then_raises_deterministically(self) -> None:
        api_request = mock.Mock(side_effect=[(500, "bad-body"), (500, {"message": "still down"})])
        with self.assertRaises(cli.WalletStoreError) as caught:
            mirroring.mirror_transfer_approval(
                flow={"approvalId": "xfr_1", "chainKey": "base_sepolia"},
                require_delivery=True,
                api_request=api_request,
                utc_now=lambda: "2026-03-08T00:00:00+00:00",
                watcher_run_id=lambda: "wrun_test",
                token_hex=lambda n: "abc12345",
                wallet_store_error=cli.WalletStoreError,
            )
        self.assertEqual(str(caught.exception), "api_error: still down")
        self.assertEqual(api_request.call_count, 2)

    def test_mirroring_best_effort_swallows_failures(self) -> None:
        api_request = mock.Mock(side_effect=RuntimeError("network down"))
        ok = mirroring.mirror_transfer_approval(
            flow={"approvalId": "xfr_1", "chainKey": "base_sepolia"},
            require_delivery=False,
            api_request=api_request,
            utc_now=lambda: "2026-03-08T00:00:00+00:00",
            watcher_run_id=lambda: "wrun_test",
            token_hex=lambda n: "abc12345",
            wallet_store_error=cli.WalletStoreError,
        )
        self.assertFalse(ok)

    def test_mirroring_x402_outbound_sets_payment_id_and_swallows_errors(self) -> None:
        flow = {
            "approvalId": "x402_1",
            "network": "base_sepolia",
            "facilitator": "cdp",
            "url": "https://example.com",
            "amountAtomic": "123",
        }
        api_request = mock.Mock(side_effect=[RuntimeError("down")])
        mirroring.mirror_x402_outbound(
            flow=flow,
            api_request=api_request,
            utc_now=lambda: "2026-03-08T00:00:00+00:00",
            token_hex=lambda n: "abcd123456",
        )
        self.assertEqual(flow["paymentId"], "xpm_abcd123456")

    def test_reporting_service_trade_status_non_2xx_with_malformed_body_is_deterministic(self) -> None:
        ctx = reporting.ReportingServiceContext(
            api_request=mock.Mock(return_value=(500, "nope")),
            wallet_store_error=cli.WalletStoreError,
            parse_decision_at=lambda value: value or "2026-03-08T00:00:00+00:00",
            utc_now=lambda: "2026-03-08T00:00:01+00:00",
            watcher_run_id=lambda: "wrun_test",
            canonical_event_for_trade_status=lambda status: f"trade.{status}",
        )
        with self.assertRaises(cli.WalletStoreError) as caught:
            reporting.post_trade_status(ctx, trade_id="trd_1", from_status="approved", to_status="failed")
        self.assertIn("trade status update failed (500)", str(caught.exception))

    def test_reporting_service_liquidity_status_non_2xx_with_malformed_body_is_deterministic(self) -> None:
        ctx = reporting.ReportingServiceContext(
            api_request=mock.Mock(return_value=(502, "nope")),
            wallet_store_error=cli.WalletStoreError,
            parse_decision_at=lambda value: value or "2026-03-08T00:00:00+00:00",
            utc_now=lambda: "2026-03-08T00:00:01+00:00",
            watcher_run_id=lambda: "wrun_test",
            canonical_event_for_trade_status=lambda status: f"trade.{status}",
        )
        with self.assertRaises(cli.WalletStoreError) as caught:
            reporting.post_liquidity_status(ctx, liquidity_intent_id="liq_1", to_status="failed")
        self.assertIn("liquidity status update failed (502)", str(caught.exception))

    def test_reporting_service_read_trade_details_fails_closed_on_missing_trade(self) -> None:
        ctx = reporting.ReportingServiceContext(
            api_request=mock.Mock(return_value=(200, {"notTrade": {}})),
            wallet_store_error=cli.WalletStoreError,
            parse_decision_at=lambda value: value or "2026-03-08T00:00:00+00:00",
            utc_now=lambda: "2026-03-08T00:00:01+00:00",
            watcher_run_id=lambda: "wrun_test",
            canonical_event_for_trade_status=lambda status: f"trade.{status}",
        )
        with self.assertRaises(cli.WalletStoreError) as caught:
            reporting.read_trade_details(ctx, "trd_1")
        self.assertIn("missing trade object", str(caught.exception).lower())

    def test_reporting_service_limit_order_status_queues_on_failure(self) -> None:
        queue = mock.Mock()
        reporting.post_limit_order_status(
            order_id="ord_1",
            payload={"status": "filled"},
            queue_on_failure=True,
            api_request=mock.Mock(return_value=(503, {"message": "down"})),
            queue_limit_order_action=queue,
            wallet_store_error=cli.WalletStoreError,
        )
        queue.assert_called_once()

    def test_reporting_service_execution_report_non_2xx_is_deterministic(self) -> None:
        ctx = reporting.ReportingServiceContext(
            api_request=mock.Mock(
                side_effect=[
                    (200, {"trade": {"tradeId": "trd_1", "agentId": "ag_1", "status": "failed", "mode": "real", "chainKey": "base_sepolia"}}),
                    (500, "bad-body"),
                ]
            ),
            wallet_store_error=cli.WalletStoreError,
            parse_decision_at=lambda value: value or "2026-03-08T00:00:00+00:00",
            utc_now=lambda: "2026-03-08T00:00:01+00:00",
            watcher_run_id=lambda: "wrun_test",
            canonical_event_for_trade_status=lambda status: f"trade.{status}",
        )
        with self.assertRaises(cli.WalletStoreError) as caught:
            reporting.send_trade_execution_report_via_context(ctx, trade_id="trd_1")
        self.assertIn("report send failed (500)", str(caught.exception))

    def test_reporting_service_posts_trade_status_with_watcher_metadata(self) -> None:
        api_request = mock.Mock(return_value=(200, {"ok": True}))
        ctx = reporting.ReportingServiceContext(
            api_request=api_request,
            wallet_store_error=cli.WalletStoreError,
            parse_decision_at=lambda value: value or "2026-03-08T00:00:00+00:00",
            utc_now=lambda: "2026-03-08T00:00:01+00:00",
            watcher_run_id=lambda: "wrun_test",
            canonical_event_for_trade_status=lambda status: f"trade.{status}",
        )
        reporting.post_trade_status(
            ctx,
            trade_id="trd_1",
            from_status="approved",
            to_status="filled",
            extra={"txHash": "0x" + "ab" * 32},
            idempotency_key="idem_1",
        )
        self.assertEqual(api_request.call_args.args[:2], ("POST", "/trades/trd_1/status"))
        payload = api_request.call_args.kwargs["payload"]
        self.assertEqual(payload["watcherRunId"], "wrun_test")
        self.assertEqual(payload["txHash"], "0x" + "ab" * 32)
        self.assertEqual(api_request.call_args.kwargs["idempotency_key"], "idem_1")

    def test_reporting_service_reads_trade_details_and_sends_execution_report(self) -> None:
        api_request = mock.Mock(
            side_effect=[
                (200, {"trade": {"tradeId": "trd_1", "agentId": "ag_1", "status": "filled", "mode": "real", "chainKey": "base_sepolia"}}),
                (200, {"trade": {"tradeId": "trd_1", "agentId": "ag_1", "status": "filled", "mode": "real", "chainKey": "base_sepolia"}}),
                (200, {"ok": True}),
            ]
        )
        ctx = reporting.ReportingServiceContext(
            api_request=api_request,
            wallet_store_error=cli.WalletStoreError,
            parse_decision_at=lambda value: value or "2026-03-08T00:00:00+00:00",
            utc_now=lambda: "2026-03-08T00:00:01+00:00",
            watcher_run_id=lambda: "wrun_test",
            canonical_event_for_trade_status=lambda status: f"trade.{status}",
        )
        trade = reporting.read_trade_details(ctx, "trd_1")
        self.assertEqual(trade["tradeId"], "trd_1")
        result = reporting.send_trade_execution_report_via_context(ctx, trade_id="trd_1")
        self.assertTrue(result["ok"])
        self.assertEqual(result["eventType"], "trade.filled")
        self.assertEqual(api_request.call_args.args[:2], ("POST", "/events"))

    def test_reporting_service_posts_liquidity_status_without_none_fields(self) -> None:
        api_request = mock.Mock(return_value=(200, {"ok": True}))
        ctx = reporting.ReportingServiceContext(
            api_request=api_request,
            wallet_store_error=cli.WalletStoreError,
            parse_decision_at=lambda value: value or "2026-03-08T00:00:00+00:00",
            utc_now=lambda: "2026-03-08T00:00:01+00:00",
            watcher_run_id=lambda: "wrun_test",
            canonical_event_for_trade_status=lambda status: f"trade.{status}",
        )
        reporting.post_liquidity_status(
            ctx,
            liquidity_intent_id="liq_1",
            to_status="filled",
            extra={"txHash": "0x1", "receipt": None},
        )
        self.assertEqual(api_request.call_args.args[:2], ("POST", "/liquidity/liq_1/status"))
        payload = api_request.call_args.kwargs["payload"]
        self.assertEqual(payload, {"status": "filled", "txHash": "0x1"})


if __name__ == "__main__":
    unittest.main()
