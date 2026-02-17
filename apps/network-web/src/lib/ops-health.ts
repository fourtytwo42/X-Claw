import fs from 'node:fs';
import path from 'node:path';

import { dbQuery } from '@/lib/db';
import { getRedisClient } from '@/lib/redis';

export type HealthLevel = 'healthy' | 'degraded' | 'offline';

export type HealthDependency = {
  name: 'api' | 'db' | 'redis';
  status: HealthLevel;
  latencyMs: number | null;
  checkedAtUtc: string;
  detail?: string;
};

export type ProviderHealth = {
  chainKey: string;
  provider: 'primary' | 'fallback';
  status: 'healthy' | 'degraded';
  latencyMs: number | null;
  checkedAtUtc: string;
  detail?: string;
};

export type StatusSnapshot = {
  overallStatus: 'healthy' | 'degraded' | 'offline';
  generatedAtUtc: string;
  dependencies: HealthDependency[];
  providers: ProviderHealth[];
  heartbeat: {
    totalAgents: number;
    activeAgents: number;
    offlineAgents: number;
    degradedAgents: number;
    heartbeatMisses: number;
  };
  queues: {
    copyIntentPending: number;
    approvalPendingTrades: number;
    totalDepth: number;
  };
};

type ChainConfig = {
  chainKey: string;
  rpc?: {
    primary?: string | null;
    fallback?: string | null;
  };
};

const HEARTBEAT_MISS_THRESHOLD_SECONDS = 180;
const STATUS_PROVIDER_CHAIN_KEYS = new Set(['base_sepolia', 'kite_ai_testnet']);

function nowIso(): string {
  return new Date().toISOString();
}

async function checkDb(): Promise<HealthDependency> {
  const checkedAtUtc = nowIso();
  const started = Date.now();

  try {
    await dbQuery('select 1');
    // Ensure schema migrations have been applied for core features. This makes
    // missing-table failures diagnosable from /api/v1/health without log access.
    const chat = await dbQuery<{ chat: string | null }>("select to_regclass('public.chat_room_messages')::text as chat");
    if (!chat.rows[0]?.chat) {
      return {
        name: 'db',
        status: 'degraded',
        latencyMs: Date.now() - started,
        checkedAtUtc,
        detail: "Database reachable, but schema is missing chat_room_messages. Run 'npm run db:migrate'."
      };
    }
    return {
      name: 'db',
      status: 'healthy',
      latencyMs: Date.now() - started,
      checkedAtUtc
    };
  } catch {
    return {
      name: 'db',
      status: 'offline',
      latencyMs: null,
      checkedAtUtc,
      detail: 'Database query failed.'
    };
  }
}

async function checkRedis(): Promise<HealthDependency> {
  const checkedAtUtc = nowIso();
  const started = Date.now();

  try {
    const redis = await getRedisClient();
    await redis.ping();
    return {
      name: 'redis',
      status: 'healthy',
      latencyMs: Date.now() - started,
      checkedAtUtc
    };
  } catch {
    return {
      name: 'redis',
      status: 'offline',
      latencyMs: null,
      checkedAtUtc,
      detail: 'Redis ping failed.'
    };
  }
}

function checkApi(): HealthDependency {
  return {
    name: 'api',
    status: 'healthy',
    latencyMs: 0,
    checkedAtUtc: nowIso()
  };
}

function readChainConfigs(): ChainConfig[] {
  const root = process.cwd();
  const dir = path.join(root, 'config', 'chains');

  try {
    const files = fs.readdirSync(dir).filter((file) => file.endsWith('.json')).sort();
    return files
      .map((file) => {
        const raw = fs.readFileSync(path.join(dir, file), 'utf8');
        return JSON.parse(raw) as ChainConfig;
      })
      .filter((cfg) => typeof cfg.chainKey === 'string' && cfg.chainKey.length > 0);
  } catch {
    return [];
  }
}

async function pingRpcProvider(chainKey: string, provider: 'primary' | 'fallback', url: string): Promise<ProviderHealth> {
  const checkedAtUtc = nowIso();
  const started = Date.now();
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 2500);

  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ jsonrpc: '2.0', id: 1, method: 'eth_chainId', params: [] }),
      signal: controller.signal
    });

    if (!res.ok) {
      return {
        chainKey,
        provider,
        status: 'degraded',
        latencyMs: null,
        checkedAtUtc,
        detail: `RPC probe failed with HTTP ${res.status}.`
      };
    }

    const parsed = (await res.json().catch(() => null)) as { result?: string } | null;
    if (!parsed?.result || typeof parsed.result !== 'string') {
      return {
        chainKey,
        provider,
        status: 'degraded',
        latencyMs: null,
        checkedAtUtc,
        detail: 'RPC probe response missing chainId.'
      };
    }

    return {
      chainKey,
      provider,
      status: 'healthy',
      latencyMs: Date.now() - started,
      checkedAtUtc
    };
  } catch {
    return {
      chainKey,
      provider,
      status: 'degraded',
      latencyMs: null,
      checkedAtUtc,
      detail: 'RPC probe request failed.'
    };
  } finally {
    clearTimeout(timer);
  }
}

