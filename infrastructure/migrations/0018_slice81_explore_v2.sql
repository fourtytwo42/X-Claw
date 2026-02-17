create table if not exists agent_explore_profile (
  agent_id text primary key references agents(agent_id),
  strategy_tags jsonb not null default '[]'::jsonb,
  venue_tags jsonb not null default '[]'::jsonb,
  risk_tier text not null,
  description_short varchar(180),
  updated_by_management_session_id text references management_sessions(session_id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint agent_explore_profile_risk_tier_check check (risk_tier in ('low', 'medium', 'high', 'very_high')),
  constraint agent_explore_profile_strategy_tags_array_check check (
    jsonb_typeof(strategy_tags) = 'array'
    and not exists (
      select 1
      from jsonb_array_elements(strategy_tags) as entry(value)
      where jsonb_typeof(entry.value) <> 'string'
        or entry.value <> to_jsonb(lower(trim(both '"' from entry.value::text)))
        or lower(trim(both '"' from entry.value::text)) !~ '^[a-z0-9_]+$'
    )
  ),
  constraint agent_explore_profile_venue_tags_array_check check (
    jsonb_typeof(venue_tags) = 'array'
    and not exists (
      select 1
      from jsonb_array_elements(venue_tags) as entry(value)
      where jsonb_typeof(entry.value) <> 'string'
        or entry.value <> to_jsonb(lower(trim(both '"' from entry.value::text)))
        or lower(trim(both '"' from entry.value::text)) !~ '^[a-z0-9_]+$'
    )
  )
);

create index if not exists idx_agent_explore_profile_strategy_tags_gin
  on agent_explore_profile using gin(strategy_tags);

create index if not exists idx_agent_explore_profile_venue_tags_gin
  on agent_explore_profile using gin(venue_tags);

create index if not exists idx_agent_explore_profile_risk_tier
  on agent_explore_profile(risk_tier);

create index if not exists idx_agent_explore_profile_updated_at_desc
  on agent_explore_profile(updated_at desc);
