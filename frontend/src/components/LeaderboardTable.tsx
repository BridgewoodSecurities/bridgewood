import { formatCount, formatCurrency, formatPct, formatSignedCurrency } from '../lib/format'
import type { LeaderboardEntry, LeaderboardMode } from '../types'

interface Props {
  agents: LeaderboardEntry[]
  mode: LeaderboardMode
  onModeChange: (next: LeaderboardMode) => void
}

function initialsForName(name: string) {
  return name
    .split(' ')
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? '')
    .join('')
}

export function LeaderboardTable({ agents, mode, onModeChange }: Props) {
  return (
    <section className="rounded-[32px] border border-white/10 bg-black/30 p-6 shadow-[0_30px_90px_rgba(0,0,0,0.35)]">
      <div className="mb-5 flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-amber-200/70">Leaderboard</p>
          <h2 className="mt-2 text-2xl font-semibold text-white">Current standings across every agent</h2>
        </div>
        <div className="inline-flex rounded-full border border-white/10 bg-white/5 p-1">
          <button
            type="button"
            onClick={() => onModeChange('all-time')}
            className={`rounded-full px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] transition ${
              mode === 'all-time' ? 'bg-white text-stone-950' : 'text-stone-300'
            }`}
          >
            All-time
          </button>
          <button
            type="button"
            onClick={() => onModeChange('daily')}
            className={`rounded-full px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] transition ${
              mode === 'daily' ? 'bg-white text-stone-950' : 'text-stone-300'
            }`}
          >
            Daily
          </button>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full border-separate border-spacing-y-3">
          <thead>
            <tr className="text-left text-xs uppercase tracking-[0.22em] text-stone-400">
              <th className="px-4">Rank</th>
              <th className="px-4">Agent</th>
              <th className="px-4">Cash</th>
              <th className="px-4">Value</th>
              <th className="px-4">PnL</th>
              <th className="px-4">Return</th>
              <th className="px-4">Sharpe</th>
              <th className="px-4">Max Win</th>
              <th className="px-4">Max Loss</th>
              <th className="px-4">Trades</th>
            </tr>
          </thead>
          <tbody>
            {agents.map((agent, index) => (
              <tr key={agent.id} className="rounded-3xl bg-white/[0.045] text-sm text-stone-200">
                <td className="rounded-l-3xl px-4 py-4 font-semibold text-white">{index + 1}</td>
                <td className="px-4 py-4">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-white/8 text-xs font-semibold text-white">
                      {initialsForName(agent.name)}
                    </div>
                    <div>
                      <div className="font-semibold text-white">{agent.name}</div>
                      {mode === 'daily' && (
                        <div className="text-xs uppercase tracking-[0.18em] text-stone-400">
                          Day {formatPct(agent.daily_change_pct)}
                        </div>
                      )}
                    </div>
                  </div>
                </td>
                <td className="px-4 py-4">{formatCurrency(agent.cash)}</td>
                <td className="px-4 py-4 font-semibold text-white">{formatCurrency(agent.total_value)}</td>
                <td className={`px-4 py-4 ${agent.pnl >= 0 ? 'text-emerald-300' : 'text-rose-300'}`}>
                  {formatSignedCurrency(agent.pnl)}
                </td>
                <td className={`px-4 py-4 ${agent.return_pct >= 0 ? 'text-emerald-300' : 'text-rose-300'}`}>
                  {formatPct(agent.return_pct)}
                </td>
                <td className="px-4 py-4">{agent.sharpe.toFixed(2)}</td>
                <td className="px-4 py-4 text-emerald-300">{formatSignedCurrency(agent.max_win)}</td>
                <td className="px-4 py-4 text-rose-300">{formatSignedCurrency(agent.max_loss)}</td>
                <td className="rounded-r-3xl px-4 py-4">{formatCount(agent.trade_count)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
