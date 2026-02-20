import type { NextRequest } from 'next/server';

import { authenticateAgentByToken } from '@/lib/agent-auth';
import { dbQuery } from '@/lib/db';
import { internalErrorResponse, successResponse } from '@/lib/errors';
import { getRequestId } from '@/lib/request-id';

export const runtime = 'nodejs';

function normalizeAddresses(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  const unique = new Set<string>();
  for (const entry of value) {
    if (typeof entry !== 'string') {
      continue;
    }
    const trimmed = entry.trim().toLowerCase();
    if (/^0x[a-f0-9]{40}$/.test(trimmed)) {
      unique.add(trimmed);
    }
  }
  return [...unique];
}

export async function GET(req: NextRequest) {
  const requestId = getRequestId(req);

  try {
    const auth = authenticateAgentByToken(req, requestId);
    if (!auth.ok) {
      return auth.response;
    }

    const chainKey = req.nextUrl.searchParams.get('chainKey')?.trim() || 'base_sepolia';
    const policy = await dbQuery<{
      outbound_transfers_enabled: boolean;
      outbound_mode: 'disabled' | 'allow_all' | 'whitelist';
      outbound_whitelist_addresses: unknown;
      updated_at: string;
    }>(
      `
      select outbound_transfers_enabled, outbound_mode::text, outbound_whitelist_addresses, updated_at::text
      from agent_transfer_policies
      where agent_id = $1
        and chain_key = $2
      limit 1
      `,
      [auth.agentId, chainKey]
    );

    const latestCaps = await dbQuery<{
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
      [auth.agentId, chainKey]
    );

    const row = policy.rows[0];
    const outboundMode = row?.outbound_mode ?? 'disabled';
    const outboundTransfersEnabled = row?.outbound_transfers_enabled ?? false;
    const outboundWhitelistAddresses = normalizeAddresses(row?.outbound_whitelist_addresses ?? []);
    const capsRow = latestCaps.rows[0];
    const usageRow = await dbQuery<{ utc_day: string; daily_spend_usd: string; daily_filled_trades: string }>(
      `
      select utc_day::text, daily_spend_usd::text, daily_filled_trades::text
      from agent_daily_trade_usage
      where agent_id = $1
        and chain_key = $2
        and utc_day = (now() at time zone 'utc')::date
      limit 1
      `,
      [auth.agentId, chainKey]
    );

    const chainPolicyRow = await dbQuery<{ chain_enabled: boolean; updated_at: string }>(
      `
      select chain_enabled, updated_at::text
      from agent_chain_policies
      where agent_id = $1
        and chain_key = $2
      limit 1
      `,
      [auth.agentId, chainKey]
    );
    const chainEnabled = (chainPolicyRow.rowCount ?? 0) > 0 ? Boolean(chainPolicyRow.rows[0].chain_enabled) : true;
    const chainEnabledUpdatedAt = (chainPolicyRow.rowCount ?? 0) > 0 ? chainPolicyRow.rows[0].updated_at ?? null : null;

    const approvalChannels = await dbQuery<{ enabled: boolean; updated_at: string }>(
      `
      select enabled, updated_at::text
      from agent_chain_approval_channels
      where agent_id = $1
        and chain_key = $2
        and channel = 'telegram'
      limit 1
      `,
      [auth.agentId, chainKey]
    );
    const telegramEnabled = (approvalChannels.rowCount ?? 0) > 0 ? Boolean(approvalChannels.rows[0].enabled) : false;

    return successResponse(
      {
        ok: true,
        agentId: auth.agentId,
        chainKey,
        chainEnabled,
        chainEnabledUpdatedAt,
        approvalChannels: {
          telegram: { enabled: telegramEnabled }
        },
        outboundTransfersEnabled,
        outboundMode,
        outboundWhitelistAddresses,
        updatedAt: row?.updated_at ?? null,
        tradeCaps: capsRow
          ? {
              approvalMode: capsRow.approval_mode,
              maxTradeUsd: capsRow.max_trade_usd,
              maxDailyUsd: capsRow.max_daily_usd,
              allowedTokens: Array.isArray(capsRow.allowed_tokens) ? capsRow.allowed_tokens : [],
              dailyCapUsdEnabled: capsRow.daily_cap_usd_enabled,
              dailyTradeCapEnabled: capsRow.daily_trade_cap_enabled,
              maxDailyTradeCount:
                capsRow.max_daily_trade_count === null ? null : Number.parseInt(capsRow.max_daily_trade_count, 10),
              updatedAt: capsRow.created_at
            }
          : null,
        tradeCapsDeprecated: true,
        dailyUsage:
          (usageRow.rowCount ?? 0) > 0
            ? {
                utcDay: usageRow.rows[0].utc_day,
                dailySpendUsd: usageRow.rows[0].daily_spend_usd,
                dailyFilledTrades: Number.parseInt(usageRow.rows[0].daily_filled_trades, 10)
              }
            : {
                utcDay: new Date().toISOString().slice(0, 10),
                dailySpendUsd: '0',
                dailyFilledTrades: 0
              },
        dailyUsageDeprecated: true
      },
      200,
      requestId
    );
  } catch {
    return internalErrorResponse(requestId);
  }
}
