import type { PoolClient } from 'pg';

export type EffectiveTradeCaps = {
  approvalMode: 'per_trade' | 'auto';
  maxTradeUsd: string | null;
  maxDailyUsd: string | null;
  allowedTokens: string[];
  dailyCapUsdEnabled: boolean;
  dailyTradeCapEnabled: boolean;
  maxDailyTradeCount: number | null;
  createdAt: string;
};

export type DailyTradeUsage = {
  utcDay: string;
  dailySpendUsd: string;
  dailyFilledTrades: number;
};

export type TradeCapViolation = {
  code: 'daily_usd_cap_exceeded' | 'daily_trade_count_cap_exceeded' | 'policy_denied';
  message: string;
  actionHint: string;
  details: Record<string, unknown>;
};

function utcDayNow(): string {
  return new Date().toISOString().slice(0, 10);
}

function asNonNegativeNumber(raw: string | null | undefined): number {
  if (!raw) {
    return 0;
  }
  const parsed = Number(raw);
  if (!Number.isFinite(parsed) || parsed < 0) {
    return 0;
  }
  return parsed;
}

export async function readLatestTradeCaps(client: PoolClient, agentId: string, chainKey: string): Promise<EffectiveTradeCaps | null> {
  const row = await client.query<{
    approval_mode: 'per_trade' | 'auto';
    max_trade_usd: string | null;
    max_daily_usd: string | null;
    allowed_tokens: unknown;
    daily_cap_usd_enabled: boolean;
    daily_trade_cap_enabled: boolean;
    max_daily_trade_count: string | null;
    created_at: string;
  }>(
    `
    select
      approval_mode,
      max_trade_usd::text,
      max_daily_usd::text,
      allowed_tokens,
      daily_cap_usd_enabled,
      daily_trade_cap_enabled,
      max_daily_trade_count::text,
      created_at::text
    from agent_policy_snapshots
    where agent_id = $1
      and chain_key = $2
    order by created_at desc
    limit 1
    `,
    [agentId, chainKey]
  );

  if ((row.rowCount ?? 0) === 0) {
    return null;
  }

  const payload = row.rows[0];
  const allowedTokens = Array.isArray(payload.allowed_tokens)
    ? payload.allowed_tokens.map((value) => String(value).trim()).filter((value) => value.length > 0)
    : [];

  const maxDailyTradeCount = payload.max_daily_trade_count === null ? null : Number.parseInt(payload.max_daily_trade_count, 10);

  return {
    approvalMode: payload.approval_mode,
    maxTradeUsd: payload.max_trade_usd,
    maxDailyUsd: payload.max_daily_usd,
    allowedTokens,
    dailyCapUsdEnabled: payload.daily_cap_usd_enabled,
    dailyTradeCapEnabled: payload.daily_trade_cap_enabled,
    maxDailyTradeCount: Number.isInteger(maxDailyTradeCount) && (maxDailyTradeCount ?? -1) >= 0 ? maxDailyTradeCount : null,
    createdAt: payload.created_at
  };
}

export async function readDailyTradeUsage(client: PoolClient, agentId: string, chainKey: string, utcDay?: string): Promise<DailyTradeUsage> {
  const day = utcDay ?? utcDayNow();
  const row = await client.query<{
    daily_spend_usd: string;
    daily_filled_trades: string;
  }>(
    `
    select daily_spend_usd::text, daily_filled_trades::text
    from agent_daily_trade_usage
    where agent_id = $1
      and chain_key = $2
      and utc_day = $3::date
    limit 1
    `,
    [agentId, chainKey, day]
  );

  if ((row.rowCount ?? 0) === 0) {
    return {
      utcDay: day,
      dailySpendUsd: '0',
      dailyFilledTrades: 0
    };
  }

  return {
    utcDay: day,
    dailySpendUsd: row.rows[0].daily_spend_usd ?? '0',
    dailyFilledTrades: Number.parseInt(row.rows[0].daily_filled_trades ?? '0', 10)
  };
}

export async function evaluateTradeCaps(
  client: PoolClient,
  input: {
    agentId: string;
    chainKey: string;
    projectedSpendUsd: string;
    projectedFilledTrades: number;
    utcDay?: string;
  }
): Promise<{ ok: true; caps: EffectiveTradeCaps; usage: DailyTradeUsage } | { ok: false; violation: TradeCapViolation }> {
  const caps = await readLatestTradeCaps(client, input.agentId, input.chainKey);
  if (!caps) {
    return {
      ok: false,
      violation: {
        code: 'policy_denied',
        message: 'Trade is blocked because no active policy snapshot exists for this agent.',
        actionHint: 'Save policy settings from the management page, then retry.',
        details: { agentId: input.agentId, chainKey: input.chainKey }
      }
    };
  }

  const usage = await readDailyTradeUsage(client, input.agentId, input.chainKey, input.utcDay);

  const projectedSpend = asNonNegativeNumber(input.projectedSpendUsd);
  const currentSpend = asNonNegativeNumber(usage.dailySpendUsd);

  if (caps.dailyCapUsdEnabled) {
    const maxDailyUsd = asNonNegativeNumber(caps.maxDailyUsd);
    if (maxDailyUsd > 0 && currentSpend + projectedSpend > maxDailyUsd) {
      return {
        ok: false,
        violation: {
          code: 'daily_usd_cap_exceeded',
          message: 'Trade is blocked because daily USD cap would be exceeded.',
          actionHint: 'Reduce trade amount, disable the cap, or raise maxDailyUsd in management policy.',
          details: {
            chainKey: input.chainKey,
            utcDay: usage.utcDay,
            currentSpendUsd: String(currentSpend),
            projectedSpendUsd: String(projectedSpend),
            maxDailyUsd: String(maxDailyUsd),
            dailyCapUsdEnabled: true
          }
        }
      };
    }
  }

  if (caps.dailyTradeCapEnabled && caps.maxDailyTradeCount !== null) {
    const currentTrades = usage.dailyFilledTrades;
    const projectedTrades = Math.max(0, Math.trunc(input.projectedFilledTrades));
    if (currentTrades + projectedTrades > caps.maxDailyTradeCount) {
      return {
        ok: false,
        violation: {
          code: 'daily_trade_count_cap_exceeded',
          message: 'Trade is blocked because daily filled-trade cap would be exceeded.',
          actionHint: 'Wait for next UTC day, disable cap, or raise maxDailyTradeCount in management policy.',
          details: {
            chainKey: input.chainKey,
            utcDay: usage.utcDay,
            currentFilledTrades: currentTrades,
            projectedFilledTrades: projectedTrades,
            maxDailyTradeCount: caps.maxDailyTradeCount,
            dailyTradeCapEnabled: true
          }
        }
      };
    }
  }

  return { ok: true, caps, usage };
}
