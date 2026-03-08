from __future__ import annotations

import argparse
import os
import secrets
import time
import urllib.parse
from datetime import datetime, timezone
from typing import Any

from xclaw_agent.runtime import state_machine as runtime_state_machine


def _parse_decision_at(value: str | None) -> str:
    raw = str(value or "").strip()
    if not raw:
        return datetime.now(timezone.utc).isoformat()
    candidate = raw[:-1] + "+00:00" if raw.endswith("Z") else raw
    parsed = datetime.fromisoformat(candidate)
    if parsed.tzinfo is None:
        raise ValueError("decision_at must be timezone-aware")
    return parsed.astimezone(timezone.utc).isoformat()



def _hydrate_transfer_flow_from_decision_payload(rt: Any, approval_id: str, chain: str, payload: dict[str, Any]) -> dict[str, Any]:
    kind = str(payload.get("kind") or "").strip().lower()
    if kind != "management_withdraw_v1":
        raise rt.WalletStoreError("unsupported decision payload kind.")
    payload_chain = str(payload.get("chainKey") or "").strip()
    if payload_chain != chain:
        raise rt.WalletStoreError("decision payload chainKey mismatch.")
    transfer_type = str(payload.get("transferType") or "").strip().lower()
    if transfer_type not in {"native", "token"}:
        raise rt.WalletStoreError("decision payload transferType must be native|token.")
    to_address = str(payload.get("toAddress") or "").strip()
    if rt._is_solana_chain(chain):
        if not rt.is_solana_address(to_address):
            raise rt.WalletStoreError("decision payload toAddress is invalid for Solana.")
    elif not rt.is_hex_address(to_address):
        raise rt.WalletStoreError("decision payload toAddress is invalid for EVM.")

    amount_wei = str(payload.get("amountWei") or "").strip()
    if not rt.re.fullmatch(r"[0-9]+", amount_wei):
        raise rt.WalletStoreError("decision payload amountWei must be uint.")

    token_address: str | None = None
    token_symbol: str | None = None
    token_decimals: int | None = None
    if transfer_type == "token":
        token_address_raw = str(payload.get("tokenAddress") or "").strip()
        if rt._is_solana_chain(chain):
            if not rt.is_solana_address(token_address_raw):
                raise rt.WalletStoreError("decision payload tokenAddress is invalid for Solana.")
        elif not rt.is_hex_address(token_address_raw):
            raise rt.WalletStoreError("decision payload tokenAddress is invalid for EVM.")
        token_address = token_address_raw if rt._is_solana_chain(chain) else token_address_raw.lower()
        symbol_raw = str(payload.get("tokenSymbol") or "").strip()
        token_symbol = symbol_raw or "TOKEN"
        decimals_raw = payload.get("tokenDecimals")
        try:
            token_decimals = int(decimals_raw) if decimals_raw is not None else (9 if rt._is_solana_chain(chain) else 18)
        except Exception:
            token_decimals = 9 if rt._is_solana_chain(chain) else 18
    else:
        token_symbol = rt._native_symbol_for_chain(chain)
        token_decimals = rt._native_decimals_for_chain(chain)

    created_at = str(payload.get("createdAt") or "").strip() or rt.utc_now()
    now_iso = rt.utc_now()
    return {
        "approvalId": approval_id,
        "chainKey": chain,
        "status": "approved",
        "transferType": transfer_type,
        "tokenAddress": token_address,
        "tokenSymbol": token_symbol,
        "tokenDecimals": token_decimals,
        "toAddress": to_address if rt._is_solana_chain(chain) else to_address.lower(),
        "amountWei": amount_wei,
        "reasonCode": None,
        "reasonMessage": None,
        "createdAt": created_at,
        "updatedAt": now_iso,
        "decidedAt": now_iso,
        "policyBlockedAtCreate": True,
        "policyBlockReasonCode": None,
        "policyBlockReasonMessage": None,
        "executionMode": "policy_override",
        "forcePolicyOverride": True,
    }



def _run_decide_transfer_inline(
    rt: Any,
    *,
    approval_id: str,
    decision: str,
    chain: str,
    source: str,
    reason_message: str | None,
    decision_payload: dict[str, Any] | None,
) -> tuple[int, dict[str, Any]]:
    nested = argparse.Namespace(
        approval_id=approval_id,
        decision=decision,
        chain=chain,
        source=source,
        reason_message=reason_message,
        decision_payload=decision_payload,
        json=True,
        decision_at=None,
    )
    return runtime_state_machine.run_json_command(
        lambda nested_args: rt.cmd_approvals_decide_transfer(nested_args),
        nested,
        fallback_payload={
            "ok": False,
            "code": "runtime_decision_failed",
            "message": "Transfer decision failed.",
            "approvalId": approval_id,
            "chain": chain,
        },
    )



def _run_approvals_sync_inline(rt: Any, chain: str) -> tuple[int, dict[str, Any]]:
    nested = argparse.Namespace(chain=chain, json=True)
    return runtime_state_machine.run_json_command(
        lambda nested_args: rt.cmd_approvals_sync(nested_args),
        nested,
        fallback_payload={
            "ok": False,
            "code": "approvals_sync_failed",
            "message": "Approval sync result unavailable.",
            "chain": chain,
        },
    )



def _run_resume_spot_inline(rt: Any, trade_id: str, chain: str) -> tuple[int, dict[str, Any]]:
    nested = argparse.Namespace(trade_id=trade_id, chain=chain, json=True)
    return runtime_state_machine.run_json_command(
        lambda nested_args: rt.cmd_approvals_resume_spot(nested_args),
        nested,
        fallback_payload={
            "ok": False,
            "code": "resume_result_unavailable",
            "message": "Resume result unavailable.",
            "tradeId": trade_id,
            "chain": chain,
        },
    )



