#!/usr/bin/env node

import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const BASE_URL = process.env.XCLAW_E2E_BASE_URL || 'http://127.0.0.1:3000';
const API_BASE = `${BASE_URL.replace(/\/$/, '')}/api/v1`;
const AGENT_API_KEY = process.env.XCLAW_E2E_AGENT_API_KEY || 'slice7_token_abc12345';
const AGENT_ID = process.env.XCLAW_E2E_AGENT_ID || 'ag_slice7';
const CHAIN_KEY = process.env.XCLAW_DEFAULT_CHAIN || 'base_sepolia';
const BOOTSTRAP_TOKEN_FILE =
  process.env.XCLAW_E2E_BOOTSTRAP_TOKEN_FILE ||
  path.join(os.homedir(), '.xclaw-secrets', 'management', `${AGENT_ID}-bootstrap-token.json`);
const OWNER_LINK_TTL_SECONDS = Number.parseInt(process.env.XCLAW_E2E_OWNER_LINK_TTL_SECONDS || '600', 10);

const state = {
  passed: 0,
  failed: 0,
  checks: [],
};

function record(ok, name, details = {}) {
  state.checks.push({ ok, name, details });
  if (ok) {
    state.passed += 1;
  } else {
    state.failed += 1;
  }
}

function expect(condition, name, details = {}) {
  record(Boolean(condition), name, details);
  return Boolean(condition);
}

