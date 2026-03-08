from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable


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
            code = str(body.get("code", "api_error"))
            message = str(body.get("message", f"limit-order status update failed ({status_code})"))
            raise wallet_store_error(f"{code}: {message}")
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
        code = str(body.get("code", "api_error"))
        message = str(body.get("message", f"report send failed ({status_code})"))
        raise wallet_store_error(f"{code}: {message}")
    return {"ok": True, "eventType": event_type}
