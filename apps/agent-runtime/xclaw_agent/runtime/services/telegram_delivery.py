from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class TelegramDeliveryServiceContext:
    telegram_dispatch_suppressed_for_harness: Callable[[], bool]
    read_openclaw_last_delivery: Callable[[], dict[str, Any] | None]
    get_approval_prompt: Callable[[str], dict[str, Any] | None]
    get_transfer_approval_prompt: Callable[[str], dict[str, Any] | None]
    get_policy_approval_prompt: Callable[[str], dict[str, Any] | None]
    record_approval_prompt: Callable[[str, dict[str, Any]], None]
    record_transfer_approval_prompt: Callable[[str, dict[str, Any]], None]
    record_policy_approval_prompt: Callable[[str, dict[str, Any]], None]
    require_openclaw_bin: Callable[[], str]
    run_subprocess: Callable[..., Any]
    wallet_store_error: type[BaseException]
    extract_openclaw_message_id: Callable[[str], str | None]
    utc_now: Callable[[], str]
    display_chain_key: Callable[[str], str]
    token_symbol_for_display: Callable[[str, str], str]
    is_solana_chain: Callable[[str], bool]
    is_solana_address: Callable[[str], bool]
    solana_mint_decimals: Callable[[str, str], int]
    normalize_amount_human_text: Callable[[str], str]
    format_units: Callable[[int, int], str]
    canonical_token_map: Callable[[str], dict[str, str]]
    shutil_module: Any
    re_module: Any
    clear_telegram_approval_buttons: Callable[[str, str], dict[str, Any]]
    remove_approval_prompt: Callable[[str], None]
    remove_transfer_approval_prompt: Callable[[str], None]
    remove_policy_approval_prompt: Callable[[str], None]


def _thread_id_from_delivery(delivery: dict[str, Any]) -> str | None:
    thread_raw = delivery.get("lastThreadId")
    if isinstance(thread_raw, int):
        return str(thread_raw)
    if isinstance(thread_raw, str) and thread_raw.strip():
        return thread_raw.strip()
    return None


def _send_telegram_message(
    ctx: TelegramDeliveryServiceContext,
    *,
    chat_id: str,
    thread_id: str | None,
    text: str,
    buttons: str | None = None,
) -> str | None:
    openclaw = ctx.require_openclaw_bin()
    cmd = [openclaw, "message", "send", "--channel", "telegram", "--target", chat_id, "--message", text]
    if buttons is not None:
        cmd.extend(["--buttons", buttons])
    cmd.append("--json")
    if thread_id:
        cmd.extend(["--thread-id", thread_id])
    proc = ctx.run_subprocess(cmd, timeout_sec=30 if buttons is not None else 20, kind="openclaw_send")
    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        stdout = (proc.stdout or "").strip()
        raise ctx.wallet_store_error(stderr or stdout or "openclaw message send failed.")
    return ctx.extract_openclaw_message_id(proc.stdout or "")


def maybe_send_transfer_approval_prompt(ctx: TelegramDeliveryServiceContext, flow: dict[str, Any]) -> None:
    if ctx.telegram_dispatch_suppressed_for_harness():
        return
    approval_id = str(flow.get("approvalId") or "").strip()
    chain = str(flow.get("chainKey") or "").strip()
    if not approval_id or not chain:
        return
    existing = ctx.get_transfer_approval_prompt(approval_id)
    if existing and str(existing.get("channel") or "") == "telegram":
        return
    delivery = ctx.read_openclaw_last_delivery()
    if not delivery or str(delivery.get("lastChannel") or "").lower() != "telegram":
        return
    chat_id = str(delivery.get("lastTo") or "").strip()
    if not chat_id:
        return
    thread_id = _thread_id_from_delivery(delivery)
    callback_approve = f"xfer|a|{approval_id}|{chain}"
    callback_deny = f"xfer|r|{approval_id}|{chain}"
    if len(callback_approve.encode("utf-8")) > 64 or len(callback_deny.encode("utf-8")) > 64:
        return
    display_chain = ctx.display_chain_key(chain)
    transfer_type = str(flow.get("transferType") or "token").strip().lower()
    token_symbol = str(flow.get("tokenSymbol") or ("ETH" if transfer_type == "native" else "TOKEN")).strip() or "TOKEN"
    token_decimals = 18
    try:
        token_decimals = int(flow.get("tokenDecimals", 18))
    except Exception:
        token_decimals = 18
    amount_wei = str(flow.get("amountWei") or "0").strip() or "0"
    try:
        amount_value = int(amount_wei)
        divisor = 10**token_decimals
        whole = amount_value // divisor
        frac = amount_value % divisor
        amount_human = str(whole) if frac == 0 else f"{whole}.{str(frac).rjust(token_decimals, '0').rstrip('0')}"
    except Exception:
        amount_human = amount_wei
    destination = str(flow.get("toAddress") or "").strip().lower() or "unknown"
    text = (
        "Approve transfer\n"
        f"Amount: {amount_human} {token_symbol}\n"
        f"To: `{destination}`\n"
        f"Chain: `{display_chain}`\n"
        f"Approval: `{approval_id}`\n\n"
        "Tap Approve to continue (or Deny to reject)."
    )
    if bool(flow.get("policyBlockedAtCreate")):
        reason_code = str(flow.get("policyBlockReasonCode") or "unknown")
        text += f"\n\nPolicy blocked at create: {reason_code}\nApprove executes this transfer as a one-off override."
    buttons = json.dumps([[{"text": "Approve", "callback_data": callback_approve}, {"text": "Deny", "callback_data": callback_deny}]], separators=(",", ":"))
    message_id = _send_telegram_message(ctx, chat_id=chat_id, thread_id=thread_id, text=text, buttons=buttons) or "unknown"
    ctx.record_transfer_approval_prompt(
        approval_id,
        {"channel": "telegram", "chainKey": chain, "to": chat_id, "threadId": thread_id, "messageId": message_id, "createdAt": ctx.utc_now()},
    )