def cmd_approvals_sync(rt: Any, args: Any) -> int:
    chk = rt.require_json_flag(args)
    if chk is not None:
        return chk
    chain = args.chain
    try:
        state = rt._load_approval_prompts()
        prompts = state.get("prompts")
        if not isinstance(prompts, dict):
            prompts = {}
        checked = 0
        deleted = 0
        skipped = 0
        failures: list[dict[str, Any]] = []
        for trade_id, entry in list(prompts.items()):
            if not isinstance(entry, dict):
                continue
            if str(entry.get("chainKey") or "") != chain:
                skipped += 1
                continue
            checked += 1
            try:
                trade = rt._read_trade_details(str(trade_id))
                status = str(trade.get("status") or "")
                if status == "approval_pending":
                    skipped += 1
                    continue
                rt._maybe_delete_telegram_approval_prompt(str(trade_id))
                deleted += 1
            except Exception as exc:
                failures.append({"tradeId": str(trade_id), "error": str(exc)})
        transfer_decisions_checked = 0
        transfer_decisions_applied = 0
        transfer_decisions_failed = 0
        transfer_decision_failures: list[dict[str, Any]] = []
        transfer_decisions = rt._fetch_transfer_decision_inbox(chain, limit=20)
        for row in transfer_decisions:
            decision_id = str(row.get("decisionId") or "").strip()
            approval_id = str(row.get("approvalId") or "").strip()
            decision = str(row.get("decision") or "").strip().lower()
            decision_chain = str(row.get("chainKey") or chain).strip()
            reason_message = str(row.get("reasonMessage") or "").strip() or None
            source = str(row.get("source") or "web").strip().lower() or "web"
            if not decision_id or not approval_id or decision not in {"approve", "deny"} or not decision_chain:
                transfer_decisions_failed += 1
                transfer_decision_failures.append(
                    {
                        "decisionId": decision_id,
                        "approvalId": approval_id,
                        "code": "invalid_inbox_row",
                        "message": "Missing required transfer decision inbox fields.",
                    }
                )
                if decision_id:
                    try:
                        rt._ack_transfer_decision_inbox(
                            decision_id,
                            "failed",
                            reason_code="invalid_inbox_row",
                            reason_message="Missing required transfer decision inbox fields.",
                        )
                    except Exception:
                        pass
                continue

            transfer_decisions_checked += 1
            code, payload = rt._run_decide_transfer_inline(
                approval_id=approval_id,
                decision=decision,
                chain=decision_chain,
                source=source,
                reason_message=reason_message,
                decision_payload=row.get("decisionPayload") if isinstance(row.get("decisionPayload"), dict) else None,
            )
            payload_code = str(payload.get("code") or "").strip() or ("ok" if code == 0 else "runtime_decision_failed")
            payload_message = str(payload.get("message") or "").strip() or (
                "Transfer decision applied." if code == 0 else "Transfer decision failed."
            )
            ack_status = "applied" if code == 0 else "failed"
            ack_status_code = 0
            try:
                ack_status_code, _ = rt._ack_transfer_decision_inbox(
                    decision_id,
                    ack_status,
                    reason_code=payload_code if ack_status == "failed" else None,
                    reason_message=payload_message if ack_status == "failed" else None,
                )
            except Exception:
                ack_status_code = 0
            if ack_status_code < 200 or ack_status_code >= 300:
                transfer_decision_failures.append(
                    {
                        "decisionId": decision_id,
                        "approvalId": approval_id,
                        "code": "inbox_ack_failed",
                        "message": "Decision processing finished but inbox ack failed.",
                    }
                )
            if code == 0:
                transfer_decisions_applied += 1
            else:
                transfer_decisions_failed += 1
                transfer_decision_failures.append(
                    {
                        "decisionId": decision_id,
                        "approvalId": approval_id,
                        "code": payload_code,
                        "message": payload_message,
                    }
                )
        return rt.ok(
            "Approval prompts synced.",
            chain=chain,
            checked=checked,
            deleted=deleted,
            skipped=skipped,
            failures=failures or None,
            transferDecisionsChecked=transfer_decisions_checked,
            transferDecisionsApplied=transfer_decisions_applied,
            transferDecisionsFailed=transfer_decisions_failed,
            transferDecisionFailures=transfer_decision_failures or None,
        )
    except Exception as exc:
        return rt.fail("approvals_sync_failed", str(exc), "Verify API auth and OpenClaw availability, then retry.", {"chain": chain}, exit_code=1)



def cmd_approvals_run_loop(rt: Any, args: Any) -> int:
    chk = rt.require_json_flag(args)
    if chk is not None:
        return chk
    chain = str(args.chain or "").strip()
    if not chain:
        return rt.fail("invalid_input", "chain is required.", "Provide --chain and retry.", exit_code=2)
    interval_ms_raw = int(args.interval_ms) if isinstance(args.interval_ms, int) else rt.APPROVAL_RUN_LOOP_INTERVAL_MS
    interval_ms = max(250, min(interval_ms_raw, 60000))
    once = bool(getattr(args, "once", False))
    iteration = 0
    backoff_ms = interval_ms
    consecutive_failures = 0
    api_base = str(os.environ.get("XCLAW_API_BASE_URL") or "").strip()
    parsed_base = urllib.parse.urlparse(api_base) if api_base else None
    api_base_host = str(parsed_base.netloc or "").strip() if parsed_base else ""
    agent_id = str(os.environ.get("XCLAW_AGENT_ID") or "").strip()
    while True:
        iteration += 1
        cycle_started = time.time()
        readiness = rt._runtime_wallet_signing_readiness(chain)
        readiness_status = 0
        readiness_code = "ok"
        try:
            readiness_status, readiness_body = rt._publish_runtime_signing_readiness(chain, readiness)
            if readiness_status < 200 or readiness_status >= 300:
                readiness_code = str(readiness_body.get("code", "api_error"))
        except Exception as exc:
            readiness_status = 0
            readiness_code = f"publish_error:{str(exc)[:120]}"
        sync_code, sync_payload = rt._run_approvals_sync_inline(chain)
        cycle_ok = sync_code == 0
        if cycle_ok:
            consecutive_failures = 0
            backoff_ms = interval_ms
        else:
            consecutive_failures += 1
            backoff_ms = min(rt.APPROVAL_RUN_LOOP_BACKOFF_MAX_MS, max(interval_ms, backoff_ms * 2))
        elapsed_ms = int((time.time() - cycle_started) * 1000)
        cycle_log = {
            "event": "approvals_run_loop_cycle",
            "chain": chain,
            "apiBaseHost": api_base_host or None,
            "agentId": agent_id or None,
            "iteration": iteration,
            "ok": cycle_ok,
            "syncCode": str(sync_payload.get("code") or ("ok" if cycle_ok else "sync_failed")),
            "transferDecisionsChecked": int(sync_payload.get("transferDecisionsChecked") or 0),
            "transferDecisionsApplied": int(sync_payload.get("transferDecisionsApplied") or 0),
            "transferDecisionsFailed": int(sync_payload.get("transferDecisionsFailed") or 0),
            "walletSigningReady": bool(readiness.get("walletSigningReady")),
            "walletSigningReasonCode": readiness.get("walletSigningReasonCode"),
            "readinessPublishStatus": readiness_status,
            "readinessPublishCode": readiness_code,
            "consecutiveFailures": consecutive_failures,
            "elapsedMs": elapsed_ms,
            "sleepMs": 0 if once else (interval_ms if cycle_ok else backoff_ms),
            "at": rt.utc_now(),
        }
        print(rt.json.dumps(cycle_log, separators=(",", ":")), file=rt.sys.stderr)
        if once:
            summary = dict(sync_payload)
            summary.setdefault("ok", cycle_ok)
            summary.setdefault("code", "ok" if cycle_ok else "approvals_run_loop_cycle_failed")
            summary["chain"] = chain
            summary["iteration"] = iteration
            summary["walletSigningReady"] = bool(readiness.get("walletSigningReady"))
            summary["walletSigningReasonCode"] = readiness.get("walletSigningReasonCode")
            summary["readinessPublishStatus"] = readiness_status
            summary["readinessPublishCode"] = readiness_code
            summary["elapsedMs"] = elapsed_ms
            return rt.emit(summary)
        time.sleep((interval_ms if cycle_ok else backoff_ms) / 1000.0)



