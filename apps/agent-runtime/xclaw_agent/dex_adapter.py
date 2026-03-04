from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from xclaw_agent.chains import get_chain
from xclaw_agent.trade_adapters.amm_v2 import AmmV2TradeAdapter


class DexAdapterError(Exception):
    pass


class TradeAdapterResolutionError(DexAdapterError):
    pass


@dataclass(frozen=True)
class DexAdapter:
    chain: str
    cast_bin: str
    rpc_url: str
    router_address: str

    def get_amount_out(
        self,
        amount_in_units: str,
        token_in: str,
        token_out: str,
        run_call: callable,
        parse_uint: callable,
    ) -> int:
        proc = run_call(
            [
                self.cast_bin,
                "call",
                "--rpc-url",
                self.rpc_url,
                self.router_address,
                "getAmountsOut(uint256,address[])(uint256[])",
                amount_in_units,
                f"[{token_in},{token_out}]",
            ]
        )
        if int(getattr(proc, "returncode", 1)) != 0:
            stderr = str(getattr(proc, "stderr", "") or "").strip()
            stdout = str(getattr(proc, "stdout", "") or "").strip()
            raise DexAdapterError(stderr or stdout or "cast call getAmountsOut failed.")
        return int(parse_uint(str(getattr(proc, "stdout", "") or "")))

    def quote_token_in_per_one_token_out(
        self,
        token_out_decimals: int,
        token_in_decimals: int,
        token_out: str,
        token_in: str,
        run_call: callable,
        parse_uint: callable,
    ) -> Decimal:
        one_token_out_units = str(10**token_out_decimals)
        amount_out_units = self.get_amount_out(one_token_out_units, token_out, token_in, run_call, parse_uint)
        return Decimal(amount_out_units) / (Decimal(10) ** Decimal(token_in_decimals))


class AmmV2RouterAdapter(DexAdapter):
    pass


class UniswapV2RouterAdapter(AmmV2RouterAdapter):
    pass


class KiteTesseractAdapter(DexAdapter):
    pass


def build_dex_adapter(chain: str, cast_bin: str, rpc_url: str, router_address: str) -> DexAdapter:
    normalized = (chain or "").strip().lower()
    if normalized == "kite_ai_testnet":
        return KiteTesseractAdapter(
            chain=chain,
            cast_bin=cast_bin,
            rpc_url=rpc_url,
            router_address=router_address,
        )
    return UniswapV2RouterAdapter(
        chain=chain,
        cast_bin=cast_bin,
        rpc_url=rpc_url,
        router_address=router_address,
    )


def _trade_execution_adapters(chain: str) -> dict[str, dict[str, Any]]:
    cfg = get_chain(chain, include_disabled=True)
    if not cfg:
        raise TradeAdapterResolutionError(f"Unsupported chain '{chain}' for trade adapter selection.")
    execution = cfg.get("execution")
    trade_cfg = execution.get("trade") if isinstance(execution, dict) else {}
    adapters = trade_cfg.get("adapters") if isinstance(trade_cfg, dict) else {}
    if not isinstance(adapters, dict) or not adapters:
        raise TradeAdapterResolutionError(f"Chain '{chain}' does not define execution.trade.adapters.")
    return {str(key).strip().lower(): value for key, value in adapters.items() if isinstance(value, dict)}


def resolve_trade_execution_adapter(chain: str, adapter_key: str = "") -> tuple[str, dict[str, Any]]:
    adapters = _trade_execution_adapters(chain)
    requested = str(adapter_key or "").strip().lower()
    if not requested:
        requested = "default"
    entry = adapters.get(requested)
    if entry is None:
        for candidate in adapters.values():
            candidate_key = str(candidate.get("adapterKey") or "").strip().lower()
            if candidate_key and candidate_key == requested:
                entry = candidate
                break
    if entry is None and requested == "uniswap":
        entry = adapters.get("uniswap_v2") or adapters.get("default")
    if entry is None and requested == "default":
        default_entry = adapters.get("default")
        if isinstance(default_entry, dict):
            resolved_key = str(default_entry.get("adapterKey") or "default").strip().lower() or "default"
            return resolved_key, default_entry
    if entry is None:
        raise TradeAdapterResolutionError(
            f"unsupported_execution_adapter: chain '{chain}' does not define trade adapter '{requested}'."
        )
    resolved_key = str(entry.get("adapterKey") or requested).strip().lower() or requested
    return resolved_key, entry


def build_trade_execution_adapter(chain: str, adapter_key: str = "") -> AmmV2TradeAdapter:
    resolved_key, entry = resolve_trade_execution_adapter(chain, adapter_key)
    family = str(entry.get("family") or "amm_v2").strip().lower() or "amm_v2"
    if family != "amm_v2":
        raise TradeAdapterResolutionError(
            f"unsupported_execution_adapter: trade adapter '{resolved_key}' on chain '{chain}' has family '{family}'."
        )
    router = str(entry.get("router") or "").strip()
    factory = str(entry.get("factory") or "").strip()
    quoter = str(entry.get("quoter") or "").strip()
    if not router or not factory:
        raise TradeAdapterResolutionError(
            f"chain_config_invalid: trade adapter '{resolved_key}' on chain '{chain}' is missing router/factory."
        )
    return AmmV2TradeAdapter(chain=chain, adapter_key=resolved_key, router=router, factory=factory, quoter=quoter)
