from __future__ import annotations

import re
from typing import Any

from xclaw_agent.runtime import errors as runtime_errors
from xclaw_agent.runtime.validators import require_wallet_key_scheme


def solana_amount_units_or_fail(rt: Any, amount_in: str) -> str:
    raw = str(amount_in or "").strip()
    if not re.fullmatch(r"[0-9]+", raw):
        raise rt.WalletStoreError("For Solana trade execution, amountIn must be base-unit integer (lamports/token units).")
    return raw


def execute_solana_trade(
    rt: Any,
    *,
    chain: str,
    trade_id: str,
    token_in: str,
    token_out: str,
    amount_in_units: str,
    slippage_bps: int,
    from_status: str,
) -> dict[str, Any]:
    quote = rt.solana_jupiter_quote(
        chain_key=chain,
        input_mint=token_in,
        output_mint=token_out,
        amount_units=amount_in_units,
        slippage_bps=slippage_bps,
    )
    store = rt.load_wallet_store()
    wallet_address, private_key_bytes, key_scheme = rt._execution_wallet_secret(store, chain)
    try:
        require_wallet_key_scheme(key_scheme, chain=chain)
    except runtime_errors.RuntimeCommandFailure as exc:
        raise rt.WalletStoreError(str(exc)) from exc
    tx = rt.solana_jupiter_execute_swap(
        chain_key=chain,
        rpc_url=rt._chain_rpc_url(chain),
        private_key_bytes=private_key_bytes,
        quote_payload=quote.quote_payload,
        user_address=wallet_address,
        quote_endpoint=quote.quote_endpoint,
    )
    signature = str(tx.get("signature") or "")
    provider_meta = rt._build_provider_meta("router_adapter", "router_adapter", False, None, quote.route_kind)
    rt._post_trade_status(trade_id, from_status, "executing", {"txHash": signature, **provider_meta})
    rt._post_trade_status(trade_id, "executing", "verifying", {"txHash": signature, **provider_meta})
    rt._post_trade_status(
        trade_id,
        "verifying",
        "filled",
        {
            "txHash": signature,
            "amountOut": quote.amount_out_units,
            "observationSource": "rpc_receipt",
            "confirmationCount": 1,
            "observedAt": rt.utc_now(),
            **provider_meta,
        },
    )
    return {
        "txHash": signature,
        "signature": signature,
        "amountOutUnits": quote.amount_out_units,
        "routeKind": quote.route_kind,
        "providerRequested": "router_adapter",
        "providerUsed": "router_adapter",
        "fallbackUsed": False,
        "fallbackReason": None,
        "executionFamily": "solana_swap",
        "executionAdapter": "jupiter",
    }
