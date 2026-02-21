import type { NextRequest } from 'next/server';

import { getChainConfig } from '@/lib/chains';
import { dbQuery } from '@/lib/db';
import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import { requireManagementSession } from '@/lib/management-auth';
import { getRequestId } from '@/lib/request-id';
import { resolveTokenMetadata } from '@/lib/token-metadata';

export const runtime = 'nodejs';

type InboxStatus = 'pending' | 'approved' | 'rejected' | 'all';
type InboxType = 'trade' | 'policy' | 'transfer';

function parseStatus(raw: string | null): InboxStatus {
  const value = String(raw ?? '').trim().toLowerCase();
  if (value === 'pending' || value === 'approved' || value === 'rejected' || value === 'all') {
    return value;
  }
  return 'pending';
}

function parseTypes(raw: string | null): InboxType[] {
  const normalized = String(raw ?? '')
    .split(',')
    .map((item) => item.trim().toLowerCase())
    .filter((item): item is InboxType => item === 'trade' || item === 'policy' || item === 'transfer');
  return normalized.length > 0 ? Array.from(new Set(normalized)) : ['trade', 'policy', 'transfer'];
}

function parseLimit(raw: string | null): number {
  const parsed = Number.parseInt(String(raw ?? ''), 10);
  if (!Number.isFinite(parsed) || parsed <= 0) {
    return 200;
  }
  return Math.min(parsed, 500);
}

function normalizeStatus(value: string): 'pending' | 'approved' | 'rejected' | null {
  const raw = String(value ?? '').trim().toLowerCase();
  if (raw === 'approval_pending') {
    return 'pending';
  }
  if (raw === 'approved' || raw === 'executing' || raw === 'verifying' || raw === 'filled') {
    return 'approved';
  }
  if (raw === 'rejected' || raw === 'failed' || raw === 'deny' || raw === 'denied' || raw === 'expired' || raw === 'verification_timeout') {
    return 'rejected';
  }
  return null;
}

function riskForRow(input: { rowKind: InboxType; reason?: string | null; policyBlocked?: boolean }): 'Low' | 'Med' | 'High' {
  if (input.rowKind === 'transfer' && input.policyBlocked) {
    return 'High';
  }
  const reason = String(input.reason ?? '').toLowerCase();
  if (reason.includes('not pre-approved') || reason.includes('policy')) {
    return 'Med';
  }
  if (input.rowKind === 'policy') {
    return 'Med';
  }
  return 'Low';
}

function isHexAddress(value: string): boolean {
  return /^0x[a-fA-F0-9]{40}$/.test(value);
}

function shortAddress(value: string): string {
  return `${value.slice(0, 6)}...${value.slice(-4)}`;
}

