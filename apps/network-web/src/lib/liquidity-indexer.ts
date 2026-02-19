import { dbQuery } from '@/lib/db';

const POLL_INTERVAL_MS = 60 * 1000;
const lastRunByAgentChain = new Map<string, number>();

function cacheKey(agentId: string, chainKey: string): string {
  return `${agentId}:${chainKey}`;
}

function parseNumeric(value: string | null | undefined): number {
  if (!value) {
    return 0;
  }
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    return 0;
  }
  return parsed;
}

function formatNumeric(value: number): string {
  if (!Number.isFinite(value)) {
    return '0';
  }
  return Number.isInteger(value) ? `${value}` : value.toFixed(8).replace(/\.0+$/, '').replace(/(\.\d*?)0+$/, '$1');
}

export async function maybeSyncLiquiditySnapshots(
  agentId: string,
  chainKey: string,
  opts: { force?: boolean } = {}
): Promise<{ ran: boolean; updated: number }> {
  const key = cacheKey(agentId, chainKey);
  const now = Date.now();
  const lastRun = lastRunByAgentChain.get(key) ?? 0;
  if (!opts.force && now - lastRun < POLL_INTERVAL_MS) {
    return { ran: false, updated: 0 };
  }
  lastRunByAgentChain.set(key, now);

  try {
    const rows = await dbQuery<{
      position_id: string;
      deposited_a: string;
      deposited_b: string;
      current_a: string;
      current_b: string;
      realized_fees_usd: string;
      position_value_usd: string | null;
      unrealized_pnl_usd: string;
    }>(
      `
      select
        position_id,
        deposited_a::text,
        deposited_b::text,
        current_a::text,
        current_b::text,
        realized_fees_usd::text,
        position_value_usd::text,
        unrealized_pnl_usd::text
      from liquidity_position_snapshots
      where agent_id = $1
        and chain_key = $2
      `,
      [agentId, chainKey]
    );

    let updates = 0;
    for (const row of rows.rows) {
      const depositedBasis = parseNumeric(row.deposited_a) + parseNumeric(row.deposited_b);
      const currentBasis = parseNumeric(row.current_a) + parseNumeric(row.current_b);
      const existingValue = parseNumeric(row.position_value_usd);
      const positionValueUsd = existingValue > 0 ? existingValue : currentBasis;
      const unrealizedPnlUsd = positionValueUsd - depositedBasis;
      await dbQuery(
        `
        update liquidity_position_snapshots
        set
          position_value_usd = $4::numeric,
          unrealized_pnl_usd = $5::numeric,
          last_synced_at = now(),
          updated_at = now()
        where agent_id = $1
          and chain_key = $2
          and position_id = $3
        `,
        [agentId, chainKey, row.position_id, formatNumeric(positionValueUsd), formatNumeric(unrealizedPnlUsd)]
      );
      updates += 1;
    }

    return { ran: true, updated: updates };
  } catch {
    // Fail-soft by design: sync failure must not break request handling.
    return { ran: false, updated: 0 };
  }
}
