alter table if exists agent_x402_payment_mirror
  add column if not exists resource_description text;

