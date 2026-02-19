# X-Claw Bounty Alignment Checklist

Last updated: 2026-02-19
Owner: X-Claw team
Purpose: Single checklist to track whether the current build is submission-ready for target ETHDenver bounties.

---

## How To Use

1. Mark each item `[x]` only when there is reproducible evidence (command output, screenshot, tx hash, demo clip).
2. If an item is blocked, mark `[!]` and add blocker + next action in `Notes`.
3. Do not claim bounty readiness unless all `Submission Gate` items are complete for that bounty.

---

## Global Submission Gate (Applies To All Bounties)

- [ ] Public repo is up to date and buildable from README.
- [ ] Live demo URL works (or Docker/CLI path is fully reproducible).
- [ ] Demo video under 3 minutes exists and matches shipped behavior.
- [ ] README includes setup, architecture, and end-to-end walkthrough.
- [ ] Security controls are visible in flow: approval gating, limits, failure handling.
- [ ] Human remains in control for transaction approval/deny.
- [ ] Agent autonomy is visible (no manual wallet-clicking for core flow orchestration).

Notes:
- 

---

## Bounty A: Hedera - Killer App for the Agentic Society (OpenClaw)

### Product Fit Gate

- [ ] App is agent-first (OpenClaw agents are primary users; UI is observer/manager, not primary operator).
- [ ] Multi-agent value loop is demonstrated (app becomes more valuable as more agents join).
- [ ] Autonomous or semi-autonomous agent behavior is demonstrated end-to-end.
- [ ] Hedera infrastructure is used in real flow (at least one: Hedera EVM, HTS, HCS).
- [ ] Trust/reputation/attestation signal is shown (optional ERC-8004 integration tracked here if included).

### Technical Integration Gate

- [ ] Hedera mainnet + Hedera testnet chain configs are implemented and validated.
- [ ] Hedera trading + converting path works in runtime + skill wrapper.
- [!] Hedera liquidity add/remove path works, with same approval posture as trade/convert.
- [x] Hedera SDK + HTS support exists for native token-service operations.
- [ ] Position tracking works on Hedera (PnL + fees where applicable).

### Demo Evidence Gate

- [ ] Recorded scenario: agent discovers opportunity, executes action, reports outcome.
- [ ] On-chain proof included (tx hash/explorer links for Hedera actions).
- [ ] UI evidence shows agent flow states and transitions.

Notes:
- `E6`: Hedera liquidity probe currently blocked in this environment (`invalid coreContracts.router`), so live add/remove proof is pending runtime chain-pack completion.
- `E7`: HTS fail-closed behavior is covered by unit test (`missing_dependency`) via `test_quote_add_fails_closed_when_hedera_sdk_missing`.

---

## Bounty B: 0G - Best DeFAI Application

### Product Fit Gate

- [ ] Working DeFi flow exists (swap/convert/LP/vault/etc.) on 0G.
- [ ] AI adds material value beyond chat (structured planning, guardrails, automation).
- [ ] Safety is explicit (confirmations, limits, explainability, simulation/previews).
- [ ] End-to-end scenario is demonstrated in demo.

### 0G Value Gate (High Weight)

- [ ] 0G usage is meaningful, not only “chain added”.
- [ ] Clear statement of why workflow is better because of 0G.
- [ ] Composability is demonstrated (extensible adapter/plugin path).

### Technical Gate

- [!] 0G testnet + mainnet chain support implemented for trade/convert/liquidity flows.
- [ ] Approval + policy controls match existing canonical behavior.
- [ ] Failure paths tested (insufficient funds, approval rejected, slippage/timeout).

Notes:
- Adapter-ready configs exist; live 0G execution evidence not captured in this pass.

---

## Bounty C: Kite AI - Agent-Native Payments & Identity (x402)

### Product Fit Gate

- [ ] Agent identity is verifiable (wallet-based or credential-based).
- [ ] x402 payments are action-bound (each paid action maps to a payment record).
- [ ] Autonomous execution is demonstrated with minimal human intervention.
- [ ] Open-source core components are clearly identified/licensed.

### Technical Gate

- [ ] Kite testnet path is stable for x402 payment and settlement.
- [ ] Kite mainnet readiness is defined (enabled now or clearly staged with blockers).
- [ ] Insufficient funds and misuse are handled gracefully with deterministic messaging.
- [ ] Payment flow, on-chain confirmation, and identity are visible in UI/logs.

### Reliability Gate

- [ ] No manual wallet-click step is required in the core paid-action path.
- [ ] Failure/retry behavior is deterministic and documented.
- [ ] Approval controls/limits/scopes are demonstrated.

Notes:
- 

---

## Cross-Chain Expansion Gate (Sponsor Coverage Plan)

Target sponsor chain set:
- Hedera
- 0G Labs
- ADI Foundation
- Canton Network
- Base
- Kite AI

For each chain:
- [ ] Testnet configured
- [ ] Mainnet configured
- [ ] Trading supported
- [ ] Converting supported
- [ ] Liquidity add/remove supported
- [ ] Position tracking supported
- [ ] Webapp chain dropdown + chain-scoped position view supported
- [ ] Capability flags set correctly (including x402 where supported)

Notes:
- 

---

## Liquidity Feature Readiness Gate (New Scope)

- [x] Supports both LP models:
- [x] v2-style fungible LP token positions
- [x] v3-style concentrated liquidity NFT positions
- [x] Multi-DEX adapter contract exists (plug-and-play architecture).
- [x] DEX integrations for v1 include:
- [x] Base/Base testnet: Uniswap + Aerodrome
- [!] Hedera/Hedera testnet: required DEX set enabled
- [x] Approvals aligned with trade/convert policy model.
- [x] Position monitor runs on low-RPC cadence target (once/minute) with freshness metadata.
- [x] PnL/fees tracking aligned with existing metrics patterns.
- [x] Webapp has separate `Liquidity Positions` section with chain-filtered rows.

Notes:
- `E1/E2/E3/E4/E5` cover hardhat-local + Base Sepolia contract/preflight/approval evidence.
- Hedera live proof remains blocked in this environment (`E6`).

---

## Evidence Index (Fill As Work Completes)

- `E1`: Hardhat-local liquidity API contract pass (`XCLAW_DEFAULT_CHAIN=hardhat_local npm run test:liquidity:contract`, 18/18 checks).
- `E2`: Base Sepolia `quote-add` preflight simulation pass (`uniswap_v2`).
- `E3`: Base Sepolia approval-required liquidity add (`approval_pending`).
- `E4`: Base Sepolia auto-approved liquidity add (`status=approved`).
- `E5`: Unsupported adapter deterministic rejection (`unsupported_liquidity_adapter`).
- `E6`: Hedera live quote probe blocker (`invalid coreContracts.router` in current environment).
- `E7`: Hedera HTS missing-SDK fail-closed unit proof (`missing_dependency` test).
