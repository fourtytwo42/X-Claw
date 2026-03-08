from __future__ import annotations

import argparse
import time
import urllib.parse
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from xclaw_agent.runtime import errors as runtime_errors
from xclaw_agent.runtime import state_machine as runtime_state_machine


def cmd_limit_orders_create(rt: Any, args: Any) -> int:
    chk = rt.require_json_flag(args)
    if chk is not None:
        return chk
    try:
        runtime_state_machine.ensure_real_mode(str(args.mode), chain=args.chain)
        token_in = rt._resolve_token_address(args.chain, args.token_in)
        token_out = rt._resolve_token_address(args.chain, args.token_out)
        if not rt._is_valid_limit_order_token(args.chain, token_in) or not rt._is_valid_limit_order_token(args.chain, token_out):
            return rt.fail(
                "invalid_input",
                "token-in and token-out must be valid addresses for the selected chain (or canonical symbols).",
                rt._limit_order_token_format_hint(args.chain),
                {"tokenIn": args.token_in, "tokenOut": args.token_out, "chain": args.chain},
                exit_code=2,
            )
        payload = {
            "schemaVersion": 1,
            "agentId": rt._resolve_agent_id(rt._resolve_api_key()),
            "chainKey": args.chain,
            "mode": args.mode,
            "side": args.side,
            "tokenIn": token_in,
            "tokenOut": token_out,
            "amountIn": args.amount_in,
            "limitPrice": args.limit_price,
            "slippageBps": int(args.slippage_bps),
        }
        if args.expires_at:
            payload["expiresAt"] = args.expires_at
        if not payload["agentId"]:
            return rt.fail(
                "auth_invalid",
                "Agent id could not be resolved for limit-order create.",
                "Set XCLAW_AGENT_ID or use signed agent token format.",
                {"chain": args.chain},
                exit_code=1,
            )

        path = "/limit-orders"
        status_code, body = rt._api_request("POST", path, payload=payload, include_idempotency=True)
        if status_code < 200 or status_code >= 300:
            code = str(body.get("code", "api_error"))
            message = str(body.get("message", f"limit-order create failed ({status_code})"))
            return rt.fail(code, message, str(body.get("actionHint", "Review payload and retry.")), rt._api_error_details(status_code, body, path, chain=args.chain), exit_code=1)
        return rt.ok("Limit order created.", chain=args.chain, orderId=body.get("orderId"), status=body.get("status", "open"))
    except runtime_errors.RuntimeCommandFailure as exc:
        return runtime_errors.emit_failure(rt, exc)
    except rt.WalletStoreError as exc:
        return rt.fail("limit_orders_create_failed", str(exc), "Verify API env/auth and retry.", {"chain": args.chain}, exit_code=1)
    except Exception as exc:
        return rt.fail("limit_orders_create_failed", str(exc), "Inspect runtime limit-order create path and retry.", {"chain": args.chain}, exit_code=1)


def cmd_limit_orders_cancel(rt: Any, args: Any) -> int:
    chk = rt.require_json_flag(args)
    if chk is not None:
        return chk
    try:
        agent_id = rt._resolve_agent_id(rt._resolve_api_key())
        if not agent_id:
            return rt.fail(
                "auth_invalid",
                "Agent id could not be resolved for limit-order cancel.",
                "Set XCLAW_AGENT_ID or use signed agent token format.",
                {"chain": args.chain},
                exit_code=1,
            )
        payload = {"schemaVersion": 1, "agentId": agent_id}
        status_code, body = rt._api_request("POST", f"/limit-orders/{args.order_id}/cancel", payload=payload, include_idempotency=True)
        if status_code < 200 or status_code >= 300:
            code = str(body.get("code", "api_error"))
            message = str(body.get("message", f"limit-order cancel failed ({status_code})"))
            return rt.fail(code, message, str(body.get("actionHint", "Verify order id and retry.")), {"chain": args.chain}, exit_code=1)
        return rt.ok("Limit order cancelled.", chain=args.chain, orderId=body.get("orderId"), status=body.get("status"))
    except rt.WalletStoreError as exc:
        return rt.fail("limit_orders_cancel_failed", str(exc), "Verify API env/auth and retry.", {"chain": args.chain}, exit_code=1)
    except Exception as exc:
        return rt.fail("limit_orders_cancel_failed", str(exc), "Inspect runtime limit-order cancel path and retry.", {"chain": args.chain}, exit_code=1)


