export type FlowStatus = 'Shipped' | 'In Progress';
export type FlowNodeTone = 'neutral' | 'ok' | 'warn';
export type RouteHint = 'default' | 'outer_top' | 'outer_bottom' | 'split_up' | 'split_down';

export type FlowNodeSpec = {
  id: string;
  label: string;
  tone?: FlowNodeTone;
  lane?: number;
  order?: number;
  override?: {
    level?: number;
    lane?: number;
    order?: number;
  };
};

export type FlowEdgeSpec = {
  from: string;
  to: string;
  label?: string;
  tone?: FlowNodeTone;
  routeHint?: RouteHint;
};

export type FlowGraphSpec = {
  id: string;
  navLabel: string;
  title: string;
  status: FlowStatus;
  subtitle: string;
  chartPreset: 'standard' | 'wide' | 'xl';
  nodes: FlowNodeSpec[];
  edges: FlowEdgeSpec[];
  whatHappens: string[];
  whyItMatters: string;
  proofSignal: string[];
};

export const FLOW_PAGES: FlowGraphSpec[] = [
  {
    id: 'architecture',
    navLabel: 'Architecture',
    title: 'System Architecture + Trust Boundaries',
    status: 'Shipped',
    subtitle: 'Non-custodial split across agent runtime, network app, and public visibility.',
    chartPreset: 'standard',
    nodes: [
      { id: 'keys', label: 'Local Wallet Keys', tone: 'ok', lane: 2 },
      { id: 'runtime', label: 'Agent Runtime (Python)', tone: 'ok', lane: 1 },
      { id: 'api', label: 'Auth HTTPS API', lane: 1 },
      { id: 'web', label: 'Network Web + API', lane: 1 },
      { id: 'db', label: 'Postgres + Redis', lane: 2 },
      { id: 'views', label: 'Public + Mgmt Surfaces', tone: 'ok', lane: 1 },
    ],
    edges: [
      { from: 'keys', to: 'runtime', label: 'custody remains local', tone: 'ok', routeHint: 'split_up' },
      { from: 'runtime', to: 'api' },
      { from: 'api', to: 'web' },
      { from: 'web', to: 'db', routeHint: 'split_down' },
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
    chartPreset: 'xl',
    nodes: [
      { id: 'proposed', label: 'proposed', lane: 2, override: { level: 0 } },
      { id: 'gate', label: 'approval required?', tone: 'warn', lane: 2, override: { level: 1 } },
      { id: 'approved', label: 'approved', tone: 'ok', lane: 1, override: { level: 2 } },
      { id: 'pending', label: 'approval_pending', tone: 'warn', lane: 3, override: { level: 2 } },
      { id: 'exec', label: 'executing', lane: 1, override: { level: 3 } },
      { id: 'verify', label: 'verifying', lane: 2, override: { level: 4 } },
      { id: 'filled', label: 'filled', tone: 'ok', lane: 1, override: { level: 5 } },
      { id: 'failed', label: 'failed', tone: 'warn', lane: 3, override: { level: 5 } },
      { id: 'rejected', label: 'rejected / expired', tone: 'warn', lane: 4, override: { level: 5 } },
    ],
    edges: [
      { from: 'proposed', to: 'gate' },
      { from: 'gate', to: 'approved', label: 'no' },
      { from: 'gate', to: 'pending', label: 'yes', tone: 'warn' },
      { from: 'approved', to: 'exec' },
      { from: 'exec', to: 'verify' },
      { from: 'verify', to: 'filled', tone: 'ok', routeHint: 'split_up' },
      { from: 'verify', to: 'failed', tone: 'warn', routeHint: 'split_down' },
      { from: 'pending', to: 'rejected', tone: 'warn' },
      { from: 'failed', to: 'exec', label: 'retry policy', tone: 'warn', routeHint: 'outer_bottom' },
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
    subtitle: 'Policy fork + token preapproval fork, then web/telegram convergence.',
    chartPreset: 'xl',
    nodes: [
      { id: 'proposed', label: 'trade proposed', lane: 2, override: { level: 0 } },
      { id: 'mode', label: 'approval_mode', tone: 'warn', lane: 2, override: { level: 1 } },
      { id: 'auto', label: 'auto => approved', tone: 'ok', lane: 1, override: { level: 2 } },
      { id: 'token', label: 'token preapproved?', tone: 'warn', lane: 3, override: { level: 2 } },
      { id: 'queue', label: 'approval queue', tone: 'warn', lane: 3, override: { level: 3 } },
      { id: 'web', label: 'web decision', lane: 2, override: { level: 4 } },
      { id: 'tele', label: 'telegram decision', lane: 4, override: { level: 4 } },
      { id: 'approved', label: 'approved', tone: 'ok', lane: 1, override: { level: 5 } },
      { id: 'rejected', label: 'rejected', tone: 'warn', lane: 4, override: { level: 5 } },
    ],
    edges: [
      { from: 'proposed', to: 'mode' },
      { from: 'mode', to: 'auto', label: 'auto' },
      { from: 'mode', to: 'token', label: 'per_trade', tone: 'warn' },
      { from: 'token', to: 'approved', label: 'yes', tone: 'ok', routeHint: 'split_up' },
      { from: 'token', to: 'queue', label: 'no', tone: 'warn' },
      { from: 'queue', to: 'web' },
      { from: 'queue', to: 'tele', routeHint: 'split_down' },
      { from: 'web', to: 'approved', tone: 'ok', routeHint: 'split_up' },
      { from: 'web', to: 'rejected', tone: 'warn', routeHint: 'split_down' },
      { from: 'tele', to: 'approved', tone: 'ok', routeHint: 'outer_top' },
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
    chartPreset: 'wide',
    nodes: [
      { id: 'create', label: 'create receive request', lane: 2, override: { level: 0 } },
      { id: 'hosted', label: '/api/v1/x402/pay/{agentId}/{linkToken}', lane: 2, override: { level: 1 } },
      { id: 'challenge', label: '402 payment_required', tone: 'warn', lane: 1, override: { level: 2 } },
      { id: 'settled', label: '200 payment_settled', tone: 'ok', lane: 3, override: { level: 2 } },
      { id: 'mirror', label: 'mirror inbound/outbound records', tone: 'ok', lane: 2, override: { level: 3 } },
      { id: 'timeline', label: 'activity + approvals timeline', tone: 'ok', lane: 3, override: { level: 4 } },
    ],
    edges: [
      { from: 'create', to: 'hosted' },
      { from: 'hosted', to: 'challenge', label: 'missing payment header', tone: 'warn', routeHint: 'split_up' },
      { from: 'hosted', to: 'settled', label: 'valid payment', tone: 'ok', routeHint: 'split_down' },
      { from: 'challenge', to: 'settled', label: 'pay + retry', tone: 'ok', routeHint: 'outer_bottom' },
      { from: 'settled', to: 'mirror', tone: 'ok' },
      { from: 'mirror', to: 'timeline', tone: 'ok', routeHint: 'split_down' },
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
    chartPreset: 'wide',
    nodes: [
      { id: 'registry', label: 'chain config registry', lane: 2, override: { level: 0 } },
      { id: 'gate', label: 'capability gate', tone: 'warn', lane: 2, override: { level: 1 } },
      { id: 'wallet', label: 'wallet-first allowed', tone: 'ok', lane: 1, override: { level: 2 } },
      { id: 'trade', label: 'trade/liquidity enabled', tone: 'ok', lane: 2, override: { level: 2 } },
      { id: 'fail', label: 'unsupported => fail closed', tone: 'warn', lane: 3, override: { level: 2 } },
      { id: 'ui', label: 'truthful web/runtime status', tone: 'ok', lane: 2, override: { level: 3 } },
    ],
    edges: [
      { from: 'registry', to: 'gate' },
      { from: 'gate', to: 'wallet', label: 'wallet scope', routeHint: 'split_up' },
      { from: 'gate', to: 'trade', label: 'enabled', tone: 'ok' },
      { from: 'gate', to: 'fail', label: 'disabled', tone: 'warn', routeHint: 'split_down' },
      { from: 'wallet', to: 'ui', routeHint: 'split_up' },
      { from: 'trade', to: 'ui', tone: 'ok' },
      { from: 'fail', to: 'ui', tone: 'warn', routeHint: 'split_down' },
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
    chartPreset: 'wide',
    nodes: [
      { id: 'select', label: 'provider select', lane: 2, override: { level: 0 } },
      { id: 'proxy', label: 'uniswap_api attempt', tone: 'warn', lane: 2, override: { level: 1 } },
      { id: 'ok', label: 'proxy success', tone: 'ok', lane: 1, override: { level: 2 } },
      { id: 'fallback', label: 'legacy fallback available?', tone: 'warn', lane: 3, override: { level: 2 } },
      { id: 'exec', label: 'execute path', tone: 'ok', lane: 1, override: { level: 3 } },
      { id: 'noexec', label: 'no provider => fail closed', tone: 'warn', lane: 3, override: { level: 3 } },
      { id: 'prove', label: 'providerUsed + fallbackReason', lane: 4, override: { level: 4 } },
    ],
    edges: [
      { from: 'select', to: 'proxy' },
      { from: 'proxy', to: 'ok', label: 'success', tone: 'ok', routeHint: 'split_up' },
      { from: 'proxy', to: 'fallback', label: 'error', tone: 'warn', routeHint: 'split_down' },
      { from: 'ok', to: 'exec', tone: 'ok' },
      { from: 'fallback', to: 'exec', label: 'yes', routeHint: 'outer_top' },
      { from: 'fallback', to: 'noexec', label: 'no', tone: 'warn' },
      { from: 'exec', to: 'prove' },
      { from: 'noexec', to: 'prove', tone: 'warn', routeHint: 'split_down' },
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
    chartPreset: 'wide',
    nodes: [
      { id: 'agent', label: 'agent writes events/status', lane: 2, override: { level: 0 } },
      { id: 'persist', label: 'validate + persist', lane: 2, override: { level: 1 } },
      { id: 'metrics', label: 'metrics + ranking jobs', tone: 'ok', lane: 1, override: { level: 2 } },
      { id: 'history', label: 'activity/profile read models', tone: 'ok', lane: 3, override: { level: 2 } },
      { id: 'public', label: 'dashboard / explore / profile', tone: 'ok', lane: 1, override: { level: 3 } },
      { id: 'mgmt', label: '/agents/:id management (gated)', tone: 'warn', lane: 3, override: { level: 3 } },
    ],
    edges: [
      { from: 'agent', to: 'persist' },
      { from: 'persist', to: 'metrics', tone: 'ok', routeHint: 'split_up' },
      { from: 'persist', to: 'history', tone: 'ok', routeHint: 'split_down' },
      { from: 'metrics', to: 'public', tone: 'ok' },
      { from: 'history', to: 'public', tone: 'ok', routeHint: 'outer_top' },
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

export function getFlowPage(flowId: string): FlowGraphSpec | null {
  return FLOW_PAGES.find((flow) => flow.id === flowId) ?? null;
}
