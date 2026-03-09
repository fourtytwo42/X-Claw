import fs from 'node:fs';
import path from 'node:path';

const root = process.cwd();

function readJson(file) {
  return JSON.parse(fs.readFileSync(file, 'utf8'));
}

function expect(condition, name, details = {}) {
  if (!condition) {
    return { ok: false, name, details };
  }
  return { ok: true, name, details };
}

function normalizeCapabilities(input = {}) {
  return {
    wallet: input.wallet ?? true,
    trade: input.trade ?? false,
    liquidity: input.liquidity ?? false,
    limitOrders: input.limitOrders ?? false,
    x402: input.x402 ?? false,
    faucet: input.faucet ?? false,
    deposits: input.deposits ?? false,
  };
}

function readEnabledMatrixFromConfig() {
  const dir = path.join(root, 'config', 'chains');
  return fs
    .readdirSync(dir)
    .filter((file) => file.endsWith('.json'))
    .map((file) => readJson(path.join(dir, file)))
    .filter((cfg) => cfg.enabled !== false && ['evm', 'solana', undefined].includes(cfg.family))
    .map((cfg) => ({
      chainKey: cfg.chainKey,
      family: cfg.family ?? 'evm',
      uiVisible: cfg.uiVisible !== false,
      capabilities: normalizeCapabilities(cfg.capabilities),
    }))
    .sort((a, b) => a.chainKey.localeCompare(b.chainKey));
}

function readMatrixFromSourceOfTruth() {
  const file = path.join(root, 'docs', 'XCLAW_SOURCE_OF_TRUTH.md');
  const source = fs.readFileSync(file, 'utf8');
  const match = source.match(
    /<!-- CURRENT_CHAIN_CAPABILITY_MATRIX_START -->\s*```json\s*([\s\S]*?)\s*```\s*<!-- CURRENT_CHAIN_CAPABILITY_MATRIX_END -->/
  );
  if (!match) {
    throw new Error('Current chain capability matrix markers not found in source-of-truth.');
  }
  const parsed = JSON.parse(match[1]);
  return parsed.sort((a, b) => String(a.chainKey).localeCompare(String(b.chainKey)));
}

function canonicalString(value) {
  return JSON.stringify(value, null, 2);
}

const checks = [];
const configMatrix = readEnabledMatrixFromConfig();
const docMatrix = readMatrixFromSourceOfTruth();

checks.push(
  expect(
    canonicalString(configMatrix) === canonicalString(docMatrix),
    'source_of_truth_current_matrix_matches_enabled_chain_configs',
    { configEntries: configMatrix.length, docEntries: docMatrix.length }
  )
);

const priorityExpected = {
  hardhat_local: { wallet: true, trade: true, liquidity: true, limitOrders: true, x402: false, faucet: false, deposits: true },
  base_sepolia: { wallet: true, trade: true, liquidity: true, limitOrders: true, x402: true, faucet: true, deposits: true },
  ethereum_sepolia: { wallet: true, trade: true, liquidity: true, limitOrders: false, x402: false, faucet: false, deposits: false },
  solana_localnet: { wallet: true, trade: true, liquidity: true, limitOrders: true, x402: true, faucet: true, deposits: true },
  solana_devnet: { wallet: true, trade: false, liquidity: false, limitOrders: false, x402: true, faucet: true, deposits: true },
};

for (const [chainKey, expectedCaps] of Object.entries(priorityExpected)) {
  const row = configMatrix.find((entry) => entry.chainKey === chainKey);
  checks.push(
    expect(
      !!row && canonicalString(row.capabilities) === canonicalString(expectedCaps),
      `${chainKey}_priority_capability_boundary`,
      { chainKey, expectedCaps, actualCaps: row?.capabilities ?? null }
    )
  );
}

const publicRoute = fs.readFileSync(path.join(root, 'apps', 'network-web', 'src', 'app', 'api', 'v1', 'public', 'chains', 'route.ts'), 'utf8');
checks.push(expect(/listEnabledChains\(\)/.test(publicRoute), 'public_chains_route_uses_enabled_chain_registry'));
checks.push(expect(/wallet:\s*cfg\.capabilities\?\.wallet \?\? true/.test(publicRoute), 'public_chains_route_wallet_from_config'));
checks.push(expect(/trade:\s*cfg\.capabilities\?\.trade \?\? false/.test(publicRoute), 'public_chains_route_trade_from_config'));
checks.push(expect(/liquidity:\s*cfg\.capabilities\?\.liquidity \?\? false/.test(publicRoute), 'public_chains_route_liquidity_from_config'));
checks.push(expect(/limitOrders:\s*cfg\.capabilities\?\.limitOrders \?\? false/.test(publicRoute), 'public_chains_route_limit_orders_from_config'));
checks.push(expect(/x402:\s*cfg\.capabilities\?\.x402 \?\? false/.test(publicRoute), 'public_chains_route_x402_from_config'));
checks.push(expect(/faucet:\s*cfg\.capabilities\?\.faucet \?\? false/.test(publicRoute), 'public_chains_route_faucet_from_config'));
checks.push(expect(/deposits:\s*cfg\.capabilities\?\.deposits \?\? false/.test(publicRoute), 'public_chains_route_deposits_from_config'));

const source = fs.readFileSync(path.join(root, 'docs', 'XCLAW_SOURCE_OF_TRUTH.md'), 'utf8');
checks.push(expect(/## 79\) Slice 97 .*Historical, Superseded by 3\.3-3\.4 Current Chain Matrices/.test(source), 'slice97_capability_contract_marked_historical'));
checks.push(expect(/## 80\) Slice 98 .*Historical, Superseded by 3\.3-3\.4 Current Chain Matrices/.test(source), 'slice98_capability_contract_marked_historical'));

const passed = checks.filter((check) => check.ok).length;
const failed = checks.filter((check) => !check.ok);

console.log(
  JSON.stringify(
    {
      ok: failed.length === 0,
      passed,
      failed: failed.length,
      checks,
    },
    null,
    2
  )
);

if (failed.length > 0) {
  process.exit(1);
}
