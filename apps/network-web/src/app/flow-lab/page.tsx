'use client';

import Link from 'next/link';

import { FLOW_PAGES } from './flow-data';
import styles from './page.module.css';

export default function FlowLabIndexPage() {
  return (
    <div className={styles.page}>
      <header className={styles.hero}>
        <p className={styles.kicker}>Devfolio Flow Lab</p>
        <h1>X-Claw Storyboards</h1>
        <p>
          Each flowchart now has its own page for larger canvas space, cleaner forks, and readable connector paths. Open any module below for full-screen
          diagram capture.
        </p>
      </header>

      <section className={styles.grid}>
        {FLOW_PAGES.map((flow) => (
          <Link key={flow.id} href={`/flow-lab/${flow.id}`} className={styles.card}>
            <div className={styles.cardTop}>
              <h2>{flow.title}</h2>
              <span className={`${styles.badge} ${flow.status === 'Shipped' ? styles.shipped : styles.inProgress}`}>{flow.status}</span>
            </div>
            <p>{flow.subtitle}</p>
            <span className={styles.cta}>Open flowchart</span>
          </Link>
        ))}
      </section>
    </div>
  );
}
