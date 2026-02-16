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
  const isApprovalsRoute = pathname === '/approvals';

  if (isDashboardRoute || isAgentDetailRoute || isApprovalsRoute) {
    return <main className="page-content page-content-dashboard">{children}</main>;
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="header-left">
          <Link href="/" className="brand" aria-label="X-Claw home">
            <Image src="/X-Claw-Logo.png" alt="X-Claw" width={900} height={280} className="brand-logo" priority />
          </Link>
          <nav className="main-nav" aria-label="Primary">
            <Link href="/">Dashboard</Link>
            <Link href="/agents">Agents</Link>
            <Link href="/status">Status</Link>
          </nav>
        </div>
        <div className="header-right">
          <div className="header-controls">
            <ChainHeaderControl />
            <ManagementHeaderControls />
            <ThemeToggle />
          </div>
        </div>
      </header>
      <main className="page-content">{children}</main>
      <footer className="app-footer">
        <Link href="/status">Diagnostics and status</Link>
      </footer>
    </div>
  );
}
