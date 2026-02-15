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
  - [ ] `npm run db:parity`
  - [ ] `npm run seed:reset`
  - [ ] `npm run seed:load`
  - [ ] `npm run seed:verify`
  - [ ] `npm run build`
  - [ ] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

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
