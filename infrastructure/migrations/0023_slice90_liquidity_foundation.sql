-- Slice 90: Liquidity + multi-DEX compatibility foundation

create table if not exists liquidity_intents (
  liquidity_intent_id varchar(26) primary key,
  agent_id varchar(26) not null references agents(agent_id) on delete cascade,
  chain_key varchar(64) not null,
  dex_key varchar(64) not null,
  action_type varchar(16) not null check (action_type in ('add', 'remove')),
  position_type varchar(16) not null check (position_type in ('v2', 'v3')),
  status varchar(32) not null check (
    status in (
      'proposed',
      'approval_pending',
      'approved',
      'rejected',
      'executing',
      'verifying',
      'filled',
      'failed',
      'expired',
      'verification_timeout'
    )
  ),
  token_a varchar(128),
  token_b varchar(128),
  amount_a numeric,
  amount_b numeric,
  amount_out numeric,
  slippage_bps int,
  position_ref varchar(128),
  reason_code varchar(64),
  reason_message text,
  tx_hash varchar(96),
  details jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_liquidity_intents_agent_chain_created
  on liquidity_intents(agent_id, chain_key, created_at desc);

create index if not exists idx_liquidity_intents_agent_chain_status
  on liquidity_intents(agent_id, chain_key, status, created_at desc);

create unique index if not exists uq_liquidity_intents_pending_dedupe
  on liquidity_intents(agent_id, chain_key, dex_key, action_type, token_a, token_b, amount_a, amount_b, slippage_bps)
  where status = 'approval_pending';

create table if not exists liquidity_position_snapshots (
  snapshot_id varchar(26) primary key,
  agent_id varchar(26) not null references agents(agent_id) on delete cascade,
  chain_key varchar(64) not null,
  dex_key varchar(64) not null,
  position_id varchar(128) not null,
  position_type varchar(16) not null check (position_type in ('v2', 'v3')),
  pool_ref varchar(256) not null,
  token_a varchar(128) not null,
  token_b varchar(128) not null,
  deposited_a numeric not null default 0,
  deposited_b numeric not null default 0,
  current_a numeric not null default 0,
  current_b numeric not null default 0,
  unclaimed_fees_a numeric not null default 0,
  unclaimed_fees_b numeric not null default 0,
  realized_fees_usd numeric not null default 0,
  unrealized_pnl_usd numeric not null default 0,
  position_value_usd numeric,
  status varchar(32) not null default 'active' check (status in ('active', 'closed', 'paused', 'deactivated')),
  explorer_url text,
  last_synced_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create unique index if not exists uq_liquidity_position_snapshots_agent_chain_position
  on liquidity_position_snapshots(agent_id, chain_key, position_id);

create index if not exists idx_liquidity_position_snapshots_agent_chain_updated
  on liquidity_position_snapshots(agent_id, chain_key, updated_at desc);

create table if not exists liquidity_fee_events (
  fee_event_id varchar(26) primary key,
  agent_id varchar(26) not null references agents(agent_id) on delete cascade,
  chain_key varchar(64) not null,
  dex_key varchar(64) not null,
  position_id varchar(128) not null,
  token varchar(128) not null,
  amount numeric not null,
  amount_usd numeric,
  tx_hash varchar(96),
  occurred_at timestamptz not null default now(),
  created_at timestamptz not null default now()
);

create index if not exists idx_liquidity_fee_events_agent_chain_occurred
  on liquidity_fee_events(agent_id, chain_key, occurred_at desc);

create table if not exists liquidity_protocol_configs (
  config_id varchar(26) primary key,
  chain_key varchar(64) not null,
  dex_key varchar(64) not null,
  protocol_family varchar(32) not null check (protocol_family in ('amm_v2', 'amm_v3', 'hedera_hts')),
  enabled boolean not null default true,
  config jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (chain_key, dex_key, protocol_family)
);
