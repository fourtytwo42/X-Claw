from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable


@dataclass(frozen=True)
class ReportingServiceContext:
    api_request: Callable[..., tuple[int, dict[str, Any]]]
    wallet_store_error: type[BaseException]
    parse_decision_at: Callable[[str | None], str]
    utc_now: Callable[[], str]
    watcher_run_id: Callable[[], str]
    canonical_event_for_trade_status: Callable[[str], str]


def _response_error(body: dict[str, Any] | Any, fallback_message: str) -> str:
    if isinstance(body, dict):
        code = str(body.get("code", "api_error"))
        message = str(body.get("message", fallback_message))
        return f"{code}: {message}"
    return f"api_error: {fallback_message}"


def post_trade_status(
    ctx: ReportingServiceContext,
    *,
    trade_id: str,
    from_status: str,
    to_status: str,
    extra: dict[str, Any] | None = None,
    idempotency_key: str | None = None,
    decision_at: str | None = None,
) -> None:
    payload: dict[str, Any] = {
        "tradeId": trade_id,
        "fromStatus": from_status,
        "toStatus": to_status,
        "at": ctx.parse_decision_at(decision_at),
        "observedBy": "agent_watcher",
        "observationSource": "local_send_result",
        "observedAt": ctx.utc_now(),
        "watcherRunId": ctx.watcher_run_id(),
    }
    if extra:
        payload.update(extra)
    status_code, body = ctx.api_request(
        "POST",
        f"/trades/{trade_id}/status",
        payload=payload,
        include_idempotency=True,
        idempotency_key=idempotency_key,
    )
    if status_code < 200 or status_code >= 300:
        raise ctx.wallet_store_error(_response_error(body, f"trade status update failed ({status_code})"))


def post_liquidity_status(
    ctx: ReportingServiceContext,
    *,
    liquidity_intent_id: str,
    to_status: str,
    extra: dict[str, Any] | None = None,
) -> None:
    payload: dict[str, Any] = {"status": to_status}
    if extra:
        for key, value in extra.items():
            if value is None:
                continue
            payload[key] = value
    status_code, body = ctx.api_request(
        "POST",
        f"/liquidity/{liquidity_intent_id}/status",
        payload=payload,
        include_idempotency=True,
    )
    if status_code < 200 or status_code >= 300:
        raise ctx.wallet_store_error(_response_error(body, f"liquidity status update failed ({status_code})"))


def read_trade_details(ctx: ReportingServiceContext, trade_id: str) -> dict[str, Any]:
    status_code, body = ctx.api_request("GET", f"/trades/{trade_id}")
    if status_code < 200 or status_code >= 300:
        raise ctx.wallet_store_error(_response_error(body, f"trade read failed ({status_code})"))
    trade = body.get("trade") if isinstance(body, dict) else None
    if not isinstance(trade, dict):
        raise ctx.wallet_store_error("Trade details response missing trade object.")
    return trade


def post_limit_order_status(
    *,
    order_id: str,
    payload: dict[str, Any],
    queue_on_failure: bool,
    api_request: Callable[..., tuple[int, dict[str, Any]]],
    queue_limit_order_action: Callable[[str, str, dict[str, Any]], None],
    wallet_store_error: type[BaseException],
) -> None:
    try:
        status_code, body = api_request("POST", f"/limit-orders/{order_id}/status", payload=payload, include_idempotency=True)
        if status_code < 200 or status_code >= 300:
            raise wallet_store_error(_response_error(body, f"limit-order status update failed ({status_code})"))
    except Exception:
        if queue_on_failure:
            queue_limit_order_action("POST", f"/limit-orders/{order_id}/status", payload)
            return
        raise


def send_trade_execution_report(
    *,
    trade_id: str,
    read_trade_details: Callable[[str], dict[str, Any]],
    canonical_event_for_trade_status: Callable[[str], str],
    api_request: Callable[..., tuple[int, dict[str, Any]]],
    wallet_store_error: type[BaseException],
) -> dict[str, Any]:
    trade = read_trade_details(trade_id)
    event_type = canonical_event_for_trade_status(str(trade.get("status")))
    payload = {
        "schemaVersion": 1,
        "agentId": trade.get("agentId"),
        "tradeId": trade_id,
        "eventType": event_type,
        "payload": {
            "status": trade.get("status"),
            "mode": trade.get("mode"),
            "chainKey": trade.get("chainKey"),
            "reasonCode": trade.get("reasonCode"),
            "reportedBy": "xclaw-agent-runtime",
        },
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    status_code, body = api_request("POST", "/events", payload=payload, include_idempotency=True)
    if status_code < 200 or status_code >= 300:
        raise wallet_store_error(_response_error(body, f"report send failed ({status_code})"))
    return {"ok": True, "eventType": event_type}


def send_trade_execution_report_via_context(
    ctx: ReportingServiceContext,
    *,
    trade_id: str,
) -> dict[str, Any]:
    return send_trade_execution_report(
        trade_id=trade_id,
        read_trade_details=lambda trade_ref: read_trade_details(ctx, trade_ref),
        canonical_event_for_trade_status=ctx.canonical_event_for_trade_status,
        api_request=ctx.api_request,
        wallet_store_error=ctx.wallet_store_error,
    )
