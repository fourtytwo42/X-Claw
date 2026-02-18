'use client';

import { useRouter } from 'next/navigation';

import {
  type ChainKey,
  type DashboardChainKey,
  useActiveChainKey,
  useDashboardChainKey,
  useChainOptions,
  useDashboardChainOptions
} from '@/lib/active-chain';

type ChainHeaderControlProps = {
  includeAll?: boolean;
  className?: string;
  id?: string;
};

export function ChainHeaderControl({ includeAll = false, className, id = 'chain-select' }: ChainHeaderControlProps) {
  const router = useRouter();
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

  const onChange = (next: ChainKey) => {
    setChainKey(next);
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
    </div>
  );
}
