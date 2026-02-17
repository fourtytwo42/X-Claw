import crypto from 'node:crypto';

import type { NextRequest } from 'next/server';

import { dbQuery } from '@/lib/db';
import { errorResponse, internalErrorResponse, successResponse } from '@/lib/errors';
import { makeId } from '@/lib/ids';
import { requireManagementSession } from '@/lib/management-auth';
import { getRequestId } from '@/lib/request-id';

export const runtime = 'nodejs';

function isoNow(): string {
  return new Date().toISOString();
}

function buildOrigin(req: NextRequest): string {
  const explicit = process.env.XCLAW_PUBLIC_BASE_URL?.trim();
  if (explicit) {
    return explicit.replace(/\/$/, '');
  }
  return req.nextUrl.origin.replace(/\/$/, '');
}

export async function GET(req: NextRequest) {
  const requestId = getRequestId(req);
  try {
    const agentId = req.nextUrl.searchParams.get('agentId')?.trim();
    if (!agentId) {
      return errorResponse(
        400,
        { code: 'payload_invalid', message: 'agentId query parameter is required.', actionHint: 'Provide ?agentId=<agent-id>.' },
        requestId
      );
    }

    const auth = await requireManagementSession(req, requestId);
    if (!auth.ok) {
      return auth.response;
    }
    if (auth.session.agentId !== agentId) {
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

    const chainKey = req.nextUrl.searchParams.get('chainKey')?.trim() || 'base_sepolia';
    const facilitatorKey = req.nextUrl.searchParams.get('facilitatorKey')?.trim() || 'cdp';
    const assetKind = req.nextUrl.searchParams.get('assetKind')?.trim() === 'erc20' ? 'erc20' : 'native';
    const assetAddressRaw = req.nextUrl.searchParams.get('assetAddress')?.trim();
    const assetAddress = assetKind === 'erc20' ? assetAddressRaw || null : null;
    const amountAtomic = req.nextUrl.searchParams.get('amountAtomic')?.trim() || '0.01';
    const ttlRaw = req.nextUrl.searchParams.get('ttlSeconds')?.trim();
    const ttlSecondsParsed = Number(ttlRaw || '1800');
    const ttlSeconds = Number.isFinite(ttlSecondsParsed) ? Math.max(60, Math.floor(ttlSecondsParsed)) : 1800;
    const now = new Date();
    const expiresAt = new Date(now.getTime() + ttlSeconds * 1000).toISOString();

    const active = await dbQuery<{
      payment_id: string;
      network_key: string;
      facilitator_key: string;
      asset_kind: 'native' | 'erc20';
      asset_address: string | null;
      amount_atomic: string;
      payment_url: string | null;
      link_token: string | null;
      status: string;
      terminal_at: string | null;
      created_at: string;
      updated_at: string;
    }>(
      `
      select
        payment_id,
        network_key,
        facilitator_key,
        asset_kind::text,
        asset_address,
        amount_atomic::text,
        payment_url,
        link_token,
        status::text,
        terminal_at::text,
        created_at::text,
        updated_at::text
      from agent_x402_payment_mirror
      where agent_id = $1
        and direction = 'inbound'
        and network_key = $2
        and status in ('proposed', 'executing')
      order by created_at desc
      limit 1
      `,
      [agentId, chainKey]
    );

    const origin = buildOrigin(req);
    let paymentId: string;
    let linkToken: string;
    let paymentUrl: string;
    let status: string;

    if ((active.rowCount ?? 0) > 0 && active.rows[0].link_token && active.rows[0].payment_url) {
      paymentId = active.rows[0].payment_id;
      linkToken = String(active.rows[0].link_token);
      paymentUrl = String(active.rows[0].payment_url);
      status = active.rows[0].status;
      await dbQuery(
        `
        update agent_x402_payment_mirror
        set
          facilitator_key = $1,
          asset_kind = $2,
          asset_address = $3,
          amount_atomic = $4::numeric,
          reason_code = null,
          reason_message = null,
          expires_at = $5::timestamptz,
          updated_at = $6::timestamptz,
          terminal_at = null
        where payment_id = $7
        `,
        [facilitatorKey, assetKind, assetAddress, amountAtomic, expiresAt, isoNow(), paymentId]
      );
    } else {
      paymentId = makeId('xpm');
      linkToken = crypto.randomBytes(10).toString('hex');
      paymentUrl = `${origin}/api/v1/x402/pay/${encodeURIComponent(agentId)}/${encodeURIComponent(linkToken)}`;
      status = 'proposed';
      await dbQuery(
        `
        insert into agent_x402_payment_mirror (
          payment_id,
          agent_id,
          direction,
          status,
          network_key,
          facilitator_key,
          asset_kind,
          asset_address,
          amount_atomic,
          payment_url,
          link_token,
          expires_at,
          created_at,
          updated_at,
          terminal_at
        ) values (
          $1, $2, 'inbound', 'proposed', $3, $4, $5, $6, $7::numeric, $8, $9, $10::timestamptz, $11::timestamptz, $12::timestamptz, null
        )
        `,
        [paymentId, agentId, chainKey, facilitatorKey, assetKind, assetAddress, amountAtomic, paymentUrl, linkToken, expiresAt, isoNow(), isoNow()]
      );
    }

    return successResponse(
      {
        ok: true,
        agentId,
        chainKey,
        paymentId,
        networkKey: chainKey,
        facilitatorKey,
        assetKind,
        assetAddress,
        amountAtomic,
        ttlSeconds,
        paymentUrl,
        expiresAt,
        timeLimitNotice: `Payment link expires in ${ttlSeconds} seconds (at ${expiresAt}).`,
        status
      },
      200,
      requestId
    );
  } catch {
    return internalErrorResponse(requestId);
  }
}
