// Auth types
export interface User {
  username: string
  email?: string | null
  full_name?: string | null
  disabled?: boolean | null
}

export interface AuthResponse {
  access_token: string
  token_type: string
}

// Chat types
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

// Config types
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

// Node and Directive types
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
