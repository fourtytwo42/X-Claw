from __future__ import annotations

from typing import Any, Callable

from xclaw_agent.execution_contracts import EvmActionPlan, EvmExecutionResult


class EvmActionExecutor:
    def __init__(
        self,
        *,
        ensure_token_allowance: Callable[..., str | None],
        send_transaction: Callable[..., str],
        wait_for_receipt_success: Callable[[str, str], dict[str, Any]],
        rpc_url_for_chain: Callable[[str], str],
    ) -> None:
        self._ensure_token_allowance = ensure_token_allowance
        self._send_transaction = send_transaction
        self._wait_for_receipt_success = wait_for_receipt_success
        self._rpc_url_for_chain = rpc_url_for_chain

    def ensure_approvals(self, plan: EvmActionPlan, *, owner: str, private_key_hex: str) -> list[str]:
        approve_tx_hashes: list[str] = []
        for approval in plan.approvals:
            tx_hash = self._ensure_token_allowance(
                chain=plan.chain,
                token_address=approval.token,
                owner=owner,
                spender=approval.spender,
                required_units=int(approval.required_units),
                private_key_hex=private_key_hex,
            )
            if tx_hash:
                approve_tx_hashes.append(str(tx_hash))
        return approve_tx_hashes

    def execute_calls(self, plan: EvmActionPlan, *, owner: str, private_key_hex: str) -> list[str]:
        tx_hashes: list[str] = []
        rpc_url = self._rpc_url_for_chain(plan.chain)
        for call in plan.calls:
            tx_obj: dict[str, Any] = {"from": owner, "to": call.to, "data": call.data}
            value_wei = str(call.value_wei or "0").strip() or "0"
            if value_wei != "0":
                tx_obj["value"] = value_wei
            tx_hashes.append(self._send_transaction(rpc_url, tx_obj, private_key_hex, chain=plan.chain))
        return tx_hashes

    def wait_for_receipts(self, chain: str, tx_hashes: list[str]) -> list[dict[str, Any]]:
        receipts: list[dict[str, Any]] = []
        for tx_hash in tx_hashes:
            receipts.append(self._wait_for_receipt_success(chain, tx_hash))
        return receipts

    def execute_plan(
        self,
        plan: EvmActionPlan,
        *,
        owner: str,
        private_key_hex: str,
        wait_for_operation_receipts: bool = True,
        liquidity_operation: str | None = None,
    ) -> EvmExecutionResult:
        approve_tx_hashes = self.ensure_approvals(plan, owner=owner, private_key_hex=private_key_hex)
        operation_tx_hashes = self.execute_calls(plan, owner=owner, private_key_hex=private_key_hex)
        if wait_for_operation_receipts:
            self.wait_for_receipts(plan.chain, operation_tx_hashes)
        tx_hash = operation_tx_hashes[-1] if operation_tx_hashes else None
        details = dict(plan.details)
        details["approveTxHashes"] = approve_tx_hashes
        details["operationTxHashes"] = operation_tx_hashes
        return EvmExecutionResult(
            ok=True,
            execution_family=plan.execution_family,
            execution_adapter=plan.execution_adapter,
            route_kind=plan.route_kind,
            liquidity_operation=liquidity_operation,
            approve_tx_hashes=approve_tx_hashes,
            operation_tx_hashes=operation_tx_hashes,
            tx_hash=tx_hash,
            details=details,
        )
