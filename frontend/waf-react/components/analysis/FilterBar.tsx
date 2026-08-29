'use client'

import { useEffect, useState } from 'react'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { Plus, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Combobox } from '@/components/ui/combobox'
import { Input } from '@/components/ui/input'
// Still used for the "Add filter" kind picker — a closed list of 12, which is what Select
// is for. The VALUE pickers are all Combobox now.
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { getDirectiveValues } from '@/lib/analysis'
import type {
  DirectiveSearchQuery,
  SortDir,
  SortField,
  ValueField,
} from '@/types'

/**
 * The criteria a directive can be filtered by.
 *
 * Each maps to a field of DirectiveSearchQuery. The split below decides what a second chip
 * of the same kind means, and it follows the underlying property rather than taste:
 * a directive has ONE type and ONE phase, so two of those read as "either"; it carries a
 * LIST of tags, so two of those read as "both".
 */
export type FilterKind =
  | 'type' | 'phase' | 'rule-id' | 'tag' | 'host' | 'location' | 'msg'  // repeatable
  | 'node-id' | 'args' | 'has-rule-id' | 'source' | 'url'               // one at a time

export interface Filter {
  kind: FilterKind
  /** The payload, as typed. `source` packs "path:line" and unpacks in toQuery(). */
  value: string
}

export interface SortState {
  by: SortField
  dir: SortDir
}

// toQuery needs a sort, but a facet count is an aggregate — ordering is irrelevant to it.
// A fixed value keeps it out of the React Query key, so changing the table's sort does not
// needlessly refetch every dropdown.
const FACET_SORT: SortState = { by: 'node_id', dir: 'asc' }

/** Kinds that accumulate. Everything else replaces the existing chip of its kind. */
const REPEATABLE: FilterKind[] = ['type', 'phase', 'rule-id', 'tag', 'host', 'location', 'msg']

type Widget = 'text' | 'number' | 'bool' | 'source' | 'values'

/** Filter kinds backed by a searchable value list, and the API field that serves it. */
const VALUE_FIELD: Partial<Record<FilterKind, ValueField>> = {
  tag: 'tag',
  host: 'host',
  location: 'location',
  type: 'type',
  phase: 'phase',
  msg: 'msg',
}

const KINDS: {
  kind: FilterKind
  label: string
  widget: Widget
  placeholder?: string
  hint: string
}[] = [
  { kind: 'url', label: 'URL from a log', widget: 'text', placeholder: '/jira/secure/Dashboard.jspa', hint: 'Finds the <Location>/<LocationMatch> blocks covering this path \u2014 scheme, host and query are ignored' },
  { kind: 'type', label: 'Directive type', widget: 'values', placeholder: 'Search types…', hint: 'Several types match any of them' },
  { kind: 'phase', label: 'Phase', widget: 'values', placeholder: 'Search phases…', hint: 'Several phases match any of them' },
  { kind: 'tag', label: 'Tag', widget: 'values', placeholder: 'Search tags…', hint: 'Several tags require ALL of them' },
  { kind: 'rule-id', label: 'Rule ID', widget: 'number', placeholder: 'e.g. 5000402', hint: 'ModSecurity id:NNN — several rows for a chained rule' },
  { kind: 'args', label: 'Arguments contain', widget: 'text', placeholder: 'e.g. REQUEST_URI', hint: 'Case-insensitive substring of the directive arguments' },
  { kind: 'msg', label: 'Message', widget: 'values', placeholder: 'Search messages…', hint: 'Several messages match any of them' },
  { kind: 'has-rule-id', label: 'Has rule ID', widget: 'bool', hint: 'Separates real ModSecurity rules from the config directives around them' },
  { kind: 'host', label: 'Host', widget: 'values', placeholder: 'Search hosts…', hint: 'Several hosts match any of them' },
  { kind: 'location', label: 'Location', widget: 'values', placeholder: 'Search locations…', hint: 'Several locations match any of them' },
  { kind: 'node-id', label: 'Node ID', widget: 'number', placeholder: 'e.g. 382', hint: "The parser's own id — not the rule ID" },
  { kind: 'source', label: 'Source line', widget: 'source', hint: 'Which directives a given config line produced' },
]

const KIND_LABEL = Object.fromEntries(KINDS.map((k) => [k.kind, k.label])) as Record<
  FilterKind,
  string
>

/**
 * What the empty string reads as, per kind. Neither of these is missing data — an absent
 * container is itself a scope, and naming it says something true about the directive.
 *
 * The two are NOT the same word, because the empty value means different things:
 *
 *   host     — outside every `<VirtualHost>` is server-level config, which is precisely
 *              what Apache calls the global context.
 *   location — outside every `<Location>` is NOT global; it applies to every path within
 *              whatever scope encloses it. Measured on this configuration: of the 20,995
 *              directives with no location, only 7,373 (35%) are also outside a
 *              VirtualHost. The other 65% sit inside one, so "Global" would be wrong for
 *              two out of three. "All paths" is true in both cases.
 */
const EMPTY_LABEL: Partial<Record<FilterKind, string>> = {
  host: 'Global',
  location: 'All paths',
}

