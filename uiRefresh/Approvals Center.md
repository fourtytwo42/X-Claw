# Page #4 — Approvals Center (Global Inbox Across All Owned Agents) — Full Build Spec
This is the security + operations hub. It aggregates approvals, allowances, and permission posture across ALL agents that the device has Owner Access cookies for.

There are no accounts; access is based on cookies. If a device has zero owner cookies, this page should show an empty state + guidance.

## Route
- `/approvals`

## Purpose
Provide one place to:
- View and act on **Pending Approval Requests** across all owned agents
- Audit and manage **Allowances Inventory** (token allowances / spenders / limits)
- Bulk actions: revoke, cap unlimited, deny requests, prioritize urgent approvals
- Filter/sort by agent, chain, token, spender, risk, status
- Jump into specific Agent pages for deeper context

## Access Model (Critical Context)
- Owners are determined by presence of secure cookies per agent.
- If no owner cookies exist:
  - Show “No agent access on this device” empty state with CTA to Settings & Security → Add agent via key link.

## Layout (Desktop 1440px+)

### 0) Global App Shell
- Left sidebar nav:
  - Dashboard
  - Explore
  - Approvals Center (active)
  - Settings & Security
- Top bar (sticky):
  - Page title: “Approvals Center”
  - Right: chain selector (All chains default) + Dark mode toggle
  - (Optional) small counter pill: “Pending: 3”

### 1) Header + Summary Strip
Top summary strip with 4 mini cards:
- Pending requests (count)
- Unlimited allowances (count)
- High-risk allowances (count)
- Last approval signed (time)

Below summary: a thin “Security posture” line:
- “Per-trade approvals active on 2 agents · Global approval enabled on 0 agents · Allowlist tokens: 7”

### 2) Primary Two-Panel Layout
Use a two-column layout:
- Left: Pending Requests (priority)
- Right: Allowances Inventory (audit)

#### Left Panel: Pending Approval Requests (the Inbox)
**Card: Pending Requests**
- Tabs: Pending / Approved / Rejected / All
- Default tab: Pending

**Filters row (inside card)**
- Agent dropdown: All my agents (default)
- Risk dropdown: Any / Low / Med / High / Critical
- Type dropdown: Trade approval / Allowance increase / Withdraw approval / Revoke request (optional)
- Token search field (symbol/address)
- Sort: Newest / Oldest / Highest risk / Largest size

**Request list items (stacked cards)**
Each request card shows:
- Agent identity (avatar + name) + chain icon
- Request type label (chip): “Trade Approval” / “Allowance Increase” / “Withdraw”
- Main summary line (big):
  - Example trade: “Swap 0.80 ETH → 2,700 USDT”
  - Example allowance: “Increase USDT allowance to 5,000”
  - Example withdraw: “Withdraw 1,200 USDC to 0x…”
- Reason line (small):
  - “Token not pre-approved” / “Allowance insufficient” / “Risk threshold exceeded”
- Risk chips (if available):
  - New token, High slippage, Unknown spender, New router, Large size
- Metadata row:
  - Est gas, expected output, slippage, venue, timestamp
- Actions (right aligned):
  - **Approve Once** (primary)
  - Approve + Allowlist Token (secondary) [only if relevant]
  - Reject (danger text/button)

**Expand details (accordion)**
- Shows the “wallet prompt” detail view:
  - Spender address (short + copy)
  - Allowance diff (before → after)
  - Route (DEXs) and token path
  - Slippage, min output, deadline
  - Estimated gas
  - Link to full simulation (optional)
  - Tx hash once submitted (pending → confirmed)

**Bulk actions bar**
When selecting multiple requests (checkbox):
- Approve selected
- Reject selected
- Export details (optional)
- Warning: “Approving multiple requests will prompt multiple signatures.”

**Empty states**
- Pending empty: “No pending approvals. Your agents are operating within limits.”
- No agents accessible: show page-level empty state (see below)

