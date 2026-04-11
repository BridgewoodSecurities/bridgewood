import { colorForAgent } from '../lib/palette'
import type { LeaderboardEntry } from '../types'

interface Props {
  agents: LeaderboardEntry[]
  hiddenIds: string[]
  onToggle: (agentId: string) => void
}

export function AgentChips({ agents, hiddenIds, onToggle }: Props) {
  return (
    <div className="flex flex-wrap gap-2">
      {agents.map((agent) => {
        const active = !hiddenIds.includes(agent.id)
        const color = colorForAgent(agent.id, agent.is_benchmark)
        return (
          <button
            key={agent.id}
            type="button"
            onClick={() => onToggle(agent.id)}
            className={`inline-flex items-center gap-2 rounded-full border px-3 py-2 text-sm transition ${
              active
                ? 'border-white/20 bg-white/10 text-white'
                : 'border-white/10 bg-black/20 text-stone-500'
            }`}
          >
            <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: color }} />
            <span>{agent.name}</span>
          </button>
        )
      })}
    </div>
  )
}
