'use client'

import { use } from 'react'
import Link from 'next/link'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft } from 'lucide-react'
import { api } from '@/lib/api'
import { EmptyState } from '@/components/ui/empty-state'
import { LoadingSpinner } from '@/components/ui/loading-spinner'
import { LogDetail } from '@/components/logs/LogDetail'
import type { LogDetailResponse } from '@/types'

export default function LogDetailPage({
  params,
}: { params: Promise<{ sessionId: string; transactionId: string }> }) {
  const { sessionId, transactionId } = use(params)
  const tid = decodeURIComponent(transactionId)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['log-detail', sessionId, tid],
    queryFn: async () =>
      (await api.get<LogDetailResponse>(`/logs/sessions/${sessionId}/log/${encodeURIComponent(tid)}`)).data,
  })

  return (
    <div className="space-y-5">
      <div>
        <Link
          href={`/logs/${sessionId}`}
          className="mb-2 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
          onClick={(e) => { if (window.history.length > 1) { e.preventDefault(); window.history.back() } }}
        >
          <ArrowLeft className="h-4 w-4" /> Back to session
        </Link>
        <h1 className="text-2xl font-bold">Log detail</h1>
        <p className="break-all font-mono text-xs text-muted-foreground">{tid}</p>
      </div>

      {isLoading && <LoadingSpinner />}
      {isError && <EmptyState title="Log not found" description="It may belong to a deleted session." />}
      {data && <LogDetail entry={data.log} />}
    </div>
  )
}
