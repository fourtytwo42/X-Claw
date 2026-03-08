# Slice 227 Tasks: Explicit Adapters for Approvals and Trade (2026-03-08)

Issue mapping: `#80`

- [x] Add explicit runtime adapter types for approvals and trade under `runtime/adapters/`.
- [x] Refactor approvals and trade command modules to consume explicit adapters instead of `sys.modules[__name__]`.
- [x] Update `cli.py` to build typed adapters and dispatch approvals/trade through thin wrappers.
- [x] Extract shared agent API helper functions used by these adapters into `runtime/services/agent_api.py`.
- [x] Add direct adapter contract coverage in `test_runtime_adapters.py` and keep approvals/trade regressions green.
- [x] Run full sequential validations + capture evidence in `acceptance.md`.
