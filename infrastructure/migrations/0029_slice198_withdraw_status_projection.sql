alter table if exists agent_transfer_approval_mirror
  add column if not exists request_kind varchar(16) not null default 'transfer';

alter table if exists agent_transfer_decision_inbox
  add column if not exists request_kind varchar(16) not null default 'transfer';

alter table if exists agent_transfer_approval_mirror
  drop constraint if exists agent_transfer_approval_request_kind_check;

alter table if exists agent_transfer_approval_mirror
  add constraint agent_transfer_approval_request_kind_check
  check (request_kind in ('transfer', 'withdraw', 'x402'));

alter table if exists agent_transfer_decision_inbox
  drop constraint if exists agent_transfer_decision_request_kind_check;

alter table if exists agent_transfer_decision_inbox
  add constraint agent_transfer_decision_request_kind_check
  check (request_kind in ('transfer', 'withdraw', 'x402'));

create index if not exists idx_transfer_approval_mirror_agent_chain_kind_status
  on agent_transfer_approval_mirror(agent_id, chain_key, request_kind, status, created_at desc);

create index if not exists idx_transfer_decision_inbox_agent_chain_kind_status
  on agent_transfer_decision_inbox(agent_id, chain_key, request_kind, status, created_at desc);
