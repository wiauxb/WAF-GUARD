'use client'

import { Suspense, use, useMemo } from 'react'
import Link from 'next/link'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, FileText, Loader2 } from 'lucide-react'
import { api } from '@/lib/api'
import { formatDate } from '@/lib/utils'
import { LoadingSpinner } from '@/components/ui/loading-spinner'
import { EmptyState } from '@/components/ui/empty-state'
import { CategoryChart, PredictionDonut, TimelineChart, TopRulesChart } from '@/components/logs/charts'
import { LogFilters } from '@/components/logs/LogFilters'
import { LogsTable } from '@/components/logs/LogsTable'
import { SessionStats } from '@/components/logs/SessionStats'
import { useLogFilters } from '@/components/logs/useLogFilters'
import type { FilteredLogsResponse, LogAnalysisSessionResponse } from '@/types'

function SessionView({ sessionId }: { sessionId: string }) {
  const { state, update, clear, request, activeCount } = useLogFilters()

  // Session summary: title, unfiltered totals, category names for the filter.
  const { data: sessions } = useQuery({
    queryKey: ['log-sessions'],
    queryFn: async () =>
      (await api.post<LogAnalysisSessionResponse[]>('/logs/sessions', { limit: 100, offset: 0 })).data,
  })
  const session = sessions?.find((s) => s.session_id === sessionId)

  // The table and all four charts read this one filtered result set, so they never disagree.
  const { data, isLoading, isError, isFetching } = useQuery({
    queryKey: ['log-session', sessionId, request],
    queryFn: async () =>
      (await api.post<FilteredLogsResponse>(`/logs/sessions/${sessionId}/filter`, request)).data,
    placeholderData: (prev) => prev,
  })

  const results = useMemo(() => data?.results ?? [], [data])
  const totals = {
    all: session?.total_logs ?? data?.total_logs ?? 0,
    fp: session?.false_positives ?? 0,
    tp: session?.true_positives ?? 0,
  }
  const categories = (session?.categories ?? []).map((c) => c.category)

  if (isLoading) return <LoadingSpinner />
  if (isError || !data) {
    return <EmptyState title="Could not load this session" description="It may have been deleted, or the API is unavailable." />
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <Link href="/logs" className="mb-2 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
            <ArrowLeft className="h-4 w-4" /> All sessions
          </Link>
          <h1 className="flex items-center gap-2 text-2xl font-bold">
            <FileText className="h-6 w-6 text-muted-foreground" />
            {session?.filename ?? 'Log session'}
          </h1>
          {session && <p className="text-sm text-muted-foreground">Analysed {formatDate(session.created_at)}</p>}
        </div>
        {isFetching && <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" aria-label="Updating" />}
      </div>

      <SessionStats results={results} total={data.total_logs} />

      <LogFilters
        state={state} update={update} clear={clear} activeCount={activeCount}
        totals={totals} categories={categories}
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <PredictionDonut results={results} onSelect={(p) => update({ prediction: state.prediction === p ? null : p })} />
        <CategoryChart
          results={results} active={state.category}
          onSelect={(c) => update({ category: state.category === c ? null : c })}
        />
        <TimelineChart results={results} />
        <TopRulesChart
          results={results}
          onSelect={(id) => update({ cols: [...state.cols, { name: 'rule_ids', type: 'contains', value: id }] })}
        />
      </div>

      <LogsTable sessionId={sessionId} results={results} />
    </div>
  )
}

export default function LogSessionPage({ params }: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = use(params)
  return (
    <Suspense fallback={<LoadingSpinner />}>
      <SessionView sessionId={sessionId} />
    </Suspense>
  )
}
