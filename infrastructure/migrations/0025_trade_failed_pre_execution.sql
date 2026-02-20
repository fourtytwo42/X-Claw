alter table trades
drop constraint if exists trade_execution_id_check;

alter table trades
add constraint trade_execution_id_check
check (
  tx_hash is not null
  or mock_receipt_id is not null
  or status = any (
    array[
      'proposed'::trade_status,
      'approval_pending'::trade_status,
      'approved'::trade_status,
      'rejected'::trade_status,
      'expired'::trade_status,
      'failed'::trade_status
    ]
  )
);
