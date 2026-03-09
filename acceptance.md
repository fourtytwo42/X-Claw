# Slice 247 Acceptance Evidence: Solana Devnet Quoted-Pair Discovery and Evidence Boundary

Date (UTC): 2026-03-09  
Active slice context: `Slice 247`.

Issue mapping: `#100`

### Objective + Scope Lock
- Objective:
  - determine whether Solana devnet has a truthful Jupiter-quotable pair for live trade evidence,
  - use that pair if it exists or otherwise record deterministic unsupported trade evidence,
  - rerun the ordered matrix through `solana_devnet`,
  - keep the slice limited to harness/reporting evidence behavior with no public runtime contract drift.

### Behavior Checks
- [x] Solana devnet trade evidence first attempts deterministic quoted-pair discovery.
- [x] Solana devnet trade scenarios stop with explicit `unsupported_live_evidence` when no quoteable pair exists.
- [x] Non-trade Solana devnet evidence remains in scope after the trade-evidence boundary.
- [x] Slice 247 outcome captured with green earlier-chain evidence plus deterministic Solana devnet later-blocker proof.

### Required Validation Gates
- [x] `python3 -m unittest -v apps/agent-runtime/tests/test_wallet_approval_harness.py`
- [x] `python3 -m unittest -v apps/agent-runtime/tests/test_wallet_approval_chain_matrix.py`
- [x] `python3 -m unittest -v apps/agent-runtime/tests/test_trade_path.py apps/agent-runtime/tests/test_wallet_approval_harness.py apps/agent-runtime/tests/test_wallet_approval_chain_matrix.py`
- [x] `npm run test:faucet:contract`
- [x] `npm run test:management:solana:contract`
- [x] `npm run test:x402:solana:contract`
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] tracked `infrastructure/seed-data/.seed-state.json` restore
- [x] `npm run hardhat:deploy-local`
- [x] `npm run hardhat:verify-local`
- [x] targeted live `solana_devnet` rerun
- [x] live earlier-chain evidence refreshed or directly rerun where touched
- [x] `npm run build`
- [x] `pm2 restart all`

### Evidence
- Code changes:
  - `apps/agent-runtime/scripts/wallet_approval_harness.py`
    - adds deterministic Solana devnet quoteable-pair discovery and machine-readable trade-pair evidence
    - stops Solana devnet trade scenarios with deterministic `unsupported_live_evidence` when no quoteable pair exists
    - continues non-trade Solana devnet evidence after the explicit trade boundary
  - `apps/agent-runtime/tests/test_wallet_approval_harness.py`
    - covers quoteable-pair selection, unsupported evidence, and continued non-trade devnet execution
  - `apps/agent-runtime/tests/test_wallet_approval_chain_matrix.py`
    - covers machine-readable later-blocker reporting for the Solana devnet unsupported boundary
- Direct tests:
  - `python3 -m unittest -v apps/agent-runtime/tests/test_wallet_approval_harness.py`
    - `Ran 64 tests`
    - `OK`
  - `python3 -m unittest -v apps/agent-runtime/tests/test_wallet_approval_chain_matrix.py`
    - `Ran 10 tests`
    - `OK`
  - `python3 -m unittest -v apps/agent-runtime/tests/test_trade_path.py apps/agent-runtime/tests/test_wallet_approval_harness.py apps/agent-runtime/tests/test_wallet_approval_chain_matrix.py`
    - `Ran 229 tests`
    - `OK`
- Solana contract rails:
  - `npm run test:faucet:contract`
    - `ok: true`
    - `passed: 10`
    - `failed: 0`
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
    - `checkedAt: 2026-03-09T18:41:58.302Z`
  - `npm run seed:reset`
    - `ok: true`
  - `npm run seed:load`
    - `ok: true`
    - `loadedAt: 2026-03-09T18:42:02.981Z`
  - `npm run seed:verify`
    - `ok: true`
  - tracked seed restore:
    - `git show HEAD:infrastructure/seed-data/.seed-state.json > infrastructure/seed-data/.seed-state.json`
  - `npm run hardhat:deploy-local`
    - `ok: true`
    - `deployedAt: 2026-03-09T18:42:10.057Z`
  - `npm run hardhat:verify-local`
    - `ok: true`
    - `verifiedAt: 2026-03-09T18:42:09.778Z`
  - `npm run build`
    - `ok: true`
  - `pm2 restart all`
    - `ok: true`
    - `xclaw-web` status: `online`
- Live evidence:
  - targeted Solana devnet report:
    - `/tmp/xclaw-slice247-solana-devnet-full.json`
    - preflight includes:
      - `solanaDevnetTradePair.quoteable=false`
      - `reason=solana_devnet_trade_pair_unavailable`
      - candidate result showing Jupiter response `TOKEN_NOT_TRADABLE` for the scoped devnet pair
    - scenario results include:
      - `solana_devnet_trade_evidence_boundary` -> `unsupported_live_evidence`
      - `transfer_only` -> `ok`
      - `x402_or_capability_assertion` -> `ok`
  - refreshed earlier-chain evidence:
    - Hardhat local green:
      - `/tmp/xclaw-slice247-reports/xclaw-slice117-hardhat-smoke.json`
    - Base Sepolia green:
      - `/tmp/xclaw-slice247-reports/xclaw-slice117-base-full.json`
    - Ethereum Sepolia direct rerun green:
      - `/tmp/xclaw-slice247-ethereum-sepolia-full-rerun.json`
    - existing Solana localnet green proof remains valid and unchanged for Slice 247:
      - `/tmp/xclaw-slice244-reports/xclaw-slice243-solana-localnet-full.json`
- Matrix note:
  - an initial full ordered rerun reached green `hardhat_local` and `base_sepolia` but hit a transient Ethereum approval-resume state mismatch before the new Solana boundary could be exercised.
  - direct Ethereum rerun cleared that transient issue.
  - Slice 247 therefore closes on stronger per-chain evidence plus targeted Solana devnet later-blocker proof instead of a synthetic full-matrix green claim.

### Slice Outcome
- Slice 247 is complete.
- Best-practice Solana devnet behavior is now codified:
  - attempt discovery of a real Jupiter-quotable pair first,
  - if none exists, do not fake trade success.
- Current truthful later blocker:
  - `class=unsupported_live_evidence`
  - `reason=solana_devnet_trade_pair_unavailable`
- Meaning:
  - Solana devnet wallet preflight and funding are green,
  - non-trade Solana devnet evidence is green,
  - the available funded devnet pair is not tradable through Jupiter, so green live trade execution evidence is out of scope until a real quoteable pair exists.
