import type { PoolClient } from 'pg';

import { makeId } from '@/lib/ids';
import { getChainConfig } from '@/lib/chains';

type LeaderTrade = {
  trade_id: string;
  chain_key: string;
  is_mock: boolean;
  token_in: string;
  token_out: string;
  pair: string;
  amount_in: string | null;
  amount_out: string | null;
  source_trade_id: string | null;
  tx_hash: string | null;
};

type SubscriptionRow = {
  subscription_id: string;
  leader_agent_id: string;
  follower_agent_id: string;
  enabled: boolean;
  scale_bps: number;
  max_trade_usd: string | null;
  allowed_tokens: string[] | null;
};

type CopyStatus = 'pending' | 'executing' | 'filled' | 'rejected' | 'expired';

function asNumber(value: string | null | undefined): number {
  if (!value) {
    return 0;
  }
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    return 0;
  }
  return parsed;
}

function toCopyStatus(tradeStatus: string): CopyStatus | null {
  if (tradeStatus === 'executing' || tradeStatus === 'verifying') {
    return 'executing';
  }
  if (tradeStatus === 'filled') {
    return 'filled';
  }
  if (tradeStatus === 'failed' || tradeStatus === 'rejected' || tradeStatus === 'expired' || tradeStatus === 'verification_timeout') {
    return 'rejected';
  }
  return null;
}

function normalizeAllowedTokens(tokens: string[] | null): Set<string> | null {
  if (!tokens || tokens.length === 0) {
    return null;
  }
  const normalized = tokens.map((token) => token.toLowerCase());
  return new Set(normalized);
}

function copyExpiry(leaderConfirmedAt: string): string {
  return new Date(new Date(leaderConfirmedAt).getTime() + 10 * 60 * 1000).toISOString();
}

export async function expireCopyIntents(client: PoolClient): Promise<number> {
  const expired = await client.query<{ count: string }>(
    `
    with updated as (
      update copy_intents
      set
        status = 'expired',
        updated_at = now(),
        rejection_code = coalesce(rejection_code, 'approval_expired'),
        rejection_message = coalesce(rejection_message, 'Copy intent expired before execution.')
      where status in ('pending', 'executing')
        and expires_at <= now()
      returning 1
    )
    select count(*)::text as count from updated
    `
  );

  return Number.parseInt(expired.rows[0]?.count ?? '0', 10);
}

async function nextSequenceForFollower(client: PoolClient, followerAgentId: string): Promise<number> {
  const next = await client.query<{ seq: string }>(
    `
    select coalesce(max(sequence), 0)::text as seq
    from copy_intents
    where follower_agent_id = $1
    `,
    [followerAgentId]
  );
  return Number.parseInt(next.rows[0]?.seq ?? '0', 10) + 1;
}

function leaderAmountUsd(trade: LeaderTrade): number {
  const amountOut = Math.abs(asNumber(trade.amount_out));
  if (amountOut > 0) {
    return amountOut;
  }
  return Math.abs(asNumber(trade.amount_in));
}

function validateBySubscription(sub: SubscriptionRow, tokenIn: string, tokenOut: string, scaledAmountUsd: number): { ok: true } | { ok: false; code: string; message: string } {
  const allowed = normalizeAllowedTokens(sub.allowed_tokens);
  if (allowed && (!allowed.has(tokenIn.toLowerCase()) || !allowed.has(tokenOut.toLowerCase()))) {
    return {
      ok: false,
      code: 'pair_not_enabled',
      message: 'Subscription allowedTokens blocked this pair.'
    };
  }

  const maxTradeUsd = asNumber(sub.max_trade_usd);
  if (maxTradeUsd > 0 && scaledAmountUsd > maxTradeUsd) {
    return {
      ok: false,
      code: 'daily_cap_exceeded',
      message: 'Copy trade exceeds subscription maxTradeUsd.'
    };
  }

  return { ok: true };
}

async function followerPolicyAllows(
  client: PoolClient,
  followerAgentId: string,
  chainKey: string,
  tokenIn: string,
  tokenOut: string,
  scaledAmountUsd: number
): Promise<{ ok: true } | { ok: false; code: string; message: string }> {
	const policy = await client.query<{
	    max_trade_usd: string | null;
	    max_daily_usd: string | null;
	    approval_mode: 'per_trade' | 'auto';
	  }>(
	    `
	    select max_trade_usd::text, max_daily_usd::text, approval_mode
	    from agent_policy_snapshots
	    where agent_id = $1
	    order by created_at desc
	    limit 1
	    `,
	    [followerAgentId]
	  );

  if ((policy.rowCount ?? 0) === 0) {
    return { ok: false, code: 'policy_denied', message: 'Follower has no active policy snapshot.' };
  }

	  const row = policy.rows[0];

	  const maxTradeUsd = asNumber(row.max_trade_usd);
	  if (maxTradeUsd > 0 && scaledAmountUsd > maxTradeUsd) {
	    return { ok: false, code: 'policy_denied', message: 'Follower max_trade_usd limit exceeded.' };
	  }

  const maxDailyUsd = asNumber(row.max_daily_usd);
  if (maxDailyUsd > 0) {
    const total = await client.query<{ total: string }>(
      `
      select coalesce(sum(coalesce(amount_out, amount_in)), 0)::text as total
      from trades
      where agent_id = $1
        and chain_key = $2
        and status in ('filled', 'failed', 'verification_timeout')
        and created_at >= date_trunc('day', now())
      `,
      [followerAgentId, chainKey]
    );

    const dailyTotal = asNumber(total.rows[0]?.total);
    if (dailyTotal + scaledAmountUsd > maxDailyUsd) {
      return { ok: false, code: 'daily_cap_exceeded', message: 'Follower max_daily_usd limit exceeded.' };
    }
  }

  return { ok: true };
}

