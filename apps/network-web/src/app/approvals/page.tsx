'use client';

import Image from 'next/image';
import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';

import { ChainHeaderControl } from '@/components/chain-header-control';
import { SidebarIcon } from '@/components/sidebar-icons';
import { ThemeToggle } from '@/components/theme-toggle';
import { useDashboardChainKey } from '@/lib/active-chain';
import { APPROVALS_CENTER_CAPABILITIES } from '@/lib/approvals-center-capabilities';
import {
  buildApprovalsCenterRows,
  type ApprovalRowStatus,
  type ApprovalsCenterManagementState,
  type ApprovalsCenterRow,
  type LocalDecisionMap
} from '@/lib/approvals-center-view-model';
import { formatNumber, formatUtc } from '@/lib/public-format';

import styles from './page.module.css';

type SessionAgentsPayload = {
  managedAgents?: string[];
  activeAgentId?: string;
};

type OwnerContext =
  | { phase: 'loading' }
  | { phase: 'none' }
  | { phase: 'error'; message: string }
  | { phase: 'ready'; managedAgents: string[]; activeAgentId: string };

type StatusTab = 'pending' | 'approved' | 'rejected' | 'all';
type TypeFilter = 'all' | 'trade' | 'policy' | 'transfer';
type SortFilter = 'newest' | 'oldest' | 'risk';

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

async function managementPost(path: string, payload: Record<string, unknown>) {
  const csrf = getCsrfToken();
  const headers: Record<string, string> = { 'content-type': 'application/json' };
  if (csrf) {
    headers['x-csrf-token'] = csrf;
  }

  const response = await fetch(path, {
    method: 'POST',
    credentials: 'same-origin',
    headers,
    body: JSON.stringify(payload)
  });

  const json = (await response.json().catch(() => null)) as { message?: string; code?: string; actionHint?: string } | null;
  if (!response.ok) {
    const error = new Error(json?.message ?? 'Management request failed.') as Error & { code?: string; actionHint?: string };
    if (json?.code) {
      error.code = json.code;
    }
    if (json?.actionHint) {
      error.actionHint = json.actionHint;
    }
    throw error;
  }

  return json;
}

function parseStoredManagedAgents(): string[] {
  if (typeof window === 'undefined') {
    return [];
  }
  try {
    const raw = window.localStorage.getItem('xclaw_managed_agent_ids');
    if (!raw) {
      return [];
    }
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) {
      return [];
    }
    return parsed.filter((item): item is string => typeof item === 'string' && item.length > 0);
  } catch {
    return [];
  }
}

function statusLabel(value: ApprovalRowStatus): string {
  if (value === 'pending') {
    return 'Pending';
  }
  if (value === 'approved') {
    return 'Approved';
  }
  return 'Rejected';
}

function riskRank(value: ApprovalsCenterRow['riskLabel']): number {
  if (value === 'High') {
    return 3;
  }
  if (value === 'Med') {
    return 2;
  }
  return 1;
}

export default function ApprovalsCenterPage() {
  const [dashboardChainKey, , dashboardChainLabel] = useDashboardChainKey();
  const [ownerContext, setOwnerContext] = useState<OwnerContext>({ phase: 'loading' });
  const [state, setState] = useState<ApprovalsCenterManagementState | null>(null);
  const [loadingState, setLoadingState] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [decisionMap, setDecisionMap] = useState<LocalDecisionMap>({});
  const [workingById, setWorkingById] = useState<Record<string, boolean>>({});

  const [activeTab, setActiveTab] = useState<StatusTab>('pending');
  const [typeFilter, setTypeFilter] = useState<TypeFilter>('all');
  const [query, setQuery] = useState('');
  const [sort, setSort] = useState<SortFilter>('newest');

  const effectiveChain = dashboardChainKey === 'all' ? 'base_sepolia' : dashboardChainKey;

  useEffect(() => {
    let cancelled = false;

    async function loadOwnerContext() {
      setOwnerContext({ phase: 'loading' });
      try {
        const response = await fetch('/api/v1/management/session/agents', { credentials: 'same-origin', cache: 'no-store' });
        if (!response.ok) {
          if (!cancelled) {
            setOwnerContext({ phase: 'none' });
          }
          return;
        }

        const payload = (await response.json()) as SessionAgentsPayload;
        const fromSession = Array.isArray(payload.managedAgents) ? payload.managedAgents : [];
        const merged = Array.from(new Set([...fromSession, ...parseStoredManagedAgents()]));
        const activeAgentId = payload.activeAgentId ?? merged[0];

        if (!cancelled && activeAgentId) {
          setOwnerContext({ phase: 'ready', managedAgents: merged.length > 0 ? merged : [activeAgentId], activeAgentId });
        }
      } catch (loadError) {
        if (!cancelled) {
          setOwnerContext({
            phase: 'error',
            message: loadError instanceof Error ? loadError.message : 'Failed to resolve owner context.'
          });
        }
      }
    }

    void loadOwnerContext();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (ownerContext.phase !== 'ready') {
      setState(null);
      return;
    }
    const activeAgentId = ownerContext.activeAgentId;

    let cancelled = false;

    async function loadState() {
      setLoadingState(true);
      setError(null);
      try {
        const response = await fetch(
          `/api/v1/management/agent-state?agentId=${encodeURIComponent(activeAgentId)}&chainKey=${encodeURIComponent(effectiveChain)}`,
          {
            cache: 'no-store',
            credentials: 'same-origin',
            headers: getCsrfToken() ? { 'x-csrf-token': getCsrfToken() as string } : {}
          }
        );

        if (!response.ok) {
          const payload = (await response.json().catch(() => null)) as { message?: string } | null;
          throw new Error(payload?.message ?? 'Failed to load approvals state.');
        }

        const payload = (await response.json()) as ApprovalsCenterManagementState;
        if (!cancelled) {
          setState(payload);
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : 'Failed to load approvals state.');
        }
      } finally {
        if (!cancelled) {
          setLoadingState(false);
        }
      }
    }

    void loadState();
    const timer = window.setInterval(() => {
      void loadState();
    }, 10_000);

    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [ownerContext, effectiveChain]);

  const rows = useMemo(() => buildApprovalsCenterRows(state ?? {}, decisionMap), [state, decisionMap]);

  const filteredRows = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();

    const out = rows.filter((row) => {
      if (activeTab !== 'all' && row.status !== activeTab) {
        return false;
      }
      if (typeFilter !== 'all' && row.rowKind !== typeFilter) {
        return false;
      }
      if (normalizedQuery && !`${row.title} ${row.subtitle} ${row.tokenSearch}`.toLowerCase().includes(normalizedQuery)) {
        return false;
      }
      return true;
    });

    if (sort === 'oldest') {
      return [...out].sort((left, right) => new Date(left.createdAt).getTime() - new Date(right.createdAt).getTime());
    }
    if (sort === 'risk') {
      return [...out].sort((left, right) => riskRank(right.riskLabel) - riskRank(left.riskLabel));
    }
    return out;
  }, [activeTab, rows, sort, typeFilter, query]);

  const summary = useMemo(() => {
    const pending = rows.filter((row) => row.status === 'pending').length;
    const approved = rows.filter((row) => row.status === 'approved').length;
    const rejected = rows.filter((row) => row.status === 'rejected').length;
    const highRisk = rows.filter((row) => row.riskLabel === 'High').length;
    return { pending, approved, rejected, highRisk };
  }, [rows]);

  async function handleDecision(row: ApprovalsCenterRow, decision: 'approve' | 'reject') {
    if (ownerContext.phase !== 'ready') {
      return;
    }

    setNotice(null);
    setError(null);
    setWorkingById((current) => ({ ...current, [row.id]: true }));

    try {
      if (row.rowKind === 'trade' && row.tradeId) {
        await managementPost('/api/v1/management/approvals/decision', {
          agentId: ownerContext.activeAgentId,
          tradeId: row.tradeId,
          decision
        });
      } else if (row.rowKind === 'policy' && row.policyApprovalId) {
        await managementPost('/api/v1/management/policy-approvals/decision', {
          agentId: ownerContext.activeAgentId,
          policyApprovalId: row.policyApprovalId,
          decision
        });
      } else if (row.rowKind === 'transfer' && row.transferApprovalId) {
        await managementPost('/api/v1/management/transfer-approvals/decision', {
          agentId: ownerContext.activeAgentId,
          approvalId: row.transferApprovalId,
          decision: decision === 'approve' ? 'approve' : 'deny',
          chainKey: row.chainKey
        });
      }

      setDecisionMap((current) => ({
        ...current,
        [row.tradeId ?? row.policyApprovalId ?? row.transferApprovalId ?? row.id]: {
          status: decision === 'approve' ? 'approved' : 'rejected',
          decidedAt: new Date().toISOString()
        }
      }));
      setNotice(`${decision === 'approve' ? 'Approved' : 'Rejected'} ${row.requestTypeLabel.toLowerCase()} request.`);
    } catch (decisionError) {
      setError(decisionError instanceof Error ? decisionError.message : 'Decision request failed.');
    } finally {
      setWorkingById((current) => ({ ...current, [row.id]: false }));
    }
  }

  return (
    <div className={styles.root}>
      <aside className={styles.sidebar}>
        <Link href="/dashboard" className={styles.sidebarLogo} aria-label="X-Claw dashboard">
          <Image src="/X-Claw-Logo.png" alt="X-Claw" width={900} height={280} className={styles.sidebarLogoImage} priority />
        </Link>
        <nav className={styles.sidebarNav} aria-label="Approvals center sections">
          <Link className={styles.sidebarItem} href="/dashboard" aria-label="Dashboard" title="Dashboard">
            <SidebarIcon name="dashboard" />
          </Link>
          <Link className={styles.sidebarItem} href="/explore" aria-label="Explore" title="Explore">
            <SidebarIcon name="explore" />
          </Link>
          <Link
            className={`${styles.sidebarItem} ${styles.sidebarItemActive}`}
            href="/approvals"
            aria-label="Approvals Center"
            title="Approvals Center"
          >
            <SidebarIcon name="approvals" />
          </Link>
          <Link className={styles.sidebarItem} href="/settings" aria-label="Settings & Security" title="Settings & Security">
            <SidebarIcon name="settings" />
          </Link>
        </nav>
      </aside>

      <section className={styles.mainSurface}>
        <header className={styles.topbar}>
          <div>
            <h1 className={styles.title}>Approvals Center</h1>
            <p className={styles.subtitle}>Global inbox across managed agents on this device.</p>
          </div>
          <div className={styles.topbarControls}>
            <ChainHeaderControl includeAll className={styles.chainControl} id="approvals-chain-select" />
            <ThemeToggle className={styles.topbarThemeToggle} />
          </div>
        </header>

        {dashboardChainKey === 'all' ? (
          <p className={styles.infoBanner}>All chains selected. v1 loads queue data from Base Sepolia; cross-chain aggregation is planned in a follow-up API slice.</p>
        ) : null}
        {notice ? <p className={styles.successBanner}>{notice}</p> : null}
        {error ? <p className={styles.warningBanner}>{error}</p> : null}

        {ownerContext.phase === 'loading' ? <p className={styles.loadingCopy}>Loading owner context...</p> : null}
        {ownerContext.phase === 'error' ? <p className={styles.warningBanner}>{ownerContext.message}</p> : null}

        {ownerContext.phase === 'none' ? (
          <section className={styles.emptyState}>
            <h2>No agent access found on this device</h2>
            <p>Approvals Center appears only when this device has an active owner management session.</p>
            <div className={styles.emptyActions}>
              <Link href="/settings#access" className={styles.primaryLink}>
                Add agent via key link
              </Link>
              <Link href="/explore" className={styles.secondaryLink}>
                Browse agents
              </Link>
            </div>
          </section>
        ) : null}

        {ownerContext.phase === 'ready' ? (
          <>
            <section className={styles.summaryStrip}>
              <article className={styles.summaryCard}>
                <p className={styles.summaryLabel}>Pending requests</p>
                <p className={styles.summaryValue}>{formatNumber(summary.pending)}</p>
              </article>
              <article className={styles.summaryCard}>
                <p className={styles.summaryLabel}>Approved (session)</p>
                <p className={styles.summaryValue}>{formatNumber(summary.approved)}</p>
              </article>
              <article className={styles.summaryCard}>
                <p className={styles.summaryLabel}>Rejected (session)</p>
                <p className={styles.summaryValue}>{formatNumber(summary.rejected)}</p>
              </article>
              <article className={styles.summaryCard}>
                <p className={styles.summaryLabel}>High risk items</p>
                <p className={styles.summaryValue}>{formatNumber(summary.highRisk)}</p>
              </article>
            </section>

            <p className={styles.postureLine}>
              Security posture: per-request approvals active on current session agent. Cross-agent and allowance posture aggregation is placeholder-only in v1.
            </p>

            <div className={styles.contentGrid}>
              <section className={styles.card}>
                <div className={styles.cardHeaderRow}>
                  <h2>Pending Approval Requests</h2>
                  <span className={styles.agentBadge}>Agent: {ownerContext.activeAgentId}</span>
                </div>

                <div className={styles.segmentTabs}>
                  {([
                    ['pending', 'Pending'],
                    ['approved', 'Approved'],
                    ['rejected', 'Rejected'],
                    ['all', 'All']
                  ] as const).map(([key, label]) => (
                    <button
                      key={key}
                      type="button"
                      className={activeTab === key ? styles.segmentTabActive : styles.segmentTab}
                      onClick={() => setActiveTab(key)}
                    >
                      {label}
                    </button>
                  ))}
                </div>

                <div className={styles.filterRow}>
                  <select
                    aria-label="Agent filter"
                    disabled={!APPROVALS_CENTER_CAPABILITIES.crossAgentAggregation}
                    value={ownerContext.activeAgentId}
                    onChange={() => {
                    }}
                  >
                    <option value={ownerContext.activeAgentId}>Active session agent</option>
                  </select>
                  <select aria-label="Type filter" value={typeFilter} onChange={(event) => setTypeFilter(event.target.value as TypeFilter)}>
                    <option value="all">All types</option>
                    <option value="trade">Trade approval</option>
                    <option value="policy">Policy approval</option>
                    <option value="transfer">Withdraw approval</option>
                  </select>
                  <select aria-label="Risk filter" disabled>
                    <option>Any risk (placeholder)</option>
                  </select>
                  <select aria-label="Sort" value={sort} onChange={(event) => setSort(event.target.value as SortFilter)}>
                    <option value="newest">Newest</option>
                    <option value="oldest">Oldest</option>
                    <option value="risk">Highest risk</option>
                  </select>
                  <input
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                    placeholder="Search pending approval requests..."
                    aria-label="Search requests"
                  />
                </div>

                {activeTab !== 'pending' ? (
                  <p className={styles.placeholderNote}>
                    Approved/Rejected tabs show local session and available history rows only. Global cross-agent history needs a dedicated aggregation API.
                  </p>
                ) : null}

                {loadingState ? <p className={styles.loadingCopy}>Loading approvals...</p> : null}
                {!loadingState && filteredRows.length === 0 ? <p className={styles.emptyCopy}>No pending approvals. Your agents are operating within limits.</p> : null}

                <div className={styles.requestList}>
                  {filteredRows.map((row) => {
                    const disabled = row.status !== 'pending' || Boolean(workingById[row.id]);
                    return (
                      <article key={row.id} className={styles.requestCard}>
                        <div className={styles.requestTop}>
                          <div>
                            <p className={styles.requestType}>{row.requestTypeLabel}</p>
                            <h3>{row.title}</h3>
                            <p className={styles.requestMeta}>{row.subtitle}</p>
                          </div>
                          <div className={styles.rightMeta}>
                            <span className={styles.statusChip}>{statusLabel(row.status)}</span>
                            <span className={styles.riskChip}>{row.riskLabel} risk</span>
                          </div>
                        </div>
                        <p className={styles.reasonLine}>{row.reasonLine}</p>
                        <div className={styles.metadataRow}>
                          <span>Chain: {row.chainKey}</span>
                          <span>Requested: {formatUtc(row.createdAt)} UTC</span>
                        </div>
                        <div className={styles.requestActions}>
                          <button type="button" disabled={disabled} onClick={() => void handleDecision(row, 'approve')}>
                            Approve Once
                          </button>
                          <button type="button" disabled className={styles.secondaryDisabled}>
                            Approve + Allowlist Token
                          </button>
                          <button
                            type="button"
                            disabled={disabled}
                            className={styles.dangerButton}
                            onClick={() => void handleDecision(row, 'reject')}
                          >
                            Reject
                          </button>
                        </div>
                      </article>
                    );
                  })}
                </div>
              </section>

              <section className={styles.card}>
                <div className={styles.cardHeaderRow}>
                  <h2>Allowances Inventory</h2>
                </div>
                <p className={styles.placeholderNote}>
                  Awaiting dedicated allowances inventory API. This section is read-only in Slice 74 and actions remain disabled.
                </p>

                <div className={styles.allowanceToolbar}>
                  <select disabled>
                    <option>Allowance type (placeholder)</option>
                  </select>
                  <select disabled>
                    <option>Agent (placeholder)</option>
                  </select>
                  <input disabled placeholder="Search allowances..." />
                </div>

                <div className={styles.allowanceTable}>
                  <div className={styles.allowanceRowHeader}>
                    <span>Spender</span>
                    <span>Token</span>
                    <span>Allowance</span>
                    <span>Actions</span>
                  </div>
                  <div className={styles.allowanceRow}>
                    <span>Data unavailable</span>
                    <span>--</span>
                    <span>--</span>
                    <span>
                      <button type="button" disabled>
                        Revoke
                      </button>
                    </span>
                  </div>
                </div>
              </section>
            </div>
          </>
        ) : null}
      </section>
    </div>
  );
}
