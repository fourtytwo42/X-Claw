# Slice 23 Spec: Agent Spot Swap (Token->Token via Configured Router)

## Goal
Give agents a first-class one-shot "spot swap" command to trade from one ERC20 token to another via the chain's configured router (`config/chains/<chain>.json` `coreContracts.router`).

This must work transparently with the Slice 22 fee-router proxy (router may be the proxy).

## Success Criteria
1. Runtime CLI supports `xclaw-agent trade spot` and returns JSON success/error bodies.
2. The swap path uses router `getAmountsOut` to compute a net `amountOutMin` (slippage-bps applied) and then submits `swapExactTokensForTokens`.
3. Skill wrapper exposes `trade-spot <token_in> <token_out> <amount_in> <slippage_bps>`.
4. Tests cover success call-shape + at least one invalid input.
5. Canonical docs/artifacts are synced for the new command surface.

## Non-Goals
1. Multi-hop paths (this slice supports a direct 2-token path only).
2. Supporting ETH/native input/output; ERC20->ERC20 only.
3. Decoding swap outputs/events or computing realized price; we rely on on-chain tx receipts and router quoting.

## Constraints / Safety
1. Never exposes private keys/seed phrases.
2. Uses the existing local signing boundary (`cast` + local wallet store).
3. Uses chain config router address only (no direct underlying router).
4. `slippage-bps` bounded to 0..5000; `deadline-sec` bounded to 30..3600.

## Acceptance Checks
- `npm run db:parity`
- `npm run seed:reset`
- `npm run seed:load`
- `npm run seed:verify`
- `npm run build`
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

# Slice 35 Spec: Wallet-Embedded Approval Controls + Correct Token Decimals

## Goal
Move approval policy controls (Global Approval + per-token preapproval) into the wallet card on `/agents/:id`, fix token decimals formatting (notably USDC) to use observed decimals from the deposit snapshot, and remove default-collapsed UI that hides operational info.

## Success Criteria
1. `/agents/:id` wallet card shows owner-only:
   - `Approve all` toggle (Global Approval),
   - per-token preapproval buttons inline with token rows.
2. Management rail no longer contains approval policy controls (caps/risk limits remain).
3. USDC and other ERC-20 balances format correctly using snapshot decimals (no hardcoded USDC=6).
4. Audit log/details is expanded by default.

## Non-Goals
1. No schema/migration changes.
2. No change to approval queue semantics or trade lifecycle.
3. No dependency additions.

## Acceptance Checks
- `npm run db:parity`
- `npm run seed:reset`
- `npm run seed:load`
- `npm run seed:verify`
- `npm run build`
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

# Slice 36 Spec: Remove Step-Up Authentication (Management Cookie Only)

## Goal
Remove the step-up mechanism entirely so a valid management session cookie + CSRF is sufficient for all management actions.

## Success Criteria
1. `/agents/:id` has no step-up prompt, messaging, or “Session and Step-up” UI.
2. No management endpoint requires `xclaw_stepup` and `requireStepupSession` is removed.
3. Step-up endpoints are removed (404).
4. Runtime and skill no longer expose `stepup-code`.
5. DB no longer has `stepup_challenges`, `stepup_sessions`, or `stepup_issued_for`.

## Non-Goals
1. No replacement second factor mechanism.
2. No dependency additions.

## Acceptance Checks
- `npm run db:parity`
- `npm run seed:reset`
- `npm run seed:load`
- `npm run seed:verify`
- `npm run build`
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

# Slice 25 Spec: Agent Skill UX Upgrade (Security + Reliability + Contract Fixes)

## Goal
Harden the Python-first X-Claw agent skill UX based on Worksheets A-H:
- Redact sensitive owner-link magic URLs by default.
- Make faucet responses explicitly pending-aware with next-step guidance.
- Fix limit-order create schema mismatches caused by sending `expiresAt: null`.

## Success Criteria
1. `owner-link` output does not print raw `managementUrl` by default; opt-in via `XCLAW_SHOW_SENSITIVE=1`.
2. `faucet-request` success JSON includes `pending`, `recommendedDelaySec`, and `nextAction`.
3. `limit-orders-create` omits `expiresAt` when not provided and succeeds against a healthy server.
4. Docs/artifacts remain synchronized: source-of-truth + tracker + roadmap + skill docs.
5. Tests cover success + at least one failure-path assertion for surfaced API validation details.

