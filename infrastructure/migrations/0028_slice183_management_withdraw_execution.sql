alter table if exists agent_transfer_decision_inbox
  add column if not exists decision_payload jsonb;

do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conname = 'agent_transfer_decision_payload_check'
  ) then
    alter table agent_transfer_decision_inbox
      add constraint agent_transfer_decision_payload_check
      check (
        decision_payload is null
        or (
          jsonb_typeof(decision_payload) = 'object'
          and decision_payload ? 'kind'
          and decision_payload->>'kind' = 'management_withdraw_v1'
          and decision_payload ? 'chainKey'
          and length(coalesce(decision_payload->>'chainKey', '')) > 0
          and decision_payload ? 'transferType'
          and decision_payload->>'transferType' in ('native', 'token')
          and decision_payload ? 'toAddress'
          and length(coalesce(decision_payload->>'toAddress', '')) > 0
          and decision_payload ? 'amountWei'
          and coalesce(decision_payload->>'amountWei', '') ~ '^[0-9]+$'
          and decision_payload ? 'tokenAddress'
          and decision_payload ? 'tokenSymbol'
          and decision_payload ? 'tokenDecimals'
        )
      );
  end if;
end $$;

create index if not exists idx_transfer_decision_inbox_payload_pending
  on agent_transfer_decision_inbox(agent_id, chain_key, status, created_at desc)
  where decision_payload is not null and status = 'pending';
