create table if not exists agent_tracked_tokens (
  tracked_token_id text primary key,
  agent_id text not null references agents(agent_id) on delete cascade,
  chain_key text not null,
  token_address text not null,
  symbol text null,
  name text null,
  decimals int null,
  source text not null default 'runtime',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (agent_id, chain_key, token_address)
);

create index if not exists idx_agent_tracked_tokens_agent_chain_updated
  on agent_tracked_tokens(agent_id, chain_key, updated_at desc);
