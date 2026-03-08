# Slice 226 Spec: Replace Dynamic Runtime Binding with Explicit Adapters (2026-03-08)

Issue mapping: `#79`

## Goal
1. Replace dynamic runtime binding for extracted liquidity and x402 command modules with explicit typed adapters.
2. Preserve all current CLI verbs, flags, JSON response shapes, exit codes, and custody/auth boundaries.
3. Keep `cli.py` as router + adapter factory for liquidity and x402 entrypoints.

## Non-goals
1. No API route/schema/database changes.
2. No runtime behavior redesign for liquidity or x402 execution engines.
3. No refactor of other extracted command families in this slice.

## Locked scope
1. `apps/agent-runtime/xclaw_agent/cli.py`
2. `apps/agent-runtime/xclaw_agent/commands/liquidity.py`
3. `apps/agent-runtime/xclaw_agent/commands/x402.py`
4. `apps/agent-runtime/xclaw_agent/runtime/adapters/liquidity.py`
5. `apps/agent-runtime/xclaw_agent/runtime/adapters/x402.py`
6. `apps/agent-runtime/tests/test_liquidity_cli.py`
7. `apps/agent-runtime/tests/test_x402_cli.py`
8. `apps/agent-runtime/tests/test_x402_runtime.py`
9. `apps/agent-runtime/tests/test_trade_path.py`
10. `apps/agent-runtime/tests/test_runtime_adapters.py`
11. `docs/XCLAW_SOURCE_OF_TRUTH.md`
12. `docs/XCLAW_SLICE_TRACKER.md`
13. `docs/XCLAW_BUILD_ROADMAP.md`
14. `docs/CONTEXT_PACK.md`
15. `spec.md`
16. `tasks.md`
17. `acceptance.md`
