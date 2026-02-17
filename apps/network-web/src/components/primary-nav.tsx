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

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    const load = () => {
      try {
        const raw = window.localStorage.getItem(FAVORITES_KEY);
        if (!raw) {
          setBookmarkedAgentIds([]);
          return;
        }
        const parsed = JSON.parse(raw) as unknown;
        if (!Array.isArray(parsed)) {
          setBookmarkedAgentIds([]);
          return;
        }
        const ids = parsed.filter((item): item is string => typeof item === 'string' && item.length > 0);
        setBookmarkedAgentIds(Array.from(new Set(ids)));
      } catch {
        setBookmarkedAgentIds([]);
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
  }, [bookmarkedAgentIds]);

  useEffect(() => {
    setMobileMoreOpen(false);
  }, [pathname]);

  const mobileAgentActive = useMemo(() => /^\/agents\/[A-Za-z0-9_-]+$/.test(pathname), [pathname]);

  function removeBookmarkedAgent(agentId: string) {
    if (typeof window === 'undefined') {
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
            {bookmarkedAgentIds.map((agentId) => {
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
