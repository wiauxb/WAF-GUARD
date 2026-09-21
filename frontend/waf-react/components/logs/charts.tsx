'use client'

import { useMemo, type ReactNode } from 'react'
import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { LogEntryResponse } from '@/types'
import {
  FP_COLOR, TP_COLOR, PREDICTION_LABEL, categoryColor, parseModsecTime, splitPipe,
  type Prediction,
} from '@/lib/logs'

const AXIS = '#94a3b8'
const GRID = 'rgba(148,163,184,0.25)'
const LEGEND_STYLE = { fontSize: 12, color: '#94a3b8' }
const TOOLTIP_STYLE = {
  background: 'hsl(var(--popover))',
  border: '1px solid hsl(var(--border))',
  borderRadius: 8,
  color: 'hsl(var(--popover-foreground))',
  fontSize: 12,
}

function ChartCard({ title, hint, children }: { title: string; hint?: string; children: ReactNode }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-semibold">{title}</CardTitle>
        {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  )
}

function Empty({ text }: { text: string }) {
  return <div className="flex h-56 items-center justify-center text-sm text-muted-foreground">{text}</div>
}

/* ---------- FP / TP donut ---------- */

export function PredictionDonut({
  results, onSelect,
}: { results: LogEntryResponse[]; onSelect: (p: Prediction) => void }) {
  const fp = results.filter((r) => r.prediction === 'false_positive').length
  const tp = results.length - fp
  const data = [
    { key: 'false_positive' as Prediction, name: PREDICTION_LABEL.false_positive, value: fp, color: FP_COLOR },
    { key: 'true_positive' as Prediction, name: PREDICTION_LABEL.true_positive, value: tp, color: TP_COLOR },
  ].filter((d) => d.value > 0)

  return (
    <ChartCard title="False vs true positives" hint="Click a slice to filter the table">
      {results.length === 0 ? <Empty text="No logs" /> : (
        <div className="relative h-56">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data} dataKey="value" nameKey="name" innerRadius={56} outerRadius={80}
                paddingAngle={2} strokeWidth={0} cursor="pointer"
                onClick={(d) => onSelect((d as unknown as { key: Prediction }).key)}
              >
                {data.map((d) => <Cell key={d.key} fill={d.color} />)}
              </Pie>
              <Tooltip
                contentStyle={TOOLTIP_STYLE}
                formatter={(v, n) => [`${v} (${Math.round((Number(v) / results.length) * 100)}%)`, n]}
              />
              <Legend iconType="circle" iconSize={8} wrapperStyle={LEGEND_STYLE} />
            </PieChart>
          </ResponsiveContainer>
          <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center pb-7">
            <span className="text-2xl font-bold">{results.length.toLocaleString()}</span>
            <span className="text-xs text-muted-foreground">logs</span>
          </div>
        </div>
      )}
    </ChartCard>
  )
}

/* ---------- Attack categories ---------- */

