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

# Slice 37 Spec: Telegram Approvals Without Extra Secret (Skill-Authoritative, Web + Telegram OR)

## Goal
Allow Telegram inline-button approvals without requiring any additional secret/config beyond the existing `xclaw-agent` skill API key.

## Success Criteria
1. `/agents/:id` owner can enable/disable Telegram approvals per chain with management cookie + CSRF, with no secret issuance/display.
2. When a trade is `approval_pending` and OpenClaw last active channel is Telegram, runtime sends an approval prompt with inline Approve button.
3. Clicking Approve in Telegram transitions the trade `approval_pending -> approved` using agent auth (`POST /api/v1/trades/:tradeId/status`) and deletes the Telegram prompt.
4. Approving in the web UI first still converges: runtime deletes any Telegram prompt on observing the status transition (best-effort + `approvals sync`).
5. OpenAPI + shared schemas remain synchronized (no `/api/v1/channel/approvals/decision`).

## Non-Goals
1. No reject-in-Telegram (web-only reject remains).
2. No new auth model; this accepts agent-auth as sufficient for Telegram approve transitions.
3. No DB migration required.

## Acceptance Checks
- `npm run db:parity`
- `npm run seed:reset`
- `npm run seed:load`
- `npm run seed:verify`
- `npm run build`
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

# Slice 38 Spec: Telegram Approval Prompt Details + Pending Approval De-Dupe (No Spam)

## Goal
Make Telegram approval prompts self-describing (swap details) and stop repeated identical trade requests from creating multiple `approval_pending` trades/prompt spam. Identical pending approvals must reuse the same `tradeId` until resolved.

## Success Criteria
1. Runtime `trade spot` persists a deterministic pending-intent key and reuses existing `tradeId` when status is `approval_pending`.
2. Approval wait timeout is 30 minutes; timeout guidance instructs approve then re-run to resume without creating a new approval.
3. Telegram prompt message text includes swap summary: `<amount> <tokenInSymbol> -> <tokenOutSymbol>`, plus `Chain` and `Trade` lines.
4. Telegram message is deleted on approve click (OpenClaw inline callback), and runtime clears local prompt state once trade leaves `approval_pending`.

## Non-Goals
1. No reject-in-Telegram.
2. No new server endpoints or schemas.

## Acceptance Checks
- `npm run db:parity`
- `npm run seed:reset`
- `npm run seed:load`
- `npm run seed:verify`
- `npm run build`
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

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

# Slice 39 Spec: Approval Amount Visibility + Gateway Telegram Callback Reliability

## Goal
Improve `/agents/:id` operational readability by showing amounts in approvals and activity, and ensure Telegram Approve buttons reliably perform the approval transition (no LLM mediation) on the deployed OpenClaw gateway.

## Success Criteria
1. Approval Queue shows `amountIn tokenIn -> tokenOut` (best-effort symbol mapping).
2. Activity feed trade rows show amountIn and (when available) amountOut.
3. OpenClaw gateway intercepts `xappr|a|...` callbacks, calls `POST /api/v1/trades/:tradeId/status` with agent-auth + Idempotency-Key, and deletes the Telegram approval message on success.
4. Runtime outbox replay does not block local input validation failures.

## Acceptance Checks
- `npm run db:parity`
- `npm run seed:reset`
- `npm run seed:load`
- `npm run seed:verify`
- `npm run build`
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

# Slice 40 Spec: OpenClaw Patch Auto-Apply (Portable, No Restart Loops)

## Goal
Make Telegram approval callbacks portable across users by auto-applying the OpenClaw gateway patch during install/update and on next skill use after OpenClaw updates, without causing restart loops.

## Success Criteria
1. Patch is applied idempotently (no-op when already present).
2. Patch targeting is dynamic (no hardcoded hashed `dist/loader-*.js` filename).
3. Gateway restart happens only when a new patch is applied and is guarded by a cooldown + lock.
4. After an OpenClaw update overwrites the bundle, the next skill use re-applies and restarts once.

## Acceptance Checks
- `npm run db:parity`
- `npm run seed:reset`
- `npm run seed:load`
- `npm run seed:verify`
- `npm run build`
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

# Slice 41 Spec: Telegram Approve Button Reliability (Patch Correct Gateway Bundle)

## Goal
Fix Telegram Approve buttons not approving trades by ensuring the OpenClaw gateway patch targets the bundle(s) actually executed in `gateway` mode (notably `dist/reply-*.js` imported by `dist/index.js`), not just `dist/loader-*.js`.