def cmd_approvals_cleanup_spot(rt: Any, args: Any) -> int:
    chk = rt.require_json_flag(args)
    if chk is not None:
        return chk
    trade_id = str(args.trade_id or "").strip()
    if not trade_id:
        return rt.fail("invalid_input", "trade_id is required.", "Provide --trade-id trd_... and retry.", exit_code=2)
    return runtime_state_machine.emit_prompt_cleanup_result(
        rt,
        subject_type="trade",
        subject_id=trade_id,
        success_message="Spot approval prompt cleanup completed.",
        failure_message="Spot approval prompt button clear failed.",
        failure_hint="Retry approvals cleanup after prompt metadata sync.",
        extra_details={"tradeId": trade_id},
    )



def cmd_approvals_clear_prompt(rt: Any, args: Any) -> int:
    chk = rt.require_json_flag(args)
    if chk is not None:
        return chk
    subject_type = str(args.subject_type or "").strip().lower()
    subject_id = str(args.subject_id or "").strip()
    if subject_type not in {"trade", "transfer", "policy"}:
        return rt.fail(
            "invalid_input",
            "subject_type must be trade|transfer|policy.",
            "Use --subject-type trade|transfer|policy.",
            {"subjectType": subject_type},
            exit_code=2,
        )
    if not subject_id:
        return rt.fail(
            "invalid_input",
            "subject_id is required.",
            "Use --subject-id <trd_|xfr_|ppr_...>.",
            {"subjectType": subject_type},
            exit_code=2,
        )
    return runtime_state_machine.emit_prompt_cleanup_result(
        rt,
        subject_type=subject_type,
        subject_id=subject_id,
        success_message="Approval prompt button clear completed.",
        failure_message="Approval prompt button clear failed.",
        failure_hint="Retry clear-prompt after prompt metadata sync.",
    )



def cmd_approvals_resume_spot(rt: Any, args: Any) -> int:
    chk = rt.require_json_flag(args)
    if chk is not None:
        return chk
    trade_id = str(args.trade_id or "").strip()
    if not trade_id:
        return rt.fail("invalid_input", "trade_id is required.", "Provide --trade-id trd_... and retry.", {"tradeId": trade_id}, exit_code=2)

    flow = rt._get_pending_spot_trade_flow(trade_id) or {}
    flow_chain = str(flow.get("chainKey") or "").strip()
    chain = str(args.chain or flow_chain).strip()
    if not chain:
        return rt.fail(
            "invalid_input",
            "chain is required when no saved spot-flow exists for this trade.",
            "Provide --chain <chainKey> and retry.",
            {"tradeId": trade_id},
            exit_code=2,
        )

    try:
        trade = rt._read_trade_details(trade_id)
        status = str(trade.get("status") or "")
        terminal = {"filled", "failed", "rejected", "expired"}
        non_actionable = {"approval_pending", "proposed", "executing", "verifying"}
        if status in terminal:
            rt._remove_pending_spot_trade_flow(trade_id)
            return rt.ok(
                "Spot trade resume skipped: trade already terminal.",
                tradeId=trade_id,
                chain=chain,
                status=status,
                skipped=True,
                reason="already_terminal",
                txHash=trade.get("txHash"),
                reasonCode=trade.get("reasonCode"),
                reasonMessage=trade.get("reasonMessage"),
                flow=flow or None,
            )
        if status in non_actionable:
            if status != "approval_pending":
                rt._remove_pending_spot_trade_flow(trade_id)
            return rt.fail(
                "not_actionable",
                f"Spot trade resume is not actionable from status '{status}'.",
                "Resume only when the trade is approved (or retry-eligible failed).",
                {"tradeId": trade_id, "chain": chain, "status": status, "flow": flow or None},
                exit_code=1,
            )

        resume_code, payload = runtime_state_machine.run_json_command(
            lambda nested_args: rt.cmd_trade_execute(nested_args),
            argparse.Namespace(intent=trade_id, chain=chain, json=True),
            fallback_payload={"ok": False, "code": "resume_result_unavailable", "message": "Resume result unavailable."},
        )
        if isinstance(payload, dict):
            payload.setdefault("tradeId", trade_id)
            payload.setdefault("chain", chain)
            if flow:
                payload.setdefault("flowSummary", flow)
        if resume_code == 0:
            rt._remove_pending_spot_trade_flow(trade_id)
            payload["ok"] = True
            payload["code"] = "ok"
            payload["message"] = str(payload.get("message") or "Spot trade resumed and executed.")
            return rt.emit(payload)

        try:
            latest_after_fail = rt._read_trade_details(trade_id)
            latest_status = str(latest_after_fail.get("status") or "").strip().lower()
            if latest_status == "approved":
                reason_code = str(payload.get("code") or "resume_failed").strip() or "resume_failed"
                reason_message = str(payload.get("message") or "Spot trade resume failed before execution status transition.").strip()
                rt._post_trade_status(
                    trade_id,
                    "approved",
                    "failed",
                    {
                        "reasonCode": reason_code[:64],
                        "reasonMessage": reason_message[:500],
                    },
                )
                payload["statusMirrored"] = True
                payload["mirroredFromStatus"] = "approved"
                payload["mirroredToStatus"] = "failed"
            else:
                payload["statusMirrored"] = False
        except Exception:
            payload["statusMirrored"] = False

        try:
            latest = rt._read_trade_details(trade_id)
            if str(latest.get("status") or "") != "approval_pending":
                rt._remove_pending_spot_trade_flow(trade_id)
        except Exception:
            pass
        return rt.emit(payload)
    except Exception as exc:
        return rt.fail(
            "spot_resume_failed",
            str(exc),
            "Inspect trade status and runtime execution path, then retry.",
            {"tradeId": trade_id, "chain": chain, "flow": flow or None},
            exit_code=1,
        )



def cmd_approvals_resume_transfer(rt: Any, args: Any) -> int:
    chk = rt.require_json_flag(args)
    if chk is not None:
        return chk
    approval_id = str(args.approval_id or "").strip()
    if not approval_id:
        return rt.fail("invalid_input", "approval_id is required.", "Provide --approval-id xfr_... and retry.", exit_code=2)
    flow = rt._get_pending_transfer_flow(approval_id)
    if not flow:
        x402_flow = rt.x402_state.get_pending_pay_flow(approval_id)
        if isinstance(x402_flow, dict):
            try:
                payload = rt.x402_pay_resume(approval_id)
                if isinstance(payload, dict):
                    rt._mirror_x402_outbound(payload)
                return rt.ok("x402 payment resume processed.", approval=payload)
            except rt.X402RuntimeError as exc:
                return rt.fail("x402_runtime_error", str(exc), "Use a valid pending approved x402 approval id and retry.", exit_code=1)
            except Exception as exc:
                return rt.fail("x402_runtime_error", str(exc), "Inspect runtime x402 pay resume flow and retry.", exit_code=1)
        return rt.fail(
            "not_found",
            "Transfer approval flow was not found.",
            "Use a pending approval ID from the latest transfer request.",
            {"approvalId": approval_id},
            exit_code=1,
        )
    chain = str(args.chain or flow.get("chainKey") or "").strip()
    if not chain:
        return rt.fail("invalid_input", "chain is required.", "Provide --chain and retry.", {"approvalId": approval_id}, exit_code=2)
    status = str(flow.get("status") or "")
    if status in {"filled", "failed", "rejected"}:
        rt._cleanup_transfer_approval_prompt(approval_id)
        return rt.ok(
            "Transfer resume skipped: approval already terminal.",
            approvalId=approval_id,
            chain=chain,
            status=status,
            txHash=flow.get("txHash"),
            reasonCode=flow.get("reasonCode"),
            reasonMessage=flow.get("reasonMessage"),
            skipped=True,
        )
    if status in {"executing", "verifying"}:
        if rt._is_stale_executing_transfer_flow(flow):
            flow["status"] = "approved"
            flow["updatedAt"] = rt.utc_now()
            rt._record_pending_transfer_flow(approval_id, flow)
            rt._mirror_transfer_approval(flow)
            return rt.emit(rt._execute_pending_transfer_flow(flow))
        return rt.ok(
            "Transfer resume skipped: approval already in progress.",
            approvalId=approval_id,
            chain=chain,
            status=status,
            txHash=flow.get("txHash"),
            skipped=True,
            inProgress=True,
        )
    if status == "approved":
        return rt.emit(rt._execute_pending_transfer_flow(flow))
    return rt.fail(
        "not_actionable",
        f"Transfer resume is not actionable from status '{status}'.",
        "Resume only when transfer approval is approved.",
        {"approvalId": approval_id, "chain": chain, "status": status},
        exit_code=1,
    )



