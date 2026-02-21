import { existsSync } from 'node:fs';
import { spawn, spawnSync } from 'node:child_process';

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

function cleanupSweepIntervalSec(): number {
  const raw = (process.env.XCLAW_TRANSFER_PROMPT_CLEANUP_SWEEP_SEC ?? '').trim();
  if (!/^\d+$/.test(raw)) {
    return 30;
  }
  const parsed = Number.parseInt(raw, 10);
  if (!Number.isFinite(parsed) || parsed < 5) {
    return 30;
  }
  return parsed;
}

const CLEANUP_SWEEP_STATE: {
  running: boolean;
  lastRunMs: number;
  seen: Map<string, number>;
} = {
  running: false,
  lastRunMs: 0,
  seen: new Map<string, number>(),
};

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

export async function kickTerminalTransferPromptCleanup(agentId: string, chainKey: string): Promise<number> {
  const now = Date.now();
  const intervalMs = cleanupSweepIntervalSec() * 1000;
  if (CLEANUP_SWEEP_STATE.running || now - CLEANUP_SWEEP_STATE.lastRunMs < intervalMs) {
    return 0;
  }
  CLEANUP_SWEEP_STATE.running = true;
  CLEANUP_SWEEP_STATE.lastRunMs = now;
  try {
    const terminal = await dbQuery<{ approval_id: string; chain_key: string }>(
      `
      select approval_id, chain_key
      from agent_transfer_approval_mirror
      where agent_id = $1
        and chain_key = $2
        and status in ('failed', 'filled', 'rejected')
        and updated_at > now() - interval '1 day'
      order by updated_at desc
      limit 25
      `,
      [agentId, chainKey]
    );
    if ((terminal.rowCount ?? 0) === 0) {
      return 0;
    }
    const runtimeBin = resolveRuntimeBin();
    let dispatched = 0;
    for (const row of terminal.rows) {
      const cacheKey = `${agentId}:${row.chain_key}:${row.approval_id}`;
      const lastSeen = CLEANUP_SWEEP_STATE.seen.get(cacheKey) ?? 0;
      if (now - lastSeen < intervalMs) {
        continue;
      }
      CLEANUP_SWEEP_STATE.seen.set(cacheKey, now);
      try {
        const child = spawn(
          runtimeBin,
          ['approvals', 'clear-prompt', '--subject-type', 'transfer', '--subject-id', row.approval_id, '--chain', row.chain_key, '--json'],
          {
            detached: true,
            stdio: 'ignore',
            env: {
              ...process.env,
              XCLAW_AGENT_ID: agentId,
              XCLAW_DEFAULT_CHAIN: row.chain_key
            }
          }
        );
        child.unref();
        dispatched += 1;
      } catch {}
    }
    return dispatched;
  } finally {
    CLEANUP_SWEEP_STATE.running = false;
  }
}

export function invokeTransferPromptCleanupNow(input: {
  agentId: string;
  chainKey: string;
  approvalId: string;
}): { ok: boolean; code: string; runtimeExitStatus?: number | null; stderrSummary?: string; payload?: Record<string, unknown> } {
  const runtimeBin = resolveRuntimeBin();
  const runtimeArgs = [
    'approvals',
    'clear-prompt',
    '--subject-type',
    'transfer',
    '--subject-id',
    input.approvalId,
    '--chain',
    input.chainKey,
    '--json'
  ];
  const child = spawnSync(runtimeBin, runtimeArgs, {
    encoding: 'utf8',
    timeout: 2500,
    env: {
      ...process.env,
      XCLAW_AGENT_ID: input.agentId,
      XCLAW_DEFAULT_CHAIN: input.chainKey
    }
  });
  const stderr = String(child.stderr ?? '').trim();
  const stdout = String(child.stdout ?? '').trim();
  let payload: Record<string, unknown> | undefined;
  if (stdout.length > 0) {
    const lines = stdout.split(/\r?\n/).map((line) => line.trim()).filter((line) => line.length > 0);
    if (lines.length > 0) {
      try {
        const parsed = JSON.parse(lines[lines.length - 1]);
        if (parsed && typeof parsed === 'object') {
          payload = parsed as Record<string, unknown>;
        }
      } catch {}
    }
  }
  const ok = child.status === 0 && Boolean(payload?.ok);
  return {
    ok,
    code: ok ? 'runtime_cleanup_applied' : 'runtime_cleanup_failed',
    runtimeExitStatus: child.status,
    stderrSummary: stderr.slice(0, 500),
    payload
  };
}
