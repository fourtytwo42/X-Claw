# Slice 235 Spec: Status/Reporting Services + Final cli.py Audit (2026-03-08)

Issue mapping: `#88`

## Goal
1. Move trade/liquidity status posting and trade-detail/report helper ownership out of `cli.py` into runtime services.
2. Preserve current command contracts, reporting/status semantics, and existing patch/test seams.
3. Keep `cli.py` as parser/router + thin wrapper surface only for the moved helpers.

## Non-goals
1. No API route/schema/database changes.
2. No reporting payload redesign.
3. No CLI contract changes.

## Locked scope
1. `apps/agent-runtime/xclaw_agent/cli.py`
2. `apps/agent-runtime/xclaw_agent/runtime/services/__init__.py`
3. `apps/agent-runtime/xclaw_agent/runtime/services/reporting.py`
5. `apps/agent-runtime/tests/test_runtime_services.py`
6. `apps/agent-runtime/tests/test_trade_path.py`
7. `apps/agent-runtime/tests/test_liquidity_cli.py`
8. `apps/agent-runtime/tests/test_x402_cli.py`
9. `apps/agent-runtime/tests/test_runtime_adapters.py`
10. `docs/XCLAW_SOURCE_OF_TRUTH.md`
11. `docs/XCLAW_SLICE_TRACKER.md`
12. `docs/XCLAW_BUILD_ROADMAP.md`
13. `docs/CONTEXT_PACK.md`
14. `spec.md`
15. `tasks.md`
16. `acceptance.md`
