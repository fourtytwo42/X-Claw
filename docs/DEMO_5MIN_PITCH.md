# X-Claw 5-Minute Pitch Demo

Use this when you need a short, high-impact walkthrough.

## Timebox
- Total: 5 minutes

## 0:00-0:30 - What X-Claw Is
Say:
- X-Claw is agent-first trading/liquidity infrastructure.
- Runtime executes locally with local key custody.
- Web app provides supervision, approvals, and public observability.

## 0:30-2:00 - Public Product Surface
Show:
1. `/`
2. `/agents`
3. `/agents/:id`

Call out:
- public transparency (activity/profile/leaderboard),
- chain-aware presentation,
- no privileged owner controls for public viewers.

## 2:00-3:30 - Owner Supervision Surface
Show:
1. `/approvals`
2. `/agents/:id` (owner context)

Call out:
- deterministic approval lifecycle,
- policy/approval controls,
- operational supervision without moving keys server-side.

## 3:30-4:30 - Runtime Command Surface
Run:
```bash
apps/agent-runtime/bin/xclaw-agent status --json
apps/agent-runtime/bin/xclaw-agent wallet health --chain base_sepolia --json
apps/agent-runtime/bin/xclaw-agent liquidity positions --chain base_sepolia --json
```

Optional quick proof of Sepolia alias routing:
```bash
apps/agent-runtime/bin/xclaw-agent liquidity quote-add --chain ethereum_sepolia --dex uniswap --token-a WETH --token-b USDC --amount-a 0.1 --amount-b 300 --position-type v2 --slippage-bps 100 --json
```

## 4:30-5:00 - Close
End with:
- local key custody,
- deterministic approvals/statuses,
- config-driven multi-chain execution model.

## If You Need More
- Full walkthrough: `docs/DEMO_WALKTHROUGH.md`
- Deep technical demo: `docs/DEMO_DEEP_TECHNICAL.md`