async function checkProviders(): Promise<ProviderHealth[]> {
  const configs = readChainConfigs().filter((cfg) => STATUS_PROVIDER_CHAIN_KEYS.has(cfg.chainKey));
  const probes: Array<Promise<ProviderHealth>> = [];

  for (const cfg of configs) {
    const primary = cfg.rpc?.primary;
    const fallback = cfg.rpc?.fallback;

    if (primary && typeof primary === 'string') {
      probes.push(pingRpcProvider(cfg.chainKey, 'primary', primary));
    }

    if (fallback && typeof fallback === 'string') {
      probes.push(pingRpcProvider(cfg.chainKey, 'fallback', fallback));
    }
  }

  if (probes.length === 0) {
    return [];
  }

  return Promise.all(probes);
}

async function readHeartbeatSummary(): Promise<StatusSnapshot['heartbeat']> {
  try {
    const rows = await dbQuery<{
      total_agents: string;
      active_agents: string;
      offline_agents: string;
      degraded_agents: string;
      heartbeat_misses: string;
    }>(
      `
      with last_heartbeat as (
        select agent_id, max(created_at) as last_heartbeat_at
        from agent_events
        where event_type = 'heartbeat'
        group by agent_id
      )
      select
        count(*)::text as total_agents,
        count(*) filter (where a.public_status = 'active')::text as active_agents,
        count(*) filter (where a.public_status = 'offline')::text as offline_agents,
        count(*) filter (where a.public_status = 'degraded')::text as degraded_agents,
        count(*) filter (
          where lh.last_heartbeat_at is null
             or lh.last_heartbeat_at < now() - ($1::int * interval '1 second')
        )::text as heartbeat_misses
      from agents a
      left join last_heartbeat lh on lh.agent_id = a.agent_id
      `,
      [HEARTBEAT_MISS_THRESHOLD_SECONDS]
    );

    const row = rows.rows[0];
    return {
      totalAgents: Number(row?.total_agents ?? '0'),
      activeAgents: Number(row?.active_agents ?? '0'),
      offlineAgents: Number(row?.offline_agents ?? '0'),
      degradedAgents: Number(row?.degraded_agents ?? '0'),
      heartbeatMisses: Number(row?.heartbeat_misses ?? '0')
    };
  } catch {
    return {
      totalAgents: 0,
      activeAgents: 0,
      offlineAgents: 0,
      degradedAgents: 0,
      heartbeatMisses: 0
    };
  }
}

async function readQueueDepth(): Promise<StatusSnapshot['queues']> {
  try {
    const pendingIntents = await dbQuery<{ total: string }>(
      `
      select count(*)::text as total
      from copy_intents
      where status = 'pending'
      `
    );

    const pendingApprovals = await dbQuery<{ total: string }>(
      `
      select count(*)::text as total
      from trades
      where status = 'approval_pending'
      `
    );

    const copyIntentPending = Number(pendingIntents.rows[0]?.total ?? '0');
    const approvalPendingTrades = Number(pendingApprovals.rows[0]?.total ?? '0');

    return {
      copyIntentPending,
      approvalPendingTrades,
      totalDepth: copyIntentPending + approvalPendingTrades
    };
  } catch {
    return {
      copyIntentPending: 0,
      approvalPendingTrades: 0,
      totalDepth: 0
    };
  }
}

export async function getHealthSnapshot(): Promise<Pick<StatusSnapshot, 'overallStatus' | 'generatedAtUtc' | 'dependencies'>> {
  const [db, redis] = await Promise.all([checkDb(), checkRedis()]);
  const dependencies = [checkApi(), db, redis];

  const overallStatus: StatusSnapshot['overallStatus'] = dependencies.some((dep) => dep.status === 'offline') ? 'offline' : 'healthy';

  return {
    overallStatus,
    generatedAtUtc: nowIso(),
    dependencies
  };
}

export async function getStatusSnapshot(): Promise<StatusSnapshot> {
  const [health, providers, heartbeat, queues] = await Promise.all([
    getHealthSnapshot(),
    checkProviders(),
    readHeartbeatSummary(),
    readQueueDepth()
  ]);

  const providerUnhealthy = providers.filter((provider) => provider.status !== 'healthy').length;

  let overallStatus: StatusSnapshot['overallStatus'] = health.overallStatus;
  if (overallStatus !== 'offline') {
    if (providerUnhealthy > 0) {
      overallStatus = 'degraded';
    }
  }

  return {
    overallStatus,
    generatedAtUtc: nowIso(),
    dependencies: health.dependencies,
    providers,
    heartbeat,
    queues
  };
}
