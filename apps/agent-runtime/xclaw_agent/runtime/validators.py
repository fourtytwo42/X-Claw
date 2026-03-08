from __future__ import annotations

import re
from typing import Any

from xclaw_agent.runtime.errors import RuntimeCommandFailure, invalid_input, unsupported_mode


def require_chain_json_mode(rt: Any, args: Any) -> None:
    chk = rt.require_json_flag(args)
    if chk is not None:
        raise RuntimeCommandFailure("missing_flag", "This command requires --json output mode.", "Re-run with --json.", {}, chk)


def validate_recipient(rt: Any, chain: str, recipient: str, *, detail_key: str = "to") -> None:
    if rt._is_solana_chain(chain):
        if not rt.is_solana_address(recipient):
            raise invalid_input("Invalid recipient address format.", "Use a valid Solana base58 address.", {detail_key: recipient})
        return
    if not rt.is_hex_address(recipient):
        raise invalid_input("Invalid recipient address format.", "Use 0x-prefixed 20-byte hex address.", {detail_key: recipient})


def parse_base_unit_amount(amount_raw: str, *, details_key: str = "amountWei") -> int:
    if not re.fullmatch(r"[0-9]+", str(amount_raw or "").strip()):
        raise invalid_input("Invalid amount-wei format.", "Use base-unit integer string.", {details_key: amount_raw})
    return int(str(amount_raw).strip())


def require_distinct_trade_assets(token_in: str, token_out: str, chain: str) -> None:
    same_asset = token_in == token_out
    if not same_asset and not rt_is_solana_chain_key(chain):
        same_asset = token_in.lower() == token_out.lower()
    if same_asset:
        noun = "token mint addresses" if rt_is_solana_chain_key(chain) else "token addresses"
        raise invalid_input(
            "token-in and token-out must be different.",
            f"Provide two distinct {noun} (or symbols).",
            {"tokenIn": token_in, "tokenOut": token_out, "chain": chain},
        )


def parse_slippage_bps(raw: Any) -> int:
    try:
        slippage_bps = int(raw)
    except Exception as exc:  # pragma: no cover - defensive parity with existing CLI behavior
        raise invalid_input("slippage-bps must be between 0 and 5000.", "Use a value like 50 for 0.5% or 500 for 5%.", {"slippageBps": raw}) from exc
    if slippage_bps < 0 or slippage_bps > 5000:
        raise invalid_input("slippage-bps must be between 0 and 5000.", "Use a value like 50 for 0.5% or 500 for 5%.", {"slippageBps": raw})
    return slippage_bps


def require_real_mode(mode: str, *, chain: str, details: dict[str, Any] | None = None) -> None:
    if str(mode) != "real":
        payload = {"mode": mode, "supportedMode": "real", "chain": chain}
        if details:
            payload.update(details)
        raise unsupported_mode(
            "Mock mode is deprecated for runtime trade execution.",
            "Execute network trades with mode=real on a configured chain.",
            payload,
        )


def require_wallet_key_scheme(key_scheme: str, *, chain: str, expected: str = "solana_ed25519") -> None:
    if str(key_scheme or "").strip() != expected:
        raise RuntimeCommandFailure(
            "wallet_store_invalid",
            f"Wallet keyScheme '{key_scheme}' is not compatible with Solana execution on chain '{chain}'.",
            "Use a wallet with the expected key scheme for this chain.",
            {"chain": chain, "keyScheme": key_scheme, "expectedKeyScheme": expected},
            1,
        )


def rt_is_solana_chain_key(chain: str) -> bool:
    return str(chain or "").startswith("solana_")
