# Slice 227 Spec: Explicit Adapters for Approvals and Trade (2026-03-08)

Issue mapping: `#80`

## Goal
1. Replace dynamic runtime binding for approvals and trade command modules with explicit typed adapters.
2. Preserve all current CLI verbs, flags, JSON response shapes, exit codes, and custody/auth boundaries.
3. Keep `cli.py` as router + adapter factory for approvals and trade entrypoints.

## Non-goals
1. No API route/schema/database changes.
2. No runtime behavior redesign for approval or trade execution engines.
3. No wallet, limit-order, liquidity, or x402 adapter changes in this slice beyond compatibility wiring.

## Locked scope
1. `apps/agent-runtime/xclaw_agent/cli.py`
2. `apps/agent-runtime/xclaw_agent/commands/approvals.py`
3. `apps/agent-runtime/xclaw_agent/commands/trade.py`
4. `apps/agent-runtime/xclaw_agent/runtime/adapters/approvals.py`
5. `apps/agent-runtime/xclaw_agent/runtime/adapters/trade.py`
6. `apps/agent-runtime/xclaw_agent/runtime/services/agent_api.py`
7. `apps/agent-runtime/tests/test_runtime_adapters.py`
8. `apps/agent-runtime/tests/test_approvals_run_loop.py`
9. `apps/agent-runtime/tests/test_trade_path.py`
10. `docs/XCLAW_SOURCE_OF_TRUTH.md`
11. `docs/XCLAW_SLICE_TRACKER.md`
12. `docs/XCLAW_BUILD_ROADMAP.md`
13. `docs/CONTEXT_PACK.md`
14. `spec.md`
15. `tasks.md`
16. `acceptance.md`
