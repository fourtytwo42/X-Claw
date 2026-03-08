from __future__ import annotations

import argparse
import io
import json
import time
import urllib.parse
from contextlib import redirect_stdout
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Callable

from xclaw_agent.runtime.adapters.liquidity import LiquidityRuntimeAdapter


def cmd_liquidity_discover_pairs_impl(rt: LiquidityRuntimeAdapter, args: argparse.Namespace) -> int:
    chk = rt.require_json_flag(args)
    if chk is not None:
        return chk
    chain = str(args.chain or "").strip()
    dex = str(args.dex or "").strip().lower()
    try:
        rt.assert_chain_capability(chain, "liquidity")
        adapter = rt.build_liquidity_adapter_for_request(chain=chain, dex=dex, position_type="v2")
        if adapter.protocol_family != "amm_v2":
            return rt.fail(
                "unsupported_liquidity_adapter",
                f"Pair discovery currently supports v2-family adapters only. Resolved adapter family: {adapter.protocol_family}.",
                "Use a v2-family DEX for discovery and retry.",
                {"chain": chain, "dex": dex, "adapterFamily": adapter.protocol_family},
                exit_code=2,
            )

        min_reserve = int(str(args.min_reserve or "1"))
        limit = int(str(args.limit or "10"))
        scan_max = int(str(getattr(args, "scan_max", None) or "50"))
        if min_reserve < 0:
            return rt.fail("invalid_input", "min-reserve must be >= 0.", "Provide a non-negative integer.", {"minReserve": args.min_reserve}, exit_code=2)
        if limit < 1 or limit > 100:
            return rt.fail("invalid_input", "limit must be between 1 and 100.", "Use --limit in [1..100].", {"limit": args.limit}, exit_code=2)
        if scan_max < 1 or scan_max > 2000:
            return rt.fail("invalid_input", "scan-max must be between 1 and 2000.", "Use --scan-max in [1..2000].", {"scanMax": args.scan_max}, exit_code=2)

        router = rt._require_chain_contract_address(chain, "router")
        factory_raw = rt._cast_call_stdout(chain, router, "factory()(address)")
        factory = rt._parse_address_from_cast_output(factory_raw)
        if factory.lower() == "0x0000000000000000000000000000000000000000":
            return rt.fail(
                "liquidity_pair_discovery_failed",
                f"Factory address resolved to zero for router {router}.",
                "Verify chain router/factory contract metadata and retry.",
                {"chain": chain, "dex": dex, "router": router},
                exit_code=1,
            )

        pair_len_raw = rt._cast_call_stdout(chain, factory, "allPairsLength()(uint256)")
        pair_count = rt._parse_uint_from_cast_output(pair_len_raw)
        if pair_count <= 0:
            return rt.fail(
                "liquidity_no_viable_pair",
                "Factory returned zero pairs.",
                "Try another DEX on this chain or verify deployment state.",
                {"chain": chain, "dex": dex, "factory": factory, "pairCount": pair_count},
                exit_code=1,
            )

        scan_cap = min(pair_count, scan_max)
        candidates: list[dict[str, Any]] = []
        skipped = 0
        failures = 0
        error_samples: list[str] = []
        for idx in range(scan_cap):
            try:
                pair_out = rt._cast_call_stdout(chain, factory, "allPairs(uint256)(address)", str(idx))
                pair_addr = rt._parse_address_from_cast_output(pair_out)
                token0 = rt._parse_address_from_cast_output(rt._cast_call_stdout(chain, pair_addr, "token0()(address)"))
                token1 = rt._parse_address_from_cast_output(rt._cast_call_stdout(chain, pair_addr, "token1()(address)"))
                reserves_out = rt._cast_call_stdout(chain, pair_addr, "getReserves()(uint112,uint112,uint32)")
                reserve_values = rt._parse_uint_tuple_from_cast_output(reserves_out)
                if len(reserve_values) < 2:
                    raise rt.WalletStoreError("Unable to parse reserves from getReserves output.")
                reserve0 = int(reserve_values[0])
                reserve1 = int(reserve_values[1])
                if reserve0 < min_reserve or reserve1 < min_reserve:
                    skipped += 1
                    continue
                candidates.append(
                    {
                        "pairAddress": pair_addr.lower(),
                        "token0": token0.lower(),
                        "token1": token1.lower(),
                        "reserve0": str(reserve0),
                        "reserve1": str(reserve1),
                        "minReserve": str(min(reserve0, reserve1)),
                    }
                )
            except Exception as exc:
                failures += 1
                if len(error_samples) < 5:
                    error_samples.append(f"index={idx}: {exc}")
                continue

        if not candidates:
            return rt.fail(
                "liquidity_no_viable_pair",
                "No viable pair matched reserve filters during discovery scan.",
                "Lower --min-reserve, try another DEX, or verify pair liquidity.",
                {
                    "chain": chain,
                    "dex": dex,
                    "factory": factory,
                    "pairCount": pair_count,
                    "scanCount": scan_cap,
                    "minReserve": str(min_reserve),
                    "skipped": skipped,
                    "failures": failures,
                    "errorSamples": error_samples,
                },
                exit_code=1,
            )

        candidates.sort(key=lambda row: int(str(row.get("minReserve") or "0")), reverse=True)
        selected = candidates[:limit]
        return rt.ok(
            "Liquidity pair discovery complete.",
            chain=chain,
            dex=dex,
            adapterFamily=adapter.protocol_family,
            router=router.lower(),
            factory=factory.lower(),
            pairCount=pair_count,
            scanCount=scan_cap,
            minReserve=str(min_reserve),
            scanMax=scan_max,
            candidateCount=len(candidates),
            returnedCount=len(selected),
            truncated=pair_count > scan_cap,
            pairs=selected,
            errorSamples=error_samples,
        )
    except rt.ChainRegistryError as exc:
        return rt.fail("unsupported_chain_capability", str(exc), rt.chain_supported_hint(), {"chain": chain, "requiredCapability": "liquidity"}, exit_code=2)
    except rt.UnsupportedLiquidityAdapter as exc:
        return rt.fail(
            "unsupported_liquidity_adapter",
            str(exc),
            "Choose a supported chain/dex combination and retry.",
            {"chain": chain, "dex": dex},
            exit_code=2,
        )
    except rt.WalletStoreError as exc:
        return rt.fail(
            "liquidity_pair_discovery_failed",
            str(exc),
            "Verify router/factory metadata, chain RPC availability, and retry.",
            {"chain": chain, "dex": dex},
            exit_code=1,
        )
    except Exception as exc:
        return rt.fail(
            "liquidity_pair_discovery_failed",
            str(exc),
            "Inspect runtime pair discovery path and retry.",
            {"chain": chain, "dex": dex},
            exit_code=1,
        )

def cmd_liquidity_quote_add_impl(rt: LiquidityRuntimeAdapter, args: argparse.Namespace) -> int:
    chk = rt.require_json_flag(args)
    if chk is not None:
        return chk
    chain = str(args.chain or "").strip()
    dex = str(args.dex or "").strip().lower()
    try:
        rt.assert_chain_capability(chain, "liquidity")
        default_position_type = "v3" if rt._is_solana_chain(chain) else "v2"
        position_type = str(args.position_type or default_position_type).strip().lower()
        adapter = rt.build_liquidity_adapter_for_request(chain=chain, dex=dex, position_type=position_type)
        token_a = rt._resolve_token_address(chain, args.token_a)
        token_b = rt._resolve_token_address(chain, args.token_b)
        if token_a.lower() == token_b.lower():
            return rt.fail("invalid_input", "token-a and token-b must be different.", "Provide distinct token values.", {"chain": chain}, exit_code=2)
        amount_a_h = rt._parse_positive_amount_text(str(args.amount_a), "amount-a")
        amount_b_h = rt._parse_positive_amount_text(str(args.amount_b), "amount-b")
        slippage_bps = int(args.slippage_bps)
        if slippage_bps < 0 or slippage_bps > 5000:
            return rt.fail("invalid_input", "slippage-bps must be between 0 and 5000.", "Use integer bps in range.", {"slippageBps": args.slippage_bps}, exit_code=2)
        v3_meta: dict[str, Any] = {}
        if position_type == "v3":
            v3_range_text = str(args.v3_range or "").strip()
            if not v3_range_text and rt._is_solana_chain(chain):
                v3_range_text = "100:0:0"
            try:
                fee, tick_lower, tick_upper = rt._parse_v3_range_text(v3_range_text)
            except rt.WalletStoreError as exc:
                return rt.fail("invalid_input", str(exc), "Provide --v3-range fee:tickLower:tickUpper.", {"chain": chain, "dex": dex}, exit_code=2)
            v3_meta = {
                "fee": fee,
                "tickLower": tick_lower,
                "tickUpper": tick_upper,
                "deadlineSec": 120,
            }
        preflight = adapter.quote_add(
            {
                "tokenA": token_a,
                "tokenB": token_b,
                "amountA": rt._decimal_text(amount_a_h),
                "amountB": rt._decimal_text(amount_b_h),
                "slippageBps": slippage_bps,
            }
        )
        if rt._is_solana_chain(chain):
            if adapter.protocol_family == "local_clmm":
                local_quote = rt.solana_local_quote_add(
                    amount_a=rt._decimal_text(amount_a_h),
                    amount_b=rt._decimal_text(amount_b_h),
                    slippage_bps=slippage_bps,
                )
            elif adapter.protocol_family == "raydium_clmm":
                pool_id = rt._resolve_raydium_pool_id(adapter, str(getattr(args, "pool_id", "") or ""))
                if not pool_id:
                    return rt.fail(
                        "invalid_input",
                        "Raydium quote-add requires --pool-id when no single default pool is configured.",
                        "Provide --pool-id for the target Raydium CLMM pool.",
                        {"chain": chain, "dex": dex},
                        exit_code=2,
                    )
                local_quote = rt.solana_raydium_quote_add(
                    amount_a=rt._decimal_text(amount_a_h),
                    amount_b=rt._decimal_text(amount_b_h),
                    slippage_bps=slippage_bps,
                    pool_id=pool_id,
                )
            else:
                return rt.fail(
                    "unsupported_liquidity_execution_family",
                    f"Unsupported Solana liquidity adapter family '{adapter.protocol_family}' for quote-add.",
                    "Use local_clmm or raydium_clmm adapter.",
                    {"chain": chain, "dex": dex, "positionType": position_type},
                    exit_code=2,
                )
            return rt.ok(
                "Liquidity add quote ready.",
                chain=chain,
                dex=dex,
                positionType=position_type,
                tokenA=token_a,
                tokenB=token_b,
                amountA=rt._decimal_text(amount_a_h),
                amountB=rt._decimal_text(amount_b_h),
                quoteAmountB=local_quote.get("amountB"),
                minAmountB=local_quote.get("minAmountB"),
                slippageBps=slippage_bps,
                tokenASymbol=None,
                tokenBSymbol=None,
                tokenADecimals=9,
                tokenBDecimals=9,
                adapterFamily=adapter.protocol_family,
                preflight={**preflight.get("simulation", {}), **local_quote},
                simulationOnly=True,
            )
        token_a_meta = rt._fetch_erc20_metadata(chain, token_a)
        token_b_meta = rt._fetch_erc20_metadata(chain, token_b)
        token_a_decimals = int(token_a_meta.get("decimals", 18))
        token_b_decimals = int(token_b_meta.get("decimals", 18))
        amount_a_units = rt._to_units_uint(rt._decimal_text(amount_a_h), token_a_decimals)
        quote_out_units = rt._router_get_amount_out(chain, amount_a_units, token_a, token_b)
        quote_out_h = rt._format_units(int(quote_out_units), token_b_decimals)
        min_b_h = rt._decimal_text(rt._to_non_negative_decimal(quote_out_h) * Decimal(max(0, 10000 - slippage_bps)) / Decimal(10000))
        return rt.ok(
            "Liquidity add quote ready.",
            chain=chain,
            dex=dex,
            positionType=position_type,
            tokenA=token_a,
            tokenB=token_b,
            amountA=rt._decimal_text(amount_a_h),
            amountB=rt._decimal_text(amount_b_h),
            quoteAmountB=quote_out_h,
            minAmountB=min_b_h,
            slippageBps=slippage_bps,
            tokenASymbol=token_a_meta.get("symbol"),
            tokenBSymbol=token_b_meta.get("symbol"),
            tokenADecimals=token_a_decimals,
            tokenBDecimals=token_b_decimals,
            adapterFamily=adapter.protocol_family,
            preflight=preflight.get("simulation", {}),
            simulationOnly=True,
        )
    except rt.ChainRegistryError as exc:
        return rt.fail("unsupported_chain_capability", str(exc), rt.chain_supported_hint(), {"chain": chain, "requiredCapability": "liquidity"}, exit_code=2)
    except rt.UnsupportedLiquidityAdapter as exc:
        return rt.fail(
            "unsupported_liquidity_adapter",
            str(exc),
            "Choose a supported chain/dex/position-type combination and retry.",
            {"chain": chain, "dex": dex, "positionType": str(args.position_type or "v2")},
            exit_code=2,
        )
    except rt.LiquidityAdapterError as exc:
        return rt.fail("liquidity_preflight_failed", str(exc), "Fix the request payload and retry.", {"chain": chain, "dex": dex}, exit_code=2)
    except rt.WalletStoreError as exc:
        return rt.fail("liquidity_quote_add_failed", str(exc), "Verify tokens/amounts and retry.", {"chain": chain, "dex": dex}, exit_code=1)
    except Exception as exc:
        return rt.fail("liquidity_quote_add_failed", str(exc), "Inspect runtime liquidity quote-add path and retry.", {"chain": chain, "dex": dex}, exit_code=1)