def maybe_send_policy_approval_prompt(ctx: TelegramDeliveryServiceContext, flow: dict[str, Any]) -> None:
    if ctx.telegram_dispatch_suppressed_for_harness():
        return
    approval_id = str(flow.get("policyApprovalId") or flow.get("approvalId") or "").strip()
    chain = str(flow.get("chainKey") or "").strip()
    if not approval_id or not chain:
        return
    existing = ctx.get_policy_approval_prompt(approval_id)
    if existing and str(existing.get("channel") or "") == "telegram":
        return
    delivery = ctx.read_openclaw_last_delivery()
    if not delivery or str(delivery.get("lastChannel") or "").lower() != "telegram":
        return
    chat_id = str(delivery.get("lastTo") or "").strip()
    if not chat_id:
        return
    thread_id = _thread_id_from_delivery(delivery)
    callback_approve = f"xpol|a|{approval_id}|{chain}"
    callback_deny = f"xpol|r|{approval_id}|{chain}"
    if len(callback_approve.encode("utf-8")) > 64 or len(callback_deny.encode("utf-8")) > 64:
        return
    display_chain = ctx.display_chain_key(chain)
    request_type = str(flow.get("requestType") or "").strip().lower()
    token_display = str(flow.get("tokenDisplay") or "").strip()
    request_label = "Policy update"
    if request_type == "token_preapprove_add":
        request_label = "Preapprove token for trading"
    elif request_type == "token_preapprove_remove":
        request_label = "Revoke preapproved token"
    elif request_type == "global_approval_enable":
        request_label = "Enable Approve all (global trading)"
    elif request_type == "global_approval_disable":
        request_label = "Disable Approve all (global trading)"
    lines = ["Approve policy change", f"Request: {request_label}"]
    if token_display:
        lines.append(f"Token: {token_display}")
    lines.extend([f"Chain: {display_chain}", f"Approval ID: {approval_id}", "Status: approval_pending", "", "Tap Approve to apply (or Deny to reject)."])
    buttons = json.dumps([[{"text": "Approve", "callback_data": callback_approve}, {"text": "Deny", "callback_data": callback_deny}]], separators=(",", ":"))
    message_id = _send_telegram_message(ctx, chat_id=chat_id, thread_id=thread_id, text="\n".join(lines), buttons=buttons) or "unknown"
    ctx.record_policy_approval_prompt(
        approval_id,
        {"channel": "telegram", "chainKey": chain, "to": chat_id, "threadId": thread_id, "messageId": message_id, "createdAt": ctx.utc_now()},
    )


