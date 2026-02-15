# Trade Approval Worksheet (Agent-Only)

Date:
Agent name / id:
Chain:

## Setup Snapshot (Agent-Verifiable)
- Global approval mode (approval_mode): `auto` / `per_trade`
- Token preapprovals (tokenIn list / allowed_tokens):
- Risk limits: daily USD cap enabled/disabled + max + current usage
- Chain access enabled/disabled for this agent+chain

Notes:

## 1) Approval-Pending To Approved Path
Goal: trade becomes `approval_pending`, then transitions to `approved`, then the agent executes and fills.

Steps
- [ ] Propose: `trade 50 usdc for weth with 1% slippage`

Expected (agent-visible)
- [ ] Contains `Trade ID: trd_...`
- [ ] Contains exact swap: `<amountIn> <tokenIn> -> <tokenOut>`
- [ ] Contains `Chain: <chainKey>`
- [ ] Contains `Status: approval_pending`
- [ ] Includes slippage bps (or percent) and quote/minOut if available
Approval wait + execution
- [ ] Poll `GET /api/v1/trades/:tradeId` until status is `approved` (or timeout 30 minutes).
- [ ] On approval: post confirmation in active chat: approved + details + tradeId.
- [ ] Execute swap and post fill summary + tx hash.

Reject path
- [ ] Repeat; wait for status `rejected` and record reasonMessage/reasonCode.
Expected
- [ ] Agent posts denial + includes reasonMessage if present.
- [ ] No on-chain tx for that tradeId.

Notes / Issues:

## 2) “Approval Surface” Independence (Agent View)
Goal: the agent does not care whether approval came from Telegram or web; it only reacts to status change.

Steps
- [ ] Create a trade that becomes `approval_pending`.
- [ ] Wait for it to become `approved` OR `rejected`.
Expected
- [ ] Agent responds correctly (execute only on `approved`, never on `rejected`).
- [ ] Agent’s user-facing message does not require the human to paste callback payloads; it only references the tradeId and next steps.

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
