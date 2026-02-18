create table if not exists chain_token_metadata_cache (
  chain_key text not null,
  token_address text not null,
  symbol text null,
  name text null,
  decimals int null,
  last_resolved_at timestamptz not null,
  resolve_status text not null check (resolve_status in ('ok', 'rpc_error', 'non_erc20', 'invalid')),
  resolve_error text null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (chain_key, token_address)
);

create index if not exists idx_chain_token_metadata_cache_chain_resolved
  on chain_token_metadata_cache(chain_key, last_resolved_at desc);
