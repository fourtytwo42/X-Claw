from __future__ import annotations

import json
import os
import pathlib
import re
import shutil
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable


@dataclass(frozen=True)
class ApprovalPromptContext:
    ensure_app_dir: Callable[[], None]
    prompts_file: pathlib.Path
    json_module: Any
    os_module: Any
    pathlib_module: Any
    utc_now: Callable[[], str]
    parse_iso_utc: Callable[[str | None], datetime | None]
    get_approval_prompt: Callable[[str], dict[str, Any] | None]
    record_approval_prompt: Callable[[str, dict[str, Any]], None]
    post_approval_prompt_metadata: Callable[[str, str, str, str | None, str], None]
    read_openclaw_last_delivery: Callable[[], dict[str, Any] | None]
    maybe_send_telegram_approval_prompt: Callable[[str, str, dict[str, Any] | None], None]
    trade_approval_prompt_resend_cooldown_sec: Callable[[], int]
    telegram_dispatch_suppressed_for_harness: Callable[[], bool]
    display_chain_key: Callable[[str], str]
    transfer_amount_display: Callable[[str | int, str, str | None, int | None], tuple[str, str]]
    token_symbol_for_display: Callable[[str, str], str]
    is_solana_chain: Callable[[str], bool]
    is_solana_address: Callable[[str], bool]
    solana_mint_decimals: Callable[[str, str], int]
    normalize_amount_human_text: Callable[[str], str]
    format_units: Callable[[int, int], str]
    require_openclaw_bin: Callable[[], str]
    run_subprocess: Callable[..., Any]
    extract_openclaw_message_id: Callable[[str], str | None]
    api_request: Callable[..., tuple[int, dict[str, Any]]]
    wallet_store_error: type[BaseException]
    openclaw_state_dir: Callable[[], pathlib.Path]
    sanitize_openclaw_agent_id: Callable[[str | None], str]
    approval_wait_timeout_sec: int
    approval_wait_poll_sec: float
    last_delivery_is_telegram: Callable[[], bool]
    trade_approval_inline_wait_sec: Callable[[], int]
    read_trade_details: Callable[[str], dict[str, Any]]
    maybe_delete_telegram_approval_prompt: Callable[[str], None]
    maybe_send_telegram_decision_message: Callable[..., None]
    remove_pending_spot_trade_flow: Callable[[str], None]
    remove_approval_prompt: Callable[[str], None]
    time_module: Any
    wallet_policy_error: type[BaseException]



def load_approval_prompts(ctx: ApprovalPromptContext) -> dict[str, Any]:
    try:
        ctx.ensure_app_dir()
        if not ctx.prompts_file.exists():
            return {"prompts": {}}
        raw = ctx.prompts_file.read_text(encoding="utf-8")
        payload = ctx.json_module.loads(raw or "{}")
        if not isinstance(payload, dict):
            return {"prompts": {}}
        prompts = payload.get("prompts")
        if not isinstance(prompts, dict):
            payload["prompts"] = {}
        return payload
    except Exception:
        return {"prompts": {}}



