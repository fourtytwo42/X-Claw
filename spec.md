# Slice 239 Spec: Transport and Remote Failure Hardening (2026-03-08)

Issue mapping: `#92`

## Goal
1. Add deterministic negative-path coverage for remote/API/subprocess-facing runtime services.
2. Preserve current required-delivery vs best-effort behavior without public contract drift.
3. Keep this slice runtime-internal only with no public contract drift.

## Non-goals
1. No API route/schema/database changes.
2. No CLI contract changes or extraction work.
3. No payload/schema redesign for reporting, Telegram callbacks, or owner-link delivery.

## Locked scope
1. `apps/agent-runtime/tests/test_runtime_services.py`
2. `apps/agent-runtime/tests/test_trade_path.py`
3. `apps/agent-runtime/tests/test_x402_cli.py`
4. `apps/agent-runtime/xclaw_agent/runtime/services/agent_api.py`
5. `apps/agent-runtime/xclaw_agent/runtime/services/mirroring.py`
6. `apps/agent-runtime/xclaw_agent/runtime/services/reporting.py`
7. `apps/agent-runtime/xclaw_agent/runtime/services/telegram_delivery.py`
8. `apps/agent-runtime/xclaw_agent/runtime/services/owner_link_delivery.py`
8. `docs/XCLAW_SOURCE_OF_TRUTH.md`
9. `docs/XCLAW_SLICE_TRACKER.md`
10. `docs/XCLAW_BUILD_ROADMAP.md`
11. `docs/CONTEXT_PACK.md`
12. `spec.md`
13. `tasks.md`
14. `acceptance.md`
