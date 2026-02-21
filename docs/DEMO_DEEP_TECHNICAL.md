# X-Claw Deep Technical Demo

Use this when the audience wants architecture, contracts, and operational rigor.

## Audience
- engineers
- technical judges/reviewers
- security-minded operators

## 1) Architecture and Trust Boundaries
Show and explain:
- `docs/ARCHITECTURE_OVERVIEW.md`
- `docs/XCLAW_SOURCE_OF_TRUTH.md`

Focus points:
- runtime/web separation,
- outbound-only runtime->network communication,
- local wallet custody and fail-closed behavior.

## 2) Contract Surfaces
Show:
- `docs/api/openapi.v1.yaml`
- `docs/api/WALLET_COMMAND_CONTRACT.md`

Explain:
- deterministic error/status contracts,
- chain capability gating from `config/chains/*.json`,
- approval/state lifecycle consistency across runtime and web.

## 3) Live Runtime Surface Walkthrough
Run:
```bash
apps/agent-runtime/bin/xclaw-agent --help
apps/agent-runtime/bin/xclaw-agent chains --json
apps/agent-runtime/bin/xclaw-agent status --json
apps/agent-runtime/bin/xclaw-agent default-chain get --json
apps/agent-runtime/bin/xclaw-agent wallet health --chain base_sepolia --json
apps/agent-runtime/bin/xclaw-agent wallet balance --chain base_sepolia --json
```

Liquidity-focused checks:
```bash
apps/agent-runtime/bin/xclaw-agent liquidity positions --chain base_sepolia --json
apps/agent-runtime/bin/xclaw-agent liquidity quote-add --chain base_sepolia --dex uniswap_v2 --token-a USDC --token-b WETH --amount-a 1 --amount-b 0.0003 --position-type v2 --slippage-bps 100 --json
apps/agent-runtime/bin/xclaw-agent liquidity quote-add --chain ethereum_sepolia --dex uniswap --token-a WETH --token-b USDC --amount-a 0.1 --amount-b 300 --position-type v2 --slippage-bps 100 --json
```

## 4) Web/API Verification Surface
Show:
1. `/agents`
2. `/agents/:id`
3. `/approvals`

Explain:
- public vs owner-gated behavior,
- queue/history semantics for approvals,
- cross-surface consistency with runtime status contracts.

## 5) Ops and Validation Discipline
Run sequence:
```bash
npm run db:parity
npm run seed:reset
npm run seed:load
npm run seed:verify
npm run build
```

Discuss:
- parity and seed determinism,
- release readiness gates,
- VM-native ops and backup/restore runbook.

Reference:
- `docs/MVP_ACCEPTANCE_RUNBOOK.md`
- `docs/OPS_BACKUP_RESTORE_RUNBOOK.md`

## 6) Suggested Technical Q&A Topics
- Why runtime custody over server custody?
- How chain capability gating prevents unsafe execution?
- How deterministic failure codes improve operator control?
- How source-of-truth and slice tracking enforce delivery integrity?

## Related Demo Docs
- 5-minute pitch: `docs/DEMO_5MIN_PITCH.md`
- General walkthrough: `docs/DEMO_WALKTHROUGH.md`
