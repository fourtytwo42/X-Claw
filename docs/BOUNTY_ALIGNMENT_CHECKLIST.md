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
- [x] Hedera liquidity add/remove path works, with same approval posture as trade/convert.
- [x] Hedera SDK + HTS support exists for native token-service operations.
- [ ] Position tracking works on Hedera (PnL + fees where applicable).

### Demo Evidence Gate

- [ ] Recorded scenario: agent discovers opportunity, executes action, reports outcome.
- [ ] On-chain proof included (tx hash/explorer links for Hedera actions).
- [ ] UI evidence shows agent flow states and transitions.

Notes:
- `E6`: Hedera EVM quote path now executes against configured Saucer router and reaches live RPC revert (`CONTRACT_REVERT_EXECUTED`) instead of config-contract failure.
- `E7`: Hedera EVM add-intent path succeeds (`status=approved`) after policy snapshot is present; first attempt demonstrates deterministic `policy_denied` guardrail.
- `E8`: HTS-native runtime path fails closed with deterministic `missing_dependency` when SDK/plugin prerequisites are unavailable.
- `E9`: HTS fail-closed unit test proof remains passing (`test_quote_add_fails_closed_when_hedera_sdk_missing`).
- `E10`: Hedera pair-discovery matrix now returns ranked live pairs for both `saucerswap` and `pangolin` via factory scan (`candidateCount:13` in sampled scan).
- `E11`: Hosted installer rerun yields Hedera wallet readiness (`hasWallet:true`) in this environment.
- `E22`: Hedera EVM runtime liquidity add submitted on-chain from `xclaw-agent liquidity add` (tx hash `0x2c019ea7b35176d6d6c1b141fabdb849625b1b05ae7a1d3112a6673e173c8891`, receipt `status=0x1`).
- `E23`: Hedera EVM runtime liquidity remove submitted on-chain from `xclaw-agent liquidity remove` (tx hash `0x69df2d9b23653b13b8a86cc2e03a6da72b2b2118ed70ed4a3f26f4ef1fd32865`, receipt `status=0x1`).
- `E24`: Deterministic EVM preflight diagnostics now include token probe outcomes + router revert payload context (`liquidity_preflight_router_revert`, `liquidity_preflight_token_transfer_blocked_token_a|b`).
- `E25`: HTS readiness matrix now reports only bridge-command gap when runtime venv + JDK are configured (`missing: XCLAW_HEDERA_HTS_BRIDGE_CMD`).
- `E26`: HTS add remains deterministic fail-closed `missing_dependency` until bridge command is configured.
- `E27`: HTS remove remains deterministic fail-closed `missing_dependency` until bridge command is configured.
- `E28`: HTS readiness passes with in-repo bridge default (`ready=true`, `bridgeCommandSource=default`).
- `E29`: HTS add executed with terminal `filled` and tx hash `4fce8accb8103ceadbb20865a9020222189d3606c309b6896c77bc8b97cb928fdbcc012933a5c373fa7f2922bccfd62f`.
- `E30`: HTS remove executed with terminal `filled` and tx hash `41428b5b6519e0c710d1aa80b796819a690ed6211ab7cce6052937cc9c89c6508b2c43813ce2ec7d0deb9cdddb9fea88`.

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
- [x] Hedera/Hedera testnet: required DEX set enabled
- [x] Approvals aligned with trade/convert policy model.
- [x] Position monitor runs on low-RPC cadence target (once/minute) with freshness metadata.
- [x] PnL/fees tracking aligned with existing metrics patterns.
- [x] Webapp has separate `Liquidity Positions` section with chain-filtered rows.

Notes:
- `E1/E2/E3/E4/E5` cover hardhat-local + Base Sepolia contract/preflight/approval evidence.
- `E22/E23` capture Hedera EVM add/remove tx-hash runtime proof.
- `E29/E30` capture Hedera HTS add/remove tx-hash runtime proof.
- `E34..E37` capture Hedera faucet deterministic failure contract and installer warmup diagnostics for non-demo install flows.
- `E38..E40` capture official Hedera helper wrapping (`wallet wrap-native`) and post-wrap faucet deterministic behavior.

---

## Evidence Index (Fill As Work Completes)