def cmd_approvals_decide_spot(rt: Any, args: Any) -> int:
    chk = rt.require_json_flag(args)
    if chk is not None:
        return chk
    trade_id = str(args.trade_id or "").strip()
    decision = str(args.decision or "").strip().lower()
    chain = str(args.chain or "").strip()
    source = str(getattr(args, "source", "") or "").strip().lower() or "runtime"
    reason_message = str(args.reason_message or "").strip()
    idempotency_key = str(getattr(args, "idempotency_key", "") or "").strip() or None
    decision_at_raw = str(getattr(args, "decision_at", "") or "").strip()
    decision_at = None
    if decision_at_raw:
        try:
            decision_at = _parse_decision_at(decision_at_raw)
        except Exception:
            return rt.fail("invalid_input", "decision_at must be ISO-8601.", "Use --decision-at <iso8601>.", {"decisionAt": decision_at_raw}, exit_code=2)
    if not trade_id:
        return rt.fail("invalid_input", "trade_id is required.", "Provide --trade-id trd_... and retry.", exit_code=2)
    if decision not in {"approve", "reject"}:
        return rt.fail("invalid_input", "decision must be approve|reject.", "Use --decision approve|reject.", exit_code=2)

    trade = rt._read_trade_details(trade_id)
    status = str(trade.get("status") or "").strip().lower()
    if not chain:
        chain = str(trade.get("chainKey") or "").strip()
    if not chain:
        return rt.fail("invalid_input", "chain is required.", "Provide --chain and retry.", {"tradeId": trade_id}, exit_code=2)

    if status in {"filled", "failed", "rejected", "expired", "verification_timeout"}:
        cleanup = rt._cleanup_trade_approval_prompt(trade_id)
        return rt.ok(
            "Trade decision converged on terminal state.",
            subjectType="trade",
            subjectId=trade_id,
            decision=decision,
            source=source,
            chain=chain,
            fromStatus=status,
            toStatus=status,
            executionStatus=status,
            txHash=trade.get("txHash"),
            promptCleanup=cleanup,
            prodDispatch={"mode": "handled_by_web_or_callback"},
            actionHint="No additional action required.",
            converged=True,
            status=status,
            resume=None,
        )

    if decision == "reject":
        from_status = "approval_pending" if status == "approval_pending" else status
        if status == "approval_pending":
            rt._post_trade_status(
                trade_id,
                "approval_pending",
                "rejected",
                {
                    "reasonCode": "approval_rejected",
                    "reasonMessage": reason_message or "Denied by owner.",
                },
                idempotency_key=idempotency_key,
                decision_at=decision_at,
            )
            trade = rt._read_trade_details(trade_id)
        cleanup = rt._cleanup_trade_approval_prompt(trade_id)
        try:
            rt._maybe_send_telegram_decision_message(trade_id=trade_id, chain=chain, decision="rejected", summary=None, trade=trade if isinstance(trade, dict) else None)
        except Exception:
            pass
        return rt.ok(
            "Trade rejected.",
            subjectType="trade",
            subjectId=trade_id,
            decision=decision,
            source=source,
            chain=chain,
            fromStatus=from_status,
            toStatus="rejected",
            executionStatus="rejected",
            txHash=trade.get("txHash"),
            promptCleanup=cleanup,
            prodDispatch={"mode": "handled_by_web_or_callback"},
            actionHint="Trade was denied and will not execute.",
            status="rejected",
            resume=None,
        )

    from_status = status
    if status == "approval_pending":
        rt._post_trade_status(
            trade_id,
            "approval_pending",
            "approved",
            {"reasonCode": None, "reasonMessage": None},
            idempotency_key=idempotency_key,
            decision_at=decision_at,
        )
    cleanup = rt._cleanup_trade_approval_prompt(trade_id)
    try:
        rt._maybe_send_telegram_decision_message(trade_id=trade_id, chain=chain, decision="approved", summary=None, trade=rt._read_trade_details(trade_id))
    except Exception:
        pass
    resume_code, resume_payload = rt._run_resume_spot_inline(trade_id, chain)
    tx_hash = str(resume_payload.get("txHash") or "").strip()
    raw_exec_status = str(resume_payload.get("executionStatus") or resume_payload.get("status") or "").strip().lower()
    exec_status = raw_exec_status or "failed"
    if exec_status == "filled" and not tx_hash:
        exec_status = "failed"
        resume_payload = {
            **resume_payload,
            "code": "terminal_status_unverified",
            "message": str(resume_payload.get("message") or "Runtime reported filled without tx hash; treating as failed/unverified."),
            "reasonCode": str(resume_payload.get("reasonCode") or "terminal_status_unverified"),
        }
    try:
        rt._maybe_send_telegram_trade_terminal_message(
            trade_id=trade_id,
            chain=chain,
            status=exec_status,
            tx_hash=tx_hash or None,
            reason_message=str(resume_payload.get("message") or "").strip() or None,
        )
    except Exception:
        pass
    return rt.emit(
        {
            "ok": bool(resume_code == 0),
            "code": str(resume_payload.get("code") or ("ok" if resume_code == 0 else "resume_failed")),
            "message": str(resume_payload.get("message") or ("Trade approved and resumed." if resume_code == 0 else "Trade resume failed.")),
            "subjectType": "trade",
            "subjectId": trade_id,
            "decision": decision,
            "source": source,
            "chain": chain,
            "fromStatus": from_status,
            "toStatus": "approved",
            "executionStatus": exec_status,
            "txHash": resume_payload.get("txHash"),
            "promptCleanup": cleanup,
            "prodDispatch": {"mode": "handled_by_web_or_callback"},
            "actionHint": "Execution resumed; monitor terminal status.",
            "status": exec_status,
            "resume": resume_payload,
        }
    )