def maybe_send_liquidity_approval_prompt(ctx: TelegramDeliveryServiceContext, flow: dict[str, Any]) -> None:
    if ctx.telegram_dispatch_suppressed_for_harness():
        return
    liquidity_intent_id = str(flow.get("liquidityIntentId") or "").strip()
    chain = str(flow.get("chainKey") or "").strip()
    if not liquidity_intent_id or not chain:
        return
    existing = ctx.get_approval_prompt(liquidity_intent_id)
    if existing and str(existing.get("channel") or "") == "telegram":
        return
    delivery = ctx.read_openclaw_last_delivery()
    if not delivery or str(delivery.get("lastChannel") or "").lower() != "telegram":
        return
    chat_id = str(delivery.get("lastTo") or "").strip()
    if not chat_id:
        return
    thread_id = _thread_id_from_delivery(delivery)
    callback_approve = f"xliq|a|{liquidity_intent_id}|{chain}"
    callback_deny = f"xliq|r|{liquidity_intent_id}|{chain}"
    if len(callback_approve.encode("utf-8")) > 64 or len(callback_deny.encode("utf-8")) > 64:
        return
    display_chain = ctx.display_chain_key(chain)
    action = str(flow.get("action") or "remove").strip().lower()
    dex = str(flow.get("dex") or "unknown").strip().lower() or "unknown"
    token_a = str(flow.get("tokenASymbol") or ctx.token_symbol_for_display(chain, str(flow.get("tokenA") or "")) or "TOKEN").strip() or "TOKEN"
    token_b = str(flow.get("tokenBSymbol") or ctx.token_symbol_for_display(chain, str(flow.get("tokenB") or "")) or "TOKEN").strip() or "TOKEN"
    amount_a = str(flow.get("amountA") or "").strip()
    amount_b = str(flow.get("amountB") or "").strip()
    position_id = str(flow.get("positionId") or "").strip()
    percent = str(flow.get("percent") or "").strip()
    lines = [
        "Approve liquidity action",
        f"Action: {action}",
        f"Pair: {token_a}/{token_b}",
        f"Chain: `{display_chain}`",
        f"DEX: `{dex}`",
        f"Intent ID: `{liquidity_intent_id}`",
        "Status: approval_pending",
    ]
    if position_id:
        lines.append(f"Position ID: `{position_id}`")
    if percent:
        lines.append(f"Percent: {percent}%")
    if amount_a or amount_b:
        lines.append(f"Amounts: {amount_a or '?'} / {amount_b or '?'}")
    lines.extend(["", "Tap Approve to execute (or Deny to reject)."])
    buttons = json.dumps([[{"text": "Approve", "callback_data": callback_approve}, {"text": "Deny", "callback_data": callback_deny}]], separators=(",", ":"))
    message_id = _send_telegram_message(ctx, chat_id=chat_id, thread_id=thread_id, text="\n".join(lines), buttons=buttons) or "unknown"
    ctx.record_approval_prompt(
        liquidity_intent_id,
        {"channel": "telegram", "chainKey": chain, "to": chat_id, "threadId": thread_id, "messageId": message_id, "createdAt": ctx.utc_now()},
    )


def maybe_send_decision_message(
    ctx: TelegramDeliveryServiceContext,
    *,
    trade_id: str,
    chain: str,
    decision: str,
    summary: dict[str, Any] | None,
    trade: dict[str, Any] | None,
) -> None:
    if ctx.telegram_dispatch_suppressed_for_harness():
        return
    chat_id = ""
    thread_id: str | None = None
    prompt = ctx.get_approval_prompt(trade_id)
    if prompt and str(prompt.get("channel") or "") == "telegram":
        chat_id = str(prompt.get("to") or "").strip()
        thread_raw = prompt.get("threadId")
        if isinstance(thread_raw, int):
            thread_id = str(thread_raw)
        elif isinstance(thread_raw, str) and thread_raw.strip():
            thread_id = thread_raw.strip()
    if not chat_id:
        delivery = ctx.read_openclaw_last_delivery()
        if not delivery or str(delivery.get("lastChannel") or "").lower() != "telegram":
            return
        chat_id = str(delivery.get("lastTo") or "").strip()
        if not chat_id:
            return
        thread_id = _thread_id_from_delivery(delivery)
    display_chain = ctx.display_chain_key(chain)
    summary = summary or {}
    trade = trade or {}
    amount = str(summary.get("amountInHuman") or "").strip() or str(trade.get("amountIn") or "").strip() or "?"
    token_in_raw = str(trade.get("tokenIn") or "").strip()
    token_out_raw = str(trade.get("tokenOut") or "").strip()
    token_in = str(summary.get("tokenInSymbol") or "").strip() or token_in_raw or "TOKEN_IN"
    token_out = str(summary.get("tokenOutSymbol") or "").strip() or token_out_raw or "TOKEN_OUT"
    if not str(summary.get("amountInHuman") or "").strip() and ctx.is_solana_chain(chain) and token_in_raw and ctx.is_solana_address(token_in_raw):
        amount_raw = str(trade.get("amountIn") or "").strip()
        if amount_raw and amount_raw.isdigit():
            try:
                token_in_decimals = ctx.solana_mint_decimals(chain, token_in_raw)
                amount = ctx.normalize_amount_human_text(ctx.format_units(int(amount_raw), token_in_decimals))
            except Exception:
                pass
    token_in = ctx.token_symbol_for_display(chain, token_in)
    token_out = ctx.token_symbol_for_display(chain, token_out)
    slip = summary.get("slippageBps")
    slip_str = ""
    try:
        if slip is not None:
            slip_str = f" (slippage {int(slip)} bps)"
    except Exception:
        slip_str = ""
    if decision == "approved":
        text = (
            "Approval received.\n\n"
            f"• Pair: {amount} {token_in} -> {token_out}{slip_str}\n"
            f"• Trade ID: `{trade_id}`\n"
            f"• Chain: `{display_chain}`\n\n"
            "Executing now. I will send a final success/failure update after on-chain outcome is known."
        )
    else:
        reason_code = str(trade.get("reasonCode") or "").strip()
        reason_message = str(trade.get("reasonMessage") or "").strip()
        reason = reason_message or reason_code or "Denied."
        text = f"Denied swap\n{amount} {token_in} -> {token_out}{slip_str}\nChain: {display_chain}\nTrade: {trade_id}\n\nReason: {reason}"
    openclaw = ctx.shutil_module.which("openclaw")
    if not openclaw:
        return
    proc = ctx.run_subprocess(
        [openclaw, "message", "send", "--channel", "telegram", "--target", chat_id, "--message", text, *(["--thread-id", thread_id] if thread_id else []), "--json"],
        timeout_sec=20,
        kind="openclaw_send",
    )
    if proc.returncode != 0:
        return


