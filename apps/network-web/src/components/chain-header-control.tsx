'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

import {
  type ChainKey,
  type DashboardChainKey,
  useActiveChainKey,
  useDashboardChainKey,
  useChainOptions,
  useDashboardChainOptions,
  syncManagedAgentsDefaultChain,
} from '@/lib/active-chain';

type ChainHeaderControlProps = {
  includeAll?: boolean;
  className?: string;
  id?: string;
};

export function ChainHeaderControl({ includeAll = false, className, id = 'chain-select' }: ChainHeaderControlProps) {
  const router = useRouter();
  const [syncError, setSyncError] = useState<string | null>(null);
  const [chainKey, setChainKey] = useActiveChainKey();
  const [dashboardChainKey, setDashboardChainKey] = useDashboardChainKey();
  const chainOptions = useChainOptions();
  const dashboardChainOptions = useDashboardChainOptions();

  if (includeAll) {
    const onChange = (next: DashboardChainKey) => {
      setDashboardChainKey(next);
      router.refresh();
    };

    return (
      <div className={className ?? 'chain-header-control'}>
        <label className="sr-only" htmlFor={id}>
          Network
        </label>
        <select
          id={id}
          value={dashboardChainKey}
          onChange={(e) => onChange(e.target.value as DashboardChainKey)}
          className="chain-select"
        >
          {dashboardChainOptions.map((opt) => (
            <option key={opt.key} value={opt.key}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>
    );
  }

  const onChange = async (next: ChainKey) => {
    const previous = chainKey;
    setChainKey(next);
    setSyncError(null);
    const synced = await syncManagedAgentsDefaultChain(next);
    if (!synced.ok) {
      setChainKey(previous);
      setSyncError(synced.message ?? 'Failed to sync selected network.');
    }
    router.refresh();
  };

  return (
    <div className={className ?? 'chain-header-control'}>
      <label className="sr-only" htmlFor={id}>
        Network
      </label>
      <select id={id} value={chainKey} onChange={(e) => onChange(e.target.value as ChainKey)} className="chain-select">
        {chainOptions.map((opt) => (
          <option key={opt.key} value={opt.key}>
            {opt.label}
          </option>
        ))}
      </select>
      {syncError ? <p role="status">{syncError}</p> : null}
    </div>
  );
}
