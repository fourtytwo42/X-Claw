import Link from 'next/link';
import { notFound } from 'next/navigation';

import { FLOW_PAGE_IDS, FLOW_PAGES, getFlowPage } from '../flow-data';
import { GraphRender } from './graph-render';
import styles from './page.module.css';

type FlowPageProps = {
  params: Promise<{ flowId: string }>;
};

export function generateStaticParams() {
  return FLOW_PAGE_IDS.map((flowId) => ({ flowId }));
}

export default async function FlowLabDetailPage({ params }: FlowPageProps) {
  const { flowId } = await params;
  const flow = getFlowPage(flowId);
  if (!flow) {
    notFound();
  }

  const index = FLOW_PAGES.findIndex((item) => item.id === flow.id);
  const prev = index > 0 ? FLOW_PAGES[index - 1] : null;
  const next = index < FLOW_PAGES.length - 1 ? FLOW_PAGES[index + 1] : null;

  return (
    <div className={styles.page}>
      <header className={styles.hero}>
        <div>
          <p className={styles.kicker}>Flowchart Module</p>
          <h1>{flow.title}</h1>
          <p>{flow.subtitle}</p>
        </div>
        <div className={styles.heroRight}>
          <span className={`${styles.badge} ${flow.status === 'Shipped' ? styles.shipped : styles.inProgress}`}>{flow.status}</span>
          <Link href="/flow-lab" className={styles.backLink}>
            Back to Index
          </Link>
        </div>
      </header>

      <section className={styles.chartCard}>
        <div className={styles.chartArea}>
          <GraphRender flow={flow} />
        </div>
      </section>

      <section className={styles.textSection}>
        <article className={styles.infoCard}>
          <h3>What Happens</h3>
          <ul>
            {flow.whatHappens.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </article>
        <article className={styles.infoCard}>
          <h3>Why Judges Care</h3>
          <p>{flow.whyItMatters}</p>
        </article>
        <article className={styles.infoCard}>
          <h3>Proof Signal</h3>
          <div className={styles.signalRow}>
            {flow.proofSignal.map((signal) => (
              <span key={signal} className={styles.signalChip}>
                {signal}
              </span>
            ))}
          </div>
        </article>
      </section>

      <nav className={styles.pager} aria-label="Flow module navigation">
        <div>{prev ? <Link href={`/flow-lab/${prev.id}`}>Previous: {prev.navLabel}</Link> : <span className={styles.dim}>Start</span>}</div>
        <div>{next ? <Link href={`/flow-lab/${next.id}`}>Next: {next.navLabel}</Link> : <span className={styles.dim}>End</span>}</div>
      </nav>
    </div>
  );
}
