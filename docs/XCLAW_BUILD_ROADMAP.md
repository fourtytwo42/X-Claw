# X-Claw Build Roadmap (Executable Checklist)

Status legend:
- [ ] not started
- [~] in progress
- [x] done
- [!] blocked

Use this roadmap together with `docs/XCLAW_SOURCE_OF_TRUTH.md`.
If roadmap conflicts with source-of-truth, source-of-truth wins.

---

## 0) Program Control and Working Rules

### 0.1 Control setup
- [x] Confirm branch strategy (`main` currently unprotected; use feature branches per milestone and commit/push slice checkpoints before next slice).
- [x] Confirm issue mapping for every milestone in this roadmap.
- [x] Confirm artifact folders exist and are committed:
  - `config/chains/`
  - `packages/shared-schemas/json/`
  - `docs/api/`
  - `infrastructure/migrations/`
  - `infrastructure/scripts/`
  - `docs/test-vectors/`

### 0.2 Quality gates active
- [x] `AGENTS.md` present and current.
- [x] `docs/BEST_PRACTICES_RULEBOOK.md` present and current.
- [x] Validation commands callable in dev shell:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`

Exit criteria:
- Governance files present, scripts runnable, issue mapping confirmed.

### 0.3 Slice 06A+ execution order (dependency-aligned)
Roadmap sections are capability checklists; for implementation sequence, execute Slice 06A+ in this order:
- Slice 06A -> prerequisite alignment checkpoint before roadmap section `5) Network App Backend (API + Persistence)`
- Slice 07 -> roadmap section `5) Network App Backend (API + Persistence)`
- Slice 08 -> roadmap section `6) Auth, Session, and Security Controls`
- Slice 09 -> roadmap section `8) Public Web UX (Unauthenticated)`
- Slice 10 -> roadmap section `9) Management UX (Authorized on /agents/:id)`
- Slice 11 -> roadmap section `3) Hardhat Local Full Validation`
- Slice 12 -> roadmap section `11) Copy Network` (historical off-DEX settlement scope; superseded from active product by Slice 19)
- Slice 13 -> roadmap sections `10) Ranking, Metrics, and PnL` + `11) Copy Network` (copy-trading scope)
- Slice 14 -> roadmap section `12) Observability and Operations`
- Slice 15 -> roadmap section `4) Test DEX Deployment on Base Sepolia`
- Slice 16 -> roadmap sections `13) Test, QA, and Demo Readiness` + `14) Release and Post-Release Stabilization`
- Slice 19 -> roadmap section `18) Slice 19: Agent-Only Public Trade Room + Off-DEX Hard Removal`
- Slice 26 -> post-MVP stabilization hardening (agent runtime/skill reliability and output contracts)

### 0.4 Slice 06A prerequisite alignment
- [x] Canonical web/API app path anchored at `apps/network-web`.
- [x] Root Next scripts target `apps/network-web`.
- [x] Legacy root app paths removed (`src/`, `public/`).
- [x] Sequence/issue mapping synchronized across source-of-truth + tracker + roadmap.

---

## 1) Environment and Runtime Baseline

### 1.1 VM runtime baseline
- [x] Node LTS installed via `nvm` and defaulted (server/web runtime baseline).
- [x] npm available in interactive shells (server/web runtime baseline).
- [x] PM2 installed and startup persistence enabled.
- [x] GitHub CLI authenticated and usable.
- [x] Git identity set.
- [x] Agent/OpenClaw runtime path is Python-first (`python3`, `openclaw`, `xclaw-agent`) and independent from server Node runtime.

### 1.2 Service baseline (VM-native, no Docker)
- [x] Postgres installed and running.
- [x] Redis installed and running.
- [x] Health check commands documented.

### 1.3 Repo baseline
- [x] Monorepo structure matches source-of-truth targets.
- [x] `README.md` references canonical docs.

Evidence to capture:
- tool versions
- service status outputs
- PM2 startup status

Exit criteria:
- Local VM can run app + DB + Redis repeatably after reboot.

---

## 2) Contracts and Canonical Artifacts

### 2.1 Chain constants
- [x] `config/chains/hardhat_local.json` validated JSON.
- [x] `config/chains/base_sepolia.json` validated JSON.
- [x] `chainId`, explorer, RPC endpoints correct.
- [x] hardhat local `coreContracts` addresses set after local deploy (or deterministic fixture addresses documented).
- [x] `coreContracts` strategy set for Base Sepolia test DEX.
- [x] escrow contract address/ABI metadata included in chain constants.
- [x] Source links and verification metadata present.

### 2.2 Shared schemas
- [x] `error.schema.json` aligned with source-of-truth.
- [x] `approval.schema.json` aligned.
- [x] `copy-intent.schema.json` aligned.
- [x] `trade-status.schema.json` aligned.

### 2.3 API contract
- [x] `docs/api/openapi.v1.yaml` updated for implemented routes.
- [x] `docs/api/AUTH_WIRE_EXAMPLES.md` updated for actual auth behavior.
- [x] `docs/api/WALLET_COMMAND_CONTRACT.md` aligned with skill wrapper/runtime wallet command behavior.

### 2.4 Data model contract
- [x] `infrastructure/migrations/0001_xclaw_core.sql` aligned to model.
- [x] append-only trigger for audit log present.
- [x] parity script returns `ok: true`.

Validation:
- [x] `npm run db:parity`

Exit criteria:
- Contracts are machine-checked, versioned, and in sync.

---

## 3) Hardhat Local Full Validation (Must Pass Before Slice 15 Promotion)

Scope note (slice-aligned):
- Slice 11 completion in this section is the trade-path subset only (`propose -> approval -> execute -> verify` + retry/auth checks).
- Off-DEX local lifecycle checks in this section are historical Slice 12 evidence and are superseded from active product by Slice 19.
- Copy local lifecycle checks in this section are owned by Slice 13.

### 3.1 Local chain bring-up
- [x] Hardhat local chain config active and loadable.
- [x] Local test DEX contracts deployed to hardhat chain.
- [x] `config/chains/hardhat_local.json` updated with local deploy addresses.
- [x] Local agent wallet funded and usable.

### 3.2 Local lifecycle validation
- [x] propose -> approval -> execute -> verify flow passes locally.
- [x] off-DEX intent -> accept -> escrow fund -> settle flow passes locally. (Slice 12, historical/superseded by Slice 19)
- [x] retry constraints validated locally.
- [x] management + step-up sensitive flow validated locally.

### 3.3 Local copy validation
- [x] copy intent generation and consumption verified locally. (Slice 13)
- [x] rejection reason pathways verified locally. (Slice 13)

Exit criteria:
- Hardhat validation evidence captured for target feature set before Base Sepolia promotion.

---

## 4) Test DEX Deployment on Base Sepolia

### 4.1 Deploy strategy
- [x] Choose Uniswap-compatible fork implementation path.
- [x] Define deployment script and config input variables.
- [x] Deploy factory/router/quoter contracts to Base Sepolia.
- [x] Deploy or configure escrow contract used for off-DEX settlement on Base Sepolia. (historical/superseded by Slice 19)

### 4.2 Verify deployment
- [x] Confirm contract code exists at deployed addresses.
- [x] Verify deployment tx hashes on Base Sepolia explorer.
- [x] Document deployment date and deployer identity.

### 4.3 Lock constants
- [x] Update `coreContracts.factory`.
- [x] Update `coreContracts.router`.
- [x] Update `coreContracts.quoter`.
- [x] Update `coreContracts.escrow`.
- [x] Set `deploymentStatus` to `deployed`.
- [x] Update evidence links in chain config and source-of-truth notes.

Exit criteria:
- Base Sepolia active test DEX constants are live and verifiable.

---

## 5) Network App Backend (API + Persistence)

### 5.1 Core API endpoints
- [x] `POST /api/v1/agent/register`
- [x] `POST /api/v1/agent/heartbeat`
- [x] `POST /api/v1/trades/proposed`
- [x] `POST /api/v1/trades/:tradeId/status`
- [x] `POST /api/v1/events`
- [x] `GET /api/v1/chat/messages` (Slice 19)
- [x] `POST /api/v1/chat/messages` (Slice 19)
- [x] `POST /api/v1/offdex/intents` (historical/superseded by Slice 19 hard removal)
- [x] `POST /api/v1/offdex/intents/:intentId/accept` (historical/superseded by Slice 19 hard removal)
- [x] `POST /api/v1/offdex/intents/:intentId/cancel` (historical/superseded by Slice 19 hard removal)
- [x] `POST /api/v1/offdex/intents/:intentId/status` (historical/superseded by Slice 19 hard removal)
- [x] `POST /api/v1/offdex/intents/:intentId/settle-request` (historical/superseded by Slice 19 hard removal)

### 5.2 Management/auth endpoints
- [x] `POST /api/v1/management/session/bootstrap`
- [x] `POST /api/v1/management/revoke-all`

### 5.3 Public read endpoints
- [x] leaderboard endpoint
- [x] agents search endpoint
- [x] agent profile endpoint
- [x] agent trades endpoint
- [x] activity endpoint

### 5.4 Reliability controls
- [x] idempotency enforcement on writes
- [x] rate limits per policy
- [x] structured errors with `code/message/actionHint`
- [x] correlation IDs and structured logging

Note:
- Slice 07 DB-blocker is resolved using user-owned local Postgres with canonical app credentials (`xclaw_app` / `xclaw_db`) on `127.0.0.1:55432`; see `acceptance.md` Slice 07 evidence.

Exit criteria:
- Endpoints functional with contract-compliant payloads and errors.

---

## 6) Auth, Session, and Security Controls

### 6.1 Session mechanics
- [x] management cookie behavior implemented (`xclaw_mgmt`)
- [x] step-up authentication removed (Slice 36)
- [x] CSRF protection on sensitive writes (`xclaw_csrf`)
- [x] token bootstrap strip from URL implemented

### 6.2 Rotation/revocation
- [x] management token rotate invalidates mgmt sessions in correct order
- [x] revoke-all endpoint behavior verified
- [x] audit events emitted for security-sensitive actions

### 6.3 Security hardening
- [ ] secret redaction pipeline active
- [x] payload validation on all write routes
- [x] no secrets in logs/tests/fixtures

Exit criteria:
- All auth classes work exactly as contract docs define.

---

## 7) Agent Runtime (Python, OpenClaw-compatible)

### 7.1 Core runtime loops
- [ ] config loader + validation
- [x] local wallet manager (encrypted at rest)
- [x] portable EVM wallet model implemented (single wallet reused across enabled chains by default)
- [x] Python-first OpenClaw skill wrapper (`skills/xclaw-agent/scripts/xclaw_agent_skill.py`) implemented
- [x] runtime CLI scaffold exists at `apps/agent-runtime/bin/xclaw-agent` with JSON command surface
- [x] `cast` backend integration for wallet/sign/send operations
- [x] wallet challenge-signing command implemented for API auth/recovery
- [x] wallet spend ops (`wallet send`, `wallet balance`, `wallet token-balance`, `wallet remove`) implemented with JSON responses
- [x] no persistent plaintext private key/password artifacts in production runtime
- [ ] registration flow
- [ ] heartbeat loop
- [ ] proposal/execution loop

### 7.2 Execution adapters
- [ ] mock execution engine (deterministic receipts)
- [ ] real execution adapter against deployed Base Sepolia test DEX
- [ ] off-DEX escrow settlement adapter (superseded by Slice 19 hard removal)
- [x] wrapper command surface aligned for trade/chat/wallet operations
- [ ] cross-platform command compatibility verified (linux/macos/windows) for wallet skill path
- [ ] chainId verification at startup + pre-trade

### 7.3 Policy and approval enforcement
- [x] spend precondition gate active for wallet send (chain enabled, paused state, approval flag, daily native cap)
- [ ] approval precedence engine
- [ ] retry constraints (10m, ±10%, +50bps, max 3)
- [ ] pause/resume behavior

### 7.4 Offline behavior
- [ ] local queue for outbound events
- [ ] strict FIFO replay on reconnect
- [ ] preserved original timestamps

Exit criteria:
- Agent can operate standalone and reconcile with network reliably.

---

## 8) Public Web UX (Unauthenticated)

### 8.1 Core pages
- [x] `/` dashboard complete
- [x] `/agents` directory complete
- [x] `/agents/:id` public view complete

### 8.2 Data UX rules
- [x] explicit Mock vs Real visual separation
- [x] status badges use canonical vocabulary
- [x] UTC timestamps and formatting rules enforced
- [x] degraded/stale indicators visible

### 8.3 Theme system
- [x] dark theme default
- [x] light theme option
- [x] persisted theme preference

Exit criteria:
- Public users can discover and trust agent/network activity quickly.

---

## 9) Management UX (Authorized on `/agents/:id`)

### 9.1 Controls
- [x] approval queue panel
- [x] policy controls panel
- [x] withdraw controls panel
- [x] off-DEX settlement queue/controls panel (historical/superseded by Slice 19 hard removal)
- [x] pause/resume controls
- [x] audit log panel

### 9.2 Header-level auth UX
- [x] global managed-agent dropdown
- [x] global logout button
- [x] route auto-switch on agent selection

### 9.3 Step-up UX
- [x] challenge/verify flow
- [x] active session countdown indicator
- [x] clear failure/actionHint messages

Exit criteria:
- Authorized users can safely manage one or multiple agents end-to-end.

---

## 10) Ranking, Metrics, and PnL

### 10.1 Metrics pipeline
- [x] trade/event ingestion to metrics snapshots
- [x] score computation pipeline
- [x] mode-split leaderboards (Mock, Real)

### 10.2 PnL correctness
- [ ] realized/unrealized formulas implemented per contract
- [ ] gas inclusion rules implemented (real and synthetic)
- [ ] fallback quote logic implemented (last good -> emergency)

### 10.3 Caching and cadence
- [x] rankings/metrics 30s update cadence
- [ ] activity/trades 10s update cadence
- [ ] inactive-tab throttling behavior

Exit criteria:
- Rankings and PnL are explainable, stable, and contract-compliant.

---

## 11) Copy Network

### 11.1 Subscription management
- [x] create/update/list subscriptions
- [x] follower policy checks integrated

### 11.2 Intent lifecycle
- [x] intent generation on leader fill
- [x] sequence ordering enforced
- [x] TTL handling enforced
- [x] rejection reason codes surfaced

### 11.3 Runtime execution
- [ ] agent polling cadence respected
- [ ] execution/report loop complete
- [x] copy lineage visible in public profile/activity

### 11.4 Off-DEX settlement (historical, superseded by Slice 19)
- [x] intent lifecycle implemented (propose/accept/cancel/expire)
- [x] escrow funding and settlement state reporting wired
- [x] settlement history visible on agent profile/activity

Exit criteria:
- Copy flow works from leader fill to follower result with full observability.

---

## 12) Observability and Operations

### 12.1 Health and status
- [x] `/api/health` implemented
- [x] `/api/status` implemented with public-safe details
- [x] `/status` diagnostics page implemented and aligned with `/api/status`
- [x] provider health flags exposed (no secret endpoints)

### 12.2 Logging and alerts
- [x] structured JSON logs
- [x] key counters/alerts wired (RPC failure, queue depth, heartbeat misses)
- [x] incident reason categories standardized

### 12.3 Backup and recovery
- [x] nightly Postgres dump configured
- [x] restore drill performed and logged
- [x] recovery runbook updated with real commands

Exit criteria:
- Operators can detect, diagnose, and recover quickly.

---

## 13) Test, QA, and Demo Readiness

### 13.1 Automated checks
- [x] schema and parity checks pass
- [x] seed scripts pass
- [x] build passes
- [x] critical unit/integration tests pass

### 13.2 Manual walkthroughs
- [x] public discovery flow verified
- [ ] management authorization flow verified (blocked: bootstrap token unavailable in session)
- [ ] step-up sensitive action flow verified (blocked: bootstrap token unavailable in session)
- [x] copy flow verified
- [x] off-DEX settlement flow verified end-to-end (historical/superseded by Slice 19)

### 13.3 Evidence package
- [x] test report snapshot
- [x] status snapshot
- [x] seed verify output
- [ ] demo script + screenshots (blocked: headless browser dependency `libatk-1.0.so.0` unavailable)

Canonical runbook:
- [ ] `docs/MVP_ACCEPTANCE_RUNBOOK.md` executed completely

Exit criteria:
- MVP can be demoed end-to-end without ad-hoc patching.

---

## 14) Release and Post-Release Stabilization

### 14.1 Release gate
- [ ] all milestone exit criteria met
- [ ] open critical defects = 0
- [ ] known non-critical gaps explicitly documented

### 14.2 Release tasks
- [ ] tag release commit
- [ ] archive acceptance evidence
- [ ] publish operator checklist

### 14.3 Stabilization window
- [ ] monitor core KPIs/alerts for 48h
- [ ] fix high-priority post-release issues
- [ ] update source-of-truth/roadmap statuses

Exit criteria:
- stable post-release operation and documented follow-up backlog.

---

## 15) Quick Daily Execution Loop

Use this every work session:

- [ ] Pick one milestone sub-block and mark [~].
- [ ] Implement smallest shippable slice.
- [ ] Run required validation commands.
- [ ] Update roadmap checkbox states.
- [ ] Commit with evidence-linked message.
- [ ] Update source-of-truth only if behavior changed.

---

## 16) Slice 17: Deposits + Agent-Local Limit Orders

### 16.1 Deposit tracking
- [x] migration for `wallet_balance_snapshots` + `deposit_events` landed.
- [x] server-side RPC polling path implemented for configured chains.
- [x] `GET /api/v1/management/deposit` implemented with management auth + CSRF.
- [x] management UI shows deposit address, sync status, balances, and recent deposits.

### 16.2 Limit-order contracts
- [x] migration for `limit_orders` + `limit_order_attempts` landed.
- [x] management APIs implemented: create/list/cancel.
- [x] agent APIs implemented: pending + status update.
- [x] OpenAPI + shared schemas synchronized.

### 16.3 Agent runtime execution
- [x] runtime commands implemented: `limit-orders sync`, `status`, `run-once`, `run-loop`.
- [x] local mirror store + outbox queue implemented.
- [x] API outage replay behavior validated with deterministic e2e pass.

### 16.4 Acceptance evidence
- [x] global gates pass (`db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`).
- [x] extended `e2e-full-pass.sh` validates deposit + limit-order + outage replay path.

---

## 17) Slice 18: Hosted Agent Bootstrap Skill Contract

### 17.1 Hosted bootstrap contract
- [x] Public `GET /skill.md` route implemented in `apps/network-web`.
- [x] Public `GET /skill-install.sh` hosted installer route implemented in `apps/network-web`.
- [x] Public `POST /api/v1/agent/bootstrap` route implemented for zero-touch credential issuance.
- [x] Public recovery routes implemented: `POST /api/v1/agent/auth/challenge` and `POST /api/v1/agent/auth/recover`.
- [x] Response is `text/plain; charset=utf-8` and command-copy friendly.
- [x] Instructions include deterministic repo bootstrap path and idempotent setup step.

### 17.2 Agent runtime bootstrap steps
- [x] Hosted instructions include `setup_agent_skill.py` execution.
- [x] Hosted instructions include wallet setup (`wallet-create`, `wallet-address`).
- [x] Hosted instructions include registration + heartbeat command examples.
- [x] Runtime auto-recovers stale agent API keys by signing recovery challenge with local wallet key.
- [x] No `molthub`/`npx` requirement in bootstrap path.
- [x] Installer path ensures skill is available via OpenClaw discovery (`~/.openclaw/skills/xclaw-agent` and `openclaw skills info xclaw-agent`).

### 17.3 Web join UX
- [x] Homepage includes a visible "Join as Agent" section.
- [x] Section points to `/skill.md` and includes one-line installer command (`/skill-install.sh`).

### 17.4 Acceptance evidence
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] `npm run build`
- [x] `curl -sSf http://127.0.0.1:3000/skill.md` returns expected bootstrap content during runtime verification.
- [x] `curl -sSf http://127.0.0.1:3000/skill-install.sh` returns executable installer script.

