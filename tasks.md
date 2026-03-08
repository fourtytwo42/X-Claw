# Slice 231 Tasks: Trade Router Execution Service Extraction (2026-03-08)

Issue mapping: `#84`

- [x] Extract router receipt/allowance/quote/execute helpers into `runtime/services/trade_execution.py`.
- [x] Keep `cli.py` wrappers thin and preserve current patch/test seams for trade + liquidity callers.
- [x] Add direct service coverage for the moved trade/router helpers.
- [x] Run full sequential validations + capture evidence in `acceptance.md`.
