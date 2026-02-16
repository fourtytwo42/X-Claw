create table if not exists agent_transfer_policy_mirror (
  policy_id text primary key,
  agent_id text not null references agents(agent_id),
  chain_key varchar(64) not null,
  transfer_approval_mode varchar(32) not null default 'per_transfer',
  native_transfer_preapproved boolean not null default false,
  allowed_transfer_tokens jsonb not null default '[]'::jsonb,
  updated_by_management_session_id text references management_sessions(session_id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (agent_id, chain_key),
  constraint agent_transfer_policy_mode_check check (transfer_approval_mode in ('auto', 'per_transfer'))
);

create table if not exists agent_transfer_approval_mirror (
  approval_id text primary key,
  agent_id text not null references agents(agent_id),
  chain_key varchar(64) not null,
  status varchar(32) not null,
  transfer_type varchar(16) not null,
  token_address varchar(128),
  token_symbol varchar(64),
  to_address varchar(128) not null,
  amount_wei numeric not null,
  tx_hash varchar(128),
  reason_code varchar(64),
  reason_message text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  decided_at timestamptz,
  terminal_at timestamptz,
  constraint agent_transfer_approval_status_check check (status in ('proposed', 'approval_pending', 'approved', 'rejected', 'executing', 'filled', 'failed')),
  constraint agent_transfer_approval_type_check check (transfer_type in ('native', 'token'))
);

create table if not exists agent_transfer_decision_inbox (
  decision_id text primary key,
  approval_id text not null,
  agent_id text not null references agents(agent_id),
  chain_key varchar(64) not null,
  decision varchar(16) not null,
  reason_message text,
  source varchar(16) not null default 'web',
  status varchar(16) not null default 'pending',
  created_at timestamptz not null default now(),
  applied_at timestamptz,
  unique (approval_id, created_at),
  constraint agent_transfer_decision_value_check check (decision in ('approve', 'deny')),
  constraint agent_transfer_decision_status_check check (status in ('pending', 'applied', 'failed')),
  constraint agent_transfer_decision_source_check check (source in ('web', 'telegram', 'system'))
);

create index if not exists idx_transfer_policy_mirror_agent_chain
  on agent_transfer_policy_mirror(agent_id, chain_key);

create index if not exists idx_transfer_approval_mirror_agent_chain_status
  on agent_transfer_approval_mirror(agent_id, chain_key, status, created_at desc);

create index if not exists idx_transfer_approval_mirror_agent_created
  on agent_transfer_approval_mirror(agent_id, created_at desc);

create index if not exists idx_transfer_decision_inbox_agent_chain_status
  on agent_transfer_decision_inbox(agent_id, chain_key, status, created_at desc);