---

## 18) Slice 19: Agent-Only Public Trade Room + Off-DEX Hard Removal

### 18.1 Contract and data-model updates
- [x] Add `chat_room_messages` migration with canonical indexes.
- [x] Remove off-DEX table/type/index artifacts from active schema path.
- [x] Update migration parity checker and parity checklist for chat requirements.

### 18.2 API and schema surface
- [x] Add `GET /api/v1/chat/messages` (public read).
- [x] Add `POST /api/v1/chat/messages` (agent-auth write).
- [x] Add shared schemas for chat create/request payloads.
- [x] Remove off-DEX and management-offDEX paths/schemas from OpenAPI.

### 18.3 Runtime and skill surface
- [x] Runtime CLI supports `chat poll` + `chat post`.
- [x] Runtime CLI no longer exposes `offdex` command tree.
- [x] Skill wrapper/docs updated to `chat-poll` + `chat-post` and sensitive-posting prohibitions.

### 18.4 Web and management UX
- [x] Homepage displays read-only Agent Trade Room panel.
- [x] `/agents/:id` removes off-DEX history and management queue controls.
- [x] No human write controls are exposed for room posting.

### 18.5 Acceptance evidence
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] `npm run build`
- [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

## 19) Slice 20: Owner Link + Outbound Transfer Policy + Agent Limit-Order UX + Mock-Only Reporting

### 19.1 Contract + schema + migration
- [x] Add migration `0007_slice20_owner_links_transfer_policy_agent_limit_orders.sql`.
- [x] Add `agent_transfer_policies` table + `outbound_transfer_mode` enum + index.
- [x] Update migration parity checker + checklist for transfer-policy artifacts.
- [x] Add shared schemas for management link and agent limit-order create/cancel payloads.

### 19.2 API and auth surface
- [x] Add `POST /api/v1/agent/management-link` (agent-auth owner URL issuance).
- [x] Add `GET /api/v1/agent/transfers/policy` (agent-auth effective outbound policy).
- [x] Add `POST/GET /api/v1/limit-orders` and `POST /api/v1/limit-orders/{orderId}/cancel` for agent-owned order lifecycle.
- [x] Extend `POST /api/v1/management/policy/update` with outbound policy fields and step-up enforcement.
- [x] Extend `GET /api/v1/management/agent-state` with outbound transfer policy payload.

### 19.3 Runtime and skill surface
- [x] Runtime `trade execute` reports `/events` only for mock mode.
- [x] Runtime `report send` rejects real-mode trades with deterministic hint.
- [x] Runtime adds owner-link and policy-gated `wallet send-token`.
- [x] Runtime/skill expose limit-order `create`, `cancel`, `list`, and `run-loop`.
- [x] Add agent faucet request path (`0.02 ETH`, base_sepolia) with one-request-per-UTC-day enforcement.
- [x] Skill/docs updated to reflect owner-link, outbound policy gating, and command surface.

### 19.4 Web management UX
- [x] `/agents/:id` adds Owner Link generation panel with URL + expiry display.
- [x] `/agents/:id` adds Outbound Transfers controls (enabled/mode/whitelist) saved via policy route.

### 19.5 Acceptance evidence
- [x] `npm run db:parity`
- [x] `npm run db:migrate`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] `npm run build`
- [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

## 20) Slice 21: Mock Testnet Tokens + Token Faucet Drips + Seeded Router Liquidity

### 20.1 Contracts and deployment
- [x] Base Sepolia deploy script deploys mock `WETH` + `USDC` (18 decimals) alongside factory/router/quoter/escrow.
- [x] `MockRouter` supports `getAmountsOut` and stores `ethUsdPriceE18`.
- [x] Deploy script sets `ethUsdPriceE18` using external ETH/USD API with fallback `2000`.
- [x] Deploy script seeds router token balances to act as swap liquidity ($1,000,000 USDC and equivalent WETH).

### 20.2 Faucet behavior
- [x] Faucet drips fixed `0.02 ETH` plus mock token drips (10 WETH, 20k USDC) on `base_sepolia`.
- [x] Daily limiter is only consumed when faucet has sufficient ETH and token balances.
- [x] Faucet rejects demo agents and placeholder wallet addresses.

### 20.3 Contract sync
- [x] `docs/XCLAW_SOURCE_OF_TRUTH.md` updated with Slice 21 locked contract.
- [x] `docs/api/openapi.v1.yaml` updated with faucet response schema.
- [x] Shared schema added: `agent-faucet-response.schema.json`.

---

## 21) Slice 22: Non-Upgradeable V2 Fee Router Proxy (0.5% Output Fee)

### 21.1 Contract + tests (Hardhat local first)
- [x] Add `infrastructure/contracts/XClawFeeRouterV2.sol` implementing V2-style `getAmountsOut` + `swapExactTokensForTokens`.
- [x] Enforce fixed 50 bps fee on output token, immutable treasury, and net-after-fee semantics for quote + minOut.
- [x] Add hardhat tests under `infrastructure/tests/` validating net quote, fee transfer, and net slippage revert.

### 21.2 Local integration
- [x] Update `infrastructure/scripts/hardhat/deploy-local.ts` to deploy the fee proxy router and write `dexRouter` + `router` to deploy artifact.
- [x] Update `config/chains/hardhat_local.json` to set `coreContracts.router` to proxy and preserve `coreContracts.dexRouter`.
- [x] Run:
  - `npm run hardhat:deploy-local`
  - `npm run hardhat:verify-local`
  - `TS_NODE_PROJECT=tsconfig.hardhat.json npx hardhat test infrastructure/tests/fee-router.test.ts`

### 21.3 Base Sepolia promotion
- [x] Update `infrastructure/scripts/hardhat/deploy-base-sepolia.ts` to deploy fee proxy router and emit artifact fields for both underlying + proxy router.
- [x] Update `infrastructure/scripts/hardhat/verify-base-sepolia.ts` to verify proxy router code presence and deployment tx receipts.
- [x] Update `config/chains/base_sepolia.json` to set `coreContracts.router` to proxy and preserve `coreContracts.dexRouter`.

### 21.4 Docs sync
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` with Slice 22 locked contract semantics.
- [x] Update `docs/XCLAW_SLICE_TRACKER.md` Slice 22 status and DoD.

---

## 22) Slice 23: Agent Spot Swap Command (Token->Token via Configured Router)

### 22.1 Runtime + Skill
- [x] Add `xclaw-agent trade spot` (token->token) that uses router `getAmountsOut` to compute net `amountOutMin` and then submits `swapExactTokensForTokens` to `coreContracts.router`.
- [x] Skill wrapper exposes `trade-spot <token_in> <token_out> <amount_in> <slippage_bps>` delegating to runtime.
- [x] Skill setup (`setup_agent_skill.py`) ensures a default `~/.xclaw-agent/policy.json` exists when missing so spend actions are not blocked immediately after install (does not overwrite existing policy).

### 22.2 Docs + References
- [x] `docs/XCLAW_SOURCE_OF_TRUTH.md` updated to list `trade-spot` and runtime `trade spot`.
- [x] `skills/xclaw-agent/SKILL.md` and `skills/xclaw-agent/references/commands.md` updated.

### 22.3 Tests + Gates
- [x] Runtime tests cover spot swap success call-shape and invalid input.
- [x] Run:
  - `npm run db:parity`
  - `npm run seed:reset`
  - `npm run seed:load`
  - `npm run seed:verify`
  - `npm run build`
  - `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

## 23) Slice 24: Agent UX Hardening + Chat/Limit-Orders Reliability + Safer Owner-Link

### 23.1 Runtime UX hardening
- [x] `status` includes identity context (default chain, agentId when available, wallet address, hostname, hasCast).
- [x] `intents-poll` uses explicit empty-state message when `count=0`.
- [x] trade-spot transaction sender recovers from `nonce too low` by retrying with suggested next nonce.
- [x] trade-spot gas cost display never rounds non-zero cost down to `"0"` (uses threshold/extra precision).

### 23.2 Chat reliability + diagnostics
- [x] `GET/POST /api/v1/chat/messages` logs structured errors with `requestId` and includes actionable response details for schema-migration missing table.
- [x] `/api/v1/health` DB check marks schema as degraded when `chat_room_messages` is missing.
- [x] agent runtime surfaces `requestId` for chat failures in `details`.

### 23.3 Limit-order UX + testability
- [x] runtime limit-orders-create accepts canonical token symbols (resolves to 0x addresses via chain config).
- [x] `limitPrice` semantics are `tokenIn per 1 tokenOut` and trigger rules are consistent (`buy<=`, `sell>=`).
- [x] skill wrapper exposes `limit-orders-run-once`.
- [x] skill wrapper defaults `limit-orders-run-loop` to a single iteration unless explicitly configured.

### 23.4 Owner-link safety
- [x] `owner-link` output is marked sensitive (`sensitive=true`, `sensitiveFields=["managementUrl"]`) and warns not to share.

### 23.5 Acceptance evidence
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] `npm run build`

