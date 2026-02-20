export type FlowStatus = 'Shipped' | 'In Progress';

export type FlowNodeTone = 'neutral' | 'ok' | 'warn';

export type FlowNode = {
  id: string;
  label: string;
  x: number;
  y: number;
  tone?: FlowNodeTone;
};

export type FlowEdge = {
  from: string;
  to: string;
  label?: string;
  tone?: FlowNodeTone;
  fromSide?: 'left' | 'right' | 'top' | 'bottom';
  toSide?: 'left' | 'right' | 'top' | 'bottom';
  via?: Array<{ x: number; y: number }>;
};

export type FlowPage = {
  id: string;
  navLabel: string;
  title: string;
  status: FlowStatus;
  subtitle: string;
  chartHeight: number;
  nodes: FlowNode[];
  edges: FlowEdge[];
  whatHappens: string[];
  whyItMatters: string;
  proofSignal: string[];
};

export const FLOW_PAGES: FlowPage[] = [
  {
    id: 'architecture',
    navLabel: 'Architecture',
    title: 'System Architecture + Trust Boundaries',
    status: 'Shipped',
    subtitle: 'Non-custodial split across agent runtime, network app, and public visibility.',
    chartHeight: 640,
    nodes: [
      { id: 'runtime', label: 'Agent Runtime (Python)', x: 17, y: 30, tone: 'ok' },
      { id: 'keys', label: 'Local Wallet Keys', x: 17, y: 58, tone: 'ok' },
      { id: 'api', label: 'Auth HTTPS API', x: 42, y: 30 },
      { id: 'web', label: 'Network Web + API', x: 66, y: 30 },
      { id: 'db', label: 'Postgres + Redis', x: 66, y: 58 },
      { id: 'views', label: 'Public + Mgmt Surfaces', x: 88, y: 30, tone: 'ok' },
    ],
    edges: [
      { from: 'keys', to: 'runtime', label: 'custody remains local', tone: 'ok' },
      { from: 'runtime', to: 'api' },
      { from: 'api', to: 'web' },
      { from: 'web', to: 'db', fromSide: 'bottom', toSide: 'top' },
      { from: 'web', to: 'views', tone: 'ok' },
    ],
    whatHappens: [
      'Runtime signs and executes locally.',
      'Server validates/records events and status transitions.',
      'Public and management surfaces read the same trusted state.',
    ],
    whyItMatters: 'Judges can see clear trust boundaries and non-custodial architecture in one diagram.',
    proofSignal: ['Agent-local keys only', 'Outbound-only runtime model', 'Public read vs gated control'],
  },
  {
    id: 'lifecycle',
    navLabel: 'Lifecycle',
    title: 'Trade Lifecycle State Machine',
    status: 'Shipped',
    subtitle: 'Policy fork, execution phases, and deterministic terminal states.',
    chartHeight: 700,
    nodes: [
      { id: 'proposed', label: 'proposed', x: 12, y: 40 },
      { id: 'gate', label: 'approval required?', x: 30, y: 40, tone: 'warn' },
      { id: 'approved', label: 'approved', x: 47, y: 24, tone: 'ok' },
      { id: 'pending', label: 'approval_pending', x: 47, y: 56, tone: 'warn' },
      { id: 'exec', label: 'executing', x: 64, y: 24 },
      { id: 'verify', label: 'verifying', x: 81, y: 24 },
      { id: 'filled', label: 'filled', x: 81, y: 44, tone: 'ok' },
      { id: 'failed', label: 'failed', x: 64, y: 66, tone: 'warn' },
      { id: 'rejected', label: 'rejected / expired', x: 81, y: 66, tone: 'warn' },
    ],
    edges: [
      { from: 'proposed', to: 'gate' },
      { from: 'gate', to: 'approved', label: 'no' },
      { from: 'gate', to: 'pending', label: 'yes', tone: 'warn' },
      { from: 'approved', to: 'exec' },
      { from: 'exec', to: 'verify' },
      { from: 'verify', to: 'filled', tone: 'ok', fromSide: 'bottom', toSide: 'top' },
      { from: 'verify', to: 'failed', tone: 'warn', fromSide: 'bottom', toSide: 'top', via: [{ x: 72, y: 46 }] },
      { from: 'pending', to: 'rejected', tone: 'warn' },
      { from: 'failed', to: 'exec', label: 'retry policy', tone: 'warn', fromSide: 'top', toSide: 'bottom', via: [{ x: 56, y: 52 }] },
    ],
    whatHappens: [
      'Trades fork into approval path vs direct approval.',
      'Execution advances through executing and verifying.',
      'Filled, failed, rejected, expired remain explicit outcomes.',
    ],
    whyItMatters: 'This proves deterministic execution behavior and auditable failure handling.',
    proofSignal: ['Canonical transitions', 'Retry constraints', 'Terminal state visibility'],
  },
  {
    id: 'approvals',
    navLabel: 'Approvals',
    title: 'Approval Control Flow',
    status: 'Shipped',
    subtitle: 'Real branching by policy mode and token preapproval, then unified decision sink.',
    chartHeight: 730,
    nodes: [
      { id: 'proposed', label: 'trade proposed', x: 12, y: 40 },
      { id: 'mode', label: 'approval_mode', x: 30, y: 40, tone: 'warn' },
      { id: 'auto', label: 'auto => approved', x: 48, y: 24, tone: 'ok' },
      { id: 'token', label: 'token preapproved?', x: 48, y: 56, tone: 'warn' },
      { id: 'queue', label: 'approval queue', x: 66, y: 56, tone: 'warn' },
      { id: 'web', label: 'web decision', x: 84, y: 40 },
      { id: 'tele', label: 'telegram decision', x: 84, y: 58 },
      { id: 'approved', label: 'approved', x: 84, y: 24, tone: 'ok' },
      { id: 'rejected', label: 'rejected', x: 84, y: 74, tone: 'warn' },
    ],
    edges: [
      { from: 'proposed', to: 'mode' },
      { from: 'mode', to: 'auto', label: 'auto' },
      { from: 'mode', to: 'token', label: 'per_trade', tone: 'warn' },
      { from: 'token', to: 'approved', label: 'yes', tone: 'ok' },
      { from: 'token', to: 'queue', label: 'no', tone: 'warn' },
      { from: 'queue', to: 'web', fromSide: 'top', toSide: 'left', via: [{ x: 74, y: 48 }] },
      { from: 'queue', to: 'tele' },
      { from: 'web', to: 'approved', tone: 'ok' },
      { from: 'web', to: 'rejected', tone: 'warn' },
      { from: 'tele', to: 'approved', tone: 'ok', fromSide: 'top', toSide: 'bottom', via: [{ x: 90, y: 42 }] },
      { from: 'tele', to: 'rejected', tone: 'warn' },
      { from: 'auto', to: 'approved', tone: 'ok' },
    ],
    whatHappens: [
      'First fork: auto vs per_trade policy.',
      'Second fork: token preapproved yes/no.',
      'Manual channels converge into one approval result model.',
    ],
    whyItMatters: 'This diagram shows that approvals are a first-class control plane, not a UI-only switch.',
    proofSignal: ['Policy-driven branching', 'Web + Telegram parity', 'Unified approve/reject contract'],
  },
  {
    id: 'x402',
    navLabel: 'x402',
    title: 'x402 Payment Flow',
    status: 'Shipped',
    subtitle: 'Hosted receive link lifecycle with challenge/settle branches and mirrored evidence.',
    chartHeight: 680,
    nodes: [
      { id: 'create', label: 'create receive request', x: 14, y: 40 },
      { id: 'hosted', label: '/api/v1/x402/pay/{agentId}/{linkToken}', x: 37, y: 40 },
      { id: 'challenge', label: '402 payment_required', x: 60, y: 25, tone: 'warn' },
      { id: 'settled', label: '200 payment_settled', x: 60, y: 56, tone: 'ok' },
      { id: 'mirror', label: 'mirror inbound/outbound records', x: 82, y: 40, tone: 'ok' },
      { id: 'timeline', label: 'activity + approvals timeline', x: 82, y: 62, tone: 'ok' },
    ],
    edges: [
      { from: 'create', to: 'hosted' },
      { from: 'hosted', to: 'challenge', label: 'missing payment header', tone: 'warn' },
      { from: 'hosted', to: 'settled', label: 'valid payment', tone: 'ok' },
      { from: 'challenge', to: 'settled', label: 'pay + retry', tone: 'ok', fromSide: 'bottom', toSide: 'top' },
      { from: 'settled', to: 'mirror', tone: 'ok' },
      { from: 'mirror', to: 'timeline', tone: 'ok', fromSide: 'bottom', toSide: 'top' },
    ],
    whatHappens: [
      'Owner creates durable hosted request metadata.',
      'Payer sees challenge and settles with x402-compliant header.',
      'Server mirrors payment lifecycle into timeline and approvals context.',
    ],
    whyItMatters: 'Judges see payment-native agent workflows, not just static payment claims.',
    proofSignal: ['402 challenge contract', 'Hosted link model', 'Inbound/outbound mirror visibility'],
  },
  {
    id: 'multichain',
    navLabel: 'Multi-Chain',
    title: 'Multi-Chain Capability Gating',
    status: 'Shipped',
    subtitle: 'Wallet-first availability with operation-level enable/disable truthfulness.',
    chartHeight: 680,
    nodes: [
      { id: 'registry', label: 'chain config registry', x: 14, y: 40 },
      { id: 'gate', label: 'capability gate', x: 36, y: 40, tone: 'warn' },
      { id: 'wallet', label: 'wallet-first allowed', x: 58, y: 22, tone: 'ok' },
      { id: 'trade', label: 'trade/liquidity enabled', x: 58, y: 40, tone: 'ok' },
      { id: 'fail', label: 'unsupported => fail closed', x: 58, y: 62, tone: 'warn' },
      { id: 'ui', label: 'truthful web/runtime status', x: 82, y: 40, tone: 'ok' },
    ],
    edges: [
      { from: 'registry', to: 'gate' },
      { from: 'gate', to: 'wallet', label: 'wallet scope' },
      { from: 'gate', to: 'trade', label: 'enabled', tone: 'ok' },
      { from: 'gate', to: 'fail', label: 'disabled', tone: 'warn' },
      { from: 'wallet', to: 'ui', fromSide: 'right', toSide: 'top', via: [{ x: 74, y: 22 }] },
      { from: 'trade', to: 'ui', tone: 'ok' },
      { from: 'fail', to: 'ui', tone: 'warn', fromSide: 'right', toSide: 'bottom', via: [{ x: 74, y: 62 }] },
    ],
    whatHappens: [
      'Capabilities are sourced from shared chain configs.',
      'Wallet actions can remain available when execution is disabled.',
      'Unsupported operations fail with deterministic, explicit errors.',
    ],
    whyItMatters: 'This prevents overpromising and keeps cross-chain support claims credible.',
    proofSignal: ['Operation-level gates', 'Wallet-first portability', 'Deterministic fail-closed behavior'],
  },
  {
    id: 'routing',
    navLabel: 'Routing',
    title: 'Execution Provider Orchestration',
    status: 'In Progress',
    subtitle: 'Uniswap proxy-first routing with fallback and provenance reporting.',
    chartHeight: 700,
    nodes: [
      { id: 'select', label: 'provider select', x: 14, y: 40 },
      { id: 'proxy', label: 'uniswap_api attempt', x: 36, y: 40, tone: 'warn' },
      { id: 'ok', label: 'proxy success', x: 58, y: 24, tone: 'ok' },
      { id: 'fallback', label: 'legacy fallback available?', x: 58, y: 58, tone: 'warn' },
      { id: 'exec', label: 'execute path', x: 82, y: 24, tone: 'ok' },
      { id: 'noexec', label: 'no provider => fail closed', x: 82, y: 58, tone: 'warn' },
      { id: 'prove', label: 'providerUsed + fallbackReason', x: 82, y: 76 },
    ],
    edges: [
      { from: 'select', to: 'proxy' },
      { from: 'proxy', to: 'ok', label: 'success', tone: 'ok' },
      { from: 'proxy', to: 'fallback', label: 'error', tone: 'warn' },
      { from: 'ok', to: 'exec', tone: 'ok' },
      { from: 'fallback', to: 'exec', label: 'yes' },
      { from: 'fallback', to: 'noexec', label: 'no', tone: 'warn' },
      { from: 'exec', to: 'prove', fromSide: 'bottom', toSide: 'top' },
      { from: 'noexec', to: 'prove', tone: 'warn', fromSide: 'bottom', toSide: 'bottom', via: [{ x: 92, y: 88 }] },
    ],
    whatHappens: [
      'Runtime starts with chain-configured primary provider.',
      'Proxy failures branch into fallback or deterministic fail-closed path.',
      'Status payload includes provider provenance fields.',
    ],
    whyItMatters: 'This makes reliability and degraded-path behavior inspectable for judges.',
    proofSignal: ['Server-kept API key boundary', 'Fallback contract', 'Provenance fields in status'],
  },
  {
    id: 'observability',
    navLabel: 'Observability',
    title: 'Public Observability Loop',
    status: 'Shipped',
    subtitle: 'Agent actions become public trust signals while management writes remain gated.',
    chartHeight: 680,
    nodes: [
      { id: 'agent', label: 'agent writes events/status', x: 14, y: 40 },
      { id: 'persist', label: 'validate + persist', x: 36, y: 40 },
      { id: 'metrics', label: 'metrics + ranking jobs', x: 58, y: 26, tone: 'ok' },
      { id: 'history', label: 'activity/profile read models', x: 58, y: 56, tone: 'ok' },
      { id: 'public', label: 'dashboard / explore / profile', x: 82, y: 26, tone: 'ok' },
      { id: 'mgmt', label: '/agents/:id management (gated)', x: 82, y: 56, tone: 'warn' },
    ],
    edges: [
      { from: 'agent', to: 'persist' },
      { from: 'persist', to: 'metrics', tone: 'ok' },
      { from: 'persist', to: 'history', tone: 'ok' },
      { from: 'metrics', to: 'public', tone: 'ok' },
      { from: 'history', to: 'public', tone: 'ok', fromSide: 'right', toSide: 'bottom', via: [{ x: 70, y: 40 }] },
      { from: 'history', to: 'mgmt' },
    ],
    whatHappens: [
      'Runtime writes are validated and persisted through canonical contracts.',
      'Read models and ranking update from execution outcomes.',
      'Public visibility and management controls read from the same truth source.',
    ],
    whyItMatters: 'Judges can verify operational transparency without exposing privileged controls.',
    proofSignal: ['Contracted ingest endpoints', 'Read-model loop', 'Public read + gated write boundary'],
  },
];

export const FLOW_PAGE_IDS = FLOW_PAGES.map((flow) => flow.id);

export function getFlowPage(flowId: string): FlowPage | null {
  return FLOW_PAGES.find((flow) => flow.id === flowId) ?? null;
}
