# Slice 238 Spec: Cross-Service Invariants + Residual cli.py Audit (2026-03-08)

Issue mapping: `#89`

## Goal
1. Add direct invariant coverage for required/best-effort delivery, stable reporting payloads, and idempotent replay behavior.
2. Prove the audited residual `cli.py` helpers are thin compatibility wrappers over existing runtime service seams.
3. Keep this slice runtime-internal only with no public contract drift.

## Non-goals
1. No API route/schema/database changes.
2. No CLI contract changes or new extraction family.
3. No forced helper moves out of `cli.py` when an existing service seam is not a clear fit.

## Locked scope
1. `apps/agent-runtime/tests/test_runtime_invariants.py`
2. `apps/agent-runtime/tests/test_runtime_services.py`
3. `apps/agent-runtime/tests/test_runtime_adapters.py`
4. `apps/agent-runtime/tests/test_trade_path.py`
5. `apps/agent-runtime/tests/test_liquidity_cli.py`
6. `apps/agent-runtime/tests/test_x402_cli.py`
7. `apps/agent-runtime/xclaw_agent/cli.py` (audit-only unless a clear service-owned residual helper is found)
8. `docs/XCLAW_SOURCE_OF_TRUTH.md`
9. `docs/XCLAW_SLICE_TRACKER.md`
10. `docs/XCLAW_BUILD_ROADMAP.md`
11. `docs/CONTEXT_PACK.md`
12. `spec.md`
13. `tasks.md`
14. `acceptance.md`
