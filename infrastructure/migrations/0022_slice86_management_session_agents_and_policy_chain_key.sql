create table if not exists management_session_agents (
  binding_id text primary key,
  session_id text not null references management_sessions(session_id) on delete cascade,
  agent_id text not null references agents(agent_id),
  created_at timestamptz not null default now(),
  unique (session_id, agent_id)
);

create index if not exists idx_management_session_agents_session
  on management_session_agents(session_id, created_at desc);

create index if not exists idx_management_session_agents_agent
  on management_session_agents(agent_id, created_at desc);

insert into management_session_agents (binding_id, session_id, agent_id, created_at)
select
  'msa_' || md5(ms.session_id || ':' || ms.agent_id),
  ms.session_id,
  ms.agent_id,
  coalesce(ms.created_at, now())
from management_sessions ms
on conflict (session_id, agent_id) do nothing;

alter table if exists agent_policy_snapshots
  add column if not exists chain_key varchar(64);

update agent_policy_snapshots
set chain_key = 'base_sepolia'
where chain_key is null;

alter table if exists agent_policy_snapshots
  alter column chain_key set default 'base_sepolia';

alter table if exists agent_policy_snapshots
  alter column chain_key set not null;

create index if not exists idx_agent_policy_snapshots_agent_chain_created
  on agent_policy_snapshots(agent_id, chain_key, created_at desc);
