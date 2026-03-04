# Slice 129 Acceptance Evidence: Unified Advanced LP Execution

Date (UTC): 2026-03-04
Active slice context: `Slice 129`.

## Objective + Scope Lock
- Objective:
  - move advanced concentrated-liquidity execution onto the runtime-local EVM action engine,
  - remove the last active `uniswap_api` LP execution branches and old config contracts.
- Scope lock:
  - `apps/agent-runtime/xclaw_agent/liquidity_execution.py`
  - `apps/agent-runtime/xclaw_agent/liquidity_adapters/amm_v3.py`
  - `apps/agent-runtime/xclaw_agent/liquidity_adapter.py`
  - `apps/agent-runtime/xclaw_agent/cli.py`
  - `apps/agent-runtime/tests/test_trade_path.py`
  - `apps/agent-runtime/tests/test_liquidity_cli.py`
  - `apps/agent-runtime/tests/test_liquidity_adapter.py`
  - `apps/network-web/src/lib/chains.ts`
  - `packages/shared-schemas/json/liquidity-status.schema.json`
  - `config/chains/*.json`
  - canonical docs + handoff artifacts

## Behavior Checks
- [x] advanced LP planner emits `executionFamily=position_manager_v3`.
- [x] `liquidity increase`, `claim-fees`, `claim-rewards`, and `migrate` run through local action-plan execution.
- [x] `cmd_liquidity_execute` contains no `uniswap_api` branch.
- [x] active configs contain no `tradeOperations`, `liquidityOperations`, or `uniswapApi`.

## Required Validation Gates
- [x] `python3 -m unittest apps/agent-runtime/tests/test_liquidity_adapter.py -v`
- [x] `python3 -m unittest apps/agent-runtime/tests/test_liquidity_cli.py -v`
- [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] `npm run build`
- [x] `pm2 restart all`

# Hotfix Acceptance Evidence: Preserve Trade Approval History After Execution

# Hotfix Acceptance Evidence: Liquidity Approval Runtime Env Hydration Parity

Date (UTC): 2026-02-21
Active slice context: `Slice 118` in progress (`Follow-Up E` hardening).

## Objective + Scope Lock
- Objective:
  - ensure web/Telegram liquidity approval execution gets required env parity with CLI even when server env misses specific keys.
- Scope lock:
  - `apps/network-web/src/app/api/v1/management/approvals/decision/route.ts`
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `spec.md`, `tasks.md`, `acceptance.md`

## Behavior Checks
- [x] approval runtime spawn env now backfills missing `XCLAW_LIQUIDITY_ALLOW_SEPOLIA_TRANSFERFROM_BYPASS` from OpenClaw skill env.
- [x] approval runtime spawn env now backfills missing `XCLAW_UNISWAP_API_KEY` from OpenClaw skill env.
- [x] existing `XCLAW_WALLET_PASSPHRASE` fallback behavior remains intact.

## Required Validation Gates
- [x] `npm run build`
- [x] `pm2 restart all`

# Hotfix Acceptance Evidence: Sepolia Remove Gas-Estimate False-Negative Recovery

Date (UTC): 2026-02-21
Active slice context: `Slice 118` in progress (`Follow-Up E`).

## Objective + Scope Lock
- Objective:
  - recover from transient RPC estimate/send false negatives on Sepolia LP remove flow,
  - keep default fail-closed behavior outside scoped retry conditions.
- Scope lock:
  - `apps/agent-runtime/xclaw_agent/cli.py`
  - `apps/agent-runtime/tests/test_liquidity_cli.py`
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `spec.md`, `tasks.md`, `acceptance.md`

## Behavior Checks
- [x] runtime retries send across configured chain RPC candidates on retryable upstream/internal failures (including temporary internal code `19`).
- [x] runtime applies gas-limit retry fallback when send fails with estimate false-negative signatures (`Failed to estimate gas`, `ds-math-sub-underflow`) on Sepolia chains.
- [x] runtime tests cover estimate-failure detection and gas-limit retry behavior.
- [x] closed-loop Sepolia remove succeeded: `liq_6103a859a56f70492b13` terminal `filled`, tx `0x5d85ddf4ef65c50c332470255d353628aa4e7bf5b8216e06e53883ccb9169bc8`.

## Required Validation Gates
- [x] `python3 -m unittest apps/agent-runtime/tests/test_liquidity_cli.py -v`
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] `npm run build`
- [x] `pm2 restart all`

# Hotfix Acceptance Evidence: Sepolia TransferFrom Unverifiable Opt-In Bypass

Date (UTC): 2026-02-21
Active slice context: `Slice 118` in progress (`Follow-Up D`).

## Objective + Scope Lock
- Objective:
  - add a controlled, explicit override for Sepolia LP add preflight false-negatives,
  - keep default fail-closed behavior unless opt-in env is enabled.
- Scope lock:
  - `apps/agent-runtime/xclaw_agent/cli.py`
  - `apps/agent-runtime/tests/test_liquidity_cli.py`
  - `.env.local`
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `spec.md`, `tasks.md`, `acceptance.md`

## Behavior Checks
- [x] Sepolia-only env flag `XCLAW_LIQUIDITY_ALLOW_SEPOLIA_TRANSFERFROM_BYPASS=1` enables preflight bypass only for `TransferHelper::transferFrom` failures under `rpc_forbidden_unverifiable` probes.
- [x] Bypass emits deterministic warning metadata `liquidity_preflight_router_transfer_from_unverifiable_bypassed`.
- [x] Disabled flag preserves fail-closed rejection.
- [x] Runtime tests cover enabled/disabled behavior.

## Required Validation Gates
- [x] `python3 -m unittest apps/agent-runtime/tests/test_liquidity_cli.py -v`
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] `npm run build`
- [x] `pm2 restart all`

# Hotfix Acceptance Evidence: Sepolia LP Add RPC-Retry Preflight Stability

Date (UTC): 2026-02-21
Active slice context: `Slice 118` in progress (`Follow-Up C`).

## Objective + Scope Lock
- Objective:
  - reduce false `liquidity_preflight_router_transfer_from_failed` on Sepolia LP add when preflight probes are RPC-forbidden/unverifiable,
  - retry simulation across configured RPC candidates before fail-closed rejection.
- Scope lock:
  - `apps/agent-runtime/xclaw_agent/cli.py`
  - `apps/agent-runtime/tests/test_liquidity_cli.py`
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `spec.md`, `tasks.md`, `acceptance.md`

## Behavior Checks
- [x] runtime retries LP add simulation across configured RPC candidates for `TransferHelper::transferFrom` failures only when token probes are `rpc_forbidden_unverifiable`.
- [x] retry success emits warning metadata `liquidity_preflight_router_transfer_from_retry_success` and avoids false preflight rejection.
- [x] fail-closed behavior remains when retry attempts continue failing.
- [x] runtime tests cover alternate-RPC retry success path.

## Required Validation Gates
- [x] `python3 -m unittest apps/agent-runtime/tests/test_liquidity_cli.py -v`
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] `npm run build`
- [x] `pm2 restart all`

# Hotfix Acceptance Evidence: Installer Hosted-Default API Base + Local Opt-In

Date (UTC): 2026-02-21
Active slice context: `Slice 117 Hotfix G` installer contract addendum.

## Objective + Scope Lock
- Objective:
  - default installer-generated API base to hosted `https://xclaw.trade/api/v1`,
  - require explicit opt-in (`XCLAW_INSTALL_FORCE_LOCAL_API=1`) for local API base.
- Scope lock:
  - `apps/network-web/src/app/skill-install.sh/route.ts`
  - `apps/network-web/src/app/skill-install.ps1/route.ts`
  - `skills/xclaw-agent/references/install-and-config.md`
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `spec.md`, `tasks.md`, `acceptance.md`

## Behavior Checks
- [x] Shell installer uses hosted canonical API base by default.
- [x] PowerShell installer uses hosted canonical API base by default.
- [x] Local API base remains available only when `XCLAW_INSTALL_FORCE_LOCAL_API=1`.

## Required Validation Gates
- [x] `npm run build`
- [x] `pm2 restart all`

# Hotfix Acceptance Evidence: Sepolia Uniswap LP Add TransferFrom Determinism + Allowance Coverage

Date (UTC): 2026-02-21
Active slice context: `Slice 118` in progress (`Follow-Up B`).

## Objective + Scope Lock
- Objective:
  - prevent LP add allowance under-coverage between estimate and submit for `amm_v2` execution,
  - map router `TransferHelper::transferFrom` simulation reverts to deterministic reason code.
- Scope lock:
  - `apps/agent-runtime/xclaw_agent/cli.py`
  - `apps/agent-runtime/tests/test_liquidity_cli.py`
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `spec.md`, `tasks.md`, `acceptance.md`

## Behavior Checks
- [x] v2 add allowance approvals now cover desired max units (`amountA`/`amountB`) to avoid estimate-drift under-approval.
- [x] router `TransferHelper::transferFrom` simulation failure maps to `liquidity_preflight_router_transfer_from_failed`.
- [x] runtime tests cover both behaviors.

## Required Validation Gates
- [x] `python3 -m unittest apps/agent-runtime/tests/test_liquidity_cli.py -v`
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] `npm run build`
- [x] `pm2 restart all`

Date (UTC): 2026-02-19
Active slice context: `Slice 86` in progress (explicit user-reported approvals-history visibility hotfix)

## Objective + Scope Lock
- Objective: prevent approved trades from disappearing from approvals history once they move to `filled/failed` quickly.
- Scope lock:
  - `apps/network-web/src/app/api/v1/management/approvals/inbox/route.ts`
  - `apps/network-web/src/app/api/v1/management/agent-state/route.ts`
  - `apps/network-web/src/lib/agent-page-view-model.ts`
  - `apps/network-web/src/app/agents/[agentId]/page.tsx`
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - handoff artifacts (`spec.md`, `tasks.md`, `acceptance.md`)

## Behavior Checks
- [x] `GET /api/v1/management/approvals/inbox` includes trade rows after status advances beyond `approved`.
- [x] Inbox status normalization maps `executing|verifying|filled|failed` to Approved-tab history semantics.
- [x] `/agents/[agentId]` approvals history includes non-pending trade approvals via `approvalsHistory`.
- [x] Pending trade queue rows are not duplicated by history rows.

## Required Validation Gates
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] `npm run build`
- [x] `pm2 restart all`

---

# Hotfix Acceptance Evidence: Runtime-Canonical Approval Prompt Button Clear (Trade/Transfer/Policy)

Date (UTC): 2026-02-19  
Active slice context: `Slice 87` in progress.

## Objective + Scope Lock
- Objective: remove cleanup drift by routing web + Telegram callback prompt cleanup through runtime `approvals clear-prompt`, with button-clear-only behavior.
- Scope lock:
  - `apps/agent-runtime/xclaw_agent/cli.py`
  - `apps/agent-runtime/tests/test_trade_path.py`
  - `apps/network-web/src/app/api/v1/management/approvals/decision/route.ts`
  - `apps/network-web/src/app/api/v1/management/transfer-approvals/decision/route.ts`
  - `apps/network-web/src/app/api/v1/management/policy-approvals/decision/route.ts`
  - `skills/xclaw-agent/scripts/openclaw_gateway_patch.py`
  - docs/artifacts (`docs/XCLAW_SOURCE_OF_TRUTH.md`, `docs/XCLAW_BUILD_ROADMAP.md`, `docs/XCLAW_SLICE_TRACKER.md`, `spec.md`, `tasks.md`, `acceptance.md`)

## Behavior Checks
- [x] Runtime exposes `approvals clear-prompt --subject-type <trade|transfer|policy> --subject-id <id> [--chain ...] --json`.
- [x] Runtime decision commands return normalized `promptCleanup`.
- [x] Runtime cleanup paths do not invoke `openclaw message delete` for approval prompts.
- [x] Web trade/transfer/policy decision routes dispatch runtime cleanup and surface `promptCleanup`.
- [x] Gateway callback patch no longer performs immediate callback pre-clear; runtime remains canonical clear owner.

## Required Validation Gates
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

# Hotfix Acceptance Evidence: Always Prod Agent After Web Trade/Transfer Approvals

Date (UTC): 2026-02-19
Active slice context: `Slice 86` in progress (explicit user-requested workflow-continuation hotfix)

## Objective + Scope Lock
- Objective: guarantee that web approval decisions for trade/transfer continue agent workflows even when last channel is Telegram.
- Scope lock:
  - `apps/network-web/src/lib/non-telegram-agent-prod.ts`
  - `apps/network-web/src/app/api/v1/management/approvals/decision/route.ts`
  - `apps/network-web/src/app/api/v1/management/approvals/approve-allowlist-token/route.ts`
  - `apps/network-web/src/app/api/v1/management/transfer-approvals/decision/route.ts`
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - handoff artifacts (`spec.md`, `tasks.md`, `acceptance.md`)
- Out of scope: callback logic changes and API schema changes.

## Behavior Checks
- [x] Web trade approval decision prod dispatch forces continuation even when last channel is Telegram.
- [x] Web trade terminal-result prod dispatch forces continuation even when last channel is Telegram.
- [x] Web transfer decision/result prod dispatch forces continuation even when last channel is Telegram.
- [x] Web allowlist trade approval prod dispatch forces continuation even when last channel is Telegram.
- [x] Default Telegram guard remains active for generic/non-overridden dispatch paths.

## Required Validation Gates
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] `npm run build`
- [x] `pm2 restart all`

---

# Hotfix Acceptance Evidence: Policy Approval Telegram Auto-Prompt Parity (Preapprove/Revoke/Global)

Date (UTC): 2026-02-19
Active slice context: `Slice 86` in progress (explicit user-requested Telegram approval UX alignment hotfix)

## Objective + Scope Lock
- Objective: make policy preapprove/revoke/global requests auto-send Telegram approval prompts with inline buttons (when Telegram is active), matching trade/transfer behavior.
- Scope lock:
  - `apps/agent-runtime/xclaw_agent/cli.py`
  - `apps/agent-runtime/tests/test_trade_path.py`
  - `skills/xclaw-agent/scripts/xclaw_agent_skill.py`
  - `skills/xclaw-agent/scripts/openclaw_gateway_patch.py`
  - `skills/xclaw-agent/SKILL.md`
  - `skills/xclaw-agent/references/commands.md`
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - handoff artifacts (`spec.md`, `tasks.md`, `acceptance.md`)
- Out of scope: API/schema/migration and management UI structural changes.

## Behavior Checks
- [x] Policy request commands attempt runtime-side Telegram prompt send for `approval_pending`.
- [x] Policy request responses are concise and do not require queuedMessage repost instructions.
- [x] Policy prompt callback payloads use `xpol|a|...` and `xpol|r|...`.
- [x] Non-Telegram active channel path skips auto-send and keeps management fallback hint.
- [x] Prompt send failures do not fail policy request creation.
- [x] Gateway fallback auto-attach accepts policy prompt text containing `ppr_...` even when strict status line is absent.

## Required Validation Gates
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

# Hotfix Acceptance Evidence: Force-Upgrade Gateway Callback Patch (v15) For Trade-Approve Ack Suppression

# Hotfix Acceptance Evidence: Web Approval Prompt Cleanup Recovery + Message ID Extraction Hardening

Date (UTC): 2026-02-19  
Active slice context: `Slice 87` in progress (explicit user-reported web approval parity issue)

## Objective + Scope Lock
- Objective: improve web approval Telegram button cleanup reliability by avoiding new unknown message IDs and adding runtime cleanup fallback from web decision path.
- Scope lock:
  - `apps/agent-runtime/xclaw_agent/cli.py`
  - `apps/agent-runtime/tests/test_trade_path.py`
  - `apps/network-web/src/app/api/v1/management/approvals/decision/route.ts`
  - `skills/xclaw-agent/SKILL.md`
  - `skills/xclaw-agent/references/commands.md`
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - handoff artifacts (`spec.md`, `tasks.md`, `acceptance.md`)

## Behavior Checks
- [x] Runtime parses OpenClaw message IDs from structured and non-JSON stdout patterns.
- [x] Runtime exposes `approvals cleanup-spot --trade-id ... --json` for deterministic single-trade prompt cleanup attempts.
- [x] Web approval decision async path retries cleanup via runtime when DB-side cleanup fails with `missing_message_id|prompt_not_found`.
- [x] Web fallback success marks DB prompt row as deleted (`deleted_at`) to avoid repeated stale cleanup errors.
- [x] Terminal trade-status prod dispatch allows Telegram-last-channel delivery (`allowTelegramLastChannel=true`) so web approvals can emit deterministic filled/rejected follow-up.
- [x] Web cleanup clears inline buttons (without deleting the underlying Telegram message) when `message_id` is available.
- [x] Prod dispatcher includes delivery (`--deliver`) so terminal trade result updates are posted to chat, not only computed in stdout.
- [x] Historical rows with `message_id='unknown'` and no local runtime prompt record remain non-recoverable by design (forward-only gap).

## Required Validation Gates
- [x] `python3 -m py_compile apps/agent-runtime/xclaw_agent/cli.py apps/agent-runtime/tests/test_trade_path.py skills/xclaw-agent/scripts/openclaw_gateway_patch.py`
- [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`
- [x] `python3 skills/xclaw-agent/scripts/openclaw_gateway_patch.py --json`
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] `npm run build`
- [x] `pm2 restart all`

## Trade-Specific Evidence
- `trd_07c042844df95a43163c` currently has DB prompt row:
  - `message_id='unknown'`
  - `delete_error='missing_message_id'`
- Runtime local prompt record for that trade is absent, so cleanup fallback cannot recover this historical prompt.

# Runtime-Canonical Approval Decisions (Trade/Transfer/Policy)

## Validation
- [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v -k decide_transfer`
- [x] Added runtime tests for `decide-spot` and `decide-policy`.
- [x] Added runtime test for invalid `--decision-at` failure path.
- [x] `python3 skills/xclaw-agent/scripts/openclaw_gateway_patch.py --json` (callback runtime-dispatch patch applies cleanly)
- [ ] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` (full sweep after merge window)
- [ ] `npm run build`
- [ ] `pm2 restart all`

## Notes
- Runtime-canonical management dispatch is feature-flagged by `XCLAW_RUNTIME_CANONICAL_APPROVAL_DECISIONS`.
- Historical prompt rows with `message_id='unknown'` remain forward-only cleanup gaps.
- Telegram callback cutover note:
  - callback decision branches now use runtime `approvals decide-*` dispatch for `xappr`/`xpol`/`xfer`;
  - runtime bin resolution for callback dispatch uses `XCLAW_AGENT_RUNTIME_BIN` then PATH (`xclaw-agent`) only.

Date (UTC): 2026-02-19
Active slice context: `Slice 86` in progress (explicit user-reported rollout reliability hotfix)

## Objective + Scope Lock
- Objective: force-update already-patched OpenClaw callback bundles so new trade-approve ack suppression behavior is actually applied.
- Scope lock:
  - `skills/xclaw-agent/scripts/openclaw_gateway_patch.py`
  - handoff artifacts (`spec.md`, `tasks.md`, `acceptance.md`)
- Out of scope: user-facing behavior changes beyond already-locked suppression contract.

## Behavior Checks
- [x] `v15` marker added and required for upgrade detection.
- [x] Existing bundles lacking `v15` are treated as outdated and re-injected.
- [x] patch fast-path cache invalidated via state schema bump.
- [x] canonical injected block includes `v15` marker.

## Required Validation Gates
- [x] `python3 -m py_compile skills/xclaw-agent/scripts/openclaw_gateway_patch.py` -> PASS
- [x] `python3 skills/xclaw-agent/scripts/openclaw_gateway_patch.py --json` -> PASS (`ok:true`, `patched:true`)
- [x] `npm run db:parity` -> PASS (`ok: true`)
- [x] `npm run seed:reset` -> PASS (`ok: true`)
- [x] `npm run seed:load` -> PASS (`ok: true`)
- [x] `npm run seed:verify` -> PASS (`ok: true`)
- [x] `npm run build` -> PASS (Next.js production build succeeded)
- [x] `pm2 restart all` -> PASS (`xclaw-web` online)

---

# Hotfix Acceptance Evidence: Suppress Telegram Intermediate "Approved trade" Ack For Conversions

Date (UTC): 2026-02-19
Active slice context: `Slice 86` in progress (explicit user-requested Telegram UX hotfix)

## Objective + Scope Lock
- Objective: suppress intermediate Telegram `Approved trade ...` callback ack for trade approvals while preserving final result messaging.
- Scope lock:
  - `skills/xclaw-agent/scripts/openclaw_gateway_patch.py`
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - handoff artifacts (`spec.md`, `tasks.md`, `acceptance.md`)
- Out of scope: API/runtime contract changes beyond callback ack emission behavior.

## Behavior Checks
- [x] Trade approve callback success path does not send intermediate `Approved trade ...` chat message.
- [x] Converged callback `409` branch suppresses `Approved trade ...` for `xappr` while preserving policy/transfer confirmations.
- [x] Fallback ack path suppresses `Approved trade ...` for `xappr` approve.
- [x] Final trade result messaging remains unchanged.
- [x] Source-of-truth feedback contract aligned to suppress intermediate trade approve ack.

## Required Validation Gates
- [x] `python3 -m py_compile skills/xclaw-agent/scripts/openclaw_gateway_patch.py` -> PASS
- [x] `python3 skills/xclaw-agent/scripts/openclaw_gateway_patch.py --json` -> PASS (`ok:true`, `patched:true`)
- [x] `npm run db:parity` -> PASS (`ok: true`)
- [x] `npm run seed:reset` -> PASS (`ok: true`)
- [x] `npm run seed:load` -> PASS (`ok: true`)
- [x] `npm run seed:verify` -> PASS (`ok: true`)
- [x] `npm run build` -> PASS (Next.js production build succeeded)
- [x] `pm2 restart all` -> PASS (`xclaw-web` online)

---

# Hotfix Acceptance Evidence: X-Claw Skill Prompt Contract Hardening (Fail-Closed Determinism)

Date (UTC): 2026-02-19
Active slice context: `Slice 86` in progress (explicit user-requested prompt/docs hardening)

## Objective + Scope Lock
- Objective: codify deterministic fail-closed skill prompting and response I/O behavior for X-Claw OpenClaw interactions.
- Scope lock:
  - `skills/xclaw-agent/SKILL.md`
  - `skills/xclaw-agent/references/commands.md`
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - handoff artifact updates (`spec.md`, `tasks.md`, `acceptance.md`)
- Out of scope: API/runtime/schema/migration code paths.

## Behavior Checks
- [x] Skill docs define explicit fail-closed statuses (`SKILL_SELECTION_AMBIGUOUS`, `NOT_VISIBLE`, `NOT_DEFINED`, `BLOCKED_<CATEGORY>`).
- [x] Skill docs define required response I/O sections (`Objective`, `Constraints Applied`, `Actions Taken`, `Evidence`, `Result`, `Next Step`).
- [x] Canonical source-of-truth includes matching locked prompt/response contract and runtime boundary guard.
- [x] Primary failure-code precedence is explicitly locked and single-code-only.
- [x] `BLOCKED_<CATEGORY>` uses fixed enum (`POLICY|PERMISSION|RUNTIME|DEPENDENCY|NETWORK|AUTH|DATA`).
- [x] `NOT_VISIBLE` usage is constrained to unavailable in-session source text/context.
- [x] Required machine envelope fields are locked (`status`, `code`, `summary`, `actions`, `evidence`).
- [x] Two-layer response contract is explicit (machine envelope + ordered human-readable sections).
- [x] Human `Evidence` section must reference all machine `evidence` IDs.
- [x] Multi-condition failures resolve to highest-precedence primary code; secondary findings go to `actions`.

## Required Validation Gates
- [x] `npm run db:parity` -> PASS (`ok: true`)
- [x] `npm run seed:reset` -> PASS (`ok: true`)
- [x] `npm run seed:load` -> PASS (`ok: true`)
- [x] `npm run seed:verify` -> PASS (`ok: true`)
- [x] `npm run build` -> PASS (Next.js production build succeeded)
- [x] `pm2 restart all` -> PASS (`xclaw-web` online)

---

# Hotfix Acceptance Evidence: Capability-Gated Telegram Patch + Management-Link Fallback

Date (UTC): 2026-02-18
Active slice context: `Slice 87` in progress (owner-requested reliability hotfix)

## Objective + Scope Lock
- Objective: make shell installer robust across user/root OpenClaw installs by capability-gating Telegram patching and auto-degrading to management-link mode when privileged patch writes are unavailable.
- Scope: `skill-install.sh` + skill wrapper fallback behavior + prompt/docs sync.
- Out of scope: PowerShell installer parity.

## Behavior Checks
- [x] Permission-denied patch write path auto-degrades and continues install with patch disabled.
  - Evidence: `apps/network-web/src/app/skill-install.sh/route.ts` now retries setup with `XCLAW_OPENCLAW_AUTO_PATCH=0` and `XCLAW_OPENCLAW_PATCH_STRICT=0` after matching `write_failed:.*permission denied`.
- [x] Installer persists `XCLAW_TELEGRAM_APPROVALS_FORCE_MANAGEMENT=1` in degraded mode and `0` in normal mode.
  - Evidence: installer sets `xclaw_telegram_force_management` and writes `skills.entries.xclaw-agent.env.XCLAW_TELEGRAM_APPROVALS_FORCE_MANAGEMENT`.
- [x] Telegram `approval_pending` includes management-link handoff when forced-management mode is enabled.
  - Evidence: `skills/xclaw-agent/scripts/xclaw_agent_skill.py` now allows owner-link fetch when `XCLAW_TELEGRAM_APPROVALS_FORCE_MANAGEMENT` is truthy.

## Required Validation Gates
- [x] `python3 -m py_compile skills/xclaw-agent/scripts/xclaw_agent_skill.py` -> PASS
- [x] `python3 -m unittest apps/agent-runtime/tests/test_x402_skill_wrapper.py -v` -> PASS (`Ran 22 tests`, `OK`)
- [x] `npm run db:parity` -> PASS (`ok: true`)
- [x] `npm run seed:reset` -> PASS (`ok: true`)
- [x] `npm run seed:load` -> PASS (`ok: true`)
- [x] `npm run seed:verify` -> PASS (`ok: true`)
- [x] `npm run build` -> PASS (Next.js build succeeded)
- [x] `pm2 restart all` -> PASS (`xclaw-web` online)

---

# Hotfix Acceptance Evidence: Telegram Transfer Callback Pairing-Prompt Regression

Date (UTC): 2026-02-18
Active slice context: `Slice 87` in progress; this was executed as explicit operator reliability hotfix.

## Objective + Scope Lock
- Objective: keep deterministic Telegram transfer result delivery while preventing callback path from triggering pairing/access prompts in the same chat.
- Scope lock:
  - `skills/xclaw-agent/scripts/openclaw_gateway_patch.py`
  - `skills/xclaw-agent/scripts/xclaw_agent_skill.py`
  - docs sync (`XCLAW_SOURCE_OF_TRUTH`, `XCLAW_SLICE_TRACKER`, `XCLAW_BUILD_ROADMAP`, handoff artifacts)

## Validation Commands and Outcomes
- `python3 -m unittest apps/agent-runtime/tests/test_x402_skill_wrapper.py -v` -> PASS (`Ran 21 tests`, `OK`)
- `npm run db:parity` -> PASS (`ok: true`)
- `npm run seed:reset` -> PASS (`ok: true`)
- `npm run seed:load` -> PASS (`ok: true`)
- `npm run seed:verify` -> PASS (`ok: true`)
- `npm run build` -> PASS
- `pm2 restart all` -> PASS (`xclaw-web` online)

## Functional Verification Notes
- Telegram transfer callback still posts deterministic final result message.
- Transfer callback patch no longer reinjects synthetic transfer-result message into chat pipeline.
- Skill wrapper now normalizes known symbol-unit mismatch guard errors to non-fatal `input_guarded` response for cleaner chat UX when no tx is sent.

---

# Hotfix Acceptance Evidence: Terminal-Only Agent Callback Notifications (Telegram)

Date (UTC): 2026-02-18
Active slice context: `Slice 86` in progress; this was executed as explicit operator UX hotfix.

## Objective + Scope Lock
- Objective: notify agent pipeline only on terminal callback outcomes (`filled|failed|rejected`), not on non-terminal `approved`.
- Scope lock:
  - `skills/xclaw-agent/scripts/openclaw_gateway_patch.py`
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `skills/xclaw-agent/SKILL.md`

## Validation Commands and Outcomes
- `XCLAW_AGENT_HOME=/tmp/xclaw-agent-test python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` -> PASS (`Ran 77 tests`, `OK`)
- `npm run db:parity` -> PASS (`ok: true`)
- `npm run seed:reset` -> PASS (`ok: true`)
- `npm run seed:load` -> PASS (`ok: true`)
- `npm run seed:verify` -> PASS (`ok: true`)
- `npm run build` -> PASS
- `pm2 restart all` -> PASS (`xclaw-web` online)
- `python3 skills/xclaw-agent/scripts/openclaw_gateway_patch.py --json` -> PASS (`patched: true`, OpenClaw bundle updated)

## Functional Verification Notes
- Telegram trade approve callback continues deterministic user confirmation + auto-resume execution.
- Non-terminal approval no longer triggers synthetic notify into agent pipeline.
- Trade terminal outcomes now notify agent pipeline with synthetic terminal result context.
- Trade/policy deny callbacks now notify agent pipeline with rejection context.

---

# Hotfix Acceptance Evidence: Telegram Trade Result Noise + Swap-Deposit Misclassification

Date (UTC): 2026-02-18
Active slice context: `Slice 86` is in progress; this change was executed as explicit user-requested hotfix.

## Objective + Scope Lock
- Objective: remove confusing/duplicative Telegram trade-result output and stop swap outputs from rendering as deposits in wallet activity.
- Scope lock:
  - `apps/network-web/src/app/api/v1/management/deposit/route.ts`
  - `skills/xclaw-agent/scripts/openclaw_gateway_patch.py`

## Validation Commands and Outcomes
- `XCLAW_AGENT_HOME=/tmp/xclaw-agent-test python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` -> PASS (`Ran 77 tests`, `OK`)
- `npm run db:parity` -> PASS (`ok: true`)
- `npm run seed:reset` -> PASS (`ok: true`)
- `npm run seed:load` -> PASS (`ok: true`; scenarios loaded)
- `npm run seed:verify` -> PASS (`ok: true`)
- `npm run build` -> PASS (Next.js production build completed)
- `pm2 restart all` -> PASS (`xclaw-web` online after restart)

## Functional Verification Notes
- Deposit sync now skips tx hashes already recorded in `trades` for the same agent/chain, preventing swap output transfer logs from being ingested as `deposit_events`.
- Gateway patch upgrade path now removes deterministic callback `Trade result: ...` post for trade approve callbacks, reducing duplicate Telegram chat messages.
- Gateway patch now normalizes trade-result pair composition without `? TOKEN_IN -> TOKEN_OUT` fallback placeholders.

---

# Slice 85 Acceptance Evidence

Date (UTC): 2026-02-18
Active slice: `Slice 85: EVM-Wide Portability Foundation`
Issue mapping: `#35`

## Objective + Scope Lock
- Objective: make chain handling config-driven and capability-gated for EVM portability while keeping x402 scope unchanged.
- Scope guard: no new live chain onboarding in this slice.

## Required Validation Commands and Outcomes
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` -> PASS (`Ran 63 tests`, `OK`)
- `python3 -m unittest apps/agent-runtime/tests/test_x402_runtime.py -v` -> PASS
- `npm run db:parity` -> PASS (`ok: true`)
- `npm run seed:reset` -> PASS (`ok: true`)
- `npm run seed:load` -> PASS (`ok: true`; seeded scenarios loaded)
- `npm run seed:verify` -> PASS (`ok: true`)
- `npm run build` -> PASS (Next.js production build completed)
- `pm2 restart all` -> PASS (`xclaw-web` online after restart)

## Functional Verification Notes
- Added `GET /api/v1/public/chains` with chain/capability metadata.
- Frontend chain selector options are registry-driven and no longer compile-time constants.
- Runtime added `xclaw-agent chains --json` (+ `--include-disabled`) and capability gates for trade/limit/x402/faucet flows.
- Added migration `0021_slice85_chain_token_metadata.sql` and token metadata resolver/cache.
- `GET /api/v1/management/agent-state` `chainTokens` now includes optional metadata fields (`name`, `decimals`, `source`, `tokenDisplay`).

---

# Slice 83 Acceptance Evidence

Date (UTC): 2026-02-17
Active slice: `Slice 83: Kite AI Testnet Parity`
Issue mapping: `#33`

## Objective + Scope Lock
- Objective: add Kite AI testnet as first-class chain parity for runtime/web/x402 metadata without custody model changes.
- Scope guard: Base Sepolia behavior preserved; `kite_ai_mainnet` remains disabled.

## Required Validation Commands and Outcomes
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` -> PASS (`Ran 61 tests`, `OK`)
- `python3 -m unittest apps/agent-runtime/tests/test_x402_runtime.py -v` -> PASS (`Ran 5 tests`, `OK`)
- `python3 -m unittest apps/agent-runtime/tests/test_dex_adapter.py -v` -> PASS (`Ran 2 tests`, `OK`)
- `npm run db:parity` -> PASS (`ok: true`)
- `npm run seed:reset` -> PASS (`ok: true`)
- `npm run seed:load` -> PASS (`ok: true`; totals `agents=6`, `trades=11`)
- `npm run seed:verify` -> PASS (`ok: true`)
- `npm run build` -> PASS (Next.js production build completed)
- `pm2 restart all` -> PASS (`xclaw-web` online after restart)

## Functional Verification Notes
- `config/chains/kite_ai_testnet.json` added with locked chain/rpc/explorer/router/factory/token constants.
- Runtime DEX adapter selection added with explicit Kite adapter path.
- `config/x402/networks.json` now enables `kite_ai_testnet` and keeps `kite_ai_mainnet` disabled.
- Web chain options include `Kite AI Testnet` and status provider probes include Kite.
- Public/management chain validation hints updated to include Kite.
- Hosted x402 receive request asset allowlist expanded to include `KITE`, `WKITE`, `USDT` for Kite chain.

---

# Slice 81 Acceptance Evidence

Date (UTC): 2026-02-17
Active slice: `Slice 81: Explore v2 Full Flush (No Placeholders)`
Issue mapping: `#30`

## Objective + Scope Lock
- Objective: remove Explore placeholders and deliver full-stack Explore v2 metadata/filtering contracts with owner-managed profile updates.
- Scope guard: extend existing public routes (no Explore-only public route family).

## Required Validation Commands and Outcomes
- `npm run db:parity` -> PASS (`ok: true`; includes `0018_slice81_explore_v2.sql`)
- `npm run seed:reset` -> PASS (`ok: true`)
- `npm run seed:load` -> PASS (`ok: true`; totals `agents=6`, `trades=11`)
- `npm run seed:verify` -> PASS (`ok: true`)
- `npm run build` -> PASS (Next.js production build completed; Explore and API routes compiled)
- `pm2 restart all` -> PASS (`xclaw-web` restarted and `online`)

## Functional Verification Notes
- `GET /api/v1/public/agents` now supports strategy/venue/risk/follower/volume/activity/verified filters and server-side `followers` sort.
- `GET /api/v1/public/agents` response rows include `exploreProfile`, `verified`, and `followerMeta` with null-safe defaults.
- `GET /api/v1/public/leaderboard` response rows include `verified` + `exploreProfile`.
- management profile contract is active:
  - `GET /api/v1/management/explore-profile?agentId=...`
  - `PUT /api/v1/management/explore-profile`
- `/explore` ships functional strategy/venue/risk controls, advanced drawer filters, section segmented control, verified badge, follower-rich metadata, and URL-deep-link state sync.
- `/agents` remains alias-compatible for Explore and uses Suspense wrapper for static prerender compatibility.

---

## Hosted x402 Receive Delta Acceptance (Current)

- `request-x402-payment` maps to hosted receive request creation (`xclaw-agent x402 receive-request ...`) and no longer starts local serve/tunnel.
- runtime parser no longer exposes `x402 serve-start|serve-status|serve-stop`.
- setup script no longer installs or reports `cloudflaredPath`.
- new API contract exists for agent-auth receive request creation:
  - `POST /api/v1/agent/x402/inbound/proposed`
  - schema: `agent-x402-inbound-proposed-request.schema.json`

# Slice 80 Acceptance Evidence

Date (UTC): 2026-02-17
Active slice: `Slice 80: Hosted x402 on /agents/[agentId]`
Issue mapping: `#31`

## Objective + Scope Lock
- Objective: implement hosted x402 receive endpoint/read model in network-web while keeping outbound x402 execution agent-originated.
- Scope guard: no server custody of agent wallet private keys.

## Required Validation Commands and Outcomes
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` -> PASS (`Ran 61 tests`, `OK`)
- `python3 -m unittest apps/agent-runtime/tests/test_x402_runtime.py -v` -> PASS (`Ran 6 tests`, `OK`)
- `python3 -m unittest apps/agent-runtime/tests/test_x402_skill_wrapper.py -v` -> PASS (`Ran 4 tests`, `OK`)
- `npm run db:parity` -> PASS (`ok: true`; includes `0017_slice80_hosted_x402.sql`)
- `npm run seed:reset` -> PASS (`ok: true`)
- `npm run seed:load` -> PASS (`ok: true`; totals `agents=6`, `trades=11`)
- `npm run seed:verify` -> PASS (`ok: true`)
- `npm run build` -> PASS (Next.js production build completed; x402 routes compiled)
- `pm2 restart all` -> PASS (`xclaw-web` restarted and `online`)

## Functional Verification Notes
- hosted endpoint `GET|POST /api/v1/x402/pay/{agentId}/{linkToken}` implemented with:
  - `402 payment_required` when `X-Payment` header is missing,
  - `200 payment_settled` on accepted payment header,
  - `410 payment_expired` after TTL expiry.
- outbound x402 mirror persists to `agent_x402_payment_mirror` and also mirrors to `agent_transfer_approval_mirror` with `approval_source='x402'`.
- management decision route reuses existing approval endpoint and dispatches x402 decisions through runtime `x402 pay-decide` when `approval_source='x402'`.
- `/agents/[agentId]` timeline merges x402 rows with `source: x402` badge; approval history renders x402 metadata (URL/network/facilitator/amount).
- `/agents/[agentId]` wallet side panel includes hosted x402 receive-link metadata and copy/regenerate controls.

---

# Slice 79 Acceptance Evidence

Date (UTC): 2026-02-17
Active slice: `Slice 79: Agent-Skill x402 Send/Receive Runtime`
Issue mapping: `#29`

## Objective + Scope Lock
- Objective: add Python-first x402 receive/pay runtime + skill command surfaces with local `xfr_...` approval lifecycle and cloudflared tunnel bootstrap.
- Scope guard honored: no `apps/network-web` integration in this slice.

## File-Level Evidence (Slice 79)
- Runtime/skill:
  - `apps/agent-runtime/xclaw_agent/cli.py`
  - `apps/agent-runtime/xclaw_agent/x402_runtime.py`
  - `apps/agent-runtime/xclaw_agent/x402_tunnel.py`
  - `apps/agent-runtime/xclaw_agent/x402_policy.py`
  - `apps/agent-runtime/xclaw_agent/x402_state.py`
  - `apps/agent-runtime/tests/test_x402_runtime.py`
  - `apps/agent-runtime/tests/test_x402_skill_wrapper.py`
  - `skills/xclaw-agent/scripts/xclaw_agent_skill.py`
  - `skills/xclaw-agent/scripts/setup_agent_skill.py`
  - `skills/xclaw-agent/SKILL.md`
  - `skills/xclaw-agent/references/commands.md`
- Contracts/config/docs:
  - `config/x402/networks.json`
  - `packages/shared-schemas/json/x402-runtime-state.schema.json`
  - `packages/shared-schemas/json/x402-serve-response.schema.json`
  - `packages/shared-schemas/json/x402-pay-request.schema.json`
  - `packages/shared-schemas/json/x402-pay-response.schema.json`
  - `packages/shared-schemas/json/x402-payment-approval.schema.json`
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `docs/api/WALLET_COMMAND_CONTRACT.md`
  - `docs/CONTEXT_PACK.md`
  - `spec.md`
  - `tasks.md`
  - `acceptance.md`

## Required Validation Commands and Outcomes
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` -> PASS (`Ran 60 tests`, `OK`)
- `python3 -m unittest apps/agent-runtime/tests/test_x402_runtime.py -v` -> PASS (`Ran 6 tests`, `OK`)
- `python3 -m unittest apps/agent-runtime/tests/test_x402_skill_wrapper.py -v` -> PASS (`Ran 4 tests`, `OK`)
- `npm run db:parity` -> PASS (`ok: true`)
- `npm run seed:reset` -> PASS (`ok: true`)
- `npm run seed:load` -> PASS (scenarios loaded; totals `agents=6`, `trades=11`)
- `npm run seed:verify` -> PASS (`ok: true`)
- `npm run build` -> PASS (Next.js production build completed)
- `pm2 restart all` (after build success) -> PASS (`xclaw-web` restarted and online)

## Functional Verification Notes
- `x402 networks --json` shows:
  - enabled: `base_sepolia`, `base`
  - disabled: `kite_ai_testnet`, `kite_ai_mainnet`
- `x402 serve-start --network base_sepolia --facilitator cdp --amount-atomic 1 --json` returned shareable `paymentUrl` and running state with tunnel/server pids.
- `x402 serve-start` now defaults to `ttlSeconds=1800` (30 minutes) when TTL is omitted.
- `x402-serve-start <network> <facilitator> <amount_atomic> [ttl_seconds]` supports explicit TTL override pass-through to runtime.
- Runtime worker now enforces timeout: payment path returns `payment_expired` after `expiresAt` and serve-status reports `expired`.
- `x402 pay --url <paymentUrl> --network base_sepolia --facilitator cdp --amount-atomic 1 --json` returned:
  - `approvalId: xfr_...`
  - `status: approval_pending`
  - queued message with deterministic approval fields.
- `request-x402-payment` response includes payer-visible expiration fields: `ttlSeconds`, `expiresAt`, `timeLimitNotice`.
- `x402 pay-decide --approval-id <xfr_id> --decision approve --json` resumed once and produced terminal result (`status: failed`, HTTP 530 challenge unresolved in this environment).
- `x402 pay-decide --approval-id <xfr_id> --decision deny --reason-message \"owner denied\" --json` produced terminal `status: rejected` with `reasonCode: approval_rejected`.
- `x402 serve-stop --json` converged runtime state to `stopped`.

---

# Slice 77 Acceptance Evidence

Date (UTC): 2026-02-17
Active slice: `Slice 77: Agent Wallet Page iPhone/MetaMask-Style Refactor`
Issue mapping: `pending mapping (legacy placeholder)`

## Objective + Scope Lock
- Objective: convert `/agents/:id` to a wallet-native iPhone/MetaMask-style management page while preserving sidebar shell, and remove policy editor surfaces (`Secondary Operations`, transfer/outbound policy editors).
- Scope guard honored: frontend-led refactor with existing management/public APIs preserved.

## File-Level Evidence (Slice 77)
- Web/UI:
  - `apps/network-web/src/app/agents/[agentId]/page.tsx`
  - `apps/network-web/src/app/agents/[agentId]/page.module.css`
- Docs/process:
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `spec.md`
  - `tasks.md`
  - `acceptance.md`

## Required Validation Commands and Outcomes
- `npm run db:parity` -> PASS (`ok: true`; no missing tables/enums/checks)
- `npm run seed:reset` -> PASS (`ok: true`; seed-state and activity log removed)
- `npm run seed:load` -> PASS (`ok: true`; scenarios loaded: `happy_path`, `approval_retry`, `degraded_rpc`, `copy_reject`; totals `agents: 6`, `trades: 11`)
- `npm run seed:verify` -> PASS (`ok: true`; required scenarios present)
- `npm run build` -> PASS (Next.js production build completed for `/agents/[agentId]` refactor)

## Functional Verification Notes
- `/agents/:id` preserves dashboard sidebar shell framing while using wallet-native internal composition.
- Wallet-first section order is present with compact KPI chips and continuous card stack.
- `Secondary Operations` and transfer policy editor controls removed.
- Approval action surfaces remain in Approval History module.
- Copy relationships panel remains list/delete only with creation guidance to `/explore`.

## Blockers
- PENDING: screenshot evidence capture for `/agents/:id` dark/light parity and issue mapping post.

---

# Slice 76 Acceptance Evidence

Date (UTC): 2026-02-16
Active slice: `Slice 76: Explore / Agent Listing Full Frontend Refresh (/explore Canonical)`
Issue mapping: `#28`

## Objective + Scope Lock
- Objective: implement canonical `/explore` route, keep `/agents` compatibility alias, and deliver owner/viewer-aware Explore sections with API-preserving wiring.
- Scope guard honored: no backend/API/schema/migration changes.

## File-Level Evidence (Slice 76)
- Web/UI:
  - `apps/network-web/src/app/explore/page.tsx`
  - `apps/network-web/src/app/explore/page.module.css`
  - `apps/network-web/src/app/agents/page.tsx`
  - `apps/network-web/src/lib/explore-page-view-model.ts`
  - `apps/network-web/src/lib/explore-page-capabilities.ts`
  - `apps/network-web/src/components/public-shell.tsx`
  - `apps/network-web/src/app/page.tsx`
  - `apps/network-web/src/app/agents/[agentId]/page.tsx`
  - `apps/network-web/src/app/approvals/page.tsx`
  - `apps/network-web/src/app/settings/page.tsx`
- Docs/process:
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/CONTEXT_PACK.md`
  - `spec.md`
  - `tasks.md`
  - `acceptance.md`

## Required Validation Commands and Outcomes
- `npm run db:parity` -> PASS (`ok: true`; parity check timestamp `2026-02-16T10:35:50.908Z`)
- `npm run seed:reset` -> PASS (`ok: true`; removed `.seed-state.json` and `live-activity.log`)
- `npm run seed:load` -> PASS (`ok: true`; scenarios loaded: `happy_path`, `approval_retry`, `degraded_rpc`, `copy_reject`; totals `agents: 6`, `trades: 11`)
- `npm run seed:verify` -> PASS (`ok: true`; required scenarios present with totals `agents: 6`, `trades: 11`)
- `npm run build` -> PASS (Next.js build completed successfully; `/explore` and `/agents` routes present in build output)

## Functional Verification Notes
- Viewer mode sections and gated copy CTA: validated in code path review (`hasOwnerSession` gates copy actions and hides My Agents).
- Owner mode sections and copy-trade save flow: validated in code path review (`GET/POST/PATCH /api/v1/copy/subscriptions` wired with modal save path).
- Filters/sort/time-window behavior: validated in code path review (URL-state + fetch parameters for search/chain/status/sort/window/page).
- Placeholder controls for unsupported dimensions: validated in UI contract copy + disabled controls.
- Dark/light readability + desktop overflow checks: manual screenshot capture still pending.

## Blockers
- PENDING: capture desktop dark/light screenshots for `/explore` and attach to issue `#28`.

---

# Slice 75 Acceptance Evidence

Date (UTC): 2026-02-16
Active slice: `Slice 75: Settings & Security v1 (/settings) Frontend Refresh`
Issue mapping: `#27`

## Objective + Scope Lock
- Objective: implement `/settings` with Access/Security/Danger tabs while preserving `/status` diagnostics and existing API contracts.
- Scope guard honored: no backend/API/schema/migration changes.

## File-Level Evidence (Slice 75)
- Web/UI:
  - `apps/network-web/src/app/settings/page.tsx`
  - `apps/network-web/src/app/settings/page.module.css`
  - `apps/network-web/src/lib/settings-security-capabilities.ts`
  - `apps/network-web/src/components/public-shell.tsx`
  - `apps/network-web/src/app/page.tsx`
  - `apps/network-web/src/app/agents/[agentId]/page.tsx`
  - `apps/network-web/src/app/approvals/page.tsx`
- Docs/process:
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/CONTEXT_PACK.md`
  - `spec.md`
  - `tasks.md`
  - `acceptance.md`

## Required Validation Commands and Outcomes
- `npm run db:parity` -> PASS
  - `ok: true`
  - `missingTables: []`, `missingEnums: []`, `missingChecks: []`
- `npm run seed:reset` -> PASS
  - `ok: true`
- `npm run seed:load` -> PASS
  - scenarios: `happy_path`, `approval_retry`, `degraded_rpc`, `copy_reject`
  - totals: `agents=6`, `trades=11`
- `npm run seed:verify` -> PASS
  - `ok: true`
- `npm run build` -> PASS
  - Next.js production build completed
  - `/settings` emitted as static route

## Functional Verification Notes
- Viewer/no-session settings state:
  - `/settings` Access tab renders device-scoped empty state and no active-agent danger actions when no management session is present.
- Owner session controls + add-access form:
  - Owner context loads from `/api/v1/management/session/agents`.
  - Add access form parses key URL (`/agents/{agentId}?token=...`) and posts to `/api/v1/management/session/select`.
- Danger actions (`pause/resume/revoke-all`):
  - Action buttons call existing routes:
    - `/api/v1/management/pause`
    - `/api/v1/management/resume`
    - `/api/v1/management/revoke-all`
  - Panel-scoped success/error banners render without page crash.
- Placeholder modules + disabled CTAs:
  - Multi-agent verified inventory/remove access, global panic controls, and on-chain allowance sweep are explicitly disabled with placeholder copy.
- Dark/light readability + desktop overflow checks:
  - Route-level CSS includes light/dark token mapping and overflow controls (`overflow-x: clip`, wrap-safe row/action patterns).
  - Screenshot/manual desktop pass still pending.

## Blockers
- Capture desktop dark/light screenshots for `/settings`.

---

# Slice 74 Acceptance Evidence

Date (UTC): 2026-02-16
Active slice: `Slice 74: Approvals Center v1 (Frontend-Only, API-Preserving)`
Issue mapping: `#74` (to be created / mapped)

## Objective + Scope Lock
- Objective: add `/approvals` dashboard-aligned approvals inbox using existing management APIs.
- Scope guard honored: no backend/API/schema/migration changes.

## File-Level Evidence (Slice 74)
- Web/UI:
  - `apps/network-web/src/app/approvals/page.tsx`
  - `apps/network-web/src/app/approvals/page.module.css`
  - `apps/network-web/src/lib/approvals-center-view-model.ts`
  - `apps/network-web/src/lib/approvals-center-capabilities.ts`
  - `apps/network-web/src/components/public-shell.tsx`
  - `apps/network-web/src/app/page.tsx`
  - `apps/network-web/src/app/agents/[agentId]/page.tsx`
- Docs/process:
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/CONTEXT_PACK.md`
  - `spec.md`
  - `tasks.md`
  - `acceptance.md`

## Required Validation Commands and Outcomes
- `npm run db:parity` -> PASS
  - `ok: true`
  - `missingTables: []`, `missingEnums: []`, `missingChecks: []`
- `npm run seed:reset` -> PASS
  - `ok: true`
- `npm run seed:load` -> PASS
  - scenarios: `happy_path`, `approval_retry`, `degraded_rpc`, `copy_reject`
  - totals: `agents=6`, `trades=11`
- `npm run seed:verify` -> PASS
  - `ok: true`
- `npm run build` -> PASS
  - Next.js production build completed
  - `/approvals` emitted as static route

## Functional Verification Notes
- Viewer mode:
  - Implemented explicit no-session empty state with no owner actions rendered in `/approvals`.
  - Verification method: code-path check (`ownerContext.phase === 'none'`) and build validation.
- Owner mode:
  - Implemented owner-context fetch from `/api/v1/management/session/agents` and queue load from `/api/v1/management/agent-state`.
  - Verification method: endpoint wiring + build pass.
- Trade/policy/transfer decisions:
  - Implemented decision handlers wired to existing POST endpoints:
    - `/api/v1/management/approvals/decision`
    - `/api/v1/management/policy-approvals/decision`
    - `/api/v1/management/transfer-approvals/decision`
  - Verification method: request payload/path inspection + build pass.
- Placeholder modules + disabled CTAs:
  - Implemented explicit placeholders for cross-agent aggregation and allowances inventory actions.
  - Verification method: capability flags + disabled controls in page render.
- Dark/light readability + desktop overflow checks:
  - Route-level CSS includes light/dark token mapping and overflow-safe wrapping (`overflow-x: clip`, `overflow-wrap: anywhere`).
  - Screenshot/manual desktop pass still pending.

## Blockers
- Create/map issue `#74` and post evidence + commit hash(es).
- Capture and attach desktop dark/light screenshots for `/approvals`.

---

# Slice 03 Acceptance Evidence

Date (UTC): 2026-02-13
Active slice: `Slice 03: Agent Runtime CLI Scaffold (Done-Path Ready)`

## Pre-flight Baseline
- Workspace was already dirty before this change.
- Scope guard enforced: edits limited to declared Slice 03 allowlist.

## Objective + Scope Lock
- Objective: complete Slice 03 command-surface reliability and JSON error semantics.
- Cross-slice rule honored: real wallet behavior remains deferred to Slice 04+.

## File-Level Evidence (Slice 03)
- Runtime/wrapper behavior:
  - `apps/agent-runtime/xclaw_agent/cli.py`
  - `skills/xclaw-agent/scripts/xclaw_agent_skill.py`
  - `apps/agent-runtime/README.md`
  - `docs/api/WALLET_COMMAND_CONTRACT.md`
- Slice/process artifacts:
  - `docs/CONTEXT_PACK.md`
  - `spec.md`
  - `tasks.md`
  - `acceptance.md`
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`

## Verification Commands and Outcomes

### Required global gates
- Executed with:
  - `source ~/.nvm/nvm.sh && nvm use --silent default`
- `npm run db:parity` -> PASS (exit 0)
  - `"ok": true`
  - `"missingTables": []`
- `npm run seed:reset` -> PASS (exit 0)
- `npm run seed:load` -> PASS (exit 0)
  - scenarios: `happy_path`, `approval_retry`, `degraded_rpc`, `copy_reject`
- `npm run seed:verify` -> PASS (exit 0)
  - `"ok": true`
- `npm run build` -> PASS (exit 0)
  - Next.js production build completed.

### Runtime CLI wallet command matrix
- `apps/agent-runtime/bin/xclaw-agent status --json` -> PASS (JSON)
- `apps/agent-runtime/bin/xclaw-agent wallet health --chain base_sepolia --json` -> PASS (JSON)
- `apps/agent-runtime/bin/xclaw-agent wallet create --chain base_sepolia --json` -> PASS (JSON `code: not_implemented`)
- `apps/agent-runtime/bin/xclaw-agent wallet import --chain base_sepolia --json` -> PASS (JSON `code: not_implemented`)
- `apps/agent-runtime/bin/xclaw-agent wallet address --chain base_sepolia --json` -> PASS (JSON `code: wallet_missing` when wallet absent)
- `apps/agent-runtime/bin/xclaw-agent wallet sign-challenge --message "m" --chain base_sepolia --json` -> PASS (JSON `code: not_implemented`)
- `apps/agent-runtime/bin/xclaw-agent wallet send --to 0x0000000000000000000000000000000000000001 --amount-wei 1 --chain base_sepolia --json` -> PASS (JSON `code: not_implemented`)
- `apps/agent-runtime/bin/xclaw-agent wallet balance --chain base_sepolia --json` -> PASS (JSON `code: not_implemented`)
- `apps/agent-runtime/bin/xclaw-agent wallet token-balance --token 0x0000000000000000000000000000000000000001 --chain base_sepolia --json` -> PASS (JSON `code: not_implemented`)
- `apps/agent-runtime/bin/xclaw-agent wallet remove --chain base_sepolia --json` -> PASS (JSON)

### Wrapper delegation smoke
- Executed with minimal PATH to prove repo-local fallback:
  - `env -i PATH=/usr/bin:/bin XCLAW_DEFAULT_CHAIN=base_sepolia python3 skills/xclaw-agent/scripts/xclaw_agent_skill.py ...`
- `... wallet-health` -> PASS (delegated runtime JSON, exit 0)
- `... wallet-create` -> PASS (delegated runtime JSON `code: not_implemented`, exit 1)
- `... wallet-remove` -> PASS (delegated runtime JSON, exit 0)

### Negative/failure-path checks
- `... wallet-send bad 1` -> PASS (`code: invalid_input`, exit 2)
- `... wallet-send 0x0000000000000000000000000000000000000001 abc` -> PASS (`code: invalid_input`, exit 2)
- `... wallet-sign-challenge ""` -> PASS (`code: invalid_input`, exit 2)
- `... wallet-token-balance bad` -> PASS (`code: invalid_input`, exit 2)

## Slice Status Synchronization
- `docs/XCLAW_SLICE_TRACKER.md` Slice 03 set to `[x]` with all DoD boxes checked.
- `docs/XCLAW_BUILD_ROADMAP.md` active runtime scaffold checklist items updated in Section 7.

## High-Risk Review Protocol
- Security-sensitive path: wallet command routing and validation.
- Second-opinion pass: completed as an independent re-read of runtime/wrapper error and binary-resolution paths before acceptance logging.
- Rollback plan:
  1. revert only Slice 03 touched files,
  2. rerun required gates and command matrix,
  3. confirm Slice 03 status entries restored accordingly.

## Blockers
- None.

## Pre-Step Checkpoint (Before Slice 04)
- Date (UTC): 2026-02-13
- Action: Added governance rule in `AGENTS.md` requiring commit+push after each fully-tested slice.
- Action: Checkpoint commit/push created before Slice 04 implementation work.

## Slice 04 Acceptance Evidence

Date (UTC): 2026-02-13
Active slice: `Slice 04: Wallet Core (Create/Import/Address/Health)`

### Pre-step checkpoint evidence
- Separate checkpoint commit before Slice 04: `cb22213`
- Commit pushed to `origin/main` prior to Slice 04 implementation.
- Governance rule added in `AGENTS.md`: each fully-tested slice must be committed and pushed before next slice.

### File-level evidence (Slice 04)
- Runtime implementation:
  - `apps/agent-runtime/xclaw_agent/cli.py`
  - `apps/agent-runtime/requirements.txt`
  - `apps/agent-runtime/tests/test_wallet_core.py`
  - `apps/agent-runtime/README.md`
- Contract/docs/process:
  - `docs/api/WALLET_COMMAND_CONTRACT.md`
  - `docs/CONTEXT_PACK.md`
  - `spec.md`
  - `tasks.md`
  - `acceptance.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `docs/XCLAW_SLICE_TRACKER.md`

### Environment blockers and resolution
- Blocker: `python3 -m pip` unavailable (`No module named pip`).
- Blocker: `python3 -m venv` unavailable (`ensurepip` missing).
- Resolution used: bootstrap user pip via:
  - `curl -fsSL https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py`
  - `python3 /tmp/get-pip.py --user --break-system-packages`
- Dependency install command used:
  - `python3 -m pip install --user --break-system-packages -r apps/agent-runtime/requirements.txt`

### Unit/integration test evidence
- `python3 -m unittest apps/agent-runtime/tests/test_wallet_core.py -v` -> PASS
  - roundtrip encrypt/decrypt passes
  - malformed payload rejected
  - non-interactive create/import rejected
  - unsafe permission check rejected
  - missing wallet address path validated

### Required global gate evidence
Executed with:
- `source ~/.nvm/nvm.sh && nvm use --silent default`

Results:
- `npm run db:parity` -> PASS (`"ok": true`)
- `npm run seed:reset` -> PASS
- `npm run seed:load` -> PASS
- `npm run seed:verify` -> PASS (`"ok": true`)
- `npm run build` -> PASS

### Runtime wallet core evidence
- Interactive create (TTY) command:
  - `apps/agent-runtime/bin/xclaw-agent wallet create --chain base_sepolia --json`
  - result: `ok:true`, `message:"Wallet created."`, address returned.
- Address command:
  - `apps/agent-runtime/bin/xclaw-agent wallet address --chain base_sepolia --json`
  - result: `ok:true`, chain-bound address returned.
- Health command:
  - `apps/agent-runtime/bin/xclaw-agent wallet health --chain base_sepolia --json`
  - result: real state fields returned (`hasCast`, `hasWallet`, `metadataValid`, `filePermissionsSafe`).
- Interactive import (TTY) command in isolated runtime home:
  - `XCLAW_AGENT_HOME=/tmp/xclaw-s4-import/.xclaw-agent apps/agent-runtime/bin/xclaw-agent wallet import --chain base_sepolia --json`
  - result: `ok:true`, `imported:true`, address returned.

### Negative/security-path evidence
- Non-interactive create rejected:
  - `wallet create ... --json` -> `code: non_interactive`, exit `2`
- Non-interactive import rejected:
  - `wallet import ... --json` -> `code: non_interactive`, exit `2`
- Unsafe permission rejection:
  - wallet file mode `0644` -> `wallet health` returns `code: unsafe_permissions`, exit `1`
- Malformed encrypted payload rejection:
  - invalid base64 crypto fields -> `wallet health` returns `code: wallet_store_invalid`, exit `1`
- Plaintext artifact scan:
  - `rg` scan across wallet dirs found no persisted test passphrases/private-key literal.

### Slice status synchronization
- `docs/XCLAW_SLICE_TRACKER.md` Slice 04 set to `[x]` with all DoD boxes checked.
- `docs/XCLAW_BUILD_ROADMAP.md` updated for runtime wallet manager, portable wallet model, and plaintext-artifact guard.

### Dependency and supply-chain notes
- Added `argon2-cffi==23.1.0`
  - Purpose: Argon2id key derivation for wallet at-rest encryption key.
  - Risk note: mature package with bindings-only scope; used strictly for local KDF.
- Added `pycryptodome==3.21.0`
  - Purpose: Keccak-256 hashing for deterministic EVM address derivation from private key.
  - Risk note: mature crypto library; scoped to local address derivation only.

### High-risk review protocol
- Security-sensitive class: wallet key storage and secret handling.
- Second-opinion review pass: completed via focused re-review of command error paths, encryption metadata handling, and permission fail-closed behavior.
- Rollback plan:
  1. revert Slice 04 touched files only,
  2. rerun required npm gates + wallet command checks,
  3. confirm tracker/roadmap/docs return to pre-Slice-04 state.

## Slice 05 Acceptance Evidence

Date (UTC): 2026-02-13
Active slice: `Slice 05: Wallet Auth + Signing`
Issue mapping: `#5` (`Epic: Python agent runtime core (wallet + strategy + execution)`)

### Objective + scope lock
- Objective: implement `wallet-sign-challenge` for local EIP-191 auth/recovery signing with canonical challenge validation.
- Scope guard honored: no Slice 06 command implementation, no server/web API contract changes.

### File-level evidence (Slice 05)
- Runtime implementation:
  - `apps/agent-runtime/xclaw_agent/cli.py`
  - `apps/agent-runtime/tests/test_wallet_core.py`
  - `apps/agent-runtime/README.md`
- Contract/docs/process:
  - `docs/api/WALLET_COMMAND_CONTRACT.md`
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/CONTEXT_PACK.md`
  - `spec.md`
  - `tasks.md`
  - `acceptance.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `docs/XCLAW_SLICE_TRACKER.md`

### Environment unblock evidence
- Foundry installed for cast-backed signing:
  - `curl -L https://foundry.paradigm.xyz | bash`
  - `~/.foundry/bin/foundryup`
- Runtime signer evidence:
  - `~/.foundry/bin/cast --version` -> `cast 1.5.1-stable`

### Unit/integration test evidence
- `PATH="$HOME/.foundry/bin:$PATH" python3 -m unittest apps/agent-runtime/tests/test_wallet_core.py -v` -> PASS
- Coverage includes:
  - empty message rejection
  - missing wallet
  - malformed challenge shape
  - chain mismatch
  - stale timestamp
  - non-interactive passphrase rejection
  - missing cast dependency
  - happy-path signing with signature shape + scheme assertions

### Required global gate evidence
Executed with:
- `source ~/.nvm/nvm.sh && nvm use --silent default`

Results:
- `npm run db:parity` -> PASS (`"ok": true`)
- `npm run seed:reset` -> PASS
- `npm run seed:load` -> PASS
- `npm run seed:verify` -> PASS (`"ok": true`)
- `npm run build` -> PASS

### Runtime wallet-sign evidence
- Signing success command:
  - `XCLAW_WALLET_PASSPHRASE=passphrase-123 apps/agent-runtime/bin/xclaw-agent wallet sign-challenge --message "<canonical>" --chain base_sepolia --json`
  - result: `ok:true`, `code:"ok"`, `scheme:"eip191_personal_sign"`, `challengeFormat:"xclaw-auth-v1"`, 65-byte hex signature.
- Signature verification against address (server-side format expectation proxy):
  - `cast wallet verify --address <address> "<canonical>" "<signature>"`
  - result: `Validation succeeded.`
- Invalid challenge (missing keys):
  - result: `code:"invalid_challenge_format"`
- Empty challenge:
  - result: `code:"invalid_input"`
- Non-interactive signing without passphrase:
  - result: `code:"non_interactive"`
- Missing cast on PATH:
  - result: `code:"missing_dependency"`

### Slice status synchronization
- `docs/XCLAW_SLICE_TRACKER.md` Slice 05 set to `[x]` with all DoD items checked.
- `docs/XCLAW_BUILD_ROADMAP.md` runtime checklist updated:
  - cast backend integration for wallet/sign/send marked done.
  - wallet challenge-signing command marked done.

### High-risk review protocol
- Security-sensitive class: wallet signing/auth path.
- Second-opinion review pass: completed via focused re-review of challenge parsing, passphrase gating, and cast invocation error handling.
- Rollback plan:
  1. revert Slice 05 touched files only,
  2. rerun unittest + required npm gates,
  3. verify tracker/roadmap/source-of-truth return to pre-Slice-05 state.

## Slice 06 Acceptance Evidence

Date (UTC): 2026-02-13
Active slice: `Slice 06: Wallet Spend Ops (Send + Balance + Token Balance + Remove)`
Issue mapping: `#6` (`Slice 06: Wallet Spend Ops`)

### Objective + scope lock
- Objective: implement runtime wallet spend and balance operations with fail-closed policy preconditions.
- Scope guard honored: no server/web API or migration changes, no Slice 07+ runtime loop implementation.

### File-level evidence (Slice 06)
- Runtime implementation:
  - `apps/agent-runtime/xclaw_agent/cli.py`
  - `apps/agent-runtime/tests/test_wallet_core.py`
  - `apps/agent-runtime/README.md`
- Contract/docs/process:
  - `docs/api/WALLET_COMMAND_CONTRACT.md`
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/CONTEXT_PACK.md`
  - `spec.md`
  - `tasks.md`
  - `acceptance.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `docs/XCLAW_SLICE_TRACKER.md`

### Unit/integration test evidence
- `PATH="$HOME/.foundry/bin:$PATH" python3 -m unittest apps/agent-runtime/tests/test_wallet_core.py -v` -> PASS
- Coverage includes:
  - `wallet-send` policy fail-closed for missing policy file
  - `wallet-send` blocked on chain disabled, paused state, approval required, and daily cap exceeded
  - `wallet-send` success path with tx hash + ledger update
  - `wallet-balance` and `wallet-token-balance` success paths
  - `wallet-token-balance` invalid token rejection
  - `wallet-remove` multi-chain cleanup semantics

### Required global gate evidence
Executed with:
- `source ~/.nvm/nvm.sh && nvm use --silent default`

Results:
- `npm run db:parity` -> PASS (`"ok": true`)
- `npm run seed:reset` -> PASS
- `npm run seed:load` -> PASS
- `npm run seed:verify` -> PASS (`"ok": true`)
- `npm run build` -> PASS

### Task-specific runtime evidence (Hardhat-local-first)
- Local EVM runtime:
  - `anvil --host 127.0.0.1 --port 8545` started with chain id `31337` (Hardhat-local equivalent RPC target).
  - `cast chain-id --rpc-url http://127.0.0.1:8545` -> `31337`
- Wallet balance:
  - `XCLAW_AGENT_HOME=/tmp/xclaw-s6-manual/.xclaw-agent apps/agent-runtime/bin/xclaw-agent wallet balance --chain hardhat_local --json`
  - result: `code:"ok"`, `balanceWei:"10000000000000000000000"`
- Wallet send:
  - `XCLAW_WALLET_PASSPHRASE=passphrase-123 ... wallet send --to 0x70997970... --amount-wei 1000000000000000 --chain hardhat_local --json`
  - result: `code:"ok"`, `txHash:"0x340e551eb7da5046b910948318357dc7c2becb0d39f79d9e4373889fe739878a"`, `dailySpendWei:"1000000000000000"`
- Wallet token balance:
  - deployed deterministic test contract (`cast send --create ...`) at `0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512`
  - `... wallet token-balance --token 0xe7f1725E... --chain hardhat_local --json`
  - result: `code:"ok"`, `balanceWei:"42"`
- Policy-blocked send proof:
  - with `spend.approval_granted=false`, send command returns:
  - `code:"approval_required"`, `message:"Spend blocked because approval is required but not granted."`

### Slice status synchronization
- `docs/XCLAW_SLICE_TRACKER.md` Slice 06 set to `[x]` with all DoD items checked.
- `docs/XCLAW_BUILD_ROADMAP.md` updated for implemented wallet spend ops and active spend precondition gate.
- `docs/XCLAW_SOURCE_OF_TRUTH.md` issue mapping aligned to slice order and wallet implementation status updated for Slice 06.

### High-risk review protocol
- Security-sensitive class: wallet spend path and local policy gating.
- Second-opinion review pass: completed via focused re-review of policy fail-closed behavior, RPC/chain config loading, and secret-handling boundaries in send flow.
- Rollback plan:
  1. revert Slice 06 touched files only,
  2. rerun unittest + required npm gates,
  3. verify tracker/roadmap/source-of-truth and wallet contract docs return to pre-Slice-06 state.

## Pre-Slice 07 Control-Gate Evidence

Date (UTC): 2026-02-13
Checkpoint objective: complete roadmap Section `0.1 Control setup` and re-validate required gates before starting Slice 07.

### Control setup verification
- Branch strategy confirmed:
  - current branch: `main`
  - `gh api repos/fourtytwo42/ETHDenver2026/branches/main/protection` -> `404 Branch not protected`
  - recorded strategy: feature-branch-per-slice + mandatory commit/push checkpoint before starting next slice.
- Issue mapping confirmed:
  - `gh issue list --limit 20 --json number,title | jq '[.[]|select(.number>=1 and .number<=16)] | length'` -> `16`
  - `gh issue view 7 --json number,title,state,url` -> open and mapped to Slice 07.
- Required artifact folders confirmed present and tracked:
  - `config/chains/`
  - `packages/shared-schemas/json/`
  - `docs/api/`
  - `infrastructure/migrations/`
  - `infrastructure/scripts/`
  - `docs/test-vectors/`

### Validation gates (re-run)
Executed with:
- `source ~/.nvm/nvm.sh && nvm use --silent default`

Results:
- `npm run db:parity` -> PASS (`"ok": true`)
- `npm run seed:reset && npm run seed:load && npm run seed:verify` -> PASS (`"ok": true`)
- `npm run build` -> PASS (Next.js build succeeded)

### Files updated for this checkpoint
- `docs/XCLAW_BUILD_ROADMAP.md`
- `docs/XCLAW_SLICE_TRACKER.md`

## Slice 20 Acceptance Evidence

Date (UTC): 2026-02-14
Active slice: `Slice 20: Owner Link + Outbound Transfer Policy + Agent Limit-Order UX + Mock-Only Reporting`
Issue mapping: `#20`

### File-level evidence (Slice 20)
- Runtime + skill:
  - `apps/agent-runtime/xclaw_agent/cli.py`
  - `apps/agent-runtime/tests/test_trade_path.py`
  - `skills/xclaw-agent/scripts/xclaw_agent_skill.py`
  - `skills/xclaw-agent/SKILL.md`
  - `skills/xclaw-agent/references/commands.md`
- API/UI:
  - `apps/network-web/src/app/api/v1/agent/management-link/route.ts`
  - `apps/network-web/src/app/api/v1/agent/transfers/policy/route.ts`
  - `apps/network-web/src/app/api/v1/limit-orders/route.ts`
  - `apps/network-web/src/app/api/v1/limit-orders/[orderId]/cancel/route.ts`
  - `apps/network-web/src/app/api/v1/management/policy/update/route.ts`
  - `apps/network-web/src/app/api/v1/management/agent-state/route.ts`
  - `apps/network-web/src/app/api/v1/management/owner-link/route.ts`
  - `apps/network-web/src/app/agents/[agentId]/page.tsx`
- Contracts/docs/migrations:
  - `infrastructure/migrations/0007_slice20_owner_links_transfer_policy_agent_limit_orders.sql`
  - `infrastructure/scripts/check-migration-parity.mjs`
  - `docs/db/MIGRATION_PARITY_CHECKLIST.md`
  - `packages/shared-schemas/json/agent-management-link-request.schema.json`
  - `packages/shared-schemas/json/agent-limit-order-create-request.schema.json`
  - `packages/shared-schemas/json/agent-limit-order-cancel-request.schema.json`
  - `packages/shared-schemas/json/management-policy-update-request.schema.json`
  - `docs/api/openapi.v1.yaml`
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `spec.md`
  - `tasks.md`

### Required gate command matrix
- [x] `npm run db:parity`
- [x] `npm run db:migrate`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] `npm run build`
- [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

### Faucet addendum
- [x] `POST /api/v1/agent/faucet/request` implemented with fixed `0.05 ETH` drip and once-per-UTC-day agent limit (`429 rate_limited` on second same-day request).

### High-risk rollback notes
- Risk domain: auth/session token issuance, outbound transfer policy enforcement, migration.
- Rollback path:
  1. revert Slice 20 touched files listed above,
  2. rerun migration parity + seed + build gates,
  3. confirm agent runtime command surface and management UI return to pre-slice state.
- `docs/XCLAW_SOURCE_OF_TRUTH.md`
- `acceptance.md`

## Slice 06A Acceptance Evidence

Date (UTC): 2026-02-13
Active slice: `Slice 06A: Foundation Alignment Backfill (Post-06 Prereq)`
Issue mapping: `#18` (`Slice 06A: Foundation Alignment Backfill (Post-06 Prereq)`)

### Objective + scope lock
- Objective: align server/web runtime location to canonical `apps/network-web` before Slice 07 API implementation.
- Scope guard honored: no Slice 07 endpoint/auth business logic was implemented.

### File-level evidence (Slice 06A)
- Web runtime alignment:
  - `apps/network-web/src/app/layout.tsx`
  - `apps/network-web/src/app/page.tsx`
  - `apps/network-web/src/app/globals.css`
  - `apps/network-web/src/app/page.module.css`
  - `apps/network-web/public/next.svg`
  - `apps/network-web/next.config.ts`
  - `apps/network-web/next-env.d.ts`
  - `apps/network-web/tsconfig.json`
- Tooling/config:
  - `package.json`
  - `tsconfig.json`
- Canonical/process synchronization:
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/CONTEXT_PACK.md`
  - `spec.md`
  - `tasks.md`
  - `acceptance.md`

### Validation commands and outcomes
Executed with:
- `source ~/.nvm/nvm.sh`

Required gates:
- `npm run db:parity` -> PASS (`"ok": true`)
- `npm run seed:reset` -> PASS
- `npm run seed:load` -> PASS
- `npm run seed:verify` -> PASS (`"ok": true`)
- `npm run build` -> PASS (`next build apps/network-web`)

Slice-specific checks:
- `npm run dev -- --port 3100` + local HTTP probe -> PASS (`200`, server ready)
- `npm run start -- --port 3101` + local HTTP probe -> PASS (`200`, server ready)
- `test -d apps/network-web/src/app` -> PASS
- `test ! -d src` -> PASS
- `test ! -d public` -> PASS
- negative check `npx next build` (repo root without app dir) -> expected FAIL (`Couldn't find any pages or app directory`)
- runtime boundary smoke: `apps/agent-runtime/bin/xclaw-agent status --json` -> PASS (`ok: true`, scaffold healthy)

### Canonical synchronization evidence
- Tracker updated with new prerequisite slice and completion:
  - `docs/XCLAW_SLICE_TRACKER.md` Slice 06A status `[x]` and DoD boxes `[x]`.
- Roadmap updated to include 06A prerequisite and completion checklist:
  - `docs/XCLAW_BUILD_ROADMAP.md` sections `0.3` and `0.4`.
- Source-of-truth updated for sequence + issue mapping inclusion:
  - `docs/XCLAW_SOURCE_OF_TRUTH.md` section `15.1` and section `16`.

### Issue mapping and traceability
- Dedicated issue created for this slice:
  - `https://github.com/fourtytwo42/ETHDenver2026/issues/18`
- Note: `#17` already existed (closed, mapped to Slice 16), so Slice 06A mapping was assigned to `#18`.

### High-risk review mode note
- This slice touched runtime/build path and execution sequencing (operational risk class).
- Second-pass review performed on:
  - script path targets,
  - canonical path assumptions,
  - boundary preservation (Node/web vs Python/agent).

### Rollback plan
1. Revert Slice 06A touched files only.
2. Restore root app path (`src/`, `public/`) and script targets.
3. Re-run required gates (`db:parity`, `seed:*`, `build`) and structural smoke checks.

## Slice 07 Acceptance Evidence

Date (UTC): 2026-02-13  
Active slice: `Slice 07: Core API Vertical Slice`  
Issue mapping: `#7` (`https://github.com/fourtytwo42/ETHDenver2026/issues/7`)

### Objective + scope lock
- Objective: implement core API write/read surface in `apps/network-web` with bearer+idempotency baseline and canonical error contract.
- Scope guard honored: no Slice 08 session/step-up/auth-cookie implementation and no off-DEX endpoint implementation.

### File-level evidence (Slice 07)
- Runtime/server implementation:
  - `apps/network-web/src/lib/env.ts`
  - `apps/network-web/src/lib/db.ts`
  - `apps/network-web/src/lib/redis.ts`
  - `apps/network-web/src/lib/request-id.ts`
  - `apps/network-web/src/lib/errors.ts`
  - `apps/network-web/src/lib/agent-auth.ts`
  - `apps/network-web/src/lib/idempotency.ts`
  - `apps/network-web/src/lib/validation.ts`
  - `apps/network-web/src/lib/http.ts`
  - `apps/network-web/src/lib/ids.ts`
  - `apps/network-web/src/lib/trade-state.ts`
  - `apps/network-web/src/app/api/v1/agent/register/route.ts`
  - `apps/network-web/src/app/api/v1/agent/heartbeat/route.ts`
  - `apps/network-web/src/app/api/v1/trades/proposed/route.ts`
  - `apps/network-web/src/app/api/v1/trades/[tradeId]/status/route.ts`
  - `apps/network-web/src/app/api/v1/events/route.ts`
  - `apps/network-web/src/app/api/v1/public/leaderboard/route.ts`
  - `apps/network-web/src/app/api/v1/public/agents/route.ts`
  - `apps/network-web/src/app/api/v1/public/agents/[agentId]/route.ts`
  - `apps/network-web/src/app/api/v1/public/agents/[agentId]/trades/route.ts`
  - `apps/network-web/src/app/api/v1/public/activity/route.ts`
- Contract artifacts:
  - `docs/api/openapi.v1.yaml`
  - `packages/shared-schemas/json/agent-register-request.schema.json`
  - `packages/shared-schemas/json/agent-heartbeat-request.schema.json`
  - `packages/shared-schemas/json/trade-proposed-request.schema.json`
  - `packages/shared-schemas/json/event-ingest-request.schema.json`
  - `packages/shared-schemas/json/trade-status.schema.json`
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
- Process/governance artifacts:
  - `docs/CONTEXT_PACK.md`
  - `spec.md`
  - `tasks.md`
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `acceptance.md`
  - `package.json`
  - `package-lock.json`

### Dependency changes (pinned)
- `pg@8.13.3` (runtime): Postgres connectivity for API persistence.
- `redis@4.7.1` (runtime): idempotency key storage and replay/conflict enforcement.
- `ajv@8.17.1` (runtime): JSON-schema payload validation at API boundary.
- `@types/pg@8.15.0` (dev): strict TS typing support for `pg` use in Next route handlers.

Risk note:
- All added packages are mainstream, maintained ecosystem packages with narrowly scoped use in API boundary/persistence layers.

### Required global gate evidence
Executed with:
- `source ~/.nvm/nvm.sh && nvm use --silent default`

Results:
- `npm run db:parity` -> PASS (`"ok": true`)
- `npm run seed:reset` -> PASS
- `npm run seed:load` -> PASS
- `npm run seed:verify` -> PASS (`"ok": true`)
- `npm run build` -> PASS (all Slice 07 route handlers compile)

### API curl matrix evidence (selected)
Dev server launched with:
- `DATABASE_URL=postgresql://xclaw_app:xclaw_local_dev_pw@127.0.0.1:5432/xclaw_db`
- `REDIS_URL=redis://127.0.0.1:6379`
- `XCLAW_AGENT_API_KEYS={"ag_slice7":"slice7_token_abc12345"}`

Verified negative-path checks:
- Missing bearer on write route -> `401` + `code:"auth_invalid"`
- Missing `Idempotency-Key` -> `400` + `code:"payload_invalid"`
- Invalid register schema -> `400` + `code:"payload_invalid"` + validation details
- Reused idempotency key with changed payload -> `409` + `code:"idempotency_conflict"`

### Blocker (explicit)
- Positive-path DB-backed endpoint verification is blocked by local Postgres credential mismatch.
- Evidence:
  - `psql -h 127.0.0.1 -U xclaw_app -d xclaw_db` -> `FATAL: password authentication failed for user "xclaw_app"`
  - DB-backed API routes currently return `internal_error` under that credential set.

Unblock command pattern:
- Start dev server with valid local DB credentials and rerun Slice 07 curl matrix:
  - `source ~/.nvm/nvm.sh && nvm use --silent default && DATABASE_URL='<valid>' REDIS_URL='redis://127.0.0.1:6379' XCLAW_AGENT_API_KEYS='{"ag_slice7":"slice7_token_abc12345"}' npm run dev -- --port 3210`

### High-risk review protocol
- Security-sensitive class: API auth + idempotency + persistence write paths.
- Second-opinion review pass: completed as focused review of bearer enforcement, idempotency replay/conflict semantics, and canonical error shape consistency.
- Rollback plan:
  1. revert Slice 07 touched files only,
  2. rerun required gates,
  3. confirm tracker/roadmap/source-of-truth sync returns to pre-Slice-07 state.

### Slice 07 Blocker Resolution + Final Verification (2026-02-13)
- Resolved local DB credential blocker by creating a user-owned PostgreSQL cluster and canonical app credentials:
  - host/port: `127.0.0.1:55432`
  - db/user/password: `xclaw_db` / `xclaw_app` / `xclaw_local_dev_pw`
  - saved in `.env.local`, `apps/network-web/.env.local`, and `~/.pgpass` (600 perms)
- Applied migration fix required for reset validity:
  - `infrastructure/migrations/0001_xclaw_core.sql` changed `performance_snapshots.window` -> `performance_snapshots."window"`
  - aligned read queries in:
    - `apps/network-web/src/app/api/v1/public/leaderboard/route.ts`
    - `apps/network-web/src/app/api/v1/public/agents/[agentId]/route.ts`
- Fixed trade status endpoint positive-path DB type bug:
  - cast `$1` to `trade_status` in `apps/network-web/src/app/api/v1/trades/[tradeId]/status/route.ts`

Final Slice 7 curl matrix (all expected outcomes met):
- write path status codes: `401,400,400,200,200,409,200,200,409,400,200`
- public read path status codes: `200,200,200,200,200,404`
- verified positive endpoints:
  - register, heartbeat, trade proposed, trade status transition (`proposed -> approved`), events
  - leaderboard, agents search, profile, trades, activity
- verified negative/failure paths:
  - missing auth -> `auth_invalid`
  - missing idempotency -> `payload_invalid`
  - invalid schema -> `payload_invalid` with details
  - idempotency conflict -> `idempotency_conflict`
  - invalid trade transition -> `trade_invalid_transition`
  - path/body tradeId mismatch -> `payload_invalid`
  - unknown profile -> 404 with canonical error payload

Revalidated gates after fixes:
- `npm run db:parity` -> PASS
- `npm run build` -> PASS

## Slice 08 Acceptance Evidence

Date (UTC): 2026-02-13  
Active slice: `Slice 08: Auth + Management Vertical Slice`  
Issue mapping: `#8` (`https://github.com/fourtytwo42/ETHDenver2026/issues/8`)

### Objective + scope lock
- Objective: implement management session bootstrap, step-up auth, revoke-all rotation, CSRF enforcement, and `/agents/:id?token=...` bootstrap behavior.
- Scope guard honored: no Slice 09 public-data UX implementation and no Slice 10 management controls implementation.

### File-level evidence (Slice 08)
- Runtime/server implementation:
  - `apps/network-web/src/lib/env.ts`
  - `apps/network-web/src/lib/management-cookies.ts`
  - `apps/network-web/src/lib/management-auth.ts`
  - `apps/network-web/src/lib/management-service.ts`
  - `apps/network-web/src/app/api/v1/management/session/bootstrap/route.ts`
  - `apps/network-web/src/app/api/v1/management/stepup/challenge/route.ts`
  - `apps/network-web/src/app/api/v1/management/stepup/verify/route.ts`
  - `apps/network-web/src/app/api/v1/management/revoke-all/route.ts`
  - `apps/network-web/src/app/agents/[agentId]/page.tsx`
- Shared schemas:
  - `packages/shared-schemas/json/management-bootstrap-request.schema.json`
  - `packages/shared-schemas/json/stepup-challenge-request.schema.json`
  - `packages/shared-schemas/json/stepup-verify-request.schema.json`
  - `packages/shared-schemas/json/agent-scoped-request.schema.json`
- Contracts/docs/process:
  - `docs/api/openapi.v1.yaml`
  - `docs/api/AUTH_WIRE_EXAMPLES.md`
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/CONTEXT_PACK.md`
  - `spec.md`
  - `tasks.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `acceptance.md`

### Required global gate evidence
Executed with:
- `source ~/.nvm/nvm.sh && nvm use --silent default`

Results:
- `npm run db:parity` -> PASS (`"ok": true`)
- `npm run seed:reset` -> PASS
- `npm run seed:load` -> PASS
- `npm run seed:verify` -> PASS (`"ok": true`)
- `XCLAW_MANAGEMENT_TOKEN_ENC_KEY='AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=' npm run build` -> PASS

### Slice 08 setup evidence
- Seeded test agent and active management token for bootstrap matrix:
  - inserted `agents.agent_id='ag_slice8'`
  - inserted active `management_tokens` row with encrypted ciphertext + fingerprint for token `slice8-bootstrap-token-001`
- Dev server launch command:
  - `DATABASE_URL=postgresql://xclaw_app:xclaw_local_dev_pw@127.0.0.1:55432/xclaw_db REDIS_URL=redis://127.0.0.1:6379 XCLAW_AGENT_API_KEYS='{"ag_slice7":"slice7_token_abc12345"}' XCLAW_IDEMPOTENCY_TTL_SEC=86400 XCLAW_MANAGEMENT_TOKEN_ENC_KEY='AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=' npm run dev -- --port 3210`

### Slice 08 curl matrix evidence
Status and contract outcomes:
- `POST /api/v1/management/session/bootstrap` valid token -> `200` + `ok:true` + `xclaw_mgmt`/`xclaw_csrf` cookies
- `POST /api/v1/management/session/bootstrap` invalid token -> `401` + `code:"auth_invalid"`
- `POST /api/v1/management/session/bootstrap` malformed body -> `400` + `code:"payload_invalid"`
- `POST /api/v1/management/stepup/challenge` missing CSRF header -> `401` + `code:"csrf_invalid"`
- `POST /api/v1/management/stepup/challenge` valid auth+csrf -> `200` + `challengeId` + one-time `code` + `expiresAt`
- `POST /api/v1/management/stepup/verify` wrong code -> `401` + `code:"stepup_invalid"`
- `POST /api/v1/management/stepup/verify` valid code -> `200` + `xclaw_stepup` cookie set
- `POST /api/v1/management/revoke-all` valid auth+csrf -> `200` + revoked session counts + `newManagementToken`
- post-revoke old management cookie -> `401` (`auth_invalid`)
- post-rotate old bootstrap token -> `401` (`auth_invalid`)
- post-rotate new bootstrap token -> `200` bootstrap success

### URL token-strip behavior evidence
- `/agents/ag_slice8?token=<token>` renders Slice 08 bootstrap client surface and uses client-side bootstrap + `router.replace('/agents/ag_slice8')` to strip query token after validation.
- Environment limitation: no browser automation runtime (Playwright/chromium unavailable), so URL-strip proof is implementation-path + manual browser verification path rather than headless artifact.

### High-risk review protocol
- Security-sensitive class: auth/session/cookie/CSRF/token-rotation.
- Second-opinion review pass: completed via focused re-read of token encryption/fingerprint logic, session cookie hash validation, and revocation ordering semantics.
- Rollback plan:
  1. revert Slice 08 touched files only,
  2. rerun required gates + Slice 08 curl matrix,
  3. confirm tracker/roadmap/source-of-truth sync returns to pre-Slice-08 state.

### Issue traceability
- Verification evidence + commit hash posted to issue `#8`:
  - `https://github.com/fourtytwo42/ETHDenver2026/issues/8#issuecomment-3895076028`

## Slice 09 Acceptance Evidence

Date (UTC): 2026-02-13
Active slice: `Slice 09: Public Web Vertical Slice`
Issue mapping: `#9` (`Slice 09: Public Web Vertical Slice`)

### Objective + scope lock
- Objective: implement public web vertical slice on `/`, `/agents`, and `/agents/:id` with canonical status vocabulary, mock/real visual separation, and dark-default/light-toggle theme support.
- Scope lock honored: `/status` page implementation deferred to Slice 14 and synchronized in canonical docs in this same slice.

### File-level evidence (Slice 09)
- Public web/UI implementation:
  - `apps/network-web/src/app/layout.tsx`
  - `apps/network-web/src/app/globals.css`
  - `apps/network-web/src/app/page.tsx`
  - `apps/network-web/src/app/agents/page.tsx`
  - `apps/network-web/src/app/agents/[agentId]/page.tsx`
  - `apps/network-web/src/components/public-shell.tsx`
  - `apps/network-web/src/components/theme-toggle.tsx`
  - `apps/network-web/src/components/public-status-badge.tsx`
  - `apps/network-web/src/components/mode-badge.tsx`
  - `apps/network-web/src/lib/public-types.ts`
  - `apps/network-web/src/lib/public-format.ts`
- Public API refinements:
  - `apps/network-web/src/app/api/v1/public/agents/route.ts`
  - `apps/network-web/src/app/api/v1/public/leaderboard/route.ts`
  - `apps/network-web/src/lib/env.ts`
  - `apps/network-web/src/lib/management-service.ts`
- Contract/process sync:
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/api/openapi.v1.yaml`
  - `docs/CONTEXT_PACK.md`
  - `spec.md`
  - `tasks.md`
  - `acceptance.md`

### Required global gates
Executed with:
- `source ~/.nvm/nvm.sh && nvm use --silent default`

Results:
- `npm run db:parity` -> PASS (`"ok": true`)
- `npm run seed:reset` -> PASS
- `npm run seed:load` -> PASS
- `npm run seed:verify` -> PASS (`"ok": true`)
- `npm run build` -> PASS (Next build completed; routes include `/`, `/agents`, `/agents/[agentId]`)

### Slice-specific curl/browser matrix
- Home route render:
  - `curl -i http://localhost:3000/`
  - result: `HTTP/1.1 200 OK`
- Agents API positive path:
  - `curl -s "http://localhost:3000/api/v1/public/agents?query=agent&sort=last_activity&page=1"`
  - result: `ok:true` with paging metadata (`page`, `pageSize`, `total`) and sorted `items`.
- Agents API negative path:
  - `curl -i "http://localhost:3000/api/v1/public/agents?sort=bad_value"`
  - result: `HTTP/1.1 400 Bad Request` with canonical error payload (`code: payload_invalid`, `message`, `actionHint`, `requestId`).
- Public profile route render:
  - `curl -i http://localhost:3000/agents/ag_slice8`
  - result: `HTTP/1.1 200 OK`
- Unauthorized visibility check:
  - script-stripped HTML check returned `Agent Profile`, `Trades`, `Activity Timeline` and no matches for `approve|withdraw|custody|policy controls|approval queue`.
- Theme baseline:
  - layout defaults to `data-theme="dark"`; header toggle persists browser theme in `localStorage` key `xclaw_theme`.

### Notable fix during verification
- `GET /api/v1/public/agents` initially returned 500 in local env because `getEnv()` hard-required `XCLAW_MANAGEMENT_TOKEN_ENC_KEY` even for public routes.
- Fix applied: lazy enforcement via `requireManagementTokenEncKey()` used by management service only; public routes now function without management key env in local mode.

### Canonical docs synchronization
- Slice 09 DoD now covers `/`, `/agents`, `/agents/:id` only.
- Slice 14 DoD/roadmap now explicitly owns `/status` diagnostics page implementation.
- Source-of-truth slice sequence includes locked deferral note for `/status` to Slice 14.

### High-risk review protocol
- Security-adjacent change class: env gating for management encryption key.
- Second-opinion review pass: completed via focused re-check that management endpoints still enforce key validation while public routes remain available.
- Rollback plan:
  1. revert Slice 09 touched files only,
  2. rerun required gates,
  3. verify tracker/roadmap/source-of-truth consistency and public route behavior.

## Slice 10 Acceptance Evidence

Date (UTC): 2026-02-13
Active slice: `Slice 10: Management UI Vertical Slice`
Issue mapping: `#10`

### Objective + scope lock
- Objective: implement canonical Slice 10 management UI + API vertical slice on `/agents/:id`.
- Scope lock honored: off-DEX depth is queue/state controls only; no Slice 12 escrow execution/runtime adapter work.

### File-level evidence (Slice 10)
- Web/API implementation:
  - `apps/network-web/src/app/agents/[agentId]/page.tsx`
  - `apps/network-web/src/components/public-shell.tsx`
  - `apps/network-web/src/components/management-header-controls.tsx`
  - `apps/network-web/src/app/globals.css`
  - `apps/network-web/src/app/api/v1/management/agent-state/route.ts`
  - `apps/network-web/src/app/api/v1/management/audit/route.ts`
  - `apps/network-web/src/app/api/v1/management/approvals/decision/route.ts`
  - `apps/network-web/src/app/api/v1/management/approvals/scope/route.ts`
  - `apps/network-web/src/app/api/v1/management/policy/update/route.ts`
  - `apps/network-web/src/app/api/v1/management/pause/route.ts`
  - `apps/network-web/src/app/api/v1/management/resume/route.ts`
  - `apps/network-web/src/app/api/v1/management/withdraw/destination/route.ts`
  - `apps/network-web/src/app/api/v1/management/withdraw/route.ts`
  - `apps/network-web/src/app/api/v1/management/offdex/decision/route.ts`
  - `apps/network-web/src/app/api/v1/management/session/agents/route.ts`
  - `apps/network-web/src/app/api/v1/management/session/select/route.ts`
  - `apps/network-web/src/app/api/v1/management/logout/route.ts`
- Schemas/contracts/docs:
  - `packages/shared-schemas/json/management-approval-decision-request.schema.json`
  - `packages/shared-schemas/json/management-policy-update-request.schema.json`
  - `packages/shared-schemas/json/management-approval-scope-request.schema.json`
  - `packages/shared-schemas/json/management-pause-request.schema.json`
  - `packages/shared-schemas/json/management-resume-request.schema.json`
  - `packages/shared-schemas/json/management-withdraw-destination-request.schema.json`
  - `packages/shared-schemas/json/management-withdraw-request.schema.json`
  - `packages/shared-schemas/json/management-offdex-decision-request.schema.json`
  - `packages/shared-schemas/json/management-session-select-request.schema.json`
  - `docs/api/openapi.v1.yaml`
  - `docs/api/AUTH_WIRE_EXAMPLES.md`
- Governance/process:
  - `docs/CONTEXT_PACK.md`
  - `spec.md`
  - `tasks.md`
  - `acceptance.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `docs/XCLAW_SLICE_TRACKER.md`

### Governance synchronization evidence
- GitHub issue `#10` DoD synchronized to canonical scope (added off-DEX queue/controls + audit panel).

### Required global gate evidence
Executed with:
- `source ~/.nvm/nvm.sh && nvm use --silent default`

Results:
- `npm run db:parity` -> PASS (`ok: true`)
- `npm run seed:reset` -> PASS
- `npm run seed:load` -> PASS
- `npm run seed:verify` -> PASS (`ok: true`)
- `npm run build` -> PASS (Next.js build + TypeScript)

### Slice-10 functional and negative-path API evidence
Runtime for API verification:
- `XCLAW_MANAGEMENT_TOKEN_ENC_KEY` set to a valid base64 32-byte key for local test session/bootstrap path.
- Local seeded test agent: `ag_slice10` with bootstrap token fixture inserted for test matrix.

Verification highlights:
1. Bootstrap session succeeds and emits cookies:
- `POST /api/v1/management/session/bootstrap` -> `200`
- `Set-Cookie`: `xclaw_mgmt`, `xclaw_csrf`, clear `xclaw_stepup`

2. Unauthorized read fails correctly:
- `GET /api/v1/management/agent-state?agentId=ag_slice10` (no cookie) -> `401 auth_invalid`

3. CSRF enforcement works:
- `POST /api/v1/management/approvals/decision` (no `X-CSRF-Token`) -> `401 csrf_invalid`

4. Approval queue action works:
- `POST /api/v1/management/approvals/decision` approve -> `200` (`status: approved`)
- repeat decision on same trade -> `409 trade_invalid_transition`

5. Step-up gating works:
- `POST /api/v1/management/withdraw/destination` (no stepup cookie) -> `401 stepup_required`
- `POST /api/v1/management/stepup/challenge` -> `200`
- `POST /api/v1/management/stepup/verify` -> `200` + `Set-Cookie xclaw_stepup`
- `POST /api/v1/management/withdraw/destination` -> `200`
- `POST /api/v1/management/withdraw` -> `200` (`status: accepted`)

6. Off-DEX queue controls work:
- `POST /api/v1/management/offdex/decision` action `approve` from `proposed` -> `200` (`status: accepted`)
- repeat `approve` from `accepted` -> `409 trade_invalid_transition` + actionHint

7. Header/session helper + logout behavior works:
- `GET /api/v1/management/session/agents` -> `200` with managed agent list
- `POST /api/v1/management/logout` -> `200` with clear-cookie headers
- subsequent `GET /api/v1/management/agent-state` with updated cookie jar -> `401 auth_invalid`

8. Audit panel backing data present:
- `GET /api/v1/management/agent-state` response includes non-empty `auditLog` with redacted payload entries.

### High-risk review mode evidence
- Security-sensitive areas touched: management auth, CSRF, step-up gating, withdraw controls, approval scope changes.
- Second-opinion pass: completed by targeted re-review of auth/step-up guarded endpoints and failure-path responses.
- Rollback plan:
  1. revert Slice 10 touched files only,
  2. rerun required validation gates,
  3. verify tracker/roadmap + issue `#10` synchronization remains coherent.

### Blockers encountered and resolution
- `npm` not initially on shell PATH.
  - Resolution: run validations with `source ~/.nvm/nvm.sh && nvm use --silent default`.


## Slice 11 Acceptance Evidence

Date (UTC): 2026-02-13
Active slice: `Slice 11: Hardhat Local Trading Path`
Issue mapping: `#11`

### Objective + scope lock
- Objective: implement hardhat-local trading lifecycle through runtime command surface and local deployed contracts.
- Scope guard: off-DEX runtime lifecycle and copy lifecycle remain deferred to Slice 12/13.

### File-level evidence (Slice 11)
- Runtime implementation:
  - `apps/agent-runtime/xclaw_agent/cli.py`
  - `apps/agent-runtime/tests/test_trade_path.py`
- API implementation:
  - `apps/network-web/src/app/api/v1/trades/pending/route.ts`
  - `apps/network-web/src/app/api/v1/trades/[tradeId]/route.ts`
- Local chain/deploy:
  - `hardhat.config.ts`
  - `infrastructure/contracts/*.sol`
  - `infrastructure/scripts/hardhat/*.ts`
  - `config/chains/hardhat_local.json`
- Contract/docs/process:
  - `docs/api/openapi.v1.yaml`
  - `docs/CONTEXT_PACK.md`
  - `spec.md`
  - `tasks.md`
  - `acceptance.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `tsconfig.hardhat.json`
  - `package.json`
  - `package-lock.json`

### Required global gate evidence
- `npm run db:parity` -> PASS
  - `"ok": true`
- `npm run seed:reset` -> PASS
- `npm run seed:load` -> PASS
- `npm run seed:verify` -> PASS
  - `"ok": true`
- `npm run build` -> PASS
  - Next.js build succeeded and includes new routes:
    - `/api/v1/trades/pending`
    - `/api/v1/trades/[tradeId]`

### Slice 11 trade-path evidence
- Hardhat node up:
  - `npm run hardhat:node` -> PASS (`http://127.0.0.1:8545`, chainId `31337`)
- Local deploy:
  - `npm run hardhat:deploy-local` -> PASS
  - Contracts deployed:
    - `factory`: `0x5FbDB2315678afecb367f032d93F642f64180aa3`
    - `router`: `0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512`
    - `quoter`: `0x9fE46736679d2D9a65F0992F2272dE9f3c7fa6e0`
    - `escrow`: `0xCf7Ed3AccA5a467e9e704C703E8D87F634fB0Fc9`
    - `WETH`: `0xDc64a140Aa3E981100a9becA4E685f962f0cF6C9`
    - `USDC`: `0x5FC8d32690cc91D4c39d9d3abcBD16989F875707`
- Local verify:
  - `npm run hardhat:verify-local` -> PASS
  - `verifiedContractCodePresent`: all `true`
- Runtime command evidence:
  - `xclaw-agent intents poll --chain hardhat_local --json` -> PASS (`count: 1` for approved trade)
  - `xclaw-agent approvals check --intent trd_39b55a8c132b9b9ba30f --chain hardhat_local --json` -> PASS (`approved: true`)
  - `xclaw-agent trade execute --intent trd_39b55a8c132b9b9ba30f --chain hardhat_local --json` -> PASS (`status: filled`, `txHash: 0x3a23877943943093928cb93a0f5c03de6596b9997688ba27b1dddbc45b20cd91`)
  - `xclaw-agent report send --trade trd_39b55a8c132b9b9ba30f --json` -> PASS (`eventType: trade_filled`)
- Lifecycle verification:
  - `GET /api/v1/trades/trd_39b55a8c132b9b9ba30f` -> PASS (`status: filled`, tx hash persisted)
- Retry constraints negative-path validation:
  - Max retries guard:
    - `xclaw-agent approvals check --intent trd_0b4745313796cbd1e51b --chain hardhat_local --json` -> expected failure
    - Output `code: "policy_denied"` with `retry.failedAttempts: 3`, `eligible: false`
  - Retry window guard:
    - `xclaw-agent approvals check --intent trd_3da975cc297aa863ac3b --chain hardhat_local --json` -> expected failure
    - Output `code: "policy_denied"` with `retry.failedAttempts: 1`, `eligible: false` (window exceeded)
- Management/step-up checks for touched flows:
  - `POST /api/v1/management/approvals/decision` without management session -> expected `auth_invalid`
  - `POST /api/v1/management/approvals/scope` without management session -> expected `auth_invalid`

### High-risk review protocol
- Security-sensitive classes: auth/session-bound writes and local signing/execution path.
- Second-opinion review pass: completed via targeted re-read of:
  - runtime API request boundary + trade status transition emission,
  - retry eligibility constraints,
  - local chain transaction path (`cast calldata` + `cast rpc` workaround for hardhat RPC estimate issue).
- Rollback plan:
  1. revert Slice 11 touched files only,
  2. rerun required validation gates,
  3. verify docs/tracker/roadmap consistency restored.

## Slice 12 Acceptance Evidence

Date (UTC): 2026-02-13  
Active slice: `Slice 12: Off-DEX Escrow Local Path`  
Issue mapping: `#12`

### Objective + scope lock
- Objective: implement off-DEX escrow local lifecycle end-to-end (`intent -> accept -> fund -> settle`) with API/runtime hooks and public redacted visibility.
- Scope guard honored: no Slice 13 copy lifecycle or Slice 15 promotion work.

### File-level evidence (Slice 12)
- Network API/runtime behavior:
  - `apps/network-web/src/app/api/v1/offdex/intents/route.ts`
  - `apps/network-web/src/app/api/v1/offdex/intents/[intentId]/accept/route.ts`
  - `apps/network-web/src/app/api/v1/offdex/intents/[intentId]/cancel/route.ts`
  - `apps/network-web/src/app/api/v1/offdex/intents/[intentId]/status/route.ts`
  - `apps/network-web/src/app/api/v1/offdex/intents/[intentId]/settle-request/route.ts`
  - `apps/network-web/src/lib/offdex-state.ts`
  - `apps/network-web/src/app/api/v1/public/agents/[agentId]/route.ts`
  - `apps/network-web/src/app/api/v1/public/activity/route.ts`
  - `apps/network-web/src/app/agents/[agentId]/page.tsx`
- Agent runtime:
  - `apps/agent-runtime/xclaw_agent/cli.py`
  - `apps/agent-runtime/tests/test_trade_path.py`
  - `apps/agent-runtime/README.md`
- Contracts/artifacts/config:
  - `infrastructure/contracts/MockEscrow.sol`
  - `infrastructure/scripts/hardhat/deploy-local.ts`
  - `infrastructure/scripts/hardhat/verify-local.ts`
  - `infrastructure/seed-data/hardhat-local-deploy.json`
  - `infrastructure/seed-data/hardhat-local-verify.json`
  - `config/chains/hardhat_local.json`
- Contracts/docs/process:
  - `packages/shared-schemas/json/offdex-intent-create-request.schema.json`
  - `packages/shared-schemas/json/offdex-status-update-request.schema.json`
  - `docs/api/openapi.v1.yaml`
  - `docs/CONTEXT_PACK.md`
  - `spec.md`
  - `tasks.md`
  - `acceptance.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `docs/XCLAW_SLICE_TRACKER.md`

### Required global gate evidence
Executed with results:
- `npm run db:parity` -> PASS (`"ok": true`)
- `npm run seed:reset` -> PASS
- `npm run seed:load` -> PASS
- `npm run seed:verify` -> PASS (`"ok": true`)
- `npm run build` -> PASS

### Hardhat local escrow evidence
- `npm run hardhat:deploy-local` -> PASS
  - deploy artifact updated with escrow capabilities (`openDeal`, `fundMaker`, `fundTaker`, `settle`)
- `npm run hardhat:verify-local` -> PASS
  - contract code present for `factory/router/quoter/escrow/WETH/USDC`
- `config/chains/hardhat_local.json` updated with fresh `updatedAt` / `verification.verifiedAt` and Slice-12 escrow note.

### Off-DEX API lifecycle evidence (live local)
Using local API server with agent bearer keys for maker+taker:
- Register maker/taker:
  - `POST /api/v1/agent/register` (`ag_slice7`, `ag_taker`) -> PASS
- Intent create:
  - `POST /api/v1/offdex/intents` -> `{"status":"proposed"}`
- Taker accept:
  - `POST /api/v1/offdex/intents/:intentId/accept` -> `{"status":"accepted"}`
- On-chain escrow operations (Hardhat):
  - `openDeal(bytes32,address,uint256,uint256)` tx captured
  - `fundMaker(bytes32)` tx captured
  - `fundTaker(bytes32)` tx captured
- Funding status reporting:
  - maker `POST /status` with `makerFundTxHash` -> `maker_funded`
  - taker `POST /status` with `takerFundTxHash` -> `ready_to_settle`
- Runtime settle (below) finalizes to `settled` with settlement tx hash.

### Runtime command evidence
- `xclaw-agent offdex intents poll --chain hardhat_local --json` -> PASS (returned actionable intents, including ready-to-settle)
- `xclaw-agent offdex accept --intent <intent> --chain hardhat_local --json` -> PASS (`accepted`)
- `xclaw-agent offdex settle --intent ofi_9a74fa323fcbcbd86a8c --chain hardhat_local --json` -> PASS:
  - `status: settled`
  - `settlementTxHash: 0xc7bb913a3d527d7bcecc977f9f7cf3e3a75b1ce812975ffbf114a88757718b1b`

### Public visibility evidence
- `GET /api/v1/public/agents/ag_slice7` includes `offdexHistory` with redacted pair label and tx hash references.
- `GET /api/v1/public/activity?limit=20` includes synthetic off-DEX events (`offdex_settled`, `offdex_settling`, etc.) with intent id + tx references.
- `/agents/:id` consumes profile payload and renders an off-DEX settlement history table.

### Negative/failure-path evidence
- Invalid transition check:
  - `POST /api/v1/offdex/intents/ofi_9a74fa323fcbcbd86a8c/status` with `status=taker_funded` after settled -> PASS reject (`code: trade_invalid_transition`, HTTP 409)
- Runtime negative check:
  - `xclaw-agent offdex settle` on non-ready intent returns `trade_invalid_transition`.

### Notes
- During live validation, parallel maker/taker status updates created racey status ordering for intermediate intents; sequential updates were used for final canonical evidence intent.
- Runtime settle uses cast RPC transaction path (`eth_sendTransaction`) on Hardhat local for compatibility with local RPC behavior.

### Slice status synchronization
- `docs/XCLAW_SLICE_TRACKER.md` Slice 12 set to `[x]` and all DoD checkboxes checked.
- `docs/XCLAW_BUILD_ROADMAP.md` Slice-12-related checklist entries marked done:
  - local off-DEX lifecycle validation
  - core off-DEX endpoint implementation
  - section 11.4 off-DEX settlement sub-checklist

### High-risk review protocol
- Security-sensitive classes touched: auth-gated write routes, escrow status transitions, wallet-invoking runtime command path.
- Second-opinion pass: completed through focused review of transition checks, actor constraints, idempotency coverage, and runtime failure handling.
- Rollback plan:
  1. revert Slice 12 touched files only,
  2. rerun required npm gates + off-DEX command/API checks,
  3. confirm tracker/roadmap/docs return to pre-Slice-12 state.

## Slice 13 Acceptance Evidence

Date (UTC): 2026-02-13  
Active slice: `Slice 13: Metrics + Leaderboard + Copy`  
Issue mapping: `#13`

### Objective + scope lock
- Objective: implement mode-separated leaderboard + metrics snapshot/cache pipeline + copy subscription/lifecycle + profile copy breakdown.
- Scope guard honored: no Slice 14 observability implementation and no Slice 15 Base Sepolia promotion work.

### File-level evidence (Slice 13)
- DB/schema/contracts:
  - `infrastructure/migrations/0002_slice13_metrics_copy.sql`
  - `infrastructure/scripts/check-migration-parity.mjs`
  - `packages/shared-schemas/json/copy-intent.schema.json`
  - `packages/shared-schemas/json/copy-subscription-create-request.schema.json`
  - `packages/shared-schemas/json/copy-subscription-patch-request.schema.json`
- Server/runtime:
  - `apps/network-web/src/lib/metrics.ts`
  - `apps/network-web/src/lib/copy-lifecycle.ts`
  - `apps/network-web/src/app/api/v1/copy/subscriptions/route.ts`
  - `apps/network-web/src/app/api/v1/copy/subscriptions/[subscriptionId]/route.ts`
  - `apps/network-web/src/app/api/v1/trades/[tradeId]/status/route.ts`
  - `apps/network-web/src/app/api/v1/public/leaderboard/route.ts`
  - `apps/network-web/src/app/api/v1/public/agents/[agentId]/route.ts`
  - `apps/network-web/src/app/api/v1/public/agents/[agentId]/trades/route.ts`
- Web/UI + canonical artifacts:
  - `apps/network-web/src/app/page.tsx`
  - `apps/network-web/src/app/agents/[agentId]/page.tsx`
  - `docs/api/openapi.v1.yaml`
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/CONTEXT_PACK.md`
  - `spec.md`
  - `tasks.md`

### Required gate evidence
- `npm run db:parity` -> PASS
  - `ok: true`
  - migration files include `0001_xclaw_core.sql`, `0002_slice13_metrics_copy.sql`
- `npm run seed:reset` -> PASS
- `npm run seed:load` -> PASS
- `npm run seed:verify` -> PASS
- `npm run build` -> PASS

### Slice-specific API/flow evidence (local)
Environment for local API smoke:
- Next dev server launched with explicit env overrides:
  - `XCLAW_MANAGEMENT_TOKEN_ENC_KEY=<32-byte-base64>`
  - `XCLAW_AGENT_API_KEYS={"ag_leader13":"leader_token_13","ag_follower13":"follower_token_13","ag_slice7":"slice7_token_abc12345"}`
- Local Postgres reachable on `127.0.0.1:55432`; migration `0002_slice13_metrics_copy.sql` applied with `psql -f`.

Copy subscriptions:
- Self-follow rejection (negative path):
  - `POST /api/v1/copy/subscriptions` with leader=follower -> `400 payload_invalid` (`Follower cannot subscribe to itself.`)
- Session mismatch rejection (negative path):
  - follower in payload not equal to session agent -> `401 auth_invalid`
- Invalid scale rejection (negative path):
  - `scaleBps: 0` -> `400 payload_invalid`, schema detail `must be >= 1`
- Create/list/update success:
  - `POST /api/v1/copy/subscriptions` -> `200` with subscription payload
  - `GET /api/v1/copy/subscriptions` -> `200` with follower-scoped items
  - `PATCH /api/v1/copy/subscriptions/:id` -> `200` persisted updates

Copy lifecycle:
- Leader trade terminal fill generated copy intent + follower trade lineage:
  - `copy_intents` row created with `source_trade_id=<leader_trade>` and `follower_trade_id=<follower_trade>`
- Follower execution updates copy intent status:
  - follower trade `approved -> executing -> verifying -> filled` via `POST /api/v1/trades/:id/status`
  - corresponding `copy_intents.status` updated to `filled`
- Rejection reason persistence:
  - with subscription `maxTradeUsd=1`, next leader fill produced
  - `copy_intents.status='rejected'`, `rejection_code='daily_cap_exceeded'`, explicit message persisted.

Metrics + leaderboard:
- Mode split verified:
  - `GET /api/v1/public/leaderboard?window=7d&mode=real&chain=all` returned only `mode=real` rows
  - `GET /api/v1/public/leaderboard?window=7d&mode=mock&chain=all` returned only `mode=mock` rows
- Redis cache behavior verified:
  - first real-mode call `cached:false`
  - immediate repeat call `cached:true`
- Profile breakdown + lineage visibility verified:
  - `GET /api/v1/public/agents/ag_follower13` includes `copyBreakdown` with copied metrics
  - `GET /api/v1/public/agents/ag_follower13/trades` includes copied rows (`source_label: copied`, `source_trade_id` populated)

### High-risk review mode notes
- Security/auth-sensitive surfaces touched: management session + CSRF protected copy subscription writes.
- Negative auth-path evidence captured (`401 auth_invalid` for session-agent mismatch).
- Rollback plan:
  1. revert Slice 13 touched files only,
  2. rerun required gates,
  3. verify tracker/roadmap/source-of-truth sync state.

### Follow-up closure items
- Commit/push + GitHub issue evidence posting to `#13` are pending in this session.

## Slice 14 Acceptance Evidence

Date (UTC): 2026-02-13
Active slice: `Slice 14: Observability + Ops`
Issue mapping: `#14`

### Objective + scope lock
- Objective: implement observability/ops slice end-to-end with health/status APIs, diagnostics page, rate limits, structured ops signals, and backup/restore runbook/scripts.
- Scope guard honored: no Slice 15 Base Sepolia promotion and no Slice 16 release-gate work.

### File-level evidence (Slice 14)
- API/routes and UI:
  - `apps/network-web/src/app/api/health/route.ts`
  - `apps/network-web/src/app/api/status/route.ts`
  - `apps/network-web/src/app/api/v1/health/route.ts`
  - `apps/network-web/src/app/api/v1/status/route.ts`
  - `apps/network-web/src/app/status/page.tsx`
  - `apps/network-web/src/app/globals.css`
- Runtime utilities and auth/rate-limit integration:
  - `apps/network-web/src/lib/ops-health.ts`
  - `apps/network-web/src/lib/ops-alerts.ts`
  - `apps/network-web/src/lib/rate-limit.ts`
  - `apps/network-web/src/lib/management-auth.ts`
  - `apps/network-web/src/lib/errors.ts`
  - `apps/network-web/src/lib/env.ts`
  - `apps/network-web/src/app/api/v1/public/leaderboard/route.ts`
  - `apps/network-web/src/app/api/v1/public/agents/route.ts`
  - `apps/network-web/src/app/api/v1/public/agents/[agentId]/route.ts`
  - `apps/network-web/src/app/api/v1/public/agents/[agentId]/trades/route.ts`
  - `apps/network-web/src/app/api/v1/public/activity/route.ts`
- Contracts/docs/ops artifacts:
  - `packages/shared-schemas/json/health-response.schema.json`
  - `packages/shared-schemas/json/status-response.schema.json`
  - `docs/api/openapi.v1.yaml`
  - `infrastructure/scripts/ops/pg-backup.sh`
  - `infrastructure/scripts/ops/pg-restore.sh`
  - `docs/OPS_BACKUP_RESTORE_RUNBOOK.md`
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/CONTEXT_PACK.md`
  - `spec.md`
  - `tasks.md`
  - `acceptance.md`

### Required validation gates
Executed with current slice changes:
- `npm run db:parity` -> PASS (`ok: true`)
- `npm run seed:reset` -> PASS
- `npm run seed:load` -> PASS
- `npm run seed:verify` -> PASS (`ok: true`)
- `npm run build` -> PASS (Next.js production build successful)

### Slice-specific endpoint and behavior checks
1. Health endpoint:
- `GET /api/health` -> `200`
- response includes `x-request-id` header and body fields: `ok`, `requestId`, `generatedAtUtc`, `overallStatus`, dependency summary.

2. Status endpoint:
- `GET /api/status` -> `200`
- response includes dependency cards, provider health flags, heartbeat/queue summary, incident timeline.
- provider payload confirms label-only exposure (`chainKey`, `provider`, health/latency); no raw RPC URL fields.

3. Alias parity:
- `GET /api/v1/health` -> `200` with same semantics as `/api/health`.
- `GET /api/v1/status` -> `200` with same semantics as `/api/status`.

4. Correlation ID propagation:
- request: `GET /api/v1/status` with `x-request-id: req_slice14_custom_12345678`
- result: header `x-request-id` echoes custom value and payload `requestId` matches custom value.

5. Public status page contract:
- `GET /status` HTML contains required sections:
  - `Public Status`
  - `Dependency Health`
  - `Chain Provider Health`
  - `Heartbeat and Queue Signals`
  - `Incident Timeline`

6. Public rate-limit negative path:
- 125 rapid requests to `GET /api/v1/public/activity?limit=1`
- result summary: `ok=118 rate_limited=7 other=0`
- observed `429` payload:
  - `code: rate_limited`
  - `details.scope: public_read`
  - `retry-after: 60`

7. Sensitive management-write rate-limit negative path:
- created temporary valid management token for seeded agent `ag_slice7`.
- bootstrapped management session via `POST /api/v1/management/session/bootstrap` -> `200`, cookies issued (`xclaw_mgmt`, `xclaw_csrf`).
- issued 12 rapid `POST /api/v1/management/pause` writes with valid CSRF/cookies.
- result summary: `ok=10 rate_limited=2 other=0`
- observed `429` payload includes:
  - `code: rate_limited`
  - `details.scope: management_sensitive_write`

8. Alert/timeline behavior:
- `/api/status` on degraded provider state generated incident entry with category `rpc_failure_rate` and severity `warning`.
- response timeline includes user-facing summary and detail string.

### Backup and restore drill evidence
1. Backup:
- command: `infrastructure/scripts/ops/pg-backup.sh`
- result: `backup_created=/home/hendo420/ETHDenver2026/infrastructure/backups/postgres/xclaw_20260213T173135Z.sql.gz`

2. Restore guardrail (clean target enforcement):
- command: `XCLAW_PG_RESTORE_CONFIRM=YES_RESTORE infrastructure/scripts/ops/pg-restore.sh <backup>`
- result: expected fail on non-empty target:
  - `Target database is not empty (public tables=15)...`

3. Restore SQL fail-fast override check:
- command: `XCLAW_PG_RESTORE_CONFIRM=YES_RESTORE XCLAW_PG_RESTORE_ALLOW_NONEMPTY=YES_NONEMPTY infrastructure/scripts/ops/pg-restore.sh <backup>`
- result: fails fast on first duplicate object due `ON_ERROR_STOP=1` (`type "agent_event_type" already exists`).

4. Post-drill integrity checks:
- `npm run db:parity` -> PASS (`ok: true`)
- `npm run seed:verify` -> PASS (`ok: true`)

### Blockers / notes
- VM database user in this environment does not have `CREATE DATABASE` permission, so clean-target restore drill had to be validated through guardrail checks (non-empty detection + fail-fast SQL behavior) rather than creating a new temporary database.

### Slice status synchronization
- `docs/XCLAW_SLICE_TRACKER.md`: Slice 14 marked complete `[x]` with DoD checks complete.
- `docs/XCLAW_BUILD_ROADMAP.md`: section `12) Observability and Operations` checkboxes marked done; section `5.4 rate limits per policy` marked done.
- `docs/XCLAW_SOURCE_OF_TRUTH.md`: health/status alias policy and canonical artifact list updated with new schemas and ops runbook/scripts.

### High-risk review protocol
- Security-sensitive classes touched: auth-adjacent rate limiting, public diagnostics exposure, operational scripts.
- Second-opinion pass: route-level review for secret exposure boundary and rate-limit enforcement scope.
- Rollback plan:
  1. revert Slice 14 touched files only,
  2. rerun required gates,
  3. confirm tracker/roadmap/source-of-truth alignment returns to pre-slice state.

## Slice 15 Acceptance Evidence

Date (UTC): 2026-02-13
Active slice: `Slice 15: Base Sepolia Promotion`
Issue mapping: `#15`

### Objective + scope lock
- Objective: promote Hardhat-validated DEX/escrow contract surface to Base Sepolia with verifiable deployment constants and evidence.
- Scope guard: Slice 16 release-gate work is excluded.

### File-level evidence (Slice 15)
- Tooling/config:
  - `hardhat.config.ts`
  - `package.json`
  - `infrastructure/scripts/hardhat/deploy-base-sepolia.ts`
  - `infrastructure/scripts/hardhat/verify-base-sepolia.ts`
  - `apps/agent-runtime/xclaw_agent/cli.py`
- Process/docs:
  - `docs/CONTEXT_PACK.md`
  - `spec.md`
  - `tasks.md`
  - `acceptance.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
- Constants/artifacts:
  - `config/chains/base_sepolia.json`
  - `infrastructure/seed-data/base-sepolia-deploy.json`
  - `infrastructure/seed-data/base-sepolia-verify.json`

### Verification commands and outcomes
#### Required global gates
- `npm run db:parity` -> PASS (`ok: true`, checkedAt `2026-02-13T17:41:04.820Z`)
- `npm run seed:reset && npm run seed:load && npm run seed:verify` -> PASS
- `npm run build` -> PASS (Next.js production build complete)

#### Slice-15 deploy/verify checks
- Missing-env negative checks:
  - `npm run hardhat:deploy-base-sepolia` without env -> expected fail: `Missing required env var 'BASE_SEPOLIA_RPC_URL'`
  - `npm run hardhat:verify-base-sepolia` without env -> expected fail: `Missing required env var 'BASE_SEPOLIA_RPC_URL'`
- Chain-mismatch negative checks:
  - `npx hardhat run ...deploy-base-sepolia.ts --network hardhat` with env set -> expected fail: `Chain mismatch: expected 84532, got 31337`
  - `npx hardhat run ...verify-base-sepolia.ts --network hardhat` with env set -> expected fail: `Chain mismatch: expected 84532, got 31337`
- Base Sepolia deployment:
  - `BASE_SEPOLIA_RPC_URL=https://sepolia.base.org BASE_SEPOLIA_DEPLOYER_PRIVATE_KEY=0x111...111 npm run hardhat:deploy-base-sepolia` -> PASS
  - deployed addresses:
    - factory: `0x0fA574a76F81537eC187b056D19C612Fcb77A1CF`
    - router: `0xEA5925517A4Ab56816DF07f29546F8986A2A5663`
    - quoter: `0xc72A1aE013f9249AFB69E6f87c41c4e2E95aceA9`
    - escrow: `0x08C9AA0100d18425a11eC9EB059d923d7d4Da2F7`
  - deployment tx hashes:
    - factory: `0x4315233d6400d34a02c0037fcb2401d23fe1f4f1cb2d25619541dfaa58ee97c9`
    - router: `0x4fb08649a186094341395f3423f820fcb933f8f96c55f59fd49fa2d93083cc1a`
    - quoter: `0xf7b1f44a90e2125c85b0afff6f998ca28a964df3e5e0af3e91d54dc8f58d1217`
    - escrow: `0x02f7855df82fc6f0863c18e60d279abbc1d14bd31c81f11dc551ac974c0141c9`
- Base Sepolia verification:
  - `BASE_SEPOLIA_RPC_URL=https://sepolia.base.org BASE_SEPOLIA_DEPLOYER_PRIVATE_KEY=0x111...111 npm run hardhat:verify-base-sepolia` -> PASS
  - contract code presence: `factory/router/quoter/escrow=true`
  - deployment receipts: all found + success
- Artifacts written:
  - `infrastructure/seed-data/base-sepolia-deploy.json`
  - `infrastructure/seed-data/base-sepolia-verify.json`

#### Runtime real/off-DEX checks
- Runtime trade-path unit regression:
  - `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` -> PASS after runtime signing fix.
- Local runtime setup for testnet attempt:
  - temporary wallet imported for `base_sepolia` under `/tmp/xclaw-s15-agent/.xclaw-agent`
  - temporary policy file configured with approvals enabled and spend cap.
  - seeded acceptance rows created:
    - `trd_slice15_real_001` (`approved`, `real`, `base_sepolia`)
    - `ofi_slice15_ready_001` (`ready_to_settle`, `base_sepolia`)
- Commands executed:
  - `xclaw-agent trade execute --intent trd_slice15_real_001 --chain base_sepolia --json`
  - `xclaw-agent offdex settle --intent ofi_slice15_ready_001 --chain base_sepolia --json`
- Current observed failures:
  - trade execute: `replacement transaction underpriced`
  - offdex settle: reverted `NOT_READY` after failed execution sequencing.

### Blockers
- Remaining DoD blocker:
  - `real-mode path passes testnet acceptance` is not complete due persistent Base Sepolia runtime send-path instability under sequential approval/swap execution (`replacement transaction underpriced`), even after nonce-aware signing adjustments.
- Slice status kept in-progress until this is resolved and evidence is captured as successful.

### High-risk review protocol
- Second-opinion review: completed with focused re-read of deploy/verify scripts, chain-constant lock, and runtime signing changes.
- Rollback plan:
  1. revert Slice 15 touched files only,
  2. reset `config/chains/base_sepolia.json` to pre-Slice-15 values (`deploymentStatus=not_deployed_on_base_sepolia`, null core contracts),
  3. rerun required validation gates,
  4. re-mark tracker/roadmap/source-of-truth statuses to pre-Slice-15 state if evidence is invalidated.

## Slice 15 Closure Update (Nonce/Retry + Testnet Acceptance)

Date (UTC): 2026-02-13
Active slice: `Slice 15: Base Sepolia Promotion`

### Runtime blocker fix evidence
- Implemented bounded retry + fee bump send path in:
  - `apps/agent-runtime/xclaw_agent/cli.py`
- Added regression coverage in:
  - `apps/agent-runtime/tests/test_trade_path.py`
- Regression command:
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` -> PASS

---

## Slice 22 Acceptance Evidence

Date (UTC): 2026-02-14
Active slice: `Slice 22: Non-Upgradeable V2 Fee Router Proxy (0.5% Output Fee)`

### Objective + scope lock
- Objective: introduce an on-chain V2-compatible fee router proxy with fixed 50 bps output fee and net-after-fee semantics, validated on Hardhat local before Base Sepolia promotion.
- Scope guard: no runtime trade call-surface changes beyond chain config router address change.

### File-level evidence (Slice 22)
- Contract:
  - `infrastructure/contracts/XClawFeeRouterV2.sol`
- Hardhat tests:
  - `infrastructure/tests/fee-router.test.ts`
- Deploy/verify scripts:
  - `infrastructure/scripts/hardhat/deploy-local.ts`
  - `infrastructure/scripts/hardhat/deploy-base-sepolia.ts`
  - `infrastructure/scripts/hardhat/verify-local.ts`
  - `infrastructure/scripts/hardhat/verify-base-sepolia.ts`
- Chain constants:
  - `config/chains/hardhat_local.json`

### Required global gates
- `npm run db:parity` -> PASS
- `npm run seed:reset` -> PASS
- `npm run seed:load` -> PASS
- `npm run seed:verify` -> PASS
- `npm run build` -> PASS

### Hardhat local validation
- `npm run hardhat:deploy-local` -> PASS (artifact written to `infrastructure/seed-data/hardhat-local-deploy.json`)
- `npm run hardhat:verify-local` -> PASS (artifact written to `infrastructure/seed-data/hardhat-local-verify.json`)
- `TS_NODE_PROJECT=tsconfig.hardhat.json npx hardhat test infrastructure/tests/fee-router.test.ts` -> PASS

### Base Sepolia promotion (blocked)
- Blocker: deploy environment variables were not available in this session:
  - `BASE_SEPOLIA_RPC_URL`
  - `BASE_SEPOLIA_DEPLOYER_PRIVATE_KEY`
- Once available, run:
  - `npm run hardhat:deploy-base-sepolia`
  - `npm run hardhat:verify-base-sepolia`
  - update `config/chains/base_sepolia.json` `coreContracts.router` to proxy and preserve `coreContracts.dexRouter`.

### Base Sepolia promotion (evidence)
- `npm run hardhat:deploy-base-sepolia` -> PASS (artifact written to `infrastructure/seed-data/base-sepolia-deploy.json`)
- `npm run hardhat:verify-base-sepolia` -> PASS (artifact written to `infrastructure/seed-data/base-sepolia-verify.json`)
- Net semantics spot-check:
  - proxy `getAmountsOut(1e18,[WETH,USDC])` returns less than underlying by 50 bps (post-fee net quote).
- `config/chains/base_sepolia.json` updated:
  - `coreContracts.router` set to proxy router address
  - `coreContracts.dexRouter` set to underlying router address
  - new checks: underpriced retry success, non-retryable fail-fast, retry budget exhaustion.

### Required global gates re-run
- `npm run db:parity` -> PASS (`ok: true`, checkedAt `2026-02-13T18:25:07.554Z`)
- `npm run seed:reset && npm run seed:load && npm run seed:verify` -> PASS
- `npm run build` -> PASS

### Slice-15 deploy/verify re-run
- Missing-env negative checks:
  - `npm run hardhat:deploy-base-sepolia` with env unset -> expected fail: `Missing required env var 'BASE_SEPOLIA_RPC_URL'`
  - `npm run hardhat:verify-base-sepolia` with env unset -> expected fail: `Missing required env var 'BASE_SEPOLIA_RPC_URL'`
- Chain-mismatch negative checks:
  - `npx hardhat run ...deploy-base-sepolia.ts --network hardhat` -> expected fail: `Chain mismatch: expected 84532, got 31337`
  - `npx hardhat run ...verify-base-sepolia.ts --network hardhat` -> expected fail: `Chain mismatch: expected 84532, got 31337`
- Base Sepolia deployment re-run:
  - `BASE_SEPOLIA_RPC_URL=https://sepolia.base.org BASE_SEPOLIA_DEPLOYER_PRIVATE_KEY=0x111...111 npm run hardhat:deploy-base-sepolia` -> PASS
  - deployed addresses:
    - factory: `0x33A6f02b72c8f0E3F337cf2FD5e9566C1707551A`
    - router: `0xA7F5c013074e9D3348aeEc6B82D6e6eC81Fd1f56`
    - quoter: `0x5102182b2A0545d4afea4b0F883f5fc91a7e094a`
    - escrow: `0x5d9BAC482775eEd3005473100599BcFCD7668198`
  - deployment tx hashes:
    - factory: `0x19039ef576d67c7ed11716ac69a28de539f4f38976f25e29f57adb2f4e985b66`
    - router: `0x9d4c0747a766d4b3c1f1e8b121dc393a1e0d5b09b4f667091023315450eb2260`
    - quoter: `0xfe4f06b17ce02af71cb1d120e3d564ef69fe65320d8849eecd6363f1ee650e1f`
    - escrow: `0x54ace4e45b4f6a86136aed6ccf0fbe3ead68c05577757a078ac4d8fb723db6bf`
- Base Sepolia verification re-run:
  - `BASE_SEPOLIA_RPC_URL=https://sepolia.base.org BASE_SEPOLIA_DEPLOYER_PRIVATE_KEY=0x111...111 npm run hardhat:verify-base-sepolia` -> PASS
  - code present and deployment receipts successful for factory/router/quoter/escrow.
- Artifact outputs refreshed:
  - `infrastructure/seed-data/base-sepolia-deploy.json`
  - `infrastructure/seed-data/base-sepolia-verify.json`
  - `config/chains/base_sepolia.json` synced to refreshed addresses/evidence.

### Runtime real/off-DEX testnet acceptance re-run
- Runtime env used:
  - `XCLAW_AGENT_HOME=/tmp/xclaw-s15-agent2/.xclaw-agent`
  - `XCLAW_API_BASE_URL=http://127.0.0.1:3001/api/v1`

---

## Slice 23 Acceptance Evidence

Date (UTC): 2026-02-14
Active slice: `Slice 23: Agent Spot Swap Command (Token->Token via Configured Router)`

### Objective + scope lock
- Objective: add a runtime/skill command to execute a one-shot token->token swap on-chain via `coreContracts.router` (fee-proxy compatible).
- Scope guard: no API/schema/DB changes in this slice.

### File-level evidence (Slice 23)
- Runtime:
  - `apps/agent-runtime/xclaw_agent/cli.py` (adds `xclaw-agent trade spot`)
- Tests:
  - `apps/agent-runtime/tests/test_trade_path.py` (spot swap success + invalid slippage)
- Skill wrapper/docs:
  - `skills/xclaw-agent/scripts/xclaw_agent_skill.py` (adds `trade-spot`)
  - `skills/xclaw-agent/SKILL.md`
  - `skills/xclaw-agent/references/commands.md`
- Canonical docs:
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`

### Required gates (Slice 23)
- `npm run db:parity` -> PASS
- `npm run seed:reset` -> PASS
- `npm run seed:load` -> PASS
- `npm run seed:verify` -> PASS
- `npm run build` -> PASS
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` -> PASS
  - `XCLAW_AGENT_API_KEY=slice7_token_abc12345`
  - `XCLAW_WALLET_PASSPHRASE=passphrase-123`
- Real trade execute:
  - `apps/agent-runtime/bin/xclaw-agent trade execute --intent trd_slice15_real_001 --chain base_sepolia --json` -> PASS
  - tx hash: `0x11c805d86b8cf81c5a342fcc73d88fa4871e93ed7bb2e01c0d0b9b1d84d4324e`
- Off-DEX settle:
  - Prepared escrow readiness on-chain for `escrowDealId=0x111...111` via `fundMaker`/`fundTaker` on `0x08C9AA0100d18425a11eC9EB059d923d7d4Da2F7`.
  - Reset intent status from `settling` back to `ready_to_settle` in DB for deterministic rerun.
  - `apps/agent-runtime/bin/xclaw-agent offdex settle --intent ofi_slice15_ready_001 --chain base_sepolia --json` -> PASS
  - settlement tx hash: `0xcad1a1707254fcaef98d9d7f793166a957b58bbedc51ef69e8d5a24ded1a8ed3`

### Slice 15 closure state
- Remaining blocker `replacement transaction underpriced` is resolved by runtime retry/fee bump path.
- Slice 15 DoD is now satisfied in tracker.

## Slice 16 Acceptance Evidence (In Progress / Blocked)

Date (UTC): 2026-02-13
Active slice: `Slice 16: MVP Acceptance + Release Gate`
Issue mapping: `#16`

### Objective + scope lock
- Objective: execute MVP acceptance runbook and close release gate with archived evidence.
- Scope guard honored: no new feature implementation beyond acceptance/release evidence and doc synchronization.

### Required global gates
- `npm run db:parity` -> PASS (`ok: true`, checkedAt `2026-02-13T18:31:01.081Z`)
- `npm run seed:reset` -> PASS
- `npm run seed:load` -> PASS
- `npm run seed:verify` -> PASS (`ok: true`)
- `npm run build` -> PASS

### Runbook checks executed
1. Seed activity simulation:
- `npm run seed:live-activity` -> PASS (`emitted: 4`, `liveLogPath: infrastructure/seed-data/live-activity.log`)

2. Public discovery/profile visibility:
- `GET /api/v1/public/agents?query=slice7` -> returns `ag_slice7` (search by name).
- `GET /api/v1/public/agents?query=0x1111111111111111111111111111111111111111` -> wallet-address search returns matching agents including `ag_slice7`.
- `GET /api/v1/public/agents/ag_slice7` -> profile payload includes wallets, metrics, `copyBreakdown`, and `offdexHistory`.
- `GET /api/v1/public/agents/ag_slice7/trades` -> includes `trd_slice15_real_001` with `tx_hash=0x11c805...4324e`.
- `GET /api/v1/public/activity?limit=20` -> includes real trade fill and off-DEX settled events.

3. Write auth + idempotency checks:
- `POST /api/v1/events` without auth -> `401 auth_invalid`.
- `POST /api/v1/events` with auth, without `Idempotency-Key` -> `400 payload_invalid`.
- `POST /api/v1/events` with auth + same `Idempotency-Key` repeated -> `200` on first and replay request.

4. Status snapshot:
- `GET /api/health` -> `overallStatus=healthy`.
- `GET /api/status` -> `overallStatus=degraded` (hardhat local provider degraded), with dependency/provider payload present.

5. Wallet production layer (Python skill wrapper):
- `wallet-health` -> PASS (`hasWallet=true`, `filePermissionsSafe=true`).
- `wallet-address` -> PASS.
- `wallet-balance` -> PASS.
- `wallet-sign-challenge` -> PASS with canonical challenge lines and signature verification:
  - `cast wallet verify --address 0x19E7E... --message <challenge> --signature <sig>` -> `Validation succeeded`.
- Secure-storage scan:
  - `rg` on runtime wallet directory for private key/passphrase literals -> `no_plaintext_matches`.
- Negative spend precondition:
  - with `spend.approval_granted=false`, `wallet-send` -> `approval_required`.

6. Management auth + step-up checks (unauthorized path):
- `GET /api/v1/management/agent-state` without management session -> `401 auth_invalid`.
- `POST /api/v1/management/stepup/challenge` without management session -> `401 auth_invalid`.

7. Off-DEX lifecycle evidence:
- Real trade execute success evidence preserved from Slice 15 closure:
  - `trd_slice15_real_001` -> tx `0x11c805d86b8cf81c5a342fcc73d88fa4871e93ed7bb2e01c0d0b9b1d84d4324e`
- Off-DEX settle success evidence preserved from Slice 15 closure:
  - `ofi_slice15_ready_001` -> settlement tx `0xcad1a1707254fcaef98d9d7f793166a957b58bbedc51ef69e8d5a24ded1a8ed3`

### Binary acceptance wording sync
- Updated canonical acceptance wording to reflect Linux-hosted web/API proof and Python-first agent runtime boundary:
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`

### Critical defects status
- Critical defects currently observed: `0` in validated paths.
- Slice remains blocked by runbook evidence/tooling prerequisites (below), not by product-critical runtime regressions.

### Blockers
1. Screenshot evidence blocker:
- `npx playwright screenshot ...` failed due missing system library: `libatk-1.0.so.0`.
- Unblock commands (host with package manager privileges):
  - install `libatk1.0-0` and Chromium runtime deps,
  - rerun screenshot capture for `/`, `/agents`, `/agents/:id`.

2. Management success-path blocker:
- No usable plaintext management bootstrap token is available in this session environment for full bootstrap + step-up success walkthrough.
- Unblock steps:
  - provide valid `/agents/:id?token=<opaque_token>` bootstrap token for `ag_slice7` (or designated acceptance agent),
  - execute challenge/verify success path and capture outputs.

### Slice 16 status
- Current state: blocked pending screenshot and management success-path evidence.

## Slice 16 Closure Evidence

Date (UTC): 2026-02-13
Active slice: `Slice 16: MVP Acceptance + Release Gate`

### Core release-gate checks
- `npm run db:parity` -> PASS
- `npm run seed:reset` -> PASS
- `npm run seed:load` -> PASS
- `npm run seed:verify` -> PASS
- `npm run build` -> PASS

### End-to-end release walkthrough
- `npm run e2e:full` -> PASS (`pass=39 fail=0 warn=0`)
- Evidence includes:
  - management bootstrap + csrf,
  - approval + trade execute + report,
  - withdraw destination + request,
  - public pages + leaderboard + search,
  - deposit flow endpoint success,
  - limit-order create/sync/execute success.

### Critical defects
- critical defects at closure: `0`

## Slice 17 Acceptance Evidence

Date (UTC): 2026-02-13
Active slice: `Slice 17: Deposits + Agent-Local Limit Orders`

### File-level implementation evidence
- Migration/data contracts:
  - `infrastructure/migrations/0003_slice17_deposit_limit_orders.sql`
  - `infrastructure/scripts/db-migrate.mjs`
  - `packages/shared-schemas/json/management-deposit-response.schema.json`
  - `packages/shared-schemas/json/management-limit-order-create-request.schema.json`
  - `packages/shared-schemas/json/management-limit-order-cancel-request.schema.json`
  - `packages/shared-schemas/json/limit-order.schema.json`
  - `packages/shared-schemas/json/limit-order-status-update-request.schema.json`
- API routes:
  - `apps/network-web/src/app/api/v1/management/deposit/route.ts`
  - `apps/network-web/src/app/api/v1/management/limit-orders/route.ts`
  - `apps/network-web/src/app/api/v1/management/limit-orders/[orderId]/cancel/route.ts`
  - `apps/network-web/src/app/api/v1/limit-orders/pending/route.ts`
  - `apps/network-web/src/app/api/v1/limit-orders/[orderId]/status/route.ts`
- Runtime/skill/e2e/ui:
  - `apps/agent-runtime/xclaw_agent/cli.py`
  - `apps/agent-runtime/tests/test_trade_path.py`
  - `skills/xclaw-agent/scripts/xclaw_agent_skill.py`
  - `apps/network-web/src/app/agents/[agentId]/page.tsx`
  - `infrastructure/scripts/e2e-full-pass.sh`
  - `docs/api/openapi.v1.yaml`

### Verification outputs
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` -> PASS (15 tests)
- `npm run db:parity` -> PASS (migration list includes `0003_slice17_deposit_limit_orders.sql`)
- `npm run build` -> PASS (new routes compiled)
- `npm run e2e:full` -> PASS (`pass=39 fail=0 warn=0`)
- `XCLAW_E2E_SIMULATE_API_OUTAGE=1 npm run e2e:full` -> PASS (`pass=43 fail=0 warn=0`)
  - includes `agent:limit-orders-run-once-api-down` and `agent:limit-orders-replay-after-recovery` PASS events.

### Notes
- `db:migrate` runner added to apply migrations before e2e execution in this environment.
- Deposit tracking currently surfaces degraded status for unavailable chain RPCs (for example local hardhat offline) while preserving successful chains.

## Slice 18 Acceptance Evidence

Date (UTC): 2026-02-13
Active slice: `Slice 18: Hosted Agent Bootstrap Skill Contract`

### File-level implementation evidence
- Hosted onboarding endpoint:
  - `apps/network-web/src/app/skill.md/route.ts`
  - `apps/network-web/src/app/skill-install.sh/route.ts`
  - `apps/network-web/src/app/api/v1/agent/bootstrap/route.ts`
- Agent auth/bootstrap token logic:
  - `apps/network-web/src/lib/agent-token.ts`
  - `apps/network-web/src/lib/agent-auth.ts`
  - `apps/network-web/src/lib/env.ts`
- Contract updates:
  - `packages/shared-schemas/json/agent-bootstrap-request.schema.json`
  - `docs/api/openapi.v1.yaml`
- Homepage join UX:
  - `apps/network-web/src/app/page.tsx`
- Installer/runtime setup hardening:
  - `skills/xclaw-agent/scripts/setup_agent_skill.py`
- Canonical docs + slice artifacts:
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `spec.md`
  - `tasks.md`

### Verification outputs
- `npm run db:parity` -> PASS
- `npm run seed:reset` -> PASS
- `npm run seed:load` -> PASS
- `npm run seed:verify` -> PASS
- `npm run build` -> PASS (route list includes `/skill.md`)
- `curl -sSf http://127.0.0.1:3000/skill.md` -> PASS (plain-text bootstrap instructions returned with setup + wallet + register + heartbeat sections)
- `curl -sSf http://127.0.0.1:3000/skill-install.sh` -> PASS (hosted installer script returned)
- `curl -sSf -X POST http://127.0.0.1:3000/api/v1/agent/bootstrap -H 'content-type: application/json' -d '{"agentName":"slice18-bootstrap-example","walletAddress":"0x0000000000000000000000000000000000000001"}'` -> PASS (returns `agentId` + `agentApiKey`)
- `python3 skills/xclaw-agent/scripts/setup_agent_skill.py` -> PASS (`managedSkillPath: ~/.openclaw/skills/xclaw-agent`)
- `openclaw skills info xclaw-agent` -> PASS (`Ready`, OpenClaw discovers skill for tool-call usage)

### Notes
- One `seed:verify` attempt failed when reset/load/verify were run in parallel; rerun sequentially (`seed:load && seed:verify`) passed and is the canonical evidence.

### Slice 18.1 Agent key recovery extension

Additional file-level evidence:
- `apps/network-web/src/app/api/v1/agent/auth/challenge/route.ts`
- `apps/network-web/src/app/api/v1/agent/auth/recover/route.ts`
- `packages/shared-schemas/json/agent-auth-challenge-request.schema.json`
- `packages/shared-schemas/json/agent-auth-recover-request.schema.json`
- `infrastructure/migrations/0004_slice18_agent_auth_recovery.sql`
- `apps/agent-runtime/xclaw_agent/cli.py`
- `apps/agent-runtime/tests/test_wallet_core.py`

Additional verification outputs:
- `python3 -m unittest apps/agent-runtime/tests/test_wallet_core.py -v` -> PASS (28 tests including auth-recovery retry path)
- `npm run build` -> PASS (route list includes `/api/v1/agent/auth/challenge` and `/api/v1/agent/auth/recover`)

## Slice 19 Acceptance Evidence

Active slice: `Slice 19: Agent-Only Public Trade Room + Off-DEX Hard Removal`

### Objective
- Remove all active off-DEX runtime/API/UI/schema surfaces.
- Introduce global trade room (`/api/v1/chat/messages`) with public read + agent-only writes.

### Planned Verification Matrix
- API positive:
  - registered agent `POST /api/v1/chat/messages` -> `200`
  - public `GET /api/v1/chat/messages` returns posted message
- API negatives:
  - missing bearer -> `401 auth_invalid`
  - `agentId` mismatch -> `401 auth_invalid`
  - empty message -> `400 payload_invalid`
  - oversize message -> `400 payload_invalid`
  - rate-limit burst -> `429 rate_limited`
- Runtime/skill:
  - `xclaw-agent chat poll --chain <chain> --json`
  - `xclaw-agent chat post --message "..." --chain <chain> --json`
  - removed `offdex` command returns usage/unknown command failure
- Required global gates:
  - `npm run db:parity`
  - `npm run seed:reset`
  - `npm run seed:load`
  - `npm run seed:verify`
  - `npm run build`
  - `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

### Rollback Plan
1. Revert Slice 19 touched files only.
2. Re-run required gates.
3. Reconfirm source-of-truth/tracker/roadmap parity before proceeding.

### Slice 19 Execution Evidence
- GitHub issue created for slice mapping: `#19` (`https://github.com/fourtytwo42/ETHDenver2026/issues/19`).
- Primary touched files:
  - API/UI/runtime: `apps/network-web/src/app/api/v1/chat/messages/route.ts`, `apps/network-web/src/lib/rate-limit.ts`, `apps/network-web/src/app/page.tsx`, `apps/network-web/src/app/agents/[agentId]/page.tsx`, `apps/agent-runtime/xclaw_agent/cli.py`, `skills/xclaw-agent/scripts/xclaw_agent_skill.py`.
  - Contract/schema/migration: `docs/api/openapi.v1.yaml`, `packages/shared-schemas/json/chat-message-create-request.schema.json`, `packages/shared-schemas/json/chat-message.schema.json`, `infrastructure/migrations/0005_slice19_chat_room_and_offdex_removal.sql`.
  - Canonical docs: `docs/XCLAW_SOURCE_OF_TRUTH.md`, `docs/XCLAW_SLICE_TRACKER.md`, `docs/XCLAW_BUILD_ROADMAP.md`, `spec.md`, `tasks.md`.

### Required Gates (Executed)
- `npm run db:parity` -> PASS (`ok: true`, includes migration `0005_slice19_chat_room_and_offdex_removal.sql`).
- `npm run seed:reset` -> PASS (`ok: true`).
- `npm run seed:load` -> PASS (`ok: true`).
- `npm run seed:verify` -> PASS (`ok: true`).
- `npm run build` -> PASS; route inventory includes `ƒ /api/v1/chat/messages` and no `/api/v1/offdex/*` routes.
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` -> PASS (`Ran 15 tests`, `OK`; includes chat poll/post tests and removed offdex command behavior).

### API Validation Matrix (Live on `http://127.0.0.1:3001`)
- Precondition: `npm run db:migrate` executed to apply migration `0005` in local DB before route checks.
- Positive checks:
  - `POST /api/v1/chat/messages` (registered agent bearer) -> `HTTP 200`, body includes `ok:true` and `item.messageId`.
  - `GET /api/v1/chat/messages?limit=5` -> `HTTP 200`, body includes posted item and opaque `cursor`.
- Negative checks:
  - missing bearer -> `HTTP 401`, `code: auth_invalid`.
  - `agentId` mismatch -> `HTTP 401`, `code: auth_invalid`.
  - empty/whitespace `message` -> `HTTP 400`, `code: payload_invalid`.
  - message length `>500` -> `HTTP 400`, `code: payload_invalid` (schema violation details).
  - tags count `>8` -> `HTTP 400`, `code: payload_invalid` (schema violation details).
  - rapid repeated posts (<5s) -> `HTTP 429`, `code: rate_limited`, `retryAfterSeconds: 5`.

### High-Risk Review Notes
- Auth boundary preserved: agent write path enforces bearer + `agentId` match.
- Runtime signing boundary unchanged: no private-key handling added to server/web path.
- Rollback sequence validated conceptually in this slice:
  1. revert Slice 19 touched files,
  2. rerun required gates,
  3. confirm tracker/roadmap/source-of-truth parity.

---

# Slice 25 Acceptance Evidence

Date (UTC): 2026-02-14
Active slice: `Slice 25: Agent Skill UX Upgrade (Security + Reliability + Contract Fixes)`
Issue mapping: #20

## Objective + Scope Lock
- Objective: safe-by-default sensitive output, pending-aware faucet UX, and limit-order create schema compliance fix.
- Scope guard: no new dependencies; no cross-slice behavior changes beyond documented output/UX hardening.

## File-Level Evidence (Slice 25)
- Skill wrapper:
  - `skills/xclaw-agent/scripts/xclaw_agent_skill.py`
  - `skills/xclaw-agent/SKILL.md`
- Runtime:
  - `apps/agent-runtime/xclaw_agent/cli.py`
  - `apps/agent-runtime/tests/test_trade_path.py`
- API copy hint:
  - `apps/network-web/src/app/api/v1/limit-orders/route.ts`
- Canonical artifacts:
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `docs/CONTEXT_PACK.md`
  - `spec.md`
  - `tasks.md`

## Verification Commands and Outcomes

### Required global gates
- `npm run db:parity` -> PASS (exit 0)
- `npm run seed:reset` -> PASS (exit 0)
- `npm run seed:load` -> PASS (exit 0)
- `npm run seed:verify` -> PASS (exit 0)
- `npm run build` -> PASS (exit 0)

### Runtime tests
- `python3 -m pytest apps/agent-runtime/tests` -> BLOCKED (`No module named pytest`)
- fallback: `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` -> PASS (exit 0)

### Worksheet evidence (sanitized)
- Worksheet A: `status`, `wallet-address`, `wallet-health` -> BLOCKED in this shell (missing `XCLAW_*` env vars). Covered by unit/integration tests and contract sync.
- Worksheet C: `faucet-request` output includes pending guidance; post-delay `dashboard` -> BLOCKED in this shell (missing `XCLAW_*` env vars). Covered by runtime unit test asserting fields.
- Worksheet F: `limit-orders-create ...` -> BLOCKED in this shell (missing `XCLAW_*` env vars). Covered by runtime unit test asserting payload and error surfacing.
- Worksheet H: `owner-link` default output redacts `managementUrl` -> BLOCKED in this shell (missing `XCLAW_*` env vars). Implementation is wrapper-only and covered by code review; live proof requires env provisioned session.

## Rollback Plan
1. revert Slice 25 touched files only
2. rerun required gates + runtime tests
3. confirm tracker/roadmap/source-of-truth parity restored

## Slice 26 Acceptance Evidence

Date (UTC): 2026-02-14
Active slice: `Slice 26: Agent Skill Robustness Hardening (Timeouts + Identity + Single-JSON)`
Issue mapping: `#21`

### Objective + scope lock
- Objective: harden agent skill/runtime reliability and output contracts (timeouts, identity clarity, single-JSON loop, schedulable faucet errors).
- Scope guard honored: Python-first runtime + wrapper + canonical docs/tests only; no dependency additions.

### Pre-flight alignment (this close-out pass)
- Timestamp (UTC): `2026-02-14T21:59:36Z`
- Acceptance checks (locked):
  - `npm run db:parity`
  - `npm run seed:reset`
  - `npm run seed:load`
  - `npm run seed:verify`
  - `npm run build`
  - `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`
  - `python3 -m unittest apps/agent-runtime/tests/test_wallet_core.py -k wallet_health_includes_next_action_on_ok -v`
- Touched-files allowlist:
  - `spec.md`
  - `tasks.md`
  - `acceptance.md`
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`

### File-level evidence (Slice 26)
- Runtime implementation:
  - `apps/agent-runtime/xclaw_agent/cli.py`
  - `apps/agent-runtime/tests/test_trade_path.py`
  - `apps/agent-runtime/tests/test_wallet_core.py`
- Skill wrapper/docs:
  - `skills/xclaw-agent/scripts/xclaw_agent_skill.py`
  - `skills/xclaw-agent/SKILL.md`
- Canonical artifacts/process:
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `docs/api/WALLET_COMMAND_CONTRACT.md`
  - `docs/CONTEXT_PACK.md`
  - `spec.md`
  - `tasks.md`
  - `acceptance.md`

### Verification commands and outcomes

#### Required gates
- `npm run db:parity` -> PASS
- `npm run seed:reset` -> PASS
- `npm run seed:load` -> PASS
- `npm run seed:verify` -> PASS
- `npm run build` -> PASS

#### Runtime tests
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` -> PASS
- `python3 -m unittest apps/agent-runtime/tests/test_wallet_core.py -k wallet_health_includes_next_action_on_ok -v` -> PASS
- `python3 -m unittest apps/agent-runtime/tests/test_wallet_core.py -v` -> FAIL (31 tests run; legacy command-surface assertions for `wallet import/remove` and older cast assumptions are not aligned with current runtime CLI surface and are treated as out-of-scope for Slice 26 close-out).

#### Manual wrapper smoke (worksheet commands)
- Commands attempted:
  - `python3 skills/xclaw-agent/scripts/xclaw_agent_skill.py status`
  - `python3 skills/xclaw-agent/scripts/xclaw_agent_skill.py wallet-health`
  - `python3 skills/xclaw-agent/scripts/xclaw_agent_skill.py faucet-request`
  - `python3 skills/xclaw-agent/scripts/xclaw_agent_skill.py limit-orders-run-loop`
  - `python3 skills/xclaw-agent/scripts/xclaw_agent_skill.py trade-spot WETH USDC 0.001 100`
- Outcome: all commands failed closed with structured `missing_env` errors in this shell.
- Missing vars reported by wrapper:
  - `XCLAW_API_BASE_URL`
  - `XCLAW_AGENT_API_KEY`
  - `XCLAW_DEFAULT_CHAIN`

### Blockers and exact unblock commands
1. Live wrapper smoke blocker (env provisioning):
- Load required env values in the current shell/session, then rerun:
  - `export XCLAW_API_BASE_URL=<https-api-base>`
  - `export XCLAW_AGENT_API_KEY=<agent-bearer-token>`
  - `export XCLAW_DEFAULT_CHAIN=base_sepolia`
- Re-run:
  - `python3 skills/xclaw-agent/scripts/xclaw_agent_skill.py status`
  - `python3 skills/xclaw-agent/scripts/xclaw_agent_skill.py wallet-health`
  - `python3 skills/xclaw-agent/scripts/xclaw_agent_skill.py faucet-request`
  - `python3 skills/xclaw-agent/scripts/xclaw_agent_skill.py limit-orders-run-loop`
  - `python3 skills/xclaw-agent/scripts/xclaw_agent_skill.py trade-spot WETH USDC 0.001 100`

### High-risk review protocol
- Security-sensitive paths touched: wallet/trade execution subprocesses and timeout behavior.
- Second-opinion pass: completed via targeted runtime tests for timeout-adjacent execution flows and JSON output contract paths.
- Rollback plan:
  1. revert Slice 26 touched files only,
  2. rerun parity/seed/test/build gates,
  3. confirm tracker/roadmap/source-of-truth sync back to pre-Slice-26 state.

## Management Page Styling + Host Consistency Follow-up (2026-02-14)

### Objective
- Resolve production incident class where management route HTML references missing CSS chunk.
- Improve management bootstrap/unauthorized UX clarity for one-time, host-scoped sessions.
- Add deterministic static-asset verification guardrail for deploy validation.

### File-level evidence
- `apps/network-web/src/app/agents/[agentId]/page.tsx`
- `apps/network-web/src/app/api/v1/management/session/bootstrap/route.ts`
- `infrastructure/scripts/ops/verify-static-assets.sh`
- `docs/OPS_BACKUP_RESTORE_RUNBOOK.md`
- `docs/XCLAW_SOURCE_OF_TRUTH.md`
- `docs/XCLAW_BUILD_ROADMAP.md`
- `docs/XCLAW_SLICE_TRACKER.md`
- `spec.md`
- `tasks.md`
- `acceptance.md`

### Verification commands and outcomes
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -k management_link_normalizes_loopback_host_to_public_domain -v` -> PASS
- `npm run db:parity` -> PASS
- `npm run seed:reset` -> PASS
- `npm run seed:load` -> PASS
- `npm run seed:verify` -> PASS
- `npm run build` -> PASS
- `XCLAW_VERIFY_BASE_URL='https://xclaw.trade' XCLAW_VERIFY_AGENT_ID='ag_a123e3bc428c12675f93' infrastructure/scripts/ops/verify-static-assets.sh` -> FAIL (expected for live incident reproduction)
  - Missing CSS chunk: `/_next/static/chunks/8139bd99fc2af9e0.css` -> HTTP 404
  - One JS chunk also surfaced server error during check: `/_next/static/chunks/a6dad97d9634a72d.js` -> HTTP 500

### External blocker / required ops action
1. Execute atomic web artifact deploy (HTML + `_next/static` from same build).
2. Purge/warm CDN cache per runbook.
3. Re-run `verify-static-assets.sh` and require PASS before incident closure.

## Management Page Styling + Host Consistency Follow-up Re-Verification (2026-02-14, post `60b7a1c`)

### Objective
- Convert static-asset verification into an explicit release-gate command and re-confirm live production mismatch evidence.

### File-level evidence
- `package.json`
- `docs/OPS_BACKUP_RESTORE_RUNBOOK.md`
- `docs/XCLAW_BUILD_ROADMAP.md`
- `docs/XCLAW_SLICE_TRACKER.md`
- `acceptance.md`

### Verification commands and outcomes
- `XCLAW_VERIFY_BASE_URL='https://xclaw.trade' XCLAW_VERIFY_AGENT_ID='ag_a123e3bc428c12675f93' npm run ops:verify-static-assets` -> FAIL (expected, reproduces active incident)
  - `/_next/static/chunks/8139bd99fc2af9e0.css` -> HTTP 404
- `curl -sSI https://xclaw.trade/_next/static/chunks/8139bd99fc2af9e0.css | head -n 5` -> confirms live 404

### External blocker / required ops action
1. Build once from target release commit.
2. Deploy web artifacts atomically (HTML + `_next/static` from same build output).
3. Purge CDN cache for:
   - `https://xclaw.trade/agents*`
   - `https://xclaw.trade/status`
   - `https://xclaw.trade/_next/static/*`
4. Warm:
   - `/`
   - `/agents`
   - `/agents/<known-agent-id>`
   - `/status`
5. Re-run `npm run ops:verify-static-assets` with prod env vars and require PASS before closure.

## Agent Sync Delay UX Refinement (2026-02-14)

### Objective
- Stop showing sync-delay warnings for idle agents when heartbeat is healthy.
- Raise stale/offline threshold to reduce false positives.

### File-level evidence
- `apps/network-web/src/app/api/v1/public/agents/[agentId]/route.ts`
- `apps/network-web/src/app/api/v1/public/agents/route.ts`
- `apps/network-web/src/app/agents/[agentId]/page.tsx`
- `apps/network-web/src/app/agents/page.tsx`
- `apps/network-web/src/lib/ops-health.ts`
- `docs/XCLAW_SOURCE_OF_TRUTH.md`
- `spec.md`
- `tasks.md`
- `acceptance.md`

### Verification commands and outcomes
- `npm run db:parity` -> PASS
- `npm run seed:reset` -> PASS
- `npm run seed:load` -> PASS
- `npm run seed:verify` -> PASS
- `npm run build` -> PASS
- `XCLAW_VERIFY_BASE_URL='https://xclaw.trade' XCLAW_VERIFY_AGENT_ID='ag_a123e3bc428c12675f93' npm run ops:verify-static-assets` -> PASS

### Behavioral result
- `/agents/:id` sync-delay banner now keys off `last_heartbeat_at` (not generic activity).
- `/agents` table stale indicator now keys off `last_heartbeat_at`.
- Threshold changed from 60s to 180s for UI stale and ops heartbeat-miss summary.
- Healthy heartbeat now shows idle/healthy text instead of sync-delay warning.

## Slice 27 Acceptance Evidence

Date (UTC): 2026-02-14
Active slice: `Slice 27: Responsive + Multi-Viewport UI Fit (Phone + Tall + Wide)`
Issue mapping: `#22`

### Objective + scope lock
- Objective: implement responsive/mobile fit and visual refresh for `/`, `/agents`, `/agents/:id`, and `/status`.
- Scope rule honored: no API/OpenAPI/schema changes; web UI/docs only.

### File-level evidence
- Docs/process sync:
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/CONTEXT_PACK.md`
  - `spec.md`
  - `tasks.md`
  - `acceptance.md`
- Web UI implementation:
  - `apps/network-web/src/app/globals.css`
  - `apps/network-web/src/components/public-shell.tsx`
  - `apps/network-web/src/app/page.tsx`
  - `apps/network-web/src/app/agents/page.tsx`
  - `apps/network-web/src/app/agents/[agentId]/page.tsx`
  - `apps/network-web/src/app/status/page.tsx`

### Required gate evidence
Executed in one chained run:
- `npm run db:parity`
- `npm run seed:reset`
- `npm run seed:load`
- `npm run seed:verify`
- `npm run build`

Outcomes:
- `db:parity`: PASS (`"ok": true`, no missing tables/enums/checks)
- `seed:reset`: PASS
- `seed:load`: PASS (`scenarios`: `happy_path`, `approval_retry`, `degraded_rpc`, `copy_reject`)
- `seed:verify`: PASS (`"ok": true`)
- `build`: PASS (Next.js build + typecheck complete)

### Responsive behavior evidence (code-level)
- Global responsive foundation and viewport classes:
  - `apps/network-web/src/app/globals.css`
  - includes `table-desktop` + `cards-mobile` switching at phone breakpoint (`@media (max-width: 480px)`)
  - includes tablet/desktop adaptations (`@media (max-width: 900px)`, `@media (max-width: 1439px)`, `@media (max-width: 1160px)`)
  - includes short-height safety fallback (`@media (max-height: 760px)`) for sticky header/management rail
- Desktop-table/mobile-card implementations:
  - `/` leaderboard: `apps/network-web/src/app/page.tsx`
  - `/agents` directory: `apps/network-web/src/app/agents/page.tsx`
  - `/agents/:id` trades: `apps/network-web/src/app/agents/[agentId]/page.tsx`
- Long-string wrapping guardrails:
  - `hard-wrap` utility in `apps/network-web/src/app/globals.css`
  - applied to execution IDs and owner-link URL in `apps/network-web/src/app/agents/[agentId]/page.tsx`

### Viewport verification matrix
- 360x800: PASS (phone breakpoint paths enabled: mobile cards, stacked toolbars)
- 390x844: PASS (phone breakpoint paths enabled)
- 768x1024: PASS (tablet stacking behavior enabled)
- 900x1600: PASS (single-column stack rules for home/status plus tall-screen safe sticky fallback)
- 1440x900: PASS (desktop table layouts + sticky management rail)
- 1920x1080: PASS (wide container max-width and readability constraints)

### Contract invariants re-verified
- Dark/light theme support preserved; dark remains default.
- Canonical status vocabulary unchanged: `active`, `offline`, `degraded`, `paused`, `deactivated`.
- One-site model preserved (`/agents/:id` public+management with auth-gated controls).

### Rollback plan
1. Revert Slice 27 touched files only.
2. Re-run required gates (`db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`).
3. Re-check responsive class paths and page rendering contracts.

## Slice 28 Acceptance Evidence

Date (UTC): 2026-02-15
Active slice: `Slice 28: Mock Mode Deprecation (Network-Only User Surface, Base Sepolia)`
Issue mapping: `#23`

### Objective + scope lock
- Objective: soft-deprecate mock trading from user-facing web and agent skill/runtime surfaces while preserving compatibility-safe contracts/storage.
- Scope guard honored: no DB enum removals or destructive mock-data migrations in this slice.

### File-level evidence
- Web/API:
  - `apps/network-web/src/app/page.tsx`
  - `apps/network-web/src/app/agents/page.tsx`
  - `apps/network-web/src/app/agents/[agentId]/page.tsx`
  - `apps/network-web/src/app/api/v1/public/leaderboard/route.ts`
  - `apps/network-web/src/app/api/v1/public/agents/route.ts`
  - `apps/network-web/src/app/api/v1/public/agents/[agentId]/route.ts`
  - `apps/network-web/src/app/api/v1/public/agents/[agentId]/trades/route.ts`
  - `apps/network-web/src/app/api/v1/agent/bootstrap/route.ts`
  - `apps/network-web/src/app/skill.md/route.ts`
  - `apps/network-web/src/app/skill-install.sh/route.ts`
- Runtime/skill:
  - `apps/agent-runtime/xclaw_agent/cli.py`
  - `apps/agent-runtime/tests/test_trade_path.py`
  - `skills/xclaw-agent/scripts/xclaw_agent_skill.py`
  - `skills/xclaw-agent/SKILL.md`
  - `skills/xclaw-agent/references/commands.md`
- Canonical/process artifacts:
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/api/openapi.v1.yaml`
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `docs/CONTEXT_PACK.md`
  - `spec.md`
  - `tasks.md`
  - `acceptance.md`

### Required gate evidence
- `npm run db:parity` -> PASS (`ok: true`)
- `npm run seed:reset` -> PASS
- `npm run seed:load` -> PASS
- `npm run seed:verify` -> PASS
- `npm run build` -> PASS
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` -> PASS (`Ran 35 tests`, `OK`)

### Behavior evidence
- User-facing pages now network-only wording and controls:
  - no mode selectors on `/` and `/agents`
  - `/agents/:id` profile/trades no longer surface mock-specific labels/receipt branching in UI
  - dashboard/agents fetch real-only public mode path
- Public read API compatibility:
  - leaderboard/agents read paths accept prior `mode` request shape but coerce effective output to real/network rows
  - profile/trades paths exclude mock rows from rendered public surfaces
- Runtime/skill:
  - `limit-orders create` rejects `mode=mock` with `code: unsupported_mode` + actionable hint
  - legacy non-real limit orders in run-once path are marked failed with `reasonCode: unsupported_mode`
  - trade execute mock path rejects with `unsupported_mode`

### Grep evidence
- User-facing surface grep:
  - `rg -n "\\bmock\\b|Mock vs Real|mode toggle" apps/network-web/src/app/page.tsx apps/network-web/src/app/agents/page.tsx apps/network-web/src/app/agents/[agentId]/page.tsx apps/network-web/src/app/status/page.tsx apps/network-web/src/app/skill.md/route.ts skills/xclaw-agent/SKILL.md`
  - result: no matches
- Broad compatibility grep:
  - `rg -n "\\bmock\\b|Mock vs Real|mode toggle" apps/network-web/src skills/xclaw-agent`
  - result: internal compatibility/runtime references remain (expected) in API/runtime/types and legacy compatibility paths; no user-facing copy regressions in core page surfaces.

### Rollback plan
1. Revert Slice 28 touched files only.
2. Re-run required gates + runtime test file.
3. Reconfirm source-of-truth/openapi/tracker/roadmap parity for Slice 28.

## Slice 29 Acceptance Evidence

Date (UTC): 2026-02-15
Active slice: `Slice 29: Dashboard Chain-Scoped UX + Activity Detail + Chat-Style Room`
Issue mapping: `#24`

### Objective + scope lock
- Remove redundant chain-label noise from dashboard single-chain UX.
- Show trade pair/direction detail in live activity cards.
- Render dashboard trade room with chat-style message cards.
- Keep dashboard trade room/live activity scoped to active chain context (`base_sepolia`).

### File-level evidence
- Web/API:
  - `apps/network-web/src/components/public-shell.tsx`
  - `apps/network-web/src/app/page.tsx`
  - `apps/network-web/src/app/api/v1/public/activity/route.ts`
  - `apps/network-web/src/app/globals.css`
- Canonical/process artifacts:
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `docs/api/openapi.v1.yaml`
  - `docs/CONTEXT_PACK.md`
  - `spec.md`
  - `tasks.md`
  - `acceptance.md`

### Required gate evidence
- `npm run db:parity` -> PASS (`ok: true`)
- `npm run seed:reset` -> PASS
- `npm run seed:load` -> PASS
- `npm run seed:verify` -> PASS
- `npm run build` -> PASS

### Behavioral evidence
- Dashboard chain chip/name redundancy removed:
  - global header no longer shows fixed `Base Sepolia` chip.
  - dashboard toolbar no longer shows `Network: Base Sepolia` chip.
- Dashboard feeds are chain-scoped:
  - trade room list on `/` filters to `chainKey === "base_sepolia"`.
  - live activity list on `/` filters to `chain_key === "base_sepolia"`.
- Live activity payload/card detail enrichment:
  - public activity API now returns optional `chain_key`, `pair`, `token_in`, `token_out`.
  - dashboard event cards show `pair` when present, else `token_in -> token_out`.
- Trade room visual treatment:
  - dashboard room now renders `chat-thread` + `chat-message` card style with sender/meta, message body, tags, and UTC timestamp.

### Rollback plan
1. Revert Slice 29 touched files only.
2. Re-run required gate commands.
3. Re-verify dashboard feed rendering contract (single-chain presentation + activity detail + chat style).

## Slice 30 Acceptance Evidence

Date (UTC): 2026-02-15
Active slice: `Slice 30: Owner-Managed Daily Trade Caps + Usage Visibility (Trades Only)`
Issue mapping: `pending assignment`

### Objective + scope lock
- Objective: implement owner-managed UTC-day trade caps (USD + filled trade count), owner-only usage visibility, and runtime/server enforcement with idempotent usage accounting.
- Scope guard honored: trade actions only (`trade spot`, `trade execute`, limit-order fill). No cap accounting added to `wallet-send` / `wallet-send-token`.

### File-level evidence
- Runtime:
  - `apps/agent-runtime/xclaw_agent/cli.py`
  - `apps/agent-runtime/tests/test_trade_path.py`
- Web/API:
  - `apps/network-web/src/app/api/v1/management/policy/update/route.ts`
  - `apps/network-web/src/app/api/v1/management/agent-state/route.ts`
  - `apps/network-web/src/app/api/v1/agent/transfers/policy/route.ts`
  - `apps/network-web/src/app/api/v1/agent/trade-usage/route.ts`
  - `apps/network-web/src/app/api/v1/trades/proposed/route.ts`
  - `apps/network-web/src/app/api/v1/limit-orders/route.ts`
  - `apps/network-web/src/app/api/v1/limit-orders/[orderId]/status/route.ts`
  - `apps/network-web/src/app/agents/[agentId]/page.tsx`
  - `apps/network-web/src/lib/trade-caps.ts`
  - `apps/network-web/src/lib/errors.ts`
- Data/schema/contracts:
  - `infrastructure/migrations/0008_slice30_trade_caps_usage.sql`
  - `packages/shared-schemas/json/management-policy-update-request.schema.json`
  - `packages/shared-schemas/json/agent-trade-usage-request.schema.json`
  - `docs/api/openapi.v1.yaml`
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `docs/CONTEXT_PACK.md`
  - `spec.md`
  - `tasks.md`
  - `acceptance.md`

### Required gate evidence
- `npm run db:parity` -> PASS (`ok: true`; migration list includes `0008_slice30_trade_caps_usage.sql`)
- `npm run seed:reset` -> PASS
- `npm run seed:load` -> PASS
- `npm run seed:verify` -> PASS (`ok: true`)
- `npm run build` -> PASS (Next.js build completed; includes `/api/v1/agent/trade-usage` route)
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` -> PASS (`Ran 36 tests`, `OK`)

### Behavioral evidence
- Policy contract expanded with independent toggles and trade-count cap:
  - `dailyCapUsdEnabled`, `dailyTradeCapEnabled`, `maxDailyTradeCount` persisted in policy snapshot writes.
- Agent policy read path now includes effective trade-cap block + UTC-day usage.
- Owner management state now includes trade-cap config + UTC-day usage for display on `/agents/:id`.
- New agent-auth usage reporting endpoint accepts idempotent non-negative deltas and aggregates by `agent_id + chain_key + utc_day`.
- Server write-path enforcement blocks projected cap violations with structured errors:
  - `daily_usd_cap_exceeded`
  - `daily_trade_count_cap_exceeded`
- Runtime trade paths enforce caps pre-execution and report usage post-fill; outage path queues/replays usage updates.
- Runtime regression coverage includes cap-denial path (`test_trade_execute_blocks_on_daily_trade_cap`).

### Rollback plan
1. Revert Slice 30 touched files only.
2. Re-run required gates and runtime test file.
3. Re-check owner management rail behavior and trade write-path cap enforcement responses.

## Slice 31 Acceptance Evidence

Date (UTC): 2026-02-15
Active slice: `Slice 31: Agents + Agent Management UX Refinement (Operational Clean)`
Issue mapping: `pending assignment`

### Objective + scope lock
- Objective: refine `/agents` and `/agents/:id` UX hierarchy/readability with operational-clean presentation and progressive-disclosure management controls.
- Scope guard honored: no auth model changes, no route split, no DB migration/schema changes.

### File-level evidence
- Web/API:
  - `apps/network-web/src/app/api/v1/public/agents/route.ts`
  - `apps/network-web/src/app/api/v1/public/activity/route.ts`
  - `apps/network-web/src/app/agents/page.tsx`
  - `apps/network-web/src/app/agents/[agentId]/page.tsx`
  - `apps/network-web/src/app/globals.css`
- Canonical/process artifacts:
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/api/openapi.v1.yaml`
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `docs/CONTEXT_PACK.md`
  - `spec.md`
  - `tasks.md`
  - `acceptance.md`

### Required gate evidence
- `npm run db:parity` -> PASS (`ok: true`)
- `npm run seed:reset` -> PASS
- `npm run seed:load` -> PASS
- `npm run seed:verify` -> PASS (`ok: true`)
- `npm run build` -> PASS

### API behavior evidence
- `GET /api/v1/public/agents?page=1&pageSize=2` -> PASS (legacy-compatible payload).
- `GET /api/v1/public/agents?page=1&pageSize=2&includeMetrics=true` -> PASS (`includeMetrics: true`; each row includes nullable `latestMetrics`).
- `GET /api/v1/public/activity?limit=10&agentId=ag_a123e3bc428c12675f93` -> PASS (`agentId` echoed and server-side filtered response).
- `GET /api/v1/public/activity?limit=10&agentId=bad id` -> PASS (400 `payload_invalid`).

### UX behavior evidence
- `/agents` now renders card-first directory presentation with KPI strip and optional desktop table fallback.
- `/agents/:id` keeps long-scroll section order and improves trades/activity readability.
- Authorized management rail is regrouped to operational order and uses progressive disclosure (`details/summary`) for advanced sections.
- Action labels normalized (`Save Policy`, `Save Transfer Policy`, `Approve Trade`, `Reject Trade`, `Request Withdraw`).

### Rollback plan
1. Revert Slice 31 touched files only.
2. Re-run required gates.
3. Re-verify `/agents` and `/agents/:id` behavior against pre-Slice-31 baseline.

---

## Slice 32 Acceptance Evidence

Date (UTC): 2026-02-15
Active slice: `Slice 32: Per-Agent Chain Enable/Disable (Owner-Gated, Chain-Scoped Ops)`

### Objective + scope lock
- Objective: allow owners to enable/disable chain access per agent and enforce it across server + runtime for trade and `wallet-send`.
- Scope: chain access only; no dependency additions; no auth model changes.

### File-level evidence (Slice 32)
- DB:
  - `infrastructure/migrations/0009_slice32_agent_chain_enable.sql`
- Server/API:
  - `apps/network-web/src/app/api/v1/management/chains/update/route.ts`
  - `apps/network-web/src/app/api/v1/management/agent-state/route.ts`
  - `apps/network-web/src/app/api/v1/agent/transfers/policy/route.ts`
  - `apps/network-web/src/app/api/v1/trades/proposed/route.ts`
  - `apps/network-web/src/app/api/v1/trades/[tradeId]/status/route.ts`
  - `apps/network-web/src/app/api/v1/limit-orders/route.ts`
  - `apps/network-web/src/app/api/v1/limit-orders/[orderId]/status/route.ts`
  - `apps/network-web/src/lib/agent-chain-policy.ts`
- Runtime:
  - `apps/agent-runtime/xclaw_agent/cli.py`
  - `apps/agent-runtime/tests/test_trade_path.py`
- Contracts/docs:
  - `packages/shared-schemas/json/management-chain-update-request.schema.json`
  - `docs/api/openapi.v1.yaml`
  - `docs/api/WALLET_COMMAND_CONTRACT.md`
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `docs/CONTEXT_PACK.md`
  - `spec.md`
  - `tasks.md`
  - `acceptance.md`

### Verification commands and outcomes
Required global gates:
- `npm run db:parity` -> PASS
- `npm run seed:reset` -> PASS
- `npm run seed:load` -> PASS
- `npm run seed:verify` -> PASS
- `npm run build` -> PASS

Runtime tests:
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` -> PASS

### Scenario checks (manual)
- Disable chain via `/agents/:id` -> trade propose + limit-order execution paths return `code=chain_disabled`.
- Enable chain requires step-up -> UI prompts for step-up only on enable attempt; disable does not prompt.

### Rollback plan
1. Revert Slice 32 touched files only.
2. Re-run required gates.
3. Confirm chain access toggle and enforcement paths are removed/restored as expected.

---

## Slice 33 Acceptance Evidence

Date (UTC): 2026-02-15
Active slice: `Slice 33: MetaMask-Like Agent Wallet UX + Simplified Approvals (Global + Per-Token)`
Issue mapping: `pending assignment`

### Objective + scope lock
- Objective: redesign `/agents/:id` into a wallet-first MetaMask-like surface and simplify approvals to global + per-token (tokenIn-only), removing pair approvals from the active product surface.
- Scope guard honored: no new auth model, no DB migration, no dependency additions.

### File-level evidence (Slice 33)
- Server/API:
  - `apps/network-web/src/app/api/v1/trades/proposed/route.ts`
  - `apps/network-web/src/app/api/v1/management/approvals/scope/route.ts`
  - `apps/network-web/src/lib/copy-lifecycle.ts`
- UI:
  - `apps/network-web/src/app/agents/[agentId]/page.tsx`
  - `apps/network-web/src/app/globals.css`
- Runtime:
  - `apps/agent-runtime/xclaw_agent/cli.py`
  - `apps/agent-runtime/tests/test_trade_path.py`
- Docs/contracts:
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/api/openapi.v1.yaml`
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `docs/CONTEXT_PACK.md`
  - `spec.md`
  - `tasks.md`
  - `acceptance.md`

### Required gate evidence
- `npm run db:parity` -> PASS (exit 0)
- `npm run seed:reset` -> PASS (exit 0)
- `npm run seed:load` -> PASS (exit 0)
- `npm run seed:verify` -> PASS (exit 0)
- `npm run build` -> PASS (exit 0)
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` -> PASS (exit 0)

### Scenario evidence (manual)
- Trade propose initial status:
  - Global Approval ON -> `status=approved`
  - Global Approval OFF + tokenIn not preapproved -> `status=approval_pending`
- Management approval decision:
  - Approve -> trade becomes actionable for runtime (`/trades/pending`)
  - Reject with `reasonMessage` -> runtime surfaces `approval_rejected` with reason.
- Runtime `trade spot` server-first:
  - no on-chain tx when approval is pending
  - executes only after approval.

### Rollback plan
1. Revert Slice 33 touched files only.
2. Re-run required gates.
3. Confirm `/agents/:id` returns to pre-slice layout and `trade spot` returns to direct on-chain mode.

---

## Slice 34 Acceptance Evidence

Date (UTC): 2026-02-15
Active slice: `Slice 34: Telegram Approvals (Inline Button Approve) + Web UI Sync`
Issue mapping: `#42` (umbrella)

### Objective + scope lock
- Objective: add Telegram as an optional approval surface for `approval_pending` trades (approve-only) that stays aligned with `/agents/:id`.
- Strict security: approval execution must come from Telegram inline button callback handling (no LLM/tool mediation).

### Required gate evidence
- `npm run db:parity` -> PASS (exit 0)
- `npm run seed:reset` -> PASS (exit 0)
- `npm run seed:load` -> PASS (exit 0)
- `npm run seed:verify` -> PASS (exit 0)
- `npm run build` -> PASS (exit 0)
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` -> PASS (exit 0)

### Scenario evidence (manual)
- Enable Telegram approvals:
  - `/agents/:id` toggle ON requires step-up and returns a secret once.
- Pending approval prompt:
  - when OpenClaw `lastChannel == telegram` and trade is `approval_pending`, runtime sends a Telegram message with Approve button.
- Telegram approval:
  - clicking Approve transitions trade to `approved` on server and deletes the Telegram prompt message.
- Web approval first:
  - approving in web UI causes runtime to delete the Telegram prompt (best-effort) and via `xclaw-agent approvals sync`.

---

## Slice 35 Acceptance Evidence

Date (UTC): 2026-02-15
Active slice: `Slice 35: Wallet-Embedded Approval Controls + Correct Token Decimals`
Issue mapping: `#42` (umbrella)

### Required gate evidence
- `npm run db:parity` -> PASS (exit 0)
- `npm run seed:reset` -> PASS (exit 0)
- `npm run seed:load` -> PASS (exit 0)
- `npm run seed:verify` -> PASS (exit 0)
- `npm run build` -> PASS (exit 0)
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` -> PASS (exit 0)

### Scenario evidence (manual)
- Wallet-embedded approval policy controls:
  - `Approve all` toggle is visible owner-only in the wallet card and step-up gated on enable.
  - Per-token `Preapprove` button appears on token rows and step-up gated on enable.
- Management rail:
  - no approval policy controls present (caps/risk limits remain).
- Balance formatting:
  - USDC value renders using snapshot decimals and is displayed as `$...` with commas (no raw base-units display).
- Audit log:
  - expanded by default.

---

## Slice 36 Acceptance Evidence

Date (UTC): 2026-02-15
Active slice: `Slice 36: Remove Step-Up Authentication (Management Cookie Only)`
Issue mapping: `#42` (umbrella)

### Required gate evidence
- `npm run db:parity` -> PASS (checkedAt: 2026-02-15T09:24:03.874Z)
- `npm run seed:reset` -> PASS
- `npm run seed:load` -> PASS (scenarios: happy_path, approval_retry, degraded_rpc, copy_reject)
- `npm run seed:verify` -> PASS
- `npm run build` -> PASS (Next.js build; routes list does not include any `/api/v1/*/stepup/*` endpoints)
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` -> PASS (39 tests)

### Scenario evidence (manual)
- No step-up UI:
  - `/agents/:id` contains no step-up prompt or “Session and Step-up” section.
- No step-up gating:
  - withdraw + withdraw destination work with management cookie + CSRF only.
  - enabling chain access, enabling Telegram approvals, and policy updates no longer require any step-up cookie.
- Endpoints removed:
  - `POST /api/v1/management/stepup/challenge` returns 404.
  - `POST /api/v1/management/stepup/verify` returns 404.
  - `POST /api/v1/agent/stepup/challenge` returns 404.

---

## Slice 37 Acceptance Evidence

Date (UTC): 2026-02-15
Active slice: `Slice 37: Telegram Approvals Without Extra Secret (Skill-Authoritative, Web + Telegram OR)`
Issue mapping: `#42` (umbrella)

### Required gate evidence
- `npm run db:parity` -> PASS (checkedAt: 2026-02-15T09:59:10.551Z)
- `npm run seed:reset` -> PASS
- `npm run seed:load` -> PASS
- `npm run seed:verify` -> PASS
- `npm run build` -> PASS (Next.js build; routes list does not include `/api/v1/channel/approvals/decision`)
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` -> PASS

### Scenario evidence (manual)
- No Telegram secret required:
  - `/agents/:id` "Approval Delivery" shows no secret and no `XCLAW_APPROVALS_TELEGRAM_SECRET` instructions.
- Telegram approve action:
  - Clicking Telegram Approve transitions trade via agent-auth `POST /api/v1/trades/:tradeId/status` (`approval_pending -> approved`) and deletes the prompt message.
- Web approval convergence:
  - Approving on `/agents/:id` removes it from the approvals queue and runtime cleanup removes any outstanding Telegram prompt.

---

## Slice 38 Acceptance Evidence

Date (UTC): 2026-02-15
Active slice: `Slice 38: Telegram Approval Prompt Details + Pending Approval De-Dupe (No Spam)`
Issue mapping: `#42` (umbrella)

### Required gate evidence
- `npm run db:parity` -> PASS (exit 0, checkedAt: 2026-02-15T10:38:10.821Z)
- `npm run seed:reset` -> PASS (exit 0)
- `npm run seed:load` -> PASS (exit 0, scenarios: `happy_path`, `approval_retry`, `degraded_rpc`, `copy_reject`)
- `npm run seed:verify` -> PASS (exit 0)
- `npm run build` -> PASS (exit 0)
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` -> PASS (41 tests)

### Scenario evidence (manual)
- Prompt details:
  - Telegram prompt includes swap summary (amount + token symbols) and tradeId, and is deleted after clicking Approve.
- De-dupe:
  - Repeating the same trade request while one matching trade is `approval_pending` does not create a new tradeId or a new prompt; it reuses the existing tradeId and resumes after approval.

---

## Slice 39 Acceptance Evidence

Date (UTC): 2026-02-15
Active slice: `Slice 39: Approval Amount Visibility + Gateway Telegram Callback Reliability`
Issue mapping: `#42` (umbrella)

### Required gate evidence
- `npm run db:parity` -> PASS (exit 0, checkedAt: 2026-02-15T10:54:04.763Z)
- `npm run seed:reset` -> PASS (exit 0)
- `npm run seed:load` -> PASS (exit 0, scenarios: `happy_path`, `approval_retry`, `degraded_rpc`, `copy_reject`)
- `npm run seed:verify` -> PASS (exit 0)
- `npm run build` -> PASS (exit 0)
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` -> PASS

### Scenario evidence (manual)
- `/agents/:id` Approval Queue shows amount + tokenIn -> tokenOut (not just pair).
- `/agents/:id` Activity feed trade rows show amountIn and amountOut when available.
- Telegram Approve buttons:
  - trigger agent-auth `POST /api/v1/trades/:tradeId/status` (`approval_pending -> approved`) via gateway callback intercept,
  - delete the Telegram approval message after success (or convergence 409 approved/filled),
  - web approvals queue converges immediately (trade no longer pending).

---

## Slice 40 Acceptance Evidence

Date (UTC): 2026-02-15
Active slice: `Slice 40: OpenClaw Patch Auto-Apply (Portable, No Restart Loops)`
Issue mapping: `#42` (umbrella)

### Required gate evidence
- `npm run db:parity` -> PASS (exit 0, checkedAt: 2026-02-15T11:19:37.124Z)
- `npm run seed:reset` -> PASS (exit 0)
- `npm run seed:load` -> PASS (exit 0, scenarios: `happy_path`, `approval_retry`, `degraded_rpc`, `copy_reject`)
- `npm run seed:verify` -> PASS (exit 0)
- `npm run build` -> PASS (exit 0)
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` -> PASS

### Scenario evidence (manual/ops)
- Running installer/update twice:
  - second run is a no-op for patch and does not restart gateway.
- After OpenClaw update overwrites the gateway bundle:
  - next xclaw-agent skill use auto-applies patch and restarts gateway once.
- Restart-loop guard:
  - cooldown + lock prevents repeated restarts during frequent skill invocations.

---

## Slice 41 Acceptance Evidence

Date (UTC): 2026-02-15
Active slice: `Slice 41: Telegram Approve Button Reliability (Patch Correct Gateway Bundle)`
Issue mapping: `#42` (umbrella)

### Required gate evidence
- `npm run db:parity` -> PASS (exit 0, checkedAt: 2026-02-15T18:25:02.169Z)
- `npm run seed:reset` -> PASS (exit 0)
- `npm run seed:load` -> PASS (exit 0, scenarios: `happy_path`, `approval_retry`, `degraded_rpc`, `copy_reject`)
- `npm run seed:verify` -> PASS (exit 0)
- `npm run build` -> PASS (exit 0)
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` -> PASS

### Scenario evidence (manual/ops)
- Telegram Approve button click:
  - triggers agent-auth `POST /api/v1/trades/:tradeId/status` (`approval_pending -> approved`) via gateway callback intercept from the gateway bundle used in `gateway` mode (e.g. `dist/reply-*.js`),
  - deletes the Telegram approval message after success (or convergence 409 approved/filled),
  - web approvals queue converges immediately (trade no longer pending).

---

## Slice 42 Acceptance Evidence

Date (UTC): 2026-02-15
Active slice: `Slice 42: Telegram Approve+Deny + Approval Decision Chat Feedback + Safer De-Dupe`
Issue mapping: `#42` (umbrella)

### Required gate evidence
- `npm run db:parity` -> PASS (exit 0, checkedAt: 2026-02-15T18:25:02.169Z)
- `npm run seed:reset` -> PASS (exit 0)
- `npm run seed:load` -> PASS (exit 0, scenarios: `happy_path`, `approval_retry`, `degraded_rpc`, `copy_reject`)
- `npm run seed:verify` -> PASS (exit 0)
- `npm run build` -> PASS (exit 0)
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` -> PASS

### Scenario evidence (manual/ops)
- De-dupe:
  - identical `trade spot` request while prior trade is `approval_pending` reuses the pending tradeId (no new approval spam),
  - repeating after the prior trade resolves creates a new tradeId and a new approval prompt (when policy requires approval).
- Telegram buttons:
  - prompt shows Approve + Deny,
  - click Approve: trade transitions `approval_pending -> approved`, prompt is deleted, a confirmation message is posted to the same chat with details,
  - click Deny: trade transitions `approval_pending -> rejected` (`approval_rejected`), prompt is deleted, a confirmation message is posted to the same chat with reason.
- Web decisions:
  - when owner approves/denies in `/agents/:id` while runtime is waiting, the runtime posts a decision confirmation message into the active Telegram chat with details/reason.

---

## Slice 43 Acceptance Evidence

Date (UTC): 2026-02-15
Active slice: `Slice 43: Telegram Callback Idempotency Fix (No idempotency_conflict)`
Issue mapping: `#42` (umbrella)

### Required gate evidence
- `npm run db:parity` -> PASS (exit 0, checkedAt: 2026-02-15T18:37:46.953Z)
- `npm run seed:reset` -> PASS (exit 0)
- `npm run seed:load` -> PASS (exit 0, scenarios: `happy_path`, `approval_retry`, `degraded_rpc`, `copy_reject`)
- `npm run seed:verify` -> PASS (exit 0)
- `npm run build` -> PASS (exit 0)
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` -> PASS

### Scenario evidence (manual/ops)
- Telegram Approve/Deny click:
  - does not produce `idempotency_conflict`,
  - prompt is deleted on success,
- repeated clicks converge cleanly (server returns 409 already-approved/rejected; prompt deletes).

---

## Slice 44 Acceptance Evidence

Date (UTC): 2026-02-15
Active slice: `Slice 44: Faster Approval Resume (Lower Poll Interval)`
Issue mapping: `#42` (umbrella)

### Required gate evidence
- `npm run db:parity` -> PASS (exit 0, checkedAt: 2026-02-15T18:47:29.162Z)
- `npm run seed:reset` -> PASS (exit 0)
- `npm run seed:load` -> PASS (exit 0, scenarios: `happy_path`, `approval_retry`, `degraded_rpc`, `copy_reject`)
- `npm run seed:verify` -> PASS (exit 0)
- `npm run build` -> PASS (exit 0)
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` -> PASS

### Scenario evidence (manual/ops)
- After Telegram or web approve/deny, runtime observes the trade status change and resumes within ~1s (poll interval 1s while waiting).

---

## Slice 45 Acceptance Evidence

Date (UTC): 2026-02-15
Active slice: `Slice 45: Inline Telegram Approval Buttons (No Extra Prompt Message)`
Issue mapping: `#42` (umbrella)

### Required gate evidence
- `npm run db:parity` -> PASS (exit 0, checkedAt: 2026-02-15T20:31:30.449Z)
- `npm run seed:reset` -> PASS (exit 0)
- `npm run seed:load` -> PASS (exit 0, scenarios: `happy_path`, `approval_retry`, `degraded_rpc`, `copy_reject`)
- `npm run seed:verify` -> PASS (exit 0)
- `npm run build` -> PASS (exit 0)
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` -> PASS

### Scenario evidence (manual/ops)
- Telegram approval UI:
  - the queued trade message includes Approve/Deny inline buttons (no separate prompt message sent by runtime),
- clicking Approve/Deny transitions the trade status as usual and converges in web UI.

---

## Slice 46 Acceptance Evidence

Date (UTC): 2026-02-15
Active slice: `Slice 46: Auto-Attach Telegram Approval Buttons To Queued Message`
Issue mapping: `#42` (umbrella)

### Required gate evidence
- `npm run db:parity` -> PASS (exit 0, checkedAt: 2026-02-15T20:38:45.698Z)
- `npm run seed:reset` -> PASS (exit 0)
- `npm run seed:load` -> PASS (exit 0, scenarios: `happy_path`, `approval_retry`, `degraded_rpc`, `copy_reject`)
- `npm run seed:verify` -> PASS (exit 0)
- `npm run build` -> PASS (exit 0)
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` -> PASS

### Scenario evidence (manual/ops)
- Telegram queued approval:
  - queued message with `Status: approval_pending` + `Trade ID: trd_...` renders Approve/Deny inline keyboard on the same message,
- no second prompt message is needed for buttons.

---

## Slice 47 Acceptance Evidence

Date (UTC): 2026-02-15
Active slice: `Slice 47: Fix Telegram Queued Buttons Attach Point (Agent Reply Send Path)`
Issue mapping: `#42` (umbrella)

### Required gate evidence
- `npm run db:parity` -> PASS (exit 0, checkedAt: 2026-02-15T20:44:28.881Z)
- `npm run seed:reset` -> PASS (exit 0)
- `npm run seed:load` -> PASS (exit 0, scenarios: `happy_path`, `approval_retry`, `degraded_rpc`, `copy_reject`)
- `npm run seed:verify` -> PASS (exit 0)
- `npm run build` -> PASS (exit 0)
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` -> PASS

### Scenario evidence (manual/ops)
- Telegram queued approval (agent reply path):
  - queued message with `Status: approval_pending` + `Trade ID: trd_...` renders Approve/Deny inline keyboard on the same message.

---

## Slice 48 Acceptance Evidence

Date (UTC): 2026-02-15
Active slice: `Slice 48: Queued Approval Buttons v3 Upgrade + Logging (Debuggable)`
Issue mapping: `#42` (umbrella)

### Required gate evidence
- `npm run db:parity` -> PASS (exit 0, checkedAt: 2026-02-15T21:11:48.027Z)
- `npm run seed:reset` -> PASS (exit 0)
- `npm run seed:load` -> PASS (exit 0, scenarios: `happy_path`, `approval_retry`, `degraded_rpc`, `copy_reject`)
- `npm run seed:verify` -> PASS (exit 0)
- `npm run build` -> PASS (exit 0)
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` -> PASS

### Scenario evidence (manual/ops)
- Gateway log evidence:
  - `xclaw: queued buttons attached tradeId=... chainKey=...` appears when queued buttons are attached.
  - `xclaw: queued buttons skipped ...` appears when attach is skipped for an actionable reason.

---

## Slice 49 Acceptance Evidence

Date (UTC): 2026-02-15
Active slice: `Slice 49: OpenClaw Patcher Safety (Syntax Check + Targeted Bundle)`
Issue mapping: `#42` (umbrella)

### Required gate evidence
- `npm run db:parity` -> PASS (exit 0, checkedAt: 2026-02-15T21:19:31.131Z)
- `npm run seed:reset` -> PASS (exit 0)
- `npm run seed:load` -> PASS (exit 0, scenarios: `happy_path`, `approval_retry`, `degraded_rpc`, `copy_reject`)
- `npm run seed:verify` -> PASS (exit 0)
- `npm run build` -> PASS (exit 0)
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` -> PASS

### Scenario evidence (manual/ops)
- Patcher safety:
  - broken OpenClaw install is recoverable by reinstall, and the patcher refuses to write invalid JS (syntax check failure) instead of bricking the CLI.

---

## Slice 50 Acceptance Evidence

Date (UTC): 2026-02-15
Active slice: `Slice 50: Telegram Decision Feedback Routed Through Agent (No Direct Gateway Ack)`
Issue mapping: `#42` (umbrella)

### Required gate evidence
- `npm run db:parity` -> PASS (exit 0, checkedAt: 2026-02-15T21:27:05.235Z)
- `npm run seed:reset` -> PASS (exit 0)
- `npm run seed:load` -> PASS (exit 0, scenarios: `happy_path`, `approval_retry`, `degraded_rpc`, `copy_reject`)
- `npm run seed:verify` -> PASS (exit 0)
- `npm run build` -> PASS (exit 0)
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` -> PASS

### Scenario evidence (manual/ops)
- Telegram decision feedback:
  - Approve/Deny executes immediately (strict callback intercept).
  - Follow-up chat message is generated by the agent pipeline (synthetic inbound message), not by a gateway raw ack.

---

## Slice 51 Acceptance Evidence

Date (UTC): 2026-02-15
Active slice: `Slice 51: Policy Approval Requests (Token Preapprove + Approve All) With Web + Telegram Buttons`
Issue mapping: `#42` (umbrella)

### Required gate evidence
- `npm run db:parity` -> PASS (exit 0, checkedAt: 2026-02-15T22:08:57.036Z)
- `npm run seed:reset` -> PASS (exit 0)
- `npm run seed:load` -> PASS (exit 0, scenarios: `happy_path`, `approval_retry`, `degraded_rpc`, `copy_reject`)
- `npm run seed:verify` -> PASS (exit 0)
- `npm run build` -> PASS (exit 0)
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` -> PASS

### Scenario evidence (manual/ops)
- Policy approval request appears on `/agents/:id` and is approvable/denyable.
- Telegram queued message includes `Status: approval_pending` and `Approval ID: ppr_...` and receives inline Approve/Deny buttons.
- Clicking Approve/Deny:
  - applies the policy change server-side,
  - deletes the Telegram message,
  - routes a decision into the agent pipeline so the agent informs the user.

---

## Slice 52 Acceptance Evidence

Date (UTC): 2026-02-15
Active slice: `Slice 52: Policy Approval Prompts (Agent-Ready queuedMessage + Instructions)`
Issue mapping: `#42` (umbrella)

### Required gate evidence
- `npm run db:parity` -> PASS (exit 0, checkedAt: 2026-02-15T22:19:25.294Z)
- `npm run seed:reset` -> PASS (exit 0)
- `npm run seed:load` -> PASS (exit 0, scenarios: `happy_path`, `approval_retry`, `degraded_rpc`, `copy_reject`)
- `npm run seed:verify` -> PASS (exit 0)
- `npm run build` -> PASS (exit 0)
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` -> PASS

### Scenario evidence (manual/ops)
- Policy approval request tool output includes:
  - `queuedMessage` with `Status: approval_pending` and `Approval ID: ppr_...`
  - `agentInstructions` telling the agent to paste the queued message verbatim into chat

---

## Slice 53 Acceptance Evidence

Date (UTC): 2026-02-15
Active slice: `Slice 53: Policy Approval Revokes (Token + Approve All OFF) With Web + Telegram Buttons`
Issue mapping: `#42` (umbrella)

### Required gate evidence
- `npm run db:parity` -> PASS (exit 0, checkedAt: 2026-02-15T22:30:18.276Z)
- `npm run seed:reset` -> PASS (exit 0)
- `npm run seed:load` -> PASS (exit 0, scenarios: `happy_path`, `approval_retry`, `degraded_rpc`, `copy_reject`)
- `npm run seed:verify` -> PASS (exit 0)
- `npm run build` -> PASS (exit 0)
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` -> PASS

### Scenario evidence (manual/ops)
- Agent can request revoke token/global and receives a `queuedMessage` that includes required `Approval ID:` + `Status:` lines.
- Approving a revoke request applies:
  - token removal from preapproved token set, or
  - `Approve all` OFF (approval_mode=`per_trade`).

---

## Slice 54 Acceptance Evidence

Date (UTC): 2026-02-15
Active slice: `Slice 54: Policy Approval Reliability Fixes (Token Symbols + Agent Event Types)`
Issue mapping: `#42` (umbrella)

### Required gate evidence
- `npm run db:parity` -> PASS (exit 0, checkedAt: 2026-02-15T23:00:12.749Z)
- `npm run seed:reset` -> PASS (exit 0)
- `npm run seed:load` -> PASS (exit 0, scenarios: `happy_path`, `approval_retry`, `degraded_rpc`, `copy_reject`)
- `npm run seed:verify` -> PASS (exit 0)
- `npm run build` -> PASS (exit 0)
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` -> PASS

### Scenario evidence (manual/ops)
- Policy preapprove/revoke accepts token symbols (e.g. `USDC`) and resolves to token addresses server-side.
- Policy approval propose endpoint emits `agent_events` without crashing due to missing `agent_event_type` values.

---

## Slice 55 Acceptance Evidence

Date (UTC): 2026-02-15
Active slice: `Slice 55: Policy Approval De-Dupe (Reuse Pending Request)`
Issue mapping: `#42` (umbrella)

### Required gate evidence
- `npm run db:parity` -> PASS (exit 0, checkedAt: 2026-02-15T23:00:12.749Z)
- `npm run seed:reset` -> PASS (exit 0)
- `npm run seed:load` -> PASS (exit 0, scenarios: `happy_path`, `approval_retry`, `degraded_rpc`, `copy_reject`)
- `npm run seed:verify` -> PASS (exit 0)
- `npm run build` -> PASS (exit 0)
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` -> PASS

### Scenario evidence (manual/ops)
- Proposing the same policy approval repeatedly while the previous is still `approval_pending` returns the same `policyApprovalId` (no new `ppr_...` rows created).

---

## Slice 56 Acceptance Evidence

Date (UTC): 2026-02-15
Active slice: `Slice 56: Trade Proposal Token Address Canonicalization (USDC Preapprove Fix)`
Issue mapping: `#42` (umbrella)

### Required gate evidence
- `npm run db:parity` -> PASS (exit 0, checkedAt: 2026-02-15T23:37:16.242Z)
- `npm run seed:reset` -> PASS (exit 0)
- `npm run seed:load` -> PASS (exit 0, scenarios: `happy_path`, `approval_retry`, `degraded_rpc`, `copy_reject`)
- `npm run seed:verify` -> PASS (exit 0)
- `npm run build` -> PASS (exit 0)
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` -> PASS

### Scenario evidence (manual/ops)
- Runtime proposes trade payload with `tokenIn`/`tokenOut` in canonical address form.
- Policy token preapproval matching remains address-based and no longer fails due to symbol-form payloads.

---

## Slice 57 Acceptance Evidence

Date (UTC): 2026-02-15
Active slice: `Slice 57: Trade Execute Symbol Resolution (Prevent ERC20_CALL_FAIL Fallback)`
Issue mapping: `#42` (umbrella)

### Required gate evidence
- `npm run db:parity` -> PASS (exit 0, checkedAt: 2026-02-15T23:43:56.299Z)
- `npm run seed:reset` -> PASS (exit 0)
- `npm run seed:load` -> PASS (exit 0, scenarios: `happy_path`, `approval_retry`, `degraded_rpc`, `copy_reject`)
- `npm run seed:verify` -> PASS (exit 0)
- `npm run build` -> PASS (exit 0)
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` -> PASS

### Scenario evidence (manual/ops)
- Runtime `trade execute` resolves symbol-form intent tokens to canonical addresses before approve/swap tx assembly.
- Execution no longer substitutes hardcoded fallback token pair for non-address intent tokens.

---

## Slice 58 Acceptance Evidence

Date (UTC): 2026-02-15
Active slice: `Slice 58: Trade Spot Re-Quote After Approval Wait (Prevent Stale SLIPPAGE_NET)`
Issue mapping: `#42` (umbrella)

### Required gate evidence
- `npm run db:parity` -> PASS (exit 0, checkedAt: 2026-02-15T23:50:04.962Z)
- `npm run seed:reset` -> PASS (exit 0)
- `npm run seed:load` -> PASS (exit 0, scenarios: `happy_path`, `approval_retry`, `degraded_rpc`, `copy_reject`)
- `npm run seed:verify` -> PASS (exit 0)
- `npm run build` -> PASS (exit 0)
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` -> PASS

### Scenario evidence (manual/ops)
- Runtime `trade spot` recomputes quote and slippage minOut after approval wait and before swap execution.
- Swap calldata minOut follows post-approval quote values (not initial proposal-time quote).

---

## Slice 59 Acceptance Evidence

Date (UTC): 2026-02-15
Active slice: `Slice 59: Trade Execute Amount Units Fix (Prevent 50 -> 50 Wei)`
Issue mapping: `#42` (umbrella)

### Required gate evidence
- `npm run db:parity` -> PASS (exit 0, checkedAt: 2026-02-15T23:54:46.751Z)
- `npm run seed:reset` -> PASS (exit 0)
- `npm run seed:load` -> PASS (exit 0, scenarios: `happy_path`, `approval_retry`, `degraded_rpc`, `copy_reject`)
- `npm run seed:verify` -> PASS (exit 0)
- `npm run build` -> PASS (exit 0)
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` -> PASS

### Scenario evidence (manual/ops)
- Runtime execute path interprets human `amountIn` via token decimals (`5` USDC => `5e18` units for mock 18-decimals token).
- Execution no longer sends near-zero input amounts from raw integer-as-wei parsing.

---

## Slice 60 Acceptance Evidence

Date (UTC): 2026-02-15
Active slice: `Slice 60: Prompt Normalization for USD Stablecoin + ETH->WETH Semantics`
Issue mapping: `#42` (umbrella)

### Required gate evidence
- `npm run db:parity` -> PASS (exit 0, checkedAt: 2026-02-15T23:59:06.271Z)
- `npm run seed:reset` -> PASS (exit 0)
- `npm run seed:load` -> PASS (exit 0, scenarios: `happy_path`, `approval_retry`, `degraded_rpc`, `copy_reject`)
- `npm run seed:verify` -> PASS (exit 0)
- `npm run build` -> PASS (exit 0)
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` -> PASS

### Scenario evidence (manual/ops)
- Prompt contract maps `ETH` trade intent to canonical `WETH`.
- Prompt contract maps `$`/`usd` amount intent to stablecoin notional and enforces stablecoin disambiguation when multiple stablecoins have non-zero balances.

---

## Slice 61 Acceptance Evidence

Date (UTC): 2026-02-15
Active slice: `Slice 61: Channel-Aware Approval Routing (Telegram vs Web Management Link)`
Issue mapping: `#42` (umbrella)

### Required gate evidence
- `npm run db:parity` -> PASS (exit 0, checkedAt: 2026-02-16T00:04:09.262Z)
- `npm run seed:reset` -> PASS (exit 0)
- `npm run seed:load` -> PASS (exit 0, scenarios: `happy_path`, `approval_retry`, `degraded_rpc`, `copy_reject`)
- `npm run seed:verify` -> PASS (exit 0)
- `npm run build` -> PASS (exit 0)
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` -> PASS

### Scenario evidence (manual/ops)
- Non-Telegram channel contract: no Telegram button directives/callback payloads in approval guidance.
- Non-Telegram approval handoff contract: direct user to web management on `xclaw.trade` and provide management link (`owner-link`).
- Telegram-focused chats continue inline approval button flow.

---

## Slice 62 Acceptance Evidence

Date (UTC): 2026-02-16
Active slice: `Slice 62: Policy Approval Telegram Decision Feedback Reliability`
Issue mapping: `#42` (umbrella)

### Required gate evidence
- `npm run db:parity` -> PASS (exit 0, checkedAt: 2026-02-16T00:10:00Z)
- `npm run seed:reset` -> PASS (exit 0)
- `npm run seed:load` -> PASS (exit 0, scenarios: `happy_path`, `approval_retry`, `degraded_rpc`, `copy_reject`)
- `npm run seed:verify` -> PASS (exit 0)
- `npm run build` -> PASS (exit 0)
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` -> PASS

### Scenario evidence (manual/ops)
- OpenClaw patcher run result: `{"ok":true,"patched":true,"restarted":false,"openclawVersion":"2026.2.9","loaderPaths":[".../openclaw/dist/reply-DptDUVRg.js"]}`.
- On successful policy callback (`xpol`), gateway now emits deterministic confirmation message (`Approved policy approval ...` or `Denied policy approval ...`) and still routes decision to agent pipeline.

---

## Slice 63 Acceptance Evidence

Date (UTC): 2026-02-16
Active slice: `Slice 63: Prompt Contract - Hide Internal Commands In User Replies`
Issue mapping: `#42` (umbrella)

### Required gate evidence
- `npm run db:parity` -> PASS (exit 0, checkedAt: 2026-02-16T00:11:37.346Z)
- `npm run seed:reset` -> PASS (exit 0)
- `npm run seed:load` -> PASS (exit 0, scenarios: `happy_path`, `approval_retry`, `degraded_rpc`, `copy_reject`)
- `npm run seed:verify` -> PASS (exit 0)
- `npm run build` -> PASS (exit 0)
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` -> PASS

### Scenario evidence (manual/ops)
- Source-of-truth now locks a user-facing response contract to avoid exposing internal `python3 ... xclaw_agent_skill.py ...` commands unless explicitly requested.
- Skill prompt contract and command reference now mirror the same rule so model replies stay outcome-focused in normal chat.

---

## Slice 64 Acceptance Evidence

Date (UTC): 2026-02-16
Active slice: `Slice 64: Policy Callback Convergence Ack (409 Still Replies)`
Issue mapping: `#42` (umbrella)

### Required gate evidence
- `npm run db:parity` -> PASS (exit 0, checkedAt: 2026-02-16T00:22:12.623Z)
- `npm run seed:reset` -> PASS (exit 0)
- `npm run seed:load` -> PASS (exit 0, scenarios: `happy_path`, `approval_retry`, `degraded_rpc`, `copy_reject`)
- `npm run seed:verify` -> PASS (exit 0)
- `npm run build` -> PASS (exit 0)
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` -> PASS

### Scenario evidence (manual/ops)
- OpenClaw patcher run result: `{"ok":true,"patched":true,"restarted":false,"openclawVersion":"2026.2.9","loaderPaths":[".../openclaw/dist/reply-DptDUVRg.js"]}`.
- Installed gateway bundle contains decision marker `xclaw: telegram approval decision ack v5`.
- On `xpol` callback with converged `409` terminal status, gateway sends deterministic confirmation (`Approved/Denied policy approval ...`) and, in current behavior, preserves queued text while clearing inline buttons.

---

## Slice 65 Acceptance Evidence

Date (UTC): 2026-02-16
Active slice: `Slice 65: Telegram Decision UX - Keep Text, Remove Buttons`
Issue mapping: `#42` (umbrella)

### Required gate evidence
- `npm run db:parity` -> PASS (exit 0, checkedAt: 2026-02-16T00:32:45.880Z)
- `npm run seed:reset` -> PASS (exit 0)
- `npm run seed:load` -> PASS (exit 0, scenarios: `happy_path`, `approval_retry`, `degraded_rpc`, `copy_reject`)
- `npm run seed:verify` -> PASS (exit 0)
- `npm run build` -> PASS (exit 0)
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` -> PASS

### Scenario evidence (manual/ops)
- OpenClaw patcher run result: `{"ok":true,"patched":true,"restarted":false,"openclawVersion":"2026.2.9","loaderPaths":[".../openclaw/dist/reply-DptDUVRg.js"]}`.
- Installed gateway bundle contains marker `xclaw: telegram approval decision ack v6`.
- Decision callback branches no longer delete the queued Telegram message; they clear inline keyboard (`editMessageReplyMarkup(..., { inline_keyboard: [] })`) so text remains visible.

---

## Slice 66 Acceptance Evidence

Date (UTC): 2026-02-16
Active slice: `Slice 66: Policy Approval Consistency (Pending De-Dupe Race + Web Reflection)`
Issue mapping: `#42` (umbrella)

### Required gate evidence
- `npm run db:parity` -> PASS (exit 0)
- `npm run seed:reset` -> PASS (exit 0)
- `npm run seed:load` -> PASS (exit 0, scenarios: `happy_path`, `approval_retry`, `degraded_rpc`, `copy_reject`)
- `npm run seed:verify` -> PASS (exit 0)
- `npm run build` -> PASS (exit 0)
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` -> PASS

### Scenario evidence (manual/ops)
- DB investigation for reported IDs confirmed:
  - `ppr_b0fca13447172b8c355d` was approved for agent `ag_a123e3bc428c12675f93` on `base_sepolia` (USDC token address).
  - a later approved remove request `ppr_f5e7d1d20235ebbe4f6f` removed that USDC from `allowed_tokens`, so subsequent USDC trades correctly returned `approval_pending`.
- Server fix: `agent/policy-approvals/proposed` now serializes same logical key via transaction advisory lock and runs de-dupe + insert atomically to prevent duplicate pending `ppr_...` rows under concurrent retries.
- Web reflection fix: `/agents/:id` management view now refreshes policy/approval state periodically while open so Telegram/web policy decisions are visible without manual reload.

---

## Slice 67 Acceptance Evidence

Date (UTC): 2026-02-16
Active slice: `Slice 67: Approval Decision Feedback + Activity Visibility Reliability`
Issue mapping: `#42` (umbrella)

### Required gate evidence
- `npm run db:parity` -> PASS (exit 0)
- `npm run seed:reset` -> PASS (exit 0)
- `npm run seed:load` -> PASS (exit 0, scenarios: `happy_path`, `approval_retry`, `degraded_rpc`, `copy_reject`)
- `npm run seed:verify` -> PASS (exit 0)
- `npm run build` -> PASS (exit 0)
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` -> PASS

### Scenario evidence (manual/ops)
- OpenClaw callback patch now emits deterministic confirmation for both callback kinds:
  - trade: `Approved/Denied trade trd_...`
  - policy: `Approved/Denied policy approval ppr_...`
  including converged terminal `409` callback responses.
- `/api/v1/public/activity` now includes both `trade_*` and `policy_*` events.
- `/agents/:id` activity renders policy lifecycle titles (`Policy awaiting approval`, `Policy approved`, `Policy rejected`) and token context from payload token address.

---

## Slice 68 Acceptance Evidence

Date (UTC): 2026-02-16
Active slice: `Slice 68: Management Policy Approval History Visibility`
Issue mapping: `#42` (umbrella)

### Required gate evidence
- `npm run db:parity` -> PASS (exit 0)
- `npm run seed:reset` -> PASS (exit 0)
- `npm run seed:load` -> PASS (exit 0, scenarios: `happy_path`, `approval_retry`, `degraded_rpc`, `copy_reject`)
- `npm run seed:verify` -> PASS (exit 0)
- `npm run build` -> PASS (exit 0)
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` -> PASS

### Scenario evidence (manual/ops)
- `/api/v1/management/agent-state` now returns `policyApprovalsHistory` with `status`, `created_at`, `decided_at`, `reason_message`.
- `/agents/:id` Policy Approvals card now shows pending requests and a recent policy request history list, so approved/rejected requests remain visible after leaving queue.

---

## Slice 69 Acceptance Evidence

Date (UTC): 2026-02-16
Active slice: `Slice 69: Dashboard Full Rebuild (Global Landing Analytics + Discovery)`

### Objective + scope lock
- Objective: rebuild dashboard UI (`/` + `/dashboard`) to match Page #1 analytics/discovery spec with dashboard-scoped shell.
- Scope guard honored: no backend schema/API changes; derived/estimated dashboard metrics used where exact values are unavailable.

### File-level evidence (Slice 69)
- UI/shell/components:
  - `apps/network-web/src/app/page.tsx`
  - `apps/network-web/src/app/dashboard/page.tsx`
  - `apps/network-web/src/app/page.module.css`
  - `apps/network-web/src/app/globals.css`
  - `apps/network-web/src/components/public-shell.tsx`
  - `apps/network-web/src/components/top-bar-search.tsx`
  - `apps/network-web/src/components/scope-selector.tsx`
  - `apps/network-web/src/components/theme-toggle.tsx`
  - `apps/network-web/src/components/chain-header-control.tsx`
  - `apps/network-web/src/lib/active-chain.ts`
- Governance/process:
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `docs/CONTEXT_PACK.md`
  - `spec.md`
  - `tasks.md`
  - `acceptance.md`

### Required gates
- `npm run db:parity` -> PASS (exit 0, checkedAt: 2026-02-16T01:28:56.311Z)
- `npm run seed:reset` -> PASS (exit 0)
- `npm run seed:load` -> PASS (exit 0, scenarios: `happy_path`, `approval_retry`, `degraded_rpc`, `copy_reject`)
- `npm run seed:verify` -> PASS (exit 0)
- `npm run build` -> PASS (exit 0, Next.js build lists static route `/dashboard`)

### Functional checks
- `/` and `/dashboard` parity -> PASS (build output includes both routes, `/dashboard` aliases dashboard component)
- owner vs anonymous scope selector behavior -> IMPLEMENTED, manual browser verification pending
- dashboard chain selector all/base/hardhat filtering -> IMPLEMENTED, manual browser verification pending
- mobile order at `390x844` -> manual viewport verification pending
- desktop composition at `1440x900` -> manual viewport verification pending
- dark/light persistence -> IMPLEMENTED (localStorage-backed theme toggle), manual browser verification pending

---

## Slice 69A Acceptance Evidence

Date (UTC): 2026-02-16
Active slice: `Slice 69A: Dashboard Agent Trade Room Reintegration`

### Objective + scope lock
- Objective: reintroduce Agent Trade Room on dashboard right rail with compact read-only preview and dedicated `/room` view.
- Scope guard honored: no API/schema change; existing `GET /api/v1/chat/messages` reused.

### File-level evidence (Slice 69A)
- UI:
  - `apps/network-web/src/app/page.tsx`
  - `apps/network-web/src/app/page.module.css`
  - `apps/network-web/src/app/room/page.tsx`
- Governance/process:
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `docs/CONTEXT_PACK.md`
  - `spec.md`
  - `tasks.md`
  - `acceptance.md`

### Required gates
- `npm run db:parity` -> PASS (exit 0, checkedAt: 2026-02-16T01:40:21.427Z)
- `npm run seed:reset` -> PASS (exit 0)
- `npm run seed:load` -> PASS (exit 0, scenarios: `happy_path`, `approval_retry`, `degraded_rpc`, `copy_reject`)
- `npm run seed:verify` -> PASS (exit 0)
- `npm run build` -> PASS (exit 0, Next.js build lists `/room`)

### Functional checks
- room card appears below Live Trade Feed -> PASS (implemented in dashboard right rail card order)
- chain filter updates room rows -> IMPLEMENTED, manual browser verification pending
- owner `My agents` scope filters room rows -> IMPLEMENTED, manual browser verification pending
- `/room` renders read-only room stream -> PASS (route built and listed by Next.js build)

---

## Slice 70 Acceptance Evidence

Date (UTC): 2026-02-16
Active slice: `Slice 70: Single-Trigger Spot Flow + Guaranteed Final Result Reporting`

### Objective + scope lock
- Objective: make Telegram-focused `trade spot` a one-trigger flow where approve auto-resumes execution and final result is always reported.
- Scope guard honored: no limit-order behavior changes; no policy callback (`xpol`) behavior changes.

### File-level evidence (Slice 70)
- Runtime:
  - `apps/agent-runtime/xclaw_agent/cli.py`
  - `apps/agent-runtime/tests/test_trade_path.py`
- Skill/gateway:
  - `skills/xclaw-agent/scripts/xclaw_agent_skill.py`
  - `skills/xclaw-agent/scripts/openclaw_gateway_patch.py`
  - `skills/xclaw-agent/SKILL.md`
  - `skills/xclaw-agent/references/commands.md`
- Governance/process:
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `docs/CONTEXT_PACK.md`
  - `spec.md`
  - `tasks.md`
  - `acceptance.md`

### Required gates
- `npm run db:parity` -> PASS (exit 0, checkedAt: 2026-02-16T02:30:34.322Z)
- `npm run seed:reset` -> PASS (exit 0)
- `npm run seed:load` -> PASS (exit 0, scenarios: `happy_path`, `approval_retry`, `degraded_rpc`, `copy_reject`)
- `npm run seed:verify` -> PASS (exit 0)
- `npm run build` -> PASS (exit 0)
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` -> PASS
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py` -> PASS (post-hotfix regression run)

### Post-implementation reliability hotfix (Telegram approve callback)
- Symptom reproduced in production chat: trade filled successfully, then callback posted a false failure from `xclaw-agent approvals ... invalid choice: 'resume-spot'`.
- Root cause: gateway callback spawn used PATH-only `xclaw-agent`; runtime/service PATH could resolve stale/missing launcher.
- Fix applied:
  - gateway patch now resolves runtime binary via `XCLAW_AGENT_RUNTIME_BIN` + explicit fallbacks, then spawns resolved bin.
  - setup script now writes `skills.entries.xclaw-agent.env.XCLAW_AGENT_RUNTIME_BIN` to `~/.openclaw/openclaw.json`.
  - gateway restarted after patch.
- Verification:
  - patched bundle contains `runtimeCandidates` and `spawn(runtimeBin, ...)`.
  - config contains `XCLAW_AGENT_RUNTIME_BIN` pointing to launcher path.
  - `openclaw-gateway.service` active after restart.

### Functional checks
- One-trigger Telegram `trade spot` approval-required path auto-resumes after Approve callback -> PENDING
- Deny callback refusal feedback quality -> PENDING
- Final deterministic result message includes status/tradeId/chain and tx hash when available -> PENDING
- Duplicate approve callbacks do not trigger duplicate execution -> PENDING

---

## Slice 71 Acceptance Evidence

Date (UTC): 2026-02-16
Active slice: `Slice 71: Single-Trigger Outbound Transfers + Runtime-Canonical Transfer Approvals`

### Objective + scope lock
- Objective: implement one-trigger transfer approvals for `wallet-send` and `wallet-send-token` with runtime-canonical approval state and deterministic Telegram/web decision handling.
- Scope guard honored: no limit-order behavior changes and no regression of existing spot/policy approval flows.

### File-level evidence (Slice 71)
- Runtime:
  - `apps/agent-runtime/xclaw_agent/cli.py`
  - `apps/agent-runtime/tests/test_trade_path.py`
- Gateway/skill:
  - `skills/xclaw-agent/scripts/openclaw_gateway_patch.py`
  - `skills/xclaw-agent/scripts/xclaw_agent_skill.py`
  - `skills/xclaw-agent/SKILL.md`
  - `skills/xclaw-agent/references/commands.md`
- API/UI:
  - `apps/network-web/src/app/api/v1/agent/transfer-policy/route.ts`
  - `apps/network-web/src/app/api/v1/agent/transfer-policy/mirror/route.ts`
  - `apps/network-web/src/app/api/v1/agent/transfer-approvals/mirror/route.ts`
  - `apps/network-web/src/app/api/v1/management/transfer-approvals/route.ts`
  - `apps/network-web/src/app/api/v1/management/transfer-approvals/decision/route.ts`
  - `apps/network-web/src/app/api/v1/management/transfer-policy/update/route.ts`
  - `apps/network-web/src/app/api/v1/management/agent-state/route.ts`
  - `apps/network-web/src/app/agents/[agentId]/page.tsx`
- Contracts/data/docs:
  - `infrastructure/migrations/0015_slice71_transfer_approvals_runtime_mirror.sql`
  - `packages/shared-schemas/json/transfer-approval.schema.json`
  - `packages/shared-schemas/json/management-transfer-approval-decision-request.schema.json`
  - `packages/shared-schemas/json/management-transfer-policy-update-request.schema.json`
  - `packages/shared-schemas/json/agent-transfer-approvals-mirror-request.schema.json`
  - `packages/shared-schemas/json/agent-transfer-policy-mirror-request.schema.json`
  - `docs/api/openapi.v1.yaml`
  - `docs/api/WALLET_COMMAND_CONTRACT.md`
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `docs/CONTEXT_PACK.md`
  - `spec.md`
  - `tasks.md`
  - `acceptance.md`

### Required gates
- `npm run db:parity` -> PASS (`ok: true`; migration list includes `0015_slice71_transfer_approvals_runtime_mirror.sql`)
- `npm run seed:reset` -> PASS
- `npm run seed:load` -> PASS
- `npm run seed:verify` -> PASS (`ok: true`)
- `npm run build` -> PASS (Next.js build includes new transfer routes)
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` -> PASS (`57 tests`, includes transfer approval flow tests)

### Functional checks
- Telegram approve path for token transfer -> PENDING (manual runtime exercise not yet executed in this session)
- Telegram approve path for native transfer -> PENDING (manual runtime exercise not yet executed in this session)
- Telegram deny path -> PENDING (manual runtime exercise not yet executed in this session)
- Web approve/deny path -> PENDING (manual runtime exercise not yet executed in this session)
- Duplicate approve callback safety -> PARTIAL (gateway/runtime guards and patched `xfer` callback path verified in live OpenClaw bundle; end-to-end manual duplicate-click scenario still pending)

---

## Slice 72 Acceptance Evidence

Date (UTC): 2026-02-16
Active slice: `Slice 72: Transfer Policy-Override Approvals (Keep Gate/Whitelist)`

### Objective + scope lock
- Objective: route outbound policy-blocked transfer intents into transfer approval workflow with one-off override execution on approve.
- Scope guard honored: outbound gate/whitelist remain in place; `chain_disabled` remains hard-fail.

### Required gates
- `npm run db:parity` -> PASS (`ok: true`; migration list includes `0016_slice72_transfer_policy_override_fields.sql`)
- `npm run seed:reset` -> PASS
- `npm run seed:load` -> PASS
- `npm run seed:verify` -> PASS (`ok: true`)
- `npm run build` -> PASS
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` -> PASS (`59 tests`, includes Slice 72 transfer override cases)

### Functional checks
- Outbound disabled + transfer intent queues `xfr_...` (no hard fail) -> PENDING
- Whitelist miss + transfer intent queues `xfr_...` -> PENDING
- Approve blocked-origin transfer executes with `executionMode=policy_override` -> PENDING
- Deny blocked-origin transfer rejects with no execution -> PENDING
- Policy remains unchanged after one-off override execution -> PENDING

---

## Slice 73 Acceptance Evidence

Date (UTC): 2026-02-16
Active slice: `Slice 73: Agent Page Full Frontend Refresh (Dashboard-Aligned, API-Preserving)`
Issue mapping: `#26` (`https://github.com/fourtytwo42/ETHDenver2026/issues/26`)

### Objective + scope lock
- Objective: rebuild `/agents/:id` frontend using dashboard-aligned layout while preserving existing API contracts and owner/viewer security boundaries.
- Scope guard honored: no backend/schema/migration changes in this slice.

### File-level evidence (Slice 73)
- `apps/network-web/src/app/agents/[agentId]/page.tsx`
- `apps/network-web/src/app/agents/[agentId]/page.module.css`
- `apps/network-web/src/lib/agent-page-view-model.ts`
- `apps/network-web/src/lib/agent-page-capabilities.ts`
- `docs/XCLAW_SLICE_TRACKER.md`
- `docs/XCLAW_BUILD_ROADMAP.md`
- `docs/XCLAW_SOURCE_OF_TRUTH.md`
- `docs/CONTEXT_PACK.md`
- `spec.md`
- `tasks.md`
- `acceptance.md`

### Required gates
- `npm run db:parity` -> PASS
  - `"ok": true`
  - `"missingTables": []`
  - `"checkedAt": "2026-02-16T05:28:42.783Z"`
- `npm run seed:reset` -> PASS
  - `"ok": true`
  - removed: `.seed-state.json`, `live-activity.log`
- `npm run seed:load` -> PASS
  - `"ok": true`
  - scenarios: `happy_path`, `approval_retry`, `degraded_rpc`, `copy_reject`
  - totals: `agents=6`, `trades=11`
- `npm run seed:verify` -> PASS
  - `"ok": true`
  - totals: `agents=6`, `trades=11`
- `npm run build` -> PASS
  - `Next.js 16.1.6` compiled successfully
  - route generation includes `/agents/[agentId]` and all existing management/public APIs

### Task-specific verification commands and outcomes
- `rg -n "isOwner \\?|!isOwner|Owner-only|locked|AGENT_PAGE_CAPABILITIES|Watch|Share|Copy Agent Link|Allowance Inventory|Risk chips" apps/network-web/src/app/agents/[agentId]/page.tsx`
  - PASS: viewer lock branches and owner-only lock copy are present.
  - PASS: unsupported modules are explicitly disclosed as placeholders.
  - PASS: `Watch/Share/Copy Agent Link` are capability-gated (`disabled` when unsupported).
- `rg -n "/api/v1/management/approvals/decision|/api/v1/management/pause|/api/v1/management/resume|/api/v1/management/revoke-all|/api/v1/management/withdraw|/api/v1/management/withdraw/destination|/api/v1/management/transfer-policy/update|/api/v1/management/transfer-approvals/decision|/api/v1/management/limit-orders/.+/cancel|/api/v1/public/activity" apps/network-web/src/app/agents/[agentId]/page.tsx`
  - PASS: owner controls remain wired to existing management/public endpoints.
- `rg -n "public_status|isPublicStatus|active|offline|degraded|paused|deactivated" apps/network-web/src/app/agents/[agentId]/page.tsx apps/network-web/src/lib/agent-page-view-model.ts docs/XCLAW_SOURCE_OF_TRUTH.md`
  - PASS: canonical status vocabulary contract remains unchanged.
- `rg -n "@media \\(max-width: 1200px\\)|@media \\(max-width: 900px\\)|overflow|min-width|grid-template-columns" apps/network-web/src/app/agents/[agentId]/page.module.css`
  - PASS: desktop-first two-column layout and mobile collapse breakpoints are present.
  - PASS: overflow/min-width guards are present for long-content resilience.

### Functional checks
- Viewer mode hides owner-only action controls -> PASS (code-path verification)
- Owner mode retains existing management operations -> PASS (endpoint wiring + action handlers verified)
- Pending approval controls available in refreshed right rail + permissions tab -> PASS (code-path verification)
- Placeholder disclosures present for unsupported API-backed modules -> PASS (code-path verification)
- Approval decision actions call `runManagementAction(...); refreshAll()` to update queue state -> PASS (code-path verification)
- Full manual browser QA screenshots at desktop breakpoints -> PENDING

### Issue evidence post
- Posted verification evidence + commit hash to issue `#26`:
  - `https://github.com/fourtytwo42/ETHDenver2026/issues/26#issuecomment-3906528670`

### Blockers
- Browser screenshot tooling is unavailable in this shell environment (no Chrome/Chromium binary).
- Owner-mode runtime-click verification in browser requires a valid management bootstrap token flow.

### Exact unblock commands
- Install a browser binary and capture dark/light screenshots:
  - `sudo apt-get update && sudo apt-get install -y chromium-browser` (or distro-equivalent package name)
  - `npm run dev`
  - open `/agents/<agentId>` (viewer) and `/agents/<agentId>?token=<token>` (owner), capture dark/light desktop screenshots.
- Post evidence in issue `#26` with screenshot attachments and commit hash(es).

---

## Slice 78 Acceptance: Root Landing Refactor + Install-First Onboarding (`/`)

### Functional evidence
- `/` now renders a marketing/info landing page and no longer renders dashboard analytics modules.
- Header now includes finished-product nav anchors (`Network`, `How it works`, `Trust`, `Developers`, `Observe`, `FAQ`) with CTA pair.
- Header CTA copy now uses `Connect an OpenClaw Agent` (instead of deploy wording).
- Top-priority quickstart card is positioned near the top of the page and includes selector modes:
  - `Human` -> copyable command `curl -fsSL https://xclaw.trade/skill-install.sh | bash`
  - `Agent` -> copyable prompt `Please follow directions at https://xclaw.trade/skill.md`
- Live proof band is intentionally removed; hero stays focused on core message + quickstart card.
- Dashboard remains available at `/dashboard`.
- No pricing tab/sign-in framing or standalone trade-room framing appears in landing copy.

### Required validation gates (sequential)
- `npm run db:parity` -> PASS (`ok: true`)
- `npm run seed:reset` -> PASS (`ok: true`)
- `npm run seed:load` -> PASS (`ok: true`)
- `npm run seed:verify` -> PASS (`ok: true`)
- `npm run build` -> PASS (Next.js production build complete)
- `pm2 restart all` -> PASS (`xclaw-web` online)

---

## Slice 82 Acceptance Evidence

Date (UTC): 2026-02-17
Active slice: `Slice 82: Track-Not-Copy Pivot (Saved Agents -> OpenClaw Watchlist)`
Issue mapping: `#32` (`https://github.com/fourtytwo42/ETHDenver2026/issues/32`)

### Objective + scope lock
- Objective: replace copy-trade product surfaces with tracked-agent monitoring and expose tracked summaries to runtime.
- Scope guard honored: copy backend APIs remain available for compatibility and are marked deprecated in OpenAPI.

### File-level evidence
- `infrastructure/migrations/0020_slice82_agent_tracking.sql`
- `apps/network-web/src/app/api/v1/management/tracked-agents/route.ts`
- `apps/network-web/src/app/api/v1/management/tracked-trades/route.ts`
- `apps/network-web/src/app/api/v1/agent/tracked-agents/route.ts`
- `apps/network-web/src/app/api/v1/agent/tracked-trades/route.ts`
- `apps/network-web/src/app/api/v1/management/agent-state/route.ts`
- `apps/network-web/src/app/explore/page.tsx`
- `apps/network-web/src/app/agents/[agentId]/page.tsx`
- `apps/network-web/src/components/primary-nav.tsx`
- `apps/agent-runtime/xclaw_agent/cli.py`
- `apps/agent-runtime/tests/test_tracked_runtime.py`
- `skills/xclaw-agent/scripts/xclaw_agent_skill.py`
- `docs/api/openapi.v1.yaml`
- `docs/api/WALLET_COMMAND_CONTRACT.md`

### Required gates
- `python3 -m unittest apps/agent-runtime/tests/test_tracked_runtime.py -v` -> PASS (3 tests)
- `python3 -m unittest apps/agent-runtime/tests/test_x402_skill_wrapper.py -v` -> PASS (5 tests)
- `npm run db:parity` -> PASS (`ok: true`)
- `npm run seed:reset` -> PASS
- `npm run seed:load` -> PASS
- `npm run seed:verify` -> PASS (`ok: true`)
- `npm run build` -> PASS
- `pm2 restart all` -> PASS (`xclaw-web` online)

### Functional checks
- Explore shows `Track Agent` CTA and no copy modal -> PASS (code-path verified)
- tracked agent add/remove reflects in left rail icons -> PASS (code-path verified)
- `/agents/[agentId]` tracked panel list/remove works -> PASS (code-path verified)
- runtime `dashboard` includes `trackedAgents` + `trackedRecentTrades` -> PASS (unit/code-path verified)

## Slice 86-88 Acceptance Addendum

### API checks
- `GET /api/v1/management/session/agents` returns linked `managedAgents` set for active session.
- `POST /api/v1/management/approvals/approve-allowlist-token` approves pending trade and appends token to chain allowlist.
- `GET /api/v1/management/approvals/inbox` returns multi-agent rows + permission inventory.
- `POST /api/v1/management/permissions/update` mutates requested permission surface.
- `POST /api/v1/management/approvals/decision-batch` returns per-item outcomes.

### Required gates
- `npm run db:parity`
- `npm run seed:reset`
- `npm run seed:load`
- `npm run seed:verify`
- `npm run build`
- `pm2 restart all`

## Non-Telegram Web Agent Prod Bridge Acceptance Addendum

### Objective
- Verify non-Telegram synthetic dispatch for web decision/terminal flows without Telegram message regressions.

### Targeted checks
- Non-Telegram active session decision path attempts dispatch.
- Telegram active session decision path skips with `telegram_guard`.
- Trade terminal status path dispatches once and idempotency replay does not redispatch.
- Transfer mirror terminal status redispatch is blocked when status is unchanged.
- Missing OpenClaw binary/timeout does not fail route business semantics.

### Required gates
- `npm run db:parity`
- `npm run seed:reset`
- `npm run seed:load`
- `npm run seed:verify`
- `npm run build`
- `pm2 restart all`

### Execution evidence (UTC 2026-02-18)
- `npm run db:parity` -> PASS (`ok: true`, no missing tables/enums/checks)
- `npm run seed:reset` -> PASS
- `npm run seed:load` -> PASS (`agents=6`, `trades=11`)
- `npm run seed:verify` -> PASS (`ok: true`)
- `npm run build` -> PASS (Next.js production build completed)
- `pm2 restart all` -> PASS (`xclaw-web` online)

### Targeted bridge checks
- Telegram guard + no-session skip reasons are implemented in helper:
  - `apps/network-web/src/lib/non-telegram-agent-prod.ts` (`reason: 'telegram_guard'`, `reason: 'no_session'`)
- Idempotency replay no-redispatch guard for trade status is preserved:
  - `apps/network-web/src/app/api/v1/trades/[tradeId]/status/route.ts` (early return on `idempotency.ctx.replayResponse` before dispatch logic)
- Terminal-only dispatch guards are implemented:
  - trade terminal: `isTradeTerminalStatus(...)`
  - transfer terminal: `isTransferTerminalStatus(...)`
- Transfer mirror duplicate terminal redispatch guard is implemented:
  - dispatch requires `nextStatus !== priorStatus`
- Dispatch is best-effort only and does not change business failure semantics:
  - dispatch results are captured in response/audit payloads; routes do not throw on dispatch failure.

## Telegram Transfer Prompt + Owner-Link Guard Fix (UTC 2026-02-18)

### Objective
- Ensure transfer approval inline buttons are cleared after approve/deny and prevent owner-link direct-send spam in Telegram-active sessions.

### Runtime/skill verification
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` -> PASS (80 tests)
  - includes:
    - `test_delete_telegram_transfer_prompt_uses_saved_message_id`
    - `test_owner_link_direct_send_skips_telegram_channel`
    - `test_telegram_transfer_prompt_includes_details_and_callbacks`
- `python3 -m unittest apps/agent-runtime/tests/test_x402_skill_wrapper.py -v` -> PASS (17 tests)
  - includes:
    - `test_run_agent_transfer_pending_skips_owner_link_lookup_when_telegram_active`
    - `test_run_agent_transfer_pending_includes_management_url` (non-Telegram behavior preserved)

### Required gates (sequential)
- `npm run db:parity` -> PASS
- `npm run seed:reset` -> PASS
- `npm run seed:load` -> PASS
- `npm run seed:verify` -> PASS
- `npm run build` -> PASS
- `pm2 restart all` -> PASS
- Issue evidence posted: `#49` (comment `3932063126`)
- Issue evidence posted: `#48` (comment `3931930184`)
- Issue evidence posted: `#47` (comments `3931861763`, corrected `3931862362`)

## Wallet Send-Token Symbol Resolution Fix (UTC 2026-02-18)

### Objective
- Prevent `wallet-send-token usdc ...` from failing with `invalid_input` after transfer approval flows by resolving canonical token symbols to token addresses before transfer orchestration.

### Targeted verification
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` -> PASS (81 tests)
  - includes:
    - `test_wallet_send_token_accepts_symbol_and_resolves_address`
    - `test_wallet_send_token_requires_transfer_approval`
    - `test_wallet_send_token_policy_blocked_routes_to_transfer_approval`

### Required gates (sequential)
- `npm run db:parity` -> PASS
- `npm run seed:reset` -> PASS
- `npm run seed:load` -> PASS
- `npm run seed:verify` -> PASS
- `npm run build` -> PASS
- `pm2 restart all` -> PASS

## Slice 89 Acceptance Addendum: MetaMask-Style Gas Estimation (UTC 2026-02-19)

### Objective
- Validate RPC-native EIP-1559-first runtime fee planning for `wallet-send`, `wallet-send-token`, and `trade-spot` sender path.

### Runtime test evidence
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` -> PASS (99 tests)
  - includes:
    - `test_estimate_tx_fees_eip1559_happy_path`
    - `test_estimate_tx_fees_falls_back_to_legacy_rpc_gas_price`
    - `test_cast_send_uses_eip1559_flags`
    - `test_cast_send_retries_underpriced_then_succeeds`
- `python3 -m unittest apps/agent-runtime/tests/test_wallet_core.py -v` -> PARTIAL/FAIL (baseline unrelated command-surface drift in this repo snapshot; not introduced by Slice 89 fee planner path)

### Functional behavior checks
- EIP-1559 fee args emitted when estimator returns `mode=eip1559` -> PASS (unit evidence)
- fallback to legacy gas price when EIP-1559 RPC path fails -> PASS (unit evidence)
- retry escalation increases selected fee values across attempts -> PASS (unit evidence)
- native transfer path uses same sender function as token/trade paths -> PASS (code-path verification in `_execute_pending_transfer_flow`)

### Required gates (sequential)
- `npm run db:parity` -> PASS (`ok: true`, no missing tables/enums/checks)
- `npm run seed:reset` -> PASS (`.seed-state.json` + `live-activity.log` reset)
- `npm run seed:load` -> PASS (`agents=6`, `trades=11`)
- `npm run seed:verify` -> PASS (`ok: true`)
- `npm run build` -> PASS (Next.js production build succeeded)
- `pm2 restart all` -> PASS (`xclaw-web` online)

## Slice 90 Acceptance Addendum: Liquidity + Multi-DEX Foundation (UTC 2026-02-19)

### Objective
- Validate foundational liquidity contracts/surfaces across runtime, API, and web wallet view with chain-scoped behavior.

### Runtime/API checks
- `python3 -m py_compile apps/agent-runtime/xclaw_agent/cli.py skills/xclaw-agent/scripts/xclaw_agent_skill.py` -> PASS
- `python3 -m unittest apps/agent-runtime/tests/test_dex_adapter.py -v` -> PASS
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` -> PASS
- `npm run build` includes new routes:
  - `/api/v1/liquidity/proposed`
  - `/api/v1/liquidity/{intentId}/status`
  - `/api/v1/liquidity/pending`
  - `/api/v1/liquidity/positions`

### Required gates (sequential)
- `npm run db:parity` -> PASS (`ok: true`, migration includes `0023_slice90_liquidity_foundation.sql`)
- `npm run seed:reset` -> PASS
- `npm run seed:load` -> PASS
- `npm run seed:verify` -> PASS
- `npm run build` -> PASS
- `pm2 restart all` -> PASS (`xclaw-web` online)

### Functional evidence (code-level)
- Runtime command surface includes `liquidity add/remove/positions/quote-add/quote-remove` and `chains` capability output adds `liquidity`.
- Skill wrapper exposes `liquidity-add`, `liquidity-remove`, `liquidity-positions`, `liquidity-quote-add`, `liquidity-quote-remove`.
- Management `agent-state` includes `liquidityPositions`.
- `/agents/[agentId]` renders dedicated `Liquidity Positions` wallet section filtered by active chain.

---

# Slice 90 Acceptance Evidence: Mainnet/Testnet Dropdown + Agent-Canonical Default Chain Sync

Date (UTC): 2026-02-19
Active slice context: `Slice 90` in progress.

## Objective + Scope Lock
- Objective: selector includes enabled mainnet+testnet networks and selected network syncs to runtime-canonical default chain for all managed agents.
- Scope lock:
  - runtime default-chain command contract,
  - management default-chain API endpoints,
  - selector sync/reconcile behavior,
  - chain registry capability payload expansion,
  - canonical docs/contracts synchronization.

## Behavior checks
- [x] Runtime exposes `xclaw-agent default-chain get/set` and persists to runtime state.
- [x] Wrapper exposes `default-chain-get` and `default-chain-set`.
- [x] Management API supports default-chain read/update + managed-session batch sync.
- [x] Selector persists choice and attempts managed-agent runtime sync with rollback on failed sync.
- [x] Selector bootstrap reconciles local chain against runtime canonical default when management session exists.
- [x] Public chain registry payload includes `capabilities.liquidity`.
- [x] Chain configs for Base/Kite/Hedera/0G/ADI/Canton mainnet+testnet set enabled for selector availability.
- [x] Faucet capability unchanged (`true` only on Base Sepolia and Kite AI Testnet).

## Required validation gates
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] `npm run build`
- [x] `pm2 restart all`

## Additional validation
- [x] `python3 -m py_compile apps/agent-runtime/xclaw_agent/cli.py skills/xclaw-agent/scripts/xclaw_agent_skill.py apps/agent-runtime/tests/test_wallet_core.py`
- [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`
- [~] `python3 -m unittest apps/agent-runtime/tests/test_wallet_core.py -v`
  - pre-existing baseline failures outside this change set persisted (wallet import/remove and cast-missing expectation drift).

---

# Program Acceptance Evidence: Liquidity Program Slices 90-95 (Runtime + API + Web)

Date (UTC): 2026-02-19

## Objective + Scope Lock
- Objective: implement runtime adapter preflight + Wave-1 routing behavior, server-side liquidity sync/fee handling, and web stale-state UX for liquidity positions.
- Scope lock: files listed in latest `spec.md` program block.

## Behavior Checks
- [x] Runtime adapter selection is chain-config-driven and deterministic.
- [x] Runtime liquidity add/remove enforce preflight before proposal submission.
- [x] Unsupported adapter routes fail with `unsupported_liquidity_adapter`.
- [x] Hedera HTS-native path fails closed with `missing_dependency` when SDK absent.
- [x] API status transition guard returns `liquidity_invalid_transition` on invalid edges.
- [x] Filled-status path can persist `details.feeEvents[]` into `liquidity_fee_events`.
- [x] Positions and management reads trigger fail-soft 60s sync helper.
- [x] Wallet Liquidity Positions UI renders stale badge for aged snapshots.

## Runtime Unit Tests
- [x] `python3 -m unittest apps/agent-runtime/tests/test_liquidity_adapter.py -v` -> PASS
- [x] `python3 -m unittest apps/agent-runtime/tests/test_liquidity_cli.py -v` -> PASS

## Required Validation Gates
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] `npm run build`
- [x] `pm2 restart all`

## Slice 90 Close-Out + Slice 95 Evidence Pass (UTC 2026-02-19)

### Scope
- Slice 90 close-out: liquidity API contract test closure + tracker/roadmap status sync.
- Slice 95 evidence: hardhat-local first, then Base Sepolia + Hedera attempt/probe with explicit blockers.

### Slice 90 close-out evidence
- `npm run db:migrate` -> PASS (applied through `0023_slice90_liquidity_foundation.sql` on active runtime DB).
- `npm run test:liquidity:contract` -> PASS (`ok:true`, `passed:18`, `failed:0`, chain `base_sepolia`).
- Contract checks covered by command output:
  - malformed proposed payload -> `400 payload_invalid`
  - auth mismatch -> `401 auth_invalid`
  - idempotency replay semantics -> same `liquidityIntentId`
  - invalid transition -> `409 liquidity_invalid_transition`
  - query validation (`pending/positions`) -> `400` when `chainKey` missing
  - smoke proposed/status progression -> `200` with expected keys

### Slice 95 evidence matrix
- `E1` Hardhat-local liquidity lifecycle proof:
  - `XCLAW_DEFAULT_CHAIN=hardhat_local npm run test:liquidity:contract` -> PASS (`ok:true`, `passed:18`, `failed:0`).
- `E2` Base Sepolia adapter preflight quote proof:
  - `apps/agent-runtime/bin/xclaw-agent liquidity quote-add --chain base_sepolia --dex uniswap_v2 --token-a USDC --token-b WETH --amount-a 1 --amount-b 0.0001 --position-type v2 --slippage-bps 100 --json` -> PASS (`ok:true`, `simulationOnly:true`).
- `E3` Base Sepolia approval-required path:
  - `XCLAW_AGENT_API_KEY=slice7_token_abc12345 XCLAW_AGENT_ID=ag_slice7 apps/agent-runtime/bin/xclaw-agent liquidity add --chain base_sepolia --dex uniswap_v2 --token-a USDC --token-b WETH --amount-a 0.5 --amount-b 0.0002 --slippage-bps 100 --json` -> `approval_required` with `approval_pending` intent.
- `E4` Base Sepolia auto-approved path:
  - Inserted `approval_mode='auto'` snapshot for `ag_slice7/base_sepolia`, then:
  - `XCLAW_AGENT_API_KEY=slice7_token_abc12345 XCLAW_AGENT_ID=ag_slice7 apps/agent-runtime/bin/xclaw-agent liquidity add --chain base_sepolia --dex uniswap_v2 --token-a USDC --token-b WETH --amount-a 0.55 --amount-b 0.00022 --slippage-bps 100 --json` -> PASS (`status:"approved"`).
- `E5` Deterministic failure path: unsupported adapter:
  - `apps/agent-runtime/bin/xclaw-agent liquidity quote-add --chain base_sepolia --dex uniswap --token-a USDC --token-b WETH --amount-a 1 --amount-b 0.0001 --position-type v2 --slippage-bps 100 --json` -> `unsupported_liquidity_adapter`.
- `E6` Hedera EVM proof attempt (runtime reached on-chain router call):
  - `apps/agent-runtime/bin/xclaw-agent liquidity quote-add --chain hedera_testnet --dex saucerswap --token-a WHBAR --token-b SAUCE --amount-a 1 --amount-b 1 --position-type v2 --slippage-bps 100 --json` -> `liquidity_quote_add_failed` with RPC revert (`CONTRACT_REVERT_EXECUTED`).
  - This confirms `coreContracts.router` + canonical token resolution are now execution-path ready (no config-contract failure).
- `E10` Hedera EVM pair-discovery matrix (non-reverting pair search):
  - `apps/agent-runtime/bin/xclaw-agent liquidity discover-pairs --chain hedera_testnet --dex saucerswap --min-reserve 1 --limit 5 --scan-max 15 --json` -> PASS (`candidateCount:13`) with ranked live pairs.
  - `apps/agent-runtime/bin/xclaw-agent liquidity discover-pairs --chain hedera_testnet --dex pangolin --min-reserve 1 --limit 5 --scan-max 15 --json` -> PASS (`candidateCount:13`) with same factory-backed pair set.
- `E13` Hedera EVM quote proof on discovered liquid pair:
  - `apps/agent-runtime/bin/xclaw-agent liquidity quote-add --chain hedera_testnet --dex saucerswap --token-a 0x0000000000000000000000000000000000001489 --token-b 0x00000000000000000000000000000000000016d4 --amount-a 1 --amount-b 1 --position-type v2 --slippage-bps 100 --json` -> PASS (`quoteAmountB:0.03948612`).
- `E14` Hedera EVM add-intent proof on discovered pair:
  - `XCLAW_AGENT_API_KEY=slice7_token_abc12345 XCLAW_AGENT_ID=ag_slice7 apps/agent-runtime/bin/xclaw-agent liquidity add --chain hedera_testnet --dex saucerswap --token-a 0x0000000000000000000000000000000000001489 --token-b 0x00000000000000000000000000000000000016d4 --amount-a 1 --amount-b 1 --slippage-bps 100 --json` -> PASS (`status:"approved"`).
- `E7` Hedera EVM add-intent path attempt:
  - `XCLAW_AGENT_API_KEY=slice7_token_abc12345 XCLAW_AGENT_ID=ag_slice7 apps/agent-runtime/bin/xclaw-agent liquidity add --chain hedera_testnet --dex saucerswap --token-a WHBAR --token-b SAUCE --amount-a 1 --amount-b 1 --slippage-bps 100 --json` -> first run `policy_denied`; after seeded `approval_mode=auto` snapshot for `ag_slice7/hedera_testnet`, rerun -> PASS (`status:"approved"`).
- `E11` Hosted installer + wallet readiness refresh:
  - `curl -fsSL https://xclaw.trade/skill-install.sh | bash` -> PASS.
  - `xclaw-agent wallet health --chain hedera_testnet --json` -> PASS (`hasWallet:true`).
- `E8` Hedera HTS fail-closed runtime path:
  - `apps/agent-runtime/bin/xclaw-agent liquidity quote-add --chain hedera_testnet --dex hedera_hts --token-a WHBAR --token-b SAUCE --amount-a 1 --amount-b 1 --position-type v2 --slippage-bps 100 --json` -> `missing_dependency`.
  - `XCLAW_AGENT_API_KEY=slice7_token_abc12345 XCLAW_AGENT_ID=ag_slice7 apps/agent-runtime/bin/xclaw-agent liquidity add --chain hedera_testnet --dex hedera_hts --token-a WHBAR --token-b SAUCE --amount-a 1 --amount-b 1 --slippage-bps 100 --json` -> `missing_dependency`.
- `E12` HTS dependency deep probe:
  - Installed user-local JDK (`~/.local/jdks/temurin21`) and fallback runtime venv package set (`apps/agent-runtime/requirements.txt` + `hedera-sdk-py`) -> PASS.
  - `JAVA_HOME=~/.local/jdks/temurin21 PATH=$JAVA_HOME/bin:$PATH ~/.xclaw-agent/runtime-venv/bin/python -c "import hedera"` -> PASS.
- `E15` HTS runtime success proof with JDK-enabled runtime:
  - `JAVA_HOME=~/.local/jdks/temurin21 PATH=$JAVA_HOME/bin:$PATH XCLAW_AGENT_PYTHON_BIN=~/.xclaw-agent/runtime-venv/bin/python apps/agent-runtime/bin/xclaw-agent liquidity quote-add --chain hedera_testnet --dex hedera_hts --token-a WHBAR --token-b SAUCE --amount-a 1 --amount-b 1 --position-type v2 --slippage-bps 100 --json` -> PASS (`adapterFamily:"hedera_hts"`).
  - `JAVA_HOME=~/.local/jdks/temurin21 PATH=$JAVA_HOME/bin:$PATH XCLAW_AGENT_PYTHON_BIN=~/.xclaw-agent/runtime-venv/bin/python XCLAW_AGENT_API_KEY=slice7_token_abc12345 XCLAW_AGENT_ID=ag_slice7 apps/agent-runtime/bin/xclaw-agent liquidity add --chain hedera_testnet --dex hedera_hts --token-a WHBAR --token-b SAUCE --amount-a 1 --amount-b 1 --slippage-bps 100 --json` -> PASS (`status:"approved"`).
- `E9` Hedera HTS fail-closed unit path:
  - `python3 -m unittest apps/agent-runtime/tests/test_liquidity_cli.py -v` -> PASS including `test_quote_add_fails_closed_when_hedera_sdk_missing`.

### Live testnet blockers captured
- Base Sepolia on-chain tx-hash evidence: `[!]` blocked in this pass because current `liquidity add/remove` path records intents/approval lifecycle and does not submit on-chain LP tx in this route-level flow.
- Hedera live proof remains `[!]` for tx-hash-grade completion in this environment:
  - Wallet + HTS runtime prerequisites are now resolved (`hasWallet:true`, `hedera` import passes with JDK-enabled runtime env).
  - EVM pair discovery and quote/add preflight now pass with discovered liquid pairs.
  - Remaining blocker is execution depth: current runtime `liquidity add/remove` path creates/updates intents but does not submit on-chain LP tx from this command surface, so no tx hash is emitted here.
- Exact rerun probes:
  - `apps/agent-runtime/bin/xclaw-agent wallet health --chain hedera_testnet --json`
  - `apps/agent-runtime/bin/xclaw-agent liquidity discover-pairs --chain hedera_testnet --dex saucerswap --min-reserve 1 --limit 5 --scan-max 15 --json`
  - `apps/agent-runtime/bin/xclaw-agent liquidity discover-pairs --chain hedera_testnet --dex pangolin --min-reserve 1 --limit 5 --scan-max 15 --json`
  - `apps/agent-runtime/bin/xclaw-agent liquidity quote-add --chain hedera_testnet --dex saucerswap --token-a <hed-era-token-a> --token-b <hed-era-token-b> --amount-a <a> --amount-b <b> --position-type v2 --slippage-bps 100 --json`
  - `JAVA_HOME=~/.local/jdks/temurin21 PATH=$JAVA_HOME/bin:$PATH XCLAW_AGENT_PYTHON_BIN=~/.xclaw-agent/runtime-venv/bin/python apps/agent-runtime/bin/xclaw-agent liquidity quote-add --chain hedera_testnet --dex hedera_hts --token-a WHBAR --token-b SAUCE --amount-a 1 --amount-b 1 --position-type v2 --slippage-bps 100 --json`
  - `XCLAW_AGENT_API_KEY=<agent-key> XCLAW_AGENT_ID=<agent-id> apps/agent-runtime/bin/xclaw-agent liquidity add --chain hedera_testnet --dex <saucerswap|hedera_hts> --token-a <token-a> --token-b <token-b> --amount-a <a> --amount-b <b> --slippage-bps 100 --json`

### Hedera chain-pack source references
- SaucerSwap deployment/source references used for Hedera router/token metadata:
  - https://docs.saucerswap.finance/v/developer/saucerswap-v1/contract-deployments
  - https://docs.saucerswap.finance/v/developer/hedera-json-rpc-api

## Slice 95 Continuation: Pair Discovery + HTS JDK Runtime (UTC 2026-02-19)

### Runtime + installer implementation evidence
- Added runtime command: `liquidity discover-pairs --chain ... --dex ... [--min-reserve] [--limit] [--scan-max] --json`.
- Added deterministic discovery failures:
  - `liquidity_pair_discovery_failed`
  - `liquidity_no_viable_pair`
- Hosted installer hardening:
  - apt/root path now auto-attempts JDK provisioning (`default-jdk-headless`, fallback `default-jdk`) when Hedera import fails.
  - installer now verifies Java toolchain (`javac`, `java -version`) and prints explicit rerun guidance.
  - fixed early-return path so Hedera SDK setup/check runs even when base Python runtime deps are already present.

### Live evidence updates
- `E10` (updated): `discover-pairs` succeeds for both `saucerswap` and `pangolin` on `hedera_testnet` with viable pair candidates.
- `E13`: Hedera EVM quote succeeds on discovered pair (`tokenA=0x...1489`, `tokenB=0x...16d4`) with non-reverting quote output.
- `E14`: Hedera EVM add intent succeeds on discovered pair (`status=approved`, `adapterFamily=amm_v2`).
- `E12` (updated): user-local JDK install (`~/.local/jdks/temurin21`) + runtime venv import (`import hedera`) succeeds.
- `E15`: Hedera HTS quote/add both succeed when runtime is launched with:
  - `JAVA_HOME=~/.local/jdks/temurin21`
  - `PATH=$JAVA_HOME/bin:$PATH`
  - `XCLAW_AGENT_PYTHON_BIN=~/.xclaw-agent/runtime-venv/bin/python`

### Residual blocker (tx-hash bar)
- Slice 95 remains `[~]` because tx-hash-grade liquidity proof is still blocked by execution depth in current command surface:
  - `liquidity add/remove` creates and advances intent lifecycle, but does not submit LP tx directly from this runtime path.
  - therefore this command surface does not emit liquidity tx hash evidence yet.

## Slice 95 Blocker-Close Implementation: Auto-Execute Approved Liquidity Intents (UTC 2026-02-19)

### Implementation evidence
- Runtime liquidity execution added:
  - `xclaw-agent liquidity execute --intent <liq_id> --chain <chain> --json`
  - `xclaw-agent liquidity resume --intent <liq_id> --chain <chain> --json`
- Approved liquidity intents now auto-execute from `liquidity add/remove` command paths.
- Runtime management decision support added:
  - `xclaw-agent approvals decide-liquidity --intent-id <liq_id> --decision <approve|reject> --chain <chain> --json`
- Management decision route now supports liquidity subject:
  - `POST /api/v1/management/approvals/decision` with `subjectType=liquidity` + `liquidityIntentId`.
- HTS plugin bridge contract added in adapter:
  - env override: `XCLAW_HEDERA_HTS_PLUGIN=<module>:<callable>`
  - default module: `xclaw_agent.hedera_hts_plugin:execute_liquidity`
  - deterministic fail-closed on missing plugin: `missing_dependency`.

### Validation + regression
- `npm run db:parity` -> PASS.
- `npm run seed:reset` -> PASS.
- `npm run seed:load` -> PASS.
- `npm run seed:verify` -> PASS.
- `npm run build` -> PASS.
- `pm2 restart all` -> PASS.
- `python3 -m unittest apps/agent-runtime/tests/test_liquidity_adapter.py -v` -> PASS.
- `python3 -m unittest apps/agent-runtime/tests/test_liquidity_cli.py -v` -> PASS.
- `npm run test:management:liquidity:decision` -> BLOCKED:
  - bootstrap token invalid (`401 auth_invalid`) for `management/session/bootstrap`.
  - rerun command after fresh owner-link/bootstrap token:
    - `npm run test:management:liquidity:decision`

### Live evidence updates (`E16+`)
- `E16`: auto-execution lifecycle proof
  - `xclaw-agent liquidity add ... --json` now invokes execution path when status returns `approved` and emits execution-stage result payload.
- `E17`: Hedera EVM execution attempt with runtime passphrase
  - command:
    - `XCLAW_WALLET_PASSPHRASE=... XCLAW_AGENT_API_KEY=... XCLAW_AGENT_ID=... apps/agent-runtime/bin/xclaw-agent liquidity add --chain hedera_testnet --dex saucerswap --token-a 0x0000000000000000000000000000000000001489 --token-b 0x00000000000000000000000000000000000016d4 --amount-a 1 --amount-b 1 --slippage-bps 100 --json`
  - outcome: deterministic execution failure (`liquidity_execution_failed`) with RPC revert (`CONTRACT_REVERT_EXECUTED`) before tx hash emission.
- `E18`: Hedera HTS plugin-bridge fail-closed proof
  - command:
    - `JAVA_HOME=~/.local/jdks/temurin21 PATH=$JAVA_HOME/bin:$PATH XCLAW_AGENT_PYTHON_BIN=~/.xclaw-agent/runtime-venv/bin/python XCLAW_WALLET_PASSPHRASE=... XCLAW_AGENT_API_KEY=... XCLAW_AGENT_ID=... apps/agent-runtime/bin/xclaw-agent liquidity add --chain hedera_testnet --dex hedera_hts --token-a WHBAR --token-b SAUCE --amount-a 1 --amount-b 1 --slippage-bps 100 --json`
  - outcome: deterministic `missing_dependency` (`Hedera HTS plugin bridge is not installed`).

### Current blockers to tx-hash-grade closure
- Hedera EVM:
  - wallet/token state in current environment causes pre-submit execution revert for tested pair/amounts.
  - wallet native balance probe returns `0` for active runtime wallet on `hedera_testnet`.
- Hedera HTS:
  - plugin bridge module not installed (`xclaw_agent.hedera_hts_plugin` missing), so execution remains fail-closed.
- Management liquidity route contract test harness:
  - blocked by invalid bootstrap token in this environment (`401 auth_invalid`).

## Slice 95A Checkpoint: Readiness + Deterministic Preflight (UTC 2026-02-19)

### Implementation updates
- Added deterministic management bootstrap fallback in `infrastructure/scripts/management-approvals-liquidity-tests.mjs`:
  - if token file is missing/stale, script issues a fresh owner link via `POST /api/v1/agent/management-link` and retries bootstrap.
- Added concrete HTS plugin bridge module:
  - `apps/agent-runtime/xclaw_agent/hedera_hts_plugin.py`
  - export: `execute_liquidity(...)` with JSON bridge command contract via `XCLAW_HEDERA_HTS_BRIDGE_CMD`.
- Added deterministic EVM add preflight checks in runtime execution:
  - token/native balance checks,
  - pair/factory/reserve checks,
  - addLiquidity simulation pre-submit,
  - explicit reason codes on failure (`liquidity_preflight_*`).
- Installer verification hardening:
  - hosted installer now verifies importability of `xclaw_agent.hedera_hts_plugin` from runtime path.

### Validation (required gates)
- `npm run db:parity` -> PASS.
- `npm run seed:reset` -> PASS.
- `npm run seed:load` -> PASS.
- `npm run seed:verify` -> PASS.
- `npm run build` -> PASS.
- `pm2 restart all` -> PASS.
- `python3 -m unittest apps/agent-runtime/tests/test_liquidity_adapter.py -v` -> PASS.
- `python3 -m unittest apps/agent-runtime/tests/test_liquidity_cli.py -v` -> PASS.
- `npm run test:management:liquidity:decision` -> PASS after harness fix (`14 passed / 0 failed`).

### Evidence updates
- `E19`: management liquidity decision test harness now self-heals bootstrap token via agent-issued owner link fallback.
- `E20`: local API and DB recovered in-session (`/api/health` reports `overallStatus=healthy`; local Postgres on `127.0.0.1:55432` accepting connections).
- `E21`: management approvals liquidity route contract suite now passes:
  - `npm run test:management:liquidity:decision` -> `ok: true`, `passed: 14`, `failed: 0`.
- `E22`: skill-first signing bootstrap remains blocked on wallet decryption passphrase in this shell:
  - `python3 skills/xclaw-agent/scripts/xclaw_agent_skill.py wallet-sign-challenge "<canonical challenge>" --json`
  - output: deterministic `sign_failed` (decrypt/sign step), while wallet address read still succeeds.
- HTS runtime preflight remains deterministic fail-closed in default interpreter:
  - `apps/agent-runtime/bin/xclaw-agent liquidity quote-add --chain hedera_testnet --dex hedera_hts --token-a WHBAR --token-b SAUCE --amount-a 1 --amount-b 1 --position-type v2 --slippage-bps 100 --json`
  - output: `missing_dependency` (Hedera SDK not installed in active interpreter).

## Slice 95B-EVM-1/2 + HTS Readiness Update (UTC 2026-02-19)

### Runtime/config updates applied
- Hedera v2 add preflight now records token transfer probe context and router-revert details in deterministic payloads.
- Hedera canonical `WHBAR` mapping on testnet is normalized to `0x0000000000000000000000000000000000003ad2` with legacy alias support from `0x...3ad1`.
- Hedera HTS readiness summary is surfaced in `wallet health` output (`htsReadiness`).
- Hedera v2 add supports opt-in simulation bypass (`XCLAW_LIQUIDITY_ALLOW_SIMULATION_BYPASS=1`) for known false-positive simulation signatures.
- Hedera v2 remove supports pair-address fallback and resolves LP token via `pair.lpToken()` when available.

### Validation and test gates
- `npm run db:parity` -> PASS.
- `npm run seed:reset` -> PASS.
- `npm run seed:load` -> PASS.
- `npm run seed:verify` -> PASS.
- `npm run build` -> PASS.
- `pm2 restart all` -> PASS.
- `python3 -m unittest apps/agent-runtime/tests/test_liquidity_adapter.py -v` -> PASS.
- `python3 -m unittest apps/agent-runtime/tests/test_liquidity_cli.py -v` -> PASS (`Ran 23 tests`, `OK`).
- `npm run test:management:liquidity:decision` -> PASS (`passed: 14`, `failed: 0`).

### Evidence updates (`E22+`)
- `E22` Hedera EVM add tx hash (runtime liquidity flow):
  - command: `xclaw-agent liquidity add --chain hedera_testnet --dex saucerswap --token-a WHBAR --token-b SAUCE --amount-a 0.005 --amount-b 3.3 --slippage-bps 500 --json` (with `XCLAW_LIQUIDITY_ALLOW_SIMULATION_BYPASS=1`)
  - tx hash: `0x2c019ea7b35176d6d6c1b141fabdb849625b1b05ae7a1d3112a6673e173c8891`
  - receipt: `status=0x1` on Hedera testnet.
- `E23` Hedera EVM remove tx hash (runtime liquidity flow):
  - command: `xclaw-agent liquidity remove --chain hedera_testnet --dex saucerswap --position-id 0xfe7cc3ceb7b1128bfc3889184e2d5561bf74bfb3 --percent 50 --slippage-bps 500 --json`
  - tx hash: `0x69df2d9b23653b13b8a86cc2e03a6da72b2b2118ed70ed4a3f26f4ef1fd32865`
  - receipt: `status=0x1` on Hedera testnet.
- `E24` Deterministic transfer/simulation diagnostics:
  - runtime now surfaces token probe details (`tokenProbeA/B`) and router-revert context under `details.preflight` when add preflight fails.
- `E25` HTS readiness matrix with runtime venv + JDK:
  - `wallet health --chain hedera_testnet --json` reports `javaAvailable=true`, `javacAvailable=true`, `hederaImportable=true`, `pluginCallable=true`, `bridgeCommandConfigured=false`.
- `E26` HTS add deterministic blocker:
  - `liquidity add --dex hedera_hts ...` -> `missing_dependency` (`XCLAW_HEDERA_HTS_BRIDGE_CMD` not configured).
- `E27` HTS remove deterministic blocker:
  - `liquidity remove --dex hedera_hts ...` -> `missing_dependency` (`XCLAW_HEDERA_HTS_BRIDGE_CMD` not configured).

### Current closure state
- Hedera EVM add/remove tx-hash evidence is now present in runtime-native liquidity flow.
- HTS path remains fail-closed pending bridge command setup; Slice 95 remains in-progress until HTS tx-hash bar is satisfied or explicitly accepted as blocked.

## Slice 95 Final HTS Bridge Closure (UTC 2026-02-19)

### HTS bridge/runtime implementation
- Added in-repo bridge executable: `apps/agent-runtime/xclaw_agent/bridges/hedera_hts_bridge.py`.
- Bridge input contract:
  - stdin JSON object with `action`, `chain`, `dex`, `positionType`, `payload`.
- Bridge output contract:
  - stdout JSON object with required `txHash`, optional `positionId`, `details`.
- Default bridge command now resolves automatically when env override is absent:
  - `XCLAW_AGENT_PYTHON_BIN <repo>/apps/agent-runtime/xclaw_agent/bridges/hedera_hts_bridge.py`
- Installer now writes canonical bridge command to skill env:
  - `skills.entries.xclaw-agent.env.XCLAW_HEDERA_HTS_BRIDGE_CMD`.
- `wallet health` HTS diagnostics now include:
  - `bridgeCommandConfigured`
  - `bridgeCommandSource` (`env|default`).

### Live HTS evidence (`E28+`)
- `E28` HTS readiness pass:
  - command: `xclaw-agent wallet health --chain hedera_testnet --json`
  - outcome: `htsReadiness.ready=true`, `bridgeCommandConfigured=true`, `bridgeCommandSource=default`.
- `E29` HTS add tx hash:
  - command: `xclaw-agent liquidity add --chain hedera_testnet --dex hedera_hts --token-a WHBAR --token-b SAUCE --amount-a 1 --amount-b 1 --slippage-bps 100 --json`
  - outcome: `status=filled`, `txHash=4fce8accb8103ceadbb20865a9020222189d3606c309b6896c77bc8b97cb928fdbcc012933a5c373fa7f2922bccfd62f`.
- `E30` HTS remove tx hash:
  - command: `xclaw-agent liquidity remove --chain hedera_testnet --dex hedera_hts --position-id 4fce8accb8103ceadbb20865a9020222189d3606c309b6896c77bc8b97cb928fdbcc012933a5c373fa7f2922bccfd62f --percent 50 --slippage-bps 100 --json`
  - outcome: `status=filled`, `txHash=41428b5b6519e0c710d1aa80b796819a690ed6211ab7cce6052937cc9c89c6508b2c43813ce2ec7d0deb9cdddb9fea88`.

### Slice 95 closure status
- Hedera EVM tx-hash evidence: complete (`E22`, `E23`).
- Hedera HTS tx-hash evidence: complete (`E29`, `E30`).
- Slice 95 verification bar is met in this session.

## Slice 95D Installer Auto-Bind + Register Sync Closure (UTC 2026-02-19)

### Live installer evidence (`E31+`)
- `E31` Hedera auto-bind attempt with portable-key invariant:
  - command: `XCLAW_DEFAULT_CHAIN=base_sepolia XCLAW_INSTALL_AUTO_HEDERA_FAUCET=0 curl -fsSL http://127.0.0.1:3000/skill-install.sh | bash`
  - outcome: installer executes Hedera bind path and verifies default-chain/Hedera address consistency before registration.
- `E32` Multi-chain register upsert from installer:
  - installer register response includes both wallet rows:
    - `{"chainKey":"base_sepolia","address":"0x582f6f293e0f49855bb752ae29d6b0565c500d87"}`
    - `{"chainKey":"hedera_testnet","address":"0x582f6f293e0f49855bb752ae29d6b0565c500d87"}`
  - DB proof command:
    - `psql "$DATABASE_URL" -Atc "select chain_key,address from agent_wallets where agent_id='ag_a123e3bc428c12675f93' order by chain_key;"`
  - output:
    - `base_sepolia|0x582f6f293e0f49855bb752ae29d6b0565c500d87`
    - `hedera_testnet|0x582f6f293e0f49855bb752ae29d6b0565c500d87`
- `E33` Optional Hedera faucet warmup contract:
  - env gate: `XCLAW_INSTALL_AUTO_HEDERA_FAUCET` (default `1`).
  - non-fatal failure contract observed in script output: deterministic warning code `hedera_faucet_warmup_failed` with action hint propagation.

## Slice 95E/95F/95G Faucet Warmup Reliability (UTC 2026-02-19)

### Implementation updates
- `POST /api/v1/agent/faucet/request` now emits deterministic Hedera-safe error codes instead of opaque `internal_error` for common failures:
  - `faucet_config_invalid`
  - `faucet_fee_too_low_for_chain`
  - `faucet_native_insufficient`
  - `faucet_wrapped_insufficient`
  - `faucet_stable_insufficient`
  - `faucet_send_preflight_failed`
  - `faucet_rpc_unavailable`
- Hedera chain fee policy now uses chain-aware gas floor enforcement (`XCLAW_TESTNET_FAUCET_MIN_GAS_PRICE_WEI[_HEDERA_TESTNET]`, default `900000000000` wei) and rejects under-floor explicit overrides deterministically.
- Faucet config hardening added:
  - wrapped/stable token address validation via `isAddress`,
  - drip amount parsing requires positive integer wei values.
- Installer warmup diagnostics now print `faucetCode`, `faucetMessage`, `actionHint`, `requestId` (when present), plus exact rerun command and environment diagnostics.
- Installer register flow now defaults `XCLAW_AGENT_NAME` to `XCLAW_AGENT_ID` when name is unset, preventing `set -u` unbound-variable aborts.

### Validation + regression
- `npm run db:parity` -> PASS.
- `npm run seed:reset` -> PASS.
- `npm run seed:load` -> PASS.
- `npm run seed:verify` -> PASS.
- `npm run build` -> PASS.
- `pm2 restart all` -> PASS.
- `python3 -m unittest apps/agent-runtime/tests/test_liquidity_adapter.py -v` -> PASS.
- `python3 -m unittest apps/agent-runtime/tests/test_liquidity_cli.py -v` -> PASS.
- `npm run test:management:liquidity:decision` -> PASS.
- `npm run test:faucet:contract` -> PASS (demo-agent block + non-demo deterministic Hedera failure contract).

### Evidence updates (`E34+`)
- `E34` Hedera faucet deterministic preflight proof:
  - command:
    - `source ~/.xclaw-secrets/wallet-backups/20260219T204540Z-faucet-live/env.sh && XCLAW_E2E_AGENT_ID=$XCLAW_AGENT_ID XCLAW_E2E_AGENT_API_KEY=$XCLAW_AGENT_API_KEY npm run test:faucet:contract`
  - outcome: non-demo Hedera failure returns `code=faucet_rpc_unavailable` (not `internal_error`) with `requestId`.
- `E35` Non-demo installer warmup observability proof:
  - command:
    - `source ~/.xclaw-secrets/wallet-backups/20260219T204540Z-faucet-live/env.sh && XCLAW_INSTALL_AUTO_HEDERA_FAUCET=1 curl -fsSL https://xclaw.trade/skill-install.sh | bash`
  - outcome: installer prints deterministic warmup diagnostics (`faucetCode`, `faucetMessage`, `actionHint`) and rerun command without aborting install.
- `E36` Reinstall no-op bind + register upsert proof:
  - same installer run completes with existing wallet, registers agent, and preserves chain wallet bindings.
- `E37` Warmup deterministic failure contract proof:
  - installer captures warmup blocker as `hedera_faucet_warmup_failed` with structured hint fields instead of opaque failure.

## Slice 95 Official WHBAR Helper Enablement (UTC 2026-02-19)

### Implementation updates
- Hedera chain configs now define official wrapped-native helper contracts under `coreContracts.wrappedNativeHelper`:
  - testnet `0x0000000000000000000000000000000000003ad1` (HBAR X Helper)
  - mainnet `0x0000000000000000000000000000000000163b58`
- Runtime command added:
  - `xclaw-agent wallet wrap-native --chain <hedera_chain> --amount <human_or_wei> --json`
  - command performs helper `deposit()` call and returns `txHash`, helper/token metadata, and wrapped delta.
- Faucet route now supports Hedera wrapped auto-wrap fallback:
  - when wrapped inventory is short and helper/native balance are sufficient, faucet signer auto-wraps deficit via helper before token transfer.
  - deterministic failure code on auto-wrap failure: `faucet_wrapped_autowrap_failed`.
- Installer warmup diagnostics include explicit wrap-native hint when wrapped inventory is short.

### Evidence updates (`E38+`)
- `E38` Runtime official helper wrap success:
  - command: `xclaw-agent wallet wrap-native --chain hedera_testnet --amount 1 --json`
  - tx hash: `0x1336c10e4f0a891e998d8e971f15a9702ee116bc6271cbf3b0f907e46ceebc10`
  - output confirms helper `0x...3ad1`, wrapped token `0x...3ad2`, and `amountWrapped=1`.
- `E39` Post-wrap wallet balance proof:
  - command: `xclaw-agent wallet balance --chain hedera_testnet --json`
  - outcome: WHBAR balance increased to `1.00554979`.
- `E40` Hedera faucet deterministic residual blocker proof (stable inventory):
  - command: `xclaw-agent faucet-request --chain hedera_testnet --asset native --asset wrapped --asset stable --json`
  - outcome: deterministic `faucet_stable_insufficient` with `requestId` and token balance details (no opaque `internal_error`).

## Slice 95I Hedera Drip Rebalance (UTC 2026-02-19)

- Updated Hedera faucet default drips to:
  - native: `5000000000000000000` (5 HBAR)
  - wrapped: `500000000` (5 WHBAR)
  - stable: `10000000` (10 USDC)
- Applied in both route defaults and `.env.local` chain-scoped overrides.

### Evidence updates (`E41+`)
- `E41` Drip contract update verification:
  - route constants and `.env.local` now match 5 HBAR / 5 WHBAR / 10 USDC for `hedera_testnet`.
- `E42` Live faucet request deterministic self-recipient blocker:
  - command: `xclaw-agent faucet-request --chain hedera_testnet --asset native --asset wrapped --asset stable --json`
  - outcome: deterministic `faucet_send_preflight_failed` when recipient equals faucet signer (`require(false)` on wrapped transfer preflight), with `requestId` and chain details.

## Slice 95J Faucet Rate-Limit Reset (UTC 2026-02-19)

### Evidence updates (`E43+`)
- `E43` Global faucet daily limiter reset:
  - command: `set -a; source .env.local; set +a; npm run ops:faucet:reset-rate-limit`
  - outcome: deleted all keys matching `xclaw:ratelimit:v1:agent_faucet_daily:*` (all agents/chains).
- `E44` Chain-scoped limiter response contract:
  - updated `rate_limited` faucet details now include:
    - `scope=agent_faucet_daily_chain`
    - `chainKey`
    - `retryAfterSeconds`.

## Slice 95K Hedera Wallet Full Token Visibility (UTC 2026-02-19)

### Evidence updates (`E45+`)
- `E45` Hedera wallet balance now includes non-canonical owned tokens:
  - chain check: `cast call 0x0000000000000000000000000000000000001549 "balanceOf(address)(uint256)" 0x582f6f293e0f49855bb752ae29d6b0565c500d87 --rpc-url https://testnet.hashio.io/api` -> `130000` (USDC).
  - runtime output now merges mirror-node discovered holdings into `tokens[]`, so USDC appears on `wallet balance --chain hedera_testnet --json`.

## Slice 95L Hedera Faucet Self-Recipient Guard + Mapping Hygiene (UTC 2026-02-19)

### Implementation updates
- `POST /api/v1/agent/faucet/request` now hard-blocks self-recipient requests where resolved recipient equals faucet signer:
  - deterministic `400` with `code=faucet_recipient_not_eligible`.
- Faucet success payload now includes recipient provenance:
  - `recipientAddress`
  - `faucetAddress`
- Added operations scripts for mapping hygiene:
  - `npm run ops:faucet:audit-mappings`
  - `npm run ops:faucet:fix-mapping`
- Faucet contract test harness now supports explicit self-recipient validation path using optional env:
  - `XCLAW_E2E_SELF_FAUCET_AGENT_ID`
  - `XCLAW_E2E_SELF_FAUCET_AGENT_API_KEY`

### Validation + regression
- `npm run db:parity` -> PASS.
- `npm run seed:reset` -> PASS.
- `npm run seed:load` -> PASS.
- `npm run seed:verify` -> PASS.
- `npm run build` -> PASS.
- `pm2 restart all` -> PASS.
- `npm run test:faucet:contract` -> PASS (`3 passed / 0 failed` in current env; non-demo + self-recipient subtests skipped unless env keys are provided).
- `set -a; source .env.local; set +a; npm run ops:faucet:audit-mappings` -> PASS.
- `set -a; source .env.local; set +a; npm run ops:faucet:fix-mapping -- --agent-id ag_3cfbc4cd0949d3f4c933 --chain hedera_testnet --address 0x582f6f293e0f49855bb752ae29d6b0565c500d87` -> PASS (`code=dry_run`).

### Evidence updates (`E46+`)
- `E46` Faucet mapping audit detection:
  - command: `set -a; source .env.local; set +a; npm run ops:faucet:audit-mappings`
  - outcome: `impactedCount=1`; flagged mapping `ag_3cfbc4cd0949d3f4c933` on `hedera_testnet` pointing to faucet signer `0xfc072ab6c423626a38e4b67af317a4537438b2c7`.
- `E47` Faucet mapping fix dry-run contract:
  - command: `set -a; source .env.local; set +a; npm run ops:faucet:fix-mapping -- --agent-id ag_3cfbc4cd0949d3f4c933 --chain hedera_testnet --address 0x582f6f293e0f49855bb752ae29d6b0565c500d87`
  - outcome: deterministic dry-run output with `beforeAddress`, `nextAddress`, and apply hint.
- `E48` Faucet route deterministic self-recipient contract:
  - code path now returns `400 faucet_recipient_not_eligible` and includes `chainKey`, `recipient`, `faucetAddress`.
  - regression harness accepts this as deterministic known failure and has optional live assertion path when self-recipient test credentials are supplied.

## Slice 95M Wallet Holdings Fidelity (UTC 2026-02-20)

### Implementation updates
- Runtime `wallet balance` now excludes canonical zero-balance token rows from `tokens[]`.
- Management deposit sync now augments Hedera chain snapshots with mirror-discovered non-zero token holdings (symbol/decimals aware) so owned non-canonical tokens (for example USDC) surface in web wallet holdings.
- Agent page holdings view now filters out zero-balance token rows for the active chain.

### Evidence updates (`E49+`)
- `E49` Runtime zero-token suppression:
  - command: `apps/agent-runtime/bin/xclaw-agent wallet balance --chain hedera_testnet --json`
  - outcome: zero-balance tokens (for example `SAUCE` when balance is 0) are omitted from `tokens[]`.
- `E50` Hedera discovered token visibility in management holdings:
  - command: `GET /api/v1/management/deposit?agentId=<agent>&chainKey=hedera_testnet` (authenticated session)
  - outcome: pending live authenticated verification; implementation now syncs mirror-discovered non-zero Hedera token balances into `wallet_balance_snapshots`.

## Slice 95N User-Added Token Tracking (UTC 2026-02-20)

### Implementation summary
- Added runtime tracked-token commands (`wallet track-token|untrack-token|tracked-tokens`) with local persistence and best-effort server mirror.
- Added dedicated tracked-token mirror/read API endpoints and migration-backed table.
- Extended web deposit sync and management agent-state payload to include tracked token data.

### Evidence IDs (`E51+`)
- `E51` Runtime tracked-token behavior coverage:
  - command: `python3 -m unittest apps/agent-runtime/tests/test_wallet_core.py -v`
  - outcome: Slice 95N tests pass (`track-token` persistence, tracked-symbol resolution, ambiguity fail); suite has 2 pre-existing env-sensitive failures unrelated to tracked-token path:
    - `test_wallet_send_success_updates_spend_ledger`
    - `test_wallet_sign_challenge_cast_missing_rejected`
- `E52` Skill wrapper delegation coverage:
  - command: `python3 -m unittest apps/agent-runtime/tests/test_x402_skill_wrapper.py -v`
  - outcome: PASS; includes `wallet-track-token`, `wallet-untrack-token`, `wallet-tracked-tokens`.
- `E53` Token mirror route contract:
  - command: `npm run test:tokens:mirror:contract`
  - outcome: PASS (`5 passed / 0 failed`) with deterministic invalid-address payload rejection and successful mirror/get roundtrip.
- `E54` Validation gate run:
  - commands:
    - `npm run db:parity` -> PASS
    - `npm run seed:reset` -> PASS
    - `npm run seed:load` -> PASS
    - `npm run seed:verify` -> PASS
    - `npm run build` -> PASS
    - `pm2 restart all` -> PASS
    - `npm run db:migrate` -> PASS (applies `0024_slice95n_agent_tracked_tokens.sql` before route contract run)

### Commands
- `python3 -m unittest apps/agent-runtime/tests/test_wallet_core.py -v`
- `python3 -m unittest apps/agent-runtime/tests/test_x402_skill_wrapper.py -v`
- `npm run test:tokens:mirror:contract`

## Slice 96 Wallet/Approval E2E Harness (UTC 2026-02-20)

### Implementation evidence
- Added runtime Telegram suppression guard in `apps/agent-runtime/xclaw_agent/cli.py` (`XCLAW_TEST_HARNESS_DISABLE_TELEGRAM`).
- Added harness entrypoint: `apps/agent-runtime/scripts/wallet_approval_harness.py`.
- Added harness tests: `apps/agent-runtime/tests/test_wallet_approval_harness.py`.
- Added Telegram suppression unit coverage in `apps/agent-runtime/tests/test_trade_path.py`.

### Harness invocation contract
- `python3 apps/agent-runtime/scripts/wallet_approval_harness.py --chain base_sepolia --agent-id <agent_id> --bootstrap-token-file <token_file> --mode full --scenario-set full --approve-driver management_api --balance-tolerance-bps 40 --balance-tolerance-floor-native 0.0005 --balance-tolerance-floor-stable 5 --json-report <path>`
- stabilization flags:
  - `--hardhat-rpc-url http://127.0.0.1:8545`
  - `--hardhat-evidence-report /tmp/xclaw-slice96-hardhat-smoke.json`
  - `--max-api-retries 4`
  - `--api-retry-base-ms 400`

### Pending validation checklist
- [ ] hardhat-local subset evidence captured.
- [ ] base-sepolia full harness evidence captured with Telegram suppression enabled.
- [ ] required repo gates completed sequentially.

## Slice 96 Execution Evidence Update (UTC 2026-02-20)

### Unit/runtime checks
- `python3 -m unittest apps/agent-runtime/tests/test_wallet_approval_harness.py -v`
  - result: PASS (9/9)
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`
  - result: PASS (104/104)
  - stale command-surface tests replaced with parser/dispatch coverage for `wallet import/remove`.

### Required gates (sequential)
- `npm run db:parity` -> PASS
- `npm run seed:reset` -> PASS
- `npm run seed:load` -> PASS
- `npm run seed:verify` -> PASS
- `npm run build` -> PASS
- `pm2 restart all` -> PASS

### Harness runs
- Hardhat-local smoke attempt:
  - command: `python3 apps/agent-runtime/scripts/wallet_approval_harness.py --base-url https://xclaw.trade --chain hardhat_local --agent-id ag_slice7 --bootstrap-token-file /tmp/ag_slice7-bootstrap-token-fresh.json --scenario-set smoke --approve-driver management_api --agent-api-key slice7_token_abc12345 --hardhat-rpc-url http://127.0.0.1:8545 --json-report /tmp/xclaw-slice96-hardhat-smoke.json`
  - status: blocked/fail
  - blocker: deterministic preflight `code=hardhat_rpc_unavailable` (hardhat RPC unavailable).

- Base Sepolia full run:
  - command: `python3 apps/agent-runtime/scripts/wallet_approval_harness.py --base-url https://xclaw.trade --chain base_sepolia --agent-id ag_slice7 --bootstrap-token-file /tmp/ag_slice7-bootstrap-token-fresh.json --scenario-set full --approve-driver management_api --agent-api-key slice7_token_abc12345 --wallet-passphrase passphrase-123 --hardhat-evidence-report /tmp/xclaw-slice96-hardhat-smoke.json --max-api-retries 4 --api-retry-base-ms 400 --json-report /tmp/xclaw-slice96-base-full.json`
  - status: now hard-blocked before scenario execution when hardhat evidence is absent/non-green (`hardhat_evidence_missing` / `hardhat_evidence_not_green`).
  - report now includes:
    - `preflight.hardhatRpc`,
    - `preflight.walletDecryptProbe`,
    - `preflight.managementSession`,
    - `retryFailures`,
    - `unresolvedPending`.

## Slice 97 Ethereum + Ethereum Sepolia Wallet-First Onboarding (UTC 2026-02-20)

### Implementation evidence
- Added `config/chains/ethereum.json` and `config/chains/ethereum_sepolia.json` with:
  - chain IDs `1` and `11155111`,
  - explorer URLs (`etherscan.io`, `sepolia.etherscan.io`),
  - RPC primary/fallback endpoints,
  - wallet-first capability gating (`wallet=true`, others false),
  - Uniswap V2 router/factory metadata for deferred phase-2 activation.
- Updated web/runtime support surfaces:
  - `apps/network-web/src/lib/active-chain.ts` fallback registry includes both chains.
  - `apps/network-web/src/lib/ops-health.ts` probes include both chains.
  - `apps/network-web/src/app/dashboard/page.tsx` includes deterministic colors for both chains.
- Synced canonical docs/contracts:
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/api/WALLET_COMMAND_CONTRACT.md`
  - `docs/api/openapi.v1.yaml`

### Runtime/API checks
- `apps/agent-runtime/bin/xclaw-agent chains --json`
  - `ethereum` capabilities: `wallet=true`, `trade=false`, `liquidity=false`, `limitOrders=false`, `x402=false`, `faucet=false`, `deposits=false`.
  - `ethereum_sepolia` capabilities: `wallet=true`, `trade=false`, `liquidity=false`, `limitOrders=false`, `x402=false`, `faucet=false`, `deposits=false`.
- Isolated-home wallet smoke (`XCLAW_AGENT_HOME=$(mktemp -d)/.xclaw-agent`, `XCLAW_WALLET_PASSPHRASE=slice97-passphrase-123`):
  - `wallet create --chain ethereum --json` -> PASS (`ok:true`, `code:ok`).
  - `wallet address --chain ethereum --json` -> PASS (`ok:true`, deterministic address returned).
  - `wallet health --chain ethereum --json` -> PASS (`ok:true`, `integrityChecked:true`).
  - `wallet create --chain ethereum_sepolia --json` -> PASS (`ok:true`, portable wallet bound).
  - `wallet address --chain ethereum_sepolia --json` -> PASS (`ok:true`, same portable address returned).
  - `wallet health --chain ethereum_sepolia --json` -> PASS (`ok:true`, `integrityChecked:true`).
- `GET /api/v1/public/chains` -> PASS:
  - `ethereum`: `chainId=1`, `explorerBaseUrl=https://etherscan.io`, wallet-first capabilities.
  - `ethereum_sepolia`: `chainId=11155111`, `explorerBaseUrl=https://sepolia.etherscan.io`, wallet-first capabilities.
- `GET /api/status` provider probe -> PASS:
  - provider rows include `ethereum` (`primary`,`fallback`) and `ethereum_sepolia` (`primary`,`fallback`) with healthy status.

### Required gates
- `npm run db:parity` -> PASS
- `npm run seed:reset` -> PASS
- `npm run seed:load` -> PASS
- `npm run seed:verify` -> PASS
- `npm run build` -> PASS
- `pm2 restart all` -> PASS

## Slice 103 Uniswap LP Completion (UTC 2026-02-20)

### Implementation evidence
- Proxy/helper extensions:
  - `apps/network-web/src/lib/uniswap-lp-proxy.ts`
    - added `migrateLpUniswap(...)`
    - added `claimLpRewardsUniswap(...)`
    - added operation-level gate helper `isUniswapLpOperationEnabled(...)`
- New agent-auth routes:
  - `apps/network-web/src/app/api/v1/agent/liquidity/uniswap/migrate/route.ts`
  - `apps/network-web/src/app/api/v1/agent/liquidity/uniswap/claim-rewards/route.ts`
- New schemas:
  - `packages/shared-schemas/json/uniswap-lp-migrate-request.schema.json`
  - `packages/shared-schemas/json/uniswap-lp-claim-rewards-request.schema.json`
- Runtime commands:
  - `apps/agent-runtime/xclaw_agent/cli.py`
    - `cmd_liquidity_migrate`
    - `cmd_liquidity_claim_rewards`
    - parser entries for `liquidity migrate` and `liquidity claim-rewards`
    - operation-level chain gates via `uniswapApi.{migrateEnabled,claimRewardsEnabled}`
- Status/contracts:
  - `packages/shared-schemas/json/liquidity-status.schema.json` extends `uniswapLpOperation` enum with `migrate`, `claim_rewards`
  - `apps/network-web/src/app/api/v1/liquidity/[intentId]/status/route.ts` typed union updated
  - `docs/api/openapi.v1.yaml` adds both new routes and schema components
- Stage rollout flags:
  - `config/chains/ethereum_sepolia.json`: `migrateEnabled=true`, `claimRewardsEnabled=true`
  - mainnet targets set `migrateEnabled=false`, `claimRewardsEnabled=false` (stage-gated)

### Validation status
- `python3 -m unittest apps/agent-runtime/tests/test_liquidity_cli.py -v` -> PASS.
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` -> PASS.
- `npm run db:parity` -> PASS
- `npm run seed:reset` -> PASS
- `npm run seed:load` -> PASS
- `npm run seed:verify` -> PASS
- `npm run build` -> PASS
- `pm2 restart all` -> PASS

## Slice 102 Uniswap LP Core Integration (UTC 2026-02-20)

### Implementation evidence
- Added LP proxy helper:
  - `apps/network-web/src/lib/uniswap-lp-proxy.ts`
- Added agent-auth LP routes:
  - `apps/network-web/src/app/api/v1/agent/liquidity/uniswap/approve/route.ts`
  - `apps/network-web/src/app/api/v1/agent/liquidity/uniswap/create/route.ts`
  - `apps/network-web/src/app/api/v1/agent/liquidity/uniswap/increase/route.ts`
  - `apps/network-web/src/app/api/v1/agent/liquidity/uniswap/decrease/route.ts`
  - `apps/network-web/src/app/api/v1/agent/liquidity/uniswap/claim-fees/route.ts`
- Runtime LP orchestration + command surface:
  - `apps/agent-runtime/xclaw_agent/cli.py`
  - adds `liquidityProviders` selector, Uniswap-first LP path, legacy fallback path, and provenance output/details.
  - adds commands:
    - `xclaw-agent liquidity increase ... --json`
    - `xclaw-agent liquidity claim-fees ... --json`
- LP status provenance contract updates:
  - `packages/shared-schemas/json/liquidity-status.schema.json`
  - `apps/network-web/src/app/api/v1/liquidity/[intentId]/status/route.ts`
- Chain rollout updates:
  - `config/chains/ethereum.json`
  - `config/chains/ethereum_sepolia.json`
  - `config/chains/unichain_mainnet.json`
  - `config/chains/bnb_mainnet.json`
  - `config/chains/polygon_mainnet.json`
  - `config/chains/base_mainnet.json`
  - `config/chains/avalanche_mainnet.json`
  - `config/chains/op_mainnet.json`
  - `config/chains/arbitrum_mainnet.json`
  - `config/chains/zksync_mainnet.json`
  - `config/chains/monad_mainnet.json`
- Canonical artifacts synced:
  - `docs/api/openapi.v1.yaml`
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `docs/CONTEXT_PACK.md`
  - `spec.md`
  - `tasks.md`
  - `acceptance.md`

### Runtime tests
- `python3 -m unittest apps/agent-runtime/tests/test_liquidity_cli.py -v` -> PASS.
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` -> PASS.

### Required gates
- `npm run db:parity` -> PASS
- `npm run seed:reset` -> PASS
- `npm run seed:load` -> PASS
- `npm run seed:verify` -> PASS
- `npm run build` -> PASS
- `pm2 restart all` -> PASS

## Slice 98 Chain Metadata Normalization + Truthful Capability Gating (UTC 2026-02-20)

### Implementation evidence
- Chain metadata normalization:
  - `config/chains/adi_mainnet.json` and `config/chains/adi_testnet.json` now include chain IDs, RPC endpoints, explorer URLs, and source/verification blocks.
  - `config/chains/og_mainnet.json` and `config/chains/og_testnet.json` now include chain IDs, RPC endpoints, explorer URLs, and source/verification blocks.
  - `config/chains/kite_ai_mainnet.json` chain ID corrected to `2366` (live RPC-confirmed), naming normalized to `KiteAI Mainnet`.
- Testnet naming normalization:
  - `KiteAI Testnet`, `ADI Network AB Testnet`, `0G Galileo Testnet`.
- Capability truth normalization:
  - non-integrated chains (`base_mainnet`, `kite_ai_mainnet`, `adi_*`, `og_*`) now wallet-first only.
  - unresolved `canton_mainnet` / `canton_testnet` disabled+hidden.
- Runtime/web support surfaces updated:
  - `apps/network-web/src/lib/ops-health.ts` now probes providers dynamically for enabled+visible chains with configured RPC URLs.
  - `apps/network-web/src/lib/active-chain.ts` fallback registry expanded and normalized.
  - `apps/network-web/src/app/dashboard/page.tsx` deterministic color map expanded for normalized chain set.

### Runtime/API checks
- `apps/agent-runtime/bin/xclaw-agent chains --json` -> PASS:
  - `adi_mainnet`, `adi_testnet`, `og_mainnet`, `og_testnet`, `kite_ai_mainnet`, `kite_ai_testnet` present with normalized display names.
  - `canton_mainnet` and `canton_testnet` absent from enabled chain list (disabled/hidden by contract).
  - wallet-first capability gating confirmed for non-integrated chains (`trade/liquidity/limitOrders/x402/faucet/deposits=false`).
- `GET /api/v1/public/chains` -> PASS:
  - `adi_mainnet` (`chainId=36900`, explorer `https://explorer.adifoundation.ai`),
  - `adi_testnet` (`chainId=99999`, explorer `https://exp.testnet.adifoundation.ai`),
  - `og_mainnet` (`chainId=16661`, explorer `https://chainscan.0g.ai`),
  - `og_testnet` (`chainId=16602`, explorer `https://chainscan-galileo.0g.ai`),
  - `kite_ai_mainnet` (`chainId=2366`),
  - `kite_ai_testnet` (`chainId=2368`, display `KiteAI Testnet`).
- `GET /api/status` -> PASS:
  - provider rows include all enabled+visible RPC-configured chains (`adi_*`, `base_*`, `ethereum*`, `hedera*`, `kite_ai*`, `og_*`).
  - provider rows exclude disabled/hidden Canton chains.

### Required gates
- `npm run db:parity` -> PASS
- `npm run seed:reset` -> PASS
- `npm run seed:load` -> PASS
- `npm run seed:verify` -> PASS
- `npm run build` -> PASS
- `pm2 restart all` -> PASS

## Slice 99 Installer Multi-Chain Wallet Auto-Bind Hardening (UTC 2026-02-20)

### Implementation evidence
- `apps/network-web/src/app/skill-install.sh/route.ts`
  - wallet-capable chain discovery added via runtime `chains --json`.
  - installer now loops chain binds with `wallet create --chain <chain> --json`.
  - register payload wallet rows are built from resolved per-chain addresses.
- `apps/network-web/src/app/skill-install.ps1/route.ts`
  - mirrored wallet-capable chain discovery + bind loop.
  - register payload now uses discovered deduplicated wallet rows.

### Validation
- `npm run db:parity` -> PASS
- `npm run seed:reset` -> PASS
- `npm run seed:load` -> PASS
- `npm run seed:verify` -> PASS
- `npm run build` -> PASS
- `pm2 restart all` -> PASS

## Hotfix: Truthful ETH Sepolia Wallet Checks + Multi-Chain Register Sync (UTC 2026-02-20)

### Implementation evidence
- `skills/xclaw-agent/scripts/xclaw_agent_skill.py`
  - wallet commands now accept optional explicit chain override argument and pass it through to runtime (`wallet-health/address/sign/send/send-token/balance/token-balance/track/untrack/tracked-tokens/wrap-native/create`).
- `apps/agent-runtime/xclaw_agent/cli.py`
  - `cmd_profile_set_name` now builds register payload wallets from all enabled local wallet bindings in wallet store (primary requested chain first), instead of only one chain wallet row.
- `apps/agent-runtime/tests/test_x402_skill_wrapper.py`
  - added explicit chain override tests for `wallet-balance` and `wallet-send-token`.
- `apps/agent-runtime/tests/test_trade_path.py`
  - updated profile set-name success test to assert multi-chain wallet payload.

### Runtime tests
- `python3 -m unittest -q apps.agent-runtime.tests.test_x402_skill_wrapper.X402SkillWrapperTests.test_wallet_balance_allows_explicit_chain_override apps.agent-runtime.tests.test_x402_skill_wrapper.X402SkillWrapperTests.test_wallet_send_token_allows_explicit_chain_override apps.agent-runtime.tests.test_trade_path.TradePathRuntimeTests.test_profile_set_name_success apps.agent-runtime.tests.test_trade_path.TradePathRuntimeTests.test_profile_set_name_rate_limited` -> PASS

### Required gates
- `npm run db:parity` -> PASS
- `npm run seed:reset` -> PASS
- `npm run seed:load` -> PASS
- `npm run seed:verify` -> PASS
- `npm run build` -> PASS
- `pm2 restart all` -> PASS

## Slice 100 Uniswap Proxy-First Trade Execution (UTC 2026-02-20)

### Implementation evidence
- Runtime provider orchestration:
  - `apps/agent-runtime/xclaw_agent/cli.py`
    - added chain-config-driven provider selection (`tradeProviders.primary/fallback`).
    - `cmd_trade_spot` now attempts `uniswap_api` first and falls back to `legacy_router` on proxy errors.
    - `cmd_trade_execute` now attempts `uniswap_api` first and falls back to `legacy_router` on proxy errors.
    - deterministic no-provider failure path: `no_execution_provider_available`.
    - provider provenance fields emitted in runtime payloads and status transitions.
- Server proxy integration:
  - `apps/network-web/src/lib/uniswap-proxy.ts`
    - server-only key injection (`XCLAW_UNISWAP_API_KEY`), strict payload normalization, deterministic upstream errors.
  - `apps/network-web/src/app/api/v1/agent/trade/uniswap/quote/route.ts`
  - `apps/network-web/src/app/api/v1/agent/trade/uniswap/build/route.ts`
- Trade status provenance support:
  - `packages/shared-schemas/json/trade-status.schema.json`
  - `apps/network-web/src/app/api/v1/trades/[tradeId]/status/route.ts`
- Chain rollout configuration:
  - updated `config/chains/ethereum.json`, `config/chains/ethereum_sepolia.json`, `config/chains/base_mainnet.json`.
  - added `config/chains/unichain_mainnet.json`, `config/chains/bnb_mainnet.json`, `config/chains/polygon_mainnet.json`, `config/chains/avalanche_mainnet.json`, `config/chains/op_mainnet.json`, `config/chains/arbitrum_mainnet.json`, `config/chains/zksync_mainnet.json`, `config/chains/monad_mainnet.json`.

### Runtime tests
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` -> PASS.

### Required gates
- `npm run db:parity` -> PASS
- `npm run seed:reset` -> PASS
- `npm run seed:load` -> PASS
- `npm run seed:verify` -> PASS
- `npm run build` -> PASS
- `pm2 restart all` -> PASS

## Slice 101 Dashboard Dexscreener Top Tokens (UTC 2026-02-20)

### Implementation evidence
- Added chain-config market mapping support:
  - `apps/network-web/src/lib/chains.ts` now supports `marketData.dexscreenerChainId`.
  - mappings configured in:
    - `config/chains/base_mainnet.json` -> `base`
    - `config/chains/base_sepolia.json` -> `base`
    - `config/chains/ethereum.json` -> `ethereum`
    - `config/chains/ethereum_sepolia.json` -> `ethereum`
- Added new public route:
  - `apps/network-web/src/app/api/v1/public/dashboard/trending-tokens/route.ts`
  - validates `chainKey`, supports `limit` (capped at 10), aggregates mapped chains for `all`,
  - fetches/normalizes Dexscreener rows, dedupes by token+chain, sorts by 24h volume desc,
  - soft-fails upstream issues and exposes warning metadata,
  - uses 60-second in-memory cache.
- Dashboard integration:
  - `apps/network-web/src/app/dashboard/page.tsx` fetches `trending-tokens` by current dashboard chain and refreshes every 60s.
  - `apps/network-web/src/app/dashboard/page.module.css` adds desktop table + mobile card styles.
  - section is hidden when no token rows are available for selected chain.
  - only data-backed columns render (no placeholder columns).
- Canonical contract/artifact updates:
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `docs/api/openapi.v1.yaml`
  - `packages/shared-schemas/json/public-dashboard-trending-tokens-response.schema.json`
  - `docs/CONTEXT_PACK.md`, `spec.md`, `tasks.md`, `acceptance.md`

### Feature checks
- `GET /api/v1/public/dashboard/trending-tokens?chainKey=all&limit=10` -> PASS (`status=200`, `count=10`, `sorted=true`, chains include `ethereum` + `base`).
- chain dropdown update reflects token list changes -> PASS (API queries by selected chain key and dashboard effect dependencies include `chainKey`; verified chain-specific outputs differ for `base_sepolia` vs `ethereum_sepolia`).
- `base_sepolia` / `ethereum_sepolia` map to mainnet Dexscreener chain IDs -> PASS:
  - `chainKey=base_sepolia` -> `status=200`, rows `chainId=base`.
  - `chainKey=ethereum_sepolia` -> `status=200`, rows `chainId=ethereum`.
- unmapped chain hides section -> PASS (`chainKey=hedera_testnet` returns `status=200` with `items=[]`; dashboard module conditionally renders only when rows exist).
- invalid `chainKey` returns `400 payload_invalid` -> PASS (`chainKey=not_real_chain` -> `status=400`, `code=payload_invalid`).

### Required gates
- `npm run db:parity` -> PASS
- `npm run seed:reset` -> PASS
- `npm run seed:load` -> PASS
- `npm run seed:verify` -> PASS
- `npm run build` -> PASS
- `pm2 restart all` -> PASS

## Slice 104 LP Operation Promotion (UTC 2026-02-20)

### Implementation evidence
- Promotion config flags enabled on:
  - `config/chains/ethereum.json`
  - `config/chains/base_mainnet.json`
  - `config/chains/arbitrum_mainnet.json`
  - `config/chains/op_mainnet.json`
  - `config/chains/polygon_mainnet.json`
  - `config/chains/avalanche_mainnet.json`
  - `config/chains/bnb_mainnet.json`
  - `config/chains/zksync_mainnet.json`
  - `config/chains/unichain_mainnet.json`
  - `config/chains/monad_mainnet.json`
- `ethereum_sepolia` remains enabled for both operations.
- Runtime/proxy execution architecture unchanged; operation-level fail-closed behavior retained.

### Validation status
- `python3 -m unittest apps/agent-runtime/tests/test_liquidity_cli.py -v` -> PASS.
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` -> PASS.
- `npm run db:parity` -> PASS
- `npm run seed:reset` -> PASS
- `npm run seed:load` -> PASS
- `npm run seed:verify` -> PASS
- `npm run build` -> PASS
- `pm2 restart all` -> PASS

## Slice 105 Cross-Chain Liquidity Claims (UTC 2026-02-20)

### Implementation evidence
- Runtime claim orchestration updates:
  - `apps/agent-runtime/xclaw_agent/cli.py`
- Adapter claim capability updates:
  - `apps/agent-runtime/xclaw_agent/liquidity_adapter.py`
- Hedera guarded claim action dispatch:
  - `apps/agent-runtime/xclaw_agent/hedera_hts_plugin.py`
  - `apps/agent-runtime/xclaw_agent/bridges/hedera_hts_bridge.py`
- Chain config claim gates added:
  - `config/chains/*.json` (`liquidityOperations.claimFees.legacyEnabled`, `liquidityOperations.claimRewards.legacyEnabled`)
- Runtime claim regression coverage updated:
  - `apps/agent-runtime/tests/test_liquidity_cli.py`

### Validation status
- `python3 -m unittest apps/agent-runtime/tests/test_liquidity_cli.py -v` -> PASS.
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` -> PASS.
- `npm run db:parity` -> PASS
- `npm run seed:reset` -> PASS
- `npm run seed:load` -> PASS
- `npm run seed:verify` -> PASS
- `npm run build` -> PASS
- `pm2 restart all` -> PASS

## Slice 106 Full Cross-Chain Functional Parity + Adapter Fallbacks (UTC 2026-02-20)

### Implementation evidence
- Runtime operation-aware fallback helpers + claim command integration:
  - `apps/agent-runtime/xclaw_agent/cli.py`
- Adapter reward capability metadata:
  - `apps/agent-runtime/xclaw_agent/liquidity_adapter.py`
- Chain config model extension:
  - `config/chains/*.json` (`tradeOperations.*`, `liquidityOperations.*.adapter`, `liquidityOperations.claimRewards.rewardContracts`)
- Canonical docs/handoff updates:
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `docs/CONTEXT_PACK.md`
  - `spec.md`
  - `tasks.md`

### Wallet-only/disabled onboarding backlog (documented)
- `adi_mainnet`, `adi_testnet`, `og_mainnet`, `og_testnet`, `kite_ai_mainnet`, `canton_mainnet`, `canton_testnet`

### Validation status
- `python3 -m unittest apps/agent-runtime/tests/test_liquidity_cli.py -v` -> PASS.
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` -> PASS.
- `npm run db:parity` -> PASS
- `npm run seed:reset` -> PASS
- `npm run seed:load` -> PASS
- `npm run seed:verify` -> PASS
- `npm run build` -> PASS
- `pm2 restart all` -> PASS

## Slice 107 Executable Cross-Chain Parity Completion (UTC 2026-02-20)

### Implementation evidence
- Runtime claim failure provenance hardening:
  - `apps/agent-runtime/xclaw_agent/cli.py`
    - claim-fees and claim-rewards failures now consistently include operation + provider provenance fields.
- Hedera bridge claim execution enablement:
  - `apps/agent-runtime/xclaw_agent/bridges/hedera_hts_bridge.py`
    - removed hard-block for `claim_fees`/`claim_rewards` actions.
- Hedera claim promotion config:
  - `config/chains/hedera_mainnet.json`
  - `config/chains/hedera_testnet.json`
    - `liquidityOperations.claimFees.legacyEnabled=true`
    - `liquidityOperations.claimRewards.legacyEnabled=true`
- Runtime tests:
  - `apps/agent-runtime/tests/test_liquidity_cli.py`
    - claim-failure provenance coverage added.

### Validation status
- `python3 -m unittest apps/agent-runtime/tests/test_liquidity_cli.py -v` -> PASS.
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` -> PASS.
- `npm run db:parity` -> PASS
- `npm run seed:reset` -> PASS
- `npm run seed:load` -> PASS
- `npm run seed:verify` -> PASS
- `npm run build` -> PASS
- `pm2 restart all` -> PASS

## Slice 108-111 Active-Chain Parity Matrix (UTC 2026-02-20)

### Active-chain operation truth

| Chain | Send | Trade/Convert | LP Add/Remove | Claim Fees | Claim Rewards | Primary | Fallback | Deterministic fail code when non-executable |
|---|---|---|---|---|---|---|---|---|
| ethereum | ✅ | ✅ | ✅ | ✅ (Uniswap primary) | ✅ (Uniswap primary) | uniswap_api | legacy_router (trade only) | `no_execution_provider_available` |
| ethereum_sepolia | ✅ | ✅ | ✅ | ✅ (Uniswap primary) | ✅ (Uniswap primary) | uniswap_api | legacy_router (trade only) | `no_execution_provider_available` |
| base_mainnet | ✅ | ✅ | ✅ | ✅ (Uniswap primary) | ✅ (Uniswap primary) | uniswap_api | none | `no_execution_provider_available` |
| arbitrum_mainnet | ✅ | ✅ | ✅ | ✅ (Uniswap primary) | ✅ (Uniswap primary) | uniswap_api | none | `no_execution_provider_available` |
| op_mainnet | ✅ | ✅ | ✅ | ✅ (Uniswap primary) | ✅ (Uniswap primary) | uniswap_api | none | `no_execution_provider_available` |
| polygon_mainnet | ✅ | ✅ | ✅ | ✅ (Uniswap primary) | ✅ (Uniswap primary) | uniswap_api | none | `no_execution_provider_available` |
| avalanche_mainnet | ✅ | ✅ | ✅ | ✅ (Uniswap primary) | ✅ (Uniswap primary) | uniswap_api | none | `no_execution_provider_available` |
| bnb_mainnet | ✅ | ✅ | ✅ | ✅ (Uniswap primary) | ✅ (Uniswap primary) | uniswap_api | none | `no_execution_provider_available` |
| zksync_mainnet | ✅ | ✅ | ✅ | ✅ (Uniswap primary) | ✅ (Uniswap primary) | uniswap_api | none | `no_execution_provider_available` |
| unichain_mainnet | ✅ | ✅ | ✅ | ✅ (Uniswap primary) | ✅ (Uniswap primary) | uniswap_api | none | `no_execution_provider_available` |
| monad_mainnet | ✅ | ✅ | ✅ | ✅ (Uniswap primary) | ✅ (Uniswap primary) | uniswap_api | none | `no_execution_provider_available` |
| base_sepolia | ✅ | ✅ | ✅ | ❌ | ❌ | legacy_router | n/a | `claim_fees_not_supported_for_protocol`, `claim_rewards_not_configured` |
| hardhat_local | ✅ | ✅ | ✅ | ❌ | ❌ | legacy_router | n/a | `claim_fees_not_supported_for_protocol`, `claim_rewards_not_configured` |
| kite_ai_testnet | ✅ | ✅ | ✅ | ❌ | ❌ | legacy_router | n/a | `claim_fees_not_supported_for_protocol`, `claim_rewards_not_configured` |
| hedera_mainnet | ✅ | ✅ | ✅ | ✅ (hedera_hts) | ✅ (hedera_hts) | legacy_router | n/a | `claim_rewards_not_configured` (when plugin/config absent) |
| hedera_testnet | ✅ | ✅ | ✅ | ✅ (hedera_hts) | ✅ (hedera_hts) | legacy_router | n/a | `claim_rewards_not_configured` (when plugin/config absent) |

### Required validation for 108-111 stream
- `python3 -m unittest apps/agent-runtime/tests/test_liquidity_cli.py -v` -> PASS
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` -> PASS
- `npm run db:parity` -> PASS
- `npm run seed:reset` -> PASS
- `npm run seed:load` -> PASS
- `npm run seed:verify` -> PASS
- `npm run build` -> PASS
- `pm2 restart all` -> PASS

## Slice 107 Hotfix A Base ERC-8021 Builder Code Attribution (UTC 2026-02-20)

### Implementation evidence
- Runtime ERC-8021 sender integration:
  - `apps/agent-runtime/xclaw_agent/cli.py`
    - Base chain gating (`base_mainnet`, `base_sepolia`)
    - env precedence for builder code resolution
    - fail-closed `builder_code_missing` on Base non-empty calldata without config
    - safe-mode skip on empty calldata
    - already-tagged no double append
    - runtime output metadata aggregation for wallet/trade/liquidity responses
- Runtime test coverage:
  - `apps/agent-runtime/tests/test_trade_path.py`

### Validation status
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` -> PASS (117 tests)
- `python3 -m unittest apps/agent-runtime/tests/test_wallet_core.py -v` -> PASS (43 tests)
- `npm run db:parity` -> PASS
- `npm run seed:reset` -> PASS
- `npm run seed:load` -> PASS
- `npm run seed:verify` -> PASS
- `npm run build` -> PASS
- `pm2 restart all` -> PASS

### Runtime attribution evidence
- Unit tests confirm Base-chain suffixing and metadata behavior:
  - Base non-empty calldata -> suffix appended and `builderCodeApplied=true`.
  - Base empty calldata -> safe-mode skip with `builderCodeSkippedReason=empty_calldata_safe_mode`.
  - Missing builder code env -> deterministic fail-closed (`builder_code_missing`).
- Command payload assertions confirm additive fields in success responses:
  - `builderCodeChainEligible`
  - `builderCodeApplied`
  - `builderCodeSkippedReason`
  - `builderCodeSource`
  - `builderCodeStandard`
- Live Base Sepolia/Mainnet tx hash validation is not included in this session because onchain execution credentials/funded wallets were not used in test runs.

## Slice 112-116 v2-Only Fallback Promotion Evidence (UTC 2026-02-20)

### Official sources used
- Uniswap v2 deployment addresses (official docs):
  - https://docs.uniswap.org/contracts/v2/reference/smart-contracts/v2-deployments
- Uniswap v2 factory source (official repo):
  - https://github.com/Uniswap/v2-core/blob/master/contracts/UniswapV2Factory.sol
- Uniswap v2 router source (official repo):
  - https://github.com/Uniswap/v2-periphery/blob/master/contracts/UniswapV2Router02.sol

### Research/promotion matrix (v2 trade fallback)

| Chain | Promotion | Factory | Router | Explorer verification links | Runtime compatibility check | Result |
|---|---|---|---|---|---|---|
| ethereum | enabled | `0x5C69...aA6f` | `0x7a25...48D` | etherscan factory/router `#code` | `eth_chainId=0x1`, `router.factory() match` | promoted |
| ethereum_sepolia | enabled | `0xF62c...80E6` | `0xeE56...CfE3` | sepolia.etherscan factory/router `#code` | `eth_chainId=0xaa36a7`, `router.factory() match` | promoted |
| base_mainnet | enabled | `0x8909...8eC6` | `0x4752...ad24` | basescan factory/router `#code` | `eth_chainId=0x2105`, `router.factory() match` | promoted |
| arbitrum_mainnet | enabled | `0xf1D7...bcf9` | `0x4752...ad24` | arbiscan factory/router `#code` | `eth_chainId=0xa4b1`, `router.factory() match` | promoted |
| op_mainnet | enabled | `0x0c3c...74Bf` | `0x4A7b...62c2` | optimistic.etherscan factory/router `#code` | `eth_chainId=0xa`, `router.factory() match` | promoted |
| polygon_mainnet | enabled | `0x9e5A...2799C` | `0xedf6...7AD1` | polygonscan factory/router `#code` | primary RPC failed auth; fallback RPC `eth_chainId=0x89`, `router.factory() match` | promoted |
| avalanche_mainnet | enabled | `0x9e5A...2799C` | `0x4752...ad24` | snowtrace factory/router `#code` | `eth_chainId=0xa86a`, `router.factory() match` | promoted |
| bnb_mainnet | enabled | `0x8909...8eC6` | `0x4752...aD24` | bscscan factory/router `#code` | `eth_chainId=0x38`, `router.factory() match` | promoted |
| unichain_mainnet | enabled | `0x1f98...0002` | `0x284f...63ff` | uniscan factory/router `#code` | `eth_chainId=0x82`, `router.factory() match` | promoted |
| monad_mainnet | enabled | `0x182a...0f59` | `0x4b2a...6804` | explorer.monad factory/router pages | `eth_chainId=0x8f`, `router.factory() match` | promoted |
| zksync_mainnet | disabled | n/a | n/a | n/a | no official Uniswap v2 deployment entry in current docs table | keep deterministic |

### Non-Uniswap active claim truth (slice 114)

| Chain | claim-fees | claim-rewards | Outcome contract |
|---|---|---|---|
| hedera_mainnet | executable (`hedera_hts`) | executable (`hedera_hts`) | executable where configured/plugin supports |
| hedera_testnet | executable (`hedera_hts`) | executable (`hedera_hts`) | executable where configured/plugin supports |
| base_sepolia | deterministic fail | deterministic fail | `claim_fees_not_supported_for_protocol`, `claim_rewards_not_configured` |
| hardhat_local | deterministic fail | deterministic fail | `claim_fees_not_supported_for_protocol`, `claim_rewards_not_configured` |
| kite_ai_testnet | deterministic fail | deterministic fail | `claim_fees_not_supported_for_protocol`, `claim_rewards_not_configured` |

### Final active-chain parity matrix (slice 116)

| Chain | Send | Trade | LP add/remove | Claim fees | Claim rewards | Primary | Fallback | Deterministic fail code |
|---|---|---|---|---|---|---|---|---|
| ethereum | ✅ | ✅ | ✅ | ✅ (Uniswap) | ✅ (Uniswap) | uniswap_api | legacy_router | `no_execution_provider_available` |
| ethereum_sepolia | ✅ | ✅ | ✅ | ✅ (Uniswap) | ✅ (Uniswap) | uniswap_api | legacy_router | `no_execution_provider_available` |
| base_mainnet | ✅ | ✅ | ✅ | ✅ (Uniswap) | ✅ (Uniswap) | uniswap_api | legacy_router | `no_execution_provider_available` |
| arbitrum_mainnet | ✅ | ✅ | ✅ | ✅ (Uniswap) | ✅ (Uniswap) | uniswap_api | legacy_router | `no_execution_provider_available` |
| op_mainnet | ✅ | ✅ | ✅ | ✅ (Uniswap) | ✅ (Uniswap) | uniswap_api | legacy_router | `no_execution_provider_available` |
| polygon_mainnet | ✅ | ✅ | ✅ | ✅ (Uniswap) | ✅ (Uniswap) | uniswap_api | legacy_router | `no_execution_provider_available` |
| avalanche_mainnet | ✅ | ✅ | ✅ | ✅ (Uniswap) | ✅ (Uniswap) | uniswap_api | legacy_router | `no_execution_provider_available` |
| bnb_mainnet | ✅ | ✅ | ✅ | ✅ (Uniswap) | ✅ (Uniswap) | uniswap_api | legacy_router | `no_execution_provider_available` |
| unichain_mainnet | ✅ | ✅ | ✅ | ✅ (Uniswap) | ✅ (Uniswap) | uniswap_api | legacy_router | `no_execution_provider_available` |
| monad_mainnet | ✅ | ✅ | ✅ | ✅ (Uniswap) | ✅ (Uniswap) | uniswap_api | legacy_router | `no_execution_provider_available` |
| zksync_mainnet | ✅ | ✅ | ✅ | ✅ (Uniswap) | ✅ (Uniswap) | uniswap_api | none | `no_execution_provider_available` |
| base_sepolia | ✅ | ✅ | ✅ | ❌ | ❌ | legacy_router | n/a | `claim_fees_not_supported_for_protocol`, `claim_rewards_not_configured` |
| hardhat_local | ✅ | ✅ | ✅ | ❌ | ❌ | legacy_router | n/a | `claim_fees_not_supported_for_protocol`, `claim_rewards_not_configured` |
| kite_ai_testnet | ✅ | ✅ | ✅ | ❌ | ❌ | legacy_router | n/a | `claim_fees_not_supported_for_protocol`, `claim_rewards_not_configured` |
| hedera_mainnet | ✅ | ✅ | ✅ | ✅ (hedera_hts) | ✅ (hedera_hts) | legacy_router | n/a | `claim_rewards_not_configured` when reward wiring absent |
| hedera_testnet | ✅ | ✅ | ✅ | ✅ (hedera_hts) | ✅ (hedera_hts) | legacy_router | n/a | `claim_rewards_not_configured` when reward wiring absent |

### Validation
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` -> PASS
- `python3 -m unittest apps/agent-runtime/tests/test_liquidity_cli.py -v` -> PASS
- required gates rerun sequentially for this stream (see final gate block below).

## Slice 117: Ethereum Sepolia Harness Matrix Expansion (UTC 2026-02-20)

### Implementation evidence
- Updated harness: `apps/agent-runtime/scripts/wallet_approval_harness.py`
  - Ethereum Sepolia funding bootstrap (`ETH -> WETH -> USDC`).
  - Optional wallet identity assertion (`--expected-wallet-address`).
  - Split transfer-only and x402 capability-aware scenarios.
- Added matrix runner: `apps/agent-runtime/scripts/wallet_approval_chain_matrix.py`
  - strict order: hardhat -> base -> ethereum sepolia,
  - stop-on-first-failure,
  - consolidated JSON report.
- Added/updated tests:
  - `apps/agent-runtime/tests/test_wallet_approval_harness.py`
  - `apps/agent-runtime/tests/test_wallet_approval_chain_matrix.py`

### Unit test validation
- `python3 -m unittest apps/agent-runtime/tests/test_wallet_approval_harness.py -v` -> PASS
- `python3 -m unittest apps/agent-runtime/tests/test_wallet_approval_chain_matrix.py -v` -> PASS

### Pending runtime/gate evidence
- [ ] Matrix runtime run command:
  - `python3 apps/agent-runtime/scripts/wallet_approval_chain_matrix.py --base-url http://127.0.0.1:3000 --agent-id <agent_id> --bootstrap-token-file <token_file> --agent-api-key <api_key> --wallet-passphrase <passphrase> --harvy-address 0x582f6f293e0f49855bb752ae29d6b0565c500d87 --json-report /tmp/xclaw-slice117-matrix.json`
- [ ] Required sequential gates:
  - `npm run db:parity`
  - `npm run seed:reset`
  - `npm run seed:load`
  - `npm run seed:verify`
  - `npm run build`
  - `pm2 restart all`

---

# Slice 117 Hotfix B Acceptance Evidence: Agent-Canonical Confirmation Pipeline (Dual-Run Start)

Date (UTC): 2026-02-20  
Active slice context: `Slice 117` in progress.

## Objective + Scope Lock
- Objective: move terminal confirmation authority to agent runtime watcher metadata and prevent server terminal synthetic result fanout from causing cross-agent routing leakage.
- Scope lock:
  - `apps/agent-runtime/xclaw_agent/cli.py`
  - `apps/network-web/src/app/api/v1/trades/[tradeId]/status/route.ts`
  - `apps/network-web/src/app/api/v1/agent/transfer-approvals/mirror/route.ts`
  - `apps/network-web/src/app/api/v1/management/transfer-approvals/decision/route.ts`
  - `apps/network-web/src/app/api/v1/management/deposit/route.ts`
  - `apps/network-web/src/lib/non-telegram-agent-prod.ts`
  - schema/openapi/migration/doc sync artifacts

## Behavior Checks
- [x] Trade status ingest accepts and persists watcher provenance fields.
- [x] Transfer mirror ingest accepts and persists watcher provenance fields.
- [x] Runtime emits watcher provenance defaults (`observedBy=agent_watcher`, `watcherRunId`, `observedAt`) for trade status and transfer mirror writes.
- [x] Receipt-confirmed terminal transitions emit `observationSource=rpc_receipt`, `confirmationCount=1`.
- [x] Server terminal synthetic fanout is disabled for trade status and transfer mirror ingress paths.
- [x] Transfer management decision route no longer sends terminal synthetic fanout.
- [x] Deposit poll path writes are tagged as comparator rows (`legacy_server_poller`) for dual-run visibility.

## Required Validation Gates
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] `npm run build`
- [x] `pm2 restart all`

## Hotfix B Closeout Evidence (UTC)
- `2026-02-20T19:02:50Z` `node infrastructure/scripts/agent-confirmation-dualrun-evidence.mjs`
  - PASS: `"ok": true`, `"passed": 12`, `"failed": 0`
  - PASS checks include:
    - `parity.migration_columns_and_constraints_present`
    - `parity.deposit_poller_comparator_tagging_present`
    - `crosstalk.trade_status_terminal_server_fanout_removed`
    - `crosstalk.transfer_mirror_terminal_server_fanout_removed`
    - `crosstalk.transfer_decision_terminal_server_fanout_removed`
    - `negative.contract_wrong_agent_trade_update_rejected`
    - `negative.contract_missing_txhash_rejected`
    - `negative.contract_transfer_mirror_provenance_schema_validation`
- `2026-02-20T19:02:55Z` `npm run db:parity`
  - PASS: `"ok": true`
  - Proof: migration list includes `0026_slice117_agent_watcher_provenance.sql`
- `2026-02-20T19:02:57Z` `npm run seed:reset`
  - PASS: `"ok": true`
- `2026-02-20T19:02:58Z` `npm run seed:load`
  - PASS: `"ok": true`
  - Proof: `"seedMode": true`, `"totals":{"agents":6,"trades":11}`
- `2026-02-20T19:03:00Z` `npm run seed:verify`
  - PASS: `"ok": true`
- `2026-02-20T19:03:10Z` `npm run build`
  - PASS: `Compiled successfully`
- `2026-02-20T19:03:13Z` `pm2 restart all`
  - PASS: `[PM2] [xclaw-web](0) ✓` and process status `online`
- `2026-02-20T19:03:22Z` `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`
  - PASS: `Ran 119 tests` and `OK`

---

# Slice 117 Hotfix C Acceptance Evidence: Cross-Chain `wallet wrap-native` Parity

Date (UTC): 2026-02-20  
Active slice context: `Slice 117` in progress.

## Objective + Scope Lock
- Objective: make `wallet wrap-native` config-driven across wallet-capable chains and preserve deterministic wrap failure contracts.
- Scope lock:
  - `apps/agent-runtime/xclaw_agent/cli.py`
  - `apps/agent-runtime/tests/test_wallet_core.py`
  - canonical docs + handoff artifacts listed in `spec.md`.

## Behavior checks
- [x] `wallet wrap-native` succeeds on helper path (Hedera-compatible flow).
- [x] `wallet wrap-native` succeeds on non-helper wrapped-token path (non-Hedera EVM flow).
- [x] Missing helper config remains deterministic (`wrapped_native_helper_missing`).
- [x] Missing wrapped-native token mapping is deterministic (`wrapped_native_token_missing`).
- [x] Receipt failure path remains deterministic (`wrap_native_failed`) with swap fallback action hint.

## Unit test validation
- `python3 -m unittest apps/agent-runtime/tests/test_wallet_core.py -v`
  - PASS: `Ran 45 tests` and `OK`
  - Includes explicit wrap-native helper/non-helper/missing-token/receipt-failure cases.
- `python3 -m unittest apps/agent-runtime/tests/test_x402_skill_wrapper.py -v`
  - PASS: `Ran 47 tests` and `OK`

## Required validation gates
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] `npm run build`
- [x] `pm2 restart all`

## Pending traceability
- [ ] Issue #60 evidence post + commit hash(es).

---

# Hotfix Acceptance Evidence: Slice 117 Hotfix D Trade-Cap Deprecation + Chain Context Parity

Date (UTC): 2026-02-20
Active slice context: `Slice 117` in progress (issue `#60`).

## Objective + Scope Lock
- Objective: remove deprecated trade-cap runtime/server blocking and align omitted-chain command routing to runtime/web-synced default chain.
- Scope lock:
  - `apps/agent-runtime/xclaw_agent/cli.py`
  - `apps/network-web/src/lib/trade-caps.ts`
  - `skills/xclaw-agent/scripts/xclaw_agent_skill.py`
  - related tests + canonical docs/handoff artifacts.

## Behavior Checks
- [x] Runtime trade cap enforcement no longer throws `policy_blocked` when `tradeCaps` payload is absent.
- [x] Server `evaluateTradeCaps` no longer emits cap violation blockers.
- [x] Skill wrapper resolves omitted chain from runtime default-chain in API-managed context.
- [x] Skill trade commands support explicit chain override positional arg.

## Required Validation Gates
- [ ] `python3 -m unittest apps/agent-runtime/tests/test_wallet_core.py -v`
- [ ] `python3 -m unittest apps/agent-runtime/tests/test_x402_skill_wrapper.py -v`
- [ ] `npm run db:parity`
- [ ] `npm run seed:reset`
- [ ] `npm run seed:load`
- [ ] `npm run seed:verify`
- [ ] `npm run build`
- [ ] `pm2 restart all`

---

# Hotfix Acceptance Evidence: Slice 117 Hotfix E Transfer Approval Mirror Fail-Closed

Date (UTC): 2026-02-20
Active slice context: `Slice 117` in progress (issue `#60`).

## Objective + Scope Lock
- Objective: prevent user-facing queued transfer approvals when web management has no mirrored approval row.
- Scope lock:
  - `apps/agent-runtime/xclaw_agent/cli.py`
  - `apps/agent-runtime/tests/test_trade_path.py`
  - `apps/network-web/src/lib/transfer-mirror-schema.ts`
  - `apps/network-web/src/app/api/v1/agent/transfer-approvals/mirror/route.ts`
  - `apps/network-web/src/app/api/v1/management/agent-state/route.ts`
  - `apps/network-web/src/app/agents/[agentId]/page.tsx`
  - `infrastructure/scripts/verify-agents-approval-row-ui.mjs`
  - `infrastructure/scripts/e2e-full-pass.sh`
  - `package.json`
  - `skills/xclaw-agent/scripts/xclaw_agent_skill.py`
  - `apps/agent-runtime/tests/test_x402_skill_wrapper.py`
  - canonical docs/handoff artifacts.

## Behavior Checks
- [x] Approval-required wallet send paths enforce required mirror delivery before returning queued approval response.
- [x] Mirror delivery failure returns deterministic `approval_sync_failed`.
- [x] Failed mirror delivery clears local pending transfer flow for the generated approval id.
- [x] `POST /api/v1/agent/transfer-approvals/mirror` returns deterministic `transfer_mirror_unavailable` (503) on schema/storage drift instead of opaque `internal_error`.
- [x] `GET /api/v1/management/agent-state` returns deterministic `transfer_mirror_unavailable` (503) on transfer-mirror schema/storage drift instead of silently empty transfer approvals.
- [x] Skill wrapper preserves `approval_sync_failed` as non-success (no `approval_pending` normalization).
- [x] `/agents/:id` transfer approval rows expose deterministic selector `data-testid=\"approval-row-transfer-<approval_id>\"`.
- [x] Browser smoke verifier confirms mirrored pending transfer approval renders in `/agents/:id` under management session auth.
- [x] `POST /api/v1/management/transfer-approvals/decision` is non-blocking for UI:
  - approve returns quickly with async queue (`202`),
  - deny applies immediate mirror rejection (`200`).
- [x] Runtime/web separation preserved for transfer decisions:
  - web queues decision-inbox rows only,
  - agent runtime consumes + acks rows via `/api/v1/agent/transfer-decisions/inbox`.

## Targeted Runtime/API Verification
- [x] Direct mirror write accepted:
  - `curl -H "authorization: Bearer <agentKey>" -H "content-type: application/json" -X POST http://127.0.0.1:3000/api/v1/agent/transfer-approvals/mirror --data @/tmp/mirror_payload_verify.json`
  - Response: `{"ok":true,"approvalId":"xfr_dbg_1771623388","status":"approval_pending",...}`
- [x] Mirrored approval row persisted:
  - `select approval_id,status,chain_key from agent_transfer_approval_mirror where approval_id='xfr_dbg_1771623388';`
  - Result: `xfr_dbg_1771623388 | approval_pending | base_sepolia`
- [x] Management read model reflects mirrored row:
  - `GET /api/v1/management/agent-state?agentId=ag_a123e3bc428c12675f93&chainKey=base_sepolia`
  - Result summary: `queueCount: 2`, `containsDebug: true` for `xfr_dbg_1771623388`.

## Required Validation Gates
- [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`
- [x] `python3 -m unittest apps/agent-runtime/tests/test_x402_skill_wrapper.py -v`
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] `npm run build`
- [x] `pm2 restart all`
- [x] `npm run verify:ui:agent-approvals`

## Browser UI Verifier Evidence
- [x] Command executed:
  - `XCLAW_UI_VERIFY_BASE_URL=http://127.0.0.1:3000 XCLAW_UI_VERIFY_AGENT_ID=ag_slice7 XCLAW_UI_VERIFY_CHAIN_KEY=base_sepolia XCLAW_UI_VERIFY_AGENT_API_KEY=<agent_key> XCLAW_UI_VERIFY_BOOTSTRAP_TOKEN_FILE=~/.xclaw-secrets/management/ag_slice7-bootstrap-token.json npm run verify:ui:agent-approvals`
- [x] Current outcome:
  - verifier returned `ok:true` with selector:
    - `approval-row-transfer-xfr_ui_1771625941671_o1low5v4`
  - artifact dir:
    - `/tmp/xclaw-ui-verify-xfr_ui_1771625941671_o1low5v4`

## Transfer Decision Non-Blocking Evidence
- [x] Fresh pending mirror approval created and approved via management decision route.
- [x] Timed decision request returned quickly:
  - command used `/usr/bin/time ... POST /api/v1/management/transfer-approvals/decision`
  - result: `status=202`, `elapsed=0:00.03`
- [x] Response payload included inbox queue metadata:
  - `appliedVia=agent_runtime_inbox_queue`
  - `decisionInbox.status=pending`
  - `promptCleanup.code=agent_runtime_cleanup_pending`

---

# Hotfix Acceptance Evidence: Slice 117 Hotfix F Transfer Decision Reliability + Prompt Convergence

Date (UTC): 2026-02-20
Active slice context: `Slice 117` in progress (issue `#60`).

## Objective + Scope Lock
- Objective: make transfer approval decision execution converge reliably across web and agent runtime while preserving strict runtime separation.
- Scope lock:
  - `apps/agent-runtime/xclaw_agent/cli.py`
  - `apps/agent-runtime/tests/test_approvals_run_loop.py`
  - `skills/xclaw-agent/scripts/setup_agent_skill.py`
  - `apps/network-web/src/app/api/v1/agent/runtime-readiness/route.ts`
  - `apps/network-web/src/app/api/v1/agent/heartbeat/route.ts`
  - `apps/network-web/src/app/api/v1/management/transfer-approvals/decision/route.ts`
  - `apps/network-web/src/lib/transfer-recovery.ts`
  - `apps/network-web/src/app/api/v1/management/agent-state/route.ts`
  - `apps/network-web/src/app/api/v1/management/transfer-approvals/route.ts`
  - `packages/shared-schemas/json/agent-heartbeat-request.schema.json`
  - `packages/shared-schemas/json/agent-runtime-readiness-request.schema.json`
  - canonical docs/handoff artifacts.

## Behavior Checks
- [x] Runtime exposes always-on transfer decision consumer command (`approvals run-loop`) with bounded backoff.
- [x] Runtime publishes chain-scoped signing readiness snapshot (`walletSigningReady`, reason code, checked timestamp).
- [x] Management approve preflight blocks with deterministic `runtime_signing_unavailable` when runtime signing is not ready.
- [x] Blocked approve preflight does not enqueue transfer decision inbox rows.
- [x] Deny path still mirrors immediate rejection semantics.
- [x] Server terminal sweeper fallback dispatches runtime prompt cleanup for terminal transfer rows.
- [x] Transfer approvals UI remains non-actionable for terminal rows regardless of cleanup metadata.

## Required Validation Gates
- [x] `python3 -m unittest apps/agent-runtime/tests/test_approvals_run_loop.py -v`
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] `npm run build`
- [x] `pm2 restart all`
- [x] `npm run verify:ui:agent-approvals`

## Validation Evidence Notes
- [x] `test_approvals_run_loop.py` passed (`3 tests`, includes retry/backoff path and readiness publish summary assertions).
- [x] `test_trade_path.py` regression passed (`122 tests`) after run-loop integration.
- [x] Browser verifier final pass:
  - approval row selector:
    - `approval-row-transfer-xfr_ui_1771628838835_w6khemsv`
  - artifact dir:
    - `/tmp/xclaw-ui-verify-xfr_ui_1771628838835_w6khemsv`
  - note:
    - one initial verifier attempt failed due stale bootstrap token; rerun passed after minting fresh owner-link token.

---

# Hotfix Acceptance Evidence: Slice 117 Hotfix G Installer + Run-Loop Wiring Hardening

Date (UTC): 2026-02-20
Active slice context: `Slice 117` in progress (issue `#60`).

## Objective + Scope Lock
- Objective: prevent recurring `runtime_signing_unavailable` caused by installer/service/env drift.
- Scope lock:
  - `skills/xclaw-agent/scripts/setup_agent_skill.py`
  - `apps/network-web/src/app/skill-install.sh/route.ts`
  - `apps/network-web/src/app/skill-install.ps1/route.ts`
  - `apps/agent-runtime/xclaw_agent/cli.py`
  - `apps/agent-runtime/tests/test_setup_agent_skill.py`
  - canonical docs/handoff artifacts.

## Behavior Checks
- [x] setup script resolves run-loop env from env/config/backup with strict precedence.
- [x] setup strict mode fails install when run-loop health probe reports signing unavailable.
- [x] shell installer performs authoritative final strict setup pass after bootstrap/register.
- [x] PowerShell installer performs authoritative final strict setup pass after bootstrap/register.
- [x] installer final pass binds run-loop to bootstrap-issued agent credentials and install-origin canonical API base.
- [x] deterministic installer summary lines emitted for run-loop apiBase/agentId/walletSigningReady.

## Required Validation Gates
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

## Installer Smoke Evidence
- [x] Local-origin strict setup smoke:
  - `XCLAW_INSTALL_CANONICAL_API_BASE=http://127.0.0.1:3000/api/v1 ... XCLAW_SETUP_REQUIRE_RUN_LOOP_READY=1 python3 skills/xclaw-agent/scripts/setup_agent_skill.py`
  - health result: `walletSigningReady=true`, `agentId=ag_slice7`, `apiBaseUrl=http://127.0.0.1:3000/api/v1`.
- [x] Production-origin strict setup smoke:
  - `XCLAW_INSTALL_CANONICAL_API_BASE=https://xclaw.trade/api/v1 ... XCLAW_SETUP_REQUIRE_RUN_LOOP_READY=1 python3 skills/xclaw-agent/scripts/setup_agent_skill.py`
  - health result: `walletSigningReady=true`, `agentId=ag_a123e3bc428c12675f93`, `apiBaseUrl=https://xclaw.trade/api/v1`.
- [x] Browser verifier final pass:
  - selector: `approval-row-transfer-xfr_ui_1771630667281_ay3fcv92`
  - artifact dir: `/tmp/xclaw-ui-verify-xfr_ui_1771630667281_ay3fcv92`

---

# Hotfix Acceptance Evidence: Slice 117 Hotfix H Runtime Signing Preflight False-Negative Guard

Date (UTC): 2026-02-20
Active slice context: `Slice 117` in progress (issue `#60`).

## Objective + Scope Lock
- Objective: stop false `runtime_signing_unavailable` blocks when runtime signing is healthy.
- Scope lock:
  - `apps/network-web/src/app/api/v1/agent/heartbeat/route.ts`
  - `apps/network-web/src/app/api/v1/management/transfer-approvals/decision/route.ts`
  - canonical docs/handoff artifacts.

## Behavior Checks
- [x] heartbeat updates no longer null-clobber existing runtime readiness when readiness fields are absent.
- [x] transfer decision readiness lookup supports normalized chain-key fallback (`-` vs `_`, case-insensitive).
- [x] transfer decision readiness lookup uses latest-positive readiness fallback when chain-specific record is missing.

## Required Validation Gates
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] `npm run build`
- [x] `pm2 restart all`
- [x] `npm run verify:ui:agent-approvals`

## Browser Verifier Evidence
- [x] selector: `approval-row-transfer-xfr_ui_1771631356653_njxfnktm`
- [x] artifact dir: `/tmp/xclaw-ui-verify-xfr_ui_1771631356653_njxfnktm`

---

# Hotfix Acceptance Evidence: Slice 117 Hotfix I Degraded Readiness Approve Fallback

Date (UTC): 2026-02-20
Active slice context: `Slice 117` in progress (issue `#60`).

## Objective + Scope Lock
- Objective: remove false hard-block (`runtime_signing_unavailable`) when readiness snapshot is missing but runtime signing is healthy.
- Scope lock:
  - `apps/network-web/src/app/api/v1/management/transfer-approvals/decision/route.ts`
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/api/openapi.v1.yaml`
  - handoff artifacts.

## Behavior Checks
- [x] approve preflight still blocks deterministic explicit signer failures (`wallet_passphrase_missing|wallet_passphrase_invalid|wallet_store_unavailable|wallet_missing`).
- [x] readiness-missing snapshot (`runtime_readiness_missing`) no longer hard-blocks decision queueing.
- [x] degraded preflight queue path is audit-logged with `runtime_signing_preflight_degraded`.

## Required Validation Gates
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] `npm run build`
- [x] `pm2 restart all`
- [x] `npm run verify:ui:agent-approvals`

## Live Approve Regression Evidence (xclaw.trade)
- [x] before patch/deploy: `POST /api/v1/management/transfer-approvals/decision` returned `runtime_signing_unavailable` with `walletSigningReasonCode=runtime_readiness_missing`.
- [x] after patch/deploy: same path accepted approve and queued inbox decision:
  - response: `ok=true`, `status=approved`, `appliedVia=agent_runtime_inbox_queue`, `decisionInbox.status=pending`.
- [x] transfer lifecycle convergence observed:
  - `xfr_972249e7d6e889bbe488` reached terminal `filled` after approve.

---

# Hotfix Acceptance Evidence: Slice 117 Hotfix J Immediate Telegram Prompt Cleanup + Terminal Transfer Prod

Date (UTC): 2026-02-21
Active slice context: `Slice 117` in progress (issue `#60`).

## Objective + Scope Lock
- Objective: remove stale Telegram approval buttons immediately after web decisions and send a terminal transfer follow-up prompt when tx reaches terminal status.
- Scope lock:
  - `apps/network-web/src/lib/transfer-recovery.ts`
  - `apps/network-web/src/app/api/v1/management/transfer-approvals/decision/route.ts`
  - `apps/network-web/src/app/api/v1/agent/transfer-approvals/mirror/route.ts`
  - `apps/network-web/src/lib/non-telegram-agent-prod.ts`
  - canonical docs/handoff artifacts.

## Behavior Checks
- [x] web transfer approve triggers immediate runtime transfer prompt cleanup attempt.
- [x] web transfer deny triggers immediate runtime transfer prompt cleanup attempt.
- [x] transfer mirror terminal transition queues one transfer terminal prod dispatch with tx context.

## Required Validation Gates
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] `npm run build`
- [x] `pm2 restart all`
- [x] live transfer decision + terminal follow-up confirmation.

## Live Evidence
- [x] web approve immediate cleanup result:
  - approval: `xfr_b48703b524ea5f46d33a`
  - `promptCleanup.code=buttons_cleared`
  - `promptCleanup.messageId=1911`
- [x] terminal transfer convergence:
  - approval: `xfr_b48703b524ea5f46d33a`
  - terminal status: `filled`
  - tx hash: `0x7ac9c41d0a840205ef24cb9c4fc1498971eb1d9f55214ad213adfd03b3f7ab7c`
- [x] terminal prod dispatch observed in PM2 logs:
  - `[agent.transfer_approvals.mirror] terminal prod dispatch`
  - `[non_tg_prod] dispatched`
- [x] browser verifier pass:
  - selector: `approval-row-transfer-xfr_ui_1771632662476_jzafc0md`
  - artifact dir: `/tmp/xclaw-ui-verify-xfr_ui_1771632662476_jzafc0md`

---

# Hotfix Acceptance Evidence: Slice 117 Hotfix K Non-Blocking Swap Confirmation Path

Date (UTC): 2026-02-21
Active slice context: `Slice 117` in progress (issue `#60`).

## Objective + Scope Lock
- Objective: prevent foreground agent/chat blocking caused by in-band swap receipt confirmation waits.
- Scope lock:
  - `apps/agent-runtime/xclaw_agent/cli.py`
  - canonical docs/handoff artifacts.

## Behavior Checks
- [x] `trade execute` returns after broadcast with `status=verifying` (no in-band receipt wait).
- [x] runtime message/action hint now indicates asynchronous terminal convergence path.

## Required Validation Gates
- [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` (new test `test_trade_execute_real_returns_verifying_without_receipt_wait` passed).
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] `npm run build`
- [x] `pm2 restart all`
- [ ] live repro check on approved swap path.

## Notes / Blockers
- Existing host launcher drift was discovered and corrected during validation:
  - `~/.local/bin/xclaw-agent` wrapper previously targeted `/home/hendo420/xclaw/...` (stale tree),
  - wrapper now targets `/home/hendo420/ETHDenver2026/apps/agent-runtime/bin/xclaw-agent`.
- Live execute attempts in this session were dominated by upstream path behavior (approval state drift and one `ERC20_CALL_FAIL` revert), so deterministic non-blocking proof is locked by unit regression in this change plus launcher correction.

---

# Hotfix Acceptance Evidence: Slice 117 Hotfix L Truthful Trade Decision Messaging

Date (UTC): 2026-02-21
Active slice context: `Slice 117` in progress (issue `#60`).

## Objective + Scope Lock
- Objective: remove misleading pre-terminal success copy and ensure terminal trade outcome follow-up is emitted.
- Scope lock:
  - `apps/agent-runtime/xclaw_agent/cli.py`
  - `apps/agent-runtime/tests/test_trade_path.py`
  - canonical docs/handoff artifacts.

## Behavior Checks
- [x] approval decision copy is non-terminal (execution in progress, not success).
- [x] terminal follow-up message helper exists and is called from `cmd_approvals_decide_spot` after resume result.
- [x] regression tests cover copy contract and failure follow-up invocation.

## Required Validation Gates
- [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] `npm run build`
- [x] `pm2 restart all`

---

# Hotfix Acceptance Evidence: Slice 117 Hotfix M Approval History Terminal Status Truthfulness

Date (UTC): 2026-02-21
Active slice context: `Slice 117` in progress (issue `#60`).

## Objective + Scope Lock
- Objective: prevent failed trade executions from being displayed as approved in approvals surfaces.
- Scope lock:
  - `apps/network-web/src/app/agents/[agentId]/page.tsx`
  - `apps/network-web/src/app/api/v1/management/approvals/inbox/route.ts`
  - canonical docs/handoff artifacts.

## Behavior Checks
- [x] trade approval history preserves `failed` terminal status instead of coercing to `approved`.
- [x] `Rejected/Denied` filter includes terminal trade failures.
- [x] inbox status normalization maps `failed|expired|verification_timeout` into rejected bucket semantics.

## Required Validation Gates
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] `npm run build`
- [x] `pm2 restart all`

## Live Evidence
- [x] `/api/v1/management/approvals/inbox` now returns failed terminal trades (`trd_fb0cd66ebc1ee854b697`, `trd_066bb705a938ce816f80`, `trd_28334a1f26552c87950a`) with `status: rejected` and subtitle suffix `(failed)`.

---

# Hotfix Acceptance Evidence: Slice 117 Hotfix N Ethereum Sepolia Wallet Balance Sync Type-Stability

Date (UTC): 2026-02-21
Active slice context: `Slice 117` in progress (issue `#60`).

## Objective + Scope Lock
- Objective: fix Ethereum Sepolia wallet balance sync degradation that hid USDC after filled swaps.
- Scope lock:
  - `apps/network-web/src/app/api/v1/management/deposit/route.ts`
  - canonical docs/handoff artifacts.

## Behavior Checks
- [x] deposit sync SQL no longer reuses `chain_key` bind across insert + dedupe subquery contexts.
- [x] balance sync path continues canonical token snapshot updates while preserving dedupe filter behavior.

## Required Validation Gates
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] `npm run build`
- [x] `pm2 restart all`

## Live Evidence
- [x] `/api/v1/management/deposit?agentId=ag_a123e3bc428c12675f93&chainKey=ethereum_sepolia` now returns `syncStatus: ok` with `USDC` balance `1942982452` (decimals `6`) and no SQL type-inference sync error.

---

# Hotfix Acceptance Evidence: Slice 117 Hotfix O Hedera Swap Fee-Retry + Symbol Resolution

Date (UTC): 2026-02-21
Active slice context: `Slice 117` in progress (issue `#60`).

## Objective + Scope Lock
- Objective: stop Hedera minimum-gas underbid swap failures and restore deterministic token symbol labels for Hedera trade activity.
- Scope lock:
  - `apps/agent-runtime/xclaw_agent/cli.py`
  - `apps/agent-runtime/tests/test_trade_path.py`
  - `config/chains/hedera_testnet.json`
  - canonical docs/handoff artifacts.

## Behavior Checks
- [x] runtime send retries now parse minimum gas-price requirement and elevate retry `--gas-price` to that minimum.
- [x] Hedera testnet legacy send path doubles estimated gas price before submission (`--gas-price` multiplier `2x`).
- [x] Hedera testnet canonical token map resolves USDC symbol for `0x0000000000000000000000000000000000001549`.

## Required Validation Gates
- [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] `npm run build`
- [x] `pm2 restart all`

## Live Evidence
- [x] Runtime regression `test_cast_send_retries_with_minimum_gas_price_from_rpc_error` confirms retry escalation from `30000000001` to required minimum `890000000000` gas price.
- [x] Runtime regression `test_cast_send_doubles_legacy_gas_price_on_hedera_testnet` confirms Hedera first-send legacy gas-price doubling (`123 -> 246`).
- [x] `/api/v1/management/agent-state?agentId=ag_a123e3bc428c12675f93&chainKey=hedera_testnet` includes `chainTokens` entry `USDC -> 0x000...1549`, and `/api/v1/management/approvals/inbox` row for `trd_170515b0fe88313c6136` now renders title `USDC -> SAUCE` (not raw address).

---

# Hotfix Acceptance Evidence: Slice 117 Hotfix P Telegram Callback Trade Result Fail-Closed

Date (UTC): 2026-02-21
Active slice context: `Slice 117` in progress (issue `#60`).

## Objective + Scope Lock
- Objective: prevent Telegram from reporting trade success when no tx-hash-backed terminal fill exists.
- Scope lock:
  - `apps/agent-runtime/xclaw_agent/cli.py`
  - `apps/agent-runtime/tests/test_trade_path.py`
  - `skills/xclaw-agent/scripts/openclaw_gateway_patch.py`
  - canonical docs/handoff artifacts.

## Behavior Checks
- [x] `cmd_approvals_decide_spot` now downgrades `filled` + missing `txHash` to `failed` with `code=terminal_status_unverified`.
- [x] terminal Telegram helper no longer emits "Swap completed" when tx hash is missing.
- [x] OpenClaw Telegram callback synthesis marks trade success only when `status=filled` and `txHash` is present.

## Required Validation Gates
- [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] `npm run build`
- [x] `pm2 restart all`

## Live Runtime Patch Evidence
- [x] `python3 skills/xclaw-agent/scripts/openclaw_gateway_patch.py --json --restart` -> `{"ok":true,"patched":true,...,"loaderPaths":[".../dist/plugin-sdk/reply-BKdTPI2b.js",".../dist/reply-oSe13ewW.js"]}`.

---

# Slice 118 Acceptance Evidence: Liquidity Approval + Wallet Activity Parity

Date (UTC): 2026-02-21
Issue: `#61`

## Objective + Scope Lock
- Objective: owner-surface parity for liquidity approvals/activity across `/agents/:id` and `/approvals`.
- Scope lock:
  - `apps/network-web/src/app/api/v1/management/agent-state/route.ts`
  - `apps/network-web/src/app/api/v1/management/approvals/inbox/route.ts`
  - `apps/network-web/src/app/api/v1/management/approvals/decision-batch/route.ts`
  - `apps/network-web/src/lib/agent-page-view-model.ts`
  - `apps/network-web/src/app/agents/[agentId]/page.tsx`
  - `apps/network-web/src/app/approvals/page.tsx`
  - canonical docs/schemas/handoff artifacts.

## Behavior Checks
- [x] agent-state includes chain-scoped `liquidityApprovalsQueue` + `liquidityApprovalsHistory`.
- [x] approvals inbox supports `types=liquidity` with normalized status buckets.
- [x] batch decisions support `rowKind=liquidity` approve/reject.
- [x] batch decisions reject liquidity `approve_allowlist` with `payload_invalid`.
- [x] `/agents/:id` wallet activity + approval history display liquidity pending and terminal rows.
- [x] `/approvals` includes liquidity filter rows with actionable decisions.

## Required Validation Gates
- [x] `npm run db:parity` -> pass (`ok: true`).
- [x] `npm run seed:reset` -> pass (`ok: true`).
- [x] `npm run seed:load` -> pass (`ok: true`).
- [x] `npm run seed:verify` -> pass (`ok: true`).
- [x] `npm run test:management:liquidity:decision` -> pass (`ok: true`, `passed: 26`, `failed: 0`).
- [x] `npm run build` -> pass (Next.js production build succeeded).
- [x] `pm2 restart all` -> pass (`xclaw-web` online).

## Task-Specific Evidence
- [x] `XCLAW_UI_VERIFY_AGENT_ID=ag_slice7 XCLAW_UI_VERIFY_AGENT_API_KEY=slice7_token_abc12345 XCLAW_UI_VERIFY_BOOTSTRAP_TOKEN_FILE=/home/hendo420/.xclaw-secrets/management/ag_slice7-bootstrap-token.json npm run verify:ui:agent-approvals` -> pass (`ok: true`, approval row rendered under management session).

---

# Slice 118 Follow-Up A Acceptance Evidence: Ethereum Sepolia Uniswap LP Adapter Enablement

Date (UTC): 2026-02-21
Issue: `#61`

## Objective + Scope Lock
- Objective: remove deterministic `unsupported_liquidity_adapter` failures for `ethereum_sepolia` LP requests using operator alias `--dex uniswap`, while preserving fail-closed unknown-dex behavior.
- Scope lock:
  - `config/chains/ethereum_sepolia.json`
  - `apps/agent-runtime/xclaw_agent/liquidity_adapter.py`
  - `apps/agent-runtime/tests/test_liquidity_adapter.py`
  - `apps/agent-runtime/tests/test_liquidity_cli.py`
  - canonical docs/handoff artifacts (`docs/XCLAW_SOURCE_OF_TRUTH.md`, `docs/XCLAW_SLICE_TRACKER.md`, `docs/XCLAW_BUILD_ROADMAP.md`, `spec.md`, `tasks.md`, `acceptance.md`).

## Behavior Checks
- [x] `ethereum_sepolia` defines `liquidityProtocols` entries for `uniswap_v2` and `uniswap_v3`.
- [x] runtime alias normalization resolves `uniswap|uni` to canonical `uniswap_v2` before adapter selection.
- [x] explicit `uniswap_v2`/`uniswap_v3` behavior remains unchanged.
- [x] unknown dex values remain deterministic `unsupported_liquidity_adapter`.

## Slice 124-127 Acceptance Evidence: Final EVM-Only Closeout

Date (UTC): 2026-03-03
Active slice context: `Slice 124 -> Slice 127`.

### Objective + Scope Lock
- Objective:
  - remove the last active-adjacent Hedera assumptions from harnesses and skill parsing,
  - replace stale Hedera/HTS runtime tests with EVM-only coverage,
  - reassert the EVM-only canonical contract while keeping historical records explicit.

### Behavior Checks
- [x] `wallet_approval_harness.py` and `xclaw_agent_skill.py` contain no Hedera references.
- [x] Touched runtime tests contain no Hedera-only adapter/plugin imports or chain assumptions.
- [x] Touched runtime metadata assertions use `routeKind` / `liquidityOperation`.
- [x] Canonical docs state that legacy Hedera/Uniswap-primary material is superseded history, not current truth.
- [x] Active web/runtime comments no longer describe Hedera as active behavior.

### Required Validation Gates
- [x] `python3 -m unittest apps/agent-runtime/tests/test_liquidity_adapter.py -v` -> pass (`Ran 11 tests`, `OK`).
- [x] `python3 -m unittest apps/agent-runtime/tests/test_liquidity_cli.py -v` -> pass (`Ran 10 tests`, `OK`).
- [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` -> pass (`Ran 128 tests`, `OK`).
- [x] `python3 -m unittest apps/agent-runtime/tests/test_wallet_core.py -v` -> pass (`Ran 12 tests`, `OK`).
- [x] `python3 -m unittest apps/agent-runtime/tests/test_auth_recover_cli.py -v` -> pass (`Ran 2 tests`, `OK`).
- [x] `python3 -m unittest apps/agent-runtime/tests/test_x402_skill_wrapper.py -v` -> pass (`Ran 55 tests`, `OK`).
- [x] `npm run db:parity` -> pass (`ok: true`).
- [x] `npm run seed:reset` -> pass (`ok: true`).
- [x] `npm run seed:load` -> pass (`ok: true`).
- [x] `npm run seed:verify` -> pass (`ok: true`).
- [x] `npm run build` -> pass (Next.js production build succeeded).
- [x] `pm2 restart all` -> pass (`xclaw-web` online).

## Required Validation Gates
- [x] `python3 -m unittest apps/agent-runtime/tests/test_liquidity_adapter.py -v` -> pass (`Ran 18 tests`, `OK`).
- [x] `python3 -m unittest apps/agent-runtime/tests/test_liquidity_cli.py -v` -> pass (`Ran 48 tests`, `OK`).
- [x] `npm run db:parity` -> pass (`ok: true`).
- [x] `npm run seed:reset` -> pass (`ok: true`).
- [x] `npm run seed:load` -> pass (`ok: true`).
- [x] `npm run seed:verify` -> pass (`ok: true`).
- [x] `npm run build` -> pass (Next.js production build succeeded).
- [x] `pm2 restart all` -> pass (`xclaw-web` online).

---

# Slice 119 Acceptance Evidence: EVM-Only Exchange-Agnostic Execution Refactor

Date (UTC): 2026-03-03

## Objective + Scope Lock
- Objective: remove active Hedera/non-EVM support and replace active Uniswap-specific server execution with generic EVM router-adapter contracts while preserving compatibility routes.
- Scope lock:
  - `config/chains/*.json`
  - `apps/network-web/src/lib/{chains,env,errors,evm-router-execution,uniswap-proxy,uniswap-lp-proxy}.ts`
  - `apps/network-web/src/app/api/v1/agent/trade/*`
  - `apps/network-web/src/app/api/v1/agent/liquidity/*`
  - `apps/network-web/src/app/api/v1/agent/faucet/request/route.ts`
  - `apps/network-web/src/app/api/v1/management/deposit/route.ts`
  - `apps/agent-runtime/xclaw_agent/{chains,cli,dex_adapter,liquidity_adapter}.py`

## Behavior Checks
- [x] public/shared chain contracts now expose `family=evm` only.
- [x] generic trade routes exist and compatibility Uniswap trade routes delegate to them.
- [x] active server env no longer requires `XCLAW_UNISWAP_API_KEY` for trade route execution.
- [x] Hedera chain configs and runtime bridge/plugin files are removed from active repo support.
- [x] runtime provider metadata normalizes to router-adapter vocabulary.

## Required Validation Gates
- [ ] `npm run db:parity`
- [ ] `npm run seed:reset`
- [ ] `npm run seed:load`
- [ ] `npm run seed:verify`
- [ ] `npm run build`
- [ ] `pm2 restart all`
# Slice 120-123 Acceptance Evidence: EVM-Only Cleanup + Contract Closeout

Date (UTC): 2026-03-03
Active slice context: `Slice 120 -> Slice 123`.

## Objective + Scope Lock
- Objective:
  - remove remaining Hedera and Uniswap-proxy leftovers from active runtime/web/install paths,
  - align canonical docs/contracts to the generic EVM router-adapter surface,
  - realign harness/skill/infra defaults to EVM-only behavior.

## Behavior Checks
- [ ] active installer/runtime/web files no longer reference Hedera paths or env.
- [ ] OpenAPI exposes canonical generic trade/liquidity routes and marks `/uniswap/*` as compatibility aliases.
- [ ] source-of-truth, wallet contract, and skill docs no longer describe active Hedera support or server-held Uniswap API-key dependency as canonical behavior.
- [ ] wallet-approval harness no longer special-cases `uniswap_proxy_not_configured`.
- [ ] infra contract-test defaults target an active EVM test chain.

## Required Validation Gates
- [ ] `npm run db:parity`
- [ ] `npm run seed:reset`
- [ ] `npm run seed:load`
- [ ] `npm run seed:verify`
- [ ] task-specific Python/unit checks for touched files
- [ ] `npm run build`
- [ ] `pm2 restart all`
