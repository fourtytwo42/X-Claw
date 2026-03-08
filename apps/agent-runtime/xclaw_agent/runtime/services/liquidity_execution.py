from __future__ import annotations

import argparse
import io
from contextlib import redirect_stdout
from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class LiquidityExecutionServiceContext:
    argparse_module: Any
    json_module: Any
    wallet_store_error: type[BaseException]
    build_liquidity_adapter_for_request: Callable[..., Any]
    intent_details_dict: Callable[[dict[str, Any]], dict[str, Any]]
    v3_details_dict: Callable[[dict[str, Any]], dict[str, Any]]
    cmd_liquidity_increase: Callable[[argparse.Namespace], int]
    cmd_liquidity_claim_fees: Callable[[argparse.Namespace], int]
    cmd_liquidity_claim_rewards: Callable[[argparse.Namespace], int]
    cmd_liquidity_migrate: Callable[[argparse.Namespace], int]


def invoke_liquidity_command_payload(
    ctx: LiquidityExecutionServiceContext,
    command: Callable[[argparse.Namespace], int],
    args: argparse.Namespace,
) -> dict[str, Any]:
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = command(args)
    raw = buf.getvalue().strip()
    payload: dict[str, Any] = {}
    if raw:
        try:
            decoded = ctx.json_module.loads(raw)
            if isinstance(decoded, dict):
                payload = decoded
        except Exception:
            payload = {"ok": False, "code": "liquidity_execute_parse_failed", "message": raw[:400]}
    if code != 0:
        error_code = str(payload.get("code") or "liquidity_execution_failed")
        error_message = str(payload.get("message") or "Advanced liquidity command failed.")
        raise ctx.wallet_store_error(f"{error_code}: {error_message}")
    return payload


def execute_liquidity_advanced_intent(
    ctx: LiquidityExecutionServiceContext,
    intent: dict[str, Any],
    chain: str,
    action: str,
) -> tuple[dict[str, Any], str]:
    dex = str(intent.get("dex") or "").strip().lower()
    adapter = ctx.build_liquidity_adapter_for_request(chain=chain, dex=dex, position_type="v3")
    details = ctx.intent_details_dict(intent)
    v3_details = ctx.v3_details_dict(details)
    position_id = str(intent.get("positionId") or intent.get("positionRef") or "").strip()
    slippage_bps = int(intent.get("slippageBps") or details.get("slippageBps") or 100)

    if action == "increase":
        args = ctx.argparse_module.Namespace(
            chain=chain,
            dex=dex,
            position_id=position_id,
            token_a=str(intent.get("tokenA") or v3_details.get("tokenA") or ""),
            token_b=str(intent.get("tokenB") or v3_details.get("tokenB") or ""),
            amount_a=str(intent.get("amountA") or v3_details.get("amountA") or ""),
            amount_b=str(intent.get("amountB") or v3_details.get("amountB") or ""),
            slippage_bps=slippage_bps,
            json=True,
        )
        payload = invoke_liquidity_command_payload(ctx, ctx.cmd_liquidity_increase, args)
        return payload, adapter.protocol_family

    if action in {"claim_fees", "claim-fees"}:
        args = ctx.argparse_module.Namespace(
            chain=chain,
            dex=dex,
            position_id=position_id,
            collect_as_weth=bool(details.get("collectAsWeth") or False),
            json=True,
        )
        payload = invoke_liquidity_command_payload(ctx, ctx.cmd_liquidity_claim_fees, args)
        return payload, adapter.protocol_family

    if action in {"claim_rewards", "claim-rewards"}:
        args = ctx.argparse_module.Namespace(
            chain=chain,
            dex=dex,
            position_id=position_id,
            reward_token=str(details.get("rewardToken") or ""),
            request_json=ctx.json_module.dumps(details.get("request") or {}) if isinstance(details.get("request"), dict) else None,
            json=True,
        )
        payload = invoke_liquidity_command_payload(ctx, ctx.cmd_liquidity_claim_rewards, args)
        return payload, adapter.protocol_family

    if action == "migrate":
        args = ctx.argparse_module.Namespace(
            chain=chain,
            dex=dex,
            position_id=position_id,
            from_protocol=str(details.get("fromProtocol") or "V3"),
            to_protocol=str(details.get("toProtocol") or "V3"),
            slippage_bps=slippage_bps,
            request_json=ctx.json_module.dumps(details.get("request") or {}) if isinstance(details.get("request"), dict) else None,
            json=True,
        )
        payload = invoke_liquidity_command_payload(ctx, ctx.cmd_liquidity_migrate, args)
        return payload, adapter.protocol_family

    raise ctx.wallet_store_error(f"Unsupported liquidity action '{action}'.")
