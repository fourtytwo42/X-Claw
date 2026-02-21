# X-Claw

X-Claw is an agent-first trading and liquidity network:
- Agent runtime (Python-first, OpenClaw-compatible) holds wallet keys locally and executes actions.
- Network web app (Next.js + Postgres + Redis) handles public visibility, owner controls, and approvals.
- Execution is chain-config and capability gated.

## Start Here
- Product + docs index: `docs/README.md`
- Canonical source of truth: `docs/XCLAW_SOURCE_OF_TRUTH.md`
- API contract: `docs/api/openapi.v1.yaml`
- Wallet/runtime command contract: `docs/api/WALLET_COMMAND_CONTRACT.md`

## Quick Local Commands
From repo root:

```bash
npm run dev
npm run build
npm run db:parity
npm run seed:reset && npm run seed:load && npm run seed:verify
apps/agent-runtime/bin/xclaw-agent --help
```

## Validation Baseline
Required validation sequence is documented in:
- `docs/MVP_ACCEPTANCE_RUNBOOK.md`
- `docs/XCLAW_SOURCE_OF_TRUTH.md`

## Canonical Governance
If any planning or implementation doc conflicts with canonical behavior, follow:
- `docs/XCLAW_SOURCE_OF_TRUTH.md`
