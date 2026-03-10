#!/usr/bin/env node

import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const DEFAULT_BASE_URL = 'http://127.0.0.1:3000';
const DEFAULT_CHAIN_KEY = 'base_sepolia';
const DEFAULT_TOKEN_FILE = path.join(os.tmpdir(), 'xclaw-slice251-bootstrap-token.json');

function fail(code, message, details = {}) {
  const payload = { ok: false, code, message, details };
  console.error(JSON.stringify(payload, null, 2));
  process.exit(1);
}

function readOpenClawSkillEnv() {
  try {
    const file = path.join(os.homedir(), '.openclaw', 'openclaw.json');
    const parsed = JSON.parse(fs.readFileSync(file, 'utf8'));
    return (((parsed?.skills ?? {}).entries ?? {})['xclaw-agent'] ?? {}).env ?? {};
  } catch {
    return {};
  }
}

function resolveEnvValue(key, fallbackEnv = {}) {
  const direct = String(process.env[key] ?? '').trim();
  if (direct) {
    return direct;
  }
  const fallback = String(fallbackEnv[key] ?? '').trim();
  return fallback;
}

function parseSetCookieValues(headers) {
  if (typeof headers.getSetCookie === 'function') {
    return headers.getSetCookie();
  }
  const single = headers.get('set-cookie');
  return single ? [single] : [];
}

function applyCookies(jar, response) {
  for (const raw of parseSetCookieValues(response.headers)) {
    const first = String(raw).split(';')[0] ?? '';
    const eq = first.indexOf('=');
    if (eq <= 0) continue;
    const name = first.slice(0, eq).trim();
    const value = first.slice(eq + 1).trim();
    if (!name) continue;
    jar.set(name, value);
  }
}

function cookieHeader(jar) {
  return Array.from(jar.entries())
    .map(([k, v]) => `${k}=${v}`)
    .join('; ');
}

async function requestJson(url, { method = 'GET', headers = {}, body, jar = null } = {}) {
  const finalHeaders = { ...headers };
  if (jar && jar.size > 0) {
    finalHeaders.cookie = cookieHeader(jar);
  }
  const response = await fetch(url, {
    method,
    headers: finalHeaders,
    body,
  });
  if (jar) {
    applyCookies(jar, response);
  }
  const text = await response.text();
  let json = null;
  try {
    json = text ? JSON.parse(text) : null;
  } catch {
    json = null;
  }
  return { response, json, text };
}

