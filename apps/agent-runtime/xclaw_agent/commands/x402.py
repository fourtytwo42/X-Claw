from __future__ import annotations

import argparse
from decimal import Decimal
from typing import Any


def _bind_runtime(rt: Any) -> None:
    globals().update({
        'argparse': argparse,
        'Decimal': Decimal,
        'require_json_flag': rt.require_json_flag,
        'fail': rt.fail,
        'ok': rt.ok,
        'emit': rt.emit,
        'assert_chain_capability': rt.assert_chain_capability,
        'chain_supported_hint': rt.chain_supported_hint,
        'ChainRegistryError': rt.ChainRegistryError,
        'WalletStoreError': rt.WalletStoreError,
        'X402RuntimeError': rt.X402RuntimeError,
        '_api_request': rt._api_request,
        '_api_error_details': rt._api_error_details,
        '_execute_x402_settlement': rt._execute_x402_settlement,
        '_mirror_x402_outbound': rt._mirror_x402_outbound,
        'x402_pay_create_or_execute': rt.x402_pay_create_or_execute,
        'x402_pay_resume': rt.x402_pay_resume,
        'x402_pay_decide': rt.x402_pay_decide,
        'x402_get_policy': rt.x402_get_policy,
        'x402_set_policy': rt.x402_set_policy,
        'x402_list_networks': rt.x402_list_networks,
        'utc_now': rt.utc_now,
    })