export async function generateCopyIntentsForLeaderFill(
  client: PoolClient,
  leaderTradeId: string,
  leaderAgentId: string,
  leaderConfirmedAt: string
): Promise<string[]> {
  const impactedAgents = new Set<string>([leaderAgentId]);

  await expireCopyIntents(client);

  const leaderTradeResult = await client.query<LeaderTrade>(
    `
    select
      trade_id,
      chain_key,
      is_mock,
      token_in,
      token_out,
      pair,
      amount_in::text,
      amount_out::text,
      source_trade_id,
      tx_hash
    from trades
    where trade_id = $1
      and agent_id = $2
    limit 1
    `,
    [leaderTradeId, leaderAgentId]
  );

  if ((leaderTradeResult.rowCount ?? 0) === 0) {
    return [...impactedAgents];
  }

  const leaderTrade = leaderTradeResult.rows[0];
  if (leaderTrade.source_trade_id) {
    return [...impactedAgents];
  }

  const subs = await client.query<SubscriptionRow>(
    `
    select
      subscription_id,
      leader_agent_id,
      follower_agent_id,
      enabled,
      scale_bps,
      max_trade_usd::text,
      allowed_tokens
    from copy_subscriptions
    where leader_agent_id = $1
      and enabled = true
    order by created_at asc
    `,
    [leaderAgentId]
  );

  const leaderUsd = leaderAmountUsd(leaderTrade);

  for (const sub of subs.rows) {
    if (sub.follower_agent_id === leaderAgentId) {
      continue;
    }

    const existing = await client.query<{ intent_id: string }>(
      `
      select intent_id
      from copy_intents
      where source_trade_id = $1
        and follower_agent_id = $2
      limit 1
      `,
      [leaderTradeId, sub.follower_agent_id]
    );

    if ((existing.rowCount ?? 0) > 0) {
      continue;
    }

    const scaledUsd = leaderUsd * (sub.scale_bps / 10000);
    const limitCheck = validateBySubscription(sub, leaderTrade.token_in, leaderTrade.token_out, scaledUsd);

    const policyCheck =
      limitCheck.ok
        ? await followerPolicyAllows(
            client,
            sub.follower_agent_id,
            leaderTrade.chain_key,
            leaderTrade.token_in,
            leaderTrade.token_out,
            scaledUsd
          )
        : limitCheck;

    const sequence = await nextSequenceForFollower(client, sub.follower_agent_id);
    const intentId = makeId('cpi');
    const expiresAt = copyExpiry(leaderConfirmedAt);

    if (!policyCheck.ok) {
      await client.query(
        `
        insert into copy_intents (
          intent_id,
          leader_agent_id,
          follower_agent_id,
          source_trade_id,
          source_tx_hash,
          mode,
          chain_key,
          pair,
          token_in,
          token_out,
          target_amount_usd,
          leader_amount_usd,
          sequence,
          leader_confirmed_at,
          expires_at,
          status,
          rejection_code,
          rejection_message,
          created_at,
          updated_at
        ) values (
          $1, $2, $3, $4, $5, $6::policy_mode, $7, $8, $9, $10,
          $11, $12, $13, $14::timestamptz, $15::timestamptz, 'rejected',
          $16, $17, now(), now()
        )
        `,
        [
          intentId,
          leaderAgentId,
          sub.follower_agent_id,
          leaderTradeId,
          leaderTrade.tx_hash,
          leaderTrade.is_mock ? 'mock' : 'real',
          leaderTrade.chain_key,
          leaderTrade.pair,
          leaderTrade.token_in,
          leaderTrade.token_out,
          scaledUsd,
          leaderUsd,
          sequence,
          leaderConfirmedAt,
          expiresAt,
          policyCheck.code,
          policyCheck.message
        ]
      );
      continue;
    }

    const followerTradeId = makeId('trd');
    const approvalModeResult = await client.query<{ approval_mode: 'per_trade' | 'auto'; allowed_tokens: unknown }>(
      `
      select approval_mode, allowed_tokens
      from agent_policy_snapshots
      where agent_id = $1
      order by created_at desc
      limit 1
      `,
      [sub.follower_agent_id]
    );
    const approvalMode = approvalModeResult.rows[0]?.approval_mode ?? 'per_trade';
    const allowedTokenSet = new Set(
      Array.isArray(approvalModeResult.rows[0]?.allowed_tokens)
        ? approvalModeResult.rows[0].allowed_tokens
            .map((value) => String(value).trim().toLowerCase())
            .filter((value) => value.length > 0)
        : []
    );
    // Back-compat: older snapshots may contain canonical token symbols.
    const cfg = getChainConfig(leaderTrade.chain_key);
    for (const [symbol, address] of Object.entries(cfg?.canonicalTokens ?? {})) {
      if (!symbol || !address) continue;
      if (allowedTokenSet.has(symbol.trim().toLowerCase())) {
        allowedTokenSet.add(address.trim().toLowerCase());
      }
    }
    const tokenInPreapproved = allowedTokenSet.has(String(leaderTrade.token_in).trim().toLowerCase());
    const followerTradeStatus = approvalMode === 'auto' || tokenInPreapproved ? 'approved' : 'approval_pending';

    await client.query(
      `
      insert into trades (
        trade_id,
        agent_id,
        chain_key,
        is_mock,
        status,
        token_in,
        token_out,
        pair,
        amount_in,
        amount_out,
        slippage_bps,
        reason,
        source_trade_id,
        created_at,
        updated_at
      ) values (
        $1, $2, $3, $4, $5::trade_status,
        $6, $7, $8, $9, null, 50,
        $10, $11,
        now(), now()
      )
      `,
      [
        followerTradeId,
        sub.follower_agent_id,
        leaderTrade.chain_key,
        leaderTrade.is_mock,
        followerTradeStatus,
        leaderTrade.token_in,
        leaderTrade.token_out,
        leaderTrade.pair,
        scaledUsd,
        `copy:${leaderTradeId}`,
        leaderTradeId
      ]
    );

    await client.query(
      `
      insert into agent_events (event_id, agent_id, trade_id, event_type, payload, created_at)
      values ($1, $2, $3, $4, $5::jsonb, now())
      `,
      [
        makeId('evt'),
        sub.follower_agent_id,
        followerTradeId,
        followerTradeStatus === 'approved' ? 'trade_approved' : 'trade_approval_pending',
        JSON.stringify({ sourceTradeId: leaderTradeId, copyIntent: true, leaderAgentId })
      ]
    );

    await client.query(
      `
      insert into copy_intents (
        intent_id,
        leader_agent_id,
        follower_agent_id,
        source_trade_id,
        source_tx_hash,
        mode,
        chain_key,
        pair,
        token_in,
        token_out,
        target_amount_usd,
        leader_amount_usd,
        sequence,
        leader_confirmed_at,
        expires_at,
        status,
        rejection_code,
        rejection_message,
        follower_trade_id,
        created_at,
        updated_at
      ) values (
        $1, $2, $3, $4, $5, $6::policy_mode, $7, $8, $9, $10,
        $11, $12, $13, $14::timestamptz, $15::timestamptz, 'pending',
        null, null, $16, now(), now()
      )
      `,
      [
        intentId,
        leaderAgentId,
        sub.follower_agent_id,
        leaderTradeId,
        leaderTrade.tx_hash,
        leaderTrade.is_mock ? 'mock' : 'real',
        leaderTrade.chain_key,
        leaderTrade.pair,
        leaderTrade.token_in,
        leaderTrade.token_out,
        scaledUsd,
        leaderUsd,
        sequence,
        leaderConfirmedAt,
        expiresAt,
        followerTradeId
      ]
    );

    impactedAgents.add(sub.follower_agent_id);
  }

  return [...impactedAgents];
}

