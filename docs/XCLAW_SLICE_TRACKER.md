# X-Claw Slice Tracker (Sequential Build Plan)

Use this alongside `docs/XCLAW_BUILD_ROADMAP.md`.

Rules:
- Complete slices in order.
- Mark a slice complete only when all DoD checks pass.
- Do not start next slice until current slice is marked complete.
- If behavior changes, update source-of-truth + artifacts in the same slice.
- Sequencing note: Slice 69-77 entries marked `[!]` are documentation/evidence blockers, not implementation-absence blockers. Their code paths are implemented; issue-mapping/screenshot evidence remains pending.

Status legend:
- [ ] not started
- [~] in progress
- [x] complete
- [!] blocked

---

## Slice 133-138: Dual-Family Runtime (EVM + Solana)
Status: [~]

Goal:
- Reverse EVM-only product scope to dual-family (`evm`, `solana`) while preserving unified command flow.

DoD:
- [~] canonical docs/contracts updated to dual-family truth.
- [~] chain registry + public schema support `family=evm|solana`.
- [~] Solana chain configs (`solana_devnet`, `solana_testnet`, `solana_mainnet_beta`) added.
- [~] runtime wallet create/import/balance/send paths support Solana.
- [~] runtime spot trade quote/execute supports Solana via Jupiter.
- [~] web trade quote/build routes dispatch by chain family.
- [~] skill docs and wrapper examples updated for Solana chains.
- [ ] full validation sequence + regression evidence posted to mapped issue.

---

## Slice 139-146: Localnet-First Full Solana Agent Parity
Status: [~]

Goal:
- Make `solana_localnet` the default deterministic Solana test target and extend parity across faucet, liquidity add/remove, approvals, and audit trails.

DoD:
- [~] `solana_localnet` chain config added and visible.
- [~] family-aware faucet routes support Solana localnet deterministic funding flow.
- [~] runtime liquidity add/remove execute path supports Solana CLMM adapter families.
- [~] skill/docs updated for localnet-first Solana workflows.
- [ ] full sequential validations + evidence posted to mapped issue.

---

## Slice 147-152: Real SPL Faucet + Direct Raydium CLMM
Status: [~]

Goal:
- Replace Solana faucet aliasing with real SPL mint/ATA transfers and introduce direct on-chain Raydium CLMM execution path for non-localnet Solana.

DoD:
- [~] no alias placeholders in active Solana faucet responses.
- [~] localnet bootstrap script provisions signer + wrapped/stable mints.
- [~] runtime splits `local_clmm` (localnet only) vs `raydium_clmm` (non-localnet direct path) with deterministic fail-closed guards.
- [~] canonical artifacts and schema/OpenAPI examples aligned.
- [ ] full sequential validation + issue evidence posted.

---

## Slice 153-158: Tatum Solana RPC + Planner-Based Raydium
Status: [~]

Goal:
- move Solana runtime RPC transport to chain-aware `tatum|standard` provider contract and replace Raydium static instruction blobs with planner-derived execution plans.

DoD:
- [~] shared Solana RPC client resolves `tatum` headers + fallback endpoint selection.
- [~] runtime no longer depends on `instructionDataHex` for non-localnet Raydium add/remove.
- [~] Solana non-localnet Raydium quote/add/remove flows use planner-derived pool/account metadata.
- [~] chain configs move from raw instruction blobs to `programIds/poolRegistry/accountsTemplate`.
- [ ] full sequential validation + issue evidence posted.

---

## Slice 159-163: Solana Deposits + Management Parity
Status: [~]

Goal:
- Make management deposit/transfer-confirmation surfaces chain-family aware (`evm|solana`) while keeping withdraw behavior audit-only.

DoD:
- [~] canonical docs/contracts updated for family-neutral management deposit address/tx id semantics.
- [~] deposit/withdraw schemas accept Solana-shaped address/signature values.
- [~] `solana_devnet` deposits capability enabled (localnet already enabled); mainnet/testnet remain deferred.
- [~] management deposit sync dispatches by chain family (`evm` + `solana`) with deterministic degraded handling.
- [~] management transfer confirmation resolvers and agent page tx explorer links are family-aware.
- [ ] full sequential validation + grep proofs + issue evidence posted.

---

## Slice 164-169: Solana-Native x402 Parity (Localnet/Devnet First)
Status: [~]

Goal:
- Make x402 settlement family-aware and chain-native (EVM + Solana), replacing header-only simulated settlement behavior.

DoD:
- [~] canonical x402 asset contract updated to `native|token` with compatibility alias `erc20`.
- [~] `solana_localnet` + `solana_devnet` have `capabilities.x402=true`; `solana_mainnet_beta` + `solana_testnet` remain deferred.
- [~] runtime x402 pay flow executes local on-chain settlement and submits proof via hosted pay endpoints.
- [~] hosted pay endpoints verify chain tx proof by family before setting status `filled`.
- [~] schemas/openapi/skill docs are updated for family-neutral asset address + tx id.
- [ ] full sequential validation + grep proofs + issue evidence posted.

---

## Slice 01: Environment + Toolchain Baseline
Status: [x]

Goal:
- Server VM runs Node, PM2, gh, Postgres, and Redis reliably; agent/OpenClaw runtime remains Python-first and independently hosted.

DoD:
- [x] tool versions captured
- [x] Postgres/Redis healthy
- [x] `npm run build` works
- [x] `openclaw skills list --eligible` works

---

## Slice 02: Canonical Contracts Freeze
Status: [x]

Goal:
- Schemas/contracts/docs are coherent before deeper implementation.

DoD:
- [x] chain config files validated
- [x] `docs/api/openapi.v1.yaml` aligned
- [x] `docs/api/WALLET_COMMAND_CONTRACT.md` aligned
- [x] `npm run db:parity` passes

---

## Slice 03: Agent Runtime CLI Scaffold (Done-Path Ready)
Status: [x]

Goal:
- `apps/agent-runtime/bin/xclaw-agent` exists with full command surface and JSON responses.

DoD:
- [x] all wallet command routes callable
- [x] wrapper delegates end-to-end without command-not-found
- [x] structured JSON errors returned for invalid inputs

---

## Slice 04: Wallet Core (Create/Import/Address/Health)
Status: [x]

Goal:
- Real wallet lifecycle baseline works on local machine.

DoD:
- [x] `wallet-create` works
- [x] `wallet-import` works
- [x] `wallet-address` works
- [x] `wallet-health` returns real state
- [x] no persistent plaintext key/password files

---

## Slice 05: Wallet Auth + Signing
Status: [x]

Goal:
- Wallet can sign API challenges for recovery/auth.

DoD:
- [x] `wallet-sign-challenge` implemented
- [x] signature verifies server-side format expectations
- [x] negative tests for empty/invalid challenge

---

## Slice 06: Wallet Spend Ops (Send + Balance + Token Balance + Remove)
Status: [x]

Goal:
- Controlled send and balance operations through runtime.

DoD:
- [x] `wallet-send` implemented with guardrails
- [x] `wallet-balance` + `wallet-token-balance` implemented
- [x] `wallet-remove` cleanup verified
- [x] spend blocked when policy preconditions fail

---

## Slice 06A: Foundation Alignment Backfill (Post-06 Prereq)
Status: [x]

Goal:
- Reconcile foundational server/web structure gaps from Slices 01-06 so Slice 07+ executes on canonical architecture.

DoD:
- [x] `apps/network-web` exists as canonical Next.js App Router surface for web+API.
- [x] Root scripts/tooling invoke canonical web app path (no hidden dependency on non-canonical root `src/app` layout).
- [x] Runtime separation remains explicit: Node/Next.js for server/web, Python-first for agent/OpenClaw.
- [x] Roadmap/tracker/source-of-truth are synchronized on this prerequisite before any Slice 07 endpoint implementation.

---

## Slice 07: Core API Vertical Slice
Status: [x]

Goal:
- Minimal production-shape API for register/heartbeat/trade/event + public reads.

DoD:
- [x] core write endpoints functional: `POST /api/v1/agent/register`, `POST /api/v1/agent/heartbeat`, `POST /api/v1/trades/proposed`, `POST /api/v1/trades/:tradeId/status`, `POST /api/v1/events`
- [x] public read endpoints functional: leaderboard, agents search, profile, trades, activity
- [x] agent write auth baseline enforced (`Authorization: Bearer` + `Idempotency-Key`)
- [x] error contract is consistent (`code`, `message`, optional `actionHint`, optional `details`, `requestId`)

---

## Slice 08: Auth + Management Vertical Slice
Status: [x]

Goal:
- Management session, step-up, and sensitive writes work as specified.

DoD:
- [x] session bootstrap works on `/agents/:id?token=...`
- [x] step-up challenge/verify works
- [x] revoke-all works
- [x] management cookie + step-up cookie + CSRF enforcement align with canonical wire contract
- [x] token bootstrap is stripped from URL after validation

---

## Slice 09: Public Web Vertical Slice
Status: [x]

Goal:
- Public users can browse dashboard/agents/profile with correct visibility rules.

DoD:
- [x] `/`, `/agents`, `/agents/:id` show expected data
- [x] management controls hidden when unauthorized
- [x] mock vs real visual separation present
- [x] canonical status vocabulary used exactly: `active`, `offline`, `degraded`, `paused`, `deactivated`

---

## Slice 10: Management UI Vertical Slice
Status: [x]

Goal:
- Authorized users can manage one agent end-to-end.

DoD:
- [x] approval queue works
- [x] policy controls + pause/resume work
- [x] withdraw controls work with step-up requirements
- [x] off-DEX settlement queue/controls and audit log panel work
- [x] global header dropdown + logout behavior correct

---

## Slice 11: Hardhat Local Trading Path
Status: [x]

Goal:
- Propose -> approval -> execute -> verify works locally.

DoD:
- [x] local DEX contracts deployed
- [x] `config/chains/hardhat_local.json` updated with addresses
- [x] lifecycle passes with evidence (including retry constraints and management/step-up checks for touched flows)

---

## Slice 12: Off-DEX Escrow Local Path
Status: [x]

Goal:
- Intent -> accept -> fund -> settle path works locally.
- Superseded by Slice 19 for active product surface (hard removal from runtime/API/UI/docs).

DoD:
- [x] off-DEX intent endpoints/runtime hooks active
- [x] escrow flow status transitions verified
- [x] public activity/profile shows redacted intent metadata + settlement tx links

---

## Slice 13: Metrics + Leaderboard + Copy
Status: [x]

Goal:
- Ranking and copy paths behave per contract.

DoD:
- [x] mode-separated leaderboards (Mock/Real)
- [x] metrics pipeline updates snapshots/caches per contract windows
- [x] copy subscription + copy intent lifecycle + rejection reasons implemented
- [x] self vs copied breakdown visible in profile

---

## Slice 14: Observability + Ops
Status: [x]

Goal:
- System is operable and diagnosable.

DoD:
- [x] `/api/health` + `/api/status` working
- [x] `/status` diagnostics page implemented with public-safe health visibility
- [x] structured logs + core alerts active
- [x] rate limits + correlation IDs + degraded/offline observability verified
- [x] backup + restore drill completed

---

## Slice 15: Base Sepolia Promotion
Status: [x]

Goal:
- Promote validated local feature set to Base Sepolia.

DoD:
- [x] test DEX/escrow contracts deployed and verified
- [x] `config/chains/base_sepolia.json` finalized with `factory/router/quoter/escrow` + evidence links + `deploymentStatus=deployed`
- [x] real-mode path passes testnet acceptance

---

## Slice 16: MVP Acceptance + Release Gate
Status: [x]

Goal:
- Finish MVP with evidence package and release confidence.

DoD:
- [x] `docs/MVP_ACCEPTANCE_RUNBOOK.md` fully executed
- [x] required evidence captured and archived
- [x] critical defects = 0
- [x] binary acceptance criteria met (linux-hosted web proof, search/profile visibility, write auth+idempotency, deterministic demo rerun, Python-first agent runtime boundary)
- [x] roadmap/source-of-truth synced to final state

---

## Slice 17: Deposits + Agent-Local Limit Orders
Status: [x]

Goal:
- Deliver self-custody deposit visibility with server-confirmed tracking and agent-local limit-order execution that remains functional during website/API outages.

DoD:
- [x] `GET /api/v1/management/deposit` returns deposit address, balance snapshots, recent confirmed deposits, and sync status.
- [x] management limit-order create/list/cancel endpoints are implemented and contract-documented.
- [x] agent pending/status limit-order endpoints are implemented for local mirror/execution flow.
- [x] Python runtime adds `limit-orders sync|status|run-once|run-loop` commands.
- [x] runtime can execute mirrored limit orders locally and replay queued status updates after API recovery.
- [x] `/agents/:id` management rail exposes deposit and limit-order controls.
- [x] `infrastructure/scripts/e2e-full-pass.sh` includes deposit + limit-order + API outage replay validations.
- [x] mandatory gates pass: `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`.

---

## Slice 18: Hosted Agent Bootstrap Skill Contract
Status: [x]

Goal:
- Provide a Moltbook/4claw-style hosted `https://<host>/skill.md` bootstrap contract so agents can self-install the X-Claw skill, initialize wallet/runtime prerequisites, and register without `molthub`.

DoD:
- [x] `GET /skill.md` is publicly hosted and returns plain-text bootstrap instructions.
- [x] `GET /skill-install.sh` is publicly hosted and returns executable installer script.
- [x] `GET /skill-install.ps1` is publicly hosted and returns executable installer script.
- [x] `POST /api/v1/agent/bootstrap` issues signed agent credentials for one-command provisioning.
- [x] Agent key recovery endpoints implemented: `POST /api/v1/agent/auth/challenge` + `POST /api/v1/agent/auth/recover`.
- [x] Hosted instructions are Python-first and use repository scripts (no Node requirement for agent skill bootstrap).
- [x] Instructions cover setup/install, wallet create/address, register, and heartbeat.
- [x] Runtime auto-recovers stale/invalid agent API keys using wallet-sign challenge flow.
- [x] Homepage includes a clear agent join block with direct installer command and agent runtime guidance.
- [x] required gates pass: `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`.

---

## Slice 19: Agent-Only Public Trade Room + Off-DEX Hard Removal
Status: [x]

Goal:
- Remove off-DEX from active product behavior and replace with one global trade room where agents write and public users read.

DoD:
- [x] `GET /api/v1/chat/messages` public endpoint returns newest-first paginated messages.
- [x] `POST /api/v1/chat/messages` enforces agent bearer auth and `agentId` ownership checks.
- [x] off-DEX endpoints/routes are removed from API router and OpenAPI.
- [x] off-DEX command surface removed from runtime and skill wrapper.
- [x] homepage includes read-only Agent Trade Room panel; human write controls are absent.
- [x] `/agents/:id` page no longer exposes off-DEX history or management queue controls.
- [x] migration adds `chat_room_messages` and removes off-DEX table/type artifacts.
- [x] required gates pass: `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, runtime tests.

---

## Slice 20: Owner Link + Outbound Transfer Policy + Agent Limit-Order UX + Mock-Only Reporting
Status: [x]

Goal:
- Add owner-link issuance and outbound transfer policy controls, simplify agent limit-order UX, and enforce mock-only runtime reporting to `/events`.

DoD:
- [x] `POST /api/v1/agent/management-link` issues short-lived owner management URLs for authenticated registered agents.
- [x] `GET /api/v1/agent/transfers/policy` returns effective chain-scoped outbound transfer policy for runtime enforcement.
- [x] `POST/GET /api/v1/limit-orders` and `POST /api/v1/limit-orders/{orderId}/cancel` are implemented with agent auth ownership checks.
- [x] limit-order create enforces cap of max 10 open/triggered orders per agent+chain.
- [x] management policy update supports outbound transfer fields and requires step-up when outbound controls are changed.
- [x] `/agents/:id` management rail includes Owner Link + Outbound Transfers panels.
- [x] runtime `trade execute` only auto-reports mock trades; real trades skip `/events`.
- [x] runtime/skill exposes `wallet-send-token` and limit-order `create/cancel/list/run-loop` command surface.
- [x] runtime/skill exposes `faucet-request` command for fixed `0.02 ETH` on base_sepolia with once-per-UTC-day limit.
- [x] required gates pass: `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, runtime tests.

---

## Slice 21: Mock Testnet Tokens + Token Faucet Drips + Seeded Router Liquidity
Status: [x]

Goal:
- Make Base Sepolia trading practical without requiring agents to wrap scarce testnet ETH by deploying mock WETH/USDC, seeding router balances, and extending faucet drips to include mock tokens.

DoD:
- [x] Base Sepolia deployment script deploys mock `WETH` + `USDC`, seeds router balances, and sets router `ethUsdPriceE18` using external API with fallback `2000`.
- [x] `MockRouter` implements `getAmountsOut` and price-based WETH/USDC quoting.
- [x] `POST /api/v1/agent/faucet/request` dispenses fixed `0.02 ETH` plus token drips (10 WETH, 20k USDC) when configured and funded.
- [x] Faucet daily limiter is only consumed when faucet has sufficient ETH and token balances (no "burned" rate limit on empty faucet).
- [x] Faucet rejects demo agents and placeholder recipient addresses.
- [x] `docs/XCLAW_SOURCE_OF_TRUTH.md` and `docs/api/openapi.v1.yaml` are synced to new faucet behavior and mock token strategy.

---

## Slice 22: Non-Upgradeable V2 Fee Router Proxy (0.5% Output Fee)
Status: [x]

Goal:
- Deploy a non-upgradeable V2-compatible router proxy that takes a fixed 50 bps fee on output token atomically and preserves net semantics for quotes/minOut.

DoD:
- [x] `infrastructure/contracts/XClawFeeRouterV2.sol` implemented with fee-on-output and net semantics.
- [x] Hardhat tests cover `getAmountsOut` net quote, fee transfer, and net slippage revert.
- [x] Hardhat local deploy script outputs `dexRouter` (underlying) and `router` (fee proxy) and artifacts are verified.
- [x] `config/chains/hardhat_local.json` uses proxy router address and preserves underlying router address.
- [x] `docs/XCLAW_SOURCE_OF_TRUTH.md` updated with Slice 22 locked contract semantics.
- [x] `docs/XCLAW_BUILD_ROADMAP.md` updated with Slice 22 checklist.
- [x] Base Sepolia deploy script updated to deploy proxy router and write both underlying + proxy addresses to artifact.
- [x] Base Sepolia verify script updated to verify proxy router code presence and deployment tx receipts.
- [x] Base Sepolia deploy executed and verified (evidence artifacts written under `infrastructure/seed-data/`).
- [x] `config/chains/base_sepolia.json` updated to use proxy router address (and preserve underlying router).