async function requestAgent(method, routePath, body) {
  const response = await fetch(`${API_BASE}${routePath}`, {
    method,
    headers: {
      'content-type': 'application/json',
      authorization: `Bearer ${AGENT_API_KEY}`,
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const text = await response.text();
  let json = {};
  try {
    json = text ? JSON.parse(text) : {};
  } catch {
    json = { raw: text };
  }
  return { status: response.status, body: json };
}

function parseBootstrapTokenFromManagementUrl(raw) {
  const text = String(raw || '').trim();
  if (!text) {
    return '';
  }
  try {
    const url = new URL(text);
    return String(url.searchParams.get('token') || '').trim();
  } catch {
    return '';
  }
}

function writeBootstrapTokenFile(token) {
  const value = String(token || '').trim();
  if (!value) {
    return;
  }
  const dir = path.dirname(BOOTSTRAP_TOKEN_FILE);
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(
    BOOTSTRAP_TOKEN_FILE,
    JSON.stringify({ agentId: AGENT_ID, token: value, source: 'agent_management_link', savedAt: new Date().toISOString() }, null, 2)
  );
}

async function issueBootstrapTokenFromAgentAuth() {
  const response = await requestAgent('POST', '/agent/management-link', {
    schemaVersion: 1,
    agentId: AGENT_ID,
    ttlSeconds: Number.isFinite(OWNER_LINK_TTL_SECONDS) && OWNER_LINK_TTL_SECONDS > 0 ? OWNER_LINK_TTL_SECONDS : 600,
  });
  if (response.status < 200 || response.status >= 300) {
    return { ok: false, blocker: `management-link issue failed (${response.status})`, details: response.body };
  }
  const token = parseBootstrapTokenFromManagementUrl(response.body?.managementUrl);
  if (!token) {
    return { ok: false, blocker: 'management-link response missing token', details: response.body };
  }
  writeBootstrapTokenFile(token);
  return { ok: true, token };
}

async function requestManagement(method, routePath, body, session) {
  const response = await fetch(`${API_BASE}${routePath}`, {
    method,
    headers: {
      'content-type': 'application/json',
      cookie: `xclaw_mgmt=${session.mgmtCookie}; xclaw_csrf=${session.csrfCookie}`,
      'x-csrf-token': session.csrfCookie,
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const text = await response.text();
  let json = {};
  try {
    json = text ? JSON.parse(text) : {};
  } catch {
    json = { raw: text };
  }
  return { status: response.status, body: json };
}

function parseSetCookies(response) {
  if (typeof response.headers.getSetCookie === 'function') {
    return response.headers.getSetCookie();
  }
  const single = response.headers.get('set-cookie');
  if (!single) {
    return [];
  }
  return single.split(/,(?=[^;]+?=)/g);
}

function cookieValue(setCookies, name) {
  for (const entry of setCookies) {
    const [pair] = String(entry || '').split(';');
    const [k, v] = pair.split('=');
    if (String(k || '').trim() === name) {
      return String(v || '').trim();
    }
  }
  return '';
}

async function bootstrapManagementSession() {
  let token = '';
  if (fs.existsSync(BOOTSTRAP_TOKEN_FILE)) {
    try {
      const tokenPayload = JSON.parse(fs.readFileSync(BOOTSTRAP_TOKEN_FILE, 'utf8'));
      token = String(tokenPayload?.token || '').trim();
    } catch {
      token = '';
    }
  }

  if (!token) {
    const issued = await issueBootstrapTokenFromAgentAuth();
    if (!issued.ok) {
      return issued;
    }
    token = String(issued.token || '').trim();
  }

  const bootstrapWithToken = async (candidateToken) => {
    const response = await fetch(`${API_BASE}/management/session/bootstrap`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ agentId: AGENT_ID, token: candidateToken }),
    });
    const body = await response.json().catch(() => ({}));
    const cookies = parseSetCookies(response);
    const mgmtCookie = cookieValue(cookies, 'xclaw_mgmt');
    const csrfCookie = cookieValue(cookies, 'xclaw_csrf');
    return {
      status: response.status,
      ok: response.ok && Boolean(mgmtCookie) && Boolean(csrfCookie),
      body,
      mgmtCookie,
      csrfCookie,
      cookies,
    };
  };

  let attempt = await bootstrapWithToken(token);
  if (!attempt.ok && (attempt.status === 401 || attempt.body?.code === 'auth_invalid')) {
    const refreshed = await issueBootstrapTokenFromAgentAuth();
    if (!refreshed.ok) {
      return refreshed;
    }
    token = String(refreshed.token || '').trim();
    attempt = await bootstrapWithToken(token);
  }
  if (!attempt.ok) {
    if (!attempt.mgmtCookie || !attempt.csrfCookie) {
      return { ok: false, blocker: 'management bootstrap missing cookies', details: { status: attempt.status, body: attempt.body, cookies: attempt.cookies } };
    }
    return { ok: false, blocker: `management bootstrap failed (${attempt.status})`, details: attempt.body };
  }
  return { ok: true, mgmtCookie: attempt.mgmtCookie, csrfCookie: attempt.csrfCookie };
}

async function setPerTradePolicy(session) {
  const body = {
    agentId: AGENT_ID,
    chainKey: CHAIN_KEY,
    mode: 'real',
    approvalMode: 'per_trade',
    maxTradeUsd: '50000',
    maxDailyUsd: '500000',
    allowedTokens: [],
    dailyCapUsdEnabled: true,
    dailyTradeCapEnabled: true,
    maxDailyTradeCount: 1000,
  };
  const response = await requestManagement('POST', '/management/policy/update', body, session);
  return response.status >= 200 && response.status < 300;
}

function liquidityPayload(overrides = {}) {
  return {
    schemaVersion: 1,
    agentId: AGENT_ID,
    chainKey: CHAIN_KEY,
    dex: 'aerodrome',
    action: 'add',
    positionType: 'v2',
    tokenA: 'WETH',
    tokenB: 'USDC',
    amountA: '0.01',
    amountB: '1',
    slippageBps: 100,
    details: { source: 'management_liquidity_decision_tests' },
    ...overrides,
  };
}

async function createApprovalPendingLiquidityIntent() {
  const response = await requestAgent('POST', '/liquidity/proposed', liquidityPayload());
  return response;
}

async function main() {
  let health;
  try {
    health = await fetch(`${BASE_URL.replace(/\/$/, '')}/api/health`);
  } catch (error) {
    console.log(
      JSON.stringify(
        {
          ok: false,
          blocker: `Server health check request failed at ${BASE_URL}/api/health`,
          error: String(error?.message || error),
        },
        null,
        2
      )
    );
    process.exit(1);
  }
  if (!health.ok) {
    console.log(
      JSON.stringify(
        {
          ok: false,
          blocker: `Server health check failed at ${BASE_URL}/api/health`,
          status: health.status,
        },
        null,
        2
      )
    );
    process.exit(1);
  }

  const session = await bootstrapManagementSession();
  expect(session.ok, 'bootstrap_management_session_ok', session);
  if (!session.ok) {
    console.log(JSON.stringify({ ok: false, ...state, blocker: session.blocker, details: session.details }, null, 2));
    process.exit(1);
  }

  const policyOk = await setPerTradePolicy(session);
  expect(policyOk, 'set_per_trade_policy_ok', { chainKey: CHAIN_KEY });
  if (!policyOk) {
    console.log(JSON.stringify({ ok: false, ...state, blocker: 'policy_update_failed' }, null, 2));
    process.exit(1);
  }

  const pendingIntent = await createApprovalPendingLiquidityIntent();
  expect(pendingIntent.status === 200, 'create_liquidity_intent_status_200', pendingIntent);
  expect(pendingIntent.body?.status === 'approval_pending', 'create_liquidity_intent_status_pending', pendingIntent.body);
  const liquidityIntentId = String(pendingIntent.body?.liquidityIntentId || '').trim();
  expect(Boolean(liquidityIntentId), 'create_liquidity_intent_has_id', { liquidityIntentId });

  const approveRes = await requestManagement(
    'POST',
    '/management/approvals/decision',
    {
      agentId: AGENT_ID,
      subjectType: 'liquidity',
      liquidityIntentId,
      decision: 'approve'
    },
    session
  );
  expect(approveRes.status === 200, 'approve_liquidity_status_200', approveRes);
  expect(approveRes.body?.ok === true, 'approve_liquidity_ok_true', approveRes.body);
  expect(approveRes.body?.subjectType === 'liquidity', 'approve_liquidity_subject_type', approveRes.body);
  expect(
    String(approveRes.body?.runtimeResume?.code || '').includes('liquidity_execute_dispatch_async'),
    'approve_liquidity_runtime_execute_queued',
    approveRes.body
  );

  const rejectIntent = await createApprovalPendingLiquidityIntent();
  const rejectLiquidityIntentId = String(rejectIntent.body?.liquidityIntentId || '').trim();
  const rejectRes = await requestManagement(
    'POST',
    '/management/approvals/decision',
    {
      agentId: AGENT_ID,
      subjectType: 'liquidity',
      liquidityIntentId: rejectLiquidityIntentId,
      decision: 'reject',
      reasonMessage: 'test rejection path'
    },
    session
  );
  expect(rejectRes.status === 200, 'reject_liquidity_status_200', rejectRes);
  expect(rejectRes.body?.status === 'rejected', 'reject_liquidity_status_rejected', rejectRes.body);

  const invalidTransitionRes = await requestManagement(
    'POST',
    '/management/approvals/decision',
    {
      agentId: AGENT_ID,
      subjectType: 'liquidity',
      liquidityIntentId: rejectLiquidityIntentId,
      decision: 'approve'
    },
    session
  );
  expect(invalidTransitionRes.status === 409, 'liquidity_invalid_transition_status_409', invalidTransitionRes);
  expect(invalidTransitionRes.body?.code === 'liquidity_invalid_transition', 'liquidity_invalid_transition_code', invalidTransitionRes.body);

  const authMismatchRes = await requestManagement(
    'POST',
    '/management/approvals/decision',
    {
      agentId: 'ag_not_managed',
      subjectType: 'liquidity',
      liquidityIntentId,
      decision: 'approve'
    },
    session
  );
  expect(authMismatchRes.status === 403 || authMismatchRes.status === 401, 'liquidity_auth_mismatch_rejected', authMismatchRes);

  const out = {
    ok: state.failed === 0,
    apiBase: API_BASE,
    chainKey: CHAIN_KEY,
    passed: state.passed,
    failed: state.failed,
    checks: state.checks,
  };
  console.log(JSON.stringify(out, null, 2));
  process.exit(state.failed === 0 ? 0 : 1);
}

main().catch((error) => {
  console.log(
    JSON.stringify(
      {
        ok: false,
        blocker: 'management_liquidity_tests_unhandled_error',
        error: String(error?.message || error),
        ...state,
      },
      null,
      2
    )
  );
  process.exit(1);
});
