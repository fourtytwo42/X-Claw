export type AgentApiKeyMap = Record<string, string>;

export type AppEnv = {
  databaseUrl: string;
  redisUrl: string;
  agentApiKeys: AgentApiKeyMap;
  agentTokenSigningKey: string | null;
  idempotencyTtlSec: number;
  managementTokenEncKey: string | null;
  opsAlertWebhookUrl: string | null;
  opsAlertWebhookTimeoutMs: number;
};

let cachedEnv: AppEnv | null = null;

function parseAgentApiKeys(raw: string | undefined): AgentApiKeyMap {
  if (!raw) {
    return {};
  }

  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    throw new Error('Invalid JSON in XCLAW_AGENT_API_KEYS');
  }

  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
    throw new Error('XCLAW_AGENT_API_KEYS must be a JSON object mapping agentId to apiKey');
  }

  const entries = Object.entries(parsed as Record<string, unknown>);
  const map: AgentApiKeyMap = {};
  for (const [agentId, token] of entries) {
    if (!agentId || typeof token !== 'string' || token.length < 8) {
      throw new Error('XCLAW_AGENT_API_KEYS contains invalid mapping values');
    }
    map[agentId] = token;
  }

  return map;
}

function parsePositiveInt(raw: string | undefined, fallback: number): number {
  if (!raw) {
    return fallback;
  }

  const parsed = Number(raw);
  if (!Number.isInteger(parsed) || parsed <= 0) {
    throw new Error('XCLAW_IDEMPOTENCY_TTL_SEC must be a positive integer when provided');
  }
  return parsed;
}

function parseTimeoutMs(raw: string | undefined, fallback: number): number {
  if (!raw) {
    return fallback;
  }

  const parsed = Number(raw);
  if (!Number.isInteger(parsed) || parsed < 500 || parsed > 30000) {
    throw new Error('XCLAW_OPS_ALERT_WEBHOOK_TIMEOUT_MS must be an integer between 500 and 30000');
  }
  return parsed;
}

export function getEnv(): AppEnv {
  if (cachedEnv) {
    return cachedEnv;
  }

  const databaseUrl = process.env.DATABASE_URL;
  if (!databaseUrl) {
    throw new Error('Missing required env: DATABASE_URL');
  }

  const redisUrl = process.env.REDIS_URL;
  if (!redisUrl) {
    throw new Error('Missing required env: REDIS_URL');
  }

  cachedEnv = {
    databaseUrl,
    redisUrl,
    agentApiKeys: parseAgentApiKeys(process.env.XCLAW_AGENT_API_KEYS),
    agentTokenSigningKey: process.env.XCLAW_AGENT_TOKEN_SIGNING_KEY ?? null,
    idempotencyTtlSec: parsePositiveInt(process.env.XCLAW_IDEMPOTENCY_TTL_SEC, 24 * 60 * 60),
    managementTokenEncKey: process.env.XCLAW_MANAGEMENT_TOKEN_ENC_KEY ?? null,
    opsAlertWebhookUrl: process.env.XCLAW_OPS_ALERT_WEBHOOK_URL ?? null,
    opsAlertWebhookTimeoutMs: parseTimeoutMs(process.env.XCLAW_OPS_ALERT_WEBHOOK_TIMEOUT_MS, 3000)
  };

  return cachedEnv;
}

export function requireManagementTokenEncKey(): string {
  const raw = getEnv().managementTokenEncKey;
  if (!raw) {
    throw new Error('Missing required env: XCLAW_MANAGEMENT_TOKEN_ENC_KEY');
  }

  let decoded: Buffer;
  try {
    decoded = Buffer.from(raw, 'base64');
  } catch {
    throw new Error('XCLAW_MANAGEMENT_TOKEN_ENC_KEY must be valid base64');
  }

  if (decoded.length !== 32) {
    throw new Error('XCLAW_MANAGEMENT_TOKEN_ENC_KEY must decode to exactly 32 bytes');
  }

  return raw;
}