/**
 * How a stored value reads on screen.
 *
 * Values arrive exactly as the parser recorded them, which is what the filter needs but not
 * what anyone wants to look at: the dump preserves the quotes around `"*:80"` and
 * `".well-known/acme-challenge"`, and stores "outside any block" as the empty string.
 * Only the label changes — the raw value is what travels to the API.
 */
export function displayValue(v: string | null | undefined, kind?: FilterKind): string {
  if (v == null || v === '') return (kind && EMPTY_LABEL[kind]) || '(none)'
  return v.length > 1 && v.startsWith('"') && v.endsWith('"') ? v.slice(1, -1) : v
}

/** How a chip reads once applied — used for aria-labels and anywhere the kind is not shown. */
export function describeFilter(f: Filter): string {
  if (f.kind === 'has-rule-id') return f.value === 'true' ? 'Has a rule ID' : 'No rule ID'
  return `${KIND_LABEL[f.kind]}: ${displayValue(f.value, f.kind)}`
}

/** Just the value: the chip rows print the kind once, as a heading for the group. */
function chipValue(f: Filter): string {
  if (f.kind === 'has-rule-id') return f.value === 'true' ? 'yes' : 'no'
  return displayValue(f.value, f.kind)
}

/**
 * Group chips by kind, preserving both the order kinds first appeared and each chip's
 * index in the flat array — `remove(index)` still operates on the unchanged `Filter[]`.
 */
function groupedFilters(filters: Filter[]): [FilterKind, { filter: Filter; index: number }[]][] {
  const groups = new Map<FilterKind, { filter: Filter; index: number }[]>()
  filters.forEach((filter, index) => {
    const list = groups.get(filter.kind)
    if (list) list.push({ filter, index })
    else groups.set(filter.kind, [{ filter, index }])
  })
  return [...groups.entries()]
}

/**
 * Fold the flat chip list into the API request body.
 *
 * Repeatable kinds collect into arrays — which the backend reads as "any of" for
 * type/phase/rule-id and "all of" for tag. Single kinds take the last chip, though the
 * add path already guarantees there is only one.
 */
export function toQuery(filters: Filter[], sort: SortState): DirectiveSearchQuery {
  const of = (kind: FilterKind) => filters.filter((f) => f.kind === kind).map((f) => f.value)
  const one = (kind: FilterKind) => of(kind).at(-1) ?? null

  const source = one('source')
  const [filePath, line] = source ? [source.slice(0, source.lastIndexOf(':')), source.slice(source.lastIndexOf(':') + 1)] : []
  const hasRuleId = one('has-rule-id')

  return {
    types: of('type'),
    phases: of('phase').map(Number),
    rule_ids: of('rule-id').map(Number),
    tags: of('tag'),
    // Exact, not the regex `host`/`location` fields: the stored values carry their quotes
    // and contain regex metacharacters, so `"*:80"` has no working pattern form.
    hosts: of('host'),
    locations: of('location'),
    node_id: one('node-id') ? Number(one('node-id')) : null,
    url: one('url'),
    args_contains: one('args'),
    msgs: of('msg'),
    has_rule_id: hasRuleId === null ? null : hasRuleId === 'true',
    source: filePath ? { file_path: filePath, line_number: Number(line) } : null,
    sort_by: sort.by,
    sort_dir: sort.dir,
  }
}

/** Add a filter, honouring the repeatable/single split and ignoring exact duplicates. */
export function addFilter(filters: Filter[], next: Filter): Filter[] {
  if (filters.some((f) => f.kind === next.kind && f.value === next.value)) return filters
  if (REPEATABLE.includes(next.kind)) return [...filters, next]
  return [...filters.filter((f) => f.kind !== next.kind), next]
}

interface FilterBarProps {
  filters: Filter[]
  onChange: (next: Filter[]) => void
  loading?: boolean
}

