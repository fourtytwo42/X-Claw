'use client';

import { useEffect, useMemo, useState } from 'react';

export type ChainKey = string;
export type DashboardChainKey = 'all' | ChainKey;

type ChainDescriptor = {
  chainKey: string;
  displayName: string;
  nativeCurrency?: { symbol?: string; decimals?: number };
};

const STORAGE_KEY = 'xclaw_chain_key';
const DASHBOARD_STORAGE_KEY = 'xclaw_dashboard_chain_key';
const CHAIN_REGISTRY_STORAGE_KEY = 'xclaw_chain_registry_v1';
const EVENT_NAME = 'xclaw:chain_changed';
const DASHBOARD_EVENT_NAME = 'xclaw:dashboard_chain_changed';
const REGISTRY_EVENT_NAME = 'xclaw:chain_registry_changed';
const FALLBACK_CHAIN = 'base_sepolia';

const FALLBACK_REGISTRY: ChainDescriptor[] = [
  { chainKey: 'base_mainnet', displayName: 'Base Mainnet', nativeCurrency: { symbol: 'ETH', decimals: 18 } },
  { chainKey: 'base_sepolia', displayName: 'Base Sepolia', nativeCurrency: { symbol: 'ETH', decimals: 18 } },
  { chainKey: 'hedera_mainnet', displayName: 'Hedera Mainnet', nativeCurrency: { symbol: 'HBAR', decimals: 8 } },
  { chainKey: 'hedera_testnet', displayName: 'Hedera Testnet', nativeCurrency: { symbol: 'HBAR', decimals: 8 } },
  { chainKey: 'ethereum', displayName: 'Ethereum', nativeCurrency: { symbol: 'ETH', decimals: 18 } },
  { chainKey: 'ethereum_sepolia', displayName: 'Ethereum Sepolia', nativeCurrency: { symbol: 'ETH', decimals: 18 } },
  { chainKey: 'kite_ai_mainnet', displayName: 'KiteAI Mainnet', nativeCurrency: { symbol: 'KITE', decimals: 18 } },
  { chainKey: 'kite_ai_testnet', displayName: 'KiteAI Testnet', nativeCurrency: { symbol: 'KITE', decimals: 18 } },
  { chainKey: 'adi_mainnet', displayName: 'ADI Mainnet', nativeCurrency: { symbol: 'ADI', decimals: 18 } },
  { chainKey: 'adi_testnet', displayName: 'ADI Network AB Testnet', nativeCurrency: { symbol: 'ADI', decimals: 18 } },
  { chainKey: 'og_mainnet', displayName: '0G Mainnet', nativeCurrency: { symbol: '0G', decimals: 18 } },
  { chainKey: 'og_testnet', displayName: '0G Galileo Testnet', nativeCurrency: { symbol: '0G', decimals: 18 } },
];

function fallbackNativeDecimalsFor(chainKey: string, nativeSymbol: string): number {
  const fromChain = FALLBACK_REGISTRY.find((row) => row.chainKey === chainKey)?.nativeCurrency?.decimals;
  if (typeof fromChain === 'number' && Number.isFinite(fromChain) && fromChain > 0) {
    return Math.floor(fromChain);
  }
  const upperSymbol = nativeSymbol.trim().toUpperCase();
  if (upperSymbol === 'HBAR') {
    return 8;
  }
  return 18;
}

function loadRegistryFromStorage(): ChainDescriptor[] {
  if (typeof window === 'undefined') {
    return FALLBACK_REGISTRY;
  }
  try {
    const raw = window.localStorage.getItem(CHAIN_REGISTRY_STORAGE_KEY);
    if (!raw) {
      return FALLBACK_REGISTRY;
    }
    const parsed = JSON.parse(raw) as {
      chains?: Array<{ chainKey?: unknown; displayName?: unknown; nativeCurrency?: { symbol?: unknown; decimals?: unknown } }>;
    };
    const rows = Array.isArray(parsed?.chains) ? parsed.chains : [];
    const normalized = rows
      .map((row) => {
        const chainKey = String(row?.chainKey ?? '').trim();
        if (!chainKey) {
          return null;
        }
        const displayName = String(row?.displayName ?? chainKey).trim() || chainKey;
        const symbolRaw = row?.nativeCurrency?.symbol;
        const nativeSymbol = typeof symbolRaw === 'string' && symbolRaw.trim() ? symbolRaw.trim() : 'ETH';
        const decimalsRaw = row?.nativeCurrency?.decimals;
        const nativeDecimals =
          typeof decimalsRaw === 'number' && Number.isFinite(decimalsRaw) && decimalsRaw > 0
            ? Math.floor(decimalsRaw)
            : fallbackNativeDecimalsFor(chainKey, nativeSymbol);
        return { chainKey, displayName, nativeCurrency: { symbol: nativeSymbol, decimals: nativeDecimals } };
      })
      .filter(Boolean) as ChainDescriptor[];
    return normalized.length > 0 ? normalized : FALLBACK_REGISTRY;
  } catch {
    return FALLBACK_REGISTRY;
  }
}

