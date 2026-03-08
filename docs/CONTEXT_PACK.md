# X-Claw Context Pack

## Current Canonical Context (2026-03-03)

- Active X-Claw delivery scope is dual-family (`evm` + `solana`).
- Hedera/HTS bridge and plugin material below is preserved as superseded slice history, not current runtime scope.
- Canonical execution vocabulary is router-adapter based:
  - `providerRequested`
  - `providerUsed`
  - `fallbackUsed`
  - `fallbackReason`
  - `executionFamily`
  - `executionAdapter`
  - `routeKind`
  - `liquidityOperation`

## Completed Context: Slice 240 Local State, Replay, and Corruption Hardening

Issue mapping: `#93`

### Objective + scope lock
- Objective:
  - harden local runtime state, replay, approval prompt, transfer flow, trade-cap, and policy helpers against corrupted local payloads and duplicate replay cases,
  - preserve runtime JSON/CLI behavior and current command/test contracts,
  - keep public runtime contracts unchanged.
- Scope guard:
  - runtime internal reliability hardening only,
  - no API/schema/database changes.

### Expected touched files
- `apps/agent-runtime/tests/test_runtime_services.py`
- `apps/agent-runtime/tests/test_trade_path.py`
- `apps/agent-runtime/tests/test_approvals_run_loop.py`
- `apps/agent-runtime/tests/test_liquidity_cli.py`
- `apps/agent-runtime/xclaw_agent/runtime/services/trade_caps.py`
- `docs/XCLAW_SOURCE_OF_TRUTH.md`
- `docs/XCLAW_SLICE_TRACKER.md`
- `docs/XCLAW_BUILD_ROADMAP.md`
- `docs/CONTEXT_PACK.md`
- `spec.md`
- `tasks.md`
- `acceptance.md`

### Completion note
- Completed 2026-03-08 with direct corruption/replay coverage for runtime state, transfer flow, approval prompt, trade-cap, and transfer policy services, plus the required sequential validation chain (`db:parity`, `seed:reset/load/verify`, `build`, `pm2 restart all`).

## Completed Context: Slice 239 Transport and Remote Failure Hardening

Issue mapping: `#92`

### Objective + scope lock
- Objective:
  - harden remote/API/mirroring/reporting/Telegram delivery runtime service seams against transport and malformed-response failures,
  - preserve runtime JSON/CLI behavior and current wrapper/test seams,
  - keep public runtime contracts unchanged.
- Scope guard:
  - runtime internal reliability hardening only,
  - no API/schema/database changes.

### Expected touched files
- `apps/agent-runtime/tests/test_runtime_services.py`
- `apps/agent-runtime/tests/test_trade_path.py`
- `apps/agent-runtime/tests/test_x402_cli.py`
- `docs/XCLAW_SOURCE_OF_TRUTH.md`
- `docs/XCLAW_SLICE_TRACKER.md`
- `docs/XCLAW_BUILD_ROADMAP.md`
- `docs/CONTEXT_PACK.md`
- `spec.md`
- `tasks.md`
- `acceptance.md`

### Completion note
- Completed 2026-03-08 with expanded remote/transport negative-path coverage plus targeted runtime regressions and the required sequential validation chain (`db:parity`, `seed:reset/load/verify`, `build`, `pm2 restart all`).

## Completed Context: Slice 238 Cross-Service Invariants + Residual cli.py Audit

Issue mapping: `#89`

### Objective + scope lock
- Objective:
  - add direct cross-service invariant coverage for runtime service seams,
  - prove residual `cli.py` helpers in audited seams are thin compatibility wrappers,
  - preserve runtime JSON/CLI behavior with no public contract drift.
- Scope guard:
  - runtime internal audit-and-test hardening only,
  - no API/schema/database changes.

### Expected touched files
- `apps/agent-runtime/tests/test_runtime_invariants.py`
- `apps/agent-runtime/xclaw_agent/cli.py` (only if residual non-wrapper helper ownership is found)
- `apps/agent-runtime/tests/test_runtime_services.py`
- `apps/agent-runtime/tests/test_runtime_adapters.py`
- `apps/agent-runtime/tests/test_trade_path.py`
- `apps/agent-runtime/tests/test_liquidity_cli.py`
- `apps/agent-runtime/tests/test_x402_cli.py`
- `docs/XCLAW_SOURCE_OF_TRUTH.md`
- `docs/XCLAW_SLICE_TRACKER.md`
- `docs/XCLAW_BUILD_ROADMAP.md`
- `docs/CONTEXT_PACK.md`
- `spec.md`
- `tasks.md`
- `acceptance.md`

### Completion note
- Completed 2026-03-08 with direct invariant coverage, a wrapper-only residual `cli.py` audit for the scoped seams, and the required sequential validation chain (`db:parity`, `seed:reset/load/verify`, `build`, `pm2 restart all`).

## Completed Context: Slice 237 Transfer-Flow/Approval-Prompt/Trade-Cap Resilience

Issue mapping: `#91`

### Objective + scope lock
- Objective:
  - harden transfer-flow, approval-prompt, and trade-cap services against malformed local state and partial failures,
  - preserve runtime JSON/CLI behavior and approval/replay contracts,
  - keep current command-surface behavior unchanged.
- Scope guard:
  - runtime internal hardening only,
  - no API/schema/database changes.

### Expected touched files
- `apps/agent-runtime/xclaw_agent/runtime/services/transfer_flows.py`
- `apps/agent-runtime/xclaw_agent/runtime/services/approval_prompts.py`
- `apps/agent-runtime/xclaw_agent/runtime/services/trade_caps.py`
- `apps/agent-runtime/tests/test_runtime_services.py`
- `apps/agent-runtime/tests/test_trade_path.py`
- `apps/agent-runtime/tests/test_approvals_run_loop.py`
- `apps/agent-runtime/tests/test_liquidity_cli.py`
- `docs/XCLAW_SOURCE_OF_TRUTH.md`
- `docs/XCLAW_SLICE_TRACKER.md`
- `docs/XCLAW_BUILD_ROADMAP.md`
- `docs/CONTEXT_PACK.md`
- `spec.md`
- `tasks.md`
- `acceptance.md`

### Completion note
- Completed 2026-03-08 with direct resilience coverage plus targeted runtime regressions and the required sequential validation chain (`db:parity`, `seed:reset/load/verify`, `build`, `pm2 restart all`).
## Completed Context: Slice 236 API/Mirroring/Reporting Failure-Injection Hardening

Issue mapping: `#90`

### Objective + scope lock
- Objective:
  - harden runtime API, mirroring, and reporting services against malformed and non-2xx responses,
  - preserve runtime JSON/CLI behavior and delivery/reporting contracts,
  - keep current `cli.py` wrapper/test seams stable.
- Scope guard:
  - runtime internal hardening only,
  - no API/schema/database changes.

### Expected touched files
- `apps/agent-runtime/xclaw_agent/runtime/services/agent_api.py`
- `apps/agent-runtime/xclaw_agent/runtime/services/mirroring.py`
- `apps/agent-runtime/xclaw_agent/runtime/services/reporting.py`
- `apps/agent-runtime/tests/test_runtime_services.py`
- `apps/agent-runtime/tests/test_trade_path.py`
- `apps/agent-runtime/tests/test_x402_cli.py`
- `docs/XCLAW_SOURCE_OF_TRUTH.md`
- `docs/XCLAW_SLICE_TRACKER.md`
- `docs/XCLAW_BUILD_ROADMAP.md`
- `docs/CONTEXT_PACK.md`
- `spec.md`
- `tasks.md`
- `acceptance.md`

### Completion note
- Completed 2026-03-08 with direct negative-path runtime service coverage plus targeted runtime regressions and the required sequential validation chain (`db:parity`, `seed:reset/load/verify`, `build`, `pm2 restart all`).

## Completed Context: Slice 235 Status/Reporting Services + Final cli.py Audit

Issue mapping: `#88`

### Objective + scope lock
- Objective:
  - move trade/liquidity status posting and trade execution report helper ownership out of `cli.py`,
  - preserve runtime JSON/CLI behavior and reporting/status contracts,
  - keep `cli.py` as parser/router + thin compatibility wrappers only.
- Scope guard:
  - runtime internal hardening only,
  - no API/schema/database changes.

### Expected touched files
- `apps/agent-runtime/xclaw_agent/cli.py`
- `apps/agent-runtime/xclaw_agent/runtime/services/__init__.py`
- `apps/agent-runtime/xclaw_agent/runtime/services/reporting.py`
- `apps/agent-runtime/tests/test_runtime_services.py`
- `apps/agent-runtime/tests/test_trade_path.py`
- `apps/agent-runtime/tests/test_liquidity_cli.py`
- `apps/agent-runtime/tests/test_x402_cli.py`
- `docs/XCLAW_SOURCE_OF_TRUTH.md`
- `docs/XCLAW_SLICE_TRACKER.md`
- `docs/XCLAW_BUILD_ROADMAP.md`
- `docs/CONTEXT_PACK.md`
- `spec.md`
- `tasks.md`
- `acceptance.md`

### Completion note
- Completed 2026-03-08 with direct runtime reporting-service coverage plus targeted runtime regressions and the required sequential validation chain (`db:parity`, `seed:reset/load/verify`, `build`, `pm2 restart all`).

## Completed Context: Slice 234 Telegram Messaging + Delivery Cleanup Services

Issue mapping: `#87`

### Objective + scope lock
- Objective:
  - move Telegram and owner-link delivery helper ownership out of `cli.py`,
  - preserve runtime JSON/CLI behavior and approval UX contracts,
  - keep `cli.py` as parser/router + thin compatibility wrappers only.
- Scope guard:
  - runtime internal hardening only,
  - no API/schema/database changes.

### Expected touched files
- `apps/agent-runtime/xclaw_agent/cli.py`
- `apps/agent-runtime/xclaw_agent/runtime/services/__init__.py`
- `apps/agent-runtime/xclaw_agent/runtime/services/telegram_delivery.py`
- `apps/agent-runtime/xclaw_agent/runtime/services/owner_link_delivery.py`
- `apps/agent-runtime/tests/test_runtime_services.py`
- `apps/agent-runtime/tests/test_trade_path.py`
- `apps/agent-runtime/tests/test_approvals_run_loop.py`
- `apps/agent-runtime/tests/test_liquidity_cli.py`
- `apps/agent-runtime/tests/test_x402_cli.py`
- `docs/XCLAW_SOURCE_OF_TRUTH.md`
- `docs/XCLAW_SLICE_TRACKER.md`
- `docs/XCLAW_BUILD_ROADMAP.md`
- `docs/CONTEXT_PACK.md`
- `spec.md`
- `tasks.md`
- `acceptance.md`

### Completion note
- Completed 2026-03-08 with direct runtime service coverage plus targeted runtime regressions and the required sequential validation chain (`db:parity`, `seed:reset/load/verify`, `build`, `pm2 restart all`).

