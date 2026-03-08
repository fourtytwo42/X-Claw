# Slice 237 Tasks: Transfer-Flow/Approval-Prompt/Trade-Cap Resilience (2026-03-08)

Issue mapping: `#91`

- [x] Add direct resilience coverage for `runtime/services/transfer_flows.py`.
- [x] Add direct resilience coverage for `runtime/services/approval_prompts.py`.
- [x] Add direct resilience coverage for `runtime/services/trade_caps.py`.
- [x] Preserve stale recovery, resend/cooldown, cleanup, and replay semantics.
- [x] Run full sequential validations + capture evidence in `acceptance.md`.
