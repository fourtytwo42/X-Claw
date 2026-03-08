# Slice 228 Acceptance Evidence: Explicit Adapters for Wallet and Limit-Orders

Date (UTC): 2026-03-08  
Active slice context: `Slice 228`.

Issue mapping: `#81`

### Objective + Scope Lock
- Objective:
  - replace dynamic runtime binding for extracted wallet and limit-order command modules,
  - preserve existing runtime JSON/CLI behavior,
  - keep current patch/test seams intact through `cli.py`.

### Behavior Checks
- [x] explicit adapter types exist under `apps/agent-runtime/xclaw_agent/runtime/adapters/` for wallet and limit-orders.
- [x] wallet and limit-order command modules no longer depend on `sys.modules[__name__]` dispatch.
- [x] `cli.py` builds explicit wallet/limit-order adapters and routes command calls through them.
- [x] direct adapter tests assert wallet/limit-order wrappers receive typed adapters.

### Required Validation Gates
- [x] `npm run db:parity` -> PASS (`ok: true`, `checkedAt=2026-03-08T17:38:26.472Z`)
- [x] `npm run seed:reset` -> PASS
- [x] `npm run seed:load` -> PASS
- [x] `npm run seed:verify` -> PASS
- [x] `python3 -m unittest -v apps/agent-runtime/tests/test_runtime_adapters.py` -> PASS (`Ran 13 tests`, `OK`)
- [x] `python3 -m unittest -v apps/agent-runtime/tests/test_wallet_core.py` -> PASS (`Ran 12 tests`, `OK`)
- [x] `python3 -m unittest -v apps/agent-runtime/tests/test_trade_path.py` -> PASS (`Ran 147 tests`, `OK`)
- [x] `npm run build` -> PASS (Next.js build completed successfully)
- [x] `pm2 restart all` -> PASS (`xclaw-web online`)
