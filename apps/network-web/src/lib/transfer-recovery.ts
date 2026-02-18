import { existsSync } from 'node:fs';
import { spawn } from 'node:child_process';

import { dbQuery } from '@/lib/db';

function resolveRuntimeBin(): string {
  const candidates = [
    process.env.XCLAW_AGENT_RUNTIME_BIN?.trim() ?? '',
    `${process.env.HOME ?? ''}/.local/bin/xclaw-agent`,
    `${process.env.HOME ?? ''}/.nvm/current/bin/xclaw-agent`,
    'xclaw-agent'
  ].filter((value) => value.length > 0);
  for (const candidate of candidates) {
    if (candidate === 'xclaw-agent' || existsSync(candidate)) {
      return candidate;
    }
  }
  return 'xclaw-agent';
}

function staleExecutingThresholdSec(): number {
  const raw = (process.env.XCLAW_TRANSFER_EXECUTING_STALE_SEC ?? '').trim();
  if (!/^\d+$/.test(raw)) {
    return 45;
  }
  const parsed = Number.parseInt(raw, 10);
  if (!Number.isFinite(parsed) || parsed < 1) {
    return 45;
  }
  return parsed;
}

export async function kickStaleTransferRecovery(agentId: string, chainKey: string): Promise<number> {
  const staleSec = staleExecutingThresholdSec();
  const stale = await dbQuery<{ approval_id: string }>(
    `
    select approval_id
    from agent_transfer_approval_mirror
    where agent_id = $1
      and chain_key = $2
      and status = 'executing'
      and tx_hash is null
      and updated_at < now() - make_interval(secs => $3::int)
    order by updated_at asc
    limit 3
    `,
    [agentId, chainKey, staleSec]
  );
  if ((stale.rowCount ?? 0) === 0) {
    return 0;
  }

  const runtimeBin = resolveRuntimeBin();
  for (const row of stale.rows) {
    try {
      const child = spawn(
        runtimeBin,
        ['approvals', 'resume-transfer', '--approval-id', row.approval_id, '--chain', chainKey, '--json'],
        {
          detached: true,
          stdio: 'ignore',
          env: process.env
        }
      );
      child.unref();
    } catch {}
  }
  return stale.rows.length;
}

