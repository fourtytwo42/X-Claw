# X-Claw Best Practices Rulebook

This rulebook is derived from project references in:
- `Notes/How-To-Build-Anything-With-AI/Resources/Checklists/Security-Checklist-AI-Code.md`
- `Notes/How-To-Build-Anything-With-AI/Resources/Checklists/Migration-Checklists.md`
- `Notes/OpenClawBook/book/00-admin/manuscript-qa-gates.md`

## A) Security and trust boundaries
1. Validate all inputs at boundaries (path, URL, payload, command args).
2. Enforce allowlists for privileged operations.
3. Use HTTPS and explicit endpoint controls.
4. Never persist plaintext secrets in code/config.
5. Keep wallet signing local to agent runtime only.

## B) Change management
1. Keep migrations explicit and reversible where practical.
2. Keep schema, API, and docs in sync in one change.
3. Preserve backward compatibility unless source-of-truth explicitly authorizes breakage.
4. Prefer small, testable increments over broad refactors.
5. Use a context pack before non-trivial changes (`docs/CONTEXT_PACK.md`).
6. State expected touched files before implementation.
7. Do not perform unrelated refactors in feature/fix changes.
8. Maintain handoff artifacts for complex work: `spec.md`, `tasks.md`, `acceptance.md`.

## C) Testing and acceptance
1. Maintain deterministic seed fixtures and repeatable runbooks.
2. Gate claims with executable evidence (parity scripts, seed verify, build, then `pm2 restart all` when PM2 is available); run build and restart sequentially, never in parallel.
3. Add test vectors for state transitions, policy logic, and failure paths.
4. Include negative/failure-path checks for changed behavior.
5. Reject placebo tests that do not assert real behavior.
6. Use local chain-first validation (Hardhat) before external testnet promotion for trading-path changes.
7. If AI generated both code and tests, add independent invariant/property validation to avoid shared assumption bias.

## D) Observability and operations
1. Emit structured logs with correlation IDs.
2. Make degraded/offline states explicit in UI.
3. Define health/status endpoints and keep them accurate.
4. Keep incident reasons human-readable.
5. Include actionable operator hints in errors (`actionHint` where applicable).

## E) QA discipline (adapted from QA gates)
1. Traceability: every major claim/change maps to file evidence.
2. Consistency: numeric/status semantics must match across docs/schemas/code.
3. Safety framing: do not include unsafe operational instructions.
4. Readiness: known gaps must be explicit, not implicit.
5. Scope control: reject over-broad diffs that solve a different problem than requested.
6. Require concrete acceptance evidence, not narrative claims.

## F) Definition of done (engineering)
A change is done only when:
1. source-of-truth is updated (if behavior changed),
2. artifacts/schemas/openapi/migrations are aligned,
3. required validation commands pass,
4. summary includes what changed + any remaining explicit gaps.
5. dependency changes (if any) are justified, pinned, and risk-noted.

## G) Dependency and supply-chain safety
1. Verify new packages are real, maintained, and necessary.
2. Pin versions for deterministic builds.
3. Avoid adding transitive risk for convenience-only changes.
4. Prefer existing project dependencies when feasible.

## H) Evidence-first debugging and recovery
1. Debug loop: reproduce -> instrument -> hypothesize -> smallest fix -> re-verify -> regression test.
2. Use minimal reproducible examples for unstable failures.
3. Use `git bisect` for regression localization when practical.
4. If context/session degrades, use recovery sequence:
- snapshot state,
- localize fault,
- rollback or incremental fix,
- resume with strict file scope.

## I) High-risk change protocol
Applies to auth, wallet, security, migration, CI, and deployment logic:
1. require second-opinion review pass,
2. require explicit rollback plan,
3. require proof commands and outputs before closure.

## J) AI output trust boundary
1. Treat all AI output as untrusted input until validated.
2. Never execute generated commands directly from free text.
3. Parse/validate generated actions against schema/policy first, then execute.
4. Reject generated output that bypasses allowlist/policy constraints.

## K) Context intake hygiene
1. Include only explicitly selected files in model context for implementation tasks.
2. Exclude untrusted or irrelevant repository content from privileged decision prompts.
3. Strip hidden/invisible context content before use when possible.
4. Keep context minimal and task-bounded to reduce prompt-injection risk.

## L) Security regression gate
1. Any change touching auth, wallet, path handling, command execution, or network controls must include at least one negative security-path test.
2. Negative tests must assert rejection behavior for invalid/unsafe input.
3. Merges are blocked for these classes if no negative test evidence exists.

## M) Rule evolution trigger
1. If a new implementation pattern appears in 3+ files or 2+ PRs, add/update a formal rule.
2. Rule updates must include actionable examples.
3. Rule updates should land in the same sprint as the repeated pattern.

## N) Proof-pass completion
1. Every non-trivial change must include a proof pass artifact:
- what changed,
- why it is safe/correct,
- validation command evidence.
2. Narrative-only completion claims are insufficient.

## O) Parallel-run migration safety
1. Risky migrations (runtime, security, auth, data path) should run old and new paths in parallel until core workflows match.
2. Cutover requires explicit parity evidence.
3. Keep rollback path available until post-cutover verification passes.

## P) Claim classification discipline
1. Major specs/decisions must be labeled `locked`, `provisional`, or `open`.
2. Implementation may only treat `locked` items as final behavior contracts.
3. `provisional` and `open` items must not silently harden into runtime assumptions.

## Q) Known-gaps ledger
1. Maintain one visible gaps ledger for unresolved decisions/defects.
2. Every gap entry must include:
- owner,
- impact,
- unblock condition.
3. No implicit gaps are allowed at release gates.

## R) Cross-artifact consistency sweep
1. Before merge/release, verify consistency for:
- enums/status names,
- TTLs/limits,
- error codes/messages,
- endpoint names and auth classes.
2. Sweep must cover source-of-truth, schemas, OpenAPI, runbooks, and affected UI copy.

## S) Render-safety baseline
1. Any user/generated markdown/html rendered in UI must be sanitized.
2. Default to safe rendering (no unsafe embeds/scripts).
3. Keep CSP-compatible rendering behavior for dynamic content surfaces.

## T) Slice-first execution discipline
1. Execute work in strict sequence using `docs/XCLAW_SLICE_TRACKER.md`.
2. Use `docs/XCLAW_BUILD_ROADMAP.md` as the detailed checklist for the active slice only.
3. Keep one active slice at a time; do not parallelize across slices unless explicitly approved.
4. A slice is complete only when all DoD items are checked and evidence exists.
5. Update tracker + roadmap status in the same change that implements slice work.
6. If scope spills into next slice, split and defer instead of expanding current change.

## U) Runtime boundary discipline
1. Keep OpenClaw skill and agent-runtime command paths Python-first.
2. Keep Node/npm requirements scoped to server/web build and API runtime concerns.
3. Reject changes that blur this boundary unless source-of-truth is explicitly updated first.
