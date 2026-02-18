'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';

import { ChainHeaderControl } from '@/components/chain-header-control';
import { PrimaryNav } from '@/components/primary-nav';
import { ThemeToggle } from '@/components/theme-toggle';
import { useDashboardChainKey } from '@/lib/active-chain';
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
type SortFilter = 'newest' | 'oldest';

type InboxRow = {
  id: string;
  requestId: string;
  rowKind: 'trade' | 'policy' | 'transfer';
  agentId: string;
  agentName: string;
  chainKey: string;
  status: 'pending' | 'approved' | 'rejected';
  title: string;
  subtitle: string;
  requestTypeLabel: string;
  reasonLine: string;
  riskLabel: 'Low' | 'Med' | 'High';
  createdAt: string;
};

type PermissionInventoryRow = {
  agentId: string;
  agentName: string;
  chainKey: string;
  tradePermissions: {
    approvalMode: 'per_trade' | 'auto';
    allowedTokens: string[];
    updatedAt: string | null;
  };
  transferPermissions: {
    transferApprovalMode: 'auto' | 'per_transfer';
    nativeTransferPreapproved: boolean;
    allowedTransferTokens: string[];
    updatedAt: string | null;
  };
  outboundPermissions: {
    outboundTransfersEnabled: boolean;
    outboundMode: 'disabled' | 'allow_all' | 'whitelist';
    outboundWhitelistAddresses: string[];
    updatedAt: string | null;
  };
};

type InboxPayload = {
  summary?: {
    pending?: number;
    approved?: number;
    rejected?: number;
  };
  rows?: InboxRow[];
  permissionInventory?: PermissionInventoryRow[];
};

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

function statusLabel(value: 'pending' | 'approved' | 'rejected'): string {
  if (value === 'pending') {
    return 'Pending';
  }
  if (value === 'approved') {
    return 'Approved';
  }
  return 'Rejected';
}

function humanizeKeyLabel(value: string): string {
  return value
    .replace(/[_-]+/g, ' ')
    .trim()
    .split(/\s+/)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase())
    .join(' ');
}

