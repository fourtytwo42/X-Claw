'use client';

import Image from 'next/image';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useMemo, useState } from 'react';

import { ActiveAgentSidebarLink } from '@/components/active-agent-sidebar-link';
import { MobileMoreSheet } from '@/components/mobile-more-sheet';
import { SidebarIcon } from '@/components/sidebar-icons';

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

  useEffect(() => {
    setMobileMoreOpen(false);
  }, [pathname]);

  const mobileAgentActive = useMemo(() => /^\/agents\/[A-Za-z0-9_-]+$/.test(pathname), [pathname]);

  return (
    <>
      <aside className={`${styles.navRoot}${className ? ` ${className}` : ''}`}>
        <Link href="/" className={styles.logo} aria-label="X-Claw home">
          <Image src="/X-Claw-Logo.png" alt="X-Claw" width={900} height={280} className={styles.logoImage} priority />
        </Link>

        <nav className={styles.linkList} aria-label="Primary navigation">
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
