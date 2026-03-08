# Slice 242 Acceptance Evidence: Runtime Recovery and Watchdog Sweep

Date (UTC): 2026-03-08  
Active slice context: `Slice 242`.

Issue mapping: `#95`

### Objective + Scope Lock
- Objective:
  - harden restart/replay/recovery behavior for pending flows, prompts, outboxes, and resume paths,
  - preserve current runtime JSON/CLI behavior and recovery semantics,
  - keep public runtime contracts unchanged.

### Behavior Checks
- [x] direct recovery/restart coverage exists for `runtime_state.py`, `transfer_flows.py`, `approval_prompts.py`, `trade_caps.py`, `reporting.py`, and `mirroring.py`.
- [x] pending-flow restart/resume behavior is deterministic and does not silently convert incomplete state into success.
- [x] replay queues remain idempotent after interruption and partial delivery.
- [x] prompt cleanup and resend semantics remain stable after reload.
- [x] command-family regressions remain green.

### Required Validation Gates
- [x] direct recovery/restart coverage for runtime services
- [x] `python3 -m unittest -v apps/agent-runtime/tests/test_trade_path.py`
- [x] `python3 -m unittest -v apps/agent-runtime/tests/test_approvals_run_loop.py`
- [x] `python3 -m unittest -v apps/agent-runtime/tests/test_liquidity_cli.py`
- [x] `python3 -m unittest -v apps/agent-runtime/tests/test_runtime_invariants.py`
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] tracked `infrastructure/seed-data/.seed-state.json` restore
- [x] `npm run build`
- [x] `pm2 restart all`

### Evidence
- Recovery tests added:
  - `apps/agent-runtime/tests/test_runtime_services.py`
    - corrupted pending intent/spot-flow files can be rewritten after restart
    - mirror failure preserves executing transfer flow across restart
    - persisted approval prompt survives restart and resend cooldown
    - trade-usage replay survives restart with deduplicated remaining queue
  - `apps/agent-runtime/tests/test_trade_path.py`
    - stale transfer resume converges once across restart
    - limit-order run-once replays queued status after restart
  - `apps/agent-runtime/tests/test_liquidity_cli.py`
    - liquidity resume reuses execute contract for approved intent
- `python3 -m unittest -v apps/agent-runtime/tests/test_runtime_services.py apps/agent-runtime/tests/test_trade_path.py apps/agent-runtime/tests/test_approvals_run_loop.py apps/agent-runtime/tests/test_liquidity_cli.py apps/agent-runtime/tests/test_runtime_invariants.py`
  - `Ran 234 tests`
  - `OK`
- `npm run db:parity`
  - `ok: true`
  - `checkedAt: 2026-03-08T21:29:41.667Z`
- `npm run seed:reset`
  - `ok: true`
- `npm run seed:load`
  - `ok: true`
  - `loadedAt: 2026-03-08T21:29:49.748Z`
- `npm run seed:verify`
  - `ok: true`
- tracked seed restore:
  - `git show HEAD:infrastructure/seed-data/.seed-state.json > infrastructure/seed-data/.seed-state.json`
- `npm run build`
  - passed
  - Next.js static/dynamic route build completed successfully
- `pm2 restart all`
  - `xclaw-web` restarted
  - status `online`
