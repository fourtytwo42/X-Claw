# Slice 249 Acceptance Evidence: Canonical Chain Capability Matrix Reconciliation

Date (UTC): 2026-03-09  
Active slice context: `Slice 249`  
Issue mapping: `#102`

### Objective + Scope Lock
- Objective:
  - establish one canonical current chain capability matrix,
  - reconcile it across enabled chain config and public chain metadata behavior,
  - demote contradictory older capability sections to explicit historical records,
  - keep the slice limited to truth reconciliation with no new chain enablement.

### Behavior Checks
- [x] one current capability matrix exists near the top of source-of-truth.
- [x] the current matrix matches enabled chain configs exactly.
- [x] older contradictory chain-capability sections are explicitly historical/superseded.
- [x] public chain metadata remains config-driven and matches the canonical matrix for priority chains.

### Required Validation Gates
- [x] `npm run test:chains:contract`
- [x] `npm run test:management:solana:contract`
- [x] `npm run test:x402:solana:contract`
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] tracked `infrastructure/seed-data/.seed-state.json` restore
- [x] `npm run build`
- [x] `pm2 restart all`

### Evidence
- Canonical current capability matrix:
  - [XCLAW_SOURCE_OF_TRUTH.md](/home/hendo420/ETHDenver2026/docs/XCLAW_SOURCE_OF_TRUTH.md)
  - machine-readable matrix lives under `CURRENT_CHAIN_CAPABILITY_MATRIX_START/END`
  - matrix entry count matches enabled chain config count: `23`
- Historical demotion:
  - Slice 97 and Slice 98 chain-capability sections are explicitly marked historical/superseded in [XCLAW_SOURCE_OF_TRUTH.md](/home/hendo420/ETHDenver2026/docs/XCLAW_SOURCE_OF_TRUTH.md)
- Contract lock:
  - [chain-capability-contract-tests.mjs](/home/hendo420/ETHDenver2026/infrastructure/scripts/chain-capability-contract-tests.mjs)
  - [package.json](/home/hendo420/ETHDenver2026/package.json) -> `npm run test:chains:contract`
  - checks:
    - source-of-truth matrix equals enabled chain configs
    - priority chains match expected capability boundary
    - public chain route maps all capability flags from config
    - old Slice 97/98 capability sections are marked historical
- Validation results:
  - `npm run test:chains:contract` -> `passed: 16`, `failed: 0`
  - `npm run test:management:solana:contract` -> `passed: 28`, `failed: 0`
  - `npm run test:x402:solana:contract` -> `count: 17`, `ok: true`
  - `npm run db:parity` -> `ok: true`, `checkedAt: 2026-03-09T19:48:06.675Z`
  - `npm run seed:reset` -> `ok: true`
  - `npm run seed:load` -> `ok: true`, `loadedAt: 2026-03-09T19:48:06.862Z`
  - `npm run seed:verify` -> `ok: true`
  - tracked `infrastructure/seed-data/.seed-state.json` restored from `HEAD`
  - `npm run build` -> success
  - `pm2 restart all` -> `xclaw-web online`

### Slice Outcome
Complete.
