import { existsSync, readFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';
import { spawnSync } from 'node:child_process';

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
    return 10_000;
  }
  const parsed = Number.parseInt(raw, 10);
  if (!Number.isFinite(parsed) || parsed < 1_000) {
    return 10_000;
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
  return [
    '[X-CLAW WEB TRADE DECISION]',
    `Decision: ${String(input.decision || '').trim().toUpperCase()}`,
    `Trade: ${input.tradeId}`,
    `Chain: ${input.chainKey}`,
    `Source: ${input.source}`,
    `Reason: ${String(input.reasonMessage ?? '').trim() || 'n/a'}`
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
  return [
    '[X-CLAW WEB TRADE RESULT]',
    `Decision: ${String(input.status || '').trim().toUpperCase()}`,
    `Trade: ${input.tradeId}`,
    `Chain: ${input.chainKey}`,
    `TxHash: ${String(input.txHash ?? '').trim() || 'n/a'}`,
    `Source: ${input.source}`,
    `Reason: ${String(input.reasonMessage ?? '').trim() || 'n/a'}`
  ].join('\n');
}

export function buildWebTransferDecisionProdMessage(input: {
  decision: string;
  approvalId: string;
  chainKey: string;
  source: string;
  reasonMessage?: string | null;
}): string {
  return [
    '[X-CLAW WEB TRANSFER DECISION]',
    `Decision: ${String(input.decision || '').trim().toUpperCase()}`,
    `Approval: ${input.approvalId}`,
    `Chain: ${input.chainKey}`,
    `Source: ${input.source}`,
    `Reason: ${String(input.reasonMessage ?? '').trim() || 'n/a'}`
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
  return [
    '[X-CLAW WEB TRANSFER RESULT]',
    `Decision: ${String(input.status || '').trim().toUpperCase()}`,
    `Approval: ${input.approvalId}`,
    `Chain: ${input.chainKey}`,
    `TxHash: ${String(input.txHash ?? '').trim() || 'n/a'}`,
    `Source: ${input.source}`,
    `Reason: ${String(input.reasonMessage ?? '').trim() || 'n/a'}`
  ].join('\n');
}

export async function dispatchNonTelegramAgentProd(input: NonTelegramAgentProdInput): Promise<NonTelegramAgentProdDispatchResult> {
  if (!nonTelegramProdEnabled()) {
    return { attempted: false, skipped: true, reason: 'disabled' };
  }

  const message = String(input.message ?? '').trim();
  if (message.length === 0) {
    return { attempted: false, skipped: true, reason: 'empty_message' };
  }

  const delivery = readLatestDeliveryContext();
  if (!delivery) {
    return { attempted: false, skipped: true, reason: 'no_session' };
  }
  const allowTelegramLastChannel = input.allowTelegramLastChannel === true;
  if (delivery.lastChannel === 'telegram' && telegramGuardEnabled() && !allowTelegramLastChannel) {
    return { attempted: false, skipped: true, reason: 'telegram_guard' };
  }

  const openclawBin = resolveOpenclawBin();
  if (!openclawBin) {
    return { attempted: true, skipped: false, reason: 'openclaw_missing', exitStatus: null };
  }

  const agentId = sanitizeOpenclawAgentId(process.env.XCLAW_OPENCLAW_AGENT_ID);
  const child = spawnSync(openclawBin, ['agent', '--agent', agentId, '--channel', 'last', '--message', message, '--json'], {
    encoding: 'utf8',
    timeout: nonTelegramProdTimeoutMs()
  });

  const errorMessage = child.error ? summarize(child.error.message) : '';
  const stderrSummary = summarize(child.stderr);
  const stdoutSummary = summarize(child.stdout);
  const timeout = errorMessage.toLowerCase().includes('timed out') || errorMessage.toLowerCase().includes('etimedout');

  return {
    attempted: true,
    skipped: false,
    reason: timeout ? 'timeout' : child.error ? 'spawn_error' : undefined,
    exitStatus: child.status,
    stdoutSummary,
    stderrSummary: errorMessage || stderrSummary
  };
}
