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
- [x] Public `GET /skill-install.ps1` hosted installer route implemented in `apps/network-web`.
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
- [x] Section includes one-line installer commands (`/skill-install.sh` and `/skill-install.ps1`) and clear agent runtime guidance.

### 17.4 Acceptance evidence
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] `npm run build`
- [x] `curl -sSf http://127.0.0.1:3000/skill.md` returns expected bootstrap content during runtime verification.
- [x] `curl -sSf http://127.0.0.1:3000/skill-install.sh` returns executable installer script.
- [x] `curl -sSf http://127.0.0.1:3000/skill-install.ps1` returns executable installer script.

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
- [x] `owner-link` output returns full `managementUrl` for owner handoff with a short-lived safety warning.

### 23.5 Acceptance evidence
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] `npm run build`

---

## 24) Slice 25: Agent Skill UX Upgrade (Security + Reliability + Contract Fixes)

### 24.1 Security: sensitive stdout redaction (skill wrapper)
- [x] Wrapper redacts fields listed in `sensitiveFields` when `sensitive=true`.
- [x] Owner-link is an explicit exception and remains unredacted so management URL can be delivered in active chat.

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

Note:
- Superseded by Slice 37 (secretless Telegram approvals via agent-auth trade status) and Slice 36 (step-up removed). The checklist below reflects the Slice 34 implementation at the time.

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

---

## 37) Slice 37: Telegram Approvals Without Extra Secret (Skill-Authoritative, Web + Telegram OR)

### 37.1 Canonical/doc sync
- [x] Add Slice 37 goal/DoD + issue mapping to `docs/XCLAW_SLICE_TRACKER.md`.
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` to reflect secretless Telegram approvals and OR convergence semantics.
- [x] Update `docs/api/openapi.v1.yaml` and shared schemas to remove `/api/v1/channel/approvals/decision` and the secret-bearing enable response.
- [x] Update handoff/process artifacts:
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`

### 37.2 Server/API/UI/OpenClaw
- [x] `POST /api/v1/management/approval-channels/update` no longer issues a secret; stores enablement only.
- [x] Delete channel-auth endpoint `/api/v1/channel/approvals/decision` and remove schema.
- [x] OpenClaw Telegram callback approves by calling X-Claw trade status endpoint using `skills.entries.xclaw-agent.apiKey` (agent auth) with idempotency.
- [x] `/agents/:id` "Approval Delivery" card removes secret display and configuration instructions.

### 37.3 Validation + evidence
- [x] Run required gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

## 38) Slice 38: Telegram Approval Prompt Details + Pending Approval De-Dupe (No Spam)

### 38.1 Canonical/doc sync
- [x] Add Slice 38 goal/DoD + issue mapping to `docs/XCLAW_SLICE_TRACKER.md`.
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` with:
  - required Telegram prompt text fields (amount/symbols + tradeId),
  - de-dupe semantics (reuse existing pending tradeId for identical request key),
  - runtime clears local prompt state when trade leaves `approval_pending`.
- [x] Update handoff/process artifacts:
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`

### 38.2 Runtime behavior
- [x] Add local pending-intent persistence file `~/.xclaw-agent/pending-trade-intents.json` with 0600 permissions.
- [x] `trade spot`:
  - [x] checks for matching pending intent and reuses tradeId if `approval_pending`,
  - [x] does not propose new trades while a matching one is pending,
  - [x] resumes execution after approval without creating new tradeId/prompt.
- [x] Approval wait timeout set to 30 minutes.
- [x] Telegram prompt text includes swap summary and deletes message on approval click (OpenClaw patch).
- [x] runtime clears local Telegram prompt state on any non-pending status transition observed.

### 38.3 Validation + evidence
- [x] Run required gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

## 39) Slice 39: Approval Amount Visibility + Gateway Telegram Callback Reliability

### 39.1 UX: amounts visible
- [x] `/agents/:id` Approval Queue shows amount + tokenIn -> tokenOut.
- [x] `/agents/:id` Activity trade rows show amountIn and (when available) amountOut.

### 39.2 Gateway: Telegram callback reliability
- [x] OpenClaw gateway intercepts `xappr|a|<tradeId>|<chainKey>` callbacks and transitions trade `approval_pending -> approved` via agent-auth `POST /api/v1/trades/:tradeId/status`.
- [x] Telegram approval message is deleted after approval click (or converged 409: approved/filled).
- [x] Patch recorded for OpenClaw `2026.2.9` dist build: `patches/openclaw/003_openclaw-2026.2.9-dist-xclaw-approvals.patch`.

### 39.3 Validation + evidence
- [x] Run required gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

## 40) Slice 40: OpenClaw Patch Auto-Apply (Portable, No Restart Loops)

### 40.1 Canonical/doc sync
- [x] Add Slice 40 goal/DoD + issue mapping to `docs/XCLAW_SLICE_TRACKER.md`.
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` with auto-apply + restart-loop guard semantics.
- [x] Update handoff/process artifacts:
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`

### 40.2 Implementation
- [x] Add Python-first patcher that:
  - [x] locates installed OpenClaw package root from `which openclaw`,
  - [x] finds the active Telegram callback handler bundle(s) dynamically (no hardcoded hashed filename),
  - [x] applies patch idempotently using stable anchors and a marker,
  - [x] records local patch state + failure backoff,
  - [x] restarts gateway best-effort only when patch newly applied (cooldown + lock).
- [x] Call patcher from:
  - [x] installer/update flow (`setup_agent_skill.py`),
  - [x] skill wrapper path (`xclaw_agent_skill.py`) to recover after OpenClaw updates.

### 40.3 Validation + evidence
- [x] Run required gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

## 41) Slice 41: Telegram Approve Button Reliability (Patch Correct Gateway Bundle)

### 41.1 Canonical/doc sync
- [x] Add Slice 41 goal/DoD + issue mapping to `docs/XCLAW_SLICE_TRACKER.md`.
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` to reflect that OpenClaw gateway patching must target the bundle(s) used by `dist/index.js` gateway mode (e.g. `dist/reply-*.js`).
- [x] Update handoff/process artifacts:
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`

### 41.2 Implementation
- [x] Update `skills/xclaw-agent/scripts/openclaw_gateway_patch.py` to patch all detected Telegram `callback_query` handler bundles in `dist/` (not only `loader-*.js`) with stable marker/replace semantics.
- [x] Record/update patch artifact under `patches/openclaw/` for OpenClaw `2026.2.9` as needed.

### 41.3 Validation + evidence
- [x] Run required gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

## 42) Slice 42: Telegram Approve+Deny + Approval Decision Chat Feedback + Safer De-Dupe

### 42.1 Canonical/doc sync
- [x] Add Slice 42 goal/DoD + issue mapping to `docs/XCLAW_SLICE_TRACKER.md`.
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md`:
  - [x] Telegram decisions support Approve + Deny.
  - [x] Runtime de-dupe only while status is `approval_pending`.
  - [x] Decision feedback is posted to the active Telegram chat with details and reason (for deny).
- [x] Update handoff/process artifacts:
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`

### 42.2 Implementation
- [x] Runtime:
  - [x] adjust `trade spot` de-dupe semantics (reuse only while `approval_pending`)
  - [x] Telegram prompt includes Approve + Deny buttons
  - [x] when web approval/deny happens while waiting, send a decision message to active Telegram chat
- [x] OpenClaw gateway patch:
  - [x] handle `xappr|a|...` approve and `xappr|r|...` reject
  - [x] on success delete the prompt and send a confirmation message in the same chat with details

### 42.3 Validation + evidence
- [x] Run required gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

## 43) Slice 43: Telegram Callback Idempotency Fix (No `idempotency_conflict`)

### 43.1 Canonical/doc sync
- [x] Add Slice 43 goal/DoD + issue mapping to `docs/XCLAW_SLICE_TRACKER.md`.
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` to document Telegram callback idempotency key and deterministic `at` requirement.
- [x] Update handoff/process artifacts:
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`

### 43.2 Implementation
- [x] Update `skills/xclaw-agent/scripts/openclaw_gateway_patch.py`:
  - [x] use `Idempotency-Key: tg-cb-<callbackId>` for decision transitions,
  - [x] set `at` deterministically from Telegram callback/query timestamp.

### 43.3 Validation + evidence
- [x] Run required gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

## 44) Slice 44: Faster Approval Resume (Lower Poll Interval)

### 44.1 Canonical/doc sync
- [x] Add Slice 44 goal/DoD + issue mapping to `docs/XCLAW_SLICE_TRACKER.md`.
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` to note the tighter approval polling interval during `approval_pending` waits.
- [x] Update handoff/process artifacts:
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`

### 44.2 Implementation
- [x] Runtime: reduce approval wait poll interval to 1s during `approval_pending` wait loops.

### 44.3 Validation + evidence
- [x] Run required gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

## 45) Slice 45: Inline Telegram Approval Buttons (No Extra Prompt Message)

### 45.1 Canonical/doc sync
- [x] Add Slice 45 goal/DoD + issue mapping to `docs/XCLAW_SLICE_TRACKER.md`.
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` to lock "inline buttons on queued message" as preferred Telegram UX.
- [x] Update handoff/process artifacts:
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`

### 45.2 Implementation
- [x] Runtime: disable out-of-band Telegram approval prompt messages by default; allow re-enable via env (`XCLAW_TELEGRAM_OUT_OF_BAND_APPROVAL_PROMPT=1`).
- [x] Skill instructions: require embedding OpenClaw `[[buttons: ...]]` directive in queued Telegram message for `approval_pending` trades.

### 45.3 Validation + evidence
- [x] Run required gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

## 46) Slice 46: Auto-Attach Telegram Approval Buttons To Queued Message

### 46.1 Canonical/doc sync
- [x] Add Slice 46 goal/DoD + issue mapping to `docs/XCLAW_SLICE_TRACKER.md`.
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` to lock that OpenClaw auto-attaches buttons for queued `approval_pending` trade messages.
- [x] Update handoff/process artifacts:
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`

### 46.2 Implementation
- [x] OpenClaw gateway patch:
  - [x] detect queued `approval_pending` trade summary messages and attach Approve/Deny inline keyboard to the same message.

### 46.3 Validation + evidence
- [x] Run required gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

## 47) Slice 47: Fix Telegram Queued Buttons Attach Point (Agent Reply Send Path)

