# Page #5 — Settings & Security (Device + Access, Cookie-Based) — Full Build Spec
There are NO user accounts. This page manages device-level access via secure cookies and global safety preferences. It should feel like a premium wallet security screen: clear, cautious, and operational.

## Route
- `/settings`
Optional hash tabs:
- `/settings#access`
- `/settings#security`
- `/settings#danger`

## Purpose
1) Show the current device’s access status (cookie-based).
2) List all agents this device can control (owner cookies) and allow removing access per agent.
3) Allow adding an agent by pasting a key URL (optional helper; primary flow is key URL visit).
4) Provide global defaults for approval behavior (per-trade vs allowlist posture, confirm risky actions).
5) Provide emergency actions (“panic controls”): pause all agents, revoke all allowances, clear device access.

## Access Model Context (Critical)
- “Owner access” is granted by visiting a URL containing an agent key.
- The app stores a secure cookie scoped to that agent (or a cookie that includes agent grants).
- This page must never claim the user has an account.
- This page must clearly distinguish:
  - **Device Access** (cookies / ability to control agents in the UI)
  - **On-chain Approvals** (token allowances that exist on-chain, independent of cookies)

## Layout (Desktop 1440px+)

### 0) Global App Shell
- Left sidebar nav:
  - Dashboard
  - Explore
  - Approvals Center
  - Settings & Security (active)
- Top bar (sticky):
  - Title: “Settings & Security”
  - Right: Dark mode toggle + Chain selector (optional, can be hidden here)

### 1) Page Tabs (horizontal)
Tabs (or left sub-nav inside page):
- Access (default)
- Security
- Notifications (optional; can be hidden v1)
- Danger Zone

---

# TAB A — Access

## Card A1: “This Device”
Shows device context and cookie state.
Content:
- “You are authorized on this device using secure cookies.”
- Device label (derived from UA): e.g., “Chrome on Windows”
- Last active time
- Cookie expiry/refresh policy (plain language):
  - “Access persists on this browser unless cleared or revoked.”
- Buttons:
  - **Clear local access** (secondary)
  - (Optional) **Export recovery bundle** (only if you support a non-account recovery mechanism)

Tooltip help icon:
- Explains that clearing access removes local control but not on-chain approvals.

## Card A2: “Agents You Can Control”
This is the core list.
Layout: table-like list with rows.

Columns:
- Agent (avatar + name)
- Access Level badge: “Owner Access”
- Chain(s) icons
- Granted via: “Key Link”
- Last used time
- Status dot
- Quick actions:
  - **Open**
  - **Remove Access** (trash icon)

Row click behavior:
- Clicking row opens details drawer:
  - Agent ID
  - Vault address
  - Cookie scope info (friendly)
  - “Open agent page”
  - “Remove access”

At top of card:
- Search input: “Search my agents”
- Filter chips (optional):
  - Online only
  - Copy trading enabled
  - Pending approvals

## Card A3: “Add Agent Access”
Even though primary flow is visiting a key link, users will want manual entry.
UI:
- Input: “Paste agent key link”
- Button: **Add Access**
Behavior:
- Validates format (basic)
- On success:
  - stores cookie grant
  - shows toast: “Access granted for Agent X”
  - adds agent to list above

Security note below input:
- “Key links grant control of an agent. Treat them like a private key.”

Optional alternate:
- “Scan QR code” (if you support)

---

# TAB B — Security

## Card B1: “Approval Defaults”
Global preferences that influence behavior across all owned agents on this device.
Controls:
- Default approval posture (radio):
  - Per-trade approvals (recommended)
  - Token allowlist first
  - Global approval allowed (advanced) (toggle enables ability to use global approval on agent pages; default OFF)
- Confirmation requirements (toggles):
  - Require confirmation for unlimited allowances (ON by default)
  - Require confirmation for withdrawals over $X (default ON, X configurable)
  - Always show spender + allowance diff before signing (ON)
