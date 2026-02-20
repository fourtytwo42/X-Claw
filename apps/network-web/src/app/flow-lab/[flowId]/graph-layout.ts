import type { FlowGraphSpec, FlowNodeSpec } from '../flow-data';

export type PortSet = {
  left: { x: number; y: number };
  right: { x: number; y: number };
  top: { x: number; y: number };
  bottom: { x: number; y: number };
};

export type ComputedNodeLayout = {
  id: string;
  label: string;
  tone: FlowNodeSpec['tone'];
  level: number;
  lane: number;
  order: number;
  x: number;
  y: number;
  width: number;
  height: number;
  ports: PortSet;
  bounds: { left: number; right: number; top: number; bottom: number };
};

export type GraphLayout = {
  width: number;
  height: number;
  nodes: ComputedNodeLayout[];
  nodeMap: Map<string, ComputedNodeLayout>;
  levelCount: number;
  warnings: string[];
};

type Preset = {
  width: number;
  height: number;
  nodeWidth: number;
  nodeHeight: number;
  rowGap: number;
  leftPad: number;
  rightPad: number;
};

const PRESETS: Record<FlowGraphSpec['chartPreset'], Preset> = {
  standard: { width: 1360, height: 560, nodeWidth: 212, nodeHeight: 90, rowGap: 118, leftPad: 130, rightPad: 130 },
  wide: { width: 1520, height: 620, nodeWidth: 220, nodeHeight: 92, rowGap: 124, leftPad: 140, rightPad: 140 },
  xl: { width: 1720, height: 760, nodeWidth: 226, nodeHeight: 94, rowGap: 128, leftPad: 150, rightPad: 150 },
};

function sortUniqueIds(nodes: FlowNodeSpec[]) {
  const seen = new Set<string>();
  const dupes: string[] = [];
  nodes.forEach((node) => {
    if (seen.has(node.id)) {
      dupes.push(node.id);
    }
    seen.add(node.id);
  });
  return dupes;
}

function topologicalLevels(flow: FlowGraphSpec): { levels: Map<string, number>; warnings: string[] } {
  const warnings: string[] = [];
  const levels = new Map<string, number>();
  const indegree = new Map<string, number>();
  const out = new Map<string, string[]>();

  flow.nodes.forEach((node) => {
    indegree.set(node.id, 0);
    out.set(node.id, []);
  });

  flow.edges.forEach((edge) => {
    if (!indegree.has(edge.from) || !indegree.has(edge.to)) {
      warnings.push(`Unknown edge reference: ${edge.from} -> ${edge.to}`);
      return;
    }
    indegree.set(edge.to, (indegree.get(edge.to) ?? 0) + 1);
    out.get(edge.from)?.push(edge.to);
  });

  const queue = [...flow.nodes.map((node) => node.id).filter((id) => (indegree.get(id) ?? 0) === 0)];
  queue.sort();
  queue.forEach((id) => levels.set(id, 0));

  let processed = 0;
  while (queue.length) {
    const current = queue.shift() as string;
    processed += 1;
    const currentLevel = levels.get(current) ?? 0;
    (out.get(current) ?? []).forEach((target) => {
      const targetLevel = levels.get(target) ?? 0;
      levels.set(target, Math.max(targetLevel, currentLevel + 1));
      const nextDegree = (indegree.get(target) ?? 0) - 1;
      indegree.set(target, nextDegree);
      if (nextDegree === 0) {
        queue.push(target);
      }
    });
  }

  if (processed < flow.nodes.length) {
    warnings.push(`Cycle detected in graph "${flow.id}". Applied fallback level assignment.`);
    let fallbackLevel = Math.max(...Array.from(levels.values()), 0);
    flow.nodes.forEach((node) => {
      if (!levels.has(node.id)) {
        fallbackLevel += 1;
        levels.set(node.id, fallbackLevel);
      }
    });
  }

  return { levels, warnings };
}

