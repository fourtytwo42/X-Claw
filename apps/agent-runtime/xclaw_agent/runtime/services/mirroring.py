from __future__ import annotations

import time
from typing import Any, Callable


def mirror_transfer_approval(
    *,
    flow: dict[str, Any],
    require_delivery: bool,
    api_request: Callable[..., tuple[int, dict[str, Any]]],
    utc_now: Callable[[], str],
    watcher_run_id: Callable[[], str],
    token_hex: Callable[[int], str],
    wallet_store_error: type[BaseException],
) -> bool:
    try:
        approval_id = str(flow.get("approvalId") or "").strip()
        chain = str(flow.get("chainKey") or "").strip()
        if not approval_id or not chain:
            return False
        payload = {
            "schemaVersion": 1,
            "approvalId": approval_id,
            "chainKey": chain,
            "status": str(flow.get("status") or "approval_pending"),
            "transferType": str(flow.get("transferType") or "native"),
            "tokenAddress": flow.get("tokenAddress"),
            "tokenSymbol": flow.get("tokenSymbol"),
            "toAddress": flow.get("toAddress"),
            "amountWei": str(flow.get("amountWei") or "0"),
            "txHash": flow.get("txHash"),
            "reasonCode": flow.get("reasonCode"),
            "reasonMessage": flow.get("reasonMessage"),
            "policyBlockedAtCreate": bool(flow.get("policyBlockedAtCreate", False)),
            "policyBlockReasonCode": flow.get("policyBlockReasonCode"),
            "policyBlockReasonMessage": flow.get("policyBlockReasonMessage"),
            "executionMode": flow.get("executionMode"),
            "observedBy": str(flow.get("observedBy") or "agent_watcher"),
            "observationSource": str(flow.get("observationSource") or "local_send_result"),
            "confirmationCount": flow.get("confirmationCount"),
            "observedAt": flow.get("observedAt") or utc_now(),
            "watcherRunId": str(flow.get("watcherRunId") or watcher_run_id()),
            "createdAt": flow.get("createdAt") or utc_now(),
            "updatedAt": flow.get("updatedAt") or utc_now(),
            "decidedAt": flow.get("decidedAt"),
            "terminalAt": flow.get("terminalAt"),
        }

        attempts = 2 if require_delivery else 1
        last_error: str | None = None
        for attempt in range(attempts):
            status_code, body = api_request(
                "POST",
                "/agent/transfer-approvals/mirror",
                payload=payload,
                include_idempotency=True,
                idempotency_key=f"rt-transfer-mirror-{approval_id}-{token_hex(8)}",
            )
            if 200 <= status_code < 300:
                return True
            code = str(body.get("code", "api_error"))
            message = str(body.get("message", f"transfer mirror failed ({status_code})"))
            last_error = f"{code}: {message}"
            if attempt < (attempts - 1):
                time.sleep(0.2)

        if require_delivery:
            raise wallet_store_error(last_error or "transfer approval mirror failed.")
        return False
    except Exception as exc:
        if require_delivery:
            raise wallet_store_error(str(exc) or "transfer approval mirror failed.") from exc
        return False


def mirror_x402_outbound(
    *,
    flow: dict[str, Any],
    api_request: Callable[..., tuple[int, dict[str, Any]]],
    utc_now: Callable[[], str],
    token_hex: Callable[[int], str],
) -> None:
    try:
        approval_id = str(flow.get("approvalId") or "").strip()
        network = str(flow.get("network") or "").strip()
        facilitator = str(flow.get("facilitator") or "").strip()
        url = str(flow.get("url") or "").strip()
        amount_atomic = str(flow.get("amountAtomic") or "").strip()
        if not approval_id or not network or not facilitator or not url or not amount_atomic:
            return

        payment_id = str(flow.get("paymentId") or "").strip() or f"xpm_{token_hex(10)}"
        flow["paymentId"] = payment_id
        payload = {
            "schemaVersion": 1,
            "paymentId": payment_id,
            "approvalId": approval_id,
            "networkKey": network,
            "facilitatorKey": facilitator,
            "status": str(flow.get("status") or "approval_pending"),
            "assetKind": "token" if str(flow.get("assetKind") or "").strip().lower() in {"erc20", "token"} else "native",
            "assetAddress": flow.get("assetAddress"),
            "assetSymbol": flow.get("assetSymbol"),
            "amountAtomic": amount_atomic,
            "url": url,
            "txHash": flow.get("txHash"),
            "reasonCode": flow.get("reasonCode"),
            "reasonMessage": flow.get("reasonMessage"),
            "createdAt": flow.get("createdAt") or utc_now(),
            "updatedAt": flow.get("updatedAt") or utc_now(),
            "terminalAt": flow.get("terminalAt"),
        }
        api_request(
            "POST",
            "/agent/x402/outbound/mirror",
            payload=payload,
            include_idempotency=True,
            idempotency_key=f"rt-x402-mirror-{approval_id}-{token_hex(8)}",
        )

        approval_payload = {
            "schemaVersion": 1,
            "approvalId": approval_id,
            "chainKey": network,
            "approvalSource": "x402",
            "status": str(flow.get("status") or "approval_pending"),
            "transferType": "token" if str(flow.get("assetKind") or "").strip().lower() in {"erc20", "token"} else "native",
            "tokenAddress": flow.get("assetAddress"),
            "tokenSymbol": str(flow.get("assetSymbol") or "X402"),
            "toAddress": str(flow.get("toAddress") or flow.get("recipientAddress") or ("11111111111111111111111111111111" if network.startswith("solana_") else "0x0000000000000000000000000000000000000000")),
            "amountWei": amount_atomic,
            "txHash": flow.get("txHash"),
            "reasonCode": flow.get("reasonCode"),
            "reasonMessage": flow.get("reasonMessage"),
            "policyBlockedAtCreate": False,
            "policyBlockReasonCode": None,
            "policyBlockReasonMessage": None,
            "executionMode": "normal",
            "x402Url": url,
            "x402NetworkKey": network,
            "x402FacilitatorKey": facilitator,
            "x402AssetKind": "token" if str(flow.get("assetKind") or "").strip().lower() in {"erc20", "token"} else "native",
            "x402AssetAddress": flow.get("assetAddress"),
            "x402AmountAtomic": amount_atomic,
            "x402PaymentId": payment_id,
            "createdAt": flow.get("createdAt") or utc_now(),
            "updatedAt": flow.get("updatedAt") or utc_now(),
            "decidedAt": flow.get("decidedAt"),
            "terminalAt": flow.get("terminalAt"),
        }
        api_request(
            "POST",
            "/agent/transfer-approvals/mirror",
            payload=approval_payload,
            include_idempotency=True,
            idempotency_key=f"rt-x402-transfer-mirror-{approval_id}-{token_hex(8)}",
        )
    except Exception:
        pass
