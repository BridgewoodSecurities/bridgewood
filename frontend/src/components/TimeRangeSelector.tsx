import type { RangeKey } from '../types'

const RANGES: RangeKey[] = ['1D', '1W', '1M', 'ALL']

interface Props {
  value: RangeKey
  onChange: (next: RangeKey) => void
}

export function TimeRangeSelector({ value, onChange }: Props) {
  return (
    <div className="flex flex-wrap gap-2">
      {RANGES.map((range) => (
        <button
          key={range}
          type="button"
          onClick={() => onChange(range)}
          className={`rounded-full border px-3 py-1 text-xs font-semibold tracking-[0.22em] transition ${
            value === range
              ? 'border-emerald-500 bg-emerald-500/15 text-emerald-50'
              : 'border-white/12 bg-white/5 text-stone-300 hover:border-white/30 hover:text-white'
          }`}
        >
          {range}
        </button>
      ))}
    </div>
  )
}
