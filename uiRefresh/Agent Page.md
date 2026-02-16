# Page #3 — Agent Page (Unified Wallet Console: Owner + Viewer Modes) — Full Build Spec
This is the single most important page. It must work as:
- Public / viewer profile (no control cookie): read-only + Copy Trade CTA
- Owner console (has agent cookie via key URL): full wallet actions, approvals, limits, revoke, withdraw/deposit
- Mobile-first friendly (bottom action bar for owner)
- Dark mode supported

## Route
- `/agents/{agentId}`

## Access Model (Critical Context)
Users do NOT have accounts. Access is granted via a URL with a secret key.
- Visiting a key URL stores a **secure cookie** on the device for that agent (Owner Access).
- Later visits to `/agents/{agentId}`:
  - If cookie exists: Owner Mode enabled
  - If cookie absent: Viewer Mode

Agent page must render based on access state:
- Owner Mode: show interactive controls + sensitive panels
- Viewer Mode: hide controls; show lock states; keep copy-trade action

## Global App Shell
- Left sidebar nav:
  - Dashboard
  - Explore
  - Approvals Center
  - Settings & Security
- Top bar (sticky):
  - Breadcrumb: “Wallet / Agents / Agent A1” (or “Explore / Agent A1” depending entry; keep consistent)
  - Search (optional)
  - Chain selector pill
  - Dark Mode toggle
  - (Optional) pending approvals indicator icon (global)

---

# Desktop Layout (Owner Mode)

## 1) Header / Hero Row
Left:
- Agent avatar + name (large)
- Status dot + label: Online / Offline / Degraded
- Tags chips (strategy): Arbitrage, DeFi, etc.
- Vault address (short) with copy button
- Links: “View on Explorer”

Right (Primary Actions row):
- **Deposit** (primary)
- **Withdraw** (secondary)
- **Revoke All** (danger outline)
- Overflow menu (⋯): Share, Copy Agent Link, Security Guide

Secondary action row (optional, if you support these):
- **Set Limits**
- **Pause Agent**
- **Manage Approvals** (if you want a dedicated CTA; otherwise use tabs)

Notes:
- Deposit/Withdraw open modal/sheet flows.
- Revoke All triggers confirmation modal with big warnings + allowance diff.

## 2) KPI Strip (under header)
4 KPI cards:
- Lifetime PnL
- 24H Volume
- Win Rate
- Fees Paid
Each KPI card:
- Big value
- Delta %
- Tooltip definition

## 3) Main Content Grid
Two-column layout:
- Left (main): charts + tabs + activity/holdings
- Right (rail): approvals queue + copy trading + permissions highlights

### Left Column
#### A) Tab Bar (segmented)
Tabs:
- Performance
- Trades
- Holdings
- Permissions
- Risk & Limits

Default: Performance

#### B) Performance Panel
- Chart: “Equity & Volume”
- Controls: 1H / 24H / 7D / 30D + Filter (DEX, chain)
- Footer chips: DEX breakdown + active DEX count

#### C) Recent Activity Feed (below chart)
List of last N actions:
- Trade executed (swap)
- Approval action (allowance change)
- Copy-trade sync events
Each row includes:
- Icon, summary text, time
- Status badge (success/pending/failed)
- Clicking opens detail drawer with tx link.

#### D) Holdings Summary Card
Shows top tokens in agent vault:
- Token icon + symbol
- Amount + USD value
- Permission badge: Approved / Limited / Not approved (for agent spending)
Click row opens Token Drawer.

### Right Column (Critical)
#### A) Pending Approval Requests Card (Owner)
This must be prominent and near top.
Content:
- If requests exist: list 1–3 most recent with “View All”
Each request card includes:
- Action summary: “Swap 0.8 ETH → 2,700 USDT”
- Reason: “USDT limit exceeded” / “Not pre-approved” / “New spender”
- Risk chips (if available): New token, High slippage, Unknown spender
- Buttons:
  - **Approve Once** (primary)
  - Reject (secondary/danger)
- Expand “Details” accordion:
  - Spender, allowance change diff
  - Route, slippage, expected output
  - Gas estimate
Approvals require signature flow (wallet-like).

Empty state:
- “No pending approvals. Agent operating within limits.”

#### B) Copy Trading Card (Owner)
Shows if THIS agent is:
- Copying another agent
- Being copied by followers (optional)

If copying:
- “Copying Agent A1” (source)
- Destination: this agent (implied)
- Last sync time
- Drift (execution divergence)
- Copied trades count
- Controls:
  - Pause copying
  - Stop copying
  - Adjust sizing (0.5x / 1x / 2x)

If not copying:
- Show “Not copy trading” + CTA “Find an agent to copy” → Explore.

#### C) Permissions Highlights Card (Owner)
A compact summary of current permission posture:
- Global Approval: Off/On
- Token allowlist count
- Unlimited allowances count
- Per-trade approvals: Active/Inactive
- Button: “Manage” (jumps to Permissions tab)

#### D) Quick Limits Card (Owner)
- Daily spend cap
- Max slippage
- Allowed DEXs (chips)
- Allowed chains
Edit button opens limits modal.

---

# Desktop Layout (Viewer Mode)

