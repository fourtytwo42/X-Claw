# Slice 229 Spec: Service Extraction from cli and Final Router Reduction (2026-03-08)

Issue mapping: `#82`

## Goal
1. Move remaining shared helper graphs used by extracted command families out of `cli.py` into runtime service modules.
2. Preserve all current CLI verbs, flags, JSON response shapes, exit codes, and custody/auth boundaries.
3. Keep `cli.py` as parser/router + adapter factory + thin service wrapper surface only.

## Non-goals
1. No API route/schema/database changes.
2. No runtime behavior redesign for execution engines.
3. No new command-family extractions in this slice.

## Locked scope
1. `apps/agent-runtime/xclaw_agent/cli.py`
2. `apps/agent-runtime/xclaw_agent/runtime/services/__init__.py`
3. `apps/agent-runtime/xclaw_agent/runtime/services/agent_api.py`
4. `apps/agent-runtime/xclaw_agent/runtime/services/mirroring.py`
5. `apps/agent-runtime/xclaw_agent/runtime/services/reporting.py`
6. `apps/agent-runtime/tests/test_runtime_adapters.py`
7. `apps/agent-runtime/tests/test_approvals_run_loop.py`
8. `apps/agent-runtime/tests/test_liquidity_cli.py`
9. `apps/agent-runtime/tests/test_x402_cli.py`
10. `apps/agent-runtime/tests/test_trade_path.py`
11. `docs/XCLAW_SOURCE_OF_TRUTH.md`
12. `docs/XCLAW_SLICE_TRACKER.md`
13. `docs/XCLAW_BUILD_ROADMAP.md`
14. `docs/CONTEXT_PACK.md`
15. `spec.md`
16. `tasks.md`
17. `acceptance.md`