---

## Slice 23: Agent Spot Swap Command (Token->Token via Configured Router)
Status: [x]

Goal:
- Let agents execute a one-shot token->token swap directly from runtime/skill without going through limit orders, using `coreContracts.router` (which may be the Slice 22 fee proxy).

DoD:
- [x] runtime CLI supports `xclaw-agent trade spot` with `--token-in/--token-out/--amount-in/--slippage-bps` and uses router `getAmountsOut` (net semantics) to compute `amountOutMin`.
- [x] skill wrapper exposes `trade-spot <token_in> <token_out> <amount_in> <slippage_bps>`.
- [x] `setup_agent_skill.py` ensures a default `~/.xclaw-agent/policy.json` exists (does not overwrite existing policy) so spend actions can run after install.
- [x] tests cover success path call-shape and at least one input validation failure path.
- [x] `docs/XCLAW_SOURCE_OF_TRUTH.md` + skill command references updated.
- [x] required gates pass: `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, runtime tests.

---

## Slice 24: Agent UX Hardening + Chat/Limit-Orders Reliability + Safer Owner-Link
Status: [x]

Goal:
- Make agent outputs more actionable for smaller models (clear empty states, identity context, request IDs).
- Fix chat internal errors and make failures diagnosable.
- Fix limit-order UX (symbols allowed), make limit-order runner testable, and lock limit price semantics.
- Harden spot swap sender against nonce drift and fix gas cost formatting.
- Ensure owner management links are directly handoff-ready in runtime output.

DoD:
- [x] `status` includes identity context (default chain, agentId when available, wallet address, hostname, hasCast).
- [x] `intents-poll` uses explicit empty-state message when count is 0.
- [x] `chat-poll` and `chat-post` surface API `requestId` in failure details.
- [x] `GET/POST /api/v1/chat/messages` no longer swallow errors and log structured server errors with requestId.
- [x] Health snapshot DB check marks schema as degraded when chat table is missing.
- [x] runtime limit-orders-create resolves canonical token symbols to 0x addresses.
- [x] limit order `limitPrice` semantics are locked as `tokenIn per 1 tokenOut` with trigger rules `buy<=` / `sell>=`.
- [x] skill wrapper exposes `limit-orders-run-once`.
- [x] skill wrapper defaults `limit-orders-run-loop` to `--iterations 1` unless explicitly configured.
- [x] trade-spot sender recovers from `nonce too low` with retry using suggested nonce and backoff.
- [x] trade-spot gas cost display does not round non-zero costs to `"0"`.
- [x] owner-link output returns full managementUrl for direct owner handoff and includes short-lived warning.
- [x] required gates pass: `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, runtime tests.

---

## Slice 25: Agent Skill UX Upgrade (Security + Reliability + Contract Fixes)
Status: [x]
Issue: #20 ("Slice 25: Agent Skill UX Upgrade (redaction + faucet pending + limit orders create fix)")

Goal:
- Preserve sensitive redaction defaults while keeping owner-link handoff directly usable in chat.
- Make faucet UX explicitly pending-aware so post-faucet balance checks are not confusing.
- Fix `limit-orders-create` schema mismatch caused by sending `expiresAt: null`.
- Improve limit-order UX documentation (limit price units).

DoD:
- [x] skill wrapper redacts `sensitiveFields` by default, with explicit owner-link handoff exception.
- [x] `faucet-request` response includes machine-readable pending guidance (`pending`, `recommendedDelaySec`, `nextAction`).
- [x] `limit-orders-create` succeeds with standard args and does not send `expiresAt` unless provided.
- [x] runtime tests include:
  - [x] faucet success includes pending guidance fields
  - [x] limit-orders-create omits `expiresAt` when missing
  - [x] limit-orders-create failure surfaces server `details` for schema errors
- [x] docs sync: source-of-truth + roadmap + skill docs updated in same change.
- [x] required gates pass: `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, runtime tests.

---

## Slice 26: Agent Skill Robustness Hardening (Timeouts + Identity + Single-JSON)
Status: [x]
Issue: #21 ("Slice 26: Agent Skill Robustness Hardening (timeouts + single-JSON + identity)")

Goal:
- Make agent skill/runtime safer and more reliable for autonomous use (hang prevention, clearer identity/health, schedulable faucet rate-limit, single-JSON outputs).

DoD:
- [x] skill wrapper enforces `XCLAW_SKILL_TIMEOUT_SEC` (default 240s) and returns structured JSON `timeout` error when exceeded.
- [x] runtime enforces per-step cast/RPC timeouts (`XCLAW_CAST_CALL_TIMEOUT_SEC`, `XCLAW_CAST_RECEIPT_TIMEOUT_SEC`, `XCLAW_CAST_SEND_TIMEOUT_SEC`) with actionable timeout codes.
- [x] `status` includes `agentName` best-effort without making `status` brittle.
- [x] `wallet-health` includes `nextAction` and `actionHint` on ok responses.
- [x] `faucet-request` surfaces `retryAfterSec` on rate-limit responses (machine schedulable).
- [x] `limit-orders-run-loop` emits exactly one JSON object per invocation (no multi-line JSON).
- [x] `trade-spot` includes numeric `totalGasCostEthExact` and keeps a pretty display field.
- [x] docs sync: source-of-truth + wallet contract + skill docs updated in same change.
- [x] required gates pass: `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, runtime tests.

Blocker:
- DoD gates are now passing in-session; commit `97dd658` is pushed and verification evidence is posted to issue #21.
- Live wrapper smoke is environment-blocked in this shell due missing required `XCLAW_*` env vars (`missing_env`), and is tracked in `acceptance.md` with exact unblock commands.
- Production incident follow-up implemented in code/docs: owner-link host normalization + management unauthorized guidance + static-asset verification runbook/script. External deploy/cache refresh remains required to clear CSS chunk 404 on `xclaw.trade`.
- Static-asset verifier is now callable as a release-gate command: `npm run ops:verify-static-assets` (uses `XCLAW_VERIFY_BASE_URL` + `XCLAW_VERIFY_AGENT_ID`).
- Agent stale/sync-delay UX refined: UI now keys stale state off `last_heartbeat_at` with 180s threshold so idle-but-healthy agents are not flagged as sync-delay.

---

## Slice 27: Responsive + Multi-Viewport UI Fit (Phone + Tall + Wide)
Status: [x]
Issue: #22 ("Slice 27: Responsive + Multi-Viewport UI Fit (phone + tall + wide)")

Goal:
- Make the web UX fit and remain usable across phone, tall-screen, desktop, and wide-monitor layouts while preserving canonical status/theme semantics and one-site public+management model.

DoD:
- [x] docs sync first: source-of-truth + roadmap + tracker + context/spec/tasks aligned to Slice 27 scope.
- [x] global responsive foundation in `apps/network-web/src/app/globals.css` with explicit breakpoints and viewport-safe layout behavior.
- [x] desktop tables + compact mobile cards implemented for `/` leaderboard, `/agents` directory, and `/agents/:id` trades.
- [x] `/agents/:id` management rail remains sticky on desktop and stacks cleanly on tablet/phone with usable controls.
- [x] `/status` overview/dependency/provider/queue panels remain readable without critical overflow on phone.
- [x] dark/light themes preserved (dark default) and canonical status vocabulary unchanged: `active`, `offline`, `degraded`, `paused`, `deactivated`.
- [x] required gates pass: `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`.
- [x] verification evidence captured in `acceptance.md` for viewport matrix:
  - [x] 360x800
  - [x] 390x844
  - [x] 768x1024
  - [x] 900x1600
  - [x] 1440x900
  - [x] 1920x1080

---

## Slice 28: Mock Mode Deprecation (Network-Only User Surface, Base Sepolia)
Status: [x]
Issue: #23 ("Slice 28: Mock Mode Deprecation (Network-Only User Surface, Base Sepolia)")

Goal:
- Soft-deprecate mock trading so user-facing web and agent skill/runtime are network-only (Base Sepolia) while backend contracts/storage remain compatibility-safe for this slice.

DoD:
- [x] docs sync first: source-of-truth + roadmap + tracker + openapi + context/spec/tasks/acceptance aligned to Slice 28.
- [x] dashboard/agents/profile UI removes mock/real mode controls and mock wording; user-facing terminology is network/base_sepolia.
- [x] public read APIs remain backward-compatible for `mode` query values but coerce to real/network-only result sets.
- [x] historical mock rows remain stored but are excluded from public UI result paths.
- [x] runtime/skill mode-bearing flows reject `mock` with structured `unsupported_mode` + actionable `actionHint`.
- [x] skill docs/command references/hosted `skill.md` and installer copy are network-only (no mock mentions for agent-facing guidance).
- [x] required gates pass: `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, runtime tests.

---

## Slice 29: Dashboard Chain-Scoped UX + Activity Detail + Chat-Style Room
Status: [x]
Issue: #24 ("Slice 29: Dashboard Chain-Scoped UX + Activity Detail + Chat-Style Room")

Goal:
- Refine dashboard readability for the current network-only product surface by removing redundant chain labels, surfacing trade pair details in live activity, and presenting trade room messages in a clearer chat-style layout.

DoD:
- [x] docs sync first: source-of-truth + roadmap + tracker + context/spec/tasks/acceptance aligned to Slice 29.
- [x] dashboard no longer shows redundant chain-name chip text for single-chain context.
- [x] dashboard trade room and live activity are filtered to active chain context (Base Sepolia).
- [x] live activity cards show trade pair/direction detail (`pair` and/or `token_in -> token_out`) when available.
- [x] agent trade room is styled as chat-like message cards while preserving responsive behavior.
- [x] required gates pass: `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`.

---

## Slice 30: Owner-Managed Daily Trade Caps + Usage Visibility (Trades Only)
Status: [x]
Issue: pending assignment

Goal:
- Add owner-managed UTC-day trade caps (USD + filled-trade count), owner-only usage visibility on `/agents/:id`, and dual enforcement across runtime/server with idempotent usage accounting.

DoD:
- [x] migration adds policy cap fields and `agent_daily_trade_usage` aggregation table.
- [x] `POST /api/v1/management/policy/update` persists cap fields (`dailyCapUsdEnabled`, `dailyTradeCapEnabled`, `maxDailyTradeCount`).
- [x] `GET /api/v1/management/agent-state` returns latest cap config + UTC-day usage.
- [x] `GET /api/v1/agent/transfers/policy` returns outbound policy + effective trade cap policy + UTC-day usage.
- [x] `POST /api/v1/agent/trade-usage` implemented with agent auth + idempotency + monotonic non-negative deltas.
- [x] server-side cap checks enforced on trade proposal, limit-order create, and limit-order filled transition.
- [x] runtime enforces trade caps for `trade spot`, `trade execute`, and limit-order fills using server policy + cached fallback.
- [x] runtime queues/replays trade-usage updates when API is unavailable without double counting.
- [x] `/agents/:id` management rail exposes cap toggles/values and owner-only usage progress.
- [x] docs/artifacts synced (`source-of-truth`, `openapi`, tracker, roadmap, context/spec/tasks/acceptance).
- [x] required gates pass: `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, runtime tests.

---

## Slice 31: Agents + Agent Management UX Refinement (Operational Clean)
Status: [x]
Issue: pending assignment

Goal:
- Refine `/agents` and `/agents/:id` into a cleaner operational UX with card-first directory presentation, stronger profile hierarchy, and progressive-disclosure management controls while preserving one-site model and existing behavior contracts.

DoD:
- [x] `/agents` is card-first with optional desktop table fallback and includes KPI summaries from lightweight API augmentation.
- [x] `GET /api/v1/public/agents` supports optional `includeMetrics=true` with nullable `latestMetrics` per row.
- [x] `GET /api/v1/public/activity` supports optional `agentId` and filters server-side.
- [x] `/agents/:id` public sections keep long-scroll order and improve section hierarchy/copy/readability.
- [x] `/agents/:id` management rail is regrouped by operational priority and uses progressive disclosure for advanced sections.
- [x] status vocabulary remains unchanged: `active`, `offline`, `degraded`, `paused`, `deactivated`.
- [x] docs/artifacts synced (`source-of-truth`, `openapi`, tracker, roadmap, context/spec/tasks/acceptance).
- [x] required gates pass: `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`.

---

## Slice 32: Per-Agent Chain Enable/Disable (Owner-Gated, Chain-Scoped Ops)
Status: [x]
Issue: #25 ("Slice 32: Per-Agent Chain Enable/Disable (Owner-Gated, Chain-Scoped Ops)")

Goal:
- Add owner-managed per-agent, per-chain enable/disable switch. When disabled, agent trade and `wallet-send` actions fail closed for that chain, while owner withdraw remains available for safety recovery.

DoD:
- [x] docs sync first: source-of-truth + roadmap + tracker + openapi + context/spec/tasks/acceptance aligned to Slice 32.
- [x] migration adds `agent_chain_policies` table with per-agent/per-chain `chain_enabled`.
- [x] `POST /api/v1/management/chains/update` implemented with step-up required for enable only.
- [x] `GET /api/v1/management/agent-state` accepts optional `chainKey` and returns `chainPolicy` for the requested chain.
- [x] `GET /api/v1/agent/transfers/policy` returns `chainEnabled` for runtime consumption.
- [x] server enforcement blocks trade/limit-order execution paths when chain is disabled with structured `code=chain_disabled`.
- [x] runtime enforces owner chain access (`chainEnabled`) for trade and `wallet-send` paths.
- [x] `/agents/:id` management rail exposes “Chain Access” toggle for active chain (global header selector drives chain context).
- [x] required gates pass: `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, runtime tests.

---

## Slice 33: MetaMask-Like Agent Wallet UX + Simplified Approvals (Global + Per-Token)
Status: [x]
Issue: #42 (umbrella)

Goal:
- Redesign `/agents/:id` to feel like a MetaMask-style wallet (assets + unified activity feed), and simplify approvals to global-on/off + per-token preapprovals (tokenIn-only) with no pair approvals.

DoD:
- [x] docs sync first: source-of-truth + roadmap + tracker + openapi + context/spec/tasks/acceptance aligned to Slice 33.
- [x] `/agents/:id` public view is wallet-first with MetaMask-like header, assets list, and unified activity feed (trades + events).
- [x] approvals model:
  - [x] Global Approval toggle (`approval_mode=auto`) exists owner-only and is step-up gated on enable.
  - [x] Per-token preapproval toggles (`allowed_tokens`) exist owner-only and are step-up gated on enable.
  - [x] Pair approvals are removed from UI and server usage.
- [x] `POST /api/v1/trades/proposed` sets initial trade status to `approved` or `approval_pending` based on approval policy (global or tokenIn preapproved).
- [x] runtime `trade spot` is server-first: proposes, waits if `approval_pending`, executes only if approved, and surfaces rejection reason on deny.
- [x] required gates pass: `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, runtime tests.
- [x] slice is mapped to a GitHub issue (required by `AGENTS.md`).

---

## Slice 34: Telegram Approvals (Inline Button Approve) + Web UI Sync
Status: [x]
Issue: #42 (umbrella)

Goal:
- Add Telegram as an optional approvals surface that stays aligned with `/agents/:id` approvals UI.

Note:
- Slice 34 shipped a strict Bearer-secret channel approval endpoint. Slice 37 removes the extra secret requirement and deletes the channel-auth endpoint in favor of agent-auth trade status transition for Telegram approve.

DoD:
- [x] docs sync first: source-of-truth + roadmap + tracker + openapi + context/spec/tasks/acceptance aligned to Slice 34.
- [x] migration adds per-agent/per-chain approval channel enablement + secret hash storage and prompt tracking tables.
- [x] `POST /api/v1/management/approval-channels/update` implemented (step-up required to enable only) and returns secret once on enable.
- [x] `GET /api/v1/management/agent-state` returns chain-scoped `approvalChannels.telegram.enabled`.
- [x] `GET /api/v1/agent/transfers/policy` returns `approvalChannels.telegram.enabled` (no secrets).
- [x] `POST /api/v1/agent/approvals/prompt` implemented (agent-auth) for prompt metadata tracking.
- [x] `POST /api/v1/channel/approvals/decision` implemented (Bearer secret auth) and idempotently transitions `approval_pending -> approved`.
- [x] runtime sends Telegram approval prompt only when Telegram approvals are enabled and OpenClaw last active channel is Telegram; runtime deletes prompt on approval and supports periodic `approvals sync`.
- [x] OpenClaw Telegram callback handler intercepts `xappr|...` approve callbacks and calls X-Claw server directly (no LLM mediation); deletes message on success.
- [x] required gates pass: `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, runtime tests.

---

## Slice 35: Wallet-Embedded Approval Controls + Correct Token Decimals
Status: [x]
Issue: #42 (umbrella)

Goal:
- Move approval policy controls (Global Approval + per-token preapproval) into the wallet card on `/agents/:id`, ensure token balances (notably USDC) render with correct decimals, and remove unnecessary default-collapsed UI for core operator visibility.

DoD:
- [x] docs sync first: source-of-truth + roadmap + tracker + context/spec/tasks/acceptance aligned to Slice 35.
- [x] `/agents/:id` wallet card includes owner-only:
  - [x] `Approve all` (Global Approval) toggle (step-up gated on enable),
  - [x] per-token preapproval buttons inline with asset rows (step-up gated on enable).
- [x] management rail keeps risk limits (caps) controls; approval policy controls are removed from the management rail.
- [x] USDC (and other ERC-20s) display uses decimals from the deposit/balance snapshot (no hardcoded USDC decimals).
- [x] audit log/details section is expanded by default (no extra click to see it).
- [x] required gates pass: `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, runtime tests.

---

## Slice 36: Remove Step-Up Authentication (Management Cookie Only)
Status: [x]
Issue: #42 (umbrella)

Goal:
- Remove the step-up mechanism entirely so management session cookie + CSRF is sufficient for all management actions.

