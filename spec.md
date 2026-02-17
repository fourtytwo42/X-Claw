# Slice 84 Spec: Multi-Network Faucet Parity (Base Sepolia + Kite Testnet)

## Goal
Enable chain-aware faucet support across Base Sepolia and Kite AI testnet with explicit per-request asset selection and discoverable faucet capabilities.

## Non-goals
1. No faucet support for Base mainnet or Kite mainnet.
2. No custody/signing model changes.
3. No management UI faucet controls in this slice.

## Locked scope
1. Extend `POST /api/v1/agent/faucet/request` for `chainKey=base_sepolia|kite_ai_testnet`.
2. Add optional `assets[]` selector (`native|wrapped|stable`) with default to all assets.
3. Add `GET /api/v1/agent/faucet/networks` capability endpoint.
4. Extend runtime CLI with `faucet-networks` and `faucet-request --asset ...`.
5. Extend skill wrapper with `faucet-networks` and optional chain/assets for `faucet-request`.
6. Sync OpenAPI/schemas/source-of-truth/tracker/roadmap/handoff artifacts.

## Acceptance checks
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`
- `npm run db:parity`
- `npm run seed:reset`
- `npm run seed:load`
- `npm run seed:verify`
- `npm run build`
- `pm2 restart all`

---

# Slice 83 Spec: Kite AI Testnet Parity (Runtime + Web + DEX + x402)

## Goal
Enable `kite_ai_testnet` as a first-class chain option across runtime and web so agents can perform wallet, trade, limit-order, tracked-agent, and hosted x402 metadata flows with parity to Base Sepolia.

## Non-goals
1. No custody changes (private keys stay agent-local).
2. No `kite_ai_mainnet` enablement in this slice.
3. No faucet expansion beyond Base Sepolia.

## Locked scope
1. Add chain config `config/chains/kite_ai_testnet.json` with locked RPC/explorer/DEX/token constants.
2. Enable `kite_ai_testnet` in `config/x402/networks.json`; keep `kite_ai_mainnet` disabled.
3. Add runtime DEX adapter abstraction with Kite adapter selection by chain.
4. Ensure runtime command families accept `--chain kite_ai_testnet`.
5. Ensure web chain selectors include `Kite AI Testnet`.
6. Ensure chain validation/hints include Kite where chain-config-backed.
7. Preserve existing Base behavior and Base-only faucet response semantics.

## Acceptance checks
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`
- `python3 -m unittest apps/agent-runtime/tests/test_x402_runtime.py -v`
- `python3 -m unittest apps/agent-runtime/tests/test_dex_adapter.py -v`
- `npm run db:parity`
- `npm run seed:reset`
- `npm run seed:load`
- `npm run seed:verify`
- `npm run build`
- `pm2 restart all`

---

# Slice 81 Spec: Explore v2 Full Flush (No Placeholders)

## Goal
Deliver full-stack Explore v2 with DB-backed strategy/risk/venue metadata, functional filters, verified/follower enrichments, and server-driven filtering/sorting/pagination.

## Non-goals
1. No Explore-only public route family (extend existing public routes instead).
2. No public write path for metadata.
3. No custody/auth boundary changes.

## Locked scope
1. Add `agent_explore_profile` migration and constraints/indexes.
2. Extend:
   - `GET /api/v1/public/agents`
   - `GET /api/v1/public/leaderboard`
3. Add owner-managed metadata APIs:
   - `GET /api/v1/management/explore-profile?agentId=...`
   - `PUT /api/v1/management/explore-profile`
4. Remove Explore placeholder controls/messages and make strategy/venue/risk/advanced filters functional.
5. Add URL-state sync for filters/sort/window/page/section.
6. Add verified badge + follower-rich metadata to Explore cards.

## Acceptance checks
- `npm run db:parity`
- `npm run seed:reset`
- `npm run seed:load`
- `npm run seed:verify`
- `npm run build`
- `pm2 restart all`

---

# Slice 80 Spec: Hosted x402 Web Integration + Agent-Originated Send

## Goal
Implement hosted x402 receive/payment visibility in `apps/network-web` and keep outbound x402 execution agent-originated in runtime/wallet.

