'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';

import { getAgentAvatarPalette, getAgentInitial } from '@/lib/agent-avatar-color';

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

export function ActiveAgentSidebarLink({ itemClassName, activeClassName, showLabel = false, labelClassName }: ActiveAgentSidebarLinkProps) {
  const pathname = usePathname();
  const [managedAgentIds, setManagedAgentIds] = useState<string[]>([]);
  const [agentNames, setAgentNames] = useState<Record<string, string>>({});

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const response = await fetch('/api/v1/management/session/agents', { credentials: 'same-origin', cache: 'no-store' });
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

        const names: Record<string, string> = {};
        await Promise.all(
          ids.map(async (id) => {
            try {
              const profileResponse = await fetch(`/api/v1/public/agents/${encodeURIComponent(id)}`, { cache: 'no-store' });
              if (!profileResponse.ok) {
                names[id] = id;
                return;
              }
              const profile = (await profileResponse.json()) as PublicAgentPayload;
              names[id] = (profile.agent?.agent_name ?? '').trim() || id;
            } catch {
              names[id] = id;
            }
          })
        );
        if (!cancelled) {
          setAgentNames(names);
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
      {managedAgentIds.map((agentId) => {
        const agentName = agentNames[agentId] ?? agentId;
        const title = agentName || agentId;
        const isActive = pathname === `/agents/${agentId}`;
        const className = isActive && activeClassName ? `${itemClassName} ${activeClassName}` : itemClassName;
        const initial = getAgentInitial(agentName, agentId);
        const avatarPalette = getAgentAvatarPalette(agentId);
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