export async function GET(req: NextRequest) {
  const requestId = getRequestId(req);

  try {
    const auth = await requireManagementSession(req, requestId);
    if (!auth.ok) {
      return auth.response;
    }

    const chainKey = String(req.nextUrl.searchParams.get('chainKey') ?? 'base_sepolia').trim().toLowerCase() || 'base_sepolia';
    const statusFilter = parseStatus(req.nextUrl.searchParams.get('status'));
    const typeFilter = parseTypes(req.nextUrl.searchParams.get('types'));
    const limit = parseLimit(req.nextUrl.searchParams.get('limit'));

    const managedAgentIds = auth.session.managedAgentIds;
    if (managedAgentIds.length === 0) {
      return successResponse({ ok: true, activeAgentId: auth.session.agentId, managedAgents: [], rows: [], permissionInventory: [] }, 200, requestId);
    }

    const [agents, tradeRows, policyRows, transferRows, policySnapshots, transferPolicyMirror, outboundPolicy] = await Promise.all([
      dbQuery<{ agent_id: string; agent_name: string; public_status: string }>(
        `
        select agent_id, agent_name, public_status::text
        from agents
        where agent_id = any($1::text[])
        `,
        [managedAgentIds]
      ),
      dbQuery<{
        agent_id: string;
        trade_id: string;
        chain_key: string;
        status: string;
        pair: string;
        token_in: string;
        token_out: string;
        reason: string | null;
        created_at: string;
      }>(
        `
        select agent_id, trade_id, chain_key, status::text, pair, token_in, token_out, reason, created_at::text
        from trades
        where agent_id = any($1::text[])
          and ($2::text = 'all' or chain_key = $2)
          and status in ('approval_pending', 'approved', 'executing', 'verifying', 'filled', 'failed', 'rejected')
        order by created_at desc
        limit $3
        `,
        [managedAgentIds, chainKey, limit]
      ),
      dbQuery<{
        agent_id: string;
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
        select agent_id, request_id, chain_key, request_type, token_address, status::text, reason_message, created_at::text, decided_at::text
        from agent_policy_approval_requests
        where agent_id = any($1::text[])
          and ($2::text = 'all' or chain_key = $2)
          and status in ('approval_pending', 'approved', 'rejected')
        order by created_at desc
        limit $3
        `,
        [managedAgentIds, chainKey, limit]
      ),
      dbQuery<{
        agent_id: string;
        approval_id: string;
        chain_key: string;
        status: string;
        transfer_type: string;
        token_symbol: string | null;
        token_address: string | null;
        to_address: string;
        policy_blocked_at_create: boolean;
        policy_block_reason_message: string | null;
        reason_message: string | null;
        created_at: string;
      }>(
        `
        select
          agent_id,
          approval_id,
          chain_key,
          status::text,
          transfer_type::text,
          token_symbol,
          token_address,
          to_address,
          policy_blocked_at_create,
          policy_block_reason_message,
          reason_message,
          created_at::text
        from agent_transfer_approval_mirror
        where agent_id = any($1::text[])
          and ($2::text = 'all' or chain_key = $2)
          and status in ('approval_pending', 'approved', 'rejected')
        order by created_at desc
        limit $3
        `,
        [managedAgentIds, chainKey, limit]
      ),
      dbQuery<{
        agent_id: string;
        chain_key: string;
        approval_mode: 'per_trade' | 'auto';
        allowed_tokens: unknown;
        created_at: string;
      }>(
        `
        select distinct on (agent_id, chain_key)
          agent_id,
          chain_key,
          approval_mode,
          allowed_tokens,
          created_at::text
        from agent_policy_snapshots
        where agent_id = any($1::text[])
          and ($2::text = 'all' or chain_key = $2)
        order by agent_id, chain_key, created_at desc
        `,
        [managedAgentIds, chainKey]
      ),
      dbQuery<{
        agent_id: string;
        chain_key: string;
        transfer_approval_mode: 'auto' | 'per_transfer';
        native_transfer_preapproved: boolean;
        allowed_transfer_tokens: unknown;
        updated_at: string;
      }>(
        `
        select agent_id, chain_key, transfer_approval_mode::text, native_transfer_preapproved, allowed_transfer_tokens, updated_at::text
        from agent_transfer_policy_mirror
        where agent_id = any($1::text[])
          and ($2::text = 'all' or chain_key = $2)
        `,
        [managedAgentIds, chainKey]
      ),
      dbQuery<{
        agent_id: string;
        chain_key: string;
        outbound_transfers_enabled: boolean;
        outbound_mode: 'disabled' | 'allow_all' | 'whitelist';
        outbound_whitelist_addresses: unknown;
        updated_at: string;
      }>(
        `
        select agent_id, chain_key, outbound_transfers_enabled, outbound_mode::text, outbound_whitelist_addresses, updated_at::text
        from agent_transfer_policies
        where agent_id = any($1::text[])
          and ($2::text = 'all' or chain_key = $2)
        `,
        [managedAgentIds, chainKey]
      )
    ]);

    const namesByAgent = new Map<string, { name: string; status: string }>();
    for (const item of agents.rows) {
      namesByAgent.set(item.agent_id, { name: item.agent_name, status: item.public_status });
    }

    const rows: Array<Record<string, unknown>> = [];
    const tokenLabelByKey = new Map<string, string>();
    const tokenResolveInFlight = new Map<string, Promise<void>>();

    async function resolveTokenLabel(chain: string, rawToken: string | null | undefined): Promise<string> {
      const token = String(rawToken ?? '').trim();
      if (!token) {
        return 'token';
      }
      if (!isHexAddress(token)) {
        return token;
      }

      const normalized = token.toLowerCase();
      const cacheKey = `${chain}:${normalized}`;
      if (tokenLabelByKey.has(cacheKey)) {
        return tokenLabelByKey.get(cacheKey) ?? token;
      }

      const pending = tokenResolveInFlight.get(cacheKey);
      if (pending) {
        await pending;
        return tokenLabelByKey.get(cacheKey) ?? shortAddress(token);
      }

      const resolvePromise = (async () => {
        const chainCfg = getChainConfig(chain);
        for (const [symbol, address] of Object.entries(chainCfg?.canonicalTokens ?? {})) {
          if (String(address).trim().toLowerCase() === normalized) {
            tokenLabelByKey.set(cacheKey, symbol);
            return;
          }
        }

        const resolved = await resolveTokenMetadata(chain, normalized).catch(() => null);
        const label = (resolved?.symbol ?? '').trim() || shortAddress(token);
        tokenLabelByKey.set(cacheKey, label);
      })();

      tokenResolveInFlight.set(cacheKey, resolvePromise);
      try {
        await resolvePromise;
      } finally {
        tokenResolveInFlight.delete(cacheKey);
      }

      return tokenLabelByKey.get(cacheKey) ?? shortAddress(token);
    }

    const tokensToWarm = new Map<string, string>();
    for (const row of tradeRows.rows) {
      if (isHexAddress(row.token_in)) {
        tokensToWarm.set(`${row.chain_key}:${row.token_in.toLowerCase()}`, row.token_in);
      }
      if (isHexAddress(row.token_out)) {
        tokensToWarm.set(`${row.chain_key}:${row.token_out.toLowerCase()}`, row.token_out);
      }
    }
    for (const row of policyRows.rows) {
      if (isHexAddress(String(row.token_address ?? ''))) {
        const token = String(row.token_address);
        tokensToWarm.set(`${row.chain_key}:${token.toLowerCase()}`, token);
      }
    }
    for (const row of transferRows.rows) {
      if (isHexAddress(String(row.token_address ?? ''))) {
        const token = String(row.token_address);
        tokensToWarm.set(`${row.chain_key}:${token.toLowerCase()}`, token);
      }
    }
    await Promise.all(
      [...tokensToWarm.keys()].map(async (key) => {
        const splitAt = key.indexOf(':');
        if (splitAt <= 0) {
          return;
        }
        const chain = key.slice(0, splitAt);
        const token = tokensToWarm.get(key) ?? '';
        await resolveTokenLabel(chain, token);
      })
    );

    for (const row of tradeRows.rows) {
      if (!typeFilter.includes('trade')) {
        continue;
      }
      const normalizedStatus = normalizeStatus(row.status);
      if (!normalizedStatus) {
        continue;
      }
      if (statusFilter !== 'all' && normalizedStatus !== statusFilter) {
        continue;
      }
      const tokenInLabel = await resolveTokenLabel(row.chain_key, row.token_in);
      const tokenOutLabel = await resolveTokenLabel(row.chain_key, row.token_out);
      rows.push({
        id: `trade:${row.trade_id}`,
        requestId: row.trade_id,
        rowKind: 'trade',
        agentId: row.agent_id,
        agentName: namesByAgent.get(row.agent_id)?.name ?? row.agent_id,
        chainKey: row.chain_key,
        status: normalizedStatus,
        title: `${tokenInLabel} -> ${tokenOutLabel}`,
        subtitle: `Trade ${row.trade_id} (${row.status})`,
        requestTypeLabel: 'Trade Approval',
        reasonLine: row.reason || (row.status === 'approval_pending' ? 'Token not pre-approved' : 'Trade approval history.'),
        riskLabel: riskForRow({ rowKind: 'trade', reason: row.reason }),
        createdAt: row.created_at
      });
    }

    for (const row of policyRows.rows) {
      if (!typeFilter.includes('policy')) {
        continue;
      }
      const normalizedStatus = normalizeStatus(row.status);
      if (!normalizedStatus) {
        continue;
      }
      if (statusFilter !== 'all' && normalizedStatus !== statusFilter) {
        continue;
      }
      const tokenLabel = await resolveTokenLabel(row.chain_key, row.token_address);
      const title =
        row.request_type === 'token_preapprove_add'
          ? `Preapprove ${tokenLabel}`
          : row.request_type === 'token_preapprove_remove'
            ? `Remove preapproval for ${tokenLabel}`
            : row.request_type;
      rows.push({
        id: `policy:${row.request_id}`,
        requestId: row.request_id,
        rowKind: 'policy',
        agentId: row.agent_id,
        agentName: namesByAgent.get(row.agent_id)?.name ?? row.agent_id,
        chainKey: row.chain_key,
        status: normalizedStatus,
        title,
        subtitle: `Request ${row.request_id}`,
        requestTypeLabel: 'Policy Approval',
        reasonLine: row.reason_message || 'Policy change requires owner confirmation.',
        riskLabel: riskForRow({ rowKind: 'policy', reason: row.reason_message }),
        createdAt: row.decided_at ?? row.created_at,
        tokenAddress: row.token_address
      });
    }

    for (const row of transferRows.rows) {
      if (!typeFilter.includes('transfer')) {
        continue;
      }
      const normalizedStatus = normalizeStatus(row.status);
      if (!normalizedStatus) {
        continue;
      }
      if (statusFilter !== 'all' && normalizedStatus !== statusFilter) {
        continue;
      }
      const tokenLabel = row.transfer_type === 'native' ? 'Native' : await resolveTokenLabel(row.chain_key, row.token_symbol || row.token_address);
      rows.push({
        id: `transfer:${row.approval_id}`,
        requestId: row.approval_id,
        rowKind: 'transfer',
        agentId: row.agent_id,
        agentName: namesByAgent.get(row.agent_id)?.name ?? row.agent_id,
        chainKey: row.chain_key,
        status: normalizedStatus,
        title: `Transfer ${tokenLabel} to ${row.to_address}`,
        subtitle: `Transfer approval ${row.approval_id}`,
        requestTypeLabel: 'Withdraw Approval',
        reasonLine: row.policy_block_reason_message || row.reason_message || 'Transfer requires owner confirmation.',
        riskLabel: riskForRow({ rowKind: 'transfer', reason: row.reason_message, policyBlocked: row.policy_blocked_at_create }),
        createdAt: row.created_at
      });
    }

    rows.sort((a, b) => new Date(String(b.createdAt)).getTime() - new Date(String(a.createdAt)).getTime());

    const transferPolicyByKey = new Map<string, (typeof transferPolicyMirror.rows)[number]>();
    for (const row of transferPolicyMirror.rows) {
      transferPolicyByKey.set(`${row.agent_id}:${row.chain_key}`, row);
    }
    const outboundByKey = new Map<string, (typeof outboundPolicy.rows)[number]>();
    for (const row of outboundPolicy.rows) {
      outboundByKey.set(`${row.agent_id}:${row.chain_key}`, row);
    }

    const permissionInventory = policySnapshots.rows.map((row) => {
      const key = `${row.agent_id}:${row.chain_key}`;
      const transferPolicy = transferPolicyByKey.get(key);
      const outbound = outboundByKey.get(key);
      const allowedTokens = Array.isArray(row.allowed_tokens)
        ? row.allowed_tokens.map((item) => String(item).trim()).filter((item) => item.length > 0)
        : [];

      return {
        agentId: row.agent_id,
        agentName: namesByAgent.get(row.agent_id)?.name ?? row.agent_id,
        chainKey: row.chain_key,
        tradePermissions: {
          approvalMode: row.approval_mode,
          allowedTokens,
          updatedAt: row.created_at
        },
        transferPermissions: {
          transferApprovalMode: transferPolicy?.transfer_approval_mode ?? 'per_transfer',
          nativeTransferPreapproved: transferPolicy?.native_transfer_preapproved ?? false,
          allowedTransferTokens: Array.isArray(transferPolicy?.allowed_transfer_tokens)
            ? transferPolicy!.allowed_transfer_tokens
            : [],
          updatedAt: transferPolicy?.updated_at ?? null
        },
        outboundPermissions: {
          outboundTransfersEnabled: outbound?.outbound_transfers_enabled ?? false,
          outboundMode: outbound?.outbound_mode ?? 'disabled',
          outboundWhitelistAddresses: Array.isArray(outbound?.outbound_whitelist_addresses)
            ? outbound!.outbound_whitelist_addresses
            : [],
          updatedAt: outbound?.updated_at ?? null
        }
      };
    });

    return successResponse(
      {
        ok: true,
        activeAgentId: auth.session.agentId,
        managedAgents: managedAgentIds,
        filters: { chainKey, status: statusFilter, types: typeFilter, limit },
        summary: {
          pending: rows.filter((row) => row.status === 'pending').length,
          approved: rows.filter((row) => row.status === 'approved').length,
          rejected: rows.filter((row) => row.status === 'rejected').length
        },
        rows,
        permissionInventory
      },
      200,
      requestId
    );
  } catch {
    return internalErrorResponse(requestId);
  }
}
