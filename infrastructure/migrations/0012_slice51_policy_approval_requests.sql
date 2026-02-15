-- Slice 51: Policy Approval Requests (Token Preapprove + Approve All) With Web + Telegram Buttons

create table if not exists agent_policy_approval_requests (
  request_id text primary key,
  agent_id text not null references agents(agent_id),
  chain_key varchar(64) not null,
  request_type varchar(64) not null,
  token_address varchar(128),
  status varchar(32) not null,
  reason_message text,
  decided_by_management_session_id text references management_sessions(session_id),
  created_at timestamptz not null default now(),
  decided_at timestamptz,
  updated_at timestamptz not null default now()
);

create index if not exists agent_policy_approval_requests_agent_chain_status_idx
  on agent_policy_approval_requests (agent_id, chain_key, status, created_at desc);

create index if not exists agent_policy_approval_requests_agent_created_idx
  on agent_policy_approval_requests (agent_id, created_at desc);

