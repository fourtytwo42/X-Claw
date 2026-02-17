'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useMemo, useState } from 'react';

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
};

export function ActiveAgentSidebarLink({ itemClassName, activeClassName }: ActiveAgentSidebarLinkProps) {
  const pathname = usePathname();
  const [agentId, setAgentId] = useState<string>('');
  const [agentName, setAgentName] = useState<string>('');

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const response = await fetch('/api/v1/management/session/agents', { credentials: 'same-origin', cache: 'no-store' });
        if (!response.ok) {
          return;
        }
        const payload = (await response.json()) as SessionAgentsPayload;
        const selected = payload.activeAgentId ?? payload.managedAgents?.[0] ?? '';
        if (!selected || cancelled) {
          return;
        }
        setAgentId(selected);

        const profileResponse = await fetch(`/api/v1/public/agents/${encodeURIComponent(selected)}`, { cache: 'no-store' });
        if (!profileResponse.ok || cancelled) {
          return;
        }
        const profile = (await profileResponse.json()) as PublicAgentPayload;
        const resolvedName = (profile.agent?.agent_name ?? '').trim();
        if (!cancelled) {
          setAgentName(resolvedName || selected);
        }
      } catch {
        // no-op
      }
    }

    void load();

    return () => {
      cancelled = true;
    };
  }, []);

  const title = useMemo(() => {
    if (!agentId) {
      return '';
    }
    return agentName || agentId;
  }, [agentId, agentName]);

  if (!agentId) {
    return null;
  }

  const isActive = pathname === `/agents/${agentId}`;
  const className = isActive && activeClassName ? `${itemClassName} ${activeClassName}` : itemClassName;
  const initial = getAgentInitial(agentName, agentId);
  const avatarPalette = useMemo(() => getAgentAvatarPalette(agentId), [agentId]);

  return (
    <Link href={`/agents/${encodeURIComponent(agentId)}`} className={className} aria-label={title} title={title}>
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
    </Link>
  );
}