def cmd_approvals_decide_liquidity(rt: Any, args: Any) -> int:
    chk = rt.require_json_flag(args)
    if chk is not None:
        return chk
    liquidity_intent_id = str(args.intent_id or "").strip()
    decision = str(args.decision or "").strip().lower()
    chain = str(args.chain or "").strip()
    source = str(getattr(args, "source", "") or "").strip().lower() or "runtime"
    reason_message = str(args.reason_message or "").strip()
    if not liquidity_intent_id:
        return rt.fail("invalid_input", "intent_id is required.", "Provide --intent-id liq_... and retry.", exit_code=2)
    if decision not in {"approve", "reject"}:
        return rt.fail("invalid_input", "decision must be approve|reject.", "Use --decision approve|reject.", exit_code=2)
    if not chain:
        return rt.fail("invalid_input", "chain is required.", "Provide --chain <chainKey> and retry.", {"liquidityIntentId": liquidity_intent_id}, exit_code=2)

    try:
        intent = rt._read_liquidity_intent(liquidity_intent_id, chain)
        status = str(intent.get("status") or "").strip().lower()
        if status in {"filled", "failed", "rejected", "expired", "verification_timeout"}:
            return rt.ok(
                "Liquidity decision converged on terminal state.",
                subjectType="liquidity",
                subjectId=liquidity_intent_id,
                decision=decision,
                source=source,
                chain=chain,
                status=status,
                converged=True,
                txHash=intent.get("txHash"),
            )
        if decision == "reject":
            if status == "approval_pending":
                rt._post_liquidity_status(
                    liquidity_intent_id,
                    "rejected",
                    {"reasonCode": "approval_rejected", "reasonMessage": reason_message or "Denied by owner."},
                )
                status = "rejected"
            return rt.ok(
                "Liquidity intent rejected.",
                subjectType="liquidity",
                subjectId=liquidity_intent_id,
                decision=decision,
                source=source,
                chain=chain,
                status=status,
                executionStatus=status,
            )
        if status == "approval_pending":
            rt._post_liquidity_status(liquidity_intent_id, "approved")
            status = "approved"
        if status != "approved":
            return rt.fail(
                "liquidity_not_actionable",
                f"Liquidity decision is not actionable from status '{status}'.",
                "Approve only approval_pending intents.",
                {"liquidityIntentId": liquidity_intent_id, "chain": chain, "status": status},
                exit_code=1,
            )
        execute_code, execute_payload = rt._run_liquidity_execute_inline(liquidity_intent_id, chain)
        if isinstance(execute_payload, dict):
            execute_payload.setdefault("subjectType", "liquidity")
            execute_payload.setdefault("subjectId", liquidity_intent_id)
            execute_payload.setdefault("decision", decision)
            execute_payload.setdefault("source", source)
        return rt.emit(execute_payload) if isinstance(execute_payload, dict) else execute_code
    except rt.WalletStoreError as exc:
        message = str(exc)
        if source == "telegram" and "was not found in pending scope" in message:
            return rt.ok(
                "Liquidity decision converged outside pending scope.",
                subjectType="liquidity",
                subjectId=liquidity_intent_id,
                decision=decision,
                source=source,
                chain=chain,
                status="converged_unknown",
                converged=True,
            )
        return rt.fail(
            "liquidity_decision_failed",
            message,
            "Inspect liquidity decision path and retry.",
            {"liquidityIntentId": liquidity_intent_id, "chain": chain},
            exit_code=1,
        )
    except Exception as exc:
        return rt.fail(
            "liquidity_decision_failed",
            str(exc),
            "Inspect liquidity decision path and retry.",
            {"liquidityIntentId": liquidity_intent_id, "chain": chain},
            exit_code=1,
        )



def cmd_approvals_decide_policy(rt: Any, args: Any) -> int:
    chk = rt.require_json_flag(args)
    if chk is not None:
        return chk
    approval_id = str(args.approval_id or "").strip()
    decision = str(args.decision or "").strip().lower()
    chain = str(args.chain or "").strip()
    source = str(getattr(args, "source", "") or "").strip().lower() or "runtime"
    reason_message = str(args.reason_message or "").strip()
    idempotency_key = str(getattr(args, "idempotency_key", "") or "").strip() or None
    decision_at_raw = str(getattr(args, "decision_at", "") or "").strip()
    try:
        decision_at = _parse_decision_at(decision_at_raw or None)
    except Exception:
        return rt.fail("invalid_input", "decision_at must be ISO-8601.", "Use --decision-at <iso8601>.", {"decisionAt": decision_at_raw}, exit_code=2)
    if not approval_id:
        return rt.fail("invalid_input", "approval_id is required.", "Provide --approval-id ppr_... and retry.", exit_code=2)
    if decision not in {"approve", "reject"}:
        return rt.fail("invalid_input", "decision must be approve|reject.", "Use --decision approve|reject.", exit_code=2)

    path = f"/policy-approvals/{urllib.parse.quote(approval_id)}/decision"
    to_status = "approved" if decision == "approve" else "rejected"
    payload: dict[str, Any] = {
        "policyApprovalId": approval_id,
        "fromStatus": "approval_pending",
        "toStatus": to_status,
        "at": decision_at,
    }
    if reason_message:
        payload["reasonMessage"] = reason_message
    status_code, body = rt._api_request("POST", path, payload=payload, include_idempotency=True, idempotency_key=idempotency_key)
    if status_code < 200 or status_code >= 300:
        return rt.fail(
            str(body.get("code", "api_error")),
            str(body.get("message", f"policy decision failed ({status_code})")),
            str(body.get("actionHint", "Refresh policy approvals and retry.")),
            {"approvalId": approval_id, "status": status_code, "source": source},
            exit_code=1,
        )
    cleanup = rt._cleanup_policy_approval_prompt(approval_id)
    return rt.ok(
        "Policy decision applied.",
        subjectType="policy",
        subjectId=approval_id,
        decision=decision,
        source=source,
        chain=chain or body.get("chainKey"),
        fromStatus="approval_pending",
        toStatus=to_status,
        executionStatus=to_status,
        promptCleanup=cleanup,
        prodDispatch={"mode": "handled_by_web_or_callback"},
        actionHint=("Policy update was applied." if to_status == "approved" else "Policy update was rejected."),
        status=to_status,
        txHash=body.get("txHash"),
        resume=None,
    )



