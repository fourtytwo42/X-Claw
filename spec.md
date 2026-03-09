# Slice 244 Spec: Solana Localnet Faucet Funding + Ethereum Sepolia Retry Stabilization (2026-03-09)

Issue mapping: `#97`

## Goal
1. Self-provision `solana_localnet` for the live chain matrix using the canonical bootstrap path.
2. Align `solana_localnet` harness token resolution and faucet funding with the bootstrap-generated stable/wrapped mint addresses and prove the server-side faucet lands those assets on-chain.
3. Stabilize the later `ethereum_sepolia` live-evidence retry path for the RPC replacement-tx wording variant already covered by the canonical retry contract.
4. Keep the matrix ordered and machine-readable: `hardhat_local` -> `base_sepolia` -> `ethereum_sepolia` -> `solana_localnet` -> `solana_devnet`.
5. Advance the matrix through `solana_localnet` and into `solana_devnet`, or stop with a concrete later-chain blocker.
6. Keep this slice evidence-focused with no public runtime contract drift.

## Outcome
1. `hardhat_local`, `base_sepolia`, `ethereum_sepolia`, and `solana_localnet` are green.
2. The ordered matrix now advances to `solana_devnet`.
3. The concrete later-chain blocker is `wallet_passphrase_mismatch` during Solana devnet wallet preflight.

## Non-goals
1. No API route/schema/database changes.
2. No runtime refactor beyond the minimum harness/matrix/server glue and bounded retry classification needed for truthful live evidence.
3. No Hedera evidence in this slice.

## Locked scope
1. `apps/agent-runtime/scripts/wallet_approval_harness.py`
2. `apps/agent-runtime/scripts/wallet_approval_chain_matrix.py`
3. `apps/agent-runtime/tests/test_wallet_approval_harness.py`
4. `apps/agent-runtime/tests/test_wallet_approval_chain_matrix.py`
5. `apps/network-web/src/app/api/v1/agent/faucet/request/route.ts`
6. `apps/network-web/src/app/api/v1/agent/faucet/networks/route.ts`
7. `apps/network-web/src/lib/solana-localnet-bootstrap-env.ts`
8. `apps/network-web/src/lib/solana-faucet.ts`
9. `apps/agent-runtime/xclaw_agent/cli.py`
10. `infrastructure/scripts/solana-localnet-bootstrap.mjs`
11. `infrastructure/scripts/management-solana-contract-tests.mjs`
12. `infrastructure/scripts/faucet-contract-tests.mjs`
13. `infrastructure/seed-data/hardhat-local-deploy.json`
14. `infrastructure/seed-data/hardhat-local-verify.json`
15. `docs/XCLAW_SOURCE_OF_TRUTH.md`
16. `docs/XCLAW_SLICE_TRACKER.md`
17. `docs/XCLAW_BUILD_ROADMAP.md`
18. `docs/CONTEXT_PACK.md`
19. `spec.md`
20. `tasks.md`
21. `acceptance.md`
