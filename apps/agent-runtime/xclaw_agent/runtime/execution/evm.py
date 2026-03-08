from __future__ import annotations

from typing import Any


def resolve_trade_execution_context(rt: Any, chain: str) -> tuple[str, str, str]:
    store = rt.load_wallet_store()
    wallet_address, private_key_hex = rt._execution_wallet(store, chain)
    adapter_key, adapter_entry = rt.resolve_trade_execution_adapter(chain, "")
    router = str(adapter_entry.get("router") or "").strip()
    if not router:
        raise rt.WalletStoreError(f"chain_config_invalid: trade adapter '{adapter_key}' on chain '{chain}' is missing router.")
    return wallet_address, private_key_hex, adapter_key


def execute_trade_via_router_adapter(rt: Any, **kwargs: Any) -> dict[str, Any]:
    return rt._execute_trade_via_router_adapter(**kwargs)
