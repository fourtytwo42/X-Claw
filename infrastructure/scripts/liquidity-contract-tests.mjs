#!/usr/bin/env node

import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import pg from 'pg';

const BASE_URL = process.env.XCLAW_E2E_BASE_URL || 'http://127.0.0.1:3000';
const API_BASE = `${BASE_URL.replace(/\/$/, '')}/api/v1`;
const AGENT_API_KEY = process.env.XCLAW_E2E_AGENT_API_KEY || 'slice7_token_abc12345';
const AGENT_ID = process.env.XCLAW_E2E_AGENT_ID || 'ag_slice7';
const CHAIN_KEY = process.env.XCLAW_DEFAULT_CHAIN || 'base_sepolia';
const BOOTSTRAP_TOKEN_FILE =
  process.env.XCLAW_E2E_BOOTSTRAP_TOKEN_FILE ||
  path.join(os.homedir(), '.xclaw-secrets', 'management', `${AGENT_ID}-bootstrap-token.json`);

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

async function request(method, path, { body, headers } = {}) {
  const reqHeaders = {
    'content-type': 'application/json',
    authorization: `Bearer ${AGENT_API_KEY}`,
    ...(headers || {}),
  };
  const response = await fetch(`${API_BASE}${path}`, {
    method,
    headers: reqHeaders,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const text = await response.text();
  let json;
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

async function bootstrapAndSetPolicy() {
  if (!fs.existsSync(BOOTSTRAP_TOKEN_FILE)) {
    return { ok: false, blocker: `missing bootstrap token file: ${BOOTSTRAP_TOKEN_FILE}` };
  }
  const tokenPayload = JSON.parse(fs.readFileSync(BOOTSTRAP_TOKEN_FILE, 'utf8'));
  const token = String(tokenPayload?.token || '').trim();
  if (!token) {
    return { ok: false, blocker: `invalid bootstrap token file: ${BOOTSTRAP_TOKEN_FILE}` };
  }

  const bootstrapRes = await fetch(`${API_BASE}/management/session/bootstrap`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ agentId: AGENT_ID, token }),
  });
  const bootstrapBody = await bootstrapRes.json().catch(() => ({}));
  if (!bootstrapRes.ok) {
    return { ok: false, blocker: `management bootstrap failed: ${bootstrapRes.status}`, details: bootstrapBody };
  }

  const cookies = parseSetCookies(bootstrapRes);
  const mgmtCookie = cookieValue(cookies, 'xclaw_mgmt');
  const csrfCookie = cookieValue(cookies, 'xclaw_csrf');
  if (!mgmtCookie || !csrfCookie) {
    return { ok: false, blocker: 'management bootstrap missing cookies', details: { cookies } };
  }

  const policyRes = await fetch(`${API_BASE}/management/policy/update`, {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      cookie: `xclaw_mgmt=${mgmtCookie}; xclaw_csrf=${csrfCookie}`,
      'x-csrf-token': csrfCookie,
    },
    body: JSON.stringify({
      agentId: AGENT_ID,
      chainKey: CHAIN_KEY,
      mode: 'real',
      approvalMode: 'per_trade',
      maxTradeUsd: '50000',
      maxDailyUsd: '500000',
      allowedTokens: ['usdc', 'USDC'],
      dailyCapUsdEnabled: true,
      dailyTradeCapEnabled: true,
      maxDailyTradeCount: 1000,
    }),
  });
  const policyBody = await policyRes.json().catch(() => ({}));
  if (!policyRes.ok) {
    return { ok: false, blocker: `policy update failed: ${policyRes.status}`, details: policyBody };
  }
  return { ok: true, details: policyBody };
}

