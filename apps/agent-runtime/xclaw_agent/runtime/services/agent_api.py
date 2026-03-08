from __future__ import annotations

from typing import Any, Callable


def ack_transfer_decision_inbox(
    api_request: Callable[..., tuple[int, dict[str, Any]]],
    decision_id: str,
    status: str,
    reason_code: str | None = None,
    reason_message: str | None = None,
) -> tuple[int, dict[str, Any]]:
    payload: dict[str, Any] = {
        "schemaVersion": 1,
        "decisionId": decision_id,
        "status": status,
    }
    if reason_code:
        payload["reasonCode"] = reason_code
    if reason_message:
        payload["reasonMessage"] = reason_message
    return api_request("POST", "/agent/transfer-decisions/inbox", payload=payload, include_idempotency=True)


def publish_runtime_signing_readiness(
    api_request: Callable[..., tuple[int, dict[str, Any]]],
    chain: str,
    readiness: dict[str, Any],
) -> tuple[int, dict[str, Any]]:
    payload = {
        "schemaVersion": 1,
        "chainKey": chain,
        "walletSigningReady": bool(readiness.get("walletSigningReady")),
        "walletSigningReasonCode": readiness.get("walletSigningReasonCode"),
        "walletSigningCheckedAt": readiness.get("walletSigningCheckedAt"),
    }
    return api_request("POST", "/agent/runtime-readiness", payload=payload, include_idempotency=True)


def resolve_agent_id_or_fail(resolve_api_key: Callable[[], str], resolve_agent_id: Callable[[str], str], wallet_store_error: type[BaseException]) -> str:
    api_key = resolve_api_key()
    agent_id = resolve_agent_id(api_key)
    if not agent_id:
        raise wallet_store_error("Agent id could not be resolved. Set XCLAW_AGENT_ID or use signed agent token format.")
    return agent_id