- `E1`: Hardhat-local liquidity API contract pass (`XCLAW_DEFAULT_CHAIN=hardhat_local npm run test:liquidity:contract`, 18/18 checks).
- `E2`: Base Sepolia `quote-add` preflight simulation pass (`uniswap_v2`).
- `E3`: Base Sepolia approval-required liquidity add (`approval_pending`).
- `E4`: Base Sepolia auto-approved liquidity add (`status=approved`).
- `E5`: Unsupported adapter deterministic rejection (`unsupported_liquidity_adapter`).
- `E6`: Hedera EVM quote attempt hit live router revert (`CONTRACT_REVERT_EXECUTED`) after router/token config hardening.
- `E7`: Hedera EVM add-intent path reached runtime approval flow (`policy_denied` then `approved` with policy snapshot).
- `E8`: Hedera HTS runtime fail-closed proof (`missing_dependency` on quote-add/add).
- `E9`: Hedera HTS missing-SDK fail-closed unit proof (`missing_dependency` test).
- `E10`: Hedera pair-discovery probes (`discover-pairs`) for `saucerswap` + `pangolin` returned viable live pairs (reserve-filtered).
- `E11`: Hosted installer rerun + wallet health proof (`hasWallet:true` for `hedera_testnet`).
- `E12`: HTS package + JDK deep probe: with user-local JDK + runtime venv, `import hedera` passes.
- `E13`: Hedera EVM quote-add succeeds on discovered pair (`TEST/FOOL` pair addresses from scan output).
- `E14`: Hedera EVM liquidity add intent succeeds on discovered pair (`status=approved`).
- `E15`: Hedera HTS quote-add/add succeed with JDK-enabled runtime (`XCLAW_AGENT_PYTHON_BIN` + `JAVA_HOME`).
- `E16`: Runtime `liquidity add/remove` now auto-executes approved intents and posts lifecycle transitions (`approved -> executing -> verifying -> filled|failed|verification_timeout`).
- `E17`: Hedera EVM auto-execution attempt reaches deterministic execution failure (`CONTRACT_REVERT_EXECUTED`) with wallet passphrase provided; blocker now reflects live token/liquidity conditions, not missing execution path.
- `E18`: Hedera HTS auto-execution path fail-closed proof (default interpreter missing Hedera SDK/JDK prerequisites).
- `E19`: Management liquidity decision route test bootstrap is self-healing (agent-issued owner link fallback) and the suite passes (`14 passed / 0 failed`).
- `E20`: Local API/DB health recovered in-session (`/api/health` -> `overallStatus=healthy`; Postgres `127.0.0.1:55432` accepting connections).
- `E21`: Remaining live blocker is wallet signing in this shell (`wallet-sign-challenge` returns deterministic `sign_failed` until correct `XCLAW_WALLET_PASSPHRASE` is provided); HTS default interpreter still fail-closes with `missing_dependency`.
- `E22`: Hedera EVM runtime `liquidity add` tx hash `0x2c019ea7b35176d6d6c1b141fabdb849625b1b05ae7a1d3112a6673e173c8891` (receipt `status=0x1`).
- `E23`: Hedera EVM runtime `liquidity remove` tx hash `0x69df2d9b23653b13b8a86cc2e03a6da72b2b2118ed70ed4a3f26f4ef1fd32865` (receipt `status=0x1`).
- `E24`: Hedera deterministic preflight probe outputs (`liquidity_preflight_token_transfer_blocked_token_a|b`, enriched router-revert details).
- `E25`: HTS readiness matrix in wallet health output (`java/javac/import/plugin/bridge` checks).
- `E26`: HTS add deterministic fail-closed sample (`missing_dependency`) before bridge default wiring.
- `E27`: HTS remove deterministic fail-closed sample (`missing_dependency`) before bridge default wiring.
- `E28`: HTS readiness pass with default bridge command resolution.
- `E29`: HTS add tx hash `4fce8accb8103ceadbb20865a9020222189d3606c309b6896c77bc8b97cb928fdbcc012933a5c373fa7f2922bccfd62f`.
- `E30`: HTS remove tx hash `41428b5b6519e0c710d1aa80b796819a690ed6211ab7cce6052937cc9c89c6508b2c43813ce2ec7d0deb9cdddb9fea88`.
- `E31`: Installer auto-binds Hedera wallet with portable-key invariant enforcement.
- `E32`: Installer register upsert writes both default-chain + Hedera wallet rows.
- `E33`: Installer optional Hedera warmup emits deterministic non-fatal warning contract.
- `E34`: Hedera faucet contract test proves non-demo deterministic Hedera error code (`faucet_rpc_unavailable`) with requestId.
- `E35`: Installer warmup output includes `faucetCode`, `faucetMessage`, `actionHint`, and rerun command.
- `E36`: Reinstall path preserves existing wallet and register upsert behavior.
- `E37`: Warmup failure remains deterministic and non-fatal (`hedera_faucet_warmup_failed`).
- `E38`: Runtime official helper wrap tx hash via `wallet wrap-native --chain hedera_testnet --amount 1 --json` (`0x1336c10e4f0a891e998d8e971f15a9702ee116bc6271cbf3b0f907e46ceebc10`).
- `E39`: Post-wrap wallet balance confirms WHBAR increase to `1.00554979`.
- `E40`: Hedera faucet request returns deterministic `faucet_stable_insufficient` with `requestId` and inventory details (no opaque `internal_error`).