## Non-Goals
1. Waiting for faucet tx receipts by default (we provide guidance instead).
2. Redesigning the server-side limit-order schema (payload is already canonical; fix is client-side).
3. Adding new dependencies.

## Constraints / Safety
1. Treat stdout as loggable/transcribed; redact sensitive fields by default.
2. Preserve runtime separation: skill wrapper delegates to local `xclaw-agent`.

## Acceptance Checks
- `npm run db:parity`
- `npm run seed:reset`
- `npm run seed:load`
- `npm run seed:verify`
- `npm run build`
- `python3 -m pytest apps/agent-runtime/tests` (fallback: `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`)

---

# Slice 26 Spec: Agent Skill Robustness Hardening (Timeouts + Identity + Single-JSON)

## Goal
Harden the agent runtime/skill command surface to prevent hangs, improve identity/health clarity, and standardize parseable JSON behavior for automation.

## Success Criteria
1. Wrapper enforces timeout (`XCLAW_SKILL_TIMEOUT_SEC`, default 240) and returns structured `code=timeout`.
2. Runtime cast/RPC operations are timeout-bounded with actionable timeout codes (`rpc_timeout`, `tx_receipt_timeout`).
3. `status` includes `agentName` best-effort and remains resilient when profile lookup fails.
4. `wallet-health` includes `nextAction` + `actionHint` on ok responses.
5. `faucet-request` surfaces `retryAfterSec` from server rate-limit details when available.
6. `limit-orders-run-loop` emits one JSON object per invocation.
7. `trade-spot` exposes exact + pretty gas cost ETH fields (`totalGasCostEthExact`, `totalGasCostEthPretty`) while preserving compatibility.

## Non-Goals
1. No changes to wallet custody boundaries.
2. No dependency additions.
3. No Node/npm requirement introduced for agent runtime command invocation.

## Constraints / Safety
1. No secrets in outputs/logs.
2. AI output remains untrusted input; retain strict command/input validation.
3. Keep source-of-truth + tracker + roadmap + command contract in sync.

## Acceptance Checks
- `npm run db:parity`
- `npm run seed:reset`
- `npm run seed:load`
- `npm run seed:verify`
- `npm run build`
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`
- `python3 -m unittest apps/agent-runtime/tests/test_wallet_core.py -k wallet_health_includes_next_action_on_ok -v`

## Close-Out Session (2026-02-14)
- Objective: close Slice 26 using evidence-only updates (no new behavior scope).
- Expected touched files allowlist:
  - `spec.md`
  - `tasks.md`
  - `acceptance.md`
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`

## Management Incident Follow-up (2026-02-14)
- Objective: fix management page incident class where HTML loads but management styling is missing due to static chunk mismatch, and clarify host-scoped management bootstrap behavior.
- In scope:
  - stronger bootstrap/unauthorized UX guidance on `/agents/:id`,
  - static-asset verification script for deploy/cache integrity,
  - runbook + canonical contract wording updates.
- Non-goals:
  - no changes to one-time owner-link semantics,
  - no relaxation of host-scoped cookie/session security model.

---

# Slice 33 Spec: MetaMask-Like Agent Wallet UX + Simplified Approvals (Global + Per-Token)

## Goal
Redesign `/agents/:id` to feel like a MetaMask-style wallet (wallet header + assets + unified activity feed) and simplify approvals to:
- Global Approval toggle (policy-driven).
- Per-token preapproval toggles evaluated on `tokenIn` only.
- No pair approvals in the active product surface.

## Success Criteria
1. Server:
   - `POST /api/v1/trades/proposed` persists initial status `approved|approval_pending` based on global/tokenIn preapproval policy.
   - initial event emitted matches status (`trade_approved` or `trade_approval_pending`).
   - copy lifecycle follower trade creation uses the same approval semantics.
2. Runtime:
   - `trade spot` is server-first: propose before on-chain execution, wait when pending, execute only if approved, surface rejection reason.
