# Slice 249 Spec: Canonical Chain Capability Matrix Reconciliation (2026-03-09)

Issue mapping: `#102`

## Goal
1. Establish one canonical current chain capability matrix near the top of source-of-truth.
2. Reconcile that matrix against enabled chain config and public chain capability surfaces.
3. Demote older contradictory chain-capability slice sections to explicit historical records.
4. Add one contract test that locks config, source-of-truth, and public chain metadata capability mapping together.

## Outcome
1. `docs/XCLAW_SOURCE_OF_TRUTH.md` contains a machine-readable current capability matrix for all enabled `evm` and `solana` chains.
2. The current matrix matches `config/chains/*.json` exactly for enabled chains.
3. `GET /api/v1/public/chains` remains config-driven and capability-faithful for the current matrix.
4. Older contradictory capability sections are explicitly historical/superseded rather than normative.

## Non-goals
1. No new chain capability enablement.
2. No API schema/database changes.
3. No runtime command behavior changes.
4. No UI redesign.

## Locked scope
1. `docs/XCLAW_SOURCE_OF_TRUTH.md`
2. `docs/XCLAW_SLICE_TRACKER.md`
3. `docs/XCLAW_BUILD_ROADMAP.md`
4. `docs/CONTEXT_PACK.md`
5. `spec.md`
6. `tasks.md`
7. `acceptance.md`
8. `infrastructure/scripts/chain-capability-contract-tests.mjs`
9. `package.json`
10. `apps/network-web/src/app/api/v1/public/chains/route.ts` only if public capability mapping requires correction
