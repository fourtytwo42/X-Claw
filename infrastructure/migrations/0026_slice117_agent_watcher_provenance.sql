alter table if exists trades
  add column if not exists observed_by varchar(32),
  add column if not exists observation_source varchar(64),
  add column if not exists confirmation_count int,
  add column if not exists observed_at timestamptz,
  add column if not exists watcher_run_id varchar(128),
  add column if not exists comparator_mismatch boolean not null default false;

alter table if exists trades
  drop constraint if exists trades_observed_by_check;

alter table if exists trades
  add constraint trades_observed_by_check
  check (observed_by is null or observed_by in ('agent_watcher', 'legacy_server_poller'));

alter table if exists trades
  drop constraint if exists trades_observation_source_check;

alter table if exists trades
  add constraint trades_observation_source_check
  check (observation_source is null or observation_source in ('rpc_receipt', 'rpc_log', 'local_send_result', 'reorg_reconciliation'));

alter table if exists trades
  drop constraint if exists trades_confirmation_count_check;

alter table if exists trades
  add constraint trades_confirmation_count_check
  check (confirmation_count is null or confirmation_count >= 0);

alter table if exists agent_transfer_approval_mirror
  add column if not exists observed_by varchar(32),
  add column if not exists observation_source varchar(64),
  add column if not exists confirmation_count int,
  add column if not exists observed_at timestamptz,
  add column if not exists watcher_run_id varchar(128),
  add column if not exists comparator_mismatch boolean not null default false;

alter table if exists agent_transfer_approval_mirror
  drop constraint if exists agent_transfer_approval_observed_by_check;

alter table if exists agent_transfer_approval_mirror
  add constraint agent_transfer_approval_observed_by_check
  check (observed_by is null or observed_by in ('agent_watcher', 'legacy_server_poller'));

alter table if exists agent_transfer_approval_mirror
  drop constraint if exists agent_transfer_approval_observation_source_check;

alter table if exists agent_transfer_approval_mirror
  add constraint agent_transfer_approval_observation_source_check
  check (observation_source is null or observation_source in ('rpc_receipt', 'rpc_log', 'local_send_result', 'reorg_reconciliation'));

alter table if exists agent_transfer_approval_mirror
  drop constraint if exists agent_transfer_approval_confirmation_count_check;

alter table if exists agent_transfer_approval_mirror
  add constraint agent_transfer_approval_confirmation_count_check
  check (confirmation_count is null or confirmation_count >= 0);

alter table if exists wallet_balance_snapshots
  add column if not exists observed_by varchar(32),
  add column if not exists observation_source varchar(64),
  add column if not exists watcher_run_id varchar(128),
  add column if not exists comparator_mismatch boolean not null default false;

alter table if exists wallet_balance_snapshots
  drop constraint if exists wallet_balance_snapshots_observed_by_check;

alter table if exists wallet_balance_snapshots
  add constraint wallet_balance_snapshots_observed_by_check
  check (observed_by is null or observed_by in ('agent_watcher', 'legacy_server_poller'));

alter table if exists wallet_balance_snapshots
  drop constraint if exists wallet_balance_snapshots_observation_source_check;

alter table if exists wallet_balance_snapshots
  add constraint wallet_balance_snapshots_observation_source_check
  check (observation_source is null or observation_source in ('rpc_receipt', 'rpc_log', 'local_send_result', 'reorg_reconciliation'));

alter table if exists deposit_events
  add column if not exists observed_by varchar(32),
  add column if not exists observation_source varchar(64),
  add column if not exists watcher_run_id varchar(128),
  add column if not exists comparator_mismatch boolean not null default false;

alter table if exists deposit_events
  drop constraint if exists deposit_events_observed_by_check;

alter table if exists deposit_events
  add constraint deposit_events_observed_by_check
  check (observed_by is null or observed_by in ('agent_watcher', 'legacy_server_poller'));

alter table if exists deposit_events
  drop constraint if exists deposit_events_observation_source_check;

alter table if exists deposit_events
  add constraint deposit_events_observation_source_check
  check (observation_source is null or observation_source in ('rpc_receipt', 'rpc_log', 'local_send_result', 'reorg_reconciliation'));
