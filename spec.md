# Slice 242 Spec: Runtime Recovery and Watchdog Sweep (2026-03-08)

Issue mapping: `#95`

## Goal
1. Add deterministic restart/replay/recovery coverage for pending flows, prompts, outboxes, and resume paths.
2. Keep recovery semantics stable and idempotent after interruption or reload.
3. Keep this slice runtime-internal only with no public contract drift.

## Non-goals
1. No API route/schema/database changes.
2. No CLI contract changes or extraction work.
3. No real-chain evidence refresh in this slice.

## Locked scope
1. `apps/agent-runtime/tests/test_runtime_services.py`
2. `apps/agent-runtime/tests/test_trade_path.py`
3. `apps/agent-runtime/tests/test_approvals_run_loop.py`
4. `apps/agent-runtime/tests/test_liquidity_cli.py`
5. `apps/agent-runtime/tests/test_runtime_invariants.py`
6. `apps/agent-runtime/xclaw_agent/runtime/services/runtime_state.py`
7. `apps/agent-runtime/xclaw_agent/runtime/services/transfer_flows.py`
8. `apps/agent-runtime/xclaw_agent/runtime/services/approval_prompts.py`
9. `apps/agent-runtime/xclaw_agent/runtime/services/trade_caps.py`
10. `apps/agent-runtime/xclaw_agent/runtime/services/reporting.py`
11. `apps/agent-runtime/xclaw_agent/runtime/services/mirroring.py`
8. `docs/XCLAW_SOURCE_OF_TRUTH.md`
9. `docs/XCLAW_SLICE_TRACKER.md`
10. `docs/XCLAW_BUILD_ROADMAP.md`
11. `docs/CONTEXT_PACK.md`
12. `spec.md`
13. `tasks.md`
14. `acceptance.md`
