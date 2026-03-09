# Slice 246 Spec: Solana Devnet Funding Provisioning and Full Matrix Completion (2026-03-09)

Issue mapping: `#99`

## Goal
1. Add explicit Solana devnet funding/provisioning for live evidence.
2. Clear the current `scenario_funding_missing` blocker on `solana_devnet`.
3. Advance the ordered matrix beyond the current `solana_devnet` stop, accepting a later truthful blocker after funding and wallet preflight are green.
4. Keep the slice limited to funding/provisioning/evidence work with no public runtime contract drift.

## Outcome
1. `solana_devnet` is faucet-capable through chain-scoped env rather than static hardcoded mint config.
2. Harness devnet token resolution and top-up use scoped Solana devnet mint/RPC/signer configuration.
3. The matrix advances beyond the current devnet funding blocker or records the next truthful later blocker.
4. If funded devnet custom mints are not Jupiter-quotable, the harness reports deterministic `solana_devnet_custom_mint_trade_unsupported` evidence instead of a generic trade wrapper failure.

## Non-goals
1. No API schema/database changes.
2. No wallet decryption or passphrase-source redesign.
3. No Hedera evidence in this slice.

## Locked scope
1. `config/chains/solana_devnet.json`
2. `apps/agent-runtime/scripts/wallet_approval_harness.py`
3. `apps/agent-runtime/tests/test_wallet_approval_harness.py`
4. `apps/agent-runtime/tests/test_wallet_approval_chain_matrix.py`
5. `apps/network-web/src/app/api/v1/agent/faucet/request/route.ts`
6. `apps/network-web/src/app/api/v1/agent/faucet/networks/route.ts`
7. `apps/network-web/src/lib/solana-faucet.ts`
8. `infrastructure/scripts/faucet-contract-tests.mjs`
9. `docs/XCLAW_SOURCE_OF_TRUTH.md`
10. `docs/XCLAW_SLICE_TRACKER.md`
11. `docs/XCLAW_BUILD_ROADMAP.md`
12. `docs/CONTEXT_PACK.md`
13. `spec.md`
14. `tasks.md`
15. `acceptance.md`
