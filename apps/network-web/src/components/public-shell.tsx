'use client';

import Image from 'next/image';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

import { ActiveAgentSidebarLink } from '@/components/active-agent-sidebar-link';
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
  const isStatusRoute = pathname === '/status';
  const isHowToRoute = pathname === '/how-to';

  if (isDashboardRoute || isAgentDetailRoute || isExploreRoute || isApprovalsRoute || isSettingsRoute || isStatusRoute || isHowToRoute) {
    return <main className="page-content page-content-dashboard">{children}</main>;
  }

  return (
    <div className="left-nav-shell">
      <aside className="left-nav-sidebar">
        <Link href="/" className="left-nav-logo" aria-label="X-Claw home">
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
          <Link href="/status" aria-label="Status" title="Status">
            <SidebarIcon name="status" />
          </Link>
          <ActiveAgentSidebarLink itemClassName="left-nav-link" />
          <Link href="/settings" aria-label="Settings & Security" title="Settings & Security">
            <SidebarIcon name="settings" />
          </Link>
          <Link href="/how-to" aria-label="How To" title="How To">
            <SidebarIcon name="howto" />
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