def save_approval_prompts(ctx: ApprovalPromptContext, payload: dict[str, Any]) -> None:
    ctx.ensure_app_dir()
    if not isinstance(payload.get("prompts"), dict):
        payload["prompts"] = {}
    tmp = f"{ctx.prompts_file}.{ctx.os_module.getpid()}.tmp"
    ctx.pathlib_module.Path(tmp).write_text(ctx.json_module.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    ctx.os_module.chmod(tmp, 0o600)
    ctx.pathlib_module.Path(tmp).replace(ctx.prompts_file)
    ctx.os_module.chmod(ctx.prompts_file, 0o600)



def record_approval_prompt(ctx: ApprovalPromptContext, trade_id: str, prompt: dict[str, Any]) -> None:
    state = load_approval_prompts(ctx)
    prompts = state.get("prompts")
    if not isinstance(prompts, dict):
        prompts = {}
        state["prompts"] = prompts
    prompts[trade_id] = {**prompt, "updatedAt": ctx.utc_now()}
    save_approval_prompts(ctx, state)



def transfer_prompt_key(approval_id: str) -> str:
    return f"xfer:{approval_id}"



def policy_prompt_key(approval_id: str) -> str:
    return f"xpol:{approval_id}"



def get_approval_prompt(ctx: ApprovalPromptContext, trade_id: str) -> dict[str, Any] | None:
    state = load_approval_prompts(ctx)
    prompts = state.get("prompts")
    if not isinstance(prompts, dict):
        return None
    entry = prompts.get(trade_id)
    return entry if isinstance(entry, dict) else None



def record_transfer_approval_prompt(ctx: ApprovalPromptContext, approval_id: str, prompt: dict[str, Any]) -> None:
    record_approval_prompt(ctx, transfer_prompt_key(approval_id), {**prompt, "promptType": "transfer", "approvalId": approval_id})



def get_transfer_approval_prompt(ctx: ApprovalPromptContext, approval_id: str) -> dict[str, Any] | None:
    return get_approval_prompt(ctx, transfer_prompt_key(approval_id))



def record_policy_approval_prompt(ctx: ApprovalPromptContext, approval_id: str, prompt: dict[str, Any]) -> None:
    record_approval_prompt(ctx, policy_prompt_key(approval_id), {**prompt, "promptType": "policy", "approvalId": approval_id})



def get_policy_approval_prompt(ctx: ApprovalPromptContext, approval_id: str) -> dict[str, Any] | None:
    return get_approval_prompt(ctx, policy_prompt_key(approval_id))



def remove_approval_prompt(ctx: ApprovalPromptContext, trade_id: str) -> None:
    state = load_approval_prompts(ctx)
    prompts = state.get("prompts")
    if not isinstance(prompts, dict):
        return
    if trade_id in prompts:
        prompts.pop(trade_id, None)
        save_approval_prompts(ctx, state)



def remove_transfer_approval_prompt(ctx: ApprovalPromptContext, approval_id: str) -> None:
    remove_approval_prompt(ctx, transfer_prompt_key(approval_id))



def remove_policy_approval_prompt(ctx: ApprovalPromptContext, approval_id: str) -> None:
    remove_approval_prompt(ctx, policy_prompt_key(approval_id))



def read_openclaw_last_delivery(ctx: ApprovalPromptContext) -> dict[str, Any] | None:
    agent_id = ctx.sanitize_openclaw_agent_id(os.environ.get("XCLAW_OPENCLAW_AGENT_ID"))
    store_path = ctx.openclaw_state_dir() / "agents" / agent_id / "sessions" / "sessions.json"
    if not store_path.exists():
        return None
    try:
        raw = store_path.read_text(encoding="utf-8")
        payload = ctx.json_module.loads(raw or "{}")
        if not isinstance(payload, dict):
            return None
        best: dict[str, Any] | None = None
        best_updated = -1
        for _, entry in payload.items():
            if not isinstance(entry, dict):
                continue
            try:
                updated_ms = int(entry.get("updatedAt")) if entry.get("updatedAt") is not None else 0
            except Exception:
                updated_ms = 0
            last_channel = str(entry.get("lastChannel") or "").strip().lower()
            last_to = str(entry.get("lastTo") or "").strip()
            if not last_channel or not last_to:
                continue
            if updated_ms >= best_updated:
                best_updated = updated_ms
                best = {"lastChannel": last_channel, "lastTo": last_to, "lastThreadId": entry.get("lastThreadId")}
        return best
    except Exception:
        return None



def _thread_id_from_delivery(delivery: dict[str, Any]) -> str | None:
    thread_raw = delivery.get("lastThreadId")
    if isinstance(thread_raw, int):
        return str(thread_raw)
    if isinstance(thread_raw, str) and thread_raw.strip():
        return thread_raw.strip()
    return None



def post_approval_prompt_metadata(ctx: ApprovalPromptContext, trade_id: str, chain: str, to_addr: str, thread_id: str | None, message_id: str) -> None:
    payload: dict[str, Any] = {
        "schemaVersion": 1,
        "tradeId": trade_id,
        "chainKey": chain,
        "channel": "telegram",
        "to": to_addr,
        "messageId": message_id,
    }
    if thread_id:
        payload["threadId"] = thread_id
    status_code, body = ctx.api_request(
        "POST",
        "/agent/approvals/prompt",
        payload=payload,
        include_idempotency=True,
        idempotency_key=f"rt-appr-prompt-{trade_id}-{os.urandom(8).hex()}",
    )
    if status_code < 200 or status_code >= 300:
        code = str(body.get("code", "api_error"))
        message = str(body.get("message", f"prompt report failed ({status_code})"))
        raise ctx.wallet_store_error(f"{code}: {message}")



def maybe_send_telegram_approval_prompt(ctx: ApprovalPromptContext, trade_id: str, chain: str, summary: dict[str, Any] | None = None) -> None:
    if ctx.telegram_dispatch_suppressed_for_harness():
        return
    existing = ctx.get_approval_prompt(trade_id)
    if existing and str(existing.get("channel") or "") == "telegram":
        updated_at = ctx.parse_iso_utc(str(existing.get("updatedAt") or existing.get("createdAt") or ""))
        if updated_at is not None:
            age_sec = (datetime.now(timezone.utc) - updated_at).total_seconds()
            if age_sec < float(ctx.trade_approval_prompt_resend_cooldown_sec()):
                return
    delivery = ctx.read_openclaw_last_delivery()
    if not delivery or str(delivery.get("lastChannel") or "").lower() != "telegram":
        return
    chat_id = str(delivery.get("lastTo") or "").strip()
    if not chat_id:
        return
    thread_id = _thread_id_from_delivery(delivery)
    callback_approve = f"xappr|a|{trade_id}|{chain}"
    callback_reject = f"xappr|r|{trade_id}|{chain}"
    if len(callback_approve.encode("utf-8")) > 64 or len(callback_reject.encode("utf-8")) > 64:
        return
    display_chain = ctx.display_chain_key(chain)
    summary = summary or {}
    amount = str(summary.get("amountInHuman") or "").strip() or "?"
    token_in_symbol = str(summary.get("tokenInSymbol") or "").strip() or "TOKEN_IN"
    token_out_symbol = str(summary.get("tokenOutSymbol") or "").strip() or "TOKEN_OUT"
    text = (
        "Approve swap\n"
        f"{amount} {token_in_symbol} -> {token_out_symbol}\n"
        f"Chain: `{display_chain}`\n"
        f"Trade: `{trade_id}`\n\n"
        "Tap Approve to continue (or Deny to reject). This will submit an on-chain transaction from the agent wallet."
    )
    buttons = ctx.json_module.dumps([[{"text": "Approve", "callback_data": callback_approve}, {"text": "Deny", "callback_data": callback_reject}]], separators=(",", ":"))
    openclaw = ctx.require_openclaw_bin()
    cmd = [openclaw, "message", "send", "--channel", "telegram", "--target", chat_id, "--message", text, "--buttons", buttons, "--json"]
    if thread_id:
        cmd.extend(["--thread-id", thread_id])
    proc = ctx.run_subprocess(cmd, timeout_sec=30, kind="openclaw_send")
    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        stdout = (proc.stdout or "").strip()
        raise ctx.wallet_store_error(stderr or stdout or "openclaw message send failed.")
    message_id = ctx.extract_openclaw_message_id(proc.stdout or "") or "unknown"
    ctx.record_approval_prompt(trade_id, {"channel": "telegram", "chainKey": chain, "to": chat_id, "threadId": thread_id, "messageId": message_id, "createdAt": ctx.utc_now()})
    try:
        ctx.post_approval_prompt_metadata(trade_id, chain, chat_id, thread_id, message_id)
    except Exception:
        pass



def maybe_delete_telegram_approval_prompt(ctx: ApprovalPromptContext, trade_id: str) -> None:
    entry = ctx.get_approval_prompt(trade_id)
    if not entry or str(entry.get("channel") or "") != "telegram":
        return
    remove_approval_prompt(ctx, trade_id)



def normalize_telegram_target(value: str) -> str:
    raw = str(value or "").strip()
    if raw.startswith("telegram:"):
        return raw[len("telegram:") :]
    return raw



def resolve_telegram_bot_token(ctx: ApprovalPromptContext) -> str | None:
    for candidate in (os.environ.get("XCLAW_TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_BOT_TOKEN")):
        token = str(candidate or "").strip()
        if token:
            return token
    try:
        openclaw = ctx.require_openclaw_bin()
        proc = ctx.run_subprocess([openclaw, "config", "get", "channels.telegram.botToken", "--json"], timeout_sec=5, kind="openclaw_config_get")
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    raw = str(proc.stdout or "").strip()
    if not raw:
        return None
    try:
        parsed = ctx.json_module.loads(raw)
        if isinstance(parsed, str) and parsed.strip():
            return parsed.strip()
    except Exception:
        pass
    if raw.startswith('"') and raw.endswith('"'):
        raw = raw[1:-1]
    raw = raw.strip()
    return raw or None



def clear_telegram_approval_buttons(
    ctx: ApprovalPromptContext,
    subject_type: str,
    subject_id: str,
    *,
    get_prompt: Callable[[str], dict[str, Any] | None],
    remove_prompt: Callable[[str], None],
) -> dict[str, Any]:
    if ctx.telegram_dispatch_suppressed_for_harness():
        entry = get_prompt(subject_id)
        if entry:
            remove_prompt(subject_id)
        return {"ok": True, "code": "telegram_dispatch_suppressed", "subjectType": subject_type, "subjectId": subject_id, "promptCleanup": {"ok": True, "code": "telegram_dispatch_suppressed", "channel": "telegram"}}
    entry = get_prompt(subject_id)
    if not entry:
        return {"ok": False, "code": "prompt_not_found", "subjectType": subject_type, "subjectId": subject_id, "promptCleanup": {"ok": False, "code": "prompt_not_found", "channel": "telegram"}}
    if str(entry.get("channel") or "") != "telegram":
        remove_prompt(subject_id)
        return {"ok": True, "code": "non_telegram_removed", "subjectType": subject_type, "subjectId": subject_id, "promptCleanup": {"ok": True, "code": "non_telegram_removed", "channel": str(entry.get("channel") or "")}}
    chat_id = normalize_telegram_target(str(entry.get("to") or ""))
    message_id = str(entry.get("messageId") or "").strip()
    if not chat_id:
        remove_prompt(subject_id)
        return {"ok": False, "code": "missing_target", "subjectType": subject_type, "subjectId": subject_id, "promptCleanup": {"ok": False, "code": "missing_target", "channel": "telegram", "messageId": message_id or None}}
    if not message_id or message_id == "unknown":
        remove_prompt(subject_id)
        return {"ok": False, "code": "missing_message_id", "subjectType": subject_type, "subjectId": subject_id, "promptCleanup": {"ok": False, "code": "missing_message_id", "channel": "telegram", "messageId": message_id or None}}
    try:
        numeric_message_id = int(message_id)
    except Exception:
        remove_prompt(subject_id)
        return {"ok": False, "code": "invalid_message_id", "subjectType": subject_type, "subjectId": subject_id, "promptCleanup": {"ok": False, "code": "invalid_message_id", "channel": "telegram", "messageId": message_id}}
    bot_token = resolve_telegram_bot_token(ctx)
    if not bot_token:
        openclaw_missing = shutil.which("openclaw") is None
        code = "openclaw_missing" if openclaw_missing else "telegram_bot_token_missing"
        return {"ok": False, "code": code, "subjectType": subject_type, "subjectId": subject_id, "promptCleanup": {"ok": False, "code": code, "channel": "telegram", "messageId": message_id}}
    endpoint = f"https://api.telegram.org/bot{urllib.parse.quote(bot_token, safe='')}/editMessageReplyMarkup"
    req_payload = {"chat_id": chat_id, "message_id": numeric_message_id, "reply_markup": {"inline_keyboard": []}}
    request = urllib.request.Request(url=endpoint, data=ctx.json_module.dumps(req_payload).encode("utf-8"), headers={"content-type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            response_body = response.read().decode("utf-8", errors="replace").strip()
        remove_prompt(subject_id)
        return {"ok": True, "code": "buttons_cleared", "subjectType": subject_type, "subjectId": subject_id, "promptCleanup": {"ok": True, "code": "buttons_cleared", "channel": "telegram", "messageId": message_id, "response": response_body[:300] if response_body else None}}
    except urllib.error.HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            body = ""
        body_trimmed = body.strip()
        if "message is not modified" in body_trimmed.lower():
            remove_prompt(subject_id)
            return {"ok": True, "code": "already_cleared", "subjectType": subject_type, "subjectId": subject_id, "promptCleanup": {"ok": True, "code": "already_cleared", "channel": "telegram", "messageId": message_id}}
        return {"ok": False, "code": "telegram_api_failed", "subjectType": subject_type, "subjectId": subject_id, "promptCleanup": {"ok": False, "code": "telegram_api_failed", "channel": "telegram", "messageId": message_id, "error": (body_trimmed or str(exc))[:300]}}
    except Exception as exc:
        return {"ok": False, "code": "telegram_api_failed", "subjectType": subject_type, "subjectId": subject_id, "promptCleanup": {"ok": False, "code": "telegram_api_failed", "channel": "telegram", "messageId": message_id, "error": str(exc)[:300]}}



def wait_for_trade_approval(ctx: ApprovalPromptContext, trade_id: str, chain: str, summary: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        ctx.maybe_send_telegram_approval_prompt(trade_id, chain, summary or {})
    except Exception:
        pass
    wait_timeout_sec = ctx.approval_wait_timeout_sec
    if ctx.last_delivery_is_telegram():
        wait_timeout_sec = min(wait_timeout_sec, ctx.trade_approval_inline_wait_sec())
    deadline_ms = int(ctx.time_module.time() * 1000) + (wait_timeout_sec * 1000)
    last_status: str | None = None
    while int(ctx.time_module.time() * 1000) <= deadline_ms:
        trade = ctx.read_trade_details(trade_id)
        status = str(trade.get("status") or "")
        last_status = status
        if status == "approved":
            try:
                ctx.maybe_delete_telegram_approval_prompt(trade_id)
            except Exception:
                pass
            ctx.remove_approval_prompt(trade_id)
            try:
                ctx.maybe_send_telegram_decision_message(trade_id=trade_id, chain=chain, decision="approved", summary=summary, trade=trade)
            except Exception:
                pass
            ctx.remove_pending_spot_trade_flow(trade_id)
            return trade
        if status == "approval_pending":
            ctx.time_module.sleep(ctx.approval_wait_poll_sec)
            continue
        if status == "rejected":
            try:
                ctx.maybe_delete_telegram_approval_prompt(trade_id)
            except Exception:
                pass
            ctx.remove_approval_prompt(trade_id)
            try:
                ctx.maybe_send_telegram_decision_message(trade_id=trade_id, chain=chain, decision="rejected", summary=summary, trade=trade)
            except Exception:
                pass
            ctx.remove_pending_spot_trade_flow(trade_id)
            raise ctx.wallet_policy_error("approval_rejected", "Trade approval was rejected.", "Review rejection reason and create a new trade if needed.", {"tradeId": trade_id, "chain": chain, "reasonCode": trade.get("reasonCode"), "reasonMessage": trade.get("reasonMessage")})
        if status == "expired":
            try:
                ctx.maybe_delete_telegram_approval_prompt(trade_id)
            except Exception:
                pass
            ctx.remove_approval_prompt(trade_id)
            ctx.remove_pending_spot_trade_flow(trade_id)
            raise ctx.wallet_policy_error("approval_expired", "Trade approval has expired.", "Re-propose trade and request approval again.", {"tradeId": trade_id, "chain": chain})
        try:
            ctx.maybe_delete_telegram_approval_prompt(trade_id)
        except Exception:
            pass
        ctx.remove_approval_prompt(trade_id)
        ctx.remove_pending_spot_trade_flow(trade_id)
        raise ctx.wallet_policy_error("policy_denied", f"Trade is not executable from status '{status}'.", "Poll intents and execute only actionable trades.", {"tradeId": trade_id, "chain": chain, "status": status})
    raise ctx.wallet_policy_error("approval_required", "Trade is waiting for management approval.", "Approve the pending trade in Telegram or web management; execution resumes automatically after approval.", {"tradeId": trade_id, "chain": chain, "lastStatus": last_status})