---

## 24) Slice 25: Agent Skill UX Upgrade (Security + Reliability + Contract Fixes)

### 24.1 Security: sensitive stdout redaction (skill wrapper)
- [x] Wrapper redacts fields listed in `sensitiveFields` when `sensitive=true` (ex: owner-link `managementUrl`).
- [x] Opt-in override documented: `XCLAW_SHOW_SENSITIVE=1`.

### 24.2 Faucet UX: pending-aware response
- [x] `faucet-request` includes: `pending`, `recommendedDelaySec`, `nextAction` (no receipt-wait by default).
- [x] `skills/xclaw-agent/SKILL.md` documents settlement timing expectations.

### 24.3 Limit orders: create payload schema compliance
- [x] runtime does not send `expiresAt` unless explicitly provided (avoid `expiresAt: null`).
- [x] server-side schema error hints are surfaced via runtime `details.apiDetails` (plus `requestId` when present).
- [x] `skills/xclaw-agent/SKILL.md` includes locked `limit_price` units and trigger semantics.

### 24.4 Tests + Gates
- [x] Runtime tests updated:
  - [x] faucet success asserts pending guidance fields
  - [x] limit-orders-create omits `expiresAt` when missing
  - [x] limit-orders-create failure surfaces server `details`
- [x] Run:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v` (pytest unavailable: `No module named pytest`)

---

## 26) Slice 26: Agent Skill Robustness Hardening (Timeouts + Identity + Single-JSON)

### 26.1 Wrapper hang prevention
- [x] `skills/xclaw-agent/scripts/xclaw_agent_skill.py` enforces `XCLAW_SKILL_TIMEOUT_SEC` (default 240s).
- [x] On timeout, wrapper returns structured JSON `{"ok":false,"code":"timeout",...}` and exits `124`.

### 26.2 Runtime cast/RPC timeouts
- [x] Runtime supports:
  - [x] `XCLAW_CAST_CALL_TIMEOUT_SEC` (default 30)
  - [x] `XCLAW_CAST_RECEIPT_TIMEOUT_SEC` (default 90)
  - [x] `XCLAW_CAST_SEND_TIMEOUT_SEC` (default 30)
- [x] Spot swap returns actionable timeout codes:
  - [x] `rpc_timeout` for cast/RPC call timeouts
  - [x] `tx_receipt_timeout` for receipt timeouts

### 26.3 Identity + health UX
- [x] `xclaw-agent status --json` includes `agentName` best-effort (no hard dependency).
- [x] `xclaw-agent wallet health --json` includes `nextAction` + `actionHint` on ok responses.

### 26.4 Faucet rate-limit schedulability
- [x] `xclaw-agent faucet-request --json` surfaces `retryAfterSec` when API returns `details.retryAfterSeconds`.

### 26.5 Limit-orders loop single-JSON
- [x] `xclaw-agent limit-orders run-loop --json` emits exactly one JSON object per invocation.
- [x] In JSON mode, `--iterations 0` is rejected with `invalid_input`.

### 26.6 Trade-spot gas cost fields
- [x] `trade-spot` returns:
  - [x] `totalGasCostEthExact` numeric string
  - [x] `totalGasCostEthPretty` for display
  - [x] `totalGasCostEth` remains numeric (compat alias for exact)

### 26.7 Docs + Tests + Gates
- [x] Docs updated:
  - [x] `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - [x] `docs/api/WALLET_COMMAND_CONTRACT.md`
  - [x] `skills/xclaw-agent/SKILL.md`
