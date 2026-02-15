# Failures + Agent Feedback Worksheet (Agent-Only)

Date:
Agent id:
Chain:

## 1) Approval Wait Timeout Behavior
Goal: on timeout the agent gives actionable instructions and does not execute.

Steps
- [ ] Create an `approval_pending` trade.
- [ ] Do not approve it.
- [ ] Wait until the agent times out (30 minutes).

Expected
- [ ] Agent returns an error/notice with `code=approval_required` (or equivalent) and includes:
  - tradeId
  - exact swap summary
  - actionHint: approve the pending trade, then rerun the same trade command to resume (no duplicate pending)
- [ ] Agent does not execute any on-chain tx.

Notes / Issues:

## 2) Idempotency / Duplicate Approvals (Agent View)
Goal: repeated approvals do not cause double execution.

Steps
- [ ] Create an `approval_pending` trade.
- [ ] Cause the approval transition to happen (approved).
- [ ] Re-run the same command immediately again.

Expected
- [ ] Agent does not execute the *same tradeId* twice.
- [ ] Any subsequent trade is a new tradeId (unless previous still pending).

Notes / Issues:

## 3) Denial Feedback Quality
Goal: denials tell the human exactly what happened and how to proceed.

Steps
- [ ] Create `approval_pending`, then deny it.
Expected
- [ ] Agent posts a denial confirmation including:
  - tradeId
  - swap summary (amount + tokenIn -> tokenOut)
  - reasonMessage (if provided) or a clear default reason
  - next step (e.g., “change policy / try smaller amount / retry later”)

## 4) Agent Feedback Quality (Is The Info Sufficient?)
Rate 1-5 and note missing fields.

Trade queued summary clarity: __/5
- Missing: token symbols / amountIn / quote / minOut / slippage / chain / tradeId / next-step instructions

Approved confirmation clarity: __/5
- Missing: tradeId / summary / tx hash / amounts out

Denied confirmation clarity: __/5
- Missing: explicit reason + how to proceed

Policy approval clarity: __/5
- Missing: what changed + impact on future trades

Notes / Issues:

## 5) Ask The Agent For Suggestions (Copy/Paste Prompt)
Send this to the agent after you finish the worksheets:

“Based on how approvals worked today, suggest 5 improvements to the approval UX. Include:
1) what info you needed but didn’t have,
2) where the human got confused,
3) what should change in the queued approval message format,
4) what should change in your follow-up confirmation messages,
5) any safety warnings that should always be included.”

Agent suggestions:
1.
2.
3.
4.
5.
