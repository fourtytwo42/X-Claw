'use client';

import Image from 'next/image';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

import { ChainHeaderControl } from '@/components/chain-header-control';
import { ManagementHeaderControls } from '@/components/management-header-controls';
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
          <Link href="/dashboard">Dashboard</Link>
          <Link href="/explore">Explore</Link>
          <Link href="/approvals">Approvals Center</Link>
          <Link href="/settings">Settings &amp; Security</Link>
          <Link href="/status">Status</Link>
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