def cmd_liquidity_quote_remove_impl(rt: LiquidityRuntimeAdapter, args: argparse.Namespace) -> int:
    chk = rt.require_json_flag(args)
    if chk is not None:
        return chk
    chain = str(args.chain or "").strip()
    dex = str(args.dex or "").strip().lower()
    try:
        rt.assert_chain_capability(chain, "liquidity")
        default_position_type = "v3" if rt._is_solana_chain(chain) else "v2"
        position_type = str(args.position_type or default_position_type).strip().lower()
        adapter = rt.build_liquidity_adapter_for_request(chain=chain, dex=dex, position_type=position_type)
        position_id = str(args.position_id or "").strip()
        if not position_id:
            return rt.fail("invalid_input", "position-id is required.", "Provide --position-id and retry.", {"chain": chain, "dex": dex}, exit_code=2)
        percent = int(args.percent)
        if percent < 1 or percent > 100:
            return rt.fail("invalid_input", "percent must be between 1 and 100.", "Use --percent in [1..100].", {"percent": args.percent}, exit_code=2)
        preflight = adapter.quote_remove({"positionId": position_id, "percent": percent})
        if rt._is_solana_chain(chain) and adapter.protocol_family == "raydium_clmm":
            pool_id = rt._resolve_raydium_pool_id(adapter, str(getattr(args, "pool_id", "") or ""))
            if not pool_id:
                return rt.fail(
                    "invalid_input",
                    "Raydium quote-remove requires --pool-id when no single default pool is configured.",
                    "Provide --pool-id for the target Raydium CLMM pool.",
                    {"chain": chain, "dex": dex, "positionId": position_id},
                    exit_code=2,
                )
            preflight = {"simulation": rt.solana_raydium_quote_remove(percent=percent, pool_id=pool_id)}
        return rt.ok(
            "Liquidity remove quote ready.",
            chain=chain,
            dex=dex,
            positionType=position_type,
            positionId=position_id,
            percent=percent,
            adapterFamily=adapter.protocol_family,
            preflight=preflight.get("simulation", {}),
            simulationOnly=True,
            note="Exact remove outputs are adapter-specific; runtime will recompute pre-execution.",
        )
    except rt.ChainRegistryError as exc:
        return rt.fail("unsupported_chain_capability", str(exc), rt.chain_supported_hint(), {"chain": chain, "requiredCapability": "liquidity"}, exit_code=2)
    except rt.UnsupportedLiquidityAdapter as exc:
        return rt.fail(
            "unsupported_liquidity_adapter",
            str(exc),
            "Choose a supported chain/dex/position-type combination and retry.",
            {"chain": chain, "dex": dex, "positionType": str(args.position_type or "v2")},
            exit_code=2,
        )
    except rt.LiquidityAdapterError as exc:
        return rt.fail("liquidity_preflight_failed", str(exc), "Fix the request payload and retry.", {"chain": chain, "dex": dex}, exit_code=2)
    except Exception as exc:
        return rt.fail("liquidity_quote_remove_failed", str(exc), "Inspect runtime liquidity quote-remove path and retry.", {"chain": chain, "dex": dex}, exit_code=1)

def cmd_liquidity_add_impl(rt: LiquidityRuntimeAdapter, args: argparse.Namespace) -> int:
    chk = rt.require_json_flag(args)
    if chk is not None:
        return chk
    chain = str(args.chain or "").strip()
    dex = str(args.dex or "").strip().lower()
    try:
        rt.assert_chain_capability(chain, "liquidity")
        default_position_type = "v3" if rt._is_solana_chain(chain) else "v2"
        position_type = str(args.position_type or default_position_type).strip().lower()
        token_a = rt._resolve_token_address(chain, args.token_a)
        token_b = rt._resolve_token_address(chain, args.token_b)
        if token_a.lower() == token_b.lower():
            return rt.fail("invalid_input", "token-a and token-b must be different.", "Provide distinct token values.", {"chain": chain}, exit_code=2)
        amount_a_h = rt._parse_positive_amount_text(str(args.amount_a), "amount-a")
        amount_b_h = rt._parse_positive_amount_text(str(args.amount_b), "amount-b")
        slippage_bps = int(args.slippage_bps)
        if slippage_bps < 0 or slippage_bps > 5000:
            return rt.fail("invalid_input", "slippage-bps must be between 0 and 5000.", "Use integer bps in range.", {"slippageBps": args.slippage_bps}, exit_code=2)
        v3_meta: dict[str, Any] = {}
        if position_type == "v3":
            v3_range_text = str(args.v3_range or "").strip()
            if not v3_range_text and rt._is_solana_chain(chain):
                v3_range_text = "100:0:0"
            try:
                fee, tick_lower, tick_upper = rt._parse_v3_range_text(v3_range_text)
            except rt.WalletStoreError as exc:
                return rt.fail("invalid_input", str(exc), "Provide --v3-range fee:tickLower:tickUpper.", {"chain": chain, "dex": dex}, exit_code=2)
            v3_meta = {"fee": fee, "tickLower": tick_lower, "tickUpper": tick_upper, "deadlineSec": 120}

        provider_requested, _ = rt._liquidity_provider_settings(chain)
        adapter = rt.build_liquidity_adapter_for_request(chain=chain, dex=dex, position_type=position_type)
        adapter_preflight = adapter.quote_add(
            {
                "tokenA": token_a,
                "tokenB": token_b,
                "amountA": rt._decimal_text(amount_a_h),
                "amountB": rt._decimal_text(amount_b_h),
                "slippageBps": slippage_bps,
            }
        )
        adapter_family = adapter.protocol_family
        adapter_dex = adapter.dex
        if rt._is_solana_chain(chain) and adapter.protocol_family == "raydium_clmm":
            pool_id = rt._resolve_raydium_pool_id(adapter, str(getattr(args, "pool_id", "") or ""))
            if not pool_id:
                return rt.fail(
                    "invalid_input",
                    "Raydium liquidity add requires --pool-id when no single default pool is configured.",
                    "Provide --pool-id for the target Raydium CLMM pool.",
                    {"chain": chain, "dex": dex},
                    exit_code=2,
                )
            v3_meta["poolId"] = pool_id
        agent_id = rt._resolve_agent_id_or_fail(chain)
        preflight = adapter_preflight
        payload = {
            "schemaVersion": 1,
            "agentId": agent_id,
            "chainKey": chain,
            "dex": adapter_dex,
            "action": "add",
            "positionType": position_type,
            "tokenA": token_a,
            "tokenB": token_b,
            "amountA": rt._decimal_text(amount_a_h),
            "amountB": rt._decimal_text(amount_b_h),
            "slippageBps": slippage_bps,
            "details": {
                "v3Range": str(args.v3_range or "").strip() or None,
                "v3": v3_meta if position_type == "v3" else None,
                "adapterFamily": adapter_family,
                "preflight": preflight.get("simulation", {}) if isinstance(preflight, dict) else {},
                "providerRequested": provider_requested,
                "source": "runtime_liquidity_add",
            },
        }
        status_code, body = rt._api_request("POST", "/liquidity/proposed", payload=payload, include_idempotency=True)
        if status_code < 200 or status_code >= 300:
            return rt.fail(
                str(body.get("code", "api_error")),
                str(body.get("message", f"liquidity proposed failed ({status_code})")),
                str(body.get("actionHint", "Verify policy/approval settings and retry.")),
                rt._api_error_details(status_code, body, "/liquidity/proposed", chain=chain),
                exit_code=1,
            )
        liquidity_intent_id = str(body.get("liquidityIntentId") or "").strip()
        status = str(body.get("status") or "")
        if status == "approval_pending":
            flow = {
                "liquidityIntentId": liquidity_intent_id,
                "chainKey": chain,
                "dex": adapter_dex,
                "action": "add",
                "tokenA": token_a,
                "tokenB": token_b,
                "amountA": rt._decimal_text(amount_a_h),
                "amountB": rt._decimal_text(amount_b_h),
            }
            try:
                rt._maybe_send_telegram_liquidity_approval_prompt(flow)
            except Exception:
                pass
            queued_message = (
                "Approval required (liquidity)\n\n"
                "Request: Add liquidity\n"
                f"Pair: {token_a}/{token_b}\n"
                f"Amounts: {rt._decimal_text(amount_a_h)} / {rt._decimal_text(amount_b_h)}\n"
                f"Chain: `{chain}`\n"
                f"DEX: `{adapter_dex}`\n"
                f"Intent ID: `{liquidity_intent_id}`\n"
                "Status: approval_pending\n\n"
                "Tap Approve or Deny."
            )
            return rt.fail(
                "approval_required",
                "Liquidity add is waiting for management approval.",
                "Send queuedMessage verbatim so Telegram buttons can attach, then wait for Approve/Deny.",
                {
                    "liquidityIntentId": liquidity_intent_id,
                    "chain": chain,
                    "dex": adapter_dex,
                    "status": status,
                    "queuedMessage": queued_message,
                    "nextAction": "Post queuedMessage verbatim to the user in the active chat.",
                },
                exit_code=1,
            )
        if status == "approved":
            code, payload = rt._run_liquidity_execute_inline(liquidity_intent_id, chain)
            if isinstance(payload, dict):
                payload.setdefault("liquidityIntentId", liquidity_intent_id)
                payload.setdefault("chain", chain)
                payload.setdefault("dex", adapter_dex)
                payload.setdefault("adapterFamily", adapter_family)
            return rt.emit(payload) if isinstance(payload, dict) else code
        return rt.ok(
            "Liquidity add intent created.",
            chain=chain,
            dex=adapter_dex,
            liquidityIntentId=liquidity_intent_id,
            status=status or "approved",
            approvalMode=status != "approval_pending",
            adapterFamily=adapter_family,
            preflight=preflight.get("simulation", {}) if isinstance(preflight, dict) else {},
            providerRequested=provider_requested,
        )
    except rt.ChainRegistryError as exc:
        return rt.fail("unsupported_chain_capability", str(exc), rt.chain_supported_hint(), {"chain": chain, "requiredCapability": "liquidity"}, exit_code=2)
    except rt.UnsupportedLiquidityAdapter as exc:
        return rt.fail(
            "unsupported_liquidity_adapter",
            str(exc),
            "Choose a supported chain/dex/position-type combination and retry.",
            {"chain": chain, "dex": dex, "positionType": str(args.position_type or "v2")},
            exit_code=2,
        )
    except rt.LiquidityAdapterError as exc:
        return rt.fail("liquidity_preflight_failed", str(exc), "Fix preflight parameters and retry.", {"chain": chain, "dex": dex}, exit_code=2)
    except rt.WalletStoreError as exc:
        return rt.fail("liquidity_add_failed", str(exc), "Verify API env/auth, chain capability, and inputs.", {"chain": chain, "dex": dex}, exit_code=1)
    except Exception as exc:
        return rt.fail("liquidity_add_failed", str(exc), "Inspect runtime liquidity add path and retry.", {"chain": chain, "dex": dex}, exit_code=1)

