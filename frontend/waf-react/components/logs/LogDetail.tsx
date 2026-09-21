'use client'

import { AlertTriangle, ShieldAlert, ShieldCheck } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { cn } from '@/lib/utils'
import type { LogEntryResponse } from '@/types'
import {
  PREDICTION_HELP, PREDICTION_LABEL, PREDICTION_STYLE, attackProbabilities, categoryColor,
  parseMessage, severityStyle, splitPipe, statusStyle,
} from '@/lib/logs'

function ProbBar({ label, value, className }: { label: string; value: number; className: string }) {
  return (
    <div className="flex items-center gap-3 text-xs">
      <span className="w-28 text-muted-foreground">{label}</span>
      <div className="h-2 flex-1 overflow-hidden rounded-full bg-muted">
        <div className={cn('h-full rounded-full', className)} style={{ width: `${value * 100}%` }} />
      </div>
      <span className="w-12 text-right tabular-nums">{(value * 100).toFixed(1)}%</span>
    </div>
  )
}

export function VerdictBanner({ entry }: { entry: LogEntryResponse }) {
  const style = PREDICTION_STYLE[entry.prediction]
  const Icon = entry.prediction === 'false_positive' ? ShieldCheck : ShieldAlert
  return (
    <div className={cn('flex flex-wrap items-start gap-4 rounded-lg border p-5', style.panel)}>
      <div className={cn('rounded-full p-3', style.badge)}><Icon className="h-6 w-6" /></div>
      <div className="min-w-[240px] flex-1">
        <p className={cn('text-xl font-bold', style.text)}>{PREDICTION_LABEL[entry.prediction]}</p>
        <p className="text-sm text-muted-foreground">
          {PREDICTION_HELP[entry.prediction]}. Model confidence{' '}
          <span className={cn('font-semibold', style.text)}>{(entry.confidence * 100).toFixed(1)}%</span>.
        </p>
        {entry.attack_type && (
          <p className="mt-2 text-sm">
            Attack type:{' '}
            {entry.attack_type.labels.map((l) => <Badge key={l} variant="secondary" className="mr-1">{l}</Badge>)}
          </p>
        )}
      </div>
      <div className="w-full max-w-sm space-y-2">
        <ProbBar label="False positive" value={entry.fp_probability} className="bg-emerald-500" />
        <ProbBar label="True positive" value={entry.tp_probability} className="bg-red-500" />
      </div>
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[130px_1fr] gap-3 py-1.5 text-sm">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="min-w-0 break-words">{children || <span className="text-muted-foreground">—</span>}</dd>
    </div>
  )
}

function RequestCard({ entry }: { entry: LogEntryResponse }) {
  const f = entry.features
  return (
    <Card>
      <CardHeader className="pb-2"><CardTitle className="text-sm">Request and response</CardTitle></CardHeader>
      <CardContent>
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <Badge variant="muted" className="font-mono">{f.request_method}</Badge>
          <span className="break-all font-mono text-sm">{f.request_url}</span>
        </div>
        <dl className="divide-y">
          <Field label="Status">
            <span className={cn('font-semibold', statusStyle(f.response_status_code))}>{f.response_status_code}</span>{' '}
            {f.response_status}
          </Field>
          <Field label="Action">{f.action}</Field>
          <Field label="Host">{f.host}</Field>
          <Field label="Client">
            <span className="font-mono">{entry.parsed.A.Remote_address || f.remote_address}
              {entry.parsed.A.Remote_port ? `:${entry.parsed.A.Remote_port}` : ''}</span>
          </Field>
          <Field label="Protocol">{f.request_protocol}</Field>
          <Field label="User-Agent"><span className="font-mono text-xs">{f.user_agent}</span></Field>
          <Field label="Time">{f.timestamp}</Field>
          {f.cookie && <Field label="Cookie"><span className="font-mono text-xs">{f.cookie}</span></Field>}
          {f.payload && (
            <Field label="Payload"><pre className="max-h-48 overflow-auto rounded bg-muted p-2 font-mono text-xs">{f.payload}</pre></Field>
          )}
        </dl>
      </CardContent>
    </Card>
  )
}

function AlertsCard({ entry }: { entry: LogEntryResponse }) {
  const f = entry.features
  const messages = f.h_raw ? f.h_raw.split(' || ').map(parseMessage) : []
  const isFP = entry.prediction === 'false_positive'
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-sm">
          <AlertTriangle className="h-4 w-4 text-amber-500" />
          {isFP ? 'Why the WAF raised an alert' : 'Alerts raised by the WAF'}
        </CardTitle>
        {isFP && (
          <p className="text-xs text-muted-foreground">
            These rules matched, but the model judges the request legitimate: a likely candidate for a rule exclusion.
          </p>
        )}
      </CardHeader>
      <CardContent className="space-y-3">
        {messages.length === 0 && <p className="text-sm text-muted-foreground">No rule message recorded.</p>}
        {messages.map((m, i) => (
          <div key={i} className="rounded-md border p-3">
            <div className="flex flex-wrap items-center gap-2">
              {m.id && <span className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs">{m.id}</span>}
              {m.severity && (
                <span className={cn('rounded-md border px-2 py-0.5 text-xs font-medium', severityStyle(m.severity))}>{m.severity}</span>
              )}
              {m.at && <span className="text-xs text-muted-foreground">at {m.at}</span>}
            </div>
            <p className="mt-1.5 text-sm font-medium">{m.msg ?? m.raw}</p>
            {m.data && <p className="mt-1 break-all font-mono text-xs text-muted-foreground">{m.data}</p>}
            {m.tags.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1">
                {m.tags.map((t, j) => <Badge key={`${t}-${j}`} variant="tag">{t}</Badge>)}
              </div>
            )}
          </div>
        ))}
      </CardContent>
    </Card>
  )
}

