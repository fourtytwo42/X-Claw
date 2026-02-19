import { existsSync, readFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';
import { spawn, spawnSync } from 'node:child_process';

type DeliveryContext = {
  lastChannel: string;
  lastTo: string;
  updatedAtMs: number;
};

export type NonTelegramAgentProdDispatchResult = {
  attempted: boolean;
  skipped: boolean;
  reason?: string;
  exitStatus?: number | null;
  stdoutSummary?: string;
  stderrSummary?: string;
};

type NonTelegramAgentProdInput = {
  message: string;
  allowTelegramLastChannel?: boolean;
};

const TRADE_TERMINAL_STATUSES = new Set(['filled', 'failed', 'rejected']);
const TRANSFER_TERMINAL_STATUSES = new Set(['filled', 'failed', 'rejected']);

function summarize(value: unknown): string {
  return String(value ?? '')
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, 1200);
}

function nonTelegramProdEnabled(): boolean {
  const raw = (process.env.XCLAW_NON_TG_PROD_ENABLED ?? '').trim().toLowerCase();
  if (!raw) {
    return true;
  }
  return raw !== '0' && raw !== 'false' && raw !== 'off' && raw !== 'no';
}

function nonTelegramProdTimeoutMs(): number {
  const raw = (process.env.XCLAW_NON_TG_PROD_TIMEOUT_MS ?? '').trim();
  if (!raw || !/^\d+$/.test(raw)) {
    return 25_000;
  }
  const parsed = Number.parseInt(raw, 10);
  if (!Number.isFinite(parsed) || parsed < 1_000) {
    return 25_000;
  }
  return parsed;
}

function telegramGuardEnabled(): boolean {
  const raw = (process.env.XCLAW_NON_TG_PROD_TELEGRAM_GUARD ?? '').trim().toLowerCase();
  if (!raw) {
    return true;
  }
  return raw !== '0' && raw !== 'false' && raw !== 'off' && raw !== 'no';
}

function sanitizeOpenclawAgentId(value: string | undefined): string {
  const raw = (value ?? '').trim() || 'main';
  if (/^[A-Za-z0-9_-]{1,64}$/.test(raw)) {
    return raw.toLowerCase();
  }
  return 'main';
}

function resolveOpenclawBin(): string | null {
  const envPath = (process.env.OPENCLAW_BIN ?? '').trim();
  if (envPath.length > 0 && existsSync(envPath)) {
    return envPath;
  }

  const whichResult = spawnSync('which', ['openclaw'], { encoding: 'utf8' });
  if (whichResult.status === 0) {
    const resolved = String(whichResult.stdout ?? '').trim();
    if (resolved.length > 0) {
      return resolved;
    }
  }

  for (const candidate of ['/usr/local/bin/openclaw', '/usr/bin/openclaw', join(homedir(), '.local', 'bin', 'openclaw')]) {
    if (existsSync(candidate)) {
      return candidate;
    }
  }
  return null;
}

type AsyncExecResult = {
  status: number | null;
  stdout: string;
  stderr: string;
  timedOut: boolean;
  errorMessage?: string;
};

function runCommandAsync(bin: string, args: string[], timeoutMs: number): Promise<AsyncExecResult> {
  return new Promise((resolve) => {
    let stdout = '';
    let stderr = '';
    let settled = false;
    let timedOut = false;
    let timeoutId: NodeJS.Timeout | null = null;

    const child = spawn(bin, args, {
      stdio: ['ignore', 'pipe', 'pipe']
    });

    child.stdout.on('data', (chunk) => {
      stdout += String(chunk);
    });
    child.stderr.on('data', (chunk) => {
      stderr += String(chunk);
    });

    const finish = (result: AsyncExecResult) => {
      if (settled) {
        return;
      }
      settled = true;
      if (timeoutId) {
        clearTimeout(timeoutId);
      }
      resolve(result);
    };

    timeoutId = setTimeout(() => {
      timedOut = true;
      try {
        child.kill('SIGKILL');
      } catch {}
    }, timeoutMs);

    child.on('error', (error) => {
      finish({
        status: null,
        stdout,
        stderr,
        timedOut,
        errorMessage: String(error.message || error)
      });
    });

    child.on('close', (code) => {
      finish({
        status: code,
        stdout,
        stderr,
        timedOut
      });
    });
  });
}