Same structure and visuals, but:
## Header actions (right side)
Replace owner actions with:
- **Copy Trade** (primary) + dropdown caret
- Watch
- Share
- Copy Agent Link
No Deposit/Withdraw/Revoke/Pause.

## Right Column changes
- Pending Approval Requests: replaced with locked card:
  - “Owner-only approvals”
  - small explanation: “Approvals and withdrawals can only be performed by the agent owner.”
- Permissions Highlights: locked/limited view:
  - You may show posture (e.g., “Per-trade approvals enabled”) but no spender addresses unless desired.
- Limits card: read-only display (if public), otherwise locked.
- Copy Trading card: shows CTA:
  - “Copy this agent” → destination picker

## Copy Trade Flow (Viewer + Owner)
When user clicks Copy Trade:
- If user has owned agents on device:
  - Dropdown/modal: select destination agent (my agents list)
  - Sizing: 0.25x / 0.5x / 1x / 2x
  - Toggle: “Use destination agent limits” (default ON)
  - Toggle: “Require per-trade approvals” (default ON)
  - Confirm: “Enable Copy Trading”
- If no owned agents:
  - “You don’t have an owned agent on this device.”
  - CTA: “Add an agent via key link” → Settings & Security (Access tab)

After enabling copy trade:
- Destination agent page shows “Copy Trading” card reflecting relationship.

---

# Mobile Layout (Owner Mode)
The mobile agent page is a vertical stack with a **sticky bottom action bar**.

## 1) Sticky Top Header
- Back arrow + Agent name
- Chain selector
- Dark mode toggle (in overflow if space tight)
- Overflow: share/copy link/explorer/security guide

## 2) Agent identity block
- Avatar + name + status dot
- Tags
- Vault address short + copy

## 3) Sticky Bottom Action Bar (MUST)
Buttons (3–4 max):
- **Approvals (N)** (primary with badge)
- Withdraw
- Deposit
- More (limits, revoke all, pause)

If you must reduce to 3:
- Approvals (N)
- Withdraw
- More

## 4) Content order (vertical)
1. KPI carousel (swipeable)
2. Security posture strip (Global off / Allowlist / Pending / Daily cap)
3. Pending approvals card (if any, always near top)
4. Performance mini chart (7D default)
5. Holdings list (top tokens)
6. Copy trading card
7. Recent activity list

## 5) Tabs on mobile
Use a segmented control:
- Overview
- Approvals
- Holdings
- Activity
(Performance & Risk are sections within Overview or separate if needed.)

Approvals tab includes:
- Requests list
- Allowance inventory
- Global approval toggle (if allowed)
- Revoke all (danger)

Token drawer on mobile:
- Full-screen sheet with balance, allowance status, set limit/unlimited/revoke

---

# Deposit / Withdraw (Owner Mode)
## Deposit
- Show vault address + QR + copy
- Optional “Request funds from wallet” button (if integrated)
- Explainer: “Deposit funds into this agent vault for trading.”

## Withdraw
Flow:
1) Select asset (ETH/USDC/…)
2) Amount + max
3) Destination address (paste / saved / current wallet)
4) Review (fees, estimated time)
5) Confirm & sign

Withdraw requests may require an approval request entry (if your backend models them similarly). If so, route through approval queue with “Withdraw” type.

---

# Permissions / Approvals Model (Owner Mode)
Permissions tab contains:
- Global Approval toggle (high risk; confirmation modal)
- Token Pre-Approvals allowlist:
  - Add token (search)
  - Per-token limit controls
  - Unlimited toggle with warning
- Per-trade approval mode:
  - status and explanation
- Allowances inventory table:
  - spender, token, limit, utilization, last used
  - revoke/manage actions

Viewer mode: show either:
- Posture summary only (recommended)
OR
- Hide entirely behind lock card

---

# Dark Mode Spec
Use global tokens (same across app).

Light:
- Background #F6F8FC
- Surface #FFFFFF
- Border #E6ECF5
- Accent #2563EB
Dark:
- Background #0B1220
- Surface #111A2E
- Border #22304D
- Accent #3B82F6

Important dark-mode rules:
- Right-rail cards keep separation with borders (not heavy shadows).
- Primary buttons remain blue; danger remains red; ensure contrast.
- Charts invert and remain readable.

---

# Component Inventory
- AgentHeaderHero
- KPIStatRow
- AgentTabs
- PerformanceChart
- TradesTable
- HoldingsList + TokenDrawer
- PendingApprovalsCard + ApprovalDetailsSheet
- CopyTradingCard + CopyTradeModal
- PermissionsSummaryCard
- LimitsCard + LimitsModal
- DepositModal
- WithdrawFlowModal
- StickyBottomActionBar (mobile owner)
- ViewerLockCard components

---

# States & Edge Cases
- No data: show “Agent has no trading history yet.”
- Offline agent: show degraded banner (“Agent currently offline; approvals still possible.”)
- Cookie exists but expired: show “Access expired — re-open key link to restore owner access.”
- Sensitive operations always require explicit confirmation:
  - Revoke all
  - Unlimited approvals
  - Withdrawals above threshold (optional)

End of Page #3 spec.
