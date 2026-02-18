# Slice 85 Tasks: EVM-Wide Portability Foundation (Chain-Agnostic Core, x402 Unchanged)

Active slice: `Slice 85: EVM-Wide Portability Foundation`
Issue mapping: `#35`

## 1) Canonical sync
- [x] Add Slice 85 tracker + roadmap entries with issue mapping.
- [x] Update source-of-truth with locked portability contract.
- [x] Update context/spec/tasks/acceptance artifacts.
- [x] Update wallet command contract + OpenAPI + schemas.

## 2) Implementation
- [x] Extend `config/chains/*.json` contract with `family/enabled/uiVisible/nativeCurrency/capabilities`.
- [x] Add migration `0021_slice85_chain_token_metadata.sql`.
- [x] Add `GET /api/v1/public/chains`.
- [x] Replace static frontend chain options with registry-driven fetch/cached options.
- [x] Add runtime `chains` command and capability checks.
- [x] Replace hardcoded chain action hints with dynamic supported-chain hints in key API routes.
- [x] Add token metadata resolver/cache and include metadata on management chain tokens.

## 3) Validation
- [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`
- [x] `python3 -m unittest apps/agent-runtime/tests/test_x402_runtime.py -v`
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] `npm run build`
- [x] `pm2 restart all`

---

# Slice 83 Tasks: Kite AI Testnet Parity (Runtime + Web + DEX + x402)

Active slice: `Slice 83: Kite AI Testnet Parity`
Issue mapping: `#33`

## 1) Canonical sync
- [x] Add Slice 83 tracker + roadmap entries with issue mapping.
- [x] Update source-of-truth with locked Kite parity contract.
- [x] Update context/spec/tasks/acceptance artifacts.
- [x] Update wallet command contract + OpenAPI chain examples.

## 2) Runtime and config
- [x] Add `config/chains/kite_ai_testnet.json`.
- [x] Add `infrastructure/seed-data/kite-ai-testnet-contracts.json`.
- [x] Enable Kite testnet in `config/x402/networks.json` (mainnet disabled).
- [x] Add runtime DEX adapter module and wire trade quote/swap path through adapter selection.
- [x] Remove Base-only runtime wording where chain-neutral behavior is expected.

## 3) Web/API parity
- [x] Add Kite option to active chain selector options.
- [x] Make status provider probes include Kite chain.
- [x] Update public/management action hints and chain validation paths to include Kite.
- [x] Keep faucet endpoint Base-only with clear unsupported response on Kite.
- [x] Ensure x402 receive request asset validation includes Kite assets (`KITE`, `WKITE`, `USDT`).

## 4) Tests and validation
- [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`
- [x] `python3 -m unittest apps/agent-runtime/tests/test_x402_runtime.py -v`
- [x] `python3 -m unittest apps/agent-runtime/tests/test_dex_adapter.py -v`
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] `npm run build`
- [x] `pm2 restart all`

---

# Slice 81 Tasks: Explore v2 Full Flush (No Placeholders)

Active slice: `Slice 81: Explore v2 Full Flush (No Placeholders)`
Issue mapping: `#30`

## 1) Canonical sync
- [x] Add Slice 81 tracker + roadmap entries with issue mapping.
- [x] Reconcile Slice 80 issue mapping and mark complete evidence path.
- [x] Update source-of-truth with Explore v2 locked contract.
- [x] Update command/API docs and schemas.
- [x] Update context/spec/tasks/acceptance artifacts.

## 2) Data model + schema
- [x] Add migration `0018_slice81_explore_v2.sql`.
- [x] Add table `agent_explore_profile`.
- [x] Add tag/risk constraints and indexes.
- [x] Add management explore profile request/response schemas.
- [x] Add public agents/leaderboard response schemas.

## 3) API implementation
- [x] Extend `GET /api/v1/public/agents` with Explore filters and enriched response.
- [x] Extend `GET /api/v1/public/leaderboard` with `verified` + `exploreProfile`.
- [x] Implement `GET /api/v1/management/explore-profile`.
- [x] Implement `PUT /api/v1/management/explore-profile`.
- [x] Update OpenAPI for new params/routes/schemas.

## 4) Explore UI implementation
- [x] Remove strategy/venue/risk placeholder labels and wire real controls.
- [x] Add functional advanced filter drawer and reset action.
- [x] Implement segmented `All/My/Favorites` single-view behavior.
- [x] Add URL-state sync for filter/sort/window/page/section.
- [x] Add verified badge and follower-rich metadata rendering.
- [x] Keep owner/viewer copy-trade behavior unchanged.
- [x] Add owner-managed Explore profile edit flow from Explore cards.

## 5) Validation
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] `npm run build`
- [x] `pm2 restart all` (post-build, sequential)

---

# Slice 80 Tasks: Hosted x402 Web Integration + Agent-Originated Send

Active slice: `Slice 80: Hosted x402 on /agents/[agentId]`
Issue mapping: `#31`

## 1) Canonical sync
- [x] Add Slice 80 tracker + roadmap entries with issue mapping.
- [x] Update source-of-truth with hosted x402 contract + `xfr_...` outbound approval reuse.
- [x] Update command contract and OpenAPI.
- [x] Update context/spec/tasks/acceptance artifacts.

## 2) Data model + schema
- [x] Add migration `0017_slice80_hosted_x402.sql`.
- [x] Add table `agent_x402_payment_mirror`.
- [x] Extend `agent_transfer_approval_mirror` for x402 metadata/source.
- [x] Add new x402 request/response schemas.
- [x] Extend transfer approval schemas for `approvalSource` + x402 fields.

## 3) API implementation
- [x] Implement `POST /api/v1/agent/x402/outbound/proposed`.
- [x] Implement `POST /api/v1/agent/x402/outbound/mirror`.
- [x] Implement `POST /api/v1/agent/x402/inbound/mirror`.
- [x] Implement `GET /api/v1/management/x402/payments`.
- [x] Implement `GET /api/v1/management/x402/receive-link`.
- [x] Implement hosted endpoint `GET|POST /api/v1/x402/pay/{agentId}/{linkToken}`.
- [x] Extend transfer mirror write and transfer approvals read/decision routes with x402 fields.

## 4) Runtime/UI integration
- [x] Runtime mirrors outbound x402 into server read model + transfer approval mirror surface.
- [x] `approvals decide-transfer|resume-transfer` fallback to x402 flow when approval ID belongs to x402 payment.
- [x] `/agents/[agentId]` adds hosted receive-link panel.
- [x] `/agents/[agentId]` wallet timeline merges x402 history with source badge.
- [x] Approval history rows show x402 URL/network/facilitator/amount context when `approval_source=x402`.

## 5) Validation
- [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`
- [x] `python3 -m unittest apps/agent-runtime/tests/test_x402_runtime.py -v`
- [x] `python3 -m unittest apps/agent-runtime/tests/test_x402_skill_wrapper.py -v`
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] `npm run build`
- [x] `pm2 restart all` (post-build, sequential)

---

# Slice 79 Tasks: Agent-Skill x402 Send/Receive Runtime (No Webapp Integration Yet)

Active slice: `Slice 79: Agent-Skill x402 Send/Receive Runtime`
Issue mapping: `#29`

## Checklist
- [x] Pre-flight lock: objective + acceptance checks + touched-file allowlist defined before edits.
- [x] Docs sync first:
  - [x] `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - [x] `docs/XCLAW_SLICE_TRACKER.md`
  - [x] `docs/XCLAW_BUILD_ROADMAP.md`
  - [x] `docs/api/WALLET_COMMAND_CONTRACT.md`
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`
- [x] Add runtime x402 modules:
  - [x] `apps/agent-runtime/xclaw_agent/x402_runtime.py`
  - [x] `apps/agent-runtime/xclaw_agent/x402_tunnel.py`
  - [x] `apps/agent-runtime/xclaw_agent/x402_policy.py`
  - [x] `apps/agent-runtime/xclaw_agent/x402_state.py`
- [x] Add runtime CLI x402 command group.
- [x] Add skill wrapper x402 command group + `request-x402-payment` auto-start behavior.
- [x] Add installer cross-platform launcher updates (`.cmd` + `.ps1` + POSIX). (cloudflared requirement later superseded by hosted receive flow)
- [x] Add x402 network config artifact (`config/x402/networks.json`).
- [x] Add x402 shared schemas under `packages/shared-schemas/json/`.
- [x] Add x402 runtime + wrapper unit tests.
- [x] Run required gates:
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_x402_runtime.py -v`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_x402_skill_wrapper.py -v`
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `pm2 restart all` (after successful build, when PM2 available)
- [x] Record verification evidence in `acceptance.md`.
- [ ] Commit + push Slice 79.
- [ ] Post verification evidence + commit hash(es) to issue `#29`.

## Hosted x402 Receive Delta Tasks
- [x] Add agent-auth hosted receive request route: `POST /api/v1/agent/x402/inbound/proposed`.
- [x] Rewire runtime x402 command surface to hosted `receive-request` (remove `serve-*` parsers/handlers).
- [x] Rewire skill `request-x402-payment` to hosted receive-request path.
- [x] Remove installer cloudflared dependency from setup flow.
- [x] Update OpenAPI/shared schema and command/source-of-truth docs for hosted receive flow.

---

# Slice 77 Tasks: Agent Wallet Page iPhone/MetaMask-Style Refactor (`/agents/:id`)

Active slice: `Slice 77: Agent Wallet Page iPhone/MetaMask-Style Refactor`
Issue mapping: `pending mapping (legacy placeholder)`

## Checklist
- [x] Pre-flight lock: objective + acceptance checks + touched-file allowlist defined before edits.
- [x] Docs sync first:
  - [x] `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - [x] `docs/XCLAW_SLICE_TRACKER.md`
  - [x] `docs/XCLAW_BUILD_ROADMAP.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`
- [x] Refactor `/agents/:id` to wallet-native composition while preserving dashboard sidebar shell.
- [x] Keep chain selector + theme toggle in compact utility bar.
- [x] Recompose module order to wallet-first stack.
- [x] Remove `Secondary Operations`.
- [x] Remove transfer/outbound policy editor controls from `/agents/:id`.
- [x] Keep approvals workflow actions (trade/policy/transfer) and policy toggle/per-token preapprove controls.
- [x] Keep withdraw destination/asset/amount/max/submit flow.
- [x] Keep copy relationships list/delete only with create guidance to `/explore`.
- [x] Keep limit-order review/cancel and audit log visibility.
- [x] Rewrite route CSS for wallet-native card grammar with light/dark responsiveness.
- [ ] Run required gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
- [x] Record verification evidence in `acceptance.md`.
- [ ] Commit + push Slice 77.
- [ ] Post verification evidence + commit hash(es) to mapped issue.

---

# Slice 76 Tasks: Explore / Agent Listing Full Frontend Refresh (`/explore` Canonical)

Active slice: `Slice 76: Explore / Agent Listing Full Frontend Refresh (/explore Canonical)`
Issue mapping: `#28`

## Checklist
- [x] Pre-flight lock: objective + acceptance checks + touched-file allowlist defined before edits.
- [x] Docs sync first:
  - [x] `docs/XCLAW_SLICE_TRACKER.md`
  - [x] `docs/XCLAW_BUILD_ROADMAP.md`
  - [x] `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`
- [x] Add canonical Explore route:
  - [x] `apps/network-web/src/app/explore/page.tsx`
  - [x] `apps/network-web/src/app/explore/page.module.css`
- [x] Add Explore frontend modules:
  - [x] `apps/network-web/src/lib/explore-page-view-model.ts`
  - [x] `apps/network-web/src/lib/explore-page-capabilities.ts`
- [x] Keep `/agents` compatibility alias to Explore.
- [x] Wire supported APIs:
  - [x] public agents + leaderboard
  - [x] owner session context
  - [x] copy subscriptions get/create/update
- [x] Implement My Agents/Favorites/All Agents sections with owner/viewer behavior.
- [x] Add explicit placeholders/disabled controls for unsupported enriched filters/metadata.
- [x] Update nav links to point Explore to `/explore` on dashboard, agent, approvals, settings.
- [x] Treat `/explore` as dashboard-shell route.
- [ ] Run required gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
- [x] Record command outputs + functional verification notes in `acceptance.md`.
- [x] Commit + push Slice 76.
- [x] Post verification evidence + commit hash(es) to mapped issue.

---

# Slice 75 Tasks: Settings & Security v1 (`/settings`) Frontend Refresh

Active slice: `Slice 75: Settings & Security v1 (/settings) Frontend Refresh`
Issue mapping: `#27`

## Checklist
- [x] Pre-flight lock: objective + acceptance checks + touched-file allowlist defined before edits.
- [x] Docs sync first:
  - [x] `docs/XCLAW_SLICE_TRACKER.md`
  - [x] `docs/XCLAW_BUILD_ROADMAP.md`
  - [x] `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`
- [x] Add `/settings` route with dashboard-aligned shell + sticky topbar.
- [x] Add tabs `Access`, `Security`, `Danger Zone` (hide Notifications in v1).
- [x] Add settings capabilities module:
  - [x] `apps/network-web/src/lib/settings-security-capabilities.ts`
- [x] Wire existing API-backed actions:
  - [x] `GET /api/v1/management/session/agents`
  - [x] `POST /api/v1/management/session/select`
  - [x] `POST /api/v1/management/logout`
  - [x] `POST /api/v1/management/pause`
  - [x] `POST /api/v1/management/resume`
  - [x] `POST /api/v1/management/revoke-all`
- [x] Keep `/status` unchanged.
- [x] Update nav links to point Settings & Security to `/settings` on dashboard, agents, approvals.
- [x] Add explicit placeholders/disabled controls for unsupported multi-agent/global/allowance modules.
- [ ] Run required gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
- [x] Record command outputs + functional verification notes in `acceptance.md`.
- [ ] Commit + push Slice 75.
- [ ] Post verification evidence + commit hash(es) to mapped issue.

---

# Slice 74 Tasks: Approvals Center v1 (Frontend-Only, API-Preserving)

Active slice: `Slice 74: Approvals Center v1 (Frontend-Only, API-Preserving)`
Issue mapping: `#74` (to be created / mapped)

## Checklist
- [x] Pre-flight lock: objective + acceptance checks + touched-file allowlist defined before edits.
- [x] Docs sync first:
  - [x] `docs/XCLAW_SLICE_TRACKER.md`
  - [x] `docs/XCLAW_BUILD_ROADMAP.md`
  - [x] `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`
- [x] Add `/approvals` route with dashboard-aligned shell + sticky topbar.
- [x] Add approvals-center frontend modules:
  - [x] `apps/network-web/src/lib/approvals-center-view-model.ts`
  - [x] `apps/network-web/src/lib/approvals-center-capabilities.ts`
- [x] Wire owner context + queue data from existing endpoints.
- [x] Wire decision actions for trade/policy/transfer via existing management POST routes.
- [x] Add placeholder modules for unsupported aggregation/allowances/risk enrichments with disabled CTAs.
- [x] Update nav links to route Approvals Center to `/approvals`.
- [x] Preserve dark/light behavior and desktop overflow safety.
- [ ] Run required gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
- [x] Record command outputs + functional verification notes in `acceptance.md`.
- [ ] Commit + push Slice 74.
- [ ] Post verification evidence + commit hash(es) to mapped issue.

---

# Slice 23 Tasks: Agent Spot Swap (Token->Token via Configured Router)

Active slice: `Slice 23: Agent Spot Swap Command (Token->Token via Configured Router)`

## Checklist
- [x] Add runtime command `xclaw-agent trade spot`.
- [x] Use router `getAmountsOut` to compute net quote and apply slippage-bps to produce `amountOutMin`.
- [x] Submit `swapExactTokensForTokens` to `coreContracts.router` (fee proxy compatible).
- [x] Skill wrapper command `trade-spot <token_in> <token_out> <amount_in> <slippage_bps>`.
- [x] Tests: spot swap success call-shape + invalid input.
- [x] Docs sync: source-of-truth + skill references + tracker/roadmap.
- [x] Run required gates and capture evidence in `acceptance.md`.

---

# Slice 25 Tasks: Agent Skill UX Upgrade (Security + Reliability + Contract Fixes)

Active slice: `Slice 25: Agent Skill UX Upgrade (Security + Reliability + Contract Fixes)`

## Checklist
- [x] Add Slice 25 to `docs/XCLAW_SLICE_TRACKER.md` + `docs/XCLAW_BUILD_ROADMAP.md`.
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` for:
  - [x] sensitive stdout redaction rule
  - [x] faucet pending guidance fields
- [x] Skill wrapper:
  - [x] redact `sensitiveFields` by default
  - [x] document `XCLAW_SHOW_SENSITIVE=1`
- [x] Runtime:
  - [x] faucet includes `pending`, `recommendedDelaySec`, `nextAction`
  - [x] limit-orders-create omits `expiresAt` unless provided
  - [x] surface server validation details in `details.apiDetails`
- [x] Server UX hint:
  - [x] update limit-orders schema error `actionHint` copy (remove outdated "pair fields")
- [x] Tests:
  - [x] faucet success asserts pending guidance fields
  - [x] limit-orders-create omits `expiresAt` when missing
  - [x] limit-orders-create failure surfaces server details
- [x] Run gates: `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`.
- [x] Run runtime tests.
- [x] Post evidence + commit hash to GitHub issue #20.

---

# Slice 26 Tasks: Agent Skill Robustness Hardening (Timeouts + Identity + Single-JSON)

Active slice: `Slice 26: Agent Skill Robustness Hardening (Timeouts + Identity + Single-JSON)`

## Checklist
- [x] Create and map issue: #21.
- [x] Wrapper:
  - [x] add `XCLAW_SKILL_TIMEOUT_SEC` handling (default 240)
  - [x] return structured `timeout` JSON on expiration
- [x] Runtime:
  - [x] add cast timeout envs (`XCLAW_CAST_CALL_TIMEOUT_SEC`, `XCLAW_CAST_RECEIPT_TIMEOUT_SEC`, `XCLAW_CAST_SEND_TIMEOUT_SEC`)
  - [x] centralize subprocess timeout handling
  - [x] `trade-spot` maps timeout failures to actionable codes
- [x] UX payloads:
  - [x] `status` includes best-effort `agentName` and warnings
  - [x] `wallet-health` includes `nextAction` + `actionHint`
  - [x] `faucet-request` surfaces `retryAfterSec` on rate limit
  - [x] `limit-orders-run-loop` emits single JSON; reject `--iterations 0` in JSON mode
  - [x] `trade-spot` includes `totalGasCostEthExact` + `totalGasCostEthPretty`
- [x] Tests:
  - [x] `test_trade_path` updates for status/faucet/run-loop behavior
  - [x] wallet-health guidance test added
- [x] Docs sync:
  - [x] `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - [x] `docs/XCLAW_SLICE_TRACKER.md`
  - [x] `docs/XCLAW_BUILD_ROADMAP.md`
  - [x] `docs/api/WALLET_COMMAND_CONTRACT.md`
  - [x] `skills/xclaw-agent/SKILL.md`
  - [x] `docs/CONTEXT_PACK.md`, `spec.md`, `tasks.md`, `acceptance.md`
- [x] Run all required gates (`db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`) and record evidence.
- [x] Run Slice 26 runtime tests (`test_trade_path` full + wallet-health guidance targeted).
- [x] Capture environment-dependent smoke outcomes (wrapper commands) with explicit blocker evidence.
- [x] Commit/push Slice 26 close-out and post verification evidence + commit hash to issue #21.

## Management incident follow-up checklist (2026-02-14)
- [x] Update management bootstrap API error guidance for one-time/host-scoped behavior.
- [x] Improve `/agents/:id` unauthorized + bootstrap-failure UX copy with actionable host guidance.
- [x] Add static asset integrity verifier script (`infrastructure/scripts/ops/verify-static-assets.sh`).
- [x] Update ops runbook with purge/warm + verifier sequence.
- [x] Update source-of-truth/roadmap/tracker notes for management host + asset guardrails.
- [x] Run mandatory gates (`db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`).
- [x] Run targeted runtime test for management-link host normalization.
- [x] Run static verifier against production and capture blocker output.

## Management incident gate hardening checklist (2026-02-14)
- [x] Add release-gate npm command for static verification (`npm run ops:verify-static-assets`).
- [x] Update runbook to use release-gate command and mark as blocking.
- [x] Update roadmap/tracker notes for release-gate command availability.
- [x] Re-run release-gate command against production and capture current blocker evidence.

## Agent sync-delay UX refinement checklist (2026-02-14)
- [x] Add `last_heartbeat_at` to public agents/profile API payloads.
- [x] Switch `/agents` and `/agents/:id` stale detection to heartbeat-based logic.
- [x] Increase stale/offline threshold from 60s to 180s for UI + ops heartbeat-miss summary.
- [x] Update source-of-truth to reflect heartbeat-based stale semantics and 180s threshold.
- [x] Run required gates and verify production static asset gate remains green.

---

# Slice 27 Tasks: Responsive + Multi-Viewport UI Fit (Phone + Tall + Wide)

Active slice: `Slice 27: Responsive + Multi-Viewport UI Fit (Phone + Tall + Wide)`
Issue mapping: `#22`

## Checklist
- [x] Create and map issue #22 for Slice 27.
- [x] Pre-flight lock: objective + acceptance checks + touched-file allowlist defined before edits.
- [x] Docs sync before UI edits:
  - [x] `docs/XCLAW_SLICE_TRACKER.md`
  - [x] `docs/XCLAW_BUILD_ROADMAP.md`
  - [x] `docs/XCLAW_SOURCE_OF_TRUTH.md`
- [x] `docs/CONTEXT_PACK.md`
- [x] `spec.md`
- [x] `tasks.md`
- [x] Global responsive foundation in `apps/network-web/src/app/globals.css`.
- [x] Update shell/header layout in `apps/network-web/src/components/public-shell.tsx`.
- [x] Dashboard (`/`) responsive table/card split and layout updates.
- [x] Agents directory (`/agents`) responsive table/card split and mobile filters.
- [x] Agent profile/management (`/agents/:id`) responsive trade cards + management usability improvements.
- [x] Status page (`/status`) mobile/tall/wide readability updates.
- [x] Run required gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
- [x] Record viewport verification matrix in `acceptance.md`.
- [x] Mark Slice 27 tracker/roadmap DoD complete.
- [x] Commit + push Slice 27.
- [x] Post verification evidence + commit hash(es) to issue #22.

---

# Slice 28 Tasks: Mock Mode Deprecation (Network-Only User Surface, Base Sepolia)

Active slice: `Slice 28: Mock Mode Deprecation (Network-Only User Surface, Base Sepolia)`
Issue mapping: `#23`

## Checklist
- [x] Create and map issue #23 for Slice 28.
- [x] Pre-flight lock: objective + acceptance checks + touched-file allowlist defined before edits.
- [x] Docs sync before implementation:
  - [x] `docs/XCLAW_SLICE_TRACKER.md`
  - [x] `docs/XCLAW_BUILD_ROADMAP.md`
  - [x] `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - [x] `docs/api/openapi.v1.yaml`
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
- [x] Remove mode controls/mock wording from web user-facing pages.
- [x] Public API read routes coerce mode compatibility to network/real-only outputs.
- [x] Agent runtime + skill reject mode=mock with structured unsupported_mode errors.
- [x] Update skill docs/references + hosted skill/install copy to network-only wording.
- [ ] Run required gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`
- [x] Run grep evidence command for user-facing mock removal.
- [x] Record evidence in `acceptance.md`.
- [x] Mark Slice 28 tracker/roadmap DoD complete.
- [x] Commit + push Slice 28.
- [x] Post verification evidence + commit hash(es) to issue #23.

---

# Slice 29 Tasks: Dashboard Chain-Scoped UX + Activity Detail + Chat-Style Room

Active slice: `Slice 29: Dashboard Chain-Scoped UX + Activity Detail + Chat-Style Room`
Issue mapping: `#24`

## Checklist
- [x] Create and map issue #24 for Slice 29.
- [x] Pre-flight lock: objective + acceptance checks + touched-file allowlist defined before edits.
- [x] Docs sync before implementation:
  - [x] `docs/XCLAW_SLICE_TRACKER.md`
  - [x] `docs/XCLAW_BUILD_ROADMAP.md`
  - [x] `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
- [x] Dashboard removes redundant chain chip/name text.
- [x] Trade room + live activity are filtered to active chain (`base_sepolia`) on dashboard.
- [x] Public activity payload includes optional trade detail fields for UI display (`pair` or `token_in -> token_out`).
- [x] Trade room adopts chat-style message card rendering.
- [x] Run required gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
- [x] Record evidence in `acceptance.md`.
- [x] Mark Slice 29 tracker/roadmap DoD complete.
- [x] Commit + push Slice 29.
- [x] Post verification evidence + commit hash(es) to issue #24.

---

# Slice 33 Tasks: MetaMask-Like Agent Wallet UX + Simplified Approvals (Global + Per-Token)

Active slice: `Slice 33: MetaMask-Like Agent Wallet UX + Simplified Approvals (Global + Per-Token)`

## Checklist
- [ ] Docs sync first:
  - [ ] `docs/XCLAW_SLICE_TRACKER.md`
  - [ ] `docs/XCLAW_BUILD_ROADMAP.md`
  - [ ] `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - [ ] `docs/api/openapi.v1.yaml`
  - [ ] `docs/CONTEXT_PACK.md`
  - [ ] `spec.md`
  - [ ] `tasks.md`
  - [ ] `acceptance.md`
- [ ] Deprecate legacy approval scopes:
  - [ ] UI removes any pair/global scope controls.
  - [ ] `POST /api/v1/management/approvals/scope` returns structured deprecation response (410) and is not used by UI.
- [ ] Server: trade proposal assigns initial approval state:
  - [ ] `POST /api/v1/trades/proposed` sets initial `trades.status` to `approved|approval_pending` based on:
    - [ ] Global Approval ON (`approval_mode=auto`) => `approved`
    - [ ] Global OFF and `tokenIn` preapproved (`allowed_tokens`) => `approved`
    - [ ] otherwise => `approval_pending`
  - [ ] `agent_events` uses `trade_approved` or `trade_approval_pending` for the initial event.
- [ ] Server: copy lifecycle aligns with simplified approvals:
  - [ ] follower trade status uses the same global/tokenIn gating
  - [ ] follower policy no longer rejects due to `allowed_tokens` mismatch (treated as preapproval, not allowlist)
- [ ] Runtime: server-first `trade spot`:
  - [ ] proposes to server before any on-chain tx
  - [ ] waits/polls if `approval_pending`
  - [ ] executes only if approved and posts status transitions
  - [ ] surfaces rejection reason on deny (`reasonCode/reasonMessage`)
- [ ] `/agents/:id` UX:
  - [ ] Wallet-first header (copyable address pill)
  - [ ] Assets list (MetaMask-like rows with icon placeholders)
  - [ ] Unified Activity feed (trades + events) in MetaMask-style list
  - [ ] Owner-only approvals panel supports reject reason message
  - [ ] Owner-only policy panel has Global Approval toggle + per-token preapproval toggles
- [ ] Gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

# Slice 52 Tasks: Policy Approval Prompts (Agent-Ready queuedMessage + Instructions)

Active slice: `Slice 52: Policy Approval Prompts (Agent-Ready queuedMessage + Instructions)`
Issue mapping: `#42` (umbrella)

## Checklist
- [x] Docs sync:
  - [x] `docs/XCLAW_SLICE_TRACKER.md`
  - [x] `docs/XCLAW_BUILD_ROADMAP.md`
  - [x] `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`
- [x] Runtime:
  - [x] policy approval request commands return `queuedMessage` + `agentInstructions`
- [x] Tests:
  - [x] assert `queuedMessage` contains `Status: approval_pending` + `Approval ID: ppr_...` and includes returned `policyApprovalId`
- [x] Gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

# Slice 53 Tasks: Policy Approval Revokes (Token + Approve All OFF) With Web + Telegram Buttons

Active slice: `Slice 53: Policy Approval Revokes (Token + Approve All OFF) With Web + Telegram Buttons`
Issue mapping: `#42` (umbrella)

## Checklist
- [x] Docs sync:
  - [x] `docs/XCLAW_SLICE_TRACKER.md`
  - [x] `docs/XCLAW_BUILD_ROADMAP.md`
  - [x] `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`
- [x] Server:
  - [x] extend policy approval propose requestType union to include revoke types
  - [x] apply revoke requests on approval (remove token / set approval_mode=per_trade)
- [x] Runtime/skill:
  - [x] add request commands for revoke token and revoke approve-all off
- [x] Web UI:
  - [x] show revoke request labels in policy approvals queue
- [x] Contracts:
  - [x] `packages/shared-schemas/json/agent-policy-approval-proposed-request.schema.json`
  - [x] `docs/api/openapi.v1.yaml`
- [x] Gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

# Slice 55 Tasks: Policy Approval De-Dupe (Reuse Pending Request)

Active slice: `Slice 55: Policy Approval De-Dupe (Reuse Pending Request)`
Issue mapping: `#42` (umbrella)

## Checklist
- [x] Docs sync:
  - [x] `docs/XCLAW_SLICE_TRACKER.md`
  - [x] `docs/XCLAW_BUILD_ROADMAP.md`
  - [x] `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`
- [x] Data model:
  - [x] add index for pending request lookup
- [x] Server:
  - [x] reuse existing `approval_pending` request when propose params match
- [x] Gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

# Slice 32 Tasks: Per-Agent Chain Enable/Disable (Owner-Gated, Chain-Scoped Ops)

Active slice: `Slice 32: Per-Agent Chain Enable/Disable (Owner-Gated, Chain-Scoped Ops)`

## Checklist
- [x] Docs sync first:
  - [x] `docs/XCLAW_SLICE_TRACKER.md`
  - [x] `docs/XCLAW_BUILD_ROADMAP.md`
  - [x] `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - [x] `docs/api/openapi.v1.yaml`
  - [x] `docs/api/WALLET_COMMAND_CONTRACT.md`
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`
- [x] Migration:
  - [x] add `infrastructure/migrations/0009_slice32_agent_chain_enable.sql` (`agent_chain_policies`)
- [x] API:
  - [x] add `POST /api/v1/management/chains/update`
  - [x] extend `GET /api/v1/management/agent-state` with optional `chainKey` and `chainPolicy` response
  - [x] extend `GET /api/v1/agent/transfers/policy` with `chainEnabled` fields
- [x] Server enforcement:
  - [x] block `POST /api/v1/trades/proposed` when chain disabled
  - [x] block `POST /api/v1/trades/:tradeId/status` execution transitions when chain disabled
  - [x] block `POST /api/v1/limit-orders` create when chain disabled
  - [x] block limit-order status `triggered|filled` when chain disabled
- [x] Runtime enforcement:
  - [x] block trade and `wallet-send` when owner chain access is disabled (`chainEnabled == false`)
  - [x] add unit tests for owner chain disabled enforcement
- [x] UI:
  - [x] `/agents/:id` shows “Chain Access” toggle for active chain context; enabling requires step-up
- [x] Gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

# Slice 30 Tasks: Owner-Managed Daily Trade Caps + Usage Visibility (Trades Only)

Active slice: `Slice 30: Owner-Managed Daily Trade Caps + Usage Visibility (Trades Only)`

## Checklist
- [x] Add Slice 30 tracker + roadmap entries.
- [x] Add migration: policy cap fields + `agent_daily_trade_usage` table.
- [x] Extend management policy schema with cap toggles/count.
- [x] Add agent trade usage request schema.
- [x] Implement `POST /api/v1/agent/trade-usage` (agent auth + idempotency).
- [x] Extend `GET /api/v1/agent/transfers/policy` with trade caps + UTC-day usage.
- [x] Extend `GET /api/v1/management/agent-state` with trade caps + UTC-day usage.
- [x] Persist cap fields in `POST /api/v1/management/policy/update`.
- [x] Add server-side cap checks for proposed/create/filled trade write paths.
- [x] Add runtime cap checks for spot/execute/limit-order-fill trade actions.
- [x] Add runtime usage report queue/replay path.
- [x] Update `/agents/:id` management rail with cap toggles/values + usage progress.
- [x] Sync source-of-truth/openapi/context/spec/tasks/acceptance artifacts.
- [x] Run required gates and capture evidence in `acceptance.md`.

---

# Slice 31 Tasks: Agents + Agent Management UX Refinement (Operational Clean)

Active slice: `Slice 31: Agents + Agent Management UX Refinement (Operational Clean)`

## Checklist
- [x] Add Slice 31 tracker + roadmap entries.
- [x] Update source-of-truth with Slice 31 locked UX/API refinements.
- [x] Extend `GET /api/v1/public/agents` with optional `includeMetrics` response enrichment.
- [x] Extend `GET /api/v1/public/activity` with optional `agentId` filter.
- [x] Refine `/agents` to card-first layout with KPI summaries and optional desktop table.
- [x] Refine `/agents/:id` public sections (overview/trades/activity readability and copy).
- [x] Re-group `/agents/:id` management rail into operational order.
- [x] Add progressive disclosure for advanced management sections.
- [x] Preserve Slice 30 cap controls/usage visibility and existing management actions.
- [x] Sync openapi/context/spec/tasks/acceptance artifacts.
- [x] Run required gates and capture evidence in `acceptance.md`.

---

# Slice 34 Tasks: Telegram Approvals (Inline Button Approve) + Web UI Sync

Active slice: `Slice 34: Telegram Approvals (Inline Button Approve) + Web UI Sync`
Issue mapping: `#42` (umbrella)

## Checklist
- [x] Docs sync first:
  - [x] `docs/XCLAW_SLICE_TRACKER.md`
  - [x] `docs/XCLAW_BUILD_ROADMAP.md`
  - [x] `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - [x] `docs/api/openapi.v1.yaml`
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`
- [x] Data model:
  - [x] `infrastructure/migrations/0010_slice34_telegram_approvals.sql`
- [x] Server:
  - [x] `POST /api/v1/management/approval-channels/update` (step-up gated on enable only; returns secret once)
  - [x] extend `GET /api/v1/management/agent-state` with `approvalChannels.telegram.enabled` for active chain
  - [x] extend `GET /api/v1/agent/transfers/policy` with `approvalChannels.telegram.enabled`
  - [x] `POST /api/v1/agent/approvals/prompt` (agent-auth)
  - [x] `POST /api/v1/channel/approvals/decision` (Bearer secret auth, approve-only)
- [x] UI:
  - [x] `/agents/:id` management rail toggle + one-time secret display + copy/instructions
- [x] Runtime:
  - [x] send Telegram prompt when trade is `approval_pending` and OpenClaw `lastChannel == telegram`
  - [x] delete prompt when trade leaves `approval_pending`
  - [x] implement `xclaw-agent approvals sync`
- [x] OpenClaw:
  - [x] intercept `xappr|...` callback before message routing (no LLM mediation)
  - [x] call X-Claw decision endpoint and delete message on success; edit message on failure
- [x] Gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`
- [x] Commit + push Slice 34 (exclude `memory/`)

---

# Slice 35 Tasks: Wallet-Embedded Approval Controls + Correct Token Decimals

Active slice: `Slice 35: Wallet-Embedded Approval Controls + Correct Token Decimals`
Issue mapping: `#42` (umbrella)

## Checklist
- [x] Docs sync first:
  - [x] `docs/XCLAW_SLICE_TRACKER.md`
  - [x] `docs/XCLAW_BUILD_ROADMAP.md`
  - [x] `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`
- [x] UI:
  - [x] Move approval policy controls into the wallet card on `/agents/:id`.
  - [x] Replace per-token toggles with per-asset preapproval buttons.
  - [x] Add `Approve all` toggle in wallet card (step-up gated on enable).
  - [x] Remove approval policy controls from the management rail (leave caps/risk limits).
  - [x] Expand audit log/details by default.
- [x] Balance formatting:
  - [x] Render token balances using decimals from deposit/balance snapshot (no hardcoded USDC decimals).
- [x] Gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

# Slice 36 Tasks: Remove Step-Up Authentication (Management Cookie Only)

Active slice: `Slice 36: Remove Step-Up Authentication (Management Cookie Only)`
Issue mapping: `#42` (umbrella)

## Checklist
- [x] Docs sync first:
  - [x] `docs/XCLAW_SLICE_TRACKER.md`
  - [x] `docs/XCLAW_BUILD_ROADMAP.md`
  - [x] `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - [x] `docs/api/openapi.v1.yaml`
  - [x] `docs/api/AUTH_WIRE_EXAMPLES.md`
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`
- [x] Data model:
  - [x] `infrastructure/migrations/0011_slice36_remove_stepup.sql` drops step-up tables/enum and removes legacy `approvals.requires_stepup`.
  - [x] Update `infrastructure/scripts/check-migration-parity.mjs` to remove step-up checks.
- [x] Server:
  - [x] Delete step-up endpoints (404 by removal):
    - [x] `apps/network-web/src/app/api/v1/management/stepup/challenge/route.ts`
    - [x] `apps/network-web/src/app/api/v1/management/stepup/verify/route.ts`
    - [x] `apps/network-web/src/app/api/v1/agent/stepup/challenge/route.ts`
  - [x] Remove `requireStepupSession` and step-up error codes.
  - [x] Remove step-up gating from withdraw, chain enable, telegram enable, policy update.
  - [x] Remove `stepup` field from management agent-state.
- [x] UI:
  - [x] Remove all step-up prompt/state from `/agents/:id`.
- [x] Runtime/skill:
  - [x] Remove `xclaw-agent stepup-code`.
  - [x] Remove `stepup-code` from skill wrapper and docs.
- [x] Ops scripts:
  - [x] Update `infrastructure/scripts/e2e-full-pass.sh` to remove step-up flows.
- [x] Gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

# Slice 37 Tasks: Telegram Approvals Without Extra Secret (Skill-Authoritative, Web + Telegram OR)

Active slice: `Slice 37: Telegram Approvals Without Extra Secret (Skill-Authoritative, Web + Telegram OR)`
Issue mapping: `#42` (umbrella)

## Checklist
- [x] Docs sync first:
  - [x] `docs/XCLAW_SLICE_TRACKER.md`
  - [x] `docs/XCLAW_BUILD_ROADMAP.md`
  - [x] `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - [x] `docs/api/openapi.v1.yaml`
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`
- [x] Server/API:
  - [x] `POST /api/v1/management/approval-channels/update` no longer issues a secret.
  - [x] Delete `/api/v1/channel/approvals/decision` and remove `channel-approval-decision-request.schema.json`.
- [x] Web UI:
  - [x] `/agents/:id` "Approval Delivery" card shows toggle only; no secret UI/instructions.
- [x] OpenClaw:
  - [x] Telegram callback approve uses agent-auth `POST /api/v1/trades/:tradeId/status` with `Idempotency-Key`.
- [x] Gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

# Slice 38 Tasks: Telegram Approval Prompt Details + Pending Approval De-Dupe (No Spam)

Active slice: `Slice 38: Telegram Approval Prompt Details + Pending Approval De-Dupe (No Spam)`
Issue mapping: `#42` (umbrella)

## Checklist
- [x] Docs sync first:
  - [x] `docs/XCLAW_SLICE_TRACKER.md`
  - [x] `docs/XCLAW_BUILD_ROADMAP.md`
  - [x] `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`
- [x] Runtime:
  - [x] Add local pending-intents file `pending-trade-intents.json` (0600) to reuse pending tradeIds.
  - [x] Increase approval wait timeout to 30 minutes.
  - [x] Telegram prompt includes swap summary details and tradeId.
  - [x] Clear local Telegram prompt state when trade leaves `approval_pending`.
- [x] Tests:
  - [x] Add unit coverage for de-dupe reuse and prompt content.
- [x] Gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

# Slice 39 Tasks: Approval Amount Visibility + Gateway Telegram Callback Reliability

Active slice: `Slice 39: Approval Amount Visibility + Gateway Telegram Callback Reliability`
Issue mapping: `#42` (umbrella)

## Checklist
- [x] Web UX:
  - [x] approval queue shows amount + tokenIn -> tokenOut
  - [x] activity feed trade rows show amountIn/amountOut
- [x] Gateway:
  - [x] OpenClaw callback handler intercepts `xappr|a|...` and posts agent-auth trade status update
  - [x] deletes approval message after success
  - [x] patch recorded under `patches/openclaw/003_openclaw-2026.2.9-dist-xclaw-approvals.patch`
- [x] Runtime:
  - [x] outbox replay is best-effort and does not block input validation failures
- [x] Gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

# Slice 40 Tasks: OpenClaw Patch Auto-Apply (Portable, No Restart Loops)

Active slice: `Slice 40: OpenClaw Patch Auto-Apply (Portable, No Restart Loops)`
Issue mapping: `#42` (umbrella)

## Checklist
- [x] Docs sync:
  - [x] `docs/XCLAW_SLICE_TRACKER.md`
  - [x] `docs/XCLAW_BUILD_ROADMAP.md`
  - [x] `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`
- [x] Implementation:
  - [x] add `skills/xclaw-agent/scripts/openclaw_gateway_patch.py` (idempotent, dynamic bundle detection, lock + cooldown)
  - [x] call patcher from `skills/xclaw-agent/scripts/setup_agent_skill.py`
  - [x] call patcher best-effort from `skills/xclaw-agent/scripts/xclaw_agent_skill.py`
- [x] Gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
- [x] `npm run build`
- [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

# Slice 41 Tasks: Telegram Approve Button Reliability (Patch Correct Gateway Bundle)

Active slice: `Slice 41: Telegram Approve Button Reliability (Patch Correct Gateway Bundle)`
Issue mapping: `#42` (umbrella)

## Checklist
- [x] Docs sync:
  - [x] `docs/XCLAW_SLICE_TRACKER.md`
  - [x] `docs/XCLAW_BUILD_ROADMAP.md`
  - [x] `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`
- [x] Implementation:
  - [x] update `skills/xclaw-agent/scripts/openclaw_gateway_patch.py` to patch gateway callback bundles used by `dist/index.js` (including `dist/reply-*.js`)
  - [x] patch is idempotent with stable marker/replace semantics (no duplicated blocks)
  - [x] record/update patch artifact in `patches/openclaw/`
- [x] Gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
- [x] `npm run build`
- [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

# Slice 42 Tasks: Telegram Approve+Deny + Approval Decision Chat Feedback + Safer De-Dupe

Active slice: `Slice 42: Telegram Approve+Deny + Approval Decision Chat Feedback + Safer De-Dupe`
Issue mapping: `#42` (umbrella)

## Checklist
- [x] Docs sync:
  - [x] `docs/XCLAW_SLICE_TRACKER.md`
  - [x] `docs/XCLAW_BUILD_ROADMAP.md`
  - [x] `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`
- [x] Runtime:
  - [x] change `trade spot` de-dupe: reuse only while `approval_pending`
  - [x] Telegram prompt includes Approve + Deny buttons
  - [x] when web approval/deny happens while waiting, send decision message into active Telegram chat
- [x] OpenClaw gateway patch:
  - [x] handle `xappr|a|...` (approve) and `xappr|r|...` (reject)
  - [x] delete prompt message and send confirmation message into same chat with details
- [x] Gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

# Slice 43 Tasks: Telegram Callback Idempotency Fix (No `idempotency_conflict`)

Active slice: `Slice 43: Telegram Callback Idempotency Fix (No idempotency_conflict)`
Issue mapping: `#42` (umbrella)

## Checklist
- [x] Docs sync:
  - [x] `docs/XCLAW_SLICE_TRACKER.md`
  - [x] `docs/XCLAW_BUILD_ROADMAP.md`
  - [x] `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`
- [x] Implementation:
  - [x] OpenClaw gateway patch uses `Idempotency-Key: tg-cb-<callbackId>`
  - [x] OpenClaw gateway patch uses deterministic `at` from Telegram callback/query timestamp
- [x] Gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
- [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

# Slice 44 Tasks: Faster Approval Resume (Lower Poll Interval)

Active slice: `Slice 44: Faster Approval Resume (Lower Poll Interval)`
Issue mapping: `#42` (umbrella)

## Checklist
- [x] Docs sync:
  - [x] `docs/XCLAW_SLICE_TRACKER.md`
  - [x] `docs/XCLAW_BUILD_ROADMAP.md`
  - [x] `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`
- [x] Implementation:
  - [x] set `APPROVAL_WAIT_POLL_SEC = 1` during `approval_pending` waits
- [x] Gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
- [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

# Slice 45 Tasks: Inline Telegram Approval Buttons (No Extra Prompt Message)

Active slice: `Slice 45: Inline Telegram Approval Buttons (No Extra Prompt Message)`
Issue mapping: `#42` (umbrella)

## Checklist
- [x] Docs sync:
  - [x] `docs/XCLAW_SLICE_TRACKER.md`
  - [x] `docs/XCLAW_BUILD_ROADMAP.md`
  - [x] `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`
- [x] Implementation:
  - [x] runtime defaults to no out-of-band Telegram approval prompt message
  - [x] `skills/xclaw-agent/SKILL.md` instructs to embed OpenClaw `[[buttons: ...]]` in queued Telegram approval message
- [x] Gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
- [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

# Slice 46 Tasks: Auto-Attach Telegram Approval Buttons To Queued Message

Active slice: `Slice 46: Auto-Attach Telegram Approval Buttons To Queued Message`
Issue mapping: `#42` (umbrella)

## Checklist
- [x] Docs sync:
  - [x] `docs/XCLAW_SLICE_TRACKER.md`
  - [x] `docs/XCLAW_BUILD_ROADMAP.md`
  - [x] `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`
- [x] Implementation:
  - [x] patch OpenClaw `sendMessageTelegram` to auto-attach buttons on queued `approval_pending` messages
- [x] Gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
- [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

# Slice 47 Tasks: Fix Telegram Queued Buttons Attach Point (Agent Reply Send Path)

Active slice: `Slice 47: Fix Telegram Queued Buttons Attach Point (Agent Reply Send Path)`
Issue mapping: `#42` (umbrella)

## Checklist
- [x] Docs sync:
  - [x] `docs/XCLAW_SLICE_TRACKER.md`
  - [x] `docs/XCLAW_BUILD_ROADMAP.md`
  - [x] `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`
- [x] Implementation:
  - [x] patch OpenClaw `sendTelegramText(bot, ...)` to auto-attach buttons for queued `approval_pending` messages
- [x] Gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

# Slice 48 Tasks: Queued Approval Buttons v3 Upgrade + Logging (Debuggable)

Active slice: `Slice 48: Queued Approval Buttons v3 Upgrade + Logging (Debuggable)`
Issue mapping: `#42` (umbrella)

## Checklist
- [x] Docs sync:
  - [x] `docs/XCLAW_SLICE_TRACKER.md`
  - [x] `docs/XCLAW_BUILD_ROADMAP.md`
  - [x] `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`
- [x] Implementation:
  - [x] OpenClaw patcher replaces queued-buttons v2 injection in `sendTelegramText(...)` with v3
  - [x] gateway logs include attach/skip messages
- [x] Gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

# Slice 49 Tasks: OpenClaw Patcher Safety (Syntax Check + Targeted Bundle)

Active slice: `Slice 49: OpenClaw Patcher Safety (Syntax Check + Targeted Bundle)`
Issue mapping: `#42` (umbrella)

## Checklist
- [x] Docs sync:
  - [x] `docs/XCLAW_SLICE_TRACKER.md`
  - [x] `docs/XCLAW_BUILD_ROADMAP.md`
  - [x] `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`
- [x] Implementation:
  - [x] patcher targets only `dist/reply-*.js`
  - [x] patcher validates patched output via `node --check` before writing
- [x] Gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

# Slice 50 Tasks: Telegram Decision Feedback Routed Through Agent (No Direct Gateway Ack)

Active slice: `Slice 50: Telegram Decision Feedback Routed Through Agent (No Direct Gateway Ack)`
Issue mapping: `#42` (umbrella)

## Checklist
- [x] Docs sync:
  - [x] `docs/XCLAW_SLICE_TRACKER.md`
  - [x] `docs/XCLAW_BUILD_ROADMAP.md`
  - [x] `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`
- [x] Implementation:
  - [x] Telegram callback intercept routes decision into agent pipeline via `processMessage(...)`
  - [x] fallback minimal ack message if synthetic processing fails
- [x] Gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

# Slice 51 Tasks: Policy Approval Requests (Token Preapprove + Approve All) With Web + Telegram Buttons

Active slice: `Slice 51: Policy Approval Requests (Token Preapprove + Approve All) With Web + Telegram Buttons`
Issue mapping: `#42` (umbrella)

## Checklist
- [x] Docs sync:
  - [x] `docs/XCLAW_SLICE_TRACKER.md`
  - [x] `docs/XCLAW_BUILD_ROADMAP.md`
  - [x] `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`
  - [x] `docs/api/openapi.v1.yaml`
  - [x] `packages/shared-schemas/json/*`
- [x] Data model:
  - [x] migration `0012_slice51_policy_approval_requests.sql`
- [x] Server:
  - [x] agent-auth propose policy approval request
  - [x] agent-auth approve/deny policy approval (Telegram callback)
  - [x] management approve/deny policy approval (web UI)
  - [x] management agent-state includes pending policy approvals
- [x] OpenClaw patch:
  - [x] auto-attach policy approval buttons on queued message
  - [x] callback intercept handles policy approval decisions and routes decision to agent pipeline
- [x] Runtime/skill:
  - [x] new CLI commands to request token/global policy approvals
  - [x] skill docs updated for prompt format (approval id + status)
- [ ] Gates:
  - [ ] `npm run db:parity`
  - [ ] `npm run seed:reset`
  - [ ] `npm run seed:load`
  - [ ] `npm run seed:verify`
  - [ ] `npm run build`
  - [ ] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

# Slice 56 Tasks: Trade Proposal Token Address Canonicalization (USDC Preapprove Fix)

Active slice: `Slice 56: Trade Proposal Token Address Canonicalization (USDC Preapprove Fix)`
Issue mapping: `#42` (umbrella)

## Checklist
- [x] Docs sync:
  - [x] `docs/XCLAW_SLICE_TRACKER.md`
  - [x] `docs/XCLAW_BUILD_ROADMAP.md`
  - [x] `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`
- [x] Implementation:
  - [x] update runtime `cmd_trade_spot` to propose `tokenIn`/`tokenOut` as canonical addresses
- [x] Tests:
  - [x] add regression test asserting address-form token payload for `_post_trade_proposed(...)`
- [x] Gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

# Slice 57 Tasks: Trade Execute Symbol Resolution (Prevent ERC20_CALL_FAIL Fallback)

Active slice: `Slice 57: Trade Execute Symbol Resolution (Prevent ERC20_CALL_FAIL Fallback)`
Issue mapping: `#42` (umbrella)

## Checklist
- [x] Docs sync:
  - [x] `docs/XCLAW_SLICE_TRACKER.md`
  - [x] `docs/XCLAW_BUILD_ROADMAP.md`
  - [x] `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`
- [x] Implementation:
  - [x] update runtime `cmd_trade_execute` token resolution to use canonical symbol/address resolver and remove hardcoded fallback token substitution
- [x] Tests:
  - [x] add regression test asserting symbol-form intent tokens resolve to canonical addresses before approve/swap tx calls
- [x] Gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

# Slice 58 Tasks: Trade Spot Re-Quote After Approval Wait (Prevent Stale SLIPPAGE_NET)

Active slice: `Slice 58: Trade Spot Re-Quote After Approval Wait (Prevent Stale SLIPPAGE_NET)`
Issue mapping: `#42` (umbrella)

## Checklist
- [x] Docs sync:
  - [x] `docs/XCLAW_SLICE_TRACKER.md`
  - [x] `docs/XCLAW_BUILD_ROADMAP.md`
  - [x] `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`
- [x] Implementation:
  - [x] update runtime `cmd_trade_spot` to re-quote output and recalculate minOut after approval wait and before swap
- [x] Tests:
  - [x] add regression test asserting swap minOut uses post-approval quote values
- [x] Gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

# Slice 59 Tasks: Trade Execute Amount Units Fix (Prevent 50 -> 50 Wei)

Active slice: `Slice 59: Trade Execute Amount Units Fix (Prevent 50 -> 50 Wei)`
Issue mapping: `#42` (umbrella)

## Checklist
- [x] Docs sync:
  - [x] `docs/XCLAW_SLICE_TRACKER.md`
  - [x] `docs/XCLAW_BUILD_ROADMAP.md`
  - [x] `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`
- [x] Implementation:
  - [x] update runtime `cmd_trade_execute` to parse `amountIn` as human token amount via token decimals
- [x] Tests:
  - [x] add regression test asserting execute-path approve/swap use decimal-scaled amount units
- [x] Gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

# Slice 60 Tasks: Prompt Normalization for USD Stablecoin + ETH->WETH Semantics

Active slice: `Slice 60: Prompt Normalization for USD Stablecoin + ETH->WETH Semantics`
Issue mapping: `#42` (umbrella)

## Checklist
- [x] Docs sync:
  - [x] `docs/XCLAW_SLICE_TRACKER.md`
  - [x] `docs/XCLAW_BUILD_ROADMAP.md`
  - [x] `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - [x] `skills/xclaw-agent/SKILL.md`
  - [x] `skills/xclaw-agent/references/commands.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`
- [x] Implementation:
  - [x] lock prompt semantics for `ETH -> WETH` in trade intents
  - [x] lock prompt semantics for `$`/`usd` as stablecoin notional intent
  - [x] lock disambiguation rule when multiple stablecoins have non-zero balances
- [x] Gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

# Slice 61 Tasks: Channel-Aware Approval Routing (Telegram vs Web Management Link)

Active slice: `Slice 61: Channel-Aware Approval Routing (Telegram vs Web Management Link)`
Issue mapping: `#42` (umbrella)

## Checklist
- [x] Docs sync:
  - [x] `docs/XCLAW_SLICE_TRACKER.md`
  - [x] `docs/XCLAW_BUILD_ROADMAP.md`
  - [x] `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - [x] `skills/xclaw-agent/SKILL.md`
  - [x] `skills/xclaw-agent/references/commands.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`
- [x] Implementation:
  - [x] lock non-Telegram channels to web management approval handoff (`owner-link`) with no Telegram buttons.
  - [x] preserve Telegram inline button behavior only for Telegram-focused chat contexts.
- [x] Gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

# Slice 62 Tasks: Policy Approval Telegram Decision Feedback Reliability

Active slice: `Slice 62: Policy Approval Telegram Decision Feedback Reliability`
Issue mapping: `#42` (umbrella)

## Checklist
- [x] Docs sync:
  - [x] `docs/XCLAW_SLICE_TRACKER.md`
  - [x] `docs/XCLAW_BUILD_ROADMAP.md`
  - [x] `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`
- [x] Implementation:
  - [x] update OpenClaw gateway patch injection to send deterministic success message on `xpol` approve/deny callbacks
  - [x] bump patch marker/schema to force upgrade on previously patched bundles
  - [x] apply patcher and verify patch result on installed OpenClaw bundle
- [x] Gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

# Slice 63 Tasks: Prompt Contract - Hide Internal Commands In User Replies

Active slice: `Slice 63: Prompt Contract - Hide Internal Commands In User Replies`
Issue mapping: `#42` (umbrella)

## Checklist
- [x] Docs sync:
  - [x] `docs/XCLAW_SLICE_TRACKER.md`
  - [x] `docs/XCLAW_BUILD_ROADMAP.md`
  - [x] `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - [x] `skills/xclaw-agent/SKILL.md`
  - [x] `skills/xclaw-agent/references/commands.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`
- [x] Implementation:
  - [x] lock user-facing rule to avoid command/tool-call leakage in normal chat replies.
  - [x] lock exception rule: provide exact command syntax only on explicit user request.
- [x] Gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

# Slice 64 Tasks: Policy Callback Convergence Ack (409 Still Replies)

Active slice: `Slice 64: Policy Callback Convergence Ack (409 Still Replies)`
Issue mapping: `#42` (umbrella)

## Checklist
- [x] Docs sync:
  - [x] `docs/XCLAW_SLICE_TRACKER.md`
  - [x] `docs/XCLAW_BUILD_ROADMAP.md`
  - [x] `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`
- [x] Implementation:
  - [x] update OpenClaw gateway callback branch so `xpol` `409` terminal responses still emit deterministic confirmation.
  - [x] bump patch marker/schema so old patched bundles are upgraded.
  - [x] apply patcher and verify installed bundle contains v5 marker + 409 convergence ack logic.
- [x] Gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

# Slice 65 Tasks: Telegram Decision UX - Keep Text, Remove Buttons

Active slice: `Slice 65: Telegram Decision UX - Keep Text, Remove Buttons`
Issue mapping: `#42` (umbrella)

## Checklist
- [x] Docs sync:
  - [x] `docs/XCLAW_SLICE_TRACKER.md`
  - [x] `docs/XCLAW_BUILD_ROADMAP.md`
  - [x] `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`
- [x] Implementation:
  - [x] update OpenClaw gateway callback success branch to clear inline buttons and keep queued message text.
  - [x] update converged `409` branch to clear inline buttons and keep queued message text.
  - [x] bump patch marker/schema and re-apply patcher.
  - [x] verify installed bundle includes decision marker v6 and no callback `deleteMessage` decision branch.
- [x] Gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

# Slice 66 Tasks: Policy Approval Consistency (Pending De-Dupe Race + Web Reflection)

Active slice: `Slice 66: Policy Approval Consistency (Pending De-Dupe Race + Web Reflection)`
Issue mapping: `#42` (umbrella)

## Checklist
- [x] Docs sync:
  - [x] `docs/XCLAW_SLICE_TRACKER.md`
  - [x] `docs/XCLAW_BUILD_ROADMAP.md`
  - [x] `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`
- [x] Implementation:
  - [x] make policy approval propose de-dupe transaction-safe under concurrency.
  - [x] keep policy propose API contract stable while reusing existing pending request deterministically.
  - [x] add management view polling to reflect Telegram/web policy approvals and denials without manual refresh.
- [x] Gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

# Slice 67 Tasks: Approval Decision Feedback + Activity Visibility Reliability

Active slice: `Slice 67: Approval Decision Feedback + Activity Visibility Reliability`
Issue mapping: `#42` (umbrella)

## Checklist
- [x] Docs sync:
  - [x] `docs/XCLAW_SLICE_TRACKER.md`
  - [x] `docs/XCLAW_BUILD_ROADMAP.md`
  - [x] `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`
- [x] Implementation:
  - [x] update OpenClaw callback patch to send deterministic confirmation for both trade + policy approve/deny.
  - [x] ensure converged terminal `409` callback path also sends deterministic confirmation.
  - [x] include `policy_*` events in `/api/v1/public/activity`.
  - [x] update activity labels/rendering for policy lifecycle events on `/agents/:id`.
- [x] Gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

# Slice 68 Tasks: Management Policy Approval History Visibility

Active slice: `Slice 68: Management Policy Approval History Visibility`
Issue mapping: `#42` (umbrella)

## Checklist
- [x] Docs sync:
  - [x] `docs/XCLAW_SLICE_TRACKER.md`
  - [x] `docs/XCLAW_BUILD_ROADMAP.md`
  - [x] `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`
- [x] Implementation:
  - [x] add `policyApprovalsHistory` to `/api/v1/management/agent-state`.
  - [x] render recent policy request history in `/agents/:id` Policy Approvals card.
  - [x] keep pending action queue behavior unchanged.
- [x] Gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

# Slice 69 Tasks: Dashboard Page #1 Full Rebuild (`/` + `/dashboard`)

Active slice: `Slice 69: Dashboard Full Rebuild (Global Landing Analytics + Discovery)`
Issue mapping: `#69` (to be created/mapped)

## Checklist
- [x] Pre-flight lock: objective + acceptance checks + touched-file allowlist defined before edits.
- [x] Docs sync:
  - [x] `docs/XCLAW_SLICE_TRACKER.md`
  - [x] `docs/XCLAW_BUILD_ROADMAP.md`
  - [x] `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`
- [x] Replace `/` dashboard page implementation from scratch.
- [x] Add `/dashboard` alias route.
- [x] Add dashboard-only shell behavior and preserve non-dashboard shell.
- [x] Implement dashboard controls/components:
  - [x] sidebar + sticky top bar
  - [x] global search autocomplete groups
  - [x] owner-only scope selector
  - [x] dashboard chain selector (`all/base_sepolia/hardhat_local`)
  - [x] dark/light icon toggle
  - [x] KPI strip + focus-tab interaction
  - [x] chart panel with tabs/range/filters
  - [x] live feed, top agents, recently active
  - [x] venue breakdown + execution health
  - [x] trending agents + docs card + footer links
- [x] Derived metrics visibly labeled when exact metrics unavailable.
- [x] Run required gates and record evidence.

---

# Slice 69A Tasks: Dashboard Agent Trade Room Reintegration

Active slice: `Slice 69A: Dashboard Agent Trade Room Reintegration`
Issue mapping: `#69A` (to be created/mapped)

## Checklist
- [x] Pre-flight lock: objective + acceptance checks + touched-file allowlist defined before edits.
- [x] Docs sync:
  - [x] `docs/XCLAW_SLICE_TRACKER.md`
  - [x] `docs/XCLAW_BUILD_ROADMAP.md`
  - [x] `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`
- [x] Extend dashboard load with chat endpoint fetch.
- [x] Add chain/scope-filtered room preview (`max 8`) below Live Trade Feed.
- [x] Add room card loading/empty/error states.
- [x] Add `/room` read-only full room route and wire `View all`.
- [x] Run required gates and record evidence.

---

# Slice 70 Tasks: Single-Trigger Spot Flow + Guaranteed Final Result Reporting

Active slice: `Slice 70: Single-Trigger Spot Flow + Guaranteed Final Result Reporting`
Issue mapping: `#70` (to be created/mapped)

## Checklist
- [x] Docs sync:
  - [x] `docs/XCLAW_SLICE_TRACKER.md`
  - [x] `docs/XCLAW_BUILD_ROADMAP.md`
  - [x] `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`
- [x] Runtime:
  - [x] add pending spot-flow persistence (`pending-spot-trade-flows.json`).
  - [x] record spot-flow context when `trade spot` is `approval_pending`.
  - [x] add `approvals resume-spot --trade-id --chain --json`.
  - [x] clear pending spot-flow on terminal outcomes.
- [x] Gateway patch:
  - [x] on `xappr approve`, guarded async trigger of `resume-spot`.
  - [x] resolve runtime binary deterministically (`XCLAW_AGENT_RUNTIME_BIN` + explicit fallbacks), avoiding PATH-only `xclaw-agent` lookup.
  - [x] deterministic final result message in same Telegram chat/thread.
  - [x] synthetic final-result route into agent pipeline.
  - [x] duplicate-callback in-flight guard.
- [x] Skill wrapper/docs:
  - [x] add `trade-resume <trade_id>` helper.
  - [x] update skill docs/reference to lock single-trigger spot behavior.
- [x] Tests:
  - [x] runtime tests for spot-flow persistence and resume behavior.
- [x] Required gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

# Slice 72 Tasks: Transfer Policy-Override Approvals (Keep Gate/Whitelist)

Active slice: `Slice 72: Transfer Policy-Override Approvals (Keep Gate/Whitelist)`
Issue mapping: `#72` (to be created/mapped)

## Checklist
- [x] Runtime evaluates outbound policy and routes blocked requests to approval queue.
- [x] Runtime execution supports one-off override mode for approved blocked-origin flows.
- [x] Transfer mirror payload/schema updated with policy-block metadata + execution mode.
- [x] Web/API routes include/read metadata fields for queue/history.
- [x] `/agents/:id` transfer approvals UI shows policy-block and override indicators.
- [x] Gateway deterministic transfer result includes override mode marker.
- [x] Required gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

# Slice 71 Tasks: Single-Trigger Outbound Transfers + Runtime-Canonical Transfer Approvals

Active slice: `Slice 71: Single-Trigger Outbound Transfers + Runtime-Canonical Transfer Approvals`
Issue mapping: `#71` (to be created/mapped)

## Checklist
- [x] Docs sync:
  - [x] `docs/XCLAW_SLICE_TRACKER.md`
  - [x] `docs/XCLAW_BUILD_ROADMAP.md`
  - [x] `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`
- [x] Runtime:
  - [x] pending transfer flows + transfer policy local state.
  - [x] `approvals decide-transfer`.
  - [x] `approvals resume-transfer`.
  - [x] `transfers policy-get` / `transfers policy-set`.
  - [x] orchestrated `wallet-send` / `wallet-send-token` queued approval path.
- [x] Gateway patch:
  - [x] support `xfer|a|...` / `xfer|r|...` callback intercept.
  - [x] deterministic transfer result message.
  - [x] synthetic transfer result route to agent pipeline.
- [x] API + UI:
  - [x] transfer approval mirror endpoints.
  - [x] transfer policy get/mirror/update endpoints.
  - [x] management transfer approvals list/decision endpoints.
  - [x] `/agents/:id` transfer approval policy + queue/history UI.
- [x] Required gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

# Slice 73 Tasks: Agent Page Full Frontend Refresh

Active slice: `Slice 73: Agent Page Full Frontend Refresh (Dashboard-Aligned, API-Preserving)`
Issue mapping: `#26`

## Checklist
- [x] Docs sync:
  - [x] `docs/XCLAW_SLICE_TRACKER.md`
  - [x] `docs/XCLAW_BUILD_ROADMAP.md`
  - [x] `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`
- [x] Replace `/agents/:id` page implementation with dashboard-aligned frontend layout.
- [x] Preserve existing management/public API calls and action handlers.
- [x] Add owner/viewer UI separation in refreshed layout.
- [x] Add explicit API-placeholder surfaces for unsupported modules.
- [x] Add view-model/capability helpers for the refreshed page:
  - [x] `apps/network-web/src/lib/agent-page-view-model.ts`
  - [x] `apps/network-web/src/lib/agent-page-capabilities.ts`
- [x] Add route-local stylesheet:
  - [x] `apps/network-web/src/app/agents/[agentId]/page.module.css`
- [x] Run required gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`

---

## Slice 78 Tasks: Root Landing Refactor + Install-First Onboarding (`/`)

- [x] Replace `apps/network-web/src/app/page.tsx` dashboard composition with landing composition.
- [x] Replace `apps/network-web/src/app/page.module.css` with landing visual system and responsive layout.
- [x] Implement finished-product header with section anchors and CTA pair (`Connect an OpenClaw Agent`, `Open Live Activity`).
- [x] Implement onboarding selector (`Human` / `Agent`) and local copy state.
- [x] Wire Human copy command exactly: `curl -fsSL https://xclaw.trade/skill-install.sh | bash`.
- [x] Wire Agent copy prompt exactly: `Please follow directions at https://xclaw.trade/skill.md`.
- [x] Keep hero focused on message + embedded quickstart card (no live-proof metric band).
- [x] Implement trust-first section stack: capabilities, lifecycle, trust/safety, observer experience, developer conversion, FAQ, final CTA.
- [x] Remove pricing tab/sign-in framing and remove standalone trade-room framing from landing content.
- [x] Run required gates sequentially (`db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, then `pm2 restart all`).

---

## Slice 82 Tasks: Track-Not-Copy Pivot (Saved Agents -> OpenClaw Watchlist)

Active slice: `Slice 82: Track-Not-Copy Pivot (Saved Agents -> OpenClaw Watchlist)`
Issue mapping: `#32`

## Checklist
- [x] Docs sync:
  - [x] `docs/XCLAW_SLICE_TRACKER.md`
  - [x] `docs/XCLAW_BUILD_ROADMAP.md`
  - [x] `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - [x] `docs/api/WALLET_COMMAND_CONTRACT.md`
  - [x] `docs/api/openapi.v1.yaml`
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`
- [x] DB migration + shared schemas for tracked relations and read payloads.
- [x] Management tracked APIs (list/add/remove + tracked trades).
- [x] Agent tracked APIs (list + tracked trades).
- [x] Extend management agent-state with tracked summaries.
- [x] Pivot Explore from copy CTA/modal to tracked actions.
- [x] Pivot `/agents/[agentId]` copy module to tracked module.
- [x] Sync left rail saved icons with server tracked list in owner session.
- [x] Add runtime tracked commands and dashboard fields.
- [x] Add skill wrapper tracked commands.
- [x] Keep copy routes operational but deprecated (transition compatibility).
- [x] Required gates:
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_tracked_runtime.py -v`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_x402_skill_wrapper.py -v`
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `pm2 restart all`