export function FilterBar({ filters, onChange, loading }: FilterBarProps) {
  const [kind, setKind] = useState<FilterKind>('type')
  const [draft, setDraft] = useState('')
  const [line, setDraftLine] = useState('')

  const spec = KINDS.find((k) => k.kind === kind)!
  const valueField = VALUE_FIELD[kind]

  // Debounced so typing does not fire a request per keystroke. 200ms is below the point
  // where the list feels laggy and well above a fast typist's inter-key gap.
  const [debounced, setDebounced] = useState('')
  useEffect(() => {
    const t = setTimeout(() => setDebounced(draft), 200)
    return () => clearTimeout(t)
  }, [draft])

  // Counted INSIDE the filters already applied, so each number says what adding that value
  // would actually return. The backend decides which chips to ignore -- its own, for an OR
  // field -- so the whole set is sent as-is. Keyed on `filters` so the list refreshes as
  // chips change.
  const values = useQuery({
    queryKey: ['analysis', 'values', valueField, debounced, filters],
    enabled: !!valueField,
    queryFn: () => getDirectiveValues(valueField!, debounced, 50, toQuery(filters, FACET_SORT)),
    staleTime: 30_000,
    placeholderData: keepPreviousData,   // no flicker while a chip is being added
  })

  // `source` needs both halves; everything else just needs a value.
  const ready = kind === 'source' ? !!draft && !!line : !!draft

  const commit = () => {
    if (!ready) return
    const value = kind === 'source' ? `${draft}:${line}` : draft
    onChange(addFilter(filters, { kind, value }))
    setDraft('')
    setDraftLine('')
  }

  const remove = (i: number) => onChange(filters.filter((_, j) => j !== i))

  // The dropdown widgets commit on pick — a separate "Add" click for a value chosen from a
  // closed list is a step with nothing in it.
  const pick = (value: string) => {
    onChange(addFilter(filters, { kind, value }))
    setDraft('')
  }

  return (
    <div className="space-y-3 rounded-lg border bg-card p-4">
      <form
        onSubmit={(e) => {
          e.preventDefault()
          commit()
        }}
        className="flex flex-col gap-3 sm:flex-row sm:items-end"
      >
        <div className="sm:w-52">
          <label className="mb-1 block text-xs uppercase tracking-wide text-muted-foreground">
            Add filter
          </label>
          <Select
            value={kind}
            onValueChange={(v) => {
              setKind(v as FilterKind)
              setDraft('')
              setDraftLine('')
            }}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {KINDS.map((k) => (
                <SelectItem key={k.kind} value={k.kind}>
                  {k.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {spec.widget === 'values' && (
          <div className="flex-1">
            <label className="mb-1 block text-xs uppercase tracking-wide text-muted-foreground">
              {spec.label}
            </label>
            <Combobox
              query={draft}
              onQueryChange={setDraft}
              onSelect={pick}
              loading={values.isFetching}
              placeholder={spec.placeholder}
              // Enter with nothing highlighted applies whatever was typed, so a value the
              // top-50 cut off is still reachable.
              onSubmitRaw={commit}
              options={(values.data?.values ?? []).map((v) => ({
                value: String(v.value),
                label: displayValue(String(v.value), kind),
                count: v.count,
                // Location values from a <LocationMatch> are regexes, not paths.
                note: v.kind === 'LocationMatch' ? 'regex' : undefined,
              }))}
            />
          </div>
        )}

        {(spec.widget === 'text' || spec.widget === 'number') && (
          <div className="flex-1">
            <label className="mb-1 block text-xs uppercase tracking-wide text-muted-foreground">
              {spec.label}
            </label>
            <Input
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder={spec.placeholder}
              inputMode={spec.widget === 'number' ? 'numeric' : undefined}
              className="font-mono"
            />
          </div>
        )}

        {spec.widget === 'source' && (
          <>
            <div className="flex-[2]">
              <label className="mb-1 block text-xs uppercase tracking-wide text-muted-foreground">
                File path
              </label>
              <Input
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                placeholder="/etc/httpd/conf/common/security/config.conf"
                className="font-mono"
              />
            </div>
            <div className="sm:w-28">
              <label className="mb-1 block text-xs uppercase tracking-wide text-muted-foreground">
                Line
              </label>
              <Input
                value={line}
                onChange={(e) => setDraftLine(e.target.value)}
                placeholder="412"
                inputMode="numeric"
                className="font-mono"
              />
            </div>
          </>
        )}

        {/* The value lists commit on pick; the button is for typed values. `bool` has only
            two options, so it commits on pick too. */}
        {spec.widget !== 'bool' && (
          <Button type="submit" disabled={!ready || loading}>
            <Plus className="mr-2 h-4 w-4" />
            Add filter
          </Button>
        )}
      </form>

      <p className="text-xs text-muted-foreground">{spec.hint}</p>

      {/* Chips are grouped by kind with the operator spelled out between them, because the
          rules are otherwise invisible: several tags require ALL of them, every other field
          matches ANY. One row per kind, and separate rows all have to hold at once — which
          is what the layout already implies. */}
      {filters.length > 0 && (
        <div className="space-y-1.5 border-t pt-3">
          {groupedFilters(filters).map(([kind, group]) => (
            <div key={kind} className="flex flex-wrap items-center gap-1.5">
              <span className="text-xs text-muted-foreground">{KIND_LABEL[kind]}</span>
              {group.map(({ filter, index }, i) => (
                <span key={`${filter.value}-${index}`} className="flex items-center gap-1.5">
                  {i > 0 && (
                    <span className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                      {kind === 'tag' ? 'and' : 'or'}
                    </span>
                  )}
                  <span className="inline-flex max-w-full items-center gap-1 rounded-md border border-primary/30 bg-primary/10 py-0.5 pl-2 pr-1 text-xs font-medium text-primary">
                    <span className="truncate font-mono">{chipValue(filter)}</span>
                    <button
                      type="button"
                      onClick={() => remove(index)}
                      aria-label={`Remove filter ${describeFilter(filter)}`}
                      className="rounded-sm p-0.5 hover:bg-primary/20"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </span>
                </span>
              ))}
            </div>
          ))}
          {filters.length > 1 && (
            <div className="pt-0.5">
              <Button type="button" variant="ghost" size="sm" onClick={() => onChange([])}>
                Clear all
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
