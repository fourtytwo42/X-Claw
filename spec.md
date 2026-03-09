# Slice 250 Spec: Canonical Chain Metadata Reconciliation (2026-03-09)

## Goal
Establish one canonical current chain metadata matrix and reconcile config, public metadata readers, fallback registries, and source-of-truth so active chain metadata cannot drift.

## Non-Goals
- no new chain enablement
- no API schema changes
- no runtime command changes
- no capability changes

## Constraints
- current enabled `evm` and `solana` chain config remains the runtime metadata source of truth
- `hardhat_local` stays hidden from public metadata where `uiVisible=false`
- historical metadata narratives remain in docs only as superseded implementation history