### Completion note
- Completed 2026-03-08 with direct runtime service coverage plus targeted runtime regressions and the required sequential validation chain (`db:parity`, `seed:reset/load/verify`, `build`, `pm2 restart all`).

## Hotfix Context: Slice 219 EVM Reliability + Mock/Stub Elimination

Issue mapping: `#72`

### Objective + scope lock
- Objective:
  - remove opaque `500` failures on active EVM contract paths (`agent/register`, tracked-token mirror),
  - keep historical mock fields compatibility while ensuring active EVM execution surfaces use network mode (`real`),
  - refresh contract/e2e scripts to stop proposing mock-mode execution requests.
- Scope guard:
  - EVM API/runtime stability + script contract cleanup only,
  - no breaking schema removals for historical `mode/is_mock/mockReceiptId` fields.

### Expected touched files
- `apps/network-web/src/app/api/v1/agent/register/route.ts`
- `apps/network-web/src/app/api/v1/agent/tokens/mirror/route.ts`
- `infrastructure/scripts/tokens-mirror-contract-tests.mjs`
- `infrastructure/scripts/e2e-full-pass.sh`
- `docs/XCLAW_SOURCE_OF_TRUTH.md`
- `docs/XCLAW_SLICE_TRACKER.md`
- `docs/XCLAW_BUILD_ROADMAP.md`
- `docs/CONTEXT_PACK.md`
- `spec.md`
- `tasks.md`
- `acceptance.md`

## Hotfix Context: Slice 220 Solana Reliability + Capability Truth Alignment

Issue mapping: `#73`

### Objective + scope lock
- Objective:
  - resolve Solana reliability drift caused by stale deferred-capability assertions,
  - add fail-closed runtime coverage for active Solana command surfaces,
  - confirm promoted Solana mainnet advanced LP and Solana contract surfaces stay deterministic.
- Scope guard:
  - Solana capability-truth alignment + fail-closed runtime coverage + verification evidence only,
  - no schema/database breaking changes.

### Expected touched files
- `apps/agent-runtime/tests/test_liquidity_adapter.py`
- `apps/agent-runtime/tests/test_trade_path.py`
- `infrastructure/scripts/management-solana-contract-tests.mjs`
- `infrastructure/scripts/x402-solana-contract-tests.mjs`
- `docs/XCLAW_SOURCE_OF_TRUTH.md`
- `docs/XCLAW_SLICE_TRACKER.md`
- `docs/XCLAW_BUILD_ROADMAP.md`
- `docs/CONTEXT_PACK.md`
- `spec.md`
- `tasks.md`
- `acceptance.md`

## Hotfix Context: Slice 216 Solana Mainnet Alias + Dropdown Testnet Grouping

Issue mapping: `#69`

### Objective + scope lock
- Objective:
  - keep backward compatibility with existing `solana_mainnet_beta` chain-key persistence,
  - expose `solana_mainnet` in user-facing runtime/Telegram copy,
  - group Solana non-mainnet options under `Testnets` in chain dropdowns.
- Scope guard:
  - runtime chain alias normalization + display copy only,
  - web dropdown grouping only,
  - no schema/DB/API route changes.

### Expected touched files
- `apps/agent-runtime/xclaw_agent/chains.py`
- `apps/agent-runtime/xclaw_agent/cli.py`
- `apps/agent-runtime/tests/test_trade_path.py`
- `apps/agent-runtime/tests/test_chain_aliases.py`
- `apps/network-web/src/components/chain-header-control.tsx`
- `skills/xclaw-agent/scripts/xclaw_agent_skill.py`
- `docs/XCLAW_SOURCE_OF_TRUTH.md`
- `docs/XCLAW_SLICE_TRACKER.md`
- `docs/XCLAW_BUILD_ROADMAP.md`
- `docs/CONTEXT_PACK.md`
- `spec.md`
- `tasks.md`
- `acceptance.md`

## Hotfix Context: Slice 217 Solana Token Symbol Resolution on Agent Page

Issue mapping: `#70`

### Objective + scope lock
- Objective:
  - stop showing raw Solana mint addresses in agent-page wallet/approval labels when symbol metadata exists,
  - keep EVM token-label behavior unchanged.
- Scope guard:
  - agent page + agent-page view-model only,
  - no API/schema/database/runtime execution changes.

### Expected touched files
- `apps/network-web/src/lib/agent-page-view-model.ts`
- `apps/network-web/src/app/agents/[agentId]/page.tsx`
- `docs/XCLAW_SOURCE_OF_TRUTH.md`
- `docs/XCLAW_SLICE_TRACKER.md`
- `docs/XCLAW_BUILD_ROADMAP.md`
- `docs/CONTEXT_PACK.md`
- `spec.md`
- `tasks.md`
- `acceptance.md`

## Hotfix Context: Slice 218 Solana Naming UX Tightening

Issue mapping: `#71`

### Objective + scope lock
- Objective:
  - remove `solana_localnet` from production web dropdown selectors,
  - avoid exposing `solana_mainnet_beta` wording in skill user-facing output.
- Scope guard:
  - web dropdown component + skill wrapper output normalization only,
  - no API/schema/database/runtime execution changes.

### Expected touched files
- `apps/network-web/src/components/chain-header-control.tsx`
- `skills/xclaw-agent/scripts/xclaw_agent_skill.py`
- `apps/agent-runtime/tests/test_x402_skill_wrapper.py`
- `docs/XCLAW_SOURCE_OF_TRUTH.md`
- `docs/XCLAW_SLICE_TRACKER.md`
- `docs/XCLAW_BUILD_ROADMAP.md`
- `docs/CONTEXT_PACK.md`
- `spec.md`
- `tasks.md`
- `acceptance.md`

## Hotfix Context: Slice 215 Solana Trade Status Schema Parity

Issue mapping: `#68`

### Objective + scope lock
- Objective: fix Solana trade execution status updates failing schema validation due to EVM-only `txHash` pattern.
- Scope guard:
  - shared `trade-status` schema + OpenAPI description only,
  - no route logic changes,
  - no database changes.

### Expected touched files
- `packages/shared-schemas/json/trade-status.schema.json`
- `docs/api/openapi.v1.yaml`
- `docs/XCLAW_SOURCE_OF_TRUTH.md`
- `docs/XCLAW_SLICE_TRACKER.md`
- `docs/XCLAW_BUILD_ROADMAP.md`
- `docs/CONTEXT_PACK.md`
- `spec.md`
- `tasks.md`
- `acceptance.md`

## Hotfix Context: Slice 214 Installer Bootstrap Signature Auto-Recovery

Issue mapping: `#67`

### Objective + scope lock
- Objective: remove manual recovery steps when installer fails at bootstrap challenge signing despite an existing wallet/agent state.
- Scope guard:
  - installer script only (`/skill-install.sh`),
  - no runtime trade path or API/schema changes,
  - preserve existing custody/auth boundaries.

### Expected touched files
- `apps/network-web/src/app/skill-install.sh/route.ts`
- `docs/XCLAW_SOURCE_OF_TRUTH.md`
- `docs/XCLAW_SLICE_TRACKER.md`
- `docs/XCLAW_BUILD_ROADMAP.md`
- `docs/CONTEXT_PACK.md`
- `spec.md`
- `tasks.md`
- `acceptance.md`

## Hotfix Context: Slice 213 Solana Jupiter Endpoint Resilience

Issue mapping: `#66`

### Objective + scope lock
- Objective: fix Solana swap failures on hosts where `quote-api.jup.ag` DNS/transport is unreliable by preferring resilient Jupiter defaults and keeping quote/swap endpoint selection consistent.
- Scope guard:
  - runtime Jupiter endpoint selection and retry behavior only,
  - no API/schema/database changes,
  - no slippage/amount mutation behavior changes.

### Expected touched files
- `apps/agent-runtime/xclaw_agent/solana_runtime.py`
- `apps/agent-runtime/xclaw_agent/cli.py`
- `apps/agent-runtime/tests/test_solana_runtime.py`
- `docs/XCLAW_SOURCE_OF_TRUTH.md`
- `docs/XCLAW_SLICE_TRACKER.md`
- `docs/XCLAW_BUILD_ROADMAP.md`
- `docs/CONTEXT_PACK.md`
- `spec.md`
- `tasks.md`
- `acceptance.md`

## Hotfix Context: Slice 212 Telegram Instant-Clear + Solana Swap Retry + Solana Amount Normalization

Issue mapping: `#65`

### Objective + scope lock
- Objective: improve owner approval UX responsiveness in Telegram, reduce transient Solana quote failures, and normalize Solana trade amount display on the agent page.
- Scope guard:
  - OpenClaw callback patch path only (no delete API behavior change),
  - runtime Solana Jupiter quote transport only (no slippage/amount auto-adjust),
  - agent page wallet activity display normalization only.

### Expected touched files
- `skills/xclaw-agent/scripts/openclaw_gateway_patch.py`
- `apps/agent-runtime/xclaw_agent/solana_runtime.py`
- `apps/network-web/src/app/agents/[agentId]/page.tsx`
- `apps/agent-runtime/tests/test_openclaw_gateway_patch.py`
- `apps/agent-runtime/tests/test_solana_runtime.py`
- `docs/XCLAW_SOURCE_OF_TRUTH.md`
- `docs/XCLAW_SLICE_TRACKER.md`
- `docs/XCLAW_BUILD_ROADMAP.md`
- `docs/CONTEXT_PACK.md`
- `spec.md`
- `tasks.md`
- `acceptance.md`

## Hotfix Context: Slice 209 Skill Wallet Chain-Family Validation Parity

Issue mapping: `#63`

### Objective + scope lock
- Objective: remove EVM-only skill-wrapper wallet pre-validation so Solana wallet command flows delegate to runtime while preserving trust boundaries.
- Scope guard: skill wrapper + tests + canonical docs/contract language only; no owner-link behavior changes and no route/schema path additions.

### Expected touched files
- `skills/xclaw-agent/scripts/xclaw_agent_skill.py`
- `apps/agent-runtime/tests/test_x402_skill_wrapper.py`
- `skills/xclaw-agent/SKILL.md`
- `skills/xclaw-agent/references/commands.md`
- `docs/api/WALLET_COMMAND_CONTRACT.md`
- `docs/XCLAW_SOURCE_OF_TRUTH.md`
- `docs/XCLAW_SLICE_TRACKER.md`
- `docs/XCLAW_BUILD_ROADMAP.md`
- `docs/CONTEXT_PACK.md`
- `spec.md`
- `tasks.md`
- `acceptance.md`

## Hotfix Context: Slice 210 OpenClaw Patch Anchor Alignment (Backward-Compatible)

Issue mapping: `#64`

### Objective + scope lock
- Objective: align OpenClaw gateway patch anchor matching to current upstream Telegram send path while preserving compatibility for older OpenClaw builds.
- Scope guard: gateway patcher + regression tests/fixtures + drift-check utility + canonical/process docs only.

