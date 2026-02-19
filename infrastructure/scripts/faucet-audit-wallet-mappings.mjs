#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';

import { Wallet, isAddress } from 'ethers';
import pg from 'pg';

const { Client } = pg;

function envSuffix(chainKey) {
  return String(chainKey || '')
    .replace(/[^a-zA-Z0-9]/g, '_')
    .toUpperCase();
}

function readChainConfigs() {
  const root = process.cwd();
  const dir = path.join(root, 'config', 'chains');
  const files = fs.readdirSync(dir).filter((f) => f.endsWith('.json')).sort();
  return files.map((f) => JSON.parse(fs.readFileSync(path.join(dir, f), 'utf8')));
}

function faucetEnabledChains() {
  const cfgs = readChainConfigs();
  return cfgs
    .filter((cfg) => cfg && cfg.enabled !== false && cfg.capabilities && cfg.capabilities.faucet === true)
    .map((cfg) => String(cfg.chainKey || '').trim())
    .filter(Boolean);
}

function faucetSignerForChain(chainKey) {
  const scopedKey = process.env[`XCLAW_TESTNET_FAUCET_PRIVATE_KEY_${envSuffix(chainKey)}`] || '';
  const fallbackKey = process.env.XCLAW_TESTNET_FAUCET_PRIVATE_KEY || '';
  const privateKey = String(scopedKey || fallbackKey).trim();
  if (!privateKey) {
    return null;
  }
  try {
    const wallet = new Wallet(privateKey);
    return wallet.address.toLowerCase();
  } catch {
    return null;
  }
}

async function main() {
  const databaseUrl = process.env.DATABASE_URL;
  if (!databaseUrl) {
    console.log(
      JSON.stringify({
        ok: false,
        code: 'missing_env',
        message: 'DATABASE_URL is required.',
        actionHint: 'Export DATABASE_URL and retry.'
      })
    );
    process.exit(1);
  }

  const chains = faucetEnabledChains();
  const signerMap = {};
  for (const chain of chains) {
    signerMap[chain] = faucetSignerForChain(chain);
  }

  const client = new Client({ connectionString: databaseUrl });
  await client.connect();
  try {
    const q = await client.query(
      `
      select agent_id, chain_key, address, updated_at
      from agent_wallets
      where chain_key = any($1::text[])
      order by chain_key asc, updated_at desc
      `,
      [chains]
    );

    const findings = [];
    for (const row of q.rows) {
      const chainKey = String(row.chain_key || '');
      const address = String(row.address || '').toLowerCase();
      const signer = String(signerMap[chainKey] || '').toLowerCase();
      if (!signer || !isAddress(address)) {
        continue;
      }
      if (address === signer) {
        findings.push({
          agentId: row.agent_id,
          chainKey,
          address,
          faucetAddress: signer,
          updatedAt: row.updated_at
        });
      }
    }

    console.log(
      JSON.stringify({
        ok: true,
        code: 'ok',
        chains,
        faucetSignerByChain: signerMap,
        totalWalletRows: q.rowCount || 0,
        impactedCount: findings.length,
        impacted: findings
      })
    );
  } finally {
    await client.end();
  }
}

main().catch((error) => {
  console.log(
    JSON.stringify({
      ok: false,
      code: 'audit_failed',
      message: error instanceof Error ? error.message : String(error),
      actionHint: 'Verify database connectivity and faucet private key env config.'
    })
  );
  process.exit(1);
});
