# Slice 230 Acceptance Evidence: Transfer Execution and Approval Prompt Services

Date (UTC): 2026-03-08  
Active slice context: `Slice 230`.

Issue mapping: `#83`

### Objective + Scope Lock
- Objective:
  - move transfer-flow persistence/recovery + execution helper ownership out of `cli.py`,
  - move approval prompt persistence/wait-loop/cleanup helper ownership out of `cli.py`,
  - preserve existing runtime JSON/CLI behavior with thin compatibility wrappers.

### Behavior Checks
- [x] transfer flow persistence/recovery + execution helpers live in runtime services.
- [x] approval prompt persistence/wait-loop/cleanup helpers live in runtime services.
- [x] `cli.py` preserves wrapper/test seams while delegating helper ownership.
- [x] direct runtime service tests cover the moved ownership seams.

### Required Validation Gates
- [x] `python3 -m unittest -v apps/agent-runtime/tests/test_runtime_services.py` -> PASS (`Ran 3 tests`, `OK`)
- [x] `python3 -m unittest -v apps/agent-runtime/tests/test_trade_path.py` -> PASS (`Ran 147 tests`, `OK`)
- [x] `python3 -m unittest -v apps/agent-runtime/tests/test_approvals_run_loop.py` -> PASS (`Ran 3 tests`, `OK`)
- [x] `npm run db:parity` -> PASS (`ok: true`, `checkedAt=2026-03-08T18:18:15.027Z`)
- [x] `npm run seed:reset` -> PASS
- [x] `npm run seed:load` -> PASS
- [x] `npm run seed:verify` -> PASS
- [x] `npm run build` -> PASS (Next.js build completed successfully)
- [x] `pm2 restart all` -> PASS (`xclaw-web online`)
