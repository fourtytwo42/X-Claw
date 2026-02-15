# Failures + Agent Feedback Worksheet (Approvals)

Date:
Tester:
Agent id:
Chain:

## 1) Telegram Callback Failure Behavior
Goal: failures are visible and retryable (not silent).

Steps
- [ ] Create an approval_pending trade with buttons in Telegram.
- [ ] Simulate server failure (stop web process or block network).
- [ ] Click Approve.

Expected
- [ ] Telegram message edits to show a clear error code/message.
- [ ] Buttons remain usable for retry (or reappear).
- [ ] Web does not incorrectly mark approved.

Notes / Issues:

## 2) Idempotency / Double Click
Goal: repeated clicks do not wedge the system.

Steps
- [ ] Create approval_pending with Telegram buttons.
- [ ] Click Approve twice quickly.

Expected
- [ ] One success; second is safe (no hard failure loop).
- [ ] Telegram message ends deleted (or buttons removed).
- [ ] Web queue clears once.

Notes / Issues:

## 3) OR Semantics (Telegram vs Web)
Goal: approving in either surface resolves the other.

Web-first
- [ ] Create pending visible in both web + Telegram
- [ ] Approve in web
Expected
- [ ] Telegram message gets deleted (or buttons removed) within ___ seconds

Telegram-first
- [ ] Create another pending
- [ ] Approve in Telegram
Expected
- [ ] Web queue clears within ___ seconds

Notes / Issues:

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

