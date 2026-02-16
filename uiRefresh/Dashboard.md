# Page #1 — Dashboard (Global Landing) — Full Build Spec (Desktop + Mobile + Dark Mode)

## Purpose
The Dashboard is the default landing page for all users (owners + non-owners). It provides a system-wide view of all agent trading activity, discovery entry points (trending/top agents), and quick navigation into Agent pages. It is NOT a trading UI. It is an analytics + discovery terminal.

This page must work for:
- Anonymous / viewer users (no agent-control cookies)
- Owners (with one or more agent-control cookies) — they can filter to “My Agents”, but no approvals are managed here.

## Route
- `/` or `/dashboard`

## Core Concepts / Data
- “All agents” metrics (system-wide)
- Optional “My agents” metrics (only if owner has cookies)
- Time range selection: 1H / 24H / 7D / 30D
- Filters: chain, DEX/venue, strategy tags, risk
- Live feed of trades across system
- Leaderboards: top agents by PnL/Volume/etc.
- Trending agents (discovery)
- Recently active agents (recency)

## Page Layout (Desktop 1440px+)
### 0) Global App Shell
- Left sidebar nav (icon + label):
  - Dashboard (active)
  - Explore
  - Approvals Center
  - Settings & Security
- Top bar (sticky):
  - Left: Logo + “Dashboard”
  - Center: Global Search input
  - Right: Chain selector pill + “All agents / My agents” scope (if owner) + Dark Mode toggle + (optional notifications icon)

### 1) Top Bar Details
**Global Search**
- Placeholder: “Search agent… wallet… tx hash… token…”
- Autocomplete results grouped:
  - Agents (name + badge + chain icons)
  - Tokens (symbol + chain)
  - Transactions (hash shortened)
- Enter navigates to best match results list (or opens Explore with query prefilled)

**Scope Selector (Owner-only)**
- Dropdown:
  - All agents (default)
  - My agents (aggregate)
  - (Optional) specific agent selection is NOT here (agent selection happens on Agent pages; dashboard scope is only all vs my)
- If no owner cookies: hide scope dropdown entirely.

**Chain Selector**
- Default: “Ethereum Mainnet” or “All chains” (recommended)
- Selecting chain filters all charts/feed/leaderboards.

**Dark Mode Toggle**
- A clear icon toggle on top bar:
  - Light: sun icon
  - Dark: moon icon
- Persists in local storage.
- Must be available on every page in same position.

### 2) KPI Strip (Full width row)
Card style: clean rounded cards with soft shadows (light mode) and subtle borders (dark mode).
Show 6 KPI tiles (responsive):
1. 24H Volume
2. 24H Trades
3. 24H Fees Paid
4. Net PnL (24H)
5. Active Agents (24H)
6. Avg Slippage (24H)

Each KPI:
- Big value (primary)
- Delta % with arrow (green up / red down)
- Small label (e.g., “vs prev 24h”)
- Tooltip on hover with definition.

Interaction:
- Clicking a KPI applies a “focus” filter for the main chart tab (e.g., clicking Fees switches chart tab to Fees).

### 3) Primary Chart Panel (Left main, ~8 cols)
Tabs inside panel:
- Volume (default)
- PnL
- Trades
- Fees

Controls in top-right of panel:
- Time range buttons: 1H, 24H, 7D, 30D
- Filter button opens inline filter chips:
  - DEX: All / Uniswap / Sushi / etc
  - Strategy: All / Arbitrage / Trend / Yield / etc
  - Risk: Any / Low / Med / High

Chart visuals:
- Use a combined line + bars (like your mock):
  - Line = selected metric trend
  - Bars = volume/trades by interval (if applicable)
- Hover tooltip shows exact timestamp/value and breakdown by DEX (optional).

Footer of chart panel:
- Mini venue breakdown chips:
  - “Uniswap $21.4M”
  - “Sushi $7.3M”
  - “Other $…”
- “# Active DEXs” indicator.

### 4) Right Column (~4 cols)
#### A) Live Trade Feed Card
- Title: “Live Trade Feed”
- Rows (scrolling list, last N trades)
Each row shows:
- Agent avatar + name (clickable)
- Pair: e.g., “ETH → USDC”
- Size in USD
- Slippage chip (e.g., “0.18%”)
- Status icon (success/pending/fail)
- Timestamp relative (e.g., “12s ago”)

Row click expands details (inline or modal):
- Route (DEXs)
- Tx hash link
- Gas used
- Price impact (if tracked)

#### B) Top Agents (24H) Card (Leaderboard)
- Title: “Top Agents (24H)”
- Sort dropdown (PnL / Volume / Win Rate)
- Rows show:
  - Rank #
  - Agent avatar + name (click)
  - Metric value
  - Risk badge
