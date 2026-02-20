'use client';

import { useEffect, useState } from 'react';

import { ChainHeaderControl } from '@/components/chain-header-control';
import { PrimaryNav } from '@/components/primary-nav';
import { ThemeToggle } from '@/components/theme-toggle';
import { useDashboardChainKey } from '@/lib/active-chain';
import { fetchWithTimeout, uiFetchTimeoutMs } from '@/lib/fetch-timeout';
import { formatUtc } from '@/lib/public-format';

import styles from './page.module.css';

type StatusPayload = {
  ok: boolean;
  requestId: string;
  generatedAtUtc: string;
  overallStatus: 'healthy' | 'degraded' | 'offline';
  dependencies: Array<{
    name: 'api' | 'db' | 'redis';
    status: 'healthy' | 'degraded' | 'offline';
    latencyMs: number | null;
    checkedAtUtc: string;
    detail?: string;
  }>;
  providers: Array<{
    chainKey: string;
    provider: 'primary' | 'fallback';
    status: 'healthy' | 'degraded';
    latencyMs: number | null;
    checkedAtUtc: string;
    detail?: string;
  }>;
  heartbeat: {
    totalAgents: number;
    activeAgents: number;
    offlineAgents: number;
    degradedAgents: number;
    heartbeatMisses: number;
  };
  queues: {
    copyIntentPending: number;
    approvalPendingTrades: number;
    totalDepth: number;
  };
  incidents: Array<{
    id: string;
    atUtc: string;
    category: string;
    severity: 'info' | 'warning' | 'critical';
    summary: string;
    details?: string;
  }>;
};

function statusTone(status: string): string {
  if (status === 'healthy') {
    return 'status-active';
  }
  if (status === 'degraded') {
    return 'status-degraded';
  }
  return 'status-offline';
}

export default function StatusPage() {
  const [dashboardChainKey] = useDashboardChainKey();
  const [data, setData] = useState<StatusPayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        setError(null);
        const res = await fetchWithTimeout('/api/status', { cache: 'no-store' }, uiFetchTimeoutMs());
        if (!res.ok) {
          throw new Error('Status request failed.');
        }
        const payload = (await res.json()) as StatusPayload;
        if (!cancelled) {
          setData(payload);
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : 'Failed to load status.');
        }
      }
    }

    void load();
    const interval = setInterval(() => {
      void load();
    }, 15000);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  const filteredProviders = (data?.providers ?? []).filter((provider) => dashboardChainKey === 'all' || provider.chainKey === dashboardChainKey);

  return (
    <div className={styles.root}>
      <PrimaryNav />

      <section className={styles.mainSurface}>
        <header className={styles.topbar}>
          <div>
            <h1 className={styles.title}>Public Status</h1>
            <p className={styles.subtitle}>Public-safe diagnostics for API, data dependencies, and chain provider health.</p>
          </div>
          <div className={styles.topbarControls}>
            <ChainHeaderControl includeAll className={styles.chainControl} id="status-chain-select" />
            <ThemeToggle className={styles.topbarThemeToggle} />
          </div>
        </header>

        {error ? <p className={styles.warningBanner}>{error}</p> : null}

        <section className={styles.card}>
          <h2 className={styles.sectionTitle}>Overview</h2>
          <div className={styles.statusOverview}>
            <div>
              <div className={styles.muted}>Overall status</div>
              <div className={`${styles.kpiValue} ${statusTone(data?.overallStatus ?? 'offline')}`}>{data?.overallStatus ?? 'loading...'}</div>
            </div>
            <div>
              <div className={styles.muted}>Last updated (UTC)</div>
              <div>{data ? formatUtc(data.generatedAtUtc) : '...'}</div>
            </div>
            <div>
              <div className={styles.muted}>Request ID</div>
              <code className={styles.hardWrap}>{data?.requestId ?? '...'}</code>
            </div>
          </div>
        </section>

        <section className={styles.card}>
          <h2 className={styles.sectionTitle}>Dependency Health</h2>
          <div className={styles.statusGrid}>
            {(data?.dependencies ?? []).map((dep) => (
              <article key={dep.name} className={styles.managementCard}>
                <h3>{dep.name.toUpperCase()}</h3>
                <p className={statusTone(dep.status)}>{dep.status}</p>
                <p className={styles.muted}>Latency: {dep.latencyMs === null ? 'n/a' : `${dep.latencyMs}ms`}</p>
                <p className={styles.muted}>Checked: {formatUtc(dep.checkedAtUtc)} UTC</p>
                {dep.detail ? <p className={styles.muted}>{dep.detail}</p> : null}
              </article>
            ))}
          </div>
        </section>

        <section className={styles.card}>
          <h2 className={styles.sectionTitle}>Chain Provider Health</h2>
          <div className={styles.statusGrid}>
            {filteredProviders.map((provider) => (
              <article key={`${provider.chainKey}_${provider.provider}`} className={styles.managementCard}>
                <h3>{provider.chainKey}</h3>
                <p className={styles.muted}>Provider: {provider.provider}</p>
                <p className={statusTone(provider.status)}>{provider.status}</p>
                <p className={styles.muted}>Latency: {provider.latencyMs === null ? 'n/a' : `${provider.latencyMs}ms`}</p>
                <p className={styles.muted}>Checked: {formatUtc(provider.checkedAtUtc)} UTC</p>
                {provider.detail ? <p className={styles.muted}>{provider.detail}</p> : null}
              </article>
            ))}
          </div>
        </section>

        <section className={styles.card}>
          <h2 className={styles.sectionTitle}>Heartbeat and Queue Signals</h2>
          <div className={styles.statusGrid}>
            <article className={styles.managementCard}>
              <h3>Agents</h3>
              <p className={styles.muted}>Total: {data?.heartbeat.totalAgents ?? 0}</p>
              <p className={styles.muted}>Active: {data?.heartbeat.activeAgents ?? 0}</p>
              <p className={styles.muted}>Offline: {data?.heartbeat.offlineAgents ?? 0}</p>
              <p className={styles.muted}>Degraded: {data?.heartbeat.degradedAgents ?? 0}</p>
              <p className={styles.muted}>Heartbeat misses: {data?.heartbeat.heartbeatMisses ?? 0}</p>
            </article>
            <article className={styles.managementCard}>
              <h3>Queues</h3>
              <p className={styles.muted}>Copy intent pending: {data?.queues.copyIntentPending ?? 0}</p>
              <p className={styles.muted}>Approval pending trades: {data?.queues.approvalPendingTrades ?? 0}</p>
              <p className={styles.muted}>Total depth: {data?.queues.totalDepth ?? 0}</p>
            </article>
          </div>
        </section>

        <section className={styles.card}>
          <h2 className={styles.sectionTitle}>Incident Timeline</h2>
          {(data?.incidents ?? []).length === 0 ? <p className={styles.muted}>No incidents recorded yet.</p> : null}
          <div className={styles.activityList}>
            {(data?.incidents ?? []).map((incident) => (
              <article key={incident.id} className={styles.activityItem}>
                <div>
                  <strong>{incident.summary}</strong>
                </div>
                <div className={styles.muted}>Category: {incident.category}</div>
                <div className={styles.muted}>Severity: {incident.severity}</div>
                <div className={styles.muted}>{formatUtc(incident.atUtc)} UTC</div>
                {incident.details ? <div className={styles.muted}>{incident.details}</div> : null}
              </article>
            ))}
          </div>
        </section>
      </section>
    </div>
  );
}
