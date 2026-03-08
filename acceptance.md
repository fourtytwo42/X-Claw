# Slice 229 Acceptance Evidence: Service Extraction from cli and Final Router Reduction

Date (UTC): 2026-03-08  
Active slice context: `Slice 229`.

Issue mapping: `#82`

### Objective + Scope Lock
- Objective:
  - move remaining shared helper graphs used by extracted command families out of `cli.py`,
  - preserve existing runtime JSON/CLI behavior,
  - keep `cli.py` as parser/router + adapter factory + thin service wrappers.

### Behavior Checks
- [x] mirror/report helper groups used by extracted command families live in runtime services.
- [x] `cli.py` wrappers remain thin and continue exposing the same command/test seams.
- [x] command modules remain independent from `cli.py` internals via adapters and service-backed wrappers.

### Required Validation Gates
- [x] `npm run db:parity` -> PASS (`ok: true`, `checkedAt=2026-03-08T17:41:47.703Z`)
- [x] `npm run seed:reset` -> PASS
- [x] `npm run seed:load` -> PASS
- [x] `npm run seed:verify` -> PASS
- [x] `python3 -m unittest -v apps/agent-runtime/tests/test_runtime_adapters.py` -> PASS (`Ran 13 tests`, `OK`)
- [x] `python3 -m unittest -v apps/agent-runtime/tests/test_approvals_run_loop.py` -> PASS (`Ran 3 tests`, `OK`)
- [x] `python3 -m unittest -v apps/agent-runtime/tests/test_liquidity_cli.py` -> PASS (`Ran 20 tests`, `OK`)
- [x] `python3 -m unittest -v apps/agent-runtime/tests/test_x402_cli.py` -> PASS (`Ran 3 tests`, `OK`)
- [x] `python3 -m unittest -v apps/agent-runtime/tests/test_trade_path.py` -> PASS (`Ran 147 tests`, `OK`)
- [x] `npm run build` -> PASS (Next.js build completed successfully)
- [x] `pm2 restart all` -> PASS (`xclaw-web online`)
