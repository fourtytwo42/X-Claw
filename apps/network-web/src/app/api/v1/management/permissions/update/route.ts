import type { NextRequest } from 'next/server';

import { dbQuery, withTransaction } from '@/lib/db';
import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import { parseJsonBody } from '@/lib/http';
import { makeId } from '@/lib/ids';
import { requireManagementWriteAuth } from '@/lib/management-auth';
import { getRequestId } from '@/lib/request-id';
import { validatePayload } from '@/lib/validation';

type PermissionsUpdateRequest = {
  agentId: string;
  chainKey: string;
  tradeApprovalMode?: 'per_trade' | 'auto';
  allowedTokens?: string[];
  transferApprovalMode?: 'auto' | 'per_transfer';
  nativeTransferPreapproved?: boolean;
  allowedTransferTokens?: string[];
  outboundTransfersEnabled?: boolean;
  outboundMode?: 'disabled' | 'allow_all' | 'whitelist';
  outboundWhitelistAddresses?: string[];
};

export const runtime = 'nodejs';

function normalizeSet(values: unknown): string[] {
  if (!Array.isArray(values)) {
    return [];
  }
  return Array.from(
    new Set(
      values
        .map((value) => String(value ?? '').trim().toLowerCase())
        .filter((value) => value.length > 0)
    )
  );
}

function normalizeAddresses(values: unknown): string[] {
  return normalizeSet(values).filter((value) => /^0x[a-f0-9]{40}$/.test(value));
}