- “View All” navigates to Explore prefiltered.

#### C) Recently Active Card
- Title: “Recently Active”
- Shows last actions by agent (trade events)
- Each row links to agent page.

#### D) Learn/How-it-works Card (Optional but recommended)
- Small card: “How it works — approvals & agent trading”
- Links to docs / security guide.

### 5) Mid Row (Below primary chart)
Two cards side-by-side (or stacked on smaller screens):
#### A) DEX / Venue Breakdown
- Donut or stacked bar chart:
  - Volume share by DEX
- Hover shows % and absolute volume
- Clicking a segment filters dashboard to that DEX.

#### B) Execution & Safety Health
A “status console” style card with:
- Success Rate (24H)
- Median confirmation time
- Median price impact
- Failure rate + top revert reasons list (short)
- “Anomalies” mini panel (optional):
  - e.g., “Slippage spike detected on SushiSwap (last 30m)”

### 6) Trending Agents Section (Discovery)
- Title: “Trending Agents”
- Grid of cards (3 across desktop):
Each agent card:
- Agent name + avatar
- Strategy tags chips
- Chain icons
- 7D sparkline (tiny)
- 24H PnL + 7D PnL
- Risk badge
- Watch count (optional)
- CTA: “View”

### 7) Footer
- Links: Docs, API, Terms, Security Guide

---

## Mobile Layout (390–430px wide)
Mobile uses same content but reordered for vertical scan.

### Sticky Top Bar (mobile)
- Left: hamburger (opens nav drawer)
- Center: “Dashboard”
- Right: chain selector + dark mode toggle

Search becomes a full-width bar below header (or expands when tapped).

### Content Order (mobile)
1. KPI carousel (horizontal swipe)
2. Primary Chart Panel (full width) with tabs
3. Live Trade Feed (collapsible with “View all”)
4. Top Agents (collapsible)
5. Venue Breakdown (stacked)
6. Execution & Safety Health (stacked)
7. Trending Agents (2-up grid or single column)

---

## Dark Mode Spec (applies globally)
### Theme Tokens
Provide both themes via CSS variables or design tokens.

**Light**
- Background: #F6F8FC
- Surface/Card: #FFFFFF
- Border: #E6ECF5
- Text primary: #0B1220
- Text secondary: #5B6B84
- Accent: #2563EB (blue)
- Success: #16A34A
- Warning: #F59E0B
- Danger: #DC2626

**Dark**
- Background: #0B1220
- Surface/Card: #111A2E
- Surface-2: #0F172A
- Border: #22304D
- Text primary: #EAF0FF
- Text secondary: #A7B4D0
- Accent: #3B82F6 (slightly brighter)
- Success: #22C55E
- Warning: #FBBF24
- Danger: #EF4444

### Dark Mode Behavior
- Charts invert: dark background, gridlines subtle, text light.
- Keep “risk badges” and “status chips” readable (use filled chips with subtle transparency).
- Shadows reduce in dark mode; use borders instead.

### Toggle Placement (consistent)
- Top bar right side on desktop.
- Top bar right side on mobile.
- Toggle state persists (local storage).

---

## Component Inventory (to implement)
- AppShellSidebar
- TopBarSearch
- ChainSelector
- ScopeSelector (owner-only)
- DarkModeToggle
- KPIStatCard (x6)
- ChartPanel (with tabs + time range controls)
- LiveTradeFeedList
- TopAgentsLeaderboard
- RecentlyActiveList
- VenueBreakdownChart
- ExecutionHealthCard
- TrendingAgentCardGrid
- DocLinkCard

---

## States & Edge Cases
### Anonymous (no cookies)
- No “My agents” scope
- Still can search and view any agent public page

### Owner (has agent cookies)
- “My agents” scope appears
- KPI + charts can toggle to “My agents” aggregate view

### Loading
- Skeletons for KPI and chart area
- Live feed shows shimmer rows

### Empty / Low data
- Show “No recent trades” state
- Provide hint: “Try switching to All chains” or “Widen time range”

### Performance
- Live feed should cap row count and virtualize if necessary
- Charts should debounce filter changes

---

## Navigation Outcomes
- Clicking any agent name navigates to unified Agent Page:
  - `/agents/{agentId}`
- “View All” navigates to Explore with prefilled filters:
  - `/explore?sort=pnl&range=24h`

---

## Copywriting Tone
- Professional, wallet-like, trust-forward.
- Avoid “trading” CTA language (no “Buy/Sell”).
- Use “Agent activity”, “execution”, “approvals”, “risk”.

End of Page #1 spec.
