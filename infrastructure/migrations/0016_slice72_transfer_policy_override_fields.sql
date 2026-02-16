alter table if exists agent_transfer_approval_mirror
  add column if not exists policy_blocked_at_create boolean not null default false,
  add column if not exists policy_block_reason_code varchar(64),
  add column if not exists policy_block_reason_message text,
  add column if not exists execution_mode varchar(32);

alter table if exists agent_transfer_approval_mirror
  drop constraint if exists agent_transfer_approval_execution_mode_check;

alter table if exists agent_transfer_approval_mirror
  add constraint agent_transfer_approval_execution_mode_check
  check (execution_mode is null or execution_mode in ('normal', 'policy_override'));
