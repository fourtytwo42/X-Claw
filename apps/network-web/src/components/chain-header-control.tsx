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

type ChainOption = { key: string; label: string };

function isTestnetOption(option: ChainOption): boolean {
  const key = option.key.toLowerCase();
  const label = option.label.toLowerCase();
  return key.includes('testnet') || key.includes('sepolia') || label.includes('testnet') || label.includes('sepolia');
}

function sortAndGroupOptions<T extends ChainOption>(options: T[]): { mainnets: T[]; testnets: T[] } {
  const sorted = [...options].sort((a, b) => a.label.localeCompare(b.label));
  const mainnets = sorted.filter((opt) => !isTestnetOption(opt));
  const testnets = sorted.filter((opt) => isTestnetOption(opt));
  return { mainnets, testnets };
}

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
  const groupedChainOptions = sortAndGroupOptions(chainOptions);
  const groupedDashboardChainOptions = sortAndGroupOptions(
    dashboardChainOptions.filter((opt) => opt.key !== 'all')
  );

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
          <option value="all">All chains</option>
          {groupedDashboardChainOptions.mainnets.length > 0 ? (
            <optgroup label="Mainnets">
              {groupedDashboardChainOptions.mainnets.map((opt) => (
                <option key={opt.key} value={opt.key}>
                  {opt.label}
                </option>
              ))}
            </optgroup>
          ) : null}
          {groupedDashboardChainOptions.testnets.length > 0 ? (
            <optgroup label="Testnets">
              {groupedDashboardChainOptions.testnets.map((opt) => (
                <option key={opt.key} value={opt.key}>
                  {opt.label}
                </option>
              ))}
            </optgroup>
          ) : null}
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
        {groupedChainOptions.mainnets.length > 0 ? (
          <optgroup label="Mainnets">
            {groupedChainOptions.mainnets.map((opt) => (
              <option key={opt.key} value={opt.key}>
                {opt.label}
              </option>
            ))}
          </optgroup>
        ) : null}
        {groupedChainOptions.testnets.length > 0 ? (
          <optgroup label="Testnets">
            {groupedChainOptions.testnets.map((opt) => (
              <option key={opt.key} value={opt.key}>
                {opt.label}
              </option>
            ))}
          </optgroup>
        ) : null}
      </select>
      {syncError ? <p role="status">{syncError}</p> : null}
    </div>
  );
}
