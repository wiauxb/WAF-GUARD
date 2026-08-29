// ==================== Auth Types ====================
export interface UserInfo {
  id: number
  username: string
  is_admin: boolean
  active_configuration_id: number | null
  created_at: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  user: UserInfo
  expires_in: number
}

export interface RegisterRequest {
  username: string
  password: string
  password_confirm: string
}

export interface LoginRequest {
  username: string
  password: string
}

export interface PasswordChangeRequest {
  old_password: string
  new_password: string
}

export interface SetActiveConfigRequest {
  configuration_id: number
}

// Legacy type for backward compatibility
export interface User {
  id?: number
  username: string
  email?: string | null
  full_name?: string | null
  disabled?: boolean | null
}

export interface AuthResponse {
  access_token: string
  token_type: string
}

// ==================== Chatbot Types ====================
export interface ConversationResponse {
  id: number
  thread_id: string
  user_id: number
  title: string | null
  configuration_id: number | null
  graph_type: string
  created_at: string
  updated_at: string
  configuration_name: string | null
}

export interface ToolCallInfo {
  name: string
  arguments: any
  result: any
}

export interface MessageResponse {
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  tools_used: ToolCallInfo[] | null
}

export interface ConversationHistoryResponse {
  conversation: ConversationResponse
  messages: MessageResponse[]
  total_messages: number
}

export interface ConversationCreateRequest {
  title?: string | null
  configuration_id?: number | null
}

export interface SendMessageRequest {
  message: string
  graph_type?: string
  stream?: boolean
}

export interface ConversationRenameRequest {
  title: string
}

// Legacy types for backward compatibility
export interface Message {
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp?: string
}

export interface Thread {
  id: string
  title?: string
  created_at?: string
  updated_at: string
  users_id?: number
}

export interface ChatConfig {
  thread_id: string
  [key: string]: any
}

// ==================== Configuration Types ====================
export interface ConfigurationResponse {
  id: number
  name: string
  description: string | null
  file_path: string
  dump_path: string | null
  file_hash: string | null
  file_size: number | null
  dump_size: number | null
  parsing_status: 'not_parsed' | 'parsing' | 'parsed' | 'error'
  parsing_error: string | null
  created_by_user_id: number | null
  created_at: string
  updated_at: string
  parsed_at: string | null
}

export interface ConfigurationUploadRequest {
  name: string
  description?: string | null
  waf_url: string
}

export interface ConfigurationUpdateRequest {
  name?: string | null
  description?: string | null
}

export interface ParseConfigurationRequest {
  force_reparse?: boolean
}

export interface ParseResponse {
  configuration_id: number
  parsing_status: string
  parsing_error: string | null
  created_at: string
  updated_at: string
  parsed_at: string | null
}

export interface ParseStatusResponse {
  configuration_id: number
  parsing_status: string
  parsing_error: string | null
}

// Legacy type for backward compatibility
export interface Config {
  id: number
  name: string
  description: string | null
  file_path: string
  file_hash: string | null
  file_size: number | null
  parsing_status: 'not_parsed' | 'parsing' | 'parsed' | 'error'
  parsing_error: string | null
  created_by_user_id: number | null
  created_at: string
  updated_at: string
  parsed_at: string | null
}

export interface SelectedConfig {
  id: number
  config_id: number
}

export interface AnalysisTask {
  task_id: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  progress: number
  progress_endpoint?: string
}

// ==================== File Tree Types ====================
export interface ConfigTreeNode {
  name: string
  type: 'file' | 'directory'
  size?: number | null
}

export interface ConfigTreeResponse {
  is_file: boolean
  path: string
  name: string
  children?: ConfigTreeNode[] | null
  content?: string | null
  size?: number | null
}

export interface FileUpdateRequest {
  content: string
}

// ==================== Log Analysis Types ====================
export interface LogClassificationResponse {
  session_id: string
  filename: string
  total_logs: number
  categories: { [category: string]: number }
  columns: string[]
}

export interface LogCategoryResponse {
  category: string
  count: number
  percentage: number
  log_indices?: number[] | null
}

export interface LogFilter {
  start_time?: string | null
  end_time?: string | null
  columns?: Array<{
    name: string
    value: any
    type: 'exact' | 'contains' | 'greater_than' | 'less_than'
  }> | null
}

export interface FilteredLogsResponse {
  session_id: string
  total_logs: number
  filtered_logs: number
  categories: LogCategoryResponse[]
  columns: string[]
  applied_filters: LogFilter
  logs?: Array<{ [key: string]: any }> | null
}

