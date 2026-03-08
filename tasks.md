# Slice 228 Tasks: Explicit Adapters for Wallet and Limit-Orders (2026-03-08)

Issue mapping: `#81`

- [x] Add explicit runtime adapter types for wallet and limit-orders under `runtime/adapters/`.
- [x] Refactor wallet and limit-order command modules to consume explicit adapters instead of `sys.modules[__name__]`.
- [x] Update `cli.py` to build typed adapters and dispatch wallet/limit-order commands through thin wrappers.
- [x] Keep direct adapter contract coverage for wallet/limit-order wrapper dispatch in `test_runtime_adapters.py`.
- [x] Run full sequential validations + capture evidence in `acceptance.md`.
