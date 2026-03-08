# Slice 235 Tasks: Status/Reporting Services + Final cli.py Audit (2026-03-08)

Issue mapping: `#88`

- [x] Extract trade/liquidity status posting helpers into `runtime/services/reporting.py`.
- [x] Extract trade-detail read + trade execution report helpers into `runtime/services/reporting.py`.
- [x] Keep `cli.py` wrappers thin and preserve current patch/test seams.
- [x] Add direct runtime service coverage for the moved seams.
- [x] Run full sequential validations + capture evidence in `acceptance.md`.
