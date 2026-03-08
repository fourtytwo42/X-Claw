from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class WalletRuntimeAdapter:
    require_json_flag: Callable[..., Any]
    fail: Callable[..., int]
    ok: Callable[..., int]
    emit: Callable[..., int]
    load_wallet_store: Callable[..., dict[str, Any]]
    ensure_wallet_entry: Callable[..., tuple[str | None, dict[str, Any]]]
    _chain_wallet: Callable[..., tuple[str | None, dict[str, Any] | None]]
    _validate_wallet_entry_shape: Callable[..., Any]
    _is_solana_chain: Callable[..., bool]
    is_hex_address: Callable[..., bool]
    is_solana_address: Callable[..., bool]
    solana_rpc_health: Callable[..., dict[str, Any]]
    solana_sign_message: Callable[..., str]
    _parse_canonical_challenge: Callable[..., Any]
    _require_wallet_passphrase_for_signing: Callable[..., str]
    _decrypt_private_key: Callable[..., bytes]
    _cast_sign_message: Callable[..., str]
    _resolve_token_address: Callable[..., str]
    _fetch_erc20_metadata: Callable[..., dict[str, Any]]
    _enforce_spend_preconditions: Callable[..., Any]
    _evaluate_outbound_transfer_policy: Callable[..., dict[str, Any]]
    _transfer_requires_approval: Callable[..., tuple[bool, Any]]
    _transfer_amount_display: Callable[..., tuple[str, str]]
    _native_symbol_for_chain: Callable[..., str]
    _native_decimals_for_chain: Callable[..., int]
    _make_transfer_approval_id: Callable[..., str]
    _record_pending_transfer_flow: Callable[..., Any]
    _remove_pending_transfer_flow: Callable[..., Any]
    _mirror_transfer_approval: Callable[..., Any]
    _maybe_send_telegram_transfer_approval_prompt: Callable[..., Any]
    _execute_pending_transfer_flow: Callable[..., dict[str, Any]]
    utc_now: Callable[..., str]
    CHALLENGE_FORMAT_VERSION: str
    SolanaRpcClientError: type[BaseException]
    SolanaRuntimeError: type[BaseException]
    TokenResolutionError: type[BaseException]
    WalletPassphraseError: type[BaseException]
    WalletPolicyError: type[BaseException]
    WalletSecurityError: type[BaseException]
    WalletStoreError: type[BaseException]
