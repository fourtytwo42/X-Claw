import type { NextRequest } from 'next/server';

import { authenticateAgentByToken } from '@/lib/agent-auth';
import { dbQuery } from '@/lib/db';
import { internalErrorResponse, successResponse } from '@/lib/errors';
import { getRequestId } from '@/lib/request-id';

export const runtime = 'nodejs';

function normalizeChainKey(raw: string | null): string {
  const trimmed = String(raw ?? '').trim().toLowerCase();
  return trimmed || 'base_sepolia';
}

function isMissingTrackedTokensSchema(error: unknown): boolean {
  if (!error || typeof error !== 'object') {
    return false;
  }
  const code = 'code' in error ? String((error as { code?: unknown }).code ?? '') : '';
  if (code === '42P01' || code === '42703') {
    return true;
  }
  const message = 'message' in error ? String((error as { message?: unknown }).message ?? '') : '';
  return message.includes('agent_tracked_tokens');
}

export async function GET(req: NextRequest) {
  const requestId = getRequestId(req);
  try {
    const auth = authenticateAgentByToken(req, requestId);
    if (!auth.ok) {
      return auth.response;
    }

    const chainKey = normalizeChainKey(req.nextUrl.searchParams.get('chainKey'));
    const rows = await dbQuery<{
      tracked_token_id: string;
      token_address: string;
      symbol: string | null;
      name: string | null;
      decimals: number | null;
      source: string;
      created_at: string;
      updated_at: string;
    }>(
      `
      select
        tracked_token_id,
        token_address,
        symbol,
        name,
        decimals,
        source,
        created_at::text,
        updated_at::text
      from agent_tracked_tokens
      where agent_id = $1
        and chain_key = $2
      order by updated_at desc, token_address asc
      `,
      [auth.agentId, chainKey]
    ).catch((error) => {
      if (isMissingTrackedTokensSchema(error)) {
        return { rows: [], rowCount: 0 };
      }
      throw error;
    });

    return successResponse(
      {
        ok: true,
        agentId: auth.agentId,
        chainKey,
        items: rows.rows.map((row) => ({
          trackedTokenId: row.tracked_token_id,
          tokenAddress: row.token_address,
          symbol: row.symbol,
          name: row.name,
          decimals: row.decimals,
          source: row.source,
          createdAt: row.created_at,
          updatedAt: row.updated_at,
        })),
      },
      200,
      requestId
    );
  } catch {
    return internalErrorResponse(requestId);
  }
}