## Non-goals
1. No private-key custody in web/server.
2. No removal of runtime x402 command surface.
3. No network-web bypass of runtime signing.

## Locked scope
1. Hosted payer endpoint at `/api/v1/x402/pay/{agentId}/{linkToken}` with `402|200|410` behavior.
2. Management x402 read surfaces:
   - `/api/v1/management/x402/payments`
   - `/api/v1/management/x402/receive-link`
3. Agent-auth x402 mirror surfaces:
   - `/api/v1/agent/x402/outbound/proposed`
   - `/api/v1/agent/x402/outbound/mirror`
   - `/api/v1/agent/x402/inbound/mirror`
4. Reuse transfer approval queue with `approval_source=x402` and `xfr_...` IDs.
5. `/agents/[agentId]` merges x402 entries into wallet timeline and includes hosted receive-link panel.
6. Loopback self-pay is standard flow (agent pays its own hosted endpoint).

---

# Slice 79 Spec: Agent-Skill x402 Send/Receive Runtime (No Webapp Integration Yet)

## Goal
Implement Python-first x402 runtime/skill pay flows with hosted website receive URL creation (no local tunnel/cloudflared path).

## Success Criteria
1. Runtime exposes x402 command group:
   - `receive-request`
   - `pay|pay-resume|pay-decide`
   - `policy-get|policy-set`
   - `networks`
2. Skill wrapper exposes corresponding `x402-*` commands plus `request-x402-payment` hosted receive shortcut.
3. Runtime payment approvals use deterministic `xfr_...` IDs and locked statuses:
   - `proposed`, `approval_pending`, `approved`, `rejected`, `executing`, `filled`, `failed`.
4. Local state files exist and are used:
   - `~/.xclaw-agent/pending-x402-pay-flows.json`
   - `~/.xclaw-agent/x402-policy.json`
5. x402 network config enforces enabled networks (`base_sepolia`, `base`) and fails closed for disabled networks (`kite_ai_testnet`, `kite_ai_mainnet`).
6. Installer generates POSIX + Windows (`.cmd` and `.ps1`) launchers and does not require cloudflared for receive setup.

## Non-Goals
1. No server-side wallet custody changes.
2. No Kite network enablement in active runtime behavior for this slice.

## Constraints / Safety
1. Keep wallet signing/settlement local in agent runtime only.
2. No private key export in skill/runtime output.
3. Validate URL/network/facilitator inputs and fail closed on invalid values.
4. Preserve Python-first runtime separation for agent/OpenClaw surface.

## Hosted Receive Delta
1. Local tunnel receive bootstrap is removed from runtime/skill surface.
2. `request-x402-payment` creates hosted receive requests through website API.
3. Installer has no `cloudflared` dependency for x402 receive flow.

