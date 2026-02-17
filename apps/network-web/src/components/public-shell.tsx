'use client';

import { usePathname } from 'next/navigation';

import { ChainHeaderControl } from '@/components/chain-header-control';
import { ManagementHeaderControls } from '@/components/management-header-controls';
import { PrimaryNav } from '@/components/primary-nav';
import { ThemeToggle } from '@/components/theme-toggle';

export function PublicShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isLandingRoute = pathname === '/';
  const isDashboardRoute = pathname === '/dashboard';
  const isAgentDetailRoute = /^\/agents\/[^/]+$/.test(pathname);
  const isExploreRoute = pathname === '/explore' || pathname === '/agents';
  const isApprovalsRoute = pathname === '/approvals';
  const isSettingsRoute = pathname === '/settings';
  const isStatusRoute = pathname === '/status';
  const isHowToRoute = pathname === '/how-to';

  if (isLandingRoute) {
    return <>{children}</>;
  }

  if (isDashboardRoute || isAgentDetailRoute || isExploreRoute || isApprovalsRoute || isSettingsRoute || isStatusRoute || isHowToRoute) {
    return <main className="page-content page-content-dashboard">{children}</main>;
  }

  return (
    <div className="primary-shell">
      <PrimaryNav
        desktopExtra={
          <>
            <ChainHeaderControl />
            <ManagementHeaderControls />
            <ThemeToggle />
          </>
        }
        mobileMoreContent={
          <>
            <ChainHeaderControl />
            <ManagementHeaderControls />
            <ThemeToggle />
          </>
        }
      />
      <main className="primary-shell-content">{children}</main>
    </div>
  );
}