## Success Criteria
1. Patcher detects and patches all `dist/*.js` bundles that contain the Telegram `bot.on("callback_query"` handler used by the gateway runtime (including `reply-*.js`).
2. Clicking Telegram Approve triggers agent-auth `POST /api/v1/trades/:tradeId/status` to transition `approval_pending -> approved`.
3. Telegram approval message is deleted after approval click (or converged 409: already approved/filled).
4. Patch is idempotent and uses stable marker/replace semantics to avoid duplicated intercept blocks.

## Acceptance Checks
- `npm run db:parity`
- `npm run seed:reset`
- `npm run seed:load`
- `npm run seed:verify`
- `npm run build`
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

# Slice 42 Spec: Telegram Approve+Deny + Approval Decision Chat Feedback + Safer De-Dupe

## Goal
Refine the approvals UX and semantics:
- only de-dupe identical trade requests while the prior trade is still `approval_pending`,
- add Telegram Deny alongside Approve,
- and post decision feedback into the active Telegram chat with details (and reason on deny).

## Success Criteria
1. Runtime reuses an identical tradeId only while the trade is `approval_pending`; once it resolves (approved/rejected/filled/etc), a repeated identical request proposes a new tradeId.
2. Telegram prompts show two inline buttons: Approve and Deny (no color support).
3. Clicking either button transitions the trade status (`approval_pending -> approved|rejected`), deletes the prompt message, and posts a confirmation message into the same Telegram chat with details.
4. When web approve/deny happens while runtime is waiting, runtime posts a confirmation message into the active Telegram chat with details and reason on deny.

## Acceptance Checks
- `npm run db:parity`
- `npm run seed:reset`
- `npm run seed:load`
- `npm run seed:verify`
- `npm run build`
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

# Slice 43 Spec: Telegram Callback Idempotency Fix (No `idempotency_conflict`)

## Goal
Prevent Telegram decision callbacks from failing with `idempotency_conflict` on repeated clicks/retries.

## Success Criteria
1. OpenClaw gateway patch uses callback-unique idempotency key: `Idempotency-Key: tg-cb-<callbackId>`.
2. The `at` field for `/api/v1/trades/:tradeId/status` is derived deterministically from Telegram callback/query timestamps.
3. Clicking Approve/Deny does not produce `idempotency_conflict`.

## Non-Goals
1. No new server endpoints or schemas.
2. No UI redesign.

## Acceptance Checks
- `npm run db:parity`
- `npm run seed:reset`
- `npm run seed:load`
- `npm run seed:verify`
- `npm run build`
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

# Slice 44 Spec: Faster Approval Resume (Lower Poll Interval)

## Goal
Reduce perceived latency after approve/deny (Telegram or web) by tightening runtime polling while waiting for `approval_pending`.

## Success Criteria
1. Runtime polls trade status every 1 second while waiting for approval.
2. No changes to trust boundaries (Telegram callback still updates trade status; runtime remains the executor).

## Acceptance Checks
- `npm run db:parity`
- `npm run seed:reset`
- `npm run seed:load`
- `npm run seed:verify`
- `npm run build`
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

# Slice 45 Spec: Inline Telegram Approval Buttons (No Extra Prompt Message)

## Goal
Reduce Telegram approval UX noise by attaching Approve/Deny buttons to the same queued trade message (wallet summary), instead of emitting a second Telegram message for the prompt.

## Success Criteria
1. Runtime does not send out-of-band Telegram prompt messages by default.
2. Telegram queued message includes OpenClaw inline-buttons directive (`[[buttons: ...]]`) with Approve/Deny callbacks.
3. Clicking either button still converges with web approvals (server status transitions remain canonical).

## Acceptance Checks
- `npm run db:parity`
- `npm run seed:reset`
- `npm run seed:load`
- `npm run seed:verify`
- `npm run build`
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

# Slice 46 Spec: Auto-Attach Telegram Approval Buttons To Queued Message

## Goal
Guarantee Telegram queued `approval_pending` trade messages always have Approve/Deny buttons without relying on the model to emit `[[buttons: ...]]`.

## Success Criteria
1. OpenClaw gateway patch detects the queued message (by `Status: approval_pending` and `Trade ID: trd_...`) and attaches inline keyboard on send.
2. No second Telegram prompt message is required for buttons to appear.

