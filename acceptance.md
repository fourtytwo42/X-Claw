# Slice 236 Acceptance Evidence: API/Mirroring/Reporting Failure-Injection Hardening

Date (UTC): 2026-03-08  
Active slice context: `Slice 236`.

Issue mapping: `#90`

### Objective + Scope Lock
- Objective:
  - harden runtime API, mirroring, and reporting services against malformed and non-2xx responses,
  - preserve runtime JSON/CLI behavior and delivery/reporting contracts,
  - keep patch/test seams stable.

### Behavior Checks
- [x] direct negative-path coverage exists for `agent_api.py`, `mirroring.py`, and `reporting.py`.
- [x] required-delivery vs best-effort mirror behavior is deterministic and preserved.
- [x] reporting/status helpers fail closed on malformed or non-2xx API responses without payload drift.
- [x] `cli.py` public wrapper/test seams remain unchanged for affected callers.

### Required Validation Gates
- [x] `python3 -m unittest -v apps/agent-runtime/tests/test_runtime_services.py`
- [x] `python3 -m unittest -v apps/agent-runtime/tests/test_trade_path.py`
- [x] `python3 -m unittest -v apps/agent-runtime/tests/test_x402_cli.py`
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] `npm run build`
- [x] `pm2 restart all`

### Evidence
- `python3 -m unittest -v apps/agent-runtime/tests/test_runtime_services.py` -> `Ran 26 tests`, `OK`
- `python3 -m unittest -v apps/agent-runtime/tests/test_trade_path.py` -> `Ran 147 tests`, `OK`
- `python3 -m unittest -v apps/agent-runtime/tests/test_x402_cli.py` -> `Ran 3 tests`, `OK`
- `npm run db:parity` -> `ok: true`, `checkedAt=2026-03-08T20:18:34.609Z`
- `npm run seed:reset` -> `ok: true`
- `npm run seed:load` -> `ok: true`
- `npm run seed:verify` -> `ok: true`
- `npm run build` -> `Compiled successfully`, `Running TypeScript`, static pages generated successfully
- `pm2 restart all` -> `xclaw-web online`
