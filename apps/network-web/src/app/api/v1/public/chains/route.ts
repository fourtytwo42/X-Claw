import type { NextRequest } from 'next/server';

import { successResponse } from '@/lib/errors';
import { listEnabledChains } from '@/lib/chains';
import { getRequestId } from '@/lib/request-id';

export const runtime = 'nodejs';

export async function GET(req: NextRequest) {
  const requestId = getRequestId(req);
  const includeHidden = req.nextUrl.searchParams.get('includeHidden') === 'true';

  const items = listEnabledChains()
    .filter((cfg) => includeHidden || cfg.uiVisible !== false)
    .map((cfg) => ({
      chainKey: cfg.chainKey,
      family: cfg.family ?? 'evm',
      enabled: cfg.enabled !== false,
      uiVisible: cfg.uiVisible !== false,
      displayName: cfg.displayName ?? cfg.chainKey,
      chainId: cfg.chainId ?? null,
      nativeCurrency: {
        name: cfg.nativeCurrency?.name ?? cfg.nativeCurrency?.symbol ?? 'Native',
        symbol: cfg.nativeCurrency?.symbol ?? 'ETH',
        decimals: cfg.nativeCurrency?.decimals ?? 18,
      },
      explorerBaseUrl: cfg.explorerBaseUrl ?? null,
      capabilities: {
        wallet: cfg.capabilities?.wallet ?? true,
        trade: cfg.capabilities?.trade ?? false,
        limitOrders: cfg.capabilities?.limitOrders ?? false,
        x402: cfg.capabilities?.x402 ?? false,
        faucet: cfg.capabilities?.faucet ?? false,
        deposits: cfg.capabilities?.deposits ?? false,
      },
    }));

  return successResponse({ ok: true, chains: items }, 200, requestId);
}

