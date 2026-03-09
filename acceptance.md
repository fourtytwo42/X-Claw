# Slice 246 Acceptance Evidence: Solana Devnet Funding Provisioning and Full Matrix Completion

Date (UTC): 2026-03-09  
Active slice context: `Slice 246`.

Issue mapping: `#99`

### Objective + Scope Lock
- Objective:
  - add explicit Solana devnet funding/provisioning for live evidence,
  - clear the current deterministic `scenario_funding_missing` blocker,
  - rerun the ordered matrix through `solana_devnet`,
  - keep the slice limited to funding/provisioning/evidence work with no public runtime contract drift.

### Behavior Checks
- [x] `solana_devnet` is faucet-capable for live evidence through chain-scoped env, not static hardcoded mint config.
- [x] harness devnet mint resolution/top-up/trade-pair selection use chain-scoped devnet mint values before fallback.
- [x] server-side faucet readiness/reporting for `solana_devnet` is deterministic.
- [x] `solana_devnet` no longer fails with the current funding-missing blocker caused by absent provisioning.
- [ ] the full ordered matrix advances beyond the current `solana_devnet` stop with either full green completion or a later truthful blocker.

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
- [x] `npm run hardhat:deploy-local`
- [x] `npm run hardhat:verify-local`
- [x] refreshed targeted `solana_devnet` live rerun
- [x] refreshed full ordered matrix rerun
- [x] `npm run build`
- [x] `pm2 restart all`

### Evidence
- Code changes:
  - `config/chains/solana_devnet.json`
    - enables faucet capability for live evidence through chain-scoped env
  - `apps/agent-runtime/scripts/wallet_approval_harness.py`
    - resolves Solana devnet stable/wrapped mints from chain-scoped env before fallback
    - requests `native|stable|wrapped` faucet top-up for `solana_devnet`
    - reports truthful Solana devnet funding details when funding is still missing
  - `apps/network-web/src/app/api/v1/agent/faucet/networks/route.ts`
    - reports `solana_devnet` faucet readiness only when signer + RPC + required asset mints are configured
- Direct tests:
  - `python3 -m unittest -v apps/agent-runtime/tests/test_wallet_approval_harness.py`
    - `Ran 57 tests`
    - `OK`
  - `python3 -m unittest -v apps/agent-runtime/tests/test_wallet_approval_chain_matrix.py`
    - `Ran 9 tests`
    - `OK`
  - `python3 -m unittest -v apps/agent-runtime/tests/test_trade_path.py apps/agent-runtime/tests/test_wallet_approval_harness.py apps/agent-runtime/tests/test_wallet_approval_chain_matrix.py`
    - `Ran 220 tests`
    - `OK`
- Solana contract rails:
  - `npm run test:faucet:contract`
    - `ok: true`
    - `passed: 10`
    - `failed: 0`
  - `npm run test:management:solana:contract`
    - `ok: true`
    - `passed: 25`
    - `failed: 0`
  - `npm run test:x402:solana:contract`
    - `ok: true`
    - `count: 17`
- Required repo validation chain:
  - `npm run db:parity`
    - `ok: true`
    - `checkedAt: 2026-03-09T05:30:45.818Z`
  - `npm run seed:reset`
    - `ok: true`
  - `npm run seed:load`
    - `ok: true`
    - `loadedAt: 2026-03-09T05:30:45.965Z`
  - `npm run seed:verify`
    - `ok: true`
  - tracked seed restore:
    - `git show HEAD:infrastructure/seed-data/.seed-state.json > infrastructure/seed-data/.seed-state.json`
  - `npm run hardhat:deploy-local`
    - `ok: true`
    - `deployedAt: 2026-03-09T05:30:46.991Z`
  - `npm run hardhat:verify-local`
    - `ok: true`
    - `verifiedAt: 2026-03-09T05:30:48.091Z`
  - `npm run build`
    - `ok: true`
    - `next build` completed successfully on 2026-03-09
  - `pm2 restart all`
    - `ok: true`
    - `xclaw-web` status: `online`
