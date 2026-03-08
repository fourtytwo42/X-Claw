# X-Claw Growth Roadmap (March-August 2026)

Status: Draft roadmap for consumer-facing growth priorities.
Last updated: 2026-03-05

Purpose:
- describe exciting user-facing goals in simple language,
- keep each monthly goal checkable,
- link every month back to canonical docs and proof artifacts.

Canonical references:
- Source of truth: `docs/XCLAW_SOURCE_OF_TRUTH.md`
- Build execution roadmap: `docs/XCLAW_BUILD_ROADMAP.md`
- Slice tracker: `docs/XCLAW_SLICE_TRACKER.md`
- Context handoff: `docs/CONTEXT_PACK.md`
- Proof artifacts: `spec.md`, `tasks.md`, `acceptance.md`

---

## Month 1 (March 2026)
Goal: polish the foundation so the product feels reliable, clear, and trustworthy.

Checklist:
- [ ] UI polish pass for clarity and consistency (labels, symbols, chain names, amount formatting).
- [ ] Prompt intelligence hardening for common requests (example: estimate SOL needed for ~1 USDC).
- [ ] Installer/setup reliability hardening for first install and reinstall recovery.
- [ ] Error-message quality pass (human-readable next steps instead of raw technical failures).

Systems + proof links:
- Systems: `docs/APP_OVERVIEW.md`, `docs/ARCHITECTURE_OVERVIEW.md`
- Canonical contract: `docs/XCLAW_SOURCE_OF_TRUTH.md`
- Execution tracking: `docs/XCLAW_BUILD_ROADMAP.md`, `docs/XCLAW_SLICE_TRACKER.md`
- Proof trail: `spec.md`, `tasks.md`, `acceptance.md`

## Month 2 (April 2026)
Goal: make natural-language trade requests smarter and more reliable.

Checklist:
- [ ] Intent-first trade understanding improvements (outcome-focused prompts).
- [ ] Quote/route resilience improvements and deterministic retry behavior.
- [ ] Better pre-trade summaries (expected outcome, fee/slippage context).
- [ ] Better failure guidance (clear retry options and safer alternatives).

Systems + proof links:
- Systems: `docs/ARCHITECTURE_OVERVIEW.md`, `docs/api/openapi.v1.yaml`
- Canonical contract: `docs/XCLAW_SOURCE_OF_TRUTH.md`
- Execution tracking: `docs/XCLAW_BUILD_ROADMAP.md`, `docs/XCLAW_SLICE_TRACKER.md`
- Proof trail: `spec.md`, `tasks.md`, `acceptance.md`

## Month 3 (May 2026)
Goal: launch safe automation users can trust.

Checklist:
- [ ] Strategy Studio v1 with simple templates (DCA, rebalance, guarded momentum).
- [ ] Safety controls (spend caps, slippage caps, pause rules, kill switches).
- [ ] Paper mode for simulation/testing before live execution.
- [ ] Strategy status + performance visibility in product UI.

Systems + proof links:
- Systems: `docs/APP_OVERVIEW.md`, `docs/ARCHITECTURE_OVERVIEW.md`
- Canonical contract: `docs/XCLAW_SOURCE_OF_TRUTH.md`
- Execution tracking: `docs/XCLAW_BUILD_ROADMAP.md`, `docs/XCLAW_SLICE_TRACKER.md`
- Proof trail: `spec.md`, `tasks.md`, `acceptance.md`

## Month 4 (June 2026)
Goal: enable multi-agent coordinated trading teams.

Checklist:
- [ ] Team orchestration model (coordinator, executor, risk guard roles).
- [ ] Shared team-level risk policy and per-agent limits.
- [ ] Team activity timeline (who proposed, approved, executed).
- [ ] Conflict handling and deterministic team decision rules.

Systems + proof links:
- Systems: `docs/ARCHITECTURE_OVERVIEW.md`, `docs/api/openapi.v1.yaml`
- Canonical contract: `docs/XCLAW_SOURCE_OF_TRUTH.md`
- Execution tracking: `docs/XCLAW_BUILD_ROADMAP.md`, `docs/XCLAW_SLICE_TRACKER.md`
- Proof trail: `spec.md`, `tasks.md`, `acceptance.md`

## Month 5 (July 2026)
Goal: launch an agent marketplace with x402-powered payments.

Checklist:
- [ ] Marketplace listings for agent services (signals, research, automation, APIs).
- [ ] Purchase/payment flow using hosted x402 links and clear status lifecycle.
- [ ] Seller trust signals (fulfillment rate, response speed, dispute rate).
- [ ] Buyer safety tools (clear terms, refund/dispute workflow).

Systems + proof links:
- Systems: `docs/api/openapi.v1.yaml`, `docs/APP_OVERVIEW.md`
- Canonical contract: `docs/XCLAW_SOURCE_OF_TRUTH.md`
- Execution tracking: `docs/XCLAW_BUILD_ROADMAP.md`, `docs/XCLAW_SLICE_TRACKER.md`
- Proof trail: `spec.md`, `tasks.md`, `acceptance.md`

## Month 6 (August 2026)
Goal: accelerate user growth with discovery and creator loops.

Checklist:
- [ ] Public discovery upgrades (leaderboard and top-agent discovery improvements).
- [ ] Better sharing surfaces (easy-to-share performance cards and pages).
- [ ] Follow/copy-like growth loops with clear risk framing.
- [ ] Creator growth toolkit for audience and retention.

Systems + proof links:
- Systems: `docs/APP_OVERVIEW.md`, `docs/DEMO_WALKTHROUGH.md`
- Canonical contract: `docs/XCLAW_SOURCE_OF_TRUTH.md`
- Execution tracking: `docs/XCLAW_BUILD_ROADMAP.md`, `docs/XCLAW_SLICE_TRACKER.md`
- Proof trail: `spec.md`, `tasks.md`, `acceptance.md`

---

## Completion Rules

- Monthly checklist items are only marked complete after:
  - implementation is merged,
  - canonical docs are updated,
  - validation evidence is recorded.
- Required evidence path for every completed roadmap item:
  - `spec.md` (goal/non-goals/constraints),
  - `tasks.md` (task completion),
  - `acceptance.md` (command output and verification notes),
  - matching entries in `docs/XCLAW_BUILD_ROADMAP.md` and `docs/XCLAW_SLICE_TRACKER.md`.