DoD:
- [x] docs sync first: source-of-truth + roadmap + tracker + openapi + context/spec/tasks/acceptance aligned to Slice 36.
- [x] migration drops step-up tables and enum (`stepup_challenges`, `stepup_sessions`, `stepup_issued_for`) and removes legacy `approvals.requires_stepup`.
- [x] step-up endpoints removed (404): `/api/v1/management/stepup/challenge`, `/api/v1/management/stepup/verify`, `/api/v1/agent/stepup/challenge`.
- [x] no API endpoint requires `xclaw_stepup` cookie; `requireStepupSession` removed.
- [x] `/agents/:id` shows no step-up UI/prompt and management actions no longer require codes.
- [x] runtime removes `xclaw-agent stepup-code` and skill/docs no longer reference step-up.
- [x] required gates pass: `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, runtime tests.

---

## Slice 37: Telegram Approvals Without Extra Secret (Skill-Authoritative, Web + Telegram OR)
Status: [x]
Issue: #42 (umbrella)

Goal:
- Remove the Telegram approvals secret/config step. Telegram approvals should work using the existing `xclaw-agent` skill API key (agent auth) and remain in sync with the web approvals UI: clicking Approve in either surface approves the trade and the other surface converges.

DoD:
- [x] docs sync first: source-of-truth + roadmap + tracker + openapi + context/spec/tasks/acceptance aligned to Slice 37.
- [x] Telegram approvals remain chain-scoped, default enabled, and no longer return/show a secret; `/agents/:id` does not expose a manual Telegram toggle.
- [x] OpenClaw Telegram callback approve uses `xclaw-agent` API key to post `approval_pending -> approved` via `/api/v1/trades/:tradeId/status` (agent-auth + Idempotency-Key).
- [x] channel-auth endpoint `/api/v1/channel/approvals/decision` removed and OpenAPI/schemas updated.
- [x] `/agents/:id` management rail no longer instructs configuring `XCLAW_APPROVALS_TELEGRAM_SECRET`.
- [x] required gates pass: `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, runtime tests.

---

## Slice 38: Telegram Approval Prompt Details + Pending Approval De-Dupe (No Spam)
Status: [x]
Issue: #42 (umbrella)

Goal:
- Make Telegram approval prompts self-describing (swap details) and prevent repeated identical trade requests from creating multiple `approval_pending` trades/prompt spam. If a matching trade is already `approval_pending`, the runtime reuses it and “resumes” once approved.

DoD:
- [x] docs sync first: source-of-truth + roadmap + tracker + context/spec/tasks/acceptance aligned to Slice 38.
- [x] runtime `trade spot` de-dupes identical pending approvals by persisting a local pending-intent key and reusing existing `tradeId` while status remains `approval_pending`.
- [x] approval wait timeout is 30 minutes; timeout error instructs “approve then re-run to resume without creating a new approval”.
- [x] Telegram approval prompt text includes: `Approve swap`, `<amount> <tokenInSymbol> -> <tokenOutSymbol>`, `Chain`, `Trade`.
- [x] Telegram approval prompt is deleted when approval is clicked; runtime also clears local prompt state once the trade leaves `approval_pending`.
- [x] required gates pass: `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, runtime tests.

---

## Slice 39: Approval Amount Visibility + Gateway Telegram Callback Reliability
Status: [x]
Issue: #42 (umbrella)

Goal:
- Make approvals and activity in `/agents/:id` show human amounts (not just pairs), and ensure Telegram Approve buttons reliably perform `approval_pending -> approved` and delete the Telegram message (no LLM mediation).

DoD:
- [x] Approval queue rows show amount + tokenIn -> tokenOut (best-effort symbol resolution).
- [x] Activity feed trade rows show amountIn and (when available) amountOut alongside token labels.
- [x] OpenClaw gateway intercepts `xappr|a|<tradeId>|<chainKey>` callback payloads and posts `POST /api/v1/trades/:tradeId/status` with agent-auth + Idempotency-Key, then deletes the Telegram prompt on success.
- [x] Runtime outbox replay is best-effort and does not block input validation (e.g. bad slippage returns `invalid_input` even when API env is missing).
- [x] Patch artifact recorded under `patches/openclaw/` for OpenClaw `2026.2.9` dist gateway handler.
- [x] required gates pass: `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, runtime tests.

---

## Slice 40: OpenClaw Patch Auto-Apply (Portable, No Restart Loops)
Status: [x]
Issue: #42 (umbrella)

Goal:
- Make Telegram approval callback support portable: the X-Claw installer/update flow and the xclaw-agent skill wrapper automatically (re)apply the OpenClaw gateway patch after OpenClaw updates, and restart safely without loops.

DoD:
- [x] docs sync first: source-of-truth + roadmap + tracker + context/spec/tasks/acceptance aligned to Slice 40.
- [x] patch auto-apply:
  - [x] installer/update path applies patch idempotently (no-op if already patched),
  - [x] next skill use after OpenClaw update re-applies patch if overwritten.
- [x] restart safety:
  - [x] gateway restart is best-effort and only triggered when a patch is newly applied,
  - [x] restart uses cooldown + lock to avoid repeated restart loops.
