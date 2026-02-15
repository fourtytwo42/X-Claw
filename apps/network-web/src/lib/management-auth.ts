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

  const result = await dbQuery<{
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

  if (result.rowCount === 0) {
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

  return {
    ok: true,
    session: {
      sessionId: row.session_id,
      agentId: row.agent_id,
      expiresAt: row.expires_at
    }
  };
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

  if (management.session.agentId !== expectedAgentId) {
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
