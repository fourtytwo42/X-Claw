# X-Claw Context Pack

## 1) Goal (Active: Slice 34)
- Primary objective: complete `Slice 34: Telegram Approvals (Inline Button Approve) + Web UI Sync`.
- Success criteria:
  - trade `approval_pending` triggers a Telegram approval prompt only when:
    - Telegram approvals are enabled for agent+chain, and
    - OpenClaw last active channel is Telegram (session store `lastChannel == telegram`)
  - clicking Approve in Telegram:
    - approves trade server-side (no management cookies/CSRF),
    - deletes the Telegram approval message,
    - and `/agents/:id` approvals queue reflects approval immediately
  - if web approves first, runtime deletes the Telegram prompt (best-effort + periodic sync)
  - strict security boundary: approval execution is from real Telegram button click (no LLM/tool mediation)
  - source-of-truth + canonical docs remain synchronized (schemas/openapi/tracker/roadmap/spec/tasks/acceptance)
  - required gates pass: `db:parity`, `seed:reset`, `seed:load`, `seed:verify`, `build`

## 2) Constraints
- Canonical authority: `docs/XCLAW_SOURCE_OF_TRUTH.md`.
- Strict slice order: Slice 34 follows completed Slice 33.
- One-site model remains fixed (`/agents/:id` public + auth-gated management).
- No dependency additions.
- DB migration required for this slice (approval channel + prompt tracking tables).

## 3) Contract Impact
- Management toggle + secret issuance:
  - `POST /api/v1/management/approval-channels/update` enables/disables Telegram approvals per chain.
  - enable is step-up gated and returns a one-time secret; disable is not step-up gated.
- Agent policy read change:
  - `GET /api/v1/agent/transfers/policy` includes `approvalChannels.telegram.enabled` (no secrets).
- Runtime prompt reporting:
  - `POST /api/v1/agent/approvals/prompt` records prompt metadata for cleanup/sync.
- Telegram approval decision:
  - `POST /api/v1/channel/approvals/decision` authorizes via Bearer secret and idempotently approves pending trades.

## 4) Files and Boundaries (Slice 34 allowlist)
- Web/API/UI:
  - `apps/network-web/src/app/agents/[agentId]/page.tsx`
  - `apps/network-web/src/app/api/v1/management/approval-channels/update/route.ts`
  - `apps/network-web/src/app/api/v1/channel/approvals/decision/route.ts`
  - `apps/network-web/src/app/api/v1/agent/approvals/prompt/route.ts`
  - `apps/network-web/src/app/api/v1/management/agent-state/route.ts`
  - `apps/network-web/src/app/api/v1/agent/transfers/policy/route.ts`
- Canonical docs/process:
  - `docs/XCLAW_SOURCE_OF_TRUTH.md`
  - `docs/XCLAW_SLICE_TRACKER.md`
  - `docs/XCLAW_BUILD_ROADMAP.md`
  - `docs/api/openapi.v1.yaml`
  - `docs/api/WALLET_COMMAND_CONTRACT.md`
  - `docs/CONTEXT_PACK.md`
  - `spec.md`
  - `tasks.md`
  - `acceptance.md`
- Runtime:
  - `apps/agent-runtime/xclaw_agent/cli.py`
- Shared schemas:
  - `packages/shared-schemas/json/management-approval-channel-update-request.schema.json`
  - `packages/shared-schemas/json/agent-approvals-prompt-request.schema.json`
  - `packages/shared-schemas/json/channel-approval-decision-request.schema.json`
- Data model:
  - `infrastructure/migrations/0010_slice34_telegram_approvals.sql`
- OpenClaw:
  - `Notes/openclaw/src/telegram/bot-handlers.ts`
  - `Notes/openclaw/src/telegram/xclaw-approvals.ts`

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
- Feature checks:
  - enabling Telegram approvals in `/agents/:id` requires step-up and returns a secret once
  - runtime sends a Telegram approval prompt only when OpenClaw last active channel is Telegram
  - clicking Telegram Approve transitions trade to `approved` and deletes the prompt message
  - approving from web UI causes runtime cleanup to delete the Telegram prompt (best-effort + `approvals sync`)

## 7) Evidence + Rollback
- Capture command outputs and UX evidence in `acceptance.md`.
- Rollback plan:
  1. revert Slice 34 touched files only,
  2. rerun required gates,
  3. confirm approvals continue to function in web UI with no Telegram delivery behavior.

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
