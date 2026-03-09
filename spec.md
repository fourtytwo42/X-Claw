# Slice 244 Spec: Solana Localnet Self-Provision + Devnet Matrix Completion (2026-03-09)

Issue mapping: `#97`

## Goal
1. Self-provision `solana_localnet` for the live chain matrix using the canonical bootstrap path.
2. Keep the matrix ordered and machine-readable: `hardhat_local` -> `base_sepolia` -> `ethereum_sepolia` -> `solana_localnet` -> `solana_devnet`.
3. Advance the matrix through `solana_localnet` and into `solana_devnet`, or stop with a concrete later-chain blocker.
4. Keep this slice evidence-focused with no public runtime contract drift.

## Non-goals
1. No API route/schema/database changes.
2. No runtime refactor beyond the minimum harness/matrix/server glue needed for truthful Solana localnet provisioning.
3. No Hedera evidence in this slice.

## Locked scope
1. `apps/agent-runtime/scripts/wallet_approval_harness.py`
2. `apps/agent-runtime/scripts/wallet_approval_chain_matrix.py`
3. `apps/agent-runtime/tests/test_wallet_approval_harness.py`
4. `apps/agent-runtime/tests/test_wallet_approval_chain_matrix.py`
5. `apps/network-web/src/app/api/v1/agent/faucet/request/route.ts`
6. `apps/network-web/src/app/api/v1/agent/faucet/networks/route.ts`
7. `apps/network-web/src/lib/solana-localnet-bootstrap-env.ts`
8. `infrastructure/scripts/solana-localnet-bootstrap.mjs`
9. `infrastructure/scripts/management-solana-contract-tests.mjs`
10. `infrastructure/seed-data/hardhat-local-deploy.json`
11. `infrastructure/seed-data/hardhat-local-verify.json`
12. `docs/XCLAW_SOURCE_OF_TRUTH.md`
13. `docs/XCLAW_SLICE_TRACKER.md`
14. `docs/XCLAW_BUILD_ROADMAP.md`
15. `docs/CONTEXT_PACK.md`
16. `spec.md`
17. `tasks.md`
18. `acceptance.md`
