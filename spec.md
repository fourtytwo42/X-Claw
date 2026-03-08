# Slice 233 Spec: Runtime State + Auth/Policy Services (2026-03-08)

Issue mapping: `#86`

## Goal
1. Move runtime auth/state/policy/trade-cap helper ownership out of `cli.py` into runtime services.
2. Preserve current command contracts, on-disk formats, and existing patch/test seams.
3. Keep `cli.py` as parser/router + thin wrapper surface only for the moved helpers.

## Non-goals
1. No API route/schema/database changes.
2. No auth/approval/product behavior redesign.
3. No CLI contract changes.

## Locked scope
1. `apps/agent-runtime/xclaw_agent/cli.py`
2. `apps/agent-runtime/xclaw_agent/runtime/services/__init__.py`
3. `apps/agent-runtime/xclaw_agent/runtime/services/runtime_state.py`
4. `apps/agent-runtime/xclaw_agent/runtime/services/transfer_policy.py`
5. `apps/agent-runtime/xclaw_agent/runtime/services/trade_caps.py`
5. `apps/agent-runtime/tests/test_runtime_services.py`
6. `apps/agent-runtime/tests/test_trade_path.py`
7. `apps/agent-runtime/tests/test_approvals_run_loop.py`
8. `apps/agent-runtime/tests/test_wallet_core.py`
11. `docs/XCLAW_SOURCE_OF_TRUTH.md`
12. `docs/XCLAW_SLICE_TRACKER.md`
13. `docs/XCLAW_BUILD_ROADMAP.md`
14. `docs/CONTEXT_PACK.md`
15. `spec.md`
16. `tasks.md`
17. `acceptance.md`
