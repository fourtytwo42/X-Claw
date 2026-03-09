# Slice 244 Acceptance Evidence: Solana Localnet Self-Provision + Devnet Matrix Completion

Date (UTC): 2026-03-09  
Active slice context: `Slice 244`.

Issue mapping: `#97`

### Objective + Scope Lock
- Objective:
  - preserve the existing Hardhat-local -> Base Sepolia -> Ethereum Sepolia evidence chain,
  - self-provision `solana_localnet` for the live matrix,
  - advance the live approval matrix through `solana_devnet`,
  - keep the slice limited to harness/report/evidence work with no public runtime contract drift.

### Behavior Checks
- [x] chain-matrix self-provisions `solana_localnet` or emits a concrete provisioning failure.
- [x] Solana harness reports bootstrap-backed localnet preflight truthfully.
- [x] chain-specific reports plus an aggregate matrix report are generated.
- [x] existing EVM harness behavior remains unchanged.

### Required Validation Gates
- [x] `python3 -m unittest -v apps/agent-runtime/tests/test_wallet_approval_harness.py`
- [x] `python3 -m unittest -v apps/agent-runtime/tests/test_wallet_approval_chain_matrix.py`
- [x] `npm run test:management:solana:contract`
- [x] `npm run test:x402:solana:contract`
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] tracked `infrastructure/seed-data/.seed-state.json` restore
- [x] `npm run hardhat:deploy-local`
- [x] `npm run hardhat:verify-local`
- [ ] refreshed full matrix run
- [x] `npm run build`
- [x] `pm2 restart all`

### Evidence
- Code changes:
  - `apps/agent-runtime/scripts/wallet_approval_chain_matrix.py`
    - adds deterministic `solana_localnet` provisioning probe/bootstrap path
    - emits concrete provisioning failures (`solana_localnet_validator_missing|solana_localnet_bootstrap_failed|solana_localnet_rpc_unavailable`)
    - injects localnet bootstrap env into harness child env
  - `apps/agent-runtime/scripts/wallet_approval_harness.py`
    - adds `solana_localnet` bootstrap preflight
    - reports localnet liquidity as preflight-blocked instead of synthetic success when bootstrap prerequisites are absent
  - `apps/network-web/src/lib/solana-localnet-bootstrap-env.ts`
    - loads canonical localnet bootstrap env file on demand
  - `apps/network-web/src/app/api/v1/agent/faucet/request/route.ts`
  - `apps/network-web/src/app/api/v1/agent/faucet/networks/route.ts`
    - resolve Solana localnet faucet config from the bootstrap env file without requiring manual server env edits
- Direct tests:
  - `python3 -m unittest -v apps/agent-runtime/tests/test_wallet_approval_harness.py`
    - `Ran 41 tests`
    - `OK`
  - `python3 -m unittest -v apps/agent-runtime/tests/test_wallet_approval_chain_matrix.py`
    - `Ran 7 tests`
    - `OK`
- Solana contract rails:
  - `npm run test:management:solana:contract`
    - `ok: true`
    - `passed: 25`
    - `failed: 0`
  - `npm run test:x402:solana:contract`
    - `ok: true`
    - `count: 17`
- Required repo validation chain:
  - `npm run db:parity`
    - `ok: true`
    - `checkedAt: 2026-03-09T00:16:55.832Z`
  - `npm run seed:reset`
    - `ok: true`
  - `npm run seed:load`
    - `ok: true`
    - `loadedAt: 2026-03-09T00:17:04.104Z`
  - `npm run seed:verify`
    - `ok: true`
  - tracked seed restore:
    - `git show HEAD:infrastructure/seed-data/.seed-state.json > infrastructure/seed-data/.seed-state.json`
  - `npm run hardhat:deploy-local`
    - `ok: true`
    - `deployedAt: 2026-03-09T00:17:08.988Z`
  - `npm run hardhat:verify-local`
    - `ok: true`
    - `verifiedAt: 2026-03-09T00:17:08.872Z`
  - `npm run build`
    - passed
  - `pm2 restart all`
    - `xclaw-web` restarted
    - status `online`
- Live matrix evidence:
  - full rerun command:
    - `python3 apps/agent-runtime/scripts/wallet_approval_chain_matrix.py ... --reports-dir /tmp/xclaw-slice244-reports --json-report /tmp/xclaw-slice244-matrix.json`
  - full rerun note:
    - refreshed run did not reach `solana_localnet` cleanly in this shell and was not accepted as completion evidence
  - isolated localnet provisioning command:
    - `python3 apps/agent-runtime/scripts/wallet_approval_chain_matrix.py ... --reports-dir /tmp/xclaw-slice244-reports --json-report /tmp/xclaw-slice244-solana-only-matrix.json --start-chain solana_localnet`
  - isolated result:
    - `/tmp/xclaw-slice244-solana-only-matrix.json`
    - `failedAt=solana_localnet`
    - concrete blocker `solana_localnet_validator_missing`
    - details include expected commands `solana-test-validator`, `agave-test-validator`
  - current environment fact:
    - `command -v solana-test-validator` -> no result
    - `command -v agave-test-validator` -> no result
    - `curl http://127.0.0.1:8899 ... getHealth` -> connection refused

### Current Blocker
- Slice 244 cannot advance `solana_localnet` in this shell because no local Solana validator binary is installed and no RPC is listening on `127.0.0.1:8899`.
- The code now fails with the correct deterministic provisioning blocker instead of generic downstream `rpc_unavailable`.
