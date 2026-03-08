from __future__ import annotations

import argparse
from decimal import Decimal

from xclaw_agent.runtime.adapters.x402 import X402RuntimeAdapter


def cmd_x402_receive_request_impl(rt: X402RuntimeAdapter, args: argparse.Namespace) -> int:
    chk = rt.require_json_flag(args)
    if chk is not None:
        return chk
    network = str(args.network or "").strip()
    facilitator = str(args.facilitator or "").strip()
    amount_atomic = str(args.amount_atomic or "").strip()
    if not network:
        return rt.fail("invalid_input", "network is required.", "Provide --network and retry.", exit_code=2)
    try:
        rt.assert_chain_capability(network, "x402")
    except rt.ChainRegistryError as exc:
        return rt.fail("unsupported_chain_capability", str(exc), rt.chain_supported_hint(), {"network": network}, exit_code=2)
    if not facilitator:
        return rt.fail("invalid_input", "facilitator is required.", "Provide --facilitator and retry.", exit_code=2)
    if not amount_atomic:
        return rt.fail("invalid_input", "amount_atomic is required.", "Provide --amount-atomic and retry.", exit_code=2)
    try:
        amount = Decimal(amount_atomic)
    except Exception:
        return rt.fail("invalid_input", "amount_atomic must be numeric.", "Use values like 0.01 or 1.", exit_code=2)
    if amount <= 0:
        return rt.fail("invalid_input", "amount_atomic must be > 0.", "Use values like 0.01 or 1.", exit_code=2)

    asset_kind_raw = str(args.asset_kind or "native").strip().lower()
    if asset_kind_raw not in {"native", "token", "erc20"}:
        return rt.fail("invalid_input", "asset_kind must be native|token.", "Use --asset-kind native or --asset-kind token.", exit_code=2)
    asset_kind = "token" if asset_kind_raw in {"token", "erc20"} else "native"
    asset_symbol = str(args.asset_symbol or "").strip()
    asset_address = str(args.asset_address or "").strip() or None
    if asset_kind == "token" and not asset_symbol and not asset_address:
        return rt.fail(
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
        status_code, body = rt._api_request("POST", "/agent/x402/inbound/proposed", payload=payload, include_idempotency=True)
        if status_code < 200 or status_code >= 300:
            return rt.fail(
                str(body.get("code", "api_error")),
                str(body.get("message", f"x402 receive request failed ({status_code})")),
                str(body.get("actionHint", "Verify x402 receive request inputs and retry.")),
                rt._api_error_details(status_code, body, "/agent/x402/inbound/proposed", network=network),
                exit_code=1,
            )
        return rt.ok(
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
    except rt.WalletStoreError as exc:
        return rt.fail("x402_receive_request_failed", str(exc), "Verify API env/auth and retry.", {"network": network}, exit_code=1)
    except Exception as exc:
        return rt.fail("x402_receive_request_failed", str(exc), "Inspect hosted x402 receive flow and retry.", {"network": network}, exit_code=1)


def cmd_x402_pay_impl(rt: X402RuntimeAdapter, args: argparse.Namespace) -> int:
    chk = rt.require_json_flag(args)
    if chk is not None:
        return chk
    network = str(args.network or "").strip()
    try:
        rt.assert_chain_capability(network, "x402")
    except rt.ChainRegistryError as exc:
        return rt.fail("unsupported_chain_capability", str(exc), rt.chain_supported_hint(), {"network": network}, exit_code=2)
    try:
        payload = rt.x402_pay_create_or_execute(
            url=str(args.url or "").strip(),
            network=network,
            facilitator=str(args.facilitator or "").strip(),
            amount_atomic=str(args.amount_atomic or "").strip(),
            memo=str(args.memo or "").strip() or None,
            settle_payment=rt._execute_x402_settlement,
        )
        if not bool(payload.get("ok", False)):
            rt.emit(payload)
            return 1
        approval = payload.get("approval")
        if isinstance(approval, dict):
            rt._mirror_x402_outbound(approval)
        return rt.emit(payload)
    except rt.X402RuntimeError as exc:
        return rt.fail("x402_runtime_error", str(exc), "Verify x402 pay inputs and retry.", exit_code=1)
    except Exception as exc:
        return rt.fail("x402_runtime_error", str(exc), "Inspect runtime x402 pay flow and retry.", exit_code=1)


def cmd_x402_pay_resume_impl(rt: X402RuntimeAdapter, args: argparse.Namespace) -> int:
    chk = rt.require_json_flag(args)
    if chk is not None:
        return chk
    approval_id = str(args.approval_id or "").strip()
    if not approval_id:
        return rt.fail("invalid_input", "approval_id is required.", "Provide --approval-id xfr_... and retry.", exit_code=2)
    try:
        payload = rt.x402_pay_resume(approval_id, settle_payment=rt._execute_x402_settlement)
        if isinstance(payload, dict):
            rt._mirror_x402_outbound(payload)
        return rt.ok("x402 payment resume processed.", approval=payload)
    except rt.X402RuntimeError as exc:
        return rt.fail("x402_runtime_error", str(exc), "Use a valid pending approved xfr_... id and retry.", exit_code=1)
    except Exception as exc:
        return rt.fail("x402_runtime_error", str(exc), "Inspect runtime x402 pay resume flow and retry.", exit_code=1)


def cmd_x402_pay_decide_impl(rt: X402RuntimeAdapter, args: argparse.Namespace) -> int:
    chk = rt.require_json_flag(args)
    if chk is not None:
        return chk
    approval_id = str(args.approval_id or "").strip()
    decision = str(args.decision or "").strip().lower()
    if not approval_id:
        return rt.fail("invalid_input", "approval_id is required.", "Provide --approval-id xfr_... and retry.", exit_code=2)
    if decision not in {"approve", "deny"}:
        return rt.fail("invalid_input", "decision must be approve|deny.", "Use --decision approve or --decision deny.", exit_code=2)
    try:
        payload = rt.x402_pay_decide(
            approval_id,
            decision,
            str(args.reason_message or "").strip() or None,
            settle_payment=rt._execute_x402_settlement,
        )
        if isinstance(payload, dict):
            rt._mirror_x402_outbound(payload)
        return rt.ok("x402 payment decision applied.", approval=payload)
    except rt.X402RuntimeError as exc:
        return rt.fail("x402_runtime_error", str(exc), "Use a valid pending xfr_... id and retry.", exit_code=1)
    except Exception as exc:
        return rt.fail("x402_runtime_error", str(exc), "Inspect runtime x402 pay decision flow and retry.", exit_code=1)


def cmd_x402_policy_get_impl(rt: X402RuntimeAdapter, args: argparse.Namespace) -> int:
    chk = rt.require_json_flag(args)
    if chk is not None:
        return chk
    network = str(args.network or "").strip()
    if not network:
        return rt.fail("invalid_input", "network is required.", "Provide --network and retry.", exit_code=2)
    try:
        policy = rt.x402_get_policy(network)
        return rt.ok("x402 pay policy loaded.", network=network, x402Policy=policy)
    except Exception as exc:
        return rt.fail("x402_runtime_error", str(exc), "Inspect x402 pay policy state and retry.", exit_code=1)


def cmd_x402_policy_set_impl(rt: X402RuntimeAdapter, args: argparse.Namespace) -> int:
    chk = rt.require_json_flag(args)
    if chk is not None:
        return chk
    network = str(args.network or "").strip()
    mode = str(args.mode or "").strip().lower()
    if not network:
        return rt.fail("invalid_input", "network is required.", "Provide --network and retry.", exit_code=2)
    if mode not in {"auto", "per_payment"}:
        return rt.fail("invalid_input", "mode must be auto|per_payment.", "Use --mode auto or --mode per_payment.", exit_code=2)
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
        "updatedAt": rt.utc_now(),
    }
    try:
        policy = rt.x402_set_policy(network, payload)
        return rt.ok("x402 pay policy saved.", network=network, x402Policy=policy)
    except Exception as exc:
        return rt.fail("x402_runtime_error", str(exc), "Inspect x402 pay policy input and retry.", exit_code=1)


def cmd_x402_networks_impl(rt: X402RuntimeAdapter, args: argparse.Namespace) -> int:
    chk = rt.require_json_flag(args)
    if chk is not None:
        return chk
    try:
        payload = rt.x402_list_networks()
        return rt.ok("x402 networks loaded.", x402Networks=payload.get("networks"), defaultNetwork=payload.get("defaultNetwork"))
    except Exception as exc:
        return rt.fail("x402_runtime_error", str(exc), "Inspect config/x402/networks.json and retry.", exit_code=1)


def cmd_x402_receive_request(rt: X402RuntimeAdapter, args: argparse.Namespace) -> int:
    return cmd_x402_receive_request_impl(rt, args)


def cmd_x402_pay(rt: X402RuntimeAdapter, args: argparse.Namespace) -> int:
    return cmd_x402_pay_impl(rt, args)


def cmd_x402_pay_resume(rt: X402RuntimeAdapter, args: argparse.Namespace) -> int:
    return cmd_x402_pay_resume_impl(rt, args)


def cmd_x402_pay_decide(rt: X402RuntimeAdapter, args: argparse.Namespace) -> int:
    return cmd_x402_pay_decide_impl(rt, args)


def cmd_x402_policy_get(rt: X402RuntimeAdapter, args: argparse.Namespace) -> int:
    return cmd_x402_policy_get_impl(rt, args)


def cmd_x402_policy_set(rt: X402RuntimeAdapter, args: argparse.Namespace) -> int:
    return cmd_x402_policy_set_impl(rt, args)


def cmd_x402_networks(rt: X402RuntimeAdapter, args: argparse.Namespace) -> int:
    return cmd_x402_networks_impl(rt, args)
