'use client'

import { useState } from 'react'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { Scissors, Search, Shield, SlidersHorizontal, Tags } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { EmptyState } from '@/components/ui/empty-state'
import { LoadingSpinner } from '@/components/ui/loading-spinner'
import { Pagination } from '@/components/ui/pagination'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ConfigGuard } from '@/components/analysis/ConfigGuard'
import { DirectiveDetail } from '@/components/analysis/DirectiveDetail'
import { DirectiveTable } from '@/components/analysis/DirectiveTable'
import { UrlMatchPanel } from '@/components/analysis/UrlMatchPanel'
import { StatsPanel } from '@/components/analysis/StatsPanel'
import {
  FilterBar,
  toQuery,
  type Filter,
  type SortState,
} from '@/components/analysis/FilterBar'
import {
  DEFAULT_PAGE_SIZE,
  getDirectivesSettingConstant,
  matchUrl,
  getDirectivesUsingConstant,
  getRemovalsByRuleId,
  getRemovalsByTag,
  searchDirectives,
  searchSymbols,
} from '@/lib/analysis'
import { useConfigStore } from '@/stores/config'
import type { DirectiveListResponse, DirectiveResponse, SymbolMatch } from '@/types'

type Page = { limit: number; offset: number }
const FIRST_PAGE: Page = { limit: DEFAULT_PAGE_SIZE, offset: 0 }
const DEFAULT_SORT: SortState = { by: 'node_id', dir: 'asc' }

