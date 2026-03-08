# Slice 236 Spec: API/Mirroring/Reporting Failure-Injection Hardening (2026-03-08)

Issue mapping: `#90`

## Goal
1. Add deterministic negative-path hardening for runtime API, mirroring, and reporting services.
2. Preserve current command contracts, payload semantics, and existing patch/test seams.
3. Keep this slice runtime-internal only with no public contract drift.

## Non-goals
1. No API route/schema/database changes.
2. No public reporting/mirroring payload redesign.
3. No CLI contract changes or new command extraction.

## Locked scope
1. `apps/agent-runtime/xclaw_agent/runtime/services/agent_api.py`
2. `apps/agent-runtime/xclaw_agent/runtime/services/mirroring.py`
3. `apps/agent-runtime/xclaw_agent/runtime/services/reporting.py`
5. `apps/agent-runtime/tests/test_runtime_services.py`
6. `apps/agent-runtime/tests/test_trade_path.py`
7. `apps/agent-runtime/tests/test_x402_cli.py`
10. `docs/XCLAW_SOURCE_OF_TRUTH.md`
11. `docs/XCLAW_SLICE_TRACKER.md`
12. `docs/XCLAW_BUILD_ROADMAP.md`
13. `docs/CONTEXT_PACK.md`
14. `spec.md`
15. `tasks.md`
16. `acceptance.md`