function readLatestDeliveryContext(): DeliveryContext | null {
  const agentId = sanitizeOpenclawAgentId(process.env.XCLAW_OPENCLAW_AGENT_ID);
  const stateDir = (process.env.OPENCLAW_STATE_DIR ?? '').trim() || join(homedir(), '.openclaw');
  const sessionsPath = join(stateDir, 'agents', agentId, 'sessions', 'sessions.json');
  if (!existsSync(sessionsPath)) {
    return null;
  }

  try {
    const raw = readFileSync(sessionsPath, 'utf8');
    const payload = JSON.parse(raw || '{}');
    if (!payload || typeof payload !== 'object') {
      return null;
    }

    let best: DeliveryContext | null = null;
    for (const entry of Object.values(payload as Record<string, unknown>)) {
      if (!entry || typeof entry !== 'object') {
        continue;
      }
      const row = entry as Record<string, unknown>;
      const lastChannel = String(row.lastChannel ?? '').trim().toLowerCase();
      const lastTo = String(row.lastTo ?? '').trim();
      if (!lastChannel || !lastTo) {
        continue;
      }
      const parsedUpdated = Number.parseInt(String(row.updatedAt ?? '0'), 10);
      const updatedAtMs = Number.isFinite(parsedUpdated) ? parsedUpdated : 0;
      if (!best || updatedAtMs >= best.updatedAtMs) {
        best = {
          lastChannel,
          lastTo,
          updatedAtMs
        };
      }
    }
    return best;
  } catch {
    return null;
  }
}

export function isTradeTerminalStatus(status: string): boolean {
  return TRADE_TERMINAL_STATUSES.has(String(status).trim().toLowerCase());
}

export function isTransferTerminalStatus(status: string): boolean {
  return TRANSFER_TERMINAL_STATUSES.has(String(status).trim().toLowerCase());
}

export function buildWebTradeDecisionProdMessage(input: {
  decision: string;
  tradeId: string;
  chainKey: string;
  source: string;
  reasonMessage?: string | null;
}): string {
  const decisionWord = String(input.decision || '').trim().toUpperCase();
  const instruction =
    decisionWord === 'APPROVE'
      ? `Immediately run trade-resume ${input.tradeId}, then reply to the user with progress.`
      : 'Reply to the user confirming the trade was rejected via web management.';
  return [
    '[X-CLAW WEB TRADE DECISION]',
    `Decision: ${decisionWord}`,
    `Trade: ${input.tradeId}`,
    `Chain: ${input.chainKey}`,
    `Source: ${input.source}`,
    `Reason: ${String(input.reasonMessage ?? '').trim() || 'n/a'}`,
    `Instruction: ${instruction}`
  ].join('\n');
}

export function buildWebTradeResultProdMessage(input: {
  status: string;
  tradeId: string;
  chainKey: string;
  txHash?: string | null;
  source: string;
  reasonMessage?: string | null;
}): string {
  const normalized = String(input.status || '').trim().toLowerCase();
  const instruction =
    normalized === 'filled'
      ? 'Reply to the user confirming the trade succeeded with tx details.'
      : normalized === 'rejected'
        ? 'Reply to the user confirming the trade was rejected and no execution occurred.'
        : 'Reply to the user confirming the trade failed and provide next steps.';
  return [
    '[X-CLAW WEB TRADE RESULT]',
    `Decision: ${String(input.status || '').trim().toUpperCase()}`,
    `Trade: ${input.tradeId}`,
    `Chain: ${input.chainKey}`,
    `TxHash: ${String(input.txHash ?? '').trim() || 'n/a'}`,
    `Source: ${input.source}`,
    `Reason: ${String(input.reasonMessage ?? '').trim() || 'n/a'}`,
    `Instruction: ${instruction}`
  ].join('\n');
}

export function buildWebTransferDecisionProdMessage(input: {
  decision: string;
  approvalId: string;
  chainKey: string;
  source: string;
  reasonMessage?: string | null;
}): string {
  const decisionWord = String(input.decision || '').trim().toUpperCase();
  const instruction =
    decisionWord === 'APPROVE'
      ? `Immediately run transfer-resume ${input.approvalId}, then reply to the user with progress.`
      : 'Reply to the user confirming the transfer was denied via web management.';
  return [
    '[X-CLAW WEB TRANSFER DECISION]',
    `Decision: ${decisionWord}`,
    `Approval: ${input.approvalId}`,
    `Chain: ${input.chainKey}`,
    `Source: ${input.source}`,
    `Reason: ${String(input.reasonMessage ?? '').trim() || 'n/a'}`,
    `Instruction: ${instruction}`
  ].join('\n');
}