### Expected touched files
- `.gitignore`
- `skills/xclaw-agent/scripts/openclaw_gateway_patch.py`
- `skills/xclaw-agent/scripts/check_openclaw_patch_alignment.py`
- `apps/agent-runtime/tests/test_openclaw_gateway_patch.py`
- `apps/agent-runtime/tests/fixtures/openclaw_patch/*`
- `docs/XCLAW_SOURCE_OF_TRUTH.md`
- `docs/XCLAW_SLICE_TRACKER.md`
- `docs/XCLAW_BUILD_ROADMAP.md`
- `docs/CONTEXT_PACK.md`
- `spec.md`
- `tasks.md`
- `acceptance.md`

## Hotfix Context: Capability-Gated Telegram Patch + Management-Link Fallback

Issue mapping: `#35` (approvals/install reliability track)

### Objective + scope lock
- Objective: keep installer successful across root-owned and user-owned OpenClaw installs by capability-gating gateway patching and enabling deterministic Telegram management-link fallback when patching is unavailable.
- Scope guard: shell installer only (`/skill-install.sh`) with skill-wrapper fallback toggle and doc sync.

### Expected touched files
- `apps/network-web/src/app/skill-install.sh/route.ts`
- `skills/xclaw-agent/scripts/xclaw_agent_skill.py`
- `skills/xclaw-agent/SKILL.md`
- `skills/xclaw-agent/references/commands.md`
- `docs/XCLAW_SOURCE_OF_TRUTH.md`
- `docs/XCLAW_BUILD_ROADMAP.md`
- `docs/XCLAW_SLICE_TRACKER.md`
- `docs/CONTEXT_PACK.md`
- `spec.md`
- `tasks.md`
- `acceptance.md`

## Slice 85 Context: EVM-Wide Portability Foundation (Chain-Agnostic Core, x402 Unchanged)

Issue mapping: `#35`

### Objective + scope lock
- Objective: remove hardcoded chain assumptions and make chain handling/capability gating config-driven for EVM portability.
- Scope guard: no new live chain onboarding and no x402 network expansion in this slice.

### Expected touched files (Slice 85 allowlist)
- Config/contracts:
  - `config/chains/base_sepolia.json`
  - `config/chains/kite_ai_testnet.json`
  - `config/chains/hardhat_local.json`
  - `infrastructure/migrations/0021_slice85_chain_token_metadata.sql`
  - `packages/shared-schemas/json/public-chains-response.schema.json`
- Web/API:
  - `apps/network-web/src/lib/chains.ts`
  - `apps/network-web/src/lib/active-chain.ts`
  - `apps/network-web/src/lib/token-metadata.ts`
  - `apps/network-web/src/components/chain-header-control.tsx`
  - `apps/network-web/src/app/api/v1/public/chains/route.ts`
  - `apps/network-web/src/app/api/v1/management/agent-state/route.ts`
  - `apps/network-web/src/app/api/v1/agent/faucet/request/route.ts`
  - `apps/network-web/src/app/api/v1/agent/faucet/networks/route.ts`
- Runtime/skill:
  - `apps/agent-runtime/xclaw_agent/chains.py`
  - `apps/agent-runtime/xclaw_agent/cli.py`
  - `skills/xclaw-agent/scripts/xclaw_agent_skill.py`
  - `skills/xclaw-agent/SKILL.md`
  - `skills/xclaw-agent/references/commands.md`
- Canonical docs:
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `docs/api/openapi.v1.yaml`
  - `docs/api/WALLET_COMMAND_CONTRACT.md`
  - `spec.md`
  - `tasks.md`
  - `acceptance.md`

## Slice 84 Context: Multi-Network Faucet Parity (Base Sepolia + Kite Testnet)

Issue mapping: `#34`

### Objective + scope lock
- Objective: add chain-aware faucet parity with selectable assets across `base_sepolia` and `kite_ai_testnet`.
- Scope guard: testnet-only faucet, no custody changes, no web management faucet UI.

### Expected touched files (Slice 84 allowlist)
- API:
  - `apps/network-web/src/app/api/v1/agent/faucet/request/route.ts`
  - `apps/network-web/src/app/api/v1/agent/faucet/networks/route.ts`
- Runtime/skill:
  - `apps/agent-runtime/xclaw_agent/cli.py`
  - `apps/agent-runtime/tests/test_trade_path.py`
  - `skills/xclaw-agent/scripts/xclaw_agent_skill.py`
  - `skills/xclaw-agent/SKILL.md`
  - `skills/xclaw-agent/references/commands.md`
- Contracts/docs:
  - `docs/api/openapi.v1.yaml`
  - `packages/shared-schemas/json/agent-faucet-request.schema.json`
  - `packages/shared-schemas/json/agent-faucet-response.schema.json`
  - `packages/shared-schemas/json/agent-faucet-networks-response.schema.json`
  - `docs/api/WALLET_COMMAND_CONTRACT.md`
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `spec.md`
  - `tasks.md`
  - `acceptance.md`

## Slice 83 Context: Kite AI Testnet Parity (Runtime + Web + DEX + x402)

Issue mapping: `#33`

### Objective + scope lock
- Objective: add `kite_ai_testnet` as first-class chain parity across runtime + web + x402 metadata while preserving Base behavior.
- Scope guard: no web custody changes; signing remains agent-local.

### Expected touched files (Slice 83 allowlist)
- Config/artifacts:
  - `config/chains/kite_ai_testnet.json`
  - `config/x402/networks.json`
  - `infrastructure/seed-data/kite-ai-testnet-contracts.json`
- Runtime:
  - `apps/agent-runtime/xclaw_agent/dex_adapter.py`
  - `apps/agent-runtime/xclaw_agent/cli.py`
  - `apps/agent-runtime/tests/test_dex_adapter.py`
  - `apps/agent-runtime/tests/test_x402_runtime.py`
- Web/API:
  - `apps/network-web/src/lib/active-chain.ts`
  - `apps/network-web/src/lib/chains.ts`
  - `apps/network-web/src/lib/ops-health.ts`
  - `apps/network-web/src/components/primary-nav.tsx`
  - `apps/network-web/src/app/agents/[agentId]/page.tsx`
  - `apps/network-web/src/app/api/v1/public/agents/route.ts`
  - `apps/network-web/src/app/api/v1/public/leaderboard/route.ts`
  - `apps/network-web/src/app/api/v1/management/agent-state/route.ts`
  - `apps/network-web/src/app/api/v1/management/chains/update/route.ts`
  - `apps/network-web/src/app/api/v1/management/approval-channels/update/route.ts`
  - `apps/network-web/src/app/api/v1/agent/approvals/prompt/route.ts`
  - `apps/network-web/src/app/api/v1/agent/policy-approvals/proposed/route.ts`
  - `apps/network-web/src/app/api/v1/management/x402/receive-link/route.ts`
  - `apps/network-web/src/app/api/v1/agent/x402/inbound/proposed/route.ts`
- Canonical docs/contracts:
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `docs/api/openapi.v1.yaml`
  - `docs/api/WALLET_COMMAND_CONTRACT.md`
  - `spec.md`
  - `tasks.md`
  - `acceptance.md`

### Verification plan
- Runtime tests:
  - `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`
  - `python3 -m unittest apps/agent-runtime/tests/test_x402_runtime.py -v`
  - `python3 -m unittest apps/agent-runtime/tests/test_dex_adapter.py -v`
- Required gates:
  - `npm run db:parity`
  - `npm run seed:reset`
  - `npm run seed:load`
  - `npm run seed:verify`
  - `npm run build`
  - `pm2 restart all` (after successful build; sequential)

## Slice 81 Context: Explore v2 Full Flush (No Placeholders)

Issue mapping: `#30`

### Objective + scope lock
- Objective: remove Explore placeholders and deliver full-stack Explore v2 with DB-backed strategy/risk/venue metadata, enriched verified/follower fields, and server-driven filtering/sorting/pagination.
- Scope guard honored: extend existing public routes (`/api/v1/public/agents`, `/api/v1/public/leaderboard`) and add owner-managed explore-profile routes; no Explore-only public route family.

### Expected touched files (Slice 81 allowlist)
- DB/contracts:
  - `infrastructure/migrations/0018_slice81_explore_v2.sql`
  - `packages/shared-schemas/json/management-explore-profile-request.schema.json`
  - `packages/shared-schemas/json/management-explore-profile-response.schema.json`
  - `packages/shared-schemas/json/public-agents-response.schema.json`
  - `packages/shared-schemas/json/public-leaderboard-response.schema.json`
- API:
  - `apps/network-web/src/app/api/v1/public/agents/route.ts`
  - `apps/network-web/src/app/api/v1/public/leaderboard/route.ts`
  - `apps/network-web/src/app/api/v1/management/explore-profile/route.ts`
- Web/UI:
  - `apps/network-web/src/app/explore/page.tsx`
  - `apps/network-web/src/app/explore/page.module.css`
  - `apps/network-web/src/app/agents/page.tsx`
  - `apps/network-web/src/lib/explore-page-view-model.ts`
  - `apps/network-web/src/lib/explore-page-capabilities.ts`
- Canonical docs/process:
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `docs/api/openapi.v1.yaml`
  - `docs/CONTEXT_PACK.md`
  - `spec.md`
  - `tasks.md`
  - `acceptance.md`

### Locked implementation contract
- Add `agent_explore_profile` metadata authority table (owner-managed values only).
- Public route extensions:
  - filters: `strategy`, `venue`, `riskTier`, `minFollowers`, `minVolumeUsd`, `activeWithinHours`, `verifiedOnly`.
  - sort: include `followers`.
  - row enrichments: `exploreProfile`, `verified`, `followerMeta`.
- Management metadata routes:
  - `GET /api/v1/management/explore-profile?agentId=...`
  - `PUT /api/v1/management/explore-profile`
- Explore UI:
  - functional strategy/venue/risk controls,
  - functional advanced drawer,
  - verified badge + follower metadata,
  - URL-state deep-link sync,
  - `/explore` canonical and `/agents` alias preserved.

### Verification plan
- Required gates:
  - `npm run db:parity`
  - `npm run seed:reset`
  - `npm run seed:load`
  - `npm run seed:verify`
  - `npm run build`
  - `pm2 restart all` (after successful build; sequential)

## Slice 79 Context: Agent-Skill x402 Send/Receive Runtime (No Webapp Integration)

Issue mapping: `#29`

### Objective + scope lock
- Objective: implement Python-first x402 receive/pay runtime + skill surfaces, including local approval lifecycle (`xpay_...`), tunnel management, and installer portability.
- Scope guard honored: no `apps/network-web` route/API integration in this slice.

### Expected touched files (Slice 79 allowlist)
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

### Locked runtime contract
- x402 command group:
  - `receive-request`
  - `pay|pay-resume|pay-decide`
  - `policy-get|policy-set`
  - `networks`
- x402 approval IDs: `xfr_...`.
- x402 statuses: `proposed`, `approval_pending`, `approved`, `rejected`, `executing`, `filled`, `failed`.
- Local state files:
  - `~/.xclaw-agent/pending-x402-pay-flows.json`
  - `~/.xclaw-agent/x402-policy.json`

