import { existsSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { join } from 'node:path';

import type { NextRequest } from 'next/server';

import { issueSignedAgentToken } from '@/lib/agent-token';
import { getChainConfig, supportedChainHint } from '@/lib/chains';
import { getEnv } from '@/lib/env';
import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import { parseJsonBody } from '@/lib/http';
import { requireCsrfToken, requireManagementSession, sessionHasAgentAccess } from '@/lib/management-auth';
import { getRequestId } from '@/lib/request-id';
import { validatePayload } from '@/lib/validation';

export const runtime = 'nodejs';

type DefaultChainUpdateRequest = {
  agentId: string;
  chainKey: string;
};

function toApiErrorPayload(payload: Record<string, unknown>): {
  code: 'internal_error';
  message: string;
  actionHint?: string;
  details?: Record<string, unknown>;
} {
  const baseDetails =
    payload.details && typeof payload.details === 'object' && !Array.isArray(payload.details)
      ? (payload.details as Record<string, unknown>)
      : {};
  return {
    code: 'internal_error',
    message:
      typeof payload.message === 'string' && payload.message.trim()
        ? payload.message
        : 'Runtime default-chain command failed.',
    actionHint:
      typeof payload.actionHint === 'string' && payload.actionHint.trim()
        ? payload.actionHint
        : 'Retry once. If the issue persists, verify xclaw-agent runtime availability.',
    details: {
      ...baseDetails,
      runtimeCode: typeof payload.code === 'string' ? payload.code : 'runtime_default_chain_failed'
    },
  };
}

function resolveRuntimeBin(): string {
  const cwd = process.cwd();
  const candidates = [
    process.env.XCLAW_AGENT_RUNTIME_BIN?.trim() ?? '',
    join(cwd, 'apps', 'agent-runtime', 'bin', 'xclaw-agent'),
    join(cwd, '..', 'agent-runtime', 'bin', 'xclaw-agent')
  ].filter((value) => value.length > 0);
  for (const candidate of candidates) {
    if (existsSync(candidate)) {
      return candidate;
    }
  }
  throw new Error('xclaw-agent runtime binary not found. Set XCLAW_AGENT_RUNTIME_BIN or deploy apps/agent-runtime/bin/xclaw-agent.');
}

function resolveRuntimeApiBase(req: NextRequest): string {
  const explicit = (process.env.XCLAW_API_BASE_URL ?? '').trim();
  if (explicit.length > 0) {
    return explicit;
  }
  return `${req.nextUrl.origin}/api/v1`;
}

function runtimeSpawnEnv(req: NextRequest, agentId: string): NodeJS.ProcessEnv {
  const env: NodeJS.ProcessEnv = {
    ...process.env,
    XCLAW_API_BASE_URL: resolveRuntimeApiBase(req),
    XCLAW_AGENT_ID: agentId,
  };
  if (!(env.XCLAW_AGENT_API_KEY ?? '').trim()) {
    const mapped = getEnv().agentApiKeys[agentId];
    if (mapped) {
      env.XCLAW_AGENT_API_KEY = mapped;
    } else {
      const signed = issueSignedAgentToken(agentId);
      if (signed) {
        env.XCLAW_AGENT_API_KEY = signed;
      }
    }
  }
  return env;
}

function parseRuntimePayload(rawStdout: string): Record<string, unknown> | null {
  const lines = String(rawStdout ?? '')
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line.length > 0);
  for (let idx = lines.length - 1; idx >= 0; idx -= 1) {
    try {
      const parsed = JSON.parse(lines[idx]);
      if (parsed && typeof parsed === 'object') {
        return parsed as Record<string, unknown>;
      }
    } catch {
      // ignore non-json logs
    }
  }
  return null;
}

function invokeRuntimeDefaultChain(req: NextRequest, agentId: string, args: string[]): { ok: boolean; status: number; payload: Record<string, unknown> } {
  const runtimeBin = resolveRuntimeBin();
  const child = spawnSync(runtimeBin, args, {
    encoding: 'utf8',
    timeout: 12_000,
    env: runtimeSpawnEnv(req, agentId)
  });
  const payload = parseRuntimePayload(String(child.stdout ?? ''));
  if (child.status !== 0 || !payload || payload.ok !== true) {
    return {
      ok: false,
      status: 502,
      payload: {
        ok: false,
        code: 'runtime_default_chain_failed',
        message: 'Runtime default-chain command failed.',
        details: {
          runtimeExitCode: child.status,
          stderrSummary: String(child.stderr ?? '').slice(0, 500),
          runtimeArgs: args,
          runtimePayload: payload
        }
      }
    };
  }
  return { ok: true, status: 200, payload };
}

export async function GET(req: NextRequest) {
  const requestId = getRequestId(req);

  try {
    const agentId = req.nextUrl.searchParams.get('agentId')?.trim() ?? '';
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
          actionHint: 'Use the matching agent session for this route.'
        },
        requestId
      );
    }

    const runtime = invokeRuntimeDefaultChain(req, agentId, ['default-chain', 'get', '--json']);
    if (!runtime.ok) {
      return errorResponse(runtime.status, toApiErrorPayload(runtime.payload), requestId);
    }

    return successResponse(
      {
        ok: true,
        agentId,
        chainKey: String(runtime.payload.chainKey ?? ''),
        source: String(runtime.payload.source ?? 'fallback'),
        persistedChainKey:
          typeof runtime.payload.persistedChainKey === 'string' ? runtime.payload.persistedChainKey : null
      },
      200,
      requestId
    );
  } catch {
    return internalErrorResponse(requestId);
  }
}

export async function POST(req: NextRequest) {
  const requestId = getRequestId(req);

  try {
    const auth = await requireManagementSession(req, requestId);
    if (!auth.ok) {
      return auth.response;
    }

    const csrf = requireCsrfToken(req, requestId);
    if (!csrf.ok) {
      return csrf.response;
    }

    const parsed = await parseJsonBody(req, requestId);
    if (!parsed.ok) {
      return parsed.response;
    }

    const validated = validatePayload<DefaultChainUpdateRequest>('management-default-chain-update-request.schema.json', parsed.body);
    if (!validated.ok) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Default-chain update payload does not match schema.',
          actionHint: 'Provide agentId and chainKey.',
          details: validated.details
        },
        requestId
      );
    }

    const body = validated.data;
    if (!sessionHasAgentAccess(auth.session, body.agentId)) {
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

    const chainCfg = getChainConfig(body.chainKey);
    if (!chainCfg || chainCfg.enabled === false) {
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

    const runtime = invokeRuntimeDefaultChain(req, body.agentId, ['default-chain', 'set', '--chain', body.chainKey, '--json']);
    if (!runtime.ok) {
      return errorResponse(runtime.status, toApiErrorPayload(runtime.payload), requestId);
    }

    return successResponse(
      {
        ok: true,
        agentId: body.agentId,
        chainKey: String(runtime.payload.chainKey ?? body.chainKey),
        source: 'state',
        runtime: {
          exitCode: 0,
          stderrSummary: null
        }
      },
      200,
      requestId
    );
  } catch {
    return internalErrorResponse(requestId);
  }
}
