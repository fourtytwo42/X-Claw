# X-Claw Context Pack

## 1) Goal (Active: Slice 39)
- Primary objective: complete `Slice 39: Approval Amount Visibility + Gateway Telegram Callback Reliability`.
- Success criteria:
  - `/agents/:id` Approval Queue shows amount + tokenIn -> tokenOut (not just pair).
  - `/agents/:id` Activity shows trade amountIn/amountOut in the feed rows.
  - Telegram Approve buttons:
    - transition `approval_pending -> approved` via agent-auth `POST /api/v1/trades/:tradeId/status`,
    - delete the Telegram approval message,
    - and the web approvals queue converges immediately.
  - runtime usage outbox replay is best-effort and never blocks local input validation errors.
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

## 4) Files and Boundaries (Slice 39 allowlist)
- Web/API/UI:
  - `apps/network-web/src/app/agents/[agentId]/page.tsx`
- Canonical docs/process:
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `docs/CONTEXT_PACK.md`
  - `spec.md`
  - `tasks.md`
  - `acceptance.md`
- Runtime:
  - `apps/agent-runtime/xclaw_agent/cli.py`
- OpenClaw:
  - `patches/openclaw/003_openclaw-2026.2.9-dist-xclaw-approvals.patch`

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
  - approvals queue shows amounts for pending approvals
  - activity feed shows trade amounts in rows
  - clicking Telegram Approve transitions trade and deletes the prompt message (no LLM mediation)

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
