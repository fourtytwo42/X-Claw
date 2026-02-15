# Trade Approval Worksheet (Web + Telegram)

Date:
Tester:
Agent name / id:
Chain:
OpenClaw version:

## Setup Snapshot (Fill Once)
- Global approval: ON / OFF
- Token preapprovals (tokenIn list):
- Risk limits: daily USD cap ON/OFF, max, today used
- Chain access: enabled/disabled
- Telegram active channel: yes/no

Notes:

## 1) Web Approval (No Telegram Active)
Goal: trade becomes `approval_pending`, can be approved/rejected in web, agent informs the user.

Steps
- [ ] Ensure Telegram is NOT the last active channel (send from some other channel last).
- [ ] Ask agent: `trade 50 usdc for weth with 1% slippage`

Expected (agent queued message)
- [ ] Contains `Trade ID: trd_...`
- [ ] Contains exact swap: `<amountIn> <tokenIn> -> <tokenOut>`
- [ ] Contains `Chain: <chainKey>`
- [ ] Contains `Status: approval_pending`
- [ ] Includes slippage bps (or percent) and quote/minOut if available

Expected (web)
- [ ] Approvals queue shows same tradeId
- [ ] Queue row includes amounts (at least amountIn) and tokens

Actions
- [ ] Approve in web
Expected
- [ ] Queue clears
- [ ] Agent posts confirmation in active chat: approved + details + tradeId
- [ ] Activity shows approved -> executing -> filled; tx hash present

Reject path
- [ ] Repeat; reject in web with a reason
Expected
- [ ] Queue clears
- [ ] Agent posts denial + includes reason
- [ ] No on-chain tx for that tradeId

Notes / Issues:

## 2) Telegram Buttons On Queued Trade Message
Goal: queued trade message has buttons; clicking is immediate; message is deleted; web stays in sync.

Steps
- [ ] Make Telegram the active channel (send any message in Telegram to the bot).
- [ ] Ask agent: `trade 75 usdc for weth with 1% slippage`

Expected
- [ ] Agent queued message includes buttons (Approve + Deny).
- [ ] No separate “prompt” message is required.

Approve
- [ ] Click Approve once
Expected
- [ ] Telegram message deleted (or buttons removed) within 3 seconds
- [ ] Web approvals queue clears within 5 seconds
- [ ] Agent posts approved confirmation in Telegram
- [ ] Trade executes and fills (tx hash in messages + web)

Deny
- [ ] Repeat and click Deny once
Expected
- [ ] Telegram message deleted (or buttons removed)
- [ ] Web queue clears
- [ ] Agent posts denied confirmation + reason
- [ ] No on-chain execution for that tradeId

Latency notes
- Approve click -> Telegram removed: ___ ms
- Approve click -> Web queue cleared: ___ ms
- Approve click -> Agent confirmation: ___ ms

Notes / Issues:

## 3) De-Dupe Rule (Only While Prior Still Pending)
Goal: the only time we reuse a trade is when the last identical request is still `approval_pending`.

While pending
- [ ] Create `approval_pending` trade for `2000 usdc -> weth`
- [ ] Immediately ask the exact same request again
Expected
- [ ] Agent reuses the existing `trd_...` (no new tradeId created)
- [ ] Agent tells user it’s already pending and points to the same tradeId

After resolution
- [ ] Approve/deny the pending trade
- [ ] Ask the same request again
Expected
- [ ] A new `trd_...` is created (not deduped)
- [ ] New approval flow begins

Notes / Issues:

