# Slice 95 Tasks: Hedera EVM Pair Discovery + HTS JDK Auto-Setup (2026-02-19)

Active slice context: `Slice 95` remains in progress.

## 1) Scope lock
- [x] Keep scope to live evidence capture + canonical artifact sync.
- [x] Do not introduce new liquidity API/public interface paths.

## 2) Evidence execution
- [x] Run hosted installer flow (`curl -fsSL https://xclaw.trade/skill-install.sh | bash`).
- [x] Re-verify runtime readiness (`status`, `wallet health`, `chains`) for `hedera_testnet`.
- [x] Add deterministic runtime pair discovery command (`liquidity discover-pairs`) with reserve filter + deterministic error codes.
- [x] Run Hedera EVM pair-discovery probes across configured DEXes (`saucerswap`, `pangolin`) and capture viable candidate set.
- [x] Capture Hedera EVM quote/add intent output using discovered non-reverting pair.
- [x] Harden installer to attempt JDK auto-provision and Java toolchain verification for HTS runtime path.
- [x] Capture HTS quote/add success with JDK-enabled runtime (`JAVA_HOME` + runtime venv interpreter).
- [x] Capture residual tx-hash blocker evidence if command surface still does not submit on-chain LP tx.

## 3) Canonical sync
- [x] Update `acceptance.md` evidence matrix and rerun commands.
- [x] Update `docs/BOUNTY_ALIGNMENT_CHECKLIST.md` notes/evidence index with new IDs.
- [x] Update `docs/XCLAW_SLICE_TRACKER.md` Slice 95 DoD blocker text.
- [x] Update `docs/XCLAW_BUILD_ROADMAP.md` 95.1 blocker text.
- [x] Sync command contracts (`docs/XCLAW_SOURCE_OF_TRUTH.md`, `docs/api/WALLET_COMMAND_CONTRACT.md`, `skills/xclaw-agent/references/commands.md`).
- [x] Sync `spec.md` and `tasks.md` to this pass.

## 4) Validation
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] `npm run build`
- [x] `pm2 restart all`
- [x] `python3 -m unittest apps/agent-runtime/tests/test_liquidity_adapter.py -v`
- [x] `python3 -m unittest apps/agent-runtime/tests/test_liquidity_cli.py -v`

---

# Hotfix Tasks: Preserve Trade Approval History After Execution

Active slice context: `Slice 86` is in progress; this is an explicit user-reported approvals-history visibility hotfix.

## 1) Scope lock
- [x] Keep scope to approvals history read-models (inbox + agent-state views).
- [x] Preserve trade execution and approval decision behavior.

## 2) Implementation
- [x] Expand approvals inbox trade status selection to include post-approval execution states.
- [x] Normalize `executing|verifying|filled|failed` into Approved tab semantics in inbox.
- [x] Add `approvalsHistory` trade feed to management agent-state payload.
- [x] Render trade approval history rows in `/agents/[agentId]` approvals section, with pending-row dedupe.
- [x] Sync source-of-truth and handoff artifacts.

## 3) Validation
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] `npm run build`
- [x] `pm2 restart all`

---

# Hotfix Tasks: Truthful ETH Sepolia Wallet Checks + Multi-Chain Register Sync (2026-02-20)

Active slice context: `Slice 99` in progress.

## 1) Scope lock
- [x] Keep scope to skill/runtime wallet-chain routing and register payload composition.
- [x] Avoid schema/API contract changes.

## 2) Implementation
- [x] Add optional explicit chain override support for skill wallet commands (`wallet-health/address/sign/send/send-token/balance/token-balance/track/untrack/tracked-tokens/wrap-native/create`).
- [x] Update runtime `cmd_profile_set_name` register payload to include all enabled local wallet bindings from wallet store (primary chain first).
- [x] Add regression coverage for explicit chain override routing and multi-chain register payload behavior.

## 3) Validation
- [x] `python3 -m unittest -q apps.agent-runtime.tests.test_x402_skill_wrapper.X402SkillWrapperTests.test_wallet_balance_allows_explicit_chain_override`
- [x] `python3 -m unittest -q apps.agent-runtime.tests.test_x402_skill_wrapper.X402SkillWrapperTests.test_wallet_send_token_allows_explicit_chain_override`
- [x] `python3 -m unittest -q apps.agent-runtime.tests.test_trade_path.TradePathRuntimeTests.test_profile_set_name_success`
- [x] `python3 -m unittest -q apps.agent-runtime.tests.test_trade_path.TradePathRuntimeTests.test_profile_set_name_rate_limited`
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] `npm run build`
- [x] `pm2 restart all`

---

# Hotfix Tasks: Runtime-Canonical Approval Prompt Button Clear (Trade/Transfer/Policy)

Active slice context: `Slice 87` in progress.

## 1) Scope lock
- [x] Centralize cleanup into runtime command `approvals clear-prompt`.
- [x] Preserve non-destructive contract (clear buttons only, keep message text).

## 2) Implementation
- [x] Added runtime helper + command `approvals clear-prompt --subject-type --subject-id [--chain] --json`.
- [x] Updated runtime `decide-spot|decide-transfer|decide-policy` cleanup to use shared clear helper.
- [x] Removed approval prompt delete-command behavior from runtime cleanup paths.
- [x] Updated web trade/transfer/policy decision routes to dispatch runtime cleanup and return `promptCleanup`.
- [x] Updated gateway callback patch to runtime-owned clear path (removed immediate callback pre-clear).
- [x] Synced source-of-truth, roadmap, tracker, and skill command docs.

## 3) Validation
- [x] `python3 -m py_compile apps/agent-runtime/xclaw_agent/cli.py apps/agent-runtime/tests/test_trade_path.py skills/xclaw-agent/scripts/openclaw_gateway_patch.py`
- [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`
- [x] `python3 skills/xclaw-agent/scripts/openclaw_gateway_patch.py --json`
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] `npm run build`
- [x] `pm2 restart all`

---

# Hotfix Tasks: Always Prod Agent After Web Trade/Transfer Approvals

Active slice context: `Slice 86` is in progress; this is an explicit user-requested workflow-continuation hotfix.

## 1) Scope lock
- [x] Restrict changes to web decision prod-dispatch behavior.
- [x] Preserve Telegram callback execution semantics.

## 2) Implementation
- [x] Add per-dispatch override in `dispatchNonTelegramAgentProd` to allow Telegram-last-channel prod dispatch for selected flows.
- [x] Enable override in web trade decision + terminal result dispatch path.
- [x] Enable override in web transfer decision + terminal result dispatch path.
- [x] Enable override in web trade allowlist-approve decision dispatch path.
- [x] Sync source-of-truth and handoff artifacts.

## 3) Validation
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] `npm run build`
- [x] `pm2 restart all`

---

# Hotfix Tasks: Policy Approval Telegram Auto-Prompt Parity (Preapprove/Revoke/Global)

Active slice context: `Slice 86` is in progress; this is an explicit user-requested Telegram approval UX alignment hotfix.

## 1) Scope lock
- [x] Keep scope to policy preapprove/revoke/global runtime + skill/gateway prompt behavior.
- [x] Preserve existing trade/transfer behavior.

## 2) Implementation
- [x] Add runtime helper `_maybe_send_telegram_policy_approval_prompt(...)` with `xpol` callbacks.
- [x] Wire helper into policy request commands: token add/remove + global enable/disable.
- [x] Remove dependency on `queuedMessage` repost for policy request success payloads.
- [x] Normalize pending policy response in skill wrapper to concise approval guidance.
- [x] Harden gateway fallback auto-attach for policy IDs without strict `Status: approval_pending` dependency.
- [x] Bump gateway patch marker/schema for rollout upgrade.
- [x] Sync skill docs and source-of-truth.
- [x] Update handoff artifacts.

## 3) Validation
- [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`
- [x] `python3 -m py_compile skills/xclaw-agent/scripts/openclaw_gateway_patch.py`
- [x] `python3 skills/xclaw-agent/scripts/openclaw_gateway_patch.py --json`
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] `npm run build`
- [x] `pm2 restart all`

---

# Hotfix Tasks: Force-Upgrade Gateway Callback Patch (v15) For Trade-Approve Ack Suppression

# Hotfix Tasks: Web Approval Prompt Cleanup Recovery + Message ID Extraction Hardening

Active slice context: `Slice 87` is in progress; this is an explicit user-reported web-vs-Telegram approval convergence fix.

## 1) Scope lock
- [x] Keep scope to runtime message-id extraction + web decision cleanup fallback.
- [x] Preserve trade execution semantics and callback behavior.

## 2) Implementation
- [x] Harden `_extract_openclaw_message_id` with non-JSON fallback patterns.
- [x] Add runtime command `approvals cleanup-spot --trade-id ... --json`.
- [x] Add web decision fallback: when DB cleanup fails with `missing_message_id|prompt_not_found`, call runtime cleanup command and reconcile prompt row on success.
- [x] Allow terminal trade-result prod dispatch (`web_trade_status`) to deliver to Telegram-last-channel for web approval parity.
- [x] Switch web prompt cleanup from full message delete to Telegram inline-button clear (`editMessageReplyMarkup`), preserving message text/history.
- [x] Enable delivery in web/terminal prod dispatcher (`openclaw agent ... --deliver`) so fulfill/reject prods reach chat.
- [x] Add runtime tests for extraction fallback + cleanup command.
- [x] Sync source-of-truth and skill command docs.

## 3) Validation
- [x] `python3 -m py_compile apps/agent-runtime/xclaw_agent/cli.py apps/agent-runtime/tests/test_trade_path.py skills/xclaw-agent/scripts/openclaw_gateway_patch.py`
- [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`
- [x] `python3 skills/xclaw-agent/scripts/openclaw_gateway_patch.py --json`
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] `npm run build`
- [x] `pm2 restart all`

# Runtime-Canonical Approval Decisions (Trade/Transfer/Policy)

## Scope
- [x] Add runtime decision commands: `decide-spot`, `decide-policy`.
- [x] Normalize `decide-transfer` envelope with source metadata.
- [x] Feature-flag runtime-canonical web dispatch for trade/policy decisions.
- [x] Keep transfer web path runtime-dispatched and pass `--source web`.
- [x] Add runtime tests for new decision commands.
- [x] Telegram callback path migrated to runtime `decide-*` commands (`xappr`, `xpol`, `xfer`) in gateway patch.
- [x] Callback runtime command calls include deterministic metadata passthrough (`--source telegram`, `--idempotency-key tg-cb-<callbackId>`, `--decision-at <iso8601>`).
- [x] Callback runtime binary resolution hardened to env/PATH only (no hardcoded home-path launcher fallbacks).

Active slice context: `Slice 86` is in progress; this is an explicit user-reported rollout reliability hotfix.

## 1) Scope lock
- [x] Force-upgrade patch semantics for already-patched bundles.
- [x] No functional drift beyond existing `xappr` approve-ack suppression intent.

## 2) Implementation
- [x] Add `DECISION_ACK_MARKER_V15` marker.
- [x] Require `v15` marker in upgrade/fast-path gating checks.
- [x] Include `v15` marker in canonical injected callback block.
- [x] Bump patch state schema to invalidate cached already-patched state.
- [x] Update handoff artifacts (`spec.md`, `tasks.md`, `acceptance.md`).

## 3) Validation
- [x] `python3 -m py_compile skills/xclaw-agent/scripts/openclaw_gateway_patch.py`
- [x] `python3 skills/xclaw-agent/scripts/openclaw_gateway_patch.py --json`
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] `npm run build`
- [x] `pm2 restart all`

---

# Hotfix Tasks: Suppress Telegram Intermediate "Approved trade" Ack For Conversions

Active slice context: `Slice 86` is in progress; this is an explicit user-requested Telegram UX hotfix.

## 1) Scope lock
- [x] Change only trade-approve callback acknowledgment behavior.
- [x] Preserve policy/transfer confirmation behavior.
- [x] Preserve final trade-result message behavior.

## 2) Implementation
- [x] Update OpenClaw gateway patch injection to suppress approve-ack send for `xappr` approve success path.
- [x] Update converged `409` callback path to suppress `Approved trade ...` emission for `xappr`.
- [x] Update fallback ack path to suppress `Approved trade ...` emission for `xappr` approve.
- [x] Sync source-of-truth decision feedback contract.
- [x] Update handoff artifacts (`spec.md`, `tasks.md`, `acceptance.md`).

## 3) Validation
- [x] `python3 -m py_compile skills/xclaw-agent/scripts/openclaw_gateway_patch.py`
- [x] `python3 skills/xclaw-agent/scripts/openclaw_gateway_patch.py --json`
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] `npm run build`
- [x] `pm2 restart all`

---

# Hotfix Tasks: X-Claw Skill Prompt Contract Hardening (Fail-Closed Determinism)

Active slice context: `Slice 86` is in progress; this is an explicit user-requested prompt-contract hotfix.

## 1) Scope lock
- [x] Skills/docs-only change; no runtime/API logic change.
- [x] Keep prompt behavior deterministic and fail-closed.

## 2) Implementation
- [x] Add locked fail-closed response contract to `skills/xclaw-agent/SKILL.md`.
- [x] Add deterministic prompting contract to `skills/xclaw-agent/references/commands.md`.
- [x] Sync canonical source-of-truth with locked skill prompting/response contract.
- [x] Add/update handoff artifacts (`spec.md`, `tasks.md`, `acceptance.md`).
- [x] Add deterministic single primary-code precedence across skill prompt contracts.
- [x] Add fixed `BLOCKED_<CATEGORY>` enum contract.
- [x] Add explicit `NOT_VISIBLE` trigger constraints.
- [x] Add required machine envelope (`status`, `code`, `summary`, `actions`, `evidence`).
- [x] Add explicit two-layer response contract (machine envelope + ordered human sections).
- [x] Add evidence mapping rule (machine `evidence` IDs must be referenced in human `Evidence` section).
- [x] Add deterministic multi-condition code rule (highest precedence code only; others in `actions`).

## 3) Validation
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] `npm run build`
- [x] `pm2 restart all`

---

# Hotfix Tasks: Capability-Gated Telegram Patch + Management-Link Fallback

Active slice context: `Slice 87` remains in progress; this is an explicit owner-requested installer reliability hotfix.

## 1) Scope lock
- [x] Shell installer only (`/skill-install.sh`) for install-mode behavior split.
- [x] No API/schema/migration changes.

## 2) Implementation
- [x] Installer runs setup patch-first; on permission-denied patch write failure it auto-retries with patch disabled.
- [x] Installer persists `XCLAW_TELEGRAM_APPROVALS_FORCE_MANAGEMENT` (`1` degraded, `0` normal) in OpenClaw skill env.
- [x] Installer emits explicit degraded-mode warning and sudo rerun command for restoring inline buttons.
- [x] Skill wrapper uses forced-management flag to include management-link handoff for Telegram `approval_pending`.
- [x] Skill prompt contracts + canonical docs/roadmap/tracker updated.

## 3) Validation
- [x] `python3 -m py_compile skills/xclaw-agent/scripts/xclaw_agent_skill.py`
- [x] `python3 -m unittest apps/agent-runtime/tests/test_x402_skill_wrapper.py -v`
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] `npm run build`
- [x] `pm2 restart all`

---

# Hotfix Tasks: Telegram Transfer Callback Pairing-Prompt Regression

Active slice context: `Slice 87` remains in progress; this is an explicit operator-reported reliability hotfix.

## 1) Scope lock
- [x] Keep transfer callback deterministic result message.
- [x] Prevent transfer callback from re-entering chat pipeline in a way that triggers pairing/access prompts.

## 2) Implementation
- [x] Gateway patch no longer re-injects synthetic transfer-result messages via `processMessage(...)` in Telegram callback path.
- [x] Gateway patch version marker/schema bumped so existing installs upgrade.
- [x] Skill wrapper keeps known symbol-unit guard rejections non-fatal to avoid noisy `Exec ... failed` chat traces when no tx was sent.
- [x] Docs/tracker/roadmap updated for behavior contract.

## 3) Validation
- [x] `python3 -m unittest apps/agent-runtime/tests/test_x402_skill_wrapper.py -v`
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] `npm run build`
- [x] `pm2 restart all`

---

# Hotfix Tasks: Terminal-Only Agent Callback Notifications (Telegram)

Active slice context: `Slice 86` remains in progress; this is an explicit operator UX hotfix.

## 1) Scope lock
- [x] Lock callback behavior to terminal/rejection notifications for agent pipeline.
- [x] Keep deterministic Telegram user-facing callback confirmations intact.

## 2) Implementation
- [x] Trade callback approve path (`xappr|a`) keeps auto-resume behavior.
- [x] Trade callback no longer notifies agent pipeline on non-terminal `approved`.
- [x] Trade callback now notifies agent pipeline on terminal `filled|failed`.
- [x] Trade/policy callback deny path notifies agent pipeline (`rejected`).
- [x] Docs updated for notification contract in source-of-truth + skill.

## 3) Validation
- [x] `XCLAW_AGENT_HOME=/tmp/xclaw-agent-test python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] `npm run build`
- [x] `pm2 restart all`
- [x] `python3 skills/xclaw-agent/scripts/openclaw_gateway_patch.py --json`

---

# Hotfix Tasks: Telegram Trade Result Noise + Swap-Deposit Misclassification

Active slice context: `Slice 86` is currently in progress; this is an explicit user-requested hotfix outside sequential slice work.

## 1) Scope lock
- [x] Define objective + acceptance checks + touched files before edits.
- [x] Keep changes limited to deposit ingestion filter + Telegram callback patch behavior.

## 2) Implementation
- [x] Exclude trade tx hashes from `deposit_events` ingestion in management deposit sync route.
- [x] Remove noisy deterministic trade-result Telegram post in callback resume path.
- [x] Remove placeholder fallbacks (`?`, `TOKEN_IN`, `TOKEN_OUT`) from trade-result composition logic.
- [x] Ensure patch-upgrade path rewrites already-patched gateway bundles.

## 3) Validation
- [x] `XCLAW_AGENT_HOME=/tmp/xclaw-agent-test python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] `npm run build`
- [x] `pm2 restart all`

---

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

## Slice 86-88 Tasks Addendum

- [x] Add migration: `management_session_agents` + policy snapshot `chain_key`.
- [x] Extend management auth to authorize linked managed agents.
- [x] Add bootstrap-time session linking for additional agents.
- [x] Make policy updates chain-scoped (`chainKey` required).
- [x] Add approve+allowlist API.
- [x] Add unified approvals inbox API with risk labels + permission inventory.
- [x] Add permissions update API.
- [x] Add batch decision API.
- [x] Rewire `/approvals` to inbox API, bulk actions, and permissions inventory.
- [ ] Run full required validation + collect evidence.

## Non-Telegram Web Agent Prod Bridge Tasks Addendum

- [x] Add shared helper `apps/network-web/src/lib/non-telegram-agent-prod.ts`.
- [x] Add dispatch hooks for trade decision and approve+allowlist decision routes.
- [x] Add dispatch hooks for transfer decision route (decision + terminal).
- [x] Add terminal dispatch hook for trade status route (non-replay only).
- [x] Add terminal dispatch hook for transfer mirror route (status-change only).
- [x] Add Telegram guard and no-`--deliver`/no-`message send` invariants.
- [x] Update source-of-truth + roadmap + tracker + handoff docs.
- [ ] Run required validation sequence and capture evidence.

## Slice 89 Tasks Addendum (MetaMask-Style Gas Estimation)

- [x] Add runtime fee planner `_estimate_tx_fees(rpc_url, attempt_index)` with EIP-1559 primary + legacy fallback.
- [x] Add RPC JSON helper path for gas estimation calls (`eth_feeHistory`, `eth_maxPriorityFeePerGas`, `eth_gasPrice`).
- [x] Refactor `_cast_rpc_send_transaction(...)` to:
  - [x] support native value sends and contract calldata sends,
  - [x] emit EIP-1559 send args when available,
  - [x] preserve nonce assignment and retry/error handling.
- [x] Route native `wallet-send` execution through unified sender in `_execute_pending_transfer_flow(...)`.
- [x] Add env controls:
  - [x] `XCLAW_TX_FEE_MODE`
  - [x] `XCLAW_TX_RETRY_BUMP_BPS`
  - [x] `XCLAW_TX_PRIORITY_FLOOR_GWEI`
- [x] Update runtime tests (`apps/agent-runtime/tests/test_trade_path.py`) for:
  - [x] EIP-1559 estimate path
  - [x] fallback legacy estimate path
  - [x] EIP-1559 cast send args
- [x] Sync docs/handoff artifacts in same change.
- [ ] Run full required validation sequence and capture evidence.

## Slice 90 Tasks Addendum (Liquidity + Multi-DEX Foundation)

- [x] Add migration `0023_slice90_liquidity_foundation.sql`.
- [x] Add shared schemas for liquidity proposed/status/position/approval.
- [x] Add API routes:
  - [x] `POST /api/v1/liquidity/proposed`
  - [x] `POST /api/v1/liquidity/{intentId}/status`
  - [x] `GET /api/v1/liquidity/pending`
  - [x] `GET /api/v1/liquidity/positions`
- [x] Add runtime liquidity command tree and capability gating.
- [x] Add skill wrapper liquidity command delegation.
- [x] Extend chain config contract with `capabilities.liquidity` + protocol metadata.
- [x] Extend management agent-state with `liquidityPositions`.
- [x] Add `/agents/[agentId]` separate Liquidity Positions section (chain-scoped).
- [x] Sync canonical docs/artifacts (tracker/roadmap/source/openapi/wallet contract/commands).
- [x] Required gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `pm2 restart all`

---

# Slice 90 Tasks: Mainnet/Testnet Dropdown + Agent-Canonical Default Chain Sync

## 1) Scope lock
- [x] Keep explicit command `--chain` precedence unchanged.
- [x] Keep faucet support constrained to capability-enabled testnets.
- [x] Keep source-of-truth for default chain in runtime state.

## 2) Implementation
- [x] Add runtime commands: `default-chain get`, `default-chain set --chain ...`.
- [x] Persist runtime default chain in agent-local `state.json.defaultChain`.
- [x] Add skill wrapper commands: `default-chain-get`, `default-chain-set <chain_key>`.
- [x] Add management endpoints:
  - [x] `GET /api/v1/management/default-chain`
  - [x] `POST /api/v1/management/default-chain`
  - [x] `POST /api/v1/management/default-chain/update-batch`
- [x] Update selector to sync default chain across all managed agents and rollback on sync failure.
- [x] Add startup reconciliation from runtime canonical default chain.
- [x] Enable configured mainnet+testnet chain configs for selector visibility.
- [x] Extend `/api/v1/public/chains` capabilities payload with `liquidity`.
- [x] Add shared schemas for default-chain management endpoints.
- [x] Sync canonical docs (`source-of-truth`, wallet command contract, openapi, roadmap, tracker, skill command refs).

## 3) Validation
- [x] `python3 -m py_compile apps/agent-runtime/xclaw_agent/cli.py skills/xclaw-agent/scripts/xclaw_agent_skill.py apps/agent-runtime/tests/test_wallet_core.py`
- [~] `python3 -m unittest apps/agent-runtime/tests/test_wallet_core.py -v`
  - baseline repo suite includes pre-existing wallet import/remove and cast expectation failures outside this slice scope.
- [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] `npm run build`
- [x] `pm2 restart all`

---

# Program Tasks: Liquidity Program Slices 90-95 (Runtime + API + Web)

Active slice context: Slice 90 close-out -> Slice 95 hardening/evidence sequence.

## 1) Slice 90 close-out
- [~] Align tracker/roadmap status to implemented Slice 90 baseline + current validation state.
- [~] Record validation/test evidence in acceptance artifact.

## 2) Slice 91/92 runtime adapter implementation
- [x] Rework liquidity adapter module to chain-config-driven routing with explicit protocol-family classes.
- [x] Add deterministic unsupported-adapter and fail-closed Hedera dependency error paths.
- [x] Enforce preflight simulation before `liquidity add/remove` proposal submission.
- [x] Add runtime tests for adapter routing + CLI preflight behavior.

## 3) Slice 93 API/indexing implementation
- [x] Add fail-soft position sync helper on 60s cadence.
- [x] Trigger sync from liquidity positions + management agent-state read paths.
- [x] Trigger force-sync on terminal liquidity status transitions.
- [x] Persist optional fee events from status update payload details.
- [x] Use liquidity-specific transition conflict code.

## 4) Slice 94 web liquidity section completion
- [x] Render required liquidity row context (chain, dex, pair/pool, type).
- [x] Show stale indicator when snapshot exceeds SLA.
- [x] Keep chain-filtered view behavior unchanged.

## 5) Slice 95 hardening/evidence sync
- [~] Run required gate commands sequentially.
- [~] Update bounty checklist and issue/evidence references.

---

# Continuation Tasks: Slice 90 Close-Out + Slice 95 Evidence (UTC 2026-02-19)

## 1) Slice 90 close-out
- [x] Diagnose and unblock liquidity API contract suite on active runtime DB (`0023` migration applied).
- [x] Add and run liquidity API contract command (`npm run test:liquidity:contract`).
- [x] Mark roadmap item `90.3 API contract tests` complete with concrete evidence.
- [x] Mark Slice 90 tracker status complete.

## 2) Slice 95 evidence/hardening
- [x] Capture hardhat-local liquidity contract evidence first.
- [x] Probe Base Sepolia runtime liquidity quote/proposal path.
- [x] Capture approval-required and auto-approved add-intent evidence.
- [x] Capture deterministic failure evidence (`unsupported_liquidity_adapter`, Hedera fail-closed unit path).
- [x] Attempt Hedera live proof and document blockers with exact rerun commands.
- [x] Update `docs/BOUNTY_ALIGNMENT_CHECKLIST.md` evidence IDs (`E1..E7`) with `[x]/[!]` state.

## 3) Finalization
- [x] Run required validation gates sequentially.
- [x] `pm2 restart all` after successful build.
- [ ] Commit/push and post issue evidence comments (#36/#41) with commit hash.

---

# Slice 95 Tasks Addendum: Hedera EVM + HTS Evidence Closure (UTC 2026-02-19)

## 1) Runtime HTS path separation
- [x] Update `liquidity quote-add` to bypass EVM router/token-metadata requirements when adapter family is `hedera_hts`.
- [x] Keep HTS missing SDK mapped to deterministic `missing_dependency`.
- [x] Preserve existing EVM `amm_v2/amm_v3` quote behavior.
- [x] Annotate HTS add intent payload details with `htsNative=true`.

## 2) Hedera chain-pack readiness
- [x] Add Hedera testnet/mainnet `coreContracts.router` values.
- [x] Add Hedera canonical token mappings for runtime symbol resolution.
- [x] Record source references in notes/evidence.

## 3) Runtime regression tests
- [x] Add test that HTS quote path is router-independent.
- [x] Add test that EVM quote path still uses router metadata path.
- [x] Add test that HTS add payload marks `htsNative` details.
- [x] Extend adapter tests for Hedera EVM protocol resolution.

## 4) Evidence runbook execution
- [x] Capture Hedera wallet preflight status.
- [x] Capture Hedera EVM quote attempt outcome.
- [x] Capture Hedera EVM add-intent outcome (`policy_denied` and `approved` after policy snapshot).
- [x] Capture Hedera HTS quote/add fail-closed `missing_dependency` outcomes.
- [x] Update bounty/acceptance evidence IDs and blocker notes.

## 5) Finalization
- [x] Run required validation gates sequentially.
- [x] `pm2 restart all` after successful build.
- [ ] Commit/push and post updated issue #41 evidence with commit hash.

---

# Slice 95 Tasks Addendum: Auto-Execute Approved Liquidity Intents (UTC 2026-02-19)

## 1) Runtime execution path
- [x] Add `liquidity execute` command for approved intents.
- [x] Add `liquidity resume` command as execution alias.
- [x] Add liquidity status posting helper for `executing|verifying|filled|failed|verification_timeout`.
- [x] Add `amm_v2` add execution path (`addLiquidity`) with approval checks.
- [x] Add `amm_v2` remove execution path (`removeLiquidity`) with pair/snapshot/LP-balance derivation.
- [x] Add deterministic v3 execution rejection (`unsupported_liquidity_execution_family`).

## 2) HTS plugin bridge
- [x] Add optional HTS plugin bridge loader in adapter (`XCLAW_HEDERA_HTS_PLUGIN`).
- [x] Enforce deterministic fail-closed `missing_dependency` for missing plugin/sdk.
- [x] Add adapter tests for plugin success + missing module + invalid plugin response.

## 3) Approval auto-run integration
- [x] Extend management approval schema for trade/liquidity decision payloads.
- [x] Extend `POST /api/v1/management/approvals/decision` to support `subjectType=liquidity`.
- [x] Queue runtime `liquidity execute` automatically on approved liquidity decisions.
- [x] Add runtime-canonical liquidity decision invocation + queue fallback.
- [x] Add non-telegram liquidity decision message builder for parity.

## 4) Validation and evidence
- [x] Required gate sequence completed (`db:parity`, seed reset/load/verify, build, pm2 restart).
- [x] Runtime unit suites pass (`test_liquidity_adapter.py`, `test_liquidity_cli.py`).
- [!] Route-level management liquidity decision contract command added and executed, but blocked by invalid management bootstrap token (`401 auth_invalid`) in this environment.
- [!] Live Hedera EVM/HTS tx-hash closure still blocked by environment prerequisites (`CONTRACT_REVERT_EXECUTED` on EVM add and missing HTS plugin bridge module).

---

# Slice 95A Tasks Addendum: Readiness + Determinism (UTC 2026-02-19)

## 1) Management test bootstrap determinism
- [x] Add owner-link fallback to auto-issue fresh management bootstrap token when token file is missing/stale.
- [x] Persist refreshed token to bootstrap token file for repeatability.
- [!] Route-level management decision command still blocked in this sandbox when local API host is unreachable (`fetch failed` to `127.0.0.1:3000`).

## 2) HTS plugin packaging
- [x] Add concrete runtime module `xclaw_agent.hedera_hts_plugin` with `execute_liquidity(...)`.
- [x] Use explicit bridge command contract via `XCLAW_HEDERA_HTS_BRIDGE_CMD`.
- [x] Keep deterministic fail-closed behavior (`HederaSdkUnavailable`) when SDK/runtime bridge prerequisites are absent.

## 3) EVM execution diagnostics
- [x] Add deterministic addLiquidity pre-submit checks (wallet token balance, gas balance, pair reserves, simulation call).
- [x] Emit deterministic preflight reason codes (`liquidity_preflight_*`) through execution failure details.
- [x] Add regression coverage for deterministic reason-code surfacing.

## 4) Validation
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] `npm run build`
- [x] `pm2 restart all`
- [x] `python3 -m unittest apps/agent-runtime/tests/test_liquidity_adapter.py -v`
- [x] `python3 -m unittest apps/agent-runtime/tests/test_liquidity_cli.py -v`
- [x] `npm run test:management:liquidity:decision`

---

# Slice 95B.0 Tasks Addendum: Skill-First Auth + Wallet Safety (UTC 2026-02-19)

## 1) Skill/runtime bootstrap surface
- [x] Add skill command `wallet-create` -> runtime `wallet create`.
- [x] Add skill command `auth-recover` -> runtime `auth recover`.
- [x] Add skill command `agent-register <name>` -> runtime `profile set-name`.
- [x] Add runtime command `auth recover --chain ... --json` with structured success/failure contract.

## 2) Safety + deterministic auth context
- [x] Allow skill API commands when auth key exists in runtime state (`~/.xclaw-agent/state.json`) even if env API key is unset.
- [x] Keep no-secret-output behavior for skill command responses.
- [x] Create wallet/runtime state backups under `~/.xclaw-secrets/wallet-backups/...`.
- [ ] Complete live signing bootstrap with valid wallet passphrase in active shell (`wallet-sign-challenge` currently fails with deterministic `sign_failed`).

## 3) Validation
- [x] `python3 -m unittest apps/agent-runtime/tests/test_auth_recover_cli.py -v`
- [x] `python3 -m unittest apps/agent-runtime/tests/test_x402_skill_wrapper.py -v`

# Slice 95B-EVM/HTS Tasks Update (UTC 2026-02-19)

## Completed
- [x] Add deterministic token transfer probe diagnostics for Hedera v2 add preflight.
- [x] Add legacy->canonical WHBAR alias resolution on Hedera testnet.
- [x] Add HTS readiness summary to `wallet health` output.
- [x] Add guarded Hedera simulation bypass env gate (`XCLAW_LIQUIDITY_ALLOW_SIMULATION_BYPASS=1`).
- [x] Add v2 remove pair fallback + Hedera `lpToken()` handling.
- [x] Capture Hedera EVM add tx hash evidence.
- [x] Capture Hedera EVM remove tx hash evidence.

## Remaining
- [!] Configure `XCLAW_HEDERA_HTS_BRIDGE_CMD` to a real bridge executable and capture HTS add/remove tx hashes.
- [~] Final Slice 95 closure status/docs after HTS tx-hash evidence or accepted explicit blocker disposition.

# Slice 95 Final Tasks Update: HTS Bridge Closure (UTC 2026-02-19)

- [x] Add in-repo HTS bridge executable and default command resolution.
- [x] Persist bridge command in installer skill env setup.
- [x] Extend HTS readiness diagnostics with bridge source/config details.
- [x] Capture HTS add tx hash (`E29`).
- [x] Capture HTS remove tx hash (`E30`).
- [x] Move Slice 95 to complete across tracker/roadmap/checklist.

# Slice 95D Tasks Update: Installer Hedera Auto-Bind + Multi-Chain Register (UTC 2026-02-19)

## 1) Installer wallet/bootstrap
- [x] Auto-attempt `wallet create --chain hedera_testnet --json` after default-chain wallet setup.
- [x] Resolve Hedera wallet address and enforce portable-key invariant against default-chain address.
- [x] Abort registration on invariant mismatch with deterministic `portable_wallet_invariant_failed` installer error.
- [x] Keep Hedera bind failure non-fatal when bind command itself fails (`hedera_wallet_bind_failed` warning).

## 2) Register/auth sync
- [x] Build deduped `wallets[]` payload including default chain + Hedera chain rows.
- [x] Run register upsert after bootstrap success to guarantee secondary chain wallet row exists.
- [x] Keep heartbeat behavior unchanged.

## 3) Optional warmup
- [x] Add `XCLAW_INSTALL_AUTO_HEDERA_FAUCET` flag (default `1`).
- [x] Run `faucet-request` warmup for Hedera assets when auth context exists.
- [x] Keep warmup failures non-fatal with deterministic warning + action hint.
# Slice 95E/95F/95G Tasks Update: Hedera Faucet Warmup Reliability (UTC 2026-02-19)

Active slice context: `Slice 95` closure hardening.

## 1) Faucet route deterministic contract
- [x] Add Hedera-aware faucet fee floor + explicit underfloor rejection (`faucet_fee_too_low_for_chain`).
- [x] Add deterministic preflight/config error codes for faucet route (`faucet_config_invalid`, `faucet_*_insufficient`, `faucet_send_preflight_failed`, `faucet_rpc_unavailable`).
- [x] Validate wrapped/stable token addresses and drip values before send path.
- [x] Preserve demo-agent faucet block policy unchanged.

## 2) Installer warmup observability
- [x] Emit warmup diagnostics (`code`, `message`, `actionHint`, `requestId`) on non-fatal failure.
- [x] Emit exact rerun command + environment hint in installer output.
- [x] Fix installer unbound variable edge case (`XCLAW_AGENT_NAME`) in register path.

## 3) Route-level regression coverage
- [x] Add faucet contract script: `infrastructure/scripts/faucet-contract-tests.mjs`.
- [x] Add npm command: `npm run test:faucet:contract`.
- [x] Validate demo-agent block + non-demo deterministic Hedera failure semantics.

# Slice 95H Tasks Update: Official WHBAR Helper + Faucet Auto-Wrap (UTC 2026-02-19)

Active slice context: `Slice 95` closure hardening.

## 1) Runtime wrapping contract
- [x] Add Hedera `coreContracts.wrappedNativeHelper` to chain configs (`hedera_testnet`, `hedera_mainnet`).
- [x] Add runtime command `wallet wrap-native --chain <hedera> --amount <amount> --json`.
- [x] Return deterministic errors (`wrapped_native_helper_missing`, `wrap_native_failed`, `invalid_amount`) and structured wrap metadata.

## 2) Faucet reliability hardening
- [x] Add Hedera wrapped auto-wrap fallback in faucet request route using helper `deposit()`.
- [x] Add deterministic `faucet_wrapped_autowrap_failed` contract for helper/missing/preflight/send failures.
- [x] Update installer warmup diagnostics with wrap-native remediation hint for wrapped shortfall.

## 3) Evidence
- [x] Capture runtime helper wrap tx hash (`E38`).
- [x] Capture post-wrap WHBAR balance increase (`E39`).
- [x] Capture deterministic faucet residual blocker for stable shortfall (`E40`).

# Slice 95I Tasks Update: Hedera Faucet Drip Rebalance (UTC 2026-02-19)

## 1) Drip defaults
- [x] Set Hedera native drip to `5000000000000000000` (5 HBAR).
- [x] Set Hedera wrapped drip to `500000000` (5 WHBAR).
- [x] Set Hedera stable drip to `10000000` (10 USDC).

## 2) Config/runtime sync
- [x] Update route constants and `.env.local` chain-scoped overrides.
- [x] Update source-of-truth default drip documentation.

# Slice 95J Tasks Update: Faucet Rate-Limit Reset + Chain-Scoped Clarity (UTC 2026-02-19)

## 1) Rate-limit reset operation
- [x] Add ops script to clear faucet daily limiter keys across all agents/chains.
- [x] Add npm command alias `ops:faucet:reset-rate-limit`.
- [x] Execute reset against live Redis.

## 2) Response contract clarity
- [x] Update faucet rate-limited response details to include chain-scoped scope key and `chainKey`.
- [x] Sync source-of-truth limiter contract note.

# Slice 95K Tasks Update: Hedera Wallet Full Token Visibility (UTC 2026-02-19)

## 1) Runtime token discovery
- [x] Add Hedera mirror-node token discovery in runtime wallet holdings path.
- [x] Merge discovered non-zero tokens into `wallet balance` output beyond canonical token map.
- [x] Preserve non-fatal failures via `tokenErrors[]`.

## 2) Validation + docs
- [x] Add wallet unit test for Hedera discovered token merge.
- [x] Update wallet contract + source-of-truth wording for Hedera discovered token behavior.

# Slice 95L Tasks Update: Hedera Faucet Self-Recipient Guard + Mapping Hygiene (UTC 2026-02-19)

## 1) Faucet route hardening
- [x] Hard-block recipient == faucet signer with deterministic `faucet_recipient_not_eligible`.
- [x] Include recipient provenance in success payload (`recipientAddress`, `faucetAddress`).
- [x] Add `faucet_recipient_not_eligible` to API error contract union.

## 2) Ops hygiene tooling
- [x] Add `ops:faucet:audit-mappings` script to detect agent wallet rows mapped to faucet signer addresses.
- [x] Add `ops:faucet:fix-mapping` script (dry-run by default, explicit `--apply` for targeted update).
- [x] Add npm script entries for audit/fix tools.

## 3) Regression coverage
- [x] Extend faucet contract test harness with self-recipient deterministic-block scenario.

## 4) Validation + evidence
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] `npm run build`
- [x] `pm2 restart all`
- [x] `npm run test:faucet:contract`
- [x] `npm run ops:faucet:audit-mappings`
- [x] `npm run ops:faucet:fix-mapping -- --agent-id ag_3cfbc4cd0949d3f4c933 --chain hedera_testnet --address 0x582f6f293e0f49855bb752ae29d6b0565c500d87` (dry-run)

# Slice 95M Tasks Update: Wallet Holdings Fidelity (UTC 2026-02-20)

## 1) Runtime holdings
- [x] Filter canonical token rows with zero balance from runtime `wallet balance` output.
- [x] Keep Hedera mirror discovery merge for non-canonical owned tokens.

## 2) Web holdings
- [x] Extend management deposit sync to ingest Hedera mirror discovered non-zero token balances into snapshots.
- [x] Filter zero-balance token rows in agent-page holdings builder.

## 3) Validation + evidence
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] `npm run build`
- [x] `pm2 restart all`
- [!] `python3 -m unittest apps/agent-runtime/tests/test_wallet_core.py -v` (3 existing env-sensitive failures unrelated to holdings changes in this shell context).
- [!] `curl -sS http://127.0.0.1:3000/api/v1/management/deposit?agentId=<agent>&chainKey=hedera_testnet` authenticated live verification pending valid management session cookie in this shell.

# Slice 95N Tasks Update: User-Added Token Tracking (UTC 2026-02-20)

## 1) Runtime + skill contract
- [x] Add runtime commands: `wallet track-token`, `wallet untrack-token`, `wallet tracked-tokens`.
- [x] Persist tracked token addresses/metadata in runtime state (`state.json`) per chain.
- [x] Extend `wallet-send-token` resolution to support unique tracked symbols with deterministic ambiguity failure.
- [x] Extend `wallet-balance` holdings merge to include non-zero tracked tokens.
- [x] Add skill wrapper commands: `wallet-track-token`, `wallet-untrack-token`, `wallet-tracked-tokens`.

## 2) Server mirror + web visibility
- [x] Add migration `0024_slice95n_agent_tracked_tokens.sql`.
- [x] Add agent-auth routes:
  - [x] `POST /api/v1/agent/tokens/mirror`
  - [x] `GET /api/v1/agent/tokens`
- [x] Add tracked-token schemas for mirror request and response.
- [x] Extend management deposit sync to include tracked token addresses in wallet snapshot updates.
- [x] Extend management agent-state payload with `trackedTokens[]` metadata.

## 3) Contract/docs/tests
- [x] Update OpenAPI for new token mirror/read routes.
- [x] Update wallet/skill/source-of-truth contracts for tracked-token command surface and behavior.
- [x] Add runtime unit tests for tracked-token resolution/state and skill-wrapper command delegation.
- [x] Add route-level contract script: `npm run test:tokens:mirror:contract`.

## 4) Validation gates
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] `npm run build`
- [x] `pm2 restart all`
- [!] `python3 -m unittest apps/agent-runtime/tests/test_wallet_core.py -v` (2 existing env-sensitive CLI tests fail in this shell context: `test_wallet_send_success_updates_spend_ledger`, `test_wallet_sign_challenge_cast_missing_rejected`; new Slice 95N tests pass).
- [x] `python3 -m unittest apps/agent-runtime/tests/test_x402_skill_wrapper.py -v`
- [x] `npm run test:tokens:mirror:contract`

# Slice 96 Tasks: Base Sepolia Wallet/Approval E2E Harness (UTC 2026-02-20)

Active slice context: `Slice 96`.

## 1) Canonical sync
- [x] Add Slice 96 entry to `docs/XCLAW_SLICE_TRACKER.md`.
- [x] Add Slice 96 roadmap section to `docs/XCLAW_BUILD_ROADMAP.md`.
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` with harness + Telegram suppression contract.
- [x] Update `docs/CONTEXT_PACK.md` and handoff artifacts.

## 2) Runtime guard
- [x] Add `XCLAW_TEST_HARNESS_DISABLE_TELEGRAM` runtime helper.
- [x] Gate Telegram prompt/decision send functions.
- [x] Gate prompt cleanup function with deterministic non-fatal suppression code.

## 3) Harness implementation
- [x] Add script: `apps/agent-runtime/scripts/wallet_approval_harness.py`.
- [x] Implement management bootstrap + csrf handling.
- [x] Implement management permission updates + restore.
- [x] Implement scenario execution orchestration and report output.
- [x] Implement tolerance-based balance checks.
- [x] Implement hardhat RPC preflight gate (`--hardhat-rpc-url`).
- [x] Implement strict base-sepolia block on missing/non-green hardhat evidence (`--hardhat-evidence-report`).
- [x] Implement wallet decrypt/sign preflight fail-fast (`wallet_passphrase_mismatch`).
- [x] Implement management write retries with exponential backoff + jitter (`--max-api-retries`, `--api-retry-base-ms`).
- [x] Emit retry diagnostics + preflight objects in JSON report.

## 4) Tests
- [x] Extend `apps/agent-runtime/tests/test_trade_path.py` with Telegram suppression tests.
- [x] Add `apps/agent-runtime/tests/test_wallet_approval_harness.py`.

## 5) Validation/evidence
- [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`
- [x] `python3 -m unittest apps/agent-runtime/tests/test_wallet_approval_harness.py -v`
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] `npm run build`
- [x] `pm2 restart all`
- [ ] hardhat-local harness subset evidence
- [ ] base-sepolia harness full evidence
- [ ] issue #42 evidence post + commit hash(es)

## Slice 96 Task Execution Update (UTC 2026-02-20)
- [x] `python3 -m unittest apps/agent-runtime/tests/test_wallet_approval_harness.py -v`
- [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] `npm run build`
- [x] `pm2 restart all`
- [x] Harness now fails fast deterministically when hardhat rpc is unavailable (`hardhat_rpc_unavailable`).
- [x] Harness now blocks base-sepolia run when hardhat evidence report missing/non-green.
- [x] Harness now retries transient management `500` responses with bounded backoff+jitter and structured diagnostics.

# Slice 97 Tasks: Ethereum + Ethereum Sepolia Wallet-First Onboarding (UTC 2026-02-20)

Active slice context: `Slice 97`.

## 1) Canonical sync
- [x] Add Slice 97 tracker entry in `docs/XCLAW_SLICE_TRACKER.md`.
- [x] Add Slice 97 roadmap section in `docs/XCLAW_BUILD_ROADMAP.md`.
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` with wallet-first chain onboarding contract.
- [x] Update `docs/api/WALLET_COMMAND_CONTRACT.md` and relevant OpenAPI chain-key examples.
- [x] Update handoff artifacts (`spec.md`, `tasks.md`, `acceptance.md`).

## 2) Implementation
- [x] Add `config/chains/ethereum.json` (enabled+visible, wallet-first capabilities, verified RPC/explorer metadata).
- [x] Add `config/chains/ethereum_sepolia.json` (enabled+visible, wallet-first capabilities, verified RPC/explorer metadata).
- [x] Update fallback chain registry in `apps/network-web/src/lib/active-chain.ts`.
- [x] Update status provider probe allowlist in `apps/network-web/src/lib/ops-health.ts`.
- [x] Update deterministic dashboard chain color map in `apps/network-web/src/app/dashboard/page.tsx`.

## 3) Validation/evidence
- [x] `apps/agent-runtime/bin/xclaw-agent chains --json` includes both new chains and wallet-first capabilities.
- [x] Isolated-home wallet create/address/health checks pass for both chains.
- [x] `/api/v1/public/chains` returns both new chains with expected metadata.
- [x] `/api/status` provider list includes both new chains.
- [x] Required repo gates run sequentially.
- [x] Issue #43 evidence posted with commit hash(es).

# Slice 98 Tasks: Chain Metadata Normalization + Truthful Capability Gating (UTC 2026-02-20)

Active slice context: `Slice 98`.

## 1) Canonical sync
- [x] Add Slice 98 tracker entry in `docs/XCLAW_SLICE_TRACKER.md`.
- [x] Add Slice 98 roadmap section in `docs/XCLAW_BUILD_ROADMAP.md`.
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` with naming/capability/metadata normalization contract.
- [x] Update `docs/api/WALLET_COMMAND_CONTRACT.md` with config-driven chain support wording.
- [x] Update handoff artifacts (`spec.md`, `tasks.md`, `acceptance.md`).

## 2) Implementation
- [x] Fill ADI mainnet/testnet chainId/rpc/explorer from source-backed metadata and live RPC verification.
- [x] Fill 0G mainnet/testnet chainId/rpc/explorer from source-backed metadata and live RPC verification.
- [x] Correct Kite mainnet chain id and normalize Kite naming (`KiteAI Mainnet`, `KiteAI Testnet`).
- [x] Normalize testnet names to canonical branding (`ADI Network AB Testnet`, `0G Galileo Testnet`).
- [x] Set wallet-first capabilities for non-integrated chains (disable trade/liquidity/limit/x402/faucet/deposits).
- [x] Disable/hide unresolved Canton placeholders pending authoritative metadata.
- [x] Update status provider probing to dynamic enabled+visible+has-rpc selection.

## 3) Validation/evidence
- [x] `apps/agent-runtime/bin/xclaw-agent chains --json` reflects normalized metadata/capabilities.
- [x] `/api/v1/public/chains` reflects normalized names and chain visibility.
- [x] `/api/status` provider list reflects enabled+visible chains with RPCs.
- [x] Required repo gates run sequentially.
- [x] Issue #44 evidence posted with commit hash(es).

# Slice 99 Tasks: Installer Multi-Chain Wallet Auto-Bind Hardening (UTC 2026-02-20)

## 1) Installer wallet auto-bind
- [x] Update `/skill-install.sh` to discover wallet-capable chains via `xclaw-agent chains --json`.
- [x] Auto-attempt wallet bind for each discovered chain using `wallet create --chain <chain> --json`.
- [x] Keep per-chain bind failures warning-level/non-fatal.

## 2) Register payload sync
- [x] Build deduplicated `wallets[]` rows from resolved wallet addresses across bound chains.
- [x] Use multi-chain `wallets[]` payload for installer register upsert.

## 3) Cross-platform parity + docs
- [x] Mirror wallet auto-bind + register payload behavior in `/skill-install.ps1`.
- [x] Sync canonical docs (`source-of-truth`, tracker, roadmap, wallet contract, spec/tasks/acceptance).

# Slice 100 Tasks: Uniswap Proxy-First Trade Execution + Fallback (UTC 2026-02-20)

## 1) Canonical/doc sync
- [x] Add Slice 100 tracker entry.
- [x] Add Slice 100 roadmap section.
- [x] Update source-of-truth for proxy-first execution + fallback semantics.
- [x] Update OpenAPI for new Uniswap proxy routes and trade status provenance fields.
- [x] Update handoff artifacts (`docs/CONTEXT_PACK.md`, `spec.md`, `tasks.md`, `acceptance.md`).

## 2) Server/runtime implementation
- [x] Add `XCLAW_UNISWAP_API_KEY` support to web env parser.
- [x] Add Uniswap proxy helper with chain support gating and deterministic error mapping.
- [x] Add `POST /api/v1/agent/trade/uniswap/quote`.
- [x] Add `POST /api/v1/agent/trade/uniswap/build`.
- [x] Add runtime provider selector and fallback behavior to `cmd_trade_spot`.
- [x] Add runtime provider selector and fallback behavior to `cmd_trade_execute`.
- [x] Surface provider provenance in runtime OK/fail payloads and trade status transitions.
- [x] Extend trade status schema/route for provenance fields.
- [x] Add/update chain configs for requested rollout (`ethereum`, `ethereum_sepolia`, `unichain_mainnet`, `bnb_mainnet`, `polygon_mainnet`, `base_mainnet`, `avalanche_mainnet`, `op_mainnet`, `arbitrum_mainnet`, `zksync_mainnet`, `monad_mainnet`).

## 3) Validation/evidence
- [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`.
- [x] `npm run db:parity`.
- [x] `npm run seed:reset`.
- [x] `npm run seed:load`.
- [x] `npm run seed:verify`.
- [x] `npm run build`.
- [x] `pm2 restart all`.
- [ ] issue evidence post with commit hash(es).

# Slice 101 Tasks: Dashboard Dexscreener Top Tokens (UTC 2026-02-20)

## 1) Canonical/doc sync
- [x] Add Slice 101 tracker entry in `docs/XCLAW_SLICE_TRACKER.md`.
- [x] Add Slice 101 roadmap section in `docs/XCLAW_BUILD_ROADMAP.md`.
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` dashboard contract for top-token module + chain filtering + hide-on-empty behavior.
- [x] Update OpenAPI with `GET /api/v1/public/dashboard/trending-tokens`.
- [x] Add shared response schema for dashboard trending tokens.
- [x] Update handoff artifacts (`docs/CONTEXT_PACK.md`, `spec.md`, `tasks.md`, `acceptance.md`).

## 2) Backend implementation
- [x] Extend chain config type with `marketData.dexscreenerChainId`.
- [x] Add mapping to `base_mainnet`, `base_sepolia`, `ethereum`, `ethereum_sepolia`.
- [x] Add route `apps/network-web/src/app/api/v1/public/dashboard/trending-tokens/route.ts`.
- [x] Validate `chainKey` against enabled+visible chains.
- [x] Resolve mapped Dexscreener chain IDs for selected chain or `all`.
- [x] Fetch Dexscreener data server-side with timeout + soft-failure handling.
- [x] Rank rows by 24h volume descending, dedupe by token+chain, cap to top 10.
- [x] Add 60-second in-memory cache for upstream fetches.

## 3) Dashboard UI integration
- [x] Add trending-token fetch bound to dashboard chain selection.
- [x] Add 60-second refresh loop for token module.
- [x] Render desktop table and mobile cards under existing dashboard insights.
- [x] Render only columns that have data in current dataset.
- [x] Hide section when current chain has no rows.

## 4) Validation/evidence
- [x] `npm run db:parity`.
- [x] `npm run seed:reset`.
- [x] `npm run seed:load`.
- [x] `npm run seed:verify`.
- [x] `npm run build`.
- [x] `pm2 restart all`.
- [x] Issue evidence post with commit hash(es).

# Slice 102 Tasks: Uniswap LP Core Integration (UTC 2026-02-20)

## 1) Canonical/doc sync
- [x] Add Slice 102 tracker entry in `docs/XCLAW_SLICE_TRACKER.md`.
- [x] Add Slice 102 roadmap section in `docs/XCLAW_BUILD_ROADMAP.md`.
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` with LP proxy-first + fallback behavior.
- [x] Update OpenAPI with LP proxy routes and liquidity provenance fields.
- [x] Update handoff artifacts (`docs/CONTEXT_PACK.md`, `spec.md`, `tasks.md`, `acceptance.md`).

## 2) Backend/runtime implementation
- [x] Add Uniswap LP proxy helper `apps/network-web/src/lib/uniswap-lp-proxy.ts`.
- [x] Add LP proxy routes:
  - [x] `/api/v1/agent/liquidity/uniswap/approve`
  - [x] `/api/v1/agent/liquidity/uniswap/create`
  - [x] `/api/v1/agent/liquidity/uniswap/increase`
  - [x] `/api/v1/agent/liquidity/uniswap/decrease`
  - [x] `/api/v1/agent/liquidity/uniswap/claim-fees`
- [x] Add runtime LP provider selector and fallback orchestration in `cmd_liquidity_add/remove/execute`.
- [x] Add runtime commands:
  - [x] `liquidity increase`
  - [x] `liquidity claim-fees`
- [x] Persist LP provider provenance in liquidity status details.
- [x] Extend liquidity status schema contract with LP provenance fields.

## 3) Chain rollout
- [x] Enable LP provider config (`liquidityProviders`, `uniswapApi.liquidityEnabled`) and liquidity capability on:
  - [x] `ethereum`
  - [x] `ethereum_sepolia`
  - [x] `unichain_mainnet`
  - [x] `bnb_mainnet`
  - [x] `polygon_mainnet`
  - [x] `base_mainnet`
  - [x] `avalanche_mainnet`
  - [x] `op_mainnet`
  - [x] `arbitrum_mainnet`
  - [x] `zksync_mainnet`
  - [x] `monad_mainnet`

## 4) Validation/evidence
- [x] `python3 -m unittest apps/agent-runtime/tests/test_liquidity_cli.py -v`.
- [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`.
- [x] `npm run db:parity`.
- [x] `npm run seed:reset`.
- [x] `npm run seed:load`.
- [x] `npm run seed:verify`.
- [x] `npm run build`.
- [x] `pm2 restart all`.
- [x] Issue evidence post with commit hash(es).

# Slice 103 Tasks: Uniswap LP Completion (UTC 2026-02-20)

## 1) Canonical/doc sync
- [x] Add Slice 103 tracker entry in `docs/XCLAW_SLICE_TRACKER.md`.
- [x] Add Slice 103 roadmap section in `docs/XCLAW_BUILD_ROADMAP.md`.
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` with migrate/claim-rewards behavior.
- [x] Update OpenAPI with:
  - [x] `POST /api/v1/agent/liquidity/uniswap/migrate`
  - [x] `POST /api/v1/agent/liquidity/uniswap/claim-rewards`
- [x] Update handoff artifacts (`docs/CONTEXT_PACK.md`, `spec.md`, `tasks.md`, `acceptance.md`).

## 2) Implementation
- [x] Extend LP proxy helper with `migrate` and `claim-rewards` upstream methods.
- [x] Add LP proxy routes:
  - [x] `/api/v1/agent/liquidity/uniswap/migrate`
  - [x] `/api/v1/agent/liquidity/uniswap/claim-rewards`
- [x] Add schemas:
  - [x] `uniswap-lp-migrate-request.schema.json`
  - [x] `uniswap-lp-claim-rewards-request.schema.json`
- [x] Add runtime commands:
  - [x] `liquidity migrate`
  - [x] `liquidity claim-rewards`
- [x] Extend liquidity status schema operation enum for `migrate`, `claim_rewards`.

## 3) Stage-gated rollout flags
- [x] `ethereum_sepolia`: `migrateEnabled=true`, `claimRewardsEnabled=true`.
- [x] Mainnet targets: `migrateEnabled=false`, `claimRewardsEnabled=false` until promotion.

## 4) Validation/evidence
- [x] `python3 -m unittest apps/agent-runtime/tests/test_liquidity_cli.py -v`.
- [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`.
- [x] `npm run db:parity`.
- [x] `npm run seed:reset`.
- [x] `npm run seed:load`.
- [x] `npm run seed:verify`.
- [x] `npm run build`.
- [x] `pm2 restart all`.
- [x] Issue evidence post with commit hash(es).

# Slice 104 Tasks: LP Migrate/Claim-Rewards Promotion (UTC 2026-02-20)

## 1) Canonical/doc sync
- [x] Add Slice 104 tracker entry in `docs/XCLAW_SLICE_TRACKER.md`.
- [x] Add Slice 104 roadmap section in `docs/XCLAW_BUILD_ROADMAP.md`.
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` with promoted chain-state truth.
- [x] Update handoff artifacts (`docs/CONTEXT_PACK.md`, `spec.md`, `tasks.md`, `acceptance.md`).

## 2) Chain promotion flags
- [x] Set `uniswapApi.migrateEnabled=true` and `uniswapApi.claimRewardsEnabled=true` for:
  - [x] `ethereum`
  - [x] `base_mainnet`
  - [x] `arbitrum_mainnet`
  - [x] `op_mainnet`
  - [x] `polygon_mainnet`
  - [x] `avalanche_mainnet`
  - [x] `bnb_mainnet`
  - [x] `zksync_mainnet`
  - [x] `unichain_mainnet`
  - [x] `monad_mainnet`
- [x] Keep `ethereum_sepolia` enabled.

## 3) Validation/evidence
- [x] `python3 -m unittest apps/agent-runtime/tests/test_liquidity_cli.py -v`.
- [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`.
- [x] `npm run db:parity`.
- [x] `npm run seed:reset`.
- [x] `npm run seed:load`.
- [x] `npm run seed:verify`.
- [x] `npm run build`.
- [x] `pm2 restart all`.
- [x] Issue evidence post with commit hash(es).

# Slice 105 Tasks: Cross-Chain Liquidity Claims (UTC 2026-02-20)

## 1) Canonical/doc sync
- [x] Add Slice 105 tracker entry in `docs/XCLAW_SLICE_TRACKER.md`.
- [x] Add Slice 105 roadmap section in `docs/XCLAW_BUILD_ROADMAP.md`.
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` with cross-chain claim contract.
- [x] Update handoff artifacts (`docs/CONTEXT_PACK.md`, `spec.md`, `tasks.md`, `acceptance.md`).

## 2) Runtime and adapter implementation
- [x] Refactor `cmd_liquidity_claim_fees` for provider orchestration + fallback.
- [x] Refactor `cmd_liquidity_claim_rewards` for provider orchestration + fallback.
- [x] Add adapter claim operation methods (`claim_fees`, `claim_rewards`) with fail-closed defaults.
- [x] Add guarded claim action dispatch in Hedera plugin/bridge.
- [x] Add per-chain config gates:
  - [x] `liquidityOperations.claimFees.legacyEnabled`
  - [x] `liquidityOperations.claimRewards.legacyEnabled`

## 3) Validation/evidence
- [x] `python3 -m unittest apps/agent-runtime/tests/test_liquidity_cli.py -v`.
- [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`.
- [x] `npm run db:parity`.
- [x] `npm run seed:reset`.
- [x] `npm run seed:load`.
- [x] `npm run seed:verify`.
- [x] `npm run build`.
- [x] `pm2 restart all`.
- [x] Issue evidence post with commit hash(es).

# Slice 106 Tasks: Full Cross-Chain Functional Parity + Adapter Fallbacks (UTC 2026-02-20)

## 1) Canonical/doc sync
- [x] Add Slice 106 tracker entry in `docs/XCLAW_SLICE_TRACKER.md`.
- [x] Add Slice 106 roadmap section in `docs/XCLAW_BUILD_ROADMAP.md`.
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` with parity/fallback contract.
- [x] Update handoff artifacts (`docs/CONTEXT_PACK.md`, `spec.md`, `tasks.md`, `acceptance.md`).

## 2) Runtime/config implementation
- [x] Add operation-aware provider helper `_resolve_operation_provider(...)`.
- [x] Add shared fallback helper `_execute_with_fallback(...)`.
- [x] Apply fallback helper to claim command paths.
- [x] Extend `liquidity_adapter.py` capability metadata for reward-claim requirements.
- [x] Extend all chain configs with:
  - [x] `tradeOperations.legacyEnabled`
  - [x] `tradeOperations.adapter`
  - [x] `liquidityOperations.claimFees.adapter`
  - [x] `liquidityOperations.claimRewards.adapter`
  - [x] `liquidityOperations.claimRewards.rewardContracts`

## 3) Backlog/promotions
- [x] Add wallet-only/disabled onboarding backlog for:
  - [x] `adi_mainnet`
  - [x] `adi_testnet`
  - [x] `og_mainnet`
  - [x] `og_testnet`
  - [x] `kite_ai_mainnet`
  - [x] `canton_mainnet`
  - [x] `canton_testnet`

## 4) Validation/evidence
- [x] `python3 -m unittest apps/agent-runtime/tests/test_liquidity_cli.py -v`.
- [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`.
- [x] `npm run db:parity`.
- [x] `npm run seed:reset`.
- [x] `npm run seed:load`.
- [x] `npm run seed:verify`.
- [x] `npm run build`.
- [x] `pm2 restart all`.
- [ ] Issue evidence post with commit hash(es).

# Slice 107 Tasks: Executable Cross-Chain Parity Completion (UTC 2026-02-20)

## 1) Canonical/doc sync
- [x] Add Slice 107 tracker entry in `docs/XCLAW_SLICE_TRACKER.md`.
- [x] Add Slice 107 roadmap section in `docs/XCLAW_BUILD_ROADMAP.md`.
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` with executable parity promotion contract.
- [x] Update handoff artifacts (`docs/CONTEXT_PACK.md`, `spec.md`, `tasks.md`, `acceptance.md`).

## 2) Runtime and bridge implementation
- [x] Ensure claim-failure payloads include provider provenance fields.
- [x] Remove hard-block for Hedera bridge `claim_fees` / `claim_rewards` actions.
- [x] Add runtime test coverage for claim failure provenance fields.

## 3) Chain config promotion
- [x] Set `config/chains/hedera_mainnet.json`:
  - [x] `liquidityOperations.claimFees.legacyEnabled=true`
  - [x] `liquidityOperations.claimRewards.legacyEnabled=true`
- [x] Set `config/chains/hedera_testnet.json`:
  - [x] `liquidityOperations.claimFees.legacyEnabled=true`
  - [x] `liquidityOperations.claimRewards.legacyEnabled=true`

## 4) Validation/evidence
- [x] `python3 -m unittest apps/agent-runtime/tests/test_liquidity_cli.py -v`.
- [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`.
- [x] `npm run db:parity`.
- [x] `npm run seed:reset`.
- [x] `npm run seed:load`.
- [x] `npm run seed:verify`.
- [x] `npm run build`.
- [x] `pm2 restart all`.
- [ ] Issue evidence post with commit hash(es).

# Slice 108 Tasks: Config-Truth + Runtime Gate Tightening (UTC 2026-02-20)

## 1) Canonical/doc sync
- [x] Add Slice 108 tracker entry in `docs/XCLAW_SLICE_TRACKER.md`.
- [x] Add Slice 108 roadmap section in `docs/XCLAW_BUILD_ROADMAP.md`.
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` with deterministic gate/provenance contract.
- [x] Update handoff artifacts (`docs/CONTEXT_PACK.md`, `spec.md`, `tasks.md`, `acceptance.md`).

## 2) Runtime/config contract checks
- [x] Ensure fallback attempts require config gate + capability support.
- [x] Ensure claim/trade failure payloads carry provider provenance fields.
- [x] Keep unsupported operation paths explicit and deterministic.

## 3) Validation/evidence
- [x] `python3 -m unittest apps/agent-runtime/tests/test_liquidity_cli.py -v`.
- [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`.
- [x] `npm run db:parity`.
- [x] `npm run seed:reset`.
- [x] `npm run seed:load`.
- [x] `npm run seed:verify`.
- [x] `npm run build`.
- [x] `pm2 restart all`.
- [ ] Issue evidence post with commit hash(es).

# Slice 109 Tasks: Uniswap-Chain Fallback Promotion (UTC 2026-02-20)

## 1) Promotion truth
- [x] Keep fallback enabled on validated chains:
  - [x] `ethereum`
  - [x] `ethereum_sepolia`
- [x] Keep fallback disabled where legacy metadata is not onboarded:
  - [x] `base_mainnet`
  - [x] `arbitrum_mainnet`
  - [x] `op_mainnet`
  - [x] `polygon_mainnet`
  - [x] `avalanche_mainnet`
  - [x] `bnb_mainnet`
  - [x] `zksync_mainnet`
  - [x] `unichain_mainnet`
  - [x] `monad_mainnet`

## 2) Validation/evidence
- [x] Runtime regression tests run.
- [x] Required gates run sequentially.
- [ ] Issue evidence post with commit hash(es).

# Slice 110 Tasks: Non-Uniswap Active Claims Completion (UTC 2026-02-20)

## 1) Claim completion truth
- [x] Keep Hedera claim execution enabled:
  - [x] `hedera_mainnet`
  - [x] `hedera_testnet`
- [x] Keep non-integrated chains deterministic fail-closed:
  - [x] `base_sepolia`
  - [x] `hardhat_local`
  - [x] `kite_ai_testnet`

## 2) Validation/evidence
- [x] Runtime regression tests run.
- [x] Required gates run sequentially.
- [ ] Issue evidence post with commit hash(es).

# Slice 111 Tasks: Active-Chain Parity Evidence Matrix (UTC 2026-02-20)

## 1) Canonical evidence
- [x] Add active-chain parity matrix to `acceptance.md`.
- [x] Sync source-of-truth, tracker, roadmap, spec, and context pack with 108-111 outcomes.

## 2) Validation/evidence
- [x] Required gates run sequentially.
- [ ] Issue evidence post with commit hash(es).

# Slice 107 Hotfix A Tasks: Base ERC-8021 Builder Code Attribution (UTC 2026-02-20)

## 1) Canonical/doc sync
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` with locked ERC-8021 Base attribution contract.
- [x] Add hotfix entry to `docs/XCLAW_SLICE_TRACKER.md` and `docs/XCLAW_BUILD_ROADMAP.md`.
- [x] Update handoff artifacts (`spec.md`, `tasks.md`, `acceptance.md`).

## 2) Runtime implementation
- [x] Add Base-gated ERC-8021 helpers in `apps/agent-runtime/xclaw_agent/cli.py`.
- [x] Update `_cast_rpc_send_transaction(...)` to apply suffix logic and fail-closed behavior when required.
- [x] Pass `chain` to all runtime send callsites in `cli.py`.
- [x] Add additive builder metadata fields in wallet/trade/liquidity tx outputs.

## 3) Tests
- [x] Add sender-path ERC-8021 unit coverage in `apps/agent-runtime/tests/test_trade_path.py`.
- [x] Add command-output metadata presence checks in `apps/agent-runtime/tests/test_trade_path.py`.
- [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`.
- [x] `python3 -m unittest apps/agent-runtime/tests/test_wallet_core.py -v`.

## 4) Required validation sequence
- [x] `npm run db:parity`.
- [x] `npm run seed:reset`.
- [x] `npm run seed:load`.
- [x] `npm run seed:verify`.
- [x] `npm run build`.
- [x] `pm2 restart all`.
- [ ] Issue evidence post with commit hash(es).

# Slice 112 Tasks: v2-Only Fallback Research Contract (UTC 2026-02-20)

## 1) Canonical/doc sync
- [x] Add Slice 112 entries to `docs/XCLAW_SOURCE_OF_TRUTH.md`, `docs/XCLAW_SLICE_TRACKER.md`, and `docs/XCLAW_BUILD_ROADMAP.md`.
- [x] Update handoff artifacts (`docs/CONTEXT_PACK.md`, `spec.md`, `tasks.md`, `acceptance.md`).
- [x] Add research-evidence template in `acceptance.md`.

# Slice 113 Tasks: Verified v2 Fallback Promotion (UTC 2026-02-20)

## 1) Chain config promotions
- [x] Promote fallback-enabled v2 chains:
  - [x] `arbitrum_mainnet`
  - [x] `base_mainnet`
  - [x] `op_mainnet`
  - [x] `polygon_mainnet`
  - [x] `avalanche_mainnet`
  - [x] `bnb_mainnet`
  - [x] `unichain_mainnet`
  - [x] `monad_mainnet`
- [x] Keep `ethereum` and `ethereum_sepolia` fallback-enabled.
- [x] Keep `zksync_mainnet` fallback-disabled with deterministic reason.

## 2) Tests
- [x] Update trade-path tests for fallback-enabled and fallback-disabled primary-failure behavior.

# Slice 114 Tasks: Non-Uniswap Active Claims Truth Finalization (UTC 2026-02-20)

## 1) Truth lock
- [x] Preserve Hedera executable claims (`hedera_mainnet`, `hedera_testnet`).
- [x] Preserve deterministic fail-closed claims (`base_sepolia`, `hardhat_local`, `kite_ai_testnet`).
- [x] Record per-chain reason mapping in acceptance matrix.

# Slice 115 Tasks: Runtime Determinism/Provenance Sweep (UTC 2026-02-20)

## 1) Guardrail verification
- [x] Ensure trade/claim failure payloads include provider provenance fields.
- [x] Keep behavior constrained to v2-only fallback contract.
- [x] Run runtime regressions (`test_trade_path.py`, `test_liquidity_cli.py`).

# Slice 116 Tasks: Final Matrix + Closeout (UTC 2026-02-20)

## 1) Evidence closeout
- [x] Publish final active-chain parity matrix with provider/fallback/fail-code columns.
- [x] Run required gates sequentially (`db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, `pm2 restart all`).

# Slice 117 Tasks: Ethereum Sepolia Harness Matrix Expansion (UTC 2026-02-20)

## 1) Harness updates
- [x] Add Ethereum Sepolia funding bootstrap (`ETH -> WETH -> USDC`) in `apps/agent-runtime/scripts/wallet_approval_harness.py`.
- [x] Add optional wallet identity assertion (`--expected-wallet-address`).
- [x] Split transfer and x402 scenarios.
- [x] Add deterministic x402 unsupported assertion path on `ethereum_sepolia`.

## 2) Matrix runner
- [x] Add `apps/agent-runtime/scripts/wallet_approval_chain_matrix.py`.
- [x] Enforce run order: hardhat smoke -> base full -> ethereum sepolia full.
- [x] Stop on first failure and emit consolidated JSON report.

## 3) Tests
- [x] Update `apps/agent-runtime/tests/test_wallet_approval_harness.py` for bootstrap and x402 capability assertions.
- [x] Add `apps/agent-runtime/tests/test_wallet_approval_chain_matrix.py` for order/failure gating.
- [x] `python3 -m unittest apps/agent-runtime/tests/test_wallet_approval_harness.py -v`
- [x] `python3 -m unittest apps/agent-runtime/tests/test_wallet_approval_chain_matrix.py -v`

## 4) Validation/evidence
- [ ] Run chain matrix against runtime environment and capture reports.
- [ ] Run required gates sequentially (`db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, `pm2 restart all`).
- [ ] Issue #60 evidence post with commit hash(es).
- [x] Add harness passphrase recovery from local encrypted backup and opt-out flag (`--disable-passphrase-recovery`).

---

# Slice 117 Hotfix B Tasks: Agent-Canonical Confirmation Pipeline (Dual-Run Start)

Active slice context: `Slice 117` in progress.

## 1) Scope lock
- [x] Keep scope to terminal confirmation authority/routing boundary and watcher provenance.
- [x] Avoid speculative new feature surfaces.

## 2) Contracts + schema
- [x] Extend `trade-status` schema with watcher provenance fields.
- [x] Extend transfer mirror schema with watcher provenance fields.
- [x] Update OpenAPI component schemas accordingly.

## 3) Persistence + migration
- [x] Add migration for watcher provenance/comparator fields on:
  - [x] `trades`
  - [x] `agent_transfer_approval_mirror`
  - [x] `wallet_balance_snapshots`
  - [x] `deposit_events`

## 4) Runtime emission
- [x] Add runtime watcher run-id persistence helper (`watcher-state.json`).
- [x] Add default watcher metadata to `_post_trade_status(...)`.
- [x] Add watcher metadata to transfer mirror payload writes.
- [x] Mark receipt-confirmed terminal transitions with `observationSource=rpc_receipt` and `confirmationCount=1`.

## 5) Server ingest hardening + notification cutover
- [x] Persist provenance metadata in trade status ingest route.
- [x] Persist provenance metadata in transfer mirror ingest route.
- [x] Disable terminal synthetic fanout in trade status route.
- [x] Disable terminal synthetic fanout in transfer mirror route.
- [x] Disable transfer decision terminal synthetic fanout path.

## 6) Deposit dual-run tagging
- [x] Tag server deposit poll writes as `legacy_server_poller` comparator rows.
- [x] Expose dual-run metadata in management deposit response.

## 7) Canonical docs sync
- [x] Update source-of-truth web bridge + provenance contract sections.
- [x] Update roadmap and tracker with Slice 117 Hotfix B checklist.
- [x] Update handoff artifacts (`spec.md`, `tasks.md`, `acceptance.md`).

## 8) Validation
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] `npm run build`
- [x] `pm2 restart all`

---

# Slice 117 Hotfix C Tasks: Cross-Chain `wallet wrap-native` Parity

Active slice context: `Slice 117` in progress.

## 1) Runtime implementation
- [x] Remove Hedera-only guard from `wallet wrap-native`.
- [x] Add config-driven target resolution:
  - [x] helper path (`coreContracts.wrappedNativeHelper`) when present/valid.
  - [x] canonical wrapped-token path from `canonicalTokens` via native-symbol mapping.
- [x] Keep payable `deposit()` execution semantics and receipt verification.

## 2) Deterministic error/output contract
- [x] Add deterministic `wrapped_native_token_missing`.
- [x] Retain deterministic `wrapped_native_helper_missing`, `invalid_amount`, `wrap_native_failed`.
- [x] Include swap fallback guidance in `wrap_native_failed` action hints.

## 3) Tests
- [x] Update `apps/agent-runtime/tests/test_wallet_core.py`:
  - [x] helper success path.
  - [x] non-Hedera wrapped-token success path.
  - [x] deterministic missing helper failure.
  - [x] deterministic missing wrapped token failure.
  - [x] deterministic receipt failure path.
- [x] `python3 -m unittest apps/agent-runtime/tests/test_wallet_core.py -v`
- [x] `python3 -m unittest apps/agent-runtime/tests/test_x402_skill_wrapper.py -v`

## 4) Canonical sync
- [x] `docs/XCLAW_SOURCE_OF_TRUTH.md`
- [x] `docs/api/WALLET_COMMAND_CONTRACT.md`
- [x] `docs/XCLAW_SLICE_TRACKER.md`
- [x] `docs/XCLAW_BUILD_ROADMAP.md`
- [x] `skills/xclaw-agent/SKILL.md`
- [x] `skills/xclaw-agent/references/commands.md`
- [x] handoff artifacts (`spec.md`, `tasks.md`, `acceptance.md`, `docs/CONTEXT_PACK.md`)

## 5) Required validations + evidence
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] `npm run build`
- [x] `pm2 restart all`
- [ ] Issue #60 evidence post with commit hash(es).

---

# Hotfix Tasks: Slice 117 Hotfix D Trade-Cap Deprecation + Chain Context Parity

Active slice context: `Slice 117` in progress.

## 1) Scope lock
- [x] Keep scope to runtime/server cap gating removal, skill chain inference parity, and canonical sync.
- [x] Preserve config-driven capability gates; do not auto-enable unsupported chains.

## 2) Runtime + server behavior
- [x] Remove runtime trade-cap blocking failure path (missing trade caps no longer fails).
- [x] Keep runtime usage telemetry ledger/report flow for compatibility.
- [x] Convert server trade-cap evaluator to non-blocking compatibility mode.
- [x] Preserve approval-mode/allowed-token behavior for proposal approval routing.

## 3) Skill chain inference + trade command overrides
- [x] Add runtime-default-chain-first resolver in skill wrapper (webapp-synced chain awareness).
- [x] Keep env fallback when runtime/default-chain lookup unavailable.
- [x] Add optional chain override support for `trade-spot`, `trade-exec`, and `trade-resume`.

## 4) Canonical docs sync
- [x] Update source-of-truth with trade-cap deprecation and chain inference precedence.
- [x] Update wallet/skill command contract docs for optional chain overrides and precedence.
- [x] Add Slice 117 Hotfix D entries to tracker and roadmap.

## 5) Validation
- [ ] `python3 -m unittest apps/agent-runtime/tests/test_wallet_core.py -v`
- [ ] `python3 -m unittest apps/agent-runtime/tests/test_x402_skill_wrapper.py -v`
- [ ] `npm run db:parity`
- [ ] `npm run seed:reset`
- [ ] `npm run seed:load`
- [ ] `npm run seed:verify`
- [ ] `npm run build`
- [ ] `pm2 restart all`

---

# Hotfix Tasks: Slice 117 Hotfix E Transfer Approval Mirror Fail-Closed

Active slice context: `Slice 117` in progress.