def cmd_liquidity_remove_impl(rt: LiquidityRuntimeAdapter, args: argparse.Namespace) -> int:
    chk = rt.require_json_flag(args)
    if chk is not None:
        return chk
    chain = str(args.chain or "").strip()
    dex = str(args.dex or "").strip().lower()
    try:
        rt.assert_chain_capability(chain, "liquidity")
        default_position_type = "v3" if rt._is_solana_chain(chain) else "v2"
        position_type = str(args.position_type or default_position_type).strip().lower()
        provider_requested, _ = rt._liquidity_provider_settings(chain)
        adapter = rt.build_liquidity_adapter_for_request(chain=chain, dex=dex, position_type=position_type)
        adapter_preflight: dict[str, Any] = {}
        adapter_dex = adapter.dex
        adapter_family = adapter.protocol_family
        agent_id = rt._resolve_agent_id_or_fail(chain)
        position_id = str(args.position_id or "").strip()
        if not position_id:
            return rt.fail("invalid_input", "position-id is required.", "Provide --position-id and retry.", {"chain": chain, "dex": dex}, exit_code=2)
        percent = int(args.percent)
        if percent < 1 or percent > 100:
            return rt.fail("invalid_input", "percent must be between 1 and 100.", "Use --percent in [1..100].", {"percent": args.percent}, exit_code=2)
        slippage_bps = int(args.slippage_bps)
        if slippage_bps < 0 or slippage_bps > 5000:
            return rt.fail("invalid_input", "slippage-bps must be between 0 and 5000.", "Use integer bps in range.", {"slippageBps": args.slippage_bps}, exit_code=2)
        adapter_preflight = adapter.quote_remove(
            {
                "positionId": position_id,
                "percent": percent,
                "slippageBps": slippage_bps,
            }
        )
        preflight = adapter_preflight
        if rt._is_solana_chain(chain):
            token_a_in = str(args.token_a or "").strip()
            token_b_in = str(args.token_b or "").strip()
            if not token_a_in or not token_b_in:
                return rt.fail(
                    "invalid_input",
                    "token-a and token-b are required for Solana liquidity remove intents.",
                    "Provide --token-a <mint> --token-b <mint> and retry.",
                    {"chain": chain, "dex": adapter_dex, "positionId": position_id},
                    exit_code=2,
                )
            resolved_token_a = rt._resolve_token_address(chain, token_a_in)
            resolved_token_b = rt._resolve_token_address(chain, token_b_in)
        elif adapter_family == "position_manager_v3":
            if not adapter.position_manager:
                return rt.fail(
                    "chain_config_invalid",
                    "Concentrated-liquidity execution metadata is incomplete for this chain.",
                    "Add execution.liquidity adapter position-manager metadata and retry.",
                    {"chain": chain, "dex": adapter_dex, "positionId": position_id},
                    exit_code=2,
                )
            snapshot = rt._read_v3_position_snapshot(chain, adapter.position_manager, position_id)
            resolved_token_a = str(snapshot.get("token0") or "").strip()
            resolved_token_b = str(snapshot.get("token1") or "").strip()
        else:
            resolved_token_a, resolved_token_b = rt._resolve_liquidity_remove_tokens(
                chain,
                position_id,
                str(args.token_a or "").strip(),
                str(args.token_b or "").strip(),
            )
        display_token_a = rt._token_symbol_for_display(chain, resolved_token_a) or resolved_token_a
        display_token_b = rt._token_symbol_for_display(chain, resolved_token_b) or resolved_token_b
        if adapter_family == "amm_v2":
            remove_context = rt._compute_v2_remove_liquidity_units(
                chain=chain,
                position_id=position_id,
                token_a=resolved_token_a,
                token_b=resolved_token_b,
                percent=percent,
            )
            liquidity_units = int(remove_context.get("liquidityUnits") or 0)
            if liquidity_units <= 0:
                return rt.fail(
                    "liquidity_preflight_zero_lp_balance",
                    "Position has no removable LP token balance for the requested percent.",
                    "Refresh liquidity positions or choose a position with non-zero LP balance.",
                    {
                        "chain": chain,
                        "dex": adapter_dex,
                        "positionId": position_id,
                        "pair": str(remove_context.get("pair") or "").lower(),
                        "lpToken": str(remove_context.get("lpToken") or "").lower(),
                        "lpBalance": str(remove_context.get("lpBalance") or "0"),
                        "percent": percent,
                    },
                    exit_code=1,
                )
        payload = {
            "schemaVersion": 1,
            "agentId": agent_id,
            "chainKey": chain,
            "dex": adapter_dex,
            "action": "remove",
            "positionType": position_type,
            "tokenA": resolved_token_a,
            "tokenB": resolved_token_b,
            "amountA": str(percent),
            "amountB": "0",
            "positionId": position_id,
            "slippageBps": slippage_bps,
            "details": {
                "percent": percent,
                "v3": {
                    "positionId": position_id,
                    "percent": percent,
                    "minAmountAUnits": "0",
                    "minAmountBUnits": "0",
                    "poolId": str(getattr(args, "pool_id", "") or "").strip() or None,
                }
                if position_type == "v3"
                else None,
                "adapterFamily": adapter_family,
                "tokenASymbol": display_token_a,
                "tokenBSymbol": display_token_b,
                "preflight": preflight.get("simulation", {}) if isinstance(preflight, dict) else {},
                "providerRequested": provider_requested,
                "source": "runtime_liquidity_remove",
            },
        }
        status_code, body = rt._api_request("POST", "/liquidity/proposed", payload=payload, include_idempotency=True)
        if status_code < 200 or status_code >= 300:
            return rt.fail(
                str(body.get("code", "api_error")),
                str(body.get("message", f"liquidity proposed failed ({status_code})")),
                str(body.get("actionHint", "Verify policy/approval settings and retry.")),
                rt._api_error_details(status_code, body, "/liquidity/proposed", chain=chain),
                exit_code=1,
            )
        liquidity_intent_id = str(body.get("liquidityIntentId") or "").strip()
        status = str(body.get("status") or "")
        if status == "approval_pending":
            flow = {
                "liquidityIntentId": liquidity_intent_id,
                "chainKey": chain,
                "dex": adapter_dex,
                "action": "remove",
                "tokenA": resolved_token_a,
                "tokenB": resolved_token_b,
                "tokenASymbol": display_token_a,
                "tokenBSymbol": display_token_b,
                "positionId": position_id,
                "percent": percent,
                "amountA": str(percent),
                "amountB": "0",
            }
            try:
                rt._maybe_send_telegram_liquidity_approval_prompt(flow)
            except Exception:
                pass
            queued_message = (
                "Approval required (liquidity)\n\n"
                "Request: Remove liquidity\n"
                f"Pair: {display_token_a}/{display_token_b}\n"
                f"Position ID: `{position_id}`\n"
                f"Percent: {percent}%\n"
                f"Chain: `{chain}`\n"
                f"DEX: `{adapter_dex}`\n"
                f"Intent ID: `{liquidity_intent_id}`\n"
                "Status: approval_pending\n\n"
                "Tap Approve or Deny."
            )
            return rt.fail(
                "approval_required",
                "Liquidity remove is waiting for management approval.",
                "Send queuedMessage verbatim so Telegram buttons can attach, then wait for Approve/Deny.",
                {
                    "liquidityIntentId": liquidity_intent_id,
                    "chain": chain,
                    "dex": adapter_dex,
                    "tokenA": resolved_token_a,
                    "tokenB": resolved_token_b,
                    "tokenASymbol": display_token_a,
                    "tokenBSymbol": display_token_b,
                    "status": status,
                    "queuedMessage": queued_message,
                    "nextAction": "Post queuedMessage verbatim to the user in the active chat.",
                },
                exit_code=1,
            )
        if status == "approved":
            code, payload = rt._run_liquidity_execute_inline(liquidity_intent_id, chain)
            if isinstance(payload, dict):
                payload.setdefault("liquidityIntentId", liquidity_intent_id)
                payload.setdefault("chain", chain)
                payload.setdefault("dex", adapter_dex)
                payload.setdefault("adapterFamily", adapter_family)
            return rt.emit(payload) if isinstance(payload, dict) else code
        return rt.ok(
            "Liquidity remove intent created.",
            chain=chain,
            dex=adapter_dex,
            liquidityIntentId=liquidity_intent_id,
            status=status or "approved",
            positionId=position_id,
            percent=percent,
            adapterFamily=adapter_family,
            preflight=preflight.get("simulation", {}) if isinstance(preflight, dict) else {},
            providerRequested=provider_requested,
        )
    except rt.ChainRegistryError as exc:
        return rt.fail("unsupported_chain_capability", str(exc), rt.chain_supported_hint(), {"chain": chain, "requiredCapability": "liquidity"}, exit_code=2)
    except rt.UnsupportedLiquidityAdapter as exc:
        return rt.fail(
            "unsupported_liquidity_adapter",
            str(exc),
            "Choose a supported chain/dex/position-type combination and retry.",
            {"chain": chain, "dex": dex, "positionType": str(args.position_type or "v2")},
            exit_code=2,
        )
    except rt.LiquidityAdapterError as exc:
        return rt.fail("liquidity_preflight_failed", str(exc), "Fix preflight parameters and retry.", {"chain": chain, "dex": dex}, exit_code=2)
    except rt.WalletStoreError as exc:
        return rt.fail("liquidity_remove_failed", str(exc), "Verify API env/auth, chain capability, and inputs.", {"chain": chain, "dex": dex}, exit_code=1)
    except Exception as exc:
        return rt.fail("liquidity_remove_failed", str(exc), "Inspect runtime liquidity remove path and retry.", {"chain": chain, "dex": dex}, exit_code=1)