export function getChainOptions(): Array<{ key: ChainKey; label: string }> {
  return loadRegistryFromStorage().map((row) => ({ key: row.chainKey, label: row.displayName }));
}

export function getDashboardChainOptions(): Array<{ key: DashboardChainKey; label: string }> {
  return [{ key: 'all', label: 'All chains' }, ...getChainOptions()];
}

export function nativeSymbolForChainKey(chainKey: ChainKey): string {
  const registry = loadRegistryFromStorage();
  const found = registry.find((row) => row.chainKey === chainKey);
  if (found?.nativeCurrency?.symbol && found.nativeCurrency.symbol.trim()) {
    return found.nativeCurrency.symbol.trim().toUpperCase();
  }
  return 'ETH';
}

export function nativeDecimalsForChainKey(chainKey: ChainKey): number {
  const registry = loadRegistryFromStorage();
  const found = registry.find((row) => row.chainKey === chainKey);
  const symbol = found?.nativeCurrency?.symbol ?? '';
  const decimals = found?.nativeCurrency?.decimals;
  if (typeof decimals === 'number' && Number.isFinite(decimals) && decimals > 0) {
    return Math.floor(decimals);
  }
  return fallbackNativeDecimalsFor(chainKey, symbol);
}

function isChainKey(value: unknown): value is ChainKey {
  if (typeof value !== 'string') {
    return false;
  }
  const normalized = value.trim();
  if (!normalized) {
    return false;
  }
  return getChainOptions().some((row) => row.key === normalized);
}

function isDashboardChainKey(value: unknown): value is DashboardChainKey {
  return value === 'all' || isChainKey(value);
}

async function fetchAndStoreRegistry(): Promise<void> {
  if (typeof window === 'undefined') {
    return;
  }
  try {
    const res = await fetch('/api/v1/public/chains', { cache: 'no-store', credentials: 'same-origin' });
    if (!res.ok) {
      return;
    }
    const payload = (await res.json()) as {
      chains?: Array<{ chainKey?: string; displayName?: string; nativeCurrency?: { symbol?: string; decimals?: number } }>;
    };
    const chains = Array.isArray(payload?.chains) ? payload.chains : [];
    if (chains.length === 0) {
      return;
    }
    window.localStorage.setItem(CHAIN_REGISTRY_STORAGE_KEY, JSON.stringify({ chains }));
    window.dispatchEvent(new CustomEvent(REGISTRY_EVENT_NAME));
  } catch {
    // ignore network/cache failures and keep fallback options
  }
}

function getCsrfToken(): string | null {
  if (typeof document === 'undefined') {
    return null;
  }
  const raw = document.cookie
    .split(';')
    .map((part) => part.trim())
    .find((part) => part.startsWith('xclaw_csrf='));
  if (!raw) {
    return null;
  }
  return decodeURIComponent(raw.split('=')[1] ?? '');
}

async function fetchRuntimeManagedDefaultChain(): Promise<ChainKey | null> {
  if (typeof window === 'undefined') {
    return null;
  }
  try {
    const sessionRes = await fetch('/api/v1/management/session/agents', {
      method: 'GET',
      credentials: 'same-origin',
      cache: 'no-store'
    });
    if (!sessionRes.ok) {
      return null;
    }
    const sessionPayload = (await sessionRes.json()) as { activeAgentId?: string };
    const activeAgentId = String(sessionPayload?.activeAgentId ?? '').trim();
    if (!activeAgentId) {
      return null;
    }
    const defaultRes = await fetch(
      `/api/v1/management/default-chain?agentId=${encodeURIComponent(activeAgentId)}`,
      {
        method: 'GET',
        credentials: 'same-origin',
        cache: 'no-store'
      }
    );
    if (!defaultRes.ok) {
      return null;
    }
    const payload = (await defaultRes.json()) as { chainKey?: unknown };
    const chainKey = typeof payload?.chainKey === 'string' ? payload.chainKey.trim() : '';
    return chainKey || null;
  } catch {
    return null;
  }
}

export async function syncManagedAgentsDefaultChain(chainKey: ChainKey): Promise<{ ok: boolean; message?: string }> {
  if (typeof window === 'undefined') {
    return { ok: true };
  }
  const csrf = getCsrfToken();
  try {
    const response = await fetch('/api/v1/management/default-chain/update-batch', {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'content-type': 'application/json',
        ...(csrf ? { 'x-csrf-token': csrf } : {})
      },
      body: JSON.stringify({ chainKey })
    });
    if (!response.ok) {
      const payload = (await response.json().catch(() => null)) as { message?: string } | null;
      return { ok: false, message: payload?.message ?? 'Failed to sync default chain.' };
    }
    const payload = (await response.json()) as { failureCount?: number };
    if (Number(payload?.failureCount ?? 0) > 0) {
      return { ok: false, message: 'Default chain sync partially failed for managed agents.' };
    }
    return { ok: true };
  } catch {
    return { ok: false, message: 'Default chain sync request failed.' };
  }
}

export function getStoredChainKey(): ChainKey {
  if (typeof window === 'undefined') {
    return FALLBACK_CHAIN;
  }
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (isChainKey(raw)) {
      return raw;
    }
  } catch {
    // ignore
  }
  return FALLBACK_CHAIN;
}

export function getStoredDashboardChainKey(): DashboardChainKey {
  if (typeof window === 'undefined') {
    return 'all';
  }
  try {
    const raw = window.localStorage.getItem(DASHBOARD_STORAGE_KEY);
    if (isDashboardChainKey(raw)) {
      return raw;
    }
  } catch {
    // ignore
  }
  return 'all';
}

export function setStoredChainKey(chainKey: ChainKey): void {
  if (typeof window === 'undefined') {
    return;
  }
  window.localStorage.setItem(STORAGE_KEY, chainKey);
  window.dispatchEvent(new CustomEvent(EVENT_NAME, { detail: { chainKey } }));
}

export function setStoredDashboardChainKey(chainKey: DashboardChainKey): void {
  if (typeof window === 'undefined') {
    return;
  }
  window.localStorage.setItem(DASHBOARD_STORAGE_KEY, chainKey);
  window.dispatchEvent(new CustomEvent(DASHBOARD_EVENT_NAME, { detail: { chainKey } }));
}

export function useActiveChainKey(): [ChainKey, (next: ChainKey) => void, string] {
  const [chainKey, setChainKey] = useState<ChainKey>(() => getStoredChainKey());
  const [options, setOptions] = useState<Array<{ key: ChainKey; label: string }>>(() => getChainOptions());

  useEffect(() => {
    fetchAndStoreRegistry().finally(() => {
      const nextOptions = getChainOptions();
      setOptions(nextOptions);
      setChainKey((current) => (nextOptions.some((opt) => opt.key === current) ? current : FALLBACK_CHAIN));
    });
    fetchRuntimeManagedDefaultChain().then((runtimeChain) => {
      if (!runtimeChain) {
        return;
      }
      const optionsNow = getChainOptions();
      if (!optionsNow.some((item) => item.key === runtimeChain)) {
        return;
      }
      setChainKey(runtimeChain);
      setStoredChainKey(runtimeChain);
    });

    const onRegistry = () => {
      const nextOptions = getChainOptions();
      setOptions(nextOptions);
      setChainKey((current) => (nextOptions.some((opt) => opt.key === current) ? current : FALLBACK_CHAIN));
    };

    const onEvent = (event: Event) => {
      const custom = event as CustomEvent<{ chainKey?: unknown }>;
      const next = custom?.detail?.chainKey;
      if (isChainKey(next)) {
        setChainKey(next);
      }
    };

    const onStorage = (event: StorageEvent) => {
      if (event.key !== STORAGE_KEY) {
        return;
      }
      if (isChainKey(event.newValue)) {
        setChainKey(event.newValue);
      }
    };

    window.addEventListener(REGISTRY_EVENT_NAME, onRegistry);
    window.addEventListener(EVENT_NAME, onEvent);
    window.addEventListener('storage', onStorage);
    return () => {
      window.removeEventListener(REGISTRY_EVENT_NAME, onRegistry);
      window.removeEventListener(EVENT_NAME, onEvent);
      window.removeEventListener('storage', onStorage);
    };
  }, []);

  const set = (next: ChainKey) => {
    setChainKey(next);
    setStoredChainKey(next);
  };

  const label = useMemo(() => options.find((opt) => opt.key === chainKey)?.label ?? chainKey, [chainKey, options]);

  return [chainKey, set, label];
}

