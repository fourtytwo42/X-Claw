create table if not exists agent_tracked_agents (
  tracking_id text primary key,
  agent_id text not null references agents(agent_id),
  tracked_agent_id text not null references agents(agent_id),
  created_by_management_session_id text references management_sessions(session_id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint agent_tracked_agents_not_self check (agent_id <> tracked_agent_id),
  unique (agent_id, tracked_agent_id)
);

create index if not exists idx_agent_tracked_agents_agent_created
  on agent_tracked_agents(agent_id, created_at desc);

create index if not exists idx_agent_tracked_agents_tracked_created
  on agent_tracked_agents(tracked_agent_id, created_at desc);
