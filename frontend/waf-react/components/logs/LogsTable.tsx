'use client'

import { useMemo, useState } from 'react'
import { useRouter } from 'next/navigation'
import { ArrowDown, ArrowUp, ArrowUpDown, ChevronRight, SearchX } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { EmptyState } from '@/components/ui/empty-state'
import { Pagination } from '@/components/ui/pagination'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { cn } from '@/lib/utils'
import type { LogEntryResponse } from '@/types'
import {
  PREDICTION_LABEL, PREDICTION_STYLE, firstMessage, parseModsecTime, severityStyle, splitPipe, statusStyle,
} from '@/lib/logs'

type SortKey = 'time' | 'prediction' | 'confidence' | 'url' | 'rules' | 'severity'
const SEVERITY_RANK: Record<string, number> = { CRITICAL: 4, ERROR: 3, WARNING: 2, NOTICE: 1 }

function sortValue(r: LogEntryResponse, key: SortKey): number | string {
  switch (key) {
    case 'time': return parseModsecTime(r.features.timestamp)?.getTime() ?? 0
    case 'prediction': return r.prediction
    case 'confidence': return r.confidence
    case 'url': return r.features.request_url
    case 'rules': return r.features.rule_count
    case 'severity': return SEVERITY_RANK[r.features.max_severity.toUpperCase()] ?? 0
  }
}

function SortHead({
  label, k, sort, onSort, className,
}: { label: string; k: SortKey; sort: { key: SortKey; dir: 'asc' | 'desc' }; onSort: (k: SortKey) => void; className?: string }) {
  const active = sort.key === k
  const Icon = !active ? ArrowUpDown : sort.dir === 'asc' ? ArrowUp : ArrowDown
  return (
    <TableHead className={className}>
      <button type="button" onClick={() => onSort(k)}
        className={cn('inline-flex items-center gap-1 hover:text-foreground', active && 'text-foreground')}>
        {label}
        <Icon className={cn('h-3 w-3', !active && 'opacity-40')} />
      </button>
    </TableHead>
  )
}

