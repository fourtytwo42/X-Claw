from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Callable


@dataclass(frozen=True)
class TradeCapsServiceContext:
    load_state: Callable[[], dict[str, Any]]
    save_state: Callable[[dict[str, Any]], None]
    utc_now: Callable[[], str]
    decimal_text: Callable[[Decimal], str]
    to_non_negative_decimal: Callable[[Any], Decimal]
    to_non_negative_int: Callable[[Any], int]
    load_trade_usage_outbox: Callable[[], list[dict[str, Any]]]
    save_trade_usage_outbox: Callable[[list[dict[str, Any]]], None]
    api_request: Callable[..., tuple[int, dict[str, Any]]]
    resolve_api_key: Callable[[], str]
    resolve_agent_id: Callable[[str], str | None]
    token_hex: Callable[[int], str]
    wallet_store_error: type[BaseException]


def load_trade_cap_ledger(ctx: TradeCapsServiceContext, state: dict[str, Any], chain: str, day_key: str) -> tuple[Decimal, int]:
    ledger = state.get("tradeCapLedger")
    if not isinstance(ledger, dict):
        return Decimal("0"), 0
    chain_ledger = ledger.get(chain)
    if not isinstance(chain_ledger, dict):
        return Decimal("0"), 0
    row = chain_ledger.get(day_key)
    if not isinstance(row, dict):
        return Decimal("0"), 0
    spend = ctx.to_non_negative_decimal(row.get("dailySpendUsd", "0"))
    filled = ctx.to_non_negative_int(row.get("dailyFilledTrades", 0))
    return spend, filled


def record_trade_cap_ledger(
    ctx: TradeCapsServiceContext,
    state: dict[str, Any],
    chain: str,
    day_key: str,
    spend_usd: Decimal,
    filled_trades: int,
) -> None:
    ledger = state.setdefault("tradeCapLedger", {})
    if not isinstance(ledger, dict):
        raise ctx.wallet_store_error("State field 'tradeCapLedger' must be an object.")
    chain_ledger = ledger.setdefault(chain, {})
    if not isinstance(chain_ledger, dict):
        raise ctx.wallet_store_error(f"State trade cap ledger for chain '{chain}' must be an object.")
    chain_ledger[day_key] = {
        "dailySpendUsd": ctx.decimal_text(spend_usd),
        "dailyFilledTrades": int(max(0, filled_trades)),
        "updatedAt": ctx.utc_now(),
    }
    ctx.save_state(state)


def queue_trade_usage_report(ctx: TradeCapsServiceContext, item: dict[str, Any]) -> None:
    outbox = ctx.load_trade_usage_outbox()
    outbox.append(item)
    ctx.save_trade_usage_outbox(outbox)


def replay_trade_usage_outbox(ctx: TradeCapsServiceContext) -> tuple[int, int]:
    queued = ctx.load_trade_usage_outbox()
    if not queued:
        return 0, 0
    remaining: list[dict[str, Any]] = []
    replayed = 0
    for entry in queued:
        payload = entry.get("payload")
        idempotency_key = entry.get("idempotencyKey")
        if not isinstance(payload, dict) or not isinstance(idempotency_key, str) or not idempotency_key.strip():
            continue
        status_code, _body = ctx.api_request(
            "POST",
            "/agent/trade-usage",
            payload=payload,
            include_idempotency=True,
            idempotency_key=idempotency_key,
        )
        if status_code < 200 or status_code >= 300:
            remaining.append(entry)
            continue
        replayed += 1
    ctx.save_trade_usage_outbox(remaining)
    return replayed, len(remaining)


def post_trade_usage(ctx: TradeCapsServiceContext, chain: str, utc_day: str, spend_usd_delta: Decimal, filled_trades_delta: int) -> None:
    if spend_usd_delta < 0:
        spend_usd_delta = Decimal("0")
    if filled_trades_delta < 0:
        filled_trades_delta = 0
    if spend_usd_delta == 0 and filled_trades_delta == 0:
        return

    api_key = ctx.resolve_api_key()
    agent_id = ctx.resolve_agent_id(api_key)
    if not agent_id:
        raise ctx.wallet_store_error("Agent id could not be resolved for trade-usage reporting.")

    idempotency_key = f"rt-usage-{chain}-{utc_day}-{ctx.token_hex(8)}"
    payload = {
        "schemaVersion": 1,
        "agentId": agent_id,
        "chainKey": chain,
        "utcDay": utc_day,
        "spendUsdDelta": ctx.decimal_text(spend_usd_delta),
        "filledTradesDelta": int(filled_trades_delta),
    }

    status_code, body = ctx.api_request(
        "POST",
        "/agent/trade-usage",
        payload=payload,
        include_idempotency=True,
        idempotency_key=idempotency_key,
    )
    if status_code < 200 or status_code >= 300:
        queue_trade_usage_report(ctx, {"idempotencyKey": idempotency_key, "payload": payload, "queuedAt": ctx.utc_now()})
        code = str(body.get("code", "api_error"))
        message = str(body.get("message", f"trade usage report failed ({status_code})"))
        raise ctx.wallet_store_error(f"{code}: {message}")
