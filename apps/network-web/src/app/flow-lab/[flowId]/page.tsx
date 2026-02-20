import Link from 'next/link';
import { notFound } from 'next/navigation';

import { FLOW_PAGE_IDS, FLOW_PAGES, getFlowPage, type FlowEdge, type FlowNode } from '../flow-data';
import styles from './page.module.css';

type FlowPageProps = {
  params: Promise<{ flowId: string }>;
};

export function generateStaticParams() {
  return FLOW_PAGE_IDS.map((flowId) => ({ flowId }));
}

function sidePoint(node: FlowNode, side: 'left' | 'right' | 'top' | 'bottom') {
  if (side === 'left') {
    return { x: node.x - 8.8, y: node.y };
  }
  if (side === 'right') {
    return { x: node.x + 8.8, y: node.y };
  }
  if (side === 'top') {
    return { x: node.x, y: node.y - 5.6 };
  }
  return { x: node.x, y: node.y + 5.6 };
}

function resolveSide(from: FlowNode, to: FlowNode, forStart: boolean): 'left' | 'right' | 'top' | 'bottom' {
  const dx = to.x - from.x;
  const dy = to.y - from.y;
  if (Math.abs(dx) >= Math.abs(dy)) {
    if (forStart) {
      return dx >= 0 ? 'right' : 'left';
    }
    return dx >= 0 ? 'left' : 'right';
  }
  if (forStart) {
    return dy >= 0 ? 'bottom' : 'top';
  }
  return dy >= 0 ? 'top' : 'bottom';
}

function polyPath(points: Array<{ x: number; y: number }>) {
  if (points.length < 2) {
    return '';
  }
  return `M ${points[0].x} ${points[0].y} ${points.slice(1).map((point) => `L ${point.x} ${point.y}`).join(' ')}`;
}

function edgeLabelPoint(points: Array<{ x: number; y: number }>) {
  const mid = Math.floor((points.length - 1) / 2);
  const start = points[mid];
  const end = points[mid + 1] ?? points[mid];
  return {
    x: start.x + (end.x - start.x) * 0.5,
    y: start.y + (end.y - start.y) * 0.5 - 1.4,
  };
}

function edgeClass(edge: FlowEdge) {
  if (edge.tone === 'ok') {
    return styles.edgeOk;
  }
  if (edge.tone === 'warn') {
    return styles.edgeWarn;
  }
  return '';
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
  const nodeMap = new Map(flow.nodes.map((node) => [node.id, node]));

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
        <div className={styles.chartArea} style={{ height: `${flow.chartHeight}px` }}>
          <svg className={styles.edgesLayer} viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
            <defs>
              <marker id={`arrow-${flow.id}`} markerWidth="6" markerHeight="6" refX="5.2" refY="3" orient="auto">
                <path d="M0,0 L6,3 L0,6 z" className={styles.edgeArrow} />
              </marker>
            </defs>
            {flow.edges.map((edge) => {
              const from = nodeMap.get(edge.from);
              const to = nodeMap.get(edge.to);
              if (!from || !to) {
                return null;
              }
              const startSide = edge.fromSide ?? resolveSide(from, to, true);
              const endSide = edge.toSide ?? resolveSide(from, to, false);
              const start = sidePoint(from, startSide);
              const end = sidePoint(to, endSide);
              const points = [start, ...(edge.via ?? []), end];
              const labelPoint = edgeLabelPoint(points);
              return (
                <g key={`${edge.from}-${edge.to}`}>
                  <path d={polyPath(points)} className={`${styles.edgePath} ${edgeClass(edge)}`} markerEnd={`url(#arrow-${flow.id})`} />
                  {edge.label ? (
                    <text x={labelPoint.x} y={labelPoint.y} className={styles.edgeLabel}>
                      {edge.label}
                    </text>
                  ) : null}
                </g>
              );
            })}
          </svg>

          {flow.nodes.map((node, idx) => (
            <article
              key={node.id}
              className={`${styles.node} ${
                node.tone === 'ok' ? styles.nodeOk : node.tone === 'warn' ? styles.nodeWarn : ''
              }`}
              style={{ left: `${node.x}%`, top: `${node.y}%` }}
            >
              <span className={styles.nodeStep}>{String(idx + 1).padStart(2, '0')}</span>
              <h2>{node.label}</h2>
            </article>
          ))}
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
