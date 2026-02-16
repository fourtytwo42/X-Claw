import type { NextRequest } from 'next/server';

import { dbQuery } from '@/lib/db';
import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import { getChainConfig } from '@/lib/chains';
import { requireManagementSession } from '@/lib/management-auth';
import { getRequestId } from '@/lib/request-id';

export const runtime = 'nodejs';

export async function GET(req: NextRequest) {
  const requestId = getRequestId(req);

  try {
    const agentId = req.nextUrl.searchParams.get('agentId');
    if (!agentId) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'agentId query parameter is required.',
          actionHint: 'Provide ?agentId=<agent-id>.'
        },
        requestId
      );
    }

    const auth = await requireManagementSession(req, requestId);
    if (!auth.ok) {
      return auth.response;
    }

    if (auth.session.agentId !== agentId) {
      return errorResponse(
        401,
        {
          code: 'auth_invalid',
          message: 'Management session is not authorized for this agent.',
          actionHint: 'Use the matching agent session for this route.'
        },
        requestId
      );
    }

    const chainKey = req.nextUrl.searchParams.get('chainKey')?.trim() || 'base_sepolia';
    const chainCfg = getChainConfig(chainKey);
    if (!chainCfg) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Invalid chainKey query parameter value.',
          actionHint: 'Provide a supported chainKey (for example base_sepolia).',
          details: { chainKey }
        },
        requestId
      );
    }

    const chainTokens = Object.entries(chainCfg.canonicalTokens ?? {}).map(([symbol, address]) => ({
      symbol,
      address
    }));

    const [agent, approvals, policyApprovals, policyApprovalsHistory, policy, audit, outboundPolicy, dailyUsage, chainPolicy, approvalChannel] = await Promise.all([
      dbQuery<{
        agent_id: string;
        public_status: string;
        openclaw_metadata: Record<string, unknown> | null;
      }>(
        `
        select agent_id, public_status, openclaw_metadata
        from agents
        where agent_id = $1
        limit 1
        `,
        [agentId]
      ),
      dbQuery<{
        trade_id: string;
        chain_key: string;
        pair: string;
        amount_in: string | null;
        token_in: string;
        token_out: string;
        reason: string | null;
        created_at: string;
      }>(
        `
        select trade_id, chain_key, pair, amount_in::text, token_in, token_out, reason, created_at::text
        from trades
        where agent_id = $1
          and status = 'approval_pending'
        order by created_at asc
        limit 50
        `,
        [agentId]
      ),
      dbQuery<{
        request_id: string;
        chain_key: string;
        request_type: string;
        token_address: string | null;
        created_at: string;
      }>(
        `
        select request_id, chain_key, request_type, token_address, created_at::text
        from agent_policy_approval_requests
        where agent_id = $1
          and status = 'approval_pending'
        order by created_at asc
        limit 50
        `,
        [agentId]
      ),
      dbQuery<{
        request_id: string;
        chain_key: string;
        request_type: string;
        token_address: string | null;
        status: string;
        reason_message: string | null;
        created_at: string;
        decided_at: string | null;
      }>(
        `
        select
          request_id,
          chain_key,
          request_type,
          token_address,
          status::text,
          reason_message,
          created_at::text,
          decided_at::text
        from agent_policy_approval_requests
        where agent_id = $1
        order by created_at desc
        limit 50
        `,
        [agentId]
      ),
      dbQuery<{
        mode: 'mock' | 'real';
        approval_mode: 'per_trade' | 'auto';
        max_trade_usd: string | null;
        max_daily_usd: string | null;
        allowed_tokens: string[];
        daily_cap_usd_enabled: boolean;
        daily_trade_cap_enabled: boolean;
        max_daily_trade_count: string | null;
        created_at: string;
      }>(
        `
        select
          mode,
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
        order by created_at desc
        limit 1
        `,
        [agentId]
      ),
      dbQuery<{
        audit_id: string;
        action_type: string;
        action_status: string;
        public_redacted_payload: Record<string, unknown>;
        created_at: string;
      }>(
        `
        select audit_id, action_type, action_status, public_redacted_payload, created_at::text
        from management_audit_log
        where agent_id = $1
        order by created_at desc
        limit 25
        `,
        [agentId]
      ),
      dbQuery<{
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
        [agentId, chainKey]
      ),
      dbQuery<{
        utc_day: string;
        daily_spend_usd: string;
        daily_filled_trades: string;
      }>(
        `
        select utc_day::text, daily_spend_usd::text, daily_filled_trades::text
        from agent_daily_trade_usage
        where agent_id = $1
          and chain_key = $2
          and utc_day = (now() at time zone 'utc')::date
        limit 1
        `,
        [agentId, chainKey]
      ),
      dbQuery<{ chain_enabled: boolean; updated_at: string }>(
        `
        select chain_enabled, updated_at::text
        from agent_chain_policies
        where agent_id = $1
          and chain_key = $2
        limit 1
        `,
        [agentId, chainKey]
      ),
      dbQuery<{ enabled: boolean; updated_at: string }>(
        `
        select enabled, updated_at::text
        from agent_chain_approval_channels
        where agent_id = $1
          and chain_key = $2
          and channel = 'telegram'
        limit 1
        `,
        [agentId, chainKey]
      )
    ]);

    if (agent.rowCount === 0) {
      return errorResponse(
        404,
        {
          code: 'payload_invalid',
          message: 'Agent was not found.',
          actionHint: 'Verify agentId and retry.'
        },
        requestId
      );
    }

    const telegramApprovalEnabled = (approvalChannel.rowCount ?? 0) > 0 ? Boolean(approvalChannel.rows[0].enabled) : false;
    const telegramApprovalUpdatedAt = (approvalChannel.rowCount ?? 0) > 0 ? approvalChannel.rows[0].updated_at ?? null : null;

    return successResponse(
      {
        ok: true,
        agent: {
          agentId: agent.rows[0].agent_id,
          publicStatus: agent.rows[0].public_status,
          metadata: agent.rows[0].openclaw_metadata ?? {}
        },
        chainTokens,
        approvalChannels: {
          telegram: { enabled: telegramApprovalEnabled, updatedAt: telegramApprovalUpdatedAt }
        },
        approvalsQueue: approvals.rows,
        policyApprovalsQueue: policyApprovals.rows,
        policyApprovalsHistory: policyApprovalsHistory.rows,
        latestPolicy: policy.rows[0] ?? null,
        tradeCaps: policy.rows[0]
          ? {
              dailyCapUsdEnabled: policy.rows[0].daily_cap_usd_enabled,
              dailyTradeCapEnabled: policy.rows[0].daily_trade_cap_enabled,
              maxDailyTradeCount:
                policy.rows[0].max_daily_trade_count === null ? null : Number.parseInt(policy.rows[0].max_daily_trade_count, 10)
            }
          : {
              dailyCapUsdEnabled: true,
              dailyTradeCapEnabled: true,
              maxDailyTradeCount: null
            },
        dailyUsage:
          (dailyUsage.rowCount ?? 0) > 0
            ? {
                utcDay: dailyUsage.rows[0].utc_day,
                dailySpendUsd: dailyUsage.rows[0].daily_spend_usd,
                dailyFilledTrades: Number.parseInt(dailyUsage.rows[0].daily_filled_trades, 10)
              }
            : {
                utcDay: new Date().toISOString().slice(0, 10),
                dailySpendUsd: '0',
                dailyFilledTrades: 0
              },
        outboundTransfersPolicy:
          (outboundPolicy.rowCount ?? 0) > 0
            ? {
                outboundTransfersEnabled: outboundPolicy.rows[0].outbound_transfers_enabled,
                outboundMode: outboundPolicy.rows[0].outbound_mode,
                outboundWhitelistAddresses: Array.isArray(outboundPolicy.rows[0].outbound_whitelist_addresses)
                  ? outboundPolicy.rows[0].outbound_whitelist_addresses
                  : [],
                updatedAt: outboundPolicy.rows[0].updated_at
              }
            : {
                outboundTransfersEnabled: false,
                outboundMode: 'disabled',
                outboundWhitelistAddresses: [],
                updatedAt: null
              },
        chainPolicy:
          (chainPolicy.rowCount ?? 0) > 0
            ? { chainKey, chainEnabled: Boolean(chainPolicy.rows[0].chain_enabled), updatedAt: chainPolicy.rows[0].updated_at ?? null }
            : { chainKey, chainEnabled: true, updatedAt: null },
        auditLog: audit.rows,
        managementSession: {
          sessionId: auth.session.sessionId,
          expiresAt: auth.session.expiresAt
        }
      },
      200,
      requestId
    );
  } catch (error) {
    console.error('[management/agent-state] unhandled error', {
      requestId,
      error: error instanceof Error ? error.message : String(error)
    });
    return internalErrorResponse(requestId);
  }
}