#### Right Panel: Allowances Inventory (audit + revoke)
**Card: Allowances Inventory**
Shows a table-like list (virtualized if large) with columns:
- Agent
- Token
- Spender (router/executor label if known)
- Allowance amount (∞ or numeric)
- Utilization (optional: used vs max)
- Last used
- Risk badge (computed or rules-based)
- Actions (Manage / Revoke)

**Filters row**
- Agent dropdown
- Token search
- Spender search
- Allowance type: Any / Unlimited only / Capped only
- Risk: Any / High only

**Row actions**
- Manage (opens right-side drawer):
  - Set new limit
  - Convert unlimited → capped
  - Revoke
  - View history
- Revoke (quick action) opens confirm modal with clear warnings + gas estimate

**Bulk actions**
Select rows:
- Revoke selected
- Cap unlimited selected (prompt for cap amount or per-token recommended caps)
- Export CSV (optional)

**Drawer: Allowance Details**
- Token info + contract address
- Spender info (label + address)
- Current allowance (big)
- Last used events list
- Buttons:
  - Set limit
  - Make unlimited (danger, confirmation)
  - Revoke (danger)

### 3) Risk & Safety Sidebar (Optional, small)
A slim card below right panel (or inside it):
- “High-risk items”
  - Unlimited allowance on Token X
  - New spender detected
- “Suggested actions”
  - “Cap unlimited allowances” CTA
  - “Enable per-trade approvals on Agent Y” CTA (links to agent)

---

## Mobile Layout (390–430px)
Mobile prioritizes Pending Requests first, with Allowances in a secondary tab.

### Sticky Top Bar
- Title: “Approvals”
- Pending count badge
- Dark mode toggle in overflow
- Chain selector

### Primary Nav (segmented control)
- Requests
- Allowances
- Posture (optional small overview)

### Requests tab (mobile)
- Filters open bottom sheet
- Request cards stacked
- Approve/Reject buttons full-width (2-button row)
- Details open bottom sheet with full diff and confirm

### Allowances tab (mobile)
- Search + filter
- List rows -> tap opens full-screen “Allowance Details”
- Bulk actions via select mode

---

## Dark Mode Spec
Same global theme tokens.

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

Dark mode behaviors:
- Risk chips use subtle filled backgrounds with high-contrast text.
- Tables become list rows with separators to maintain legibility.
- Danger buttons keep red but with strong contrast.

---

## Component Inventory
- ApprovalsSummaryStrip
- RequestsInboxCard
  - RequestsFilterRow
  - RequestCard + RequestDetailsAccordion
  - BulkSelectionToolbar
- AllowancesInventoryCard
  - AllowanceRow
  - AllowanceDetailsDrawer
  - BulkRevokeToolbar
- FiltersBottomSheet (mobile)
- ConfirmModal (for revoke, unlimited, bulk)
- EmptyStatePanel (no agent access)

---

## Logic Rules (Important)
### Risk Scoring (UI-only rules, can be simple v1)
Mark as High/Critical if any:
- Unlimited allowance
- New spender not seen before
- Token age < threshold (if tracked)
- Slippage > X%
- Trade size > daily cap (if cap exists)
- Failure rate spike (optional)

### Cross-Agent Aggregation
Requests and allowances must always show which Agent they belong to (agent is first-class context).

### Navigation
- Clicking agent name -> `/agents/{agentId}` (owner mode if cookie exists)
- Clicking token -> opens token drawer (within Allowance drawer) or routes to Agent holdings view (optional)

---

## Empty State (No Owner Cookies)
Show a full-page empty state:
- Title: “No agent access found on this device”
- Body: “Approvals Center only appears when you’ve added an agent key link on this device.”
- CTA button: “Add agent via key link” → `/settings#access` (or open modal)
- Secondary: “Browse agents” → `/explore`

---

## Copywriting Tone
- Wallet-security-first
- Clear warnings on dangerous actions
- Always distinguish:
  - “Device access (cookies)” vs “On-chain approvals (allowances)”

End of Page #4 spec.
