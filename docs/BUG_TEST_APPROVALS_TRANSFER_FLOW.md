# Transfer Approval Worksheet (Slice 71, Single-Trigger)

Date:
Agent id:
Chain:
Telegram chat id/thread:

Goal: validate one-trigger outbound transfers (`wallet-send`, `wallet-send-token`) with runtime-canonical transfer approvals (`xfr_...`), deterministic Approve/Deny handling, and deterministic final result reporting.

## Preconditions
- [ ] OpenClaw gateway patched with `xfer|a|...` and `xfer|r|...` callbacks.
- [ ] Agent can reach X-Claw API (no auth/network errors).
- [ ] Chain enabled for this agent.
- [ ] Transfer policy mode for chain:
  - `transferApprovalMode = per_transfer`
  - `nativeTransferPreapproved = false`
  - `allowedTransferTokens = []`

## 1) Telegram Approve Path (ERC-20 transfer)
Prompt to send:
- [ ] `send 45 usdc to 0x<recipient> on base sepolia`

Expected queued approval message:
- [ ] Contains `Approval required (transfer)`
- [ ] Contains `Approval ID: xfr_...`
- [ ] Contains `Status: approval_pending`
- [ ] Contains token symbol/address, amount, destination, and chain
- [ ] Amount is human-readable first (for example `45 USDC` / `0.002 ETH`) and may include raw wei in parentheses
- [ ] Telegram buttons attached: `Approve` / `Deny`

Approve action:
- [ ] Click `Approve` once.

Expected immediate deterministic ack:
- [ ] `Approved transfer approval xfr_...`
- [ ] `Chain: base_sepolia`

Expected deterministic final result message (no extra user prompt):
- [ ] `Transfer result: filled` (or `failed`)
- [ ] `Approval: xfr_...`
- [ ] `Chain: base_sepolia`
- [ ] Amount line is human-readable (not raw wei-only)
- [ ] Includes `Tx: 0x...` when tx submitted
- [ ] Includes failure reason when failed

Expected agent follow-up:
- [ ] Agent posts natural-language summary to human after synthetic transfer-result routing.
- [ ] Agent summary uses human-readable amount text.

Notes / issues:

## 2) Telegram Deny Path (ERC-20 transfer)
Prompt to send:
- [ ] `send 12 usdc to 0x<recipient> on base sepolia`

Expected queued approval:
- [ ] `Approval ID: xfr_...` + `Status: approval_pending` + buttons

Deny action:
- [ ] Click `Deny`.

Expected:
- [ ] Immediate deterministic deny ack in chat.
- [ ] Transfer marked `rejected` (no execution).
- [ ] Agent posts refusal context with reason/next step.
- [ ] No tx hash for denied transfer.

Notes / issues:

## 3) Telegram Approve Path (Native transfer)
Prompt to send:
- [ ] `send 0.002 eth to 0x<recipient> on base sepolia`

Expected:
- [ ] Same `xfr_...` pending flow with buttons.
- [ ] Approve triggers automatic execution (single trigger only).
- [ ] Deterministic final result message includes status/approval/chain and tx hash when available.

Notes / issues:

## 4) Duplicate Callback Safety
Setup:
- [ ] Create one pending transfer (`xfr_...`).

Action:
- [ ] Click `Approve` twice (or tap once and re-open callback quickly).

Expected:
- [ ] No duplicate execution / no second tx for same `xfr_...`.
- [ ] Converged response allowed (`already decided`/terminal status), but no re-execution.
- [ ] Final state remains single terminal outcome.

Notes / issues:

## 5) Web Approve/Deny Remote Interface
Navigate:
- [ ] `/agents/:id` on active chain.

Expected UI:
- [ ] Transfer Approvals queue section present.
- [ ] Transfer Approval Policy section present.
- [ ] Auto-refresh keeps queue/history current.

Approve path from web:
- [ ] Pending `xfr_...` visible in queue.
- [ ] Click `Approve`.
- [ ] Transfer reaches terminal status (`filled` or `failed`) and appears in history.

Deny path from web:
- [ ] Pending `xfr_...` visible in queue.
- [ ] Click `Deny` with optional reason.
- [ ] Status converges to `rejected`; no tx executed.

Notes / issues:

## 6) Policy Controls Behavior
Set policy in web:
- [ ] `transferApprovalMode = auto`

Validate:
- [ ] New token/native transfer executes immediately (no pending approval).

Set policy in web:
- [ ] `transferApprovalMode = per_transfer`
- [ ] `nativeTransferPreapproved = true`
- [ ] `allowedTransferTokens` includes USDC address

Validate:
- [ ] Native transfer bypasses approval.
- [ ] USDC transfer bypasses approval.
- [ ] Non-allowed token transfer still requires `xfr_...` approval.

Notes / issues:

## 7) Required Evidence Capture
- [ ] Screenshot/log of queued transfer approval message with `xfr_...`.
- [ ] Screenshot/log of deterministic approve/deny ack.
- [ ] Screenshot/log of final result message.
- [ ] Tx hash + explorer link (or failure reason) recorded.
- [ ] `/agents/:id` queue/history screenshots before and after decision.

## Verdict
- [ ] PASS
- [ ] FAIL

Failure summary:
