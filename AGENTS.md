# X-Claw Agent Rules (Repo-Local, Mandatory)

These rules apply to all coding/planning work in this repository.

## 1) Canonical authority
1. `docs/XCLAW_SOURCE_OF_TRUTH.md` is the single source of truth.
2. If code/docs conflict with source-of-truth, update both in the same change.
3. Do not implement speculative behavior that is not locked in source-of-truth.
4. Synchronization is mandatory:
- If app behavior changes, update source-of-truth and affected canonical artifacts in the same change.
- If source-of-truth changes behavior, update app code and affected canonical artifacts in the same change.
- If canonical artifacts change behavior/contract, update app code and source-of-truth in the same change.

## 2) Best-practice baseline (always-on)
Follow `docs/BEST_PRACTICES_RULEBOOK.md` for every change. Treat it as a quality gate, not optional guidance.
For non-trivial changes, complete `docs/CONTEXT_PACK.md` first.

## 2.1) Execution order baseline (mandatory)
Build execution must follow both:
- `docs/XCLAW_SLICE_TRACKER.md` (sequential slice order),
- `docs/XCLAW_BUILD_ROADMAP.md` (detailed milestone checklist).

Rules:
1. Work one slice at a time from `XCLAW_SLICE_TRACKER.md`.
2. Do not start the next slice until current slice DoD is met and marked complete.
3. For every active slice, implementation scope must be validated against both:
- `docs/XCLAW_SLICE_TRACKER.md` (slice Goal + DoD),
- `docs/XCLAW_SOURCE_OF_TRUTH.md` (canonical behavior/contract for that slice scope).
4. If tracker and source-of-truth differ, stop implementation and reconcile both docs in the same change before continuing.
5. Any touched roadmap items for the active slice must be updated in the same change.
6. If work crosses slice boundaries, stop and split into separate follow-up changes unless explicitly approved.
7. After a slice is fully tested and all required validations pass, commit and push that slice before starting the next slice.
8. Every slice must be linked to at least one GitHub issue; on slice completion, post verification evidence + commit hash(es) to the mapped issue(s) in the same session.

## 2.2) Runtime separation baseline (mandatory)
1. Treat server/web runtime and agent/OpenClaw runtime as separate concerns.
2. Server/web stack is Node/Next.js (`apps/network-web` + API + build scripts).
3. Agent/OpenClaw skill stack is Python-first (`skills/xclaw-agent/scripts/*.py` + `apps/agent-runtime` CLI surface).
4. Do not introduce Node/npm as a requirement for invoking OpenClaw skill commands or agent skill setup flows.

## 3) Security-first implementation rules
1. Treat AI output as untrusted input.
2. Never execute arbitrary shell/user strings without allowlisted validation.
3. Never hardcode secrets; use env/secret management only.
4. Validate/sanitize paths, URLs, and rendered content.
5. Preserve trust boundaries (agent-local wallet keys never leave agent runtime).

## 4) Contract and schema discipline
1. API changes must update:
- `docs/api/openapi.v1.yaml`
- relevant schemas in `packages/shared-schemas/json/`
- relevant source-of-truth sections
2. Data-model changes must update:
- `infrastructure/migrations/*.sql`
- parity checks and docs
3. No partial contract updates:
- do not merge changes where app/code, source-of-truth, and canonical artifacts are out of sync.

## 5) Required validation before claiming done
Run and verify:
1. `npm run db:parity`
2. `npm run seed:reset`
3. `npm run seed:load`
4. `npm run seed:verify`
5. `npm run build` (when Node/npm available)
6. After `npm run build` succeeds, run `pm2 restart all` (when PM2 is available) so the latest build is live for testing.
7. Build and PM2 restart must be sequential (never parallel): restart only after build exits successfully.
8. For changed functionality, include task-specific verification commands and expected outcomes in summary.
9. Trading-path features must show Hardhat-local validation evidence before Base Sepolia evidence.

## 6) Evidence and traceability
1. For non-trivial changes, include file-level evidence in summary.
2. For factual external claims, cite authoritative sources in docs.
3. Keep rationale concise and explicit.

## 7) UI consistency rules
1. Follow canonical prompt/style contracts in `docs/XCLAW_SOURCE_OF_TRUTH.md` (Section 42).
2. Support dark/light themes; dark default.
3. Preserve exact status vocabulary: `active`, `offline`, `degraded`, `paused`, `deactivated`.

## 8) If blocked
If a required tool/runtime is missing, state the blocker explicitly, implement what is possible, and provide exact next command(s) to unblock.

## 9) Pre-flight and in-flight discipline
1. Before edits, define:
- objective,
- acceptance checks,
- expected touched files.
 - active slice ID from `docs/XCLAW_SLICE_TRACKER.md`.
2. Announce touched files list before applying edits.
3. Keep diffs reviewable by default (small slices). If change is large, explain why in summary.
4. No opportunistic refactors/format-only changes unless explicitly requested or required for correctness.
5. For non-trivial work, create/update handoff artifacts:
- `spec.md` (goal/non-goals/constraints),
- `tasks.md` (checklist),
- `acceptance.md` (proof commands/outcomes),
or explicitly document why not needed.

## 10) Dependency and supply-chain controls
1. Do not add dependencies without explicit justification in summary.
2. Any new dependency must include:
- purpose,
- version pin,
- risk note (why package is trusted/necessary).
3. Never use packages that cannot be verified as real/maintained.

## 11) Testing quality guardrails
1. Avoid placebo tests (`assert true` style).
2. For behavior changes, include at least one negative/failure-path validation.
3. For auth/security-sensitive paths, require explicit proof command/output in summary.
4. If both implementation and tests are AI-generated, require an extra human-verified invariant/property check.

## 12) Stop-ship triggers
Pause and resolve before continuing if any occur:
1. scope drift beyond stated objective,
2. contract mismatch between app/source-of-truth/canonical artifacts,
3. unverifiable dependency addition,
4. security-sensitive change without verification evidence.
5. repeated speculative fixes without reproducible failure evidence.

## 13) Evidence-first debugging and recovery
1. Debug in this order:
- reproduce failure,
- instrument/observe runtime,
- list hypotheses,
- smallest fix,
- reproduce again,
- add regression coverage.
2. If session state degrades, apply recovery sequence:
- stop edits,
- snapshot state (`git status` + commit/stash),
- localize fault,
- choose rollback vs incremental fix,
- resume with strict file allowlist.
3. For regressions, prefer `git bisect` when feasible.

## 14) High-risk review mode
Use high-risk mode (security/auth/payments/wallet/migrations/CI changes):
1. require second-opinion review pass (human or second model),
2. require explicit rollback plan in summary,
3. reject merge without concrete verification evidence.
