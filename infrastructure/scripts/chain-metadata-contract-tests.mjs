import fs from 'node:fs';
import path from 'node:path';

const root = process.cwd();
const chainsDir = path.join(root, 'config', 'chains');
const sotPath = path.join(root, 'docs', 'XCLAW_SOURCE_OF_TRUTH.md');
const routePath = path.join(root, 'apps', 'network-web', 'src', 'app', 'api', 'v1', 'public', 'chains', 'route.ts');
const fallbackPath = path.join(root, 'apps', 'network-web', 'src', 'lib', 'active-chain.ts');

const START = '<!-- CURRENT_CHAIN_METADATA_MATRIX_START -->';
const END = '<!-- CURRENT_CHAIN_METADATA_MATRIX_END -->';

function fail(message, details = undefined) {
  const payload = { ok: false, message, ...(details ? { details } : {}) };
  console.error(JSON.stringify(payload, null, 2));
  process.exit(1);
}

function readEnabledMatrixFromConfig() {
  return fs.readdirSync(chainsDir)
    .filter((file) => file.endsWith('.json'))
    .sort()
    .map((file) => JSON.parse(fs.readFileSync(path.join(chainsDir, file), 'utf8')))
    .filter((cfg) => cfg.enabled !== false)
    .filter((cfg) => ['evm', 'solana'].includes(String(cfg.family ?? 'evm')))
    .map((cfg) => ({
      chainKey: cfg.chainKey,
      family: cfg.family ?? 'evm',
      uiVisible: cfg.uiVisible !== false,
      displayName: cfg.displayName ?? cfg.chainKey,
      chainId: cfg.chainId ?? null,
      nativeCurrency: {
        name: cfg.nativeCurrency?.name ?? null,
        symbol: cfg.nativeCurrency?.symbol ?? null,
        decimals: cfg.nativeCurrency?.decimals ?? null,
      },
      explorerBaseUrl: cfg.explorerBaseUrl ?? null,
      rpc: {
        primary: cfg.rpc?.primary ?? null,
        fallback: cfg.rpc?.fallback ?? null,
      },
    }));
}

function readMatrixFromSourceOfTruth() {
  const text = fs.readFileSync(sotPath, 'utf8');
  const start = text.indexOf(START);
  const end = text.indexOf(END);
  if (start === -1 || end === -1 || end <= start) {
    fail('current_chain_metadata_matrix_missing');
  }
  const block = text.slice(start + START.length, end);
  const match = block.match(/```json\s*([\s\S]*?)```/);
  if (!match) {
    fail('current_chain_metadata_matrix_unparseable');
  }
  try {
    return JSON.parse(match[1]);
  } catch (error) {
    fail('current_chain_metadata_matrix_invalid_json', { error: String(error?.message ?? error) });
  }
}

function stable(value) {
  return JSON.stringify(value, null, 2);
}

function assertDocMatrixMatchesConfig() {
  const expected = readEnabledMatrixFromConfig();
  const actual = readMatrixFromSourceOfTruth();
  if (stable(actual) !== stable(expected)) {
    fail('source_of_truth_metadata_matrix_mismatch', { expected, actual });
  }
}

function assertHistoricalSectionsMarked() {
  const text = fs.readFileSync(sotPath, 'utf8');
  const required = [
    'Slice 97 Ethereum + Ethereum Sepolia Wallet-First Onboarding Contract (Historical, Superseded by 3.3-3.4 Current Chain Matrices)',
    'Slice 98 Chain Metadata Normalization + Truthful Capability Gating Contract (Historical, Superseded by 3.3-3.4 Current Chain Matrices)',
  ];
  for (const marker of required) {
    if (!text.includes(marker)) {
      fail('historical_metadata_marker_missing', { marker });
    }
  }
}

function assertPublicRouteIsConfigDriven() {
  const text = fs.readFileSync(routePath, 'utf8');
  const requiredSnippets = [
    "displayName: cfg.displayName ?? cfg.chainKey",
    'chainId: cfg.chainId ?? null',
    "name: cfg.nativeCurrency?.name ?? cfg.nativeCurrency?.symbol ?? 'Native'",
    "symbol: cfg.nativeCurrency?.symbol ?? 'ETH'",
    'decimals: cfg.nativeCurrency?.decimals ?? 18',
    'explorerBaseUrl: cfg.explorerBaseUrl ?? null',
  ];
  for (const snippet of requiredSnippets) {
    if (!text.includes(snippet)) {
      fail('public_chain_route_metadata_mapping_drift', { snippet });
    }
  }
}

function parseFallbackRegistry() {
  const text = fs.readFileSync(fallbackPath, 'utf8');
  const blockMatch = text.match(/const FALLBACK_REGISTRY: ChainDescriptor\[] = \[([\s\S]*?)\];/);
  if (!blockMatch) {
    fail('fallback_registry_missing');
  }
  const block = blockMatch[1];
  const rows = [];
  const regex = /\{\s*chainKey:\s*'([^']+)',\s*displayName:\s*'([^']+)',\s*nativeCurrency:\s*\{\s*symbol:\s*'([^']+)',\s*decimals:\s*(\d+)\s*\}\s*\}/g;
  let match;
  while ((match = regex.exec(block)) !== null) {
    rows.push({ chainKey: match[1], displayName: match[2], nativeCurrency: { symbol: match[3], decimals: Number(match[4]) } });
  }
  return rows;
}

function assertFallbackRegistryMatchesConfig() {
  const configMap = new Map(readEnabledMatrixFromConfig().map((row) => [row.chainKey, row]));
  const rows = parseFallbackRegistry();
  const visibleCovered = [
    'base_mainnet',
    'base_sepolia',
    'ethereum',
    'ethereum_sepolia',
    'kite_ai_mainnet',
    'kite_ai_testnet',
    'adi_mainnet',
    'adi_testnet',
    'og_mainnet',
    'og_testnet',
    'solana_devnet',
    'solana_testnet',
    'solana_localnet',
    'solana_mainnet_beta',
  ];
  for (const chainKey of visibleCovered) {
    const fallback = rows.find((row) => row.chainKey === chainKey);
    if (!fallback) {
      fail('fallback_registry_entry_missing', { chainKey });
    }
    const cfg = configMap.get(chainKey);
    if (!cfg) {
      fail('enabled_chain_missing_from_config_matrix', { chainKey });
    }
    if (fallback.displayName !== cfg.displayName) {
      fail('fallback_registry_display_name_mismatch', { chainKey, expected: cfg.displayName, actual: fallback.displayName });
    }
    if (fallback.nativeCurrency.symbol !== cfg.nativeCurrency.symbol || fallback.nativeCurrency.decimals !== cfg.nativeCurrency.decimals) {
      fail('fallback_registry_native_currency_mismatch', {
        chainKey,
        expected: cfg.nativeCurrency,
        actual: fallback.nativeCurrency,
      });
    }
  }
  if (rows.some((row) => row.chainKey === 'hardhat_local')) {
    fail('fallback_registry_should_not_expose_hidden_hardhat_local');
  }
}

function assertPriorityChains() {
  const map = new Map(readEnabledMatrixFromConfig().map((row) => [row.chainKey, row]));
  const expected = {
    hardhat_local: { uiVisible: false, displayName: 'Hardhat Local', chainId: 31337, explorerBaseUrl: null, rpcPrimary: 'http://127.0.0.1:8545' },
    base_sepolia: { uiVisible: true, displayName: 'Base Sepolia', chainId: 84532, explorerBaseUrl: 'https://sepolia.basescan.org', rpcPrimary: 'https://sepolia.base.org' },
    ethereum_sepolia: { uiVisible: true, displayName: 'Ethereum Sepolia', chainId: 11155111, explorerBaseUrl: 'https://sepolia.etherscan.io', rpcPrimary: 'https://ethereum-sepolia-rpc.publicnode.com' },
    solana_localnet: { uiVisible: true, displayName: 'Solana Localnet', chainId: 100, explorerBaseUrl: 'http://127.0.0.1:8899', rpcPrimary: 'http://127.0.0.1:8899' },
    solana_devnet: { uiVisible: true, displayName: 'Solana Devnet', chainId: 103, explorerBaseUrl: 'https://explorer.solana.com/?cluster=devnet', rpcPrimary: 'https://api.devnet.solana.com' },
  };
  for (const [chainKey, exp] of Object.entries(expected)) {
    const row = map.get(chainKey);
    if (!row) fail('priority_chain_missing', { chainKey });
    if (row.uiVisible !== exp.uiVisible || row.displayName !== exp.displayName || row.chainId !== exp.chainId || row.explorerBaseUrl !== exp.explorerBaseUrl || row.rpc.primary !== exp.rpcPrimary) {
      fail('priority_chain_metadata_mismatch', { chainKey, expected: exp, actual: row });
    }
  }
}

assertDocMatrixMatchesConfig();
assertHistoricalSectionsMarked();
assertPublicRouteIsConfigDriven();
assertFallbackRegistryMatchesConfig();
assertPriorityChains();

console.log(JSON.stringify({ ok: true, checks: 5, priorities: ['hardhat_local','base_sepolia','ethereum_sepolia','solana_localnet','solana_devnet'] }, null, 2));
