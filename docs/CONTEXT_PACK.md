# X-Claw Context Pack

## 1) Goal (Active: Slice 47)
- Primary objective: complete `Slice 47: Fix Telegram Queued Buttons Attach Point (Agent Reply Send Path)`.
- Success criteria:
  - For Telegram, OpenClaw auto-attaches Approve/Deny buttons to the queued `approval_pending` trade message in the agent reply pipeline (not just the CLI send path).
  - required gates pass: `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`, runtime tests.

## 2) Constraints
- Canonical authority: `docs/XCLAW_SOURCE_OF_TRUTH.md`.
- Strict slice order: Slice 38 follows completed Slice 37.
- One-site model remains fixed (`/agents/:id` public + auth-gated management).
- No dependency additions.
- No new DB migration required for this slice (reuses Slice 34 tables; removes secret requirement and channel-auth path).

## 3) Contract Impact
- Management toggle:
  - `POST /api/v1/management/approval-channels/update` enables/disables Telegram approvals per chain (no secret issuance).
- Agent policy read change:
  - `GET /api/v1/agent/transfers/policy` includes `approvalChannels.telegram.enabled` (no secrets).
- Runtime prompt reporting:
  - `POST /api/v1/agent/approvals/prompt` records prompt metadata for cleanup/sync.
- Telegram approve path:
  - Telegram approve uses `POST /api/v1/trades/:tradeId/status` (agent-auth + `Idempotency-Key`) to transition `approval_pending -> approved`.
 - No API schema changes in this slice; web UI only.
 - OpenClaw gateway behavior change is delivered as a patch against OpenClaw dist bundle for the deployed version.

## 4) Files and Boundaries (Slice 47 allowlist)
- Web/API/UI:
  - none
- Canonical docs/process:
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `docs/CONTEXT_PACK.md`
  - `spec.md`
  - `tasks.md`
  - `acceptance.md`
- Runtime:
  - none
- OpenClaw patcher:
  - `skills/xclaw-agent/scripts/openclaw_gateway_patch.py`
- OpenClaw:
  - `skills/xclaw-agent/scripts/openclaw_gateway_patch.py`
  - `apps/agent-runtime/xclaw_agent/cli.py` (unchanged for this slice)
  - `skills/xclaw-agent/scripts/setup_agent_skill.py`
  - `skills/xclaw-agent/scripts/xclaw_agent_skill.py`
  - patch artifacts in `patches/openclaw/` (for reproducibility / inspection)

## 5) Invariants
- Status vocabulary remains exactly: `active`, `offline`, `degraded`, `paused`, `deactivated`.
- Authorized management controls remain owner/session-gated only.
- Dark/light themes remain supported with dark default.
- Existing management functionality remains available (pause/resume, policy, approvals, limit orders, withdraw, audit).

## 6) Verification Plan
- Required gates:
  - `npm run db:parity`
  - `npm run seed:reset`
  - `npm run seed:load`
  - `npm run seed:verify`
  - `npm run build`
  - `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`
- Feature checks:
  - running installer twice does not restart gateway again when already patched
  - after simulating an OpenClaw update (patch marker removed), next skill use re-applies patch and restarts once

## 7) Evidence + Rollback
- Capture command outputs and UX evidence in `acceptance.md`.
- Rollback plan:
  1. revert Slice 37 touched files only,
  2. rerun required gates,
  3. confirm approvals continue to function in web UI and Telegram prompts do not attempt secretless approvals.

---

## Slice 35 Context: Wallet-Embedded Approval Controls + Correct Token Decimals

Issue mapping: `#42` (umbrella)

### Objective + scope lock
- Objective: embed approval policy controls into the wallet card on `/agents/:id`, fix token decimals formatting (USDC), and expand default-collapsed management details.
- Scope guard honored: no DB migrations, no new auth model, no dependency additions.

### Expected touched files (Slice 35 allowlist)
- Web/UI:
  - `apps/network-web/src/app/agents/[agentId]/page.tsx`
  - `apps/network-web/src/app/globals.css`
- Server:
  - `apps/network-web/src/app/api/v1/management/agent-state/route.ts`
  - `apps/network-web/src/app/api/v1/trades/proposed/route.ts`
  - `apps/network-web/src/lib/copy-lifecycle.ts`
- Docs/process:
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/CONTEXT_PACK.md`
  - `spec.md`
  - `tasks.md`
  - `acceptance.md`

### Verification Plan
- Required gates:
  - `npm run db:parity`
  - `npm run seed:reset`
  - `npm run seed:load`
  - `npm run seed:verify`
  - `npm run build`
  - `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

## Slice 48 Context: Queued Approval Buttons v3 Upgrade + Logging (Debuggable)

Issue mapping: `#42` (umbrella)

### Objective + scope lock
- Objective: make Telegram queued approval buttons attach behavior diagnosable and resilient by upgrading the OpenClaw patch to v3 and emitting gateway logs on attach/skip.
- Scope guard honored: no DB changes, no dependency additions, no auth model changes.

### Expected touched files (Slice 48 allowlist)
- Skill tooling:
  - `skills/xclaw-agent/scripts/openclaw_gateway_patch.py`
- Docs/process:
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/CONTEXT_PACK.md`
  - `spec.md`
  - `tasks.md`
  - `acceptance.md`

### Verification Plan
- Required gates:
  - `npm run db:parity`
  - `npm run seed:reset`
  - `npm run seed:load`
  - `npm run seed:verify`
  - `npm run build`
  - `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

## Slice 49 Context: OpenClaw Patcher Safety (Syntax Check + Targeted Bundle)

Issue mapping: `#42` (umbrella)

### Objective + scope lock
- Objective: ensure the OpenClaw gateway patcher cannot break `openclaw` by validating patched output syntax and targeting only canonical gateway bundles.
- Scope guard honored: no DB changes, no dependency additions.

### Expected touched files (Slice 49 allowlist)
- Skill tooling:
  - `skills/xclaw-agent/scripts/openclaw_gateway_patch.py`
- Docs/process:
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/CONTEXT_PACK.md`
  - `spec.md`
  - `tasks.md`
  - `acceptance.md`

### Verification Plan
- Required gates:
  - `npm run db:parity`
  - `npm run seed:reset`
  - `npm run seed:load`
  - `npm run seed:verify`
  - `npm run build`
  - `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

## Slice 50 Context: Telegram Decision Feedback Routed Through Agent (No Direct Gateway Ack)

Issue mapping: `#42` (umbrella)

### Objective + scope lock
- Objective: after Telegram Approve/Deny, route the decision into the agent message pipeline (so the agent informs the user), rather than the gateway posting a raw ack message.
- Scope guard honored: no DB changes, no dependency additions, no server contract changes.

### Expected touched files (Slice 50 allowlist)
- Skill tooling:
  - `skills/xclaw-agent/scripts/openclaw_gateway_patch.py`
- Docs/process:
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/CONTEXT_PACK.md`
  - `spec.md`
  - `tasks.md`
  - `acceptance.md`

### Verification Plan
- Required gates:
  - `npm run db:parity`
  - `npm run seed:reset`
  - `npm run seed:load`
  - `npm run seed:verify`
  - `npm run build`
  - `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

## Slice 51 Context: Policy Approval Requests (Token Preapprove + Approve All) With Web + Telegram Buttons

Issue mapping: `#42` (umbrella)

### Objective + scope lock
- Objective: let the agent request owner approval for token preapproval and global approval, with convergent approvals in web UI and Telegram buttons.
- Scope guard honored: no new auth model; approvals are web (mgmt cookie) or Telegram buttons (gateway intercept) like trades.

### Expected touched files (Slice 51 allowlist)
- Data model:
  - `infrastructure/migrations/0012_slice51_policy_approval_requests.sql`
- Server/API/UI:
  - `apps/network-web/src/app/api/v1/agent/policy-approvals/proposed/route.ts`
  - `apps/network-web/src/app/api/v1/policy-approvals/[requestId]/decision/route.ts`
  - `apps/network-web/src/app/api/v1/management/policy-approvals/decision/route.ts`
  - `apps/network-web/src/app/api/v1/management/agent-state/route.ts`
  - `apps/network-web/src/app/agents/[agentId]/page.tsx`
  - `apps/network-web/src/lib/*` (helpers as needed)
- Runtime/skill:
  - `apps/agent-runtime/xclaw_agent/cli.py`
  - `skills/xclaw-agent/scripts/xclaw_agent_skill.py`
  - `skills/xclaw-agent/SKILL.md`
- OpenClaw patcher:
- `skills/xclaw-agent/scripts/openclaw_gateway_patch.py`

---

## Slice 52 Context: Policy Approval Prompts (Agent-Ready queuedMessage + Instructions)

### Objective
- Make policy approval request tool outputs “agent-ready” so the agent reliably tells the human what to do and Telegram button auto-attach works every time.

### Scope lock
- In scope: runtime output fields for policy approval request commands + unit tests + docs/process evidence.
- Out of scope: server endpoints, DB schema, web UI changes (already delivered in Slice 51).

### Expected touched files (Slice 52 allowlist)
- Runtime:
  - `apps/agent-runtime/xclaw_agent/cli.py`
  - `apps/agent-runtime/tests/test_trade_path.py`
- Docs/process:
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `docs/CONTEXT_PACK.md`
  - `spec.md`
  - `tasks.md`
