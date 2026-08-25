'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  ChevronDown,
  ChevronRight,
  FileCode,
  Layers,
  Scissors,
  X,
} from 'lucide-react'
import { Badge, directiveVariant } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { LoadingSpinner } from '@/components/ui/loading-spinner'
import { getMacroTrace, getNodeMetadata, getRemoversOfNode } from '@/lib/analysis'
import type { DirectiveResponse } from '@/types'

interface DirectiveDetailProps {
  directive: DirectiveResponse
  onClose: () => void
  onTagClick: (tag: string) => void
  onRuleIdClick: (ruleId: number) => void
  onSymbolClick: (name: string) => void
  onSourceClick: (filePath: string, lineNumber: number) => void
  onNodeIdClick: (nodeId: number) => void
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-muted-foreground">{label}</dt>
      <dd className="mt-0.5 text-sm">{children}</dd>
    </div>
  )
}

function Section({
  title,
  icon: Icon,
  count,
  children,
  defaultOpen = true,
}: {
  title: string
  icon: React.ElementType
  count?: number
  children: React.ReactNode
  defaultOpen?: boolean
}) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="border-t pt-4">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center gap-2 text-left"
      >
        {open ? (
          <ChevronDown className="h-4 w-4 text-muted-foreground" />
        ) : (
          <ChevronRight className="h-4 w-4 text-muted-foreground" />
        )}
        <Icon className="h-4 w-4 text-muted-foreground" />
        <span className="font-medium">{title}</span>
        {count != null && <Badge variant="muted">{count}</Badge>}
      </button>
      {open && <div className="mt-3 pl-6">{children}</div>}
    </div>
  )
}

/**
 * Side panel for one directive.
 *
 * Beyond the directive's own fields it pulls three more endpoints, which is what makes
 * them discoverable without a separate form each: the source chain, the macro trace and
 * the removers. Provenance comes from /nodes/{id}/metadata — the parser's own `context`
 * string was removed from the API because it was truncated on ~98.5% of directives.
 */
