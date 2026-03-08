# Slice 230 Tasks: Transfer Execution and Approval Prompt Services (2026-03-08)

Issue mapping: `#83`

- [x] Extract pending transfer flow persistence/recovery helpers into `runtime/services/transfer_flows.py`.
- [x] Extract transfer execution + transfer balance precondition helpers into `runtime/services/transfer_flows.py`.
- [x] Extract approval prompt persistence/wait-loop/cleanup helpers into `runtime/services/approval_prompts.py`.
- [x] Keep `cli.py` wrappers thin and preserve current patch/test seams.
- [x] Add direct service coverage and keep targeted runtime suites green.
- [x] Run full sequential validations + capture evidence in `acceptance.md`.
