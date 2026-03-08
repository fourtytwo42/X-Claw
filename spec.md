# Slice 243 Spec: Live Chain Evidence Matrix Expansion (EVM + Solana) (2026-03-08)

Issue mapping: `#96`

## Goal
1. Refresh live execution evidence across the canonical EVM harness path and add Solana matrix legs.
2. Keep the matrix ordered and machine-readable: `hardhat_local` -> `base_sepolia` -> `ethereum_sepolia` -> `solana_localnet` -> `solana_devnet`.
3. Keep this slice evidence-focused with no public runtime contract drift.

## Non-goals
1. No API route/schema/database changes.
2. No runtime refactor unless a harness gap blocks truthful evidence generation.
3. No Hedera evidence in this slice.

## Locked scope
1. `apps/agent-runtime/scripts/wallet_approval_harness.py`
2. `apps/agent-runtime/scripts/wallet_approval_chain_matrix.py`
3. `apps/agent-runtime/tests/test_wallet_approval_harness.py`
4. `apps/agent-runtime/tests/test_wallet_approval_chain_matrix.py`
5. `apps/network-web/src/lib/management-cookies.ts`
6. `apps/network-web/src/app/api/v1/agent/management-link/route.ts`
7. `apps/network-web/src/app/api/v1/management/owner-link/route.ts`
8. `infrastructure/scripts/management-solana-contract-tests.mjs`
9. `infrastructure/seed-data/hardhat-local-deploy.json`
10. `infrastructure/seed-data/hardhat-local-verify.json`
11. `docs/XCLAW_SOURCE_OF_TRUTH.md`
12. `docs/XCLAW_SLICE_TRACKER.md`
13. `docs/XCLAW_BUILD_ROADMAP.md`
14. `docs/CONTEXT_PACK.md`
15. `spec.md`
16. `tasks.md`
17. `acceptance.md`
