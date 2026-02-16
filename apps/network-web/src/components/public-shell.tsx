'use client';

import Image from 'next/image';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

import { ChainHeaderControl } from '@/components/chain-header-control';
import { ManagementHeaderControls } from '@/components/management-header-controls';
import { SidebarIcon } from '@/components/sidebar-icons';
import { ThemeToggle } from '@/components/theme-toggle';

export function PublicShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isDashboardRoute = pathname === '/' || pathname === '/dashboard';
  const isAgentDetailRoute = /^\/agents\/[^/]+$/.test(pathname);
  const isExploreRoute = pathname === '/explore' || pathname === '/agents';
  const isApprovalsRoute = pathname === '/approvals';
  const isSettingsRoute = pathname === '/settings';

  if (isDashboardRoute || isAgentDetailRoute || isExploreRoute || isApprovalsRoute || isSettingsRoute) {
    return <main className="page-content page-content-dashboard">{children}</main>;
  }

  return (
    <div className="left-nav-shell">
      <aside className="left-nav-sidebar">
        <Link href="/dashboard" className="left-nav-logo" aria-label="X-Claw dashboard">
          <Image src="/X-Claw-Logo.png" alt="X-Claw" width={900} height={280} className="left-nav-logo-image" priority />
        </Link>
        <nav className="left-nav-links" aria-label="Primary">
          <Link href="/dashboard" aria-label="Dashboard" title="Dashboard">
            <SidebarIcon name="dashboard" />
          </Link>
          <Link href="/explore" aria-label="Explore" title="Explore">
            <SidebarIcon name="explore" />
          </Link>
          <Link href="/approvals" aria-label="Approvals Center" title="Approvals Center">
            <SidebarIcon name="approvals" />
          </Link>
          <Link href="/settings" aria-label="Settings & Security" title="Settings & Security">
            <SidebarIcon name="settings" />
          </Link>
          <Link href="/status" aria-label="Status" title="Status">
            <SidebarIcon name="status" />
          </Link>
        </nav>
        <div className="left-nav-controls">
          <ChainHeaderControl />
          <ManagementHeaderControls />
          <ThemeToggle />
        </div>
      </aside>
      <main className="left-nav-content">{children}</main>
    </div>
  );
}
