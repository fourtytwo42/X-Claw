from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from xclaw_agent.evm_action_executor import EvmActionExecutor


@dataclass(frozen=True)
class TradeExecutionServiceContext:
    require_cast_bin: Callable[[], str]
    chain_rpc_url: Callable[[str], str]
    run_subprocess: Callable[..., Any]
    cast_receipt_timeout_sec: Callable[[], int]
    json_module: Any
    wallet_store_error: type[BaseException]
    fetch_token_allowance_wei: Callable[[str, str, str, str], str]
    cast_calldata: Callable[..., str]
    cast_rpc_send_transaction: Callable[..., str]
    quote_trade: Callable[..., dict[str, Any]]
    build_trade_plan: Callable[..., Any]
    execute_trade_plan: Callable[..., Any]
    router_get_amount_out: Callable[[str, str, str, str], int]



def wait_for_tx_receipt_success(ctx: TradeExecutionServiceContext, chain: str, tx_hash: str) -> dict[str, Any]:
    cast_bin = ctx.require_cast_bin()
    rpc_url = ctx.chain_rpc_url(chain)
    receipt_proc = ctx.run_subprocess(
        [cast_bin, "receipt", "--json", "--rpc-url", rpc_url, tx_hash],
        timeout_sec=ctx.cast_receipt_timeout_sec(),
        kind="cast_receipt",
    )
    if receipt_proc.returncode != 0:
        stderr = (receipt_proc.stderr or "").strip()
        stdout = (receipt_proc.stdout or "").strip()
        raise ctx.wallet_store_error(stderr or stdout or "cast receipt failed.")
    receipt_payload = ctx.json_module.loads((receipt_proc.stdout or "{}").strip() or "{}")
    receipt_status = str(receipt_payload.get("status", "0x0")).lower()
    if receipt_status not in {"0x1", "1"}:
        raise ctx.wallet_store_error(f"On-chain receipt indicates failure status '{receipt_status}'.")
    return receipt_payload



def ensure_token_allowance(
    ctx: TradeExecutionServiceContext,
    *,
    chain: str,
    token_address: str,
    owner: str,
    spender: str,
    required_units: int,
    private_key_hex: str,
) -> str | None:
    allowance_wei = int(ctx.fetch_token_allowance_wei(chain, token_address, owner, spender))
    if allowance_wei >= required_units:
        return None
    approve_data = ctx.cast_calldata("approve(address,uint256)(bool)", [spender, str(required_units)])
    tx_hash = ctx.cast_rpc_send_transaction(
        ctx.chain_rpc_url(chain),
        {"from": owner, "to": token_address, "data": approve_data},
        private_key_hex,
        chain=chain,
    )
    wait_for_tx_receipt_success(ctx, chain, tx_hash)
    return tx_hash



def router_action_executor(ctx: TradeExecutionServiceContext) -> EvmActionExecutor:
    return EvmActionExecutor(
        ensure_token_allowance=lambda **kwargs: ensure_token_allowance(ctx, **kwargs),
        send_transaction=ctx.cast_rpc_send_transaction,
        wait_for_receipt_success=lambda chain, tx_hash: wait_for_tx_receipt_success(ctx, chain, tx_hash),
        rpc_url_for_chain=ctx.chain_rpc_url,
    )



def quote_trade_via_router_adapter(
    ctx: TradeExecutionServiceContext,
    *,
    chain: str,
    adapter_key: str,
    token_in: str,
    token_out: str,
    amount_in_units: str,
) -> dict[str, Any]:
    return ctx.quote_trade(
        chain=chain,
        adapter_key=adapter_key,
        request={
            "tokenIn": token_in,
            "tokenOut": token_out,
            "amountInUnits": amount_in_units,
        },
        get_amount_out=lambda value, token_a, token_b: ctx.router_get_amount_out(chain, value, token_a, token_b),
    )



def execute_trade_via_router_adapter(
    ctx: TradeExecutionServiceContext,
    *,
    chain: str,
    adapter_key: str,
    wallet_address: str,
    private_key_hex: str,
    token_in: str,
    token_out: str,
    amount_in_units: str,
    min_out_units: str,
    deadline: str,
    recipient: str,
    wait_for_receipt: bool,
) -> dict[str, Any]:
    plan = ctx.build_trade_plan(
        chain=chain,
        adapter_key=adapter_key,
        request={
            "tokenIn": token_in,
            "tokenOut": token_out,
            "amountInUnits": amount_in_units,
            "amountOutMinUnits": min_out_units,
            "recipient": recipient,
            "deadline": deadline,
            "routeKind": "router_path",
        },
        wallet_address=wallet_address,
        build_calldata=ctx.cast_calldata,
    )
    execution = ctx.execute_trade_plan(
        executor=router_action_executor(ctx),
        plan=plan,
        wallet_address=wallet_address,
        private_key_hex=private_key_hex,
        wait_for_operation_receipts=wait_for_receipt,
    )
    return {
        "txHash": execution.tx_hash,
        "approveTxHashes": execution.approve_tx_hashes,
        "operationTxHashes": execution.operation_tx_hashes,
        "executionFamily": execution.execution_family,
        "executionAdapter": execution.execution_adapter,
        "routeKind": execution.route_kind,
    }
