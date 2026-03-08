# Slice 232 Spec: Final cli.py Reduction + Service-Hardening Pass (2026-03-08)

Issue mapping: `#85`

## Goal
1. Move the remaining provider/liquidity execution helper ownership out of `cli.py` into runtime services.
2. Preserve current trade/liquidity command contracts and existing patch/test seams.
3. Keep `cli.py` as parser/router + thin wrapper surface only for the moved helpers.

## Non-goals
1. No API route/schema/database changes.
2. No trade or liquidity execution-engine redesign.
3. No CLI contract changes.

## Locked scope
1. `apps/agent-runtime/xclaw_agent/cli.py`
2. `apps/agent-runtime/xclaw_agent/runtime/services/__init__.py`
3. `apps/agent-runtime/xclaw_agent/runtime/services/execution_contracts.py`
4. `apps/agent-runtime/xclaw_agent/runtime/services/liquidity_execution.py`
5. `apps/agent-runtime/tests/test_runtime_services.py`
6. `apps/agent-runtime/tests/test_runtime_adapters.py`
7. `apps/agent-runtime/tests/test_trade_path.py`
8. `apps/agent-runtime/tests/test_approvals_run_loop.py`
9. `apps/agent-runtime/tests/test_liquidity_cli.py`
10. `apps/agent-runtime/tests/test_x402_cli.py`
11. `docs/XCLAW_SOURCE_OF_TRUTH.md`
12. `docs/XCLAW_SLICE_TRACKER.md`
13. `docs/XCLAW_BUILD_ROADMAP.md`
14. `docs/CONTEXT_PACK.md`
15. `spec.md`
16. `tasks.md`
17. `acceptance.md`