export default function ApprovalsCenterPage() {
  const [dashboardChainKey] = useDashboardChainKey();
  const [ownerContext, setOwnerContext] = useState<OwnerContext>({ phase: 'loading' });
  const [state, setState] = useState<InboxPayload | null>(null);
  const [loadingState, setLoadingState] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [workingById, setWorkingById] = useState<Record<string, boolean>>({});
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  const [activeTab, setActiveTab] = useState<StatusTab>('pending');
  const [typeFilter, setTypeFilter] = useState<TypeFilter>('all');
  const [query, setQuery] = useState('');
  const [sort, setSort] = useState<SortFilter>('newest');

  const effectiveChain = dashboardChainKey === 'all' ? 'all' : dashboardChainKey;

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
        const managed = Array.isArray(payload.managedAgents) ? payload.managedAgents : [];
        const active = payload.activeAgentId ?? managed[0];

        if (!cancelled && active) {
          setOwnerContext({ phase: 'ready', managedAgents: managed.length > 0 ? managed : [active], activeAgentId: active });
        }
      } catch (loadError) {
        if (!cancelled) {
          setOwnerContext({ phase: 'error', message: loadError instanceof Error ? loadError.message : 'Failed to resolve owner context.' });
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

    let cancelled = false;

    async function loadState() {
      setLoadingState(true);
      setError(null);
      try {
        const response = await fetch(
          `/api/v1/management/approvals/inbox?chainKey=${encodeURIComponent(effectiveChain)}&status=all&types=trade,policy,transfer&limit=400`,
          { cache: 'no-store', credentials: 'same-origin' }
        );

        if (!response.ok) {
          const payload = (await response.json().catch(() => null)) as { message?: string } | null;
          throw new Error(payload?.message ?? 'Failed to load approvals inbox.');
        }

        const payload = (await response.json()) as InboxPayload;
        if (!cancelled) {
          setState(payload);
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : 'Failed to load approvals inbox.');
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

  const rows = useMemo(() => state?.rows ?? [], [state]);

  const filteredRows = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();

    const out = rows.filter((row) => {
      if (activeTab !== 'all' && row.status !== activeTab) {
        return false;
      }
      if (typeFilter !== 'all' && row.rowKind !== typeFilter) {
        return false;
      }
      if (normalizedQuery && !`${row.title} ${row.subtitle} ${row.agentName} ${row.reasonLine}`.toLowerCase().includes(normalizedQuery)) {
        return false;
      }
      return true;
    });

    if (sort === 'oldest') {
      return [...out].sort((left, right) => new Date(left.createdAt).getTime() - new Date(right.createdAt).getTime());
    }
    return out;
  }, [activeTab, rows, sort, typeFilter, query]);

  const summary = useMemo(() => {
    return {
      pending: state?.summary?.pending ?? rows.filter((row) => row.status === 'pending').length,
      approved: state?.summary?.approved ?? rows.filter((row) => row.status === 'approved').length,
      rejected: state?.summary?.rejected ?? rows.filter((row) => row.status === 'rejected').length
    };
  }, [rows, state]);

  async function reloadInbox() {
    const response = await fetch(
      `/api/v1/management/approvals/inbox?chainKey=${encodeURIComponent(effectiveChain)}&status=all&types=trade,policy,transfer&limit=400`,
      { cache: 'no-store', credentials: 'same-origin' }
    );
    if (!response.ok) {
      return;
    }
    const payload = (await response.json()) as InboxPayload;
    setState(payload);
  }

  async function handleDecision(row: InboxRow, decision: 'approve' | 'reject' | 'approve_allowlist') {
    setNotice(null);
    setError(null);
    setWorkingById((current) => ({ ...current, [row.id]: true }));

    try {
      if (row.rowKind === 'trade' && decision === 'approve_allowlist') {
        await managementPost('/api/v1/management/approvals/approve-allowlist-token', {
          agentId: row.agentId,
          tradeId: row.requestId
        });
      } else if (row.rowKind === 'trade') {
        await managementPost('/api/v1/management/approvals/decision', {
          agentId: row.agentId,
          tradeId: row.requestId,
          decision
        });
      } else if (row.rowKind === 'policy') {
        await managementPost('/api/v1/management/policy-approvals/decision', {
          agentId: row.agentId,
          policyApprovalId: row.requestId,
          decision
        });
      } else {
        await managementPost('/api/v1/management/transfer-approvals/decision', {
          agentId: row.agentId,
          approvalId: row.requestId,
          decision: decision === 'approve' ? 'approve' : 'deny',
          chainKey: row.chainKey
        });
      }

      setNotice(
        decision === 'approve_allowlist'
          ? 'Approved trade and allowlisted token.'
          : `${decision === 'approve' ? 'Approved' : 'Rejected'} ${row.requestTypeLabel.toLowerCase()} request.`
      );
      await reloadInbox();
    } catch (decisionError) {
      setError(decisionError instanceof Error ? decisionError.message : 'Decision request failed.');
    } finally {
      setWorkingById((current) => ({ ...current, [row.id]: false }));
    }
  }

  async function handleBatch(decision: 'approve' | 'reject' | 'approve_allowlist') {
    const selectedRows = filteredRows.filter((row) => selectedIds.includes(row.id) && row.status === 'pending');
    if (selectedRows.length === 0) {
      return;
    }

    try {
      await managementPost('/api/v1/management/approvals/decision-batch', {
        items: selectedRows.map((row) => ({
          agentId: row.agentId,
          rowKind: row.rowKind,
          requestId: row.requestId,
          chainKey: row.chainKey,
          decision
        }))
      });
      setSelectedIds([]);
      setNotice(`Batch ${decision} executed for ${selectedRows.length} request(s).`);
      await reloadInbox();
    } catch (decisionError) {
      setError(decisionError instanceof Error ? decisionError.message : 'Batch decision failed.');
    }
  }

  return (
    <div className={styles.root}>
      <PrimaryNav />

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
                <p className={styles.summaryLabel}>Approved</p>
                <p className={styles.summaryValue}>{formatNumber(summary.approved)}</p>
              </article>
              <article className={styles.summaryCard}>
                <p className={styles.summaryLabel}>Rejected</p>
                <p className={styles.summaryValue}>{formatNumber(summary.rejected)}</p>
              </article>
            </section>

            <p className={styles.postureLine}>Security posture: per-request approvals are active for linked agents.</p>

            <div className={styles.contentGrid}>
              <section className={styles.card}>
                <div className={styles.cardHeaderRow}>
                  <h2>Approval Requests</h2>
                  <span className={styles.agentBadge}>Linked agents: {ownerContext.managedAgents.length}</span>
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
                      className={`${styles.segmentTab}${activeTab === key ? ` ${styles.segmentTabActive}` : ''}${
                        key === 'pending'
                          ? ` ${styles.segmentTabPending}`
                          : key === 'approved'
                            ? ` ${styles.segmentTabApproved}`
                            : key === 'rejected'
                              ? ` ${styles.segmentTabRejected}`
                              : ''
                      }`}
                      onClick={() => setActiveTab(key)}
                    >
                      {label}
                    </button>
                  ))}
                </div>

                <div className={styles.filterRow}>
                  <select aria-label="Type filter" value={typeFilter} onChange={(event) => setTypeFilter(event.target.value as TypeFilter)}>
                    <option value="all">All types</option>
                    <option value="trade">Trade approval</option>
                    <option value="policy">Policy approval</option>
                    <option value="transfer">Withdraw approval</option>
                  </select>
                  <select aria-label="Sort" value={sort} onChange={(event) => setSort(event.target.value as SortFilter)}>
                    <option value="newest">Newest</option>
                    <option value="oldest">Oldest</option>
                  </select>
                  <input
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                    placeholder="Search approval requests..."
                    aria-label="Search requests"
                  />
                </div>

                <div className={styles.requestActions}>
                  <button type="button" onClick={() => void handleBatch('approve')} disabled={selectedIds.length === 0}>
                    Bulk Approve
                  </button>
                  <button type="button" onClick={() => void handleBatch('approve_allowlist')} disabled={selectedIds.length === 0}>
                    Bulk Approve + Allowlist
                  </button>
                  <button type="button" className={styles.dangerButton} onClick={() => void handleBatch('reject')} disabled={selectedIds.length === 0}>
                    Bulk Reject
                  </button>
                </div>

                {loadingState ? <p className={styles.loadingCopy}>Loading approvals...</p> : null}
                {!loadingState && filteredRows.length === 0 ? <p className={styles.emptyCopy}>No matching approvals.</p> : null}

                <div className={styles.requestList}>
                  {filteredRows.map((row) => {
                    const disabled = row.status !== 'pending' || Boolean(workingById[row.id]);
                    const checked = selectedIds.includes(row.id);
                    return (
                      <article key={row.id} className={styles.requestCard}>
                        <div className={styles.requestTop}>
                          <div>
                            <p className={styles.requestType}>{row.requestTypeLabel}</p>
                            <h3>{row.title}</h3>
                            <p className={styles.requestMeta}>{row.subtitle}</p>
                          </div>
                          <div className={styles.rightMeta}>
                            <span className={`${styles.statusChip} ${row.status === 'pending' ? styles.statusChipPending : row.status === 'approved' ? styles.statusChipApproved : styles.statusChipRejected}`}>
                              {statusLabel(row.status)}
                            </span>
                          </div>
                        </div>
                        <p className={styles.reasonLine}>{row.reasonLine}</p>
                        <div className={styles.metadataRow}>
                          <span>Agent: {row.agentName}</span>
                          <span>Chain: {humanizeKeyLabel(row.chainKey)}</span>
                          <span>Risk: {row.riskLabel}</span>
                          <span>Requested: {formatUtc(row.createdAt)} UTC</span>
                        </div>
                        <div className={styles.requestActions}>
                          <label>
                            <input
                              type="checkbox"
                              checked={checked}
                              onChange={(event) => {
                                setSelectedIds((current) =>
                                  event.target.checked ? Array.from(new Set([...current, row.id])) : current.filter((item) => item !== row.id)
                                );
                              }}
                              disabled={row.status !== 'pending'}
                            />
                            Select
                          </label>
                          <button type="button" disabled={disabled} onClick={() => void handleDecision(row, 'approve')}>
                            Approve Once
                          </button>
                          <button
                            type="button"
                            disabled={disabled || row.rowKind !== 'trade'}
                            onClick={() => void handleDecision(row, 'approve_allowlist')}
                          >
                            Approve + Allowlist Token
                          </button>
                          <button type="button" disabled={disabled} className={styles.dangerButton} onClick={() => void handleDecision(row, 'reject')}>
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
                  <h2>Permissions Inventory</h2>
                </div>
                <p className={styles.placeholderNote}>Chain-scoped trade, transfer, and outbound permission posture for linked agents.</p>

                <div className={styles.allowanceTable}>
                  <div className={styles.allowanceRowHeader}>
                    <span>Agent / Chain</span>
                    <span>Trade Permissions</span>
                    <span>Transfer Permissions</span>
                    <span>Outbound</span>
                  </div>
                  {(state?.permissionInventory ?? []).map((item) => (
                    <div key={`${item.agentId}:${item.chainKey}`} className={styles.allowanceRow}>
                      <span>{item.agentName} / {humanizeKeyLabel(item.chainKey)}</span>
                      <span>
                        {item.tradePermissions.approvalMode === 'auto' ? 'Approve all' : 'Per-trade'}
                        <br />
                        Tokens: {item.tradePermissions.allowedTokens.length}
                      </span>
                      <span>
                        {item.transferPermissions.transferApprovalMode}
                        <br />
                        Native: {item.transferPermissions.nativeTransferPreapproved ? 'yes' : 'no'}
                      </span>
                      <span>
                        {item.outboundPermissions.outboundTransfersEnabled ? item.outboundPermissions.outboundMode : 'disabled'}
                        <br />
                        <button
                          type="button"
                          onClick={() =>
                            void managementPost('/api/v1/management/permissions/update', {
                              agentId: item.agentId,
                              chainKey: item.chainKey,
                              tradeApprovalMode: item.tradePermissions.approvalMode === 'auto' ? 'per_trade' : 'auto'
                            }).then(() => reloadInbox())
                          }
                        >
                          {item.tradePermissions.approvalMode === 'auto' ? 'Set Per-Trade' : 'Set Approve-All'}
                        </button>
                        <br />
                        <button
                          type="button"
                          onClick={() =>
                            void managementPost('/api/v1/management/permissions/update', {
                              agentId: item.agentId,
                              chainKey: item.chainKey,
                              outboundTransfersEnabled: !item.outboundPermissions.outboundTransfersEnabled
                            }).then(() => reloadInbox())
                          }
                        >
                          {item.outboundPermissions.outboundTransfersEnabled ? 'Disable Outbound' : 'Enable Outbound'}
                        </button>
                      </span>
                    </div>
                  ))}
                  {(state?.permissionInventory ?? []).length === 0 ? (
                    <div className={styles.allowanceRow}>
                      <span>No permission inventory rows yet.</span>
                      <span>--</span>
                      <span>--</span>
                      <span>--</span>
                    </div>
                  ) : null}
                </div>
              </section>
            </div>
          </>
        ) : null}
      </section>
    </div>
  );
}
