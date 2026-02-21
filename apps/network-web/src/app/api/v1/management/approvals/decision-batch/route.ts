import type { NextRequest } from 'next/server';

import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import { fetchWithTimeout, upstreamFetchTimeoutMs } from '@/lib/fetch-timeout';
import { parseJsonBody } from '@/lib/http';
import { getRequestId } from '@/lib/request-id';
import { validatePayload } from '@/lib/validation';

type BatchDecisionRequest = {
  items: Array<{
    agentId: string;
    rowKind: 'trade' | 'policy' | 'transfer' | 'liquidity';
    requestId: string;
    decision: 'approve' | 'reject' | 'approve_allowlist';
    chainKey?: string;
    reasonMessage?: string | null;
  }>;
};

export const runtime = 'nodejs';

async function postWithSession(req: NextRequest, path: string, body: Record<string, unknown>): Promise<{ ok: boolean; status: number; payload: unknown }> {
  const response = await fetchWithTimeout(
    new URL(path, req.nextUrl.origin),
    {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        cookie: req.headers.get('cookie') ?? '',
        'x-csrf-token': req.headers.get('x-csrf-token') ?? ''
      },
      body: JSON.stringify(body)
    },
    upstreamFetchTimeoutMs(),
  );
  const payload = await response.json().catch(() => null);
  return { ok: response.ok, status: response.status, payload };
}

export async function POST(req: NextRequest) {
  const requestId = getRequestId(req);
  try {
    const parsed = await parseJsonBody(req, requestId);
    if (!parsed.ok) {
      return parsed.response;
    }

    const validated = validatePayload<BatchDecisionRequest>('management-approvals-decision-batch-request.schema.json', parsed.body);
    if (!validated.ok) {
      return errorResponse(
        400,
        {
          code: 'payload_invalid',
          message: 'Batch decision payload does not match schema.',
          actionHint: 'Provide items[] with rowKind, requestId, and decision.',
          details: validated.details
        },
        requestId
      );
    }

    const results: Array<Record<string, unknown>> = [];

    for (const item of validated.data.items) {
      let path = '';
      let payload: Record<string, unknown> = {};

      if (item.rowKind !== 'trade' && item.decision === 'approve_allowlist') {
        results.push({
          requestId: item.requestId,
          rowKind: item.rowKind,
          decision: item.decision,
          ok: false,
          status: 400,
          response: {
            code: 'payload_invalid',
            message: 'approve_allowlist is only supported for trade rows.',
            actionHint: 'Use approve/reject for liquidity, policy, or transfer rows.'
          }
        });
        continue;
      }

      if (item.rowKind === 'trade' && item.decision === 'approve_allowlist') {
        path = '/api/v1/management/approvals/approve-allowlist-token';
        payload = { agentId: item.agentId, tradeId: item.requestId };
      } else if (item.rowKind === 'trade') {
        path = '/api/v1/management/approvals/decision';
        payload = { agentId: item.agentId, tradeId: item.requestId, decision: item.decision === 'reject' ? 'reject' : 'approve' };
      } else if (item.rowKind === 'liquidity') {
        const reasonMessage = typeof item.reasonMessage === 'string' ? item.reasonMessage.trim() : '';
        path = '/api/v1/management/approvals/decision';
        payload = {
          agentId: item.agentId,
          subjectType: 'liquidity',
          liquidityIntentId: item.requestId,
          decision: item.decision === 'reject' ? 'reject' : 'approve',
          ...(reasonMessage ? { reasonMessage } : {})
        };
      } else if (item.rowKind === 'policy') {
        path = '/api/v1/management/policy-approvals/decision';
        payload = {
          agentId: item.agentId,
          policyApprovalId: item.requestId,
          decision: item.decision === 'reject' ? 'reject' : 'approve',
          reasonMessage: item.reasonMessage ?? null
        };
      } else {
        path = '/api/v1/management/transfer-approvals/decision';
        payload = {
          agentId: item.agentId,
          approvalId: item.requestId,
          decision: item.decision === 'reject' ? 'deny' : 'approve',
          chainKey: item.chainKey,
          reasonMessage: item.reasonMessage ?? null
        };
      }

      const res = await postWithSession(req, path, payload);
      results.push({
        requestId: item.requestId,
        rowKind: item.rowKind,
        decision: item.decision,
        ok: res.ok,
        status: res.status,
        response: res.payload
      });
    }

    const successCount = results.filter((row) => row.ok === true).length;

    return successResponse(
      {
        ok: true,
        total: results.length,
        successCount,
        failureCount: results.length - successCount,
        results
      },
      200,
      requestId
    );
  } catch {
    return internalErrorResponse(requestId);
  }
}
