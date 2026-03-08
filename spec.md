# Slice 230 Spec: Transfer Execution and Approval Prompt Services (2026-03-08)

Issue mapping: `#83`

## Goal
1. Move transfer-flow persistence/recovery and transfer execution helper ownership out of `cli.py` into runtime services.
2. Move approval prompt persistence, trade approval wait-loop handling, and prompt cleanup helper ownership out of `cli.py` into runtime services.
3. Preserve all current CLI verbs, flags, JSON response shapes, exit codes, and custody/auth boundaries.

## Non-goals
1. No API route/schema/database changes.
2. No execution-engine redesign.
3. No command-surface changes.

## Locked scope
1. `apps/agent-runtime/xclaw_agent/cli.py`
2. `apps/agent-runtime/xclaw_agent/runtime/services/__init__.py`
3. `apps/agent-runtime/xclaw_agent/runtime/services/transfer_flows.py`
4. `apps/agent-runtime/xclaw_agent/runtime/services/approval_prompts.py`
5. `apps/agent-runtime/tests/test_runtime_services.py`
6. `apps/agent-runtime/tests/test_trade_path.py`
7. `apps/agent-runtime/tests/test_approvals_run_loop.py`
8. `docs/XCLAW_SOURCE_OF_TRUTH.md`
9. `docs/XCLAW_SLICE_TRACKER.md`
10. `docs/XCLAW_BUILD_ROADMAP.md`
11. `docs/CONTEXT_PACK.md`
12. `spec.md`
13. `tasks.md`
14. `acceptance.md`