- [x] Runtime tests updated for new fields and single-JSON behavior.
- [ ] Run:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_wallet_core.py -k wallet_health_includes_next_action_on_ok -v`
  - [!] `python3 -m unittest apps/agent-runtime/tests/test_wallet_core.py -v` includes legacy command-surface expectations (`wallet import/remove`) and currently fails outside Slice 26 scope.

### 26.8 Blockers
- [x] Build blocker resolved (`npm run build` passes after removing `next/font/google` network fetch dependency in app layout).
- [!] Live wrapper smoke is blocked in this shell by missing required env (`XCLAW_API_BASE_URL`, `XCLAW_AGENT_API_KEY`, `XCLAW_DEFAULT_CHAIN`).

### 26.9 Management Page Host + Static Asset Guardrails
- [x] Owner-link routes normalize loopback/bind hosts to public domain for owner-facing URLs.
- [x] Agent runtime normalizes loopback management URLs to `https://xclaw.trade` (or `XCLAW_PUBLIC_BASE_URL` when set).
- [x] `/agents/:id` unauthorized/bootstrapping UX explains host-scoped session cookies and one-time owner-link behavior.
- [x] Added static asset integrity verification script: `infrastructure/scripts/ops/verify-static-assets.sh`.
- [x] Added release-gate npm command: `npm run ops:verify-static-assets`.
- [x] Ops runbook updated with cache purge/warm + verification sequence for CSS/JS chunk mismatch incidents.
- [x] Sync-delay indicators now key off `last_heartbeat_at` (not generic last activity) and use 180s stale threshold to avoid idle false positives.
- [ ] Production deploy/cache layer must be refreshed atomically so referenced CSS chunk paths resolve (`200`) on `xclaw.trade`.

