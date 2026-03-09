# Slice 245 Spec: Solana Devnet Passphrase-Source Alignment (2026-03-09)

Issue mapping: `#98`

## Goal
1. Align live harness wallet passphrase sourcing with the installed skill config.
2. Clear the Solana devnet `wallet_passphrase_mismatch` preflight blocker.
3. Advance Solana devnet evidence to the next truthful blocker or full green completion.
4. Keep this slice evidence-focused with no public runtime contract drift.

## Outcome
1. Harness wallet preflight now resolves passphrase from installed skill config when arg/env are absent.
2. The Solana devnet passphrase blocker is cleared.
3. The next truthful Solana devnet blocker is `scenario_funding_missing` for the repaired devnet wallet.

## Non-goals
1. No API route/schema/database changes.
2. No runtime refactor beyond the minimum harness fallback logic needed for truthful live evidence.
3. No Hedera evidence in this slice.

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
