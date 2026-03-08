# Slice 231 Acceptance Evidence: Trade Router Execution Service Extraction

Date (UTC): 2026-03-08  
Active slice context: `Slice 231`.

Issue mapping: `#84`

### Objective + Scope Lock
- Objective:
  - move shared trade/router receipt, allowance, quote, and execute helper ownership out of `cli.py`,
  - preserve trade/liquidity runtime JSON/CLI behavior,
  - keep patch/test seams stable through `cli.py` wrappers.

### Behavior Checks
- [x] shared trade/router helper ownership lives in runtime services.
- [x] `cli.py` preserves wrapper/test seams for trade and liquidity callers.
- [x] direct runtime service tests cover the moved trade/router helpers.

### Required Validation Gates
- [x] `python3 -m unittest -v apps/agent-runtime/tests/test_runtime_services.py apps/agent-runtime/tests/test_trade_path.py apps/agent-runtime/tests/test_liquidity_cli.py` -> PASS (`Ran 171 tests`, `OK`)
- [x] `npm run db:parity` -> PASS (`ok: true`, `checkedAt=2026-03-08T18:22:32.219Z`)
- [x] `npm run seed:reset` -> PASS
- [x] `npm run seed:load` -> PASS
- [x] `npm run seed:verify` -> PASS
- [x] `npm run build` -> PASS (Next.js build completed successfully)
- [x] `pm2 restart all` -> PASS (`xclaw-web online`)