function sortWithinLevels(flow: FlowGraphSpec, levels: Map<string, number>): Map<number, FlowNodeSpec[]> {
  const byLevel = new Map<number, FlowNodeSpec[]>();
  flow.nodes.forEach((node) => {
    const level = node.override?.level ?? levels.get(node.id) ?? 0;
    if (!byLevel.has(level)) {
      byLevel.set(level, []);
    }
    byLevel.get(level)?.push(node);
  });

  const sortedLevels = [...byLevel.keys()].sort((a, b) => a - b);
  const positionById = new Map<string, number>();

  sortedLevels.forEach((level) => {
    const arr = byLevel.get(level) ?? [];
    arr.sort((a, b) => {
      const laneA = a.override?.lane ?? a.lane ?? 0;
      const laneB = b.override?.lane ?? b.lane ?? 0;
      if (laneA !== laneB) {
        return laneA - laneB;
      }
      const orderA = a.override?.order ?? a.order ?? 0;
      const orderB = b.override?.order ?? b.order ?? 0;
      if (orderA !== orderB) {
        return orderA - orderB;
      }
      return a.id.localeCompare(b.id);
    });

    if (level === sortedLevels[0]) {
      arr.forEach((node, idx) => positionById.set(node.id, idx));
      return;
    }

    // Lightweight crossing minimization: re-sort by predecessor barycenter where available.
    arr.sort((a, b) => {
      const predsA = flow.edges.filter((edge) => edge.to === a.id).map((edge) => positionById.get(edge.from)).filter((v): v is number => typeof v === 'number');
      const predsB = flow.edges.filter((edge) => edge.to === b.id).map((edge) => positionById.get(edge.from)).filter((v): v is number => typeof v === 'number');
      const baryA = predsA.length ? predsA.reduce((sum, v) => sum + v, 0) / predsA.length : Number.MAX_SAFE_INTEGER;
      const baryB = predsB.length ? predsB.reduce((sum, v) => sum + v, 0) / predsB.length : Number.MAX_SAFE_INTEGER;
      if (baryA !== baryB) {
        return baryA - baryB;
      }
      const laneA = a.override?.lane ?? a.lane ?? 0;
      const laneB = b.override?.lane ?? b.lane ?? 0;
      if (laneA !== laneB) {
        return laneA - laneB;
      }
      return a.id.localeCompare(b.id);
    });
    arr.forEach((node, idx) => positionById.set(node.id, idx));
  });

  return byLevel;
}

export function computeGraphLayout(flow: FlowGraphSpec): GraphLayout {
  const warnings: string[] = [];
  const dupes = sortUniqueIds(flow.nodes);
  if (dupes.length > 0) {
    warnings.push(`Duplicate node IDs detected: ${dupes.join(', ')}`);
  }

  const preset = PRESETS[flow.chartPreset];
  const { levels, warnings: topoWarnings } = topologicalLevels(flow);
  warnings.push(...topoWarnings);
  const grouped = sortWithinLevels(flow, levels);
  const levelKeys = [...grouped.keys()].sort((a, b) => a - b);
  const maxLevel = levelKeys.length ? levelKeys[levelKeys.length - 1] : 0;
  const levelCount = Math.max(1, maxLevel + 1);
  const colGap = levelCount > 1 ? (preset.width - preset.leftPad - preset.rightPad) / (levelCount - 1) : 0;

  const nodes: ComputedNodeLayout[] = [];
  const nodeMap = new Map<string, ComputedNodeLayout>();

  levelKeys.forEach((level) => {
    const levelNodes = grouped.get(level) ?? [];
    const span = (levelNodes.length - 1) * preset.rowGap;
    const firstY = preset.height * 0.5 - span * 0.5;
    levelNodes.forEach((node, idx) => {
      const lane = node.override?.lane ?? node.lane ?? idx;
      const order = node.override?.order ?? node.order ?? idx;
      const x = preset.leftPad + colGap * level;
      const y = firstY + idx * preset.rowGap;
      const bounds = {
        left: x - preset.nodeWidth * 0.5,
        right: x + preset.nodeWidth * 0.5,
        top: y - preset.nodeHeight * 0.5,
        bottom: y + preset.nodeHeight * 0.5,
      };
      const layoutNode: ComputedNodeLayout = {
        id: node.id,
        label: node.label,
        tone: node.tone,
        level,
        lane,
        order,
        x,
        y,
        width: preset.nodeWidth,
        height: preset.nodeHeight,
        ports: {
          left: { x: bounds.left, y },
          right: { x: bounds.right, y },
          top: { x, y: bounds.top },
          bottom: { x, y: bounds.bottom },
        },
        bounds,
      };
      nodes.push(layoutNode);
      nodeMap.set(node.id, layoutNode);
    });
  });

  return { width: preset.width, height: preset.height, nodes, nodeMap, levelCount, warnings };
}
