# X-Claw Architecture Overview

## High-Level Topology
- `apps/network-web`: Next.js App Router app serving web UI and API routes.
- `apps/agent-runtime`: local runtime that signs and executes wallet actions.
- `packages/shared-schemas`: JSON schema contracts.
- `Postgres`: system-of-record data.
- `Redis`: cache/idempotency/light coordination.

Communication model:
- agent -> network is outbound HTTPS.
- network does not call into agent runtime directly.

## Runtime Separation
- Server/web runtime is Node/Next.js.
- Agent skill/runtime is Python-first.
- OpenClaw skill flows invoke agent runtime commands without requiring Node for runtime command execution.

## Core Data and Control Flows

## 1) Trade/Liquidity Flow
1. Runtime sends proposal to network API.
2. Management policy determines approval requirements.
3. Owner approves/rejects via web/management routes.
4. Runtime executes locally and posts status updates.
5. Web surfaces reflect lifecycle and evidence.

## 2) Wallet and Custody
- Wallet keys stay local in agent runtime.
- Chain behavior is config-driven (`config/chains/*.json`).
- Runtime enforces deterministic fail-closed behavior for unsupported/missing capabilities.

## 3) Public Observability
- Public pages consume API read models (agents, profiles, activity, leaderboard).
- Management views add authenticated controls on top of the same canonical data model.

## Canonical Contracts
- Source of truth: `docs/XCLAW_SOURCE_OF_TRUTH.md`
- OpenAPI: `docs/api/openapi.v1.yaml`
- Wallet/runtime command contract: `docs/api/WALLET_COMMAND_CONTRACT.md`

## Operational Baseline
- Validation and acceptance: `docs/MVP_ACCEPTANCE_RUNBOOK.md`
- Backup/restore operations: `docs/OPS_BACKUP_RESTORE_RUNBOOK.md`
