# Slice 231 Spec: Trade Router Execution Service Extraction (2026-03-08)

Issue mapping: `#84`

## Goal
1. Move shared trade/router execution helper ownership out of `cli.py` into runtime services.
2. Preserve current trade/liquidity command contracts and existing patch/test seams.
3. Keep `cli.py` as parser/router + thin wrapper surface for the moved trade/router helpers.

## Non-goals
1. No API route/schema/database changes.
2. No liquidity execution-engine redesign.
3. No CLI contract changes.

## Locked scope
1. `apps/agent-runtime/xclaw_agent/cli.py`
2. `apps/agent-runtime/xclaw_agent/runtime/services/__init__.py`
3. `apps/agent-runtime/xclaw_agent/runtime/services/trade_execution.py`
4. `apps/agent-runtime/tests/test_runtime_services.py`
5. `apps/agent-runtime/tests/test_trade_path.py`
6. `apps/agent-runtime/tests/test_liquidity_cli.py`
7. `docs/XCLAW_SOURCE_OF_TRUTH.md`
8. `docs/XCLAW_SLICE_TRACKER.md`
9. `docs/XCLAW_BUILD_ROADMAP.md`
10. `docs/CONTEXT_PACK.md`
11. `spec.md`
12. `tasks.md`
13. `acceptance.md`
