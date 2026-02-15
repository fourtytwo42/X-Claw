-- Slice 54: Agent Event Types For Policy Approval Requests

-- Postgres enum ALTER TYPE does not support IF NOT EXISTS on all versions, so use a guard.
do $$
begin
  if not exists (
    select 1
    from pg_enum e
    join pg_type t on t.oid = e.enumtypid
    where t.typname = 'agent_event_type' and e.enumlabel = 'policy_approval_pending'
  ) then
    alter type agent_event_type add value 'policy_approval_pending';
  end if;
end$$;

do $$
begin
  if not exists (
    select 1
    from pg_enum e
    join pg_type t on t.oid = e.enumtypid
    where t.typname = 'agent_event_type' and e.enumlabel = 'policy_approved'
  ) then
    alter type agent_event_type add value 'policy_approved';
  end if;
end$$;

do $$
begin
  if not exists (
    select 1
    from pg_enum e
    join pg_type t on t.oid = e.enumtypid
    where t.typname = 'agent_event_type' and e.enumlabel = 'policy_rejected'
  ) then
    alter type agent_event_type add value 'policy_rejected';
  end if;
end$$;

