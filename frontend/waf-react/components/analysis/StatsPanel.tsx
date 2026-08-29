'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { BarChart3, ChevronRight } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { LoadingSpinner } from '@/components/ui/loading-spinner'
import { getDirectiveStats } from '@/lib/analysis'
import { displayValue, toQuery, type Filter, type SortState } from './FilterBar'
import type { FacetCount } from '@/types'

/** A facet count is an aggregate; ordering is irrelevant, so this stays out of the key. */
const STATS_SORT: SortState = { by: 'node_id', dir: 'asc' }

const fmt = (n: number) => n.toLocaleString()

/**
 * A headline number. Not a one-bar chart — a handful of figures is a KPI row, and the
 * number IS the chart.
 */
function StatTile({ value, label, sub }: { value: number; label: string; sub?: string }) {
  return (
    <div>
      <p className="text-2xl font-semibold tabular-nums">{fmt(value)}</p>
      <p className="text-xs text-muted-foreground">{label}</p>
      {sub && <p className="text-xs text-muted-foreground/70">{sub}</p>}
    </div>
  )
}

/** A single ratio against its track. Not a two-slice pie. */
function Meter({ label, value, total }: { label: string; value: number; total: number }) {
  const pct = total ? (value / total) * 100 : 0
  return (
    <div className="space-y-1">
      <div className="flex items-baseline justify-between gap-2 text-xs">
        <span className="text-muted-foreground">{label}</span>
        <span className="tabular-nums">
          {fmt(value)} <span className="text-muted-foreground">({pct.toFixed(1)}%)</span>
        </span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-muted">
        <div className="h-full rounded-full bg-primary" style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

/**
 * One bar in a magnitude comparison.
 *
 * Single series, so one hue throughout: rank is carried by LENGTH, never by colour, and
 * there is no legend — the section title names the series. `share` is optional because
 * some sections are not part-to-whole: a directive carries several tags, so tag counts
 * sum to more than the total and a percentage there would be a lie.
 */
function BarRow({
  label,
  count,
  max,
  share,
  note,
}: {
  label: string
  count: number
  max: number
  share?: number
  note?: string
}) {
  const width = max ? Math.max((count / max) * 100, count > 0 ? 1.5 : 0) : 0
  return (
    <div className="group grid grid-cols-[minmax(0,9rem)_1fr_auto] items-center gap-3">
      <span className="truncate font-mono text-xs text-muted-foreground" title={label}>
        {label}
        {note && <span className="ml-1 uppercase tracking-wide opacity-60">{note}</span>}
      </span>
      <div className="h-3 rounded-sm bg-muted/60" title={`${label}: ${fmt(count)}`}>
        <div
          className="h-full rounded-sm bg-primary transition-[width] group-hover:brightness-110"
          style={{ width: `${width}%` }}
        />
      </div>
      <span className="w-24 shrink-0 text-right text-xs tabular-nums">
        {fmt(count)}
        {share !== undefined && (
          <span className="ml-1 text-muted-foreground">{share.toFixed(1)}%</span>
        )}
      </span>
    </div>
  )
}

function Section({
  title,
  caption,
  rows,
  total,
}: {
  title: string
  caption?: string
  rows: FacetCount[]
  /** Omit where the section is not part-to-whole — then no percentages are shown. */
  total?: number
}) {
  if (!rows.length) return null
  const max = Math.max(...rows.map((r) => r.count), 1)
  return (
    <div className="space-y-2">
      <div>
        <h4 className="text-sm font-medium">{title}</h4>
        {caption && <p className="text-xs text-muted-foreground">{caption}</p>}
      </div>
      <div className="space-y-1.5">
        {rows.map((r, i) => (
          <BarRow
            key={`${r.value}-${i}`}
            label={r.value === null ? '(no phase)' : displayValue(String(r.value), 'location')}
            count={r.count}
            max={max}
            share={total ? (r.count / total) * 100 : undefined}
            note={r.kind === 'LocationMatch' ? 'regex' : undefined}
          />
        ))}
      </div>
    </div>
  )
}

interface StatsPanelProps {
  filters: Filter[]
  /** Shown in the header while folded, so the panel is useful without opening. */
  fallbackTotal?: number
}

/**
 * A summary of whatever the filters currently match.
 *
 * Collapsed by default and fetched only when opened: the endpoint runs several
 * aggregations (~850 ms on 92k directives), which is fine on demand but not worth paying
 * on every page load.
 *
 * Every figure honours the WHOLE filter set, unlike the dropdown counts which drop their
 * own field's chips — the panel describes what is on screen, the dropdowns offer what
 * could be added next.
 */
export function StatsPanel({ filters, fallbackTotal }: StatsPanelProps) {
  const [open, setOpen] = useState(false)

  const stats = useQuery({
    queryKey: ['analysis', 'stats', filters],
    enabled: open,
    queryFn: () => getDirectiveStats(toQuery(filters, STATS_SORT)),
    staleTime: 30_000,
  })

  const d = stats.data

  return (
    <Card>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex w-full items-center gap-2 px-4 py-2.5 text-left text-sm hover:bg-muted/50"
      >
        <ChevronRight
          className={'h-4 w-4 shrink-0 transition-transform ' + (open ? 'rotate-90' : '')}
        />
        <BarChart3 className="h-4 w-4 shrink-0 text-muted-foreground" />
        <span className="font-medium">Statistics</span>
        <span className="text-muted-foreground">
          {d ? `${fmt(d.total)} directives` : fallbackTotal != null ? `${fmt(fallbackTotal)} directives` : ''}
        </span>
      </button>

      {open && (
        <CardContent className="space-y-6 border-t p-4">
          {stats.isLoading ? (
            <LoadingSpinner />
          ) : !d ? null : (
            <>
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                <StatTile value={d.total} label="directives" />
                <StatTile
                  value={d.secrules}
                  label="SecRules"
                  sub={d.total ? `${((d.secrules / d.total) * 100).toFixed(1)}% of the slice` : undefined}
                />
                <StatTile
                  value={d.with_rule_id}
                  label="declare a rule ID"
                  sub={d.total ? `${((d.with_rule_id / d.total) * 100).toFixed(1)}% of the slice` : undefined}
                />
                <StatTile
                  value={d.distinct_tags}
                  label="distinct tags"
                  sub={`${fmt(d.distinct_locations)} distinct locations`}
                />
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <Meter label="inside a Location block" value={d.in_location} total={d.total} />
                <Meter label="inside a VirtualHost" value={d.in_vhost} total={d.total} />
              </div>

              <div className="grid gap-6 lg:grid-cols-2">
                {/* Phase is ORDINAL — 1→5 is the request lifecycle — so this is rendered in
                    the order the API returns it, never re-sorted by count. That ordering is
                    also why it is a bar and not a pie. */}
                <Section
                  title="Phase"
                  caption="ModSecurity processing order, request → response → logging"
                  rows={d.phases}
                  total={d.total}
                />
                <Section
                  title="Directive types"
                  caption="Top 8; everything else folded into Other"
                  rows={d.types}
                  total={d.total}
                />
                <Section
                  title="Tags"
                  // No `total`: a directive carries several tags, so these sum to more than
                  // the directive count and a percentage would misrepresent them.
                  caption="Most used — occurrences, not shares (a directive carries several)"
                  rows={d.tags}
                />
                <Section
                  title="Locations"
                  caption="Top 8 by directive count"
                  rows={d.locations}
                  total={d.total}
                />
              </div>
            </>
          )}
        </CardContent>
      )}
    </Card>
  )
}