def maybe_send_trade_terminal_message(
    ctx: TelegramDeliveryServiceContext,
    *,
    trade_id: str,
    chain: str,
    status: str,
    tx_hash: str | None = None,
    reason_message: str | None = None,
) -> None:
    if ctx.telegram_dispatch_suppressed_for_harness():
        return
    normalized = str(status or "").strip().lower()
    if normalized not in {"filled", "failed", "rejected", "verification_timeout"}:
        return
    chat_id = ""
    thread_id: str | None = None
    prompt = ctx.get_approval_prompt(trade_id)
    if prompt and str(prompt.get("channel") or "") == "telegram":
        chat_id = str(prompt.get("to") or "").strip()
        thread_raw = prompt.get("threadId")
        if isinstance(thread_raw, int):
            thread_id = str(thread_raw)
        elif isinstance(thread_raw, str) and thread_raw.strip():
            thread_id = thread_raw.strip()
    if not chat_id:
        delivery = ctx.read_openclaw_last_delivery()
        if not delivery or str(delivery.get("lastChannel") or "").lower() != "telegram":
            return
        chat_id = str(delivery.get("lastTo") or "").strip()
        if not chat_id:
            return
        thread_id = _thread_id_from_delivery(delivery)
    display_chain = ctx.display_chain_key(chain)
    tx_hash_clean = str(tx_hash or "").strip()
    if normalized == "filled" and not tx_hash_clean:
        normalized = "failed"
        if not str(reason_message or "").strip():
            reason_message = "Execution reported filled without tx hash; treating as unverified."
    tx_line = f"\nTx: `{tx_hash_clean}`" if tx_hash_clean else ""
    if normalized == "filled":
        text = f"Swap completed.\n\nTrade: `{trade_id}`\nChain: `{display_chain}`{tx_line}"
    else:
        reason = str(reason_message or "").strip() or "Execution failed."
        text = f"Swap failed.\n\nTrade: `{trade_id}`\nChain: `{display_chain}`\nReason: {reason}{tx_line}"
    openclaw = ctx.shutil_module.which("openclaw")
    if not openclaw:
        return
    proc = ctx.run_subprocess(
        [openclaw, "message", "send", "--channel", "telegram", "--target", chat_id, "--message", text, *(["--thread-id", thread_id] if thread_id else []), "--json"],
        timeout_sec=20,
        kind="openclaw_send",
    )
    if proc.returncode != 0:
        return


def resolve_telegram_bot_token(ctx: TelegramDeliveryServiceContext) -> str | None:
    for candidate in (os.environ.get("XCLAW_TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_BOT_TOKEN")):
        token = str(candidate or "").strip()
        if token:
            return token
    try:
        openclaw = ctx.require_openclaw_bin()
    except Exception:
        return None
    try:
        proc = ctx.run_subprocess([openclaw, "config", "get", "channels.telegram.botToken", "--json"], timeout_sec=5, kind="openclaw_config_get")
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    raw = str(proc.stdout or "").strip()
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, str) and parsed.strip():
            return parsed.strip()
    except Exception:
        pass
    if raw.startswith('"') and raw.endswith('"'):
        raw = raw[1:-1]
    raw = raw.strip()
    return raw or None


def cleanup_prompt(ctx: TelegramDeliveryServiceContext, subject_type: str, subject_id: str) -> dict[str, Any]:
    try:
        result = ctx.clear_telegram_approval_buttons(subject_type, subject_id)
        return dict(result.get("promptCleanup") or {"ok": bool(result.get("ok")), "code": str(result.get("code") or "unknown")})
    except Exception as exc:
        return {"ok": False, "code": "prompt_cleanup_failed", "error": str(exc)[:300]}
