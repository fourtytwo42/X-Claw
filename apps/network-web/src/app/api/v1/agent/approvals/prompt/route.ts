import type { NextRequest } from 'next/server';

import { authenticateAgentByToken } from '@/lib/agent-auth';
import { dbQuery, withTransaction } from '@/lib/db';
import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import { parseJsonBody } from '@/lib/http';
import { makeId } from '@/lib/ids';
import { getChainConfig, supportedChainHint } from '@/lib/chains';
import { ensureIdempotency, storeIdempotencyResponse } from '@/lib/idempotency';
import { getRequestId } from '@/lib/request-id';
import { validatePayload } from '@/lib/validation';

export const runtime = 'nodejs';

type AgentApprovalsPromptRequest = {
  schemaVersion: 1;
  tradeId: string;
  chainKey: string;
  channel: 'telegram';
  to: string;
  threadId?: string | null;
  messageId: string;
};

export async function POST(req: NextRequest) {
  const requestId = getRequestId(req);

  try {
    const auth = authenticateAgentByToken(req, requestId);
    if (!auth.ok) {
      return auth.response;
    }

    const parsed = await parseJsonBody(req, requestId);
    if (!parsed.ok) {
      return parsed.response;
    }

    const validated = validatePayload<AgentApprovalsPromptRequest>('agent-approvals-prompt-request.schema.json', parsed.body);
    if (!validated.ok) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Prompt payload does not match schema.',
          actionHint: 'Provide tradeId, chainKey, and delivery metadata.',
          details: validated.details
        },
        requestId
      );
    }

    const body = validated.data;
    const idempotency = await ensureIdempotency(req, 'agent_approvals_prompt', auth.agentId, body, requestId);
    if (!idempotency.ok) {
      return idempotency.response;
    }
    if (idempotency.ctx.replayResponse) {
      return successResponse(idempotency.ctx.replayResponse.body as Record<string, unknown>, idempotency.ctx.replayResponse.status, requestId);
    }

    if (!getChainConfig(body.chainKey)) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Invalid chainKey value.',
          actionHint: supportedChainHint(),
          details: { chainKey: body.chainKey }
        },
        requestId
      );
    }

    const trade = await dbQuery<{ agent_id: string; chain_key: string }>(
      `
      select agent_id, chain_key
      from trades
      where trade_id = $1
      limit 1
      `,
      [body.tradeId]
    );
    if (trade.rowCount === 0) {
      return errorResponse(
        404,
        {
          code: 'payload_invalid',
          message: 'Trade was not found.',
          actionHint: 'Verify tradeId and retry.'
        },
        requestId
      );
    }
    if (trade.rows[0].agent_id !== auth.agentId || trade.rows[0].chain_key !== body.chainKey) {
      return errorResponse(
        401,
        {
          code: 'auth_invalid',
          message: 'Trade does not belong to this agent or chain context.',
          actionHint: 'Verify agent auth token and chainKey.'
        },
        requestId
      );
    }

    const promptId = makeId('tap');
    await withTransaction(async (client) => {
      await client.query(
        `
        insert into trade_approval_prompts (
          prompt_id,
          trade_id,
          agent_id,
          chain_key,
          channel,
          to_address,
          thread_id,
          message_id,
          created_at,
          deleted_at,
          delete_error
        ) values ($1, $2, $3, $4, $5, $6, $7, $8, now(), null, null)
        on conflict (trade_id, channel) do update
          set to_address = excluded.to_address,
              thread_id = excluded.thread_id,
              message_id = excluded.message_id,
              deleted_at = null,
              delete_error = null
        `,
        [promptId, body.tradeId, auth.agentId, body.chainKey, body.channel, body.to, body.threadId ?? null, body.messageId]
      );
    });

    const responseBody = {
      ok: true,
      tradeId: body.tradeId,
      chainKey: body.chainKey,
      channel: body.channel
    };
    await storeIdempotencyResponse(idempotency.ctx, 200, responseBody);
    return successResponse(responseBody, 200, requestId);
  } catch {
    return internalErrorResponse(requestId);
  }
}
