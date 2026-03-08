#!/usr/bin/env node

const BASE_URL = process.env.XCLAW_E2E_BASE_URL || 'http://127.0.0.1:3000';
const API_BASE = `${BASE_URL.replace(/\/$/, '')}/api/v1`;
const AGENT_ID = process.env.XCLAW_E2E_AGENT_ID || 'ag_slice7';
const AGENT_API_KEY = process.env.XCLAW_E2E_AGENT_API_KEY || 'slice7_token_abc12345';
const CHAIN_KEY = process.env.XCLAW_E2E_CHAIN_KEY || 'base_sepolia';
const TOKEN_ADDRESS = (process.env.XCLAW_E2E_TRACKED_TOKEN || '0x0000000000000000000000000000000000001549').toLowerCase();

const state = { passed: 0, failed: 0, checks: [] };

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

async function requestAgent({ method = 'GET', routePath, body }) {
  const normalizedMethod = String(method).toUpperCase();
  const response = await fetch(`${API_BASE}${routePath}`, {
    method: normalizedMethod,
    headers: {
      'content-type': 'application/json',
      authorization: `Bearer ${AGENT_API_KEY}`,
      'idempotency-key': `tok-mirror-${Date.now()}-${Math.random().toString(16).slice(2, 10)}`,
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

async function main() {
  const health = await fetch(`${BASE_URL.replace(/\/$/, '')}/api/health`).catch((error) => ({
    ok: false,
    status: 0,
    error: String(error?.message || error),
  }));
  if (!health.ok) {
    console.log(JSON.stringify({ ok: false, blocker: 'server_unreachable', details: health }, null, 2));
    process.exit(1);
  }

  const register = await requestAgent({
    method: 'POST',
    routePath: '/agent/register',
    body: {
      schemaVersion: 1,
      agentId: AGENT_ID,
      agentName: 'Token Mirror Contract Runner',
      runtimePlatform: 'linux',
      wallets: [{ chainKey: CHAIN_KEY, address: '0x1111111111111111111111111111111111111111' }],
    },
  });
  expect(register.status === 200, 'agent_register_status_200', register);

  const badPayload = await requestAgent({
    method: 'POST',
    routePath: '/agent/tokens/mirror',
    body: {
      agentId: AGENT_ID,
      chainKey: CHAIN_KEY,
      tokens: [{ token: 'bad' }],
    },
  });
  expect(badPayload.status === 400, 'mirror_rejects_bad_token_status', badPayload);
  expect(badPayload.body?.code === 'payload_invalid', 'mirror_rejects_bad_token_code', badPayload.body);

  const mismatchedAgent = await requestAgent({
    method: 'POST',
    routePath: '/agent/tokens/mirror',
    body: {
      agentId: 'ag_not_authenticated',
      chainKey: CHAIN_KEY,
      tokens: [{ token: TOKEN_ADDRESS }],
    },
  });
  expect(mismatchedAgent.status === 401, 'mirror_rejects_agent_mismatch_status', mismatchedAgent);
  expect(mismatchedAgent.body?.code === 'auth_invalid', 'mirror_rejects_agent_mismatch_code', mismatchedAgent.body);

  const mirror = await requestAgent({
    method: 'POST',
    routePath: '/agent/tokens/mirror',
    body: {
      agentId: AGENT_ID,
      chainKey: CHAIN_KEY,
      tokens: [{ token: TOKEN_ADDRESS, symbol: 'USDC', decimals: 6 }],
    },
  });
  expect(mirror.status >= 200 && mirror.status < 300, 'mirror_upsert_status', mirror);

  const list = await requestAgent({
    method: 'GET',
    routePath: `/agent/tokens?chainKey=${encodeURIComponent(CHAIN_KEY)}`,
  });
  expect(list.status === 200, 'tracked_tokens_get_status', list);
  const hasToken = Array.isArray(list.body?.items)
    ? list.body.items.some((row) => String(row?.tokenAddress || '').toLowerCase() === TOKEN_ADDRESS)
    : false;
  expect(hasToken, 'tracked_tokens_get_includes_mirrored_token', list.body);

  const ok = state.failed === 0;
  console.log(JSON.stringify({ ok, passed: state.passed, failed: state.failed, checks: state.checks }, null, 2));
  if (!ok) {
    process.exit(1);
  }
}

main().catch((error) => {
  console.log(JSON.stringify({ ok: false, blocker: 'token_mirror_contract_test_exception', error: String(error?.message || error) }, null, 2));
  process.exit(1);
});
