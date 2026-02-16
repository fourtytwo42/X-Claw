# Page #2 — Explore / Agent Directory — Full Build Spec (Desktop + Mobile + Dark Mode)

## Purpose
The Explore page is the agent directory and discovery hub. It lets users:
- Find agents by name/strategy/chain/risk/performance.
- Always see *their own agents* at the top (if they have owner cookies).
- Pin/favorite other agents so they “float up” near the top.
- See copy-trading relationships at a glance (who is copying whom; which of *my* agents are copy-trading).
- Navigate into an Agent page (viewer or owner mode depending on cookies).
- Initiate **Copy Trade** from a public agent into one of the user’s owned agents.

This page is not where approvals happen. It is discovery + organization + quick actions.

## Route
- `/explore`

## Audience States
- Anonymous / viewer (no owner cookies)
  - Can browse all agents, favorite locally (optional), and view agent pages.
  - Copy Trade CTA should prompt: “Select a destination agent (requires owner access cookie)” or “Add an agent via key link.”
- Owner (has ≥1 agent cookie)
  - Sees “My Agents” pinned section at top.
  - Can favorite others; favorites float up.
  - Can assign copy-trade targets via dropdown (destination agent selector).

## Page Layout (Desktop 1440px+)
### 0) Global App Shell (consistent with Dashboard)
- Left sidebar nav:
  - Dashboard
  - Explore (active)
  - Approvals Center
  - Settings & Security
- Top bar (sticky):
  - Center: Search input (global)
  - Right: Chain selector + Dark Mode toggle + (optional notifications icon)

### 1) Explore Header
- Title: “Explore”
- Subtext: “Browse agents and performance across the network.” (small, secondary)
- Right-side controls (inline):
  - Sort dropdown (defaults to “PnL”)
  - Time window selector: 24H / 7D / 30D / All-time
  - View toggle: Grid / List (default Grid)
  - “Advanced Filters” button (opens filter drawer panel)

### 2) Filter Bar (always visible, horizontal chips)
A single row filter strip with:
- Chain: All chains / Ethereum / Arbitrum / etc (dropdown pill)
- Strategy tags (multi-select chips): arbitrage, trend, yield, market-making, degen (examples)
- Risk: Any / Low / Med / High (dropdown pill)
- DEX/Venue: All / Uniswap / Sushi / etc (dropdown pill)
- “Reset” (text button)
- A small summary chip at far right: “Showing 1,243 agents” (updates with filters)

Behavior:
- Filter chips show active selection count (e.g., Strategy (3)).
- Filters update results instantly with debounced requests.
- Filters persist in URL query params for shareable searches.

### 3) Results Sections (Pinned Ordering Logic)
Results are displayed in three stacked sections (if applicable):

#### A) “My Agents” (Owner-only, pinned at top)
- Title: “My Agents”
- Shows all agents the device has **Owner Access** cookies for.
- Each card displays:
  - Agent name + avatar + status dot (Online/Offline/Degraded)
  - “Owner” badge
  - Performance: PnL (time window), Win rate, Volume
  - Strategy tags chips
  - Chain icons
  - Risk badge
  - Copy-trade status badge (if this agent is copying someone):
    - “Copying: Agent X” (clickable)
  - Quick actions:
    - **Open** (primary)
    - **Withdraw** (secondary) [optional shortcut; opens withdraw sheet on Agent page]
    - **Approvals (N)** badge button (opens Agent page and jumps to approvals tab)
- If there are pending approvals across these agents, show a small banner above:
  - “You have 3 pending approvals across 2 agents → Open Approvals Center”

Layout:
- Use a 2-column grid of larger cards (comfortable scan).

#### B) “Favorites” (Owner + Viewer)
- Title: “Favorites”
- Shows favorited agents, regardless of ownership.
- Favorite is stored in local storage keyed to device.
- If owner: favorites can include your own agents too, but still keep “My Agents” section separate.

Card actions:
- **View** (always)
- **Copy Trade** (always visible, but behavior differs by state)
  - Owner: dropdown to pick destination agent (your agents)
  - Viewer/no owner: disabled with tooltip “Add an owned agent to copy trade (key link)”
- Star icon toggles favorite (filled if favorited).

Sorting within Favorites:
- Defaults to selected Sort metric (PnL, Volume, etc.)
- Still respects filters.

#### C) “All Agents” (Main Directory)
- Title: “All Agents”
- This is the full list/grid.
- Applies filters/sort.
- Pagination or infinite scroll (prefer pagination with page controls for predictable UX).

Card content same as favorites but with:
- “Watch” indicator (optional)
- “Verified” badge (optional future hook)

---

## Card Design (Grid Default)
Each Agent Card includes:

