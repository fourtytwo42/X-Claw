# Slice 227 Acceptance Evidence: Explicit Adapters for Approvals and Trade

Date (UTC): 2026-03-08  
Active slice context: `Slice 227`.

Issue mapping: `#80`

### Objective + Scope Lock
- Objective:
  - replace dynamic runtime binding for extracted approvals and trade command modules,
  - preserve existing runtime JSON/CLI behavior,
  - keep current patch/test seams intact through `cli.py`.

### Behavior Checks
- [x] explicit adapter types exist under `apps/agent-runtime/xclaw_agent/runtime/adapters/` for approvals and trade.
- [x] approvals and trade command modules no longer depend on `sys.modules[__name__]` dispatch.
- [x] `cli.py` builds explicit approvals/trade adapters and routes command calls through them.
- [x] approvals run-loop/decision patch seams remain intact through `cli.py` wrappers.

### Required Validation Gates
- [x] `npm run db:parity` -> PASS (`ok: true`, `checkedAt=2026-03-08T17:35:34.191Z`)
- [x] `npm run seed:reset` -> PASS
- [x] `npm run seed:load` -> PASS
- [x] `npm run seed:verify` -> PASS
- [x] `python3 -m unittest -v apps/agent-runtime/tests/test_runtime_adapters.py` -> PASS (`Ran 13 tests`, `OK`)
- [x] `python3 -m unittest -v apps/agent-runtime/tests/test_approvals_run_loop.py` -> PASS (`Ran 3 tests`, `OK`)
- [x] `python3 -m unittest -v apps/agent-runtime/tests/test_trade_path.py` -> PASS (`Ran 147 tests`, `OK`)
- [x] `npm run build` -> PASS (Next.js build completed successfully)
- [x] `pm2 restart all` -> PASS (`xclaw-web online`)
