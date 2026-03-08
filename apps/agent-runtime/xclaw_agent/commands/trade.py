from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from xclaw_agent.runtime import errors as runtime_errors
from xclaw_agent.runtime import preconditions as runtime_preconditions
from xclaw_agent.runtime import validators as runtime_validators
from xclaw_agent.runtime.execution import evm as evm_execution
from xclaw_agent.runtime.execution import solana as solana_execution


def cmd_trade_spot(rt: Any, args: Any) -> int:
    chk = rt.require_json_flag(args)
    if chk is not None:
        return chk

    chain = args.chain
    trade_id: str | None = None
    provider_requested, _ = rt._trade_provider_settings(chain)
    provider_used = "router_adapter"
    fallback_used = False
    fallback_reason: dict[str, str] | None = None
    uniswap_route_type: str | None = None
    try:
        if rt._is_solana_chain(chain):
            token_in = rt._resolve_token_address(chain, args.token_in)
            token_out = rt._resolve_token_address(chain, args.token_out)
            try:
                runtime_validators.require_distinct_trade_assets(token_in, token_out, chain)
                slippage_bps = runtime_validators.parse_slippage_bps(args.slippage_bps)
            except runtime_errors.RuntimeCommandFailure as exc:
                return runtime_errors.emit_failure(rt, exc)
            amount_in_units = solana_execution.solana_amount_units_or_fail(rt, str(args.amount_in))
            amount_in_int = int(amount_in_units)
            state, day_key, current_spend, max_daily_wei = rt._enforce_spend_preconditions(chain, amount_in_int, enforce_native_cap=False)
            amount_in_human = rt._normalize_amount_human_text(amount_in_units)
            try:
                token_in_decimals = rt._solana_mint_decimals(chain, token_in)
                amount_in_human = rt._normalize_amount_human_text(rt._format_units(amount_in_int, token_in_decimals))
            except Exception:
                pass
            summary = {
                "tradeId": None,
                "chainKey": chain,
                "tokenInSymbol": str(args.token_in),
                "tokenOutSymbol": str(args.token_out),
                "amountInHuman": amount_in_human,
                "slippageBps": slippage_bps,
            }
            proposed = rt._post_trade_proposed(chain, token_in, token_out, amount_in_units, slippage_bps, amount_out_human=None, reason="trade_spot_solana")
            trade_id = str(proposed.get("tradeId") or "")
            if not trade_id:
                raise rt.WalletStoreError("Trade proposal did not return a tradeId.")
            summary["tradeId"] = trade_id
            if str(proposed.get("status") or "") != "approved":
                rt._wait_for_trade_approval(trade_id, chain, summary)
            execution = solana_execution.execute_solana_trade(
                rt,
                chain=chain,
                trade_id=trade_id,
                token_in=token_in,
                token_out=token_out,
                amount_in_units=amount_in_units,
                slippage_bps=slippage_bps,
                from_status="approved",
            )
            rt._record_spend(state, chain, day_key, current_spend + amount_in_int)
            return rt.ok(
                "Spot swap executed on-chain via runtime-local Solana adapter.",
                chain=chain,
                tokenIn=token_in,
                tokenOut=token_out,
                amountInUnits=amount_in_units,
                expectedOutUnits=str(execution.get("amountOutUnits") or "0"),
                txHash=execution.get("txHash"),
                signature=execution.get("signature"),
                providerRequested=execution.get("providerRequested"),
                providerUsed=execution.get("providerUsed"),
                fallbackUsed=execution.get("fallbackUsed"),
                fallbackReason=execution.get("fallbackReason"),
                executionFamily=execution.get("executionFamily"),
                executionAdapter=execution.get("executionAdapter"),
                routeKind=execution.get("routeKind"),
                day=day_key,
                dailySpendWei=str(current_spend + amount_in_int),
                maxDailyNativeWei=str(max_daily_wei),
            )

        try:
            rt._replay_trade_usage_outbox()
        except Exception:
            pass
        token_in = rt._resolve_token_address(chain, args.token_in)
        token_out = rt._resolve_token_address(chain, args.token_out)
        try:
            runtime_validators.require_distinct_trade_assets(token_in, token_out, chain)
            slippage_bps = runtime_validators.parse_slippage_bps(args.slippage_bps)
        except runtime_errors.RuntimeCommandFailure as exc:
            return runtime_errors.emit_failure(rt, exc)

        wallet_address, private_key_hex, adapter_key = evm_execution.resolve_trade_execution_context(rt, chain)
        cast_bin = rt._require_cast_bin()
        rpc_url = rt._chain_rpc_url(chain)

        token_in_meta = rt._fetch_erc20_metadata(chain, token_in)
        token_out_meta = rt._fetch_erc20_metadata(chain, token_out)
        token_in_decimals = int(token_in_meta.get("decimals", 18))
        token_out_decimals = int(token_out_meta.get("decimals", 18))

        amount_in_units, amount_in_mode = rt._parse_amount_in_units(str(args.amount_in), token_in_decimals)
        amount_in_int = int(amount_in_units)
        state, day_key, current_spend, max_daily_wei = rt._enforce_spend_preconditions(chain, amount_in_int, enforce_native_cap=False)

        quote_payload = rt._quote_trade_via_router_adapter(chain=chain, adapter_key=adapter_key, token_in=token_in, token_out=token_out, amount_in_units=amount_in_units)
        expected_out_int = int(str(quote_payload.get("amountOutUnits") or "0"))
        uniswap_route_type = str(quote_payload.get("routeKind") or "").strip() or None
        min_out_int = (expected_out_int * (10000 - slippage_bps)) // 10000
        if min_out_int <= 0:
            raise rt.WalletStoreError("Computed amountOutMin is zero; reduce slippage or increase amount.")
        amount_in_human = rt._to_non_negative_decimal(rt._format_units(int(amount_in_units), token_in_decimals))
        expected_out_human = rt._to_non_negative_decimal(rt._format_units(int(expected_out_int), token_out_decimals))
        projected_spend_usd = rt._projected_trade_spend_usd(token_in_meta.get("symbol"), token_out_meta.get("symbol"), amount_in_human, expected_out_human)
        cap_state, _, current_spend_usd, current_filled_trades, trade_caps = rt._enforce_trade_caps(chain, projected_spend_usd, 1)

        amount_in_for_server = str(args.amount_in).strip()
        if amount_in_mode == "base_units":
            amount_in_for_server = rt._format_units(int(amount_in_units), token_in_decimals)

        summary = {
            "tradeId": None,
            "chainKey": chain,
            "tokenInSymbol": str(token_in_meta.get("symbol") or "").strip() or str(token_in),
            "tokenOutSymbol": str(token_out_meta.get("symbol") or "").strip() or str(token_out),
            "amountInHuman": rt._normalize_amount_human_text(amount_in_for_server),
            "slippageBps": slippage_bps,
        }

        intent_key = rt._trade_intent_key(chain, token_in, token_out, amount_in_for_server, slippage_bps)
        existing_intent = rt._get_pending_trade_intent(intent_key)
        if existing_intent:
            existing_trade_id = str(existing_intent.get("tradeId") or "").strip()
            if existing_trade_id:
                try:
                    existing_trade = rt._read_trade_details(existing_trade_id)
                except Exception:
                    existing_trade = None
                status = str((existing_trade or {}).get("status") or "")
                if status == "approval_pending":
                    trade_id = existing_trade_id
                    summary["tradeId"] = trade_id
                    rt._record_pending_spot_trade_flow(
                        trade_id,
                        {
                            "tradeId": trade_id,
                            "chainKey": chain,
                            "tokenIn": token_in.lower(),
                            "tokenOut": token_out.lower(),
                            "tokenInSymbol": str(token_in_meta.get("symbol") or "").strip() or str(token_in),
                            "tokenOutSymbol": str(token_out_meta.get("symbol") or "").strip() or str(token_out),
                            "amountInHuman": rt._normalize_amount_human_text(amount_in_for_server),
                            "slippageBps": slippage_bps,
                            "source": "trade_spot_existing_pending",
                            "createdAt": rt.utc_now(),
                        },
                    )
                    rt._wait_for_trade_approval(trade_id, chain, summary)
                    rt._remove_pending_trade_intent(intent_key)
                else:
                    rt._remove_pending_trade_intent(intent_key)

        if not trade_id:
            proposed = rt._post_trade_proposed(chain, token_in, token_out, amount_in_for_server, slippage_bps, amount_out_human=rt._decimal_text(expected_out_human), reason="trade_spot")
            trade_id = str(proposed.get("tradeId") or "")
            if not trade_id:
                raise rt.WalletStoreError("Trade proposal did not return a tradeId.")
            summary["tradeId"] = trade_id
            proposed_status = str(proposed.get("status") or "")
            if proposed_status != "approved":
                rt._record_pending_trade_intent(
                    intent_key,
                    {
                        "tradeId": trade_id,
                        "chainKey": chain,
                        "tokenIn": token_in.lower(),
                        "tokenOut": token_out.lower(),
                        "amountInHuman": rt._normalize_amount_human_text(amount_in_for_server),
                        "slippageBps": slippage_bps,
                        "createdAt": rt.utc_now(),
                        "lastSeenStatus": proposed_status,
                    },
                )
                rt._record_pending_spot_trade_flow(
                    trade_id,
                    {
                        "tradeId": trade_id,
                        "chainKey": chain,
                        "tokenIn": token_in.lower(),
                        "tokenOut": token_out.lower(),
                        "tokenInSymbol": str(token_in_meta.get("symbol") or "").strip() or str(token_in),
                        "tokenOutSymbol": str(token_out_meta.get("symbol") or "").strip() or str(token_out),
                        "amountInHuman": rt._normalize_amount_human_text(amount_in_for_server),
                        "slippageBps": slippage_bps,
                        "source": "trade_spot_proposed_pending",
                        "createdAt": rt.utc_now(),
                    },
                )
                rt._wait_for_trade_approval(trade_id, chain, summary)
                rt._remove_pending_trade_intent(intent_key)
            else:
                rt._remove_pending_trade_intent(intent_key)

        quote_payload = rt._quote_trade_via_router_adapter(chain=chain, adapter_key=adapter_key, token_in=token_in, token_out=token_out, amount_in_units=amount_in_units)
        expected_out_int = int(str(quote_payload.get("amountOutUnits") or "0"))
        uniswap_route_type = str(quote_payload.get("routeKind") or "").strip() or uniswap_route_type
        min_out_int = (expected_out_int * (10000 - slippage_bps)) // 10000
        if min_out_int <= 0:
            raise rt.WalletStoreError("Computed amountOutMin is zero after approval; reduce slippage or increase amount.")
        expected_out_human = rt._to_non_negative_decimal(rt._format_units(int(expected_out_int), token_out_decimals))

        deadline_sec = int(args.deadline_sec)
        if deadline_sec < 30 or deadline_sec > 3600:
            return runtime_errors.emit_failure(
                rt,
                runtime_errors.invalid_input("deadline-sec must be between 30 and 3600.", "Use a value like 120.", {"deadlineSec": args.deadline_sec}),
            )
        deadline = str(int(datetime.now(timezone.utc).timestamp()) + deadline_sec)

        to_addr = str(args.to or "").strip() or wallet_address
        if not rt.is_hex_address(to_addr):
            return runtime_errors.emit_failure(
                rt,
                runtime_errors.invalid_input(
                    "to must be a valid 0x address.",
                    "Provide a 0x-prefixed 20-byte hex address or omit to default to the execution wallet.",
                    {"to": args.to},
                ),
            )

        execution = evm_execution.execute_trade_via_router_adapter(
            rt,
            chain=chain,
            adapter_key=adapter_key,
            wallet_address=wallet_address,
            private_key_hex=private_key_hex,
            token_in=token_in,
            token_out=token_out,
            amount_in_units=amount_in_units,
            min_out_units=str(min_out_int),
            deadline=deadline,
            recipient=to_addr,
            wait_for_receipt=False,
        )
        approve_tx_hashes = execution.get("approveTxHashes") or []
        approve_tx_hash = str(approve_tx_hashes[-1]) if isinstance(approve_tx_hashes, list) and approve_tx_hashes else None
        tx_hash = str(execution.get("txHash") or "")
        if not rt.re.fullmatch(r"0x[a-fA-F0-9]{64}", tx_hash):
            raise rt.WalletStoreError("trade_execution_failed: missing txHash from router adapter execution.")
        uniswap_route_type = str(execution.get("routeKind") or "").strip() or None
        execution_family = str(execution.get("executionFamily") or "").strip() or "amm_v2"
        execution_adapter = str(execution.get("executionAdapter") or "").strip() or adapter_key
        provider_meta = rt._build_provider_meta(provider_requested, provider_used, fallback_used, fallback_reason, uniswap_route_type)
        rt._post_trade_status(trade_id, "approved", "executing", {"txHash": tx_hash, **provider_meta})
        rt._post_trade_status(trade_id, "executing", "verifying", {"txHash": tx_hash, **provider_meta})

        receipt_proc = rt._run_subprocess([cast_bin, "receipt", "--json", "--rpc-url", rpc_url, tx_hash], timeout_sec=rt._cast_receipt_timeout_sec(), kind="cast_receipt")
        if receipt_proc.returncode != 0:
            stderr = (receipt_proc.stderr or "").strip()
            stdout = (receipt_proc.stdout or "").strip()
            raise rt.WalletStoreError(stderr or stdout or "cast receipt failed.")
        receipt_payload = rt.json.loads((receipt_proc.stdout or "{}").strip() or "{}")
        receipt_status = str(receipt_payload.get("status", "0x0")).lower()
        if receipt_status not in {"0x1", "1"}:
            raise rt.WalletStoreError(f"On-chain receipt indicates failure status '{receipt_status}'.")

        rt._record_spend(state, chain, day_key, current_spend + amount_in_int)
        rt._record_trade_cap_ledger(cap_state, chain, day_key, current_spend_usd + projected_spend_usd, current_filled_trades + 1)
        try:
            rt._post_trade_usage(chain, day_key, projected_spend_usd, 1)
        except Exception:
            pass
        rt._post_trade_status(
            trade_id,
            "verifying",
            "filled",
            {
                "txHash": tx_hash,
                "amountOut": rt._format_units(int(expected_out_int), token_out_decimals),
                "observationSource": "rpc_receipt",
                "confirmationCount": 1,
                "observedAt": rt.utc_now(),
                **provider_meta,
            },
        )
        rt._remove_pending_spot_trade_flow(trade_id)

        builder_meta = rt._builder_output_from_hashes(chain, [approve_tx_hash, tx_hash])
        return rt.ok(
            "Spot swap executed on-chain via runtime-local router adapter.",
            chain=chain,
            router=str(rt.resolve_trade_execution_adapter(chain, "")[1].get("router") or "").strip(),
            fromAddress=wallet_address,
            toAddress=to_addr,
            tokenIn=token_in,
            tokenOut=token_out,
            amountInUnits=amount_in_units,
            expectedOutUnits=str(expected_out_int),
            amountOutMinUnits=str(min_out_int),
            slippageBps=slippage_bps,
            deadline=deadline,
            approveTxHash=approve_tx_hash,
            txHash=tx_hash,
            amountIn=rt._format_units(int(amount_in_units), token_in_decimals),
            expectedOut=rt._format_units(int(expected_out_int), token_out_decimals),
            amountOutMin=rt._format_units(int(min_out_int), token_out_decimals),
            amountInPretty=rt._format_units_pretty(int(amount_in_units), token_in_decimals),
            expectedOutPretty=rt._format_units_pretty(int(expected_out_int), token_out_decimals),
            amountOutMinPretty=rt._format_units_pretty(int(min_out_int), token_out_decimals),
            amountInInputMode=amount_in_mode,
            tokenInDecimals=token_in_decimals,
            tokenOutDecimals=token_out_decimals,
            tokenInSymbol=token_in_meta.get("symbol"),
            tokenOutSymbol=token_out_meta.get("symbol"),
            dailySpendUsd=rt._decimal_text(current_spend_usd + projected_spend_usd),
            maxDailyUsd=trade_caps.get("maxDailyUsd"),
            dailyFilledTrades=int(current_filled_trades + 1),
            maxDailyTradeCount=trade_caps.get("maxDailyTradeCount"),
            day=day_key,
            dailySpendWei=str(current_spend + amount_in_int),
            maxDailyNativeWei=str(max_daily_wei),
            providerRequested=provider_requested,
            providerUsed=provider_used,
            fallbackUsed=fallback_used,
            fallbackReason=fallback_reason,
            executionFamily=execution_family,
            executionAdapter=execution_adapter,
            routeKind=uniswap_route_type,
            **builder_meta,
        )
    except rt.WalletPolicyError as exc:
        return rt.fail(exc.code, str(exc), exc.action_hint, exc.details, exit_code=1)
    except rt.WalletStoreError as exc:
        return rt.fail(
            "trade_spot_failed",
            str(exc),
            "Verify approval state, wallet setup, and local chain connectivity.",
            {
                "chain": chain,
                "providerRequested": provider_requested,
                "providerUsed": provider_used,
                "fallbackUsed": fallback_used,
                "fallbackReason": fallback_reason,
                "routeKind": uniswap_route_type,
            },
            exit_code=1,
        )
    except Exception as exc:
        return rt.fail(
            "trade_spot_failed",
            str(exc),
            "Inspect runtime trade-spot path and retry.",
            {
                "chain": chain,
                "providerRequested": provider_requested,
                "providerUsed": provider_used,
                "fallbackUsed": fallback_used,
                "fallbackReason": fallback_reason,
                "routeKind": uniswap_route_type,
            },
            exit_code=1,
        )


