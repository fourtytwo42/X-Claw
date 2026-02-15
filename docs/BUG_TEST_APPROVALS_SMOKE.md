# Approval Smoke Worksheet (10 Checks)

Date:
Tester:
Agent id:
Chain:

## Preconditions
- [ ] Management session active in web app
- [ ] OpenClaw gateway running; Telegram provider connected
- [ ] Agent heartbeat fresh

## Smoke (Run In Order)
1. [ ] Create a trade that should require approval (global approval OFF, tokenIn not preapproved).
2. [ ] Agent posts queued trade summary containing: `Trade ID: trd_...`, swap amounts/symbols, `Chain: ...`, `Status: approval_pending`.
3. [ ] Telegram: that same queued message has Approve + Deny buttons.
4. [ ] Web: approvals queue shows the same `trd_...` with amountIn and tokenIn/tokenOut.
5. [ ] Click Approve in Telegram once.
6. [ ] Telegram message is deleted (or buttons removed) within 3 seconds.
7. [ ] Web approvals queue removes that `trd_...` within 5 seconds.
8. [ ] Agent posts “approved” confirmation in the active chat with tradeId + swap summary.
9. [ ] Trade executes and ends `filled` with tx hash shown in agent message and in web activity.
10. [ ] Repeat a new approval-required trade and click Deny: message removed, web queue clears, agent explains denial with reason, no on-chain execution.

Notes / Issues:

