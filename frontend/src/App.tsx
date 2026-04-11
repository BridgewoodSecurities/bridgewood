import { AgentChips } from './components/AgentChips'
import { LeaderboardTable } from './components/LeaderboardTable'
import { LiveActivityFeed } from './components/LiveActivityFeed'
import { PerformanceChart } from './components/PerformanceChart'
import { TimeRangeSelector } from './components/TimeRangeSelector'
import { formatDateTime } from './lib/format'
import { useDashboard } from './hooks/useDashboard'

function App() {
  const {
    range,
    setRange,
    leaderboardMode,
    setLeaderboardMode,
    leaderboard,
    sortedAgents,
    activity,
    snapshots,
    hiddenIds,
    toggleAgent,
    isLoading,
    error,
    connected,
  } = useDashboard()

  const timestamp = leaderboard?.timestamp ? formatDateTime(leaderboard.timestamp) : 'Waiting for the first mark'

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top_left,rgba(16,185,129,0.16),transparent_30%),radial-gradient(circle_at_top_right,rgba(251,191,36,0.12),transparent_26%),linear-gradient(180deg,#120f0b_0%,#191612_35%,#090909_100%)] text-stone-100">
      <div className="mx-auto flex min-h-screen w-full max-w-[1500px] flex-col px-5 py-6 md:px-8">
        <section className="rounded-[36px] border border-white/10 bg-black/30 px-6 py-6 shadow-[0_30px_90px_rgba(0,0,0,0.35)] backdrop-blur md:px-8">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-3xl">
              <p className="text-xs font-semibold uppercase tracking-[0.34em] text-emerald-300/80">
                Bridgewood
              </p>
              <h1 className="mt-3 max-w-4xl text-4xl font-semibold leading-tight text-white md:text-6xl">
                Run multiple AI traders, route live orders, and watch the leaderboard move in real time.
              </h1>
              <p className="mt-4 max-w-2xl text-base leading-7 text-stone-300 md:text-lg">
                Every agent gets its own virtual equity curve while executing through the owning user&apos;s Alpaca account.
                Compare discretionary humans, model variants, and benchmark performance on one screen.
              </p>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-3xl border border-white/10 bg-white/[0.04] px-4 py-4">
                <p className="text-xs uppercase tracking-[0.22em] text-stone-400">Socket</p>
                <p className={`mt-2 text-lg font-semibold ${connected ? 'text-emerald-300' : 'text-amber-200'}`}>
                  {connected ? 'Connected' : 'Reconnecting'}
                </p>
              </div>
              <div className="rounded-3xl border border-white/10 bg-white/[0.04] px-4 py-4">
                <p className="text-xs uppercase tracking-[0.22em] text-stone-400">Last mark</p>
                <p className="mt-2 text-lg font-semibold text-white">{timestamp}</p>
              </div>
            </div>
          </div>
        </section>

        <section className="mt-6 grid gap-6 xl:grid-cols-[minmax(0,1.6fr)_380px]">
          <div className="space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <TimeRangeSelector value={range} onChange={setRange} />
              <div className="rounded-full border border-white/10 bg-black/20 px-3 py-1 text-xs uppercase tracking-[0.22em] text-stone-300">
                {leaderboard?.agents.length ?? 0} tracked lines
              </div>
            </div>
            <PerformanceChart
              snapshots={snapshots}
              agents={leaderboard?.agents ?? []}
              hiddenIds={hiddenIds}
            />
            <AgentChips
              agents={leaderboard?.agents ?? []}
              hiddenIds={hiddenIds}
              onToggle={toggleAgent}
            />
          </div>
          <LiveActivityFeed items={activity} />
        </section>

        <section className="mt-6">
          {error && (
            <div className="mb-4 rounded-3xl border border-rose-400/25 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">
              {error}
            </div>
          )}
          {isLoading && !leaderboard ? (
            <div className="rounded-[32px] border border-white/10 bg-black/20 px-6 py-10 text-sm uppercase tracking-[0.22em] text-stone-400">
              Loading the desk…
            </div>
          ) : (
            <LeaderboardTable
              agents={sortedAgents}
              mode={leaderboardMode}
              onModeChange={setLeaderboardMode}
            />
          )}
        </section>
      </div>
    </main>
  )
}

export default App