export interface LogEntryResponse {
  id: string
  A_transaction_id: string
  A_remote_address: string
  A_remote_port: number
  A_local_address: string
  A_local_port: number
  B_http_request: string
  B_request_url: string
  B_request_protocol: string
  B_host: string
  B_user_agent: string
  F_response_protocol: string
  F_response_status_code: number
  F_response_status: string
  F_x_unique_id?: string
  F_strict_transport_security?: string
  F_content_length?: string
  F_content_type?: string
  H_messages: string[] | "empty"
  H_action?: string
  H_webapp_info?: string
  H_sensor_id?: string
  H_engine_mode?: string
  Z_categories: string
  Z_blocked: string
  time: string
  payloads: string
  formatted_log: string
  msgtags: string[]
  new_categories: {
    labels: string[]
    probabilities: Array<Record<string, number>>
  }
  // Legacy fields for backward compatibility
  transaction_id?: string
  timestamp?: string
  severity?: string
  category?: string
  message?: string
  source_ip?: string | null
  destination_ip?: string | null
  rule_id?: string | null
  [key: string]: any
}

export interface LogAnalysisSessionResponse {
  id: number
  session_id: string
  user_id: number
  filename: string
  configuration_id?: number | null
  total_logs: number
  created_at: string
  file_size: number
  columns: string[]
  categories?: { [category: string]: number } | null
}

export interface LogDetailResponse {
  session_id: string
  transaction_id: string
  log: { [key: string]: any }
}

export interface CategoryDetailsResponse {
  session_id: string
  category: string
  total_count: number
  logs: LogEntryResponse[]
}

// ==================== Analysis Types ====================
// Mirrors backend/src/services/analysis/schemas.py exactly.
//
// TWO IDENTIFIER SPACES, never conflated and never named bare `id`:
//   node_id  - assigned by the parser, on EVERY directive, unique per configuration
//   rule_id  - the ModSecurity `id:NNN`, only where declared, one-to-many
//              (a chained SecRule spans several directives sharing one rule_id)
// Their numeric ranges overlap, so which one you mean must always be explicit.

export interface DirectiveResponse {
  node_id: number
  type: string                 // lowercased directive name == the Neo4j label
  args: string
  location: string | null
  /**
   * Which container produced `location`: 'Location' (a literal path) or 'LocationMatch'
   * (a regex). '' / null when the directive is outside any location block.
   */
  location_kind: string | null
  virtual_host: string | null
  if_level: number
  conditions: string[]
  phase: number | null
  rule_id: number | null       // ModSecurity id:NNN — NOT the node_id
  tags: string[]
  msg: string | null
  constants: string[]
  variables: string[]
  // No `context`: provenance comes from getNodeMetadata(node_id) instead.
}

export interface Paginated {
  total_count: number          // FULL match count, not the page size
  limit: number
  offset: number
}

export interface DirectiveListResponse extends Paginated {
  configuration_id: number
  directives: DirectiveResponse[]
}

export interface RemoverEntry {
  criterion_type: string       // "Id" (a rule_id) | "Regex" (a tag pattern)
  criterion_value: number | string
  directive: DirectiveResponse // the SecRuleRemoveBy* that did it
}

export interface RemoverListResponse extends Paginated {
  configuration_id: number
  node_id: number              // the victim — a parser node_id
  removers: RemoverEntry[]
}

export interface SymbolMatch {
  name: string
  value: string | null
  labels: string[]             // Constant | Variable | Collection
}

export interface SymbolSearchResponse extends Paginated {
  configuration_id: number
  query: string
  matches: SymbolMatch[]
}

export interface NodeMetadataEntry {
  macro_name: string           // "/" for the frame sitting directly in a file
  file_path: string
  line_number: number
}

export interface NodeMetadataResponse {
  configuration_id: number
  node_id: number
  frames: NodeMetadataEntry[]  // innermost call first, defining file last
}

export interface MacroTraceFrame {
  macro_name: string
  file_path: string
  line_number: number
  content: string              // the <Macro> body, or the `Use` line
}

export interface MacroTraceResponse {
  configuration_id: number
  node_id: number
  frames: MacroTraceFrame[]
  formatted: string            // pre-rendered text
}

// --- request bodies ---

export interface HttpRequestFilter {
  location: string             // regex
  host: string                 // regex
}

/** Columns the backend will order by. Closed set — anything else 422s. */
export type SortField = 'node_id' | 'type' | 'rule_id' | 'phase' | 'host' | 'location'
export type SortDir = 'asc' | 'desc'

/** Properties offering a searchable value list, for the filter comboboxes. */
export type ValueField = 'tag' | 'host' | 'location' | 'type' | 'phase' | 'msg'

