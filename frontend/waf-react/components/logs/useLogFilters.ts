'use client'

import { useCallback, useMemo } from 'react'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'
import type { ColFilter, FilterType, Prediction } from '@/lib/logs'
import { toRequest } from '@/lib/logs'

export interface LogFilterState {
  prediction: Prediction | null
  category: string | null
  q: string
  from: string
  to: string
  cols: ColFilter[]
}

const encodeCol = (c: ColFilter) => `${c.name}:${c.type}:${c.value}`

function decodeCols(all: string[]): ColFilter[] {
  return all.flatMap((entry) => {
    const i = entry.indexOf(':')
    const j = entry.indexOf(':', i + 1)
    if (i < 0 || j < 0) return []
    return [{ name: entry.slice(0, i), type: entry.slice(i + 1, j) as FilterType, value: entry.slice(j + 1) }]
  })
}

/**
 * Filter state lives in the URL, so a filtered view can be bookmarked or shared and
 * survives a refresh. The same object drives the request sent to the API.
 */
export function useLogFilters() {
  const router = useRouter()
  const pathname = usePathname()
  const sp = useSearchParams()

  const state: LogFilterState = useMemo(() => ({
    prediction: (sp.get('prediction') as Prediction | null) || null,
    category: sp.get('category'),
    q: sp.get('q') ?? '',
    from: sp.get('from') ?? '',
    to: sp.get('to') ?? '',
    cols: decodeCols(sp.getAll('cf')),
  }), [sp])

  const update = useCallback((patch: Partial<LogFilterState>) => {
    const next = { ...state, ...patch }
    const params = new URLSearchParams()
    if (next.prediction) params.set('prediction', next.prediction)
    if (next.category) params.set('category', next.category)
    if (next.q) params.set('q', next.q)
    if (next.from) params.set('from', next.from)
    if (next.to) params.set('to', next.to)
    next.cols.forEach((c) => params.append('cf', encodeCol(c)))
    const qs = params.toString()
    router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false })
  }, [state, router, pathname])

  const clear = useCallback(() => router.replace(pathname, { scroll: false }), [router, pathname])

  const request = useMemo(() => toRequest(state), [state])

  const activeCount =
    (state.prediction ? 1 : 0) + (state.category ? 1 : 0) + (state.q ? 1 : 0) +
    (state.from ? 1 : 0) + (state.to ? 1 : 0) + state.cols.filter((c) => c.value !== '').length

  return { state, update, clear, request, activeCount }
}
