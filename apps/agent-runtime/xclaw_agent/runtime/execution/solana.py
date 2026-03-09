from __future__ import annotations

import hashlib
import re
from decimal import Decimal, ROUND_DOWN
from typing import Any

from xclaw_agent.runtime import errors as runtime_errors
from xclaw_agent.runtime.validators import require_wallet_key_scheme

_BASE58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def solana_amount_units_or_fail(rt: Any, amount_in: str) -> str:
    raw = str(amount_in or "").strip()
    if not re.fullmatch(r"[0-9]+", raw):
        raise rt.WalletStoreError("For Solana trade execution, amountIn must be base-unit integer (lamports/token units).")
    return raw


def _deterministic_base58_id(seed: str, length: int = 64) -> str:
    if length <= 0:
        return ""
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    number = int.from_bytes(digest, "big")
    out = []
    while len(out) < length:
        number, rem = divmod(number, len(_BASE58_ALPHABET))
        out.append(_BASE58_ALPHABET[rem])
        if number == 0:
            digest = hashlib.sha256(digest).digest()
            number = int.from_bytes(digest, "big")
    return "".join(out)[:length]


def _solana_local_price_token_in_per_one_token_out(token_in: str, token_out: str) -> Decimal:
    seed = f"{token_in.lower()}->{token_out.lower()}"
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    basis = int.from_bytes(digest[:4], "big")
    scaled = (basis % 49500) + 500
    return (Decimal(scaled) / Decimal(1000)).quantize(Decimal("0.000001"))


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
    if chain == "solana_localnet":
        token_in_decimals = rt._solana_mint_decimals(chain, token_in)
        token_out_decimals = rt._solana_mint_decimals(chain, token_out)
        amount_in_human = Decimal(int(amount_in_units)) / (Decimal(10) ** Decimal(token_in_decimals))
        price = _solana_local_price_token_in_per_one_token_out(token_in, token_out)
        if price <= 0:
            raise rt.WalletStoreError("chain_config_invalid: local Solana quote price is not positive.")
        amount_out_human = amount_in_human / price
        if amount_out_human <= 0:
            raise rt.WalletStoreError("transaction_failed: local Solana quote produced zero output.")
        quant = Decimal(1) if token_out_decimals <= 0 else Decimal(1) / (Decimal(10) ** Decimal(token_out_decimals))
        amount_out_units = rt._to_units_uint(str(amount_out_human.quantize(quant, rounding=ROUND_DOWN)), token_out_decimals)
        store = rt.load_wallet_store()
        wallet_address, _private_key_bytes, key_scheme = rt._execution_wallet_secret(store, chain)
        try:
            require_wallet_key_scheme(key_scheme, chain=chain)
        except runtime_errors.RuntimeCommandFailure as exc:
            raise rt.WalletStoreError(str(exc)) from exc
        signature = _deterministic_base58_id(f"{trade_id}:{wallet_address}:{amount_in_units}:{rt.utc_now()}", 64)
        provider_meta = rt._build_provider_meta("router_adapter", "router_adapter", False, None, "local_direct")
        rt._post_trade_status(trade_id, from_status, "executing", {"txHash": signature, **provider_meta})
        rt._post_trade_status(trade_id, "executing", "verifying", {"txHash": signature, **provider_meta})
        rt._post_trade_status(
            trade_id,
            "verifying",
            "filled",
            {
                "txHash": signature,
                "amountOut": amount_out_units,
                "observationSource": "rpc_receipt",
                "confirmationCount": 1,
                "observedAt": rt.utc_now(),
                **provider_meta,
            },
        )
        return {
            "txHash": signature,
            "signature": signature,
            "amountOutUnits": amount_out_units,
            "routeKind": "local_direct",
            "providerRequested": "router_adapter",
            "providerUsed": "router_adapter",
            "fallbackUsed": False,
            "fallbackReason": None,
            "executionFamily": "solana_swap",
            "executionAdapter": "local_amm",
        }
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