## Acceptance Checks
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`
- `python3 -m unittest apps/agent-runtime/tests/test_x402_runtime.py -v`
- `python3 -m unittest apps/agent-runtime/tests/test_x402_skill_wrapper.py -v`
- `npm run db:parity`
- `npm run seed:reset`
- `npm run seed:load`
- `npm run seed:verify`
- `npm run build`
- `pm2 restart all` (after successful build, when PM2 is available)

---

# Slice 77 Spec: Agent Wallet Page iPhone/MetaMask-Style Refactor (`/agents/:id`)

## Goal
Refactor `/agents/:id` into a wallet-native iPhone/MetaMask-style experience while preserving the dashboard sidebar shell, owner/viewer boundaries, and existing API contracts.

## Success Criteria
1. `/agents/:id` preserves dashboard sidebar shell framing.
2. Page is wallet-first with compact utility bar, wallet header, and KPI chip row.
3. Core sections render in wallet workflow order:
   - Assets & Approvals
   - Wallet Activity
   - Approval History
   - Withdraw
   - Copy relationships (list + delete only)
   - Limit Orders
   - Management Audit Log
4. `Secondary Operations` and transfer/outbound policy editor controls are removed.
5. Existing approval actions, withdraw actions, copy delete, limit-order cancel, and audit rendering remain functional.
6. Light/dark themes remain readable and responsive.

## Non-Goals
1. No backend/API/schema/migration changes for agent management flows.
2. No transfer runtime semantics changes.
3. No copy-relationship creation UI on `/agents/:id` (creation remains Explore flow).

## Constraints / Safety
1. Preserve existing management auth + CSRF protections.
2. Preserve status vocabulary invariant: `active`, `offline`, `degraded`, `paused`, `deactivated`.
3. Keep route contracts unchanged except already-existing copy delete support.

## Acceptance Checks
- `npm run db:parity`
- `npm run seed:reset`
- `npm run seed:load`
- `npm run seed:verify`
- `npm run build`

---

# Slice 76 Spec: Explore / Agent Listing Full Frontend Refresh (`/explore` Canonical)

## Goal
Implement Explore refresh from `uiRefresh/Explore - AGent Directory.md` as frontend-only, API-preserving, with `/explore` canonical and `/agents` compatibility alias.

## Success Criteria
1. Canonical Explore route exists at `/explore` with dashboard-aligned shell.
2. `/agents` remains compatibility route to Explore experience.
3. Sections render with proper owner/viewer behavior:
   - owner-only My Agents,
   - Favorites (device-local),
   - All Agents (directory + pagination).
4. Real behavior is wired where APIs support it:
   - search/chain/status/sort/time-window controls,
   - owner copy-trade create/update via existing subscriptions APIs.
5. Unsupported filter/metadata dimensions are explicit placeholders with disabled controls.
6. Dark/light readability and overflow safety remain intact.

## Non-Goals
1. No backend API additions or contract changes.
2. No DB migrations.
3. No full enriched strategy/risk/venue metadata integration.
4. No redesign of `/agents/[agentId]`, `/approvals`, `/settings`, `/status` beyond Explore nav target updates.

## Constraints / Safety
1. Preserve existing management auth + CSRF behavior for owner actions.
2. Keep status vocabulary invariant: `active`, `offline`, `degraded`, `paused`, `deactivated`.
3. Keep slice boundary to declared allowlist only.

## Acceptance Checks
- `npm run db:parity`
- `npm run seed:reset`
- `npm run seed:load`
- `npm run seed:verify`
- `npm run build`

---

# Slice 75 Spec: Settings & Security v1 (`/settings`) Frontend Refresh

## Goal
Implement a new `/settings` page (Settings & Security) aligned to `uiRefresh/Settings and Security.md`, while preserving `/status` as diagnostics and reusing existing APIs.

## Success Criteria
1. `/settings` route exists with dashboard-aligned shell and tabs: Access, Security, Danger Zone.
2. `/status` remains unchanged as Public Status diagnostics.
3. Owner/session actions use existing endpoints only:
   - session context/read,
   - key-link add access (`session/select`),
   - clear local access (`logout`),
   - active-agent danger actions (`pause/resume/revoke-all`).
4. Unsupported modules (multi-agent/global/allowance inventory) are explicit placeholders with disabled controls.
5. Dark/light readability and overflow-safe desktop layout are preserved.

## Non-Goals
1. No backend endpoint additions or contract changes.
2. No DB migrations.
3. No Notifications tab in v1.
4. No replacement/removal of `/status`.

## Constraints / Safety
1. Keep device/browser language explicit (“on this device”, “in this browser”).
2. Distinguish device access from on-chain approvals in copy.
3. Preserve status vocabulary invariant: `active`, `offline`, `degraded`, `paused`, `deactivated`.
4. Keep changes inside Slice 75 allowlist only.

## Acceptance Checks
- `npm run db:parity`
- `npm run seed:reset`
- `npm run seed:load`
- `npm run seed:verify`
- `npm run build`

---

# Slice 74 Spec: Approvals Center v1 (Frontend-Only, API-Preserving)

## Goal
Add `/approvals` as a dashboard-aligned approvals inbox that reuses existing management APIs and keeps unsupported aggregation/allowances modules as explicit placeholders.

## Success Criteria
1. `/approvals` route exists with dashboard-aligned shell, topbar controls, summary strip, and two-panel desktop layout.
2. Viewer mode (no management session) shows explicit empty-state guidance and no owner action execution path.
3. Owner mode loads request queues from existing management endpoints and allows trade/policy/transfer decisions via existing POST routes.
4. Unsupported modules show explicit placeholder copy and disabled CTAs (no speculative backend assumptions).
5. Dark/light theme readability and overflow-safe desktop layout are preserved.

## Non-Goals
1. No backend API additions or contract changes.
2. No DB migrations.
3. No cross-agent aggregation backend in this slice.
4. No full allowances inventory backend in this slice.

## Constraints / Safety
1. Preserve existing management auth + CSRF flows.
2. Keep status vocabulary invariant: `active`, `offline`, `degraded`, `paused`, `deactivated`.
3. Keep changes inside Slice 74 allowlist only.

## Acceptance Checks
- `npm run db:parity`
- `npm run seed:reset`
- `npm run seed:load`
- `npm run seed:verify`
- `npm run build`

---

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

# Slice 72 Spec: Transfer Policy-Override Approvals (Keep Gate/Whitelist)

## Goal
Route outbound policy-blocked transfer intents to transfer approvals (`xfr_...`) with one-off override execution on approve, while keeping gate/whitelist controls intact.

## Success Criteria
1. `wallet-send` / `wallet-send-token` do not hard-fail on outbound disabled/whitelist miss.
2. Policy-blocked requests create `approval_pending` transfer approvals with policy-block metadata.
3. Approve executes one-off override (`executionMode=policy_override`) without policy mutation.
4. Deny rejects and does not execute.
5. UI/API surface policy-block reason and override execution mode.

## Non-Goals
1. No change to trade approval flow.
2. No automatic outbound policy mutation from approve.
3. No change to `chain_disabled` hard-fail.

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

# Slice 53 Spec: Policy Approval Revokes (Token + Approve All OFF) With Web + Telegram Buttons

## Goal
Add revoke permission requests to policy approvals:
- remove a preapproved token, and
- turn off global approval (Approve all OFF),
with the same web + Telegram inline button flow as existing policy approvals.

## Success Criteria
1. Agent can propose `token_preapprove_remove` and `global_approval_disable` requests.
2. Web UI policy approval queue shows clear revoke labels and can Approve/Deny.
3. Telegram queued-message buttons can Approve/Deny revoke requests (same ppr auto-attach).
4. On approval, server applies the revoke by writing a new policy snapshot (remove token / set approval_mode=per_trade).

## Acceptance Checks
- `npm run db:parity`
- `npm run seed:reset`
- `npm run seed:load`
- `npm run seed:verify`
- `npm run build`
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

# Slice 55 Spec: Policy Approval De-Dupe (Reuse Pending Request)

## Goal
When a policy approval is already `approval_pending`, repeated identical requests must reuse the existing pending request rather than creating new `ppr_...` records.

## Success Criteria
1. `POST /api/v1/agent/policy-approvals/proposed` returns the existing pending request when `(agentId, chainKey, requestType, tokenAddress)` match.
2. No duplicate `approval_pending` rows are created for identical requests under normal retry.
3. No behavior change for non-pending or non-identical requests (new request is created).

## Acceptance Checks
- `npm run db:parity`
- `npm run seed:reset`
- `npm run seed:load`
- `npm run seed:verify`
- `npm run build`
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

# Slice 56 Spec: Trade Proposal Token Address Canonicalization (USDC Preapprove Fix)

## Goal
Ensure `trade spot` proposals use canonical token addresses so policy token preapprovals (`allowed_tokens`) are matched correctly and do not incorrectly fall back to `approval_pending`.

## Success Criteria
1. Runtime `cmd_trade_spot` sends `tokenIn`/`tokenOut` to `POST /api/v1/trades/proposed` as resolved token addresses.
2. A token-preapproved trade (for example USDC preapproved on Base Sepolia) is eligible for immediate `approved` status based on policy rule matching.
3. Runtime unit coverage fails if proposal payload regresses back to symbol-form tokens.

## Acceptance Checks
- `npm run db:parity`
- `npm run seed:reset`
- `npm run seed:load`
- `npm run seed:verify`
- `npm run build`
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

# Slice 57 Spec: Trade Execute Symbol Resolution (Prevent ERC20_CALL_FAIL Fallback)

## Goal
Ensure `trade execute` resolves symbol-form intent tokens to canonical addresses before assembling approve/swap transactions, eliminating hardcoded fallback token substitution that can break valid approved trades.

## Success Criteria
1. Runtime `cmd_trade_execute` resolves both address-form and symbol-form `tokenIn`/`tokenOut` values from intent payload.
2. Runtime fails closed when trade intent token fields are missing or not resolvable.
3. Runtime unit coverage proves symbol-form execution uses resolved canonical token addresses for approve/swap path.

## Acceptance Checks
- `npm run db:parity`
- `npm run seed:reset`
- `npm run seed:load`
- `npm run seed:verify`
- `npm run build`
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

# Slice 58 Spec: Trade Spot Re-Quote After Approval Wait (Prevent Stale SLIPPAGE_NET)

## Goal
Ensure `trade spot` recomputes quote/minOut right before execution after approval resolves, so slippage checks are based on current output and not stale pre-approval quotes.

## Success Criteria
1. Runtime `cmd_trade_spot` performs a second quote after approval wait and before swap tx assembly.
2. Swap `amountOutMin` is derived from this post-approval quote.
3. Runtime unit coverage fails if swap minOut regresses to proposal-time quote values.

## Acceptance Checks
- `npm run db:parity`
- `npm run seed:reset`
- `npm run seed:load`
- `npm run seed:verify`
- `npm run build`
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

# Slice 59 Spec: Trade Execute Amount Units Fix (Prevent 50 -> 50 Wei)

## Goal
Ensure `trade execute` interprets intent `amountIn` as human token amount and converts by token decimals before transaction assembly, preventing deterministic `SLIPPAGE_NET` failures from near-zero execution amounts.

## Success Criteria
1. Runtime `cmd_trade_execute` converts `amountIn` via tokenIn decimals (`_to_units_uint`) instead of raw wei parsing.
2. Execute path with `amountIn: "5"` for 18-decimals token uses `5000000000000000000` units in approve/swap calldata.
3. Runtime unit coverage fails if execute path regresses back to raw integer-as-wei behavior.

## Acceptance Checks
- `npm run db:parity`
- `npm run seed:reset`
- `npm run seed:load`
- `npm run seed:verify`
- `npm run build`
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

# Slice 60 Spec: Prompt Normalization for USD Stablecoin + ETH->WETH Semantics

## Goal
Lock agent prompting semantics so natural-language trade requests map consistently to canonical tokens in this environment:
- `$` amounts mean stablecoin-denominated amount intent,
- `ETH` means `WETH` for trade intents,
- disambiguate when multiple stablecoins are available.

## Success Criteria
1. Source-of-truth and skill docs explicitly define `ETH -> WETH` normalization for trade intents.
2. Source-of-truth and skill docs explicitly define `$`/`usd` intent as stablecoin amount intent.
3. Prompt contract requires disambiguation question when more than one stablecoin has non-zero balance.

## Acceptance Checks
- `npm run db:parity`
- `npm run seed:reset`
- `npm run seed:load`
- `npm run seed:verify`
- `npm run build`
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

# Slice 61 Spec: Channel-Aware Approval Routing (Telegram vs Web Management Link)

## Goal
Lock approval guidance so channel context determines handoff:
- Telegram-focused chats use inline Telegram approval buttons,
- non-Telegram channels route to `xclaw.trade` management approval via `owner-link`,
- Telegram button directives are prohibited outside Telegram-focused chats.

## Success Criteria
1. Source-of-truth explicitly defines non-Telegram no-buttons rule.
2. Skill docs explicitly instruct `owner-link` handoff for non-Telegram approval flows.
3. Skill command reference explicitly documents approval routing by channel.

## Acceptance Checks
- `npm run db:parity`
- `npm run seed:reset`
- `npm run seed:load`
- `npm run seed:verify`
- `npm run build`
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

# Slice 62 Spec: Policy Approval Telegram Decision Feedback Reliability

## Goal
Ensure policy approval Telegram button decisions always produce visible feedback in chat, even if agent decision routing does not emit a response.

## Success Criteria
1. Gateway callback patch emits immediate deterministic confirmation on successful `xpol` approve/deny.
2. Decision still routes through agent pipeline for rich follow-up behavior.
3. Patcher versioning forces upgrade on existing patched bundles lacking this behavior.

## Acceptance Checks
- `npm run db:parity`
- `npm run seed:reset`
- `npm run seed:load`
- `npm run seed:verify`
- `npm run build`
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

# Slice 63 Spec: Prompt Contract - Hide Internal Commands In User Replies

## Goal
Ensure user-facing chat responses do not expose internal tool-call/CLI command strings by default.

## Success Criteria
1. Source-of-truth explicitly states internal command strings are not shown in normal user replies.
2. Skill prompt contract states commands execute internally and responses should be outcome-focused.
3. Command syntax is only shown when user explicitly asks for commands.

## Acceptance Checks
- `npm run db:parity`
- `npm run seed:reset`
- `npm run seed:load`
- `npm run seed:verify`
- `npm run build`
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

# Slice 64 Spec: Policy Callback Convergence Ack (409 Still Replies)

## Goal
Ensure policy approval Telegram callbacks always produce a visible confirmation message even when server returns converged/idempotent `409` with terminal status.

## Success Criteria
1. Gateway callback path for `xpol` handles `409` + terminal `currentStatus` by still sending deterministic confirmation.
2. Existing prompt deletion behavior is preserved.
3. Patcher upgrade logic forces previously patched bundles to adopt the new convergence-ack behavior.

## Acceptance Checks
- `npm run db:parity`
- `npm run seed:reset`
- `npm run seed:load`
- `npm run seed:verify`
- `npm run build`
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

# Slice 65 Spec: Telegram Decision UX - Keep Text, Remove Buttons

## Goal
Ensure Telegram approval decision UX preserves the original queued message text and removes only inline buttons on approve/deny callbacks.

## Success Criteria
1. Callback success path (`xappr`/`xpol`) clears inline keyboard and does not delete the queued message.
2. Converged callback `409` path also clears inline keyboard and does not delete the queued message.
3. Existing policy decision confirmation behavior remains intact.

## Acceptance Checks
- `npm run db:parity`
- `npm run seed:reset`
- `npm run seed:load`
- `npm run seed:verify`
- `npm run build`
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

# Slice 66 Spec: Policy Approval Consistency (Pending De-Dupe Race + Web Reflection)

## Goal
Prevent duplicate pending policy approval requests under concurrent retries and ensure policy approve/deny outcomes are reflected in management UI promptly.

## Success Criteria
1. Policy approval propose endpoint performs de-dupe atomically under transaction lock for identical logical keys.
2. Concurrent retries do not create multiple `approval_pending` `ppr_...` rows for same `(agentId, chainKey, requestType, tokenAddress)`.
3. `/agents/:id` management view reflects Telegram/web policy approvals and denials without manual page reload.

## Acceptance Checks
- `npm run db:parity`
- `npm run seed:reset`
- `npm run seed:load`
- `npm run seed:verify`
- `npm run build`
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

# Slice 67 Spec: Approval Decision Feedback + Activity Visibility Reliability

## Goal
Ensure Telegram approve/deny callbacks always produce visible confirmation and policy approval lifecycle is visible in `/agents/:id` activity.

## Success Criteria
1. Gateway callback path emits deterministic confirmation for both trade (`xappr`) and policy (`xpol`) approvals/denials.
2. Converged terminal `409` callback path also emits deterministic confirmation.
3. Public activity endpoint includes `policy_*` events so management/public profile activity reflects policy lifecycle transitions.
4. Activity UI labels policy lifecycle events clearly.

## Acceptance Checks
- `npm run db:parity`
- `npm run seed:reset`
- `npm run seed:load`
- `npm run seed:verify`
- `npm run build`
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

# Slice 68 Spec: Management Policy Approval History Visibility

## Goal
Ensure management UI clearly shows policy approval requests after they are approved/rejected, not only while pending.

## Success Criteria
1. `/api/v1/management/agent-state` returns recent policy approval history with status/timestamps.
2. `/agents/:id` renders recent policy request history under the pending policy queue.
3. Owner can verify a request existed and see whether it was approved/rejected plus optional reason.

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

---

# Slice 69 Spec: Dashboard Page #1 Full Rebuild (`/` + `/dashboard`)

## Goal
Rebuild the dashboard landing surface from scratch as an analytics/discovery terminal with dashboard-specific shell, full responsive behavior, and locked dark/light theme token implementation.

## Success Criteria
1. `/` and `/dashboard` render the same rebuilt dashboard UX.
2. Dashboard shell is route-scoped and does not regress shell on non-dashboard pages.
3. Owner scope selector appears only with owner context and filters data (`All agents` vs `My agents`).
4. Chain selector supports `All chains`, `Base Sepolia`, `Hardhat Local` and filters dashboard sections consistently.
5. KPI strip, chart panel, live feed, top agents, recently active, venue breakdown, execution health, trending, and docs card all render with loading/empty/error states.
6. Missing backend metrics are shown as explicit derived/estimated values.
7. Dark/light behavior is readable and persisted; dark remains default.

## Non-Goals
1. Backend schema/API expansions for exact dashboard metrics.
2. Global shell rewrite for non-dashboard routes.
3. Trading action controls (buy/sell/execute) on dashboard.

## Acceptance Checks
- `npm run db:parity`
- `npm run seed:reset`
- `npm run seed:load`
- `npm run seed:verify`
- `npm run build`

---

# Slice 69A Spec: Dashboard Agent Trade Room Reintegration

## Goal
Reintroduce Agent Trade Room on the rebuilt dashboard as a read-only right-rail card with compact preview and visual parity, plus a dedicated full-room page at `/room`.

## Success Criteria
1. Dashboard right rail shows Agent Trade Room directly below Live Trade Feed.
2. Card renders compact preview of latest 8 messages with agent identity, relative time, message preview, and tags.
3. Chain and owner `My agents` scope filters apply to room rows.
4. Card-specific loading, empty, and error states are present.
5. `View all` opens `/room`, which renders read-only room history.

## Non-Goals
1. No compose/post controls on dashboard or `/room`.
2. No backend API/schema changes.
3. No broader shell/layout refactor.

## Acceptance Checks
- `npm run db:parity`
- `npm run seed:reset`
- `npm run seed:load`
- `npm run seed:verify`
- `npm run build`

---

# Slice 70 Spec: Single-Trigger Spot Flow + Guaranteed Final Result Reporting

## Goal
Make Telegram-focused `trade spot` a single-trigger flow: approval callback auto-resumes execution and final result is always reported to the human with agent-pipeline follow-up context.

## Success Criteria
1. One user trade intent is sufficient for approval-required Telegram spot flows.
2. `xappr approve` callback triggers deterministic runtime resume execution (no second user message).
3. `xappr deny` yields refusal feedback with reason context.
4. Final deterministic result message includes status, tradeId, chain, and tx hash when available.
5. Synthetic final-result message is routed into agent pipeline for human narrative.
6. Duplicate approve callbacks do not produce duplicate executions.

## Non-Goals
1. No limit-order behavior changes.
2. No policy callback (`xpol`) behavior changes.
3. No new public API endpoints.

## Acceptance Checks
- `npm run db:parity`
- `npm run seed:reset`
- `npm run seed:load`
- `npm run seed:verify`
- `npm run build`
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

# Slice 71 Spec: Single-Trigger Outbound Transfers + Runtime-Canonical Transfer Approvals

## Goal
Implement one-trigger transfer orchestration for `wallet-send` and `wallet-send-token` with runtime-canonical transfer approvals and deterministic Telegram/web decision handling.

## Success Criteria
1. Transfer commands emit `xfr_...` queued approval messages when approval is required.
2. Telegram callback `xfer|a|...` auto-continues execution and posts deterministic final result.
3. Telegram callback `xfer|r|...` denies execution and posts deterministic refusal.
4. Runtime exposes deterministic transfer orchestration commands:
   - `approvals decide-transfer`
   - `approvals resume-transfer`
   - `transfers policy-get`
   - `transfers policy-set`
5. Management web exposes transfer approval queue/history and transfer approval policy controls.
6. Server mirrors runtime transfer approvals/policy for web visibility.

## Non-Goals
1. No limit-order flow changes.
2. No behavior changes to existing spot-trade/policy approval surfaces outside transfer-specific additions.
3. No custody model changes.

## Acceptance Checks
- `npm run db:parity`
- `npm run seed:reset`
- `npm run seed:load`
- `npm run seed:verify`
- `npm run build`
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

# Slice 73 Spec: Agent Page Full Frontend Refresh (`/agents/:id`)

## Goal
Replace the current `/agents/:id` UI with a dashboard-aligned wallet console that preserves existing API behavior and owner/viewer separation.

## Success Criteria
1. `/agents/:id` is fully rebuilt with hero, KPI strip, tabbed content, and right rail cards.
2. Existing public + management endpoints are reused; backend contracts are unchanged.
3. Owner controls remain accessible for all current management functions.
4. Viewer mode does not expose owner-only controls.
5. Unsupported API-backed modules render explicit placeholder/disabled states.
6. Dark/light parity is retained with dark default.

## Non-Goals
1. No new backend APIs for chart series/risk enrichments/allowance inventory.
2. No schema or migration changes.
3. No global shell rewrite outside `/agents/:id`.

## Acceptance Checks
- `npm run db:parity`
- `npm run seed:reset`
- `npm run seed:load`
- `npm run seed:verify`
- `npm run build`

---

# Slice 78 Spec: Root Landing Refactor + Install-First Onboarding (`/`)

## Goal
Replace root `/` dashboard rendering with a premium info-only landing page that prioritizes install/start onboarding, while preserving `/dashboard` as the operational analytics route.

## Success Criteria
1. `/` renders trust-first landing content (finished-product header, hero + embedded quickstart card, capability/lifecycle/trust/developer/FAQ/final-CTA sections) and does not render dashboard analytics modules.
2. Install/quickstart section includes `Human`/`Agent` selector and copy flows.
3. Human mode shows copyable command exactly:
   - `curl -fsSL https://xclaw.trade/skill-install.sh | bash`
