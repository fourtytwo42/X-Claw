import fs from 'node:fs';
import path from 'node:path';

const root = process.cwd();
const results = [];

function readJson(relPath) {
  return JSON.parse(fs.readFileSync(path.join(root, relPath), 'utf8'));
}

function readText(relPath) {
  return fs.readFileSync(path.join(root, relPath), 'utf8');
}

function expect(condition, label, details = {}) {
  if (!condition) {
    throw new Error(`${label} failed ${JSON.stringify(details)}`);
  }
  results.push(label);
}

function run() {
  const solLocal = readJson('config/chains/solana_localnet.json');
  const solDev = readJson('config/chains/solana_devnet.json');
  const solMain = readJson('config/chains/solana_mainnet_beta.json');
  const solTest = readJson('config/chains/solana_testnet.json');
  expect(solLocal?.capabilities?.x402 === true, 'solana_localnet_x402_enabled');
  expect(solDev?.capabilities?.x402 === true, 'solana_devnet_x402_enabled');
  expect(solMain?.capabilities?.x402 === false, 'solana_mainnet_x402_deferred');
  expect(solTest?.capabilities?.x402 === false, 'solana_testnet_x402_deferred');

  const x402Networks = readJson('config/x402/networks.json');
  expect(x402Networks?.networks?.solana_localnet?.enabled === true, 'x402_networks_solana_localnet_enabled');
  expect(x402Networks?.networks?.solana_devnet?.enabled === true, 'x402_networks_solana_devnet_enabled');
  expect(x402Networks?.networks?.solana_mainnet_beta?.enabled === false, 'x402_networks_solana_mainnet_deferred');

  const inboundSchema = readJson('packages/shared-schemas/json/agent-x402-inbound-proposed-request.schema.json');
  const kindEnum = inboundSchema?.properties?.assetKind?.enum || [];
  expect(Array.isArray(kindEnum) && kindEnum.includes('token') && kindEnum.includes('erc20'), 'x402_asset_kind_token_and_alias');
  const addrAnyOf = inboundSchema?.properties?.assetAddress?.anyOf || [];
  const hasHex = addrAnyOf.some((x) => x?.pattern === '^0x[a-fA-F0-9]{40}$');
  const hasBase58 = addrAnyOf.some((x) => x?.pattern === '^[1-9A-HJ-NP-Za-km-z]{32,64}$');
  expect(hasHex && hasBase58, 'x402_asset_address_family_neutral');

  const outboundSchema = readJson('packages/shared-schemas/json/agent-x402-outbound-proposed-request.schema.json');
  const txAnyOf = outboundSchema?.properties?.txHash?.anyOf || [];
  const hasHexTx = txAnyOf.some((x) => x?.pattern === '^0x[a-fA-F0-9]{64}$');
  const hasSigTx = txAnyOf.some((x) => x?.pattern === '^[1-9A-HJ-NP-Za-km-z]{64,128}$');
  expect(hasHexTx && hasSigTx, 'x402_txid_family_neutral');

  const payTokenized = readText('apps/network-web/src/app/api/v1/x402/pay/[agentId]/[linkToken]/route.ts');
  expect(payTokenized.includes('verifyX402Settlement'), 'x402_tokenized_route_uses_verifier');
  expect(payTokenized.includes("req.headers.get('x-tx-id')"), 'x402_tokenized_route_supports_tx_id_header');

  const payCompat = readText('apps/network-web/src/app/api/v1/x402/pay/[agentId]/route.ts');
  expect(payCompat.includes('verifyX402Settlement'), 'x402_compat_route_uses_verifier');
  expect(payCompat.includes("req.headers.get('x-tx-id')"), 'x402_compat_route_supports_tx_id_header');

  console.log(JSON.stringify({ ok: true, count: results.length, results }, null, 2));
}

try {
  run();
} catch (error) {
  console.error(
    JSON.stringify(
      {
        ok: false,
        error: error instanceof Error ? error.message : String(error),
        passed: results,
      },
      null,
      2
    )
  );
  process.exit(1);
}
