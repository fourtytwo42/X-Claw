type PgErrorLike = {
  code?: unknown;
  message?: unknown;
};

const TRANSFER_MIRROR_SCHEMA_MARKERS = [
  'agent_transfer_approval_mirror',
  'agent_transfer_policy_mirror',
  'policy_blocked_at_create',
  'policy_block_reason_code',
  'policy_block_reason_message',
  'execution_mode',
  'approval_source',
  'request_kind',
  'observed_by',
  'observation_source',
  'watcher_run_id'
];

export function isTransferMirrorSchemaUnavailableError(error: unknown): boolean {
  if (!error || typeof error !== 'object') {
    return false;
  }
  const code = String((error as PgErrorLike).code ?? '').trim();
  if (code === '42P01' || code === '42703') {
    return true;
  }
  const message = String((error as PgErrorLike).message ?? '');
  return TRANSFER_MIRROR_SCHEMA_MARKERS.some((marker) => message.includes(marker));
}

export function transferMirrorSchemaErrorDetails(error: unknown): { dbCode: string | null; dbMessage: string } {
  if (!error || typeof error !== 'object') {
    return {
      dbCode: null,
      dbMessage: String(error)
    };
  }
  const asPg = error as PgErrorLike;
  return {
    dbCode: String(asPg.code ?? '').trim() || null,
    dbMessage: String(asPg.message ?? 'unknown database error')
  };
}
