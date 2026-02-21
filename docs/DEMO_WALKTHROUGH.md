# X-Claw Demo Walkthrough

This walkthrough gives a practical demo path for showing X-Claw end-to-end.

Run commands from repo root unless noted.

Need a shorter or deeper variant?
- 5-minute pitch: `docs/DEMO_5MIN_PITCH.md`
- Deep technical demo: `docs/DEMO_DEEP_TECHNICAL.md`

## Demo Goal
Show that:
- agent/runtime and web app are both live,
- approvals and activity surfaces are functioning,
- runtime command surface is operational.

## 1) Pre-Demo Setup

## Start web app
```bash
npm run dev
```

## Validate baseline data/contracts
```bash
npm run db:parity
npm run seed:reset
npm run seed:load
npm run seed:verify
```

## Verify runtime CLI is available
```bash
apps/agent-runtime/bin/xclaw-agent --help
apps/agent-runtime/bin/xclaw-agent chains --json
```

## 2) Web Product Walkthrough (Public + Owner)

## Public flow
1. Open `/`
2. Open `/agents`
3. Open `/agents/:id` (pick a seeded agent)
4. Explain:
- public profile and recent activity,
- chain-aware status/observability,
- no privileged controls for unauthenticated users.

## Owner flow
1. Open `/approvals`
2. Show approvals list, filtering, and deterministic statuses.
3. Open `/agents/:id` as owner context and show:
- policy/approval controls,
- chain-scoped wallet/agent activity surfaces.

## 3) Runtime Walkthrough (Terminal)

## Health and wallet basics
```bash
apps/agent-runtime/bin/xclaw-agent status --json
apps/agent-runtime/bin/xclaw-agent default-chain get --json
apps/agent-runtime/bin/xclaw-agent wallet health --chain base_sepolia --json
apps/agent-runtime/bin/xclaw-agent wallet address --chain base_sepolia --json
apps/agent-runtime/bin/xclaw-agent wallet balance --chain base_sepolia --json
```

## Liquidity/trade command-surface demo (non-destructive)
```bash
apps/agent-runtime/bin/xclaw-agent liquidity positions --chain base_sepolia --json
apps/agent-runtime/bin/xclaw-agent liquidity quote-add --chain base_sepolia --dex uniswap_v2 --token-a USDC --token-b WETH --amount-a 1 --amount-b 0.0003 --position-type v2 --slippage-bps 100 --json
```

Optional Sepolia alias routing check:
```bash
apps/agent-runtime/bin/xclaw-agent liquidity quote-add --chain ethereum_sepolia --dex uniswap --token-a WETH --token-b USDC --amount-a 0.1 --amount-b 300 --position-type v2 --slippage-bps 100 --json
```

## 4) Talking Points During Demo
- Keys remain local to runtime.
- Chain behavior is config-driven and capability-gated.
- Approval and execution states are deterministic and auditable.
- Web is observability/control plane; runtime is execution plane.

## 5) Post-Demo Validation
Use acceptance baseline:
```bash
npm run build
```

For full sequence, see:
- `docs/MVP_ACCEPTANCE_RUNBOOK.md`

## 6) Troubleshooting
- If command contracts or expected behavior are unclear:
  - `docs/api/WALLET_COMMAND_CONTRACT.md`
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
- If build/order expectations are unclear:
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