3. UI (`/agents/:id`):
   - public view is wallet-first with a MetaMask-like wallet header + assets list.
   - trades + activity are presented as a unified MetaMask-like activity feed.
   - owner-only management rail includes approvals (approve/reject with reason) and policy toggles (Global Approval + per-token).
4. Deprecated legacy:
   - pair/global approval scope UI is removed.
   - `POST /api/v1/management/approvals/scope` is deprecated and not used by UI.
5. Docs/contracts are synced (source-of-truth, openapi, tracker/roadmap, context/spec/tasks/acceptance).

## Non-Goals
1. New auth model or route split for management.
2. Applying approvals to read-only wallet commands.
3. Introducing a separate “allowed tokens” safety allowlist beyond the preapproval list.

## Acceptance Checks
- `npm run db:parity`
- `npm run seed:reset`
- `npm run seed:load`
- `npm run seed:verify`
- `npm run build`
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

# Slice 34 Spec: Telegram Approvals (Inline Button Approve) + Web UI Sync

## Goal
Add Telegram as an optional approval surface that stays aligned with the existing `/agents/:id` approvals UI.

When a trade becomes `approval_pending` and the owner's active OpenClaw conversation is Telegram, the runtime sends a Telegram message with an **Approve** inline button. Clicking it approves the trade server-side (strict button execution, no LLM mediation), deletes the Telegram message, and the web approvals queue reflects the approval.

## Success Criteria
1. Owner can enable/disable Telegram approvals per chain on `/agents/:id` (enable is step-up gated; disable is not).
2. Runtime sends Telegram approval prompt only when:
   - Telegram approvals are enabled for agent+chain, and
   - OpenClaw last active channel is Telegram (`lastChannel == telegram`).
3. Telegram button click:
   - calls X-Claw channel approval endpoint with Bearer secret,
   - transitions trade `approval_pending -> approved` idempotently,
   - deletes Telegram prompt message on success.
4. Web approval first:
   - runtime deletes Telegram prompt best-effort when it observes approval,
   - plus `xclaw-agent approvals sync` can remove stale prompts.
5. Docs/contracts remain synchronized (source-of-truth/openapi/schemas/tracker/roadmap/context/spec/tasks/acceptance).

## Non-Goals
1. Reject-in-Telegram (reject remains web-only).
2. WhatsApp/Slack/Discord approval buttons.
3. New generalized auth model for management actions outside approvals.

## Constraints / Security
1. Strict: approval execution must come from Telegram inline button callback handler (no LLM/tool mediation).
2. Server never stores raw secrets; only hashes.
3. Channel decision endpoint uses Bearer secret and does not use management cookies/CSRF.

## Acceptance Checks
- `npm run db:parity`
- `npm run seed:reset`
- `npm run seed:load`
- `npm run seed:verify`
- `npm run build`
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

# Slice 32 Spec: Per-Agent Chain Enable/Disable (Owner-Gated, Chain-Scoped Ops)

## Goal
Add an owner-managed per-agent, per-chain enable/disable switch. If a chain is disabled:
- agent runtime blocks trade and `wallet-send` on that chain with structured `code=chain_disabled`
- server rejects trade/limit-order execution paths on that chain with a policy-style error
- owner withdraw remains available for safety recovery
- enabling chain access requires step-up; disabling does not

## Success Criteria
1. DB has `agent_chain_policies` with unique `(agent_id, chain_key)` and audited `updated_by_management_session_id`.
2. API:
   - `POST /api/v1/management/chains/update` upserts chain access.
   - `GET /api/v1/management/agent-state` accepts optional `chainKey` and returns `chainPolicy`.
   - `GET /api/v1/agent/transfers/policy` returns `chainEnabled` fields.
3. Enforcement:
   - Server blocks trades/limit-orders when chain disabled (`code=chain_disabled`).
   - Runtime blocks `trade` and `wallet-send` when owner chain access disabled.
4. UI:
   - `/agents/:id` management rail shows “Chain Access” toggle for the active chain selector context.
   - Enabling prompts step-up only when required (event-driven).
5. Docs/artifacts are synced (source-of-truth, openapi, schemas, tracker/roadmap, context/spec/tasks/acceptance).

## Non-Goals
1. Auto-cancelling open limit orders on disable (orders are frozen; owner can cancel manually).
2. Blocking owner withdraw when chain is disabled.