def cmd_limit_orders_list(rt: Any, args: Any) -> int:
    chk = rt.require_json_flag(args)
    if chk is not None:
        return chk
    try:
        query = f"/limit-orders?chainKey={urllib.parse.quote(args.chain)}&limit={int(args.limit)}"
        if args.status:
            query += f"&status={urllib.parse.quote(str(args.status))}"
        status_code, body = rt._api_request("GET", query)
        if status_code < 200 or status_code >= 300:
            code = str(body.get("code", "api_error"))
            message = str(body.get("message", f"limit-orders list failed ({status_code})"))
            raise rt.WalletStoreError(f"{code}: {message}")
        items = body.get("items", [])
        if not isinstance(items, list):
            items = []
        return rt.ok("Limit orders listed.", chain=args.chain, count=len(items), items=items)
    except rt.WalletStoreError as exc:
        return rt.fail("limit_orders_list_failed", str(exc), "Verify API env/auth and retry.", {"chain": args.chain}, exit_code=1)
    except Exception as exc:
        return rt.fail("limit_orders_list_failed", str(exc), "Inspect runtime limit-order list path and retry.", {"chain": args.chain}, exit_code=1)


def cmd_limit_orders_sync(rt: Any, args: Any) -> int:
    chk = rt.require_json_flag(args)
    if chk is not None:
        return chk
    try:
        total, open_count = rt._sync_limit_orders(args.chain)
        return rt.ok("Limit orders synced.", chain=args.chain, total=total, open=open_count)
    except rt.WalletStoreError as exc:
        return rt.fail("limit_orders_sync_failed", str(exc), "Verify API env/auth and retry.", {"chain": args.chain}, exit_code=1)
    except Exception as exc:
        return rt.fail("limit_orders_sync_failed", str(exc), "Inspect runtime limit-order sync path and retry.", {"chain": args.chain}, exit_code=1)


def cmd_limit_orders_status(rt: Any, args: Any) -> int:
    chk = rt.require_json_flag(args)
    if chk is not None:
        return chk
    try:
        store = rt.load_limit_order_store()
        orders = [entry for entry in store.get("orders", []) if isinstance(entry, dict)]
        by_status: dict[str, int] = {}
        for entry in orders:
            status = str(entry.get("status") or "unknown")
            by_status[status] = by_status.get(status, 0) + 1
        outbox = rt.load_limit_order_outbox()
        return rt.ok("Limit-order local state loaded.", chain=args.chain, count=len(orders), byStatus=by_status, outboxCount=len(outbox))
    except rt.WalletStoreError as exc:
        return rt.fail("limit_orders_status_failed", str(exc), "Repair local limit-order store metadata and retry.", {"chain": args.chain}, exit_code=1)
    except Exception as exc:
        return rt.fail("limit_orders_status_failed", str(exc), "Inspect runtime limit-order status path and retry.", {"chain": args.chain}, exit_code=1)


def _limit_orders_run_once_result(rt: Any, chain: str, sync: bool) -> dict[str, Any]:
    replayed, remaining = rt._replay_limit_order_outbox()
    try:
        trade_usage_replayed, trade_usage_remaining = rt._replay_trade_usage_outbox()
    except Exception:
        trade_usage_replayed, trade_usage_remaining = 0, 0
    synced = False
    if sync:
        rt._sync_limit_orders(chain)
        synced = True
    store = rt.load_limit_order_store()
    orders = [entry for entry in store.get("orders", []) if isinstance(entry, dict)]
    executed = 0
    skipped = 0
    now = datetime.now(timezone.utc)
    for order in orders:
        if str(order.get("chainKey")) != chain:
            skipped += 1
            continue
        if str(order.get("status")) != "open":
            skipped += 1
            continue
        expires_at = order.get("expiresAt")
        if isinstance(expires_at, str) and expires_at:
            try:
                expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                if expiry <= now:
                    rt._post_limit_order_status(str(order.get("orderId")), {"status": "expired", "triggerAt": rt.utc_now()})
                    skipped += 1
                    continue
            except Exception:
                pass

        side = str(order.get("side") or "")
        limit_price = Decimal(str(order.get("limitPrice") or "0"))
        mode = str(order.get("mode") or "real")
        try:
            runtime_state_machine.ensure_real_mode(mode, chain=chain)
        except runtime_errors.RuntimeCommandFailure as exc:
            rt._post_limit_order_status(
                str(order.get("orderId")),
                {
                    "status": "failed",
                    "triggerAt": rt.utc_now(),
                    "reasonCode": exc.code,
                    "reasonMessage": exc.message,
                },
            )
            skipped += 1
            continue
        current_price = rt._quote_limit_order_price(chain, str(order.get("tokenIn")), str(order.get("tokenOut")))
        if not rt._limit_order_triggered(side, current_price, limit_price):
            skipped += 1
            continue

        order_id = str(order.get("orderId"))
        rt._post_limit_order_status(order_id, {"status": "triggered", "triggerPrice": str(current_price), "triggerAt": rt.utc_now()})
        try:
            tx_hash = rt._execute_limit_order_real(order, chain)
            rt._post_limit_order_status(order_id, {"status": "filled", "triggerPrice": str(current_price), "triggerAt": rt.utc_now(), "txHash": tx_hash})
            executed += 1
        except rt.WalletPolicyError as exc:
            rt._post_limit_order_status(
                order_id,
                {
                    "status": "failed",
                    "triggerPrice": str(current_price),
                    "triggerAt": rt.utc_now(),
                    "reasonCode": exc.code,
                    "reasonMessage": str(exc),
                },
            )
        except rt.WalletStoreError as exc:
            rt._post_limit_order_status(
                order_id,
                {
                    "status": "failed",
                    "triggerPrice": str(current_price),
                    "triggerAt": rt.utc_now(),
                    **runtime_state_machine.limit_order_failure_details(exc),
                },
            )

    return {
        "synced": synced,
        "replayed": replayed,
        "outboxRemaining": remaining,
        "tradeUsageReplayed": trade_usage_replayed,
        "tradeUsageOutboxRemaining": trade_usage_remaining,
        "executed": executed,
        "skipped": skipped,
    }