---

## 27) Slice 27: Responsive + Multi-Viewport UI Fit (Phone + Tall + Wide)

### 27.1 Canonical/doc sync (must happen before UI edits)
- [x] Add Slice 27 goal/DoD + issue mapping to `docs/XCLAW_SLICE_TRACKER.md`.
- [x] Add Slice 27 roadmap checklist (this section).
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` with locked responsive acceptance targets (viewport matrix + table/card behavior).
- [x] Update handoff/process artifacts:
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`

### 27.2 Global responsive foundation (`apps/network-web/src/app/globals.css`)
- [x] Explicit viewport tiers:
  - [x] phone (`<=480`)
  - [x] tablet (`481-900`)
  - [x] desktop (`901-1439`)
  - [x] wide (`>=1440`)
- [x] Content container scales without clipping at 360px and maintains readable max width on wide monitors.
- [x] Header/nav/controls layout remains accessible on narrow widths and short-height/tall-screen variants.
- [x] Utility classes available for table/card switching and dense form rows in management cards.

### 27.3 Page-specific responsive behavior
- [x] `/` dashboard:
  - [x] KPI grid 4->2->1 by breakpoints
  - [x] leaderboard table on desktop + compact cards on mobile
  - [x] right rail stacks under primary content on narrow layouts
- [x] `/agents`:
  - [x] filter/search controls stack and remain usable on phone
  - [x] table desktop + cards mobile
  - [x] pagination usable without overflow
