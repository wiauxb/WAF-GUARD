import type { LogEntryResponse, LogFilter } from '@/types'

export type Prediction = 'false_positive' | 'true_positive'
export type FilterType = 'exact' | 'contains' | 'greater_than' | 'less_than'

export interface ColFilter {
  name: string
  type: FilterType
  value: string
}

/** Semantic colours: green = benign alert (FP), red = real attack (TP). */
export const FP_COLOR = '#10b981'
export const TP_COLOR = '#ef4444'

export const PREDICTION_LABEL: Record<Prediction, string> = {
  false_positive: 'False positive',
  true_positive: 'True positive',
}

export const PREDICTION_HELP: Record<Prediction, string> = {
  false_positive: 'Alert raised by a rule on a legitimate request',
  true_positive: 'Alert raised on a real attack',
}

/** Classes for badges/panels; each pairs a light and a dark variant. */
export const PREDICTION_STYLE: Record<Prediction, { badge: string; panel: string; text: string; bar: string }> = {
  false_positive: {
    badge: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400',
    panel: 'border-emerald-500/30 bg-emerald-500/5',
    text: 'text-emerald-700 dark:text-emerald-400',
    bar: 'bg-emerald-500',
  },
  true_positive: {
    badge: 'border-red-500/30 bg-red-500/10 text-red-700 dark:text-red-400',
    panel: 'border-red-500/30 bg-red-500/5',
    text: 'text-red-700 dark:text-red-400',
    bar: 'bg-red-500',
  },
}

export const FILTERABLE_COLUMNS: { value: string; label: string }[] = [
  { value: 'host', label: 'Host' },
  { value: 'request_method', label: 'Method' },
  { value: 'request_url', label: 'URL' },
  { value: 'remote_address', label: 'Remote IP' },
  { value: 'response_status_code', label: 'Status code' },
  { value: 'max_severity', label: 'Max severity' },
  { value: 'rule_ids', label: 'Rule IDs' },
  { value: 'rule_count', label: 'Rule count' },
  { value: 'tags', label: 'Tags' },
  { value: 'messages', label: 'Messages' },
  { value: 'matched_data', label: 'Matched data' },
  { value: 'matched_locations', label: 'Matched location' },
  { value: 'user_agent', label: 'User-Agent' },
  { value: 'payload', label: 'Payload' },
  { value: 'action', label: 'Action' },
]

export const FILTER_TYPES: { value: FilterType; label: string }[] = [
  { value: 'contains', label: 'contains' },
  { value: 'exact', label: 'equals' },
  { value: 'greater_than', label: 'greater than' },
  { value: 'less_than', label: 'less than' },
]

const CATEGORY_COLORS = [
  '#f97316', '#3b82f6', '#8b5cf6', '#eab308', '#06b6d4', '#ec4899',
  '#14b8a6', '#84cc16', '#6366f1', '#f59e0b', '#0ea5e9', '#a855f7',
]

export function categoryColor(index: number): string {
  return CATEGORY_COLORS[index % CATEGORY_COLORS.length]
}

export function splitPipe(value: string | undefined | null): string[] {
  return value ? value.split('|').filter(Boolean) : []
}

const MONTHS: Record<string, number> = {
  Jan: 0, Feb: 1, Mar: 2, Apr: 3, May: 4, Jun: 5, Jul: 6, Aug: 7, Sep: 8, Oct: 9, Nov: 10, Dec: 11,
}

/** Parses "21/Sep/2025:10:15:23.123456 +0200" (ModSecurity section A). */
export function parseModsecTime(ts: string | undefined | null): Date | null {
  if (!ts) return null
  const m = ts.match(/(\d{2})\/(\w{3})\/(\d{4}):(\d{2}):(\d{2}):(\d{2})(?:\.\d+)?(?: ([+-])(\d{2})(\d{2}))?/)
  if (!m || !(m[2] in MONTHS)) return null
  const [, d, mon, y, hh, mm, ss, sign, oh, om] = m
  let ms = Date.UTC(+y, MONTHS[mon], +d, +hh, +mm, +ss)
  if (sign) ms -= (sign === '+' ? 1 : -1) * (+oh * 60 + +om) * 60_000
  return new Date(ms)
}

export interface ParsedMessage {
  id?: string
  msg?: string
  severity?: string
  data?: string
  tags: string[]
  at?: string
  file?: string
  line?: string
  raw: string
}

/** Splits one ModSecurity `Message:` line into its bracketed fields. */
export function parseMessage(raw: string): ParsedMessage {
  const one = (re: RegExp) => raw.match(re)?.[1]
  return {
    id: one(/\[id "(\d+)"\]/),
    msg: one(/\[msg "(.*?)"\]/),
    severity: one(/\[severity "(.*?)"\]/),
    data: one(/\[data "(.*?)"\]/),
    tags: [...raw.matchAll(/\[tag "(.*?)"\]/g)].map((t) => t[1]),
    at: one(/ at (\S+?)\./),
    file: one(/\[file "(.*?)"\]/),
    line: one(/\[line "(.*?)"\]/),
    raw,
  }
}

export function severityStyle(sev: string | undefined): string {
  switch ((sev ?? '').toUpperCase()) {
    case 'CRITICAL': return 'border-red-500/30 bg-red-500/10 text-red-700 dark:text-red-400'
    case 'ERROR': return 'border-orange-500/30 bg-orange-500/10 text-orange-700 dark:text-orange-400'
    case 'WARNING': return 'border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-400'
    case 'NOTICE': return 'border-sky-500/30 bg-sky-500/10 text-sky-700 dark:text-sky-400'
    default: return 'border-border bg-muted text-muted-foreground'
  }
}

/** First message of an entry: the readable reason the WAF raised the alert. */
export function firstMessage(entry: LogEntryResponse): string {
  return entry.features.messages.split(' || ')[0] ?? ''
}

export function statusStyle(code: string): string {
  const n = Number(code)
  if (n >= 500) return 'text-red-600 dark:text-red-400'
  if (n >= 400) return 'text-orange-600 dark:text-orange-400'
  if (n >= 300) return 'text-sky-600 dark:text-sky-400'
  if (n >= 200) return 'text-emerald-600 dark:text-emerald-400'
  return 'text-muted-foreground'
}

/** Attack-type probabilities arrive as [{label: p, ...}] or as one flat dict. */
export function attackProbabilities(entry: LogEntryResponse): { label: string; p: number }[] {
  const merged: Record<string, number> = {}
  for (const obj of entry.attack_type?.probabilities ?? []) {
    if (obj && typeof obj === 'object') {
      for (const [k, v] of Object.entries(obj)) if (typeof v === 'number') merged[k] = v
    }
  }
  return Object.entries(merged).map(([label, p]) => ({ label, p })).sort((a, b) => b.p - a.p)
}

export function toRequest(state: {
  prediction: Prediction | null
  category: string | null
  q: string
  from: string
  to: string
  cols: ColFilter[]
}): LogFilter {
  const columns = state.cols.filter((c) => c.name && c.value !== '')
  return {
    ...(state.prediction ? { prediction: state.prediction } : {}),
    ...(state.category ? { category: state.category } : {}),
    ...(state.q.trim() ? { search: state.q.trim() } : {}),
    ...(state.from ? { start_time: new Date(state.from).toISOString() } : {}),
    ...(state.to ? { end_time: new Date(state.to).toISOString() } : {}),
    ...(columns.length ? { columns } : {}),
  }
}
