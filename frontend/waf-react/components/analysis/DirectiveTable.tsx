'use client'

import { ArrowDown, ArrowUp, ChevronsUpDown } from 'lucide-react'
import { Badge, directiveVariant } from '@/components/ui/badge'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import type { DirectiveResponse, SortDir, SortField } from '@/types'
import { displayValue, type SortState } from './FilterBar'

interface DirectiveTableProps {
  directives: DirectiveResponse[]
  onSelect: (d: DirectiveResponse) => void
  selectedNodeId?: number | null
  /** Re-run a search from a chip inside the table. */
  onTagClick?: (tag: string) => void
  onRuleIdClick?: (ruleId: number) => void
  /**
   * Sorting. Both optional together — omit them and the headers render as plain labels,
   * which is what the Removals tab and the nested usage tables want: those show one
   * unpaginated set, so a header that reordered only the visible rows would mislead.
   */
  sort?: SortState
  onSortChange?: (next: SortState) => void
}

/**
 * Directive results table.
 *
 * Columns are chosen from what is actually populated: `if_level` and `conditions` are
 * empty on every directive in practice, so they live in the detail panel instead.
 * `location` IS shown, though it is nearly always empty today: the parser does not yet
 * track <LocationMatch>, so directives inside those blocks carry no location. That is the
 * next parser fix, so the column stays.
 *
 * Sorting is applied by the SERVER over the whole match set, never here over the current
 * page — ordering 50 rows out of ~97,000 would answer a different question than the one
 * clicking a header asks.
 */
export function DirectiveTable({
  directives,
  onSelect,
  selectedNodeId,
  onTagClick,
  onRuleIdClick,
  sort,
  onSortChange,
}: DirectiveTableProps) {
  /** A header cell that sorts, when the parent supports it. */
  const SortHead = ({
    field,
    children,
    className,
  }: {
    field: SortField
    children: React.ReactNode
    className?: string
  }) => {
    if (!sort || !onSortChange) return <TableHead className={className}>{children}</TableHead>

    const active = sort.by === field
    // A fresh column starts ascending; the active one flips.
    const next: SortDir = active && sort.dir === 'asc' ? 'desc' : 'asc'
    const Icon = !active ? ChevronsUpDown : sort.dir === 'asc' ? ArrowUp : ArrowDown

    return (
      <TableHead className={className}>
        <button
          type="button"
          onClick={() => onSortChange({ by: field, dir: next })}
          aria-sort={active ? (sort.dir === 'asc' ? 'ascending' : 'descending') : 'none'}
          className={
            'group -mx-1 flex items-center gap-1 rounded px-1 py-0.5 hover:text-foreground ' +
            (active ? 'text-foreground' : '')
          }
        >
          {children}
          <Icon
            className={
              'h-3.5 w-3.5 shrink-0 ' + (active ? 'opacity-100' : 'opacity-30 group-hover:opacity-60')
            }
          />
        </button>
      </TableHead>
    )
  }

  return (
    <div className="space-y-3">
      <div className="rounded-lg border">
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/40">
              <SortHead field="node_id">Node ID</SortHead>
              <SortHead field="type">Type</SortHead>
              <SortHead field="rule_id">Rule ID</SortHead>
              <SortHead field="phase">Phase</SortHead>
              <SortHead field="host">Host</SortHead>
              <SortHead field="location">Location</SortHead>
              {/* Not sortable: tags is a list, args is free text — neither has a
                  meaningful single order, and both are expensive to sort at scale. */}
              <TableHead>Tags</TableHead>
              <TableHead className="w-[32%]">Arguments</TableHead>
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
                {/* Both stored with the quotes the dump used (`"*:80"`), so both go
                    through displayValue rather than rendering raw. */}
                <TableCell className="max-w-[140px] truncate font-mono text-xs">
                  {d.virtual_host ? (
                    displayValue(d.virtual_host, 'host')
                  ) : (
                    // Not missing data: no VirtualHost means server-level configuration.
                    // Named here as well as in the filter, so a "Host: Global" chip and the
                    // rows it selects say the same thing.
                    <span className="text-muted-foreground">Global</span>
                  )}
                </TableCell>
                <TableCell className="max-w-[160px] truncate font-mono text-xs">
                  {d.location ? (
                    displayValue(d.location, 'location')
                  ) : (
                    <span className="text-muted-foreground">—</span>
                  )}
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