### Network rollout lock
- Enabled now: `base_sepolia`, `base`.
- Disabled by default: `kite_ai_testnet`, `kite_ai_mainnet`.

### Verification plan
- Runtime tests:
  - `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`
  - `python3 -m unittest apps/agent-runtime/tests/test_x402_runtime.py -v`
  - `python3 -m unittest apps/agent-runtime/tests/test_x402_skill_wrapper.py -v`
- Required gates:
  - `npm run db:parity`
  - `npm run seed:reset`
  - `npm run seed:load`
  - `npm run seed:verify`
  - `npm run build`
  - `pm2 restart all` (after successful build, when PM2 available)

## Slice 76 Context: Explore / Agent Listing Frontend Refresh (`/explore` Canonical)

## Hosted x402 Receive Delta (Post-Slice 80)

- Local x402 receive tunnel flow is retired from agent skill/runtime command surface.
- `request-x402-payment` now calls hosted receive creation via agent-auth API:
  - `POST /api/v1/agent/x402/inbound/proposed`
- Local `serve-start|serve-status|serve-stop` command path is removed from active skill/runtime usage.
- Installer no longer installs or requires `cloudflared` for x402 receive behavior.

Issue mapping: `#28`

### Objective + scope lock
- Objective: rebuild Explore as canonical `/explore` while preserving existing API contracts and keeping `/agents` compatibility.
- Scope guard honored: no backend endpoints, schema, migrations, or OpenAPI changes.

### Expected touched files (Slice 76 allowlist)
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
- Canonical docs/process:
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `docs/CONTEXT_PACK.md`
  - `spec.md`
  - `tasks.md`
  - `acceptance.md`

### API/data constraints
- Directory + metrics:
  - `GET /api/v1/public/agents`
  - `GET /api/v1/public/leaderboard`
- Owner context:
  - `GET /api/v1/management/session/agents`
- Copy-trade:
  - `GET /api/v1/copy/subscriptions`
  - `POST /api/v1/copy/subscriptions`
  - `PATCH /api/v1/copy/subscriptions/:subscriptionId`

### Placeholders required in Slice 76
- Enriched strategy/risk/venue filter dimensions.
- Advanced filters drawer.
- Rich follower/status overlays not present in current payloads.

### Verification plan
- Required gates:
  - `npm run db:parity`
  - `npm run seed:reset`
  - `npm run seed:load`
  - `npm run seed:verify`
  - `npm run build`
- Functional checks:
  - viewer mode sections + gated copy CTA,
  - owner mode sections + copy-trade save flow,
  - URL/controls behavior for supported filters/sort/time-window,
  - placeholder disclosures + disabled controls,
  - desktop overflow + dark/light readability.

## Slice 75 Context: Settings & Security v1 (`/settings`) Frontend Refresh

Issue mapping: `#27`

### Objective + scope lock
- Objective: implement `/settings` as Settings & Security while preserving `/status` diagnostics and existing management APIs.
- Scope guard honored: no backend endpoints, schema, migrations, or OpenAPI changes.

### Expected touched files (Slice 75 allowlist)
- Web/UI:
  - `apps/network-web/src/app/settings/page.tsx`
  - `apps/network-web/src/app/settings/page.module.css`
  - `apps/network-web/src/lib/settings-security-capabilities.ts`
  - `apps/network-web/src/components/public-shell.tsx`
  - `apps/network-web/src/app/page.tsx`
  - `apps/network-web/src/app/agents/[agentId]/page.tsx`
  - `apps/network-web/src/app/approvals/page.tsx`
- Canonical docs/process:
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `docs/CONTEXT_PACK.md`
  - `spec.md`
  - `tasks.md`
  - `acceptance.md`

### API/data constraints
- Owner/session context:
  - `GET /api/v1/management/session/agents`
- Add access from key link:
  - `POST /api/v1/management/session/select`
- Clear local access:
  - `POST /api/v1/management/logout`
- Danger actions (active session agent):
  - `POST /api/v1/management/pause`
  - `POST /api/v1/management/resume`
  - `POST /api/v1/management/revoke-all`

### Placeholders required in Slice 75
- Verified multi-agent access inventory + per-agent remove access.
- Global panic actions across all owned agents in a single operation.
- On-chain allowance inventory/revoke sweep from settings.

### Verification plan
- Required gates:
  - `npm run db:parity`
  - `npm run seed:reset`
  - `npm run seed:load`
  - `npm run seed:verify`
  - `npm run build`
- Functional checks:
  - viewer/no-session empty-state behavior,
  - owner session controls + key-link add flow,
  - danger actions + panel-scoped errors,
  - placeholder disclosure + disabled CTAs,
  - desktop overflow + dark/light readability.

## Slice 74 Context: Approvals Center v1 (Frontend-Only, API-Preserving)

Issue mapping: `#74` (to be created / mapped)

### Objective + scope lock
- Objective: implement `/approvals` as a dashboard-aligned approvals inbox while preserving existing API contracts.
- Scope guard honored: no backend endpoints, schema, migrations, or OpenAPI changes.

### Expected touched files (Slice 74 allowlist)
- Web/UI:
  - `apps/network-web/src/app/approvals/page.tsx`
  - `apps/network-web/src/app/approvals/page.module.css`
  - `apps/network-web/src/lib/approvals-center-view-model.ts`
  - `apps/network-web/src/lib/approvals-center-capabilities.ts`
  - `apps/network-web/src/components/public-shell.tsx`
  - `apps/network-web/src/app/page.tsx`
  - `apps/network-web/src/app/agents/[agentId]/page.tsx`
- Canonical docs/process:
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `docs/CONTEXT_PACK.md`
  - `spec.md`
  - `tasks.md`
  - `acceptance.md`

### API/data constraints
- Owner context:
  - `GET /api/v1/management/session/agents`
- Queue/state data:
  - `GET /api/v1/management/agent-state`
- Decisions:
  - `POST /api/v1/management/approvals/decision`
  - `POST /api/v1/management/policy-approvals/decision`
  - `POST /api/v1/management/transfer-approvals/decision`

### Placeholders required in Slice 74
- Cross-agent aggregation (single-session agent state only in current API).
- Full allowances inventory table with revoke/cap actions.
- Risk enrichment chips + route/gas detail + bulk action workflows.

### Verification plan
- Required gates:
  - `npm run db:parity`
  - `npm run seed:reset`
  - `npm run seed:load`
  - `npm run seed:verify`
  - `npm run build`
- Functional checks:
  - viewer/no-session empty-state behavior,
  - owner queue loading and decision actions,
  - placeholder disclosure + disabled CTAs,
  - desktop overflow + dark/light readability.

## 1) Goal (Active: Slice 47)
- Primary objective: complete `Slice 47: Fix Telegram Queued Buttons Attach Point (Agent Reply Send Path)`.
- Success criteria:
  - For Telegram, OpenClaw auto-attaches Approve/Deny buttons to the queued `approval_pending` trade message in the agent reply pipeline (not just the CLI send path).
  - required gates pass: `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, runtime tests.

## 2) Constraints
- Canonical authority: `docs/XCLAW_SOURCE_OF_TRUTH.md`.
- Strict slice order: Slice 38 follows completed Slice 37.
- One-site model remains fixed (`/agents/:id` public + auth-gated management).
- No dependency additions.
- No new DB migration required for this slice (reuses Slice 34 tables; removes secret requirement and channel-auth path).

## 3) Contract Impact
- Management toggle:
  - `POST /api/v1/management/approval-channels/update` enables/disables Telegram approvals per chain (no secret issuance).
- Agent policy read change:
  - `GET /api/v1/agent/transfers/policy` includes `approvalChannels.telegram.enabled` (no secrets).
- Runtime prompt reporting:
  - `POST /api/v1/agent/approvals/prompt` records prompt metadata for cleanup/sync.
- Telegram approve path:
  - Telegram approve uses `POST /api/v1/trades/:tradeId/status` (agent-auth + `Idempotency-Key`) to transition `approval_pending -> approved`.
 - No API schema changes in this slice; web UI only.
 - OpenClaw gateway behavior change is delivered as a patch against OpenClaw dist bundle for the deployed version.

## 4) Files and Boundaries (Slice 47 allowlist)
- Web/API/UI:
  - none
- Canonical docs/process:
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `docs/CONTEXT_PACK.md`
  - `spec.md`
  - `tasks.md`
  - `acceptance.md`
- Runtime:
  - none
- OpenClaw patcher:
  - `skills/xclaw-agent/scripts/openclaw_gateway_patch.py`
- OpenClaw:
  - `skills/xclaw-agent/scripts/openclaw_gateway_patch.py`
  - `apps/agent-runtime/xclaw_agent/cli.py` (unchanged for this slice)
  - `skills/xclaw-agent/scripts/setup_agent_skill.py`
  - `skills/xclaw-agent/scripts/xclaw_agent_skill.py`
  - patch artifacts in `patches/openclaw/` (for reproducibility / inspection)

## 5) Invariants
- Status vocabulary remains exactly: `active`, `offline`, `degraded`, `paused`, `deactivated`.
- Authorized management controls remain owner/session-gated only.
- Dark/light themes remain supported with dark default.
- Existing management functionality remains available (pause/resume, policy, approvals, limit orders, withdraw, audit).

## 6) Verification Plan
- Required gates:
  - `npm run db:parity`
  - `npm run seed:reset`
  - `npm run seed:load`
  - `npm run seed:verify`
  - `npm run build`
  - `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`
- Feature checks:
  - running installer twice does not restart gateway again when already patched
  - after simulating an OpenClaw update (patch marker removed), next skill use re-applies patch and restarts once

## 7) Evidence + Rollback
- Capture command outputs and UX evidence in `acceptance.md`.
- Rollback plan:
  1. revert Slice 37 touched files only,
  2. rerun required gates,
  3. confirm approvals continue to function in web UI and Telegram prompts do not attempt secretless approvals.

---

## Slice 35 Context: Wallet-Embedded Approval Controls + Correct Token Decimals

Issue mapping: `#42` (umbrella)

### Objective + scope lock
- Objective: embed approval policy controls into the wallet card on `/agents/:id`, fix token decimals formatting (USDC), and expand default-collapsed management details.
- Scope guard honored: no DB migrations, no new auth model, no dependency additions.

### Expected touched files (Slice 35 allowlist)
- Web/UI:
  - `apps/network-web/src/app/agents/[agentId]/page.tsx`
  - `apps/network-web/src/app/globals.css`
- Server:
  - `apps/network-web/src/app/api/v1/management/agent-state/route.ts`
  - `apps/network-web/src/app/api/v1/trades/proposed/route.ts`
  - `apps/network-web/src/lib/copy-lifecycle.ts`
- Docs/process:
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/CONTEXT_PACK.md`
  - `spec.md`
  - `tasks.md`
  - `acceptance.md`

### Verification Plan
- Required gates:
  - `npm run db:parity`
  - `npm run seed:reset`
  - `npm run seed:load`
  - `npm run seed:verify`
  - `npm run build`
  - `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

