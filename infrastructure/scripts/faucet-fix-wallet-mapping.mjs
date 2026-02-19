#!/usr/bin/env node

import { isAddress } from 'ethers';
import pg from 'pg';

const { Client } = pg;

function parseArg(flag) {
  const idx = process.argv.indexOf(flag);
  if (idx === -1) {
    return '';
  }
  return String(process.argv[idx + 1] || '').trim();
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

  const agentId = parseArg('--agent-id');
  const chainKey = parseArg('--chain');
  const address = parseArg('--address').toLowerCase();
  const apply = process.argv.includes('--apply');

  if (!agentId || !chainKey || !address) {
    console.log(
      JSON.stringify({
        ok: false,
        code: 'invalid_input',
        message: 'Missing required args.',
        actionHint: 'Use --agent-id <id> --chain <chain_key> --address <0x...> [--apply].'
      })
    );
    process.exit(2);
  }
  if (!isAddress(address)) {
    console.log(
      JSON.stringify({
        ok: false,
        code: 'invalid_input',
        message: 'Address is not a valid EVM address.',
        actionHint: 'Provide a 0x-prefixed 20-byte address.'
      })
    );
    process.exit(2);
  }

  const client = new Client({ connectionString: databaseUrl });
  await client.connect();
  try {
    const current = await client.query(
      `
      select agent_id, chain_key, address, updated_at
      from agent_wallets
      where agent_id = $1 and chain_key = $2
      limit 1
      `,
      [agentId, chainKey]
    );
    if ((current.rowCount || 0) === 0) {
      console.log(
        JSON.stringify({
          ok: false,
          code: 'not_found',
          message: 'agent_wallets row not found for agent/chain.',
          details: { agentId, chainKey }
        })
      );
      process.exit(1);
    }

    const before = current.rows[0];
    if (!apply) {
      console.log(
        JSON.stringify({
          ok: true,
          code: 'dry_run',
          message: 'No change applied (dry-run).',
          details: {
            agentId,
            chainKey,
            beforeAddress: String(before.address || '').toLowerCase(),
            nextAddress: address,
            applyHint: 'Re-run with --apply to execute update.'
          }
        })
      );
      return;
    }

    const upd = await client.query(
      `
      update agent_wallets
      set address = $3, updated_at = now()
      where agent_id = $1 and chain_key = $2
      returning agent_id, chain_key, address, updated_at
      `,
      [agentId, chainKey, address]
    );
    console.log(
      JSON.stringify({
        ok: true,
        code: 'ok',
        message: 'Agent wallet mapping updated.',
        details: {
          agentId,
          chainKey,
          beforeAddress: String(before.address || '').toLowerCase(),
          afterAddress: String(upd.rows[0]?.address || '').toLowerCase()
        }
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
      code: 'update_failed',
      message: error instanceof Error ? error.message : String(error)
    })
  );
  process.exit(1);
});
