'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';

import { getAgentAvatarPalette, getAgentInitial } from '@/lib/agent-avatar-color';
import { fetchWithTimeout, uiFetchTimeoutMs } from '@/lib/fetch-timeout';

type SessionAgentsPayload = {
  managedAgents?: string[];
  activeAgentId?: string;
};

type PublicAgentPayload = {
  agent?: {
    agent_name?: string | null;
  };
};

type ActiveAgentSidebarLinkProps = {
  itemClassName: string;
  activeClassName?: string;
  showLabel?: boolean;
  labelClassName?: string;
};

const MANAGED_AGENT_IDS_KEY = 'xclaw_managed_agent_ids';
const MANAGED_AGENT_NAMES_KEY = 'xclaw_managed_agent_names';

function parseStoredManagedAgentIds(): string[] {
  if (typeof window === 'undefined') {
    return [];
  }
  try {
    const raw = window.localStorage.getItem(MANAGED_AGENT_IDS_KEY);
    if (!raw) {
      return [];
    }
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) {
      return [];
    }
    return parsed.map((item) => String(item ?? '').trim()).filter((item) => item.length > 0);
  } catch {
    return [];
  }
}

function parseStoredManagedAgentNames(): Record<string, string> {
  if (typeof window === 'undefined') {
    return {};
  }
  try {
    const raw = window.localStorage.getItem(MANAGED_AGENT_NAMES_KEY);
    if (!raw) {
      return {};
    }
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
      return {};
    }
    const out: Record<string, string> = {};
    for (const [agentId, name] of Object.entries(parsed)) {
      const normalizedId = String(agentId ?? '').trim();
      const normalizedName = String(name ?? '').trim();
      if (!normalizedId || !normalizedName) {
        continue;
      }
      out[normalizedId] = normalizedName;
    }
    return out;
  } catch {
    return {};
  }
}

function persistManagedAgentNames(next: Record<string, string>): void {
  if (typeof window === 'undefined') {
    return;
  }
  window.localStorage.setItem(MANAGED_AGENT_NAMES_KEY, JSON.stringify(next));
}

export function ActiveAgentSidebarLink({ itemClassName, activeClassName, showLabel = false, labelClassName }: ActiveAgentSidebarLinkProps) {
  const pathname = usePathname();
  const [managedAgentIds, setManagedAgentIds] = useState<string[]>([]);
  const [agentNames, setAgentNames] = useState<Record<string, string>>({});

  useEffect(() => {
    let cancelled = false;

    async function load() {
      const storedIds = parseStoredManagedAgentIds();
      const storedNames = parseStoredManagedAgentNames();
      if (storedIds.length > 0) {
        setManagedAgentIds(storedIds);
      }
      if (Object.keys(storedNames).length > 0) {
        setAgentNames(storedNames);
      }

      try {
        const response = await fetchWithTimeout(
          '/api/v1/management/session/agents',
          { credentials: 'same-origin', cache: 'no-store' },
          uiFetchTimeoutMs(3000),
        );
        if (!response.ok) {
          return;
        }
        const payload = (await response.json()) as SessionAgentsPayload;
        const ids = Array.from(
          new Set(
            [payload.activeAgentId ?? '', ...(payload.managedAgents ?? [])]
              .map((value) => String(value).trim())
              .filter((value) => value.length > 0)
          )
        );
        if (ids.length === 0 || cancelled) {
          return;
        }
        setManagedAgentIds(ids);

        if (typeof window !== 'undefined') {
          window.localStorage.setItem(MANAGED_AGENT_IDS_KEY, JSON.stringify(ids));
        }

        const names: Record<string, string> = { ...storedNames };
        await Promise.all(
          ids.map(async (id) => {
            try {
              const profileResponse = await fetchWithTimeout(
                `/api/v1/public/agents/${encodeURIComponent(id)}`,
                { cache: 'no-store' },
                uiFetchTimeoutMs(3000),
              );
              if (!profileResponse.ok) {
                return;
              }
              const profile = (await profileResponse.json()) as PublicAgentPayload;
              const resolvedName = (profile.agent?.agent_name ?? '').trim();
              if (resolvedName) {
                names[id] = resolvedName;
              }
            } catch {
              // keep best-effort cached value
            }
          })
        );
        if (!cancelled) {
          const filtered: Record<string, string> = {};
          for (const id of ids) {
            const name = String(names[id] ?? '').trim();
            if (name) {
              filtered[id] = name;
            }
          }
          setAgentNames(filtered);
          persistManagedAgentNames(filtered);
        }
      } catch {
        // no-op
      }
    }

    void load();

    return () => {
      cancelled = true;
    };
  }, [pathname]);

  if (managedAgentIds.length === 0) {
    return null;
  }

  return (
    <>
      {managedAgentIds.map((agentId, index) => {
        const resolvedName = String(agentNames[agentId] ?? '').trim();
        const title = resolvedName || agentId;
        const isActive = pathname === `/agents/${agentId}`;
        const className = isActive && activeClassName ? `${itemClassName} ${activeClassName}` : itemClassName;
        const initial = resolvedName ? getAgentInitial(resolvedName, agentId) : '?';
        const avatarPalette = getAgentAvatarPalette(agentId, index * 137);
        return (
          <Link key={`managed-${agentId}`} href={`/agents/${encodeURIComponent(agentId)}`} className={className} aria-label={title} title={title}>
            <span
              className="agent-shortcut-badge"
              style={{
                backgroundColor: avatarPalette.backgroundColor,
                borderColor: avatarPalette.borderColor,
                color: avatarPalette.textColor
              }}
            >
              {initial}
            </span>
            {showLabel ? <span className={labelClassName}>Agent</span> : null}
          </Link>
        );
      })}
    </>
  );
}
