'use client';

import { useEffect, useMemo, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { fetchWithTimeout, uiFetchTimeoutMs } from '@/lib/fetch-timeout';

const MANAGED_AGENT_IDS_KEY = 'xclaw_managed_agent_ids';
const MANAGED_AGENT_TOKENS_KEY = 'xclaw_managed_agent_tokens';

function parseStoredAgentIds(raw: string | null): string[] {
  if (!raw) {
    return [];
  }
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) {
      return [];
    }
    return parsed.filter((item): item is string => typeof item === 'string' && item.length > 0);
  } catch {
    return [];
  }
}

export function rememberManagedAgent(agentId: string): void {
  if (typeof window === 'undefined') {
    return;
  }
  const current = parseStoredAgentIds(window.localStorage.getItem(MANAGED_AGENT_IDS_KEY));
  if (current.includes(agentId)) {
    return;
  }
  const next = [...current, agentId];
  window.localStorage.setItem(MANAGED_AGENT_IDS_KEY, JSON.stringify(next));
}

function clearManagedAgents(): void {
  if (typeof window === 'undefined') {
    return;
  }
  window.localStorage.removeItem(MANAGED_AGENT_IDS_KEY);
}

function parseStoredManagedAgentTokens(): Record<string, string> {
  if (typeof window === 'undefined') {
    return {};
  }
  try {
    const raw = window.localStorage.getItem(MANAGED_AGENT_TOKENS_KEY);
    if (!raw) {
      return {};
    }
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
      return {};
    }
    const out: Record<string, string> = {};
    for (const [agentId, token] of Object.entries(parsed)) {
      const id = String(agentId ?? '').trim();
      const value = String(token ?? '').trim();
      if (!id || !value) {
        continue;
      }
      out[id] = value;
    }
    return out;
  } catch {
    return {};
  }
}

export function ManagementHeaderControls() {
  const router = useRouter();
  const pathname = usePathname();
  const [agentIds, setAgentIds] = useState<string[]>([]);
  const [agentNames, setAgentNames] = useState<Record<string, string>>({});
  const [active, setActive] = useState<string>('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    const stored = parseStoredAgentIds(window.localStorage.getItem(MANAGED_AGENT_IDS_KEY));
    setAgentIds(stored);

    if (pathname?.startsWith('/agents/')) {
      const currentPathAgent = pathname.split('/')[2] ?? '';
      if (currentPathAgent) {
        setActive(currentPathAgent);
      }
    }

    void fetchWithTimeout('/api/v1/management/session/agents', { credentials: 'same-origin', cache: 'no-store' }, uiFetchTimeoutMs())
      .then(async (response) => {
        if (!response.ok) {
          return null;
        }
        const payload = (await response.json()) as { managedAgents?: string[]; activeAgentId?: string };
        return payload;
      })
      .then((payload) => {
        if (!payload) {
          return;
        }

        const sessionIds = Array.from(new Set((payload.managedAgents ?? []).map((item) => String(item ?? '').trim()).filter(Boolean)));
        setAgentIds(sessionIds);
        if (payload.activeAgentId) {
          setActive(payload.activeAgentId);
        }
        window.localStorage.setItem(MANAGED_AGENT_IDS_KEY, JSON.stringify(sessionIds));
      })
      .catch(() => {
        // no-op
      });
  }, [pathname]);

  useEffect(() => {
    if (agentIds.length === 0) {
      setAgentNames({});
      return;
    }
    let cancelled = false;
    async function loadNames() {
      const names: Record<string, string> = {};
      await Promise.all(
        agentIds.map(async (agentId) => {
          try {
            const response = await fetchWithTimeout(
              `/api/v1/public/agents/${encodeURIComponent(agentId)}`,
              { cache: 'no-store' },
              uiFetchTimeoutMs(),
            );
            if (!response.ok) {
              names[agentId] = 'Unnamed Agent';
              return;
            }
            const payload = (await response.json()) as { agent?: { agent_name?: string | null } };
            names[agentId] = payload.agent?.agent_name?.trim() || 'Unnamed Agent';
          } catch {
            names[agentId] = 'Unnamed Agent';
          }
        })
      );
      if (!cancelled) {
        setAgentNames(names);
      }
    }
    void loadNames();
    return () => {
      cancelled = true;
    };
  }, [agentIds]);

  const canRender = useMemo(() => agentIds.length > 0, [agentIds]);

  if (!canRender) {
    return null;
  }

  const onSelect = async (nextAgentId: string) => {
    setActive(nextAgentId);
    const token = parseStoredManagedAgentTokens()[nextAgentId];
    if (token) {
      try {
        await fetchWithTimeout(
          '/api/v1/management/session/select',
          {
            method: 'POST',
            headers: { 'content-type': 'application/json' },
            credentials: 'same-origin',
            body: JSON.stringify({ agentId: nextAgentId, token })
          },
          uiFetchTimeoutMs(),
        );
      } catch {
        // Best effort: page-level bootstrap fallback still runs.
      }
    }
    router.push(`/agents/${nextAgentId}`);
  };

  const onLogout = async () => {
    setBusy(true);
    try {
      await fetchWithTimeout(
        '/api/v1/management/logout',
        {
          method: 'POST',
          credentials: 'same-origin'
        },
        uiFetchTimeoutMs(),
      );
    } finally {
      clearManagedAgents();
      setAgentIds([]);
      setActive('');
      setBusy(false);
      router.refresh();
    }
  };

  return (
    <div className="management-header-controls">
      <label className="sr-only" htmlFor="managed-agent-select">
        Managed agent selector
      </label>
      <select
        id="managed-agent-select"
        value={active || agentIds[0]}
        onChange={(event) => {
          void onSelect(event.target.value);
        }}
        className="managed-agent-select"
      >
        {agentIds.map((agentId) => (
          <option key={agentId} value={agentId}>
            {agentNames[agentId] || 'Unnamed Agent'}
          </option>
        ))}
      </select>
      <button type="button" className="logout-button" disabled={busy} onClick={onLogout}>
        {busy ? 'Logging out...' : 'Logout'}
      </button>
    </div>
  );
}
