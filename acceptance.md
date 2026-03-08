# Slice 225 Acceptance Evidence: Process Doc Compression

Date (UTC): 2026-03-08  
Active slice context: `Slice 225`.

Issue mapping: `#76`

### Objective + Scope Lock
- Objective:
  - keep `docs/XCLAW_SOURCE_OF_TRUTH.md` canonical,
  - move historical handoff ledgers out of active slice docs,
  - leave active `spec.md`, `tasks.md`, and `acceptance.md` concise and current.

### Behavior Checks
- [x] `spec.md`, `tasks.md`, and `acceptance.md` are active-slice summaries only.
- [x] historical ledgers are preserved in `docs/history/SPEC_HISTORY.md`, `docs/history/TASKS_HISTORY.md`, and `docs/history/ACCEPTANCE_HISTORY.md`.
- [x] `docs/XCLAW_SOURCE_OF_TRUTH.md` remains the canonical behavior contract.

### Required Validation Gates
- [x] doc consistency checks -> PASS (`rg` confirmed active slice/issue mappings in active docs; archived history files exist under `docs/history/`)
- [x] `npm run build` -> PASS (Next.js build completed successfully)
- [x] `pm2 restart all` -> PASS (`xclaw-web online`)