export function buildWebTransferResultProdMessage(input: {
  status: string;
  approvalId: string;
  chainKey: string;
  txHash?: string | null;
  source: string;
  reasonMessage?: string | null;
}): string {
  const normalized = String(input.status || '').trim().toLowerCase();
  const instruction =
    normalized === 'filled'
      ? 'Reply to the user confirming the transfer succeeded with tx details.'
      : normalized === 'rejected'
        ? 'Reply to the user confirming the transfer was denied and no transaction was executed.'
        : 'Reply to the user confirming the transfer failed and provide next steps.';
  return [
    '[X-CLAW WEB TRANSFER RESULT]',
    `Decision: ${String(input.status || '').trim().toUpperCase()}`,
    `Approval: ${input.approvalId}`,
    `Chain: ${input.chainKey}`,
    `TxHash: ${String(input.txHash ?? '').trim() || 'n/a'}`,
    `Source: ${input.source}`,
    `Reason: ${String(input.reasonMessage ?? '').trim() || 'n/a'}`,
    `Instruction: ${instruction}`
  ].join('\n');
}

export async function dispatchNonTelegramAgentProd(input: NonTelegramAgentProdInput): Promise<NonTelegramAgentProdDispatchResult> {
  const head = String(input.message ?? '').split('\n')[0] ?? '';
  if (!nonTelegramProdEnabled()) {
    console.info('[non_tg_prod] skipped disabled', { head });
    return { attempted: false, skipped: true, reason: 'disabled' };
  }

  const message = String(input.message ?? '').trim();
  if (message.length === 0) {
    console.info('[non_tg_prod] skipped empty_message');
    return { attempted: false, skipped: true, reason: 'empty_message' };
  }

  const delivery = readLatestDeliveryContext();
  if (!delivery) {
    console.warn('[non_tg_prod] skipped no_session', { head });
    return { attempted: false, skipped: true, reason: 'no_session' };
  }
  const allowTelegramLastChannel = input.allowTelegramLastChannel === true;
  if (delivery.lastChannel === 'telegram' && telegramGuardEnabled() && !allowTelegramLastChannel) {
    console.info('[non_tg_prod] skipped telegram_guard', { head, lastTo: delivery.lastTo });
    return { attempted: false, skipped: true, reason: 'telegram_guard' };
  }

  const openclawBin = resolveOpenclawBin();
  if (!openclawBin) {
    console.error('[non_tg_prod] openclaw_missing', { head });
    return { attempted: true, skipped: false, reason: 'openclaw_missing', exitStatus: null };
  }

  const agentId = sanitizeOpenclawAgentId(process.env.XCLAW_OPENCLAW_AGENT_ID);
  const dispatchArgs = ['agent', '--agent', agentId, '--channel', 'last', '--message', message, '--deliver', '--json'];
  const runDispatch = (timeoutMs: number) => runCommandAsync(openclawBin, dispatchArgs, timeoutMs);
  const timeoutMs = nonTelegramProdTimeoutMs();
  let child = await runDispatch(timeoutMs);

  const errorMessage = summarize(child.errorMessage ?? '');
  const stderrSummary = summarize(child.stderr);
  const stdoutSummary = summarize(child.stdout);
  const timeout = child.timedOut || errorMessage.toLowerCase().includes('timed out') || errorMessage.toLowerCase().includes('etimedout');
  if (timeout) {
    const retryTimeoutMs = Math.min(60_000, timeoutMs * 2);
    console.warn('[non_tg_prod] retry_timeout', { head, timeoutMs, retryTimeoutMs });
    child = await runDispatch(retryTimeoutMs);
  }
  const finalErrorMessage = summarize(child.errorMessage ?? '');
  const finalStderrSummary = summarize(child.stderr);
  const finalStdoutSummary = summarize(child.stdout);
  const finalTimeout = child.timedOut || finalErrorMessage.toLowerCase().includes('timed out') || finalErrorMessage.toLowerCase().includes('etimedout');
  console.info('[non_tg_prod] dispatched', {
    head,
    allowTelegramLastChannel,
    lastChannel: delivery.lastChannel,
    lastTo: delivery.lastTo,
    exitStatus: child.status,
    timeout: finalTimeout,
    stderrSummary: (finalErrorMessage || finalStderrSummary).slice(0, 280)
  });

  return {
    attempted: true,
    skipped: false,
    reason: finalTimeout ? 'timeout' : child.errorMessage ? 'spawn_error' : undefined,
    exitStatus: child.status,
    stdoutSummary: finalStdoutSummary,
    stderrSummary: finalErrorMessage || finalStderrSummary
  };
}
