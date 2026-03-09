# Slice 248 Tasks: Solana Devnet Capability Boundary Alignment (2026-03-09)

Issue mapping: `#101`

- [x] Disable Solana devnet `trade`, `liquidity`, and `limitOrders` capability flags in chain config.
- [x] Keep Solana devnet `wallet`, `faucet`, `deposits`, and `x402` capability flags enabled.
- [x] Update the harness so Solana devnet full evidence skips disabled execution families and remains green for the supported boundary.
- [x] Add direct unit coverage proving disabled Solana devnet trade no longer creates a required failing scenario.
- [x] Add contract assertions proving Solana devnet capability flags are aligned.
- [x] Capture targeted Solana devnet supported-boundary evidence in `acceptance.md`.
- [x] Run the required sequential validation chain, then commit/push and post issue evidence.
