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
- [!] refreshed live matrix run
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
  - `infrastructure/scripts/management-solana-contract-tests.mjs`
    - Solana runtime contract assertions updated to follow shared validator locations after runtime extraction
- Direct tests:
  - `python3 -m unittest -v apps/agent-runtime/tests/test_wallet_approval_harness.py`
    - `Ran 34 tests`
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
  - exact matrix command run:
    - `python3 apps/agent-runtime/scripts/wallet_approval_chain_matrix.py --base-url http://127.0.0.1:3000 --agent-id ag_a123e3bc428c12675f93 --bootstrap-token-file /home/hendo420/.xclaw-secrets/management/ag_a123e3bc428c12675f93-bootstrap-token.json --runtime-bin apps/agent-runtime/bin/xclaw-agent --agent-api-key <installed-skill-api-key> --wallet-passphrase <installed-skill-passphrase> --harvy-address 0x582f6f293e0f49855bb752ae29d6b0565c500d87 --solana-wallet-address 9F4znU1PsW5yBK5TAfR9x8C9q3yVGNHUMuaXY35uCEXT --solana-recipient-address Gjgssop34eL6h6StEuFvMGqXNjfekzEJhAB2hANKdtHA --reports-dir /tmp/xclaw-slice243-reports --json-report /tmp/xclaw-slice243-matrix.json`
  - generated reports:
    - aggregate: `/tmp/xclaw-slice243-matrix.json`
    - hardhat local: `/tmp/xclaw-slice243-reports/xclaw-slice117-hardhat-smoke.json`
    - base sepolia: `/tmp/xclaw-slice243-reports/xclaw-slice117-base-full.json`
  - live matrix result:
    - `hardhat_local`: `ok=true`
    - `base_sepolia`: `ok=false`
      - `trade_pending_approve` failed with `builder_code_missing`
      - `global_and_allowlist` failed with `builder_code_missing`
      - unresolved pending approvals remained:
        - `xfr_30b4d0d3d06d21055d49`
        - `xfr_334558518af821b96d4e`
        - `xfr_e29b055f0e831b658b05`
      - retry failure:
        - request id `req_741d5893145f2f8d`
        - path `/management/transfer-approvals/decision`
        - response `404 payload_invalid`
  - remaining unblockers:
    - configure `XCLAW_BUILDER_CODE_BASE_SEPOLIA` or `XCLAW_BUILDER_CODE_BASE` in the active runtime/web environment
    - debug the Base Sepolia x402 transfer-approval decision path returning `404 payload_invalid` for generated approval ids before rerunning the matrix beyond `base_sepolia`
