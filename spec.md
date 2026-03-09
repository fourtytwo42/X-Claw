# Slice 248 Spec: Solana Devnet Capability Boundary Alignment (2026-03-09)

Issue mapping: `#101`

## Goal
1. Align `solana_devnet` advertised capabilities with the truthful live-evidence boundary the app can prove today.
2. Keep Solana devnet green for supported wallet/faucet/deposits/x402 evidence.
3. Stop advertising unsupported Solana devnet trade, liquidity, and limit-order execution surfaces.
4. Preserve all public runtime and API contracts.

## Outcome
1. `config/chains/solana_devnet.json` advertises `trade=false`, `liquidity=false`, and `limitOrders=false` while keeping `wallet`, `faucet`, `deposits`, and `x402` enabled.
2. `wallet_approval_harness.py` no longer requires Solana devnet trade scenarios for green full evidence when trade capability is disabled.
3. Contract rails assert the updated Solana devnet capability boundary directly.
4. Canonical docs and acceptance evidence reflect the supported Solana devnet boundary.

## Non-goals
1. No API schema/database changes.
2. No runtime command contract changes.
3. No new Solana faucet/bootstrap redesign.
4. No re-enabling Solana devnet trade execution without a real quoteable market.

## Locked scope
1. `apps/agent-runtime/scripts/wallet_approval_harness.py`
2. `config/chains/solana_devnet.json`
3. `infrastructure/scripts/management-solana-contract-tests.mjs`
4. `apps/agent-runtime/tests/test_wallet_approval_harness.py`
5. `apps/agent-runtime/tests/test_wallet_approval_chain_matrix.py`
6. `docs/XCLAW_SOURCE_OF_TRUTH.md`
7. `docs/XCLAW_SLICE_TRACKER.md`
8. `docs/XCLAW_BUILD_ROADMAP.md`
9. `docs/CONTEXT_PACK.md`
10. `spec.md`
11. `tasks.md`
12. `acceptance.md`