## Acceptance Checks
- `npm run db:parity`
- `npm run seed:reset`
- `npm run seed:load`
- `npm run seed:verify`
- `npm run build`
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

## Management Incident Follow-up (2026-02-14, gate hardening)
- Objective: make static-asset verification executable as an explicit release-gate command and re-confirm production mismatch evidence.
- In scope:
  - add `npm run ops:verify-static-assets`,
  - wire runbook/roadmap/tracker to this release-gate command,
  - capture fresh live verification evidence.
- Non-goals:
  - no API/contract expansion,
  - no token/session semantic changes,
  - no direct production deploy from this workspace.

## Agent Sync Delay UX Refinement (2026-02-14)
- Objective: prevent idle-but-healthy agents from being shown as sync-delayed.
- In scope:
  - stale/sync-delay checks switch from `last_activity_at` to `last_heartbeat_at`,
  - stale threshold increases from 60s to 180s in agent directory/profile and ops heartbeat-miss summary.
- Non-goals:
  - no trading/runtime command behavior changes,
  - no auth/session behavior changes.

---

# Slice 27 Spec: Responsive + Multi-Viewport UI Fit (Phone + Tall + Wide)

## Goal
Upgrade `apps/network-web` responsive behavior and styling so `/`, `/agents`, `/agents/:id`, and `/status` fit cleanly on phone, tall-screen, desktop, and wide-monitor viewports while preserving canonical X-Claw semantics.

## Success Criteria
1. No critical overflow/clipping of core controls/content at 360px width.
2. Desktop-table/mobile-card pattern is implemented for:
   - dashboard leaderboard (`/`)
   - agents directory listing (`/agents`)
   - trades list on agent profile (`/agents/:id`)
3. `/agents/:id` management controls remain usable on phone and sticky-rail behavior remains on desktop.
4. `/status` diagnostic panels collapse to readable mobile card layouts.
5. Dark/light themes and canonical status vocabulary remain unchanged.
6. Required gates pass and viewport verification evidence is recorded.

## Non-Goals
1. No API/OpenAPI/schema changes.
2. No runtime/agent command-surface changes.
3. No dependency additions.

## Constraints / Safety
1. Preserve one-site model (public and authorized management on `/agents/:id`).
2. Keep exact status vocabulary unchanged: `active`, `offline`, `degraded`, `paused`, `deactivated`.
3. Keep management trust boundaries and action semantics unchanged.

## Acceptance Checks
- `npm run db:parity`
- `npm run seed:reset`
- `npm run seed:load`
- `npm run seed:verify`
- `npm run build`
- Manual viewport checks:
  - 360x800
  - 390x844
  - 768x1024
  - 900x1600
  - 1440x900
  - 1920x1080

---

# Slice 28 Spec: Mock Mode Deprecation (Network-Only User Surface, Base Sepolia)

## Goal
Soft-deprecate mock trading so user-facing web and agent skill/runtime operate network-only on Base Sepolia while backend contract/storage compatibility remains intact for this slice.

## Success Criteria
1. No mock/real mode controls remain on dashboard/agents/profile user surfaces.
2. User-facing copy and skill guidance use network/base-sepolia wording only.
3. Public read APIs preserve `mode` query compatibility but return effective real/network-only data.
4. Historical mock records remain stored but are excluded from user-facing result paths.
5. Runtime/skill mode-bearing flows reject `mock` with structured `unsupported_mode` and actionable hint.
6. Docs/openapi/tracker/roadmap/handoff artifacts remain synchronized.

## Non-Goals
1. No hard DB enum or schema removal in this slice.
2. No destructive migration of existing mock records.
3. No dependency additions.

## Constraints / Safety
1. Preserve runtime separation (Node/Next.js vs Python-first agent runtime).
2. Preserve canonical status vocabulary (`active`, `offline`, `degraded`, `paused`, `deactivated`).
3. Keep API request shape compatibility where documented for mode params.