async function dbSeedPolicySnapshot() {
  const databaseUrl =
    process.env.DATABASE_URL || 'postgres://xclaw_app:xclaw_dev_password@127.0.0.1:55432/xclaw_db';
  const client = new pg.Client({ connectionString: databaseUrl });
  const snapshotId = `pol_liq_contract_${Date.now()}`;
  try {
    await client.connect();
    await client.query(
      `
      insert into agent_policy_snapshots (
        snapshot_id, agent_id, chain_key, mode, approval_mode, max_trade_usd, max_daily_usd, allowed_tokens,
        daily_cap_usd_enabled, daily_trade_cap_enabled, max_daily_trade_count, created_at
      ) values (
        $1, $2, $3, 'real'::policy_mode, 'per_trade'::policy_approval_mode, '50000'::numeric, '500000'::numeric, $4::jsonb,
        true, true, 1000, now()
      )
      `,
      [snapshotId, AGENT_ID, CHAIN_KEY, JSON.stringify(['usdc', 'USDC'])]
    );
    return { ok: true, details: { snapshotId, via: 'db_fallback' } };
  } catch (error) {
    return { ok: false, blocker: 'db_policy_seed_failed', details: String(error) };
  } finally {
    await client.end().catch(() => {});
  }
}

function basePayload(overrides = {}) {
  return {
    schemaVersion: 1,
    agentId: AGENT_ID,
    chainKey: CHAIN_KEY,
    dex: 'aerodrome',
    action: 'add',
    positionType: 'v2',
    tokenA: 'USDC',
    tokenB: 'WETH',
    amountA: '1.0',
    amountB: '0.0001',
    slippageBps: 100,
    details: { source: 'liquidity_contract_tests' },
    ...overrides,
  };
}

