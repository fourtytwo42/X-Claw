# Slice 240 Acceptance Evidence: Local State, Replay, and Corruption Hardening

Date (UTC): 2026-03-08  
Active slice context: `Slice 240`.

Issue mapping: `#93`

### Objective + Scope Lock
- Objective:
  - harden local runtime state, replay, approval prompt, transfer flow, trade-cap, and policy helpers against corrupted local payloads and duplicate replay cases,
  - preserve runtime JSON/CLI behavior and current command/test contracts,
  - keep public runtime contracts unchanged.

### Behavior Checks
- [x] direct corruption/replay coverage exists for `runtime_state.py`, `transfer_flows.py`, `approval_prompts.py`, `trade_caps.py`, and `transfer_policy.py`.
- [x] malformed local state fails closed or resets to the existing safe empty state contract without silent bad behavior.
- [x] replay, queue, and stale-recovery behavior remain deterministic and idempotent.
- [x] command-family regressions remain green.

### Required Validation Gates
- [x] `python3 -m unittest -v apps/agent-runtime/tests/test_runtime_services.py`
- [x] `python3 -m unittest -v apps/agent-runtime/tests/test_trade_path.py`
- [x] `python3 -m unittest -v apps/agent-runtime/tests/test_approvals_run_loop.py`
- [x] `python3 -m unittest -v apps/agent-runtime/tests/test_liquidity_cli.py`
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] `npm run build`
- [x] `pm2 restart all`

### Evidence
- Direct service coverage added in [test_runtime_services.py](/home/hendo420/ETHDenver2026/apps/agent-runtime/tests/test_runtime_services.py):
  - `test_approval_prompt_service_invalid_prompt_file_falls_back_to_empty`
  - `test_runtime_state_service_corrupted_pending_files_reset_to_safe_empty`
  - `test_runtime_state_service_env_api_key_takes_precedence_over_state`
  - `test_transfer_policy_service_invalid_state_and_older_remote_preserve_safe_local`
  - `test_trade_caps_service_replay_deduplicates_duplicate_idempotency_keys`
  - `test_transfer_flow_service_native_balance_precondition_fails_closed`
- Runtime change in [trade_caps.py](/home/hendo420/ETHDenver2026/apps/agent-runtime/xclaw_agent/runtime/services/trade_caps.py):
  - `replay_trade_usage_outbox(...)` now deduplicates duplicate queued entries by `idempotencyKey` before replaying usage posts.
- Validation results:
  - `python3 -m unittest -v apps/agent-runtime/tests/test_runtime_services.py` -> `Ran 47 tests`, `OK`
  - `python3 -m unittest -v apps/agent-runtime/tests/test_trade_path.py` -> `Ran 147 tests`, `OK`
  - `python3 -m unittest -v apps/agent-runtime/tests/test_approvals_run_loop.py` -> `Ran 3 tests`, `OK`
  - `python3 -m unittest -v apps/agent-runtime/tests/test_liquidity_cli.py` -> `Ran 20 tests`, `OK`
  - `npm run db:parity` -> `checkedAt=2026-03-08T20:57:12.912Z`
  - `npm run seed:reset` -> `ok: true`
  - `npm run seed:load` -> `ok: true`, `loadedAt=2026-03-08T20:57:17.434Z`
  - `npm run seed:verify` -> `ok: true`
  - tracked seed file restored via `git show HEAD:infrastructure/seed-data/.seed-state.json > infrastructure/seed-data/.seed-state.json`
  - `npm run build` -> `ok`
  - `pm2 restart all` -> `xclaw-web online`
