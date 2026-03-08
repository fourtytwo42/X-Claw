# Slice 232 Tasks: Final cli.py Reduction + Service-Hardening Pass (2026-03-08)

Issue mapping: `#85`

- [x] Extract provider settings/fallback/provider-meta helper ownership into `runtime/services/execution_contracts.py`.
- [x] Extract advanced liquidity nested-command execution helpers into `runtime/services/liquidity_execution.py`.
- [x] Keep `cli.py` wrappers thin and preserve current patch/test seams for trade + liquidity callers.
- [x] Expand direct runtime service coverage for the new service seams.
- [x] Run full sequential validations + capture evidence in `acceptance.md`.
