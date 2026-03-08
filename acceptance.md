# Slice 232 Acceptance Evidence: Final cli.py Reduction + Service-Hardening Pass

Date (UTC): 2026-03-08  
Active slice context: `Slice 232`.

Issue mapping: `#85`

### Objective + Scope Lock
- Objective:
  - move the remaining provider/liquidity execution helper ownership out of `cli.py`,
  - preserve trade/liquidity runtime JSON/CLI behavior,
  - keep patch/test seams stable through `cli.py` wrappers.

### Behavior Checks
- [x] provider settings/fallback/provider-meta helper ownership lives in runtime services.
- [x] advanced liquidity nested-command execution helper ownership lives in runtime services.
- [x] `cli.py` preserves wrapper/test seams for trade and liquidity callers.
- [x] direct runtime service tests cover the moved service seams.

### Required Validation Gates
- [x] `python3 -m unittest -v apps/agent-runtime/tests/test_runtime_services.py apps/agent-runtime/tests/test_runtime_adapters.py apps/agent-runtime/tests/test_trade_path.py` -> PASS (`Ran 167 tests`, `OK`)
- [x] `python3 -m unittest -v apps/agent-runtime/tests/test_approvals_run_loop.py apps/agent-runtime/tests/test_liquidity_cli.py apps/agent-runtime/tests/test_x402_cli.py` -> PASS (`Ran 26 tests`, `OK`)
- [x] `npm run db:parity` -> PASS (`ok: true`, `checkedAt=2026-03-08T18:27:25.489Z`)
- [x] `npm run seed:reset` -> PASS
- [x] `npm run seed:load` -> PASS
- [x] `npm run seed:verify` -> PASS
- [x] `npm run build` -> PASS (Next.js build completed successfully)
- [x] `pm2 restart all` -> PASS (`xclaw-web online`)
