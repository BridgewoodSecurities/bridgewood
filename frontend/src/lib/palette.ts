const AGENT_COLORS = [
  "#2563eb",
  "#ea580c",
  "#0f766e",
  "#7c3aed",
  "#ca8a04",
  "#dc2626",
  "#0891b2",
  "#4f46e5",
  "#059669",
  "#9333ea",
];

function hashString(value: string) {
  let hash = 0;
  for (let index = 0; index < value.length; index += 1) {
    hash = (hash << 5) - hash + value.charCodeAt(index);
    hash |= 0;
  }
  return Math.abs(hash);
}

export function colorForAgent(agentId: string, isBenchmark = false) {
  if (isBenchmark) {
    return "#475569";
  }

  return AGENT_COLORS[hashString(agentId) % AGENT_COLORS.length];
}
