import type { NextRequest } from 'next/server';

import { dbQuery } from '@/lib/db';
import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import { parseJsonBody } from '@/lib/http';
import { requireManagementSession, requireManagementWriteAuth, sessionHasAgentAccess } from '@/lib/management-auth';
import { getRequestId } from '@/lib/request-id';
import { validatePayload } from '@/lib/validation';

type ManagementExploreProfileRequest = {
  agentId: string;
  strategyTags?: string[];
  venueTags?: string[];
  riskTier?: 'low' | 'medium' | 'high' | 'very_high';
  descriptionShort?: string | null;
};

const RISK_TIERS = new Set(['low', 'medium', 'high', 'very_high']);

function normalizeTags(items: string[] | undefined): string[] {
  const out = new Set<string>();
  for (const item of items ?? []) {
    const normalized = String(item).trim().toLowerCase();
    if (!normalized || !/^[a-z0-9_]+$/.test(normalized)) {
      continue;
    }
    out.add(normalized);
  }
  return [...out];
}

export const runtime = 'nodejs';

export async function GET(req: NextRequest) {
  const requestId = getRequestId(req);
  try {
    const agentId = req.nextUrl.searchParams.get('agentId')?.trim();
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
    if (!sessionHasAgentAccess(auth.session, agentId)) {
      return errorResponse(
        401,
        {
          code: 'auth_invalid',
          message: 'Management session is not authorized for this agent.',
          actionHint: 'Use the matching agent management session.'
        },
        requestId
      );
    }

    const profile = await dbQuery<{
      strategy_tags: string[];
      venue_tags: string[];
      risk_tier: string;
      description_short: string | null;
      updated_at: string;
    }>(
      `
      select
        strategy_tags,
        venue_tags,
        risk_tier,
        description_short,
        updated_at::text
      from agent_explore_profile
      where agent_id = $1
      limit 1
      `,
      [agentId]
    );

    const row = profile.rows[0];
    return successResponse(
      {
        ok: true,
        agentId,
        exploreProfile: {
          strategyTags: row?.strategy_tags ?? [],
          venueTags: row?.venue_tags ?? [],
          riskTier: row?.risk_tier ?? 'medium',
          descriptionShort: row?.description_short ?? null,
          updatedAt: row?.updated_at ?? null
        }
      },
      200,
      requestId
    );
  } catch {
    return internalErrorResponse(requestId);
  }
}

export async function PUT(req: NextRequest) {
  const requestId = getRequestId(req);
  try {
    const parsed = await parseJsonBody(req, requestId);
    if (!parsed.ok) {
      return parsed.response;
    }

    const validated = validatePayload<ManagementExploreProfileRequest>('management-explore-profile-request.schema.json', parsed.body);
    if (!validated.ok) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Explore profile payload does not match schema.',
          actionHint: 'Provide valid agentId, tags, riskTier, and optional descriptionShort.',
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

    const strategyTags = normalizeTags(body.strategyTags);
    const venueTags = normalizeTags(body.venueTags);
    const riskTier = String(body.riskTier ?? 'medium').toLowerCase();
    if (!RISK_TIERS.has(riskTier)) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'riskTier must be one of: low, medium, high, very_high.',
          actionHint: 'Provide a valid riskTier value.'
        },
        requestId
      );
    }

    const descriptionShort = body.descriptionShort?.trim() || null;

    await dbQuery(
      `
      insert into agent_explore_profile (
        agent_id,
        strategy_tags,
        venue_tags,
        risk_tier,
        description_short,
        updated_by_management_session_id,
        created_at,
        updated_at
      ) values (
        $1,
        $2::jsonb,
        $3::jsonb,
        $4,
        $5,
        $6,
        now(),
        now()
      )
      on conflict (agent_id)
      do update set
        strategy_tags = excluded.strategy_tags,
        venue_tags = excluded.venue_tags,
        risk_tier = excluded.risk_tier,
        description_short = excluded.description_short,
        updated_by_management_session_id = excluded.updated_by_management_session_id,
        updated_at = now()
      `,
      [body.agentId, JSON.stringify(strategyTags), JSON.stringify(venueTags), riskTier, descriptionShort, auth.session.sessionId]
    );

    return successResponse(
      {
        ok: true,
        agentId: body.agentId,
        exploreProfile: {
          strategyTags,
          venueTags,
          riskTier,
          descriptionShort
        }
      },
      200,
      requestId
    );
  } catch {
    return internalErrorResponse(requestId);
  }
}