export default function DirectivesPage() {
  const { selectedConfig } = useConfigStore()
  const configId = selectedConfig?.id ?? null

  const [tab, setTab] = useState('directives')

  // Each tab keeps its own state — the old page shared one `results` array across all
  // four tabs, so switching tabs showed the previous search's output.
  const [filters, setFilters] = useState<Filter[]>([])
  const [sort, setSort] = useState<SortState>(DEFAULT_SORT)
  const [page, setPage] = useState<Page>(FIRST_PAGE)
  const [selected, setSelected] = useState<DirectiveResponse | null>(null)

  const [symbolQuery, setSymbolQuery] = useState('')
  const [appliedSymbol, setAppliedSymbol] = useState('')
  // The whole match, not just its name: a :Variable node is identified by (name, value),
  // and one name commonly has several nodes — one per assigned value. Keying on the name
  // alone highlighted every variant at once and queried only the value-IS-NULL one.
  const [activeSymbol, setActiveSymbol] = useState<SymbolMatch | null>(null)

  const [removalKind, setRemovalKind] = useState<'rule' | 'tag'>('rule')
  const [removalInput, setRemovalInput] = useState('')
  const [appliedRemoval, setAppliedRemoval] = useState<{ kind: 'rule' | 'tag'; value: string } | null>(null)

  // ---------- directives tab ----------

  // One query for every combination of filters. An empty filter set is legal and returns
  // the whole configuration, which is what makes the sortable headers discoverable on
  // arrival — the backend does page+count in ~120 ms on ~97k directives.
  const directives = useQuery<DirectiveListResponse>({
    queryKey: ['analysis', 'search', configId, filters, sort, page],
    queryFn: () => searchDirectives(toQuery(filters, sort), page),
    // Filters apply on every chip change, so without this the table would blank to a
    // spinner each time one is added or removed.
    placeholderData: keepPreviousData,
  })

  // Which location blocks the pasted URL falls into. Only fetched when a URL chip exists;
  // the same matching backs the `url` search field, so the panel and the table agree.
  const urlChip = filters.find((f) => f.kind === 'url')?.value ?? null
  const urlMatch = useQuery({
    queryKey: ['analysis', 'match-url', configId, urlChip],
    enabled: !!urlChip,
    queryFn: () => matchUrl(urlChip!),
  })

  const applyFilters = (next: Filter[]) => {
    setFilters(next)
    setPage(FIRST_PAGE)          // page 3 of the old result set means nothing in the new one
    setSelected(null)
  }

  const applySort = (next: SortState) => {
    setSort(next)
    setPage(FIRST_PAGE)
  }

  // Cross-links: clicking a chip anywhere replaces the filter set with just that criterion.
  const replaceWith = (filter: Filter) => {
    setTab('directives')
    applyFilters([filter])
  }
  const searchByTag = (tag: string) => replaceWith({ kind: 'tag', value: tag })
  const searchByRuleId = (ruleId: number) =>
    replaceWith({ kind: 'rule-id', value: String(ruleId) })
  const searchByNodeId = (nodeId: number) =>
    replaceWith({ kind: 'node-id', value: String(nodeId) })
  const searchBySource = (filePath: string, lineNumber: number) =>
    replaceWith({ kind: 'source', value: `${filePath}:${lineNumber}` })
  const inspectSymbol = (name: string) => {
    setTab('symbols')
    setSymbolQuery(name)
    setAppliedSymbol(name)
    setActiveSymbol({ name, value: null, labels: [] })
  }

  // ---------- symbols tab ----------

  const symbols = useQuery({
    queryKey: ['analysis', 'symbols', configId, appliedSymbol],
    enabled: !!appliedSymbol,
    queryFn: () => searchSymbols(appliedSymbol, { limit: 100 }),
  })
  const usedBy = useQuery({
    queryKey: ['analysis', 'used-by', configId, activeSymbol?.name, activeSymbol?.value],
    enabled: !!activeSymbol,
    queryFn: () =>
      getDirectivesUsingConstant(
        { name: activeSymbol!.name, value: activeSymbol!.value },
        { limit: 25 }
      ),
  })
  const setBy = useQuery({
    queryKey: ['analysis', 'set-by', configId, activeSymbol?.name, activeSymbol?.value],
    enabled: !!activeSymbol,
    queryFn: () =>
      getDirectivesSettingConstant(
        { name: activeSymbol!.name, value: activeSymbol!.value },
        { limit: 25 }
      ),
  })

  // ---------- removals tab ----------

  const removals = useQuery({
    queryKey: ['analysis', 'removals', configId, appliedRemoval],
    enabled: !!appliedRemoval,
    queryFn: () =>
      appliedRemoval!.kind === 'rule'
        ? getRemovalsByRuleId(Number(appliedRemoval!.value), { limit: 50 })
        : getRemovalsByTag(appliedRemoval!.value, { limit: 50 }),
  })

  // A 4xx from any tab means the configuration itself isn't queryable — show the guard
  // instead of the results area.
  const blockingError = directives.error || symbols.error || removals.error

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="flex items-center gap-2 text-3xl font-bold">
            <Shield className="h-8 w-8" />
            Directives
          </h1>
          <p className="text-muted-foreground">
            Explore the parsed configuration
            {selectedConfig && (
              <>
                {' — '}
                <span className="font-medium text-foreground">{selectedConfig.name}</span>
              </>
            )}
          </p>
        </div>
      </div>

      {blockingError ? (
        <ConfigGuard error={blockingError} configurationId={configId} />
      ) : (
        <Tabs value={tab} onValueChange={setTab}>
          <TabsList className="grid w-full grid-cols-3 sm:w-auto sm:inline-grid">
            <TabsTrigger value="directives">
              <SlidersHorizontal className="mr-2 h-4 w-4" />
              Directives
            </TabsTrigger>
            <TabsTrigger value="symbols">
              <Tags className="mr-2 h-4 w-4" />
              Variables
            </TabsTrigger>
            <TabsTrigger value="removals">
              <Scissors className="mr-2 h-4 w-4" />
              Removals
            </TabsTrigger>
          </TabsList>

          {/* ============ Directives ============ */}
          <TabsContent value="directives" className="space-y-4">
            <FilterBar
              filters={filters}
              onChange={applyFilters}
              loading={directives.isFetching}
            />

            {urlChip && (
              <UrlMatchPanel
                data={urlMatch.data}
                loading={urlMatch.isLoading}
                // Drill from "5 blocks matched" into one: swap the URL chip for that
                // location, so the chip set always says exactly what is being filtered.
                onPick={(value) =>
                  applyFilters([
                    ...filters.filter((f) => f.kind !== 'url'),
                    { kind: 'location', value },
                  ])
                }
              />
            )}

            <StatsPanel filters={filters} fallbackTotal={directives.data?.total_count} />

            {directives.isLoading ? (
              <LoadingSpinner />
            ) : directives.data ? (
              <div
                className={
                  'grid gap-4 ' +
                  (selected ? 'xl:grid-cols-[minmax(0,1fr)_420px]' : 'grid-cols-1')
                }
              >
                <Card>
                  <CardContent className="space-y-4 p-4">
                    {directives.data.total_count === 0 ? (
                      <EmptyState
                        icon={Search}
                        title="No directives matched"
                        description={
                          filters.length > 1
                            ? 'All filters must hold at once — try removing one.'
                            : undefined
                        }
                      />
                    ) : (
                      <>
                        <p className="text-sm text-muted-foreground">
                          <span className="font-medium text-foreground">
                            {directives.data.total_count.toLocaleString()}
                          </span>{' '}
                          {directives.data.total_count === 1 ? 'directive' : 'directives'}
                          {filters.length === 0 && ' — add a filter to narrow down'}
                        </p>
                        <DirectiveTable
                          directives={directives.data.directives}
                          onSelect={setSelected}
                          selectedNodeId={selected?.node_id}
                          onTagClick={searchByTag}
                          onRuleIdClick={searchByRuleId}
                          sort={sort}
                          onSortChange={applySort}
                        />
                        <Pagination
                          total={directives.data.total_count}
                          limit={directives.data.limit}
                          offset={directives.data.offset}
                          onChange={setPage}
                          disabled={directives.isFetching}
                        />
                      </>
                    )}
                  </CardContent>
                </Card>

                {selected && (
                  <div className="xl:sticky xl:top-4 xl:max-h-[calc(100vh-6rem)]">
                    <DirectiveDetail
                      directive={selected}
                      onClose={() => setSelected(null)}
                      onTagClick={searchByTag}
                      onRuleIdClick={searchByRuleId}
                      onSymbolClick={inspectSymbol}
                      onSourceClick={searchBySource}
                      onNodeIdClick={searchByNodeId}
                    />
                  </div>
                )}
              </div>
            ) : null}
          </TabsContent>

          {/* ============ Symbols ============ */}
          <TabsContent value="symbols" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Constants and variables</CardTitle>
                <CardDescription>
                  Full-text search across constants, variables and collections. Pick one to
                  see which directives read it and which set it.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <form
                  className="flex gap-2"
                  onSubmit={(e) => {
                    e.preventDefault()
                    setAppliedSymbol(symbolQuery)
                    setActiveSymbol(null)
                  }}
                >
                  <Input
                    value={symbolQuery}
                    onChange={(e) => setSymbolQuery(e.target.value)}
                    placeholder="e.g. blocked, skipAfter, waf"
                    className="font-mono"
                  />
                  <Button type="submit" disabled={!symbolQuery || symbols.isFetching}>
                    <Search className="mr-2 h-4 w-4" />
                    Search
                  </Button>
                </form>
              </CardContent>
            </Card>

            {symbols.isLoading ? (
              <LoadingSpinner />
            ) : symbols.data ? (
              <div className="grid gap-4 lg:grid-cols-[320px_minmax(0,1fr)]">
                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-base">
                      {symbols.data.total_count} match
                      {symbols.data.total_count === 1 ? '' : 'es'}
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="max-h-[520px] space-y-1 overflow-y-auto">
                    {symbols.data.matches.map((m, i) => (
                      <button
                        key={`${m.name}-${i}`}
                        onClick={() => setActiveSymbol(m)}
                        className={
                          'w-full rounded-md border px-3 py-2 text-left hover:bg-muted ' +
                          (activeSymbol?.name === m.name && activeSymbol?.value === m.value
                            ? 'border-primary bg-primary/5'
                            : '')
                        }
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="truncate font-mono text-sm">{m.name}</span>
                          {m.labels[0] && <Badge variant="muted">{m.labels[0]}</Badge>}
                        </div>
                        {m.value && (
                          <p className="mt-0.5 truncate font-mono text-xs text-muted-foreground">
                            = {m.value}
                          </p>
                        )}
                      </button>
                    ))}
                    {symbols.data.matches.length === 0 && (
                      <p className="py-6 text-center text-sm text-muted-foreground">
                        No variables matched.
                      </p>
                    )}
                  </CardContent>
                </Card>

                <div className="space-y-4">
                  {!activeSymbol ? (
                    <EmptyState icon={Tags} title="Select a variable" />
                  ) : (
                    <>
                      <SymbolUsage
                        title="Read by"
                        description="Directives that use this variable"
                        data={usedBy.data}
                        loading={usedBy.isLoading}
                        onSelect={(d) => searchByNodeId(d.node_id)}
                      />
                      <SymbolUsage
                        title="Set by"
                        description="Directives that define or assign it"
                        data={setBy.data}
                        loading={setBy.isLoading}
                        onSelect={(d) => searchByNodeId(d.node_id)}
                      />
                    </>
                  )}
                </div>
              </div>
            ) : (
              <EmptyState icon={Tags} title="Search for a constant or variable" />
            )}
          </TabsContent>

          {/* ============ Removals ============ */}
          <TabsContent value="removals" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Removal directives</CardTitle>
                <CardDescription>
                  Which <code className="font-mono text-xs">SecRuleRemoveById</code> /
                  <code className="ml-1 font-mono text-xs">SecRuleRemoveByTag</code>{' '}
                  directives target a given rule or tag. A rule ID need not exist in this
                  configuration — removals often reference rules that were never loaded.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <form
                  className="flex flex-col gap-2 sm:flex-row"
                  onSubmit={(e) => {
                    e.preventDefault()
                    setAppliedRemoval({ kind: removalKind, value: removalInput })
                  }}
                >
                  <div className="flex gap-1">
                    <Button
                      type="button"
                      variant={removalKind === 'rule' ? 'default' : 'outline'}
                      onClick={() => setRemovalKind('rule')}
                    >
                      By rule ID
                    </Button>
                    <Button
                      type="button"
                      variant={removalKind === 'tag' ? 'default' : 'outline'}
                      onClick={() => setRemovalKind('tag')}
                    >
                      By tag
                    </Button>
                  </div>
                  <Input
                    value={removalInput}
                    onChange={(e) => setRemovalInput(e.target.value)}
                    placeholder={removalKind === 'rule' ? 'e.g. 2000901' : 'e.g. output'}
                    className="font-mono"
                  />
                  <Button type="submit" disabled={!removalInput || removals.isFetching}>
                    <Search className="mr-2 h-4 w-4" />
                    Search
                  </Button>
                </form>
              </CardContent>
            </Card>

            {removals.isLoading ? (
              <LoadingSpinner />
            ) : removals.data ? (
              <Card>
                <CardContent className="p-4">
                  {removals.data.total_count === 0 ? (
                    <EmptyState
                      icon={Scissors}
                      title="Nothing removes this"
                      description={
                        removalKind === 'tag'
                          ? 'Note that some tag-removal links can be missing — the parser resolves them at write time.'
                          : undefined
                      }
                    />
                  ) : (
                    <DirectiveTable
                      directives={removals.data.directives}
                      onSelect={(d) => searchByNodeId(d.node_id)}
                      onTagClick={searchByTag}
                      onRuleIdClick={searchByRuleId}
                    />
                  )}
                </CardContent>
              </Card>
            ) : (
              <EmptyState icon={Scissors} title="Search for a removed rule or tag" />
            )}
          </TabsContent>
        </Tabs>
      )}
    </div>
  )
}

function SymbolUsage({
  title,
  description,
  data,
  loading,
  onSelect,
}: {
  title: string
  description: string
  data?: DirectiveListResponse
  loading: boolean
  onSelect: (d: DirectiveResponse) => void
}) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          {title}
          {data && <Badge variant="muted">{data.total_count}</Badge>}
        </CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent>
        {loading ? (
          <LoadingSpinner />
        ) : !data || data.directives.length === 0 ? (
          <p className="py-4 text-center text-sm text-muted-foreground">None.</p>
        ) : (
          <div className="max-h-72 overflow-y-auto">
            <DirectiveTable directives={data.directives} onSelect={onSelect} />
          </div>
        )}
      </CardContent>
    </Card>
  )
}
