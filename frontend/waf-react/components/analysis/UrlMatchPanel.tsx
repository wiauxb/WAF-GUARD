'use client'

import { Route } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { LoadingSpinner } from '@/components/ui/loading-spinner'
import { displayValue } from './FilterBar'
import type { UrlMatchResponse } from '@/types'

interface UrlMatchPanelProps {
  data?: UrlMatchResponse
  loading?: boolean
  /** Narrow from "5 patterns matched" to one of them. */
  onPick: (locationValue: string) => void
}

/**
 * Which location containers a pasted URL falls into.
 *
 * The point of the feature: with 545 `<LocationMatch>` regexes in a configuration, "does
 * this URL hit that block" is not a question you answer by reading. Showing the matched
 * patterns matters as much as filtering by them, so they are listed rather than folded
 * silently into the result count.
 *
 * `data.warnings` — containers the backend judges unreachable — is deliberately NOT
 * rendered. The reasoning behind it is subtle enough that displaying it risks asserting
 * something wrong to an audience. The endpoint still returns it if it is ever wanted.
 */
export function UrlMatchPanel({ data, loading, onPick }: UrlMatchPanelProps) {
  if (loading) {
    return (
      <Card>
        <CardContent className="p-4">
          <LoadingSpinner />
        </CardContent>
      </Card>
    )
  }
  if (!data) return null

  return (
    <Card>
      <CardContent className="space-y-3 p-4">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <p className="flex items-center gap-2 text-sm">
            <Route className="h-4 w-4 shrink-0 text-muted-foreground" />
            <span>
              <span className="font-medium">
                {data.matches.length} location {data.matches.length === 1 ? 'block' : 'blocks'}
              </span>{' '}
              cover{data.matches.length === 1 ? 's' : ''}{' '}
              <code className="font-mono text-xs">{data.path}</code>
            </span>
          </p>
          {/* "in these blocks", not just "directives": the table below shows the count
              AFTER the other chips apply, and two bare totals on one screen read as a
              contradiction. This one is about location matching alone. */}
          <p className="text-sm text-muted-foreground">
            {data.total_directives.toLocaleString()} directives in these blocks
          </p>
        </div>

        {data.matches.length === 0 ? (
          <p className="py-2 text-sm text-muted-foreground">
            No location block covers this path.
          </p>
        ) : (
          <ul className="divide-y rounded-md border">
            {data.matches.map((m) => (
              <li key={`${m.kind}-${m.value}`}>
                <button
                  type="button"
                  onClick={() => onPick(m.value)}
                  title="Filter to just this location"
                  className="flex w-full items-baseline justify-between gap-3 px-3 py-1.5 text-left hover:bg-muted"
                >
                  <span className="flex min-w-0 items-baseline gap-1.5">
                    <span className="truncate font-mono text-xs">
                      {displayValue(m.value, 'location')}
                    </span>
                    {m.kind === 'LocationMatch' && (
                      <span className="shrink-0 text-[10px] uppercase tracking-wide text-muted-foreground">
                        regex
                      </span>
                    )}
                  </span>
                  <span className="shrink-0 tabular-nums text-xs text-muted-foreground">
                    {m.count.toLocaleString()}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}

        {/* Stated rather than silent: these DO apply to the URL, they are just excluded
            because they apply to every URL and would swamp the result on every query. */}
        <p className="text-xs text-muted-foreground">
          Not counted: {data.no_location_count.toLocaleString()} directives sit outside every
          location block, so they apply to all paths — add an{' '}
          <span className="font-medium">All paths</span> location filter to include them.
        </p>

      </CardContent>
    </Card>
  )
}
