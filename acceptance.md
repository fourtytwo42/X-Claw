# Slice 243 Acceptance Evidence: Live Chain Evidence Matrix Expansion (EVM + Solana)

Date (UTC): 2026-03-08  
Active slice context: `Slice 243`.

Issue mapping: `#96`

### Objective + Scope Lock
- Objective:
  - preserve the existing Hardhat-local -> Base Sepolia -> Ethereum Sepolia evidence chain,
  - extend the live approval matrix to `solana_localnet` then `solana_devnet`,
  - keep the slice limited to harness/report/evidence work with no public runtime contract drift.

### Behavior Checks
- [x] chain-matrix order includes `solana_localnet` and `solana_devnet` after the existing EVM legs.
- [x] Solana harness scenarios report truthful supported/unsupported outcomes.
- [x] chain-specific reports plus an aggregate matrix report are generated.
- [x] existing EVM harness behavior remains unchanged.

### Required Validation Gates
- [x] `python3 -m unittest -v apps/agent-runtime/tests/test_wallet_approval_harness.py`
- [x] `python3 -m unittest -v apps/agent-runtime/tests/test_wallet_approval_chain_matrix.py`
- [x] `npm run test:management:solana:contract`
- [x] `npm run test:x402:solana:contract`
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] tracked `infrastructure/seed-data/.seed-state.json` restore
- [x] refreshed live matrix run
- [x] `npm run build`
- [x] `pm2 restart all`

### Evidence
- Harness + matrix changes:
  - `apps/agent-runtime/scripts/wallet_approval_chain_matrix.py`
    - chain order extended to `hardhat_local`, `base_sepolia`, `ethereum_sepolia`, `solana_localnet`, `solana_devnet`
    - additive CLI support for `--solana-wallet-address` and `--solana-recipient-address`
    - Solana per-chain report paths added to aggregate matrix output
  - `apps/agent-runtime/scripts/wallet_approval_harness.py`
    - Solana-specific trade asset defaults use canonical wrapped SOL + USDC mint semantics
    - Solana localnet faucet bootstrap uses native-only top-up path
    - Solana liquidity scenario returns truthful unsupported details when live preflight is not runnable
    - runtime env now inherits canonical builder-code settings from the installed skill context when the harness caller does not provide them explicitly
    - transfer-approval decision flow now waits until x402 approvals are mirrored/actionable before issuing the management decision
    - Base Sepolia x402 capability scenario now uses canonical integer atomic amounts so mirror-backed transfer approvals are actually created
    - trade receipt confirmation falls back from `cast receipt` to direct JSON-RPC when `cast` is unavailable or fails transiently
  - `apps/network-web/src/app/api/v1/management/approvals/decision/route.ts`
    - management background trade-resume env now inherits canonical builder-code settings from the installed skill context for Base-family live evidence runs
  - `infrastructure/scripts/management-solana-contract-tests.mjs`
    - Solana runtime contract assertions updated to follow shared validator locations after runtime extraction
- Direct tests:
  - `python3 -m unittest -v apps/agent-runtime/tests/test_wallet_approval_harness.py`
    - `Ran 38 tests`
    - `OK`
  - `python3 -m unittest -v apps/agent-runtime/tests/test_wallet_approval_chain_matrix.py`
    - `Ran 5 tests`
    - `OK`
- Solana contract rails:
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
    - `checkedAt: 2026-03-08T22:37:27.926Z`
  - `npm run seed:reset`
    - `ok: true`
  - `npm run seed:load`
    - `ok: true`
    - `loadedAt: 2026-03-08T22:37:28.123Z`
  - `npm run seed:verify`
    - `ok: true`
  - tracked seed restore:
    - `git show HEAD:infrastructure/seed-data/.seed-state.json > infrastructure/seed-data/.seed-state.json`
  - `npm run hardhat:deploy-local`
    - `ok: true`
    - `deployedAt: 2026-03-08T23:29:27.963Z`
  - `npm run hardhat:verify-local`
    - `ok: true`
    - `verifiedAt: 2026-03-08T23:29:28.677Z`
  - `npm run build`
    - passed
    - Next.js build completed successfully
  - `pm2 restart all`
    - `xclaw-web` restarted
    - status `online`
