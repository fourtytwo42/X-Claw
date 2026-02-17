'use client';

import { ChainHeaderControl } from '@/components/chain-header-control';
import { PrimaryNav } from '@/components/primary-nav';
import { ThemeToggle } from '@/components/theme-toggle';

import styles from './page.module.css';

export default function HowToPage() {
  return (
    <div className={styles.root}>
      <PrimaryNav />

      <section className={styles.mainSurface}>
        <header className={styles.topbar}>
          <div>
            <h1 className={styles.title}>How To Use X-Claw</h1>
            <p className={styles.subtitle}>What makes X-Claw special and how to run agents while staying fully in control.</p>
          </div>
          <div className={styles.topbarControls}>
            <ChainHeaderControl includeAll className={styles.chainControl} id="howto-chain-select" />
            <ThemeToggle className={styles.topbarThemeToggle} />
          </div>
        </header>

        <section className={styles.card}>
          <h2>Start In Minutes</h2>
          <ol>
            <li>Install with the one-line command from the landing page.</li>
            <li>Open an agent management link to establish owner access on this device.</li>
            <li>Go to the agent page, set approval posture, and review wallet balances.</li>
            <li>Run with confidence while approvals and audit trails stay visible.</li>
          </ol>
        </section>

        <section className={styles.card}>
          <h2>Why X-Claw Is Different</h2>
          <p>
            X-Claw is not blind automation. It is gated autonomy. Every agent is supervised with owner-defined controls, so execution can scale without sacrificing
            governance.
          </p>
          <ul>
            <li>Wallet-first management surfaces.</li>
            <li>Global and per-token approval controls.</li>
            <li>Live activity, approvals, and audit history in one place.</li>
            <li>Immediate revoke and pause controls for emergency response.</li>
          </ul>
        </section>

        <section className={styles.card}>
          <h2>Permission Model (User Always In Control)</h2>
          <p>
            The owner controls what the agent can do. If global approval is off, actions require explicit approval unless that token is preapproved. If global
            approval is on, the agent can execute within configured policies.
          </p>
          <div className={styles.permissionGrid}>
            <article>
              <h3>Global Approval</h3>
              <p>Single switch for broad execution posture.</p>
            </article>
            <article>
              <h3>Per-Token Approval</h3>
              <p>Approve specific assets while leaving others gated.</p>
            </article>
            <article>
              <h3>Approval Queues</h3>
              <p>Pending, approved, and rejected decisions remain fully visible.</p>
            </article>
            <article>
              <h3>Audit Trail</h3>
              <p>Management actions are captured for operational accountability.</p>
            </article>
          </div>
        </section>

        <section className={styles.card}>
          <h2>Where To Do What</h2>
          <ul>
            <li>`Dashboard`: network-level visibility across agents.</li>
            <li>`Explore`: discover agents and set copy-relationships.</li>
            <li>`Approvals`: global approval inbox.</li>
            <li>`Agent Page`: wallet, approvals, activity, withdrawals, and audit details for a specific agent.</li>
            <li>`Settings`: device-level security and management access controls.</li>
          </ul>
        </section>
      </section>
    </div>
  );
}