export function DirectiveDetail({
  directive: d,
  onClose,
  onTagClick,
  onRuleIdClick,
  onSymbolClick,
  onSourceClick,
  onNodeIdClick,
}: DirectiveDetailProps) {
  const metadata = useQuery({
    queryKey: ['analysis', 'metadata', d.node_id],
    queryFn: () => getNodeMetadata(d.node_id),
  })
  const removers = useQuery({
    queryKey: ['analysis', 'removers', d.node_id],
    queryFn: () => getRemoversOfNode(d.node_id, { limit: 50 }),
  })
  const [showTrace, setShowTrace] = useState(false)
  const trace = useQuery({
    queryKey: ['analysis', 'macro-trace', d.node_id],
    queryFn: () => getMacroTrace(d.node_id),
    enabled: showTrace,
  })

  return (
    <aside className="flex h-full w-full flex-col overflow-y-auto border-l bg-background">
      <div className="sticky top-0 z-10 flex items-start justify-between gap-3 border-b bg-background px-5 py-4">
        <div>
          <div className="flex items-center gap-2">
            <Badge variant={directiveVariant(d.type)}>{d.type}</Badge>
            <span className="font-mono text-sm text-muted-foreground">
              node {d.node_id}
            </span>
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            {d.msg && d.msg !== "''" ? d.msg : 'No message'}
          </p>
        </div>
        <Button variant="ghost" size="icon" onClick={onClose} aria-label="Close">
          <X className="h-4 w-4" />
        </Button>
      </div>

      <div className="space-y-4 px-5 py-4">
        {/* Identity — both id spaces, labelled so they can't be confused */}
        <dl className="grid grid-cols-2 gap-3">
          <Field label="Node ID (parser)">
            <span className="font-mono">{d.node_id}</span>
          </Field>
          <Field label="Rule ID (ModSecurity)">
            {d.rule_id != null ? (
              <button
                className="font-mono hover:underline"
                onClick={() => onRuleIdClick(d.rule_id!)}
              >
                {d.rule_id}
              </button>
            ) : (
              <span className="text-muted-foreground">none</span>
            )}
          </Field>
          <Field label="Phase">
            {d.phase != null ? <Badge variant="phase">{d.phase}</Badge> : '—'}
          </Field>
          <Field label="Virtual host">
            <span className="font-mono text-xs">{d.virtual_host || '—'}</span>
          </Field>
          <Field label="Location">
            <span className="font-mono text-xs">{d.location || '—'}</span>
          </Field>
          <Field label="If depth">{d.if_level}</Field>
        </dl>

        {d.conditions.length > 0 && (
          <Field label="Enclosing conditions">
            <ul className="mt-1 space-y-1">
              {d.conditions.map((c, i) => (
                <li key={i} className="rounded bg-muted px-2 py-1 font-mono text-xs">
                  {c}
                </li>
              ))}
            </ul>
          </Field>
        )}

        <Field label="Arguments">
          <pre className="mt-1 max-h-64 overflow-auto whitespace-pre-wrap break-all rounded-md bg-muted p-3 font-mono text-xs">
            {d.args}
          </pre>
        </Field>

        {d.tags.length > 0 && (
          <Field label="Tags">
            <div className="mt-1 flex flex-wrap gap-1">
              {d.tags.map((t) => (
                <Badge key={t} variant="tag" clickable onClick={() => onTagClick(t)}>
                  {t}
                </Badge>
              ))}
            </div>
          </Field>
        )}

        {/* Source chain — the accurate provenance */}
        <Section title="Source" icon={FileCode} count={metadata.data?.frames.length}>
          {metadata.isLoading ? (
            <LoadingSpinner />
          ) : metadata.data?.frames.length ? (
            <ol className="space-y-1">
              {metadata.data.frames.map((f, i) => (
                <li key={i}>
                  <button
                    onClick={() => onSourceClick(f.file_path, f.line_number)}
                    className="w-full rounded px-2 py-1 text-left hover:bg-muted"
                    title="Find every directive produced by this line"
                  >
                    <span className="font-medium">
                      {f.macro_name === '/' ? (
                        <span className="text-muted-foreground">in file</span>
                      ) : (
                        f.macro_name
                      )}
                    </span>
                    <span className="ml-2 font-mono text-xs text-muted-foreground">
                      {f.file_path}:{f.line_number}
                    </span>
                  </button>
                </li>
              ))}
            </ol>
          ) : (
            <p className="text-sm text-muted-foreground">No source information.</p>
          )}
        </Section>

        {/* Macro trace — lazy, it reads files on the server */}
        <Section title="Macro trace" icon={Layers} defaultOpen={false}>
          {!showTrace ? (
            <Button variant="outline" size="sm" onClick={() => setShowTrace(true)}>
              Load macro trace
            </Button>
          ) : trace.isLoading ? (
            <LoadingSpinner />
          ) : trace.data?.formatted ? (
            <pre className="max-h-96 overflow-auto whitespace-pre-wrap rounded-md bg-muted p-3 font-mono text-xs">
              {trace.data.formatted}
            </pre>
          ) : (
            <p className="text-sm text-muted-foreground">
              This directive is not inside a macro.
            </p>
          )}
        </Section>

        {/* Removals */}
        <Section title="Removed by" icon={Scissors} count={removers.data?.total_count}>
          {removers.isLoading ? (
            <LoadingSpinner />
          ) : removers.data?.removers.length ? (
            <ul className="space-y-2">
              {removers.data.removers.map((r, i) => (
                <li key={i} className="rounded-md border p-2">
                  <div className="flex items-center gap-2 text-sm">
                    <Badge variant="removal">{r.directive.type}</Badge>
                    <button
                      className="font-mono text-xs hover:underline"
                      onClick={() => onNodeIdClick(r.directive.node_id)}
                    >
                      node {r.directive.node_id}
                    </button>
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">
                    matched on {r.criterion_type === 'Id' ? 'rule ID' : 'tag pattern'}{' '}
                    <code className="font-mono">{String(r.criterion_value)}</code>
                  </p>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-muted-foreground">
              Nothing removes this directive.
            </p>
          )}
        </Section>

        {/* Symbols */}
        {(d.constants.length > 0 || d.variables.length > 0) && (
          <Section title="Symbols used" icon={Layers} defaultOpen={false}>
            {d.constants.length > 0 && (
              <div className="mb-3">
                <p className="mb-1 text-xs uppercase tracking-wide text-muted-foreground">
                  Constants
                </p>
                <div className="flex flex-wrap gap-1">
                  {d.constants.map((c, i) => (
                    <Badge key={i} variant="outline" clickable onClick={() => onSymbolClick(c)}>
                      {c}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
            {d.variables.length > 0 && (
              <div>
                <p className="mb-1 text-xs uppercase tracking-wide text-muted-foreground">
                  Variables
                </p>
                <div className="flex flex-wrap gap-1">
                  {d.variables.map((v, i) => (
                    <Badge key={i} variant="secondary" clickable onClick={() => onSymbolClick(v)}>
                      {v}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </Section>
        )}
      </div>
    </aside>
  )
}
