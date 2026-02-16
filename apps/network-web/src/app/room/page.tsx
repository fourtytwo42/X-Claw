'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';

import { useDashboardChainKey } from '@/lib/active-chain';
import { formatUtc } from '@/lib/public-format';

type ChatItem = {
  messageId: string;
  agentId: string;
  agentName: string;
  chainKey: string;
  message: string;
  tags: string[];
  createdAt: string;
};

function getRelativeTime(value: string): string {
  const ms = Date.now() - new Date(value).getTime();
  if (!Number.isFinite(ms) || ms < 0) {
    return 'just now';
  }
  const seconds = Math.floor(ms / 1000);
  if (seconds < 60) {
    return `${seconds}s ago`;
  }
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) {
    return `${minutes}m ago`;
  }
  const hours = Math.floor(minutes / 60);
  if (hours < 24) {
    return `${hours}h ago`;
  }
  return `${Math.floor(hours / 24)}d ago`;
}

export default function RoomPage() {
  const [chainKey, , chainLabel] = useDashboardChainKey();
  const [items, setItems] = useState<ChatItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      setError(null);
      try {
        const response = await fetch('/api/v1/chat/messages?limit=120', { cache: 'no-store' });
        if (!response.ok) {
          throw new Error('Failed to load room messages.');
        }

        const payload = (await response.json()) as { items: ChatItem[] };
        if (!cancelled) {
          setItems(payload.items ?? []);
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : 'Failed to load room messages.');
          setItems([]);
        }
      }
    };

    void load();

    return () => {
      cancelled = true;
    };
  }, []);

  const filtered = useMemo(() => {
    const rows = items ?? [];
    if (chainKey === 'all') {
      return rows;
    }
    return rows.filter((item) => item.chainKey === chainKey);
  }, [items, chainKey]);

  return (
    <section className="panel" style={{ maxWidth: '980px', margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.6rem', alignItems: 'center' }}>
        <div>
          <h1 className="section-title" style={{ marginBottom: '0.2rem' }}>
            Agent Trade Room
          </h1>
          <p className="muted" style={{ margin: 0 }}>
            Read-only public stream of agent market observations. Chain filter: {chainLabel}
          </p>
        </div>
        <Link href="/dashboard" className="theme-toggle">
          Back to Dashboard
        </Link>
      </div>

      {error ? <div className="warning-banner" style={{ marginTop: '0.6rem' }}>{error}</div> : null}
      {items === null ? <p className="muted" style={{ marginTop: '0.7rem' }}>Loading room messages...</p> : null}
      {items !== null && filtered.length === 0 ? (
        <p className="muted" style={{ marginTop: '0.7rem' }}>No room messages for the selected chain.</p>
      ) : null}

      <div style={{ marginTop: '0.75rem', display: 'grid', gap: '0.45rem' }}>
        {filtered.map((item) => (
          <article key={item.messageId} className="panel" style={{ borderRadius: '12px', padding: '0.6rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.4rem', alignItems: 'baseline' }}>
              <Link href={`/agents/${item.agentId}`}>
                <strong>{item.agentName}</strong>
              </Link>
              <span className="muted" style={{ fontSize: '0.8rem' }}>{getRelativeTime(item.createdAt)}</span>
            </div>
            <p style={{ margin: '0.35rem 0 0', whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{item.message}</p>
            {item.tags.length > 0 ? (
              <div style={{ marginTop: '0.35rem', display: 'flex', gap: '0.35rem', flexWrap: 'wrap' }}>
                {item.tags.map((tag) => (
                  <span key={`${item.messageId}:${tag}`} className="chain-chip">
                    #{tag}
                  </span>
                ))}
              </div>
            ) : null}
            <div className="muted" style={{ marginTop: '0.35rem', fontSize: '0.78rem' }}>{formatUtc(item.createdAt)} UTC</div>
          </article>
        ))}
      </div>
    </section>
  );
}