## 1) Scope lock
- [x] Keep scope to runtime transfer mirror delivery guarantees for approval-required sends.
- [x] Preserve transfer decision and execution semantics.

## 2) Implementation
- [x] Extend `_mirror_transfer_approval` with required-delivery mode and deterministic retry.
- [x] Make `wallet-send` and `wallet-send-token` fail closed with `approval_sync_failed` when required mirror delivery fails.
- [x] Remove pending local transfer flow when required mirror delivery fails to avoid ghost approvals.
- [x] Add shared transfer-mirror schema drift classifier and wire deterministic `transfer_mirror_unavailable` handling into:
  - [x] `POST /api/v1/agent/transfer-approvals/mirror`
  - [x] `GET /api/v1/management/agent-state`
- [x] Add structured logging for mirror route write failures (`requestId`, `approvalId`, `agentId`, db code/message).
- [x] Ensure skill wrapper keeps `approval_sync_failed` non-success (no pending normalization).

## 3) Tests
- [x] Add regression test for approval sync failure path in `test_trade_path.py`.
- [x] Add skill-wrapper regression that `approval_sync_failed` remains non-success/non-normalized.
- [x] Add deterministic `/agents/:id` transfer approval row selector (`data-testid="approval-row-transfer-<approval_id>"`).
- [x] Add browser smoke verifier `infrastructure/scripts/verify-agents-approval-row-ui.mjs` for management-session-gated approval rendering.
- [x] Add npm command entrypoint `verify:ui:agent-approvals`.
- [x] Add optional `e2e-full` hook to run UI verifier and report WARN/FAIL deterministically.
- [x] Convert management transfer approval decision route to non-blocking agent-inbox queue behavior (approve async `202`, deny immediate mirror apply `200`).
- [x] Add agent-auth transfer decision inbox endpoints so runtime polls + acks decisions without web-side runtime execution.
- [x] Update transfer decision UI success copy to “decision submitted” (not immediate execution success wording).

## 4) Validation
- [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`
- [x] `python3 -m unittest apps/agent-runtime/tests/test_x402_skill_wrapper.py -v`
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] `npm run build`
- [x] `pm2 restart all`
- [x] `npm run verify:ui:agent-approvals`

---

# Hotfix Tasks: Slice 117 Hotfix F Transfer Decision Reliability + Prompt Convergence

Active slice context: `Slice 117` in progress.

## 1) Scope lock
- [x] Preserve web/runtime separation: web never executes wallet operations.
- [x] Keep transfer policy semantics unchanged (`outbound_disabled`, whitelist, override model).

## 2) Runtime always-on decision consumer
- [x] Add `approvals run-loop` command with interval + bounded backoff.
- [x] Reuse existing transfer decision sync/apply/ack behavior.
- [x] Add structured loop-cycle counters/logging for observability.
- [x] Keep `approvals sync` backward-compatible as manual fallback.
- [x] Wire best-effort skill setup service for continuous run-loop execution.

## 3) Approve preflight readiness gate
- [x] Extend runtime readiness payload contract (`walletSigningReady`, reason code, checked timestamp).
- [x] Add agent-auth runtime readiness update endpoint.
- [x] Heartbeat route stores readiness snapshot when provided.
- [x] Block `decision=approve` with deterministic `runtime_signing_unavailable` when readiness is not sign-capable.
- [x] Ensure blocked approve does not queue transfer decision inbox row.

## 4) Terminal prompt convergence fallback
- [x] Add server-side terminal transfer prompt cleanup sweeper fallback.
- [x] Sweeper targets terminal transfer rows (`filled|failed|rejected`) and dispatches runtime `approvals clear-prompt`.
- [x] Cleanup fallback is idempotent and safe when prompt metadata is missing.
- [x] Keep UI terminal approvals non-actionable independent of cleanup result.

## 5) Validation
- [x] `python3 -m unittest apps/agent-runtime/tests/test_approvals_run_loop.py -v`
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] `npm run build`
- [x] `pm2 restart all`
- [x] `npm run verify:ui:agent-approvals`

---

# Hotfix Tasks: Slice 117 Hotfix G Installer + Run-Loop Wiring Hardening

Active slice context: `Slice 117` in progress.

## 1) Scope lock
- [x] Keep runtime/web separation unchanged.
- [x] Enforce single-agent host wiring for installer-managed run-loop service.

## 2) Setup script hardening
- [x] Add deterministic config ingestion for OpenClaw skill env + apiKey.
- [x] Add passphrase backup decrypt fallback for run-loop env resolution.
- [x] Enforce strict required-key validation for run-loop env writes.
- [x] Make run-loop env writes atomic and permission-hardened.
- [x] Add strict health probe gate (`approvals run-loop --once --json`) and fail closed on unhealthy readiness.
- [x] Extend setup JSON payload with run-loop health summary (`envValidated`, health fields).

## 3) Installer hardening (shell + PowerShell)
- [x] Derive canonical API base from installer origin (local/prod).
- [x] Run final strict setup pass after bootstrap/register.
- [x] Bind final run-loop wiring to bootstrap-issued credentials.
- [x] Emit deterministic run-loop summary lines (`apiBase`, `agentId`, `walletSigningReady`).
- [x] Refuse install completion when final strict setup fails.

## 4) Regression coverage
- [x] Add setup-script unit tests for config+backup resolution and strict fail-closed behavior.
- [x] Add run-loop cycle sanity metadata (api host + agent id) to runtime logs.

## 5) Validation
- [x] `python3 -m unittest apps/agent-runtime/tests/test_approvals_run_loop.py -v`
- [x] `python3 -m unittest apps/agent-runtime/tests/test_setup_agent_skill.py -v`
- [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] `npm run build`
- [x] `pm2 restart all`
- [x] `npm run verify:ui:agent-approvals`

---

# Hotfix Tasks: Slice 117 Hotfix H Runtime Signing Preflight False-Negative Guard

Active slice context: `Slice 117` in progress.

## 1) Implementation
- [x] Prevent heartbeat null-clobber on runtime readiness map when readiness fields are omitted.
- [x] Add normalized chain-key fallback matching for transfer approve readiness preflight.
- [x] Add defensive latest-positive readiness fallback when chain-specific readiness record is missing.

## 2) Validation
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] `npm run build`
- [x] `pm2 restart all`
- [x] `npm run verify:ui:agent-approvals`

---

# Hotfix Tasks: Slice 117 Hotfix I Degraded Readiness Approve Fallback

Active slice context: `Slice 117` in progress.

## 1) Implementation
- [x] Transfer approve preflight hard-block narrowed to explicit signer-unavailable readiness reason codes.
- [x] Readiness-missing preflight (`runtime_readiness_missing`) no longer hard-blocks approval queueing.
- [x] Added audit trace for degraded preflight queue path (`runtime_signing_preflight_degraded`).
- [x] Canonical docs synchronized (`XCLAW_SOURCE_OF_TRUTH`, OpenAPI, handoff artifacts).

## 2) Validation
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] `npm run build`
- [x] `pm2 restart all`
- [x] `npm run verify:ui:agent-approvals`
- [x] Live prod-path approve regression check via `POST /api/v1/management/transfer-approvals/decision` no longer returns `runtime_signing_unavailable` for readiness-missing snapshots.

---

# Hotfix Tasks: Slice 117 Hotfix J Immediate Telegram Prompt Cleanup + Terminal Transfer Prod

Active slice context: `Slice 117` in progress.

## 1) Implementation
- [x] Transfer decision route now triggers immediate runtime `approvals clear-prompt` for transfer approvals after both approve and deny decisions.
- [x] Transfer decision responses/audit payloads now include immediate prompt cleanup result payload instead of pending-only placeholder.
- [x] Transfer mirror route now dispatches one terminal transfer result prod on first transition to terminal status (`filled|failed|rejected`).
- [x] Terminal transfer prod dispatch bypasses canonical guard for this explicit terminal follow-up path.
- [x] Canonical docs/handoff artifacts synchronized.

## 2) Validation
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] `npm run build`
- [x] `pm2 restart all`
- [x] Live transfer approval + terminal follow-up behavior check on `xclaw.trade`.

---

# Hotfix Tasks: Slice 117 Hotfix K Non-Blocking Swap Confirmation Path

Active slice context: `Slice 117` in progress.

## 1) Implementation
- [x] runtime `cmd_trade_execute` no longer waits in-band on swap receipt confirmation.
- [x] runtime returns immediate success payload in `verifying` state after broadcast.
- [x] source-of-truth and handoff artifacts synchronized.

## 2) Validation
- [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` (includes new non-blocking execute regression).
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] `npm run build`
- [x] `pm2 restart all`
- [ ] live repro: message agent immediately after approved swap no longer blocked by receipt wait.

---

# Hotfix Tasks: Slice 117 Hotfix L Truthful Trade Decision Messaging

Active slice context: `Slice 117` in progress.

## 1) Implementation
- [x] Telegram trade approval acknowledgement copy no longer claims terminal success before execution outcome.
- [x] Runtime trade decision path sends terminal follow-up Telegram message for `filled|failed|rejected|verification_timeout`.
- [x] Added regression tests for copy contract and terminal follow-up emission.

## 2) Validation
- [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] `npm run build`
- [x] `pm2 restart all`

---

# Hotfix Tasks: Slice 117 Hotfix M Approval History Terminal Status Truthfulness

Active slice context: `Slice 117` in progress.

## 1) Implementation
- [x] Preserve trade terminal status in `/agents/:id` approval history (`filled|failed|verification_timeout|expired`).
- [x] Update approvals rejected filter to include terminal failure statuses.
- [x] Update management approvals inbox status normalization so failed terminal trades are not bucketed as approved.
- [x] Sync canonical docs + handoff artifacts.

## 2) Validation
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] `npm run build`
- [x] `pm2 restart all`
- [x] Live evidence: failed trade rows now map to rejected bucket semantics in management approvals inbox.

---

# Hotfix Tasks: Slice 117 Hotfix N Ethereum Sepolia Wallet Balance Sync Type-Stability

Active slice context: `Slice 117` in progress.

## 1) Implementation
- [x] Split `chain_key` bind usage in management deposit dedupe SQL so cross-table inference cannot fail.
- [x] Preserve existing dedupe behavior while removing bind-type ambiguity in `syncChainDeposits`.
- [x] Sync canonical docs + handoff artifacts.

## 2) Validation
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] `npm run build`
- [x] `pm2 restart all`
- [x] Live evidence: `management/deposit` returns `syncStatus=ok` and non-zero `USDC` balance on `ethereum_sepolia` after filled swap.

---

# Hotfix Tasks: Slice 117 Hotfix O Hedera Swap Fee-Retry + Symbol Resolution

Active slice context: `Slice 117` in progress.

## 1) Implementation
- [x] Add minimum-gas-price parsing for send failures and carry enforced gas-price floor across retries.
- [x] Add deterministic `2x` legacy gas-price multiplier for `hedera_testnet` send path.
- [x] Add runtime regression test for minimum gas-price retry behavior.
- [x] Add runtime regression test covering Hedera testnet doubled gas-price submission.
- [x] Add Hedera testnet canonical `USDC` mapping for symbol resolution.
- [x] Sync canonical docs + handoff artifacts.

## 2) Validation
- [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] `npm run build`
- [x] `pm2 restart all`
- [x] Evidence: Hedera trade labels resolve `USDC`; minimum-gas underbid retry path is covered by runtime regression test.
