# Slice 247 Spec: Solana Devnet Quoted-Pair Discovery and Evidence Boundary (2026-03-09)

Issue mapping: `#100`

## Goal
1. Determine whether Solana devnet has a truthful Jupiter-quotable pair available for live trade evidence.
2. Use that pair if it exists; otherwise record deterministic unsupported trade evidence without forcing a green trade leg.
3. Keep wallet/faucet/capability proof in scope on Solana devnet even when trade execution is unsupported.
4. Preserve all public runtime and API contracts.

## Outcome
1. `wallet_approval_harness.py` performs a deterministic Solana devnet quoteable-pair discovery step against a small allowlisted candidate set.
2. Harness preflight/report output records machine-readable Solana devnet trade-pair discovery evidence.
3. Solana devnet trade scenarios either use a real quoteable pair or stop with deterministic `unsupported_live_evidence` using `solana_devnet_trade_pair_unavailable`.
4. Non-trade Solana devnet evidence continues after the explicit trade-evidence boundary.

## Non-goals
1. No API schema/database changes.
2. No runtime command contract changes.
3. No new Solana faucet/bootstrap redesign.
4. No synthetic success for Solana devnet trade execution.

## Locked scope
1. `apps/agent-runtime/scripts/wallet_approval_harness.py`
2. `apps/agent-runtime/tests/test_wallet_approval_harness.py`
3. `apps/agent-runtime/tests/test_wallet_approval_chain_matrix.py`
4. `docs/XCLAW_SOURCE_OF_TRUTH.md`
5. `docs/XCLAW_SLICE_TRACKER.md`
6. `docs/XCLAW_BUILD_ROADMAP.md`
7. `docs/CONTEXT_PACK.md`
8. `spec.md`
9. `tasks.md`
10. `acceptance.md`