### 47.1 Canonical/doc sync
- [x] Add Slice 47 goal/DoD + issue mapping to `docs/XCLAW_SLICE_TRACKER.md`.
- [x] Update handoff/process artifacts:
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`

### 47.2 Implementation
- [x] OpenClaw gateway patch:
  - [x] attach queued approval buttons in Telegram agent reply send path (`sendTelegramText(bot, ...)`).

### 47.3 Validation + evidence
- [x] Run required gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

## 48) Slice 48: Queued Approval Buttons v3 Upgrade + Logging (Debuggable)

### 48.1 Canonical/doc sync
- [x] Add Slice 48 goal/DoD + issue mapping to `docs/XCLAW_SLICE_TRACKER.md`.
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` to lock that queued-buttons attach emits debug logs and uses normalized matching.
- [x] Update handoff/process artifacts:
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`

### 48.2 Implementation
- [x] OpenClaw gateway patcher:
  - [x] replace any existing queued-buttons v2 injection in `sendTelegramText(...)` with v3 (normalized text + broader `trd_...` extraction).
  - [x] emit gateway logs when queued buttons are attached or skipped for actionable reasons.

### 48.3 Validation + evidence
- [x] Run required gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

## 49) Slice 49: OpenClaw Patcher Safety (Syntax Check + Targeted Bundle)

### 49.1 Canonical/doc sync
- [x] Add Slice 49 goal/DoD + issue mapping to `docs/XCLAW_SLICE_TRACKER.md`.
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` to lock patcher safety requirements (syntax check + targeted bundle).
- [x] Update handoff/process artifacts:
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`

### 49.2 Implementation
- [x] OpenClaw gateway patcher:
  - [x] only patch the canonical gateway bundle(s) (at minimum `dist/reply-*.js`)
  - [x] validate patched JS via `node --check` before writing; refuse to write invalid output.

### 49.3 Validation + evidence
- [x] Run required gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

## 50) Slice 50: Telegram Decision Feedback Routed Through Agent (No Direct Gateway Ack)

### 50.1 Canonical/doc sync
- [x] Add Slice 50 goal/DoD + issue mapping to `docs/XCLAW_SLICE_TRACKER.md`.
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` to lock "route decision feedback through agent pipeline" semantics.
- [x] Update handoff/process artifacts:
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`

### 50.2 Implementation
- [x] OpenClaw gateway patch:
  - [x] on approve/deny, call `processMessage(...)` with a synthetic inbound message (decision + instructions), instead of posting a raw gateway ack.
  - [x] fallback: if synthetic processing fails, post a minimal ack message to the chat.

### 50.3 Validation + evidence
- [x] Run required gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

## 51) Slice 51: Policy Approval Requests (Token Preapprove + Approve All) With Web + Telegram Buttons

### 51.1 Canonical/doc sync
- [x] Add Slice 51 goal/DoD + issue mapping to `docs/XCLAW_SLICE_TRACKER.md`.
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` to lock policy approval request semantics and Telegram callback prefix.
- [x] Update handoff/process artifacts:
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`
- [x] Update API contracts:
  - [x] `docs/api/openapi.v1.yaml`
  - [x] `packages/shared-schemas/json/*`

### 51.2 Data model
- [x] Add migration for policy approval requests table.
- [x] `npm run db:parity`

### 51.3 Implementation
- [x] Server:
  - [x] agent-auth propose policy approval request
  - [x] agent-auth approve/deny policy approval (Telegram callback)
  - [x] management approve/deny policy approval (web UI)
  - [x] management agent-state includes pending policy approvals
- [x] Runtime:
  - [x] add CLI commands to request token/global policy approvals
- [x] OpenClaw gateway patch:
  - [x] auto-attach policy approval buttons to queued message
  - [x] intercept policy approval callbacks and apply decision
  - [x] route decision into agent pipeline (synthetic message + instructions)
- [x] Web UI:
  - [x] show pending policy approvals on `/agents/:id` with Approve/Deny

### 51.4 Validation + evidence
- [x] Run required gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

## 52) Slice 52: Policy Approval Prompts (Agent-Ready queuedMessage + Instructions)

### 52.1 Canonical/doc sync
- [x] Add Slice 52 goal/DoD + issue mapping to `docs/XCLAW_SLICE_TRACKER.md`.
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` to require a runtime `queuedMessage` template for policy approvals.
- [x] Update handoff/process artifacts:
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`

### 52.2 Implementation
- [x] Runtime:
  - [x] policy approval request commands return `queuedMessage` + `agentInstructions` (agent-ready)
- [x] Tests:
  - [x] assert queued message contains `Status: approval_pending` + `Approval ID: ppr_...`

### 52.3 Validation + evidence
- [x] Run required gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

## 53) Slice 53: Policy Approval Revokes (Token + Approve All OFF) With Web + Telegram Buttons

### 53.1 Canonical/doc sync
- [x] Add Slice 53 goal/DoD + issue mapping to `docs/XCLAW_SLICE_TRACKER.md`.
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` to lock revoke request types and semantics.
- [x] Update handoff/process artifacts:
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`

### 53.2 Implementation
- [x] Server:
  - [x] allow propose request types `token_preapprove_remove` and `global_approval_disable`
  - [x] apply revoke requests on approval by writing a new policy snapshot
- [x] Runtime/skill:
  - [x] commands to request revoke token and revoke approve-all (OFF)
- [x] Web UI:
  - [x] policy approval queue shows clear labels for revoke requests

### 53.3 Validation + evidence
- [x] Run required gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

## 54) Slice 54: Policy Approval Reliability Fixes (Token Symbols + Agent Event Types)

### 54.1 Canonical/doc sync
- [x] Add Slice 54 goal/DoD + issue mapping to `docs/XCLAW_SLICE_TRACKER.md`.
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` and skill docs to reflect token symbol support and policy approval event types.

### 54.2 Data model
- [x] Add migration for policy approval lifecycle event enum values.
- [x] `npm run db:parity`

### 54.3 Implementation
- [x] Runtime/skill: allow `policy-preapprove-token USDC` / `policy-revoke-token USDC` (resolve canonical symbol to token address).
- [x] Server: policy approval propose endpoint emits lifecycle events without enum errors.

### 54.4 Validation + evidence
- [x] Run required gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

## 55) Slice 55: Policy Approval De-Dupe (Reuse Pending Request)

### 55.1 Canonical/doc sync
- [x] Add Slice 55 goal/DoD + issue mapping to `docs/XCLAW_SLICE_TRACKER.md`.
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` to lock de-dupe semantics.
- [x] Update handoff/process artifacts:
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`

### 55.2 Data model
- [x] Add index to support de-dupe lookup on `agent_policy_approval_requests`.
- [x] `npm run db:parity`

### 55.3 Implementation
- [x] Server: policy approval propose endpoint reuses existing `approval_pending` request when parameters match.

### 55.4 Validation + evidence
- [x] Run required gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

## 56) Slice 56: Trade Proposal Token Address Canonicalization (USDC Preapprove Fix)

### 56.1 Canonical/doc sync
- [x] Add Slice 56 goal/DoD + issue mapping to `docs/XCLAW_SLICE_TRACKER.md`.
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` to lock address-form `tokenIn`/`tokenOut` proposal behavior for runtime `trade spot`.
- [x] Update handoff/process artifacts:
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`

### 56.2 Implementation
- [x] Runtime: `cmd_trade_spot` proposes `tokenIn`/`tokenOut` as canonical addresses (not symbols).
- [x] Tests: add runtime regression coverage asserting `_post_trade_proposed(...)` receives address-form tokens.

### 56.3 Validation + evidence
- [x] Run required gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

## 57) Slice 57: Trade Execute Symbol Resolution (Prevent ERC20_CALL_FAIL Fallback)

### 57.1 Canonical/doc sync
- [x] Add Slice 57 goal/DoD + issue mapping to `docs/XCLAW_SLICE_TRACKER.md`.
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` to lock symbol/address resolution behavior for `trade execute`.
- [x] Update handoff/process artifacts:
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`

### 57.2 Implementation
- [x] Runtime: `cmd_trade_execute` resolves intent `tokenIn`/`tokenOut` to canonical addresses and removes hardcoded token fallback behavior.
- [x] Tests: add runtime regression coverage for symbol-form intent token execution path.

### 57.3 Validation + evidence
- [x] Run required gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

## 58) Slice 58: Trade Spot Re-Quote After Approval Wait (Prevent Stale SLIPPAGE_NET)

### 58.1 Canonical/doc sync
- [x] Add Slice 58 goal/DoD + issue mapping to `docs/XCLAW_SLICE_TRACKER.md`.
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` to lock re-quote-before-execution behavior for `trade spot`.
- [x] Update handoff/process artifacts:
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`

### 58.2 Implementation
- [x] Runtime: `cmd_trade_spot` recomputes `expectedOut` and `amountOutMin` after approval wait and right before swap tx.
- [x] Tests: add runtime regression coverage asserting swap calldata minOut uses post-approval quote.

### 58.3 Validation + evidence
- [x] Run required gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

## 59) Slice 59: Trade Execute Amount Units Fix (Prevent 50 -> 50 Wei)

### 59.1 Canonical/doc sync
- [x] Add Slice 59 goal/DoD + issue mapping to `docs/XCLAW_SLICE_TRACKER.md`.
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` to lock human-amount decimal conversion behavior in `trade execute`.
- [x] Update handoff/process artifacts:
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`

### 59.2 Implementation
- [x] Runtime: `cmd_trade_execute` parses `amountIn` as human token amount using tokenIn decimals.
- [x] Tests: add runtime regression coverage asserting `amountIn=5` becomes `5e18` units for 18-decimals token on approve/swap path.

### 59.3 Validation + evidence
- [x] Run required gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

## 60) Slice 60: Prompt Normalization for USD Stablecoin + ETH->WETH Semantics

### 60.1 Canonical/doc sync
- [x] Add Slice 60 goal/DoD + issue mapping to `docs/XCLAW_SLICE_TRACKER.md`.
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` to lock natural-language trade intent normalization for `$` and `ETH`.
- [x] Update skill docs/contracts:
  - [x] `skills/xclaw-agent/SKILL.md`
  - [x] `skills/xclaw-agent/references/commands.md`
- [x] Update handoff/process artifacts:
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`

### 60.2 Implementation
- [x] Prompt contract:
  - [x] `$` amount intent maps to stablecoin-denominated trade intent.
  - [x] `ETH` trade intent maps to `WETH`.
  - [x] if multiple stablecoins have non-zero balance, ask user to choose stablecoin before proposing trade.

### 60.3 Validation + evidence
- [x] Run required gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

## 61) Slice 61: Channel-Aware Approval Routing (Telegram vs Web Management Link)

### 61.1 Canonical/doc sync
- [x] Add Slice 61 goal/DoD + issue mapping to `docs/XCLAW_SLICE_TRACKER.md`.
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` to lock channel-aware approval routing behavior.
- [x] Update skill docs/contracts:
  - [x] `skills/xclaw-agent/SKILL.md`
  - [x] `skills/xclaw-agent/references/commands.md`
- [x] Update handoff/process artifacts:
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`

### 61.2 Implementation
- [x] Prompt contract:
  - [x] non-Telegram channels must not emit Telegram button directives/callback payloads.
  - [x] non-Telegram approval handoff uses web management surface (`xclaw.trade`) with management link (`owner-link`).
  - [x] Telegram-focused channels continue inline approval buttons.

### 61.3 Validation + evidence
- [x] Run required gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

## 62) Slice 62: Policy Approval Telegram Decision Feedback Reliability

### 62.1 Canonical/doc sync
- [x] Add Slice 62 goal/DoD + issue mapping to `docs/XCLAW_SLICE_TRACKER.md`.
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` to lock immediate policy decision confirmation behavior for Telegram callbacks.
- [x] Update handoff/process artifacts:
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`

### 62.2 Implementation
- [x] OpenClaw gateway patch:
  - [x] add decision-ack marker/version bump for upgrade detection,
  - [x] on successful `xpol` callback, send deterministic confirmation chat message (`Approved/Denied policy approval ...`) and still route decision to agent pipeline.
- [x] Apply patcher to installed OpenClaw bundle and verify patch result.

### 62.3 Validation + evidence
- [x] Run required gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

## 63) Slice 63: Prompt Contract - Hide Internal Commands In User Replies

### 63.1 Canonical/doc sync
- [x] Add Slice 63 goal/DoD + issue mapping to `docs/XCLAW_SLICE_TRACKER.md`.
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` to lock no-command-leak behavior for user-facing replies.
- [x] Update skill docs/contracts:
  - [x] `skills/xclaw-agent/SKILL.md`
  - [x] `skills/xclaw-agent/references/commands.md`
- [x] Update handoff/process artifacts:
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`

### 63.2 Implementation
- [x] Prompt contract:
  - [x] internal tool/CLI command strings are hidden in normal user-facing chat responses.
  - [x] exact command syntax is provided only when the user explicitly asks for commands.

### 63.3 Validation + evidence
- [x] Run required gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

## 64) Slice 64: Policy Callback Convergence Ack (409 Still Replies)

### 64.1 Canonical/doc sync
- [x] Add Slice 64 goal/DoD + issue mapping to `docs/XCLAW_SLICE_TRACKER.md`.
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` to lock converged `409` policy callback confirmation behavior.
- [x] Update handoff/process artifacts:
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`

### 64.2 Implementation
- [x] OpenClaw gateway callback patch:
  - [x] on policy callback `409` with terminal `currentStatus`, clear inline buttons (preserve message text) and send deterministic `Approved/Denied policy approval ...` confirmation.
  - [x] bump patch marker/schema so existing patched bundles upgrade.
  - [x] re-apply patcher to installed OpenClaw and verify marker/branch presence.

### 64.3 Validation + evidence
- [x] Run required gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

## 65) Slice 65: Telegram Decision UX - Keep Text, Remove Buttons

### 65.1 Canonical/doc sync
- [x] Add Slice 65 goal/DoD + issue mapping to `docs/XCLAW_SLICE_TRACKER.md`.
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` to lock Telegram callback UX (keep text, clear buttons).
- [x] Update handoff/process artifacts:
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`

### 65.2 Implementation
- [x] OpenClaw gateway callback patch:
  - [x] success path clears inline keyboard and preserves message text for both trade and policy callbacks.
  - [x] converged `409` path clears inline keyboard and preserves message text.
  - [x] bump patch marker/schema to force upgrade on existing patched bundles.
  - [x] apply patcher and verify installed bundle contains v6 marker + no callback `deleteMessage` in decision branches.

### 65.3 Validation + evidence
- [x] Run required gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

## 66) Slice 66: Policy Approval Consistency (Pending De-Dupe Race + Web Reflection)

### 66.1 Canonical/doc sync
- [x] Add Slice 66 goal/DoD + issue mapping to `docs/XCLAW_SLICE_TRACKER.md`.
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` for policy de-dupe concurrency and management view reflection requirements.
- [x] Update handoff/process artifacts:
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`

### 66.2 Implementation
- [x] Server:
  - [x] serialize identical policy propose requests with advisory transaction lock and perform de-dupe check + insert in one transaction.
  - [x] preserve existing response contract (`policyApprovalId`, `status=approval_pending`) while preventing duplicate pending rows.
- [x] Web:
  - [x] `/agents/:id` management screen polls management state while open so Telegram/web policy approve/deny outcomes reflect without manual reload.

### 66.3 Validation + evidence
- [x] Run required gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

## 67) Slice 67: Approval Decision Feedback + Activity Visibility Reliability

### 67.1 Canonical/doc sync
- [x] Add Slice 67 goal/DoD + issue mapping to `docs/XCLAW_SLICE_TRACKER.md`.
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` for:
  - [x] deterministic Telegram decision confirmation for both trade + policy callbacks,
  - [x] policy lifecycle visibility in public activity feed.
- [x] Update handoff/process artifacts:
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`

### 67.2 Implementation
- [x] OpenClaw gateway patch:
  - [x] deterministic confirmation for `xappr` and `xpol` on success path.
  - [x] deterministic confirmation for converged terminal `409` path.
  - [x] preserve queued message text and clear inline buttons.
- [x] Web/public activity:
  - [x] `/api/v1/public/activity` includes `policy_*` events and resolves policy token address from payload.
  - [x] `/agents/:id` activity labels policy lifecycle events and renders policy token context cleanly.

### 67.3 Validation + evidence
- [x] Run required gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

## 68) Slice 68: Management Policy Approval History Visibility

### 68.1 Canonical/doc sync
- [x] Add Slice 68 goal/DoD + issue mapping to `docs/XCLAW_SLICE_TRACKER.md`.
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` to require policy approval history visibility in management UI.
- [x] Update handoff/process artifacts:
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`

### 68.2 Implementation
- [x] API: `/api/v1/management/agent-state` returns recent policy approval history rows (pending+terminal statuses, timestamps, reason).
- [x] UI: `/agents/:id` Policy Approvals card shows recent policy requests, so approved/rejected requests remain visible after leaving pending queue.

### 68.3 Validation + evidence
- [x] Run required gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

## 69) Slice 69: Dashboard Full Rebuild (Global Landing Analytics + Discovery)

### 69.1 Canonical/doc sync
- [x] Add Slice 69 goal/DoD + issue mapping to `docs/XCLAW_SLICE_TRACKER.md`.
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` with locked Dashboard rebuild contract (layout + components + theme tokens + mobile order + scope behavior).
- [x] Update handoff/process artifacts:
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`

### 69.2 Implementation
- [x] Replace dashboard page implementation from scratch for `/` and add `/dashboard` alias route.
- [x] Add dashboard-only shell (left sidebar + sticky topbar) while preserving non-dashboard shell behavior.
- [x] Implement dashboard component inventory:
  - [x] `AppShellSidebar`
  - [x] `TopBarSearch`
  - [x] `ChainSelector` (dashboard all-chains capable)
  - [x] `ScopeSelector` (owner-only)
  - [x] `DarkModeToggle` (sun/moon + localStorage)
  - [x] `KPIStatCard` strip
  - [x] `ChartPanel` (chain/system view switcher + time range + line/bar)
  - [x] `LiveTradeFeedList`
  - [x] `TopAgentsLeaderboard`
  - [x] `ChainBreakdownCard`
  - [x] `TradeSnapshotCard`
  - [x] `TrendingAgentCardGrid`
  - [x] `DocLinkCard`
- [x] Keep existing API contracts and derive unsupported metrics with explicit estimated labeling.
- [x] Add `GET /api/v1/public/dashboard/summary` for chain-aware KPI + series + zero-state chain breakdown aggregation.

### 69.3 Validation + evidence
- [x] Run required gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
- [ ] Record functional verification evidence for:
  - [x] `/` and `/dashboard` parity
  - [ ] owner vs anonymous scope behavior
  - [ ] mobile ordering at `390x844`
  - [ ] desktop layout at `1440x900`
  - [ ] dark/light toggle persistence.

---

## 69A) Slice 69A: Dashboard Agent Trade Room Reintegration

### 69A.1 Canonical/doc sync
- [x] Add Slice 69A goal/DoD + issue mapping to `docs/XCLAW_SLICE_TRACKER.md`.
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` with locked dashboard Agent Trade Room placement/filtering/read-only contract.
- [x] Update handoff/process artifacts:
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`

### 69A.2 Implementation
- [x] Extend dashboard data load with `GET /api/v1/chat/messages?limit=40`.
- [x] Add chain/scope-filtered room preview (`max 8`) to dashboard right rail under Live Trade Feed.
- [x] Add room card states: loading skeleton, empty hint, card-scoped degraded error.
- [x] Add `View all` route to `/room` and implement read-only room page.

### 69A.3 Validation + evidence
- [x] Run required gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
- [ ] Record functional verification evidence:
  - [x] room card appears below live feed on dashboard
  - [ ] chain filter updates room rows
  - [ ] owner `My agents` scope filters room rows
  - [x] `/room` renders read-only full room stream.

---

## 70) Slice 70: Single-Trigger Spot Flow + Guaranteed Final Result Reporting

### 70.1 Canonical/doc sync
- [x] Add Slice 70 goal/DoD + issue mapping to `docs/XCLAW_SLICE_TRACKER.md`.
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` with locked single-trigger Telegram spot flow semantics.
- [x] Update handoff/process artifacts:
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`

### 70.2 Implementation
- [x] Runtime: add persisted pending spot-flow context (`trade spot` approval-pending path).
- [x] Runtime: add `approvals resume-spot --trade-id <id> --chain <key> --json`.
- [x] Runtime: clear pending spot-flow context on terminal outcomes.
- [x] Skill wrapper/docs:
  - [x] add `trade-resume <trade_id>` in `skills/xclaw-agent/scripts/xclaw_agent_skill.py`
  - [x] update `skills/xclaw-agent/SKILL.md` + `skills/xclaw-agent/references/commands.md`
- [x] OpenClaw gateway patch:
  - [x] on `xappr approve` success, trigger guarded async `resume-spot` execution path.
  - [x] emit deterministic final trade result message in same Telegram chat/thread.
  - [x] route synthetic final result message into agent pipeline.
  - [x] enforce duplicate-callback in-flight guard for same `(tradeId, chainKey)`.

### 70.3 Validation + evidence
- [x] Run required gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] runtime unit tests
- [ ] Record functional verification evidence:
  - [ ] one-trigger Telegram `trade spot` approval-required path auto-resumes after Approve.
  - [ ] Deny yields refusal feedback in chat.
  - [ ] final result message always includes status/tradeId/chain and txHash when available.
  - [ ] duplicate Approve callbacks do not trigger duplicate execution.

---

## 71) Slice 71: Single-Trigger Outbound Transfers + Runtime-Canonical Transfer Approvals

### 71.1 Canonical/doc sync
- [x] Add Slice 71 goal/DoD + issue mapping to `docs/XCLAW_SLICE_TRACKER.md`.
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` with locked transfer-approval contract (`xfr_...`, runtime-canonical).
- [x] Update handoff/process artifacts:
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`

### 71.2 Implementation
- [x] Runtime transfer approval orchestration:
  - [x] local pending transfer flow state + local transfer policy state.
  - [x] `approvals decide-transfer`, `approvals resume-transfer`.
  - [x] `transfers policy-get`, `transfers policy-set`.
  - [x] `wallet-send` / `wallet-send-token` approval-required queued path + auto execution when allowed.
- [x] OpenClaw gateway patch:
  - [x] support `xfer|a|<approvalId>|<chainKey>` and `xfer|r|...` callbacks.
  - [x] deterministic transfer final result chat message.
  - [x] synthetic transfer-result route into agent pipeline.
- [x] API/mirror + management:
  - [x] agent transfer approval mirror endpoint.
  - [x] agent transfer policy get/mirror endpoints.
  - [x] management transfer approvals list/decision endpoints.
  - [x] management transfer policy update endpoint.
- [x] `/agents/:id` management UI:
  - [x] transfer approval policy controls.
  - [x] transfer approvals queue + history.

### 71.3 Validation + evidence
- [x] Run required gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] runtime unit tests
- [ ] Record functional verification evidence:
  - [ ] Telegram approve path (`xfer`) executes once and reports tx result.
  - [ ] Telegram deny path reports refusal and no execution.
  - [ ] Web approve/deny path converges to terminal transfer status.
  - [ ] duplicate callback does not double execute.

---

## 72) Slice 72: Transfer Policy-Override Approvals (Keep Gate/Whitelist)

### 72.1 Canonical/doc sync
- [x] Update source-of-truth to lock one-off override behavior for policy-blocked transfer approvals.
- [x] Add Slice 72 tracker entry + roadmap checklist.
- [x] Update wallet contract + OpenAPI/schema docs for new policy-block/override fields.

### 72.2 Implementation
- [x] Runtime transfer orchestration evaluates outbound gate/whitelist and routes blocked requests to `xfr_...` approvals.
- [x] Runtime execution enforces one-off override semantics for approved blocked-origin flows.
- [x] Transfer mirror payload includes:
  - [x] `policyBlockedAtCreate`
  - [x] `policyBlockReasonCode`
  - [x] `policyBlockReasonMessage`
  - [x] `executionMode`
- [x] Web/API read-model paths expose and render policy-block + override indicators.
- [x] Gateway transfer final message includes override mode line when applicable.

### 72.3 Validation + evidence
- [x] Run required gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] runtime unit tests

---

## 73) Slice 73: Agent Page Full Frontend Refresh (Dashboard-Aligned, API-Preserving)

### 73.1 Canonical/doc sync
- [x] Add Slice 73 goal/DoD + issue mapping to `docs/XCLAW_SLICE_TRACKER.md`.
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` with locked Slice 73 frontend contract.
- [x] Update handoff/process artifacts:
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`

### 73.2 Implementation
- [x] Replace `/agents/:id` UI with dashboard-aligned shell and card system.
- [x] Shift `/agents/:id` from tab-primary layout to wallet-first continuous workspace:
  - [x] wallet controls/header + assets and approvals as primary module
  - [x] unified wallet activity timeline (trades/transfers/deposits/approvals)
  - [x] integrated approval history/actions in wallet context
  - [x] secondary modules (copy/risk/ops/audit) demoted below primary wallet stack
- [x] Finalize `/agents/:id` as sidebar-preserved wallet-native shell:
  - [x] keep dashboard sidebar shell framing on this route
  - [x] keep compact KPI chips under wallet header
  - [x] remove `Secondary Operations` and transfer/outbound policy editor controls
  - [x] keep copy relationships as list/delete only with create flow directed to `/explore`
- [x] Preserve existing API integration for profile/trades/activity/management actions.
- [x] Keep owner controls reachable (policy approvals, approval decisions, limits, audit, withdraw, pause/resume, revoke-all).
- [x] Enforce viewer lock behavior for owner-only controls.
- [x] Add explicit placeholder states for unsupported API-backed modules.
- [x] Add frontend view-model/capability modules:
  - [x] `apps/network-web/src/lib/agent-page-view-model.ts`
  - [x] `apps/network-web/src/lib/agent-page-capabilities.ts`
- [x] Add route-local stylesheet:
  - [x] `apps/network-web/src/app/agents/[agentId]/page.module.css`

### 73.3 Validation + evidence
- [x] Run required gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
- [ ] Record functional verification evidence:
  - [x] viewer mode hides owner actions
  - [x] owner mode action controls operate via existing endpoints
  - [x] approval decision buttons update queue state
  - [ ] dark/light parity screenshots at desktop breakpoints

---

## 74) Slice 74: Approvals Center v1 (Frontend-Only, API-Preserving)

### 74.1 Canonical/doc sync
- [x] Add Slice 74 goal/DoD + issue mapping to `docs/XCLAW_SLICE_TRACKER.md`.
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` with locked Slice 74 frontend contract.
- [x] Update handoff/process artifacts:
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`

### 74.2 Implementation
- [x] Add `/approvals` route with dashboard-aligned shell and sticky topbar.
- [x] Wire owner context + queue loading with existing management APIs.
- [x] Wire decision actions for trade/policy/transfer approvals using existing endpoints.
- [x] Add frontend view-model/capability modules:
  - [x] `apps/network-web/src/lib/approvals-center-view-model.ts`
  - [x] `apps/network-web/src/lib/approvals-center-capabilities.ts`
- [x] Add route-local stylesheet:
  - [x] `apps/network-web/src/app/approvals/page.module.css`
- [x] Add explicit placeholders/disabled actions for unsupported modules (allowances inventory, cross-agent/risk enrichments, bulk actions).

### 74.3 Validation + evidence
- [x] Run required gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
- [ ] Record functional verification evidence:
  - [x] viewer mode empty state + no owner actions
  - [x] owner mode queue loads and decision actions execute
  - [x] placeholder sections remain disabled and explicit
  - [ ] desktop dark/light screenshots for `/approvals`

---

## 75) Slice 75: Settings & Security v1 (`/settings`) Frontend Refresh

### 75.1 Canonical/doc sync
- [x] Add Slice 75 goal/DoD + issue mapping to `docs/XCLAW_SLICE_TRACKER.md`.
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` with locked Slice 75 frontend contract.
- [x] Update handoff/process artifacts:
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`

### 75.2 Implementation
- [x] Add `/settings` route with dashboard-aligned shell and sticky topbar.
- [x] Keep `/status` unchanged as diagnostics.
- [x] Add tabs `Access`, `Security`, `Danger Zone` (hide Notifications in v1).
- [x] Wire existing session/device actions (session select/logout + pause/resume/revoke-all).
- [x] Add frontend capability module:
  - [x] `apps/network-web/src/lib/settings-security-capabilities.ts`
- [x] Add route-local stylesheet:
  - [x] `apps/network-web/src/app/settings/page.module.css`
- [x] Add explicit placeholders/disabled controls for unsupported global/allowance modules; keep per-agent remove-access device-local in settings.
- [x] Update nav links to point Settings & Security to `/settings` on dashboard, agent page, approvals page.

### 75.3 Validation + evidence
- [x] Run required gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
- [ ] Record functional verification evidence:
  - [x] viewer/no-session settings state
  - [x] owner session controls wired
  - [x] danger actions route to existing endpoints
  - [x] placeholder modules remain disabled with explicit copy
  - [ ] desktop dark/light screenshots for `/settings`

---

## 76) Slice 76: Explore / Agent Listing Full Frontend Refresh (`/explore` Canonical)

### 76.1 Canonical/doc sync
- [x] Add Slice 76 goal/DoD + issue mapping to `docs/XCLAW_SLICE_TRACKER.md`.
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` with locked Slice 76 frontend contract.
- [x] Update handoff/process artifacts:
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`

### 76.2 Implementation
- [x] Add canonical Explore route:
  - [x] `apps/network-web/src/app/explore/page.tsx`
  - [x] `apps/network-web/src/app/explore/page.module.css`
- [x] Keep `/agents` compatibility alias to `/explore`.
- [x] Add Explore frontend modules:
  - [x] `apps/network-web/src/lib/explore-page-view-model.ts`
  - [x] `apps/network-web/src/lib/explore-page-capabilities.ts`
- [x] Wire existing data surfaces:
  - [x] public agents + leaderboard
  - [x] owner session context
  - [x] copy subscriptions get/create/update/delete
- [x] Add explicit placeholders/disabled controls for unsupported enriched filters/metadata.
- [x] Update dashboard/agent/approvals/settings nav links to `/explore`.
- [x] Treat `/explore` as dashboard-shell route in `public-shell`.

### 76.3 Validation + evidence
- [x] Run required gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
- [ ] Record functional verification evidence:
  - [x] viewer mode (all/favorites, gated copy CTA)
  - [x] owner mode (my agents + copy-trade save flow)
  - [x] placeholders for unsupported filter dimensions
  - [ ] desktop dark/light screenshots for `/explore`

---

## 77) Slice 77: Agent Wallet Page MetaMask-Style Full-Screen Refactor (`/agents/:id`)

### 77.1 Canonical/doc sync
- [x] Add Slice 77 goal/DoD + issue mapping to `docs/XCLAW_SLICE_TRACKER.md`.
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` Slice 73 contract for sidebar-preserved wallet-native shell.
- [x] Update handoff/process artifacts:
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`

### 77.2 Implementation
- [x] Refactor `/agents/:id` into wallet-native composition while preserving dashboard sidebar framing.
- [x] Keep chain selector + theme toggle in compact utility bar.
- [x] Keep compact KPI chip row below wallet header.
- [x] Recompose wallet-first stack:
  - [x] Assets & Approvals
  - [x] Wallet Activity
  - [x] Approval History
  - [x] Withdraw
  - [x] Copy relationships (list/delete only)
  - [x] Limit Orders
  - [x] Management Audit Log
- [x] Remove `Secondary Operations` card and transfer/outbound policy editor controls.
- [x] Preserve existing owner/viewer auth boundaries and management endpoint wiring.

### 77.3 Validation + evidence
- [x] Run required gates:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
- [ ] Record functional verification evidence:
  - [x] transfer/outbound policy editor controls removed from `/agents/:id`
  - [x] copy relationship create guidance points to `/explore`
  - [x] approval/withdraw/order/audit surfaces remain reachable
  - [ ] desktop dark/light screenshots for `/agents/:id`

---

## 78) Slice 78: Root Landing Refactor + Install-First Onboarding (`/`)

### 78.1 Canonical/doc sync
- [x] Add Slice 78 goal/DoD + issue mapping to `docs/XCLAW_SLICE_TRACKER.md`.
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` with locked root landing/install-first contract.

### 78.2 Implementation
- [x] Replace root `/` dashboard rendering with premium info-only landing composition.
- [x] Add finished-product header with section anchors and CTA pair.
- [x] Add install-first onboarding/quickstart module with selector:
  - [x] `Human` mode with copyable `curl -fsSL https://xclaw.trade/skill-install.sh | bash`.
  - [x] `Human` mode includes Windows equivalent `irm https://xclaw.trade/skill-install.ps1 | iex`.
  - [x] `Agent` mode with copyable prompt `Please follow directions at https://xclaw.trade/skill.md`.
- [x] Add live proof band sourced from existing public/status APIs.
- [x] Add trust-first section stack (capabilities, lifecycle, trust/safety, observer, developers, FAQ, final CTA).
- [x] Keep functional dashboard operations on `/dashboard`.
- [x] Remove left menu/sidebar from root landing and keep primary CTA routing to `/dashboard`.

### 78.3 Validation + evidence
- [x] Run required gates sequentially:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `pm2 restart all` (after successful build; not parallel)

---

## 79) Slice 79: Agent-Skill x402 Send/Receive Runtime (No Webapp Integration Yet)

### 79.1 Canonical/doc sync
- [x] Add Slice 79 goal/DoD + issue mapping to `docs/XCLAW_SLICE_TRACKER.md`.
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` with locked x402 runtime/skill contract and network rollout constraints.
- [x] Update `docs/api/WALLET_COMMAND_CONTRACT.md` for x402 command extensions.
- [x] Update handoff/process artifacts:
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`

### 79.2 Implementation
- [x] Add runtime x402 modules:
  - [x] `apps/agent-runtime/xclaw_agent/x402_runtime.py`
  - [x] `apps/agent-runtime/xclaw_agent/x402_tunnel.py`
  - [x] `apps/agent-runtime/xclaw_agent/x402_policy.py`
  - [x] `apps/agent-runtime/xclaw_agent/x402_state.py`
- [x] Add runtime CLI command group `x402`:
  - [x] `serve-start|serve-status|serve-stop`
  - [x] `pay|pay-resume|pay-decide`
  - [x] `policy-get|policy-set`
  - [x] `networks`
- [x] Add skill wrapper x402 commands + `request-x402-payment` auto-start path.
- [x] Add installer x402 portability updates:
  - [x] Windows `.cmd` + `.ps1` launcher generation
  - [x] cloudflared install/resolve path for Linux/macOS/Windows
- [x] Add x402 config artifact: `config/x402/networks.json` (`base_sepolia/base enabled`, `kite_* disabled`).
- [x] Add schema artifacts:
  - [x] `packages/shared-schemas/json/x402-runtime-state.schema.json`
  - [x] `packages/shared-schemas/json/x402-serve-response.schema.json`
  - [x] `packages/shared-schemas/json/x402-pay-request.schema.json`
  - [x] `packages/shared-schemas/json/x402-pay-response.schema.json`
  - [x] `packages/shared-schemas/json/x402-payment-approval.schema.json`

### 79.3 Validation + evidence
- [x] Run required gates sequentially:
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_x402_runtime.py -v`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_x402_skill_wrapper.py -v`
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `pm2 restart all` (after successful build; when PM2 is available)
- [x] Record functional verification evidence:
  - [x] `x402 serve-start` returns shareable `paymentUrl`.
  - [x] `x402 pay` approval-required path returns `xfr_...` + `approval_pending`.
  - [x] `x402 pay-decide approve` resumes once and yields terminal result.
  - [x] `x402 pay-decide deny` yields terminal `rejected` with no execution.

---

## 80) Slice 80: Hosted x402 on `/agents/[agentId]` + Agent-Originated Send + Loopback Self-Pay

### 80.1 Canonical/doc sync
- [x] Add Slice 80 goal/DoD + issue mapping to `docs/XCLAW_SLICE_TRACKER.md`.
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` with hosted x402 contract (server receive endpoint + agent-originated outbound send + loopback path).
- [x] Update `docs/api/WALLET_COMMAND_CONTRACT.md` for x402 outbound mirror obligations and `xfr_...` approval reuse.
- [x] Update `docs/api/openapi.v1.yaml` and shared schema artifacts for new x402 routes.
- [x] Update handoff artifacts (`docs/CONTEXT_PACK.md`, `spec.md`, `tasks.md`, `acceptance.md`).

### 80.2 Implementation
- [x] Add migration: `infrastructure/migrations/0017_slice80_hosted_x402.sql`.
- [x] Add x402 API surfaces under `apps/network-web/src/app/api/v1/agent/x402/*`.
- [x] Add management x402 read/receive-link surfaces under `apps/network-web/src/app/api/v1/management/x402/*`.
- [x] Add hosted payer endpoint: `apps/network-web/src/app/api/v1/x402/pay/[agentId]/[linkToken]/route.ts`.
- [x] Extend transfer approvals mirror table write/read/decision path with nullable x402 metadata.
- [x] Runtime x402 mirrors outbound flow and maps approvals to `xfr_...`.
- [x] `/agents/[agentId]` merges x402 history rows into wallet activity with source labeling and receive-link panel.
- [x] Hosted receive supersedes local tunnel path in runtime/skill (`x402 receive-request`/`request-x402-payment`), removing cloudflared setup dependency.

### 80.3 Validation + evidence
- [x] Run required gates sequentially:
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_x402_runtime.py -v`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_x402_skill_wrapper.py -v`
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `pm2 restart all` (after successful build; not parallel)
- [x] Record evidence:
  - [x] hosted x402 endpoint returns `402` before payment.
  - [x] hosted x402 endpoint returns `200` after payment and `410` when expired.
  - [x] outbound approval-required x402 appears in transfer approvals queue as `approval_source=x402`.
  - [x] loopback self-pay records both outbound and inbound rows.

---

## 81) Slice 81: Explore v2 Full Flush (No Placeholders)

### 81.1 Canonical/doc sync
- [x] Add Slice 81 goal/DoD + issue mapping to `docs/XCLAW_SLICE_TRACKER.md`.
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` with locked Slice 81 Explore v2 contract.
- [x] Update handoff/process artifacts:
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`
- [x] Update OpenAPI and shared schemas for Explore v2 route/field additions.

### 81.2 Implementation
- [x] Add migration `infrastructure/migrations/0018_slice81_explore_v2.sql` with `agent_explore_profile` + constraints/indexes.
- [x] Extend `GET /api/v1/public/agents` with:
  - [x] strategy/venue/risk/minFollowers/minVolume/activeWithin/verified filters
  - [x] server-driven sorting/pagination with added `followers` sort
  - [x] `exploreProfile`, `verified`, `followerMeta` response fields
- [x] Extend `GET /api/v1/public/leaderboard` with `verified` and `exploreProfile`.
- [x] Add owner-managed Explore profile routes:
  - [x] `GET /api/v1/management/explore-profile`
  - [x] `PUT /api/v1/management/explore-profile`
- [x] Replace Explore placeholders with functional controls:
  - [x] strategy multi-select
  - [x] venue multi-select
  - [x] risk select
  - [x] verified-only toggle
  - [x] advanced filter drawer
  - [x] segmented section control
  - [x] URL-state synchronization
  - [x] verified badges + follower-rich card metadata

### 81.3 Validation + evidence
- [x] Run required gates sequentially:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `pm2 restart all` (after successful build; not parallel)
- [x] Record evidence:
  - [x] no Explore placeholder labels/messages remain for strategy/risk/venue/advanced/follower enrichments
  - [x] functional URL-deep-link filter replay
  - [x] owner-managed Explore profile edit reflects on public Explore cards
  - [x] owner/viewer copy-trade gating remains intact

---

## 82) Slice 82: Track-Not-Copy Pivot (Saved Agents -> OpenClaw Watchlist)

### 82.1 Canonical/doc sync
- [x] Add Slice 82 goal/DoD + issue mapping to `docs/XCLAW_SLICE_TRACKER.md`.
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` with locked track-not-copy product contract.
- [x] Update handoff/process artifacts:
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`
- [x] Update `docs/api/WALLET_COMMAND_CONTRACT.md` with tracked runtime/skill obligations.
- [x] Update `docs/api/openapi.v1.yaml` with tracked routes and copy-route deprecation notes.

### 82.2 Implementation
- [x] Add migration `infrastructure/migrations/0020_slice82_agent_tracking.sql`.
- [x] Add tracked APIs:
  - [x] `apps/network-web/src/app/api/v1/management/tracked-agents/route.ts`
  - [x] `apps/network-web/src/app/api/v1/management/tracked-trades/route.ts`
  - [x] `apps/network-web/src/app/api/v1/agent/tracked-agents/route.ts`
  - [x] `apps/network-web/src/app/api/v1/agent/tracked-trades/route.ts`
- [x] Extend management agent-state payload with `trackedAgents` and `trackedRecentTrades`.
- [x] Pivot Explore UI from copy CTA/modal to tracked-agent flow.
- [x] Pivot `/agents/[agentId]` copy module to tracked-agents module.
- [x] Sync left-rail saved icons to server tracked list for owner sessions with local fallback.
- [x] Extend runtime and skill:
  - [x] `xclaw-agent dashboard` includes tracked summaries
  - [x] `xclaw-agent tracked list`
  - [x] `xclaw-agent tracked trades`
  - [x] `xclaw_agent_skill.py tracked-list|tracked-trades`
- [x] Add/extend tracked schemas under `packages/shared-schemas/json/`.

### 82.3 Validation + evidence
- [x] Run required gates sequentially:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `pm2 restart all`
- [x] Runtime tests:
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_tracked_runtime.py -v`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_x402_skill_wrapper.py -v`

---

## 83) Slice 83: Kite AI Testnet Parity (Runtime + Web + DEX + x402)

### 83.1 Canonical/doc sync
- [x] Add Slice 83 goal/DoD + issue mapping to `docs/XCLAW_SLICE_TRACKER.md`.
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` with locked Kite testnet parity contract.
- [x] Update handoff/process artifacts:
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`
- [x] Update `docs/api/WALLET_COMMAND_CONTRACT.md` and `docs/api/openapi.v1.yaml` for chain examples/contracts.

### 83.2 Implementation
- [x] Add `config/chains/kite_ai_testnet.json` with locked chain/rpc/explorer/router/factory/token constants.
- [x] Enable Kite testnet in `config/x402/networks.json` and keep `kite_ai_mainnet` disabled.
- [x] Add runtime DEX adapter abstraction (`UniswapV2RouterAdapter`, `KiteTesseractAdapter`) and route selection by chain.
- [x] Ensure runtime wallet/trade/limit/tracked/x402 command families accept `kite_ai_testnet`.
- [x] Ensure web chain selector includes `Kite AI Testnet` and status provider probes include it.
- [x] Ensure API validation/hints include `kite_ai_testnet` where chain-config-backed.
- [x] Keep faucet endpoint Base-only with structured unsupported response for Kite.

### 83.3 Validation + evidence
- [x] Run required gates sequentially:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `pm2 restart all`
- [x] Runtime tests:
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_x402_runtime.py -v`
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_dex_adapter.py -v`

---

## 84) Slice 84: Multi-Network Faucet Parity (Base Sepolia + Kite Testnet)

### 84.1 Canonical/doc sync
- [x] Add Slice 84 goal/DoD + issue mapping to `docs/XCLAW_SLICE_TRACKER.md`.
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` with locked faucet parity contract.
- [x] Update handoff/process artifacts:
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`
- [x] Update `docs/api/WALLET_COMMAND_CONTRACT.md` and `docs/api/openapi.v1.yaml`.

### 84.2 Implementation
- [x] Refactor `POST /api/v1/agent/faucet/request` to support `base_sepolia|kite_ai_testnet|hedera_testnet`.
- [x] Add selectable assets (`native|wrapped|stable`) with chain-canonical symbol/address mapping.
- [x] Add `GET /api/v1/agent/faucet/networks` capability endpoint.
- [x] Extend runtime CLI (`faucet-request --asset ...`, `faucet-networks`).
- [x] Extend skill wrapper (`faucet-request [chain] [asset ...]`, `faucet-networks`).
- [x] Keep daily limiter key scope per-agent/per-chain.

### 84.3 Validation + evidence
- [x] Runtime tests:
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`
- [x] Run required gates sequentially:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `pm2 restart all`

---

## 85) Slice 85: EVM-Wide Portability Foundation (Chain-Agnostic Core, x402 Unchanged)

### 85.1 Canonical/doc sync
- [x] Add Slice 85 goal/DoD + issue mapping to `docs/XCLAW_SLICE_TRACKER.md`.
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` with locked portability contract and x402 scope boundary.
- [x] Update handoff/process artifacts:
  - [x] `docs/CONTEXT_PACK.md`
  - [x] `spec.md`
  - [x] `tasks.md`
  - [x] `acceptance.md`
- [x] Update `docs/api/WALLET_COMMAND_CONTRACT.md` and `docs/api/openapi.v1.yaml`.

### 85.2 Implementation
- [x] Extend `config/chains/*.json` contract with `family`, `enabled`, `uiVisible`, `nativeCurrency`, and `capabilities`.
- [x] Add migration `0021_slice85_chain_token_metadata.sql`.
- [x] Add public chain registry endpoint `GET /api/v1/public/chains`.
- [x] Replace static frontend chain selector options with dynamic `/api/v1/public/chains` loading + local fallback cache.
- [x] Add runtime chain registry loader + `xclaw-agent chains --json`.
- [x] Add capability gating for chain-scoped runtime command families (`wallet`, `trade`, `limitOrders`, `x402`, `faucet`).
- [x] Add token metadata resolver/cache and include metadata fields in management chain tokens.

### 85.3 Validation + evidence
- [x] Runtime tests:
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`
- [x] Run required gates sequentially:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `pm2 restart all`

---

## 86) Slice 86: Multi-Agent Management Session + Chain-Scoped Policy Snapshots

### 86.1 Canonical/doc sync
- [~] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` for multi-agent management session model and chain-scoped policy snapshot contract.
- [~] Add Slice 86 entries in `docs/XCLAW_SLICE_TRACKER.md` and this roadmap section.
- [~] Update handoff artifacts (`docs/CONTEXT_PACK.md`, `spec.md`, `tasks.md`, `acceptance.md`).

### 86.2 Implementation
- [~] Add migration for `management_session_agents` with backfill from existing `management_sessions`.
- [~] Extend management auth to authorize `expectedAgentId` against linked session agent set.
- [~] Extend bootstrap flow to link an additional agent into active management session.
- [~] Add migration and code updates for `agent_policy_snapshots.chain_key` (write/read scoped).

### 86.3 Validation + evidence
- [ ] Validate multi-agent link path (`/management/session/bootstrap`) and `GET /management/session/agents` returns linked set.
- [ ] Validate unauthorized linked-agent write path returns 401.

## 87) Slice 87: Approvals Core APIs + Permission Inventory

### 87.1 Canonical/doc sync
- [~] Update Source-of-Truth + OpenAPI + schemas for new approvals APIs and policy update `chainKey` requirement.

### 87.2 Implementation
- [~] Add `POST /api/v1/management/approvals/approve-allowlist-token`.
- [~] Add `GET /api/v1/management/approvals/inbox`.
- [~] Add `POST /api/v1/management/permissions/update`.
- [~] Wire `/approvals` to inbox API and enable `Approve + Allowlist Token` action.
- [~] Replace allowances placeholder with permissions inventory module.
- [x] Add web synthetic agent prod bridge for trade/transfer decisions + terminal outcomes with no-deliver dispatch (Telegram-safe by default; optional Telegram guard override).
- [x] Keep Telegram transfer callback deterministic result delivery and route synthetic transfer-result envelope into agent pipeline for completion follow-up.
- [x] Centralize approval prompt cleanup under runtime command `approvals clear-prompt` for trade/transfer/policy, with button-clear-only (no message delete) behavior across web + Telegram callback flows.
- [x] Shell installer uses capability-gated gateway patching: on patch permission failure it auto-degrades (no patch), enables Telegram management-link fallback mode, and emits explicit sudo rerun guidance for inline-button support.

### 87.3 Validation + evidence
- [ ] Verify approve+allowlist updates trade status and chain allowlist atomically.
- [ ] Verify inbox aggregation across linked agents and chain filter behavior.
- [x] Verify non-Telegram prod dispatch attempted on web decision/terminal paths.
- [x] Verify Telegram-last synthetic prod dispatch runs without `--deliver` and does not emit extra Telegram messages.
- [x] Verify transfer approval Telegram inline buttons are removed on approve/deny convergence.
- [x] Verify no approval prompt cleanup path invokes Telegram/OpenClaw message delete; runtime clear codes are surfaced as `promptCleanup` metadata.
- [x] Verify owner-link direct-send is skipped when active channel is Telegram (button-first handoff).

## 88) Slice 88: Approvals Full UX Flush (Batch + Risk)

### 88.1 Canonical/doc sync
- [~] Update Source-of-Truth + schemas for batched decision contract.

### 88.2 Implementation
- [~] Add `POST /api/v1/management/approvals/decision-batch` with per-item result payload.
- [~] Add `/approvals` multi-select bulk decision controls.
- [~] Render deterministic risk labels in request cards.

### 88.3 Validation + evidence
- [ ] Verify mixed-success batch responses are stable and idempotent on retry.
- [ ] Capture functional screenshots for `/approvals` dark/light desktop.

---

## 89) Slice 89: MetaMask-Style Gas Estimation For Agent Wallet Runtime

### 89.1 Canonical/doc sync
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` runtime send robustness contract for EIP-1559-first fee planning.
- [x] Add Slice 89 entries to `docs/XCLAW_SLICE_TRACKER.md` and this roadmap section.
- [x] Update `docs/api/WALLET_COMMAND_CONTRACT.md` with fee planner + env controls.
- [x] Update handoff artifacts: `docs/CONTEXT_PACK.md`, `spec.md`, `tasks.md`, `acceptance.md`.

### 89.2 Implementation
- [x] Add runtime helper `_estimate_tx_fees(rpc_url, attempt_index)`:
  - [x] EIP-1559 primary path (`eth_feeHistory`, `eth_maxPriorityFeePerGas`, reward fallback).
  - [x] bounded retry bump application (`XCLAW_TX_RETRY_BUMP_BPS`).
  - [x] legacy fallback (`eth_gasPrice`) when EIP-1559 path is unavailable.
- [x] Refactor `_cast_rpc_send_transaction(...)`:
  - [x] support both calldata sends and native value sends.
  - [x] emit EIP-1559 send args (`--max-fee-per-gas`, `--priority-gas-price`) or legacy `--gas-price`.
  - [x] preserve nonce handling and retryable error semantics.
- [x] Route native transfer execution through unified sender path in `_execute_pending_transfer_flow`.
- [x] Add rollout controls:
  - [x] `XCLAW_TX_FEE_MODE=rpc|legacy` (default `rpc`),
  - [x] `XCLAW_TX_RETRY_BUMP_BPS` (default `1250`),
  - [x] `XCLAW_TX_PRIORITY_FLOOR_GWEI` (default `1`).

### 89.3 Validation + evidence
- [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`
- [~] `python3 -m unittest apps/agent-runtime/tests/test_wallet_core.py -v`
  - current repo baseline includes unrelated CLI-surface failures in this suite (`wallet import/remove` command expectations and cast-missing expectation drift); Slice 89 runtime fee tests remain passing.
- [x] Required gates execution evidence captured in acceptance:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `pm2 restart all`

---

## 90) Slice 90: Liquidity + Multi-DEX Compatibility Foundation

### 90.1 Canonical/doc sync
- [x] Add Slice 90 goal/DoD + issue mapping to `docs/XCLAW_SLICE_TRACKER.md`.
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` with liquidity command/capability contract.
- [x] Update `docs/api/WALLET_COMMAND_CONTRACT.md` + `skills/xclaw-agent/references/commands.md` for liquidity command surface.
- [x] Update `docs/api/openapi.v1.yaml` with liquidity endpoints and request/response schema refs.

### 90.2 Implementation
- [x] Add migration `0023_slice90_liquidity_foundation.sql` with:
  - [x] `liquidity_intents`
  - [x] `liquidity_position_snapshots`
  - [x] `liquidity_fee_events`
  - [x] `liquidity_protocol_configs`
- [x] Add shared schemas:
  - [x] `liquidity-proposed-request.schema.json`
  - [x] `liquidity-status.schema.json`
  - [x] `liquidity-position.schema.json`
  - [x] `liquidity-approval.schema.json`
- [x] Runtime CLI:
  - [x] `liquidity add`
  - [x] `liquidity remove`
  - [x] `liquidity positions`
  - [x] `liquidity quote-add`
  - [x] `liquidity quote-remove`
  - [x] `chains --json` includes `capabilities.liquidity`.
- [x] Skill wrapper command delegation includes liquidity add/remove/list/quote operations.
- [x] Chain configs include `capabilities.liquidity` and baseline `liquidityProtocols` metadata for Wave-1 and sponsor onboarding stubs.
- [x] Mainnet+testnet chain selector availability enabled via chain config (`enabled=true`) while preserving capability gating (faucet unchanged).
- [x] Server/API routes added:
  - [x] `POST /api/v1/liquidity/proposed`
  - [x] `POST /api/v1/liquidity/{intentId}/status`
  - [x] `GET /api/v1/liquidity/pending`
  - [x] `GET /api/v1/liquidity/positions`
- [x] Management agent-state and `/agents/:id` wallet UI include separate Liquidity Positions section.
- [x] Runtime default-chain contract added (`xclaw-agent default-chain get/set`) with agent-local state source-of-truth.
- [x] Management APIs added for default-chain sync/read (`/management/default-chain`, `/management/default-chain/update-batch`).
- [x] Web selector sync path updates managed-agent runtime defaults and reconciles local selector from runtime canonical default.

### 90.3 Validation + evidence
- [x] Runtime unit tests for liquidity command routing and negative validation paths.
- [x] API contract tests for liquidity endpoints and transition guardrails (`npm run test:liquidity:contract`).
- [x] Web checks for chain-scoped Liquidity Positions rendering + stale-state visibility.
- [x] Run required gates sequentially:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `pm2 restart all`

---

## 91) Slice 91: Runtime Liquidity Intents + Adapter Framework Behavior

### 91.1 Runtime adapter execution contract
- [x] Adapter selection resolves from chain config `liquidityProtocols` using `(chain, dex, position_type)`.
- [x] Runtime enforces preflight quote simulation before liquidity proposal submit on `add/remove`.
- [x] Unsupported routes return deterministic `unsupported_liquidity_adapter`.
- [x] Hedera HTS-native route fails closed with `missing_dependency` when SDK plugin is unavailable.

### 91.2 Runtime CLI hardening
- [x] `liquidity quote-add` emits adapter-family + preflight payload.
- [x] `liquidity quote-remove` supports `--position-type` and emits adapter-family + preflight payload.
- [x] `liquidity add/remove` payload details include preflight + adapter family metadata.

### 91.3 Validation
- [x] `python3 -m unittest apps/agent-runtime/tests/test_liquidity_adapter.py -v`
- [x] `python3 -m unittest apps/agent-runtime/tests/test_liquidity_cli.py -v`

## 92) Slice 92: Wave 1 Protocol Adapters + Hedera HTS Plugin Depth

### 92.1 Wave-1 routing readiness
- [x] Base protocol keys resolve: `uniswap_v2`, `uniswap_v3`, `aerodrome`.
- [x] Kite protocol keys resolve: `tesseract_univ2`; disabled `tesseract_univ3` rejected.
- [x] Hedera protocol keys resolve: `saucerswap`, `pangolin`, `hedera_hts`.
- [x] Disabled/unsupported protocol keys fail with deterministic adapter errors.

### 92.2 Validation
- [x] Adapter route-selection tests include Wave-1 + disabled protocol paths.

## 93) Slice 93: Server APIs + Position Indexing/PnL/Fee Computation

### 93.1 Position sync + refresh
- [x] Added fail-soft `maybeSyncLiquiditySnapshots(...)` helper with 60s cadence keying by `agentId:chainKey`.
- [x] `/api/v1/liquidity/positions` triggers non-forced sync before read.
- [x] `/api/v1/management/agent-state` triggers non-forced sync before read.
- [x] terminal statuses (`filled|failed|verification_timeout`) trigger forced refresh.

### 93.2 Fee/pnl state handling
- [x] `filled` status path persists optional `details.feeEvents[]` into `liquidity_fee_events`.
- [x] position sync computes/refreshes `position_value_usd`, `unrealized_pnl_usd`, and `last_synced_at`.
- [x] transition conflict code is liquidity-specific (`liquidity_invalid_transition`).

## 94) Slice 94: Web Liquidity Positions UX Completion

### 94.1 Wallet liquidity section polish
- [x] Rows now include chain + dex + pair/pool and explicit position type labels.
- [x] Copy updated for deposited basis/current underlying/unrealized estimate fields.
- [x] stale badge rendered for snapshots older than 60s SLA.
- [x] management payload now includes `stale` boolean per liquidity row.

## 95) Slice 95: Verification + Hardening + Bounty Evidence Packaging

### 95.1 Pending verification/evidence pass
- [x] Run required repo gates sequentially for this liquidity program pass.
- [x] Add runtime pair-discovery utility (`liquidity discover-pairs`) and capture Hedera EVM viable pair evidence.
- [x] Implement runtime auto-execution for approved liquidity intents (`liquidity execute/resume`, v2 + hedera_hts scope) and management decision auto-queue integration.
- [x] Capture hardhat-local + external testnet acceptance evidence (Hedera EVM add/remove and Hedera HTS add/remove now emit runtime tx-hash evidence with terminal `filled` outcomes).
- [x] Hosted installer auto-binds Hedera wallet context with portable-key invariant checks and multi-chain register upsert (`default chain` + `hedera_testnet`).
- [x] Harden Hedera faucet request path with deterministic `faucet_*` error codes, Hedera gas-floor handling, and config/preflight validation.
- [x] Enable official Hedera wrap path (`wallet wrap-native`) and helper-based faucet auto-wrap fallback (`faucet_wrapped_autowrap_failed` deterministic contract).
- [x] Rebalance Hedera faucet default drips to operational test values (5 HBAR / 5 WHBAR / 10 USDC) in route defaults + chain-scoped env overrides.
- [x] Hedera runtime `wallet balance` merges mirror-node discovered token holdings so non-canonical owned tokens (for example USDC) appear in `tokens[]`.
- [x] Add user-token tracking contract (`wallet track-token|untrack-token|tracked-tokens`) with dedicated server mirror (`/api/v1/agent/tokens/mirror`) and deposit sync inclusion for tracked-token web holdings.
- [x] Add route-level faucet contract test (`npm run test:faucet:contract`) covering demo-agent block and non-demo deterministic error semantics.
- [x] Installer warmup diagnostics now emit faucet `code/message/actionHint/requestId` and exact rerun command.
- [x] Faucet self-recipient sends are hard-blocked (`faucet_recipient_not_eligible`) and success payload includes `recipientAddress` + `faucetAddress`.
- [x] Add ops scripts to audit/fix agent wallet mappings that match faucet signer addresses (`ops:faucet:audit-mappings`, `ops:faucet:fix-mapping`).
- [x] Update bounty checklist evidence IDs for Hedera/0G/Kite.
- [x] Post issue evidence + commit hashes for slices 90-95.

## 96) Slice 96: Base Sepolia Wallet/Approval E2E Harness (Telegram-Suppressed)

### 96.1 Canonical/doc sync
- [x] Add Slice 96 goal/DoD + issue mapping to `docs/XCLAW_SLICE_TRACKER.md`.
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` with Telegram-suppressed harness contract and runtime env flag.
- [x] Update handoff artifacts (`docs/CONTEXT_PACK.md`, `spec.md`, `tasks.md`, `acceptance.md`).

### 96.2 Runtime + harness implementation
- [x] Add runtime guard `XCLAW_TEST_HARNESS_DISABLE_TELEGRAM` to skip Telegram approval prompt/decision dispatch safely.
- [x] Add harness script `apps/agent-runtime/scripts/wallet_approval_harness.py` with:
  - [x] management session bootstrap (cookie + csrf),
  - [x] scenario matrix execution,
  - [x] management decision driver (`approve-driver=management_api`),
  - [x] baseline policy restore,
  - [x] tolerance-based balance convergence assertions,
  - [x] json report emission.
- [x] Add unit tests:
  - [x] `apps/agent-runtime/tests/test_wallet_approval_harness.py`
  - [x] `apps/agent-runtime/tests/test_trade_path.py` Telegram suppression coverage.

### 96.3 Validation + evidence
- [~] Hardhat-local subset evidence attempted before Base Sepolia; blocked by unavailable local hardhat RPC in this session.
- [~] Base Sepolia harness full run captured with `XCLAW_TEST_HARNESS_DISABLE_TELEGRAM=1` (report generated, scenarios currently failing under reproducible runtime/server errors).
- [ ] Required repo gates run sequentially:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `pm2 restart all`
- [ ] Issue #42 updated with verification evidence + commit hash(es).

### 96.4 Stabilization pass (reliability remediation)
- [x] Harness strict hardhat gate added:
  - [x] `hardhat_local` preflight probes `eth_chainId` at `--hardhat-rpc-url`.
  - [x] Base Sepolia runs are blocked unless `--hardhat-evidence-report` exists and has `ok=true`.
- [x] Wallet decrypt preflight added:
  - [x] preflight runtime checks for `wallet address`, `wallet health`, and `wallet sign-challenge`.
  - [x] deterministic fail-fast `wallet_passphrase_mismatch` with `walletStorePath`, `passphraseSource`, `chain`.
- [x] Management API resilience:
  - [x] retry/backoff+jitter wrapper for permission updates and management write calls.
  - [x] retry exhaustion diagnostics include `requestId/status/code/attempts/path/payloadHash`.
- [x] Runtime test baseline fixed:
  - [x] stale `wallet import/remove` not-available tests replaced with parser/dispatch contract tests.
- [x] Harness report hardening:
  - [x] preflight block emitted in JSON report,
  - [x] retry failure diagnostics emitted in JSON report,
  - [x] pending cleanup includes unresolved list for traceability.

## 97) Slice 97: Ethereum + Ethereum Sepolia Wallet-First Onboarding

### 97.1 Canonical/doc sync
- [x] Add Slice 97 entries to `docs/XCLAW_SLICE_TRACKER.md` and this roadmap section.
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` with wallet-first onboarding contract for `ethereum` + `ethereum_sepolia`.
- [x] Update `docs/api/WALLET_COMMAND_CONTRACT.md` supported chain list.
- [x] Update handoff artifacts: `spec.md`, `tasks.md`, `acceptance.md`.

### 97.2 Implementation
- [x] Add `config/chains/ethereum.json` with:
  - [x] `chainId=1`, `displayName=Ethereum`, `explorerBaseUrl=https://etherscan.io`.
  - [x] `rpc.primary=https://ethereum-rpc.publicnode.com`, `rpc.fallback=https://eth.drpc.org`.
  - [x] `coreContracts` metadata with Uniswap V2 mainnet router/factory references.
  - [x] `canonicalTokens` (`WETH`, `USDC`) and wallet-first capability gating.
- [x] Add `config/chains/ethereum_sepolia.json` with:
  - [x] `chainId=11155111`, `displayName=Ethereum Sepolia`, `explorerBaseUrl=https://sepolia.etherscan.io`.
  - [x] `rpc.primary=https://ethereum-sepolia-rpc.publicnode.com`, `rpc.fallback=https://sepolia.drpc.org`.
  - [x] `coreContracts` metadata with Uniswap V2 Sepolia router/factory references.
  - [x] `canonicalTokens` (`WETH`, `USDC`) and wallet-first capability gating.
- [x] Update web fallback chain registry in `apps/network-web/src/lib/active-chain.ts`.
- [x] Update status RPC probe allowlist in `apps/network-web/src/lib/ops-health.ts`.
- [x] Update deterministic dashboard chain colors in `apps/network-web/src/app/dashboard/page.tsx`.
- [x] Update chain-key example descriptions in `docs/api/openapi.v1.yaml` where chain-config-backed.

### 97.3 Validation + evidence
- [x] `apps/agent-runtime/bin/xclaw-agent chains --json` includes `ethereum` + `ethereum_sepolia` with wallet-only capabilities.
- [x] Isolated-home wallet smoke per chain:
  - [x] `wallet create --chain ethereum --json`
  - [x] `wallet address --chain ethereum --json`
  - [x] `wallet health --chain ethereum --json` (`integrityChecked=true`)
  - [x] `wallet create --chain ethereum_sepolia --json`
  - [x] `wallet address --chain ethereum_sepolia --json`
  - [x] `wallet health --chain ethereum_sepolia --json` (`integrityChecked=true`)
- [x] `/api/v1/public/chains` includes both new chains with expected `chainId` + explorer + capabilities.
- [x] `/api/status` provider probe includes both new chains.
- [ ] Required gates run sequentially:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `pm2 restart all`

## 98) Slice 98: Chain Metadata Normalization + Truthful Capability Gating

### 98.1 Canonical/doc sync
- [x] Add Slice 98 entries to `docs/XCLAW_SLICE_TRACKER.md` and this roadmap section.
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` with metadata-normalization + naming + capability-truth contract.
- [x] Update `docs/api/WALLET_COMMAND_CONTRACT.md` chain-support wording to config-driven model.
- [x] Update handoff artifacts: `spec.md`, `tasks.md`, `acceptance.md`.

### 98.2 Implementation
- [x] Populate ADI chain metadata:
  - [x] `adi_mainnet` chain id/rpc/explorer from authoritative sources + live rpc chainId verification.
  - [x] `adi_testnet` chain id/rpc/explorer from authoritative sources + live rpc chainId verification.
- [x] Populate 0G chain metadata:
  - [x] `og_mainnet` chain id/rpc/explorer + live rpc chainId verification.
  - [x] `og_testnet` chain id/rpc/explorer + live rpc chainId verification.
- [x] Correct `kite_ai_mainnet` chain id to `2366` and normalize display naming (`KiteAI Mainnet`).
- [x] Normalize testnet names (`KiteAI Testnet`, `ADI Network AB Testnet`, `0G Galileo Testnet`).
- [x] Set wallet-first capability gating for non-integrated chains (`base_mainnet`, `kite_ai_mainnet`, `adi_*`, `og_*`).
- [x] Disable/hide unresolved Canton placeholders (`canton_mainnet`, `canton_testnet`).
- [x] Update status provider probing in `apps/network-web/src/lib/ops-health.ts` to dynamic chain-config selection (enabled+visible+has-rpc).

### 98.3 Validation + evidence
- [x] `apps/agent-runtime/bin/xclaw-agent chains --json` reflects normalized chain metadata/capabilities.
- [x] `/api/v1/public/chains` reflects canonical names and visible-chain set.
- [x] `/api/status` providers include all enabled+visible chains with RPCs.
- [ ] Required gates run sequentially:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `pm2 restart all`

## 99) Slice 99: Installer Multi-Chain Wallet Auto-Bind Hardening

### 99.1 Canonical/doc sync
- [x] Add Slice 99 entries to `docs/XCLAW_SLICE_TRACKER.md` and this roadmap section.
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` installer wallet bootstrap contract to wallet-capable chain auto-bind.
- [x] Update `docs/api/WALLET_COMMAND_CONTRACT.md` hosted installer wallet behavior.
- [x] Update handoff artifacts: `spec.md`, `tasks.md`, `acceptance.md`.

### 99.2 Implementation
- [x] `apps/network-web/src/app/skill-install.sh/route.ts`:
  - [x] discover wallet-capable chains from `xclaw-agent chains --json`,
  - [x] auto-bind portable wallet per discovered chain,
  - [x] build deduplicated register `wallets[]` from successful chain-address resolutions.
- [x] `apps/network-web/src/app/skill-install.ps1/route.ts` mirrors the same chain discovery + auto-bind + register wallet payload behavior.
- [x] `skills/xclaw-agent/scripts/xclaw_agent_skill.py` wallet command surface supports optional explicit chain override args (`[chain_key]`) while preserving runtime-default fallback.
- [x] `apps/agent-runtime/xclaw_agent/cli.py` `profile set-name`/`agent-register` upsert payload includes all enabled local wallet bindings (primary chain first).

### 99.3 Validation + evidence
- [x] installer scripts generate and include wallet-capable chain bindings for register payloads.
- [x] Required gates run sequentially:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `pm2 restart all`

## 100) Slice 100: Uniswap Proxy-First Trade Execution + Runtime Fallback

### 100.1 Canonical/doc sync
- [x] Add Slice 100 entries to `docs/XCLAW_SLICE_TRACKER.md` and this roadmap section.
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` with Uniswap proxy-first execution contract and fallback semantics.
- [x] Update `docs/api/openapi.v1.yaml` with new Uniswap proxy routes and trade status provenance fields.
- [x] Update handoff artifacts: `docs/CONTEXT_PACK.md`, `spec.md`, `tasks.md`, `acceptance.md`.

### 100.2 Implementation
- [x] Add server-side env contract in `apps/network-web/src/lib/env.ts` for `XCLAW_UNISWAP_API_KEY`.
- [x] Add Uniswap proxy client helper `apps/network-web/src/lib/uniswap-proxy.ts`:
  - [x] server-held key injection only,
  - [x] supported-chain gate by chain config/chainId,
  - [x] strict payload normalization and deterministic upstream error mapping.
- [x] Add agent-auth routes:
  - [x] `POST /api/v1/agent/trade/uniswap/quote`
  - [x] `POST /api/v1/agent/trade/uniswap/build`
- [x] Runtime `trade spot` updated for provider orchestration:
  - [x] `provider=uniswap_api` primary path for configured chains,
  - [x] fallback to legacy router on any Uniswap proxy failure,
  - [x] deterministic `no_execution_provider_available` when neither path can execute.
- [x] Runtime `trade execute` updated with matching provider orchestration + fallback behavior.
- [x] Provider provenance surfaced in runtime outputs and status transitions:
  - [x] `providerRequested`, `providerUsed`, `fallbackUsed`, `fallbackReason`, `uniswapRouteType`.
- [x] Trade status schema/route updated to accept and mirror provider provenance metadata.
- [x] Chain rollout configs added/updated for requested Uniswap scope:
  - [x] `ethereum`, `ethereum_sepolia`, `unichain_mainnet`, `bnb_mainnet`, `polygon_mainnet`, `base_mainnet`,
  - [x] `avalanche_mainnet`, `op_mainnet`, `arbitrum_mainnet`, `zksync_mainnet`, `monad_mainnet`.

### 100.3 Validation + evidence
- [x] Runtime unit tests pass with new provider/fallback cases:
  - [x] `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`
- [x] Required gates run sequentially:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `pm2 restart all`
- [ ] Issue #46 evidence post + commit hash(es).

## 101) Slice 101: Dashboard Dexscreener Top Tokens (Chain-Aware, Top 10)

### 101.1 Canonical/doc sync
- [x] Add Slice 101 entries to `docs/XCLAW_SLICE_TRACKER.md` and this roadmap section.
- [x] Update `docs/XCLAW_SOURCE_OF_TRUTH.md` dashboard contract with `Top Trending Tokens` behavior and chain-filter rules.
- [x] Update `docs/api/openapi.v1.yaml` with `GET /api/v1/public/dashboard/trending-tokens`.
- [x] Add shared response schema `packages/shared-schemas/json/public-dashboard-trending-tokens-response.schema.json`.
- [x] Update handoff artifacts: `docs/CONTEXT_PACK.md`, `spec.md`, `tasks.md`, `acceptance.md`.

### 101.2 Implementation
- [x] Add optional chain mapping field `marketData.dexscreenerChainId` in `apps/network-web/src/lib/chains.ts`.
- [x] Populate mapping in chain configs:
  - [x] `base_mainnet` + `base_sepolia` -> `base`
  - [x] `ethereum` + `ethereum_sepolia` -> `ethereum`
- [x] Add route `apps/network-web/src/app/api/v1/public/dashboard/trending-tokens/route.ts`:
  - [x] validate `chainKey` against enabled+visible chains,
  - [x] resolve mapped Dexscreener chains (`all` aggregates mapped chains),
  - [x] fetch Dexscreener rows server-side with timeout and structured soft-failure handling,
  - [x] normalize token rows and dedupe by token+chain,
  - [x] rank by `volume.h24 desc` and return top 10.
- [x] Add 60s in-memory cache for upstream Dexscreener reads.
- [x] Update dashboard page integration:
  - [x] fetch `/api/v1/public/dashboard/trending-tokens?chainKey=<selected>&limit=10`,
  - [x] refresh token data every 60 seconds,
  - [x] render desktop table + mobile cards below existing dashboard insights,
  - [x] include only columns with available data across returned rows,
  - [x] hide section when no rows for current chain.

### 101.3 Validation + evidence
- [x] Feature checks:
  - [x] `chainKey=all` returns max 10 sorted by 24h volume descending.
  - [x] selected chain updates rows on dropdown change.
  - [x] mapped testnet selections (`base_sepolia`, `ethereum_sepolia`) resolve to mainnet Dexscreener chain data.
  - [x] unmapped chains hide token section.
  - [x] invalid `chainKey` returns `400 payload_invalid`.
- [ ] Required gates run sequentially:
  - [x] `npm run db:parity`
  - [x] `npm run seed:reset`
  - [x] `npm run seed:load`
  - [x] `npm run seed:verify`
  - [x] `npm run build`
  - [x] `pm2 restart all`
- [ ] Issue #47 evidence post + commit hash(es).
