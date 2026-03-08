from __future__ import annotations

from typing import Any

from xclaw_agent.runtime.adapters.wallet import WalletRuntimeAdapter
from xclaw_agent.runtime import errors as runtime_errors
from xclaw_agent.runtime import preconditions as runtime_preconditions
from xclaw_agent.runtime import validators as runtime_validators


def cmd_wallet_rpc_health(rt: WalletRuntimeAdapter, args: Any) -> int:
    chk = rt.require_json_flag(args)
    if chk is not None:
        return chk

    chain = str(args.chain or "").strip()
    if not chain:
        return runtime_errors.emit_failure(rt, runtime_errors.invalid_input("--chain is required.", "Provide --chain and retry."))
    if not rt._is_solana_chain(chain):
        return rt.fail(
            "unsupported_chain",
            "wallet rpc-health currently supports Solana chains only.",
            "Use a solana_* chain key and retry.",
            {"chain": chain},
            exit_code=2,
        )

    try:
        payload = rt.solana_rpc_health(chain)
        mode = str(payload.get("mode") or "").strip()
        if mode == "public_ok":
            return rt.ok("Solana RPC health checked.", **payload)
        if mode == "proxy_fallback_used":
            return rt.ok("Solana RPC health checked (proxy fallback active).", **payload)
        return rt.fail(
            "rpc_unavailable",
            "Solana RPC health check failed for public and proxy fallback paths.",
            "Verify public RPC and server proxy fallback env/auth, then retry.",
            {"chain": chain, "rpcHealth": payload},
            exit_code=1,
        )
    except rt.SolanaRpcClientError as exc:
        return rt.fail(str(exc.code or "rpc_unavailable"), str(exc), "Verify Solana chain config and RPC settings, then retry.", {"chain": chain, **(exc.details or {})}, exit_code=1)
    except Exception as exc:
        return rt.fail("rpc_unavailable", str(exc), "Inspect Solana RPC health path and retry.", {"chain": chain}, exit_code=1)


def cmd_wallet_address(rt: WalletRuntimeAdapter, args: Any) -> int:
    chk = rt.require_json_flag(args)
    if chk is not None:
        return chk

    chain = args.chain
    try:
        store = rt.load_wallet_store()
        _, wallet = rt._chain_wallet(store, chain)
        if wallet:
            address = wallet.get("address")
            if isinstance(address, str) and (rt.is_hex_address(address) or rt.is_solana_address(address)):
                return rt.ok("Wallet address fetched.", chain=chain, address=address)
    except (rt.WalletStoreError, rt.WalletSecurityError) as exc:
        return rt.fail("wallet_store_invalid", str(exc), "Repair wallet store metadata and retry.", {"chain": chain}, exit_code=1)

    _, legacy_wallet = rt.ensure_wallet_entry(chain)
    addr = legacy_wallet.get("address")
    if not isinstance(addr, str) or (not rt.is_hex_address(addr) and not rt.is_solana_address(addr)):
        return rt.fail("wallet_missing", f"No wallet configured for chain '{chain}'.", "Run hosted bootstrap installer to initialize wallet.", {"chain": chain}, exit_code=1)
    return rt.ok("Wallet address fetched.", chain=chain, address=addr)