async function main() {
  const health = await fetch(`${BASE_URL.replace(/\/$/, '')}/api/health`);
  if (!health.ok) {
    console.error(
      JSON.stringify(
        {
          ok: false,
          error: `Server health check failed at ${BASE_URL}/api/health`,
          status: health.status,
        },
        null,
        2
      )
    );
    process.exit(1);
  }

  const registerPayload = {
    schemaVersion: 1,
    agentId: AGENT_ID,
    agentName: 'Slice7 Contract Runner',
    runtimePlatform: 'linux',
    wallets: [{ chainKey: CHAIN_KEY, address: '0x1111111111111111111111111111111111111111' }],
  };
  const register = await request('POST', '/agent/register', {
    body: registerPayload,
    headers: { 'idempotency-key': `liq-register-${Date.now()}` },
  });
  expect(register.status === 200, 'agent_register_status_200', { got: register.status, body: register.body });
  if (register.status !== 200) {
    const output = {
      ok: false,
      apiBase: API_BASE,
      chainKey: CHAIN_KEY,
      passed: state.passed,
      failed: state.failed + 1,
      checks: state.checks,
      blocker: 'agent_register_failed',
    };
    console.log(JSON.stringify(output, null, 2));
    process.exit(1);
  }

  let policySetup = await bootstrapAndSetPolicy();
  if (!policySetup.ok) {
    policySetup = await dbSeedPolicySnapshot();
  }
  expect(policySetup.ok === true, 'management_policy_setup_ok', {
    details: policySetup.details,
    blocker: policySetup.blocker,
  });
  if (!policySetup.ok) {
    const output = {
      ok: false,
      apiBase: API_BASE,
      chainKey: CHAIN_KEY,
      passed: state.passed,
      failed: state.failed + 1,
      checks: state.checks,
      blocker: 'management_policy_setup_failed',
      details: policySetup,
    };
    console.log(JSON.stringify(output, null, 2));
    process.exit(1);
  }

  // 1) malformed payload -> payload_invalid
  {
    const res = await request('POST', '/liquidity/proposed', { body: { agentId: AGENT_ID } });
    expect(res.status === 400, 'proposed_malformed_status_400', { got: res.status, body: res.body });
    expect(res.body?.code === 'payload_invalid', 'proposed_malformed_code_payload_invalid', { got: res.body?.code });
  }

  // 2) auth mismatch rejection
  {
    const res = await request('POST', '/liquidity/proposed', {
      body: basePayload({ agentId: 'ag_other_mismatch' }),
    });
    expect(res.status === 401, 'proposed_auth_mismatch_status_401', { got: res.status, body: res.body });
    expect(res.body?.code === 'auth_invalid', 'proposed_auth_mismatch_code_auth_invalid', { got: res.body?.code });
  }

  // 3) idempotency replay semantics
  let replayIntentId = '';
  {
    const idem = `liq-contract-replay-${Date.now()}`;
    const payload = basePayload({ details: { source: 'liquidity_contract_replay', replayKey: idem } });
    const first = await request('POST', '/liquidity/proposed', {
      body: payload,
      headers: { 'idempotency-key': idem },
    });
    const second = await request('POST', '/liquidity/proposed', {
      body: payload,
      headers: { 'idempotency-key': idem },
    });
    const firstId = String(first.body?.liquidityIntentId || '');
    const secondId = String(second.body?.liquidityIntentId || '');
    replayIntentId = firstId;
    expect(first.status === 200, 'proposed_idempotency_first_status_200', { got: first.status, body: first.body });
    expect(second.status === 200, 'proposed_idempotency_second_status_200', { got: second.status, body: second.body });
    expect(Boolean(firstId) && firstId === secondId, 'proposed_idempotency_reused_intent', {
      firstId,
      secondId,
    });
  }

  // 4) invalid transition -> 409 liquidity_invalid_transition
  {
    const create = await request('POST', '/liquidity/proposed', {
      body: basePayload({ details: { source: 'liquidity_contract_transition', transitionKey: Date.now() } }),
      headers: { 'idempotency-key': `liq-transition-${Date.now()}` },
    });
    const intentId = String(create.body?.liquidityIntentId || '');
    const transition = await request('POST', `/liquidity/${intentId}/status`, {
      body: { status: 'verifying' },
    });
    expect(create.status === 200 && Boolean(intentId), 'status_transition_setup_created_intent', {
      createStatus: create.status,
      createBody: create.body,
    });
    expect(transition.status === 409, 'status_invalid_transition_status_409', {
      got: transition.status,
      body: transition.body,
    });
    expect(transition.body?.code === 'liquidity_invalid_transition', 'status_invalid_transition_code', {
      got: transition.body?.code,
    });
  }

  // 5) pending/positions chainKey validation
  {
    const pending = await request('GET', '/liquidity/pending');
    const positions = await request('GET', '/liquidity/positions');
    expect(pending.status === 400, 'pending_missing_chainKey_status_400', { got: pending.status, body: pending.body });
    expect(positions.status === 400, 'positions_missing_chainKey_status_400', {
      got: positions.status,
      body: positions.body,
    });
  }

  // 6) positive smoke proposed + valid transition with expected keys
  {
    const create = await request('POST', '/liquidity/proposed', {
      body: basePayload({ details: { source: 'liquidity_contract_smoke', smokeKey: Date.now() } }),
      headers: { 'idempotency-key': `liq-smoke-${Date.now()}` },
    });
    const intentId = String(create.body?.liquidityIntentId || '');
    const current = String(create.body?.status || '');
    const next = current === 'approval_pending' ? 'approved' : 'executing';
    const update = await request('POST', `/liquidity/${intentId}/status`, { body: { status: next } });
    expect(create.status === 200, 'smoke_proposed_status_200', { got: create.status, body: create.body });
    expect(Boolean(intentId) && Boolean(current), 'smoke_proposed_has_keys', { intentId, status: current });
    expect(update.status === 200, 'smoke_status_update_status_200', { got: update.status, body: update.body });
    expect(
      update.body?.ok === true && String(update.body?.liquidityIntentId || '') === intentId && String(update.body?.status || '') === next,
      'smoke_status_update_expected_keys',
      { body: update.body, expectedStatus: next }
    );
  }

  const output = {
    ok: state.failed === 0,
    apiBase: API_BASE,
    chainKey: CHAIN_KEY,
    passed: state.passed,
    failed: state.failed,
    replayIntentId,
    checks: state.checks,
  };

  console.log(JSON.stringify(output, null, 2));
  process.exit(state.failed === 0 ? 0 : 1);
}

main().catch((error) => {
  console.error(
    JSON.stringify(
      {
        ok: false,
        error: error instanceof Error ? error.message : String(error),
      },
      null,
      2
    )
  );
  process.exit(1);
});
