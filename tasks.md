# Slice 251 Tasks: Management Session Bootstrap Reliability and Authorized `/agents/:id` Proof (2026-03-10)

- [x] Add a deterministic management bootstrap/session proof runner under `infrastructure/scripts/`.
- [x] Add a management-session contract test that locks invalid/expired bootstrap rejection, CSRF enforcement, and removal of stale step-up blocker wording.
- [x] Add npm script entries for the new proof runner and contract test.
- [x] Reconcile `docs/XCLAW_SOURCE_OF_TRUTH.md`, `docs/XCLAW_SLICE_TRACKER.md`, `docs/XCLAW_BUILD_ROADMAP.md`, `docs/CONTEXT_PACK.md`, `spec.md`, and `acceptance.md` to the current cookie + CSRF contract.
- [x] Prove authorized `/agents/:id` owner-only surface using the existing approval-row verifier after management bootstrap.
- [x] Run validation chain and capture evidence in `acceptance.md`.
- [x] Commit, push, and post evidence to issue `#104`.