export function useDashboardChainKey(): [DashboardChainKey, (next: DashboardChainKey) => void, string] {
  const [chainKey, setChainKey] = useState<DashboardChainKey>(() => getStoredDashboardChainKey());
  const [options, setOptions] = useState<Array<{ key: DashboardChainKey; label: string }>>(() => getDashboardChainOptions());

  useEffect(() => {
    fetchAndStoreRegistry().finally(() => {
      const nextOptions = getDashboardChainOptions();
      setOptions(nextOptions);
      setChainKey((current) => (nextOptions.some((opt) => opt.key === current) ? current : 'all'));
    });

    const onRegistry = () => {
      const nextOptions = getDashboardChainOptions();
      setOptions(nextOptions);
      setChainKey((current) => (nextOptions.some((opt) => opt.key === current) ? current : 'all'));
    };

    const onEvent = (event: Event) => {
      const custom = event as CustomEvent<{ chainKey?: unknown }>;
      const next = custom?.detail?.chainKey;
      if (isDashboardChainKey(next)) {
        setChainKey(next);
      }
    };

    const onStorage = (event: StorageEvent) => {
      if (event.key !== DASHBOARD_STORAGE_KEY) {
        return;
      }
      if (isDashboardChainKey(event.newValue)) {
        setChainKey(event.newValue);
      }
    };

    window.addEventListener(REGISTRY_EVENT_NAME, onRegistry);
    window.addEventListener(DASHBOARD_EVENT_NAME, onEvent);
    window.addEventListener('storage', onStorage);
    return () => {
      window.removeEventListener(REGISTRY_EVENT_NAME, onRegistry);
      window.removeEventListener(DASHBOARD_EVENT_NAME, onEvent);
      window.removeEventListener('storage', onStorage);
    };
  }, []);

  const set = (next: DashboardChainKey) => {
    setChainKey(next);
    setStoredDashboardChainKey(next);
  };

  const label = useMemo(() => options.find((opt) => opt.key === chainKey)?.label ?? chainKey, [chainKey, options]);

  return [chainKey, set, label];
}

export function useChainOptions(): Array<{ key: ChainKey; label: string }> {
  const [options, setOptions] = useState<Array<{ key: ChainKey; label: string }>>(() => getChainOptions());
  useEffect(() => {
    fetchAndStoreRegistry().finally(() => setOptions(getChainOptions()));
    const onRegistry = () => setOptions(getChainOptions());
    window.addEventListener(REGISTRY_EVENT_NAME, onRegistry);
    return () => window.removeEventListener(REGISTRY_EVENT_NAME, onRegistry);
  }, []);
  return options;
}

export function useDashboardChainOptions(): Array<{ key: DashboardChainKey; label: string }> {
  const [options, setOptions] = useState<Array<{ key: DashboardChainKey; label: string }>>(() => getDashboardChainOptions());
  useEffect(() => {
    fetchAndStoreRegistry().finally(() => setOptions(getDashboardChainOptions()));
    const onRegistry = () => setOptions(getDashboardChainOptions());
    window.addEventListener(REGISTRY_EVENT_NAME, onRegistry);
    return () => window.removeEventListener(REGISTRY_EVENT_NAME, onRegistry);
  }, []);
  return options;
}
