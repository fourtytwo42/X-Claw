import type { FlowEdgeSpec } from '../flow-data';
import type { ComputedNodeLayout, GraphLayout } from './graph-layout';

export type ComputedEdgeLayout = {
  id: string;
  tone: FlowEdgeSpec['tone'];
  label?: string;
  points: Array<{ x: number; y: number }>;
  labelPoint?: { x: number; y: number };
};

type Rect = { left: number; right: number; top: number; bottom: number };

function intersectsRect(p1: { x: number; y: number }, p2: { x: number; y: number }, rect: Rect) {
  if (p1.x === p2.x) {
    const x = p1.x;
    if (x < rect.left || x > rect.right) {
      return false;
    }
    const minY = Math.min(p1.y, p2.y);
    const maxY = Math.max(p1.y, p2.y);
    return maxY >= rect.top && minY <= rect.bottom;
  }
  if (p1.y === p2.y) {
    const y = p1.y;
    if (y < rect.top || y > rect.bottom) {
      return false;
    }
    const minX = Math.min(p1.x, p2.x);
    const maxX = Math.max(p1.x, p2.x);
    return maxX >= rect.left && minX <= rect.right;
  }
  return false;
}

function pathHitsNodes(points: Array<{ x: number; y: number }>, nodes: ComputedNodeLayout[], fromId: string, toId: string) {
  const blockers = nodes.filter((node) => node.id !== fromId && node.id !== toId);
  for (let i = 0; i < points.length - 1; i += 1) {
    const p1 = points[i];
    const p2 = points[i + 1];
    const collides = blockers.some((node) =>
      intersectsRect(p1, p2, {
        left: node.bounds.left - 8,
        right: node.bounds.right + 8,
        top: node.bounds.top - 8,
        bottom: node.bounds.bottom + 8,
      }),
    );
    if (collides) {
      return true;
    }
  }
  return false;
}

function choosePorts(from: ComputedNodeLayout, to: ComputedNodeLayout, hint: FlowEdgeSpec['routeHint']) {
  if (hint === 'split_up') {
    return { start: from.ports.right, end: to.ports.left };
  }
  if (hint === 'split_down') {
    return { start: from.ports.right, end: to.ports.left };
  }
  if (hint === 'outer_top' || hint === 'outer_bottom') {
    return { start: from.ports.right, end: to.ports.left };
  }

  const dx = to.x - from.x;
  const dy = to.y - from.y;
  if (Math.abs(dx) >= Math.abs(dy)) {
    if (dx >= 0) {
      return { start: from.ports.right, end: to.ports.left };
    }
    return { start: from.ports.left, end: to.ports.right };
  }
  if (dy >= 0) {
    return { start: from.ports.bottom, end: to.ports.top };
  }
  return { start: from.ports.top, end: to.ports.bottom };
}

function routeDefault(
  from: ComputedNodeLayout,
  to: ComputedNodeLayout,
  edgeIndex: number,
  nodes: ComputedNodeLayout[],
  hint: FlowEdgeSpec['routeHint'],
) {
  const { start, end } = choosePorts(from, to, hint);
  const pad = 24;
  const horizontalBias = Math.max(start.x, end.x) + 28 + edgeIndex * 4;
  const topRail = Math.min(from.bounds.top, to.bounds.top) - 54 - (edgeIndex % 3) * 16;
  const bottomRail = Math.max(from.bounds.bottom, to.bounds.bottom) + 54 + (edgeIndex % 3) * 16;

  let points: Array<{ x: number; y: number }>;
  if (hint === 'outer_top') {
    points = [start, { x: start.x + pad, y: start.y }, { x: start.x + pad, y: topRail }, { x: end.x - pad, y: topRail }, { x: end.x - pad, y: end.y }, end];
  } else if (hint === 'outer_bottom') {
    points = [start, { x: start.x + pad, y: start.y }, { x: start.x + pad, y: bottomRail }, { x: end.x - pad, y: bottomRail }, { x: end.x - pad, y: end.y }, end];
  } else if (hint === 'split_up') {
    const splitY = Math.min(start.y, end.y) - 34 - (edgeIndex % 2) * 10;
    points = [start, { x: start.x + pad, y: start.y }, { x: start.x + pad, y: splitY }, { x: end.x - pad, y: splitY }, { x: end.x - pad, y: end.y }, end];
  } else if (hint === 'split_down') {
    const splitY = Math.max(start.y, end.y) + 34 + (edgeIndex % 2) * 10;
    points = [start, { x: start.x + pad, y: start.y }, { x: start.x + pad, y: splitY }, { x: end.x - pad, y: splitY }, { x: end.x - pad, y: end.y }, end];
  } else {
    const midX = Math.min(horizontalBias, (start.x + end.x) * 0.5 + 70);
    points = [start, { x: start.x + pad, y: start.y }, { x: midX, y: start.y }, { x: midX, y: end.y }, { x: end.x - pad, y: end.y }, end];
  }

  if (!pathHitsNodes(points, nodes, from.id, to.id)) {
    return points;
  }

  const offsetSequence = [0, -38, 38, -76, 76];
  for (const offset of offsetSequence) {
    const midX = (start.x + end.x) * 0.5;
    const alt = [start, { x: start.x + pad, y: start.y }, { x: midX, y: start.y + offset }, { x: midX, y: end.y + offset }, { x: end.x - pad, y: end.y }, end];
    if (!pathHitsNodes(alt, nodes, from.id, to.id)) {
      return alt;
    }
  }

  return points;
}

function labelPointForPath(points: Array<{ x: number; y: number }>) {
  if (points.length < 2) {
    return undefined;
  }
  let total = 0;
  const lengths: number[] = [];
  for (let i = 0; i < points.length - 1; i += 1) {
    const dx = points[i + 1].x - points[i].x;
    const dy = points[i + 1].y - points[i].y;
    const len = Math.hypot(dx, dy);
    lengths.push(len);
    total += len;
  }
  const target = total * 0.5;
  let acc = 0;
  for (let i = 0; i < lengths.length; i += 1) {
    const next = acc + lengths[i];
    if (target <= next) {
      const t = lengths[i] === 0 ? 0 : (target - acc) / lengths[i];
      return {
        x: points[i].x + (points[i + 1].x - points[i].x) * t,
        y: points[i].y + (points[i + 1].y - points[i].y) * t - 10,
      };
    }
    acc = next;
  }
  return { x: points[0].x, y: points[0].y };
}

export function computeEdgeLayouts(layout: GraphLayout, edges: FlowEdgeSpec[]): ComputedEdgeLayout[] {
  const result: ComputedEdgeLayout[] = [];
  edges.forEach((edge, index) => {
    const from = layout.nodeMap.get(edge.from);
    const to = layout.nodeMap.get(edge.to);
    if (!from || !to) {
      return;
    }

    const points = routeDefault(from, to, index, layout.nodes, edge.routeHint ?? 'default');
    result.push({
      id: `${edge.from}-${edge.to}-${index}`,
      tone: edge.tone,
      label: edge.label,
      points,
      labelPoint: edge.label ? labelPointForPath(points) : undefined,
    });
  });

  return result;
}
