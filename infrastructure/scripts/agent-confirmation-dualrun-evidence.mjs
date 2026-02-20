#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';

const root = process.cwd();
const report = {
  ok: true,
  startedAt: new Date().toISOString(),
  checks: [],
};

function check(ok, name, details = {}) {
  report.checks.push({ ok, name, details });
  if (!ok) report.ok = false;
}

function read(relPath) {
  return fs.readFileSync(path.join(root, relPath), 'utf8');
}

function mustInclude(haystack, needle) {
  return haystack.includes(needle);
}

function mustNotInclude(haystack, needle) {
  return !haystack.includes(needle);
}

function runStaticAssertions() {
  const migration = read('infrastructure/migrations/0026_slice117_agent_watcher_provenance.sql').toLowerCase();
  const tradeRoute = read('apps/network-web/src/app/api/v1/trades/[tradeId]/status/route.ts');
  const transferMirrorRoute = read('apps/network-web/src/app/api/v1/agent/transfer-approvals/mirror/route.ts');
  const transferDecisionRoute = read('apps/network-web/src/app/api/v1/management/transfer-approvals/decision/route.ts');
  const depositRoute = read('apps/network-web/src/app/api/v1/management/deposit/route.ts');
  const runtimeCli = read('apps/agent-runtime/xclaw_agent/cli.py');
  const tradeStatusSchema = read('packages/shared-schemas/json/trade-status.schema.json').toLowerCase();
  const transferMirrorSchema = read('packages/shared-schemas/json/agent-transfer-approvals-mirror-request.schema.json').toLowerCase();

  // Dual-run parity assertions: migration columns/constraints present.
  const migrationNeedles = [
    "alter table if exists trades",
    "add column if not exists observed_by",
    "add column if not exists observation_source",
    "add column if not exists confirmation_count",
    "add column if not exists observed_at",
    "add column if not exists watcher_run_id",
    "add column if not exists comparator_mismatch",
    "alter table if exists agent_transfer_approval_mirror",
    "alter table if exists wallet_balance_snapshots",
    "alter table if exists deposit_events",
    "legacy_server_poller",
  ];
  const missingMigrationNeedles = migrationNeedles.filter((needle) => !mustInclude(migration, needle));
  check(missingMigrationNeedles.length === 0, 'parity.migration_columns_and_constraints_present', { missing: missingMigrationNeedles });

  // Deposit comparator tagging present in write path.
  check(
    mustInclude(depositRoute, "'legacy_server_poller'") && mustInclude(depositRoute, "'server_poller_dual_run'"),
    'parity.deposit_poller_comparator_tagging_present',
    {},
  );

  // Runtime emits watcher metadata.
  check(
    mustInclude(runtimeCli, '"observedBy": "agent_watcher"') &&
      mustInclude(runtimeCli, '"watcherRunId": _watcher_run_id()') &&
      mustInclude(runtimeCli, '"observationSource": "local_send_result"'),
    'parity.runtime_trade_status_emits_watcher_metadata',
    {},
  );

  check(
    mustInclude(runtimeCli, '"observedBy": str(flow.get("observedBy") or "agent_watcher")') &&
      mustInclude(runtimeCli, '"watcherRunId": str(flow.get("watcherRunId") or _watcher_run_id())'),
    'parity.runtime_transfer_mirror_emits_watcher_metadata',
    {},
  );

  // Schema contracts include watcher provenance fields.
  check(
    mustInclude(tradeStatusSchema, '"observedby"') &&
      mustInclude(tradeStatusSchema, '"observationsource"') &&
      mustInclude(tradeStatusSchema, '"confirmationcount"') &&
      mustInclude(tradeStatusSchema, '"watcherrunid"'),
    'parity.trade_status_schema_has_watcher_fields',
    {},
  );

  check(
    mustInclude(transferMirrorSchema, '"observedby"') &&
      mustInclude(transferMirrorSchema, '"observationsource"') &&
      mustInclude(transferMirrorSchema, '"confirmationcount"') &&
      mustInclude(transferMirrorSchema, '"watcherrunid"'),
    'parity.transfer_mirror_schema_has_watcher_fields',
    {},
  );

  // Cross-talk regression assertions.
  check(
    mustInclude(tradeRoute, "reason: 'agent_canonical_terminal_delivery'") &&
      mustNotInclude(tradeRoute, 'buildWebTradeResultProdMessage') &&
      mustNotInclude(tradeRoute, 'isTradeTerminalStatus'),
    'crosstalk.trade_status_terminal_server_fanout_removed',
    {},
  );

  check(
    mustInclude(transferMirrorRoute, "reason: 'agent_canonical_terminal_delivery'") &&
      mustNotInclude(transferMirrorRoute, 'buildWebTransferResultProdMessage') &&
      mustNotInclude(transferMirrorRoute, 'isTransferTerminalStatus'),
    'crosstalk.transfer_mirror_terminal_server_fanout_removed',
    {},
  );

  check(
    mustInclude(transferDecisionRoute, "reason: 'agent_canonical_terminal_delivery'") &&
      mustNotInclude(transferDecisionRoute, 'buildWebTransferResultProdMessage') &&
      mustNotInclude(transferDecisionRoute, 'isTransferTerminalStatus'),
    'crosstalk.transfer_decision_terminal_server_fanout_removed',
    {},
  );

  // Negative-path coverage assertions (contract-level/static).
  check(
    mustInclude(tradeRoute, "if (row.agent_id !== auth.agentId)") &&
      mustInclude(tradeRoute, "code: 'auth_invalid'") &&
      mustInclude(tradeRoute, 'Authenticated agent is not allowed to update this trade.'),
    'negative.contract_wrong_agent_trade_update_rejected',
    {},
  );

  check(
    mustInclude(tradeRoute, "kind: 'missing_tx_hash'") &&
      mustInclude(tradeRoute, 'txHash is required for real-mode execution transitions.'),
    'negative.contract_missing_txhash_rejected',
    {},
  );

  check(
    mustInclude(transferMirrorRoute, 'validatePayload<AgentTransferApprovalsMirrorRequest>') &&
      mustInclude(transferMirrorSchema, '"enum": ["agent_watcher", "legacy_server_poller", null]'),
    'negative.contract_transfer_mirror_provenance_schema_validation',
    {},
  );
}

try {
  runStaticAssertions();
} catch (error) {
  check(false, 'script.execution_error', { message: String(error?.message || error) });
}

report.finishedAt = new Date().toISOString();
report.passed = report.checks.filter((c) => c.ok).length;
report.failed = report.checks.filter((c) => !c.ok).length;

const out = JSON.stringify(report, null, 2);
if (report.ok) {
  console.log(out);
  process.exit(0);
}
console.error(out);
process.exit(1);