- `acceptance.md`

---

## Slice 53 Context: Policy Approval Revokes (Token + Approve All OFF) With Web + Telegram Buttons

### Objective
- Extend policy approvals to support revoking permissions (token removal and global approve-all disable) with the same web + Telegram button surfaces.

### Scope lock
- In scope: server requestType handling + runtime/skill commands + UI label updates + docs/process + required gates.
- Out of scope: new DB tables (reuse existing `agent_policy_approval_requests`), new Telegram patch behavior (reuse existing ppr queued-message buttons).

### Expected touched files (Slice 53 allowlist)
- Server:
  - `apps/network-web/src/app/api/v1/agent/policy-approvals/proposed/route.ts`
  - `apps/network-web/src/app/api/v1/management/policy-approvals/decision/route.ts`
  - `apps/network-web/src/app/api/v1/policy-approvals/[requestId]/decision/route.ts`
- Schemas/contracts:
  - `packages/shared-schemas/json/agent-policy-approval-proposed-request.schema.json`
  - `docs/api/openapi.v1.yaml`
- Web UI:
  - `apps/network-web/src/app/agents/[agentId]/page.tsx`
- Runtime/skill:
  - `apps/agent-runtime/xclaw_agent/cli.py`
  - `apps/agent-runtime/tests/test_trade_path.py`
  - `skills/xclaw-agent/scripts/xclaw_agent_skill.py`
  - `skills/xclaw-agent/SKILL.md`
- Docs/process:
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `docs/CONTEXT_PACK.md`
  - `spec.md`
  - `tasks.md`
- `acceptance.md`

---

## Slice 55 Context: Policy Approval De-Dupe (Reuse Pending Request)

### Objective
- Prevent policy approval spam by reusing an existing pending request when the same policy change is requested repeatedly.

### Scope lock
- In scope: server propose endpoint behavior + DB index + docs/process evidence.
- Out of scope: Telegram/web decision handling (unchanged).

### Expected touched files (Slice 55 allowlist)
- Server:
  - `apps/network-web/src/app/api/v1/agent/policy-approvals/proposed/route.ts`
- Data model:
  - `infrastructure/migrations/*.sql`
- Docs/process:
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `docs/CONTEXT_PACK.md`
  - `spec.md`
  - `tasks.md`
  - `acceptance.md`
- Contracts/docs:
  - `docs/api/openapi.v1.yaml`
  - `packages/shared-schemas/json/*`
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `spec.md`
  - `tasks.md`
  - `acceptance.md`

### Verification Plan
- Required gates:
  - `npm run db:parity`
  - `npm run seed:reset`
  - `npm run seed:load`
  - `npm run seed:verify`
  - `npm run build`
  - `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`

---

## Slice 36 Context: Remove Step-Up Authentication (Management Cookie Only)

Issue mapping: `#42` (umbrella)

### Objective + scope lock
- Objective: remove step-up entirely (cookies, endpoints, UI prompts, runtime command, DB objects) so management session cookie + CSRF is sufficient for all management actions.
- Scope guard honored: no replacement 2FA system, no dependency additions.

### Expected touched files (Slice 36 allowlist)
- Data model:
  - `infrastructure/migrations/0011_slice36_remove_stepup.sql`
  - `infrastructure/scripts/check-migration-parity.mjs`
- Server/API/UI:
  - `apps/network-web/src/lib/management-auth.ts`
  - `apps/network-web/src/lib/management-cookies.ts`
  - `apps/network-web/src/lib/management-service.ts`
  - `apps/network-web/src/lib/errors.ts`
  - `apps/network-web/src/app/api/v1/management/*` (remove stepup gates)
  - `apps/network-web/src/app/api/v1/management/stepup/*` (delete)
  - `apps/network-web/src/app/api/v1/agent/stepup/*` (delete)
  - `apps/network-web/src/app/agents/[agentId]/page.tsx`
- Runtime/skill:
  - `apps/agent-runtime/xclaw_agent/cli.py`
  - `skills/xclaw-agent/scripts/xclaw_agent_skill.py`
  - `skills/xclaw-agent/references/commands.md`
  - `skills/xclaw-agent/SKILL.md`
- Docs/contracts:
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `docs/api/openapi.v1.yaml`
  - `docs/api/AUTH_WIRE_EXAMPLES.md`
  - `packages/shared-schemas/json/*` (remove stepup schemas, update approval schema)
  - `spec.md`
  - `tasks.md`
  - `acceptance.md`

### Verification Plan
- Required gates:
  - `npm run db:parity`
  - `npm run seed:reset`
  - `npm run seed:load`
  - `npm run seed:verify`
  - `npm run build`
  - `python3 -m unittest apps/agent-runtime/tests/test_trade_path.py -v`