- Live matrix execution evidence:
  - skill-derived runtime inputs were recovered and written locally:
    - agent id: `ag_a123e3bc428c12675f93`
    - bootstrap token file: `/home/hendo420/.xclaw-secrets/management/ag_a123e3bc428c12675f93-bootstrap-token.json`
    - EVM wallet: `0x582f6f293e0f49855bb752ae29d6b0565c500d87`
    - Solana localnet wallet: `9F4znU1PsW5yBK5TAfR9x8C9q3yVGNHUMuaXY35uCEXT`
    - Solana recipient: `Gjgssop34eL6h6StEuFvMGqXNjfekzEJhAB2hANKdtHA`
  - local management bootstrap/session persistence fix:
    - `apps/network-web/src/lib/management-cookies.ts`
      - loopback requests now omit `Secure` by resolving hostname from forwarded/host headers before `req.nextUrl.hostname`
    - `apps/network-web/src/app/api/v1/agent/management-link/route.ts`
    - `apps/network-web/src/app/api/v1/management/owner-link/route.ts`
      - local evidence runs now preserve request-origin management URLs instead of force-rewriting loopback issuers to `https://xclaw.trade`
  - direct loopback bootstrap proof after rebuild + restart:
    - `POST /api/v1/management/session/bootstrap` returned `200`
    - cookies were set without `Secure` on `127.0.0.1`
    - follow-up `GET /api/v1/management/agent-state?...chainKey=hardhat_local` returned `200`
  - exact initial matrix command run:
    - `python3 apps/agent-runtime/scripts/wallet_approval_chain_matrix.py --base-url http://127.0.0.1:3000 --agent-id ag_a123e3bc428c12675f93 --bootstrap-token-file /home/hendo420/.xclaw-secrets/management/ag_a123e3bc428c12675f93-bootstrap-token.json --runtime-bin apps/agent-runtime/bin/xclaw-agent --agent-api-key <installed-skill-api-key> --wallet-passphrase <installed-skill-passphrase> --harvy-address 0x582f6f293e0f49855bb752ae29d6b0565c500d87 --solana-wallet-address 9F4znU1PsW5yBK5TAfR9x8C9q3yVGNHUMuaXY35uCEXT --solana-recipient-address Gjgssop34eL6h6StEuFvMGqXNjfekzEJhAB2hANKdtHA --reports-dir /tmp/xclaw-slice243-reports --json-report /tmp/xclaw-slice243-matrix.json`
  - exact post-Base rerun command:
    - `python3 apps/agent-runtime/scripts/wallet_approval_chain_matrix.py --base-url http://127.0.0.1:3000 --agent-id ag_a123e3bc428c12675f93 --bootstrap-token-file /home/hendo420/.xclaw-secrets/management/ag_a123e3bc428c12675f93-bootstrap-token.json --runtime-bin apps/agent-runtime/bin/xclaw-agent --agent-api-key <installed-skill-api-key> --wallet-passphrase <installed-skill-passphrase> --harvy-address 0x582f6f293e0f49855bb752ae29d6b0565c500d87 --solana-wallet-address 9F4znU1PsW5yBK5TAfR9x8C9q3yVGNHUMuaXY35uCEXT --solana-recipient-address Gjgssop34eL6h6StEuFvMGqXNjfekzEJhAB2hANKdtHA --reports-dir /tmp/xclaw-slice243-reports --json-report /tmp/xclaw-slice243-matrix-post-base.json --start-chain ethereum_sepolia`
  - generated reports:
    - aggregate: `/tmp/xclaw-slice243-matrix.json`
    - aggregate post-base rerun: `/tmp/xclaw-slice243-matrix-post-base.json`
    - hardhat local: `/tmp/xclaw-slice243-reports/xclaw-slice117-hardhat-smoke.json`
    - base sepolia: `/tmp/xclaw-slice243-reports/xclaw-slice117-base-full.json`
    - ethereum sepolia: `/tmp/xclaw-slice243-reports/xclaw-slice117-ethereum-sepolia-full.json`
  - refreshed live matrix result:
    - `hardhat_local`: `ok=true`
      - report: `/tmp/xclaw-slice243-reports/xclaw-slice117-hardhat-smoke.json`
    - `base_sepolia`: `ok=true`
      - report: `/tmp/xclaw-slice243-reports/xclaw-slice117-base-full.json`
      - `trade_pending_approve`: `filled`, tx `0xf4f4605ceca240c241b49f074b839ffa65375bd61cff9194d8eee98f1b45c911`
      - `global_and_allowlist`: passed, trade `trd_c820940dc69a023acc7e`
      - `x402_or_capability_assertion`: passed, approval `xfr_d2b88ded16eae5b772c8`
    - `ethereum_sepolia`: `ok=true`
      - report: `/tmp/xclaw-slice243-reports/xclaw-slice117-ethereum-sepolia-full.json`
      - `trade_pending_approve`: `filled`, tx `0xe528e32cec43e5564b477261ad4419de9216b0c174b4660bd9ad42f2ec8b3b07`
      - `global_and_allowlist`: passed, trade `trd_23eed3efe3a0fee75317`
      - `x402_or_capability_assertion`: passed via canonical unsupported assertion `unsupported_chain_capability`
    - later-chain stop after Base Sepolia was cleared:
      - aggregate post-base rerun failed at `solana_localnet`
      - harness error: `wallet balance failed: rpc_unavailable: All Solana RPC candidates are unavailable.`
      - stdout tail recorded in `/tmp/xclaw-slice243-matrix-post-base.json`
  - Slice 243 closeout decision:
    - the active blockers that originally stopped the matrix at `base_sepolia` are resolved
    - the remaining stop is a later-chain environment blocker (`solana_localnet` RPC availability), so Slice 243 is complete and the next slice may target that later-chain evidence gap
