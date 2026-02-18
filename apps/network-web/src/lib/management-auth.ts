import { timingSafeEqual } from 'node:crypto';

import type { NextRequest } from 'next/server';

import { dbQuery } from '@/lib/db';
import { errorResponse } from '@/lib/errors';
import { CSRF_COOKIE_NAME, MGMT_COOKIE_NAME } from '@/lib/management-cookies';
import { hashManagementCookieSecret } from '@/lib/management-service';
import { enforceSensitiveManagementWriteRateLimit } from '@/lib/rate-limit';

type ManagementSession = {
  sessionId: string;
  agentId: string;
  managedAgentIds: string[];
  expiresAt: string;
};

type AuthFailure = {
  ok: false;
  response: Response;
};

type AuthSuccess = {
  ok: true;
  session: ManagementSession;
};

function parseManagementCookie(raw: string | undefined): { sessionId: string; secret: string } | null {
  if (!raw) {
    return null;
  }

  const splitAt = raw.indexOf('.');
  if (splitAt <= 0 || splitAt === raw.length - 1) {
    return null;
  }

  return {
    sessionId: raw.slice(0, splitAt),
    secret: raw.slice(splitAt + 1)
  };
}

function constantTimeEqual(left: string, right: string): boolean {
  const a = Buffer.from(left, 'utf8');
  const b = Buffer.from(right, 'utf8');
  if (a.length !== b.length) {
    return false;
  }
  return timingSafeEqual(a, b);
}

function failManagementAuth(requestId: string): AuthFailure {
  return {
    ok: false,
    response: errorResponse(
      401,
      {
        code: 'auth_invalid',
        message: 'Management session is invalid or expired.',
        actionHint: 'Bootstrap a new management session from /agents/:id?token=...'
      },
      requestId
    )
  };
}

export async function requireManagementSession(req: NextRequest, requestId: string): Promise<AuthFailure | AuthSuccess> {
  const parsed = parseManagementCookie(req.cookies.get(MGMT_COOKIE_NAME)?.value);
  if (!parsed) {
    return failManagementAuth(requestId);
  }

  let result: {
    rowCount: number | null;
    rows: Array<{
      session_id: string;
      agent_id: string;
      cookie_hash: string;
      expires_at: string;
      revoked_at: string | null;
    }>;
  };
  try {
    result = await dbQuery<{
      session_id: string;
      agent_id: string;
      cookie_hash: string;
      expires_at: string;
      revoked_at: string | null;
    }>(
      `
      select session_id, agent_id, cookie_hash, expires_at::text, revoked_at::text
      from management_sessions
      where session_id = $1
      limit 1
      `,
      [parsed.sessionId]
    );
  } catch {
    return failManagementAuth(requestId);
  }

  if ((result.rowCount ?? 0) === 0) {
    return failManagementAuth(requestId);
  }

  const row = result.rows[0];
  if (row.revoked_at || new Date(row.expires_at).getTime() <= Date.now()) {
    return failManagementAuth(requestId);
  }

  const expectedHash = hashManagementCookieSecret(parsed.sessionId, parsed.secret);
  if (!constantTimeEqual(expectedHash, row.cookie_hash)) {
    return failManagementAuth(requestId);
  }

  let managedAgentIds = [row.agent_id];
  try {
    const managed = await dbQuery<{ agent_id: string }>(
      `
      select agent_id
      from management_session_agents
      where session_id = $1
      `,
      [row.session_id]
    );
    if ((managed.rowCount ?? 0) > 0) {
      managedAgentIds = Array.from(
        new Set(
          managed.rows
            .map((entry) => String(entry.agent_id ?? '').trim())
            .filter((entry) => entry.length > 0)
            .concat([row.agent_id])
        )
      );
    }
  } catch (error) {
    const code = error && typeof error === 'object' && 'code' in error ? String((error as { code?: unknown }).code ?? '') : '';
    if (code !== '42P01' && code !== '42703') {
      return failManagementAuth(requestId);
    }
  }

  return {
    ok: true,
    session: {
      sessionId: row.session_id,
      agentId: row.agent_id,
      managedAgentIds,
      expiresAt: row.expires_at
    }
  };
}

export function sessionHasAgentAccess(session: ManagementSession, agentId: string): boolean {
  const normalized = String(agentId).trim();
  if (!normalized) {
    return false;
  }
  return session.managedAgentIds.includes(normalized);
}

export function requireCsrfToken(req: NextRequest, requestId: string): AuthFailure | { ok: true } {
  const csrfCookie = req.cookies.get(CSRF_COOKIE_NAME)?.value;
  const csrfHeader = req.headers.get('x-csrf-token');

  if (!csrfCookie || !csrfHeader || !constantTimeEqual(csrfCookie, csrfHeader)) {
    return {
      ok: false,
      response: errorResponse(
        401,
        {
          code: 'csrf_invalid',
          message: 'CSRF token validation failed for management write request.',
          actionHint: 'Send matching xclaw_csrf cookie and X-CSRF-Token header values.'
        },
        requestId
      )
    };
  }

  return { ok: true };
}

export async function requireManagementWriteAuth(
  req: NextRequest,
  requestId: string,
  expectedAgentId: string
): Promise<AuthFailure | AuthSuccess> {
  const management = await requireManagementSession(req, requestId);
  if (!management.ok) {
    return management;
  }

  if (!sessionHasAgentAccess(management.session, expectedAgentId)) {
    return {
      ok: false,
      response: errorResponse(
        401,
        {
          code: 'auth_invalid',
          message: 'Management session is not authorized for this agent.',
          actionHint: 'Use the matching agent management session for this request.'
        },
        requestId
      )
    };
  }

  const rateLimit = await enforceSensitiveManagementWriteRateLimit(
    req,
    requestId,
    expectedAgentId,
    management.session.sessionId
  );
  if (!rateLimit.ok) {
    return {
      ok: false,
      response: rateLimit.response
    };
  }

  const csrf = requireCsrfToken(req, requestId);
  if (!csrf.ok) {
    return csrf;
  }

  return management;
}