def cmd_approvals_decide_transfer(rt: Any, args: Any) -> int:
    chk = rt.require_json_flag(args)
    if chk is not None:
        return chk
    approval_id = str(args.approval_id or "").strip()
    decision = str(args.decision or "").strip().lower()
    source = str(getattr(args, "source", "") or "").strip().lower() or "runtime"
    decision_at_raw = str(getattr(args, "decision_at", "") or "").strip()
    if decision_at_raw:
        try:
            _parse_decision_at(decision_at_raw)
        except Exception:
            return rt.fail("invalid_input", "decision_at must be ISO-8601.", "Use --decision-at <iso8601>.", {"decisionAt": decision_at_raw}, exit_code=2)
    if not approval_id:
        return rt.fail("invalid_input", "approval_id is required.", "Provide --approval-id xfr_... and retry.", exit_code=2)
    if decision not in {"approve", "deny"}:
        return rt.fail("invalid_input", "decision must be approve|deny.", "Use --decision approve or --decision deny.", exit_code=2)

    flow = rt._get_pending_transfer_flow(approval_id)
    if not flow:
        decision_payload = getattr(args, "decision_payload", None)
        if decision == "approve" and isinstance(decision_payload, dict):
            try:
                hydrate_chain = str(args.chain or decision_payload.get("chainKey") or "").strip()
                if not hydrate_chain:
                    raise rt.WalletStoreError("decision payload chainKey is required.")
                flow = _hydrate_transfer_flow_from_decision_payload(rt, approval_id, hydrate_chain, decision_payload)
                rt._record_pending_transfer_flow(approval_id, flow)
                rt._mirror_transfer_approval(flow)
            except rt.WalletStoreError as exc:
                return rt.fail(
                    "invalid_decision_payload",
                    str(exc),
                    "Resync transfer decisions and retry approve.",
                    {"approvalId": approval_id},
                    exit_code=1,
                )
        x402_flow = rt.x402_state.get_pending_pay_flow(approval_id)
        if flow is None and isinstance(x402_flow, dict):
            try:
                payload = rt.x402_pay_decide(approval_id, decision, str(args.reason_message or "").strip() or None)
                if isinstance(payload, dict):
                    rt._mirror_x402_outbound(payload)
                return rt.ok("x402 payment decision applied.", approval=payload)
            except rt.X402RuntimeError as exc:
                return rt.fail("x402_runtime_error", str(exc), "Use a valid pending x402 approval id and retry.", exit_code=1)
            except Exception as exc:
                return rt.fail("x402_runtime_error", str(exc), "Inspect runtime x402 pay decision flow and retry.", exit_code=1)
        if flow is None:
            return rt.fail(
                "not_found",
                "Transfer approval flow was not found.",
                "Use a pending approval ID from the latest transfer request.",
                {"approvalId": approval_id},
                exit_code=1,
            )
    status = str(flow.get("status") or "")
    chain = str(args.chain or flow.get("chainKey") or "").strip()
    flow_transfer_type = str(flow.get("transferType") or "native").strip().lower()
    flow_token_symbol = str(flow.get("tokenSymbol") or ("NATIVE" if flow_transfer_type == "native" else "TOKEN")).strip()
    flow_token_decimals_raw = flow.get("tokenDecimals", 18 if flow_transfer_type == "native" else None)
    try:
        flow_token_decimals = int(flow_token_decimals_raw) if flow_token_decimals_raw is not None else None
    except Exception:
        flow_token_decimals = 18 if flow_transfer_type == "native" else None
    flow_amount_human, flow_amount_unit = rt._transfer_amount_display(
        str(flow.get("amountWei") or "0"),
        flow_transfer_type,
        flow_token_symbol,
        flow_token_decimals,
    )
    flow_amount_display = f"{flow_amount_human} {flow_amount_unit}"
    if status in {"filled", "failed", "rejected"}:
        cleanup = rt._cleanup_transfer_approval_prompt(approval_id)
        return rt.ok(
            "Transfer decision converged on terminal approval.",
            subjectType="transfer",
            subjectId=approval_id,
            decision=decision,
            source=source,
            approvalId=approval_id,
            chain=chain,
            status=status,
            executionStatus=status,
            txHash=flow.get("txHash"),
            reasonCode=flow.get("reasonCode"),
            reasonMessage=flow.get("reasonMessage"),
            amountWei=flow.get("amountWei"),
            amount=flow_amount_human,
            amountUnit=flow_amount_unit,
            amountDisplay=flow_amount_display,
            policyBlockedAtCreate=bool(flow.get("policyBlockedAtCreate", False)),
            policyBlockReasonCode=flow.get("policyBlockReasonCode"),
            policyBlockReasonMessage=flow.get("policyBlockReasonMessage"),
            executionMode=flow.get("executionMode"),
            converged=True,
            fromStatus=status,
            toStatus=status,
            promptCleanup=cleanup,
            prodDispatch={"mode": "handled_by_web_or_callback"},
            actionHint="No additional action required.",
        )
    if status in {"executing", "verifying"}:
        cleanup = rt._cleanup_transfer_approval_prompt(approval_id)
        return rt.ok(
            "Transfer decision already in progress.",
            subjectType="transfer",
            subjectId=approval_id,
            decision=decision,
            source=source,
            approvalId=approval_id,
            chain=chain,
            status=status,
            executionStatus=status,
            txHash=flow.get("txHash"),
            reasonCode=flow.get("reasonCode"),
            reasonMessage=flow.get("reasonMessage"),
            amountWei=flow.get("amountWei"),
            amount=flow_amount_human,
            amountUnit=flow_amount_unit,
            amountDisplay=flow_amount_display,
            policyBlockedAtCreate=bool(flow.get("policyBlockedAtCreate", False)),
            policyBlockReasonCode=flow.get("policyBlockReasonCode"),
            policyBlockReasonMessage=flow.get("policyBlockReasonMessage"),
            executionMode=flow.get("executionMode"),
            converged=True,
            inProgress=True,
            fromStatus=status,
            toStatus=status,
            promptCleanup=cleanup,
            prodDispatch={"mode": "handled_by_web_or_callback"},
            actionHint="Transfer already in progress.",
        )
    if status == "approved" and decision == "deny":
        cleanup = rt._cleanup_transfer_approval_prompt(approval_id)
        return rt.ok(
            "Transfer decision converged on approved approval.",
            subjectType="transfer",
            subjectId=approval_id,
            decision=decision,
            source=source,
            approvalId=approval_id,
            chain=chain,
            status="approved",
            executionStatus="approved",
            txHash=flow.get("txHash"),
            amountWei=flow.get("amountWei"),
            amount=flow_amount_human,
            amountUnit=flow_amount_unit,
            amountDisplay=flow_amount_display,
            policyBlockedAtCreate=bool(flow.get("policyBlockedAtCreate", False)),
            policyBlockReasonCode=flow.get("policyBlockReasonCode"),
            policyBlockReasonMessage=flow.get("policyBlockReasonMessage"),
            executionMode=flow.get("executionMode"),
            converged=True,
            fromStatus="approved",
            toStatus="approved",
            promptCleanup=cleanup,
            prodDispatch={"mode": "handled_by_web_or_callback"},
            actionHint="Transfer already approved.",
        )
    if status not in {"approval_pending", "approved"}:
        return rt.fail(
            "not_actionable",
            f"Transfer decision is not actionable from status '{status}'.",
            "Use a pending transfer approval.",
            {"approvalId": approval_id, "chain": chain, "status": status},
            exit_code=1,
        )

    if decision == "deny":
        flow["status"] = "rejected"
        flow["reasonCode"] = "approval_rejected"
        flow["reasonMessage"] = str(args.reason_message or "Denied via management/telegram").strip()
        flow["decidedAt"] = rt.utc_now()
        flow["updatedAt"] = flow["decidedAt"]
        flow["terminalAt"] = flow["decidedAt"]
        rt._record_pending_transfer_flow(approval_id, flow)
        rt._mirror_transfer_approval(flow)
        cleanup = rt._cleanup_transfer_approval_prompt(approval_id)
        return rt.ok(
            "Transfer denied.",
            subjectType="transfer",
            subjectId=approval_id,
            decision=decision,
            source=source,
            approvalId=approval_id,
            chain=chain,
            status="rejected",
            executionStatus="rejected",
            reasonCode=flow.get("reasonCode"),
            reasonMessage=flow.get("reasonMessage"),
            transferType=flow.get("transferType"),
            tokenAddress=flow.get("tokenAddress"),
            tokenSymbol=flow_token_symbol,
            tokenDecimals=flow_token_decimals,
            to=flow.get("toAddress"),
            amountWei=flow.get("amountWei"),
            amount=flow_amount_human,
            amountUnit=flow_amount_unit,
            amountDisplay=flow_amount_display,
            policyBlockedAtCreate=bool(flow.get("policyBlockedAtCreate", False)),
            policyBlockReasonCode=flow.get("policyBlockReasonCode"),
            policyBlockReasonMessage=flow.get("policyBlockReasonMessage"),
            executionMode=flow.get("executionMode"),
            fromStatus=status,
            toStatus="rejected",
            promptCleanup=cleanup,
            prodDispatch={"mode": "handled_by_web_or_callback"},
            actionHint="Transfer was denied and will not execute.",
        )

    flow["status"] = "approved"
    flow["decidedAt"] = rt.utc_now()
    flow["updatedAt"] = flow["decidedAt"]
    rt._record_pending_transfer_flow(approval_id, flow)
    rt._mirror_transfer_approval(flow)
    cleanup = rt._cleanup_transfer_approval_prompt(approval_id)
    payload = rt._execute_pending_transfer_flow(flow)
    if isinstance(payload, dict):
        payload.setdefault("subjectType", "transfer")
        payload.setdefault("subjectId", approval_id)
        payload.setdefault("decision", decision)
        payload.setdefault("source", source)
        payload.setdefault("executionStatus", str(payload.get("status") or "unknown"))
        payload.setdefault("fromStatus", status)
        payload.setdefault("toStatus", "approved")
        payload.setdefault("promptCleanup", cleanup)
        payload.setdefault("prodDispatch", {"mode": "handled_by_web_or_callback"})
        payload.setdefault("actionHint", "Execution continued; monitor terminal status.")
    return rt.emit(payload)