export function CategoryChart({
  results, onSelect, active,
}: { results: LogEntryResponse[]; onSelect: (c: string) => void; active: string | null }) {
  const data = useMemo(() => {
    const counts = new Map<string, number>()
    for (const r of results) {
      if (!r.attack_type) continue
      const label = r.attack_type.labels.join(', ') || 'unknown'
      counts.set(label, (counts.get(label) ?? 0) + 1)
    }
    return [...counts].map(([name, count]) => ({ name, count })).sort((a, b) => b.count - a.count).slice(0, 10)
  }, [results])

  return (
    <ChartCard title="Attack categories" hint="True positives only, click a bar to filter">
      {data.length === 0 ? <Empty text="No attack category in this selection" /> : (
        <div className="h-56">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} layout="vertical" margin={{ top: 0, right: 16, left: 0, bottom: 0 }}>
              <CartesianGrid horizontal={false} stroke={GRID} />
              <XAxis type="number" allowDecimals={false} tick={{ fill: AXIS, fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis type="category" dataKey="name" width={110} tick={{ fill: AXIS, fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={TOOLTIP_STYLE} cursor={{ fill: 'rgba(148,163,184,0.12)' }} formatter={(v) => [v, 'logs']} />
              <Bar dataKey="count" radius={[0, 4, 4, 0]} cursor="pointer" onClick={(d) => onSelect((d as unknown as { name: string }).name)}>
                {data.map((d, i) => (
                  <Cell key={d.name} fill={categoryColor(i)} opacity={active && active !== d.name ? 0.35 : 1} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </ChartCard>
  )
}

/* ---------- Timeline ---------- */

const MIN = 60_000
const HOUR = 60 * MIN
const DAY = 24 * HOUR

export function TimelineChart({ results }: { results: LogEntryResponse[] }) {
  const { data, bucketLabel } = useMemo(() => {
    const times = results
      .map((r) => ({ t: parseModsecTime(r.features.timestamp)?.getTime(), fp: r.prediction === 'false_positive' }))
      .filter((x): x is { t: number; fp: boolean } => x.t !== undefined)
    if (times.length === 0) return { data: [], bucketLabel: '' }

    const min = Math.min(...times.map((x) => x.t))
    const max = Math.max(...times.map((x) => x.t))
    const span = max - min
    const size = span <= 2 * HOUR ? 5 * MIN : span <= 2 * DAY ? HOUR : DAY
    const label = size === DAY ? 'per day' : size === HOUR ? 'per hour' : 'per 5 minutes'

    const buckets = new Map<number, { fp: number; tp: number }>()
    for (let b = Math.floor(min / size) * size; b <= max; b += size) buckets.set(b, { fp: 0, tp: 0 })
    for (const { t, fp } of times) {
      const b = buckets.get(Math.floor(t / size) * size)!
      if (fp) b.fp++
      else b.tp++
    }
    const fmt = (ms: number) =>
      new Date(ms).toLocaleString(undefined, size === DAY
        ? { day: '2-digit', month: 'short' }
        : { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
    return {
      data: [...buckets].map(([ms, v]) => ({ label: fmt(ms), 'False positive': v.fp, 'True positive': v.tp })),
      bucketLabel: label,
    }
  }, [results])

  return (
    <ChartCard title="Alerts over time" hint={bucketLabel ? `Volume ${bucketLabel}` : undefined}>
      {data.length === 0 ? <Empty text="No timestamps available" /> : (
        <div className="h-56">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} margin={{ top: 4, right: 8, left: -12, bottom: 0 }}>
              <CartesianGrid vertical={false} stroke={GRID} />
              <XAxis dataKey="label" tick={{ fill: AXIS, fontSize: 10 }} axisLine={false} tickLine={false} minTickGap={24} />
              <YAxis allowDecimals={false} tick={{ fill: AXIS, fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={TOOLTIP_STYLE} cursor={{ fill: 'rgba(148,163,184,0.12)' }} />
              <Legend iconType="circle" iconSize={8} wrapperStyle={LEGEND_STYLE} />
              <Bar dataKey="False positive" stackId="a" fill={FP_COLOR} />
              <Bar dataKey="True positive" stackId="a" fill={TP_COLOR} radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </ChartCard>
  )
}

/* ---------- Top triggered rules ---------- */

export function TopRulesChart({
  results, onSelect,
}: { results: LogEntryResponse[]; onSelect: (ruleId: string) => void }) {
  const data = useMemo(() => {
    const rules = new Map<string, { fp: number; tp: number }>()
    for (const r of results) {
      for (const id of splitPipe(r.features.rule_ids)) {
        const v = rules.get(id) ?? { fp: 0, tp: 0 }
        if (r.prediction === 'false_positive') v.fp++
        else v.tp++
        rules.set(id, v)
      }
    }
    return [...rules]
      .map(([id, v]) => ({ id, 'False positive': v.fp, 'True positive': v.tp, total: v.fp + v.tp }))
      .sort((a, b) => b.total - a.total)
      .slice(0, 8)
  }, [results])

  return (
    <ChartCard title="Most triggered rules" hint="Which rules raise false alarms vs real attacks; click to filter">
      {data.length === 0 ? <Empty text="No rule triggered" /> : (
        <div className="h-56">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} layout="vertical" margin={{ top: 0, right: 16, left: 0, bottom: 0 }}>
              <CartesianGrid horizontal={false} stroke={GRID} />
              <XAxis type="number" allowDecimals={false} tick={{ fill: AXIS, fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis type="category" dataKey="id" width={64} tick={{ fill: AXIS, fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={TOOLTIP_STYLE} cursor={{ fill: 'rgba(148,163,184,0.12)' }} />
              <Legend iconType="circle" iconSize={8} wrapperStyle={LEGEND_STYLE} />
              <Bar dataKey="False positive" stackId="a" fill={FP_COLOR} cursor="pointer" onClick={(d) => onSelect((d as unknown as { id: string }).id)} />
              <Bar dataKey="True positive" stackId="a" fill={TP_COLOR} radius={[0, 4, 4, 0]} cursor="pointer" onClick={(d) => onSelect((d as unknown as { id: string }).id)} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </ChartCard>
  )
}
