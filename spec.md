# Slice 241 Spec: Command-Surface Failure Injection Sweep (2026-03-08)

Issue mapping: `#94`

## Goal
1. Add deterministic command-surface failure-injection coverage across wallet, trade, approvals, limit-orders, liquidity, and x402.
2. Keep EVM and Solana degraded-path error contracts aligned where semantics match.
3. Keep this slice runtime-internal only with no public contract drift.

## Non-goals
1. No API route/schema/database changes.
2. No CLI contract changes or extraction work.
3. No new runtime architecture or service extraction unless a test exposes a real gap.

## Locked scope
1. `apps/agent-runtime/tests/test_trade_path.py`
2. `apps/agent-runtime/tests/test_liquidity_cli.py`
3. `apps/agent-runtime/tests/test_x402_cli.py`
4. `apps/agent-runtime/tests/test_runtime_invariants.py`
8. `docs/XCLAW_SOURCE_OF_TRUTH.md`
9. `docs/XCLAW_SLICE_TRACKER.md`
10. `docs/XCLAW_BUILD_ROADMAP.md`
11. `docs/CONTEXT_PACK.md`
12. `spec.md`
13. `tasks.md`
14. `acceptance.md`
