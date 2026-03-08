# Slice 240 Spec: Local State, Replay, and Corruption Hardening (2026-03-08)

Issue mapping: `#93`

## Goal
1. Add deterministic corruption/replay coverage for local-state runtime services.
2. Make replay and stale/local recovery behavior deterministic and idempotent without public contract drift.
3. Keep this slice runtime-internal only with no public contract drift.

## Non-goals
1. No API route/schema/database changes.
2. No CLI contract changes or extraction work.
3. No redesign of approval lifecycle or transfer-policy product semantics.

## Locked scope
1. `apps/agent-runtime/tests/test_runtime_services.py`
2. `apps/agent-runtime/tests/test_trade_path.py`
3. `apps/agent-runtime/tests/test_approvals_run_loop.py`
4. `apps/agent-runtime/tests/test_liquidity_cli.py`
5. `apps/agent-runtime/xclaw_agent/runtime/services/runtime_state.py`
6. `apps/agent-runtime/xclaw_agent/runtime/services/transfer_flows.py`
7. `apps/agent-runtime/xclaw_agent/runtime/services/approval_prompts.py`
8. `apps/agent-runtime/xclaw_agent/runtime/services/trade_caps.py`
9. `apps/agent-runtime/xclaw_agent/runtime/services/transfer_policy.py`
8. `docs/XCLAW_SOURCE_OF_TRUTH.md`
9. `docs/XCLAW_SLICE_TRACKER.md`
10. `docs/XCLAW_BUILD_ROADMAP.md`
11. `docs/CONTEXT_PACK.md`
12. `spec.md`
13. `tasks.md`
14. `acceptance.md`
