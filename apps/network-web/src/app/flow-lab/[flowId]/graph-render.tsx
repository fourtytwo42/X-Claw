import styles from './page.module.css';
import { computeEdgeLayouts } from './edge-routing';
import { computeGraphLayout } from './graph-layout';
import type { FlowGraphSpec } from '../flow-data';

function toPath(points: Array<{ x: number; y: number }>) {
  if (points.length < 2) {
    return '';
  }
  return `M ${points[0].x} ${points[0].y} ${points.slice(1).map((p) => `L ${p.x} ${p.y}`).join(' ')}`;
}

function wrapNodeLabel(label: string, maxCharsPerLine: number) {
  const words = label.split(' ');
  const lines: string[] = [];
  let current = '';
  words.forEach((word) => {
    const candidate = current ? `${current} ${word}` : word;
    if (candidate.length <= maxCharsPerLine) {
      current = candidate;
      return;
    }
    if (current) {
      lines.push(current);
    }
    current = word;
  });
  if (current) {
    lines.push(current);
  }

  if (lines.length <= 2) {
    return lines;
  }

  const first = lines[0];
  const second = `${lines[1].slice(0, Math.max(0, maxCharsPerLine - 1))}…`;
  return [first, second];
}

export function GraphRender({ flow }: { flow: FlowGraphSpec }) {
  const layout = computeGraphLayout(flow);
  const edges = computeEdgeLayouts(layout, flow.edges);

  return (
    <svg className={styles.graphSvg} viewBox={`0 0 ${layout.width} ${layout.height}`} role="img" aria-label={`${flow.title} flowchart`}>
      <defs>
        <marker id={`arrow-${flow.id}`} markerWidth="10" markerHeight="8" refX="8.6" refY="4" orient="auto">
          <path d="M0,0 L10,4 L0,8 z" className={styles.edgeArrow} />
        </marker>
      </defs>

      <g>
        {edges.map((edge) => (
          <path key={edge.id} d={toPath(edge.points)} className={`${styles.edgePath} ${edge.tone === 'ok' ? styles.edgeOk : edge.tone === 'warn' ? styles.edgeWarn : ''}`} markerEnd={`url(#arrow-${flow.id})`} />
        ))}
      </g>

      <g>
        {layout.nodes.map((node, idx) => {
          const lines = wrapNodeLabel(node.label, 22);
          return (
            <g key={node.id} transform={`translate(${node.x - node.width / 2} ${node.y - node.height / 2})`}>
              <rect className={`${styles.nodeRect} ${node.tone === 'ok' ? styles.nodeOkRect : node.tone === 'warn' ? styles.nodeWarnRect : ''}`} width={node.width} height={node.height} rx="14" />
              <text className={styles.nodeStep} x="14" y="18">
                {String(idx + 1).padStart(2, '0')}
              </text>
              <text className={styles.nodeTitle} x="14" y="40">
                {lines.map((line, lineIdx) => (
                  <tspan key={`${node.id}-${line}`} x="14" dy={lineIdx === 0 ? 0 : 16}>
                    {line}
                  </tspan>
                ))}
              </text>
            </g>
          );
        })}
      </g>

      <g>
        {edges.map((edge) =>
          edge.label && edge.labelPoint ? (
            <text key={`${edge.id}-label`} x={edge.labelPoint.x} y={edge.labelPoint.y} className={styles.edgeLabel}>
              {edge.label}
            </text>
          ) : null,
        )}
      </g>
    </svg>
  );
}