## Slice 48 Context: Queued Approval Buttons v3 Upgrade + Logging (Debuggable)

Issue mapping: `#42` (umbrella)

### Objective + scope lock
- Objective: make Telegram queued approval buttons attach behavior diagnosable and resilient by upgrading the OpenClaw patch to v3 and emitting gateway logs on attach/skip.
- Scope guard honored: no DB changes, no dependency additions, no auth model changes.

### Expected touched files (Slice 48 allowlist)
- Skill tooling:
  - `skills/xclaw-agent/scripts/openclaw_gateway_patch.py`
- Docs/process:
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/CONTEXT_PACK.md`
  - `spec.md`
  - `tasks.md`
  - `acceptance.md`

### Verification Plan
- Required gates:
  - `npm run db:parity`
  - `npm run seed:reset`
  - `npm run seed:load`
  - `npm run seed:verify`
  - `npm run build`
  - `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

## Slice 49 Context: OpenClaw Patcher Safety (Syntax Check + Targeted Bundle)

Issue mapping: `#42` (umbrella)

### Objective + scope lock
- Objective: ensure the OpenClaw gateway patcher cannot break `openclaw` by validating patched output syntax and targeting only canonical gateway bundles.
- Scope guard honored: no DB changes, no dependency additions.

### Expected touched files (Slice 49 allowlist)
- Skill tooling:
  - `skills/xclaw-agent/scripts/openclaw_gateway_patch.py`
- Docs/process:
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/CONTEXT_PACK.md`
  - `spec.md`
  - `tasks.md`
  - `acceptance.md`

### Verification Plan
- Required gates:
  - `npm run db:parity`
  - `npm run seed:reset`
  - `npm run seed:load`
  - `npm run seed:verify`
  - `npm run build`
  - `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

## Slice 50 Context: Telegram Decision Feedback Routed Through Agent (No Direct Gateway Ack)

Issue mapping: `#42` (umbrella)

### Objective + scope lock
- Objective: after Telegram Approve/Deny, route the decision into the agent message pipeline (so the agent informs the user), rather than the gateway posting a raw ack message.
- Scope guard honored: no DB changes, no dependency additions, no server contract changes.

### Expected touched files (Slice 50 allowlist)
- Skill tooling:
  - `skills/xclaw-agent/scripts/openclaw_gateway_patch.py`
- Docs/process:
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/CONTEXT_PACK.md`
  - `spec.md`
  - `tasks.md`
  - `acceptance.md`

### Verification Plan
- Required gates:
  - `npm run db:parity`
  - `npm run seed:reset`
  - `npm run seed:load`
  - `npm run seed:verify`
  - `npm run build`
  - `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

## Slice 51 Context: Policy Approval Requests (Token Preapprove + Approve All) With Web + Telegram Buttons

Issue mapping: `#42` (umbrella)

### Objective + scope lock
- Objective: let the agent request owner approval for token preapproval and global approval, with convergent approvals in web UI and Telegram buttons.
- Scope guard honored: no new auth model; approvals are web (mgmt cookie) or Telegram buttons (gateway intercept) like trades.

### Expected touched files (Slice 51 allowlist)
- Data model:
  - `infrastructure/migrations/0012_slice51_policy_approval_requests.sql`
- Server/API/UI:
  - `apps/network-web/src/app/api/v1/agent/policy-approvals/proposed/route.ts`
  - `apps/network-web/src/app/api/v1/policy-approvals/[requestId]/decision/route.ts`
  - `apps/network-web/src/app/api/v1/management/policy-approvals/decision/route.ts`
  - `apps/network-web/src/app/api/v1/management/agent-state/route.ts`
  - `apps/network-web/src/app/agents/[agentId]/page.tsx`
  - `apps/network-web/src/lib/*` (helpers as needed)
- Runtime/skill:
  - `apps/agent-runtime/xclaw_agent/cli.py`
  - `skills/xclaw-agent/scripts/xclaw_agent_skill.py`
  - `skills/xclaw-agent/SKILL.md`
- OpenClaw patcher:
- `skills/xclaw-agent/scripts/openclaw_gateway_patch.py`

---

## Slice 52 Context: Policy Approval Prompts (Agent-Ready queuedMessage + Instructions)

### Objective
- Make policy approval request tool outputs “agent-ready” so the agent reliably tells the human what to do and Telegram button auto-attach works every time.

### Scope lock
- In scope: runtime output fields for policy approval request commands + unit tests + docs/process evidence.
- Out of scope: server endpoints, DB schema, web UI changes (already delivered in Slice 51).

### Expected touched files (Slice 52 allowlist)
- Runtime:
  - `apps/agent-runtime/xclaw_agent/cli.py`
  - `apps/agent-runtime/tests/test_trade_path.py`
- Docs/process:
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `docs/CONTEXT_PACK.md`
  - `spec.md`
  - `tasks.md`
- `acceptance.md`

---

## Slice 53 Context: Policy Approval Revokes (Token + Approve All OFF) With Web + Telegram Buttons

### Objective
- Extend policy approvals to support revoking permissions (token removal and global approve-all disable) with the same web + Telegram button surfaces.

### Scope lock
- In scope: server requestType handling + runtime/skill commands + UI label updates + docs/process + required gates.
- Out of scope: new DB tables (reuse existing `agent_policy_approval_requests`), new Telegram patch behavior (reuse existing ppr queued-message buttons).

### Expected touched files (Slice 53 allowlist)
- Server:
  - `apps/network-web/src/app/api/v1/agent/policy-approvals/proposed/route.ts`
  - `apps/network-web/src/app/api/v1/management/policy-approvals/decision/route.ts`
  - `apps/network-web/src/app/api/v1/policy-approvals/[requestId]/decision/route.ts`
- Schemas/contracts:
  - `packages/shared-schemas/json/agent-policy-approval-proposed-request.schema.json`
  - `docs/api/openapi.v1.yaml`
- Web UI:
  - `apps/network-web/src/app/agents/[agentId]/page.tsx`
- Runtime/skill:
  - `apps/agent-runtime/xclaw_agent/cli.py`
  - `apps/agent-runtime/tests/test_trade_path.py`
  - `skills/xclaw-agent/scripts/xclaw_agent_skill.py`
  - `skills/xclaw-agent/SKILL.md`
- Docs/process:
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `docs/CONTEXT_PACK.md`
  - `spec.md`
  - `tasks.md`
- `acceptance.md`

---

## Slice 55 Context: Policy Approval De-Dupe (Reuse Pending Request)

### Objective
- Prevent policy approval spam by reusing an existing pending request when the same policy change is requested repeatedly.

### Scope lock
- In scope: server propose endpoint behavior + DB index + docs/process evidence.
- Out of scope: Telegram/web decision handling (unchanged).

### Expected touched files (Slice 55 allowlist)
- Server:
  - `apps/network-web/src/app/api/v1/agent/policy-approvals/proposed/route.ts`
- Data model:
  - `infrastructure/migrations/*.sql`
- Docs/process:
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `docs/CONTEXT_PACK.md`
  - `spec.md`
  - `tasks.md`
  - `acceptance.md`
- Contracts/docs:
  - `docs/api/openapi.v1.yaml`
  - `packages/shared-schemas/json/*`
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `spec.md`
  - `tasks.md`
  - `acceptance.md`

### Verification Plan
- Required gates:
  - `npm run db:parity`
  - `npm run seed:reset`
  - `npm run seed:load`
  - `npm run seed:verify`
  - `npm run build`
  - `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

## Slice 36 Context: Remove Step-Up Authentication (Management Cookie Only)

Issue mapping: `#42` (umbrella)

### Objective + scope lock
- Objective: remove step-up entirely (cookies, endpoints, UI prompts, runtime command, DB objects) so management session cookie + CSRF is sufficient for all management actions.
- Scope guard honored: no replacement 2FA system, no dependency additions.

### Expected touched files (Slice 36 allowlist)
- Data model:
  - `infrastructure/migrations/0011_slice36_remove_stepup.sql`
  - `infrastructure/scripts/check-migration-parity.mjs`
- Server/API/UI:
  - `apps/network-web/src/lib/management-auth.ts`
  - `apps/network-web/src/lib/management-cookies.ts`
  - `apps/network-web/src/lib/management-service.ts`
  - `apps/network-web/src/lib/errors.ts`
  - `apps/network-web/src/app/api/v1/management/*` (remove stepup gates)
  - `apps/network-web/src/app/api/v1/management/stepup/*` (delete)
  - `apps/network-web/src/app/api/v1/agent/stepup/*` (delete)
  - `apps/network-web/src/app/agents/[agentId]/page.tsx`
- Runtime/skill:
  - `apps/agent-runtime/xclaw_agent/cli.py`
  - `skills/xclaw-agent/scripts/xclaw_agent_skill.py`
  - `skills/xclaw-agent/references/commands.md`
  - `skills/xclaw-agent/SKILL.md`
- Docs/contracts:
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `docs/api/openapi.v1.yaml`
  - `docs/api/AUTH_WIRE_EXAMPLES.md`
  - `packages/shared-schemas/json/*` (remove stepup schemas, update approval schema)
  - `spec.md`
  - `tasks.md`
  - `acceptance.md`

### Verification Plan
- Required gates:
  - `npm run db:parity`
  - `npm run seed:reset`
  - `npm run seed:load`
  - `npm run seed:verify`
  - `npm run build`
  - `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

## Slice 69 Context: Dashboard Full Rebuild (Global Landing Analytics + Discovery)

Issue mapping: `#69` (to be created/mapped)

### Objective + scope lock
- Objective: rebuild `/` dashboard from scratch to match Page #1 spec with desktop/mobile/dark-mode behavior, add `/dashboard` alias, and keep implementation dashboard-scoped.
- Scope guard honored: no backend schema/API contract change; unsupported metrics are derived with explicit estimated labeling.

### Expected touched files (Slice 69 allowlist)
- Dashboard UI/shell:
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
- Docs/process:
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `docs/CONTEXT_PACK.md`
  - `spec.md`
  - `tasks.md`
  - `acceptance.md`

### Verification Plan
- Required gates:
  - `npm run db:parity`
  - `npm run seed:reset`
  - `npm run seed:load`
  - `npm run seed:verify`
  - `npm run build`
- Functional checks:
  - `/` and `/dashboard` parity
  - owner-only scope selector visibility
  - chain filtering (`all/base_sepolia/hardhat_local`)
  - dark/light persistence
  - mobile ordering + desktop layout

---

## Slice 69A Context: Dashboard Agent Trade Room Reintegration

Issue mapping: `#69A` (to be created/mapped)

### Objective + scope lock
- Objective: add back Agent Trade Room in dashboard right rail with compact read-only preview and full `/room` view while preserving analytics-first hierarchy.
- Scope guard honored: no backend schema/API changes; existing chat API contract reused.

### Expected touched files (Slice 69A allowlist)
- UI:
  - `apps/network-web/src/app/page.tsx`
  - `apps/network-web/src/app/page.module.css`
  - `apps/network-web/src/app/room/page.tsx`