def cmd_wallet_sign_challenge(rt: WalletRuntimeAdapter, args: Any) -> int:
    chk = rt.require_json_flag(args)
    if chk is not None:
        return chk
    if not args.message.strip():
        return runtime_errors.emit_failure(
            rt,
            runtime_errors.invalid_input("Challenge message cannot be empty.", "Provide a non-empty message string.", {"message": args.message}),
        )

    chain = args.chain
    try:
        store = rt.load_wallet_store()
        _, wallet = rt._chain_wallet(store, chain)
        if wallet:
            rt._validate_wallet_entry_shape(wallet)
        else:
            return rt.fail("wallet_missing", f"No wallet configured for chain '{chain}'.", "Run hosted bootstrap installer to initialize wallet.", {"chain": chain}, exit_code=1)

        try:
            rt._parse_canonical_challenge(args.message, chain)
        except ValueError as exc:
            return rt.fail(
                "invalid_challenge_format",
                str(exc),
                "Provide canonical challenge lines: domain, chain, nonce, timestamp, action.",
                {"format": rt.CHALLENGE_FORMAT_VERSION, "chain": chain},
                exit_code=2,
            )

        passphrase = rt._require_wallet_passphrase_for_signing(chain)
        private_key_bytes = rt._decrypt_private_key(wallet, passphrase)
        key_scheme = str(wallet.get("keyScheme") or "evm_secp256k1").strip().lower() or "evm_secp256k1"
        if key_scheme == "solana_ed25519" or rt._is_solana_chain(chain):
            signature = rt.solana_sign_message(private_key_bytes, args.message)
            scheme = "solana_ed25519"
        else:
            signature = rt._cast_sign_message(private_key_bytes.hex(), args.message)
            scheme = "eip191_personal_sign"
        return rt.ok("Challenge signed.", chain=chain, address=wallet.get("address"), signature=signature, scheme=scheme, challengeFormat=rt.CHALLENGE_FORMAT_VERSION)
    except rt.WalletPassphraseError as exc:
        return rt.fail("non_interactive", str(exc), "Set XCLAW_WALLET_PASSPHRASE or run with TTY attached.", {"chain": chain}, exit_code=2)
    except rt.WalletSecurityError as exc:
        return rt.fail("unsafe_permissions", str(exc), "Restrict permissions to owner-only (0700/0600) and retry.", {"chain": chain}, exit_code=1)
    except rt.WalletStoreError as exc:
        return runtime_errors.wallet_store_failure(
            rt,
            exc,
            default_code="sign_failed",
            default_action_hint="Verify wallet passphrase and cast runtime, then retry.",
            chain=chain,
            invalid_token_hint="Use a canonical token symbol (for example USDC) or 0x token address.",
            invalid_token_details={"chain": chain, "token": str(getattr(args, "token", "") or "")},
        )
    except rt.SolanaRuntimeError as exc:
        return rt.fail(exc.code, str(exc), "Install Solana runtime dependencies and retry.", {"chain": chain, **exc.details}, exit_code=1)
    except Exception as exc:
        return rt.fail("sign_failed", str(exc), "Inspect runtime wallet/signing configuration and retry.", {"chain": chain}, exit_code=1)


def cmd_wallet_send(rt: WalletRuntimeAdapter, args: Any) -> int:
    chk = rt.require_json_flag(args)
    if chk is not None:
        return chk
    try:
        runtime_validators.validate_recipient(rt, args.chain, args.to)
        amount_wei = runtime_validators.parse_base_unit_amount(args.amount_wei)
    except runtime_errors.RuntimeCommandFailure as exc:
        return runtime_errors.emit_failure(rt, exc)

    chain = args.chain
    try:
        outbound_eval = runtime_preconditions.prepare_transfer_flow(rt, chain, amount_wei, args.to)
        approval_required, transfer_policy = rt._transfer_requires_approval(chain, "native", None)
        native_symbol = rt._native_symbol_for_chain(chain)
        amount_human, amount_unit = rt._transfer_amount_display(str(args.amount_wei), "native", native_symbol, rt._native_decimals_for_chain(chain))
        amount_display = f"{amount_human} {amount_unit}"
        if not bool(outbound_eval.get("allowed")):
            approval_required = True
        to_address_store = args.to if rt._is_solana_chain(chain) else args.to.lower()
        approval_id = rt._make_transfer_approval_id()
        flow = {
            "approvalId": approval_id,
            "chainKey": chain,
            "status": "approval_pending" if approval_required else "approved",
            "transferType": "native",
            "tokenAddress": None,
            "tokenSymbol": native_symbol,
            "tokenDecimals": rt._native_decimals_for_chain(chain),
            "toAddress": to_address_store,
            "amountWei": str(args.amount_wei),
            "reasonCode": None,
            "reasonMessage": None,
            "createdAt": rt.utc_now(),
            "updatedAt": rt.utc_now(),
            "transferPolicy": transfer_policy,
            "policyBlockedAtCreate": bool(outbound_eval.get("policyBlockedAtCreate", False)),
            "policyBlockReasonCode": outbound_eval.get("policyBlockReasonCode"),
            "policyBlockReasonMessage": outbound_eval.get("policyBlockReasonMessage"),
            "executionMode": None,
        }
        rt._record_pending_transfer_flow(approval_id, flow)
        try:
            rt._mirror_transfer_approval(flow, require_delivery=approval_required)
        except rt.WalletStoreError as exc:
            rt._remove_pending_transfer_flow(approval_id)
            return rt.fail(
                "approval_sync_failed",
                "Transfer approval could not be synced to management inbox.",
                "Retry once. If this persists, run auth-recover and verify API connectivity before retrying send.",
                {"approvalId": approval_id, "chain": chain, "error": str(exc)},
                exit_code=1,
            )

        if approval_required:
            try:
                rt._maybe_send_telegram_transfer_approval_prompt(flow)
            except Exception:
                pass
            queued_message = (
                "Approval required (transfer)\n\n"
                "Request: Send native token\n"
                f"Amount: {amount_display} ({args.amount_wei} base units)\n"
                f"To: `{to_address_store}`\n"
                f"Chain: `{chain}`\n"
                f"Approval ID: `{approval_id}`\n"
                "Status: approval_pending\n\n"
                "Tap Approve or Deny."
            )
            if bool(outbound_eval.get("policyBlockedAtCreate")):
                queued_message += (
                    f"\n\nPolicy blocked at create: {str(outbound_eval.get('policyBlockReasonCode') or 'unknown')}"
                    "\nApprove to execute this transfer as a one-off override."
                )
            return rt.fail(
                "approval_required",
                "Transfer is waiting for management approval.",
                "Send queuedMessage verbatim so Telegram buttons can attach, then wait for Approve/Deny.",
                {
                    "approvalId": approval_id,
                    "chain": chain,
                    "status": "approval_pending",
                    "queuedMessage": queued_message,
                    "amount": amount_human,
                    "amountUnit": amount_unit,
                    "amountDisplay": amount_display,
                    "nextAction": "Post queuedMessage verbatim to the user in the active chat.",
                    "policyBlockedAtCreate": bool(outbound_eval.get("policyBlockedAtCreate", False)),
                    "policyBlockReasonCode": outbound_eval.get("policyBlockReasonCode"),
                    "policyBlockReasonMessage": outbound_eval.get("policyBlockReasonMessage"),
                },
                exit_code=1,
            )
        return rt.emit(rt._execute_pending_transfer_flow(flow))
    except rt.WalletPolicyError as exc:
        return rt.fail(exc.code, str(exc), exc.action_hint, exc.details, exit_code=1)
    except rt.WalletPassphraseError as exc:
        return rt.fail("non_interactive", str(exc), "Set XCLAW_WALLET_PASSPHRASE or run with TTY attached.", {"chain": chain}, exit_code=2)
    except rt.WalletSecurityError as exc:
        return rt.fail("unsafe_permissions", str(exc), "Restrict permissions to owner-only (0700/0600) and retry.", {"chain": chain}, exit_code=1)
    except rt.WalletStoreError as exc:
        return runtime_errors.wallet_store_failure(
            rt,
            exc,
            default_code="send_failed",
            default_action_hint="Verify wallet passphrase, policy, RPC connectivity, and retry.",
            chain=chain,
            map_chain_config=True,
        )
    except Exception as exc:
        return rt.fail("send_failed", str(exc), "Inspect runtime send configuration and retry.", {"chain": chain}, exit_code=1)


