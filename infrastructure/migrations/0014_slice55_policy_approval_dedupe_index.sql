-- Slice 55: Policy Approval De-Dupe (Reuse Pending Request)

-- Support fast lookup for existing pending requests by (agent, chain, type, token).
create index if not exists agent_policy_approval_requests_dedupe_lookup_idx
  on agent_policy_approval_requests (agent_id, chain_key, request_type, token_address, status, created_at desc);