- Docs/process:
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `docs/CONTEXT_PACK.md`
  - `spec.md`
  - `tasks.md`
  - `acceptance.md`

### Verification Plan
- Required gates:
  - `npm run db:parity`
  - `npm run seed:reset`
  - `npm run seed:load`
  - `npm run seed:verify`
  - `npm run build`
- Functional checks:
  - dashboard room card placement below live feed
  - room chain and owner-scope filtering
  - room loading/empty/error states
  - `/room` read-only view behavior.

---

## Slice 70 Context: Single-Trigger Spot Flow + Guaranteed Final Result Reporting

Issue mapping: `#70` (to be created/mapped)

### Objective + scope lock
- Objective: for Telegram-focused `trade spot`, make approval->execution->result a one-trigger flow with deterministic human-visible final outcome reporting.
- Scope guard honored: limit-order behavior remains unchanged; policy callback contract (`xpol`) remains unchanged.

### Expected touched files (Slice 70 allowlist)
- Runtime:
  - `apps/agent-runtime/xclaw_agent/cli.py`
  - `apps/agent-runtime/tests/test_trade_path.py`
- Skill/gateway:
  - `skills/xclaw-agent/scripts/xclaw_agent_skill.py`
  - `skills/xclaw-agent/scripts/openclaw_gateway_patch.py`
  - `skills/xclaw-agent/SKILL.md`
  - `skills/xclaw-agent/references/commands.md`
- Docs/process:
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `docs/CONTEXT_PACK.md`
  - `spec.md`
  - `tasks.md`
  - `acceptance.md`

### Verification Plan
- Required gates:
  - `npm run db:parity`
  - `npm run seed:reset`
  - `npm run seed:load`
  - `npm run seed:verify`
  - `npm run build`
  - `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`
- Functional checks:
  - one-trigger Telegram `trade spot` approval-required path auto-resumes execution after Approve callback.
  - Deny callback produces refusal feedback with reason.
  - final deterministic result message includes status/tradeId/chain/txHash (when available).
  - synthetic final-result message is routed to agent pipeline.

---

## Slice 71 Context: Single-Trigger Outbound Transfers + Runtime-Canonical Transfer Approvals

Issue mapping: `#71` (to be created/mapped)

### Objective + scope lock
- Objective: implement one-trigger transfer approvals for `wallet-send` and `wallet-send-token` with runtime-canonical state and deterministic Telegram/web decision behavior.
- Scope guard honored: no limit-order behavior changes; existing spot-trade and policy approval semantics remain intact outside transfer-specific additions.

### Expected touched files (Slice 71 allowlist)
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
  - `packages/shared-schemas/json/*transfer*`
  - `docs/api/openapi.v1.yaml`
  - `docs/api/WALLET_COMMAND_CONTRACT.md`
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `spec.md`
  - `tasks.md`
  - `acceptance.md`

### Verification Plan
- Required gates:
  - `npm run db:parity`
  - `npm run seed:reset`
  - `npm run seed:load`
  - `npm run seed:verify`
  - `npm run build`
  - `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`
- Functional checks:
  - Telegram `xfer` approve executes once and reports terminal result.
  - Telegram `xfer` deny rejects without execution.
  - web management transfer approve/deny converges with runtime state.
  - transfer policy updates reflect in runtime-driven decisions.

---

## Slice 72 Context: Transfer Policy-Override Approvals (Keep Gate/Whitelist)

### Objective + scope lock
- Objective: keep outbound gate/whitelist intact, but route policy-blocked transfer intents into transfer approval workflow with one-off override execution on approve.
- Scope guard honored: trade approvals and limit-order behavior remain unchanged.

### Expected touched files (Slice 72 allowlist)
- `apps/agent-runtime/xclaw_agent/cli.py`
- `apps/agent-runtime/tests/test_trade_path.py`
- `skills/xclaw-agent/scripts/openclaw_gateway_patch.py`
- `apps/network-web/src/app/api/v1/agent/transfer-approvals/mirror/route.ts`
- `apps/network-web/src/app/api/v1/management/transfer-approvals/route.ts`
- `apps/network-web/src/app/api/v1/management/agent-state/route.ts`
- `apps/network-web/src/app/agents/[agentId]/page.tsx`
- `packages/shared-schemas/json/agent-transfer-approvals-mirror-request.schema.json`
- `packages/shared-schemas/json/transfer-approval.schema.json`
- `infrastructure/migrations/0016_slice72_transfer_policy_override_fields.sql`
- `docs/api/openapi.v1.yaml`
- `docs/XCLAW_SOURCE_OF_TRUTH.md`
- `docs/XCLAW_SLICE_TRACKER.md`
- `docs/XCLAW_BUILD_ROADMAP.md`
- `docs/api/WALLET_COMMAND_CONTRACT.md`
- `spec.md`
- `tasks.md`
- `acceptance.md`

---

## Slice 73 Context: Agent Page Full Frontend Refresh (Dashboard-Aligned, API-Preserving)

Issue mapping: `#26`

### Objective + scope lock
- Objective: direct-replace `/agents/:id` with a new dashboard-aligned wallet console UI while preserving all existing API behavior and owner/viewer security boundaries.
- Scope guard honored: frontend-only; no backend route/schema/migration changes.

### Expected touched files (Slice 73 allowlist)
- Docs/process:
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `docs/CONTEXT_PACK.md`
  - `spec.md`
  - `tasks.md`
  - `acceptance.md`
- Web/UI:
  - `apps/network-web/src/app/agents/[agentId]/page.tsx`
  - `apps/network-web/src/app/agents/[agentId]/page.module.css`
  - `apps/network-web/src/lib/agent-page-view-model.ts`
  - `apps/network-web/src/lib/agent-page-capabilities.ts`

### Verification Plan
- Required gates:
  - `npm run db:parity`
  - `npm run seed:reset`
  - `npm run seed:load`
  - `npm run seed:verify`
  - `npm run build`
- Functional checks:
  - viewer mode hides owner controls,
  - owner mode operations still hit existing management endpoints,
  - approvals queue decisions reflect in refreshed UI state,
  - placeholder modules are clearly labeled where APIs do not yet exist.
## Slice 77 Context: Agent Wallet Page MetaMask-Style Full-Screen Refactor

Issue mapping: `#29` (to be created / mapped)

### Objective + scope lock
- Objective: refactor `/agents/:id` into MetaMask-style full-screen wallet framing while preserving existing owner/viewer contracts and management endpoint semantics.
- Scope guard honored: frontend-first page/copy/layout changes; no speculative backend contract additions.

### Expected touched files (Slice 77 allowlist)
- Docs/process:
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `docs/CONTEXT_PACK.md`
  - `spec.md`
  - `tasks.md`
  - `acceptance.md`
- Web/UI:
  - `apps/network-web/src/app/agents/[agentId]/page.tsx`
  - `apps/network-web/src/app/agents/[agentId]/page.module.css`

### Verification Plan
- Required gates:
  - `npm run db:parity`
  - `npm run seed:reset`
  - `npm run seed:load`
  - `npm run seed:verify`
  - `npm run build`
- Functional checks:
  - no dashboard sidebar shell on `/agents/:id`,
  - wallet-first module order preserved,
  - transfer/outbound policy editor controls removed,
  - approval decisions + withdraw + copy delete + limit-order cancel + audit remain functional.

---

---

## Slice 82 Context: Track-Not-Copy Pivot (Saved Agents -> OpenClaw Watchlist)

Issue mapping: `#32`

### Objective + scope lock
- Objective: pivot product surfaces from copy trading to tracked-agent monitoring with server-backed tracked relations per managed agent.
- Scope guard honored: no removal of legacy copy backend paths in this slice; routes stay operational but are UI-hidden/deprecated.

### Expected touched files (Slice 82 allowlist)
- Docs/process:
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `docs/api/WALLET_COMMAND_CONTRACT.md`
  - `docs/api/openapi.v1.yaml`
  - `docs/CONTEXT_PACK.md`
  - `spec.md`
  - `tasks.md`
  - `acceptance.md`
- DB/schema:
  - `infrastructure/migrations/0020_slice82_agent_tracking.sql`
  - `packages/shared-schemas/json/management-tracked-agents-upsert-request.schema.json`
  - `packages/shared-schemas/json/management-tracked-agents-delete-request.schema.json`
  - `packages/shared-schemas/json/management-tracked-agents-response.schema.json`
  - `packages/shared-schemas/json/management-tracked-trades-response.schema.json`
  - `packages/shared-schemas/json/agent-tracked-agents-response.schema.json`
  - `packages/shared-schemas/json/agent-tracked-trades-response.schema.json`
- API/UI/runtime:
  - `apps/network-web/src/app/api/v1/management/tracked-agents/route.ts`
  - `apps/network-web/src/app/api/v1/management/tracked-trades/route.ts`
  - `apps/network-web/src/app/api/v1/agent/tracked-agents/route.ts`
  - `apps/network-web/src/app/api/v1/agent/tracked-trades/route.ts`
  - `apps/network-web/src/app/api/v1/management/agent-state/route.ts`
  - `apps/network-web/src/app/explore/page.tsx`
  - `apps/network-web/src/app/agents/[agentId]/page.tsx`
  - `apps/network-web/src/components/primary-nav.tsx`
  - `apps/network-web/src/lib/agent-page-view-model.ts`
  - `apps/agent-runtime/xclaw_agent/cli.py`
  - `apps/agent-runtime/tests/test_tracked_runtime.py`
  - `apps/agent-runtime/tests/test_x402_skill_wrapper.py`
  - `skills/xclaw-agent/scripts/xclaw_agent_skill.py`
  - `skills/xclaw-agent/SKILL.md`
  - `skills/xclaw-agent/references/commands.md`

### Verification Plan
- Required gates:
  - `npm run db:parity`
  - `npm run seed:reset`
  - `npm run seed:load`
  - `npm run seed:verify`
  - `npm run build`
  - `pm2 restart all`
- Runtime tests:
  - `python3 -m unittest apps/agent-runtime/tests/test_tracked_runtime.py -v`
  - `python3 -m unittest apps/agent-runtime/tests/test_x402_skill_wrapper.py -v`
- Functional checks:
  - Explore shows `Track Agent` CTA and no copy-trade modal.
  - owner tracked agents persist server-side and reflect in left rail.
  - `/agents/[agentId]` tracked panel lists/removes tracked agents and shows recent tracked filled trades.
  - runtime `dashboard` includes tracked summaries.

## Context Pack Addendum: Slice 86-88 Approvals Center Full Flush

### Objective
- Deliver permission-native approvals center with multi-agent management-session authorization, chain-scoped policy snapshots, approve+allowlist action, unified inbox, permission inventory, and batch decisions.

### Constraints
- Preserve existing approval decision routes for backward compatibility.
- Keep status vocabulary invariant (`active`, `offline`, `degraded`, `paused`, `deactivated`).
- Keep agent runtime trust boundaries unchanged.