def cmd_wallet_send_token(rt: WalletRuntimeAdapter, args: Any) -> int:
    chk = rt.require_json_flag(args)
    if chk is not None:
        return chk
    chain = args.chain
    try:
        runtime_validators.validate_recipient(rt, chain, args.to)
        amount_wei = runtime_validators.parse_base_unit_amount(args.amount_wei)
        token_input = str(args.token or "").strip()
        token_address = rt._resolve_token_address(chain, token_input)
        token_symbol = str(token_input or "").strip().upper() or "TOKEN"
        token_decimals = 9 if rt._is_solana_chain(chain) else 18
        if not rt._is_solana_chain(chain):
            token_meta = rt._fetch_erc20_metadata(chain, token_address)
            token_symbol = str(token_meta.get("symbol") or "").strip() or token_symbol
            try:
                token_decimals = int(token_meta.get("decimals", 18))
            except Exception:
                token_decimals = 18
        if not rt._is_solana_chain(chain) and not rt.is_hex_address(token_input):
            min_symbol_wei = 10 ** max(token_decimals - 6, 0)
            if amount_wei < min_symbol_wei:
                one_token_wei = 10**max(token_decimals, 0)
                raise runtime_errors.invalid_input(
                    "Amount is too small for symbol-based transfer and looks like a base-unit mistake.",
                    "Use base-unit integer amount. Example: 10 tokens => 10 * (10^decimals) wei. "
                    f"For {token_symbol}, 1 token = {one_token_wei} wei.",
                    {
                        "chain": chain,
                        "token": token_input,
                        "tokenAddress": token_address,
                        "tokenSymbol": token_symbol,
                        "tokenDecimals": token_decimals,
                        "amountWei": str(amount_wei),
                        "minSuggestedWeiForSymbolInput": str(min_symbol_wei),
                    },
                )
    except runtime_errors.RuntimeCommandFailure as exc:
        return runtime_errors.emit_failure(rt, exc)
    except rt.TokenResolutionError as exc:
        return rt.fail(exc.code, str(exc), "Use a token address or a unique tracked symbol.", exc.details, exit_code=2)

    try:
        outbound_eval = runtime_preconditions.prepare_transfer_flow(rt, chain, amount_wei, args.to)
        amount_human, amount_unit = rt._transfer_amount_display(str(args.amount_wei), "token", token_symbol, token_decimals)
        amount_display = f"{amount_human} {amount_unit}"
        approval_required, transfer_policy = rt._transfer_requires_approval(chain, "token", token_address)
        if not bool(outbound_eval.get("allowed")):
            approval_required = True
        token_address_store = token_address if rt._is_solana_chain(chain) else token_address.lower()
        to_address_store = args.to if rt._is_solana_chain(chain) else args.to.lower()
        approval_id = rt._make_transfer_approval_id()
        flow = {
            "approvalId": approval_id,
            "chainKey": chain,
            "status": "approval_pending" if approval_required else "approved",
            "transferType": "token",
            "tokenAddress": token_address_store,
            "tokenSymbol": token_symbol,
            "tokenDecimals": token_decimals,
            "toAddress": to_address_store,
            "amountWei": str(args.amount_wei),
            "reasonCode": None,
            "reasonMessage": None,
            "createdAt": rt.utc_now(),
            "updatedAt": rt.utc_now(),
            "transferPolicy": transfer_policy,
            "policyBlockedAtCreate": bool(outbound_eval.get("policyBlockedAtCreate", False)),
            "policyBlockReasonCode": outbound_eval.get("policyBlockReasonCode"),
            "policyBlockReasonMessage": outbound_eval.get("policyBlockReasonMessage"),
            "executionMode": None,
        }
        rt._record_pending_transfer_flow(approval_id, flow)
        try:
            rt._mirror_transfer_approval(flow, require_delivery=approval_required)
        except rt.WalletStoreError as exc:
            rt._remove_pending_transfer_flow(approval_id)
            return rt.fail(
                "approval_sync_failed",
                "Transfer approval could not be synced to management inbox.",
                "Retry once. If this persists, run auth-recover and verify API connectivity before retrying send.",
                {"approvalId": approval_id, "chain": chain, "error": str(exc)},
                exit_code=1,
            )

        if approval_required:
            try:
                rt._maybe_send_telegram_transfer_approval_prompt(flow)
            except Exception:
                pass
            queued_message = (
                "Approval required (transfer)\n\n"
                "Request: Send token\n"
                f"Token: {token_symbol} ({token_address_store})\n"
                f"Amount: {amount_display} ({args.amount_wei} wei)\n"
                f"To: `{to_address_store}`\n"
                f"Chain: `{chain}`\n"
                f"Approval ID: `{approval_id}`\n"
                "Status: approval_pending\n\n"
                "Tap Approve or Deny."
            )
            if bool(outbound_eval.get("policyBlockedAtCreate")):
                queued_message += (
                    f"\n\nPolicy blocked at create: {str(outbound_eval.get('policyBlockReasonCode') or 'unknown')}"
                    "\nApprove to execute this transfer as a one-off override."
                )
            return rt.fail(
                "approval_required",
                "Transfer is waiting for management approval.",
                "Send queuedMessage verbatim so Telegram buttons can attach, then wait for Approve/Deny.",
                {
                    "approvalId": approval_id,
                    "chain": chain,
                    "status": "approval_pending",
                    "queuedMessage": queued_message,
                    "amount": amount_human,
                    "amountUnit": amount_unit,
                    "amountDisplay": amount_display,
                    "nextAction": "Post queuedMessage verbatim to the user in the active chat.",
                    "policyBlockedAtCreate": bool(outbound_eval.get("policyBlockedAtCreate", False)),
                    "policyBlockReasonCode": outbound_eval.get("policyBlockReasonCode"),
                    "policyBlockReasonMessage": outbound_eval.get("policyBlockReasonMessage"),
                },
                exit_code=1,
            )
        return rt.emit(rt._execute_pending_transfer_flow(flow))
    except rt.WalletPolicyError as exc:
        return rt.fail(exc.code, str(exc), exc.action_hint, exc.details, exit_code=1)
    except rt.TokenResolutionError as exc:
        return rt.fail(exc.code, str(exc), "Use a token address or a unique tracked symbol.", exc.details, exit_code=2)
    except rt.WalletPassphraseError as exc:
        return rt.fail("non_interactive", str(exc), "Set XCLAW_WALLET_PASSPHRASE or run with TTY attached.", {"chain": chain}, exit_code=2)
    except rt.WalletSecurityError as exc:
        return rt.fail("unsafe_permissions", str(exc), "Restrict permissions to owner-only (0700/0600) and retry.", {"chain": chain}, exit_code=1)
    except rt.WalletStoreError as exc:
        return runtime_errors.wallet_store_failure(
            rt,
            exc,
            default_code="send_failed",
            default_action_hint="Verify wallet passphrase, policy, RPC connectivity, and retry.",
            chain=chain,
            map_chain_config=True,
        )
    except Exception as exc:
        return rt.fail("send_failed", str(exc), "Inspect runtime token-send configuration and retry.", {"chain": chain}, exit_code=1)
