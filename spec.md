# Slice 237 Spec: Transfer-Flow/Approval-Prompt/Trade-Cap Resilience (2026-03-08)

Issue mapping: `#91`

## Goal
1. Add deterministic resilience coverage for transfer-flow, approval-prompt, and trade-cap services.
2. Preserve current command contracts, approval/replay semantics, and existing patch/test seams.
3. Keep this slice runtime-internal only with no public contract drift.

## Non-goals
1. No API route/schema/database changes.
2. No public approval/transfer/reporting payload redesign.
3. No CLI contract changes or new command extraction.

## Locked scope
1. `apps/agent-runtime/xclaw_agent/runtime/services/transfer_flows.py`
2. `apps/agent-runtime/xclaw_agent/runtime/services/approval_prompts.py`
3. `apps/agent-runtime/xclaw_agent/runtime/services/trade_caps.py`
5. `apps/agent-runtime/tests/test_runtime_services.py`
6. `apps/agent-runtime/tests/test_trade_path.py`
7. `apps/agent-runtime/tests/test_approvals_run_loop.py`
8. `apps/agent-runtime/tests/test_liquidity_cli.py`
10. `docs/XCLAW_SOURCE_OF_TRUTH.md`
11. `docs/XCLAW_SLICE_TRACKER.md`
12. `docs/XCLAW_BUILD_ROADMAP.md`
13. `docs/CONTEXT_PACK.md`
14. `spec.md`
15. `tasks.md`
16. `acceptance.md`
