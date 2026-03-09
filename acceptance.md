# Slice 250 Acceptance Evidence: Canonical Chain Metadata Reconciliation

Active slice context: `Slice 250`  
Issue mapping: `#103`

## Goal
Lock one canonical current chain metadata matrix and prove enabled chain config, public metadata readers, and fallback registry metadata stay aligned.

## Validation
- [x] `npm run test:chain-metadata:contract`
- [x] `npm run test:chains:contract`
- [x] `npm run test:management:solana:contract`
- [x] `npm run test:x402:solana:contract`
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] restore tracked `infrastructure/seed-data/.seed-state.json`
- [x] `npm run build`
- [x] `pm2 restart all`

## Evidence
- `npm run test:chain-metadata:contract` -> `ok: true`, `checks: 5`
- `npm run test:chains:contract` -> `ok: true`, `passed: 16`, `failed: 0`
- `npm run test:management:solana:contract` -> `ok: true`, `passed: 28`, `failed: 0`
- `npm run test:x402:solana:contract` -> `ok: true`, `count: 17`
- `npm run db:parity` -> `ok: true`, `checkedAt: 2026-03-09T19:55:29.654Z`
- `npm run seed:reset` -> `ok: true`
- `npm run seed:load` -> `ok: true`, `loadedAt: 2026-03-09T19:55:29.830Z`
- `npm run seed:verify` -> `ok: true`
- tracked `infrastructure/seed-data/.seed-state.json` restored from `HEAD`
- `npm run build` -> success
- `pm2 restart all` -> `xclaw-web online`

## Outcome
- One current machine-readable chain metadata matrix is now canonical in `docs/XCLAW_SOURCE_OF_TRUTH.md`.
- Enabled chain config, `/api/v1/public/chains`, and `active-chain.ts` fallback metadata are locked together by `npm run test:chain-metadata:contract`.
- Older conflicting metadata narratives remain in source-of-truth as historical records only and no longer read as active contract.