export async function syncCopyIntentFromTradeStatus(
  client: PoolClient,
  tradeId: string,
  toStatus: string,
  reasonCode: string | null,
  reasonMessage: string | null
): Promise<string[]> {
  await expireCopyIntents(client);

  const nextCopyStatus = toCopyStatus(toStatus);
  if (!nextCopyStatus) {
    return [];
  }

  const trade = await client.query<{ trade_id: string; source_trade_id: string | null; agent_id: string }>(
    `
    select trade_id, source_trade_id, agent_id
    from trades
    where trade_id = $1
    limit 1
    `,
    [tradeId]
  );

  if ((trade.rowCount ?? 0) === 0) {
    return [];
  }

  const sourceTradeId = trade.rows[0].source_trade_id;
  if (!sourceTradeId) {
    return [];
  }

  const update = await client.query<{
    follower_agent_id: string;
    leader_agent_id: string;
  }>(
    `
    update copy_intents
    set
      status = $1::varchar,
      rejection_code = case when $1::text = 'rejected' then coalesce($2, rejection_code) else rejection_code end,
      rejection_message = case when $1::text = 'rejected' then coalesce($3, rejection_message) else rejection_message end,
      updated_at = now()
    where follower_trade_id = $4
    returning follower_agent_id, leader_agent_id
    `,
    [nextCopyStatus, reasonCode, reasonMessage, tradeId]
  );

  const impacted = new Set<string>([trade.rows[0].agent_id]);
  for (const row of update.rows) {
    impacted.add(row.follower_agent_id);
    impacted.add(row.leader_agent_id);
  }

  return [...impacted];
}
