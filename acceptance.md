# Slice 234 Acceptance Evidence: Telegram Messaging + Delivery Cleanup Services

Date (UTC): 2026-03-08  
Active slice context: `Slice 234`.

Issue mapping: `#87`

### Objective + Scope Lock
- Objective:
  - move Telegram and owner-link delivery helper ownership out of `cli.py`,
  - preserve runtime JSON/CLI behavior and approval UX contracts,
  - keep patch/test seams stable through `cli.py` wrappers.

### Behavior Checks
- [x] Telegram transfer/policy/liquidity prompt helper ownership lives in runtime services.
- [x] Telegram decision/terminal/cleanup/bot-token helper ownership lives in runtime services.
- [x] owner-link delivery helper ownership lives in runtime services.
- [x] `cli.py` preserves wrapper/test seams for affected callers.
- [x] direct runtime service tests cover the moved service seams.

### Required Validation Gates
- [x] `python3 -m unittest -v apps/agent-runtime/tests/test_runtime_services.py`
- [x] `python3 -m unittest -v apps/agent-runtime/tests/test_trade_path.py`
- [x] `python3 -m unittest -v apps/agent-runtime/tests/test_approvals_run_loop.py`
- [x] `python3 -m unittest -v apps/agent-runtime/tests/test_liquidity_cli.py`
- [x] `python3 -m unittest -v apps/agent-runtime/tests/test_x402_cli.py`
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] `npm run build`
- [x] `pm2 restart all`

### Evidence
- `python3 -m unittest -v apps/agent-runtime/tests/test_runtime_services.py` -> `Ran 12 tests`, `OK`
- `python3 -m unittest -v apps/agent-runtime/tests/test_trade_path.py apps/agent-runtime/tests/test_approvals_run_loop.py` -> `Ran 150 tests`, `OK`
- `python3 -m unittest -v apps/agent-runtime/tests/test_liquidity_cli.py apps/agent-runtime/tests/test_x402_cli.py` -> `Ran 23 tests`, `OK`
- `npm run db:parity` -> `ok: true`, `checkedAt=2026-03-08T19:58:01.007Z`
- `npm run seed:reset` -> `ok: true`
- `npm run seed:load` -> `ok: true`
- `npm run seed:verify` -> `ok: true`
- `npm run build` -> `Compiled successfully`, `Running TypeScript`, static pages generated successfully
- `pm2 restart all` -> `xclaw-web online`
