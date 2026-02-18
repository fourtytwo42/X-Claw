'use client';

import { useEffect, useMemo, useState } from 'react';

export type ChainKey = 'base_sepolia' | 'kite_ai_testnet';
export type DashboardChainKey = 'all' | ChainKey;

export const CHAIN_OPTIONS: Array<{ key: ChainKey; label: string }> = [
  { key: 'base_sepolia', label: 'Base Sepolia' },
  { key: 'kite_ai_testnet', label: 'Kite AI Testnet' }
];

export const DASHBOARD_CHAIN_OPTIONS: Array<{ key: DashboardChainKey; label: string }> = [
  { key: 'all', label: 'All chains' },
  ...CHAIN_OPTIONS
];

export function nativeSymbolForChainKey(chainKey: ChainKey): string {
  return chainKey === 'kite_ai_testnet' ? 'KITE' : 'ETH';
}

const STORAGE_KEY = 'xclaw_chain_key';
const DASHBOARD_STORAGE_KEY = 'xclaw_dashboard_chain_key';
const EVENT_NAME = 'xclaw:chain_changed';
const DASHBOARD_EVENT_NAME = 'xclaw:dashboard_chain_changed';

function isChainKey(value: unknown): value is ChainKey {
  return value === 'base_sepolia' || value === 'kite_ai_testnet';
}

function isDashboardChainKey(value: unknown): value is DashboardChainKey {
  return value === 'all' || isChainKey(value);
}

export function getStoredChainKey(): ChainKey {
  if (typeof window === 'undefined') {
    return 'base_sepolia';
  }
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (isChainKey(raw)) {
      return raw;
    }
  } catch {
    // ignore
  }
  return 'base_sepolia';
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

  useEffect(() => {
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

    window.addEventListener(EVENT_NAME, onEvent);
    window.addEventListener('storage', onStorage);
    return () => {
      window.removeEventListener(EVENT_NAME, onEvent);
      window.removeEventListener('storage', onStorage);
    };
  }, []);

  const set = (next: ChainKey) => {
    setChainKey(next);
    setStoredChainKey(next);
  };

  const label = useMemo(() => CHAIN_OPTIONS.find((opt) => opt.key === chainKey)?.label ?? chainKey, [chainKey]);

  return [chainKey, set, label];
}

export function useDashboardChainKey(): [DashboardChainKey, (next: DashboardChainKey) => void, string] {
  const [chainKey, setChainKey] = useState<DashboardChainKey>(() => getStoredDashboardChainKey());

  useEffect(() => {
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

    window.addEventListener(DASHBOARD_EVENT_NAME, onEvent);
    window.addEventListener('storage', onStorage);
    return () => {
      window.removeEventListener(DASHBOARD_EVENT_NAME, onEvent);
      window.removeEventListener('storage', onStorage);
    };
  }, []);

  const set = (next: DashboardChainKey) => {
    setChainKey(next);
    setStoredDashboardChainKey(next);
  };

  const label = useMemo(() => DASHBOARD_CHAIN_OPTIONS.find((opt) => opt.key === chainKey)?.label ?? chainKey, [chainKey]);

  return [chainKey, set, label];
}
