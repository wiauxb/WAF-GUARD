'use client'

import { useEffect, useState } from 'react'
import { ChevronDown, ChevronUp, Plus, Search, SlidersHorizontal, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { cn } from '@/lib/utils'
import {
  FILTERABLE_COLUMNS, FILTER_TYPES, FP_COLOR, PREDICTION_LABEL, TP_COLOR,
  type ColFilter, type Prediction,
} from '@/lib/logs'
import type { LogFilterState } from './useLogFilters'

const ALL = '__all__'

interface Props {
  state: LogFilterState
  update: (patch: Partial<LogFilterState>) => void
  clear: () => void
  activeCount: number
  /** Unfiltered totals, so the segmented control shows the real size of each class. */
  totals: { all: number; fp: number; tp: number }
  categories: string[]
}

function Segment({
  active, onClick, color, label, count,
}: { active: boolean; onClick: () => void; color?: string; label: string; count: number }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'inline-flex items-center gap-2 rounded-md px-3 py-1.5 text-sm font-medium transition-colors',
        active ? 'bg-background shadow-sm text-foreground' : 'text-muted-foreground hover:text-foreground',
      )}
    >
      {color && <span className="h-2 w-2 rounded-full" style={{ background: color }} />}
      {label}
      <span className="rounded-full bg-muted px-1.5 text-xs tabular-nums text-muted-foreground">
        {count.toLocaleString()}
      </span>
    </button>
  )
}

function Chip({ label, onRemove }: { label: string; onRemove: () => void }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-full border bg-muted/50 py-0.5 pl-2.5 pr-1 text-xs">
      {label}
      <button type="button" onClick={onRemove} className="rounded-full p-0.5 hover:bg-muted" aria-label={`Remove filter ${label}`}>
        <X className="h-3 w-3" />
      </button>
    </span>
  )
}

