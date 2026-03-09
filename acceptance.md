# Slice 245 Acceptance Evidence: Solana Devnet Passphrase-Source Alignment

Date (UTC): 2026-03-09  
Active slice context: `Slice 245`.

Issue mapping: `#98`

### Objective + Scope Lock
- Objective:
  - align harness wallet preflight with the installed skill config passphrase source,
  - clear the deterministic `solana_devnet` `wallet_passphrase_mismatch` blocker,
  - capture the next truthful Solana devnet blocker after wallet preflight succeeds,
  - keep the slice limited to harness/report/evidence work with no public runtime contract drift.

### Behavior Checks
- [x] harness wallet preflight resolves passphrase in canonical order: arg -> env -> skill config -> backup.
- [x] `passphraseSource` evidence distinguishes `arg|env|skill_config|backup|missing`.
- [x] `solana_devnet` no longer fails at wallet preflight because the harness cannot find a passphrase source.
- [x] the next truthful later blocker is captured in machine-readable evidence.

### Required Validation Gates
- [x] `python3 -m unittest -v apps/agent-runtime/tests/test_wallet_approval_harness.py`
- [x] `python3 -m unittest -v apps/agent-runtime/tests/test_wallet_approval_chain_matrix.py`
- [x] `python3 -m unittest -v apps/agent-runtime/tests/test_trade_path.py apps/agent-runtime/tests/test_wallet_approval_harness.py apps/agent-runtime/tests/test_wallet_approval_chain_matrix.py`
- [x] `npm run test:management:solana:contract`
- [x] `npm run test:x402:solana:contract`
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] tracked `infrastructure/seed-data/.seed-state.json` restore
- [x] `npm run hardhat:deploy-local`
- [x] `npm run hardhat:verify-local`
- [x] refreshed targeted `solana_devnet` live rerun
- [x] `npm run build`
- [x] `pm2 restart all`

### Evidence
- Code changes:
  - `apps/agent-runtime/scripts/wallet_approval_harness.py`
    - resolves passphrase from installed skill config after arg/env and before backup
    - preserves deterministic `wallet_passphrase_mismatch` when no usable source exists
- Direct tests:
  - `python3 -m unittest -v apps/agent-runtime/tests/test_trade_path.py apps/agent-runtime/tests/test_wallet_approval_harness.py apps/agent-runtime/tests/test_wallet_approval_chain_matrix.py`
    - `Ran 216 tests`
    - `OK`
  - `python3 -m unittest -v apps/agent-runtime/tests/test_wallet_approval_harness.py`
    - `Ran 53 tests`
    - `OK`
  - `python3 -m unittest -v apps/agent-runtime/tests/test_wallet_approval_chain_matrix.py`
    - `Ran 8 tests`
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
    - `checkedAt: 2026-03-09T04:46:12.031Z`
  - `npm run seed:reset`
    - `ok: true`
  - `npm run seed:load`
    - `ok: true`
    - `loadedAt: 2026-03-09T04:46:12.251Z`
  - `npm run seed:verify`
    - `ok: true`
  - tracked seed restore:
    - `git show HEAD:infrastructure/seed-data/.seed-state.json > infrastructure/seed-data/.seed-state.json`
  - `npm run hardhat:deploy-local`
    - `ok: true`
    - `deployedAt: 2026-03-09T04:46:13.398Z`
  - `npm run hardhat:verify-local`
    - `ok: true`
    - `verifiedAt: 2026-03-09T04:46:14.243Z`
  - `npm run build`
    - `ok: true`
    - `next build` completed successfully on 2026-03-09
  - `pm2 restart all`
    - `ok: true`
    - `xclaw-web` status: `online`
- Live Solana devnet evidence:
  - targeted rerun:
    - `/tmp/xclaw-slice245-solana-devnet-full.json`
    - wallet preflight no longer fails with `wallet_passphrase_mismatch`
    - next truthful blocker:
      - `code: scenario_funding_missing`
      - `walletAddress: 8GpQWRfcsyeNh1SeZna6Ah5dRrMotnm63pF2iNaHapeQ`
      - `nativeAtomic: 0`
      - `stableAtomic: 0`
      - `wrappedAtomic: 0`
  - machine-readable devnet matrix artifact:
    - `/tmp/xclaw-slice245-matrix.json`
    - `failedAt: solana_devnet`
    - concrete later blocker:
      - `code: scenario_funding_missing`
      - `chain: solana_devnet`

### Slice Outcome
- Slice 245 is complete.
- The original `solana_devnet` `wallet_passphrase_mismatch` blocker is resolved at the harness layer.
- The next truthful later blocker is `solana_devnet` funding availability (`scenario_funding_missing`) for the repaired devnet wallet.
- Existing green earlier-chain evidence from Slice 244 remains authoritative because this slice only changed Solana devnet passphrase sourcing.
