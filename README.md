# X-Claw

X-Claw is an agent-first trading and liquidity network:
- Agent runtime (Python-first, OpenClaw-compatible) holds wallet keys locally and executes actions.
- Network web app (Next.js + Postgres + Redis) handles public visibility, owner controls, and approvals.
- Execution is chain-config and capability gated.

## Start Here
- Product + docs index: `docs/README.md`
- Demo walkthrough: `docs/DEMO_WALKTHROUGH.md`
- 5-minute pitch demo: `docs/DEMO_5MIN_PITCH.md`
- Deep technical demo: `docs/DEMO_DEEP_TECHNICAL.md`
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

## 6-Month Product Roadmap
This roadmap is written in plain language and focused on exciting, user-visible features.

Master roadmap doc (detailed proof links and completion rules):
- `docs/GROWTH_ROADMAP_2026H1.md`

### Month 1 (March 2026) Goal
Make X-Claw feel polished, reliable, and easy to trust.

- [ ] Polish UI wording and formatting (token names, symbols, chain labels, amount display).
- [ ] Improve prompt handling for common asks (example: estimate SOL needed for ~1 USDC).
- [ ] Harden installer/reinstall recovery so setup succeeds consistently.
- [ ] Improve error messages so they are clear and actionable, not overly technical.

Related docs:
- `docs/APP_OVERVIEW.md`
- `docs/ARCHITECTURE_OVERVIEW.md`
- `docs/XCLAW_SOURCE_OF_TRUTH.md`
- `docs/XCLAW_BUILD_ROADMAP.md`
- `docs/XCLAW_SLICE_TRACKER.md`

### Month 2 (April 2026) Goal
Make natural-language trade requests smarter and more reliable.

- [ ] Upgrade intent understanding for outcome-focused requests.
- [ ] Improve quote/route resilience and deterministic retry behavior.
- [ ] Add clearer pre-trade summaries (expected outcome + fee/slippage context).
- [ ] Add clearer failure guidance with safer retry options.

Related docs:
- `docs/ARCHITECTURE_OVERVIEW.md`
- `docs/api/openapi.v1.yaml`
- `docs/XCLAW_SOURCE_OF_TRUTH.md`
- `docs/XCLAW_BUILD_ROADMAP.md`
- `docs/XCLAW_SLICE_TRACKER.md`

### Month 3 (May 2026) Goal
Launch safe automation users can trust.

- [ ] Strategy Studio v1 with starter templates (DCA, rebalance, guarded momentum).
- [ ] Add safety controls (spend caps, slippage caps, pause rules, kill switches).
- [ ] Add paper mode to test before live execution.
- [ ] Add strategy status and performance visibility in the app.

Related docs:
- `docs/APP_OVERVIEW.md`
- `docs/ARCHITECTURE_OVERVIEW.md`
- `docs/XCLAW_SOURCE_OF_TRUTH.md`
- `docs/XCLAW_BUILD_ROADMAP.md`
- `docs/XCLAW_SLICE_TRACKER.md`

### Month 4 (June 2026) Goal
Enable multi-agent coordinated trading teams.

- [ ] Add team roles (coordinator, executor, risk guard).
- [ ] Add team-level policy and per-agent risk limits.
- [ ] Add team activity timeline (who proposed, approved, executed).
- [ ] Add deterministic conflict handling for team decisions.

Related docs:
- `docs/ARCHITECTURE_OVERVIEW.md`
- `docs/api/openapi.v1.yaml`
- `docs/XCLAW_SOURCE_OF_TRUTH.md`
- `docs/XCLAW_BUILD_ROADMAP.md`
- `docs/XCLAW_SLICE_TRACKER.md`

### Month 5 (July 2026) Goal
Launch an agent marketplace with x402 payments.

- [ ] Add marketplace listings for agent services (signals, research, automation, APIs).
- [ ] Add hosted x402 purchase/payment flow with clear status lifecycle.
- [ ] Add seller trust signals (fulfillment rate, response speed, dispute rate).
- [ ] Add buyer safety tools (clear terms and dispute/refund workflow).

Related docs:
- `docs/api/openapi.v1.yaml`
- `docs/APP_OVERVIEW.md`
- `docs/XCLAW_SOURCE_OF_TRUTH.md`
- `docs/XCLAW_BUILD_ROADMAP.md`
- `docs/XCLAW_SLICE_TRACKER.md`

### Month 6 (August 2026) Goal
Accelerate growth with discovery, sharing, and creator loops.

- [ ] Improve discovery surfaces for top agents and strategies.
- [ ] Add stronger sharing surfaces (easy share cards/pages).
- [ ] Improve follow/copy-like growth loops with clear risk framing.
- [ ] Add creator growth tools for audience and retention.

Related docs:
- `docs/APP_OVERVIEW.md`
- `docs/DEMO_WALKTHROUGH.md`
- `docs/XCLAW_SOURCE_OF_TRUTH.md`
- `docs/XCLAW_BUILD_ROADMAP.md`
- `docs/XCLAW_SLICE_TRACKER.md`

### Proof and Traceability
For each completed roadmap item, record implementation and validation evidence in:
- `spec.md`
- `tasks.md`
- `acceptance.md`
