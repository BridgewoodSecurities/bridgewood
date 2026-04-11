import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { formatCompactCurrency, formatCurrency, formatDateTime } from '../lib/format'
import { colorForAgent } from '../lib/palette'
import type { LeaderboardEntry, SnapshotPoint } from '../types'

interface Props {
  snapshots: SnapshotPoint[]
  agents: LeaderboardEntry[]
  hiddenIds: string[]
}

function buildRows(points: SnapshotPoint[]) {
  const grouped = new Map<string, Record<string, number | string>>()
  ;[...points]
    .sort((left, right) => new Date(left.snapshot_at).getTime() - new Date(right.snapshot_at).getTime())
    .forEach((point) => {
      const key = point.snapshot_at
      const row = grouped.get(key) ?? { timestamp: key }
      row[point.agent_id] = point.total_value
      grouped.set(key, row)
    })
  return Array.from(grouped.values())
}

export function PerformanceChart({ snapshots, agents, hiddenIds }: Props) {
  const rows = buildRows(snapshots)
  const visibleAgents = agents.filter((agent) => !hiddenIds.includes(agent.id))

  return (
    <div className="rounded-[30px] border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.08),rgba(255,255,255,0.02))] p-6 shadow-[0_30px_90px_rgba(0,0,0,0.35)]">
      <div className="mb-5 flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-emerald-300/80">
            Performance History
          </p>
          <h2 className="mt-2 text-2xl font-semibold text-white">Agent equity curves against the opening stake</h2>
        </div>
        <div className="rounded-full border border-white/10 bg-black/20 px-3 py-1 text-xs uppercase tracking-[0.22em] text-stone-300">
          Baseline {formatCurrency(10000)}
        </div>
      </div>

      <div className="h-[360px]">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={rows} margin={{ top: 12, right: 24, bottom: 0, left: 0 }}>
            <CartesianGrid stroke="rgba(255,255,255,0.08)" vertical={false} />
            <ReferenceLine
              y={10000}
              stroke="rgba(255,255,255,0.25)"
              strokeDasharray="6 6"
            />
            <XAxis
              dataKey="timestamp"
              axisLine={false}
              tickLine={false}
              tick={{ fill: '#c7c2b8', fontSize: 12 }}
              tickFormatter={(value) => formatDateTime(String(value))}
              minTickGap={24}
            />
            <YAxis
              axisLine={false}
              tickLine={false}
              tick={{ fill: '#c7c2b8', fontSize: 12 }}
              tickFormatter={(value) => formatCompactCurrency(Number(value))}
              width={80}
            />
            <Tooltip
              contentStyle={{
                background: 'rgba(17, 24, 39, 0.96)',
                borderRadius: 18,
                border: '1px solid rgba(255,255,255,0.12)',
                boxShadow: '0 24px 60px rgba(0,0,0,0.35)',
              }}
              formatter={(value, name) => [formatCurrency(Number(value ?? 0)), String(name)]}
              labelFormatter={(label) => formatDateTime(String(label))}
            />
            {visibleAgents.map((agent) => (
              <Line
                key={agent.id}
                type="monotone"
                dataKey={agent.id}
                name={agent.name}
                stroke={colorForAgent(agent.id, agent.is_benchmark)}
                strokeWidth={agent.is_benchmark ? 2.5 : 3}
                dot={false}
                activeDot={{ r: 5, strokeWidth: 0 }}
                connectNulls
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
