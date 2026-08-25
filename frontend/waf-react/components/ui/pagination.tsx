'use client'

import { ChevronLeft, ChevronRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

interface PaginationProps {
  /** Full match count, not the page size. */
  total: number
  limit: number
  offset: number
  onChange: (next: { limit: number; offset: number }) => void
  disabled?: boolean
}

const PAGE_SIZES = [25, 50, 100, 250]

/**
 * Offset pagination for analysis result lists.
 *
 * The API returns `total_count` for the whole match set alongside one page, so the page
 * count is known up front. Results are ordered deterministically server-side (by node_id,
 * or by execution order for the request filter), so paging never repeats or skips a row.
 */
export function Pagination({ total, limit, offset, onChange, disabled }: PaginationProps) {
  if (total === 0) return null

  const page = Math.floor(offset / limit) + 1
  const pages = Math.max(1, Math.ceil(total / limit))
  const from = offset + 1
  const to = Math.min(offset + limit, total)

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 border-t pt-3">
      <p className="text-sm text-muted-foreground">
        Showing <span className="font-medium text-foreground">{from.toLocaleString()}</span>
        {'–'}
        <span className="font-medium text-foreground">{to.toLocaleString()}</span> of{' '}
        <span className="font-medium text-foreground">{total.toLocaleString()}</span>
      </p>

      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">Per page</span>
          <Select
            value={String(limit)}
            onValueChange={(v) => onChange({ limit: Number(v), offset: 0 })}
          >
            <SelectTrigger className="h-8 w-[76px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {PAGE_SIZES.map((s) => (
                <SelectItem key={s} value={String(s)}>
                  {s}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="flex items-center gap-1">
          <Button
            variant="outline"
            size="sm"
            disabled={disabled || offset === 0}
            onClick={() => onChange({ limit, offset: Math.max(0, offset - limit) })}
          >
            <ChevronLeft className="h-4 w-4" />
            Prev
          </Button>
          <span className="px-2 text-sm tabular-nums text-muted-foreground">
            {page} / {pages.toLocaleString()}
          </span>
          <Button
            variant="outline"
            size="sm"
            disabled={disabled || to >= total}
            onClick={() => onChange({ limit, offset: offset + limit })}
          >
            Next
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  )
}
