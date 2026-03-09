# Slice 244 Tasks: Solana Localnet Self-Provision + Devnet Matrix Completion (2026-03-09)

Issue mapping: `#97`

- [x] Make the chain matrix self-provision `solana_localnet` via the canonical bootstrap path.
- [x] Load the generated localnet bootstrap env into harness child env and local Solana faucet resolution.
- [x] Add direct unit coverage for matrix provisioning/env loading and localnet harness preflight behavior.
- [x] Run Solana contract rails and the full sequential validation chain.
- [!] Re-run the matrix and capture `solana_localnet` plus `solana_devnet` evidence or a later concrete blocker in `acceptance.md`.
