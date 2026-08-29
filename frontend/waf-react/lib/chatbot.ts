/**
 * Typed client for the chatbot API.
 *
 * A conversation is pinned to one configuration when it is created and keeps it for life,
 * so revisiting an old thread still answers about the configuration it was started for.
 * That is why `configuration_id` is required here and is NOT sent per message.
 */
import { api } from './api'
import type { ConversationResponse, MessageResponse } from '@/types'

/** One event from the streaming endpoint. */
export type ChatEvent =
  | { type: 'token'; content: string }
  | { type: 'tool_start'; name: string; arguments: Record<string, unknown>; id?: string }
  | { type: 'tool_end'; name: string; id?: string; result: string }
  | { type: 'done' }
  | { type: 'error'; message: string }

/** A tool call as the UI tracks it while the turn is in flight. */
export interface ToolActivity {
  id?: string
  name: string
  arguments: Record<string, unknown>
  result?: string
  running: boolean
}

export async function createConversation(configurationId: number, title?: string | null) {
  const { data } = await api.post<ConversationResponse>('/chatbot/conversations', {
    title: title ?? null,
    configuration_id: configurationId,
  })
  return data
}

export async function listConversations() {
  const { data } = await api.get<ConversationResponse[]>('/chatbot/conversations')
  return Array.isArray(data) ? data : []
}

export async function deleteConversation(threadId: string) {
  await api.delete(`/chatbot/conversations/${threadId}`)
}

export async function renameConversation(threadId: string, title: string) {
  const { data } = await api.patch<ConversationResponse>(
    `/chatbot/conversations/${threadId}/title`,
    { title },
  )
  return data
}

export async function getHistory(threadId: string) {
  const { data } = await api.get(`/chatbot/conversations/${threadId}/history`)
  return data
}

/**
 * Send a message and consume the SSE stream, calling `onEvent` for each event.
 *
 * Uses fetch + a ReadableStream reader rather than EventSource: EventSource cannot issue a
 * POST and cannot set an Authorization header, and this endpoint needs both.
 */
export async function streamMessage(
  threadId: string,
  message: string,
  onEvent: (event: ChatEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const base = api.defaults.baseURL ?? ''
  const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null

  const res = await fetch(`${base}/chatbot/conversations/${threadId}/messages/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ message, graph_name: 'ui_graph_v1', stream: true }),
    signal,
  })

  if (!res.ok || !res.body) {
    throw new Error(`Stream failed: ${res.status} ${res.statusText}`)
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    // SSE frames are separated by a blank line. Keep the trailing partial frame in the
    // buffer — a chunk boundary lands mid-frame often enough to matter.
    const frames = buffer.split('\n\n')
    buffer = frames.pop() ?? ''

    for (const frame of frames) {
      const line = frame.split('\n').find((l) => l.startsWith('data: '))
      if (!line) continue
      try {
        onEvent(JSON.parse(line.slice(6)) as ChatEvent)
      } catch {
        // A frame we cannot parse is not worth killing the stream over.
        console.warn('Unparseable SSE frame', line)
      }
    }
  }
}
