# Policy Approval Worksheet (Preapprove Token + Global Approval + Revoke)

Date:
Tester:
Agent id:
Chain:
Telegram active: yes/no

## Setup Snapshot
- Global approval: ON / OFF
- Preapproved tokens (tokenIn): list

## 1) Preapprove Token (USDC)
Goal: agent can request a policy change; queued message has `ppr_...`; buttons attach; approve updates policy and agent explains result.

Steps
- [ ] Ask agent: `preapprove USDC for trading on base sepolia`

Expected (agent queued message)
- [ ] Contains `Approval ID: ppr_...`
- [ ] Contains token symbol + address
- [ ] Contains `Chain: base_sepolia`
- [ ] Contains `Status: approval_pending`
- [ ] Has Approve + Deny buttons on that same message (Telegram)
- [ ] Shows up in web approvals surface (if your build shows policy approvals in UI)

Approve
- [ ] Click Approve
Expected
- [ ] Telegram message deleted (or buttons removed) within 3 seconds
- [ ] Web reflects approved (queue clears)
- [ ] Agent posts a human-facing explanation:
  - what changed (USDC preapproved)
  - on which chain
  - what effect (tokenIn=USDC trades no longer need manual approval)

Verify effect
- [ ] Ask agent for a USDC->WETH trade that previously required approval
Expected
- [ ] It is auto-approved (no approval_pending) if the policy rule is tokenIn-only.

Notes / Issues:

## 2) Revoke Token Preapproval (USDC)
Goal: reverse the above; same approval mechanics; effect is restored to requiring approvals.

Steps
- [ ] Ask agent: `revoke USDC preapproval on base sepolia`
Expected
- [ ] Queued policy message with `ppr_...` + `approval_pending` + buttons.

Approve
- [ ] Click Approve
Expected
- [ ] Agent explains the revoke result and effect.

Verify effect
- [ ] Ask agent for USDC->WETH trade
Expected
- [ ] It becomes approval_required again (pending approval).

Notes / Issues:

## 3) Global Approval Toggle (Approve All)
Goal: agent can request enabling/disabling global approval via policy approvals flow.

Enable
- [ ] Ask agent: `turn on approve all`
Expected
- [ ] Queued policy message with `ppr_...` + buttons.
- [ ] On approve: agent explains that approvals are no longer required for trades.

Disable
- [ ] Ask agent: `turn off approve all`
Expected
- [ ] Queued policy message with `ppr_...` + buttons.
- [ ] On approve: agent explains approvals are required again unless tokenIn is preapproved.

Notes / Issues:

