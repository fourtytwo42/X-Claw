from __future__ import annotations

import hashlib
import json
import os
import time
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

_STATE_FILE = Path(os.environ.get("XCLAW_AGENT_HOME", str(Path.home() / ".xclaw-agent"))) / "solana_local_liquidity_positions.json"


def _now_ms() -> int:
    return int(time.time() * 1000)


def _as_positive_decimal(value: Any, field: str) -> Decimal:
    try:
        parsed = Decimal(str(value or "").strip())
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(f"{field} must be a positive decimal.") from exc
    if parsed <= 0:
        raise ValueError(f"{field} must be greater than zero.")
    return parsed


def _read_state() -> dict[str, Any]:
    try:
        raw = _STATE_FILE.read_text(encoding="utf-8")
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass
    return {"positions": {}}


def _write_state(state: dict[str, Any]) -> None:
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")


def _make_sig(label: str, payload: str) -> str:
    digest = hashlib.sha256(f"{label}|{payload}|{_now_ms()}".encode("utf-8")).hexdigest()
    return f"solsig_{digest[:48]}"


def quote_add(*, amount_a: str, amount_b: str, slippage_bps: int) -> dict[str, Any]:
    a = _as_positive_decimal(amount_a, "amountA")
    b = _as_positive_decimal(amount_b, "amountB")
    if slippage_bps < 0 or slippage_bps > 5000:
        raise ValueError("slippageBps must be between 0 and 5000.")
    multiplier = Decimal(max(0, 10000 - slippage_bps)) / Decimal(10000)
    return {
        "amountA": str(a.normalize()),
        "amountB": str(b.normalize()),
        "minAmountA": str((a * multiplier).normalize()),
        "minAmountB": str((b * multiplier).normalize()),
        "slippageBps": slippage_bps,
    }


def create_position(
    *,
    chain: str,
    dex: str,
    owner: str,
    token_a: str,
    token_b: str,
    amount_a: str,
    amount_b: str,
    details: dict[str, Any] | None,
) -> dict[str, Any]:
    a = _as_positive_decimal(amount_a, "amountA")
    b = _as_positive_decimal(amount_b, "amountB")
    state = _read_state()
    positions = state.setdefault("positions", {})
    position_id = f"solpos_{hashlib.sha1(f'{chain}:{dex}:{owner}:{token_a}:{token_b}:{_now_ms()}'.encode('utf-8')).hexdigest()[:18]}"
    signature = _make_sig("add", position_id)
    positions[position_id] = {
        "chain": chain,
        "dex": dex,
        "owner": owner,
        "tokenA": token_a,
        "tokenB": token_b,
        "amountA": str(a.normalize()),
        "amountB": str(b.normalize()),
        "createdAtMs": _now_ms(),
        "updatedAtMs": _now_ms(),
        "details": details or {},
    }
    _write_state(state)
    return {"positionId": position_id, "txHash": signature}


def remove_position(
    *,
    chain: str,
    dex: str,
    owner: str,
    position_id: str,
    percent: int,
) -> dict[str, Any]:
    if percent < 1 or percent > 100:
        raise ValueError("percent must be between 1 and 100.")
    state = _read_state()
    positions = state.setdefault("positions", {})
    entry = positions.get(position_id)
    if not isinstance(entry, dict):
        raise ValueError("position_not_found")
    if str(entry.get("chain") or "") != chain or str(entry.get("dex") or "") != dex:
        raise ValueError("position_not_found")
    if str(entry.get("owner") or "").lower() != owner.lower():
        raise ValueError("position_not_owned")

    amount_a = _as_positive_decimal(entry.get("amountA"), "amountA")
    amount_b = _as_positive_decimal(entry.get("amountB"), "amountB")
    ratio = Decimal(percent) / Decimal(100)
    out_a = (amount_a * ratio).normalize()
    out_b = (amount_b * ratio).normalize()
    left_a = (amount_a - out_a).normalize()
    left_b = (amount_b - out_b).normalize()
    if left_a <= 0 or left_b <= 0 or percent == 100:
        positions.pop(position_id, None)
    else:
        entry["amountA"] = str(left_a)
        entry["amountB"] = str(left_b)
        entry["updatedAtMs"] = _now_ms()
    _write_state(state)
    return {
        "positionId": position_id,
        "txHash": _make_sig("remove", position_id),
        "removedAmountA": str(out_a),
        "removedAmountB": str(out_b),
        "remainingAmountA": str(max(left_a, Decimal(0)).normalize()),
        "remainingAmountB": str(max(left_b, Decimal(0)).normalize()),
    }