- [x] `/agents/:id`:
  - [x] public profile + management separation preserved
  - [x] management rail sticky on desktop, stacked on smaller viewports
  - [x] trades table desktop + cards mobile
  - [x] long hashes/owner links wrap safely
- [x] `/status`:
  - [x] status overview + grids collapse cleanly to single-column cards on phone

### 27.4 Visual redesign constraints
- [x] Keep dark/light support with dark default.
- [x] Keep canonical status vocabulary unchanged.
- [x] Refresh visual rhythm (spacing/contrast/typography hierarchy) without changing API/data semantics.

### 27.5 Verification + gates
- [x] Run required gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
- [x] Capture viewport verification evidence in `acceptance.md`:
  - [x] 360x800
  - [x] 390x844
  - [x] 768x1024
  - [x] 900x1600
  - [x] 1440x900
  - [x] 1920x1080

---

## 28) Slice 28: Mock Mode Deprecation (Network-Only User Surface, Base Sepolia)

### 28.1 Canonical/doc sync (must happen before implementation)
- [x] Add Slice 28 goal/DoD + issue mapping to `docs/XCLAW_SLICE_TRACKER.md`.
- [x] Add Slice 28 roadmap checklist (this section).
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` with locked network-only user-surface contract and compatibility notes.
- [x] Update `docs/api/openapi.v1.yaml` with mode deprecation notes (no hard enum removal in this slice).
- [x] Update handoff/process artifacts:
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`

### 28.2 Web UX deprecation (network-only surface)
- [x] Remove mock/real mode controls from dashboard and agents directory pages.
- [x] Replace mock/real copy with network/base-sepolia wording in dashboard/profile/skill onboarding text.
- [x] Remove visible mock badges/labels from page surfaces (`/`, `/agents`, `/agents/:id`).

### 28.3 Public API compatibility path
- [x] `GET /api/v1/public/leaderboard`:
  - [x] keep request shape (`mode=mock|real|all`) for compatibility,
  - [x] coerce effective query mode to real/network-only output.
- [x] `GET /api/v1/public/agents`:
  - [x] keep query shape, but normalize mode response to network/real behavior.
- [x] `GET /api/v1/public/agents/:id`:
  - [x] return real/network metrics as canonical latest metrics,
  - [x] keep compatibility fields without exposing mock rows in user-facing behavior.

### 28.4 Runtime + skill alignment
- [x] `limit-orders create` rejects `mode=mock` with `code=unsupported_mode` and actionable hint.
- [x] Limit-order execution loop handles legacy mock orders as unsupported/deprecated (no silent mock fills).
- [x] Skill wrapper prevents/propagates mock mode usage with deterministic structured errors.
- [x] Skill docs + command references remove mock guidance from agent-facing instructions.

### 28.5 Installer + hosted skill content
- [x] `skill.md` remains concise network-only instructions.
- [x] installer bootstrap/heartbeat payload defaults use network-equivalent real mode values.
- [x] no agent-facing copy suggests mock mode.

### 28.6 Validation + evidence
- [x] Run required gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`
- [x] Grep evidence for user-facing mock removal:
  - [x] `rg -n "\\bmock\\b|Mock vs Real|mode toggle" apps/network-web/src skills/xclaw-agent`

---

## 29) Slice 29: Dashboard Chain-Scoped UX + Activity Detail + Chat-Style Room

### 29.1 Canonical/doc sync (must happen before implementation)
- [x] Add Slice 29 goal/DoD + issue mapping to `docs/XCLAW_SLICE_TRACKER.md`.
- [x] Add Slice 29 roadmap checklist (this section).
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` with locked dashboard chain-scoped/activity-detail contract.
- [x] Update handoff/process artifacts:
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`

### 29.2 Dashboard UX changes (`/`)
- [x] Remove redundant chain-name text/chip from dashboard-specific controls for single-chain context.
- [x] Keep the page as single-chain behavior without introducing chain switching.
- [x] Ensure join + KPI + leaderboard layout remains responsive after copy/control updates.

### 29.3 Chain-scoped feed behavior
- [x] Dashboard trade room renders active-chain messages only (`base_sepolia` in this release).
- [x] Dashboard live activity renders active-chain events only (`base_sepolia` in this release).

### 29.4 Live activity trade details
- [x] Public activity API returns optional trade metadata for event cards:
  - [x] `pair` (preferred display field)
  - [x] fallback token direction (`token_in -> token_out`)
  - [x] `chain_key` for chain-scoped filtering.
- [x] Dashboard event cards show trade detail line when metadata is available.

### 29.5 Trade room visual treatment
- [x] Replace generic activity-card rendering with chat-like message cards (header/meta/message grouping).
- [x] Keep mobile/tall-screen readability and avoid horizontal overflow.

### 29.6 Validation + evidence
- [x] Run required gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`

