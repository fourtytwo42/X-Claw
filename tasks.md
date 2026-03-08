# Slice 229 Tasks: Service Extraction from cli and Final Router Reduction (2026-03-08)

Issue mapping: `#82`

- [x] Extract shared transfer/x402 mirror helpers from `cli.py` into runtime services.
- [x] Extract shared reporting/status helper functions from `cli.py` into runtime services.
- [x] Keep `cli.py` wrappers thin and preserve command-module independence from `cli.py` internals.
- [x] Keep direct adapter coverage and extracted-family runtime suites green.
- [x] Run full sequential validations + capture evidence in `acceptance.md`.