export function LogsTable({ sessionId, results }: { sessionId: string; results: LogEntryResponse[] }) {
  const router = useRouter()
  const [sort, setSort] = useState<{ key: SortKey; dir: 'asc' | 'desc' }>({ key: 'time', dir: 'desc' })
  const [page, setPage] = useState({ limit: 25, offset: 0 })

  const sorted = useMemo(() => {
    const f = sort.dir === 'asc' ? 1 : -1
    return [...results].sort((a, b) => {
      const x = sortValue(a, sort.key), y = sortValue(b, sort.key)
      return x < y ? -f : x > y ? f : 0
    })
  }, [results, sort])

  // A filter change can leave the current offset past the end of the new result set.
  const offset = page.offset >= sorted.length ? 0 : page.offset
  const rows = sorted.slice(offset, offset + page.limit)

  const onSort = (key: SortKey) => {
    setSort((s) => (s.key === key ? { key, dir: s.dir === 'asc' ? 'desc' : 'asc' } : { key, dir: 'desc' }))
    setPage((p) => ({ ...p, offset: 0 }))
  }

  if (results.length === 0) {
    return (
      <EmptyState
        icon={SearchX}
        title="No logs match these filters"
        description="Remove a filter above, or clear them all to see the whole session."
      />
    )
  }

  return (
    <div className="space-y-3">
      <div className="overflow-x-auto rounded-lg border">
        <Table>
          <TableHeader>
            <TableRow>
              <SortHead label="Time" k="time" sort={sort} onSort={onSort} className="w-[150px]" />
              <SortHead label="Prediction" k="prediction" sort={sort} onSort={onSort} className="w-[170px]" />
              <SortHead label="Request" k="url" sort={sort} onSort={onSort} />
              <SortHead label="Flagged by" k="rules" sort={sort} onSort={onSort} className="min-w-[280px]" />
              <TableHead className="normal-case">Category</TableHead>
              <SortHead label="Severity" k="severity" sort={sort} onSort={onSort} />
              <TableHead className="w-8" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((r, idx) => {
              const f = r.features
              const rules = splitPipe(f.rule_ids)
              const time = parseModsecTime(f.timestamp)
              const style = PREDICTION_STYLE[r.prediction]
              return (
                <TableRow
                  key={`${f.transaction_id}-${offset + idx}`}
                  className="group cursor-pointer"
                  onClick={() => router.push(`/logs/${sessionId}/log/${encodeURIComponent(f.transaction_id)}`)}
                >
                  <TableCell className="whitespace-nowrap align-top text-xs text-muted-foreground">
                    {time ? (
                      <>
                        <div className="text-foreground">{time.toLocaleDateString(undefined, { day: '2-digit', month: 'short' })}</div>
                        <div>{time.toLocaleTimeString()}</div>
                      </>
                    ) : '—'}
                  </TableCell>

                  <TableCell className="align-top">
                    <span className={cn('inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium', style.badge)}>
                      {PREDICTION_LABEL[r.prediction]}
                    </span>
                    <div className="mt-1.5 flex items-center gap-1.5" title={`Model confidence ${(r.confidence * 100).toFixed(1)}%`}>
                      <div className="h-1 w-16 overflow-hidden rounded-full bg-muted">
                        <div className={cn('h-full rounded-full', style.bar)} style={{ width: `${Math.round(r.confidence * 100)}%` }} />
                      </div>
                      <span className="text-[11px] tabular-nums text-muted-foreground">{Math.round(r.confidence * 100)}%</span>
                    </div>
                  </TableCell>

                  <TableCell className="max-w-[340px] align-top">
                    <div className="flex items-center gap-2">
                      <Badge variant="muted" className="font-mono">{f.request_method || '—'}</Badge>
                      <span className={cn('text-xs font-semibold tabular-nums', statusStyle(f.response_status_code))}>
                        {f.response_status_code}
                      </span>
                    </div>
                    <div className="mt-1 truncate font-mono text-xs" title={f.request_url}>{f.request_url}</div>
                    <div className="truncate text-[11px] text-muted-foreground">{f.remote_address}{f.host && ` → ${f.host}`}</div>
                  </TableCell>

                  <TableCell className="align-top">
                    {rules.length === 0 ? (
                      <span className="text-xs text-muted-foreground">No rule matched</span>
                    ) : (
                      <>
                        <div className="flex flex-wrap items-center gap-1">
                          {rules.slice(0, 3).map((id) => (
                            <span key={id} className="rounded bg-muted px-1.5 py-0.5 font-mono text-[11px]">{id}</span>
                          ))}
                          {rules.length > 3 && <span className="text-[11px] text-muted-foreground">+{rules.length - 3}</span>}
                        </div>
                        <div className="mt-1 line-clamp-2 text-xs text-muted-foreground" title={f.messages}>
                          {firstMessage(r)}
                        </div>
                      </>
                    )}
                  </TableCell>

                  <TableCell className="align-top">
                    {r.attack_type ? (
                      <Badge variant="secondary">{r.attack_type.labels.join(', ') || 'unknown'}</Badge>
                    ) : (
                      <span className="text-xs text-muted-foreground">—</span>
                    )}
                  </TableCell>

                  <TableCell className="align-top">
                    {f.max_severity && f.max_severity !== 'NONE' ? (
                      <span className={cn('inline-flex rounded-md border px-2 py-0.5 text-xs font-medium', severityStyle(f.max_severity))}>
                        {f.max_severity}
                      </span>
                    ) : <span className="text-xs text-muted-foreground">—</span>}
                  </TableCell>

                  <TableCell className="align-middle">
                    <ChevronRight className="h-4 w-4 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
                  </TableCell>
                </TableRow>
              )
            })}
          </TableBody>
        </Table>
      </div>

      <Pagination
        total={sorted.length}
        limit={page.limit}
        offset={offset}
        onChange={setPage}
      />
    </div>
  )
}
