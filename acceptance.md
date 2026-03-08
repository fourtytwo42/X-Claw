# Slice 237 Acceptance Evidence: Transfer-Flow/Approval-Prompt/Trade-Cap Resilience

Date (UTC): 2026-03-08  
Active slice context: `Slice 237`.

Issue mapping: `#91`

### Objective + Scope Lock
- Objective:
  - harden transfer-flow, approval-prompt, and trade-cap services against malformed local state and partial failures,
  - preserve runtime JSON/CLI behavior and approval/replay contracts,
  - keep command-surface behavior stable.

### Behavior Checks
- [x] direct resilience coverage exists for `transfer_flows.py`, `approval_prompts.py`, and `trade_caps.py`.
- [x] stale recovery, resend/cooldown, cleanup failure tolerance, and replay/queue behavior are deterministic and preserved.
- [x] local malformed state fails closed without silent bad behavior.
- [x] command-surface behavior remains unchanged for approvals, transfers, and trade-cap paths.

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
- `python3 -m unittest -v apps/agent-runtime/tests/test_runtime_services.py` -> `Ran 33 tests`, `OK`
- `python3 -m unittest -v apps/agent-runtime/tests/test_trade_path.py` -> `Ran 147 tests`, `OK`
- `python3 -m unittest -v apps/agent-runtime/tests/test_approvals_run_loop.py apps/agent-runtime/tests/test_liquidity_cli.py` -> `Ran 23 tests`, `OK`
- `npm run db:parity` -> `ok: true`, `checkedAt=2026-03-08T20:22:39.139Z`
- `npm run seed:reset` -> `ok: true`
- `npm run seed:load` -> `ok: true`
- `npm run seed:verify` -> `ok: true`
- `npm run build` -> `Compiled successfully`, `Running TypeScript`, static pages generated successfully
- `pm2 restart all` -> `xclaw-web online`