## Acceptance Checks
- `npm run db:parity`
- `npm run seed:reset`
- `npm run seed:load`
- `npm run seed:verify`
- `npm run build`
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`
- `rg -n "\bmock\b|Mock vs Real|mode toggle" apps/network-web/src skills/xclaw-agent`

---

# Slice 29 Spec: Dashboard Chain-Scoped UX + Activity Detail + Chat-Style Room

## Goal
Refine dashboard clarity for the current network-only release by removing redundant chain labels, presenting a chat-like trade room, and enriching live activity with what-traded-for-what details.

## Success Criteria
1. Dashboard no longer shows redundant chain-name chip text in dashboard controls.
2. Dashboard trade room and live activity display active-chain entries only (Base Sepolia).
3. Live activity cards show pair detail (`pair`) or fallback token direction (`token_in -> token_out`).
4. Trade room uses a chat-like message card design and remains responsive on phone and wide screens.
5. Canonical docs/artifacts stay synchronized.

## Non-Goals
1. No multi-chain selector reintroduction on dashboard.
2. No changes to trade execution/runtime behavior.
3. No dependency additions.

## Constraints / Safety
1. Preserve canonical status vocabulary (`active`, `offline`, `degraded`, `paused`, `deactivated`).
2. Preserve API route compatibility; payload additions are optional/append-only.
3. Keep dark/light theme support and responsive requirements from Slice 27.

## Acceptance Checks
- `npm run db:parity`
- `npm run seed:reset`
- `npm run seed:load`
- `npm run seed:verify`
- `npm run build`

---

# Slice 30 Spec: Owner-Managed Daily Trade Caps + Usage Visibility (Trades Only)

## Goal
Add owner-managed per-agent, per-chain UTC-day trade caps (USD + filled-trade count), expose owner-only usage progress on `/agents/:id`, and enforce these caps in both runtime and server trade paths.

## Success Criteria
1. Owner policy supports `dailyCapUsdEnabled`, `dailyTradeCapEnabled`, and `maxDailyTradeCount` in addition to existing fields.
2. Runtime enforces trade caps for `trade spot`, `trade execute`, and limit-order real fills, with cached fail-closed behavior.
3. Server enforces cap checks on `POST /api/v1/trades/proposed`, `POST /api/v1/limit-orders`, and `POST /api/v1/limit-orders/{orderId}/status` (filled path).
4. Runtime reports usage via idempotent `POST /api/v1/agent/trade-usage`, with queue/replay on outage.
5. `/agents/:id` management rail shows cap toggles/values and UTC-day usage (owner-only).
6. Canonical docs and schemas remain synchronized.

## Non-Goals
1. No cap accounting changes for `wallet-send` / `wallet-send-token`.
2. No public exposure of owner cap values/usage.
3. No dependency additions.

## Constraints / Safety
1. UTC day is canonical reset boundary.
2. Cap accounting is scoped to `agent + chain + utc_day`.
3. If cap is disabled, that cap does not block execution even if a value is present.

## Acceptance Checks
- `npm run db:parity`
- `npm run seed:reset`
- `npm run seed:load`
- `npm run seed:verify`
- `npm run build`
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

# Slice 31 Spec: Agents + Agent Management UX Refinement (Operational Clean)

## Goal
Refine `/agents` and `/agents/:id` into a production-quality operations surface while preserving the one-site model, existing management behavior, and responsive constraints.

## Success Criteria
1. `/agents` renders card-first directory UX with KPI summaries and optional desktop table fallback.
2. `GET /api/v1/public/agents` supports optional `includeMetrics=true` and returns nullable `latestMetrics` per row.
3. `GET /api/v1/public/activity` supports optional `agentId` for server-side filtering.
4. `/agents/:id` keeps long-scroll structure and improves public trades/activity readability.
5. `/agents/:id` management rail is regrouped by operational priority and uses progressive disclosure for advanced sections.
6. Existing management actions continue to work without contract regressions.

## Non-Goals
1. No route split/tabs architecture change for profile management.
2. No auth/session model changes.
3. No DB schema/migration changes.
4. No dependency additions.

## Constraints / Safety
1. Preserve exact status vocabulary (`active`, `offline`, `degraded`, `paused`, `deactivated`).
2. Keep management controls authorized-only under existing session guard.
3. Preserve sticky management rail desktop behavior and stacked mobile behavior.

## Acceptance Checks
- `npm run db:parity`
- `npm run seed:reset`
- `npm run seed:load`
- `npm run seed:verify`
- `npm run build`
