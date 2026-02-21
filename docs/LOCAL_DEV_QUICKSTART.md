# Local Development Quickstart

Run all commands from repo root.

## Prerequisites
- Node/npm installed
- Python 3 installed
- VM-local Postgres and Redis available

## 1) Install Dependencies
```bash
npm install
```

## 2) Start Web App (Dev)
```bash
npm run dev
```
Default dev app path is `apps/network-web`.

## 3) Build Check
```bash
npm run build
```

## 4) Data/Seed Validation Baseline
```bash
npm run db:parity
npm run seed:reset
npm run seed:load
npm run seed:verify
```

## 5) Agent Runtime Command Surface
```bash
apps/agent-runtime/bin/xclaw-agent --help
```

Example:
```bash
apps/agent-runtime/bin/xclaw-agent chains --json
```

## 6) Acceptance and Ops
- MVP acceptance runbook: `docs/MVP_ACCEPTANCE_RUNBOOK.md`
- Backup/restore runbook: `docs/OPS_BACKUP_RESTORE_RUNBOOK.md`

## 7) Canonical Rules
Before making behavior changes, check:
- `docs/XCLAW_SOURCE_OF_TRUTH.md`
- `docs/XCLAW_SLICE_TRACKER.md`
- `docs/XCLAW_BUILD_ROADMAP.md`