- [x] patch mechanism does not depend on hardcoded `dist/loader-*.js` filenames (detects target file(s) dynamically).
- [x] patch state is recorded locally so repeated calls are cheap and failure backoff prevents thrashing.
- [x] required gates pass: `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, runtime tests.

---

## Slice 41: Telegram Approve Button Reliability (Patch Correct Gateway Bundle)
Status: [x]
Issue: #42 (umbrella)

Goal:
- Ensure Telegram inline Approve buttons actually approve the trade server-side by patching the OpenClaw gateway bundle that is executed in `gateway` mode (e.g. `dist/reply-*.js`), not just `dist/loader-*.js`.

DoD:
- [x] docs sync first: source-of-truth + roadmap + tracker + context/spec/tasks/acceptance aligned to Slice 41.
- [x] OpenClaw patch auto-apply detects and patches all gateway bundles that contain Telegram `bot.on("callback_query"` handlers used by `dist/index.js` (including `reply-*.js`), not only `loader-*.js`.
- [x] Clicking Telegram Approve triggers `POST /api/v1/trades/:tradeId/status` (`approval_pending -> approved`) and deletes the Telegram prompt message on success (or on 409 already-approved/filled).
- [x] Patch is idempotent and does not create duplicated intercept blocks in patched bundles (stable marker / replace semantics).
- [x] Patch artifact recorded under `patches/openclaw/` for OpenClaw `2026.2.9` gateway bundle(s) as needed.
- [x] required gates pass: `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, runtime tests.

---

## Slice 42: Telegram Approve+Deny + Approval Decision Chat Feedback + Safer De-Dupe
Status: [x]
Issue: #42 (umbrella)

Goal:
- Adjust trade de-dupe so identical trades are only de-duped while the prior trade is still awaiting approval (`approval_pending`).
- Add Telegram **Deny** button alongside Approve (colors not supported; use text), and ensure clicking either produces an immediate agent-visible chat acknowledgement with details.
- Ensure when approval/denial happens (Telegram or web), the agent reports the decision back into the active Telegram chat with details (tradeId + amount/pair + reason if denied).

DoD:
- [x] docs sync first: source-of-truth + roadmap + tracker + context/spec/tasks/acceptance aligned to Slice 42.
- [x] runtime de-dupe rule:
  - [x] if an identical trade exists in `approval_pending`, reuse that tradeId (no new proposal),
  - [x] once the trade is no longer `approval_pending`, a repeated identical request proposes a new tradeId.
- [x] Telegram prompt includes Approve + Deny buttons and is deleted on either decision.
- [x] Telegram decision sends a confirmation message into the same chat with trade details and (for deny) a reason.
- [x] When a trade is approved/denied via the web UI while runtime is waiting, runtime posts a decision message into the active Telegram chat with details.
- [x] required gates pass: `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, runtime tests.

---

## Slice 43: Telegram Callback Idempotency Fix (No `idempotency_conflict`)
Status: [x]
Issue: #42 (umbrella)

Goal:
- Eliminate Telegram inline-button approval failures caused by idempotency key reuse with a different payload (typically because `at` differs across retries/clicks), while keeping strict callback handling in the OpenClaw gateway patch.

DoD:
- [x] docs sync first: source-of-truth + roadmap + tracker + context/spec/tasks/acceptance aligned to Slice 43.
- [x] OpenClaw gateway patch uses a callback-unique idempotency key (`tg-cb-<callbackId>`) for `POST /api/v1/trades/:tradeId/status`.
- [x] OpenClaw gateway patch sets `at` deterministically from Telegram callback/query timestamp so replays of the same callback are byte-stable.
- [x] Clicking Telegram Approve/Deny no longer produces `idempotency_conflict` errors.
- [x] required gates pass: `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, runtime tests.

---

## Slice 44: Faster Approval Resume (Lower Poll Interval)
Status: [x]
Issue: #42 (umbrella)

Goal:
- Reduce perceived latency after Telegram/web approve/deny by having the runtime resume from `approval_pending` within ~1s (without changing trust boundaries or adding new endpoints).

DoD:
- [x] docs sync first: source-of-truth + roadmap + tracker + context/spec/tasks/acceptance aligned to Slice 44.
- [x] runtime polls approval status every 1s while waiting (instead of 3s).
- [x] required gates pass: `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, runtime tests.

---

## Slice 45: Inline Telegram Approval Buttons (No Extra Prompt Message)
Status: [x]
Issue: #42 (umbrella)

Goal:
- When a trade becomes `approval_pending`, Telegram should show Approve/Deny buttons on the same queued message (wallet summary) instead of sending a second prompt message.

DoD:
- [x] docs sync first: source-of-truth + roadmap + tracker + context/spec/tasks/acceptance aligned to Slice 45.
- [x] runtime does not send out-of-band Telegram prompt messages by default (inline delivery is preferred); legacy prompting can be re-enabled via env.
- [x] skill instructions require embedding OpenClaw `[[buttons: ...]]` directive in the queued message for Telegram.
- [x] required gates pass: `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, runtime tests.

---

## Slice 46: Auto-Attach Telegram Approval Buttons To Queued Message
Status: [x]
Issue: #42 (umbrella)

Goal:
- For Telegram, when the agent posts the queued `approval_pending` trade summary, OpenClaw auto-attaches Approve/Deny inline buttons to that same message (no second prompt message, no reliance on the model emitting `[[buttons: ...]]`).

DoD:
- [x] docs sync first: source-of-truth + roadmap + tracker + context/spec/tasks/acceptance aligned to Slice 46.
- [x] OpenClaw gateway patch auto-attaches buttons when message contains:
  - `Status: approval_pending`
  - `Trade ID: trd_...`
- [x] required gates pass: `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, runtime tests.

---

## Slice 47: Fix Telegram Queued Buttons Attach Point (Agent Reply Send Path)
Status: [x]
Issue: #42 (umbrella)

Goal:
- Ensure the queued `approval_pending` message sent by the agent reply pipeline (OpenClaw `sendTelegramText(bot, ...)`) receives Approve/Deny inline buttons. (Slice 46 initially patched only the CLI send path.)

DoD:
- [x] docs sync first: source-of-truth + roadmap + tracker + context/spec/tasks/acceptance aligned to Slice 47.
- [x] OpenClaw gateway patch auto-attaches queued approval buttons in the agent reply send path (`sendTelegramText`) as well as the CLI send path.
- [x] required gates pass: `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, runtime tests.

---

## Slice 48: Queued Approval Buttons v3 Upgrade + Logging (Debuggable)
Status: [x]
Issue: #42 (umbrella)

Goal:
- Make queued-message button attach behavior debuggable and resilient by upgrading the OpenClaw patch from v2 to v3 (normalized matching + explicit logging), so missing buttons can be diagnosed from gateway logs.

DoD:
- [x] docs sync first: source-of-truth + roadmap + tracker + context/spec/tasks/acceptance aligned to Slice 48.
- [x] OpenClaw patcher replaces queued-buttons v2 injection in `sendTelegramText(...)` with v3 (normalized text + broad `trd_...` extraction).
- [x] OpenClaw emits gateway logs when queued buttons are attached or skipped due to missing tradeId / existing replyMarkup.
- [x] required gates pass: `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, runtime tests.

---

## Slice 49: OpenClaw Patcher Safety (Syntax Check + Targeted Bundle)
Status: [x]
Issue: #42 (umbrella)

Goal:
- Prevent the OpenClaw gateway patcher from bricking `openclaw` by:
  - patching only the required gateway bundle(s), and
  - running a syntax check on patched output before writing to disk.

DoD:
- [x] docs sync first: source-of-truth + roadmap + tracker + context/spec/tasks/acceptance aligned to Slice 49.
- [x] patcher only targets the canonical gateway bundle (`dist/reply-*.js`) instead of patching multiple bundles.
- [x] patcher runs `node --check` against the patched output and refuses to write if syntax fails.
- [x] required gates pass: `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, runtime tests.

---

## Slice 50: Telegram Decision Feedback Routed Through Agent (No Direct Gateway Ack)
Status: [x]
Issue: #42 (umbrella)

Goal:
- After Telegram Approve/Deny is clicked, do not have the OpenClaw gateway post a raw "Approved trade ..." message.
- Instead, route the decision into the agent message pipeline with clear instructions so the agent informs the user (and continues/halts execution accordingly).

DoD:
- [x] docs sync first: source-of-truth + roadmap + tracker + context/spec/tasks/acceptance aligned to Slice 50.
- [x] Telegram callback intercept triggers `processMessage(...)` with a synthetic inbound message describing the decision + instructions.
- [x] Fallback behavior: if synthetic processing fails, post a minimal confirmation message (so the user still gets feedback).
- [x] required gates pass: `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, runtime tests.

---

## Slice 51: Policy Approval Requests (Token Preapprove + Approve All) With Web + Telegram Buttons
Status: [x]
Issue: #42 (umbrella)

Goal:
- Let the agent request owner approval to:
  - preapprove a token for trading (tokenIn preapproval), and
  - enable global trading approvals (Approve all / `approval_mode=auto`).
- Requests must appear on `/agents/:id` like trade approvals and be approvable/denyable from both web UI and Telegram (inline buttons).

DoD:
- [x] docs sync first: source-of-truth + roadmap + tracker + context/spec/tasks/acceptance aligned to Slice 51.
- [x] DB: add table to store pending policy approval requests.
- [x] Server: agent-auth endpoint to propose a policy approval request; endpoints to approve/deny:
  - Telegram callback via agent-auth (OpenClaw inline button) and
  - Web management action via management cookie.
- [x] Web UI: `/agents/:id` shows pending policy approval requests with Approve/Deny buttons.
- [x] OpenClaw patch: auto-attach Approve/Deny buttons to the queued approval message and route decisions into agent pipeline (like trade approvals).
- [x] Runtime/skill: add CLI surface to create policy approval requests so the agent can trigger them.
- [x] required gates pass: `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, runtime tests.

---

## Slice 52: Policy Approval Prompts (Agent-Ready queuedMessage + Instructions)
Status: [x]
Issue: #42 (umbrella)

Goal:
- When the agent requests a policy approval (preapprove token / approve-all), the runtime must return an agent-ready `queuedMessage` template containing the exact `Status: approval_pending` + `Approval ID: ppr_...` lines so:
  - the agent can paste it verbatim to the user, and
  - Telegram queued-message button auto-attach is reliable.

DoD:
- [x] docs sync first: source-of-truth + roadmap + tracker + context/spec/tasks/acceptance aligned to Slice 52.
- [x] Runtime: policy approval request commands return:
  - `queuedMessage` (includes `Status: approval_pending` and `Approval ID: ppr_...` verbatim),
  - `agentInstructions` (explicitly tells agent to paste the message verbatim).
- [x] Tests: runtime unit tests assert `queuedMessage` includes the required lines + policyApprovalId.
- [x] required gates pass: `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, runtime tests.

---

## Slice 53: Policy Approval Revokes (Token + Approve All OFF) With Web + Telegram Buttons
Status: [x]
Issue: #42 (umbrella)

Goal:
- Add revoke permission requests to the policy approvals system:
  - revoke a preapproved token, and
  - turn off global approval (Approve all OFF).
- Requests must appear on `/agents/:id` and be actionable via web UI and Telegram inline buttons.

DoD:
- [x] docs sync first: source-of-truth + roadmap + tracker + context/spec/tasks/acceptance aligned to Slice 53.
- [x] Server: support new request types end-to-end (propose + approve/deny applies policy snapshot changes).
- [x] Runtime/skill: add CLI + skill commands for revoke token and revoke global.
- [x] Web UI: policy approval queue displays correct labels for revoke requests.
- [x] required gates pass: `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, runtime tests.

---

## Slice 54: Policy Approval Reliability Fixes (Token Symbols + Agent Event Types)
Status: [x]
Issue: #42 (umbrella)

Goal:
- Make policy approval requests reliable in ops:
  - agent/skill can request policy approvals using canonical token symbols (e.g. `USDC`) as well as 0x addresses, and
  - server can emit policy approval lifecycle events without crashing due to missing `agent_event_type` enum values.

DoD:
- [x] Runtime/skill: policy approval request commands accept canonical token symbols and resolve them to chain token addresses.
- [x] DB: `agent_event_type` includes `policy_approval_pending`, `policy_approved`, `policy_rejected`.
- [x] required gates pass: `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, runtime tests.

---

## Slice 55: Policy Approval De-Dupe (Reuse Pending Request)
Status: [x]
Issue: #42 (umbrella)

Goal:
- When the same policy approval is requested repeatedly (e.g. user says "try again"), do not spam new `ppr_...` requests if an identical request is already `approval_pending`.
- De-dupe rule: reuse an existing `approval_pending` request for the same `(agentId, chainKey, requestType, tokenAddress)` and return that `policyApprovalId`.

DoD:
- [x] docs sync first: source-of-truth + roadmap + tracker + context/spec/tasks/acceptance aligned to Slice 55.
- [x] Server: `/api/v1/agent/policy-approvals/proposed` reuses an existing pending request rather than creating a new one when parameters match.
- [x] DB: add index to support efficient lookup for de-dupe.
- [x] required gates pass: `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, runtime tests.

---

## Slice 56: Trade Proposal Token Address Canonicalization (USDC Preapprove Fix)
Status: [x]
Issue: #42 (umbrella)

Goal:
- Ensure token preapproval (`allowed_tokens`) is honored during `trade spot` proposals by sending canonical token addresses to `POST /api/v1/trades/proposed` instead of symbols, preventing false `approval_pending` trades after USDC preapprove approval.

DoD:
- [x] docs sync first: source-of-truth + roadmap + tracker + context/spec/tasks/acceptance aligned to Slice 56.
- [x] Runtime: `cmd_trade_spot` proposes `tokenIn`/`tokenOut` using resolved canonical addresses.
- [x] Tests: runtime unit coverage proves `trade spot` proposal payload uses addresses (policy-match safe).
- [x] required gates pass: `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, runtime tests.

---

## Slice 57: Trade Execute Symbol Resolution (Prevent ERC20_CALL_FAIL Fallback)
Status: [x]
Issue: #42 (umbrella)

Goal:
- Prevent `trade execute` from failing approved USDC trades with `ERC20_CALL_FAIL` due to hardcoded token fallback behavior when intent payload carries token symbols.

DoD:
- [x] docs sync first: source-of-truth + roadmap + tracker + context/spec/tasks/acceptance aligned to Slice 57.
- [x] Runtime: `cmd_trade_execute` resolves `tokenIn`/`tokenOut` from intent payload to canonical addresses (symbol or 0x address input), with fail-closed error on invalid token fields.
- [x] Tests: runtime unit coverage proves symbol-form intent tokens resolve correctly before approve/swap tx assembly.
- [x] required gates pass: `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, runtime tests.

---

## Slice 58: Trade Spot Re-Quote After Approval Wait (Prevent Stale SLIPPAGE_NET)
Status: [x]
Issue: #42 (umbrella)

Goal:
- Prevent `trade spot` execution from reverting with `SLIPPAGE_NET` due to stale pre-approval quote/minOut values when owner approval is delayed.

DoD:
- [x] docs sync first: source-of-truth + roadmap + tracker + context/spec/tasks/acceptance aligned to Slice 58.
- [x] Runtime: `cmd_trade_spot` recomputes quote + minOut immediately before swap tx assembly (after approval wait resolves).
- [x] Tests: runtime unit coverage proves execution uses post-approval quote for minOut, not the initial proposal-time quote.
- [x] required gates pass: `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, runtime tests.

---

## Slice 59: Trade Execute Amount Units Fix (Prevent 50 -> 50 Wei)
Status: [x]
Issue: #42 (umbrella)

Goal:
- Prevent `trade execute` from misreading human `amountIn` strings (e.g. `"50"`) as base units (`50 wei`), which can force near-zero output and deterministic `SLIPPAGE_NET` reverts.

DoD:
- [x] docs sync first: source-of-truth + roadmap + tracker + context/spec/tasks/acceptance aligned to Slice 59.
- [x] Runtime: `cmd_trade_execute` converts `amountIn` from human units using tokenIn decimals before approve/swap calldata construction.
- [x] Tests: runtime unit coverage proves symbol-form execute path uses decimal-scaled amount units (e.g. `5` => `5e18` for 18-decimals token).
- [x] required gates pass: `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, runtime tests.

---

## Slice 60: Prompt Normalization for USD Stablecoin + ETH->WETH Semantics
Status: [x]
Issue: #42 (umbrella)

Goal:
- Ensure prompt/skill contract interprets natural language trade intent consistently:
  - `$` means stablecoin-denominated amount,
  - `ETH` trade intent maps to `WETH`,
  - disambiguation occurs when multiple stablecoins are available.

DoD:
- [x] docs sync first: source-of-truth + roadmap + tracker + context/spec/tasks/acceptance aligned to Slice 60.
- [x] Source-of-truth and skill docs explicitly lock USD/stablecoin + ETH/WETH interpretation behavior.
- [x] Skill command reference includes the disambiguation rule when multiple stablecoins have non-zero balance.
- [x] required gates pass: `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, runtime tests.

---

## Slice 61: Channel-Aware Approval Routing (Telegram vs Web Management Link)
Status: [x]
Issue: #42 (umbrella)

Goal:
- Ensure the agent routes approval UX by active channel:
  - Telegram-focused chats use Telegram inline approval buttons,
  - non-Telegram chats must use `xclaw.trade` web approvals via management link and must not emit Telegram button directives.

DoD:
- [x] docs sync first: source-of-truth + roadmap + tracker + context/spec/tasks/acceptance aligned to Slice 61.
- [x] Source-of-truth locks non-Telegram rule: no Telegram buttons/callback instructions outside Telegram-focused chat.
- [x] Skill docs require `owner-link` handoff to web approval when channel is non-Telegram.
- [x] required gates pass: `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, runtime tests.

---

## Slice 62: Policy Approval Telegram Decision Feedback Reliability
Status: [x]
Issue: #42 (umbrella)

Goal:
- Ensure clicking Telegram Approve/Deny on policy approvals always yields visible user feedback in chat, even when agent decision-routing pipeline is silent.

DoD:
- [x] docs sync first: source-of-truth + roadmap + tracker + context/spec/tasks/acceptance aligned to Slice 62.
- [x] OpenClaw gateway callback patch emits deterministic policy decision confirmation message on successful callback (`xpol`) before/alongside agent decision routing.
- [x] Gateway patch normalization/versioning upgrades existing installs to include the reliability behavior.
- [x] required gates pass: `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, runtime tests.

---

## Slice 63: Prompt Contract - Hide Internal Commands In User Replies
Status: [x]
Issue: #42 (umbrella)

Goal:
- Prevent the agent from exposing internal wrapper/CLI command strings in user-facing chat by default.
- Keep command syntax available only when the user explicitly asks for commands.

DoD:
- [x] docs sync first: source-of-truth + roadmap + tracker + context/spec/tasks/acceptance aligned to Slice 63.
- [x] Source-of-truth locks user-facing response contract: no internal tool-call command strings unless explicitly requested.
- [x] Skill docs/command reference lock the same behavior for runtime prompt guidance.
- [x] required gates pass: `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, runtime tests.

---

## Slice 64: Policy Callback Convergence Ack (409 Still Replies)
Status: [x]
Issue: #42 (umbrella)

Goal:
- Ensure policy approval Telegram callbacks still send visible confirmation when server returns converged/idempotent `409` terminal status (`approved`/`rejected`/`filled`), instead of silently deleting buttons only.

DoD:
- [x] docs sync first: source-of-truth + roadmap + tracker + context/spec/tasks/acceptance aligned to Slice 64.
- [x] OpenClaw gateway patch handles `409` terminal callback responses for `xpol` by clearing inline buttons (preserving text) and sending deterministic confirmation message.
- [x] Gateway patch versioning/normalization upgrades existing patched bundles to include convergence-ack behavior.
- [x] required gates pass: `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, runtime tests.

---

## Slice 65: Telegram Decision UX - Keep Text, Remove Buttons
Status: [x]
Issue: #42 (umbrella)

Goal:
- On Telegram approve/deny callbacks, preserve the queued message text in chat history and remove only inline buttons.

DoD:
- [x] docs sync first: source-of-truth + roadmap + tracker + context/spec/tasks/acceptance aligned to Slice 65.
- [x] OpenClaw gateway callback success path (`xappr`/`xpol`) clears inline keyboard instead of deleting the message.
- [x] OpenClaw gateway callback converged `409` path clears inline keyboard instead of deleting the message.
- [x] Gateway patch versioning/normalization upgrades existing patched bundles to include this UX behavior.
- [x] required gates pass: `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, runtime tests.

---

## Slice 66: Policy Approval Consistency (Pending De-Dupe Race + Web Reflection)
Status: [x]
Issue: #42 (umbrella)

Goal:
- Prevent duplicate pending policy approval requests under concurrent retries and ensure policy approve/deny outcomes are reflected in `/agents/:id` management view without manual refresh.

DoD:
- [x] docs sync first: source-of-truth + roadmap + tracker + context/spec/tasks/acceptance aligned to Slice 66.
- [x] Server: `/api/v1/agent/policy-approvals/proposed` de-dupe is transaction-safe under concurrency.
- [x] Web: `/agents/:id` management view auto-refreshes state so token/global policy approvals/denials from Telegram/web are visible promptly.
- [x] required gates pass: `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, runtime tests.

---

## Slice 67: Approval Decision Feedback + Activity Visibility Reliability
Status: [x]
Issue: #42 (umbrella)

Goal:
- Ensure every Telegram approve/deny callback (trade or policy) emits a visible confirmation message.
- Ensure `/agents/:id` activity reflects policy lifecycle events (`policy_*`) in addition to trade events.

DoD:
- [x] docs sync first: source-of-truth + roadmap + tracker + context/spec/tasks/acceptance aligned to Slice 67.
- [x] OpenClaw callback patch emits deterministic confirmation for both `xappr` and `xpol` success/converged terminal responses.
- [x] Public activity endpoint includes `policy_*` lifecycle events with token-address resolution for display.
- [x] `/agents/:id` activity rendering labels policy lifecycle events clearly.
- [x] required gates pass: `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, runtime tests.

---

## Slice 68: Management Policy Approval History Visibility
Status: [x]
Issue: #42 (umbrella)

Goal:
- Ensure `/agents/:id` clearly shows that policy approval requests existed and how they resolved (approved/rejected), not only pending queue items.

DoD:
- [x] docs sync first: source-of-truth + roadmap + tracker + context/spec/tasks/acceptance aligned to Slice 68.
- [x] management agent-state API returns recent policy approval history (status + timestamps + reason).
- [x] `/agents/:id` Policy Approvals card renders recent policy request history below pending queue.
- [x] required gates pass: `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, runtime tests.

---

## Slice 69: Dashboard Full Rebuild (Global Landing Analytics + Discovery)
Status: [!]
Issue: #69 (to be created / mapped)

Goal:
- Rebuild `/` dashboard from scratch as a wallet-like analytics and discovery terminal (not trading UI), with a new dashboard shell (sidebar + sticky topbar), full mobile ordering, and dark/light parity.

DoD:
- [x] docs sync first: source-of-truth + roadmap + tracker + context/spec/tasks/acceptance aligned to Slice 69.
- [x] `/` and `/dashboard` both render the new dashboard layout and behavior.
- [x] dashboard shell is route-scoped (`/`, `/dashboard`) and does not regress non-dashboard pages.
- [x] owner-only scope selector (`All agents` / `My agents`) appears only when owner session context exists.
- [x] dashboard chain selector supports `All chains`, `Base Sepolia`, `Hardhat Local` and consistently filters dashboard data.
- [x] KPI strip, chain/system chart panel (view switcher + time range), live feed, top agents, chain breakdown, trade snapshot, trending cards, and docs card are present with loading/empty/error handling.
- [x] `GET /api/v1/public/dashboard/summary` provides dashboard KPIs, range chart series, and chain breakdown with zero-state enabled-chain rows.
- [x] unsupported metrics (fees/slippage/health internals) are visibly labeled as estimated/derived where exact API data is unavailable.
- [x] dark/light theme tokens for dashboard match locked palette and remain readable.
- [x] required gates pass: `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`.

Blocker:
- Issue mapping + completion evidence post is pending (`Issue: #69` not created/mapped in-session yet).

---

## Slice 69A: Dashboard Agent Trade Room Reintegration
Status: [!]
Issue: #69A (to be created / mapped)

Goal:
- Reintroduce Agent Trade Room on dashboard right rail with visual parity and compact read-only preview, plus full-room `View all` route.

DoD:
- [x] docs sync first: source-of-truth + roadmap + tracker + context/spec/tasks/acceptance aligned to Slice 69A.
- [x] dashboard right rail includes Agent Trade Room card directly below Live Trade Feed.
- [x] room card uses read-only compact preview (max 8), chat-style rows, and tags.
- [x] room card applies same chain and owner scope filters as dashboard.
- [x] room card loading/empty/error states are card-scoped.
- [x] `View all` routes to `/room` read-only room page.
- [x] required gates pass: `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`.

Blocker:
- Issue mapping + completion evidence post is pending (`Issue: #69A` not created/mapped in-session yet).

---

## Slice 70: Single-Trigger Spot Flow + Guaranteed Final Result Reporting
Status: [!]
Issue: #70 (to be created / mapped)

Goal:
- Make Telegram-focused `trade spot` one-trigger:
  - if approval is needed, owner approves/denies via Telegram buttons,
  - approve auto-resumes execution without a second human message,
  - final trade outcome is always sent to the same chat and routed into the agent message pipeline.
- Limit-order behavior remains unchanged.

DoD:
- [x] docs sync first: source-of-truth + roadmap + tracker + context/spec/tasks/acceptance aligned to Slice 70.
- [x] Runtime: persist pending spot-flow context for approval-pending `trade spot` and expose deterministic `approvals resume-spot`.
- [x] Gateway patch: on `xappr approve`, trigger guarded async `resume-spot`, emit deterministic final trade result chat message, and route synthetic final-result message to agent pipeline.
- [x] Duplicate callback safety: no double execution trigger for repeated approve callbacks on the same trade.
- [x] required gates pass: `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, runtime tests.

Blocker:
- Issue mapping + completion evidence post is pending (`Issue: #70` not created/mapped in-session yet).

---

## Slice 71: Single-Trigger Outbound Transfers + Runtime-Canonical Transfer Approvals
Status: [!]
Issue: #71 (to be created / mapped)

Goal:
- Make `wallet-send` and `wallet-send-token` one-trigger for Telegram-focused chats using runtime-canonical transfer approvals (`xfr_...`) with deterministic approve/deny callback handling and guaranteed final result reporting.

DoD:
- [x] docs sync first: source-of-truth + roadmap + tracker + context/spec/tasks/acceptance aligned to Slice 71.
- [x] Runtime: local transfer approval state (`pending-transfer-flows.json`) + local transfer approval policy (`transfer-policy.json`) + deterministic commands:
  - `approvals decide-transfer`
  - `approvals resume-transfer`
  - `transfers policy-get`
  - `transfers policy-set`
- [x] Runtime: `wallet-send` and `wallet-send-token` orchestrate approval-required path with `queuedMessage` (`Approval ID: xfr_...`, `Status: approval_pending`) and auto execution when policy allows.
- [x] Gateway patch: support `xfer|a|...` / `xfer|r|...` callbacks, trigger runtime decide-transfer, emit deterministic transfer result, and route synthetic transfer-result message to agent pipeline.
- [x] Web/API: add transfer-approval mirror + management queue/decision endpoints and transfer-policy update/get mirror endpoints.
- [x] `/agents/:id` management view: transfer approval policy controls + transfer approvals queue/history with periodic refresh.
- [x] required gates pass: `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, runtime tests.

Blocker:
- Issue mapping + completion evidence post is pending (`Issue: #71` not created/mapped in-session yet).

---

## Slice 72: Transfer Policy-Override Approvals (Keep Gate/Whitelist)
Status: [!]
Issue: #72 (to be created / mapped)

Goal:
- Keep outbound gate + whitelist controls but route policy-blocked transfer intents to `xfr_...` Approve/Deny instead of immediate hard-fail.

DoD:
- [x] Runtime evaluates outbound policy without hard-failing transfer orchestration (`chain_disabled` still hard-fails).
- [x] Policy-blocked transfers create `approval_pending` with policy-block metadata.
- [x] Approve executes one-off override (`executionMode=policy_override`) without policy mutation.
- [x] Deny remains terminal rejected with deterministic refusal context.
- [x] Mirror/API/UI include policy-block metadata and override mode indicators.
- [x] required gates pass: `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, runtime tests.

---

## Slice 73: Agent Page Full Frontend Refresh (Dashboard-Aligned, API-Preserving)
Status: [!]
Issue: #26

Goal:
- Rebuild `/agents/:id` as a dashboard-aligned wallet console while preserving existing backend contracts and owner/viewer access boundaries.

DoD:
- [x] docs sync first: source-of-truth + roadmap + tracker + context/spec/tasks/acceptance aligned to Slice 73.
- [x] `/agents/:id` is direct-replaced with sidebar-preserved wallet-native layout, compact KPI chips, and single continuous wallet workspace.
- [x] existing APIs remain unchanged; owner operations continue using existing management routes.
- [x] unsupported API surfaces render explicit placeholders/disabled controls (no speculative backend changes).
- [x] viewer mode hides owner-only controls while preserving public profile observability.
- [x] secondary operations / transfer policy editor surfaces are removed from `/agents/:id`; transfer approval actions/history remain visible in approvals modules.
- [x] dark/light themes remain supported with dark default.
- [x] canonical status vocabulary remains unchanged (`active`, `offline`, `degraded`, `paused`, `deactivated`).
- [x] required gates pass: `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`.

Blocker:
- Dark/light parity screenshots at desktop breakpoints are pending capture + attachment in issue evidence post.

---

## Slice 74: Approvals Center v1 (Frontend-Only, API-Preserving)
Status: [!]
Issue: #74 (to be created / mapped)

Goal:
- Add `/approvals` as a dashboard-aligned approvals inbox that reuses existing management APIs, with explicit placeholder modules for unsupported cross-agent aggregation and allowances inventory.

DoD:
- [x] docs sync first: source-of-truth + roadmap + tracker + context/spec/tasks/acceptance aligned to Slice 74.
- [x] `/approvals` route implemented with dashboard-aligned shell, summary strip, requests inbox, and allowances placeholder panel.
- [x] owner/viewer separation enforced:
  - [x] no-management-session users see empty state with guidance.
  - [x] owner session users can execute existing approval decisions.
- [x] existing endpoints reused as-is:
  - [x] `GET /api/v1/management/session/agents`
  - [x] `GET /api/v1/management/agent-state`
  - [x] `POST /api/v1/management/approvals/decision`
  - [x] `POST /api/v1/management/policy-approvals/decision`
  - [x] `POST /api/v1/management/transfer-approvals/decision`
- [x] unsupported surfaces are explicit placeholders with disabled actions:
  - [x] cross-agent aggregation
  - [x] full allowances inventory
  - [x] risk-chip enrichment/bulk actions
- [x] dark/light theme support preserved with dark default.
- [x] required gates pass: `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`.

Blocker:
- Issue mapping + evidence post for Slice 74 is pending (`Issue: #74` to be created/mapped in-session).

---

## Slice 75: Settings & Security v1 (`/settings`) Frontend Refresh
Status: [!]
Issue: #27

Goal:
- Implement `/settings` as a dashboard-aligned Settings & Security page while preserving existing APIs and keeping `/status` as diagnostics.

DoD:
- [x] docs sync first: source-of-truth + roadmap + tracker + context/spec/tasks/acceptance aligned to Slice 75.
- [x] add `/settings` route with tabs: Access, Security, Danger Zone.
- [x] preserve `/status` route as Public Status diagnostics surface.
- [x] owner/session controls reuse existing endpoints:
  - [x] `GET /api/v1/management/session/agents`
  - [x] `POST /api/v1/management/session/select`
  - [x] `POST /api/v1/management/logout`
  - [x] `POST /api/v1/management/pause`
  - [x] `POST /api/v1/management/resume`
  - [x] `POST /api/v1/management/revoke-all`
- [x] unsupported modules are explicit placeholders with disabled actions:
  - [x] verified cross-agent access inventory
  - [x] global panic actions across all owned agents in one operation
  - [x] full on-chain allowance inventory/revoke sweep from settings
- [x] dashboard/agents/approvals nav routes point Settings & Security to `/settings`.
- [x] dark/light support preserved (dark default) and desktop overflow guarded.
- [x] required gates pass: `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`.

Blocker:
- Desktop dark/light screenshots for `/settings` are pending capture + attachment in issue evidence.

---

## Slice 76: Explore / Agent Listing Full Frontend Refresh (`/explore` Canonical)
Status: [!]
Issue: #28

Goal:
- Rebuild Explore as the canonical `/explore` route with dashboard-aligned layout, while keeping `/agents` as compatibility path and preserving existing backend contracts.

DoD:
- [x] docs sync first: source-of-truth + roadmap + tracker + context/spec/tasks/acceptance aligned to Slice 76.
- [x] new canonical Explore page at `/explore` with sections:
  - [x] My Agents (owner-only),
  - [x] Favorites (device-local),
  - [x] All Agents (directory + pagination).
- [x] `/agents` kept as compatibility alias to Explore.
- [x] existing APIs reused as-is for available features:
  - [x] `GET /api/v1/public/agents`
  - [x] `GET /api/v1/public/leaderboard`
  - [x] `GET /api/v1/management/session/agents`
  - [x] `GET /api/v1/copy/subscriptions`
  - [x] `POST /api/v1/copy/subscriptions`
  - [x] `PATCH /api/v1/copy/subscriptions/:subscriptionId`
  - [x] `DELETE /api/v1/copy/subscriptions/:subscriptionId`
- [x] copy-trade CTA behavior:
  - [x] owner: modal + save flow wired
  - [x] viewer: disabled/gated copy with explicit messaging
- [x] unsupported dimensions render explicit placeholders/disabled controls:
  - [x] strategy/risk/venue enriched filters
  - [x] advanced filters drawer
  - [x] follower-rich metadata badges
- [x] dashboard/agent/approvals/settings nav routes point Explore to `/explore`.
- [x] dark/light support preserved with desktop overflow protection.
- [x] required gates pass: `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`.

Blocker:
- Desktop dark/light screenshots for `/explore` still pending attachment in issue #28.

---

## Slice 77: Agent Wallet Page MetaMask-Style Full-Screen Refactor (`/agents/:id`)
Status: [!]
Issue: pending mapping (legacy placeholder)

Goal:
- Reframe `/agents/:id` as a MetaMask-style full-screen wallet experience, remove transfer/outbound policy editor clutter, and preserve existing owner/viewer controls and API contracts.

DoD:
- [x] docs sync first: source-of-truth + roadmap + tracker + context/spec/tasks/acceptance aligned to Slice 77.
- [x] `/agents/:id` preserves the left sidebar shell and keeps chain selector + per-agent chain trading toggle + theme in compact utility bar.
- [x] wallet-first module order present: header + compact KPI chips + assets/approvals + activity + approval history + withdraw + copy + limit orders + audit.
- [x] `Secondary Operations` section removed.
- [x] transfer/outbound policy editor controls removed from `/agents/:id` while transfer approval actions/history remain in approvals surfaces.
- [x] copy relationships on `/agents/:id` remain list/delete only with create flow guidance to `/explore`.
- [x] light/dark support preserved and responsive overflow remains safe.
- [x] required gates pass: `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`.

Blocker:
- Issue mapping and screenshot evidence post pending.

---

## Slice 78: Root Landing Refactor + Install-First Onboarding (`/`)
Status: [x]
Issue: pending mapping

Goal:
- Replace root `/` dashboard rendering with a premium marketing/info landing page that prioritizes onboarding, while preserving dashboard operations on `/dashboard`.

DoD:
- [x] docs sync first: source-of-truth + roadmap + tracker aligned to Slice 78 contract.
- [x] `/` renders trust-first landing content (finished header, hero + live console preview, proof band, capability/lifecycle/trust/developer/FAQ/final-CTA sections) and does not render dashboard analytics modules.
- [x] onboarding module supports `Human`/`Agent` selector:
  - [x] `Human` shows copyable `curl -fsSL https://xclaw.trade/skill-install.sh | bash`.
  - [x] `Human` includes Windows one-liner `irm https://xclaw.trade/skill-install.ps1 | iex`.
  - [x] `Agent` shows copyable prompt `Please follow directions at https://xclaw.trade/skill.md`.
- [x] landing header/nav uses section anchors + CTA pair, with utility links to existing status/explorer routes.
- [x] live proof band values are derived from existing public/status APIs and fail gracefully when unavailable.
- [x] no backend/API/schema changes introduced.
- [x] required gates pass: `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, then `pm2 restart all` sequentially.

Blocker:
- Issue mapping and screenshot evidence post pending.

---

## Slice 79: Agent-Skill x402 Send/Receive Runtime (No Webapp Integration Yet)
Status: [x]
Issue: #29

Goal:
- Add Python-first x402 receive/pay runtime + skill command surface with runtime-canonical payment approvals (`xfr_...`) and Cloudflare tunnel bootstrap, without integrating network-web APIs in this slice.

DoD:
- [x] docs sync first: source-of-truth + roadmap + tracker + wallet command contract + context/spec/tasks/acceptance aligned to Slice 79.
- [x] runtime adds x402 command group:
  - [x] `x402 serve-start|serve-status|serve-stop`
  - [x] `x402 pay|pay-resume|pay-decide`
  - [x] `x402 policy-get|policy-set`
  - [x] `x402 networks`
- [x] x402 pay approval lifecycle uses deterministic `xfr_...` IDs and statuses:
  - [x] `proposed|approval_pending|approved|rejected|executing|filled|failed`
- [x] local x402 state files implemented:
  - [x] `~/.xclaw-agent/x402-runtime.json`
  - [x] `~/.xclaw-agent/pending-x402-pay-flows.json`
- [x] local x402 policy file implemented:
  - [x] `~/.xclaw-agent/x402-policy.json` (`auto|per_payment`, max amount, host allowlist)
- [x] cloudflared tunnel manager implemented and installer ensures cloudflared availability (Linux/macOS/Windows paths).
- [x] skill wrapper adds:
  - [x] `x402-serve-start|x402-serve-status|x402-serve-stop`
  - [x] `x402-pay|x402-pay-resume|x402-pay-decide`
  - [x] `x402-policy-get|x402-policy-set`
  - [x] `x402-networks`
  - [x] `request-x402-payment` auto-start shortcut returning `paymentUrl/network/facilitator/amount/expiresAt`
- [x] x402 network config artifact added with:
  - [x] enabled: `base_sepolia`, `base`
  - [x] disabled by default: `kite_ai_testnet`, `kite_ai_mainnet`
- [x] required gates pass: `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, runtime tests.

---

## Slice 80: Hosted x402 on `/agents/[agentId]` + Agent-Originated Send + Loopback Self-Pay
Status: [x]
Issue: #31

Goal:
- Add hosted x402 receive endpoints in network-web and merge x402 send/receive visibility into `/agents/[agentId]` while keeping outbound x402 execution agent-originated.

DoD:
- [x] Add server x402 read model table + indexes (`agent_x402_payment_mirror`) and extend `agent_transfer_approval_mirror` with x402 metadata/source fields.
- [x] Add API routes:
  - [x] `POST /api/v1/agent/x402/outbound/proposed`
  - [x] `POST /api/v1/agent/x402/outbound/mirror`
  - [x] `POST /api/v1/agent/x402/inbound/mirror`
  - [x] `GET /api/v1/management/x402/payments`
  - [x] `GET /api/v1/management/x402/receive-link`
  - [x] `GET|POST /api/v1/x402/pay/{agentId}/{linkToken}`
- [x] Extend transfer-approval mirror and management transfer approval read/decision flows for `approval_source=x402`.
- [x] Runtime mirrors outbound x402 lifecycle into server and supports x402 approvals through transfer decision path (`xfr_...` IDs).
- [x] `/agents/[agentId]` wallet timeline includes x402 entries with source badge and receive-link panel.
- [x] Loopback self-pay path (agent pays own hosted endpoint) records both inbound and outbound history rows.
- [x] Hosted receive flow supersedes local tunnel serve path in skill/runtime (`request-x402-payment` hosted-only; no cloudflared dependency).
- [x] Source-of-truth, roadmap, OpenAPI, schema, and command contract are synced.
- [x] Required validation gates pass.

---

## Slice 81: Explore v2 Full Flush (No Placeholders)
Status: [x]
Issue: #30

Goal:
- Deliver full-stack Explore v2 by removing placeholder controls/messages and implementing DB-backed strategy/risk/venue metadata with server-driven filtering/sorting/pagination.

DoD:
- [x] docs sync first: source-of-truth + roadmap + tracker + context/spec/tasks/acceptance aligned to Slice 81.
- [x] add migration `0018_slice81_explore_v2.sql` with `agent_explore_profile` + constraints/indexes.
- [x] extend `GET /api/v1/public/agents` with enriched filters and response fields (`exploreProfile`, `verified`, `followerMeta`) and server-driven filtering/sorting/pagination.
- [x] extend `GET /api/v1/public/leaderboard` with `verified` + `exploreProfile` fields.
- [x] add owner-managed metadata APIs:
  - [x] `GET /api/v1/management/explore-profile?agentId=...`
  - [x] `PUT /api/v1/management/explore-profile`
- [x] remove Explore placeholder controls/messages and add:
  - [x] functional strategy/venue/risk filters,
  - [x] functional advanced filter drawer,
  - [x] verified badges + follower-rich metadata,
  - [x] URL-state sync for filter/query/sort/window/page/section.
- [x] keep `/explore` canonical and `/agents` alias behavior unchanged.
- [x] update OpenAPI + shared schemas for new/extended contracts.
- [x] required validation gates pass: `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, `pm2 restart all` (sequential).

---

## Slice 82: Track-Not-Copy Pivot (Saved Agents -> OpenClaw Watchlist)
Status: [x]
Issue: #32

Goal:
- Pivot product surfaces from copy trading to tracked-agent monitoring with server-backed tracked relations per managed agent.

DoD:
- [x] docs sync first: source-of-truth + roadmap + tracker + wallet contract + context/spec/tasks/acceptance aligned to Slice 82.
- [x] migration adds `agent_tracked_agents` with uniqueness and self-track guard.
- [x] management tracked APIs implemented:
  - [x] `GET/POST/DELETE /api/v1/management/tracked-agents`
  - [x] `GET /api/v1/management/tracked-trades`
- [x] agent runtime tracked APIs implemented:
  - [x] `GET /api/v1/agent/tracked-agents`
  - [x] `GET /api/v1/agent/tracked-trades`
- [x] `GET /api/v1/management/agent-state` extended with `trackedAgents` + `trackedRecentTrades`.
- [x] Explore product surface uses `Track Agent` action and removes copy-trade modal/CTA.
- [x] `/agents/[agentId]` uses tracked-agents module (list/remove + recent tracked filled trades) and removes copy-subscription module.
- [x] left rail saved icons sync with server tracked agents for owner sessions; localStorage remains fallback when no session.
- [x] runtime `dashboard` includes tracked summary; runtime CLI adds `tracked list` and `tracked trades`; skill wrapper adds `tracked-list` and `tracked-trades`.
- [x] copy subscription APIs remain available but are marked deprecated in OpenAPI for transition compatibility.
- [x] required gates pass: `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, `pm2 restart all` (sequential), runtime tracked tests.

---

## Slice 83: Kite AI Testnet Parity (Runtime + Web + DEX + x402)
Status: [x]
Issue: #33

Goal:
- Add `kite_ai_testnet` as a first-class chain option across runtime + web with DEX/x402 parity while preserving existing Base Sepolia behavior.

DoD:
- [x] docs sync first: source-of-truth + roadmap + tracker + wallet contract + context/spec/tasks/acceptance aligned to Slice 83.
- [x] lock chain/config constants for `kite_ai_testnet` (`chainId=2368`, rpc/explorer, router/factory, canonical tokens).
- [x] runtime adds DEX adapter selection for Kite (`KiteTesseractAdapter`) and keeps Base path under existing router adapter semantics.
- [x] runtime/skill chain surfaces support `--chain kite_ai_testnet` for wallet/trade/limit/tracked/x402 command families.
- [x] x402 config enables `kite_ai_testnet` with facilitator `https://facilitator.pieverse.io` (`/v2/verify`, `/v2/settle`), while keeping `kite_ai_mainnet` disabled.
- [x] web chain selectors include `Kite AI Testnet` across dashboard/explore/approvals/agents/status.
- [x] management/public API chain validation and action hints include `kite_ai_testnet`.
- [x] Base-only faucet behavior preserved with structured unsupported response for Kite.
- [x] required gates pass: `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, `pm2 restart all` (sequential), plus runtime Kite/x402 tests.

---

## Slice 84: Multi-Network Faucet Parity (Base Sepolia + Kite Testnet)
Status: [x]
Issue: #34

Goal:
- Extend faucet flows so agents can request assets on both Base Sepolia and Kite AI testnet with explicit per-request asset selection.

DoD:
- [x] docs sync first: source-of-truth + roadmap + tracker + wallet contract + context/spec/tasks/acceptance aligned to Slice 84.
- [x] `POST /api/v1/agent/faucet/request` supports `chainKey=base_sepolia|kite_ai_testnet|hedera_testnet` and `assets[]` (`native|wrapped|stable`).
- [x] faucet request resolves canonical wrapped/stable tokens from chain config and emits chain-canonical symbols (`ETH/WETH/USDC`, `KITE/WKITE/USDT`, `HBAR/WHBAR/(USDC|USDT via config/env)`).
- [x] per-agent per-chain daily limiter behavior retained.
- [x] new `GET /api/v1/agent/faucet/networks` returns supported networks + asset capability metadata.
- [x] runtime CLI adds `faucet-networks` and extends `faucet-request --asset ...`.
- [x] skill wrapper adds `faucet-networks` and supports optional `faucet-request [chain] [asset ...]`.
- [x] required gates pass: runtime tests, `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, `pm2 restart all` (sequential).

---

## Slice 85: EVM-Wide Portability Foundation (Chain-Agnostic Core, x402 Unchanged)
Status: [x]
Issue: #35

Goal:
- Make chain plumbing config-driven and capability-gated so adding EVM chains is data/config work, while preserving x402 scope boundaries.

DoD:
- [x] docs sync first: source-of-truth + roadmap + tracker + wallet contract + context/spec/tasks/acceptance aligned to Slice 85.
- [x] chain config contract extended with `family`, `enabled`, `uiVisible`, `nativeCurrency`, and `capabilities`.
- [x] new migration adds `chain_token_metadata_cache` for symbol/name/decimals cache with resolve status.
- [x] new `GET /api/v1/public/chains` returns enabled chain registry + capabilities.
- [x] web chain selectors load chain options from public chain registry (with local fallback cache).
- [x] runtime adds chain registry command (`xclaw-agent chains --json`) and capability enforcement.
- [x] faucet and chain validation paths consume config/capability model instead of hardcoded chain lists.
- [x] management agent-state chain token rows include optional resolved metadata (`name`, `decimals`, `source`, `tokenDisplay`).
- [x] x402 scope remains unchanged and chain-gated by capability.

---

## Slice 86: Multi-Agent Management Session + Chain-Scoped Trade Policy Snapshots
Status: [x]
Issue: #33

Goal:
- Expand management-session authorization to support multiple managed agents per cookie session, and harden `agent_policy_snapshots` reads/writes to chain-scoped behavior.

DoD:
- [~] migration adds `management_session_agents` and backfills existing session->agent bindings.
- [~] management auth loads authorized `managedAgentIds` for active session.
- [~] bootstrap supports linking additional agent token access into existing session.
- [~] `GET /api/v1/management/session/agents` returns linked managed agents from session bindings.
- [~] migration adds `agent_policy_snapshots.chain_key` with backfill default `base_sepolia`.
- [~] policy snapshot writes include `chain_key`; chain-key fallback reads removed from management views.

## Slice 87: Approvals Center Core APIs + Permission Inventory
Status: [x]
Issue: #34

Goal:
- Make `/approvals` fully functional for approve+allowlist and permission-native inventory while preserving existing approval decision routes.

DoD:
- [~] add `POST /api/v1/management/approvals/approve-allowlist-token` (atomic trade approve + allowlist tokenIn).
- [~] add `GET /api/v1/management/approvals/inbox` unified rows + risk labels + permission inventory.
- [~] add `POST /api/v1/management/permissions/update` for direct permission posture updates.
- [~] `/approvals` uses inbox API and enables `Approve + Allowlist Token`.
- [~] allowances placeholder replaced with permissions inventory module.
- [x] web synthetic prod bridge dispatches trade/transfer decision + terminal notifications with no-deliver dispatch (Telegram-safe by default; optional Telegram guard override).
- [x] transfer Telegram approval prompts are tracked and cleared on approve/deny convergence.
- [x] approval prompt cleanup is runtime-canonical across trade/transfer/policy (`approvals clear-prompt`) and removes inline buttons only (no prompt message delete).
- [x] owner-link direct-send is disabled for Telegram-active channel (button-first approval UX).
- [x] transfer Telegram callback path sends deterministic transfer result and routes synthetic transfer-result envelope to agent pipeline for completion follow-up.
- [x] shell installer capability-gates Telegram gateway patching; permission-denied patch paths auto-degrade to management-link Telegram fallback mode with explicit sudo rerun guidance for inline-button support.

## Slice 88: Approvals Center Full UX Flush (Batch + Risk)
Status: [x]
Issue: #35

Goal:
- Complete approvals UX with deterministic risk context and batched decision operations.

DoD:
- [~] add `POST /api/v1/management/approvals/decision-batch` with per-item outcomes.
- [~] `/approvals` supports multi-select bulk decisions.
- [~] deterministic risk labels rendered in inbox cards.
- [~] copy surface uses “Permissions Inventory” language (no allowances placeholder contract).

## Slice 89: MetaMask-Style Gas Estimation For Agent Wallet Runtime
Status: [x]
Issue: #36

Goal:
- Make runtime-signed wallet/trade transactions use RPC-native, EIP-1559-first fee planning with bounded retry escalation and legacy rollback controls.

DoD:
- [x] `wallet-send`, `wallet-send-token`, and `trade-spot` execution paths share the unified sender fee planner.
- [x] default fee mode uses RPC-native EIP-1559 estimation (`eth_feeHistory` + `eth_maxPriorityFeePerGas`, with reward fallback).
- [x] fallback path uses `eth_gasPrice` when EIP-1559 methods are unavailable/invalid.
- [x] retryable send failures keep nonce policy (RPC-assigned first attempt, deterministic pinned retries) and escalate fees by retry bump.
- [x] env controls added: `XCLAW_TX_FEE_MODE`, `XCLAW_TX_RETRY_BUMP_BPS`, `XCLAW_TX_PRIORITY_FLOOR_GWEI`.
- [x] docs/handoff sync complete in same change (source-of-truth, roadmap, wallet contract, context/spec/tasks/acceptance).
- [x] runtime tests cover EIP-1559 happy path, fallback legacy path, and EIP-1559 cast flag emission.

---

## Slice 90: Liquidity + Multi-DEX Compatibility Foundation
Status: [x]
Issue: #36

Goal:
- Introduce chain-agnostic liquidity contracts and command surfaces aligned with existing trade approval/policy controls.

DoD:
- [x] docs sync first: source-of-truth + roadmap + tracker + wallet contract + commands reference aligned to Slice 90.
- [x] migration adds liquidity core tables: `liquidity_intents`, `liquidity_position_snapshots`, `liquidity_fee_events`, `liquidity_protocol_configs`.
- [x] shared schemas include liquidity proposed/status/position/approval contracts.
- [x] runtime CLI adds `liquidity add/remove/positions/quote-add/quote-remove` with chain capability gating.
- [x] skill wrapper exposes liquidity commands and delegates to runtime.
- [x] chain config capability model includes `capabilities.liquidity` and protocol metadata.
- [x] enabled chain registry drives mainnet+testnet selector options; faucet scope remains capability-gated to testnet chains.
- [x] API adds liquidity endpoints:
  - `POST /api/v1/liquidity/proposed`
  - `POST /api/v1/liquidity/:intentId/status`
  - `GET /api/v1/liquidity/pending`
  - `GET /api/v1/liquidity/positions`
- [x] management `agent-state` includes chain-scoped `liquidityPositions`.
- [x] `/agents/:id` wallet view renders separate Liquidity Positions section for active chain.
- [x] runtime default-chain commands (`default-chain get/set`) establish agent-runtime canonical default chain.
- [x] management endpoints expose default-chain read/update + managed-session batch sync.
- [x] global chain selector persists and synchronizes runtime default chain for all managed agents in active session.
- [x] route-level liquidity API contract tests pass for payload/auth/transition/query validation and idempotency replay semantics.

---

## Slice 91: Runtime Liquidity Intents + Adapter Framework Behavior
Status: [x]
Issue: #37

Goal:
- Enforce full liquidity lifecycle parity with trade approval contracts and deterministic adapter routing by v2/v3 family.

DoD:
- [x] runtime adapter preflight runs before `liquidity add/remove` proposal submission.
- [x] adapter selection uses chain config `liquidityProtocols` and `(chain, dex, position_type)` tuple.
- [x] deterministic runtime errors for unsupported adapters (`unsupported_liquidity_adapter`).
- [x] Hedera HTS adapter fails closed with `missing_dependency` when SDK plugin is missing.
- [x] liquidity command tests cover routing + negative preflight paths.
- [x] docs/handoff sync (`source-of-truth`, roadmap, tracker, wallet contract, spec/tasks/acceptance).

## Slice 92: Wave 1 Protocol Adapters + Hedera HTS Plugin Depth
Status: [x]
Issue: #38

Goal:
- Deliver Wave-1 adapter coverage and runtime fail-closed behavior for HTS-native routes.

DoD:
- [x] Base adapters resolve for `uniswap_v2`, `uniswap_v3`, and `aerodrome` protocol metadata.
- [x] Kite adapters resolve for `tesseract_univ2` with v3 disabled rejection path.
- [x] Hedera adapters resolve for `saucerswap`, `pangolin`, and `hedera_hts` plugin route.
- [x] unsupported/disabled DEX routes return deterministic adapter errors.
- [x] adapter docs and chain-protocol notes synchronized in canonical docs.

## Slice 93: Server APIs + Position Indexing/PnL/Fee Computation
Status: [x]
Issue: #40

Goal:
- Add request-safe liquidity snapshot refresh and strengthen lifecycle/state transition handling.

DoD:
- [x] positions + management reads trigger 60s-cadence fail-soft sync helper.
- [x] terminal liquidity status transitions trigger immediate force refresh.
- [x] filled status path persists optional `feeEvents[]` records to `liquidity_fee_events`.
- [x] transition guard returns liquidity-specific invalid-transition code.
- [x] API contract artifacts and evidence notes synchronized.

## Slice 94: Web Liquidity Positions Section Completion
Status: [x]
Issue: #39

Goal:
- Complete chain-filtered wallet liquidity visibility with stale/freshness indicators.

DoD:
- [x] wallet liquidity rows include chain + dex + pair/pool + v2/v3 type context.
- [x] row copy includes deposited basis/current underlying/fees/PnL/value fields.
- [x] stale indicator rendered when snapshot age exceeds 60s SLA.
- [x] chain-scoped filtering remains bound to active chain selector.
- [x] docs/handoff sync completed.

## Slice 95: Verification + Hardening + Bounty Evidence Packaging
Status: [x]
Issue: #41

Goal:
- Produce verification evidence, harden reliability paths, and update bounty checklist artifacts.

DoD:
- [x] required validation gates rerun with latest liquidity/runtime/web changes.
- [x] hardhat-local lifecycle evidence recorded before external testnet evidence.
- [x] bounty checklist updated with evidence IDs for Hedera/0G/Kite paths.
- [x] Hedera evidence pass captures both EVM (`saucerswap`) and HTS-native (`hedera_hts`) runtime attempts with deterministic outcomes (`policy_denied|approved|missing_dependency`) and explicit rerun blockers.
- [x] runtime adds deterministic Hedera EVM pair discovery utility (`liquidity discover-pairs`) with reserve filtering and failure codes (`liquidity_pair_discovery_failed`, `liquidity_no_viable_pair`).
- [x] runtime auto-executes approved liquidity intents (`liquidity execute/resume`) with lifecycle transitions and deterministic v3 execution reject (`unsupported_liquidity_execution_family`).
- [x] tx-hash-grade Hedera liquidity proof is complete: EVM add/remove tx hashes captured (`E22`,`E23`) and HTS add/remove tx hashes captured (`E29`,`E30`) in runtime flow.
- [x] hosted installer auto-binds `hedera_testnet` wallet context to the portable default wallet key and performs multi-chain register upsert (`default chain` + `hedera_testnet`) with optional Hedera faucet warmup warnings on non-fatal failure.
- [x] Hedera faucet request route now returns deterministic `faucet_*` error contracts (no opaque `internal_error` for known preflight/config/RPC failures).
- [x] Faucet hard-blocks self-recipient sends (`faucet_recipient_not_eligible`) and success payloads include `recipientAddress` + `faucetAddress` provenance fields.
- [x] Official Hedera helper wrap path is available (`wallet wrap-native`) and faucet wrapped-asset deficits can auto-wrap via helper with deterministic `faucet_wrapped_autowrap_failed` fallback.
- [x] Hedera faucet default drips are set to 5 HBAR / 5 WHBAR / 10 USDC for non-demo warmup reliability.
- [x] Ops tooling includes faucet wallet-mapping audit/fix scripts (`ops:faucet:audit-mappings`, `ops:faucet:fix-mapping`) to detect/remediate agent-chain mappings that point to faucet signer addresses.
- [x] installer warmup logs include faucet `code/message/actionHint/requestId` and explicit rerun diagnostics; install remains non-fatal on warmup failure after wallet/register invariants pass.
- [x] Hedera wallet balance visibility includes mirror-node discovered token holdings for the requested chain, so non-canonical owned tokens are surfaced in runtime `tokens[]`.
- [x] Runtime/skill now support user-added token tracking by address (`wallet-track-token`, `wallet-untrack-token`, `wallet-tracked-tokens`), and tracked tokens are included in non-zero holdings + `wallet-send-token` symbol resolution (deterministic `token_symbol_ambiguous` on collisions).
- [x] final docs sync + issue evidence posts with commit hashes.

## Slice 96: Base Sepolia Wallet/Approval E2E Harness (Telegram-Suppressed)
Status: [x]
Issue: #42

Goal:
- Deliver a deterministic Python-first harness that executes real Base Sepolia wallet/approval flows (trade, transfer, liquidity, x402, pause/resume) with Telegram dispatch suppressed for test runs.

DoD:
- [x] runtime env gate `XCLAW_TEST_HARNESS_DISABLE_TELEGRAM` suppresses Telegram prompt/decision sends without affecting approval/execution state transitions.
- [x] add harness entrypoint `apps/agent-runtime/scripts/wallet_approval_harness.py` with management-API approval driver.
- [x] harness supports `--scenario-set smoke|full` and default `full`.
- [x] harness validates tolerance-based end-balance convergence using configurable bps/floor args.
- [x] harness stabilization includes strict hardhat-first gating, wallet decrypt preflight fail-fast, and retry-backed management writes with diagnostics.
- [x] add unit tests for harness planner/tolerance/runtime parsing, retry/preflight behavior, and runtime Telegram suppression behavior.
- [x] docs/handoff sync completed in same change (`source-of-truth`, roadmap, tracker, context/spec/tasks/acceptance).

## Slice 97: Ethereum + Ethereum Sepolia Wallet-First Chain Onboarding
Status: [x]
Issue: #43

Goal:
- Add `ethereum` and `ethereum_sepolia` as first-class chain registry entries, visible in selectors and health probes, with wallet-only capabilities enabled.

DoD:
- [x] docs sync first: source-of-truth + roadmap + tracker + wallet contract + spec/tasks/acceptance aligned to Slice 97 scope.
- [x] add `config/chains/ethereum.json` with validated chain metadata (chain id, rpc, explorer, canonical tokens, wallet-first capabilities).
- [x] add `config/chains/ethereum_sepolia.json` with validated chain metadata (chain id, rpc, explorer, canonical tokens, wallet-first capabilities).
- [x] web chain-selector fallback registry includes `ethereum` + `ethereum_sepolia`.
- [x] status provider probe allowlist includes `ethereum` + `ethereum_sepolia`.
- [x] dashboard chain color map includes deterministic entries for `ethereum` + `ethereum_sepolia`.
- [x] runtime validation evidence captured for `chains --json` and isolated-home wallet create/address/health on both new chains.
- [x] required repo gates rerun sequentially (`db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, `pm2 restart all`).
- [x] issue #43 updated with verification evidence + commit hash(es).

## Slice 98: Chain Metadata Normalization + Truthful Capability Gating
Status: [x]
Issue: #44

Goal:
- Ensure every enabled+visible chain has authoritative metadata (chainId/rpc/explorer/name) and truthful runtime capabilities; hide unresolved placeholders.

DoD:
- [x] docs sync first: source-of-truth + roadmap + tracker + wallet contract + spec/tasks/acceptance aligned to Slice 98 scope.
- [x] ADI mainnet/testnet chain metadata populated (`chainId`, `rpc`, `explorer`, sources, live RPC verification evidence).
- [x] 0G mainnet/testnet chain metadata populated (`chainId`, `rpc`, `explorer`, sources, live RPC verification evidence).
- [x] Kite mainnet chain id corrected to live network (`2366`) and naming normalized.
- [x] Testnet display names normalized to canonical labels (`KiteAI Testnet`, `ADI Network AB Testnet`, `0G Galileo Testnet`, etc.).
- [x] non-integrated networks are wallet-first capability-gated (trade/liquidity/limit/x402/faucet/deposits disabled).
- [x] unresolved Canton placeholder chains are disabled+hidden pending authoritative metadata.
- [x] status provider probing is chain-config-driven for all enabled+visible chains with configured RPC URLs.
- [x] runtime/web validation evidence captured (`chains`, public chains, status providers) reflecting normalized metadata.
- [x] required repo gates rerun sequentially (`db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, `pm2 restart all`).
- [x] issue #44 updated with verification evidence + commit hash(es).

## Slice 99: Installer Multi-Chain Wallet Auto-Bind Hardening
Status: [x]
Issue: #45

Goal:
- Ensure hosted installers bind wallet context across all enabled wallet-capable chains so runtime commands are immediately usable after install.

DoD:
- [x] `/skill-install.sh` discovers runtime chains via `xclaw-agent chains --json` and auto-attempts `wallet create --chain <chain>` for each wallet-capable chain.
- [x] `/skill-install.ps1` mirrors the same wallet-capable chain auto-bind behavior.
- [x] installer register payload upserts deduplicated wallet rows for all successfully bound wallet-capable chains.
- [x] installer keeps bind failures non-fatal per chain and logs deterministic warning output.
- [x] skill wallet commands accept explicit chain override args (chain-optional fallback remains runtime default chain).
- [x] runtime `username-set`/`agent-register` register upsert includes all enabled local wallet bindings (primary requested chain first).
- [x] canonical docs sync (`source-of-truth`, roadmap, tracker, wallet contract, spec/tasks/acceptance).

## Slice 100: Uniswap Proxy-First Trade Execution With Legacy Fallback
Status: [~]
Issue: #46

Goal:
- Route runtime spot/execute trading through server-side Uniswap API proxy for supported chains while preserving deterministic legacy-router fallback behavior.

DoD:
- [x] server-side `XCLAW_UNISWAP_API_KEY` env contract added; runtime/skill do not require or store Uniswap key.
- [x] add agent-auth Uniswap proxy endpoints:
  - `POST /api/v1/agent/trade/uniswap/quote`
  - `POST /api/v1/agent/trade/uniswap/build`
- [x] runtime `trade spot` provider orchestration added:
  - supported chain + proxy success -> `providerUsed=uniswap_api`
  - proxy error -> auto fallback to `legacy_router` (when available)
  - unsupported/missing fallback -> deterministic `no_execution_provider_available`.
- [x] runtime `trade execute` provider orchestration added with same precedence.
- [x] provider provenance surfaced in runtime outputs and status transitions:
  - `providerRequested`
  - `providerUsed`
  - `fallbackUsed`
  - `fallbackReason`
  - `uniswapRouteType`
- [x] `trade-status` schema + route payload now accept/provider-pass-through provenance fields.
- [x] requested chain rollout config added/updated for Uniswap-eligible scope:
  - `ethereum`, `ethereum_sepolia`, `unichain_mainnet`, `bnb_mainnet`, `polygon_mainnet`, `base_mainnet`, `avalanche_mainnet`, `op_mainnet`, `arbitrum_mainnet`, `zksync_mainnet`, `monad_mainnet`.
- [x] runtime unit coverage added for proxy-success and fallback paths.
- [x] required gates run sequentially (`db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, `pm2 restart all`).
- [ ] issue #46 updated with evidence + commit hash(es).

## Slice 101: Dashboard Dexscreener Top Tokens (Chain-Aware, Top 10)
Status: [~]
Issue: #47

Goal:
- Add a dashboard `Top Trending Tokens` section powered by Dexscreener data, filtered by dashboard chain selector (`all` + chain-specific), with 60-second refresh and no placeholder columns.

DoD:
- [x] docs sync first: source-of-truth + roadmap + tracker + openapi + schema + context/spec/tasks/acceptance aligned to Slice 101 scope.
- [x] add public endpoint `GET /api/v1/public/dashboard/trending-tokens` with `chainKey` + `limit` query contract.
- [x] add shared schema `public-dashboard-trending-tokens-response.schema.json` and openapi route reference.
- [x] chain config supports optional `marketData.dexscreenerChainId` mapping and includes:
  - `base_mainnet` + `base_sepolia` -> `base`,
  - `ethereum` + `ethereum_sepolia` -> `ethereum`.
- [x] route resolves selected dashboard chain to mapped Dexscreener chain(s), dedupes token rows, sorts by `volume.h24 desc`, and returns top 10.
- [x] route soft-fails upstream chain fetch errors (non-fatal to endpoint) and includes deterministic warning metadata when upstream data is unavailable.
- [x] route includes 60-second in-memory TTL cache to reduce upstream rate-limit pressure.
- [x] dashboard integrates the new endpoint and refreshes token data every 60 seconds while mounted.
- [x] dashboard chain dropdown updates token rows without extra selector controls.
- [x] table/card rendering includes only columns with available data; section is hidden when selected chain has no mapped/unavailable data.
- [x] required repo gates rerun sequentially (`db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, `pm2 restart all`).
- [ ] issue #47 updated with verification evidence + commit hash(es).

## Slice 102: Uniswap LP Core Integration (Proxy-First + Fallback)
Status: [~]
Issue: #45

Goal:
- Extend Uniswap proxy-first execution from swaps into LP core operations (approve/create/increase/decrease/claim-fees) on repo-supported Uniswap chains, while preserving deterministic fallback behavior.

DoD:
- [x] add server-side Uniswap LP proxy client and agent-auth routes:
  - `POST /api/v1/agent/liquidity/uniswap/approve`
  - `POST /api/v1/agent/liquidity/uniswap/create`
  - `POST /api/v1/agent/liquidity/uniswap/increase`
  - `POST /api/v1/agent/liquidity/uniswap/decrease`
  - `POST /api/v1/agent/liquidity/uniswap/claim-fees`
- [x] runtime LP provider selector added (`liquidityProviders.primary/fallback`) with Uniswap-first behavior.
- [x] `liquidity add/remove/execute` support Uniswap-first execution and fallback to legacy when available.
- [x] runtime adds LP commands:
  - `liquidity increase`
  - `liquidity claim-fees`
- [x] LP provenance fields are surfaced in runtime outputs and persisted in liquidity intent `details`.
- [x] chain rollout applied for repo-supported Uniswap chains:
  - `ethereum`, `ethereum_sepolia`, `unichain_mainnet`, `bnb_mainnet`, `polygon_mainnet`, `base_mainnet`,
  - `avalanche_mainnet`, `op_mainnet`, `arbitrum_mainnet`, `zksync_mainnet`, `monad_mainnet`.
- [x] openapi + schema artifacts updated for LP proxy routes and liquidity status provenance fields.
- [x] required gates rerun sequentially (`db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, `pm2 restart all`).
- [x] issue #45 updated with verification evidence + commit hash(es).

## Slice 103: Uniswap LP Completion (Migrate + Claim Rewards)
Status: [~]
Issue: #46

Goal:
- Complete remaining Uniswap LP operations (`migrate`, `claim_rewards`) using proxy-first runtime execution with deterministic fallback semantics.

DoD:
- [x] add server-side Uniswap LP proxy routes:
  - `POST /api/v1/agent/liquidity/uniswap/migrate`
  - `POST /api/v1/agent/liquidity/uniswap/claim-rewards`
- [x] add request schemas:
  - `uniswap-lp-migrate-request.schema.json`
  - `uniswap-lp-claim-rewards-request.schema.json`
- [x] runtime command additions:
  - `liquidity migrate`
  - `liquidity claim-rewards`
- [x] runtime outputs include provenance fields for new operations.
- [x] liquidity status schema supports `uniswapLpOperation` values `migrate` and `claim_rewards`.
- [x] stage-gated rollout config:
  - `ethereum_sepolia` has `uniswapApi.migrateEnabled=true` and `claimRewardsEnabled=true`
  - mainnet targets set `migrateEnabled=false` and `claimRewardsEnabled=false` pending promotion.
- [x] required gates rerun sequentially (`db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, `pm2 restart all`).
- [x] issue #46 updated with verification evidence + commit hash(es).

## Slice 104: Promote LP Migrate/Claim-Rewards to Target Mainnets
Status: [~]
Issue: #47

Goal:
- Promote Uniswap LP `migrate` and `claim_rewards` from Sepolia-only staging to all repo target chains with agent-first execution and deterministic fail-closed behavior.

DoD:
- [x] Canonical docs/handoff synced for Slice 104 rollout contract.
- [x] Promotion flags set true on:
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
- [x] `ethereum_sepolia` remains enabled for both operations.
- [x] Runtime/proxy behavior unchanged: fail closed deterministically when no execution provider path exists.
- [x] Required gates rerun sequentially (`db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, `pm2 restart all`).
- [x] Issue #47 evidence post + commit hash(es).

## Slice 105: Cross-Chain Liquidity Claims (Fees + Rewards)
Status: [~]
Issue: #48

Goal:
- Implement deterministic cross-chain claim behavior for `liquidity claim-fees` and `liquidity claim-rewards` with Uniswap-first fallback semantics where available.

DoD:
- [x] Runtime claim commands use provider orchestration and deterministic fail-closed behavior.
- [x] Legacy claim operation support checks use config gate + adapter capability.
- [x] Adapter layer exposes `claim_fees` and `claim_rewards` fail-closed defaults.
- [x] Hedera plugin/bridge includes guarded claim action dispatch with fail-closed defaults.
- [x] Chain configs include `liquidityOperations.claimFees.legacyEnabled` and `liquidityOperations.claimRewards.legacyEnabled`.
- [x] claim command outputs include provider provenance fields consistently.
- [x] Required gates rerun sequentially (`db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, `pm2 restart all`).
- [x] Runtime tests pass (`test_liquidity_cli.py`, `test_trade_path.py`).
- [x] Issue #48 evidence post + commit hash(es).

## Slice 106: Full Cross-Chain Functional Parity + Adapter Fallbacks
Status: [~]
Issue: #49

Goal:
- Expand operation-level fallback contracts so active chains have deterministic full-function behavior and Uniswap chains can fallback to adapter-backed paths where configured.

DoD:
- [x] chain config model extended with `tradeOperations` and enriched `liquidityOperations` operation descriptors.
- [x] runtime provider helper model includes operation-aware provider resolution + fallback executor helper.
- [x] claim-fees and claim-rewards use unified fallback helper semantics.
- [x] claim fallback gating checks operation config + adapter capability + reward contract requirements.
- [x] adapter layer includes explicit reward-claim capability metadata.
- [x] wallet-only/disabled chain promotion backlog documented with gate checklist.
- [x] required gates rerun sequentially (`db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, `pm2 restart all`).
- [x] runtime tests pass (`test_liquidity_cli.py`, `test_trade_path.py`).
- [x] issue #49 evidence post + commit hash(es).

## Slice 107: Executable Cross-Chain Parity Completion
Status: [~]
Issue: #50

Goal:
- Promote real executable claim fallbacks where adapters support them, while retaining deterministic fail-closed behavior for unsupported paths.

DoD:
- [x] claim command failure payloads include provider provenance (`providerRequested`, `providerUsed`, `fallbackUsed`, `fallbackReason`).
- [x] Hedera bridge/plugin claim actions are executable (not hard-blocked) and remain deterministic on failure.
- [x] Hedera chain configs promoted for legacy claim execution:
  - `hedera_mainnet`
  - `hedera_testnet`
- [x] Uniswap claim fallback semantics remain unchanged (fallback only when configured and supported).
- [x] required gates rerun sequentially (`db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, `pm2 restart all`).
- [x] runtime tests pass (`test_liquidity_cli.py`, `test_trade_path.py`).
- [ ] issue #50 evidence post + commit hash(es).

## Slice 108: Config-Truth + Runtime Gate Tightening
Status: [~]
Issue: #51

Goal:
- Lock deterministic fallback behavior and provenance across active-chain trade and claim paths.

DoD:
- [x] runtime fallback behavior remains gate-driven (config + capability).
- [x] claim/trade failure payloads include provider provenance details.
- [x] active-chain config operation contracts are explicit and deterministic.
- [x] required gates run sequentially (`db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, `pm2 restart all`).
- [x] runtime tests pass (`test_liquidity_cli.py`, `test_trade_path.py`).
- [ ] issue #51 evidence post + commit hash(es).

## Slice 109: Uniswap-Chain Fallback Promotion
Status: [~]
Issue: #52

Goal:
- Promote fallback only on Uniswap chains with real legacy execution metadata.

DoD:
- [x] validated fallback remains enabled on `ethereum`, `ethereum_sepolia`.
- [x] unsupported Uniswap chains remain explicit fallback-disabled (`legacyEnabled=false`, `adapter=none`).
- [x] forced-primary-failure behavior remains deterministic on non-enabled chains.
- [x] required gates run sequentially.
- [ ] issue #52 evidence post + commit hash(es).

## Slice 110: Non-Uniswap Active Claims Completion
Status: [~]
Issue: #53

Goal:
- Close non-Uniswap active-chain claim behavior as executable-or-deterministic.

DoD:
- [x] Hedera claim legacy execution remains enabled (`hedera_mainnet`, `hedera_testnet`).
- [x] non-integrated chains preserve deterministic claim error contract (no synthetic success).
- [x] required gates run sequentially.
- [x] runtime tests pass.
- [ ] issue #53 evidence post + commit hash(es).

## Slice 111: Active-Chain Parity Evidence Matrix
Status: [~]
Issue: #54

Goal:
- Publish canonical active-chain parity matrix and close 108-111 evidence trail.

DoD:
- [x] matrix added to `acceptance.md` with per-chain operation/provider truth.
- [x] canonical docs/handoff sync completed for 108-111.
- [x] required gates run sequentially.
- [ ] issue #54 evidence post + commit hash(es).

## Slice 107 Hotfix A: Base ERC-8021 Builder Code Attribution
Status: [~]
Issue: #50

Goal:
- Enforce ERC-8021 builder code attribution for Base transaction send paths with deterministic env-based config and runtime output metadata.

DoD:
- [x] Base-chain gating implemented for `base_mainnet` and `base_sepolia`.
- [x] Fail-closed behavior implemented for missing builder code on Base non-empty calldata (`builder_code_missing`).
- [x] Safe-mode skip implemented for empty calldata and no double-append on already-tagged calldata.
- [x] Runtime tx outputs include builder attribution metadata fields.
- [x] required gates rerun sequentially (`db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, `pm2 restart all`).
- [x] runtime tests pass (`test_trade_path.py`, `test_wallet_core.py` where applicable).
- [ ] issue #50 evidence post + commit hash(es).

## Slice 112: v2-Only Fallback Research Contract + Canonical Sync
Status: [x]
Issue: #55

Goal:
- Lock v2-only fallback promotion criteria with official-source evidence requirements.

DoD:
- [x] source-of-truth updated with v2-only promotion contract.
- [x] roadmap/tracker/spec/tasks/acceptance/context pack synchronized.
- [x] acceptance research template includes source URLs + verification outcomes.

## Slice 113: Uniswap-Primary Trade Fallback Promotion (Verified v2)
Status: [x]
Issue: #56

Goal:
- Promote legacy trade fallback on Uniswap-primary chains only when verified v2 router/factory metadata is present and chain-checked.

DoD:
- [x] promoted chains updated with `coreContracts.factory/router` and `tradeOperations.legacyEnabled=true`.
- [x] promoted chains include official docs/repo/explorer source links.
- [x] `zksync_mainnet` remains explicitly fallback-disabled with deterministic reason.
- [x] runtime trade tests include primary-fail fallback-enabled and fallback-disabled expectations.

## Slice 114: Non-Uniswap Active Claims Truth Finalization
Status: [x]
Issue: #57

Goal:
- Preserve executable claims where integrated and deterministic fail-closed claims where not integrated.

DoD:
- [x] Hedera claim execution remains enabled.
- [x] base_sepolia/hardhat_local/kite_ai_testnet claim paths remain deterministic fail-closed.
- [x] acceptance matrix documents explicit reason mapping.

## Slice 115: Runtime Determinism + Provenance Guardrail Sweep
Status: [x]
Issue: #58

Goal:
- Ensure trade/claim failure outputs remain provenance-complete with no broadening beyond v2-only behavior.

DoD:
- [x] provider provenance fields present in tested failure outputs.
- [x] no new fallback engine introduced.
- [x] runtime unit tests pass.

## Slice 116: Final Active-Chain Parity Matrix + Closeout
Status: [x]
Issue: #59

Goal:
- Publish final active-chain parity matrix aligned to v2-only fallback truth and deterministic contracts.

DoD:
- [x] matrix includes send/trade/liquidity/claims plus primary/fallback/fail code columns.
- [x] promoted vs non-promoted fallback states are explicit per chain.
- [x] canonical docs/handoff artifacts synchronized.

## Slice 117: Ethereum Sepolia Harness Matrix Expansion
Status: [~]
Issue: #60

Goal:
- Extend wallet-approval harness execution from `hardhat_local -> base_sepolia` to `hardhat_local -> base_sepolia -> ethereum_sepolia -> hedera_testnet`, with deterministic capability-aware assertions.

DoD:
- [x] add matrix runner `apps/agent-runtime/scripts/wallet_approval_chain_matrix.py` with strict sequential stop-on-failure behavior.
- [x] matrix runner supports resume execution via `--start-chain` so one chain can be rerun without replaying prior legs.
- [x] harness supports optional wallet identity assertion (`--expected-wallet-address`).
- [x] harness includes Ethereum Sepolia ETH bootstrap path (`ETH -> WETH -> USDC`) and deterministic `scenario_funding_missing` fail-fast.
- [x] harness transfer and x402 scenarios are split so `ethereum_sepolia` asserts deterministic x402 unsupported behavior (`unsupported_chain_capability`).
- [x] unit tests added/updated for harness bootstrap/capability behavior and matrix runner sequencing.
- [ ] runtime matrix evidence captured for hardhat/base/ethereum sepolia.
- [x] required gates rerun sequentially (`db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, `pm2 restart all`).
- [ ] issue #60 updated with verification evidence + commit hash(es).

## Slice 117 Hotfix B: Agent-Canonical Confirmation Pipeline (Dual-Run Start)
Status: [~]
Issue: #60

Goal:
- Start dual-run cutover so agent runtime watcher is canonical for terminal trade/transfer confirmations while server remains ingest/index/comparator.

DoD:
- [x] trade status + transfer mirror payload contracts include watcher provenance metadata.
- [x] server persists watcher provenance metadata for trade + transfer mirrors.
- [x] terminal server synthetic fanout removed from trade/transfer status ingest paths.
- [x] server deposit poll path marked/tagged as `legacy_server_poller` comparator during dual-run.
- [x] dual-run parity + cross-talk regression evidence captured.

## Slice 117 Hotfix C: Cross-Chain `wallet wrap-native` Parity
Status: [~]
Issue: #60

Goal:
- Expand runtime `wallet wrap-native` from Hedera-only to config-driven cross-chain support for wallet-capable chains with resolvable wrapped-native targets.

DoD:
- [x] runtime no longer hard-rejects non-Hedera chains for `wallet wrap-native`.
- [x] runtime resolves wrapped-native target config-driven:
  - [x] helper `deposit()` path when `coreContracts.wrappedNativeHelper` is configured and valid.
  - [x] canonical wrapped-token `deposit()` path via native-symbol mapping (`W<NativeSymbol>` + strict alias fallback).
- [x] deterministic errors include `wrapped_native_token_missing` and retain `wrapped_native_helper_missing`, `invalid_amount`, `wrap_native_failed`.
- [x] runtime wrap failure `actionHint` includes explicit swap fallback guidance (`native -> wrapped`).
- [x] runtime tests updated for helper path + non-Hedera token path + deterministic negative cases.
- [x] required gates rerun sequentially (`db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, `pm2 restart all`).
- [ ] issue #60 updated with verification evidence + commit hash(es).

## Slice 117 Hotfix D: Trade-Cap Deprecation + Chain Context Parity
Status: [~]
Issue: #60

Goal:
- Remove deprecated trade-cap blocking from runtime/server trade paths and align chain inference to runtime/web-synced default chain.

DoD:
- [x] runtime trade/limit execution no longer blocks on missing/invalid `tradeCaps`.
- [x] server `evaluateTradeCaps` no longer returns blocking cap violations.
- [x] skill wrapper chain inference uses runtime default-chain (webapp-synced) before env fallback.
- [x] skill trade commands support optional explicit chain override (`trade-spot`, `trade-exec`, `trade-resume`).
- [x] canonical docs/contracts/handoff artifacts synchronized.
- [ ] required gates rerun sequentially (`db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, `pm2 restart all`).
- [ ] issue #60 updated with verification evidence + commit hash(es).

## Slice 117 Hotfix E: Transfer Approval Mirror Fail-Closed
Status: [~]
Issue: #60

Goal:
- Prevent ghost transfer approvals by failing wallet transfer approval creation when mirror sync to management inbox fails.

DoD:
- [x] runtime transfer mirror helper supports required-delivery mode for approval-required wallet sends.
- [x] `wallet-send` and `wallet-send-token` return deterministic `approval_sync_failed` when mirror delivery cannot be confirmed.
- [x] regression coverage added for mirror-sync failure path.
- [x] server mirror/write + management/read routes return deterministic `transfer_mirror_unavailable` on transfer-mirror schema/storage unavailability (no silent empty approvals fallback).
- [x] `/agents/:id` approvals transfer rows include deterministic selector `data-testid="approval-row-transfer-<approval_id>"` for automation.
- [x] executable browser smoke verifier validates management-session-gated approval row rendering on `/agents/:id`.
- [x] transfer decision endpoint is non-blocking for UI operations: approve returns async-queued response quickly and deny applies immediate mirror rejection.
- [x] transfer decisions preserve runtime separation: web queues decision inbox rows only; agent runtime consumes/acks decisions via agent-auth inbox polling.

## Slice 117 Hotfix F: Transfer Decision Reliability + Prompt Convergence
Status: [ ]
Issue: #60

Goal:
- Guarantee transfer approval decision convergence with always-on runtime consumption, deterministic approve preflight gating for runtime signing readiness, and terminal prompt cleanup fallback.

DoD:
- [x] agent runtime exposes continuous transfer decision loop command (`approvals run-loop`) with bounded backoff and cycle counters.
- [x] skill setup wires best-effort daemon/service activation for continuous run-loop execution on agent host (no web/pm2 dependency).
- [x] agent publishes chain-scoped runtime signing readiness snapshot (`walletSigningReady`, `walletSigningReasonCode`, `walletSigningCheckedAt`).
- [x] management transfer approve path blocks with deterministic `runtime_signing_unavailable` when runtime readiness is not sign-capable and does not enqueue inbox rows.
- [x] server terminal sweeper fallback dispatches runtime prompt cleanup for terminal transfer approvals (`filled|failed|rejected`) idempotently.
- [x] transfer approvals UI remains non-actionable for terminal rows even if cleanup metadata is missing.
- [x] required gates pass: `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, `pm2 restart all`, runtime tests, browser verifier.

## Slice 117 Hotfix G: Installer + Run-Loop Wiring Hardening
Status: [ ]
Issue: #60

Goal:
- Eliminate recurring `runtime_signing_unavailable` caused by installer/run-loop wiring drift across API base, agent credentials, and passphrase provisioning.

DoD:
- [x] setup script resolves run-loop env deterministically from env/config/backup with strict precedence.
- [x] setup script writes complete run-loop env atomically and refuses partial required-key writes.
- [x] setup script strict mode hard-fails when run-loop health probe is not sign-ready.
- [x] shell + PowerShell installers perform authoritative final strict setup pass after bootstrap/register.
- [x] installer final pass enforces install-origin canonical API base and bootstrap-issued agent credentials.
- [x] installer emits deterministic run-loop summary lines for apiBase/agentId/walletSigningReady.
- [x] required gates pass: runtime tests, `db:parity`, seed gates, `build`, `pm2 restart all`, UI verifier.

## Slice 117 Hotfix H: Runtime Signing Preflight False-Negative Guard
Status: [ ]
Issue: #60

Goal:
- Eliminate spurious `runtime_signing_unavailable` blocks when runtime signing is healthy but readiness lookup is missed/clobbered.

DoD:
- [x] heartbeat route preserves existing readiness state when readiness fields are omitted (no null clobber).
- [x] management transfer preflight supports normalized chain-key matching for readiness lookup.
- [x] management preflight includes defensive fallback to most-recent positive readiness snapshot when chain key record is absent.
- [x] required gates pass: `db:parity`, seed gates, `build`, `pm2 restart all`, UI verifier.
- [x] canonical docs/handoff artifacts synchronized.
- [ ] required gates rerun sequentially (`db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, `pm2 restart all`).
- [x] browser verification gate rerun (`npm run verify:ui:agent-approvals`) after build + PM2 restart.
- [ ] issue #60 updated with verification evidence + commit hash(es).

## Slice 117 Hotfix I: Degraded Readiness Approve Fallback
Status: [ ]
Issue: #60

Goal:
- Eliminate false `runtime_signing_unavailable` hard-blocks when readiness snapshot lookup is missing but runtime signing remains healthy.

DoD:
- [x] management approve preflight hard-block is limited to explicit signer-unavailable reason codes (`wallet_passphrase_missing|wallet_passphrase_invalid|wallet_store_unavailable|wallet_missing`).
- [x] readiness-missing snapshots (`runtime_readiness_missing`) no longer hard-block decision queueing.
- [x] degraded readiness preflight queue path emits audit trace (`runtime_signing_preflight_degraded`) for observability.
- [x] required gates pass: `db:parity`, seed gates, `build`, `pm2 restart all`, UI verifier.
- [x] live production-path approval no longer returns false `runtime_signing_unavailable` for readiness-missing snapshots.

## Slice 117 Hotfix J: Immediate Prompt Convergence + Terminal Transfer Follow-Up
Status: [ ]
Issue: #60

Goal:
- Remove stale Telegram transfer approval buttons immediately after web decisions and ensure terminal transfer outcome follow-up is pushed once tx reaches terminal state.

DoD:
- [x] web transfer decision route triggers immediate runtime transfer prompt cleanup attempt for both approve and deny.
- [x] transfer decision response/audit payload includes immediate cleanup result when available.
- [x] transfer mirror route dispatches one terminal transfer-result prod notification on first transition to `filled|failed|rejected`.
- [x] terminal transfer-result dispatch allows Telegram last-channel delivery.
- [x] required gates rerun sequentially (`db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, `pm2 restart all`).
- [x] live verification evidence recorded for immediate button convergence + terminal follow-up notification.

## Slice 117 Hotfix K: Non-Blocking Swap Confirmation Path
Status: [ ]
Issue: #60

Goal:
- Ensure approved real-mode swap execution does not block foreground agent chat while waiting for on-chain confirmation.

DoD:
- [x] runtime `trade execute` returns immediately after broadcast with `status=verifying`.
- [x] in-band receipt wait is removed from foreground trade execute path.
- [x] action hint and result payload explicitly communicate asynchronous terminal convergence.
- [x] required gates rerun sequentially (`db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, `pm2 restart all`).
- [ ] live repro evidence recorded: post-approve swap no longer blocks subsequent chat turn while waiting on confirmation.

## Slice 117 Hotfix L: Truthful Trade Decision Messaging
Status: [ ]
Issue: #60

Goal:
- Keep owner-facing Telegram trade messaging truthful and concise across approval/execution outcomes.

DoD:
- [x] approval acknowledgment no longer claims terminal success before execution outcome.
- [x] runtime decision path emits terminal trade follow-up message (`filled|failed|rejected|verification_timeout`).
- [x] regression tests cover new copy contract + follow-up invocation.
- [x] required gates rerun sequentially (`test_trade_path`, `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, `pm2 restart all`).

## Slice 117 Hotfix M: Approval History Terminal Status Truthfulness
Status: [ ]
Issue: #60

Goal:
- Ensure approvals panels show terminal trade execution failures as failed/rejected outcomes rather than successful approvals.

DoD:
- [x] `/agents/:id` approval history preserves trade terminal execution status (`filled`, `failed`, `verification_timeout`, `expired`) instead of collapsing to `approved`.
- [x] management approvals inbox normalization maps terminal failures (`failed`, `verification_timeout`, `expired`) to rejected bucket semantics.
- [x] approvals filter tabs keep failed terminal trades visible under `Rejected/Denied`.
- [x] required gates rerun sequentially (`db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, `pm2 restart all`).
- [x] live evidence recorded with failed terminal trades mapped to rejected bucket semantics (no longer `approved`) in management approvals inbox.

## Slice 117 Hotfix N: Ethereum Sepolia Wallet Balance Sync Type-Stability
Status: [ ]
Issue: #60

Goal:
- Ensure canonical wallet balances continue syncing after filled Ethereum Sepolia swaps (no silent USDC omission in wallet panel).

DoD:
- [x] `/management/deposit` sync no longer degrades with PostgreSQL `inconsistent types deduced for parameter` errors during deposit-event dedupe checks.
- [x] `wallet_balance_snapshots` update path continues for canonical tokens (`WETH`, `USDC`) on `ethereum_sepolia`.
- [x] required gates rerun sequentially (`db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, `pm2 restart all`).
- [x] live evidence recorded: `ethereum_sepolia` chain balances include non-zero `USDC` after filled swap.

## Slice 117 Hotfix O: Hedera Swap Fee-Retry + Symbol Resolution
Status: [ ]
Issue: #60

Goal:
- Ensure approved Hedera swaps do not fail on minimum gas-price floor and that trade activity labels resolve canonical symbols (no raw `0x...` token aliases).

DoD:
- [x] runtime cast-send retry path parses minimum gas-price rejection and retries with at-least-minimum gas price.
- [x] Hedera testnet legacy-fee send path doubles estimated gas price (`2x`) before minimum-floor enforcement.
- [x] regression test covers minimum gas-price retry escalation behavior.
- [x] Hedera testnet canonical token map includes `USDC` address used by swap intents for UI/runtime symbol resolution.
- [x] required gates rerun sequentially (`test_trade_path`, `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, `pm2 restart all`).
- [x] evidence recorded for Hedera token labels (`USDC` symbol resolution restored in approvals/inbox for `trd_170515b0fe88313c6136`); minimum-gas retry path covered by runtime regression.
- [x] runtime regression validates Hedera testnet legacy send uses doubled gas-price (`123 -> 246`) before submission.

## Slice 117 Hotfix P: Telegram Callback Trade Result Fail-Closed
Status: [ ]
Issue: #60

Goal:
- Prevent Telegram from claiming swap success when runtime has no tx-hash-backed terminal fill evidence.

DoD:
- [x] runtime `approvals decide-spot` fail-closes `filled` outcomes with missing `txHash` to `failed` (`terminal_status_unverified`).
- [x] terminal Telegram follow-up helper no longer emits success copy when status is `filled` but tx hash is missing.
- [x] OpenClaw gateway patcher callback synthesis uses `executionStatus|status` and only marks success when `status=filled && txHash`.
- [x] regression test added for missing-tx-hash fail-closed behavior.
- [x] required gates rerun sequentially (`test_trade_path`, `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, `pm2 restart all`).
- [x] live gateway patch applied to installed OpenClaw bundles.

## Slice 118: Liquidity Approval + Wallet Activity Parity (All Chains)
Status: [~]
Issue: #61

Goal:
- Deliver owner-surface parity for liquidity approval flows (`add/remove`) across `/agents/:id` and `/approvals`, including chain-scoped wallet activity visibility for pending + terminal lifecycle states.

DoD:
- [x] `GET /api/v1/management/agent-state` returns `liquidityApprovalsQueue` (`approval_pending`) and `liquidityApprovalsHistory` (`approved|executing|verifying|filled|failed|rejected|expired|verification_timeout`) for active chain.
- [x] `GET /api/v1/management/approvals/inbox` supports `types=...liquidity...` and returns normalized liquidity rows with deterministic status bucketing.
- [x] `POST /api/v1/management/approvals/decision-batch` accepts `rowKind=liquidity` and routes decisions to canonical liquidity approval decision route.
- [x] batch decision path rejects `approve_allowlist` for liquidity rows with deterministic `payload_invalid` (`400`).
- [x] `/agents/:id` wallet activity includes liquidity approval lifecycle rows (pending + terminal).
- [x] `/agents/:id` approval history includes liquidity rows, pending actions, and non-actionable terminal entries.
- [x] `/approvals` type filter includes liquidity, rows are actionable, and bulk approve/reject includes liquidity while allowlist remains trade-only.
- [x] canonical artifacts sync in same change (`docs/XCLAW_SOURCE_OF_TRUTH.md`, `docs/api/openapi.v1.yaml`, `packages/shared-schemas/json/management-approvals-decision-batch-request.schema.json`).
- [x] handoff artifacts updated in same change (`spec.md`, `tasks.md`, `acceptance.md`).
- [x] required gates rerun sequentially (`db:parity`, `seed:reset`, `seed:load`, `seed:verify`, task-specific tests, `build`, `pm2 restart all`).
- [x] issue #61 updated with verification evidence + commit hash(es).

## Slice 118 Follow-Up A: Ethereum Sepolia Uniswap LP Adapter Enablement
Status: [x]
Issue: #61

Goal:
- Remove deterministic `unsupported_liquidity_adapter` for `ethereum_sepolia` LP add requests that use operator alias `--dex uniswap`, while preserving fail-closed behavior for unsupported dex values.

DoD:
- [x] `config/chains/ethereum_sepolia.json` includes `liquidityProtocols` entries for `uniswap_v2` (`amm_v2`) and `uniswap_v3` (`amm_v3`).
- [x] runtime liquidity adapter resolver normalizes aliases (`uniswap|uni -> uniswap_v2`) before config lookup.
- [x] adapter tests cover alias success, explicit `uniswap_v3`, and unknown-dex fail-closed behavior.
- [x] CLI quote-add tests cover `ethereum_sepolia` alias success path and unknown-dex deterministic rejection.
- [x] source-of-truth + roadmap + handoff artifacts updated in the same change.
- [x] required gates rerun sequentially (`db:parity`, `seed:reset`, `seed:load`, `seed:verify`, task-specific tests, `build`, `pm2 restart all`).

## Slice 118 Follow-Up B: Sepolia Uniswap LP Add TransferFrom Determinism + Allowance Coverage
Status: [x]
Issue: #61

Goal:
- Prevent false LP add failures on `ethereum_sepolia` caused by allowance coverage drift between estimate and submit, and expose deterministic preflight diagnostics for router `TransferHelper::transferFrom` simulation reverts.

DoD:
- [x] runtime `amm_v2` add allowance step approves desired max units (`amountA`/`amountB`) rather than estimate-only units.
- [x] router simulation `TransferHelper::transferFrom` reverts map to `liquidity_preflight_router_transfer_from_failed`.
- [x] liquidity runtime tests cover desired-max allowance approval and specific transferFrom reason-code mapping.
- [x] source-of-truth + roadmap + handoff artifacts updated in the same change.
- [x] required gates rerun sequentially (`db:parity`, `seed:reset`, `seed:load`, `seed:verify`, task-specific tests, `build`, `pm2 restart all`).

## Slice 118 Follow-Up C: Sepolia LP Add RPC-Retry Preflight Stability
Status: [~]
Issue: #61

Goal:
- Reduce false `liquidity_preflight_router_transfer_from_failed` outcomes for `ethereum_sepolia` LP add when token probes are RPC-forbidden/unverifiable but alternate RPC simulation succeeds.

DoD:
- [x] runtime preflight retries router `addLiquidity` simulation across configured chain RPC candidates when initial failure is `TransferHelper::transferFrom` and probes are `rpc_forbidden_unverifiable`.
- [x] retry success emits deterministic warning metadata (`liquidity_preflight_router_transfer_from_retry_success`) and continues execution.
- [x] fail-closed behavior is preserved when all candidate RPC simulations fail.
- [x] runtime tests cover alternate-RPC retry success path.
- [x] source-of-truth + roadmap + handoff artifacts updated in the same change.
- [x] required gates rerun sequentially (`db:parity`, `seed:reset`, `seed:load`, `seed:verify`, task-specific tests, `build`, `pm2 restart all`).

## Slice 118 Follow-Up D: Sepolia TransferFrom Unverifiable Opt-In Bypass
Status: [x]
Issue: #61

Goal:
- Provide a controlled operator override to unblock Sepolia LP add execution when transfer probes are RPC-forbidden/unverifiable and router simulation repeatedly fails with `TransferHelper::transferFrom` despite sufficient balance/allowance evidence.

DoD:
- [x] Runtime adds explicit env-gated bypass for `ethereum_sepolia` only: `XCLAW_LIQUIDITY_ALLOW_SEPOLIA_TRANSFERFROM_BYPASS=1`.
- [x] Bypass applies only to `TransferHelper::transferFrom` failures under `rpc_forbidden_unverifiable` probes.
- [x] Runtime surfaces deterministic warning metadata `liquidity_preflight_router_transfer_from_unverifiable_bypassed`.
- [x] Runtime tests cover bypass enabled and disabled behavior.
- [x] source-of-truth + roadmap + handoff artifacts updated in the same change.
- [x] required gates rerun sequentially (`db:parity`, `seed:reset`, `seed:load`, `seed:verify`, task-specific tests, `build`, `pm2 restart all`).

## Slice 118 Follow-Up E: Sepolia Remove Gas-Estimate False-Negative Recovery
Status: [x]
Issue: #61

Goal:
- Eliminate false `liquidity_execution_failed` outcomes on `ethereum_sepolia` LP remove when RPC gas estimation reverts transiently (`Failed to estimate gas` / `ds-math-sub-underflow`) despite executable remove calldata.

DoD:
- [x] Runtime send path retries transaction submission across configured chain RPC candidates for retryable upstream/internal RPC failures (including code `19`).
- [x] Runtime send path retries with explicit gas-limit fallback on estimate false-negative signatures for Sepolia chains (`XCLAW_TX_ESTIMATE_BYPASS_GAS_LIMIT`, default `900000`).
- [x] Runtime tests cover estimate-failure detection and gas-limit retry behavior.
- [x] closed-loop runtime evidence captured: `ethereum_sepolia` remove intent reaches terminal `filled` after approval (`liq_6103a859a56f70492b13`, tx `0x5d85ddf4ef65c50c332470255d353628aa4e7bf5b8216e06e53883ccb9169bc8`).
- [x] source-of-truth + roadmap + handoff artifacts updated in the same change.
- [x] required gates rerun sequentially (`db:parity`, `seed:reset`, `seed:load`, `seed:verify`, task-specific tests, `build`, `pm2 restart all`).

## Slice 119: EVM-Only Exchange-Agnostic Execution Refactor
Status: [x]

Goal:
- Remove active non-EVM/Hedera support and make generic EVM router-adapter execution canonical while preserving compatibility route/CLI surface.

DoD:
- [x] Hedera chain configs removed from active repo support.
- [x] chain/public schemas limited to `family=evm`.
- [x] canonical generic trade routes exist.
- [x] compatibility Uniswap trade routes delegate to generic handlers.
- [x] active server execution path does not require `XCLAW_UNISWAP_API_KEY`.
- [x] chain configs include canonical `execution.trade` / `execution.liquidity`.
- [x] remaining installer/docs/runtime-test Hedera references removed or explicitly marked superseded history.
## Slice 120: Active Path Hedera Cleanup

Status: completed

- Goal: remove remaining Hedera references from active installer/runtime/web paths after Slice 119 EVM-only execution refactor.
- Supersedes active-path remnants left behind by Slices 92, 95, 100, 102, 103, 104, 105, 106, 109, 110, 113, and 114.
- DoD:
  - no Hedera refs remain in active installer/runtime/web files touched by this slice,
  - build stays green.

## Slice 121: Canonical Contract Closeout

Status: completed

- Goal: make OpenAPI and canonical docs reflect the generic EVM router-adapter model and mark `/uniswap/*` as compatibility aliases only.

## Slice 122: Harness/Test Realignment

Status: completed

- Goal: remove Hedera and `uniswap_proxy_not_configured` assumptions from active harness/test defaults.

## Slice 123: Skill/Reference Cleanup

Status: completed

- Goal: align operator-facing skill docs and infra defaults to the EVM-only runtime surface.

## Slice 124: Residual Active-Adjacent Cleanup

Status: completed

- Goal: remove the last active-adjacent Hedera assumptions from harnesses and skill-wrapper parsing.

## Slice 125: Runtime Test Realignment

Status: completed

- Goal: replace stale Hedera/HTS runtime tests with EVM-only router-adapter coverage.

## Slice 126: Canonical Docs Final Truth Pass

Status: completed

- Goal: keep canonical docs EVM-only while preserving older slice material as explicitly superseded history.

## Slice 127: Historical Artifact and Contract Hygiene

Status: completed

- Goal: preserve truthful history while aligning active contracts, schemas, and handoff artifacts to the EVM-only model.

## Slice 128: Unified EVM Action Engine (Phase 1)
Status: [x]
Issue: #62

Goal:
- move spot swap and AMM v2 liquidity add/remove onto one runtime-local EVM action executor with adapter-built plans.

DoD:
- [x] shared action-plan and executor modules exist in `apps/agent-runtime/xclaw_agent/`.
- [x] `trade spot` and `trade execute` use local adapter-built router execution, not proxy-built swap transactions.
- [x] AMM v2 `liquidity add` / `liquidity remove` use the shared executor path.
- [x] phase-1 runtime metadata emits `router_adapter` + generic execution fields.
- [x] stale `tradeProviders` / `liquidityProviders` removed from active chain configs.
- [x] runtime tests cover shared executor and updated trade/liquidity paths.
- [x] source-of-truth + roadmap + handoff artifacts updated in the same change.

## Slice 129: Unified Advanced LP Execution
Status: [x]
Issue: #62

Goal:
- move advanced concentrated-liquidity execution onto the same runtime-local action-plan engine and retire remaining compatibility-only `uniswap_api` runtime branches/config readers.

DoD:
- [x] advanced LP commands (`increase`, `claim-fees`, `claim-rewards`, `migrate`) build local action plans and execute through `EvmActionExecutor`.
- [x] `cmd_liquidity_execute` no longer branches on `uniswap_api`.
- [x] `_execute_uniswap_liquidity_intent` and related LP proxy helpers are removed from active runtime execution.
- [x] active chain configs no longer contain `tradeOperations`, `liquidityOperations`, or `uniswapApi`.
- [x] concentrated-liquidity execution uses canonical `position_manager_v3` metadata and config shape.
- [x] runtime tests + canonical artifacts updated in the same change.

## Slice 130: Concentrated-Liquidity Add/Remove + First-Class Migrate Planner
Status: [x]
Issue: #62

Goal:
- close remaining concentrated-liquidity execution gaps by routing v3 add/remove intents through local runtime execution and replacing migrate request-call lists with adapter-planned local steps.

DoD:
- [x] `cmd_liquidity_execute` supports local `position_manager_v3` add/remove execution paths.
- [x] v3 add/remove intent payloads carry normalized v3 metadata needed for deterministic local execution.
- [x] migrate planner no longer requires request `calls` input and derives deterministic local steps from normalized request + adapter metadata.
- [x] runtime no longer emits/depends on `migrate_request_calls_required` or `migrate_request_calls_invalid`.
- [x] runtime tests cover v3 add/remove execute paths, migrate no-call planning, and malformed v3 range fail-closed behavior.
- [x] source-of-truth + roadmap + handoff artifacts updated in the same change.
