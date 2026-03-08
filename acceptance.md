# Slice 241 Acceptance Evidence: Command-Surface Failure Injection Sweep

Date (UTC): 2026-03-08  
Active slice context: `Slice 241`.

Issue mapping: `#94`

### Objective + Scope Lock
- Objective:
  - harden wallet, trade, approvals, limit-order, liquidity, and x402 command surfaces under injected runtime-service failures,
  - preserve current EVM/Solana JSON error contracts and command semantics,
  - keep public runtime contracts unchanged.

### Behavior Checks
- [x] command-surface failure injection covers wallet, trade, approvals, limit-orders, liquidity, and x402 families.
- [x] EVM and Solana degraded-path error codes and JSON field names remain stable where semantics match.
- [x] no mock/stub execution regressions or duplicate queue/replay side effects are introduced.
- [x] command-family regressions remain green.

### Required Validation Gates
- [x] expanded command-surface failure-injection suites for wallet/trade/approvals/limit-orders/liquidity/x402
- [x] `python3 -m unittest -v apps/agent-runtime/tests/test_runtime_invariants.py`
- [x] `python3 -m unittest -v apps/agent-runtime/tests/test_runtime_services.py`
- [x] `python3 -m unittest -v apps/agent-runtime/tests/test_runtime_adapters.py`
- [x] `python3 -m unittest -v apps/agent-runtime/tests/test_trade_path.py`
- [x] `python3 -m unittest -v apps/agent-runtime/tests/test_liquidity_cli.py`
- [x] `python3 -m unittest -v apps/agent-runtime/tests/test_x402_cli.py`
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] `npm run build`
- [x] `pm2 restart all`

### Evidence
- Runtime bug fix in [trade.py](/home/hendo420/ETHDenver2026/apps/agent-runtime/xclaw_agent/commands/trade.py):
  - `cmd_trade_execute(...)` now enforces `mode=real` before entering either the EVM or Solana execution branch, closing the prior Solana mock-execution gap.
- Command-surface failure-injection coverage added:
  - [test_trade_path.py](/home/hendo420/ETHDenver2026/apps/agent-runtime/tests/test_trade_path.py)
    - `test_trade_execute_solana_rejects_mock_mode`
    - `test_trade_execute_fails_closed_when_status_posting_rejected`
    - `test_wallet_send_fails_when_approval_sync_missing`
    - `test_approvals_decide_transfer_x402_fallback_survives_best_effort_mirror_failure`
  - [test_liquidity_cli.py](/home/hendo420/ETHDenver2026/apps/agent-runtime/tests/test_liquidity_cli.py)
    - `test_liquidity_execute_fails_closed_when_status_post_rejected`
  - [test_x402_cli.py](/home/hendo420/ETHDenver2026/apps/agent-runtime/tests/test_x402_cli.py)
    - `test_x402_pay_best_effort_mirror_failure_does_not_change_payload`
  - [test_runtime_invariants.py](/home/hendo420/ETHDenver2026/apps/agent-runtime/tests/test_runtime_invariants.py)
    - `test_trade_execute_mock_mode_rejected_for_evm_and_solana_invariant`
- Validation results:
  - `python3 -m unittest -v apps/agent-runtime/tests/test_runtime_invariants.py` -> `Ran 5 tests`, `OK`
  - `python3 -m unittest -v apps/agent-runtime/tests/test_runtime_services.py` -> `Ran 47 tests`, `OK`
  - `python3 -m unittest -v apps/agent-runtime/tests/test_runtime_adapters.py` -> `Ran 13 tests`, `OK`
  - `python3 -m unittest -v apps/agent-runtime/tests/test_trade_path.py` -> `Ran 151 tests`, `OK`
  - `python3 -m unittest -v apps/agent-runtime/tests/test_liquidity_cli.py` -> `Ran 21 tests`, `OK`
  - `python3 -m unittest -v apps/agent-runtime/tests/test_x402_cli.py` -> `Ran 4 tests`, `OK`
  - `npm run db:parity` -> `checkedAt=2026-03-08T21:07:00.617Z`
  - `npm run seed:reset` -> `ok: true`
  - `npm run seed:load` -> `ok: true`, `loadedAt=2026-03-08T21:07:06.453Z`
  - `npm run seed:verify` -> `ok: true`
  - tracked seed file restored via `git show HEAD:infrastructure/seed-data/.seed-state.json > infrastructure/seed-data/.seed-state.json`
  - `npm run build` -> `ok`
  - `pm2 restart all` -> `xclaw-web online`
