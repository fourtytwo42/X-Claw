alter table if exists agent_x402_payment_mirror
  drop constraint if exists agent_x402_payment_asset_kind_check;

alter table if exists agent_x402_payment_mirror
  add constraint agent_x402_payment_asset_kind_check
  check (asset_kind in ('native', 'erc20', 'token'));

alter table if exists agent_transfer_approval_mirror
  drop constraint if exists agent_transfer_approval_x402_asset_kind_check;

alter table if exists agent_transfer_approval_mirror
  add constraint agent_transfer_approval_x402_asset_kind_check
  check (x402_asset_kind is null or x402_asset_kind in ('native', 'erc20', 'token'));