def cmd_approvals_request_token(rt: Any, args: Any) -> int:
    chk = rt.require_json_flag(args)
    if chk is not None:
        return chk
    token = str(args.token or "").strip()
    if token == "":
        return rt.fail("invalid_input", "token is required.", "Provide a token address (0x...) and retry.", {"token": token}, exit_code=2)
    token_symbol = None
    token_address = None
    try:
        token_address = rt._resolve_token_address(args.chain, token)
        if not rt.is_hex_address(token):
            token_symbol = token.strip().upper()
    except Exception as exc:
        return rt.fail(
            "invalid_input",
            "token must be a 0x address or a canonical token symbol for the active chain.",
            "Use a token address like 0xabc... or a symbol like USDC/WETH, then retry.",
            {"token": token, "chain": args.chain, "error": str(exc)},
            exit_code=2,
        )
    try:
        payload = {"schemaVersion": 1, "chainKey": args.chain, "requestType": "token_preapprove_add", "tokenAddress": token_address}
        status_code, body = rt._api_request(
            "POST",
            "/agent/policy-approvals/proposed",
            payload=payload,
            include_idempotency=True,
            idempotency_key=f"rt-polreq-token-{args.chain}-{rt._normalize_address(token_address)}-{secrets.token_hex(8)}",
        )
        if status_code < 200 or status_code >= 300:
            return rt.fail(
                str(body.get("code", "api_error")),
                str(body.get("message", f"policy approval request failed ({status_code})")),
                str(body.get("actionHint", "Verify API auth and retry.")),
                {"status": status_code, "chain": args.chain, "token": token},
                exit_code=1,
            )
        policy_approval_id = str(body.get("policyApprovalId", ""))
        status = str(body.get("status", "approval_pending"))
        token_addr = rt._normalize_address(token_address)
        token_display = f"{token_symbol} ({token_addr})" if token_symbol else token_addr
        prompt_sent = False
        if status == "approval_pending":
            try:
                rt._maybe_send_telegram_policy_approval_prompt(
                    {
                        "policyApprovalId": policy_approval_id,
                        "chainKey": args.chain,
                        "status": status,
                        "requestType": "token_preapprove_add",
                        "tokenDisplay": token_display,
                    }
                )
                prompt_sent = True
            except Exception:
                prompt_sent = False
        return rt.ok(
            "Policy approval requested (pending).",
            chain=args.chain,
            policyApprovalId=policy_approval_id,
            status=status,
            requestType="token_preapprove_add",
            tokenAddress=token_addr,
            tokenDisplay=token_display,
            promptSent=prompt_sent,
            actionHint=(
                "Approve or deny in Telegram/management to apply this policy change."
                if prompt_sent
                else "Approve or deny in management (or active Telegram session) to apply this policy change."
            ),
        )
    except Exception as exc:
        return rt.fail(
            "policy_approval_request_failed",
            str(exc),
            "Inspect runtime policy approval request and retry.",
            {"chain": args.chain, "token": token},
            exit_code=1,
        )



def cmd_approvals_request_global(rt: Any, args: Any) -> int:
    chk = rt.require_json_flag(args)
    if chk is not None:
        return chk
    try:
        payload = {"schemaVersion": 1, "chainKey": args.chain, "requestType": "global_approval_enable", "tokenAddress": None}
        status_code, body = rt._api_request(
            "POST",
            "/agent/policy-approvals/proposed",
            payload=payload,
            include_idempotency=True,
            idempotency_key=f"rt-polreq-global-{args.chain}-{secrets.token_hex(8)}",
        )
        if status_code < 200 or status_code >= 300:
            return rt.fail(
                str(body.get("code", "api_error")),
                str(body.get("message", f"policy approval request failed ({status_code})")),
                str(body.get("actionHint", "Verify API auth and retry.")),
                {"status": status_code, "chain": args.chain},
                exit_code=1,
            )
        policy_approval_id = str(body.get("policyApprovalId", ""))
        status = str(body.get("status", "approval_pending"))
        prompt_sent = False
        if status == "approval_pending":
            try:
                rt._maybe_send_telegram_policy_approval_prompt(
                    {
                        "policyApprovalId": policy_approval_id,
                        "chainKey": args.chain,
                        "status": status,
                        "requestType": "global_approval_enable",
                    }
                )
                prompt_sent = True
            except Exception:
                prompt_sent = False
        return rt.ok(
            "Policy approval requested (pending).",
            chain=args.chain,
            policyApprovalId=policy_approval_id,
            status=status,
            requestType="global_approval_enable",
            promptSent=prompt_sent,
            actionHint=(
                "Approve or deny in Telegram/management to apply this policy change."
                if prompt_sent
                else "Approve or deny in management (or active Telegram session) to apply this policy change."
            ),
        )
    except Exception as exc:
        return rt.fail("policy_approval_request_failed", str(exc), "Inspect runtime policy approval request and retry.", {"chain": args.chain}, exit_code=1)