def cmd_limit_orders_run_once(rt: Any, args: Any) -> int:
    chk = rt.require_json_flag(args)
    if chk is not None:
        return chk
    try:
        result = _limit_orders_run_once_result(rt, args.chain, bool(args.sync))
        return rt.ok("Limit-order run completed.", chain=args.chain, **result)
    except rt.WalletStoreError as exc:
        return rt.fail("limit_orders_run_failed", str(exc), "Verify local wallet/policy/chain setup and retry.", {"chain": args.chain}, exit_code=1)
    except Exception as exc:
        return rt.fail("limit_orders_run_failed", str(exc), "Inspect runtime limit-order loop and retry.", {"chain": args.chain}, exit_code=1)


def cmd_limit_orders_run_loop(rt: Any, args: Any) -> int:
    chk = rt.require_json_flag(args)
    if chk is not None:
        return chk
    iterations = int(args.iterations)
    interval_sec = int(args.interval_sec)
    if iterations < 0:
        return rt.fail("invalid_input", "--iterations must be >= 0.", "Use 0 for infinite loop or positive count.", {"iterations": iterations}, exit_code=2)
    if iterations == 0:
        return rt.fail(
            "invalid_input",
            "--iterations 0 (infinite loop) is not allowed in JSON skill mode.",
            "Provide --iterations >= 1 (or use run-once).",
            {"iterations": iterations},
            exit_code=2,
        )
    if interval_sec < 1:
        return rt.fail("invalid_input", "--interval-sec must be >= 1.", "Provide interval in seconds >= 1.", {"intervalSec": interval_sec}, exit_code=2)

    completed = 0
    totals = {"executed": 0, "skipped": 0, "replayed": 0}
    last_run: dict[str, Any] | None = None
    try:
        while True:
            nested = argparse.Namespace(chain=args.chain, json=True, sync=args.sync)
            code, run_payload = runtime_state_machine.run_json_command(
                lambda nested_args: rt.cmd_limit_orders_run_once(nested_args),
                nested,
                fallback_payload={
                    "ok": False,
                    "code": "limit_orders_run_failed",
                    "message": "Unexpected run-once output shape.",
                    "chain": args.chain,
                },
            )
            if code != 0:
                return rt.emit(run_payload)
            last_run = run_payload
            totals["executed"] += int(run_payload.get("executed") or 0)
            totals["skipped"] += int(run_payload.get("skipped") or 0)
            totals["replayed"] += int(run_payload.get("replayed") or 0)
            completed += 1
            if iterations > 0 and completed >= iterations:
                break
            time.sleep(interval_sec)
        return rt.ok(
            "Limit-order loop finished.",
            chain=args.chain,
            iterations=completed,
            intervalSec=interval_sec,
            totals=totals,
            lastRun=last_run,
        )
    except KeyboardInterrupt:
        return rt.ok("Limit-order loop interrupted.", chain=args.chain, iterations=completed, interrupted=True, totals=totals, lastRun=last_run)
