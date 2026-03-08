# Slice 243 Acceptance Evidence: Live Chain Evidence Matrix Expansion (EVM + Solana)

Date (UTC): 2026-03-08  
Active slice context: `Slice 243`.

Issue mapping: `#96`

### Objective + Scope Lock
- Objective:
  - preserve the existing Hardhat-local -> Base Sepolia -> Ethereum Sepolia evidence chain,
  - extend the live approval matrix to `solana_localnet` then `solana_devnet`,
  - keep the slice limited to harness/report/evidence work with no public runtime contract drift.

### Behavior Checks
- [x] chain-matrix order includes `solana_localnet` and `solana_devnet` after the existing EVM legs.
- [x] Solana harness scenarios report truthful supported/unsupported outcomes.
- [ ] chain-specific reports plus an aggregate matrix report are generated.
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
- [!] refreshed live matrix run
- [x] `npm run build`
- [x] `pm2 restart all`

### Evidence
- Harness + matrix changes:
  - `apps/agent-runtime/scripts/wallet_approval_chain_matrix.py`
    - chain order extended to `hardhat_local`, `base_sepolia`, `ethereum_sepolia`, `solana_localnet`, `solana_devnet`
    - additive CLI support for `--solana-wallet-address` and `--solana-recipient-address`
    - Solana per-chain report paths added to aggregate matrix output
  - `apps/agent-runtime/scripts/wallet_approval_harness.py`
    - Solana-specific trade asset defaults use canonical wrapped SOL + USDC mint semantics
    - Solana localnet faucet bootstrap uses native-only top-up path
    - Solana liquidity scenario returns truthful unsupported details when live preflight is not runnable
  - `infrastructure/scripts/management-solana-contract-tests.mjs`
    - Solana runtime contract assertions updated to follow shared validator locations after runtime extraction
- Direct tests:
  - `python3 -m unittest -v apps/agent-runtime/tests/test_wallet_approval_harness.py`
    - `Ran 34 tests`
    - `OK`
  - `python3 -m unittest -v apps/agent-runtime/tests/test_wallet_approval_chain_matrix.py`
    - `Ran 5 tests`
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
    - `checkedAt: 2026-03-08T22:37:27.926Z`
  - `npm run seed:reset`
    - `ok: true`
  - `npm run seed:load`
    - `ok: true`
    - `loadedAt: 2026-03-08T22:37:28.123Z`
  - `npm run seed:verify`
    - `ok: true`
  - tracked seed restore:
    - `git show HEAD:infrastructure/seed-data/.seed-state.json > infrastructure/seed-data/.seed-state.json`
  - `npm run build`
    - passed
    - Next.js build completed successfully
  - `pm2 restart all`
    - `xclaw-web` restarted
    - status `online`
- Live matrix blocker:
  - current environment has no discovered `XCLAW_*` live harness credentials and no bootstrap token JSON candidate file
  - required matrix inputs are not provisioned:
    - `--agent-id`
    - `--bootstrap-token-file`
    - `--harvy-address`
  - optional Solana address inputs are also absent:
    - `--solana-wallet-address`
    - `--solana-recipient-address`
  - exact command to unblock:
    - `python3 apps/agent-runtime/scripts/wallet_approval_chain_matrix.py --agent-id <agent_id> --bootstrap-token-file <bootstrap_token.json> --harvy-address <evm_wallet_address> --solana-wallet-address <solana_wallet_address> --solana-recipient-address <solana_recipient_address> --json-report /tmp/xclaw-slice243-matrix.json --reports-dir /tmp/xclaw-slice243-reports`
