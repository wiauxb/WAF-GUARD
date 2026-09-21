import { Activity, Percent, ShieldAlert, ShieldCheck } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { LogEntryResponse } from '@/types'

interface Props {
  results: LogEntryResponse[]
  total: number
}

export function SessionStats({ results, total }: Props) {
  const fp = results.filter((r) => r.prediction === 'false_positive').length
  const tp = results.length - fp
  const filtered = results.length !== total
  const rate = results.length ? Math.round((tp / results.length) * 100) : 0
  const avgConf = results.length
    ? Math.round((results.reduce((s, r) => s + r.confidence, 0) / results.length) * 100)
    : 0

  const stats = [
    { label: filtered ? 'Matching logs' : 'Total logs', value: results.length.toLocaleString(),
      sub: filtered ? `of ${total.toLocaleString()}` : undefined, icon: Activity, tone: 'text-foreground', box: '' },
    { label: 'False positives', value: fp.toLocaleString(), sub: 'legitimate traffic',
      icon: ShieldCheck, tone: 'text-emerald-700 dark:text-emerald-400', box: 'border-emerald-500/30 bg-emerald-500/5' },
    { label: 'True positives', value: tp.toLocaleString(), sub: 'real attacks',
      icon: ShieldAlert, tone: 'text-red-700 dark:text-red-400', box: 'border-red-500/30 bg-red-500/5' },
    { label: 'Attack rate', value: `${rate}%`, sub: `avg. confidence ${avgConf}%`,
      icon: Percent, tone: rate > 50 ? 'text-orange-700 dark:text-orange-400' : 'text-sky-700 dark:text-sky-400', box: '' },
  ]

  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      {stats.map(({ label, value, sub, icon: Icon, tone, box }) => (
        <div key={label} className={cn('rounded-lg border bg-card p-4', box)}>
          <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
            <Icon className={cn('h-4 w-4', tone)} />
            {label}
          </div>
          <p className={cn('mt-1 text-2xl font-bold tabular-nums', tone)}>{value}</p>
          {sub && <p className="text-xs text-muted-foreground">{sub}</p>}
        </div>
      ))}
    </div>
  )
}
