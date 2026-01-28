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

// ==================== Node and Directive Types ====================
export interface Node {
  node_id: number
  [key: string]: any
}

export interface Directive {
  node_id: number
  labels?: string[]
  [key: string]: any
}

export interface NodeMetadata {
  macro_name: string
  file_path: string
  line_number: number
}

// Cypher types
export interface CypherQuery {
  query: string
}

export interface CypherResult {
  html?: string
  df?: any[]
}

// File types
export interface ConfigTreeNode {
  name: string
  type: 'file' | 'directory'
  size?: number | null
}

export interface ConfigTreeResponse {
  is_file: boolean
  path: string
  children?: ConfigTreeNode[] | null  // For directories
  content?: string | null  // For files
  size?: number | null
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

export interface FileContext {
  file_path: string
  line_num: number
}

export interface ConstantQuery {
  var_name: string
  var_value?: string | null
}

export interface HttpRequest {
  host: string
  location: string
}

// Database types
export interface ExportResponse {
  status: string
  message?: string
}

export interface ImportResponse {
  status: string
  message?: string
}
