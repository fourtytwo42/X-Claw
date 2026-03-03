#!/usr/bin/env node

const BASE_URL = process.env.XCLAW_E2E_BASE_URL || 'http://127.0.0.1:3000';
const API_BASE = `${BASE_URL.replace(/\/$/, '')}/api/v1`;
const DEMO_AGENT_ID = process.env.XCLAW_E2E_DEMO_AGENT_ID || 'ag_slice7';
const DEMO_AGENT_API_KEY = process.env.XCLAW_E2E_DEMO_AGENT_API_KEY || 'slice7_token_abc12345';
const AGENT_ID = process.env.XCLAW_E2E_AGENT_ID || '';
const AGENT_API_KEY = process.env.XCLAW_E2E_AGENT_API_KEY || '';
const SELF_AGENT_ID = process.env.XCLAW_E2E_SELF_FAUCET_AGENT_ID || '';
const SELF_AGENT_API_KEY = process.env.XCLAW_E2E_SELF_FAUCET_AGENT_API_KEY || '';
const CHAIN_KEY = process.env.XCLAW_E2E_CHAIN_KEY || 'base_sepolia';

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
  const ok = Boolean(condition);
  record(ok, name, details);
  return ok;
}

async function requestAgent({ agentId, apiKey, routePath, method = 'POST', body }) {
  const response = await fetch(`${API_BASE}${routePath}`, {
    method,
    headers: {
      'content-type': 'application/json',
      authorization: `Bearer ${apiKey}`,
      'idempotency-key': `faucet-ct-${Date.now()}-${Math.random().toString(16).slice(2, 10)}`,
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
    console.log(
      JSON.stringify(
        {
          ok: false,
          blocker: 'server_unreachable',
          details: {
            status: health.status || null,
            error: health.error || null,
            baseUrl: BASE_URL,
          },
        },
        null,
        2
      )
    );
    process.exit(1);
  }

  const demoResponse = await requestAgent({
    agentId: DEMO_AGENT_ID,
    apiKey: DEMO_AGENT_API_KEY,
    routePath: '/agent/faucet/request',
    body: {
      schemaVersion: 1,
      agentId: DEMO_AGENT_ID,
      chainKey: CHAIN_KEY,
      assets: ['native'],
    },
  });
  expect(demoResponse.status === 400, 'demo_agent_block_status_400', demoResponse);
  expect(demoResponse.body?.code === 'payload_invalid', 'demo_agent_block_payload_invalid', demoResponse.body);

  if (!AGENT_ID || !AGENT_API_KEY) {
    record(true, 'non_demo_tests_skipped_missing_env', {
      requiredEnv: ['XCLAW_E2E_AGENT_ID', 'XCLAW_E2E_AGENT_API_KEY'],
    });
  } else {
    const nonDemoNetworks = await requestAgent({
      agentId: AGENT_ID,
      apiKey: AGENT_API_KEY,
      method: 'GET',
      routePath: '/agent/faucet/networks',
    });
    expect(nonDemoNetworks.status === 200, 'non_demo_networks_status_200', nonDemoNetworks);
    const configuredNetwork = Array.isArray(nonDemoNetworks.body?.networks)
      ? nonDemoNetworks.body.networks.find((entry) => entry?.chainKey === CHAIN_KEY)
      : null;
    expect(Boolean(configuredNetwork), 'configured_network_present', { chainKey: CHAIN_KEY });

    const nonDemoFaucet = await requestAgent({
      agentId: AGENT_ID,
      apiKey: AGENT_API_KEY,
      routePath: '/agent/faucet/request',
      body: {
        schemaVersion: 1,
        agentId: AGENT_ID,
        chainKey: CHAIN_KEY,
        assets: ['native', 'wrapped', 'stable'],
      },
    });

    const knownDeterministicFailures = new Set([
      'rate_limited',
      'payload_invalid',
      'faucet_recipient_not_eligible',
      'faucet_fee_too_low_for_chain',
      'faucet_native_insufficient',
      'faucet_wrapped_insufficient',
      'faucet_stable_insufficient',
      'faucet_send_preflight_failed',
      'faucet_rpc_unavailable',
      'faucet_config_invalid',
    ]);

    if (nonDemoFaucet.status >= 200 && nonDemoFaucet.status < 300) {
      expect(typeof nonDemoFaucet.body?.txHash === 'string' && nonDemoFaucet.body.txHash.length > 0, 'non_demo_success_has_tx_hash', nonDemoFaucet.body);
    } else {
      expect(nonDemoFaucet.body?.code !== 'internal_error', 'non_demo_failure_not_internal_error', nonDemoFaucet.body);
      expect(knownDeterministicFailures.has(String(nonDemoFaucet.body?.code || '')), 'non_demo_failure_is_deterministic_code', nonDemoFaucet.body);
      expect(typeof nonDemoFaucet.body?.requestId === 'string' && nonDemoFaucet.body.requestId.length > 0, 'non_demo_failure_has_request_id', nonDemoFaucet.body);
    }

    if (SELF_AGENT_ID && SELF_AGENT_API_KEY) {
      const selfRecipient = await requestAgent({
        agentId: SELF_AGENT_ID,
        apiKey: SELF_AGENT_API_KEY,
        routePath: '/agent/faucet/request',
        body: {
          schemaVersion: 1,
          agentId: SELF_AGENT_ID,
          chainKey: CHAIN_KEY,
          assets: ['native'],
        },
      });
      expect(selfRecipient.status === 400, 'self_recipient_block_status_400', selfRecipient);
      expect(selfRecipient.body?.code === 'faucet_recipient_not_eligible', 'self_recipient_block_code', selfRecipient.body);
    } else {
      record(true, 'self_recipient_block_skipped_missing_env', {
        requiredEnv: ['XCLAW_E2E_SELF_FAUCET_AGENT_ID', 'XCLAW_E2E_SELF_FAUCET_AGENT_API_KEY'],
      });
    }
  }

  const ok = state.failed === 0;
  console.log(
    JSON.stringify(
      {
        ok,
        passed: state.passed,
        failed: state.failed,
        checks: state.checks,
      },
      null,
      2
    )
  );

  if (!ok) {
    process.exit(1);
  }
}

main().catch((error) => {
  console.log(
    JSON.stringify(
      {
        ok: false,
        blocker: 'faucet_contract_test_exception',
        error: String(error?.message || error),
      },
      null,
      2
    )
  );
  process.exit(1);
});