## Acceptance Checks
- `npm run db:parity`
- `npm run seed:reset`
- `npm run seed:load`
- `npm run seed:verify`
- `npm run build`
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

# Slice 47 Spec: Fix Telegram Queued Buttons Attach Point (Agent Reply Send Path)

## Goal
Fix missing Telegram buttons on the agent’s queued `approval_pending` message by patching the Telegram send path used for agent replies (`sendTelegramText(bot, ...)`).

## Success Criteria
1. Queued message that includes `Status: approval_pending` + `Trade ID: trd_...` renders Approve/Deny buttons on the same message in Telegram.
2. Works for agent replies (not only `openclaw message send`).

## Acceptance Checks
- `npm run db:parity`
- `npm run seed:reset`
- `npm run seed:load`
- `npm run seed:verify`
- `npm run build`
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

# Slice 48 Spec: Queued Approval Buttons v3 Upgrade + Logging (Debuggable)

## Goal
Upgrade the OpenClaw queued-buttons injection from v2 to v3 so it is resilient to formatting differences (normalized text) and emits gateway logs when buttons are attached or skipped.

## Success Criteria
1. For queued `approval_pending` agent replies, Telegram shows Approve/Deny buttons on the same message.
2. Gateway logs include `xclaw: queued buttons attached ...` when buttons are attached.
3. If buttons are not attached, gateway logs include a `xclaw: queued buttons skipped ...` reason (e.g. missing tradeId or existing replyMarkup).

## Acceptance Checks
- `npm run db:parity`
- `npm run seed:reset`
- `npm run seed:load`
- `npm run seed:verify`
- `npm run build`
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

# Slice 49 Spec: OpenClaw Patcher Safety (Syntax Check + Targeted Bundle)

## Goal
Ensure `skills/xclaw-agent/scripts/openclaw_gateway_patch.py` cannot brick OpenClaw: patch only canonical gateway bundle(s) and validate patched JS syntax before writing.

## Success Criteria
1. Patcher only modifies `dist/reply-*.js` (and does not touch other dist bundles).
2. Patcher runs `node --check` on patched output and refuses to write invalid JS.
3. If syntax check fails, patcher returns a structured error and does not restart the gateway.

## Acceptance Checks
- `npm run db:parity`
- `npm run seed:reset`
- `npm run seed:load`
- `npm run seed:verify`
- `npm run build`
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

# Slice 50 Spec: Telegram Decision Feedback Routed Through Agent (No Direct Gateway Ack)

## Goal
After Telegram approve/deny, route the decision through the agent message pipeline (so the agent informs the user) instead of the gateway posting a raw ack message.

## Success Criteria
1. Clicking Telegram Approve/Deny still performs the strict server-side status transition (no LLM mediation).
2. The follow-up message comes from the agent pipeline (triggered by a synthetic inbound message with instructions).
3. If the synthetic pipeline call fails, a minimal fallback confirmation message is posted to the chat.

## Acceptance Checks
- `npm run db:parity`
- `npm run seed:reset`
- `npm run seed:load`
- `npm run seed:verify`
- `npm run build`
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

# Slice 51 Spec: Policy Approval Requests (Token Preapprove + Approve All) With Web + Telegram Buttons

## Goal
Allow the agent to request owner approval for policy changes (token preapproval and global approval), using the same web + Telegram button approval surfaces as trade approvals.

## Success Criteria
1. Agent can create a policy approval request (token preapprove or global approve-all enable).
2. Pending requests appear on `/agents/:id` with Approve/Deny.
3. Telegram queued message can receive Approve/Deny inline buttons (auto-attach) and clicking them applies the decision.
4. After Telegram approve/deny, decision feedback is routed into the agent pipeline (synthetic message + instructions) so the agent informs the user.

## Acceptance Checks
- `npm run db:parity`
- `npm run seed:reset`
- `npm run seed:load`
- `npm run seed:verify`
- `npm run build`
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

# Slice 52 Spec: Policy Approval Prompts (Agent-Ready queuedMessage + Instructions)

## Goal
Make policy approval request tool outputs “agent-ready” so the agent reliably tells the owner what to do and Telegram queued-message button auto-attach works without brittle formatting.

## Success Criteria
1. Runtime policy approval request commands return:
   - `queuedMessage` including `Status: approval_pending` and `Approval ID: ppr_...` verbatim.
   - `agentInstructions` telling the agent to paste the queued message verbatim into the active chat.
2. Unit tests assert `queuedMessage` contains required lines.

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
