import type { NextRequest } from 'next/server';

import { requireAgentAuth } from '@/lib/agent-auth';
import { withTransaction } from '@/lib/db';
import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import { parseJsonBody } from '@/lib/http';
import { ensureIdempotency, storeIdempotencyResponse } from '@/lib/idempotency';
import { makeId } from '@/lib/ids';
import { getRequestId } from '@/lib/request-id';
import { validatePayload } from '@/lib/validation';

export const runtime = 'nodejs';

type RegisterRequest = {
  schemaVersion: number;
  agentId: string;
  agentName: string;
  runtimePlatform: 'windows' | 'linux' | 'macos';
  wallets: Array<{
    chainKey: string;
    address: string;
  }>;
};

const NAME_CHANGE_COOLDOWN_MS = 7 * 24 * 60 * 60 * 1000;

class NameChangeTooSoonError extends Error {
  readonly currentName: string;
  readonly requestedName: string;
  readonly nextAllowedAt: string;

  constructor(currentName: string, requestedName: string, nextAllowedAt: string) {
    super('Agent name can only be changed once every 7 days.');
    this.currentName = currentName;
    this.requestedName = requestedName;
    this.nextAllowedAt = nextAllowedAt;
  }
}

function isMissingLastNameChangeColumn(error: unknown): boolean {
  if (!error || typeof error !== 'object') {
    return false;
  }
  const code = String((error as { code?: unknown }).code ?? '');
  const column = String((error as { column?: unknown }).column ?? '');
  const message = String((error as { message?: unknown }).message ?? '');
  return code === '42703' && (column === 'last_name_change_at' || message.includes('last_name_change_at'));
}

async function readExistingAgentForUpdate(
  client: { query: <T = { agent_name: string; last_name_change_at: string | null }>(text: string, values: unknown[]) => Promise<{ rows: T[] }> },
  agentId: string
): Promise<{ agent_name: string; last_name_change_at: string | null } | null> {
  try {
    const existing = await client.query<{ agent_name: string; last_name_change_at: string | null }>(
      `
      select agent_name, last_name_change_at::text
      from agents
      where agent_id = $1
      for update
      `,
      [agentId]
    );
    return existing.rows[0] ?? null;
  } catch (error) {
    if (!isMissingLastNameChangeColumn(error)) {
      throw error;
    }
    const existingLegacy = await client.query<{ agent_name: string }>(
      `
      select agent_name
      from agents
      where agent_id = $1
      for update
      `,
      [agentId]
    );
    if (existingLegacy.rows.length === 0) {
      return null;
    }
    return { agent_name: existingLegacy.rows[0].agent_name, last_name_change_at: null };
  }
}

async function upsertWallets(client: { query: (text: string, values: unknown[]) => Promise<unknown> }, body: RegisterRequest): Promise<void> {
  for (const wallet of body.wallets) {
    await client.query(
      `
      insert into agent_wallets (
        wallet_id, agent_id, chain_key, address, custody, created_at, updated_at
      ) values ($1, $2, $3, $4, 'agent_local', now(), now())
      on conflict (agent_id, chain_key)
      do update set
        address = excluded.address,
        updated_at = now()
      `,
      [makeId('wlt'), body.agentId, wallet.chainKey, wallet.address]
    );
  }
}

