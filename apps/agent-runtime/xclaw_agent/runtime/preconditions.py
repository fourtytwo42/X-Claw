from __future__ import annotations

from typing import Any

from xclaw_agent.runtime.errors import RuntimeCommandFailure, chain_mismatch


def prepare_transfer_flow(rt: Any, chain: str, amount_wei: int, recipient: str) -> dict[str, Any]:
    rt._enforce_spend_preconditions(chain, amount_wei)
    return rt._evaluate_outbound_transfer_policy(chain, recipient)


def ensure_trade_chain_match(trade: dict[str, Any], *, requested_chain: str, trade_id: str) -> None:
    trade_chain = str(trade.get("chainKey") or "")
    if trade_chain != requested_chain:
        raise chain_mismatch(trade_id, trade_chain, requested_chain)


def ensure_trade_actionable(rt: Any, *, trade_id: str, status: str, retry: dict[str, Any] | None = None) -> None:
    retry_payload = retry if isinstance(retry, dict) else {}
    retry_eligible = bool(retry_payload.get("eligible", False))
    if status not in {"approved", "failed"}:
        raise RuntimeCommandFailure(
            "approval_required",
            f"Trade is not executable from status '{status}'.",
            "Execute only approved trades or failed trades within retry policy.",
            {"tradeId": trade_id, "status": status},
            1,
        )
    if status == "failed" and not retry_eligible:
        raise RuntimeCommandFailure(
            "policy_denied",
            "Retry policy does not allow this failed trade to execute.",
            "Re-propose trade or retry within policy window/limits.",
            {"tradeId": trade_id, "retry": retry_payload, "maxRetries": rt.MAX_TRADE_RETRIES, "retryWindowSec": rt.RETRY_WINDOW_SEC},
            1,
        )