def cmd_x402_receive_request_impl(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    network = str(args.network or "").strip()
    facilitator = str(args.facilitator or "").strip()
    amount_atomic = str(args.amount_atomic or "").strip()
    if not network:
        return fail("invalid_input", "network is required.", "Provide --network and retry.", exit_code=2)
    try:
        assert_chain_capability(network, "x402")
    except ChainRegistryError as exc:
        return fail("unsupported_chain_capability", str(exc), chain_supported_hint(), {"network": network}, exit_code=2)
    if not facilitator:
        return fail("invalid_input", "facilitator is required.", "Provide --facilitator and retry.", exit_code=2)
    if not amount_atomic:
        return fail("invalid_input", "amount_atomic is required.", "Provide --amount-atomic and retry.", exit_code=2)
    try:
        amount = Decimal(amount_atomic)
    except Exception:
        return fail("invalid_input", "amount_atomic must be numeric.", "Use values like 0.01 or 1.", exit_code=2)
    if amount <= 0:
        return fail("invalid_input", "amount_atomic must be > 0.", "Use values like 0.01 or 1.", exit_code=2)

    asset_kind_raw = str(args.asset_kind or "native").strip().lower()
    if asset_kind_raw not in {"native", "token", "erc20"}:
        return fail("invalid_input", "asset_kind must be native|token.", "Use --asset-kind native or --asset-kind token.", exit_code=2)
    asset_kind = "token" if asset_kind_raw in {"token", "erc20"} else "native"
    asset_symbol = str(args.asset_symbol or "").strip()
    asset_address = str(args.asset_address or "").strip() or None
    if asset_kind == "token" and not asset_symbol and not asset_address:
        return fail(
            "invalid_input",
            "Token receive requests require asset symbol or asset address.",
            "Set --asset-symbol (USDC|WETH|WKITE|USDT) or --asset-address <token-address>.",
            exit_code=2,
        )

    payload = {
        "schemaVersion": 1,
        "networkKey": network,
        "facilitatorKey": facilitator,
        "assetKind": asset_kind,
        "assetAddress": asset_address,
        "assetSymbol": asset_symbol or None,
        "amountAtomic": format(amount, "f"),
        "resourceDescription": str(args.resource_description or "").strip() or None,
    }
    try:
        status_code, body = _api_request("POST", "/agent/x402/inbound/proposed", payload=payload, include_idempotency=True)
        if status_code < 200 or status_code >= 300:
            return fail(
                str(body.get("code", "api_error")),
                str(body.get("message", f"x402 receive request failed ({status_code})")),
                str(body.get("actionHint", "Verify x402 receive request inputs and retry.")),
                _api_error_details(status_code, body, "/agent/x402/inbound/proposed", network=network),
                exit_code=1,
            )
        return ok(
            "Hosted x402 receive request created.",
            paymentId=body.get("paymentId"),
            paymentUrl=body.get("paymentUrl"),
            network=body.get("networkKey", network),
            facilitator=body.get("facilitatorKey", facilitator),
            assetKind=body.get("assetKind", asset_kind),
            assetAddress=body.get("assetAddress"),
            assetSymbol=body.get("assetSymbol"),
            amountAtomic=body.get("amountAtomic", format(amount, "f")),
            resourceDescription=body.get("resourceDescription"),
            status=body.get("status"),
            timeLimitNotice=body.get("timeLimitNotice"),
            requestSource="hosted",
        )
    except WalletStoreError as exc:
        return fail("x402_receive_request_failed", str(exc), "Verify API env/auth and retry.", {"network": network}, exit_code=1)
    except Exception as exc:
        return fail("x402_receive_request_failed", str(exc), "Inspect hosted x402 receive flow and retry.", {"network": network}, exit_code=1)


def cmd_x402_pay_impl(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    network = str(args.network or "").strip()
    try:
        assert_chain_capability(network, "x402")
    except ChainRegistryError as exc:
        return fail("unsupported_chain_capability", str(exc), chain_supported_hint(), {"network": network}, exit_code=2)
    try:
        payload = x402_pay_create_or_execute(
            url=str(args.url or "").strip(),
            network=network,
            facilitator=str(args.facilitator or "").strip(),
            amount_atomic=str(args.amount_atomic or "").strip(),
            memo=str(args.memo or "").strip() or None,
            settle_payment=_execute_x402_settlement,
        )
        if not bool(payload.get("ok", False)):
            emit(payload)
            return 1
        approval = payload.get("approval")
        if isinstance(approval, dict):
            _mirror_x402_outbound(approval)
        return emit(payload)
    except X402RuntimeError as exc:
        return fail("x402_runtime_error", str(exc), "Verify x402 pay inputs and retry.", exit_code=1)
    except Exception as exc:
        return fail("x402_runtime_error", str(exc), "Inspect runtime x402 pay flow and retry.", exit_code=1)


def cmd_x402_pay_resume_impl(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    approval_id = str(args.approval_id or "").strip()
    if not approval_id:
        return fail("invalid_input", "approval_id is required.", "Provide --approval-id xfr_... and retry.", exit_code=2)
    try:
        payload = x402_pay_resume(approval_id, settle_payment=_execute_x402_settlement)
        if isinstance(payload, dict):
            _mirror_x402_outbound(payload)
        return ok("x402 payment resume processed.", approval=payload)
    except X402RuntimeError as exc:
        return fail("x402_runtime_error", str(exc), "Use a valid pending approved xfr_... id and retry.", exit_code=1)
    except Exception as exc:
        return fail("x402_runtime_error", str(exc), "Inspect runtime x402 pay resume flow and retry.", exit_code=1)


def cmd_x402_pay_decide_impl(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    approval_id = str(args.approval_id or "").strip()
    decision = str(args.decision or "").strip().lower()
    if not approval_id:
        return fail("invalid_input", "approval_id is required.", "Provide --approval-id xfr_... and retry.", exit_code=2)
    if decision not in {"approve", "deny"}:
        return fail("invalid_input", "decision must be approve|deny.", "Use --decision approve or --decision deny.", exit_code=2)
    try:
        payload = x402_pay_decide(
            approval_id,
            decision,
            str(args.reason_message or "").strip() or None,
            settle_payment=_execute_x402_settlement,
        )
        if isinstance(payload, dict):
            _mirror_x402_outbound(payload)
        return ok("x402 payment decision applied.", approval=payload)
    except X402RuntimeError as exc:
        return fail("x402_runtime_error", str(exc), "Use a valid pending xfr_... id and retry.", exit_code=1)
    except Exception as exc:
        return fail("x402_runtime_error", str(exc), "Inspect runtime x402 pay decision flow and retry.", exit_code=1)


def cmd_x402_policy_get_impl(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    network = str(args.network or "").strip()
    if not network:
        return fail("invalid_input", "network is required.", "Provide --network and retry.", exit_code=2)
    try:
        policy = x402_get_policy(network)
        return ok("x402 pay policy loaded.", network=network, x402Policy=policy)
    except Exception as exc:
        return fail("x402_runtime_error", str(exc), "Inspect x402 pay policy state and retry.", exit_code=1)


def cmd_x402_policy_set_impl(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    network = str(args.network or "").strip()
    mode = str(args.mode or "").strip().lower()
    if not network:
        return fail("invalid_input", "network is required.", "Provide --network and retry.", exit_code=2)
    if mode not in {"auto", "per_payment"}:
        return fail("invalid_input", "mode must be auto|per_payment.", "Use --mode auto or --mode per_payment.", exit_code=2)
    allowed_hosts: list[str] = []
    for host in list(args.allowed_host or []):
        if not isinstance(host, str):
            continue
        normalized = host.strip().lower()
        if normalized:
            allowed_hosts.append(normalized)
    payload = {
        "payApprovalMode": mode,
        "maxAmountAtomic": str(args.max_amount_atomic).strip() if args.max_amount_atomic is not None else None,
        "allowedHosts": allowed_hosts,
        "updatedAt": utc_now(),
    }
    try:
        policy = x402_set_policy(network, payload)
        return ok("x402 pay policy saved.", network=network, x402Policy=policy)
    except Exception as exc:
        return fail("x402_runtime_error", str(exc), "Inspect x402 pay policy input and retry.", exit_code=1)


def cmd_x402_networks_impl(args: argparse.Namespace) -> int:
    chk = require_json_flag(args)
    if chk is not None:
        return chk
    try:
        payload = x402_list_networks()
        return ok("x402 networks loaded.", x402Networks=payload.get("networks"), defaultNetwork=payload.get("defaultNetwork"))
    except Exception as exc:
        return fail("x402_runtime_error", str(exc), "Inspect config/x402/networks.json and retry.", exit_code=1)


def cmd_x402_receive_request(rt: Any, args: argparse.Namespace) -> int:
    _bind_runtime(rt)
    return cmd_x402_receive_request_impl(args)


def cmd_x402_pay(rt: Any, args: argparse.Namespace) -> int:
    _bind_runtime(rt)
    return cmd_x402_pay_impl(args)


def cmd_x402_pay_resume(rt: Any, args: argparse.Namespace) -> int:
    _bind_runtime(rt)
    return cmd_x402_pay_resume_impl(args)


def cmd_x402_pay_decide(rt: Any, args: argparse.Namespace) -> int:
    _bind_runtime(rt)
    return cmd_x402_pay_decide_impl(args)


def cmd_x402_policy_get(rt: Any, args: argparse.Namespace) -> int:
    _bind_runtime(rt)
    return cmd_x402_policy_get_impl(args)


def cmd_x402_policy_set(rt: Any, args: argparse.Namespace) -> int:
    _bind_runtime(rt)
    return cmd_x402_policy_set_impl(args)


def cmd_x402_networks(rt: Any, args: argparse.Namespace) -> int:
    _bind_runtime(rt)
    return cmd_x402_networks_impl(args)