export async function POST(req: NextRequest) {
  const requestId = getRequestId(req);

  try {
    const parsed = await parseJsonBody(req, requestId);
    if (!parsed.ok) {
      return parsed.response;
    }

    const validated = validatePayload<RegisterRequest>('agent-register-request.schema.json', parsed.body);
    if (!validated.ok) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Register payload does not match schema.',
          actionHint: 'Ensure required fields and wallet address formats are valid.',
          details: validated.details
        },
        requestId
      );
    }

    const body = validated.data;
    const agentName = body.agentName.trim();
    if (!agentName) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Agent name must be non-empty after trimming whitespace.',
          actionHint: 'Choose an explicit agent name and run registration again.',
          details: { field: 'agentName' }
        },
        requestId
      );
    }

    const auth = requireAgentAuth(req, body.agentId, requestId);
    if (!auth.ok) {
      return auth.response;
    }

    const idempotency = await ensureIdempotency(req, 'agent_register', body.agentId, body, requestId);
    if (!idempotency.ok) {
      return idempotency.response;
    }

    if (idempotency.ctx.replayResponse) {
      return successResponse(idempotency.ctx.replayResponse.body, idempotency.ctx.replayResponse.status, requestId);
    }

    await withTransaction(async (client) => {
      const existing = await readExistingAgentForUpdate(client, body.agentId);
      if (existing) {
        const currentName = existing.agent_name;
        const lastNameChangeAt = existing.last_name_change_at;
        const requestedDifferentName = currentName !== agentName;
        if (requestedDifferentName && lastNameChangeAt) {
          const parsedLastChange = new Date(lastNameChangeAt);
          if (!Number.isNaN(parsedLastChange.getTime())) {
            const nextAllowedAtMs = parsedLastChange.getTime() + NAME_CHANGE_COOLDOWN_MS;
            if (nextAllowedAtMs > Date.now()) {
              throw new NameChangeTooSoonError(currentName, agentName, new Date(nextAllowedAtMs).toISOString());
            }
          }
        }
      }

      await client.query(
        `
        insert into agents (
          agent_id, agent_name, runtime_platform, public_status, openclaw_metadata, last_name_change_at, created_at, updated_at
        ) values ($1, $2, $3, 'offline', '{}'::jsonb, null, now(), now())
        on conflict (agent_id)
        do update set
          agent_name = excluded.agent_name,
          runtime_platform = excluded.runtime_platform,
          last_name_change_at = case
            when agents.agent_name is distinct from excluded.agent_name then now()
            else agents.last_name_change_at
          end,
          updated_at = now()
        `,
        [body.agentId, agentName, body.runtimePlatform]
      );

      await upsertWallets(client, body);

      await client.query(
        `
        insert into agent_events (event_id, agent_id, event_type, payload, created_at)
        values ($1, $2, 'policy_changed', $3::jsonb, now())
        `,
        [makeId('evt'), body.agentId, JSON.stringify({ source: 'register', schemaVersion: body.schemaVersion })]
      );
    });

    const responseBody = {
      ok: true,
      agentId: body.agentId,
      agentName,
      wallets: body.wallets
    };

    await storeIdempotencyResponse(idempotency.ctx, 200, responseBody);
    return successResponse(responseBody, 200, requestId);
  } catch (error) {
    if (error instanceof NameChangeTooSoonError) {
      return errorResponse(
        429,
        {
          code: 'rate_limited',
          message: `Agent name can only be changed once every 7 days. Current name is '${error.currentName}'.`,
          actionHint: `Run the same register command again after ${error.nextAllowedAt} UTC, or choose to keep the current name until then.`,
          details: {
            field: 'agentName',
            currentName: error.currentName,
            requestedName: error.requestedName,
            renameCooldown: '7d',
            nextAllowedAt: error.nextAllowedAt
          }
        },
        requestId
      );
    }

    const maybeCode = (error as { code?: string }).code;
    const maybeConstraint = (error as { constraint?: string }).constraint;
    if (maybeCode === '23505') {
      if (maybeConstraint === 'agents_agent_name_key' || maybeConstraint === 'idx_agents_agent_name') {
        return errorResponse(
          409,
          {
            code: 'payload_invalid',
            message:
              'Agent name already exists. Registration was not applied, and no partial submission was saved.',
            actionHint: 'Pick a different agent name and run the same register command again.',
            details: { field: 'agentName', conflict: 'already_exists', constraint: maybeConstraint }
          },
          requestId
        );
      }
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Agent registration violates a uniqueness constraint.',
          actionHint: 'Use a unique agent name and wallet chain mapping.',
          details: { databaseCode: maybeCode }
        },
        requestId
      );
    }

    return internalErrorResponse(requestId);
  }
}
