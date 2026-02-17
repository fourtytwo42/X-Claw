create table if not exists agent_x402_payment_mirror (
  payment_id text primary key,
  agent_id text not null references agents(agent_id),
  direction varchar(16) not null,
  status varchar(32) not null,
  network_key varchar(64) not null,
  facilitator_key varchar(64) not null,
  asset_kind varchar(16) not null,
  asset_address varchar(128),
  asset_symbol varchar(64),
  amount_atomic numeric not null,
  payment_url text,
  link_token text,
  approval_id text,
  tx_hash varchar(128),
  reason_code varchar(64),
  reason_message text,
  expires_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  terminal_at timestamptz,
  constraint agent_x402_payment_direction_check check (direction in ('inbound', 'outbound')),
  constraint agent_x402_payment_status_check check (status in ('proposed', 'approval_pending', 'approved', 'executing', 'filled', 'failed', 'rejected', 'expired')),
  constraint agent_x402_payment_asset_kind_check check (asset_kind in ('native', 'erc20'))
);

create index if not exists idx_x402_payment_mirror_agent_created
  on agent_x402_payment_mirror(agent_id, created_at desc);

create index if not exists idx_x402_payment_mirror_agent_direction_status_created
  on agent_x402_payment_mirror(agent_id, direction, status, created_at desc);

create index if not exists idx_x402_payment_mirror_approval_id
  on agent_x402_payment_mirror(approval_id)
  where approval_id is not null;

create index if not exists idx_x402_payment_mirror_tx_hash
  on agent_x402_payment_mirror(tx_hash)
  where tx_hash is not null;

create unique index if not exists uq_x402_payment_mirror_agent_link_token
  on agent_x402_payment_mirror(agent_id, link_token)
  where link_token is not null;

alter table if exists agent_transfer_approval_mirror
  add column if not exists approval_source varchar(16) not null default 'transfer',
  add column if not exists x402_url text,
  add column if not exists x402_network_key varchar(64),
  add column if not exists x402_facilitator_key varchar(64),
  add column if not exists x402_asset_kind varchar(16),
  add column if not exists x402_asset_address varchar(128),
  add column if not exists x402_amount_atomic numeric,
  add column if not exists x402_payment_id text;

alter table if exists agent_transfer_approval_mirror
  drop constraint if exists agent_transfer_approval_source_check;

alter table if exists agent_transfer_approval_mirror
  add constraint agent_transfer_approval_source_check
  check (approval_source in ('transfer', 'x402'));

alter table if exists agent_transfer_approval_mirror
  drop constraint if exists agent_transfer_approval_x402_asset_kind_check;

alter table if exists agent_transfer_approval_mirror
  add constraint agent_transfer_approval_x402_asset_kind_check
  check (x402_asset_kind is null or x402_asset_kind in ('native', 'erc20'));
