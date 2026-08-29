'use client'

import { errorMessage } from '@/lib/errors'
import { Markdown } from '@/components/ui/markdown'
import { useState, useRef, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { streamMessage, type ToolActivity } from '@/lib/chatbot'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { LoadingSpinner } from '@/components/ui/loading-spinner'
import { 
  Send, 
  Plus, 
  Trash2, 
  Edit2,
  MessageSquare,
  Bot,
  User as UserIcon,
  Wrench,
  Check,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { ConversationResponse, MessageResponse, ConversationHistoryResponse } from '@/types'
import { formatRelativeTime } from '@/lib/utils'
import { useConfigStore } from '@/stores/config'

export default function ChatbotPage() {
  const [currentThreadId, setCurrentThreadId] = useState<string | null>(null)
  const [messageInput, setMessageInput] = useState('')
  const [messages, setMessages] = useState<MessageResponse[]>([])
  const [isTyping, setIsTyping] = useState(false)
  const [editThreadId, setEditThreadId] = useState<string | null>(null)
  const [editThreadTitle, setEditThreadTitle] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const queryClient = useQueryClient()
  const { selectedConfig } = useConfigStore()

  const { data: conversations, isLoading: conversationsLoading } = useQuery({
    queryKey: ['conversations'],
    queryFn: async () => {
      const response = await api.get<ConversationResponse[]>('/chatbot/conversations')
      return response.data
    },
  })

  const { data: conversationHistory } = useQuery({
    queryKey: ['conversation-history', currentThreadId],
    queryFn: async () => {
      if (!currentThreadId) return null
      const response = await api.get<ConversationHistoryResponse>(
        `/chatbot/conversations/${currentThreadId}/history`
      )
      return response.data
    },
    enabled: !!currentThreadId,
  })

  useEffect(() => {
    if (conversationHistory) {
      setMessages(conversationHistory.messages)
    }
  }, [conversationHistory])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Which configuration a NEW conversation will analyse. Seeded from the active one for
  // convenience, but explicit: the conversation keeps whatever is chosen here for life, so
  // reopening it later still answers about that configuration rather than silently
  // following whatever is active at the time.
  const [newConfigId, setNewConfigId] = useState<number | null>(null)
  const [pickerOpen, setPickerOpen] = useState(false)

  const configs = useQuery({
    queryKey: ['configs'],
    queryFn: async () => {
      const res = await api.get('/configurations')
      const list = Array.isArray(res.data) ? res.data : res.data?.configurations ?? []
      return list.filter((c: any) => c.parsing_status === 'parsed')
    },
  })

  // The open conversation, so the UI can state ITS configuration rather than the active one.
  const currentConversation = (conversations ?? []).find(
    (c: any) => c.thread_id === currentThreadId,
  )

  const createConversationMutation = useMutation({
    mutationFn: async (configurationId: number) => {
      const response = await api.post<ConversationResponse>('/chatbot/conversations', {
        title: null,
        configuration_id: configurationId,
      })
      return response.data
    },
    onSuccess: (data) => {
      setCurrentThreadId(data.thread_id)
      setMessages([])
      queryClient.invalidateQueries({ queryKey: ['conversations'] })
      toast.success('New conversation started!')
    },
    onError: (error: any) => {
      toast.error(errorMessage(error, 'Failed to create conversation'))
    },
  })

  // The turn currently streaming: prose as it arrives, and each tool as it runs. Held
  // separately from `messages` so a half-finished turn never lands in the history.
  const [streamingText, setStreamingText] = useState('')
  const [liveTools, setLiveTools] = useState<ToolActivity[]>([])

  const runStream = async (threadId: string, message: string) => {
    setIsTyping(true)
    setStreamingText('')
    setLiveTools([])
    try {
      await streamMessage(threadId, message, (event) => {
        if (event.type === 'token') {
          setStreamingText((t) => t + event.content)
        } else if (event.type === 'tool_start') {
          setLiveTools((ts) => [
            ...ts,
            { id: event.id, name: event.name, arguments: event.arguments, running: true },
          ])
        } else if (event.type === 'tool_end') {
          // Match on the call id where there is one — the same tool can run twice in a turn.
          setLiveTools((ts) =>
            ts.map((t) =>
              (event.id ? t.id === event.id : t.name === event.name) && t.running
                ? { ...t, running: false, result: event.result }
                : t,
            ),
          )
        } else if (event.type === 'error') {
          toast.error(event.message)
        }
      })
    } catch (e: any) {
      toast.error(e?.message || 'Streaming failed')
    } finally {
      setIsTyping(false)
      setStreamingText('')
      setLiveTools([])
      // The turn is persisted server-side by the checkpointer; refetch so the finished
      // message (with its tools) becomes part of the history.
      queryClient.invalidateQueries({ queryKey: ['conversation-history', threadId] })
      queryClient.invalidateQueries({ queryKey: ['conversations'] })
    }
  }

  const deleteConversationMutation = useMutation({
    mutationFn: async (threadId: string) => {
      const response = await api.delete(`/chatbot/conversations/${threadId}`)
      return response.data
    },
    onSuccess: (_, threadId) => {
      toast.success('Conversation deleted!')
      if (currentThreadId === threadId) {
        setCurrentThreadId(null)
        setMessages([])
      }
      queryClient.invalidateQueries({ queryKey: ['conversations'] })
    },
    onError: (error: any) => {
      toast.error(errorMessage(error, 'Failed to delete conversation'))
    },
  })

  const renameConversationMutation = useMutation({
    mutationFn: async ({ threadId, title }: { threadId: string, title: string }) => {
      const response = await api.put<ConversationResponse>(
        `/chatbot/conversations/${threadId}/title`,
        { title }
      )
      return response.data
    },
    onSuccess: () => {
      toast.success('Conversation renamed!')
      queryClient.invalidateQueries({ queryKey: ['conversations'] })
      setEditThreadId(null)
    },
    onError: (error: any) => {
      toast.error(errorMessage(error, 'Failed to rename conversation'))
      setEditThreadId(null)   // otherwise the row stays stuck in edit mode
    },
  })

  /**
   * Finish a rename, or abandon it.
   *
   * An empty or unchanged title is a cancel, not a request: the API requires at least one
   * character, so submitting "" returned a 422 whose `detail` is an array of objects —
   * which the old error toast rendered as a React child and crashed the page. Not sending
   * it is the real fix; errorMessage() stops that shape crashing anywhere else.
   */
  const commitRename = (conversation: any) => {
    const title = editThreadTitle.trim()
    if (!title || title === (conversation.title ?? '')) {
      setEditThreadId(null)
      return
    }
    renameConversationMutation.mutate({ threadId: conversation.thread_id, title })
  }

  const handleSendMessage = async () => {
    const text = messageInput.trim()
    if (!text) return

    // Sending with no conversation open needs a configuration first — it is a deliberate
    // choice, not something to infer from whatever is active.
    if (!currentThreadId) {
      setNewConfigId(selectedConfig?.id ?? null)
      setPickerOpen(true)
      return
    }

    setMessages((prev) => [
      ...prev,
      { role: 'user', content: text, timestamp: new Date().toISOString(), tools_used: null },
    ])
    setMessageInput('')
    await runStream(currentThreadId, text)
  }


  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  // Full-bleed: the negative margin cancels the dashboard layout's p-4/lg:p-6 so the chat
  // reaches the sidebar and the window edges, then p-2 puts a thin gutter back. The old
  // h-[calc(100vh-8rem)] reserved 128px for a page header this route does not render, which
  // is where the large dead strip under the panel came from.
  return (
    <div className="flex h-screen gap-3 -m-4 lg:-m-6 p-2">
      <Card className="w-80 flex flex-col bg-gradient-to-br from-purple-50 to-blue-50 border-purple-200">
        <div className="p-4 border-b flex items-center justify-between">
          <h2 className="font-semibold flex items-center gap-2">
            <MessageSquare className="h-5 w-5" />
            Conversations
          </h2>
          <Button size="sm" onClick={() => { setNewConfigId(selectedConfig?.id ?? null); setPickerOpen(true) }} disabled={createConversationMutation.isPending} className="bg-blue-300 hover:bg-white/30 text-purple-700 border-purple-700">
            <Plus className="h-4 w-4" />
          </Button>
        </div>
        {/* overflow-x-hidden: the selected item uses scale-105, and a transform still counts
              toward scrollWidth, so it raised an 8px horizontal scrollbar on the list. */}
        <div className="flex-1 overflow-y-auto overflow-x-hidden p-2">
          {conversationsLoading ? (
            <LoadingSpinner />
          ) : conversations?.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-8">No conversations yet</p>
          ) : (
            <div className="space-y-1">
              {conversations?.map((conversation) => (
                <div
                  key={conversation.thread_id}
                  className={`p-3 rounded-lg cursor-pointer transition-all duration-200 ${
                    currentThreadId === conversation.thread_id 
                      ? 'bg-gradient-to-r from-purple-500 to-blue-500 text-white shadow-lg scale-105' 
                      : 'hover:bg-white/60 hover:shadow-md hover:scale-102'
                  }`}
                  onClick={() => setCurrentThreadId(conversation.thread_id)}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      {editThreadId === conversation.thread_id ? (
                        <Input
                          value={editThreadTitle}
                          onChange={(e) => setEditThreadTitle(e.target.value)}
                          onBlur={() => commitRename(conversation)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') commitRename(conversation)
                            if (e.key === 'Escape') setEditThreadId(null)
                          }}
                          className="h-6 text-sm"
                          autoFocus
                        />
                      ) : (
                        <>
                          <p className="text-sm font-medium truncate">{conversation.title || 'Untitled Conversation'}</p>
                          <p className="text-xs opacity-70">{formatRelativeTime(conversation.updated_at)}</p>
                          {conversation.configuration_name && (
                            <p className="text-xs opacity-60 truncate mt-1">Config: {conversation.configuration_name}</p>
                          )}
                        </>
                      )}
                    </div>
                    <div className="flex gap-1">
                      <Button size="sm" variant="ghost" className="h-6 w-6 p-0" onClick={(e) => { e.stopPropagation(); setEditThreadId(conversation.thread_id); setEditThreadTitle(conversation.title || '') }}>
                        <Edit2 className="h-3 w-3" />
                      </Button>
                      <Button size="sm" variant="ghost" className="h-6 w-6 p-0" onClick={(e) => { e.stopPropagation(); if (confirm('Delete this conversation?')) deleteConversationMutation.mutate(conversation.thread_id) }}>
                        <Trash2 className="h-3 w-3" />
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </Card>

      {/* min-w-0 here is what actually stops the horizontal blowout: this Card is a flex
          item, and a flex item refuses to shrink below its content unless min-width is 0.
          Without it a wide tool-call <pre> widened the Card itself, so the constraints on
          the bubble inside never got a chance to apply. */}
      <Card className="flex-1 min-w-0 flex flex-col bg-gradient-to-br from-slate-50 to-gray-100 border-slate-200">
        {!currentThreadId ? (
          <div className="flex-1 flex items-center justify-center bg-gradient-to-br from-purple-50 via-blue-50 to-indigo-50">
            <div className="text-center space-y-4">
              <div className="relative">
                <div className="absolute inset-0 bg-gradient-to-r from-purple-500 to-blue-500 blur-xl opacity-30 animate-pulse"></div>
                <Bot className="h-16 w-16 mx-auto text-purple-600 relative z-10" />
              </div>
              <div>
                <h3 className="text-lg font-semibold bg-gradient-to-r from-purple-600 to-blue-600 bg-clip-text text-transparent">Welcome to WAF-GUARD Assistant</h3>
                <p className="text-sm text-muted-foreground">Start a new conversation to get help with your WAF configuration</p>
              </div>
              <Button onClick={() => { setNewConfigId(selectedConfig?.id ?? null); setPickerOpen(true) }} className="bg-gradient-to-r from-purple-500 to-blue-500 hover:from-purple-600 hover:to-blue-600 text-white shadow-lg">
                <Plus className="h-4 w-4 mr-2" />
                Start New Conversation
              </Button>
            </div>
          </div>
        ) : (
          <>
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {messages.map((message, index) => (
                <div key={index} className={`flex gap-3 min-w-0 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  {message.role === 'assistant' && (
                    <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center flex-shrink-0 shadow-lg">
                      <Bot className="h-5 w-5 text-white" />
                    </div>
                  )}
                  {/* min-w-0: a flex item defaults to min-width:auto, so a wide <pre> in an
                      expanded tool call pushed the bubble past max-w-[70%] and stretched the
                      whole panel off-screen. With min-width:0 the inner overflow-x-auto
                      finally engages and the long line scrolls inside the bubble instead. */}
                  <div className={`max-w-[85%] min-w-0 rounded-lg p-3 shadow-md ${
                    message.role === 'user' 
                      ? 'bg-gradient-to-br from-blue-500 to-indigo-500 text-white' 
                      : 'bg-white border-2 border-purple-200'
                  }`}>
                    {/* The assistant writes markdown; rendering it as preformatted text
                        showed literal ** and | . User messages stay plain — echoing a
                        user's own text through a renderer buys nothing. */}
                    {message.role === 'user' ? (
                      <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                    ) : (
                      <Markdown content={message.content} />
                    )}
                    {message.tools_used && message.tools_used.length > 0 && (
                      <div className="mt-2 pt-2 border-t border-border/50">
                        <p className="text-xs opacity-70 flex items-center gap-1 mb-1">
                          <Wrench className="h-3 w-3" />Tools used:
                        </p>
                        {message.tools_used.map((tool, idx) => (
                          <details key={idx} className="text-xs opacity-70 mt-1">
                            <summary className="cursor-pointer font-mono">{tool.name}</summary>
                            <pre className="mt-1 p-1 bg-black/10 rounded max-w-full max-h-40 overflow-y-auto whitespace-pre-wrap break-all">{JSON.stringify(tool.arguments, null, 2)}</pre>
                            {/* The result, which this never used to show — a tool call you
                                cannot see the output of is not much of an audit trail. */}
                            {tool.result != null && (
                              <pre className="mt-1 max-h-48 max-w-full overflow-y-auto p-1 bg-black/5 rounded whitespace-pre-wrap break-all">
                                {typeof tool.result === 'string' ? tool.result : JSON.stringify(tool.result, null, 2)}
                              </pre>
                            )}
                          </details>
                        ))}
                      </div>
                    )}
                    <p className="text-xs opacity-50 mt-1">{new Date(message.timestamp).toLocaleTimeString()}</p>
                  </div>
                  {message.role === 'user' && (
                    <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-cyan-500 flex items-center justify-center flex-shrink-0 shadow-lg">
                      <UserIcon className="h-5 w-5 text-white" />
                    </div>
                  )}
                </div>
              ))}
              {/* The turn in flight: tools appear as they are called, each showing its
                  arguments and then its result, with the prose streaming underneath. The
                  old version showed only bouncing dots, then tool NAMES after the fact and
                  never their output. */}
              {isTyping && (
                <div className="flex gap-3">
                  <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center shadow-lg flex-shrink-0">
                    <Bot className="h-5 w-5 text-white" />
                  </div>
                  <div className="bg-white border-2 border-purple-200 rounded-lg p-3 shadow-md max-w-[85%] min-w-0 space-y-2">
                    {liveTools.map((t, i) => (
                      <div key={t.id ?? `${t.name}-${i}`} className="rounded border border-purple-100 bg-purple-50/60 p-2">
                        <div className="flex items-center gap-2 text-xs font-medium text-purple-900">
                          {t.running ? (
                            <span className="h-3 w-3 shrink-0 animate-spin rounded-full border-2 border-purple-400 border-t-transparent" />
                          ) : (
                            <Check className="h-3 w-3 shrink-0 text-green-600" />
                          )}
                          <span className="font-mono">{t.name}</span>
                          {t.running && <span className="opacity-60">running…</span>}
                        </div>
                        <pre className="mt-1 max-w-full text-[11px] text-purple-900/80 whitespace-pre-wrap break-all">
                          {JSON.stringify(t.arguments, null, 0)}
                        </pre>
                        {t.result && (
                          <details className="mt-1 text-[11px]">
                            <summary className="cursor-pointer opacity-70">result</summary>
                            <pre className="mt-1 max-h-40 max-w-full overflow-y-auto rounded bg-black/5 p-1 whitespace-pre-wrap break-all">{t.result}</pre>
                          </details>
                        )}
                      </div>
                    ))}
                    {streamingText ? (
                      <Markdown content={streamingText} />
                    ) : liveTools.length === 0 ? (
                      <div className="flex gap-1">
                        <div className="w-2 h-2 rounded-full bg-purple-500 animate-bounce" />
                        <div className="w-2 h-2 rounded-full bg-blue-500 animate-bounce delay-100" />
                        <div className="w-2 h-2 rounded-full bg-indigo-500 animate-bounce delay-200" />
                      </div>
                    ) : null}
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            <div className="p-4 border-t border-purple-200 bg-gradient-to-r from-purple-50 to-blue-50">
              <div className="flex gap-2">
                <Input 
                  value={messageInput} 
                  onChange={(e) => setMessageInput(e.target.value)} 
                  onKeyPress={handleKeyPress} 
                  placeholder="Type your message..." 
                  disabled={isTyping} 
                  className="border-purple-200 focus:ring-purple-500 focus:border-purple-500"
                />
                <Button 
                  onClick={handleSendMessage} 
                  disabled={isTyping || !messageInput.trim()}
                  className="bg-gradient-to-r from-purple-500 to-blue-500 hover:from-purple-600 hover:to-blue-600 text-white shadow-lg"
                >
                  <Send className="h-4 w-4" />
                </Button>
              </div>
              {/* The CONVERSATION's configuration, not the sidebar's active one. Showing
                  the active config here was actively misleading: a thread pinned to
                  "Full conf" would claim to be using "Full conf v2". */}
              {currentConversation && (
                <p className="text-xs text-purple-600 mt-2 flex items-center gap-1">
                  <span className="inline-block w-2 h-2 bg-green-500 rounded-full"></span>
                  This conversation analyses{' '}
                  <span className="font-semibold">
                    {currentConversation.configuration_name ?? `configuration ${currentConversation.configuration_id}`}
                  </span>
                  {selectedConfig && currentConversation.configuration_id !== selectedConfig.id && (
                    <span className="text-muted-foreground">
                      (your active configuration is {selectedConfig.name})
                    </span>
                  )}
                </p>
              )}
            </div>
          </>
        )}
      </Card>

      {/* Choosing the configuration is a deliberate step, not an inherited default: the
          conversation keeps it for life, which is what stops an old thread from silently
          answering about whatever happens to be active later. */}
      {pickerOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
             onClick={() => setPickerOpen(false)}>
          <div className="w-full max-w-md rounded-lg bg-white p-5 shadow-xl"
               onClick={(e) => e.stopPropagation()}>
            <h3 className="text-lg font-semibold">New conversation</h3>
            <p className="mt-1 text-sm text-muted-foreground">
              Which configuration should it analyse? This is fixed for the life of the
              conversation.
            </p>
            <div className="mt-4 max-h-64 space-y-1 overflow-y-auto">
              {(configs.data ?? []).length === 0 && (
                <p className="py-4 text-center text-sm text-muted-foreground">
                  No parsed configuration available.
                </p>
              )}
              {(configs.data ?? []).map((c: any) => (
                <button
                  key={c.id}
                  onClick={() => setNewConfigId(c.id)}
                  className={
                    'flex w-full items-center justify-between rounded-md border px-3 py-2 text-left text-sm hover:bg-muted ' +
                    (newConfigId === c.id ? 'border-purple-500 bg-purple-50' : '')
                  }
                >
                  <span className="font-medium">{c.name}</span>
                  {selectedConfig?.id === c.id && (
                    <span className="text-xs text-muted-foreground">currently active</span>
                  )}
                </button>
              ))}
            </div>
            <div className="mt-5 flex justify-end gap-2">
              <Button variant="ghost" onClick={() => setPickerOpen(false)}>Cancel</Button>
              <Button
                disabled={!newConfigId || createConversationMutation.isPending}
                onClick={() => {
                  if (!newConfigId) return
                  createConversationMutation.mutate(newConfigId)
                  setPickerOpen(false)
                }}
              >
                Start
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
