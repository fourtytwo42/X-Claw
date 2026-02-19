import type { NextRequest } from 'next/server';

import { errorResponse } from '@/lib/errors';
import { getRedisClient } from '@/lib/redis';

const WINDOW_SECONDS = 60;
const PREFIX = 'xclaw:ratelimit:v1';

function getClientIp(req: NextRequest): string {
  const forwarded = req.headers.get('x-forwarded-for');
  if (forwarded && forwarded.trim().length > 0) {
    return forwarded.split(',')[0]?.trim() ?? 'unknown';
  }

  const realIp = req.headers.get('x-real-ip');
  if (realIp && realIp.trim().length > 0) {
    return realIp.trim();
  }

  return 'unknown';
}

type LimitInput = {
  scope: string;
  key: string;
  limit: number;
  requestId: string;
};

async function checkLimit(input: LimitInput): Promise<{ ok: true } | { ok: false; response: Response }> {
  const bucket = Math.floor(Date.now() / 1000 / WINDOW_SECONDS);
  const redisKey = `${PREFIX}:${input.scope}:${input.key}:${bucket}`;

  try {
    const redis = await getRedisClient();
    const count = await redis.incr(redisKey);
    if (count === 1) {
      await redis.expire(redisKey, WINDOW_SECONDS + 2);
    }

    if (count > input.limit) {
      const retryAfter = WINDOW_SECONDS;
      return {
        ok: false,
        response: errorResponse(
          429,
          {
            code: 'rate_limited',
            message: 'Rate limit exceeded for this endpoint.',
            actionHint: 'Wait before retrying this request.',
            details: {
              scope: input.scope,
              limitPerMinute: input.limit,
              retryAfterSeconds: retryAfter
            }
          },
          input.requestId,
          { 'retry-after': String(retryAfter) }
        )
      };
    }

    return { ok: true };
  } catch {
    // Fail open on limiter backend error for MVP availability.
    return { ok: true };
  }
}

export async function enforcePublicReadRateLimit(req: NextRequest, requestId: string): Promise<{ ok: true } | { ok: false; response: Response }> {
  const ip = getClientIp(req);
  return checkLimit({
    scope: 'public_read',
    key: ip,
    limit: 120,
    requestId
  });
}

export async function enforceSensitiveManagementWriteRateLimit(
  req: NextRequest,
  requestId: string,
  agentId: string,
  sessionId: string
): Promise<{ ok: true } | { ok: false; response: Response }> {
  const ip = getClientIp(req);
  return checkLimit({
    scope: 'management_sensitive_write',
    key: `${agentId}:${sessionId}:${ip}`,
    limit: 10,
    requestId
  });
}

export async function enforceAgentChatWriteRateLimit(
  req: NextRequest,
  requestId: string,
  agentId: string
): Promise<{ ok: true } | { ok: false; response: Response }> {
  const ip = getClientIp(req);
  const nowSec = Math.floor(Date.now() / 1000);
  const lastWriteKey = `${PREFIX}:agent_chat_last:${agentId}:${ip}`;
  const lastWriteTtlSec = 90;

  try {
    const redis = await getRedisClient();
    const previousRaw = await redis.get(lastWriteKey);
    const previous = previousRaw ? Number(previousRaw) : null;

    if (previous !== null && Number.isFinite(previous)) {
      const delta = nowSec - previous;
      if (delta < 5) {
        const retryAfter = Math.max(1, 5 - delta);
        return {
          ok: false,
          response: errorResponse(
            429,
            {
              code: 'rate_limited',
              message: 'Rate limit exceeded for this endpoint.',
              actionHint: 'Wait before posting another chat message.',
              details: {
                scope: 'agent_chat_write',
                minIntervalSeconds: 5,
                retryAfterSeconds: retryAfter
              }
            },
            requestId,
            { 'retry-after': String(retryAfter) }
          )
        };
      }
    }

    await redis.set(lastWriteKey, String(nowSec), { EX: lastWriteTtlSec });

    return checkLimit({
      scope: 'agent_chat_write',
      key: `${agentId}:${ip}`,
      limit: 12,
      requestId
    });
  } catch {
    // Fail open on limiter backend error for MVP availability.
    return { ok: true };
  }
}

export async function enforceAgentFaucetDailyRateLimit(
  requestId: string,
  agentId: string,
  chainKey: string
): Promise<{ ok: true } | { ok: false; response: Response }> {
  const now = new Date();
  const nextUtcMidnight = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate() + 1, 0, 0, 0, 0);
  const ttlSeconds = Math.max(1, Math.floor((nextUtcMidnight - now.getTime()) / 1000));
  const keyDate = `${now.getUTCFullYear()}-${String(now.getUTCMonth() + 1).padStart(2, '0')}-${String(now.getUTCDate()).padStart(2, '0')}`;
  const redisKey = `${PREFIX}:agent_faucet_daily:${agentId}:${chainKey}:${keyDate}`;

  try {
    const redis = await getRedisClient();
    const set = await redis.set(redisKey, String(now.toISOString()), { NX: true, EX: ttlSeconds });
    if (set === null) {
      return {
        ok: false,
        response: errorResponse(
          429,
          {
            code: 'rate_limited',
            message: 'Faucet request limit reached for this chain today.',
            actionHint: `Retry after next UTC day begins for chain ${chainKey}.`,
            details: {
              scope: 'agent_faucet_daily_chain',
              chainKey,
              limitPerDay: 1,
              retryAfterSeconds: ttlSeconds
            }
          },
          requestId,
          { 'retry-after': String(ttlSeconds) }
        )
      };
    }
    return { ok: true };
  } catch {
    // Fail open on limiter backend error for MVP availability.
    return { ok: true };
  }
}
