# Slice 242 Tasks: Runtime Recovery and Watchdog Sweep (2026-03-08)

Issue mapping: `#95`

- [x] Add direct restart/recovery coverage for runtime state, transfer flows, approval prompts, trade caps, reporting, and mirroring.
- [x] Keep pending-flow restart/resume behavior deterministic and fail-closed.
- [x] Prove replay queues and prompt cleanup remain idempotent after interruption/reload.
- [x] Run full sequential validations + capture evidence in `acceptance.md`.
