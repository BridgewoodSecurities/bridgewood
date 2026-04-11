import { useState } from 'react'

import { formatDateTime } from '../lib/format'
import type { ActivityItem } from '../types'

interface Props {
  items: ActivityItem[]
}

function initialsForName(name: string) {
  return name
    .split(' ')
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? '')
    .join('')
}

export function LiveActivityFeed({ items }: Props) {
  const [expandedIds, setExpandedIds] = useState<number[]>([])

  return (
    <section className="rounded-[30px] border border-white/10 bg-black/25 p-5 shadow-[0_20px_70px_rgba(0,0,0,0.35)]">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-amber-200/70">Live Activity</p>
          <h2 className="mt-2 text-xl font-semibold text-white">Cycle rationale and spend</h2>
        </div>
        <div className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs uppercase tracking-[0.2em] text-stone-300">
          Streaming
        </div>
      </div>

      <div className="max-h-[470px] space-y-3 overflow-y-auto pr-1">
        {items.map((item) => {
          const expanded = expandedIds.includes(item.id)
          const shouldTruncate = item.summary.length > 160
          const summary = shouldTruncate && !expanded ? `${item.summary.slice(0, 160)}…` : item.summary

          return (
            <article
              key={item.id}
              className="rounded-3xl border border-white/8 bg-white/[0.04] p-4 transition hover:border-white/18"
            >
              <div className="flex items-start gap-3">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-emerald-400/15 text-sm font-semibold text-emerald-100">
                  {initialsForName(item.agent_name)}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2 text-sm">
                    <span className="font-semibold text-white">{item.agent_name}</span>
                    {item.cost_tokens != null && (
                      <span className="rounded-full border border-amber-400/25 bg-amber-400/10 px-2 py-0.5 text-xs font-medium text-amber-100">
                        ◆ {item.cost_tokens.toFixed(1)}s
                      </span>
                    )}
                  </div>
                  <p className="mt-1 text-xs uppercase tracking-[0.18em] text-stone-400">
                    {formatDateTime(item.created_at)}
                  </p>
                  <p className="mt-3 text-sm leading-6 text-stone-200">{summary}</p>
                  {shouldTruncate && (
                    <button
                      type="button"
                      onClick={() =>
                        setExpandedIds((current) =>
                          expanded
                            ? current.filter((id) => id !== item.id)
                            : [...current, item.id],
                        )
                      }
                      className="mt-3 text-xs font-semibold uppercase tracking-[0.2em] text-emerald-300"
                    >
                      {expanded ? 'Show less' : 'See more'}
                    </button>
                  )}
                </div>
              </div>
            </article>
          )
        })}
      </div>
    </section>
  )
}
