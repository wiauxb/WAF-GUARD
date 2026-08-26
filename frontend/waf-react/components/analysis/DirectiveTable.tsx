'use client'

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
}

/**
 * Directive results table.
 *
 * Columns are chosen from what is actually populated: `if_level` and `conditions` are
 * empty on every directive in practice, so they live in the detail panel instead.
 * `location` IS shown, though it is nearly always empty today: the parser does not yet
 * track <LocationMatch>, so directives inside those blocks carry no location. That is the
 * next parser fix, so the column stays.
 */
export function DirectiveTable({
  directives,
  onSelect,
  selectedNodeId,
  onTagClick,
  onRuleIdClick,
}: DirectiveTableProps) {
  return (
    <div className="space-y-3">
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
