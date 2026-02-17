'use client';

import Image from 'next/image';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useMemo, useState } from 'react';

import { ActiveAgentSidebarLink } from '@/components/active-agent-sidebar-link';
import { MobileMoreSheet } from '@/components/mobile-more-sheet';
import { SidebarIcon } from '@/components/sidebar-icons';
import { getAgentAvatarPalette, getAgentInitial } from '@/lib/agent-avatar-color';

import styles from './primary-nav.module.css';

type PrimaryNavProps = {
  className?: string;
  desktopExtra?: React.ReactNode;
  mobileMoreContent?: React.ReactNode;
};

type NavItem = {
  id: 'dashboard' | 'explore' | 'approvals' | 'settings' | 'howto';
  href: string;
  label: string;
  icon: 'dashboard' | 'explore' | 'approvals' | 'settings' | 'howto';
};

type PublicAgentPayload = {
  agent?: {
    agent_name?: string | null;
  };
};

const FAVORITES_KEY = 'xclaw_explore_favorite_agent_ids';

const PRIMARY_ITEMS: NavItem[] = [
  { id: 'dashboard', href: '/dashboard', label: 'Dashboard', icon: 'dashboard' },
  { id: 'explore', href: '/explore', label: 'Explore', icon: 'explore' },
  { id: 'approvals', href: '/approvals', label: 'Approvals', icon: 'approvals' }
];

const BOTTOM_ITEMS: NavItem[] = [
  { id: 'settings', href: '/settings', label: 'Settings', icon: 'settings' },
  { id: 'howto', href: '/how-to', label: 'How To', icon: 'howto' }
];

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

function isActivePath(pathname: string, href: string): boolean {
  if (href === '/explore') {
    return pathname === '/explore' || pathname === '/agents';
  }
  return pathname === href;
}