def cmd_liquidity_increase_impl(rt: LiquidityRuntimeAdapter, args: argparse.Namespace) -> int:
    chk = rt.require_json_flag(args)
    if chk is not None:
        return chk
    chain = str(args.chain or "").strip()
    dex = str(args.dex or "").strip().lower()
    position_id = str(args.position_id or "").strip()
    try:
        rt.assert_chain_capability(chain, "liquidity")
        if not position_id:
            return rt.fail("invalid_input", "position-id is required.", "Provide --position-id and retry.", {"chain": chain}, exit_code=2)
        slippage_bps = int(args.slippage_bps)
        if slippage_bps < 0 or slippage_bps > 5000:
            return rt.fail("invalid_input", "slippage-bps must be between 0 and 5000.", "Use integer bps in range.", {"slippageBps": args.slippage_bps}, exit_code=2)

        provider_requested, _ = rt._liquidity_provider_settings(chain)
        adapter = rt.build_liquidity_adapter_for_request(chain=chain, dex=dex, position_type="v3")
        if adapter.protocol_family not in {"position_manager_v3", "local_clmm", "raydium_clmm"}:
            return rt.fail(
                "unsupported_liquidity_execution_family",
                f"Liquidity increase requires a concentrated-liquidity execution adapter, got '{adapter.protocol_family}'.",
                "Use a chain/dex with advanced concentrated-liquidity support and retry.",
                {"chain": chain, "dex": dex, "positionId": position_id},
                exit_code=2,
            )
        if not adapter.supports_operation("increase"):
            return rt.fail(
                "unsupported_liquidity_operation",
                f"Adapter '{adapter.dex}' does not support liquidity increase on chain '{chain}'.",
                "Choose a supported chain/dex combination and retry.",
                {"chain": chain, "dex": adapter.dex, "positionId": position_id},
                exit_code=2,
            )
        token_a = rt._resolve_token_address(chain, str(args.token_a or ""))
        token_b = rt._resolve_token_address(chain, str(args.token_b or ""))
        amount_a_text = rt._decimal_text(rt._parse_positive_amount_text(str(args.amount_a), "amount-a"))
        amount_b_text = rt._decimal_text(rt._parse_positive_amount_text(str(args.amount_b), "amount-b"))
        deadline = str(int(datetime.now(timezone.utc).timestamp()) + 120)

        if rt._is_solana_chain(chain) and adapter.protocol_family in {"local_clmm", "raydium_clmm"}:
            store = rt.load_wallet_store()
            wallet_address, secret = rt._execution_wallet_solana_secret(store, chain)
            amount_a_units = str(rt._to_units_uint(amount_a_text, 9))
            amount_b_units = str(rt._to_units_uint(amount_b_text, 9))
            min_a_units = str((int(amount_a_units) * max(0, 10000 - slippage_bps)) // 10000)
            min_b_units = str((int(amount_b_units) * max(0, 10000 - slippage_bps)) // 10000)
            if adapter.protocol_family == "local_clmm":
                if chain != "solana_localnet":
                    return rt.fail(
                        "unsupported_liquidity_adapter",
                        "local_clmm adapter is only supported on solana_localnet.",
                        "Switch to solana_localnet or use raydium_clmm.",
                        {"chain": chain, "dex": dex, "positionId": position_id},
                        exit_code=2,
                    )
                increased = rt.solana_local_increase_position(
                    chain=chain,
                    dex=adapter.dex,
                    owner=wallet_address,
                    position_id=position_id,
                    amount_a=amount_a_text,
                    amount_b=amount_b_text,
                )
                tx_hash = str(increased.get("txHash") or "")
                details = {
                    "amountAUnits": amount_a_units,
                    "amountBUnits": amount_b_units,
                    "minAmountAUnits": min_a_units,
                    "minAmountBUnits": min_b_units,
                    "approveTxHashes": [],
                    "operationTxHashes": [tx_hash] if tx_hash else [],
                    "simulationMode": True,
                    "routeKind": "adapter_default",
                    **increased,
                }
                return rt.ok(
                    "Liquidity position increased.",
                    chain=chain,
                    dex=adapter.dex,
                    positionId=position_id,
                    txHash=tx_hash,
                    approveTxHashes=[],
                    operationTxHashes=[tx_hash] if tx_hash else [],
                    providerRequested=provider_requested,
                    providerUsed="router_adapter",
                    fallbackUsed=False,
                    fallbackReason=None,
                    executionFamily="solana_clmm",
                    executionAdapter=adapter.dex,
                    routeKind="adapter_default",
                    liquidityOperation="increase",
                    details=details,
                )

            pool_id = rt._resolve_raydium_pool_id(adapter, "")
            if not pool_id:
                return rt.fail(
                    "invalid_input",
                    "Raydium liquidity increase requires configured pool metadata.",
                    "Provide pool metadata in chain config or include a single default pool.",
                    {"chain": chain, "dex": dex, "positionId": position_id},
                    exit_code=2,
                )
            execution = rt.solana_raydium_execute_instruction(
                chain=chain,
                rpc_url=rt._chain_rpc_url(chain),
                private_key_bytes=secret,
                owner=wallet_address,
                adapter_metadata=dict(adapter.adapter_metadata or {}),
                request={
                    "poolId": pool_id,
                    "positionId": position_id,
                    "tokenA": token_a,
                    "tokenB": token_b,
                    "amountAUnits": amount_a_units,
                    "amountBUnits": amount_b_units,
                    "minAmountAUnits": min_a_units,
                    "minAmountBUnits": min_b_units,
                    "slippageBps": slippage_bps,
                },
                operation_key="increase",
            )
            tx_hash = str(execution.tx_hash or "")
            details = {
                "poolId": pool_id,
                "amountAUnits": amount_a_units,
                "amountBUnits": amount_b_units,
                "minAmountAUnits": min_a_units,
                "minAmountBUnits": min_b_units,
                "approveTxHashes": [],
                "operationTxHashes": [tx_hash] if tx_hash else [],
                **execution.details,
            }
            return rt.ok(
                "Liquidity position increased.",
                chain=chain,
                dex=adapter.dex,
                positionId=position_id,
                txHash=tx_hash,
                approveTxHashes=[],
                operationTxHashes=[tx_hash] if tx_hash else [],
                providerRequested=provider_requested,
                providerUsed="router_adapter",
                fallbackUsed=False,
                fallbackReason=None,
                executionFamily="solana_clmm",
                executionAdapter=adapter.dex,
                routeKind=execution.route_kind,
                liquidityOperation="increase",
                details=details,
            )

        store = rt.load_wallet_store()
        wallet_address, private_key_hex = rt._execution_wallet(store, chain)
        token_a_meta = rt._fetch_erc20_metadata(chain, token_a)
        token_b_meta = rt._fetch_erc20_metadata(chain, token_b)
        amount_a_units = str(rt._to_units_uint(amount_a_text, int(token_a_meta.get("decimals", 18))))
        amount_b_units = str(rt._to_units_uint(amount_b_text, int(token_b_meta.get("decimals", 18))))
        min_a_units = str((int(amount_a_units) * max(0, 10000 - slippage_bps)) // 10000)
        min_b_units = str((int(amount_b_units) * max(0, 10000 - slippage_bps)) // 10000)
        plan = rt.build_liquidity_increase_plan(
            chain=chain,
            dex=adapter.dex,
            position_type="v3",
            request={
                "positionId": position_id,
                "tokenA": token_a,
                "tokenB": token_b,
                "amountAUnits": amount_a_units,
                "amountBUnits": amount_b_units,
                "minAmountAUnits": min_a_units,
                "minAmountBUnits": min_b_units,
                "deadline": deadline,
            },
            wallet_address=wallet_address,
            build_calldata=rt._cast_calldata,
        )
        execution = rt.execute_liquidity_plan(
            executor=rt._router_action_executor(),
            plan=plan,
            wallet_address=wallet_address,
            private_key_hex=private_key_hex,
            wait_for_operation_receipts=False,
            liquidity_operation="increase",
        )
        tx_hash = str(execution.tx_hash or "")
        builder_meta = rt._builder_output_from_hashes(chain, [*execution.approve_tx_hashes, *execution.operation_tx_hashes])
        return rt.ok(
            "Liquidity position increased.",
            chain=chain,
            dex=adapter.dex,
            positionId=position_id,
            txHash=tx_hash,
            approveTxHashes=execution.approve_tx_hashes,
            operationTxHashes=execution.operation_tx_hashes,
            providerRequested=provider_requested,
            providerUsed="router_adapter",
            fallbackUsed=False,
            fallbackReason=None,
            executionFamily=execution.execution_family,
            executionAdapter=execution.execution_adapter,
            routeKind=execution.route_kind,
            liquidityOperation="increase",
            details={**execution.details, **builder_meta},
            **builder_meta,
        )
    except rt.ChainRegistryError as exc:
        return rt.fail("unsupported_chain_capability", str(exc), rt.chain_supported_hint(), {"chain": chain, "requiredCapability": "liquidity"}, exit_code=2)
    except rt.UnsupportedLiquidityAdapter as exc:
        return rt.fail("unsupported_liquidity_adapter", str(exc), "Choose a supported chain/dex/position-type combination and retry.", {"chain": chain, "dex": dex}, exit_code=2)
    except rt.UnsupportedLiquidityOperation as exc:
        return rt.fail("unsupported_liquidity_operation", str(exc), "Use a chain/dex with concentrated-liquidity increase support.", {"chain": chain, "dex": dex, "positionId": position_id}, exit_code=2)
    except ValueError as exc:
        code = str(exc)
        if code == "chain_config_invalid":
            return rt.fail("chain_config_invalid", "Concentrated-liquidity execution metadata is incomplete for this chain.", "Add execution.liquidity adapter position-manager metadata and retry.", {"chain": chain, "dex": dex, "positionId": position_id}, exit_code=2)
        return rt.fail("liquidity_increase_failed", str(exc), "Verify local router-adapter configuration and retry.", {"chain": chain, "dex": dex, "positionId": position_id}, exit_code=1)
    except rt.WalletStoreError as exc:
        return rt.fail("liquidity_increase_failed", str(exc), "Verify local router-adapter configuration and retry.", {"chain": chain, "dex": dex, "positionId": position_id}, exit_code=1)
    except Exception as exc:
        return rt.fail("liquidity_increase_failed", str(exc), "Inspect runtime liquidity increase path and retry.", {"chain": chain, "dex": dex, "positionId": position_id}, exit_code=1)

def cmd_liquidity_claim_fees_impl(rt: LiquidityRuntimeAdapter, args: argparse.Namespace) -> int:
    chk = rt.require_json_flag(args)
    if chk is not None:
        return chk
    chain = str(args.chain or "").strip()
    dex = str(args.dex or "").strip().lower()
    position_id = str(args.position_id or "").strip()
    provider_requested = "router_adapter"
    provider_used = "router_adapter"
    fallback_used = False
    fallback_reason: dict[str, str] | None = None

    def _claim_failure_details() -> dict[str, Any]:
        details: dict[str, Any] = {
            "chain": chain,
            "dex": dex,
            "positionId": position_id,
            "operation": "claim_fees",
            "providerRequested": provider_requested,
            "fallbackUsed": bool(fallback_used),
            "fallbackReason": fallback_reason,
        }
        if provider_used:
            details["providerUsed"] = provider_used
        return details

    try:
        rt.assert_chain_capability(chain, "liquidity")
        if not position_id:
            return rt.fail("invalid_input", "position-id is required.", "Provide --position-id and retry.", _claim_failure_details(), exit_code=2)
        provider_requested, _ = rt._liquidity_provider_settings(chain)
        adapter = rt.build_liquidity_adapter_for_request(chain=chain, dex=dex, position_type="v3")
        if adapter.protocol_family not in {"position_manager_v3", "local_clmm", "raydium_clmm"}:
            return rt.fail(
                "unsupported_liquidity_execution_family",
                f"Liquidity claim-fees requires a concentrated-liquidity execution adapter, got '{adapter.protocol_family}'.",
                "Use a chain/dex with advanced concentrated-liquidity support and retry.",
                _claim_failure_details(),
                exit_code=2,
            )
        if not adapter.supports_operation("claim_fees"):
            return rt.fail(
                "unsupported_liquidity_operation",
                f"Adapter '{adapter.dex}' does not support claim-fees on chain '{chain}'.",
                "Choose a supported chain/dex combination and retry.",
                _claim_failure_details(),
                exit_code=2,
            )
        if rt._is_solana_chain(chain) and adapter.protocol_family in {"local_clmm", "raydium_clmm"}:
            store = rt.load_wallet_store()
            wallet_address, secret = rt._execution_wallet_solana_secret(store, chain)
            if adapter.protocol_family == "local_clmm":
                if chain != "solana_localnet":
                    return rt.fail(
                        "unsupported_liquidity_adapter",
                        "local_clmm adapter is only supported on solana_localnet.",
                        "Switch to solana_localnet or use raydium_clmm.",
                        _claim_failure_details(),
                        exit_code=2,
                    )
                claimed = rt.solana_local_claim_fees(
                    chain=chain,
                    dex=adapter.dex,
                    owner=wallet_address,
                    position_id=position_id,
                )
                tx_hash = str(claimed.get("txHash") or "").strip()
                details = {
                    "approveTxHashes": [],
                    "operationTxHashes": [tx_hash] if tx_hash else [],
                    "routeKind": "adapter_default",
                    "simulationMode": True,
                    **claimed,
                }
                return rt.ok(
                    "Liquidity fees claimed.",
                    chain=chain,
                    dex=adapter.dex,
                    positionId=position_id,
                    txHash=tx_hash,
                    approveTxHashes=[],
                    operationTxHashes=[tx_hash] if tx_hash else [],
                    providerRequested=provider_requested,
                    providerUsed=provider_used,
                    fallbackUsed=fallback_used,
                    fallbackReason=fallback_reason,
                    executionFamily="solana_clmm",
                    executionAdapter=adapter.dex,
                    routeKind="adapter_default",
                    liquidityOperation="claim_fees",
                    details=details,
                )
            pool_id = rt._resolve_raydium_pool_id(adapter, "")
            if not pool_id:
                return rt.fail(
                    "invalid_input",
                    "Raydium claim-fees requires configured pool metadata.",
                    "Provide pool metadata in chain config or include a single default pool.",
                    _claim_failure_details(),
                    exit_code=2,
                )
            execution = rt.solana_raydium_execute_instruction(
                chain=chain,
                rpc_url=rt._chain_rpc_url(chain),
                private_key_bytes=secret,
                owner=wallet_address,
                adapter_metadata=dict(adapter.adapter_metadata or {}),
                request={"poolId": pool_id, "positionId": position_id, "tokenId": position_id},
                operation_key="claim_fees",
            )
            tx_hash = str(execution.tx_hash or "").strip()
            details = {
                "poolId": pool_id,
                "approveTxHashes": [],
                "operationTxHashes": [tx_hash] if tx_hash else [],
                **execution.details,
            }
            return rt.ok(
                "Liquidity fees claimed.",
                chain=chain,
                dex=adapter.dex,
                positionId=position_id,
                txHash=tx_hash,
                approveTxHashes=[],
                operationTxHashes=[tx_hash] if tx_hash else [],
                providerRequested=provider_requested,
                providerUsed=provider_used,
                fallbackUsed=fallback_used,
                fallbackReason=fallback_reason,
                executionFamily="solana_clmm",
                executionAdapter=adapter.dex,
                routeKind=execution.route_kind,
                liquidityOperation="claim_fees",
                details=details,
            )

        store = rt.load_wallet_store()
        wallet_address, private_key_hex = rt._execution_wallet(store, chain)
        plan = rt.build_liquidity_claim_fees_plan(
            chain=chain,
            dex=adapter.dex,
            position_type="v3",
            request={
                "positionId": position_id,
                "tokenId": position_id,
                "collectAsWeth": bool(args.collect_as_weth),
            },
            wallet_address=wallet_address,
            build_calldata=rt._cast_calldata,
        )
        execution = rt.execute_liquidity_plan(
            executor=rt._router_action_executor(),
            plan=plan,
            wallet_address=wallet_address,
            private_key_hex=private_key_hex,
            wait_for_operation_receipts=False,
            liquidity_operation="claim_fees",
        )
        tx_hash = str(execution.tx_hash or "").strip()
        if not tx_hash:
            raise rt.WalletStoreError("liquidity_claim_fees_failed: claim execution returned empty txHash.")
        builder_meta = rt._builder_output_from_hashes(chain, [*execution.approve_tx_hashes, *execution.operation_tx_hashes])
        return rt.ok(
            "Liquidity fees claimed.",
            chain=chain,
            dex=adapter.dex,
            positionId=position_id,
            txHash=tx_hash,
            approveTxHashes=execution.approve_tx_hashes,
            operationTxHashes=execution.operation_tx_hashes,
            providerRequested=provider_requested,
            providerUsed=provider_used,
            fallbackUsed=fallback_used,
            fallbackReason=fallback_reason,
            executionFamily=execution.execution_family,
            executionAdapter=execution.execution_adapter,
            routeKind=execution.route_kind,
            liquidityOperation="claim_fees",
            details={**execution.details, **builder_meta},
            **builder_meta,
        )
    except rt.ChainRegistryError as exc:
        return rt.fail("unsupported_chain_capability", str(exc), rt.chain_supported_hint(), {"chain": chain, "requiredCapability": "liquidity"}, exit_code=2)
    except rt.UnsupportedLiquidityAdapter as exc:
        return rt.fail("unsupported_liquidity_adapter", str(exc), "Choose a supported chain/dex/position-type combination and retry.", _claim_failure_details(), exit_code=2)
    except rt.UnsupportedLiquidityOperation as exc:
        return rt.fail("unsupported_liquidity_operation", str(exc), "Use a chain/dex with concentrated-liquidity fee-claim support.", _claim_failure_details(), exit_code=2)
    except ValueError as exc:
        code = str(exc)
        if code == "chain_config_invalid":
            return rt.fail("chain_config_invalid", "Concentrated-liquidity execution metadata is incomplete for this chain.", "Add execution.liquidity adapter position-manager metadata and retry.", _claim_failure_details(), exit_code=2)
        return rt.fail("liquidity_claim_fees_failed", str(exc), "Verify local router-adapter configuration and retry.", _claim_failure_details(), exit_code=1)
    except rt.WalletStoreError as exc:
        err = str(exc)
        for code in {"claim_fees_not_supported_for_protocol", "unsupported_liquidity_operation", "no_execution_provider_available"}:
            if err.startswith(f"{code}:"):
                return rt.fail(code, err.split(":", 1)[1].strip(), "Verify chain claim-fees support and retry.", _claim_failure_details(), exit_code=1)
        return rt.fail("liquidity_claim_fees_failed", str(exc), "Verify local router-adapter configuration and retry.", _claim_failure_details(), exit_code=1)
    except Exception as exc:
        return rt.fail("liquidity_claim_fees_failed", str(exc), "Inspect runtime liquidity fee-claim path and retry.", _claim_failure_details(), exit_code=1)

def cmd_liquidity_migrate_impl(rt: LiquidityRuntimeAdapter, args: argparse.Namespace) -> int:
    chk = rt.require_json_flag(args)
    if chk is not None:
        return chk
    chain = str(args.chain or "").strip()
    dex = str(args.dex or "").strip().lower()
    position_id = str(args.position_id or "").strip()
    from_protocol = str(args.from_protocol or "").strip().upper()
    to_protocol = str(args.to_protocol or "").strip().upper()
    try:
        rt.assert_chain_capability(chain, "liquidity")
        if not position_id:
            return rt.fail("invalid_input", "position-id is required.", "Provide --position-id and retry.", {"chain": chain}, exit_code=2)
        if from_protocol not in {"V2", "V3", "V4"} or to_protocol not in {"V2", "V3", "V4"}:
            return rt.fail(
                "invalid_input",
                "from-protocol and to-protocol must be one of V2|V3|V4.",
                "Provide valid protocol versions and retry.",
                {"fromProtocol": from_protocol, "toProtocol": to_protocol},
                exit_code=2,
            )
        slippage_bps = int(args.slippage_bps)
        if slippage_bps < 0 or slippage_bps > 5000:
            return rt.fail("invalid_input", "slippage-bps must be between 0 and 5000.", "Use integer bps in range.", {"slippageBps": args.slippage_bps}, exit_code=2)
        provider_requested, _ = rt._liquidity_provider_settings(chain)
        fallback_used = False
        fallback_reason: dict[str, str] | None = None
        adapter = rt.build_liquidity_adapter_for_request(chain=chain, dex=dex, position_type="v3")
        if adapter.protocol_family not in {"position_manager_v3", "local_clmm", "raydium_clmm"}:
            return rt.fail(
                "unsupported_liquidity_execution_family",
                f"Liquidity migrate requires a concentrated-liquidity execution adapter, got '{adapter.protocol_family}'.",
                "Use a chain/dex with advanced concentrated-liquidity support and retry.",
                {"chain": chain, "dex": dex, "positionId": position_id},
                exit_code=2,
            )
        if not adapter.supports_operation("migrate"):
            return rt.fail(
                "unsupported_liquidity_operation",
                f"Adapter '{adapter.dex}' does not support migrate on chain '{chain}'.",
                "Choose a supported chain/dex combination and retry.",
                {"chain": chain, "dex": adapter.dex, "positionId": position_id},
                exit_code=2,
            )

        request_json = str(args.request_json or "").strip()
        request_payload: dict[str, Any] = {}
        if request_json:
            extra = json.loads(request_json)
            if not isinstance(extra, dict):
                raise rt.WalletStoreError("request-json must decode to an object.")
            request_payload.update(extra)

        if rt._is_solana_chain(chain) and adapter.protocol_family in {"local_clmm", "raydium_clmm"}:
            store = rt.load_wallet_store()
            wallet_address, secret = rt._execution_wallet_solana_secret(store, chain)
            target_adapter_key = str(
                request_payload.get("targetAdapterKey")
                or ((adapter.operations or {}).get("migrate") or {}).get("targetAdapterKey")
                or ""
            ).strip()
            if not target_adapter_key:
                return rt.fail(
                    "migration_target_not_configured",
                    "Migration target adapter is not configured for this chain/dex.",
                    "Add execution.liquidity adapter migrate target metadata and retry.",
                    {"chain": chain, "dex": dex, "positionId": position_id},
                    exit_code=2,
                )
            if adapter.protocol_family == "local_clmm":
                if chain != "solana_localnet":
                    return rt.fail(
                        "unsupported_liquidity_adapter",
                        "local_clmm adapter is only supported on solana_localnet.",
                        "Switch to solana_localnet or use raydium_clmm.",
                        {"chain": chain, "dex": dex, "positionId": position_id},
                        exit_code=2,
                    )
                migrated = rt.solana_local_migrate_position(
                    chain=chain,
                    dex=adapter.dex,
                    owner=wallet_address,
                    position_id=position_id,
                    target_dex=target_adapter_key,
                    recreate=bool(request_payload.get("targetRecreate")),
                )
                tx_hash = str(migrated.get("txHash") or "").strip()
                route_kind = "migration" if str(migrated.get("migrationMode") or "") == "recreate" else "position_manager"
                details = {
                    "targetAdapterKey": target_adapter_key,
                    "approveTxHashes": [],
                    "operationTxHashes": [tx_hash] if tx_hash else [],
                    "routeKind": route_kind,
                    "simulationMode": True,
                    **migrated,
                }
                return rt.ok(
                    "Liquidity position migrated.",
                    chain=chain,
                    dex=adapter.dex,
                    positionId=position_id,
                    txHash=tx_hash,
                    approveTxHashes=[],
                    operationTxHashes=[tx_hash] if tx_hash else [],
                    providerRequested=provider_requested,
                    providerUsed="router_adapter",
                    fallbackUsed=fallback_used,
                    fallbackReason=fallback_reason,
                    executionFamily="solana_clmm",
                    executionAdapter=adapter.dex,
                    routeKind=route_kind,
                    liquidityOperation="migrate",
                    fromProtocol=from_protocol,
                    toProtocol=to_protocol,
                    details=details,
                )
            pool_id = rt._resolve_raydium_pool_id(adapter, str(request_payload.get("poolId") or ""))
            if not pool_id:
                return rt.fail(
                    "invalid_input",
                    "Raydium migrate requires configured pool metadata.",
                    "Provide pool metadata in chain config or include a single default pool.",
                    {"chain": chain, "dex": dex, "positionId": position_id},
                    exit_code=2,
                )
            execution = rt.solana_raydium_execute_instruction(
                chain=chain,
                rpc_url=rt._chain_rpc_url(chain),
                private_key_bytes=secret,
                owner=wallet_address,
                adapter_metadata=dict(adapter.adapter_metadata or {}),
                request={
                    "poolId": pool_id,
                    "positionId": position_id,
                    "tokenId": position_id,
                    "targetAdapterKey": target_adapter_key,
                    "targetRecreate": bool(request_payload.get("targetRecreate")),
                    **request_payload,
                },
                operation_key="migrate",
            )
            tx_hash = str(execution.tx_hash or "")
            return rt.ok(
                "Liquidity position migrated.",
                chain=chain,
                dex=adapter.dex,
                positionId=position_id,
                txHash=tx_hash,
                approveTxHashes=[],
                operationTxHashes=[tx_hash] if tx_hash else [],
                providerRequested=provider_requested,
                providerUsed="router_adapter",
                fallbackUsed=fallback_used,
                fallbackReason=fallback_reason,
                executionFamily="solana_clmm",
                executionAdapter=adapter.dex,
                routeKind=execution.route_kind,
                liquidityOperation="migrate",
                fromProtocol=from_protocol,
                toProtocol=to_protocol,
                details={
                    "poolId": pool_id,
                    "targetAdapterKey": target_adapter_key,
                    "approveTxHashes": [],
                    "operationTxHashes": [tx_hash] if tx_hash else [],
                    **execution.details,
                },
            )

        store = rt.load_wallet_store()
        wallet_address, private_key_hex = rt._execution_wallet(store, chain)
        position_snapshot = rt._read_v3_position_snapshot(chain, adapter.position_manager, position_id)
        liquidity_total = int(position_snapshot.get("liquidityUnits") or 0)
        if liquidity_total <= 0:
            return rt.fail(
                "liquidity_preflight_zero_position_liquidity",
                "Position has no removable concentrated liquidity for migration.",
                "Choose a position with non-zero liquidity and retry.",
                {"chain": chain, "dex": dex, "positionId": position_id, "liquidityTotal": str(liquidity_total)},
                exit_code=1,
            )
        deadline = str(int(datetime.now(timezone.utc).timestamp()) + 120)
        request_payload: dict[str, Any] = {
            "positionId": position_id,
            "tokenId": position_id,
            "inputProtocol": from_protocol,
            "outputProtocol": to_protocol,
            "slippageTolerance": slippage_bps,
            "liquidityUnits": str(liquidity_total),
            "minAmountAUnits": "0",
            "minAmountBUnits": "0",
            "deadline": deadline,
        }
        if request_json:
            extra = json.loads(request_json)
            if not isinstance(extra, dict):
                raise rt.WalletStoreError("request-json must decode to an object.")
            request_payload.update(extra)
        migrate_cfg = dict((adapter.operations or {}).get("migrate") or {})
        target_adapter_key = str(request_payload.get("targetAdapterKey") or migrate_cfg.get("targetAdapterKey") or "").strip()
        if target_adapter_key:
            request_payload["targetAdapterKey"] = target_adapter_key
            try:
                target_adapter = rt.build_liquidity_adapter_for_request(chain=chain, dex=target_adapter_key, position_type="v3")
                request_payload["targetPositionManager"] = str(target_adapter.position_manager or "").strip()
                target_ops = dict(target_adapter.operations or {})
                target_add = dict(target_ops.get("add") or {})
                if target_add:
                    request_payload["targetAddMethod"] = str(target_add.get("method") or "mint").strip() or "mint"
            except Exception:
                pass
        plan = rt.build_liquidity_migrate_plan(
            chain=chain,
            dex=adapter.dex,
            position_type="v3",
            request=request_payload,
            wallet_address=wallet_address,
            build_calldata=rt._cast_calldata,
        )
        execution = rt.execute_liquidity_plan(
            executor=rt._router_action_executor(),
            plan=plan,
            wallet_address=wallet_address,
            private_key_hex=private_key_hex,
            wait_for_operation_receipts=False,
            liquidity_operation="migrate",
        )
        tx_hash = str(execution.tx_hash or "")
        builder_meta = rt._builder_output_from_hashes(chain, [*execution.approve_tx_hashes, *execution.operation_tx_hashes])
        return rt.ok(
            "Liquidity position migrated.",
            chain=chain,
            dex=adapter.dex,
            positionId=position_id,
            txHash=tx_hash,
            approveTxHashes=execution.approve_tx_hashes,
            operationTxHashes=execution.operation_tx_hashes,
            providerRequested=provider_requested,
            providerUsed="router_adapter",
            fallbackUsed=fallback_used,
            fallbackReason=fallback_reason,
            executionFamily=execution.execution_family,
            executionAdapter=execution.execution_adapter,
            routeKind=execution.route_kind,
            liquidityOperation="migrate",
            fromProtocol=from_protocol,
            toProtocol=to_protocol,
            details={**execution.details, **builder_meta},
            **builder_meta,
        )
    except rt.ChainRegistryError as exc:
        return rt.fail("unsupported_chain_capability", str(exc), rt.chain_supported_hint(), {"chain": chain, "requiredCapability": "liquidity"}, exit_code=2)
    except rt.UnsupportedLiquidityAdapter as exc:
        return rt.fail("unsupported_liquidity_adapter", str(exc), "Choose a supported chain/dex/position-type combination and retry.", {"chain": chain, "dex": dex, "positionId": position_id}, exit_code=2)
    except rt.UnsupportedLiquidityOperation as exc:
        return rt.fail("unsupported_liquidity_operation", str(exc), "Use a chain/dex with concentrated-liquidity migrate support.", {"chain": chain, "dex": dex, "positionId": position_id}, exit_code=2)
    except ValueError as exc:
        code = str(exc)
        if code == "chain_config_invalid":
            return rt.fail("chain_config_invalid", "Concentrated-liquidity execution metadata is incomplete for this chain.", "Add execution.liquidity adapter position-manager metadata and retry.", {"chain": chain, "dex": dex, "positionId": position_id}, exit_code=2)
        if code == "migration_target_not_configured":
            return rt.fail("migration_target_not_configured", "Migration target adapter is not configured for this chain/dex.", "Add execution.liquidity adapter migrate target metadata and retry.", {"chain": chain, "dex": dex, "positionId": position_id}, exit_code=2)
        return rt.fail("liquidity_migrate_failed", str(exc), "Verify local router-adapter migrate configuration and retry.", {"chain": chain, "dex": dex, "positionId": position_id}, exit_code=1)
    except rt.WalletStoreError as exc:
        return rt.fail("liquidity_migrate_failed", str(exc), "Verify local router-adapter migrate configuration and retry.", {"chain": chain, "dex": dex, "positionId": position_id}, exit_code=1)
    except Exception as exc:
        return rt.fail("liquidity_migrate_failed", str(exc), "Inspect runtime liquidity migrate path and retry.", {"chain": chain, "dex": dex, "positionId": position_id}, exit_code=1)

def cmd_liquidity_claim_rewards_impl(rt: LiquidityRuntimeAdapter, args: argparse.Namespace) -> int:
    chk = rt.require_json_flag(args)
    if chk is not None:
        return chk
    chain = str(args.chain or "").strip()
    dex = str(args.dex or "").strip().lower()
    position_id = str(args.position_id or "").strip()
    provider_requested = "router_adapter"
    provider_used = "router_adapter"
    fallback_used = False
    fallback_reason: dict[str, str] | None = None

    def _claim_failure_details() -> dict[str, Any]:
        details: dict[str, Any] = {
            "chain": chain,
            "dex": dex,
            "positionId": position_id,
            "operation": "claim_rewards",
            "providerRequested": provider_requested,
            "fallbackUsed": bool(fallback_used),
            "fallbackReason": fallback_reason,
        }
        if provider_used:
            details["providerUsed"] = provider_used
        return details

    try:
        rt.assert_chain_capability(chain, "liquidity")
        if not position_id:
            return rt.fail("invalid_input", "position-id is required.", "Provide --position-id and retry.", _claim_failure_details(), exit_code=2)
        provider_requested, _ = rt._liquidity_provider_settings(chain)
        fallback_used = False
        fallback_reason = None
        adapter = rt.build_liquidity_adapter_for_request(chain=chain, dex=dex, position_type="v3")
        if adapter.protocol_family not in {"position_manager_v3", "local_clmm", "raydium_clmm"}:
            return rt.fail(
                "unsupported_liquidity_execution_family",
                f"Liquidity claim-rewards requires a concentrated-liquidity execution adapter, got '{adapter.protocol_family}'.",
                "Use a chain/dex with advanced concentrated-liquidity support and retry.",
                _claim_failure_details(),
                exit_code=2,
            )
        if not adapter.supports_operation("claim_rewards"):
            return rt.fail(
                "unsupported_liquidity_operation",
                f"Adapter '{adapter.dex}' does not support claim-rewards on chain '{chain}'.",
                "Choose a supported chain/dex combination and retry.",
                _claim_failure_details(),
                exit_code=2,
            )
        request_payload: dict[str, Any] = {"positionId": position_id}
        reward_token = str(args.reward_token or "").strip()
        if reward_token:
            request_payload["tokens"] = [rt._resolve_token_address(chain, reward_token)]
        request_json = str(args.request_json or "").strip()
        if request_json:
            extra = json.loads(request_json)
            if not isinstance(extra, dict):
                raise rt.WalletStoreError("request-json must decode to an object.")
            request_payload.update(extra)

        if rt._is_solana_chain(chain) and adapter.protocol_family in {"local_clmm", "raydium_clmm"}:
            reward_contracts: list[str] = []
            reward_cfg = ((adapter.operations or {}).get("claimRewards") or {}) if isinstance(adapter.operations, dict) else {}
            configured_rewards = reward_cfg.get("rewardContracts") if isinstance(reward_cfg, dict) else None
            if isinstance(configured_rewards, list):
                reward_contracts = [str(item or "").strip() for item in configured_rewards if str(item or "").strip()]
            if reward_token:
                reward_contracts = [str(rt._resolve_token_address(chain, reward_token))]
            if not reward_contracts:
                return rt.fail(
                    "claim_rewards_not_configured",
                    "Reward contracts are not configured for this chain/dex.",
                    "Add execution.liquidity adapter claimRewards.rewardContracts and retry.",
                    _claim_failure_details(),
                    exit_code=1,
                )
            store = rt.load_wallet_store()
            wallet_address, secret = rt._execution_wallet_solana_secret(store, chain)
            if adapter.protocol_family == "local_clmm":
                if chain != "solana_localnet":
                    return rt.fail(
                        "unsupported_liquidity_adapter",
                        "local_clmm adapter is only supported on solana_localnet.",
                        "Switch to solana_localnet or use raydium_clmm.",
                        _claim_failure_details(),
                        exit_code=2,
                    )
                claimed = rt.solana_local_claim_rewards(
                    chain=chain,
                    dex=adapter.dex,
                    owner=wallet_address,
                    position_id=position_id,
                    reward_contracts=reward_contracts,
                )
                tx_hash = str(claimed.get("txHash") or "").strip()
                details = {
                    "rewardContracts": reward_contracts,
                    "approveTxHashes": [],
                    "operationTxHashes": [tx_hash] if tx_hash else [],
                    "routeKind": "reward_claim",
                    "simulationMode": True,
                    **claimed,
                }
                return rt.ok(
                    "Liquidity rewards claimed.",
                    chain=chain,
                    dex=adapter.dex,
                    positionId=position_id,
                    txHash=tx_hash,
                    approveTxHashes=[],
                    operationTxHashes=[tx_hash] if tx_hash else [],
                    providerRequested=provider_requested,
                    providerUsed=provider_used,
                    fallbackUsed=fallback_used,
                    fallbackReason=fallback_reason,
                    executionFamily="solana_clmm",
                    executionAdapter=adapter.dex,
                    routeKind="reward_claim",
                    liquidityOperation="claim_rewards",
                    details=details,
                )
            pool_id = rt._resolve_raydium_pool_id(adapter, "")
            if not pool_id:
                return rt.fail(
                    "invalid_input",
                    "Raydium claim-rewards requires configured pool metadata.",
                    "Provide pool metadata in chain config or include a single default pool.",
                    _claim_failure_details(),
                    exit_code=2,
                )
            execution = rt.solana_raydium_execute_instruction(
                chain=chain,
                rpc_url=rt._chain_rpc_url(chain),
                private_key_bytes=secret,
                owner=wallet_address,
                adapter_metadata=dict(adapter.adapter_metadata or {}),
                request={
                    "poolId": pool_id,
                    "positionId": position_id,
                    "tokenId": position_id,
                    "rewardContracts": reward_contracts,
                },
                operation_key="claim_rewards",
            )
            tx_hash = str(execution.tx_hash or "").strip()
            details = {
                "poolId": pool_id,
                "rewardContracts": reward_contracts,
                "approveTxHashes": [],
                "operationTxHashes": [tx_hash] if tx_hash else [],
                **execution.details,
            }
            return rt.ok(
                "Liquidity rewards claimed.",
                chain=chain,
                dex=adapter.dex,
                positionId=position_id,
                txHash=tx_hash,
                approveTxHashes=[],
                operationTxHashes=[tx_hash] if tx_hash else [],
                providerRequested=provider_requested,
                providerUsed=provider_used,
                fallbackUsed=fallback_used,
                fallbackReason=fallback_reason,
                executionFamily="solana_clmm",
                executionAdapter=adapter.dex,
                routeKind=execution.route_kind,
                liquidityOperation="claim_rewards",
                details=details,
            )

        store = rt.load_wallet_store()
        wallet_address, private_key_hex = rt._execution_wallet(store, chain)
        plan = rt.build_liquidity_claim_rewards_plan(
            chain=chain,
            dex=adapter.dex,
            position_type="v3",
            request=request_payload,
            wallet_address=wallet_address,
            build_calldata=rt._cast_calldata,
        )
        execution = rt.execute_liquidity_plan(
            executor=rt._router_action_executor(),
            plan=plan,
            wallet_address=wallet_address,
            private_key_hex=private_key_hex,
            wait_for_operation_receipts=False,
            liquidity_operation="claim_rewards",
        )
        tx_hash = str(execution.tx_hash or "").strip()
        if not tx_hash:
            raise rt.WalletStoreError("liquidity_claim_rewards_failed: claim execution returned empty txHash.")
        builder_meta = rt._builder_output_from_hashes(chain, [*execution.approve_tx_hashes, *execution.operation_tx_hashes])
        return rt.ok(
            "Liquidity rewards claimed.",
            chain=chain,
            dex=adapter.dex,
            positionId=position_id,
            txHash=tx_hash,
            approveTxHashes=execution.approve_tx_hashes,
            operationTxHashes=execution.operation_tx_hashes,
            providerRequested=provider_requested,
            providerUsed=provider_used,
            fallbackUsed=fallback_used,
            fallbackReason=fallback_reason,
            executionFamily=execution.execution_family,
            executionAdapter=execution.execution_adapter,
            routeKind=execution.route_kind,
            liquidityOperation="claim_rewards",
            details={**execution.details, **builder_meta},
            **builder_meta,
        )
    except rt.ChainRegistryError as exc:
        return rt.fail("unsupported_chain_capability", str(exc), rt.chain_supported_hint(), {"chain": chain, "requiredCapability": "liquidity"}, exit_code=2)
    except rt.UnsupportedLiquidityAdapter as exc:
        return rt.fail("unsupported_liquidity_adapter", str(exc), "Choose a supported chain/dex/position-type combination and retry.", _claim_failure_details(), exit_code=2)
    except rt.UnsupportedLiquidityOperation as exc:
        return rt.fail("unsupported_liquidity_operation", str(exc), "Use a chain/dex with concentrated-liquidity rewards-claim support.", _claim_failure_details(), exit_code=2)
    except ValueError as exc:
        code = str(exc)
        if code == "chain_config_invalid":
            return rt.fail("chain_config_invalid", "Concentrated-liquidity execution metadata is incomplete for this chain.", "Add execution.liquidity adapter position-manager metadata and retry.", _claim_failure_details(), exit_code=2)
        if code == "claim_rewards_not_configured":
            return rt.fail("claim_rewards_not_configured", "Reward contracts are not configured for this chain/dex.", "Add execution.liquidity adapter claimRewards.rewardContracts and retry.", _claim_failure_details(), exit_code=1)
        return rt.fail("liquidity_claim_rewards_failed", str(exc), "Verify local router-adapter claim-rewards configuration and retry.", _claim_failure_details(), exit_code=1)
    except rt.WalletStoreError as exc:
        err = str(exc)
        for code in {"claim_rewards_not_configured", "claim_rewards_not_supported_for_protocol", "unsupported_liquidity_operation", "no_execution_provider_available"}:
            if err.startswith(f"{code}:"):
                return rt.fail(code, err.split(":", 1)[1].strip(), "Verify chain claim-rewards support and retry.", _claim_failure_details(), exit_code=1)
        return rt.fail("liquidity_claim_rewards_failed", str(exc), "Verify local router-adapter claim-rewards configuration and retry.", _claim_failure_details(), exit_code=1)
    except Exception as exc:
        return rt.fail("liquidity_claim_rewards_failed", str(exc), "Inspect runtime liquidity claim-rewards path and retry.", _claim_failure_details(), exit_code=1)

def _invoke_liquidity_command_payload_impl(rt: LiquidityRuntimeAdapter, command: Callable[[argparse.Namespace], int], args: argparse.Namespace) -> dict[str, Any]:
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = command(args)
    raw = buf.getvalue().strip()
    payload: dict[str, Any] = {}
    if raw:
        try:
            decoded = json.loads(raw)
            if isinstance(decoded, dict):
                payload = decoded
        except Exception:
            payload = {"ok": False, "code": "liquidity_execute_parse_failed", "message": raw[:400]}
    if code != 0:
        error_code = str(payload.get("code") or "liquidity_execution_failed")
        error_message = str(payload.get("message") or "Advanced liquidity command failed.")
        raise rt.WalletStoreError(f"{error_code}: {error_message}")
    return payload

def _execute_liquidity_advanced_intent_impl(rt: LiquidityRuntimeAdapter, intent: dict[str, Any], chain: str, action: str) -> tuple[dict[str, Any], str]:
    dex = str(intent.get("dex") or "").strip().lower()
    adapter = rt.build_liquidity_adapter_for_request(chain=chain, dex=dex, position_type="v3")
    details = rt._intent_details_dict(intent)
    v3_details = rt._v3_details_dict(details)
    position_id = str(intent.get("positionId") or intent.get("positionRef") or "").strip()
    slippage_bps = int(intent.get("slippageBps") or details.get("slippageBps") or 100)

    if action == "increase":
        args = argparse.Namespace(
            chain=chain,
            dex=dex,
            position_id=position_id,
            token_a=str(intent.get("tokenA") or v3_details.get("tokenA") or ""),
            token_b=str(intent.get("tokenB") or v3_details.get("tokenB") or ""),
            amount_a=str(intent.get("amountA") or v3_details.get("amountA") or ""),
            amount_b=str(intent.get("amountB") or v3_details.get("amountB") or ""),
            slippage_bps=slippage_bps,
            json=True,
        )
        payload = _invoke_liquidity_command_payload_impl(rt, rt.cmd_liquidity_increase, args)
        return payload, adapter.protocol_family

    if action in {"claim_fees", "claim-fees"}:
        args = argparse.Namespace(
            chain=chain,
            dex=dex,
            position_id=position_id,
            collect_as_weth=bool(details.get("collectAsWeth") or False),
            json=True,
        )
        payload = _invoke_liquidity_command_payload_impl(rt, rt.cmd_liquidity_claim_fees, args)
        return payload, adapter.protocol_family

    if action in {"claim_rewards", "claim-rewards"}:
        args = argparse.Namespace(
            chain=chain,
            dex=dex,
            position_id=position_id,
            reward_token=str(details.get("rewardToken") or ""),
            request_json=json.dumps(details.get("request") or {}) if isinstance(details.get("request"), dict) else None,
            json=True,
        )
        payload = _invoke_liquidity_command_payload_impl(rt, rt.cmd_liquidity_claim_rewards, args)
        return payload, adapter.protocol_family

    if action == "migrate":
        args = argparse.Namespace(
            chain=chain,
            dex=dex,
            position_id=position_id,
            from_protocol=str(details.get("fromProtocol") or "V3"),
            to_protocol=str(details.get("toProtocol") or "V3"),
            slippage_bps=slippage_bps,
            request_json=json.dumps(details.get("request") or {}) if isinstance(details.get("request"), dict) else None,
            json=True,
        )
        payload = _invoke_liquidity_command_payload_impl(rt, rt.cmd_liquidity_migrate, args)
        return payload, adapter.protocol_family

    raise rt.WalletStoreError(f"Unsupported liquidity action '{action}'.")

def _run_liquidity_execute_inline_impl(rt: LiquidityRuntimeAdapter, liquidity_intent_id: str, chain: str) -> tuple[int, dict[str, Any]]:
    nested = argparse.Namespace(intent=liquidity_intent_id, chain=chain, json=True)
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = rt.cmd_liquidity_execute(nested)
    raw = buf.getvalue().strip()
    payload: dict[str, Any] = {
        "ok": bool(code == 0),
        "code": "liquidity_execute_result_unavailable",
        "message": "Liquidity execute result unavailable.",
        "liquidityIntentId": liquidity_intent_id,
        "chain": chain,
    }
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                payload = parsed
        except Exception:
            payload = {
                "ok": False,
                "code": "liquidity_execute_parse_failed",
                "message": raw[:400],
                "liquidityIntentId": liquidity_intent_id,
                "chain": chain,
            }
    return code, payload

def cmd_liquidity_execute_impl(rt: LiquidityRuntimeAdapter, args: argparse.Namespace) -> int:
    chk = rt.require_json_flag(args)
    if chk is not None:
        return chk
    liquidity_intent_id = str(args.intent or "").strip()
    chain = str(args.chain or "").strip()
    if not liquidity_intent_id:
        return rt.fail("invalid_input", "intent is required.", "Provide --intent liq_... and retry.", exit_code=2)
    if not chain:
        return rt.fail("invalid_input", "chain is required.", "Provide --chain <chainKey> and retry.", {"liquidityIntentId": liquidity_intent_id}, exit_code=2)

    transition_state = "init"
    last_tx_hash: str | None = None
    provider_requested = rt._liquidity_provider_settings(chain)[0]
    provider_used = "router_adapter"
    fallback_used = False
    fallback_reason: dict[str, str] | None = None
    try:
        intent = rt._read_liquidity_intent(liquidity_intent_id, chain)
        status = str(intent.get("status") or "").strip().lower()
        action = str(intent.get("action") or "").strip().lower()
        dex = str(intent.get("dex") or "").strip().lower()
        position_type = str(intent.get("positionType") or "v2").strip().lower()
        if status != "approved":
            return rt.fail(
                "liquidity_not_actionable",
                f"Liquidity intent is not actionable from status '{status}'.",
                "Execute only approved liquidity intents in this slice.",
                {"liquidityIntentId": liquidity_intent_id, "chain": chain, "status": status},
                exit_code=1,
            )

        execution: dict[str, Any]
        adapter_family = "unknown"

        def _execute_local() -> tuple[dict[str, Any], str]:
            adapter = rt.build_liquidity_adapter_for_request(chain=chain, dex=dex, position_type=position_type)
            if action == "add":
                if adapter.protocol_family == "amm_v2":
                    return rt._execute_liquidity_v2_add(intent, chain), adapter.protocol_family
                if adapter.protocol_family in {"position_manager_v3", "local_clmm", "raydium_clmm"}:
                    return rt._execute_liquidity_v3_add(intent, chain), adapter.protocol_family
                raise rt.WalletStoreError(
                    f"unsupported_liquidity_execution_family: Liquidity intent add requires supported local execution family, got '{adapter.protocol_family}'."
                )
            if action == "remove":
                if adapter.protocol_family == "amm_v2":
                    return rt._execute_liquidity_v2_remove(intent, chain), adapter.protocol_family
                if adapter.protocol_family in {"position_manager_v3", "local_clmm", "raydium_clmm"}:
                    return rt._execute_liquidity_v3_remove(intent, chain), adapter.protocol_family
                raise rt.WalletStoreError(
                    f"unsupported_liquidity_execution_family: Liquidity intent remove requires supported local execution family, got '{adapter.protocol_family}'."
                )
            if action in {"increase", "claim_fees", "claim-fees", "claim_rewards", "claim-rewards", "migrate"}:
                return rt._execute_liquidity_advanced_intent(intent, chain, action)
            raise rt.WalletStoreError(f"Unsupported liquidity action '{action}'.")

        rt._post_liquidity_status(liquidity_intent_id, "executing")
        transition_state = "executing"

        execution, adapter_family = _execute_local()
        provider_used = "router_adapter"

        tx_hash = str(execution.get("txHash") or "").strip()
        if not tx_hash:
            raise rt.WalletStoreError("Liquidity execution did not return txHash.")
        last_tx_hash = tx_hash
        liquidity_operation = str(execution.get("liquidityOperation") or action).strip().lower() or None
        provider_meta = rt._build_liquidity_provider_meta(
            provider_requested=provider_requested,
            provider_used=provider_used,
            fallback_used=fallback_used,
            fallback_reason=fallback_reason,
            liquidity_operation=liquidity_operation,
        )
        status_details = execution.get("details") if isinstance(execution.get("details"), dict) else {}
        if execution.get("executionFamily"):
            status_details["executionFamily"] = execution.get("executionFamily")
        if execution.get("executionAdapter"):
            status_details["executionAdapter"] = execution.get("executionAdapter")
        if execution.get("routeKind"):
            status_details["routeKind"] = execution.get("routeKind")
        builder_hashes: list[str | None] = [tx_hash]
        approve_hashes = status_details.get("approveTxHashes")
        if isinstance(approve_hashes, list):
            builder_hashes.extend([str(item or "").strip() for item in approve_hashes if str(item or "").strip()])
        operation_hashes = status_details.get("operationTxHashes")
        if isinstance(operation_hashes, list):
            builder_hashes.extend([str(item or "").strip() for item in operation_hashes if str(item or "").strip()])
        builder_meta = rt._builder_output_from_hashes(chain, builder_hashes)
        status_details = {**status_details, **builder_meta}
        status_details = {**status_details, **provider_meta}

        rt._post_liquidity_status(
            liquidity_intent_id,
            "verifying",
            {
                "txHash": tx_hash,
                "positionId": execution.get("positionId"),
                "details": status_details,
            },
        )
        transition_state = "verifying"

        if adapter_family in {"amm_v2", "position_manager_v3"}:
            rt._wait_for_tx_receipt_success(chain, tx_hash)

        rt._post_liquidity_status(
            liquidity_intent_id,
            "filled",
            {
                "txHash": tx_hash,
                "positionId": execution.get("positionId"),
                "details": status_details,
            },
        )
        return rt.ok(
            "Liquidity intent executed.",
            liquidityIntentId=liquidity_intent_id,
            chain=chain,
            dex=dex,
            action=action,
            positionType=position_type,
            adapterFamily=adapter_family,
            status="filled",
            txHash=tx_hash,
            positionId=execution.get("positionId"),
            details=status_details,
            providerRequested=provider_requested,
            providerUsed=provider_used,
            fallbackUsed=fallback_used,
            fallbackReason=fallback_reason,
            liquidityOperation=liquidity_operation,
            **builder_meta,
        )
    except rt.SubprocessTimeout as exc:
        if transition_state == "verifying":
            try:
                rt._post_liquidity_status(
                    liquidity_intent_id,
                    "verification_timeout",
                    {"reasonCode": "verification_timeout", "reasonMessage": str(exc), "txHash": last_tx_hash},
                )
            except Exception:
                pass
        return rt.fail(
            "liquidity_verification_failed",
            str(exc),
            "Receipt timed out; inspect explorer and retry if needed.",
            {"liquidityIntentId": liquidity_intent_id, "chain": chain, "txHash": last_tx_hash},
            exit_code=1,
        )
    except rt.LiquidityExecutionError as exc:
        reason_code = str(exc.reason_code or "liquidity_execution_failed")
        failure_details = exc.details if isinstance(getattr(exc, "details", None), dict) else {}
        if transition_state in {"executing", "verifying"}:
            try:
                rt._post_liquidity_status(
                    liquidity_intent_id,
                    "failed",
                    {
                        "reasonCode": reason_code,
                        "reasonMessage": str(exc),
                        "txHash": last_tx_hash,
                        "details": failure_details if failure_details else None,
                    },
                )
            except Exception:
                pass
        return rt.fail(
            "liquidity_execution_failed",
            str(exc),
            "Verify intent payload, wallet balances, pair liquidity, and chain contracts, then retry.",
            {
                "liquidityIntentId": liquidity_intent_id,
                "chain": chain,
                "txHash": last_tx_hash,
                "reasonCode": reason_code,
                "preflight": failure_details if failure_details else None,
            },
            exit_code=1,
        )
    except (rt.LiquidityAdapterError, rt.WalletStoreError) as exc:
        err_text = str(exc)
        if err_text.startswith("invalid_input:"):
            return rt.fail(
                "invalid_input",
                err_text.split(":", 1)[1].strip(),
                "Update intent payload and retry.",
                {"liquidityIntentId": liquidity_intent_id, "chain": chain, "txHash": last_tx_hash},
                exit_code=2,
            )
        if err_text.startswith("unsupported_liquidity_execution_family:"):
            return rt.fail(
                "unsupported_liquidity_execution_family",
                err_text.split(":", 1)[1].strip(),
                "Use a supported liquidity execution family and retry.",
                {"liquidityIntentId": liquidity_intent_id, "chain": chain, "txHash": last_tx_hash},
                exit_code=2,
            )
        if err_text.startswith("unsupported_liquidity_operation"):
            return rt.fail(
                "unsupported_liquidity_operation",
                "Requested liquidity operation is not supported by the resolved adapter.",
                "Use a chain/dex with matching operation capability and retry.",
                {"liquidityIntentId": liquidity_intent_id, "chain": chain, "txHash": last_tx_hash},
                exit_code=2,
            )
        if transition_state in {"executing", "verifying"}:
            fail_status = "failed" if transition_state == "executing" else "failed"
            try:
                rt._post_liquidity_status(liquidity_intent_id, fail_status, {"reasonCode": "liquidity_execution_failed", "reasonMessage": err_text, "txHash": last_tx_hash})
            except Exception:
                pass
        return rt.fail(
            "liquidity_execution_failed",
            err_text,
            "Verify intent payload, wallet configuration, and chain contracts, then retry.",
            {"liquidityIntentId": liquidity_intent_id, "chain": chain, "txHash": last_tx_hash},
            exit_code=1,
        )
    except Exception as exc:
        if transition_state in {"executing", "verifying"}:
            try:
                rt._post_liquidity_status(liquidity_intent_id, "failed", {"reasonCode": "liquidity_execution_failed", "reasonMessage": str(exc), "txHash": last_tx_hash})
            except Exception:
                pass
        return rt.fail(
            "liquidity_execution_failed",
            str(exc),
            "Inspect runtime liquidity execution path and retry.",
            {"liquidityIntentId": liquidity_intent_id, "chain": chain, "txHash": last_tx_hash},
            exit_code=1,
        )

def cmd_liquidity_resume_impl(rt: LiquidityRuntimeAdapter, args: argparse.Namespace) -> int:
    chk = rt.require_json_flag(args)
    if chk is not None:
        return chk
    liquidity_intent_id = str(args.intent or "").strip()
    chain = str(args.chain or "").strip()
    nested = argparse.Namespace(intent=liquidity_intent_id, chain=chain, json=True)
    return rt.cmd_liquidity_execute(nested)

def cmd_liquidity_positions_impl(rt: LiquidityRuntimeAdapter, args: argparse.Namespace) -> int:
    chk = rt.require_json_flag(args)
    if chk is not None:
        return chk
    chain = str(args.chain or "").strip()
    dex = str(args.dex or "").strip().lower()
    status_filter = str(args.status or "").strip().lower()
    status_aliases = {
        "open": "active",
        "opened": "active",
        "live": "active",
    }
    status_filter = status_aliases.get(status_filter, status_filter)
    try:
        rt.assert_chain_capability(chain, "liquidity")
        agent_id = rt._resolve_agent_id_or_fail(chain)
        status_code, body = rt._api_request(
            "GET",
            f"/liquidity/positions?agentId={urllib.parse.quote(agent_id)}&chainKey={urllib.parse.quote(chain)}",
        )
        if status_code < 200 or status_code >= 300:
            return rt.fail(
                str(body.get("code", "api_error")),
                str(body.get("message", f"liquidity positions request failed ({status_code})")),
                str(body.get("actionHint", "Verify API auth and retry.")),
                rt._api_error_details(status_code, body, "/liquidity/positions", chain=chain),
                exit_code=1,
            )
        items = body.get("items")
        if not isinstance(items, list):
            items = []
        normalized_items: list[dict[str, Any]] = []
        for row in items:
            if not isinstance(row, dict):
                continue
            item = dict(row)
            token_a_raw = str(item.get("tokenA") or "").strip()
            token_b_raw = str(item.get("tokenB") or "").strip()
            token_a = token_a_raw
            token_b = token_b_raw
            if rt._is_placeholder_liquidity_token(token_a_raw) or rt._is_placeholder_liquidity_token(token_b_raw):
                pair_ref = str(item.get("pool") or item.get("poolRef") or item.get("pair") or "").strip()
                if rt.is_hex_address(pair_ref):
                    try:
                        pair_token_a, pair_token_b = rt._resolve_pair_tokens_from_contract(chain, pair_ref)
                        if rt._is_placeholder_liquidity_token(token_a_raw):
                            token_a = pair_token_a
                        if rt._is_placeholder_liquidity_token(token_b_raw):
                            token_b = pair_token_b
                    except Exception:
                        pass
            token_a_symbol = rt._token_symbol_for_display(chain, token_a) or token_a
            token_b_symbol = rt._token_symbol_for_display(chain, token_b) or token_b
            item["tokenA"] = token_a
            item["tokenB"] = token_b
            item["tokenASymbol"] = token_a_symbol
            item["tokenBSymbol"] = token_b_symbol
            item["pairDisplay"] = f"{token_a_symbol}/{token_b_symbol}"
            normalized_items.append(item)
        items = normalized_items
        if dex:
            items = [row for row in items if str((row or {}).get("dex") or "").strip().lower() == dex]
        if status_filter:
            items = [row for row in items if str((row or {}).get("status") or "").strip().lower() == status_filter]
        return rt.ok(
            "Liquidity positions loaded.",
            chain=chain,
            dex=dex or None,
            status=status_filter or None,
            count=len(items),
            positions=items,
        )
    except rt.ChainRegistryError as exc:
        return rt.fail("unsupported_chain_capability", str(exc), rt.chain_supported_hint(), {"chain": chain, "requiredCapability": "liquidity"}, exit_code=2)
    except rt.WalletStoreError as exc:
        return rt.fail("liquidity_positions_failed", str(exc), "Verify API env/auth and retry.", {"chain": chain, "dex": dex}, exit_code=1)
    except Exception as exc:
        return rt.fail("liquidity_positions_failed", str(exc), "Inspect runtime liquidity positions path and retry.", {"chain": chain, "dex": dex}, exit_code=1)


def cmd_liquidity_discover_pairs(rt: LiquidityRuntimeAdapter, args: Any) -> int:
    return cmd_liquidity_discover_pairs_impl(rt, args)


def cmd_liquidity_quote_add(rt: LiquidityRuntimeAdapter, args: Any) -> int:
    return cmd_liquidity_quote_add_impl(rt, args)


def cmd_liquidity_quote_remove(rt: LiquidityRuntimeAdapter, args: Any) -> int:
    return cmd_liquidity_quote_remove_impl(rt, args)


def cmd_liquidity_add(rt: LiquidityRuntimeAdapter, args: Any) -> int:
    return cmd_liquidity_add_impl(rt, args)


def cmd_liquidity_remove(rt: LiquidityRuntimeAdapter, args: Any) -> int:
    return cmd_liquidity_remove_impl(rt, args)


def cmd_liquidity_increase(rt: LiquidityRuntimeAdapter, args: Any) -> int:
    return cmd_liquidity_increase_impl(rt, args)


def cmd_liquidity_claim_fees(rt: LiquidityRuntimeAdapter, args: Any) -> int:
    return cmd_liquidity_claim_fees_impl(rt, args)


def cmd_liquidity_migrate(rt: LiquidityRuntimeAdapter, args: Any) -> int:
    return cmd_liquidity_migrate_impl(rt, args)


def cmd_liquidity_claim_rewards(rt: LiquidityRuntimeAdapter, args: Any) -> int:
    return cmd_liquidity_claim_rewards_impl(rt, args)


def _run_liquidity_execute_inline(rt: LiquidityRuntimeAdapter, liquidity_intent_id: str, chain: str) -> tuple[int, dict[str, Any]]:
    return _run_liquidity_execute_inline_impl(rt, liquidity_intent_id, chain)


def cmd_liquidity_execute(rt: LiquidityRuntimeAdapter, args: Any) -> int:
    return cmd_liquidity_execute_impl(rt, args)


def cmd_liquidity_resume(rt: LiquidityRuntimeAdapter, args: Any) -> int:
    return cmd_liquidity_resume_impl(rt, args)


def cmd_liquidity_positions(rt: LiquidityRuntimeAdapter, args: Any) -> int:
    return cmd_liquidity_positions_impl(rt, args)
