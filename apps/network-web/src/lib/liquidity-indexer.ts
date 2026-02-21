import { dbQuery } from '@/lib/db';
import { getChainConfig } from '@/lib/chains';

const POLL_INTERVAL_MS = 60 * 1000;
const lastRunByAgentChain = new Map<string, number>();
const PLACEHOLDER_TOKENS = new Set(['', 'POSITION', 'TOKEN', 'UNKNOWN', 'N/A', 'NA', '?']);

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
    const chainCfg = getChainConfig(chainKey);
    const symbolByAddress = new Map<string, string>();
    for (const [symbol, address] of Object.entries(chainCfg?.canonicalTokens ?? {})) {
      const normalizedAddress = String(address ?? '').trim().toLowerCase();
      const normalizedSymbol = String(symbol ?? '').trim().toUpperCase();
      if (!normalizedAddress || !normalizedSymbol) continue;
      symbolByAddress.set(normalizedAddress, normalizedSymbol);
    }

    await dbQuery(
      `
      update liquidity_position_snapshots s
      set
        token_a = i.token_a,
        token_b = i.token_b,
        pool_ref = i.token_a || '/' || i.token_b,
        last_synced_at = now(),
        updated_at = now()
      from (
        select distinct on (position_ref)
          position_ref,
          token_a,
          token_b
        from liquidity_intents
        where agent_id = $1
          and chain_key = $2
          and action_type in ('add', 'increase')
          and token_a ~* '^0x[0-9a-f]{40}$'
          and token_b ~* '^0x[0-9a-f]{40}$'
        order by position_ref, created_at desc
      ) i
      where s.agent_id = $1
        and s.chain_key = $2
        and s.position_id = i.position_ref
        and (
          upper(coalesce(s.token_a, '')) = any($3::text[])
          or upper(coalesce(s.token_b, '')) = any($3::text[])
          or coalesce(s.pool_ref, '') = 'POSITION/POSITION'
        )
      `,
      [agentId, chainKey, Array.from(PLACEHOLDER_TOKENS)]
    );

    await dbQuery(
      `
      update liquidity_position_snapshots s
      set
        status = 'closed',
        current_a = 0,
        current_b = 0,
        position_value_usd = 0,
        unrealized_pnl_usd = 0,
        last_synced_at = now(),
        updated_at = now()
      where s.agent_id = $1
        and s.chain_key = $2
        and s.status = 'active'
        and exists (
          select 1
          from liquidity_intents i
          where i.agent_id = s.agent_id
            and i.chain_key = s.chain_key
            and i.position_ref = s.position_id
            and i.action_type = 'remove'
            and i.status = 'filled'
            and i.amount_a >= 100::numeric
        )
      `,
      [agentId, chainKey]
    );

    await dbQuery(
      `
      update liquidity_position_snapshots s
      set
        status = 'closed',
        current_a = 0,
        current_b = 0,
        position_value_usd = 0,
        unrealized_pnl_usd = 0,
        last_synced_at = now(),
        updated_at = now()
      where s.agent_id = $1
        and s.chain_key = $2
        and s.status = 'active'
        and exists (
          select 1
          from liquidity_intents i
          where i.agent_id = s.agent_id
            and i.chain_key = s.chain_key
            and i.position_ref = s.position_id
            and i.action_type = 'remove'
            and i.status = 'failed'
            and (
              i.reason_code = 'liquidity_preflight_zero_lp_balance'
              or (
                i.reason_code = 'liquidity_execution_failed'
                and (
                  coalesce(i.reason_message, '') ilike 'Computed LP liquidity amount is zero%'
                  or coalesce(i.reason_message, '') ilike 'Position has no removable LP token balance%'
                )
              )
            )
        )
      `,
      [agentId, chainKey]
    );

    await dbQuery(
      `
      update liquidity_position_snapshots s
      set
        status = 'closed',
        current_a = 0,
        current_b = 0,
        position_value_usd = 0,
        unrealized_pnl_usd = 0,
        last_synced_at = now(),
        updated_at = now()
      where s.agent_id = $1
        and s.chain_key = $2
        and s.status = 'active'
        and s.position_type = 'v2'
        and exists (
          select 1
          from liquidity_intents i
          where i.agent_id = s.agent_id
            and i.chain_key = s.chain_key
            and i.dex_key = s.dex_key
            and i.action_type = 'remove'
            and i.status = 'failed'
            and (
              i.reason_code = 'liquidity_preflight_zero_lp_balance'
              or (
                i.reason_code = 'liquidity_execution_failed'
                and (
                  coalesce(i.reason_message, '') ilike 'Computed LP liquidity amount is zero%'
                  or coalesce(i.reason_message, '') ilike 'Position has no removable LP token balance%'
                )
              )
            )
            and (
              (
                lower(coalesce(i.token_a, '')) = lower(coalesce(s.token_a, ''))
                and lower(coalesce(i.token_b, '')) = lower(coalesce(s.token_b, ''))
              )
              or (
                lower(coalesce(i.token_a, '')) = lower(coalesce(s.token_b, ''))
                and lower(coalesce(i.token_b, '')) = lower(coalesce(s.token_a, ''))
              )
            )
        )
      `,
      [agentId, chainKey]
    );

    const rows = await dbQuery<{
      position_id: string;
      dex_key: string;
      token_a: string;
      token_b: string;
      status: string;
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
        dex_key,
        token_a,
        token_b,
        status,
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
      const tokenASymbol = symbolByAddress.get(String(row.token_a ?? '').trim().toLowerCase()) ?? '';
      const tokenBSymbol = symbolByAddress.get(String(row.token_b ?? '').trim().toLowerCase()) ?? '';
      const lpMirrorCandidates =
        tokenASymbol && tokenBSymbol
          ? [`SSLP-${tokenASymbol}-${tokenBSymbol}`, `SSLP-${tokenBSymbol}-${tokenASymbol}`]
          : [];
      let closeForZeroLpMirror = false;
      if (
        row.status === 'active' &&
        chainKey === 'hedera_testnet' &&
        String(row.dex_key ?? '').trim().toLowerCase() === 'saucerswap' &&
        lpMirrorCandidates.length > 0
      ) {
        const lpMirror = await dbQuery<{ balance: string }>(
          `
          select balance::text
          from wallet_balance_snapshots
          where agent_id = $1
            and chain_key = $2
            and upper(token) = any($3::text[])
          limit 1
          `,
          [agentId, chainKey, lpMirrorCandidates]
        );
        if ((lpMirror.rowCount ?? 0) > 0 && parseNumeric(lpMirror.rows[0]?.balance) <= 0) {
          closeForZeroLpMirror = true;
        }
      }
      if (closeForZeroLpMirror) {
        await dbQuery(
          `
          update liquidity_position_snapshots
          set
            status = 'closed',
            current_a = 0,
            current_b = 0,
            position_value_usd = 0,
            unrealized_pnl_usd = 0,
            last_synced_at = now(),
            updated_at = now()
          where agent_id = $1
            and chain_key = $2
            and position_id = $3
          `,
          [agentId, chainKey, row.position_id]
        );
        updates += 1;
        continue;
      }
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