def cmd_approvals_revoke_token(rt: Any, args: Any) -> int:
    chk = rt.require_json_flag(args)
    if chk is not None:
        return chk
    token = str(args.token or "").strip()
    if token == "":
        return rt.fail("invalid_input", "token is required.", "Provide a token address (0x...) and retry.", {"token": token}, exit_code=2)
    token_symbol = None
    token_address = None
    try:
        token_address = rt._resolve_token_address(args.chain, token)
        if not rt.is_hex_address(token):
            token_symbol = token.strip().upper()
    except Exception as exc:
        return rt.fail(
            "invalid_input",
            "token must be a 0x address or a canonical token symbol for the active chain.",
            "Use a token address like 0xabc... or a symbol like USDC/WETH, then retry.",
            {"token": token, "chain": args.chain, "error": str(exc)},
            exit_code=2,
        )
    try:
        payload = {"schemaVersion": 1, "chainKey": args.chain, "requestType": "token_preapprove_remove", "tokenAddress": token_address}
        status_code, body = rt._api_request(
            "POST",
            "/agent/policy-approvals/proposed",
            payload=payload,
            include_idempotency=True,
            idempotency_key=f"rt-polrev-token-{args.chain}-{rt._normalize_address(token_address)}-{secrets.token_hex(8)}",
        )
        if status_code < 200 or status_code >= 300:
            return rt.fail(
                str(body.get("code", "api_error")),
                str(body.get("message", f"policy approval request failed ({status_code})")),
                str(body.get("actionHint", "Verify API auth and retry.")),
                {"status": status_code, "chain": args.chain, "token": token},
                exit_code=1,
            )
        policy_approval_id = str(body.get("policyApprovalId", ""))
        status = str(body.get("status", "approval_pending"))
        token_addr = rt._normalize_address(token_address)
        token_display = f"{token_symbol} ({token_addr})" if token_symbol else token_addr
        prompt_sent = False
        if status == "approval_pending":
            try:
                rt._maybe_send_telegram_policy_approval_prompt(
                    {
                        "policyApprovalId": policy_approval_id,
                        "chainKey": args.chain,
                        "status": status,
                        "requestType": "token_preapprove_remove",
                        "tokenDisplay": token_display,
                    }
                )
                prompt_sent = True
            except Exception:
                prompt_sent = False
        return rt.ok(
            "Policy revoke requested (pending).",
            chain=args.chain,
            policyApprovalId=policy_approval_id,
            status=status,
            requestType="token_preapprove_remove",
            tokenAddress=token_addr,
            tokenDisplay=token_display,
            promptSent=prompt_sent,
            actionHint=(
                "Approve or deny in Telegram/management to apply this policy change."
                if prompt_sent
                else "Approve or deny in management (or active Telegram session) to apply this policy change."
            ),
        )
    except Exception as exc:
        return rt.fail(
            "policy_approval_request_failed",
            str(exc),
            "Inspect runtime policy revoke request and retry.",
            {"chain": args.chain, "token": token},
            exit_code=1,
        )



def cmd_approvals_revoke_global(rt: Any, args: Any) -> int:
    chk = rt.require_json_flag(args)
    if chk is not None:
        return chk
    try:
        payload = {"schemaVersion": 1, "chainKey": args.chain, "requestType": "global_approval_disable", "tokenAddress": None}
        status_code, body = rt._api_request(
            "POST",
            "/agent/policy-approvals/proposed",
            payload=payload,
            include_idempotency=True,
            idempotency_key=f"rt-polrev-global-{args.chain}-{secrets.token_hex(8)}",
        )
        if status_code < 200 or status_code >= 300:
            return rt.fail(
                str(body.get("code", "api_error")),
                str(body.get("message", f"policy approval request failed ({status_code})")),
                str(body.get("actionHint", "Verify API auth and retry.")),
                {"status": status_code, "chain": args.chain},
                exit_code=1,
            )
        policy_approval_id = str(body.get("policyApprovalId", ""))
        status = str(body.get("status", "approval_pending"))
        prompt_sent = False
        if status == "approval_pending":
            try:
                rt._maybe_send_telegram_policy_approval_prompt(
                    {
                        "policyApprovalId": policy_approval_id,
                        "chainKey": args.chain,
                        "status": status,
                        "requestType": "global_approval_disable",
                    }
                )
                prompt_sent = True
            except Exception:
                prompt_sent = False
        return rt.ok(
            "Policy revoke requested (pending).",
            chain=args.chain,
            policyApprovalId=policy_approval_id,
            status=status,
            requestType="global_approval_disable",
            promptSent=prompt_sent,
            actionHint=(
                "Approve or deny in Telegram/management to apply this policy change."
                if prompt_sent
                else "Approve or deny in management (or active Telegram session) to apply this policy change."
            ),
        )
    except Exception as exc:
        return rt.fail("policy_approval_request_failed", str(exc), "Inspect runtime policy revoke request and retry.", {"chain": args.chain}, exit_code=1)



def cmd_approvals_check(rt: Any, args: Any) -> int:
    chk = rt.require_json_flag(args)
    if chk is not None:
        return chk
    try:
        trade = rt._read_trade_details(args.intent)
        if str(trade.get("chainKey")) != args.chain:
            return rt.fail(
                "chain_mismatch",
                "Trade chain does not match command --chain.",
                "Use matching chain or refresh intent selection.",
                {"tradeId": args.intent, "tradeChain": trade.get("chainKey"), "requestedChain": args.chain},
                exit_code=1,
            )

        status = str(trade.get("status"))
        retry = trade.get("retry") if isinstance(trade.get("retry"), dict) else {}
        retry_eligible = bool(retry.get("eligible", False))
        if status == "approved" or (status == "failed" and retry_eligible):
            return rt.ok("Approval check passed.", tradeId=args.intent, chain=args.chain, approved=True, status=status, retry=retry)
        if status == "approval_pending":
            return rt.fail("approval_required", "Trade is waiting for management approval.", "Approve trade from authorized management view.", {"tradeId": args.intent}, exit_code=1)
        if status == "rejected":
            return rt.fail("approval_rejected", "Trade approval was rejected.", "Review rejection reason and create a new trade if needed.", {"tradeId": args.intent, "reasonCode": trade.get("reasonCode")}, exit_code=1)
        if status == "expired":
            return rt.fail("approval_expired", "Trade approval has expired.", "Re-propose trade and request approval again.", {"tradeId": args.intent}, exit_code=1)
        return rt.fail(
            "policy_denied",
            f"Trade is not executable from status '{status}'.",
            "Poll intents and execute only actionable trades.",
            {"tradeId": args.intent, "status": status, "retry": retry},
            exit_code=1,
        )
    except rt.WalletStoreError as exc:
        return rt.fail("approval_check_failed", str(exc), "Verify API env, auth, and trade visibility.", {"tradeId": args.intent, "chain": args.chain}, exit_code=1)
    except Exception as exc:
        return rt.fail("approval_check_failed", str(exc), "Inspect runtime approval-check path and retry.", {"tradeId": args.intent, "chain": args.chain}, exit_code=1)
