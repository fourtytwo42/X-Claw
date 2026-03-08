# Slice 238 Acceptance Evidence: Cross-Service Invariants + Residual cli.py Audit

Date (UTC): 2026-03-08  
Active slice context: `Slice 238`.

Issue mapping: `#89`

### Objective + Scope Lock
- Objective:
  - add direct cross-service invariant coverage for runtime service seams,
  - prove residual `cli.py` helpers in audited seams are thin compatibility wrappers,
  - preserve runtime JSON/CLI behavior with no public contract drift.

### Behavior Checks
- [x] direct invariant coverage exists for required/best-effort delivery behavior, stable reporting payload fields, and idempotent replay semantics.
- [x] audited `cli.py` helpers that belong to existing service seams are proven to be wrapper-only delegations.
- [x] no additional behavior-heavy helper ownership remains in `cli.py` for the audited service seams.
- [x] command-family regressions remain green.

### Required Validation Gates
- [x] `python3 -m unittest -v apps/agent-runtime/tests/test_runtime_invariants.py`
- [x] `python3 -m unittest -v apps/agent-runtime/tests/test_runtime_services.py`
- [x] `python3 -m unittest -v apps/agent-runtime/tests/test_runtime_adapters.py`
- [x] `python3 -m unittest -v apps/agent-runtime/tests/test_trade_path.py`
- [x] `python3 -m unittest -v apps/agent-runtime/tests/test_liquidity_cli.py`
- [x] `python3 -m unittest -v apps/agent-runtime/tests/test_x402_cli.py`
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] `npm run build`
- [x] `pm2 restart all`

### Evidence
- `python3 -m unittest -v apps/agent-runtime/tests/test_runtime_invariants.py` -> `Ran 4 tests`, `OK`
- `python3 -m unittest -v apps/agent-runtime/tests/test_runtime_services.py` -> `Ran 33 tests`, `OK`
- `python3 -m unittest -v apps/agent-runtime/tests/test_runtime_adapters.py` -> `Ran 13 tests`, `OK`
- `python3 -m unittest -v apps/agent-runtime/tests/test_trade_path.py` -> `Ran 147 tests`, `OK`
- `python3 -m unittest -v apps/agent-runtime/tests/test_liquidity_cli.py` -> `Ran 20 tests`, `OK`
- `python3 -m unittest -v apps/agent-runtime/tests/test_x402_cli.py` -> `Ran 3 tests`, `OK`
- `npm run db:parity` -> `ok: true`, `checkedAt=2026-03-08T20:29:20.450Z`
- `npm run seed:reset` -> `ok: true`
- `npm run seed:load` -> `ok: true`
- `npm run seed:verify` -> `ok: true`
- `npm run build` -> `Compiled successfully`, `Running TypeScript`, static pages generated successfully
- `pm2 restart all` -> `xclaw-web online`

### Residual `cli.py` Audit
- Audited wrapper seams:
  - `_load_pending_transfer_flows`
  - `_record_pending_transfer_flow`
  - `_remove_pending_transfer_flow`
  - `_mirror_transfer_approval`
  - `_mirror_x402_outbound`
  - `_wait_for_trade_approval`
  - `_maybe_send_telegram_approval_prompt`
  - `_clear_telegram_approval_buttons`
  - `_ack_transfer_decision_inbox`
  - `_publish_runtime_signing_readiness`
  - `_post_trade_status`
  - `_post_liquidity_status`
  - `_read_trade_details`
  - `_send_trade_execution_report`
- Result:
  - each audited helper is a thin compatibility wrapper over an existing runtime service seam with context construction only,
  - no further helper move was justified in this slice,
  - no public runtime contract drift was introduced.