### Header Row
- Avatar + Agent Name (clickable)
- Status dot + label (Online/Offline)
- Favorite star icon (top-right)

### Primary Metrics Row (big + small)
- Primary metric: PnL (based on selected time window)
- Secondary: Win rate %
- Secondary: Volume

### Meta Row
- Strategy tags chips (2–4 max, overflow into “+2”)
- Chain icons (ETH, ARB, etc.)
- Risk badge: Low/Med/High

### Copy Trading Row (conditional)
- If agent is known to be copied a lot: “Followers: 372” (optional)
- If THIS agent is copying another: “Copying: Agent B2” chip

### Actions Row
- Button: **View**
- Button: **Copy Trade** (with dropdown caret)
  - Clicking opens a small modal/dropdown:
    - Title: “Copy this agent into…”
    - Destination agent selector (list of “My Agents”)
    - Sizing: 1.0x (dropdown: 0.25x, 0.5x, 1.0x, 2.0x)
    - Guardrails quick toggles:
      - “Use my agent limits” (default ON)
      - “Require per-trade approvals” (default ON)
    - Confirm: “Enable Copy Trading”
  - If no owner agents available:
    - Show CTA: “Add an agent via key link” → goes to Settings & Security > Access tab.

---

## Sorting & Filtering (Must-have)
### Sort Options
- PnL (default)
- Volume
- Win Rate
- Drawdown (lowest first)
- Followers (optional)
- Recently Active

### Time Window
- 24H / 7D / 30D / All-time
- Affects PnL, win rate, volume displayed and sorting.

### Filters
- Chain
- Strategy tags
- Risk
- Venue/DEX
- Status: All / Online only

### Search Behavior
Top search input filters agents by:
- Agent name
- Strategy tags
- Vault address (partial)
- Owner label (optional)
- Token focus (optional)

Search integrates with filters (AND logic).

---

## Mobile Layout (390–430px)
### Top Bar (sticky)
- Title: Explore
- Search icon opens full-width search field
- Chain selector and dark toggle in top bar

### Sections on Mobile
- My Agents becomes a collapsible section at top with a count:
  - “My Agents (3)”
- Favorites collapsible:
  - “Favorites (7)”
- All Agents list becomes single-column cards

### Filters on Mobile
- Filter chips become a single row:
  - “Filters” button opens a bottom sheet with:
    - chain
    - strategy
    - risk
    - venue
    - status
    - sort + time window
- Apply/Reset buttons at bottom of sheet.

### Copy Trade on Mobile
- “Copy Trade” opens a full-screen bottom sheet:
  - destination agent selection list
  - sizing dropdown
  - toggles
  - confirm button

---

## Dark Mode Spec (applies globally)
Uses same token system as Dashboard.

**Light**
- Background: #F6F8FC
- Surface: #FFFFFF
- Border: #E6ECF5
- Text primary: #0B1220
- Text secondary: #5B6B84
- Accent: #2563EB

**Dark**
- Background: #0B1220
- Surface: #111A2E
- Border: #22304D
- Text primary: #EAF0FF
- Text secondary: #A7B4D0
- Accent: #3B82F6

Dark mode behaviors:
- Cards rely more on borders than shadows.
- Favorite star uses high-contrast yellow/gold accent (subtle).
- Risk badges remain readable (filled chips).

---

## Component Inventory
- ExploreHeader
- FilterChipBar
- AdvancedFiltersDrawer (desktop right panel) / FiltersBottomSheet (mobile)
- SectionContainer (My Agents / Favorites / All Agents)
- AgentCard (grid)
- AgentRow (list view alternative)
- CopyTradeModal/Sheet (destination picker + sizing + toggles)
- PaginationControls (if not infinite scroll)

---

## States & Edge Cases
### Anonymous (no owner cookies)
- Hide “My Agents” section entirely.
- Copy Trade button shows disabled state with tooltip:
  - “Add an owned agent via key link to enable copy trading.”
- Favorites still works locally (optional).

### Owner with many agents
- My Agents section supports:
  - search within my agents
  - sort within my agents (optional)
  - collapsible / show first N with “View all my agents” (optional)

### Empty Results
- If filters remove all results:
  - show empty state with “Reset filters” CTA.

### Loading
- Skeleton cards for each section.
- Avoid layout shift: reserve space for sections.

---

## Navigation Outcomes
- View/Open → `/agents/{agentId}`
- Clicking “Copying: Agent X” chip navigates to that agent page (viewer mode unless owner cookie exists).

---

## Copywriting Tone
- “Explore” not “Marketplace”
- “Copy Trade” not “Invest”
- Emphasis on transparency and risk: show risk badges clearly.

End of Page #2 spec.
