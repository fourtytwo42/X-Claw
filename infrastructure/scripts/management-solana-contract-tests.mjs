#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';

const ROOT = process.cwd();
const state = { passed: 0, failed: 0, checks: [] };

function record(ok, name, details = {}) {
  state.checks.push({ ok, name, details });
  if (ok) state.passed += 1;
  else state.failed += 1;
}

function expect(condition, name, details = {}) {
  record(Boolean(condition), name, details);
}

function readJson(relPath) {
  return JSON.parse(fs.readFileSync(path.join(ROOT, relPath), 'utf8'));
}

function readText(relPath) {
  return fs.readFileSync(path.join(ROOT, relPath), 'utf8');
}

async function main() {
  const devnet = readJson('config/chains/solana_devnet.json');
  const mainnet = readJson('config/chains/solana_mainnet_beta.json');
  const testnet = readJson('config/chains/solana_testnet.json');

  expect(devnet?.capabilities?.deposits === true, 'solana_devnet_deposits_enabled');
  expect(mainnet?.capabilities?.deposits === true, 'solana_mainnet_deposits_enabled');
  expect(testnet?.capabilities?.deposits === false, 'solana_testnet_deposits_deferred');

  const depositSchema = readJson('packages/shared-schemas/json/management-deposit-response.schema.json');
  const depositAddressAnyOf = depositSchema?.properties?.chains?.items?.properties?.depositAddress?.anyOf;
  const txHashAnyOf = depositSchema?.properties?.chains?.items?.properties?.recentDeposits?.items?.properties?.txHash?.anyOf;
  expect(Array.isArray(depositAddressAnyOf) && depositAddressAnyOf.length >= 2, 'management_deposit_schema_family_address');
  expect(Array.isArray(txHashAnyOf) && txHashAnyOf.length >= 2, 'management_deposit_schema_family_txid');

  const withdrawSchema = readJson('packages/shared-schemas/json/management-withdraw-request.schema.json');
  expect(Array.isArray(withdrawSchema?.properties?.destination?.anyOf), 'withdraw_schema_family_destination');

  const depositRoute = readText('apps/network-web/src/app/api/v1/management/deposit/route.ts');
  expect(depositRoute.includes('syncSolanaDeposits'), 'deposit_route_has_solana_sync');
  expect(depositRoute.includes('getSignaturesForAddress'), 'deposit_route_uses_signature_stream');
  expect(depositRoute.includes('getTokenAccountsByOwner'), 'deposit_route_uses_spl_balances');

  const confirmationsHelper = readText('apps/network-web/src/lib/tx-confirmations.ts');
  expect(confirmationsHelper.includes('getSignatureStatuses'), 'confirmations_helper_solana_status');

  const chainsLib = readText('apps/network-web/src/lib/chains.ts');
  expect(chainsLib.includes('chainTxExplorerUrl'), 'chains_helper_tx_explorer_url');

  const withdrawReadHelper = readText('apps/network-web/src/lib/withdraws-read.ts');
  expect(withdrawReadHelper.includes("m.request_kind = 'withdraw'"), 'withdraws_helper_filters_request_kind');

  const managementWithdrawsRoute = readText('apps/network-web/src/app/api/v1/management/withdraws/route.ts');
  expect(managementWithdrawsRoute.includes('readWithdrawRows'), 'management_withdraws_route_uses_shared_reader');

  const agentWithdrawsRoute = readText('apps/network-web/src/app/api/v1/agent/withdraws/route.ts');
  expect(agentWithdrawsRoute.includes('authenticateAgentByToken'), 'agent_withdraws_route_agent_auth');
  expect(agentWithdrawsRoute.includes('readWithdrawRows'), 'agent_withdraws_route_reads_withdraw_projection');

  const agentWithdrawsSchema = readJson('packages/shared-schemas/json/agent-withdraws-response.schema.json');
  expect(agentWithdrawsSchema?.required?.includes('queue'), 'agent_withdraws_schema_queue_required');
  expect(agentWithdrawsSchema?.required?.includes('history'), 'agent_withdraws_schema_history_required');

  const ok = state.failed === 0;
  console.log(JSON.stringify({ ok, passed: state.passed, failed: state.failed, checks: state.checks }, null, 2));
  if (!ok) {
    process.exit(1);
  }
}

main().catch((error) => {
  console.log(
    JSON.stringify(
      {
        ok: false,
        blocker: 'management_solana_contract_test_exception',
        error: String(error?.message || error),
      },
      null,
      2
    )
  );
  process.exit(1);
});