- Live Solana devnet evidence:
  - scoped devnet faucet signer funded and backed up:
    - signer: `4w1dxGBT2x12EtX3NwEVsT2V8TcgH8jwXqTqexx3WzxA`
    - backup: `/home/hendo420/.xclaw-secrets/solana-devnet/4w1dxGBT2x12EtX3NwEVsT2V8TcgH8jwXqTqexx3WzxA.json`
  - live server-side devnet funding lands on the aligned runtime wallet:
    - wallet: `8GpQWRfcsyeNh1SeZna6Ah5dRrMotnm63pF2iNaHapeQ`
    - native tx: `3gWjLrsqMfxE6FH7A9F9LoTSNAbHY9oqL1HuLLSupR2nDdZoqXYJxoua4kTGb3WoYFQ38ERcdWBR41tW4vyXP3S6`
    - stable tx: `2VeEN6jGusiRocqogSbFnK2RHtQJedeaTikBrJGdQHceGYVzxdJUKWZeMeg4twMMADXJi8a7SDvAMjaaFe2oRUk1`
    - wrapped tx: `2wrTXhyerxAzcSzLf8EeUAfEkPMmfBvfmc62iLYcZtsrWid4P6spDWngN9LRKPGtvJ4n7zh4KdDSTrDDEdwZrHbp`
  - funding blocker is cleared; current later blocker is Solana devnet custom-mint routing through Jupiter
  - targeted devnet live rerun:
    - command:
      - `XCLAW_AGENT_HOME=/tmp/xclaw-slice245-home python3 apps/agent-runtime/scripts/wallet_approval_harness.py --base-url http://127.0.0.1:3000 --chain solana_devnet --agent-id ag_a123e3bc428c12675f93 --bootstrap-token-file /home/hendo420/.xclaw-secrets/management/ag_a123e3bc428c12675f93-bootstrap-token.json --runtime-bin apps/agent-runtime/bin/xclaw-agent --agent-api-key <skill-config-api-key> --approve-driver management_api --scenario-set full --hardhat-rpc-url http://127.0.0.1:8545 --hardhat-evidence-report /tmp/xclaw-slice244-reports/xclaw-slice117-hardhat-smoke.json --expected-wallet-address 8GpQWRfcsyeNh1SeZna6Ah5dRrMotnm63pF2iNaHapeQ --json-report /tmp/xclaw-slice246-solana-devnet-full.json`
    - report:
      - `/tmp/xclaw-slice246-solana-devnet-full.json`
    - outcome:
      - `trade_pending_approve` now fails deterministically with:
        - `class=unsupported_live_evidence`
        - `error=Solana devnet custom-mint trade routing is not supported for truthful live evidence.`
  - resumed matrix rerun from the final leg:
    - command:
      - `XCLAW_AGENT_HOME=/tmp/xclaw-slice245-home python3 apps/agent-runtime/scripts/wallet_approval_chain_matrix.py --base-url http://127.0.0.1:3000 --agent-id ag_a123e3bc428c12675f93 --bootstrap-token-file /home/hendo420/.xclaw-secrets/management/ag_a123e3bc428c12675f93-bootstrap-token.json --runtime-bin apps/agent-runtime/bin/xclaw-agent --harness-bin apps/agent-runtime/scripts/wallet_approval_harness.py --agent-api-key <skill-config-api-key> --hardhat-rpc-url http://127.0.0.1:8545 --harvy-address 0x582f6f293e0f49855bb752ae29d6b0565c500d87 --solana-wallet-address 8GpQWRfcsyeNh1SeZna6Ah5dRrMotnm63pF2iNaHapeQ --solana-recipient-address 8GpQWRfcsyeNh1SeZna6Ah5dRrMotnm63pF2iNaHapeQ --reports-dir /tmp/xclaw-slice246-reports --json-report /tmp/xclaw-slice246-matrix-resume.json --start-chain solana_devnet`
    - aggregate report:
      - `/tmp/xclaw-slice246-matrix-resume.json`
    - outcome:
      - `failedAt=solana_devnet`
      - later blocker is deterministic `unsupported_live_evidence` from the targeted devnet leg after funding and wallet preflight succeed
  - earlier ordered matrix legs remain green from the latest completed live evidence:
    - `/tmp/xclaw-slice244-reports/xclaw-slice117-hardhat-smoke.json`
    - `/tmp/xclaw-slice244-reports/xclaw-slice117-base-full.json`
    - `/tmp/xclaw-slice244-reports/xclaw-slice117-ethereum-sepolia-full.json`
    - `/tmp/xclaw-slice244-reports/xclaw-slice243-solana-localnet-full.json`

### Slice Outcome
- Slice 246 is complete.
- The original Solana devnet funding blocker is resolved.
- The ordered matrix now advances beyond the previous funding stop and records the next truthful later blocker at `solana_devnet`.
- Current later blocker:
  - `class=unsupported_live_evidence`
  - `reason=solana_devnet_custom_mint_trade_unsupported`
  - concrete meaning: the funded scoped Solana devnet custom mints are not Jupiter-quotable for truthful live trade execution.
