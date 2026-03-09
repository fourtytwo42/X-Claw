# Slice 248 Acceptance Evidence: Solana Devnet Capability Boundary Alignment

Date (UTC): 2026-03-09  
Active slice context: `Slice 248`.

Issue mapping: `#101`

### Objective + Scope Lock
- Objective:
  - align `solana_devnet` advertised capabilities with the truthful live-evidence boundary the app can prove today,
  - keep wallet/faucet/deposits/x402 green on Solana devnet,
  - stop advertising unsupported trade/liquidity/limit-order execution features on Solana devnet,
  - keep the slice limited to capability-boundary alignment with no public runtime contract drift.

### Behavior Checks
- [x] `solana_devnet` no longer advertises `trade`, `liquidity`, or `limitOrders`.
- [x] `solana_devnet` still advertises `wallet`, `faucet`, `deposits`, and `x402`.
- [x] Solana devnet full harness evidence no longer requires trade scenarios when trade capability is disabled.
- [x] Targeted Solana devnet evidence remains green for the supported boundary.

### Required Validation Gates
- [x] `python3 -m unittest -v apps/agent-runtime/tests/test_wallet_approval_harness.py`
- [x] `python3 -m unittest -v apps/agent-runtime/tests/test_wallet_approval_chain_matrix.py`
- [x] `python3 -m unittest -v apps/agent-runtime/tests/test_trade_path.py apps/agent-runtime/tests/test_wallet_approval_harness.py apps/agent-runtime/tests/test_wallet_approval_chain_matrix.py`
- [x] `npm run test:faucet:contract`
- [x] `npm run test:management:solana:contract`
- [x] `npm run test:x402:solana:contract`
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] tracked `infrastructure/seed-data/.seed-state.json` restore
- [x] targeted live `solana_devnet` rerun
- [x] `npm run build`
- [x] `pm2 restart all`

### Evidence
- Capability boundary:
  - [solana_devnet.json](/home/hendo420/ETHDenver2026/config/chains/solana_devnet.json)
    - `trade=false`
    - `liquidity=false`
    - `limitOrders=false`
    - `wallet=true`
    - `faucet=true`
    - `deposits=true`
    - `x402=true`
- Harness boundary handling:
  - [wallet_approval_harness.py](/home/hendo420/ETHDenver2026/apps/agent-runtime/scripts/wallet_approval_harness.py)
    - `solana_devnet` full runs now record `preflight.solanaDevnetTradePair.reason=solana_devnet_trade_disabled`
    - supported boundary scenarios remain `transfer_only` and `x402_or_capability_assertion`
- Contract alignment:
  - [management-solana-contract-tests.mjs](/home/hendo420/ETHDenver2026/infrastructure/scripts/management-solana-contract-tests.mjs)
    - `solana_devnet_trade_disabled`
    - `solana_devnet_liquidity_disabled`
    - `solana_devnet_limit_orders_disabled`
- Targeted live Solana devnet report:
  - `/tmp/xclaw-slice248-solana-devnet-full.json`
  - Outcome:
    - `ok=true`
    - `preflight.walletDecryptProbe.passphraseSource=skill_config`
    - `preflight.solanaDevnetTradePair.reason=solana_devnet_trade_disabled`
    - `transfer_only` passed
    - `x402_or_capability_assertion` passed
- Validation results:
  - `python3 -m unittest -v apps/agent-runtime/tests/test_wallet_approval_harness.py` -> `Ran 65 tests`, `OK`
  - `python3 -m unittest -v apps/agent-runtime/tests/test_wallet_approval_chain_matrix.py` -> `Ran 10 tests`, `OK`
  - `python3 -m unittest -v apps/agent-runtime/tests/test_trade_path.py apps/agent-runtime/tests/test_wallet_approval_harness.py apps/agent-runtime/tests/test_wallet_approval_chain_matrix.py` -> `Ran 230 tests`, `OK`
  - `npm run test:faucet:contract` -> `passed: 10`, `failed: 0`
  - `npm run test:management:solana:contract` -> `passed: 28`, `failed: 0`
  - `npm run test:x402:solana:contract` -> `count: 17`, `ok: true`
  - `npm run db:parity` -> `ok: true`, `checkedAt: 2026-03-09T19:17:36.043Z`
  - `npm run seed:reset` -> `ok: true`
  - `npm run seed:load` -> `ok: true`, `loadedAt: 2026-03-09T19:17:36.250Z`
  - `npm run seed:verify` -> `ok: true`
  - tracked `infrastructure/seed-data/.seed-state.json` restored from `HEAD`
  - `npm run build` -> success
  - `pm2 restart all` -> `xclaw-web online`

### Slice Outcome
Complete.
