# Slice 244 Tasks: Solana Localnet Faucet Funding + Ethereum Sepolia Retry Stabilization (2026-03-09)

Issue mapping: `#97`

- [x] Make the chain matrix self-provision `solana_localnet` via the canonical bootstrap path.
- [x] Load the generated localnet bootstrap env into harness child env and local Solana faucet resolution.
- [x] Resolve localnet stable/wrapped token addresses from bootstrap env and request the full local funding asset set.
- [x] Prove direct `solana_localnet` faucet funding lands on-chain for the registered agent wallet.
- [x] Treat `could not replace existing tx` as a retryable EVM send-path variant under the existing bounded retry contract.
- [x] Add direct unit coverage for matrix provisioning/env loading and localnet harness preflight behavior.
- [x] Run Solana contract rails and the full sequential validation chain.
- [x] Re-run the matrix and capture `solana_localnet` plus `solana_devnet` evidence or a later concrete blocker in `acceptance.md`.
