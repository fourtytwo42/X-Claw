# Slice 246 Tasks: Solana Devnet Funding Provisioning and Full Matrix Completion (2026-03-09)

Issue mapping: `#99`

- [x] Enable `solana_devnet` faucet capability through chain-scoped env.
- [x] Align harness devnet token resolution, faucet top-up, and trade-pair selection with scoped Solana devnet mints.
- [x] Ensure faucet readiness reporting prefers scoped Solana devnet signer/RPC/mints over generic fallback.
- [x] Add direct unit/contract coverage for truthful devnet funding behavior.
- [x] Provision live Solana devnet signer + mint env and capture targeted devnet evidence.
- [x] Classify funded custom-mint Solana devnet Jupiter incompatibility as a truthful later blocker and capture it in `acceptance.md`.
- [x] Re-run the full ordered matrix and record the next truthful outcome in `acceptance.md`.
- [x] Run the required sequential validation chain, then commit/push and post issue evidence.