async function main() {
  const skillEnv = readOpenClawSkillEnv();
  const baseUrl = resolveEnvValue('XCLAW_MGMT_VERIFY_BASE_URL') || DEFAULT_BASE_URL;
  const apiBase = `${baseUrl.replace(/\/+$/, '')}/api/v1`;
  const agentId = resolveEnvValue('XCLAW_MGMT_VERIFY_AGENT_ID', skillEnv) || resolveEnvValue('XCLAW_AGENT_ID', skillEnv);
  const agentApiKey =
    resolveEnvValue('XCLAW_MGMT_VERIFY_AGENT_API_KEY', skillEnv) || resolveEnvValue('XCLAW_AGENT_API_KEY', skillEnv);
  const chainKey = resolveEnvValue('XCLAW_MGMT_VERIFY_CHAIN_KEY', skillEnv) || DEFAULT_CHAIN_KEY;
  const tokenFile = resolveEnvValue('XCLAW_MGMT_VERIFY_BOOTSTRAP_TOKEN_FILE') || DEFAULT_TOKEN_FILE;

  if (!agentId) fail('missing_env', 'Missing agent id for management verification.', { keys: ['XCLAW_MGMT_VERIFY_AGENT_ID', 'XCLAW_AGENT_ID'] });
  if (!agentApiKey) fail('missing_env', 'Missing agent API key for management verification.', { keys: ['XCLAW_MGMT_VERIFY_AGENT_API_KEY', 'XCLAW_AGENT_API_KEY'] });

  const results = {
    baseUrl,
    apiBase,
    agentId,
    chainKey,
    tokenFile,
    steps: {},
  };

  const validLink = await requestJson(`${apiBase}/agent/management-link`, {
    method: 'POST',
    headers: {
      authorization: `Bearer ${agentApiKey}`,
      'content-type': 'application/json',
    },
    body: JSON.stringify({ schemaVersion: 1, agentId, ttlSeconds: 600 }),
  });
  if (!validLink.response.ok || !validLink.json?.ok || !validLink.json?.managementUrl) {
    fail('management_link_failed', 'Failed to generate management link.', {
      status: validLink.response.status,
      body: validLink.json ?? validLink.text,
    });
  }

  const validUrl = new URL(String(validLink.json.managementUrl));
  const validToken = String(validUrl.searchParams.get('token') ?? '').trim();
  if (!validToken) {
    fail('management_link_missing_token', 'Generated management link did not contain a token.');
  }
  fs.writeFileSync(tokenFile, JSON.stringify({ token: validToken, generatedAt: new Date().toISOString() }, null, 2));
  results.steps.managementLink = {
    ok: true,
    managementUrl: validLink.json.managementUrl,
    expiresAt: validLink.json.expiresAt ?? null,
  };

  const invalidBootstrap = await requestJson(`${apiBase}/management/session/bootstrap`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ agentId, token: `${validToken}-invalid` }),
  });
  if (invalidBootstrap.response.status !== 401 || invalidBootstrap.json?.code !== 'auth_invalid') {
    fail('invalid_token_contract_mismatch', 'Invalid bootstrap token did not fail with auth_invalid.', {
      status: invalidBootstrap.response.status,
      body: invalidBootstrap.json ?? invalidBootstrap.text,
    });
  }
  results.steps.invalidToken = { ok: true, status: invalidBootstrap.response.status, code: invalidBootstrap.json.code };

  const expiringLink = await requestJson(`${apiBase}/agent/management-link`, {
    method: 'POST',
    headers: {
      authorization: `Bearer ${agentApiKey}`,
      'content-type': 'application/json',
    },
    body: JSON.stringify({ schemaVersion: 1, agentId, ttlSeconds: 60 }),
  });
  if (!expiringLink.response.ok || !expiringLink.json?.managementUrl) {
    fail('expiring_management_link_failed', 'Failed to issue short-lived management link.', {
      status: expiringLink.response.status,
      body: expiringLink.json ?? expiringLink.text,
    });
  }
  const expiringToken = new URL(String(expiringLink.json.managementUrl)).searchParams.get('token');
  await new Promise((resolve) => setTimeout(resolve, 65000));
  const expiredBootstrap = await requestJson(`${apiBase}/management/session/bootstrap`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ agentId, token: expiringToken }),
  });
  if (expiredBootstrap.response.status !== 401 || expiredBootstrap.json?.code !== 'auth_invalid') {
    fail('expired_token_contract_mismatch', 'Expired bootstrap token did not fail with auth_invalid.', {
      status: expiredBootstrap.response.status,
      body: expiredBootstrap.json ?? expiredBootstrap.text,
    });
  }
  results.steps.expiredToken = {
    ok: true,
    status: expiredBootstrap.response.status,
    code: expiredBootstrap.json.code,
    message: expiredBootstrap.json.message ?? null,
  };

  const jar = new Map();
  const bootstrap = await requestJson(`${apiBase}/management/session/bootstrap`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ agentId, token: validToken }),
    jar,
  });
  if (!bootstrap.response.ok || !bootstrap.json?.ok) {
    fail('bootstrap_failed', 'Valid bootstrap failed.', {
      status: bootstrap.response.status,
      body: bootstrap.json ?? bootstrap.text,
    });
  }
  const csrfToken = jar.get('xclaw_csrf') ?? '';
  const mgmtCookie = jar.get('xclaw_mgmt') ?? '';
  if (!csrfToken || !mgmtCookie) {
    fail('bootstrap_cookie_missing', 'Bootstrap succeeded but management cookies were missing.', {
      cookies: Array.from(jar.keys()),
    });
  }
  results.steps.bootstrap = {
    ok: true,
    status: bootstrap.response.status,
    cookies: Array.from(jar.keys()),
    sessionExpiresAt: bootstrap.json?.session?.expiresAt ?? null,
  };

  const sessionAgents = await requestJson(`${apiBase}/management/session/agents`, {
    headers: { 'x-csrf-token': csrfToken },
    jar,
  });
  if (!sessionAgents.response.ok || !sessionAgents.json?.ok) {
    fail('session_agents_failed', 'Management session agents read failed.', {
      status: sessionAgents.response.status,
      body: sessionAgents.json ?? sessionAgents.text,
    });
  }
  results.steps.sessionAgents = {
    ok: true,
    activeAgentId: sessionAgents.json.activeAgentId,
    managedAgents: sessionAgents.json.managedAgents ?? [],
  };

  const agentState = await requestJson(
    `${apiBase}/management/agent-state?agentId=${encodeURIComponent(agentId)}&chainKey=${encodeURIComponent(chainKey)}`,
    { jar }
  );
  if (!agentState.response.ok || !agentState.json?.ok) {
    fail('agent_state_failed', 'Management agent-state read failed.', {
      status: agentState.response.status,
      body: agentState.json ?? agentState.text,
    });
  }
  results.steps.agentState = {
    ok: true,
    publicStatus: agentState.json?.agent?.publicStatus ?? null,
    chainEnabled: agentState.json?.chainPolicy?.chainEnabled ?? null,
  };

  const defaultChainGet = await requestJson(`${apiBase}/management/default-chain?agentId=${encodeURIComponent(agentId)}`, {
    headers: { 'x-csrf-token': csrfToken },
    jar,
  });
  if (!defaultChainGet.response.ok || !defaultChainGet.json?.ok || !defaultChainGet.json?.chainKey) {
    fail('default_chain_get_failed', 'Default-chain get failed.', {
      status: defaultChainGet.response.status,
      body: defaultChainGet.json ?? defaultChainGet.text,
    });
  }
  const currentChainKey = String(defaultChainGet.json.chainKey);
  results.steps.defaultChainRead = {
    ok: true,
    chainKey: currentChainKey,
    source: defaultChainGet.json.source ?? null,
  };

  const updateBatch = await requestJson(`${apiBase}/management/default-chain/update-batch`, {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      'x-csrf-token': csrfToken,
    },
    body: JSON.stringify({ chainKey: currentChainKey }),
    jar,
  });
  if (!updateBatch.response.ok || !updateBatch.json?.ok || Number(updateBatch.json.successCount ?? 0) < 1) {
    fail('default_chain_update_batch_failed', 'Default-chain update-batch with CSRF failed.', {
      status: updateBatch.response.status,
      body: updateBatch.json ?? updateBatch.text,
    });
  }
  results.steps.defaultChainWriteWithCsrf = {
    ok: true,
    successCount: updateBatch.json.successCount,
    failureCount: updateBatch.json.failureCount,
  };

  const noCsrfWrite = await requestJson(`${apiBase}/management/default-chain/update-batch`, {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
    },
    body: JSON.stringify({ chainKey: currentChainKey }),
    jar,
  });
  if (noCsrfWrite.response.status !== 401 || noCsrfWrite.json?.code !== 'csrf_invalid') {
    fail('csrf_write_contract_mismatch', 'CSRF-less write did not fail with csrf_invalid.', {
      status: noCsrfWrite.response.status,
      body: noCsrfWrite.json ?? noCsrfWrite.text,
    });
  }
  results.steps.defaultChainWriteWithoutCsrf = {
    ok: true,
    status: noCsrfWrite.response.status,
    code: noCsrfWrite.json.code,
  };

  console.log(JSON.stringify({ ok: true, ...results }, null, 2));
}

main().catch((error) => {
  fail('unexpected_error', 'Unhandled management bootstrap verifier failure.', {
    error: error instanceof Error ? error.message : String(error),
  });
});
