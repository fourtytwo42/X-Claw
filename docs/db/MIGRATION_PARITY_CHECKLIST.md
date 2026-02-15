# Migration Parity Checklist

This checklist maps source-of-truth schema requirements to SQL migration coverage.

## Required now
- canonical core tables present, including:
  - `agents`, `agent_wallets`, `agent_policy_snapshots`, `trades`, `agent_events`, `performance_snapshots`
  - `copy_subscriptions`, `management_tokens`, `management_sessions`
  - `management_audit_log`, `chat_room_messages`, `agent_transfer_policies`
  - `agent_chain_policies`, `agent_chain_approval_channels`, `trade_approval_prompts`
- compatibility contract tables present:
  - `approvals`, `copy_intents`
- canonical enums present, including:
  - trade lifecycle enum (`trade_status`)
  - approval/copy/session related enums
- `management_audit_log` is append-only via DB trigger.
- required canonical indexes for trades/audit/chat are present.
- `agents.last_name_change_at` exists for username-change cooldown enforcement.
- outbound transfer policy enum/table/index exists:
  - `outbound_transfer_mode`
  - `agent_transfer_policies`
  - `idx_agent_transfer_policies_agent_chain`

## Verification command
```bash
npm run db:parity
```

## Exit criteria
- command returns JSON with `"ok": true`
- no missing tables
- no missing enums
- no missing checks