/**
 * Combinable directive filter — the single query behind the Directives page.
 *
 * Criteria are AND-ed. Within one criterion the meaning follows the property:
 *   types / phases / rule_ids  — a directive has ONE of each, so a list means "any of"
 *   tags                       — a directive carries a LIST, so a list means "all of"
 *
 * An empty object is legal and returns the whole configuration.
 */
export interface DirectiveSearchQuery {
  types?: string[]
  phases?: number[]
  rule_ids?: number[]
  tags?: string[]
  /**
   * Exact host/location, any of — what the UI sends. The stored values keep the quotes the
   * dump used (`"*:80"`) and contain regex metacharacters, so the regex fields below cannot
   * express them. `""` is a real value: "outside any VirtualHost/Location block".
   */
  hosts?: string[]
  locations?: string[]
  node_id?: number | null
  host?: string | null           // regex — API only, not reachable from the UI
  location?: string | null       // regex — API only, not reachable from the UI
  args_contains?: string | null  // case-insensitive substring
  msgs?: string[]                // exact rule messages, any of
  msg_contains?: string | null   // case-insensitive substring — API only
  has_rule_id?: boolean | null   // null = don't care
  source?: SourceLocationQuery | null
  /**
   * Shorthand for `locations`: the server works out which `<Location>`/`<LocationMatch>`
   * blocks cover this path and filters on exactly those. Paste a URL from a log — scheme,
   * host, query and fragment are ignored.
   */
  url?: string | null
  sort_by?: SortField
  sort_dir?: SortDir
}

/**
 * A summary of the directives a filter set matches — the statistics panel.
 *
 * Every figure honours the WHOLE filter set, unlike the dropdown value lists which drop a
 * field's own chips so another value stays addable.
 */
export interface DirectiveStatsResponse {
  configuration_id: number
  total: number
  secrules: number
  with_rule_id: number
  in_location: number
  in_vhost: number
  distinct_tags: number
  distinct_locations: number
  /** Ordered 1..5 then null — phase is ORDINAL, so never re-sort this by count. */
  phases: FacetCount[]
  /** Top 8 plus an "Other" row, so these still sum to `total`. */
  types: FacetCount[]
  /** Top 8. NOT part-to-whole: a directive carries several tags, so these sum to MORE
   *  than `total` and must never be rendered as shares. */
  tags: FacetCount[]
  locations: FacetCount[]
}

export interface LocationMatchEntry {
  value: string                  // raw, as stored — usable directly as a `locations` filter
  kind: string                   // Location | LocationMatch
  count: number
}

export interface LocationWarning {
  value: string
  kind: string
  reason: string
}

/**
 * Which location containers cover a request path.
 *
 * Directives with NO location apply to every path, so they are excluded from `matches`
 * (they would be the same block on every URL) and reported as `no_location_count` instead.
 */
export interface UrlMatchResponse {
  configuration_id: number
  url: string                    // what was submitted
  path: string                   // the normalised path actually matched on
  matches: LocationMatchEntry[]  // commonest first
  total_directives: number
  no_location_count: number
  /**
   * Containers the backend judges unreachable. Computed and returned, but deliberately
   * NOT rendered: the analysis is subtle enough that showing it risks asserting something
   * wrong in front of an audience. Available via the API if it is ever wanted back.
   */
  warnings: LocationWarning[]
}

export interface FacetCount {
  value: string | number
  count: number
  /** Only the `location` list sets this: 'Location' | 'LocationMatch'. */
  kind?: string | null
}

/**
 * A searchable slice of one property's distinct values, commonest first.
 *
 * Never the whole set — the search runs server-side because the value count grows with the
 * configuration. `value` is raw: quotes included, and `""` for "outside any block".
 */
export interface FacetValuesResponse {
  configuration_id: number
  field: ValueField
  query: string
  values: FacetCount[]
}

export interface ConstantQuery {
  name: string
  // omitted/null matches the node with NO value set — not "any value"
  value?: string | null
}

export interface SourceLocationQuery {
  file_path: string
  line_number: number
}

export interface PageParams {
  limit?: number
  offset?: number
}

// ==================== Common Response Types ====================
export interface SuccessResponse {
  success: boolean
  message: string
}

export interface ErrorResponse {
  detail: string
  error_code?: string | null
  field_errors?: { [key: string]: string[] } | null
}

// ==================== Legacy/Compatibility Types ====================
// Legacy type for compatibility (can be removed after full migration)
export interface ConfigContent {
  filename: string
  is_folder: boolean
  file_content?: string | null
}

