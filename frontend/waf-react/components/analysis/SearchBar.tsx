'use client'

import { Search } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

export type SearchMode = 'request' | 'rule-id' | 'tag' | 'node-id' | 'source'

export interface SearchState {
  mode: SearchMode
  location: string
  host: string
  ruleId: string
  tag: string
  nodeId: string
  filePath: string
  lineNumber: string
}

export const initialSearch: SearchState = {
  mode: 'request',
  location: '.*',
  host: '.*',
  ruleId: '',
  tag: '',
  nodeId: '',
  filePath: '',
  lineNumber: '',
}

const MODES: { value: SearchMode; label: string; hint: string }[] = [
  { value: 'request', label: 'Request filter', hint: 'Which directives apply to a host and path' },
  { value: 'rule-id', label: 'Rule ID', hint: 'ModSecurity id:NNN — several rows for a chained rule' },
  { value: 'tag', label: 'Tag', hint: 'Exact tag value' },
  { value: 'node-id', label: 'Node ID', hint: "The parser's own id — not the rule ID" },
  { value: 'source', label: 'Source line', hint: 'Which directives a config line produced' },
]

interface SearchBarProps {
  value: SearchState
  onChange: (next: SearchState) => void
  onSearch: () => void
  loading?: boolean
}

export function SearchBar({ value, onChange, onSearch, loading }: SearchBarProps) {
  const set = (patch: Partial<SearchState>) => onChange({ ...value, ...patch })
  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    onSearch()
  }
  const mode = MODES.find((m) => m.value === value.mode)!

  return (
    <form onSubmit={submit} className="space-y-3 rounded-lg border bg-card p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
        <div className="sm:w-52">
          <label className="mb-1 block text-xs uppercase tracking-wide text-muted-foreground">
            Search by
          </label>
          <Select
            value={value.mode}
            onValueChange={(v) => set({ mode: v as SearchMode })}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {MODES.map((m) => (
                <SelectItem key={m.value} value={m.value}>
                  {m.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {value.mode === 'request' && (
          <>
            <div className="flex-1">
              <label className="mb-1 block text-xs uppercase tracking-wide text-muted-foreground">
                Host (regex)
              </label>
              <Input
                value={value.host}
                onChange={(e) => set({ host: e.target.value })}
                placeholder=".*"
                className="font-mono"
              />
            </div>
            <div className="flex-1">
              <label className="mb-1 block text-xs uppercase tracking-wide text-muted-foreground">
                Location (regex)
              </label>
              <Input
                value={value.location}
                onChange={(e) => set({ location: e.target.value })}
                placeholder=".*"
                className="font-mono"
              />
            </div>
          </>
        )}

        {value.mode === 'rule-id' && (
          <div className="flex-1">
            <label className="mb-1 block text-xs uppercase tracking-wide text-muted-foreground">
              ModSecurity rule ID
            </label>
            <Input
              value={value.ruleId}
              onChange={(e) => set({ ruleId: e.target.value })}
              placeholder="e.g. 5000402"
              inputMode="numeric"
              className="font-mono"
            />
          </div>
        )}

        {value.mode === 'tag' && (
          <div className="flex-1">
            <label className="mb-1 block text-xs uppercase tracking-wide text-muted-foreground">
              Tag
            </label>
            <Input
              value={value.tag}
              onChange={(e) => set({ tag: e.target.value })}
              placeholder="e.g. security"
              className="font-mono"
            />
          </div>
        )}

        {value.mode === 'node-id' && (
          <div className="flex-1">
            <label className="mb-1 block text-xs uppercase tracking-wide text-muted-foreground">
              Parser node ID
            </label>
            <Input
              value={value.nodeId}
              onChange={(e) => set({ nodeId: e.target.value })}
              placeholder="e.g. 382"
              inputMode="numeric"
              className="font-mono"
            />
          </div>
        )}

        {value.mode === 'source' && (
          <>
            <div className="flex-[2]">
              <label className="mb-1 block text-xs uppercase tracking-wide text-muted-foreground">
                File path
              </label>
              <Input
                value={value.filePath}
                onChange={(e) => set({ filePath: e.target.value })}
                placeholder="/etc/httpd/conf/common/security/config.conf"
                className="font-mono"
              />
            </div>
            <div className="sm:w-28">
              <label className="mb-1 block text-xs uppercase tracking-wide text-muted-foreground">
                Line
              </label>
              <Input
                value={value.lineNumber}
                onChange={(e) => set({ lineNumber: e.target.value })}
                placeholder="412"
                inputMode="numeric"
                className="font-mono"
              />
            </div>
          </>
        )}

        <Button type="submit" disabled={loading}>
          <Search className="mr-2 h-4 w-4" />
          Search
        </Button>
      </div>

      <p className="text-xs text-muted-foreground">{mode.hint}</p>
    </form>
  )
}
