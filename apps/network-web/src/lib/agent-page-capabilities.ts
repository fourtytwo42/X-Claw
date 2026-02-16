export const AGENT_PAGE_CAPABILITIES = {
  liveRangeChartApi: false,
  approvalRiskChips: false,
  approvalGasAndRouteDetails: false,
  allowanceInventoryBySpender: false,
  watchApi: false,
  shareApi: false,
  copyAgentLinkApi: false
} as const;

export type AgentPageCapabilityKey = keyof typeof AGENT_PAGE_CAPABILITIES;
