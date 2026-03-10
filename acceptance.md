# Slice 251 Acceptance Evidence: Management Session Bootstrap Reliability and Authorized `/agents/:id` Proof

Active slice context: `Slice 251`  
Issue mapping: `#104`

## Goal
Verify the active management authorization contract end to end: management-link issuance, bootstrap token acceptance, `xclaw_mgmt` + `xclaw_csrf` issuance, authorized management reads, sensitive write success with CSRF, sensitive write rejection without CSRF, and authorized `/agents/:id` owner-only surface proof.

## Validation
- [x] `npm run test:management:session:contract`
- [x] `npm run verify:management:bootstrap`
- [x] `npm run verify:ui:agent-approvals`
- [x] `npm run db:parity`
- [x] `npm run seed:reset`
- [x] `npm run seed:load`
- [x] `npm run seed:verify`
- [x] restore tracked `infrastructure/seed-data/.seed-state.json`
- [x] `npm run build`
- [x] `pm2 restart all`

## Evidence
- `npm run test:management:session:contract` -> `ok: true`, `passed: 12`, `failed: 0`
- `npm run verify:management:bootstrap` -> `ok: true`
  - valid management link issued for `ag_a123e3bc428c12675f93`
  - invalid bootstrap token -> `401 auth_invalid`
  - expired bootstrap token -> `401 auth_invalid`, message `Management bootstrap token has expired.`
  - bootstrap cookies issued -> `xclaw_mgmt`, `xclaw_csrf`
  - authorized reads succeeded -> `/management/session/agents`, `/management/agent-state`, `/management/default-chain`
  - sensitive write with CSRF succeeded -> `/management/default-chain/update-batch`, `successCount: 1`
  - same write without CSRF -> `401 csrf_invalid`
  - bootstrap token file written -> `/tmp/xclaw-slice251-bootstrap-token.json`
- `npm run verify:ui:agent-approvals` -> `ok: true`
  - owner-only `/agents/:id` surface proved under bootstrapped management session
  - mirrored approval row rendered at `[data-testid="approval-row-transfer-xfr_ui_1773113757637_w6lyxhwd"]`
  - owner controls visible -> `ownerControlsVisible: true`
  - UI verifier artifacts -> `/tmp/xclaw-ui-verify-xfr_ui_1773113757637_w6lyxhwd`
- `npm run db:parity` -> `ok: true`, `checkedAt: 2026-03-10T03:36:09.574Z`
- `npm run seed:reset` -> `ok: true`
- `npm run seed:load` -> `ok: true`, `loadedAt: 2026-03-10T03:36:17.675Z`
- `npm run seed:verify` -> `ok: true`
- tracked `infrastructure/seed-data/.seed-state.json` restored from `HEAD`
- `npm run build` -> success
- `pm2 restart all` -> `xclaw-web online`

## Outcome
- Management authorization is now verified end to end using a deterministic bootstrap/session proof runner plus the existing approval-row UI verifier for owner-only `/agents/:id` rendering.
- Current management contract is explicitly locked to owner-link generation, bootstrap token acceptance, `xclaw_mgmt` + `xclaw_csrf`, authorized reads, sensitive write success with CSRF, and sensitive write rejection without CSRF.
- Stale roadmap language that still implied a step-up layer or bootstrap-token blocker has been removed.
