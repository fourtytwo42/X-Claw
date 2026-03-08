from __future__ import annotations

import io
import json
import re
from contextlib import redirect_stdout
from typing import Any, Callable

from xclaw_agent.runtime import errors as runtime_errors

_LIMIT_ORDER_REASON_CODES = {
    "unsupported_chain_capability",
    "invalid_input",
    "rpc_unavailable",
    "transaction_failed",
    "slippage_exceeded",
    "unsupported_execution_adapter",
    "chain_config_invalid",
}


def run_json_command(func: Callable[[Any], int], args: Any, *, fallback_payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = func(args)
    raw = buf.getvalue().strip()
    payload: dict[str, Any] = dict(fallback_payload)
    payload.setdefault("ok", code == 0)
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                payload = parsed
        except Exception:
            payload = {**payload, "ok": False, "code": "resume_parse_failed", "message": raw[:400]}
    return code, payload


def emit_prompt_cleanup_result(rt: Any, *, subject_type: str, subject_id: str, success_message: str, failure_message: str, failure_hint: str, extra_details: dict[str, Any] | None = None) -> int:
    result = rt._clear_telegram_approval_buttons(subject_type, subject_id)
    payload = {
        "subjectType": subject_type,
        "subjectId": subject_id,
        "promptCleanup": result.get("promptCleanup"),
    }
    if extra_details:
        payload.update(extra_details)
    if bool(result.get("ok")):
        return rt.ok(success_message, **payload, actionHint="No additional action required.")
    return rt.fail(
        str(result.get("code") or "approval_prompt_cleanup_failed"),
        failure_message,
        failure_hint,
        payload,
        exit_code=1,
    )


def limit_order_failure_details(exc: Exception) -> dict[str, str]:
    reason_code = "rpc_unavailable"
    message_text = str(exc)
    code_match = re.match(r"^([a-z0-9_]+):\s*", message_text.strip().lower())
    if code_match:
        candidate = code_match.group(1)
        if candidate in _LIMIT_ORDER_REASON_CODES:
            reason_code = candidate
    return {"reasonCode": reason_code, "reasonMessage": message_text}


def ensure_real_mode(mode: str, *, chain: str, details: dict[str, Any] | None = None) -> None:
    if str(mode or "").strip().lower() != "real":
        raise runtime_errors.unsupported_mode(
            "Mock mode is deprecated for limit orders.",
            "Use network mode (`real`) on a configured chain.",
            {"mode": mode, "supportedMode": "real", "chain": chain, **(details or {})},
        )
