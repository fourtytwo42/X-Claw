# Agent-Only Approval Smoke Worksheet (10 Checks)

Date:
Agent name / id:
Chain:

Goal: confirm the approval pipeline works end-to-end using only signals the agent can observe
(its own outgoing messages + X-Claw API responses). This sheet assumes a human may click a button
in Telegram or web, but the agent verifies outcome only by API status transitions.

## Preconditions (Agent-Verifiable)
- [ ] Agent can reach X-Claw API (no auth/network errors)
- [ ] Chain enabled for this agent (no `chain_disabled`)
- [ ] Global approval OFF (approval_mode = per_trade) OR pick a tokenIn not preapproved

## Smoke (Run In Order)
1. [ ] Propose an approval-required trade (pick tokenIn not preapproved): `trade-spot ...`
2. [ ] Confirm server response is `approval_pending` and returns a stable `tradeId=trd_...`
3. [ ] Post a single queued summary message for the human that includes:
  - `Trade ID: trd_...`
  - `<amountIn> <tokenIn> -> <tokenOut>`
  - `Chain: <chainKey>`
  - `Status: approval_pending`
4. [ ] Wait for approval up to 30 minutes (poll trade status).
5. [ ] If status becomes `approved`, immediately acknowledge in the active chat:
  - “Approved” + tradeId + swap summary
6. [ ] Execute swap and transition statuses (`executing` -> `verifying` -> `filled`) and include tx hash.
7. [ ] If status becomes `rejected`, acknowledge in the active chat:
  - “Denied” + tradeId + reasonMessage (if present)
  - Confirm you did not execute any on-chain tx.
8. [ ] Idempotency safety: retry the same approve callback outcome by re-polling status; ensure no duplicate execution.
9. [ ] De-dupe safety: re-run the exact same trade request while still `approval_pending`; confirm you reuse the same `trd_...`.
10. [ ] After the trade is terminal (filled/rejected), run the exact same request again; confirm a NEW `trd_...` is created.

Notes / Issues:

