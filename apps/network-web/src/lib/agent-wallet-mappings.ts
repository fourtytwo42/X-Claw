import { chainCapabilityEnabled, listEnabledChains } from '@/lib/chains';
import { makeId } from '@/lib/ids';
import { withTransaction } from '@/lib/db';

type WalletRow = {
  chain_key: string;
  address: string;
  custody: string;
};

function pickCanonicalWallet(
  wallets: WalletRow[],
  preferredChainKey: string | null
): WalletRow | null {
  if (wallets.length === 0) {
    return null;
  }
  if (preferredChainKey) {
    const preferred = wallets.find((row) => row.chain_key === preferredChainKey);
    if (preferred) {
      return preferred;
    }
  }
  const baseSepolia = wallets.find((row) => row.chain_key === 'base_sepolia');
  if (baseSepolia) {
    return baseSepolia;
  }
  return wallets[0];
}

export async function ensureAgentWalletMappings(
  agentId: string,
  preferredChainKey?: string
): Promise<{ insertedCount: number }> {
  const targetChains = listEnabledChains()
    .map((chain) => chain.chainKey)
    .filter((chainKey) => chainCapabilityEnabled(chainKey, 'wallet'));

  if (targetChains.length === 0) {
    return { insertedCount: 0 };
  }

  return withTransaction(async (client) => {
    const agent = await client.query<{ agent_id: string }>(
      `
      select agent_id
      from agents
      where agent_id = $1
      for update
      `,
      [agentId]
    );
    if (agent.rowCount === 0) {
      return { insertedCount: 0 };
    }

    const existing = await client.query<WalletRow>(
      `
      select chain_key, address, custody
      from agent_wallets
      where agent_id = $1
      `,
      [agentId]
    );
    if (existing.rowCount === 0) {
      return { insertedCount: 0 };
    }

    const canonical = pickCanonicalWallet(existing.rows, preferredChainKey ?? null);
    if (!canonical) {
      return { insertedCount: 0 };
    }

    const existingChains = new Set(existing.rows.map((row) => row.chain_key));
    let insertedCount = 0;
    for (const chainKey of targetChains) {
      if (existingChains.has(chainKey)) {
        continue;
      }

      const result = await client.query(
        `
        insert into agent_wallets (
          wallet_id, agent_id, chain_key, address, custody, created_at, updated_at
        ) values ($1, $2, $3, $4, $5, now(), now())
        on conflict (agent_id, chain_key) do nothing
        `,
        [makeId('wlt'), agentId, chainKey, canonical.address, canonical.custody]
      );
      insertedCount += result.rowCount ?? 0;
    }

    return { insertedCount };
  });
}