- Optional:
  - Default daily spend cap suggestion (numeric; applied when configuring limits on an agent, not forced)
  - Default max slippage preference (numeric)

## Card B2: “Auto-Lock / Safety”
Since there are no accounts, you can still implement local safety:
- Auto-lock approvals after idle time:
  - Dropdown: Never / 5m / 15m / 1h
- “Require re-confirmation before approving” (toggle)
- “Hide high-risk actions behind extra confirmation” (toggle)
  - Example: type “REVOKE” or “ENABLE” to proceed on dangerous actions

## Card B3: “Privacy”
- “Store favorites locally on this device” (toggle)
- “Store agent access list locally” (always yes; informational)
- Optional: “Clear cached analytics” button

---

# TAB C — Notifications (Optional)
If you do not have notifications in v1, hide this tab entirely.
If included, it should be device-based:
- In-app notifications (toggle)
- Web push (toggle + permission)
- Telegram webhook (field + test button)
Triggers:
- Approval requested
- Trade failed
- Drawdown threshold exceeded
- Copy trade drift exceeded

---

# TAB D — Danger Zone (Must-have)

This tab must be visually distinct:
- red border accents
- warning copy
- strong confirmation modals

## Card D1: “Emergency Controls”
Actions:
1) **Pause all owned agents**
   - Explanation: “Stops execution (if supported). Approvals remain possible.”
2) **Revoke all allowances (across all owned agents)**
   - Explanation: “This is on-chain. Requires signatures and gas.”
   - Confirmation includes:
     - count of allowances affected
     - estimated gas
     - multi-signature warning: “You may be prompted multiple times.”

3) **Disable all copy trading**
   - Stops copy relationships on destination agents.

Each action opens a confirmation modal with:
- Big warning header
- “What will happen” bullet list
- “This cannot be undone easily” line
- Confirm button (danger)
- Optional “type to confirm” for revoke all

## Card D2: “Clear This Device”
- **Clear local access**
  - Removes all agent cookies and local favorites for this browser.
  - Does NOT revoke on-chain allowances.
- Confirmation modal must say explicitly:
  - “This only removes access on this device.”
  - “To remove token allowances, use Revoke All.”

---

## Mobile Layout (390–430px)
- Tabs become segmented control at top with horizontal scroll:
  - Access | Security | Danger
- Cards become single column stacked.
- “Agents you can control” becomes list with expandable rows.
- Danger actions use full-width buttons.
- Confirmations use bottom sheets (not tiny modals).

---

## Dark Mode Spec
Uses global tokens.

Light:
- Background #F6F8FC
- Surface #FFFFFF
- Border #E6ECF5
- Text #0B1220
- Accent #2563EB
Dark:
- Background #0B1220
- Surface #111A2E
- Border #22304D
- Text #EAF0FF
- Accent #3B82F6

Dark mode rules:
- Danger zone keeps red border but ensure contrast.
- Toggle controls and inputs have clear focus rings.
- Avoid heavy shadows; rely on borders.

---

## Component Inventory
- SettingsTabs
- DeviceCard
- AgentAccessList + AgentAccessRow + AgentAccessDrawer
- AddAgentKeyLinkForm
- ApprovalDefaultsCard
- AutoLockCard
- DangerZoneCard
- ConfirmModal / ConfirmBottomSheet
- Toast system

---

## Edge Cases & States
### No agent cookies on device
- Access tab shows empty state:
  - “No agent access found on this device.”
  - CTA: “Add agent via key link” (paste input)
  - Secondary CTA: “Browse agents” → Explore

### Cookie present but expired/invalid
- Agent row shows “Access expired” badge
- Action: “Re-add via key link”
- Do not show owner controls until refreshed

### User clears device access
- Immediately removes agents from list
- Redirect user to Dashboard
- Show toast: “Local access cleared”

---

## Copywriting Tone
- Always say “on this device” / “in this browser”
- Emphasize key links are sensitive
- Distinguish on-chain approvals vs device access

End of Page #5 spec.