export function PrimaryNav({ className, desktopExtra, mobileMoreContent }: PrimaryNavProps) {
  const pathname = usePathname();
  const [mobileMoreOpen, setMobileMoreOpen] = useState(false);
  const [bookmarkedAgentIds, setBookmarkedAgentIds] = useState<string[]>([]);
  const [bookmarkedAgentNames, setBookmarkedAgentNames] = useState<Record<string, string>>({});
  const [activeManagedAgentId, setActiveManagedAgentId] = useState<string | null>(null);
  const [usingServerTracked, setUsingServerTracked] = useState(false);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    const load = () => {
      try {
        const raw = window.localStorage.getItem(FAVORITES_KEY);
        const parsed = raw ? (JSON.parse(raw) as unknown) : [];
        const localIds = Array.isArray(parsed)
          ? Array.from(new Set(parsed.filter((item): item is string => typeof item === 'string' && item.length > 0)))
          : [];
        setBookmarkedAgentIds(localIds);
        setUsingServerTracked(false);

        void fetch('/api/v1/management/session/agents', { credentials: 'same-origin', cache: 'no-store' })
          .then(async (response) => {
            if (!response.ok) {
              return null;
            }
            return (await response.json()) as { activeAgentId?: string };
          })
          .then(async (payload) => {
            const activeAgentId = String(payload?.activeAgentId ?? '').trim();
            if (!activeAgentId) {
              setActiveManagedAgentId(null);
              return;
            }
            setActiveManagedAgentId(activeAgentId);
            const trackedResponse = await fetch(
              `/api/v1/management/tracked-agents?agentId=${encodeURIComponent(activeAgentId)}&chainKey=base_sepolia`,
              { credentials: 'same-origin', cache: 'no-store' }
            );
            if (!trackedResponse.ok) {
              return;
            }
            const trackedPayload = (await trackedResponse.json()) as {
              items?: Array<{ trackedAgentId?: string; agentName?: string | null }>;
            };
            const items = Array.isArray(trackedPayload.items) ? trackedPayload.items : [];
            const ids = Array.from(
              new Set(
                items
                  .map((item) => String(item?.trackedAgentId ?? '').trim())
                  .filter((item) => item.length > 0)
              )
            );
            const names: Record<string, string> = {};
            for (const item of items) {
              const id = String(item?.trackedAgentId ?? '').trim();
              if (!id) {
                continue;
              }
              names[id] = String(item?.agentName ?? 'Tracked Agent').trim() || 'Tracked Agent';
            }
            setBookmarkedAgentIds(ids);
            setBookmarkedAgentNames(names);
            setUsingServerTracked(true);
          })
          .catch(() => {
            // local fallback only
          });
      } catch {
        setBookmarkedAgentIds([]);
        setUsingServerTracked(false);
      }
    };

    load();
    const onStorage = (event: StorageEvent) => {
      if (event.key === FAVORITES_KEY) {
        load();
      }
    };
    const onFavoritesUpdated = () => load();
    window.addEventListener('storage', onStorage);
    window.addEventListener('xclaw:favorites-updated', onFavoritesUpdated);
    return () => {
      window.removeEventListener('storage', onStorage);
      window.removeEventListener('xclaw:favorites-updated', onFavoritesUpdated);
    };
  }, []);

  useEffect(() => {
    if (usingServerTracked) {
      return;
    }
    if (bookmarkedAgentIds.length === 0) {
      setBookmarkedAgentNames({});
      return;
    }
    let cancelled = false;
    async function loadNames() {
      const names: Record<string, string> = {};
      await Promise.all(
        bookmarkedAgentIds.map(async (agentId) => {
          try {
            const response = await fetch(`/api/v1/public/agents/${encodeURIComponent(agentId)}`, { cache: 'no-store' });
            if (!response.ok) {
              names[agentId] = 'Saved Agent';
              return;
            }
            const payload = (await response.json()) as PublicAgentPayload;
            names[agentId] = payload.agent?.agent_name?.trim() || 'Saved Agent';
          } catch {
            names[agentId] = 'Saved Agent';
          }
        })
      );
      if (!cancelled) {
        setBookmarkedAgentNames(names);
      }
    }
    void loadNames();
    return () => {
      cancelled = true;
    };
  }, [bookmarkedAgentIds, usingServerTracked]);

  useEffect(() => {
    setMobileMoreOpen(false);
  }, [pathname]);

  const mobileAgentActive = useMemo(() => /^\/agents\/[A-Za-z0-9_-]+$/.test(pathname), [pathname]);
  const visibleBookmarkedAgentIds = useMemo(() => {
    if (!activeManagedAgentId) {
      return bookmarkedAgentIds;
    }
    return bookmarkedAgentIds.filter((agentId) => agentId !== activeManagedAgentId);
  }, [activeManagedAgentId, bookmarkedAgentIds]);

  function removeBookmarkedAgent(agentId: string) {
    if (typeof window === 'undefined') {
      return;
    }

    if (usingServerTracked && activeManagedAgentId) {
      const csrf = getCsrfToken();
      void fetch('/api/v1/management/tracked-agents', {
        method: 'DELETE',
        credentials: 'same-origin',
        headers: {
          'content-type': 'application/json',
          ...(csrf ? { 'x-csrf-token': csrf } : {})
        },
        body: JSON.stringify({ agentId: activeManagedAgentId, trackedAgentId: agentId })
      }).then(() => {
        setBookmarkedAgentIds((current) => current.filter((id) => id !== agentId));
        setBookmarkedAgentNames((current) => {
          const copy = { ...current };
          delete copy[agentId];
          return copy;
        });
        window.dispatchEvent(new Event('xclaw:favorites-updated'));
      });
      return;
    }

    const next = bookmarkedAgentIds.filter((id) => id !== agentId);
    window.localStorage.setItem(FAVORITES_KEY, JSON.stringify(next));
    window.dispatchEvent(new Event('xclaw:favorites-updated'));
    setBookmarkedAgentIds(next);
    setBookmarkedAgentNames((current) => {
      const copy = { ...current };
      delete copy[agentId];
      return copy;
    });
  }

  return (
    <>
      <aside className={`${styles.navRoot}${className ? ` ${className}` : ''}`}>
        <Link href="/" className={styles.logo} aria-label="X-Claw home">
          <Image src="/X-Claw-Logo.png" alt="X-Claw" width={900} height={280} className={styles.logoImage} priority />
        </Link>

        <nav className={styles.linkList} aria-label="Primary navigation">
          <div className={styles.topLinks}>
            {PRIMARY_ITEMS.map((item) => {
              const active = isActivePath(pathname, item.href);
              return (
                <Link
                  key={item.id}
                  href={item.href}
                  className={`${styles.linkItem}${active ? ` ${styles.linkItemActive}` : ''}`}
                  aria-label={item.label}
                  title={item.label}
                >
                  <SidebarIcon name={item.icon} />
                </Link>
              );
            })}

            <ActiveAgentSidebarLink itemClassName={styles.linkItem} activeClassName={styles.linkItemActive} />
          </div>

          <div className={styles.agentLinksScroller} aria-label="Saved agents">
            {visibleBookmarkedAgentIds.map((agentId) => {
              const active = pathname === `/agents/${agentId}`;
              const name = bookmarkedAgentNames[agentId] || 'Saved Agent';
              const palette = getAgentAvatarPalette(agentId);
              const initial = getAgentInitial(name, agentId);
              return (
                <div key={`saved-${agentId}`} className={styles.bookmarkItemWrap}>
                  <Link
                    href={`/agents/${encodeURIComponent(agentId)}`}
                    className={`${styles.linkItem}${active ? ` ${styles.linkItemActive}` : ''}`}
                    aria-label={`Saved: ${name}`}
                    title={`Saved: ${name}`}
                  >
                    <span
                      className="agent-shortcut-badge"
                      style={{
                        backgroundColor: palette.backgroundColor,
                        borderColor: palette.borderColor,
                        color: palette.textColor
                      }}
                    >
                      {initial}
                    </span>
                  </Link>
                  <button
                    type="button"
                    className={styles.bookmarkRemoveBtn}
                    aria-label={`Remove saved agent ${name}`}
                    title={`Remove ${name}`}
                    onClick={(event) => {
                      event.preventDefault();
                      event.stopPropagation();
                      removeBookmarkedAgent(agentId);
                    }}
                  >
                    ×
                  </button>
                </div>
              );
            })}
          </div>

          <div className={styles.bottomLinks}>
            {BOTTOM_ITEMS.map((item) => {
              const active = isActivePath(pathname, item.href);
              return (
                <Link
                  key={item.id}
                  href={item.href}
                  className={`${styles.linkItem}${active ? ` ${styles.linkItemActive}` : ''}`}
                  aria-label={item.label}
                  title={item.label}
                >
                  <SidebarIcon name={item.icon} />
                </Link>
              );
            })}
          </div>
        </nav>

        {desktopExtra ? <div className={styles.desktopExtra}>{desktopExtra}</div> : null}
      </aside>

      <nav className={styles.mobileBar} aria-label="Mobile navigation">
        {PRIMARY_ITEMS.map((item) => {
          const active = isActivePath(pathname, item.href);
          return (
            <Link
              key={`mobile-${item.id}`}
              href={item.href}
              className={`${styles.mobileItem}${active ? ` ${styles.mobileItemActive}` : ''}`}
              aria-label={item.label}
            >
              <SidebarIcon name={item.icon} />
              <span>{item.label}</span>
            </Link>
          );
        })}

        <Link
          href="/agents"
          className={`${styles.mobileItem}${mobileAgentActive ? ` ${styles.mobileItemActive}` : ''}`}
          aria-label="Agent"
        >
          <span className="agent-shortcut-badge">A</span>
          <span>Agent</span>
        </Link>

        <button type="button" className={styles.mobileMoreBtn} onClick={() => setMobileMoreOpen(true)} aria-label="More navigation">
          <SidebarIcon name="howto" />
          <span>More</span>
        </button>
      </nav>

      <MobileMoreSheet open={mobileMoreOpen} onClose={() => setMobileMoreOpen(false)}>
        <div className={styles.sheetLinks}>
          {BOTTOM_ITEMS.map((item) => (
            <Link key={`sheet-${item.id}`} href={item.href} className={styles.sheetLink}>
              <SidebarIcon name={item.icon} />
              <span>{item.label}</span>
            </Link>
          ))}
        </div>
        {mobileMoreContent ? <div className={styles.sheetExtra}>{mobileMoreContent}</div> : null}
      </MobileMoreSheet>
    </>
  );
}
