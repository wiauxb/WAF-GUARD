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
  thread_id: string
  title?: string
  created_at: string
  updated_at: string
  users_id: number
}

export interface ChatConfig {
  thread_id: string
  [key: string]: any
}

// Config types
export interface Config {
  id: number
  nickname: string
  selected: boolean  // Whether this config is currently selected
  created_at: string
  parsed?: boolean   // Whether this config has been analyzed
}

// API response format (array format from backend)
export type ConfigArray = [number, string, boolean, string] // [id, nickname, selected, created_at]

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