def cmd_trade_execute(rt: Any, args: Any) -> int:
    chk = rt.require_json_flag(args)
    if chk is not None:
        return chk

    transition_state = "init"
    previous_status = "approved"
    provider_requested, _ = rt._trade_provider_settings(args.chain)
    provider_used = "router_adapter"
    fallback_used = False
    fallback_reason: dict[str, str] | None = None
    uniswap_route_type: str | None = None
    try:
        trade = rt._read_trade_details(args.intent)
        runtime_preconditions.ensure_trade_chain_match(trade, requested_chain=args.chain, trade_id=args.intent)
        status = str(trade.get("status"))
        retry = trade.get("retry") if isinstance(trade.get("retry"), dict) else {}
        runtime_preconditions.ensure_trade_actionable(rt, trade_id=args.intent, status=status, retry=retry)

        if rt._is_solana_chain(args.chain):
            token_in = rt._resolve_token_address(args.chain, str(trade.get("tokenIn") or ""))
            token_out = rt._resolve_token_address(args.chain, str(trade.get("tokenOut") or ""))
            amount_in_units = solana_execution.solana_amount_units_or_fail(rt, str(trade.get("amountIn") or ""))
            slippage_bps = int(trade.get("slippageBps", 100) or 100)
            execution = solana_execution.execute_solana_trade(
                rt,
                chain=args.chain,
                trade_id=args.intent,
                token_in=token_in,
                token_out=token_out,
                amount_in_units=amount_in_units,
                slippage_bps=slippage_bps,
                from_status=status,
            )
            return rt.ok(
                "Trade executed in real mode via runtime-local Solana adapter.",
                tradeId=args.intent,
                chain=args.chain,
                status="filled",
                txHash=execution.get("txHash"),
                signature=execution.get("signature"),
                providerRequested=execution.get("providerRequested"),
                providerUsed=execution.get("providerUsed"),
                fallbackUsed=execution.get("fallbackUsed"),
                fallbackReason=execution.get("fallbackReason"),
                executionFamily=execution.get("executionFamily"),
                executionAdapter=execution.get("executionAdapter"),
                routeKind=execution.get("routeKind"),
            )

        try:
            rt._replay_trade_usage_outbox()
        except Exception:
            pass

        previous_status = status
        try:
            runtime_validators.require_real_mode(str(trade.get("mode")), chain=args.chain, details={"tradeId": args.intent})
        except runtime_errors.RuntimeCommandFailure as exc:
            return runtime_errors.emit_failure(rt, exc)

        wallet_address, private_key_hex, adapter_key = evm_execution.resolve_trade_execution_context(rt, args.chain)

        token_in_raw = str(trade.get("tokenIn") or "").strip()
        token_out_raw = str(trade.get("tokenOut") or "").strip()
        if token_in_raw == "" or token_out_raw == "":
            raise rt.WalletStoreError("Trade payload is missing tokenIn/tokenOut.")
        try:
            token_in = rt._resolve_token_address(args.chain, token_in_raw)
            token_out = rt._resolve_token_address(args.chain, token_out_raw)
        except Exception as exc:
            raise rt.WalletStoreError(f"Could not resolve trade token addresses for execution ({token_in_raw} -> {token_out_raw}): {exc}") from exc

        token_in_meta = rt._fetch_erc20_metadata(args.chain, token_in)
        token_in_decimals = int(token_in_meta.get("decimals", 18))
        amount_wei_str = rt._to_units_uint(str(trade.get("amountIn") or ""), token_in_decimals)
        amount_wei = int(amount_wei_str)
        state, day_key, current_spend, max_daily_wei = rt._enforce_spend_preconditions(args.chain, amount_wei, enforce_native_cap=False)
        projected_spend_usd = rt._to_non_negative_decimal(trade.get("amountIn") or "0")
        cap_state, _, current_spend_usd, current_filled_trades, trade_caps = rt._enforce_trade_caps(args.chain, projected_spend_usd, 1)
        deadline = str(int(datetime.now(timezone.utc).timestamp()) + 120)
        execution = evm_execution.execute_trade_via_router_adapter(
            rt,
            chain=args.chain,
            adapter_key=adapter_key,
            wallet_address=wallet_address,
            private_key_hex=private_key_hex,
            token_in=token_in,
            token_out=token_out,
            amount_in_units=amount_wei_str,
            min_out_units="1",
            deadline=deadline,
            recipient=wallet_address,
            wait_for_receipt=False,
        )
        approve_tx_hashes = execution.get("approveTxHashes") or []
        approve_tx_hash = str(approve_tx_hashes[-1]) if isinstance(approve_tx_hashes, list) and approve_tx_hashes else None
        tx_hash = str(execution.get("txHash") or "")
        if not rt.re.fullmatch(r"0x[a-fA-F0-9]{64}", tx_hash):
            raise rt.WalletStoreError("trade_execution_failed: missing txHash from router adapter execution.")
        uniswap_route_type = str(execution.get("routeKind") or "").strip() or None
        execution_family = str(execution.get("executionFamily") or "").strip() or "amm_v2"
        execution_adapter = str(execution.get("executionAdapter") or "").strip() or adapter_key
        provider_meta = rt._build_provider_meta(provider_requested, provider_used, fallback_used, fallback_reason, uniswap_route_type)
        rt._post_trade_status(args.intent, previous_status, "executing", {"txHash": tx_hash, **provider_meta})
        transition_state = "executing"
        rt._post_trade_status(args.intent, "executing", "verifying", {"txHash": tx_hash, **provider_meta})
        transition_state = "verifying"

        report_result = {
            "ok": False,
            "skipped": True,
            "reason": "real_mode_server_tracked",
            "message": "Real-mode trade reports are server-tracked via wallet/RPC and are not sent by runtime.",
        }
        builder_meta = rt._builder_output_from_hashes(args.chain, [approve_tx_hash, tx_hash])
        return rt.ok(
            "Trade broadcast in real mode via runtime-local router adapter; confirmation is asynchronous.",
            tradeId=args.intent,
            chain=args.chain,
            mode=str(trade.get("mode")),
            status="verifying",
            txHash=tx_hash,
            day=day_key,
            dailySpendUsd=rt._decimal_text(current_spend_usd),
            maxDailyUsd=trade_caps.get("maxDailyUsd"),
            dailyFilledTrades=int(current_filled_trades),
            maxDailyTradeCount=trade_caps.get("maxDailyTradeCount"),
            dailySpendWei=str(current_spend),
            maxDailyNativeWei=str(max_daily_wei),
            providerRequested=provider_requested,
            providerUsed=provider_used,
            fallbackUsed=fallback_used,
            fallbackReason=fallback_reason,
            executionFamily=execution_family,
            executionAdapter=execution_adapter,
            routeKind=uniswap_route_type,
            report=report_result,
            actionHint="Execution is in verifying state; watcher will publish terminal filled/failed status.",
            **builder_meta,
        )
    except runtime_errors.RuntimeCommandFailure as exc:
        return runtime_errors.emit_failure(rt, exc)
    except rt.WalletPolicyError as exc:
        if transition_state == "executing":
            try:
                provider_meta = rt._build_provider_meta(provider_requested, provider_used, fallback_used, fallback_reason, uniswap_route_type)
                rt._post_trade_status(args.intent, "executing", "failed", {"reasonCode": "policy_denied", "reasonMessage": str(exc), **provider_meta})
            except Exception:
                pass
        details = dict(exc.details or {})
        details.update(rt._build_provider_meta(provider_requested, provider_used, fallback_used, fallback_reason, uniswap_route_type))
        return rt.fail(exc.code, str(exc), exc.action_hint, details, exit_code=1)
    except rt.WalletStoreError as exc:
        if transition_state == "executing":
            try:
                provider_meta = rt._build_provider_meta(provider_requested, provider_used, fallback_used, fallback_reason, uniswap_route_type)
                rt._post_trade_status(args.intent, "executing", "failed", {"reasonCode": "rpc_unavailable", "reasonMessage": str(exc), **provider_meta})
            except Exception:
                pass
        elif transition_state == "init":
            try:
                provider_meta = rt._build_provider_meta(provider_requested, provider_used, fallback_used, fallback_reason, uniswap_route_type)
                rt._post_trade_status(args.intent, previous_status, "failed", {"reasonCode": "rpc_unavailable", "reasonMessage": str(exc), **provider_meta})
            except Exception:
                pass
        elif transition_state == "verifying":
            try:
                provider_meta = rt._build_provider_meta(provider_requested, provider_used, fallback_used, fallback_reason, uniswap_route_type)
                rt._post_trade_status(args.intent, "verifying", "failed", {"reasonCode": "verification_timeout", "reasonMessage": str(exc), **provider_meta})
            except Exception:
                pass
        return rt.fail(
            "trade_execute_failed",
            str(exc),
            "Verify approval state, wallet setup, and local chain connectivity.",
            {
                "tradeId": args.intent,
                "chain": args.chain,
                "providerRequested": provider_requested,
                "providerUsed": provider_used,
                "fallbackUsed": fallback_used,
                "fallbackReason": fallback_reason,
                "routeKind": uniswap_route_type,
            },
            exit_code=1,
        )
    except Exception as exc:
        return rt.fail(
            "trade_execute_failed",
            str(exc),
            "Inspect runtime trade execute path and retry.",
            {
                "tradeId": args.intent,
                "chain": args.chain,
                "providerRequested": provider_requested,
                "providerUsed": provider_used,
                "fallbackUsed": fallback_used,
                "fallbackReason": fallback_reason,
                "routeKind": uniswap_route_type,
            },
            exit_code=1,
        )
