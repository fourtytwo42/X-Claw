export type AgentAvatarPalette = {
  backgroundColor: string;
  borderColor: string;
  textColor: string;
};

function hashString(input: string): number {
  let hash = 2166136261;
  for (let index = 0; index < input.length; index += 1) {
    hash ^= input.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

export function getAgentAvatarPalette(agentId: string, hueOffset = 0): AgentAvatarPalette {
  const hash = hashString(agentId || 'xclaw-agent');
  const hue = ((hash % 360) + (hueOffset % 360) + 360) % 360;
  const lightness = 42 + ((hash >>> 8) % 8);
  const borderLightness = Math.max(24, lightness - 14);
  return {
    backgroundColor: `hsl(${hue} 72% ${lightness}%)`,
    borderColor: `hsl(${hue} 70% ${borderLightness}%)`,
    textColor: '#f8fbff'
  };
}

export function getAgentInitial(agentName: string | null | undefined, fallbackId: string): string {
  const source = (agentName ?? '').trim() || fallbackId;
  return source.slice(0, 1).toUpperCase();
}
