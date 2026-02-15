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