export async function POST(req: NextRequest) {
  const requestId = getRequestId(req);
  try {
    const parsed = await parseJsonBody(req, requestId);
    if (!parsed.ok) {
      return parsed.response;
    }

    const validated = validatePayload<PermissionsUpdateRequest>('management-permissions-update-request.schema.json', parsed.body);
    if (!validated.ok) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Permissions update payload does not match schema.',
          actionHint: 'Provide agentId, chainKey, and at least one permission field.',
          details: validated.details
        },
        requestId
      );
    }

    const body = validated.data;
    const auth = await requireManagementWriteAuth(req, requestId, body.agentId);
    if (!auth.ok) {
      return auth.response;
    }

    const result = await withTransaction(async (client) => {
      let updatedTradePolicy = false;
      let updatedTransferPolicy = false;
      let updatedOutboundPolicy = false;

      if (body.tradeApprovalMode !== undefined || body.allowedTokens !== undefined) {
        const latest = await client.query<{
          mode: 'mock' | 'real';
          approval_mode: 'per_trade' | 'auto';
          max_trade_usd: string | null;
          max_daily_usd: string | null;
          allowed_tokens: unknown;
          daily_cap_usd_enabled: boolean;
          daily_trade_cap_enabled: boolean;
          max_daily_trade_count: number | null;
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
            max_daily_trade_count
          from agent_policy_snapshots
          where agent_id = $1
            and chain_key = $2
          order by created_at desc
          limit 1
          `,
          [body.agentId, body.chainKey]
        );
        if (latest.rowCount === 0) {
          return { ok: false as const, kind: 'missing_policy' as const };
        }
        const snapshot = latest.rows[0];

        await client.query(
          `
          insert into agent_policy_snapshots (
            snapshot_id, agent_id, chain_key, mode, approval_mode, max_trade_usd, max_daily_usd, allowed_tokens,
            daily_cap_usd_enabled, daily_trade_cap_enabled, max_daily_trade_count, created_at
          ) values ($1, $2, $3, $4::policy_mode, $5::policy_approval_mode, $6::numeric, $7::numeric, $8::jsonb, $9, $10, $11, now())
          `,
          [
            makeId('pol'),
            body.agentId,
            body.chainKey,
            snapshot.mode,
            body.tradeApprovalMode ?? snapshot.approval_mode,
            snapshot.max_trade_usd ?? '0',
            snapshot.max_daily_usd ?? '0',
            JSON.stringify(body.allowedTokens !== undefined ? normalizeSet(body.allowedTokens) : normalizeSet(snapshot.allowed_tokens)),
            snapshot.daily_cap_usd_enabled,
            snapshot.daily_trade_cap_enabled,
            snapshot.max_daily_trade_count
          ]
        );
        updatedTradePolicy = true;
      }

      if (
        body.transferApprovalMode !== undefined ||
        body.nativeTransferPreapproved !== undefined ||
        body.allowedTransferTokens !== undefined
      ) {
        const existingTransfer = await client.query<{
          transfer_approval_mode: 'auto' | 'per_transfer';
          native_transfer_preapproved: boolean;
          allowed_transfer_tokens: unknown;
        }>(
          `
          select transfer_approval_mode::text, native_transfer_preapproved, allowed_transfer_tokens
          from agent_transfer_policy_mirror
          where agent_id = $1
            and chain_key = $2
          limit 1
          `,
          [body.agentId, body.chainKey]
        );

        await client.query(
          `
          insert into agent_transfer_policy_mirror (
            policy_mirror_id, agent_id, chain_key, transfer_approval_mode, native_transfer_preapproved,
            allowed_transfer_tokens, updated_at, created_at
          ) values ($1, $2, $3, $4, $5, $6::jsonb, now(), now())
          on conflict (agent_id, chain_key)
          do update set
            transfer_approval_mode = excluded.transfer_approval_mode,
            native_transfer_preapproved = excluded.native_transfer_preapproved,
            allowed_transfer_tokens = excluded.allowed_transfer_tokens,
            updated_at = now()
          `,
          [
            makeId('tpm'),
            body.agentId,
            body.chainKey,
            body.transferApprovalMode ?? existingTransfer.rows[0]?.transfer_approval_mode ?? 'per_transfer',
            body.nativeTransferPreapproved ?? existingTransfer.rows[0]?.native_transfer_preapproved ?? false,
            JSON.stringify(
              body.allowedTransferTokens !== undefined
                ? normalizeAddresses(body.allowedTransferTokens)
                : normalizeAddresses(existingTransfer.rows[0]?.allowed_transfer_tokens)
            )
          ]
        );

        updatedTransferPolicy = true;
      }

      if (body.outboundTransfersEnabled !== undefined || body.outboundMode !== undefined || body.outboundWhitelistAddresses !== undefined) {
        const existingOutbound = await client.query<{
          outbound_transfers_enabled: boolean;
          outbound_mode: 'disabled' | 'allow_all' | 'whitelist';
          outbound_whitelist_addresses: unknown;
        }>(
          `
          select outbound_transfers_enabled, outbound_mode::text, outbound_whitelist_addresses
          from agent_transfer_policies
          where agent_id = $1
            and chain_key = $2
          limit 1
          `,
          [body.agentId, body.chainKey]
        );

        await client.query(
          `
          insert into agent_transfer_policies (
            policy_id,
            agent_id,
            chain_key,
            outbound_transfers_enabled,
            outbound_mode,
            outbound_whitelist_addresses,
            updated_by_management_session_id,
            created_at,
            updated_at
          ) values ($1, $2, $3, $4, $5::outbound_transfer_mode, $6::jsonb, $7, now(), now())
          on conflict (agent_id, chain_key)
          do update set
            outbound_transfers_enabled = excluded.outbound_transfers_enabled,
            outbound_mode = excluded.outbound_mode,
            outbound_whitelist_addresses = excluded.outbound_whitelist_addresses,
            updated_by_management_session_id = excluded.updated_by_management_session_id,
            updated_at = now()
          `,
          [
            makeId('atp'),
            body.agentId,
            body.chainKey,
            body.outboundTransfersEnabled ?? existingOutbound.rows[0]?.outbound_transfers_enabled ?? false,
            body.outboundMode ?? existingOutbound.rows[0]?.outbound_mode ?? 'disabled',
            JSON.stringify(
              body.outboundWhitelistAddresses !== undefined
                ? normalizeAddresses(body.outboundWhitelistAddresses)
                : normalizeAddresses(existingOutbound.rows[0]?.outbound_whitelist_addresses)
            ),
            auth.session.sessionId
          ]
        );

        updatedOutboundPolicy = true;
      }

      await client.query(
        `
        insert into management_audit_log (
          audit_id, agent_id, management_session_id, action_type, action_status,
          public_redacted_payload, private_payload, user_agent, created_at
        ) values ($1, $2, $3, 'permissions.update', 'accepted', $4::jsonb, $5::jsonb, $6, now())
        `,
        [
          makeId('aud'),
          body.agentId,
          auth.session.sessionId,
          JSON.stringify({ chainKey: body.chainKey, updatedTradePolicy, updatedTransferPolicy, updatedOutboundPolicy }),
          JSON.stringify(body),
          req.headers.get('user-agent')
        ]
      );

      await client.query(
        `
        insert into agent_events (event_id, agent_id, trade_id, event_type, payload, created_at)
        values ($1, $2, null, 'policy_changed', $3::jsonb, now())
        `,
        [
          makeId('evt'),
          body.agentId,
          JSON.stringify({
            source: 'permissions.update',
            chainKey: body.chainKey,
            updatedTradePolicy,
            updatedTransferPolicy,
            updatedOutboundPolicy
          })
        ]
      );

      return { ok: true as const, updatedTradePolicy, updatedTransferPolicy, updatedOutboundPolicy };
    });

    if (!result.ok) {
      return errorResponse(
        409,
        {
          code: 'policy_denied',
          message: 'Cannot update permissions because no chain policy snapshot exists.',
          actionHint: 'Create a policy snapshot first, then retry.'
        },
        requestId
      );
    }

    return successResponse({ chainKey: body.chainKey, ...result }, 200, requestId);
  } catch {
    return internalErrorResponse(requestId);
  }
}