export function LogFilters({ state, update, clear, activeCount, totals, categories }: Props) {
  const [search, setSearch] = useState(state.q)
  const [advanced, setAdvanced] = useState(state.cols.length > 0 || !!state.from || !!state.to)

  // Keep the box in sync when the URL changes elsewhere (chip removal, "clear all").
  useEffect(() => setSearch(state.q), [state.q])
  // Debounce: one request per pause, not one per keystroke.
  useEffect(() => {
    if (search === state.q) return
    const t = setTimeout(() => update({ q: search }), 350)
    return () => clearTimeout(t)
  }, [search, state.q, update])

  const setCol = (i: number, patch: Partial<ColFilter>) =>
    update({ cols: state.cols.map((c, idx) => (idx === i ? { ...c, ...patch } : c)) })
  const advancedCount = state.cols.length + (state.from ? 1 : 0) + (state.to ? 1 : 0)

  const colLabel = (name: string) => FILTERABLE_COLUMNS.find((c) => c.value === name)?.label ?? name
  const typeLabel = (t: string) => FILTER_TYPES.find((x) => x.value === t)?.label ?? t

  return (
    <div className="space-y-3 rounded-lg border bg-card p-3">
      <div className="flex flex-wrap items-center gap-3">
        <div className="inline-flex rounded-lg bg-muted p-1" role="tablist" aria-label="Prediction">
          <Segment active={!state.prediction} onClick={() => update({ prediction: null })} label="All" count={totals.all} />
          <Segment active={state.prediction === 'false_positive'} onClick={() => update({ prediction: 'false_positive' })}
            color={FP_COLOR} label={PREDICTION_LABEL.false_positive + 's'} count={totals.fp} />
          <Segment active={state.prediction === 'true_positive'} onClick={() => update({ prediction: 'true_positive' })}
            color={TP_COLOR} label={PREDICTION_LABEL.true_positive + 's'} count={totals.tp} />
        </div>

        <div className="relative min-w-[220px] flex-1">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search URL, IP, rule, message, payload…"
            className="h-9 pl-8"
          />
        </div>

        <Select
          value={state.category ?? ALL}
          onValueChange={(v) => update({ category: v === ALL ? null : v })}
        >
          <SelectTrigger className="h-9 w-[190px]">
            <SelectValue placeholder="All categories" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>All categories</SelectItem>
            {categories.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}
          </SelectContent>
        </Select>

        <Button variant="outline" size="sm" className="h-9 gap-1.5" onClick={() => setAdvanced((a) => !a)}>
          <SlidersHorizontal className="h-4 w-4" />
          Advanced
          {advancedCount > 0 && <span className="rounded-full bg-primary/10 px-1.5 text-xs text-primary">{advancedCount}</span>}
          {advanced ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
        </Button>
      </div>

      {advanced && (
        <div className="space-y-3 border-t pt-3">
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="space-y-1 text-xs font-medium text-muted-foreground">
              From
              <Input type="datetime-local" className="h-9" value={state.from} onChange={(e) => update({ from: e.target.value })} />
            </label>
            <label className="space-y-1 text-xs font-medium text-muted-foreground">
              To
              <Input type="datetime-local" className="h-9" value={state.to} onChange={(e) => update({ to: e.target.value })} />
            </label>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-muted-foreground">Field filters</span>
              <Button variant="ghost" size="sm" className="h-7 gap-1 text-xs"
                onClick={() => update({ cols: [...state.cols, { name: 'request_url', type: 'contains', value: '' }] })}>
                <Plus className="h-3.5 w-3.5" /> Add field filter
              </Button>
            </div>
            {state.cols.length === 0 && (
              <p className="text-xs italic text-muted-foreground">
                Narrow down on any extracted field, e.g. Status code equals 403 or Rule IDs contains 930130.
              </p>
            )}
            {state.cols.map((c, i) => (
              <div key={i} className="flex flex-wrap items-center gap-2">
                <Select value={c.name} onValueChange={(v) => setCol(i, { name: v })}>
                  <SelectTrigger className="h-8 w-[160px] text-xs"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {FILTERABLE_COLUMNS.map((f) => <SelectItem key={f.value} value={f.value}>{f.label}</SelectItem>)}
                  </SelectContent>
                </Select>
                <Select value={c.type} onValueChange={(v) => setCol(i, { type: v as ColFilter['type'] })}>
                  <SelectTrigger className="h-8 w-[130px] text-xs"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {FILTER_TYPES.map((t) => <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>)}
                  </SelectContent>
                </Select>
                <Input className="h-8 min-w-[140px] flex-1 text-xs" placeholder="value" value={c.value}
                  onChange={(e) => setCol(i, { value: e.target.value })} />
                <Button variant="ghost" size="sm" className="h-8 w-8 p-0 text-muted-foreground hover:text-destructive"
                  onClick={() => update({ cols: state.cols.filter((_, idx) => idx !== i) })} aria-label="Remove field filter">
                  <X className="h-4 w-4" />
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}

      {activeCount > 0 && (
        <div className="flex flex-wrap items-center gap-2 border-t pt-3">
          <span className="text-xs text-muted-foreground">Active filters</span>
          {state.prediction && <Chip label={PREDICTION_LABEL[state.prediction as Prediction]} onRemove={() => update({ prediction: null })} />}
          {state.category && <Chip label={`Category: ${state.category}`} onRemove={() => update({ category: null })} />}
          {state.q && <Chip label={`Search: ${state.q}`} onRemove={() => update({ q: '' })} />}
          {state.from && <Chip label={`From ${state.from.replace('T', ' ')}`} onRemove={() => update({ from: '' })} />}
          {state.to && <Chip label={`To ${state.to.replace('T', ' ')}`} onRemove={() => update({ to: '' })} />}
          {state.cols.map((c, i) => c.value !== '' && (
            <Chip key={i} label={`${colLabel(c.name)} ${typeLabel(c.type)} ${c.value}`}
              onRemove={() => update({ cols: state.cols.filter((_, idx) => idx !== i) })} />
          ))}
          <Button variant="ghost" size="sm" className="ml-auto h-7 text-xs text-muted-foreground" onClick={clear}>
            Clear all
          </Button>
        </div>
      )}
    </div>
  )
}