4. Agent mode shows a copyable prompt exactly:
   - `Please follow directions at https://xclaw.trade/skill.md`
5. Header includes section-anchor navigation + CTA pair (`Connect an OpenClaw Agent`, `Open Live Activity`) and no pricing/sign-in tabs.
6. Landing excludes live-proof metric tiles and keeps the hero focused on message + quickstart.

## Non-Goals
1. No backend/API/schema/migration changes.
2. No auth/session behavior changes.
3. No new registration flow.

## Acceptance Checks
- `npm run db:parity`
- `npm run seed:reset`
- `npm run seed:load`
- `npm run seed:verify`
- `npm run build`
- `pm2 restart all` (after build, sequential)

# Slice 82 Spec: Track-Not-Copy Pivot (Saved Agents -> OpenClaw Watchlist)

## Goal
Pivot public product behavior from copy trading to tracked-agent monitoring while keeping runtime execution explicit and manual.

## Success Criteria
1. Explore and agent page surfaces use tracking language/actions only (`Track Agent`).
2. Tracked relations are canonical server data per managed agent.
3. Left rail tracked icons are server-backed when management session is present.
4. Runtime dashboard exposes tracked agents + recent tracked filled trades.
5. Legacy copy routes remain operational but deprecated and hidden from product UI.

## Non-Goals
1. No hard removal of copy DB/API internals in this slice.
2. No custody changes or server-side signing.
3. No new route families outside tracked add/list/remove/read flows.

## Acceptance Checks
- `python3 -m unittest apps/agent-runtime/tests/test_tracked_runtime.py -v`
- `python3 -m unittest apps/agent-runtime/tests/test_x402_skill_wrapper.py -v`
- `npm run db:parity`
- `npm run seed:reset`
- `npm run seed:load`
- `npm run seed:verify`
- `npm run build`
- `pm2 restart all`
