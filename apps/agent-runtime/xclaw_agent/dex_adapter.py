from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


class DexAdapterError(Exception):
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


class UniswapV2RouterAdapter(DexAdapter):
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
