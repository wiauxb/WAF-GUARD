'use client'

import { Info } from 'lucide-react'
import { Badge, directiveVariant } from '@/components/ui/badge'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import type { DirectiveResponse } from '@/types'

interface DirectiveTableProps {
  directives: DirectiveResponse[]
  onSelect: (d: DirectiveResponse) => void
  selectedNodeId?: number | null
  /** Re-run a search from a chip inside the table. */
  onTagClick?: (tag: string) => void
  onRuleIdClick?: (ruleId: number) => void
  /** Suppress the Location explainer in nested/compact tables where it is just noise. */
  showHints?: boolean
}

/**
 * Directive results table.
 *
 * Columns are chosen from what is actually populated: `if_level` and `conditions` are
 * empty on every directive in practice, so they live in the detail panel instead.
 * `location` IS shown — it is nearly always empty today because the parser does not yet
 * track <LocationMatch>, but it is the next fix, so the column is here waiting for it.
 */
export function DirectiveTable({
  directives,
  onSelect,
  selectedNodeId,
  onTagClick,
  onRuleIdClick,
  showHints = true,
}: DirectiveTableProps) {
  // Explain the blank Location column rather than letting it look like a bug.
  const withLocation = directives.filter((d) => d.location).length
  const locationMostlyEmpty =
    showHints && directives.length >= 5 && withLocation / directives.length < 0.1

  return (
    <div className="space-y-3">
      {locationMostlyEmpty && (
        <div className="flex items-start gap-2 rounded-md border border-blue-200 bg-blue-50 px-3 py-2 text-sm text-blue-900">
          <Info className="mt-0.5 h-4 w-4 shrink-0" />
          <p>
            <span className="font-medium">Location is mostly empty.</span> The parser does
            not track <code className="font-mono text-xs">&lt;LocationMatch&gt;</code> yet,
            so directives inside those blocks are recorded without a location. Plain{' '}
            <code className="font-mono text-xs">&lt;Location&gt;</code> blocks are correct.
          </p>
        </div>
      )}

      <div className="rounded-lg border">
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/40">
              <TableHead>Node ID</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Rule ID</TableHead>
              <TableHead>Phase</TableHead>
              <TableHead>Location</TableHead>
              <TableHead>Tags</TableHead>
              <TableHead className="w-[40%]">Arguments</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {directives.map((d) => (
              <TableRow
                key={d.node_id}
                onClick={() => onSelect(d)}
                className={
                  'cursor-pointer ' +
                  (selectedNodeId === d.node_id ? 'bg-primary/5' : '')
                }
              >
                <TableCell className="font-mono text-xs tabular-nums">{d.node_id}</TableCell>
                <TableCell>
                  <Badge variant={directiveVariant(d.type)}>{d.type}</Badge>
                </TableCell>
                <TableCell className="font-mono text-xs tabular-nums">
                  {d.rule_id != null ? (
                    <button
                      className="hover:underline"
                      onClick={(e) => {
                        e.stopPropagation()
                        onRuleIdClick?.(d.rule_id!)
                      }}
                      title="Find all directives with this rule ID"
                    >
                      {d.rule_id}
                    </button>
                  ) : (
                    <span className="text-muted-foreground">—</span>
                  )}
                </TableCell>
                <TableCell>
                  {d.phase != null ? (
                    <Badge variant="phase">{d.phase}</Badge>
                  ) : (
                    <span className="text-muted-foreground">—</span>
                  )}
                </TableCell>
                <TableCell className="max-w-[160px] truncate font-mono text-xs">
                  {d.location || <span className="text-muted-foreground">—</span>}
                </TableCell>
                <TableCell>
                  <div className="flex max-w-[200px] flex-wrap gap-1">
                    {d.tags.slice(0, 2).map((t) => (
                      <Badge
                        key={t}
                        variant="tag"
                        clickable={!!onTagClick}
                        onClick={(e) => {
                          e.stopPropagation()
                          onTagClick?.(t)
                        }}
                      >
                        {t}
                      </Badge>
                    ))}
                    {d.tags.length > 2 && (
                      <Badge variant="muted">+{d.tags.length - 2}</Badge>
                    )}
                    {d.tags.length === 0 && <span className="text-muted-foreground">—</span>}
                  </div>
                </TableCell>
                <TableCell className="max-w-[520px]">
                  <code className="line-clamp-2 break-all font-mono text-xs text-muted-foreground">
                    {d.args}
                  </code>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}