### Canonical artifacts touched
- `docs/XCLAW_SOURCE_OF_TRUTH.md`
- `docs/XCLAW_SLICE_TRACKER.md`
- `docs/XCLAW_BUILD_ROADMAP.md`
- `docs/api/openapi.v1.yaml`
- `packages/shared-schemas/json/*.schema.json`

## Context Pack Addendum: Non-Telegram Web Agent Prod Bridge (Trade/Transfer)

### Objective + scope lock
- Objective: keep autonomous agent state synchronized for web-driven decisions and terminal outcomes when active channel is non-Telegram.
- Scope lock:
  - trade decision (`/management/approvals/decision`),
  - approve+allowlist decision (`/management/approvals/approve-allowlist-token`),
  - transfer decision (`/management/transfer-approvals/decision`),
  - trade terminal status (`/trades/:tradeId/status`),
  - transfer mirror terminal transition (`/agent/transfer-approvals/mirror`).

### Safety constraints
- Do not modify Telegram callback/gateway behavior.
- Skip synthetic dispatch when OpenClaw last channel is Telegram.
- Never use `openclaw message send` from this bridge.
- Dispatch failures are best-effort and cannot fail business endpoints.

### Expected touched files
- `apps/network-web/src/lib/non-telegram-agent-prod.ts`
- `apps/network-web/src/app/api/v1/management/approvals/decision/route.ts`
- `apps/network-web/src/app/api/v1/management/approvals/approve-allowlist-token/route.ts`
- `apps/network-web/src/app/api/v1/management/transfer-approvals/decision/route.ts`
- `apps/network-web/src/app/api/v1/trades/[tradeId]/status/route.ts`
- `apps/network-web/src/app/api/v1/agent/transfer-approvals/mirror/route.ts`

## Context Pack Addendum: Slice 89 MetaMask-Style Gas Estimation

### Objective
- Replace fixed runtime gas-price strategy with RPC-native EIP-1559-first fee planning for signed wallet/trade sends.

### Scope lock
- In scope: `wallet-send`, `wallet-send-token`, and `trade-spot` execution sender path.
- Out of scope: server/web faucet sender strategy and non-EVM runtime surfaces.

### Canonical artifacts touched
- `docs/XCLAW_SOURCE_OF_TRUTH.md`
- `docs/XCLAW_SLICE_TRACKER.md`
- `docs/XCLAW_BUILD_ROADMAP.md`
- `docs/api/WALLET_COMMAND_CONTRACT.md`

### Expected implementation files
- `apps/agent-runtime/xclaw_agent/cli.py`
- `apps/agent-runtime/tests/test_trade_path.py`

### Verification plan
- `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`
- `python3 -m unittest apps/agent-runtime/tests/test_wallet_core.py -v`
- required gates sequence:
  - `npm run db:parity`
  - `npm run seed:reset`
  - `npm run seed:load`
  - `npm run seed:verify`
  - `npm run build`
  - `pm2 restart all`

## Context Pack Addendum: Slice 90 Liquidity + Multi-DEX Foundation

### Objective
- Introduce canonical liquidity intent/position model and bridge it into runtime + skill + management wallet visibility.

### Scope lock
- In scope:
  - liquidity intents (`add`/`remove`) with trade-aligned approval semantics,
  - chain capability extension (`capabilities.liquidity`),
  - chain-scoped liquidity positions read model in management agent-state,
  - wallet UI liquidity section.
- Out of scope:
  - IL decomposition and strategy automation,
  - mandatory enablement for all sponsor chains in this slice.

### Canonical artifacts touched
- `docs/XCLAW_SOURCE_OF_TRUTH.md`
- `docs/XCLAW_SLICE_TRACKER.md`
- `docs/XCLAW_BUILD_ROADMAP.md`
- `docs/api/openapi.v1.yaml`
- `docs/api/WALLET_COMMAND_CONTRACT.md`
- `skills/xclaw-agent/references/commands.md`

### Expected implementation files
- `infrastructure/migrations/0023_slice90_liquidity_foundation.sql`
- `packages/shared-schemas/json/liquidity-*.schema.json`
- `apps/agent-runtime/xclaw_agent/cli.py`
- `skills/xclaw-agent/scripts/xclaw_agent_skill.py`
- `apps/network-web/src/app/api/v1/liquidity/**/route.ts`
- `apps/network-web/src/app/api/v1/management/agent-state/route.ts`
- `apps/network-web/src/app/agents/[agentId]/page.tsx`

# Slice 96 Context Addendum: Base Sepolia Wallet/Approval E2E Harness (UTC 2026-02-20)

## Objective
- Implement a deterministic Python-first end-to-end harness for wallet/approval behavior across trade, transfer, liquidity, x402, and pause/resume on Base Sepolia.
- Add runtime Telegram suppression for harness runs.

## Constraints
- Canonical authority: `docs/XCLAW_SOURCE_OF_TRUTH.md`.
- Approval driver for this harness slice is management API only.
- No Node/npm requirement for invoking runtime harness command flow.
- Hardhat-local evidence precedes external testnet evidence.
- Base Sepolia execution is hard-blocked until a green Hardhat smoke report is present.

## Expected touched artifacts
- `apps/agent-runtime/xclaw_agent/cli.py`
- `apps/agent-runtime/scripts/wallet_approval_harness.py`
- `apps/agent-runtime/tests/test_trade_path.py`
- `apps/agent-runtime/tests/test_wallet_approval_harness.py`
- canonical docs/handoff files for Slice 96 sync.

## Verification targets
- runtime Telegram suppression guard behavior covered in unit tests.
- harness unit tests for scenario parsing/tolerance/report flow.
- harness preflight/report behavior validated:
  - hardhat RPC probe,
  - wallet decrypt/sign fail-fast,
  - management write retry diagnostics.
- required repo gates executed sequentially.

## Context Pack Addendum: Slice 101 Dashboard Dexscreener Top Tokens (UTC 2026-02-20)

### Objective
- Add a dashboard `Top Trending Tokens` module sourced from Dexscreener, chain-aware via existing dashboard chain dropdown, with top-10 ranking by 24h volume.

### Scope lock
- In scope:
  - public route `GET /api/v1/public/dashboard/trending-tokens`,
  - chain config mapping `marketData.dexscreenerChainId`,
  - dashboard UI module (desktop table + mobile cards),
  - 60-second refresh loop and soft-failure handling.
- Out of scope:
  - skill/runtime Dexscreener command changes,
  - additional chain mapping beyond validated Base/Ethereum mappings,
  - replacing dashboard summary endpoint.

### Constraints
- Canonical authority: `docs/XCLAW_SOURCE_OF_TRUTH.md`.
- Dashboard chain selector remains single source of truth (no secondary selector).
- If selected chain has no mapped Dexscreener data, section is hidden.
- Render only columns with available data (no placeholder columns).

### Expected touched artifacts
- `apps/network-web/src/app/api/v1/public/dashboard/trending-tokens/route.ts`
- `apps/network-web/src/app/dashboard/page.tsx`
- `apps/network-web/src/app/dashboard/page.module.css`
- `apps/network-web/src/lib/chains.ts`
- `config/chains/base_mainnet.json`
- `config/chains/base_sepolia.json`
- `config/chains/ethereum.json`
- `config/chains/ethereum_sepolia.json`
- `packages/shared-schemas/json/public-dashboard-trending-tokens-response.schema.json`
- `docs/api/openapi.v1.yaml`
- `docs/XCLAW_SOURCE_OF_TRUTH.md`
- `docs/XCLAW_SLICE_TRACKER.md`
- `docs/XCLAW_BUILD_ROADMAP.md`
- `spec.md`
- `tasks.md`
- `acceptance.md`

### Verification targets
- Route returns max 10 items sorted by 24h volume descending.
- Chain switch updates token rows (`all` aggregation + specific chain mapping).
- Invalid `chainKey` returns deterministic `payload_invalid` error.
- Dexscreener failures are soft and do not break dashboard shell rendering.

## Slice 100 Context Pack (2026-02-20): Uniswap Proxy-First Execution (Superseded by Slice 119)

### Objective
Implement Uniswap API integration as server-side proxy execution for runtime trade commands with deterministic fallback to legacy router path.

### Constraints
- Historical note only. Active execution is EVM-only and router-adapter-driven.
- Runtime/skill wallet remains source-of-truth execution authority.

### Decision locks
- Provider precedence: `uniswap_api` -> `legacy_router`.
- Fallback trigger: any Uniswap proxy error class.
- Provenance fields are mandatory in runtime outputs and trade status payloads.

### Primary touchpoints
- Runtime: `apps/agent-runtime/xclaw_agent/cli.py`
- Server proxy: `apps/network-web/src/lib/uniswap-proxy.ts`
- API routes: `/api/v1/agent/trade/uniswap/quote`, `/api/v1/agent/trade/uniswap/build`
- Chain config rollout: requested Uniswap-supported chain set in `config/chains/`
- Contracts/docs: `openapi.v1.yaml`, shared schemas, source-of-truth, tracker, roadmap, handoff artifacts.

## Slice 102 Context Pack (2026-02-20): Uniswap LP Core (Proxy-First + Fallback, Superseded by Slice 119)

### Objective
Extend Uniswap proxy-first execution to LP core operations (`approve/create/increase/decrease/claim-fees`) on repo-supported Uniswap chains while retaining legacy liquidity fallback when available.

### Constraints
- Historical note only. Active liquidity execution is EVM-only and router-adapter-driven.
- Runtime/skill wallet remains execution/signing source of truth.

### Decision locks
- LP provider precedence: `uniswap_api` -> `legacy_router`.
- LP provenance metadata must be present in runtime outputs and liquidity status details.
- Chain rollout limited to repo-supported Uniswap LP chain set.

### Primary touchpoints
- Runtime orchestration + new commands: `apps/agent-runtime/xclaw_agent/cli.py`
- Server LP proxy client: `apps/network-web/src/lib/uniswap-lp-proxy.ts`
- Agent-auth LP routes: `apps/network-web/src/app/api/v1/agent/liquidity/uniswap/*/route.ts`
- Contracts: `docs/api/openapi.v1.yaml`, `packages/shared-schemas/json/liquidity-status.schema.json`, `packages/shared-schemas/json/uniswap-lp-*.schema.json`
- Chain config rollout: `config/chains/{ethereum,ethereum_sepolia,unichain_mainnet,bnb_mainnet,polygon_mainnet,base_mainnet,avalanche_mainnet,op_mainnet,arbitrum_mainnet,zksync_mainnet,monad_mainnet}.json`

## Slice 103 Context Pack (2026-02-20): Uniswap LP Completion (Migrate + Claim Rewards)

### Objective
Complete Uniswap LP integration by adding `migrate` and `claim_rewards` with the same proxy-first/runtime-wallet execution model.

### Constraints
- Server-only Uniswap key custody.
- Runtime wallet signs and broadcasts all transactions.
- Stage-gated rollout: operation-level enablement starts at `ethereum_sepolia` only.
- Fallback is allowed only when operation-specific legacy support exists.