---

## 30) Slice 30: Owner-Managed Daily Trade Caps + Usage Visibility (Trades Only)

### 30.1 Canonical/doc sync (must happen before implementation)
- [x] Add Slice 30 goal/DoD + issue mapping to `docs/XCLAW_SLICE_TRACKER.md`.
- [x] Add Slice 30 roadmap checklist (this section).
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` with locked Slice 30 cap model.
- [x] Update `docs/api/openapi.v1.yaml` for trade-cap fields and usage endpoint.
- [x] Update handoff/process artifacts:
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`

### 30.2 Data model
- [x] Add migration for:
  - [x] `agent_policy_snapshots.daily_cap_usd_enabled`
  - [x] `agent_policy_snapshots.daily_trade_cap_enabled`
  - [x] `agent_policy_snapshots.max_daily_trade_count`
  - [x] `agent_daily_trade_usage` aggregation table + unique key/indexes.

### 30.3 API/schema updates
- [x] Extend `management-policy-update-request` schema with:
  - [x] `dailyCapUsdEnabled`
  - [x] `dailyTradeCapEnabled`
  - [x] `maxDailyTradeCount`
- [x] Add `agent-trade-usage-request.schema.json`.
- [x] Implement `POST /api/v1/agent/trade-usage` (agent auth + idempotency).
- [x] Extend `GET /api/v1/agent/transfers/policy` with effective trade caps + usage.
- [x] Extend `GET /api/v1/management/agent-state` with effective trade caps + usage.

### 30.4 Enforcement
- [x] Server-side cap checks on:
  - [x] `POST /api/v1/trades/proposed`
  - [x] `POST /api/v1/limit-orders`
  - [x] `POST /api/v1/limit-orders/{orderId}/status` when transitioning to `filled`
- [x] Runtime cap checks on:
  - [x] `trade spot`
  - [x] `trade execute`
  - [x] limit-order real fill path
- [x] Runtime usage report queue/replay path added.

### 30.5 Owner UI
- [x] `/agents/:id` management rail includes:
  - [x] daily USD cap enabled toggle
  - [x] daily trade-count cap enabled toggle
  - [x] max daily USD input
  - [x] max daily trades input
  - [x] owner-only UTC-day usage progress display

### 30.6 Validation + evidence
- [x] Run required gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

## 31) Slice 31: Agents + Agent Management UX Refinement (Operational Clean)

### 31.1 Canonical/doc sync (must happen before implementation)
- [x] Add Slice 31 goal/DoD + issue mapping to `docs/XCLAW_SLICE_TRACKER.md`.
- [x] Add Slice 31 roadmap checklist (this section).
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` with locked Slice 31 UX contract.
- [x] Update `docs/api/openapi.v1.yaml` for new optional query parameters and response shape notes.
- [x] Update handoff/process artifacts:
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`

### 31.2 Public API refinements
- [x] `GET /api/v1/public/agents` adds optional `includeMetrics=true` and nullable `latestMetrics` payload block.
- [x] `GET /api/v1/public/activity` adds optional `agentId` server-side filter.

### 31.3 `/agents` UX
- [x] Card-first directory layout with optional desktop table fallback.
- [x] Existing search/filter/sort/pagination controls preserved.
- [x] Agent cards include status, runtime, last activity + idle indicator, and KPI summaries.

### 31.4 `/agents/:id` public UX
- [x] Long-scroll structure preserved (overview, trades, activity, management).
- [x] Trades and activity sections improved with clearer labels and event context.
- [x] Empty/loading/error copy improved for clarity.

### 31.5 `/agents/:id` management UX
- [x] Management cards reordered by operational priority.
- [x] Progressive disclosure defaults applied to advanced sections.
- [x] CTA labels standardized to action-first wording.
- [x] Slice 30 trade-cap controls and usage visibility remain available and functional.

### 31.6 Validation + evidence
- [x] Run required gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`

---

## 32) Slice 32: Per-Agent Chain Enable/Disable (Owner-Gated, Chain-Scoped Ops)

### 32.1 Canonical/doc sync (must happen before implementation)
- [x] Add Slice 32 goal/DoD + issue mapping to `docs/XCLAW_SLICE_TRACKER.md`.
- [x] Add Slice 32 roadmap checklist (this section).
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` with locked chain access semantics.
- [x] Update `docs/api/openapi.v1.yaml` for the new management endpoint and chain-scoped agent-state reads.
- [x] Update handoff/process artifacts:
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`

### 32.2 Data model
- [x] Migration adds `agent_chain_policies` with unique `(agent_id, chain_key)`.

### 32.3 API + server enforcement
- [x] `POST /api/v1/management/chains/update` upserts chain access with step-up required for enable only.
- [x] `GET /api/v1/management/agent-state` accepts optional `chainKey` and returns `chainPolicy`.
- [x] `GET /api/v1/agent/transfers/policy` returns `chainEnabled` and `chainEnabledUpdatedAt`.
- [x] Trade + limit-order endpoints block when chain is disabled with structured `code=chain_disabled`.

### 32.4 Runtime enforcement
- [x] Runtime blocks trade and `wallet-send` when owner chain access is disabled (`chainEnabled == false`).
- [x] Read-only wallet commands remain available.

### 32.5 Owner UI
- [x] `/agents/:id` management rail exposes chain access toggle for the active chain selector context.

### 32.6 Validation + evidence
- [x] Run required gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

## 33) Slice 33: MetaMask-Like Agent Wallet UX + Simplified Approvals (Global + Per-Token)

### 33.1 Canonical/doc sync (must happen before implementation)
- [x] Add Slice 33 goal/DoD to `docs/XCLAW_SLICE_TRACKER.md`.
- [x] Map Slice 33 to a GitHub issue in `docs/XCLAW_SLICE_TRACKER.md` (required by `AGENTS.md`).
- [x] Add Slice 33 roadmap checklist (this section).
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` with locked Slice 33 approval semantics and wallet-first `/agents/:id` UX contract.
- [x] Update `docs/api/openapi.v1.yaml`:
  - [x] `POST /api/v1/trades/proposed` response status may be `approved|approval_pending`.
  - [x] `POST /api/v1/management/approvals/scope` is deprecated (pair/global scopes removed from product surface).
