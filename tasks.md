# Slice 233 Tasks: Runtime State + Auth/Policy Services (2026-03-08)

Issue mapping: `#86`

- [x] Extract runtime auth and pending trade/spot flow persistence helpers into `runtime/services/runtime_state.py`.
- [x] Extract transfer policy persistence/normalize/sync helpers into `runtime/services/transfer_policy.py`.
- [x] Extract trade-cap ledger and trade-usage helpers into `runtime/services/trade_caps.py`.
- [x] Keep `cli.py` wrappers thin and preserve current patch/test seams.
- [x] Add direct runtime service coverage for the moved seams.
- [x] Run full sequential validations + capture evidence in `acceptance.md`.