### Primary touchpoints
- LP proxy client + new routes:
  - `apps/network-web/src/lib/uniswap-lp-proxy.ts`
  - `apps/network-web/src/app/api/v1/agent/liquidity/uniswap/{migrate,claim-rewards}/route.ts`
- Runtime CLI:
  - `apps/agent-runtime/xclaw_agent/cli.py` (`liquidity migrate`, `liquidity claim-rewards`)
- Contracts:
  - `docs/api/openapi.v1.yaml`
  - `packages/shared-schemas/json/uniswap-lp-migrate-request.schema.json`
  - `packages/shared-schemas/json/uniswap-lp-claim-rewards-request.schema.json`
  - `packages/shared-schemas/json/liquidity-status.schema.json`
- Stage flags:
  - `config/chains/*.json` `uniswapApi.{migrateEnabled,claimRewardsEnabled}`

## Slice 104 Context Pack (2026-02-20): LP Migrate/Claim-Rewards Promotion

### Objective
Promote already-implemented Uniswap LP `migrate` and `claim_rewards` operations from Sepolia-only staging to all repo target chains without changing runtime architecture.

### Constraints
- Agent runtime wallet remains execution/signing source of truth.
- Uniswap API key remains server-only.
- No synthetic fallback for unsupported operations; fail closed deterministically.

### Primary touchpoints
- Chain promotion configs:
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
- Canonical sync:
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `spec.md`
  - `tasks.md`
  - `acceptance.md`

## Slice 105 Context Pack (2026-02-20): Cross-Chain Liquidity Claims

### Objective
Implement deterministic cross-chain `liquidity claim-fees` and `liquidity claim-rewards` behavior with Uniswap-first execution and legacy fallback only when explicitly configured and implemented.

### Constraints
- Agent runtime wallet remains signing/execution source of truth.
- Uniswap key remains server-only.
- No synthetic success paths for unsupported claims.
- Disabled/no-liquidity chains remain fail-closed.

### Primary touchpoints
- Runtime orchestration:
  - `apps/agent-runtime/xclaw_agent/cli.py`
- Adapter capability layer:
  - `apps/agent-runtime/xclaw_agent/liquidity_adapter.py`
- Hedera bridge/plugin guarded claim dispatch:
  - `apps/agent-runtime/xclaw_agent/hedera_hts_plugin.py`
  - `apps/agent-runtime/xclaw_agent/bridges/hedera_hts_bridge.py`
- Chain config gates:
  - `config/chains/*.json`
- Regression coverage:
  - `apps/agent-runtime/tests/test_liquidity_cli.py`

## Slice 106 Context Pack (2026-02-20): Full Cross-Chain Functional Parity + Adapter Fallbacks

### Objective
Unify cross-chain execution/fallback contracts so active chains expose deterministic behavior for send/trade/liquidity/claims, with Uniswap-primary chains falling back to adapter paths only when configured and supported.

### Constraints
- No synthetic success paths.
- Uniswap remains primary on configured chains.
- Claim-rewards fallback requires configured reward contracts when adapter requires them.
- Wallet-only/disabled chains remain fail-closed this slice.

### Primary touchpoints
- Runtime orchestration:
  - `apps/agent-runtime/xclaw_agent/cli.py`
- Adapter capability metadata:
  - `apps/agent-runtime/xclaw_agent/liquidity_adapter.py`
- Chain config model:
  - `config/chains/*.json`

## Slice 107 Context Pack (2026-02-20): Executable Cross-Chain Parity Completion

### Objective
Promote executable claim fallback behavior where adapter paths are real (Hedera first), and tighten claim failure payload provenance.

### Constraints
- Uniswap remains primary for configured Uniswap chains.
- No synthetic success on unsupported claim operations.
- Disabled/wallet-only chains remain unchanged in this slice.

### Primary touchpoints
- Runtime claim failure payloads:
  - `apps/agent-runtime/xclaw_agent/cli.py`
- Hedera claim bridge execution:
  - `apps/agent-runtime/xclaw_agent/bridges/hedera_hts_bridge.py`
- Hedera claim rollout config:
  - `config/chains/hedera_mainnet.json`
  - `config/chains/hedera_testnet.json`
- Regression coverage:
  - `apps/agent-runtime/tests/test_liquidity_cli.py`

## Slice 108-111 Context Pack (2026-02-20): Active-Chain Parity Completion

### Objective
Close active-chain parity gaps with deterministic operation contracts and evidence-first rollout under concurrent multi-agent development.

### Constraints
- Uniswap remains primary on configured Uniswap chains.
- Fallback execution requires explicit config gate + real capability support.
- Unsupported paths remain deterministic fail-closed.
- Wallet-only/disabled chains are out-of-scope for this stream.

### Primary touchpoints
- Runtime contract/gating validation:
  - `apps/agent-runtime/xclaw_agent/cli.py`
- Active-chain config truth:
  - `config/chains/*.json` (active-chain subset)
- Canonical/handoff artifacts:
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `spec.md`
  - `tasks.md`
  - `acceptance.md`

## Slice 112-116 Context Pack (2026-02-20): Chain-Verified v2 Fallback Completion

### Objective
Promote legacy trade fallback only where the current v2-router runtime is technically valid and chain-verified, while preserving deterministic fail-closed behavior elsewhere.

### Constraints
- v2-only fallback stream (no v3/universal adapter work).
- Active chains only in this stream.
- Official-source evidence required for fallback promotion:
  - Uniswap deployment docs,
  - Uniswap official contract repos,
  - chain explorer contract verification links.

### Promotion outcome target
- Promote fallback for verified v2-compatible Uniswap-primary chains.
- Keep non-verified chains fallback-disabled with deterministic `no_execution_provider_available` behavior.
- Keep non-Uniswap claim truth unchanged: Hedera executable, others deterministic where not integrated.

### Primary touchpoints
- `config/chains/{arbitrum_mainnet,base_mainnet,op_mainnet,polygon_mainnet,avalanche_mainnet,bnb_mainnet,unichain_mainnet,monad_mainnet,zksync_mainnet}.json`
- `apps/agent-runtime/tests/test_trade_path.py`
- canonical/handoff docs:
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `spec.md`
  - `tasks.md`
  - `acceptance.md`

## Slice 117 Context Pack (2026-02-20): Ethereum Sepolia Harness Matrix Expansion

### Objective
Run deterministic wallet-approval harness evidence in strict sequence (`hardhat_local`, `base_sepolia`, `ethereum_sepolia`) and prove Ethereum Sepolia capability-valid flow success with deterministic unsupported x402 behavior.

### Constraints
- Keep Python-first runtime execution.
- Keep `ethereum_sepolia` capability truth (`x402=false`, `faucet=false`).
- No new API contracts and no dependency additions.
- Hardhat evidence is a strict gate for non-hardhat runs.

### Primary touchpoints
- Harness runtime script:
  - `apps/agent-runtime/scripts/wallet_approval_harness.py`
- New matrix runner:
  - `apps/agent-runtime/scripts/wallet_approval_chain_matrix.py`
- Unit tests:
  - `apps/agent-runtime/tests/test_wallet_approval_harness.py`
  - `apps/agent-runtime/tests/test_wallet_approval_chain_matrix.py`
- Canonical/handoff docs:
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `spec.md`
  - `tasks.md`
  - `acceptance.md`

## Slice 117 Hotfix C Context Pack (2026-02-20): Cross-Chain `wallet wrap-native` Parity

### Objective
Promote `wallet wrap-native` to config-driven cross-chain behavior for wallet-capable chains without changing CLI surface, while preserving deterministic error contracts and operational fallback guidance.

### Constraints
- No dependency additions.
- No server/web API contract changes.
- Resolution must be config-driven:
  - helper `deposit()` when `coreContracts.wrappedNativeHelper` exists and is valid,
  - otherwise canonical wrapped token `deposit()` from `canonicalTokens` (`W<NativeSymbol>` + strict alias fallback).
- Deterministic failures must include `wrapped_native_token_missing` for unresolved wrapped-native token mapping.

### Primary touchpoints
- Runtime command path:
  - `apps/agent-runtime/xclaw_agent/cli.py`
- Runtime regression tests:
  - `apps/agent-runtime/tests/test_wallet_core.py`
- Canonical/handoff docs:
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/api/WALLET_COMMAND_CONTRACT.md`
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `skills/xclaw-agent/SKILL.md`
  - `skills/xclaw-agent/references/commands.md`
  - `spec.md`
  - `tasks.md`
  - `acceptance.md`

---

## Hotfix Context: Slice 117 Hotfix D Trade-Cap Deprecation + Chain Context Parity

Issue mapping: `#60`

### Objective + scope lock
- Objective: remove deprecated trade-cap gating and make omitted-chain trade/dashboard/wallet context follow runtime/web-synced default chain.
- Scope guard: no schema deletions; no chain capability promotion beyond config.

### Expected touched files
- `apps/agent-runtime/xclaw_agent/cli.py`
- `apps/agent-runtime/tests/test_wallet_core.py`
- `skills/xclaw-agent/scripts/xclaw_agent_skill.py`
- `apps/agent-runtime/tests/test_x402_skill_wrapper.py`
- `apps/network-web/src/lib/trade-caps.ts`
- `apps/network-web/src/app/api/v1/agent/transfers/policy/route.ts`
- `docs/XCLAW_SOURCE_OF_TRUTH.md`
- `docs/api/WALLET_COMMAND_CONTRACT.md`
- `docs/XCLAW_SLICE_TRACKER.md`
- `docs/XCLAW_BUILD_ROADMAP.md`
- `skills/xclaw-agent/SKILL.md`
- `skills/xclaw-agent/references/commands.md`
- `spec.md`
- `tasks.md`
- `acceptance.md`
- `docs/CONTEXT_PACK.md`

---

## Hotfix Context: Slice 117 Hotfix E Transfer Approval Mirror Fail-Closed

Issue mapping: `#60`

### Objective + scope lock
- Objective: prevent transfer approvals from being reported as queued when mirror sync to web approvals inbox fails.
- Scope guard: runtime + server mirror/read error-contract hardening + regression tests + canonical docs only; no schema changes.

### Expected touched files
- `apps/agent-runtime/xclaw_agent/cli.py`
- `apps/agent-runtime/tests/test_trade_path.py`
- `apps/network-web/src/lib/transfer-mirror-schema.ts`
- `apps/network-web/src/app/api/v1/agent/transfer-approvals/mirror/route.ts`
- `apps/network-web/src/app/api/v1/management/agent-state/route.ts`
- `skills/xclaw-agent/scripts/xclaw_agent_skill.py`
- `apps/agent-runtime/tests/test_x402_skill_wrapper.py`
- `docs/XCLAW_SOURCE_OF_TRUTH.md`
- `docs/api/WALLET_COMMAND_CONTRACT.md`
- `docs/api/openapi.v1.yaml`
- `docs/XCLAW_SLICE_TRACKER.md`
- `docs/XCLAW_BUILD_ROADMAP.md`
- `spec.md`
- `tasks.md`
- `acceptance.md`
- `docs/CONTEXT_PACK.md`
