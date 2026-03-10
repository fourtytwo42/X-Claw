# Slice 251 Spec: Management Session Bootstrap Reliability and Authorized `/agents/:id` Proof (2026-03-10)

## Goal
Turn management authorization into deterministic proof covering owner-link issuance, bootstrap token acceptance, session cookie + CSRF issuance, authorized reads, sensitive write success with CSRF, sensitive write rejection without CSRF, and owner-only `/agents/:id` proof.

## Non-Goals
- no API schema changes
- no new auth/step-up mechanism
- no runtime command redesign
- no API schema changes

## Constraints
- active management contract remains bootstrap token -> `xclaw_mgmt` + `xclaw_csrf` -> authorized read/write
- sensitive management writes require CSRF and must fail deterministically without it
- owner-only `/agents/:id` proof should use deterministic automation, not introduce a new browser stack
- step-up is removed and must not reappear as an active contract
