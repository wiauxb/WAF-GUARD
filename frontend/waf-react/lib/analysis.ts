/**
 * Typed client for the analysis API (/api/v1/analysis).
 *
 * `configuration_id` is never passed: the backend falls back to the caller's active
 * configuration, which is what the sidebar switcher sets via PUT /auth/me/active-config.
 * That keeps "which config am I looking at" in exactly one place.
 *
 * Two identifier spaces, never mixed — see types/index.ts:
 *   nodeId  - parser id, on every directive
 *   ruleId  - ModSecurity id:NNN, only where declared, one-to-many
 */
import { api } from './api'
import type {
  ConstantQuery,
  DirectiveListResponse,
  HttpRequestFilter,
  MacroTraceResponse,
  NodeMetadataResponse,
  PageParams,
  RemoverListResponse,
  SourceLocationQuery,
  SymbolSearchResponse,
} from '@/types'

export const DEFAULT_PAGE_SIZE = 50

/** Backend caps limit at 1000; keep the client honest so it 422s less often. */
export const MAX_PAGE_SIZE = 1000

function pageParams({ limit = DEFAULT_PAGE_SIZE, offset = 0 }: PageParams = {}) {
  return { limit: Math.min(limit, MAX_PAGE_SIZE), offset }
}

// ==================== Directive lookup ====================

/** By PARSER node_id. */
export async function getDirectiveByNodeId(nodeId: number, page?: PageParams) {
  const { data } = await api.get<DirectiveListResponse>(
    `/analysis/directives/${nodeId}`,
    { params: pageParams(page) },
  )
  return data
}

/** By MODSECURITY rule id. Returns several rows for a chained rule. */
export async function getDirectivesByRuleId(ruleId: number, page?: PageParams) {
  const { data } = await api.get<DirectiveListResponse>(
    `/analysis/directives/by-rule-id/${ruleId}`,
    { params: pageParams(page) },
  )
  return data
}

export async function getDirectivesByTag(tag: string, page?: PageParams) {
  const { data } = await api.get<DirectiveListResponse>(
    `/analysis/directives/by-tag/${encodeURIComponent(tag)}`,
    { params: pageParams(page) },
  )
  return data
}

/** Directives applying to a host/location, in execution order. Both are regexes. */
export async function filterDirectives(filter: HttpRequestFilter, page?: PageParams) {
  const { data } = await api.post<DirectiveListResponse>(
    `/analysis/directives/filter`,
    filter,
    { params: pageParams(page) },
  )
  return data
}

// ==================== Removal analysis ====================

/** What removed this directive. Takes a PARSER node_id. */
export async function getRemoversOfNode(nodeId: number, page?: PageParams) {
  const { data } = await api.get<RemoverListResponse>(
    `/analysis/directives/${nodeId}/removed-by`,
    { params: pageParams(page) },
  )
  return data
}

/** SecRuleRemoveById directives targeting a rule id (which need not exist here). */
export async function getRemovalsByRuleId(ruleId: number, page?: PageParams) {
  const { data } = await api.get<DirectiveListResponse>(
    `/analysis/removals/by-rule-id/${ruleId}`,
    { params: pageParams(page) },
  )
  return data
}

export async function getRemovalsByTag(tag: string, page?: PageParams) {
  const { data } = await api.get<DirectiveListResponse>(
    `/analysis/removals/by-tag/${encodeURIComponent(tag)}`,
    { params: pageParams(page) },
  )
  return data
}

// ==================== Symbols ====================

export async function searchSymbols(q: string, page?: PageParams) {
  const { data } = await api.get<SymbolSearchResponse>(`/analysis/symbols/search`, {
    params: { q, ...pageParams(page) },
  })
  return data
}

/** Directives that READ a constant/variable. value omitted = the node with no value. */
export async function getDirectivesUsingConstant(query: ConstantQuery, page?: PageParams) {
  const { data } = await api.post<DirectiveListResponse>(
    `/analysis/symbols/used-by`,
    query,
    { params: pageParams(page) },
  )
  return data
}

/** Directives that SET or DEFINE a constant/variable. */
export async function getDirectivesSettingConstant(query: ConstantQuery, page?: PageParams) {
  const { data } = await api.post<DirectiveListResponse>(
    `/analysis/symbols/set-by`,
    query,
    { params: pageParams(page) },
  )
  return data
}

// ==================== Source mapping ====================

/** The file/line chain for a directive. This is the provenance source of truth. */
export async function getNodeMetadata(nodeId: number) {
  const { data } = await api.get<NodeMetadataResponse>(
    `/analysis/nodes/${nodeId}/metadata`,
  )
  return data
}

/** Full macro call stack with the source text of each frame. */
export async function getMacroTrace(nodeId: number) {
  const { data } = await api.get<MacroTraceResponse>(
    `/analysis/nodes/${nodeId}/macro-trace`,
  )
  return data
}

/** Which directives a given configuration line produced. */
export async function getNodesAtSource(query: SourceLocationQuery, page?: PageParams) {
  const { data } = await api.post<DirectiveListResponse>(
    `/analysis/nodes/at-source`,
    query,
    { params: pageParams(page) },
  )
  return data
}

// ==================== Error helpers ====================

export interface AnalysisApiError {
  status: number
  detail: string
  /** 409 with an empty graph — the configuration needs (re-)parsing. */
  needsParse: boolean
  /** 400 — no configuration selected at all. */
  noConfig: boolean
}

/**
 * Normalise an axios error from the analysis API.
 *
 * The backend distinguishes: 400 (no configuration selected), 404 (unknown), and 409
 * for both "not parsed" and "marked parsed but its graph is empty". The UI shows an
 * explanatory panel with a parse action rather than a raw toast for the 409s.
 */
export function parseAnalysisError(error: any): AnalysisApiError {
  const status: number = error?.response?.status ?? 0
  const detail: string = error?.response?.data?.detail ?? error?.message ?? 'Request failed'
  return {
    status,
    detail,
    needsParse: status === 409,
    noConfig: status === 400,
  }
}