function AttackTypeCard({ entry }: { entry: LogEntryResponse }) {
  const probs = attackProbabilities(entry)
  if (!entry.attack_type || probs.length === 0) return null
  return (
    <Card>
      <CardHeader className="pb-2"><CardTitle className="text-sm">Attack type probabilities</CardTitle></CardHeader>
      <CardContent className="space-y-2">
        {probs.slice(0, 8).map(({ label, p }, i) => (
          <div key={label} className="flex items-center gap-3 text-xs">
            <span className={cn('w-36 truncate', entry.attack_type?.labels.includes(label) && 'font-semibold')}>{label}</span>
            <div className="h-2 flex-1 overflow-hidden rounded-full bg-muted">
              <div className="h-full rounded-full" style={{ width: `${p * 100}%`, background: categoryColor(i) }} />
            </div>
            <span className="w-12 text-right tabular-nums">{(p * 100).toFixed(1)}%</span>
          </div>
        ))}
      </CardContent>
    </Card>
  )
}

function RulesTab({ entry }: { entry: LogEntryResponse }) {
  const f = entry.features
  const stats = [
    { label: 'Rules triggered', value: f.rule_count },
    { label: 'Max severity', value: f.max_severity || '—' },
    { label: 'Tags', value: splitPipe(f.tags).length },
  ]
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-3">
        {stats.map((s) => (
          <div key={s.label} className="rounded-lg border bg-card p-3 text-center">
            <p className="text-xl font-bold">{s.value}</p>
            <p className="text-xs text-muted-foreground">{s.label}</p>
          </div>
        ))}
      </div>
      <Card>
        <CardContent className="space-y-4 pt-6">
          <div>
            <p className="mb-1.5 text-xs font-medium text-muted-foreground">Rule IDs</p>
            <div className="flex flex-wrap gap-1.5">
              {splitPipe(f.rule_ids).map((id) => <span key={id} className="rounded bg-muted px-2 py-0.5 font-mono text-xs">{id}</span>)}
              {!f.rule_ids && <span className="text-sm text-muted-foreground">None</span>}
            </div>
          </div>
          {f.tags && (
            <div>
              <p className="mb-1.5 text-xs font-medium text-muted-foreground">Tags</p>
              <div className="flex flex-wrap gap-1.5">{splitPipe(f.tags).map((t, j) => <Badge key={`${t}-${j}`} variant="tag">{t}</Badge>)}</div>
            </div>
          )}
          {(f.has_bot_rule || f.has_access_denied) && (
            <div className="flex gap-2">
              {f.has_bot_rule && <Badge variant="phase">Bot rule</Badge>}
              {f.has_access_denied && <Badge variant="removal">Access denied</Badge>}
            </div>
          )}
          {f.matched_data && (
            <div>
              <p className="mb-1.5 text-xs font-medium text-muted-foreground">
                Matched data{f.matched_locations && <> in <span className="font-mono">{f.matched_locations}</span></>}
              </p>
              <pre className="max-h-48 overflow-auto rounded bg-muted p-3 font-mono text-xs">{f.matched_data}</pre>
            </div>
          )}
        </CardContent>
      </Card>
      <AlertsCard entry={entry} />
    </div>
  )
}

export function LogDetail({ entry }: { entry: LogEntryResponse }) {
  return (
    <div className="space-y-6">
      <VerdictBanner entry={entry} />
      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="rules">WAF rules</TabsTrigger>
          <TabsTrigger value="raw">Raw data</TabsTrigger>
        </TabsList>
        <TabsContent value="overview" className="mt-4 grid gap-4 lg:grid-cols-2">
          <div className="space-y-4">
            <AlertsCard entry={entry} />
            <AttackTypeCard entry={entry} />
          </div>
          <RequestCard entry={entry} />
        </TabsContent>
        <TabsContent value="rules" className="mt-4"><RulesTab entry={entry} /></TabsContent>
        <TabsContent value="raw" className="mt-4">
          <pre className="max-h-[600px] overflow-auto rounded-lg border bg-muted p-4 font-mono text-xs">
            {JSON.stringify(entry.parsed, null, 2)}
          </pre>
        </TabsContent>
      </Tabs>
    </div>
  )
}
