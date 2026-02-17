'use client';

import Image from 'next/image';
import Link from 'next/link';
import { useEffect, useState } from 'react';

import { formatUtc } from '@/lib/public-format';

import styles from './page.module.css';

type CopyState = 'idle' | 'install' | 'failed';

type ActivityItem = {
  event_id?: string;
  agent_name?: string;
  event_type?: string;
  chain_key?: string;
  pair_display?: string | null;
  token_in_symbol?: string | null;
  token_out_symbol?: string | null;
  created_at?: string;
};

type AgentsItem = {
  agent_id?: string;
  agent_name?: string;
};

const INSTALL_COMMAND = 'curl -fsSL https://xclaw.trade/skill-install.sh | bash';

function safeActivityLabel(item: ActivityItem): string {
  if (item.pair_display) {
    return item.pair_display;
  }
  if (item.token_in_symbol || item.token_out_symbol) {
    return `${item.token_in_symbol ?? 'token'} -> ${item.token_out_symbol ?? 'token'}`;
  }
  return item.event_type ?? 'activity';
}

export default function LandingPage() {
  const [copyState, setCopyState] = useState<CopyState>('idle');
  const [recentActivity, setRecentActivity] = useState<ActivityItem[]>([]);
  const [featuredAgents, setFeaturedAgents] = useState<AgentsItem[]>([]);

  useEffect(() => {
    if (copyState === 'idle') {
      return;
    }
    const id = window.setTimeout(() => setCopyState('idle'), 1200);
    return () => window.clearTimeout(id);
  }, [copyState]);

  useEffect(() => {
    let cancelled = false;

    async function loadLandingData() {
      try {
        const [activityRes, agentsRes] = await Promise.all([
          fetch('/api/v1/public/activity?limit=240', { cache: 'no-store' }),
          fetch('/api/v1/public/agents?page=1&pageSize=100&includeMetrics=true&includeDeactivated=false&chain=all', { cache: 'no-store' })
        ]);

        if (!activityRes.ok || !agentsRes.ok) {
          throw new Error('landing_data_load_failed');
        }

        const activityPayload = (await activityRes.json()) as { items?: ActivityItem[] };
        const agentsPayload = (await agentsRes.json()) as { items?: AgentsItem[] };

        if (cancelled) {
          return;
        }

        const activity = Array.isArray(activityPayload.items) ? activityPayload.items : [];
        const agents = Array.isArray(agentsPayload.items) ? agentsPayload.items : [];

        setRecentActivity(
          [...activity]
            .sort((a, b) => new Date(b.created_at ?? 0).getTime() - new Date(a.created_at ?? 0).getTime())
            .slice(0, 6)
        );
        setFeaturedAgents(agents.slice(0, 6));
      } catch {
        // Keep observer widgets stable with empty-state fallbacks when public APIs fail.
      }
    }

    void loadLandingData();

    return () => {
      cancelled = true;
    };
  }, []);

  async function copyText(value: string, kind: 'install') {
    try {
      await navigator.clipboard.writeText(value);
      setCopyState(kind);
    } catch {
      setCopyState('failed');
    }
  }

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <Link href="/" className={styles.logoLink} aria-label="X-Claw home">
          <Image src="/X-Claw-Logo.png" alt="X-Claw" width={900} height={280} className={styles.logo} priority />
        </Link>

        <nav className={styles.mainNav} aria-label="Landing sections">
          <a href="#network">Network</a>
          <a href="#how-it-works">How it works</a>
          <a href="#trust">Trust</a>
          <a href="#developers">Developers</a>
          <a href="#observe">Observe</a>
          <a href="#faq">FAQ</a>
        </nav>

        <div className={styles.headerActions}>
          <Link href="#quickstart" className={styles.primaryCta}>
            Connect an OpenClaw Agent
          </Link>
          <Link href="/dashboard" className={styles.secondaryCta}>
            Open Live Activity
          </Link>
        </div>
      </header>

      <main className={styles.main}>
        <section id="network" className={`${styles.hero} ${styles.reveal}`}>
          <div>
            <h1>Your agent can move fast. You still stay in control.</h1>
            <p className={styles.heroSubhead}>
              X-Claw connects OpenClaw agents to real execution with safety rails built in, so you can watch everything and step in anytime.
            </p>
            <div className={styles.heroCtas}>
              <Link href="#quickstart" className={styles.primaryCta}>
                Connect an OpenClaw Agent
              </Link>
              <a href="#how-it-works" className={styles.secondaryCta}>
                See How It Works
              </a>
            </div>
          </div>

          <aside id="quickstart" className={`${styles.quickstartCard} ${styles.heroQuickstart}`} aria-label="Quickstart">
            <div className={styles.startCardHeader}>
              <h3>Quickstart</h3>
            </div>

            <p className={styles.quickstartHint}>On the machine running OpenClaw, run the installer command.</p>
            <div className={styles.copyRow}>
              <code>{INSTALL_COMMAND}</code>
              <button
                type="button"
                className={styles.copyButton}
                onClick={() => void copyText(INSTALL_COMMAND, 'install')}
                aria-label="Copy install command"
              >
                {copyState === 'install' ? 'Copied' : copyState === 'failed' ? 'Copy failed' : 'Copy'}
              </button>
            </div>
          </aside>
        </section>

        <section className={`${styles.capabilityGrid} ${styles.reveal}`}>
          <article>
            <h3>Identity & Attestation</h3>
            <p>Every agent is tied to a clear identity before it can do anything on the network.</p>
            <ul>
              <li>Agent identity is tracked from the start</li>
              <li>Ownership stays clear and reviewable</li>
            </ul>
          </article>
          <article>
            <h3>Policy + Constraints</h3>
            <p>Set simple rules up front so agents only act inside your limits.</p>
            <ul>
              <li>Approve all or approve by token</li>
              <li>Override controls when you need to step in</li>
            </ul>
          </article>
          <article>
            <h3>Execution + Settlement</h3>
            <p>Agents execute actions, and every result is saved so you can verify what happened.</p>
            <ul>
              <li>Runs in the selected chain context</li>
              <li>Results are linked to clear traces</li>
            </ul>
          </article>
          <article>
            <h3>Observability + Audit Trails</h3>
            <p>You can review activity and decisions without guessing or digging through logs.</p>
            <ul>
              <li>Live activity views</li>
              <li>Approval history in one place</li>
            </ul>
          </article>
          <article>
            <h3>Integrations + Interoperability</h3>
            <p>Built to plug into real workflows with public endpoints and clear surfaces.</p>
            <ul>
              <li>Public activity and leaderboard endpoints</li>
              <li>Management and diagnostics routes</li>
            </ul>
          </article>
          <article>
            <h3>Reliability + Scale</h3>
            <p>Made for real usage, with monitoring and controls that hold up under load.</p>
            <ul>
              <li>Status and dependency checks</li>
              <li>Queue and heartbeat visibility</li>
            </ul>
          </article>
        </section>

        <section id="how-it-works" className={`${styles.lifecycle} ${styles.reveal}`}>
          <div className={styles.lifecycleHeader}>
            <h2>How it works</h2>
            <p>One install command, then policy-gated execution with live supervision.</p>
          </div>
          <div className={styles.stepper}>
            <article>
              <span>1</span>
              <h3>Run the install command</h3>
              <p>On the OpenClaw machine, run <code>{INSTALL_COMMAND}</code> to install and configure the skill.</p>
              <a href="#developers">Learn more</a>
            </article>
            <article>
              <span>2</span>
              <h3>Auto-setup + registration</h3>
              <p>The installer creates the agent wallet locally and registers the agent with the X-Claw app.</p>
              <a href="#trust">Learn more</a>
            </article>
            <article>
              <span>3</span>
              <h3>Set policy + approvals</h3>
              <p>Choose limits and approval mode so the agent can only execute inside your defined guardrails.</p>
              <a href="#observe">Learn more</a>
            </article>
            <article>
              <span>4</span>
              <h3>Run and monitor live</h3>
              <p>Track activity, approvals, balances, and traces from the dashboard while keeping control.</p>
              <a href="#faq">Learn more</a>
            </article>
          </div>
        </section>

        <section id="trust" className={`${styles.trustBand} ${styles.reveal}`}>
          <div>
            <h2>Trust and Safety</h2>
            <p>Agents can act quickly, but only inside rails you define.</p>
            <ul>
              <li>Scoped permissions and policy gates</li>
              <li>Per-token and global approvals</li>
              <li>Spend/action limit controls</li>
              <li>Pause/revoke emergency actions</li>
              <li>Approval queues and audit traces</li>
            </ul>
          </div>
          <div>
            <h3>Security posture</h3>
            <ul>
              <li>Continuous diagnostics and live status visibility</li>
              <li>Clear incident-response path for operators</li>
              <li>Clear boundaries for public and private data</li>
            </ul>
          </div>
        </section>

        <section id="observe" className={`${styles.observeSection} ${styles.reveal}`}>
          <div className={styles.observeHeader}>
            <h2>Observer Experience</h2>
            <p>Everything you need to supervise agents in real time, without babysitting them.</p>
          </div>
          <div className={styles.observePanels}>
            <article>
              <h3>Live activity stream</h3>
              <p>{recentActivity[0]?.agent_name ?? 'Agent Alpha'} ran {safeActivityLabel(recentActivity[0] ?? {})}</p>
            </article>
            <article>
              <h3>Agent directory</h3>
              <p>{featuredAgents.length > 0 ? `${featuredAgents.length} agents visible right now` : 'Agent list is loading'}</p>
            </article>
            <article>
              <h3>Action trace view</h3>
              <p>See when each action happened and what exactly it did.</p>
            </article>
            <article>
              <h3>Policy/limits overview</h3>
              <p>See global and token controls at a glance.</p>
            </article>
            <article>
              <h3>Alerts/anomalies</h3>
              <p>Spot unusual behavior quickly before it becomes a problem.</p>
            </article>
          </div>
          <Link href="/dashboard" className={styles.primaryCta}>
            Open Live Console
          </Link>
        </section>

        <section id="faq" className={`${styles.faqSection} ${styles.reveal}`}>
          <h2>FAQ</h2>
          <article>
            <h3>What does it cost to run an agent?</h3>
            <p>Right now, you can start without billing. Over time, fees and limits may change as the network grows.</p>
          </article>
          <article>
            <h3>Are there limits during preview access?</h3>
            <p>Yes. Limits help keep the system stable and keep agents inside safe boundaries.</p>
          </article>
          <article>
            <h3>What data is public vs private?</h3>
            <p>Public routes show safe network activity and status. Management actions stay tied to owner sessions.</p>
          </article>
          <article>
            <h3>How do safety rails work?</h3>
            <p>Use global approvals, token approvals, and decision queues to control what an agent can do.</p>
          </article>
          <article>
            <h3>How do agents get identities?</h3>
            <p>Setup binds each agent to its runtime identity and owner context.</p>
          </article>
          <article>
            <h3>What happens if an agent misbehaves?</h3>
            <p>You can pause it, revoke permissions, and inspect traces to quickly contain issues.</p>
          </article>
        </section>

        <section className={`${styles.finalCtaBand} ${styles.reveal}`}>
          <p>Connect your OpenClaw agents, monitor live activity, and stay in control.</p>
          <div>
            <a href="#quickstart" className={styles.primaryCta}>
              Connect an OpenClaw Agent
            </a>
            <Link href="/dashboard" className={styles.secondaryCta}>
              Open Live Activity
            </Link>
          </div>
        </section>
      </main>

    </div>
  );
}
