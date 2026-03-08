# Slice 233 Acceptance Evidence: Runtime State + Auth/Policy Services

Date (UTC): 2026-03-08  
Active slice context: `Slice 233`.

Issue mapping: `#86`

### Objective + Scope Lock
- Objective:
  - move runtime auth/state/policy/trade-cap helper ownership out of `cli.py`,
  - preserve runtime JSON/CLI behavior and on-disk formats,
  - keep patch/test seams stable through `cli.py` wrappers.

### Behavior Checks
- [x] runtime auth + pending trade/spot flow helper ownership lives in runtime services.
- [x] transfer policy persistence/normalize/sync helper ownership lives in runtime services.
- [x] trade-cap ledger and trade-usage helper ownership lives in runtime services.
- [x] `cli.py` preserves wrapper/test seams for affected callers.
- [x] direct runtime service tests cover the moved service seams.

### Required Validation Gates
- [x] `python3 -m unittest -v apps/agent-runtime/tests/test_runtime_services.py` -> PASS (`Ran 10 tests`, `OK`)
- [x] `python3 -m unittest -v apps/agent-runtime/tests/test_trade_path.py apps/agent-runtime/tests/test_wallet_core.py apps/agent-runtime/tests/test_approvals_run_loop.py` -> PASS (`Ran 162 tests`, `OK`)
- [x] `npm run db:parity` -> PASS (`ok: true`, `checkedAt=2026-03-08T19:08:31.929Z`)
- [x] `npm run seed:reset` -> PASS
- [x] `npm run seed:load` -> PASS
- [x] `npm run seed:verify` -> PASS
- [x] `npm run build` -> PASS (Next.js build completed successfully)
- [x] `pm2 restart all` -> PASS (`xclaw-web online`)
