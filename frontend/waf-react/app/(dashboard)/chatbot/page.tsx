'use client'

import { useState, useRef, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
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
  Wrench
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

  const createConversationMutation = useMutation({
    mutationFn: async () => {
      const response = await api.post<ConversationResponse>('/chatbot/conversations', {
        title: null,
        configuration_id: selectedConfig?.id || null,
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
      toast.error(error.response?.data?.detail || 'Failed to create conversation')
    },
  })

  const sendMessageMutation = useMutation({
    mutationFn: async (message: string) => {
      const response = await api.post<MessageResponse>(
        `/chatbot/conversations/${currentThreadId}/messages`,
        {
          message,
          graph_type: 'ui_graph_v1',
          stream: false,
        }
      )
      return response.data
    },
    onSuccess: (data) => {
      setMessages(prev => [...prev, data])
      setIsTyping(false)
      queryClient.invalidateQueries({ queryKey: ['conversation-history', currentThreadId] })
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to send message')
      setIsTyping(false)
    },
  })

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
      toast.error(error.response?.data?.detail || 'Failed to delete conversation')
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
      toast.error(error.response?.data?.detail || 'Failed to rename conversation')
    },
  })

  const handleSendMessage = async () => {
    if (!messageInput.trim()) return
    
    let threadId = currentThreadId
    
    if (!threadId) {
      const newConversation = await createConversationMutation.mutateAsync()
      threadId = newConversation.thread_id
      setCurrentThreadId(threadId)
    }

    const userMessage: MessageResponse = {
      role: 'user',
      content: messageInput,
      timestamp: new Date().toISOString(),
      tools_used: null,
    }

    setMessages(prev => [...prev, userMessage])
    setMessageInput('')
    setIsTyping(true)
    
    sendMessageMutation.mutate(messageInput)
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  return (
    <div className="flex h-[calc(100vh-8rem)] gap-4">
      <Card className="w-80 flex flex-col bg-gradient-to-br from-purple-50 to-blue-50 dark:from-purple-950/20 dark:to-blue-950/20 border-purple-200 dark:border-purple-800">
        <div className="p-4 border-b border-purple-200 dark:border-purple-800 flex items-center justify-between bg-gradient-to-r from-purple-500 to-blue-500 text-white">
          <h2 className="font-semibold flex items-center gap-2">
            <MessageSquare className="h-5 w-5" />
            Conversations
          </h2>
          <Button size="sm" onClick={() => createConversationMutation.mutate()} disabled={createConversationMutation.isPending} className="bg-white/20 hover:bg-white/30 text-white border-white/30">
            <Plus className="h-4 w-4" />
          </Button>
        </div>
        <div className="flex-1 overflow-y-auto p-2">
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
                      : 'hover:bg-white/60 dark:hover:bg-white/10 hover:shadow-md hover:scale-102'
                  }`}
                  onClick={() => setCurrentThreadId(conversation.thread_id)}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      {editThreadId === conversation.thread_id ? (
                        <Input
                          value={editThreadTitle}
                          onChange={(e) => setEditThreadTitle(e.target.value)}
                          onBlur={() => renameConversationMutation.mutate({ threadId: conversation.thread_id, title: editThreadTitle })}
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

      <Card className="flex-1 flex flex-col bg-gradient-to-br from-slate-50 to-gray-100 dark:from-slate-950 dark:to-gray-950 border-slate-200 dark:border-slate-800">
        {!currentThreadId ? (
          <div className="flex-1 flex items-center justify-center bg-gradient-to-br from-purple-50 via-blue-50 to-indigo-50 dark:from-purple-950/20 dark:via-blue-950/20 dark:to-indigo-950/20">
            <div className="text-center space-y-4">
              <div className="relative">
                <div className="absolute inset-0 bg-gradient-to-r from-purple-500 to-blue-500 blur-xl opacity-30 animate-pulse"></div>
                <Bot className="h-16 w-16 mx-auto text-purple-600 dark:text-purple-400 relative z-10" />
              </div>
              <div>
                <h3 className="text-lg font-semibold bg-gradient-to-r from-purple-600 to-blue-600 bg-clip-text text-transparent">Welcome to WAF-GUARD Assistant</h3>
                <p className="text-sm text-muted-foreground">Start a new conversation to get help with your WAF configuration</p>
              </div>
              <Button onClick={() => createConversationMutation.mutate()} className="bg-gradient-to-r from-purple-500 to-blue-500 hover:from-purple-600 hover:to-blue-600 text-white shadow-lg">
                <Plus className="h-4 w-4 mr-2" />
                Start New Conversation
              </Button>
            </div>
          </div>
        ) : (
          <>
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {messages.map((message, index) => (
                <div key={index} className={`flex gap-3 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  {message.role === 'assistant' && (
                    <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center flex-shrink-0 shadow-lg">
                      <Bot className="h-5 w-5 text-white" />
                    </div>
                  )}
                  <div className={`max-w-[70%] rounded-lg p-3 shadow-md ${
                    message.role === 'user' 
                      ? 'bg-gradient-to-br from-blue-500 to-indigo-500 text-white' 
                      : 'bg-white dark:bg-slate-800 border-2 border-purple-200 dark:border-purple-800'
                  }`}>
                    <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                    {message.tools_used && message.tools_used.length > 0 && (
                      <div className="mt-2 pt-2 border-t border-border/50">
                        <p className="text-xs opacity-70 flex items-center gap-1 mb-1">
                          <Wrench className="h-3 w-3" />Tools used:
                        </p>
                        {message.tools_used.map((tool, idx) => (
                          <details key={idx} className="text-xs opacity-70 mt-1">
                            <summary className="cursor-pointer">{tool.name}</summary>
                            <pre className="mt-1 p-1 bg-black/10 rounded overflow-x-auto">{JSON.stringify(tool.arguments, null, 2)}</pre>
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
              {isTyping && (
                <div className="flex gap-3">
                  <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center shadow-lg">
                    <Bot className="h-5 w-5 text-white" />
                  </div>
                  <div className="bg-white dark:bg-slate-800 border-2 border-purple-200 dark:border-purple-800 rounded-lg p-3 shadow-md">
                    <div className="flex gap-1">
                      <div className="w-2 h-2 rounded-full bg-purple-500 animate-bounce" />
                      <div className="w-2 h-2 rounded-full bg-blue-500 animate-bounce delay-100" />
                      <div className="w-2 h-2 rounded-full bg-indigo-500 animate-bounce delay-200" />
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            <div className="p-4 border-t border-purple-200 dark:border-purple-800 bg-gradient-to-r from-purple-50 to-blue-50 dark:from-purple-950/20 dark:to-blue-950/20">
              <div className="flex gap-2">
                <Input 
                  value={messageInput} 
                  onChange={(e) => setMessageInput(e.target.value)} 
                  onKeyPress={handleKeyPress} 
                  placeholder="Type your message..." 
                  disabled={sendMessageMutation.isPending} 
                  className="border-purple-200 dark:border-purple-800 focus:ring-purple-500 focus:border-purple-500"
                />
                <Button 
                  onClick={handleSendMessage} 
                  disabled={sendMessageMutation.isPending || !messageInput.trim()}
                  className="bg-gradient-to-r from-purple-500 to-blue-500 hover:from-purple-600 hover:to-blue-600 text-white shadow-lg"
                >
                  <Send className="h-4 w-4" />
                </Button>
              </div>
              {selectedConfig && (
                <p className="text-xs text-purple-600 dark:text-purple-400 mt-2 flex items-center gap-1">
                  <span className="inline-block w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
                  Using configuration: <span className="font-semibold">{selectedConfig.name}</span>
                </p>
              )}
            </div>
          </>
        )}
      </Card>
    </div>
  )
}