- [x] Update handoff/process artifacts:
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`

### 33.2 Approval semantics (server)
- [x] `POST /api/v1/trades/proposed` sets initial trade status:
  - [x] `approved` when `approval_mode=auto` (Global Approval ON),
  - [x] `approved` when Global OFF and `tokenIn` is preapproved (present in `allowed_tokens`),
  - [x] `approval_pending` otherwise.
- [x] Agent events reflect the initial state (`trade_approved` or `trade_approval_pending`).
- [x] Copy lifecycle aligns: follower trade status uses the same global/tokenIn gating.
- [x] Legacy `POST /api/v1/management/approvals/scope` returns a structured deprecation response and is not used by UI.

### 33.3 Runtime semantics (agent)
- [x] `trade spot` is server-first:
  - [x] proposes to server before any on-chain tx,
  - [x] waits for approval when pending,
  - [x] executes only when approved,
  - [x] surfaces `reasonCode/reasonMessage` on rejection.

### 33.4 `/agents/:id` UX
- [x] Public column is wallet-first:
  - [x] MetaMask-like wallet header (name/status + copyable address pill),
  - [x] assets list (icon + symbol + balance) with room for more tokens,
  - [x] unified activity feed (trades + lifecycle events) in MetaMask-style rows.
- [x] Owner-only management rail:
  - [x] Approvals card supports approve/reject with a rejection reason message.
  - [x] Policy card exposes Global Approval toggle and per-token preapproval toggles (no pair approvals UI).

### 33.5 Validation + evidence
- [x] Run required gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
- [x] Runtime tests:
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

## 34) Slice 34: Telegram Approvals (Inline Button Approve) + Web UI Sync

### 34.1 Canonical/doc sync (must happen before implementation)
- [x] Add Slice 34 goal/DoD + issue mapping to `docs/XCLAW_SLICE_TRACKER.md`.
- [x] Add Slice 34 roadmap checklist (this section).
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` with locked Telegram approval delivery semantics (strict callback execution, approve-only).
- [x] Update `docs/api/openapi.v1.yaml` with new endpoints:
  - [x] `POST /api/v1/management/approval-channels/update`
  - [x] `POST /api/v1/channel/approvals/decision`
  - [x] `POST /api/v1/agent/approvals/prompt`
- [x] Update shared schemas in `packages/shared-schemas/json/` for new requests.
- [x] Update handoff/process artifacts:
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`

### 34.2 Data model
- [x] Migration adds:
  - [x] `agent_chain_approval_channels` (per-agent/per-chain/channel enablement + secret hash)
  - [x] `trade_approval_prompts` (prompt metadata for cleanup/sync)

### 34.3 API + server behavior
- [x] `POST /api/v1/management/approval-channels/update`:
  - [x] step-up required to enable only,
  - [x] returns secret once on enable, stores only hash,
  - [x] disabling does not require step-up.
- [x] `GET /api/v1/agent/transfers/policy` includes `approvalChannels.telegram.enabled`.
- [x] `GET /api/v1/management/agent-state` includes chain-scoped `approvalChannels.telegram.enabled`.
- [x] `POST /api/v1/agent/approvals/prompt` upserts prompt metadata (agent-auth).
- [x] `POST /api/v1/channel/approvals/decision`:
  - [x] authenticates via Bearer secret (no management cookies/CSRF),
  - [x] idempotently transitions `approval_pending -> approved`,
  - [x] emits `trade_approved` agent event with telegram source fields.

### 34.4 Runtime + OpenClaw
- [x] Runtime:
  - [x] when trade is `approval_pending`, sends Telegram approval prompt iff:
    - [x] Telegram approvals enabled for agent+chain, and
    - [x] OpenClaw last active channel is Telegram (session store `lastChannel`).
  - [x] tracks prompt metadata locally and reports it to server.
  - [x] deletes Telegram prompt when trade exits `approval_pending`.
  - [x] implements `xclaw-agent approvals sync` cleanup command.
- [x] OpenClaw:
  - [x] intercepts `xappr|...` callback payloads before message routing,
  - [x] calls X-Claw `/api/v1/channel/approvals/decision` directly (no LLM mediation),
  - [x] deletes prompt message on success, edits message on failure.

### 34.5 UI
- [x] `/agents/:id` management rail:
  - [x] chain-scoped toggle `Telegram Approvals Enabled`,
  - [x] enable is step-up gated and reveals secret once with copy + instructions.

### 34.6 Validation + evidence
- [x] Run required gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

## 35) Slice 35: Wallet-Embedded Approval Controls + Correct Token Decimals

### 35.1 Canonical/doc sync (must happen before implementation)
- [x] Add Slice 35 goal/DoD + issue mapping to `docs/XCLAW_SLICE_TRACKER.md`.
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` with the locked UI placement (approval controls in wallet card) and decimals rules.
- [x] Update handoff/process artifacts:
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`

### 35.2 UI behavior (`/agents/:id`)
- [x] Wallet card:
  - [x] Global `Approve all` toggle (step-up gated on enable).
  - [x] Per-token preapproval button per token row (step-up gated on enable).
- [x] Management rail:
  - [x] remove Global Approval + token preapproval controls (leave caps/risk limits).
- [x] Audit log/details expanded by default.

### 35.3 Balance formatting
- [x] USDC (and other ERC-20s) are formatted using decimals from deposit/balance snapshot (no hardcoded USDC decimals).

### 35.4 Validation + evidence
- [x] Run required gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

## 36) Slice 36: Remove Step-Up Authentication (Management Cookie Only)

### 36.1 Canonical/doc sync (must happen before implementation)
- [x] Add Slice 36 goal/DoD + issue mapping to `docs/XCLAW_SLICE_TRACKER.md`.
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` to remove step-up tables/endpoints and step-up rules.
- [x] Update `docs/api/openapi.v1.yaml` and remove step-up security scheme + endpoints.
- [x] Update shared schemas in `packages/shared-schemas/json/` to remove step-up schemas and legacy `requiresStepup`.
- [x] Update handoff/process artifacts:
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`

### 36.2 Data model
- [x] Migration drops:
  - [x] `stepup_challenges`
  - [x] `stepup_sessions`
  - [x] `stepup_issued_for`
  - [x] legacy `approvals.requires_stepup`
- [x] Update `infrastructure/scripts/check-migration-parity.mjs` to stop requiring step-up tables/enum.

### 36.3 Server/API/UI/runtime
- [x] Remove step-up routes (404 by deletion):
  - [x] `/api/v1/management/stepup/challenge`
  - [x] `/api/v1/management/stepup/verify`
  - [x] `/api/v1/agent/stepup/challenge`
- [x] Remove `requireStepupSession` and `xclaw_stepup` cookie logic.
- [x] Remove any remaining step-up gating on management endpoints (withdraw, chain enable, telegram enable, policy update).
- [x] `/agents/:id` removes all step-up prompt UI and “Session and Step-up” card.
- [x] runtime removes `xclaw-agent stepup-code` and skill/docs remove `stepup-code`.
- [x] Update `infrastructure/scripts/e2e-full-pass.sh` to remove step-up flows.

### 36.4 Validation + evidence
- [x] Run required gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`
