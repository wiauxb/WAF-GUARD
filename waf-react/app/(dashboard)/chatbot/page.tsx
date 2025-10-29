'use client'

import { useState, useRef, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { chatbotApi } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { LoadingSpinner } from '@/components/ui/loading-spinner'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { 
  Send, 
  Plus, 
  Trash2, 
  Edit2,
  MessageSquare,
  Bot,
  User as UserIcon
} from 'lucide-react'
import toast from 'react-hot-toast'
import { Message, Thread } from '@/types'
import { formatRelativeTime } from '@/lib/utils'

export default function ChatbotPage() {
  const [currentThreadId, setCurrentThreadId] = useState<string | null>(null)
  const [messageInput, setMessageInput] = useState('')
  const [messages, setMessages] = useState<Message[]>([])
  const [isTyping, setIsTyping] = useState(false)
  const [editThreadId, setEditThreadId] = useState<string | null>(null)
  const [editThreadTitle, setEditThreadTitle] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const queryClient = useQueryClient()

  // Fetch threads
  const { data: threads, isLoading: threadsLoading } = useQuery({
    queryKey: ['threads'],
    queryFn: async () => {
      const response = await chatbotApi.get('/chat/threads')
      return response.data
    },
  })

  // Fetch messages for current thread
  const { data: threadMessages } = useQuery({
    queryKey: ['thread-messages', currentThreadId],
    queryFn: async () => {
      if (!currentThreadId) return []
      const response = await chatbotApi.get(`/chat/threads/${currentThreadId}`)
      return response.data
    },
    enabled: !!currentThreadId,
  })

  useEffect(() => {
    if (threadMessages) {
      setMessages(threadMessages)
    }
  }, [threadMessages])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Create thread mutation
  const createThreadMutation = useMutation({
    mutationFn: async () => {
      const response = await chatbotApi.post('/chat/threads')
      return response.data
    },
    onSuccess: (data) => {
      setCurrentThreadId(data.thread_id)
      setMessages([])
      queryClient.invalidateQueries({ queryKey: ['threads'] })
      toast.success('New conversation started!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to create thread')
    },
  })

  // Send message mutation
  const sendMessageMutation = useMutation({
    mutationFn: async (message: string) => {
      const response = await chatbotApi.post('/chat/ui_graph', {
        messages: [
          ...messages.map(m => ({ role: m.role, content: m.content })),
          { role: 'user', content: message }
        ],
        config: { thread_id: currentThreadId }
      })
      return response.data
    },
    onSuccess: (data) => {
      // Add assistant response
      if (data.messages && data.messages.length > 0) {
        const assistantMessage = data.messages[data.messages.length - 1]
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: assistantMessage.content,
          timestamp: new Date().toISOString()
        }])
      }
      setIsTyping(false)
      queryClient.invalidateQueries({ queryKey: ['thread-messages', currentThreadId] })
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to send message')
      setIsTyping(false)
    },
  })

  // Delete thread mutation
  const deleteThreadMutation = useMutation({
    mutationFn: async (threadId: string) => {
      const response = await chatbotApi.delete(`/chat/threads/${threadId}`)
      return response.data
    },
    onSuccess: () => {
      toast.success('Conversation deleted!')
      if (currentThreadId === editThreadId) {
        setCurrentThreadId(null)
        setMessages([])
      }
      queryClient.invalidateQueries({ queryKey: ['threads'] })
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to delete thread')
    },
  })

  // Rename thread mutation
  const renameThreadMutation = useMutation({
    mutationFn: async ({ threadId, newTitle }: { threadId: string, newTitle: string }) => {
      const response = await chatbotApi.put(`/chat/threads/${threadId}`, {
        new_title: newTitle
      })
      return response.data
    },
    onSuccess: () => {
      toast.success('Conversation renamed!')
      queryClient.invalidateQueries({ queryKey: ['threads'] })
      setEditThreadId(null)
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to rename thread')
    },
  })

  const handleSendMessage = async () => {
    if (!messageInput.trim()) return
    
    if (!currentThreadId) {
      // Create new thread first
      const newThread = await createThreadMutation.mutateAsync()
      setCurrentThreadId(newThread.thread_id)
    }

    const userMessage: Message = {
      role: 'user',
      content: messageInput,
      timestamp: new Date().toISOString()
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
      {/* Sidebar - Thread List */}
      <Card className="w-80 flex flex-col">
        <div className="p-4 border-b flex items-center justify-between">
          <h2 className="font-semibold flex items-center gap-2">
            <MessageSquare className="h-5 w-5" />
            Conversations
          </h2>
          <Button
            size="sm"
            onClick={() => createThreadMutation.mutate()}
            disabled={createThreadMutation.isPending}
          >
            <Plus className="h-4 w-4" />
          </Button>
        </div>
        <div className="flex-1 overflow-y-auto p-2">
          {threadsLoading ? (
            <LoadingSpinner />
          ) : threads?.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-8">
              No conversations yet
            </p>
          ) : (
            <div className="space-y-1">
              {threads?.map((thread: Thread) => (
                <div
                  key={thread.thread_id}
                  className={`p-3 rounded-lg cursor-pointer transition-colors ${
                    currentThreadId === thread.thread_id
                      ? 'bg-primary text-primary-foreground'
                      : 'hover:bg-accent'
                  }`}
                  onClick={() => {
                    setCurrentThreadId(thread.thread_id)
                    setMessages([])
                  }}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      {editThreadId === thread.thread_id ? (
                        <Input
                          value={editThreadTitle}
                          onChange={(e) => setEditThreadTitle(e.target.value)}
                          onBlur={() => {
                            renameThreadMutation.mutate({
                              threadId: thread.thread_id,
                              newTitle: editThreadTitle
                            })
                          }}
                          onKeyPress={(e) => {
                            if (e.key === 'Enter') {
                              renameThreadMutation.mutate({
                                threadId: thread.thread_id,
                                newTitle: editThreadTitle
                              })
                            }
                          }}
                          className="h-6 text-sm"
                          autoFocus
                        />
                      ) : (
                        <p className="text-sm font-medium truncate">
                          {thread.title || 'New Conversation'}
                        </p>
                      )}
                      <p className="text-xs opacity-70" suppressHydrationWarning>
                        {formatRelativeTime(thread.updated_at)}
                      </p>
                    </div>
                    <div className="flex gap-1">
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          setEditThreadId(thread.thread_id)
                          setEditThreadTitle(thread.title || 'New Conversation')
                        }}
                        className="p-1 hover:bg-accent rounded"
                      >
                        <Edit2 className="h-3 w-3" />
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          if (confirm('Delete this conversation?')) {
                            deleteThreadMutation.mutate(thread.thread_id)
                          }
                        }}
                        className="p-1 hover:bg-destructive hover:text-destructive-foreground rounded"
                      >
                        <Trash2 className="h-3 w-3" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </Card>

      {/* Chat Area */}
      <Card className="flex-1 flex flex-col">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 && !currentThreadId ? (
            <div className="h-full flex flex-col items-center justify-center text-center">
              <Bot className="h-16 w-16 text-muted-foreground mb-4" />
              <h3 className="text-xl font-semibold mb-2">
                Welcome to WAF-GUARD Assistant
              </h3>
              <p className="text-muted-foreground max-w-md">
                Ask me anything about your WAF configurations, directives, or security rules.
                I'm here to help!
              </p>
            </div>
          ) : (
            <>
              {messages.map((message, index) => (
                <div
                  key={index}
                  className={`flex gap-3 ${
                    message.role === 'user' ? 'justify-end' : 'justify-start'
                  }`}
                >
                  {message.role === 'assistant' && (
                    <div className="h-8 w-8 rounded-full bg-gradient-to-br from-blue-600 to-purple-600 flex items-center justify-center flex-shrink-0">
                      <Bot className="h-5 w-5 text-white" />
                    </div>
                  )}
                  <div
                    className={`max-w-[70%] rounded-lg p-3 ${
                      message.role === 'user'
                        ? 'bg-primary text-primary-foreground'
                        : 'bg-secondary'
                    }`}
                  >
                    <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                    {message.timestamp && (
                      <p className="text-xs opacity-70 mt-1" suppressHydrationWarning>
                        {formatRelativeTime(message.timestamp)}
                      </p>
                    )}
                  </div>
                  {message.role === 'user' && (
                    <div className="h-8 w-8 rounded-full bg-gradient-to-br from-green-600 to-teal-600 flex items-center justify-center flex-shrink-0">
                      <UserIcon className="h-5 w-5 text-white" />
                    </div>
                  )}
                </div>
              ))}
              {isTyping && (
                <div className="flex gap-3">
                  <div className="h-8 w-8 rounded-full bg-gradient-to-br from-blue-600 to-purple-600 flex items-center justify-center">
                    <Bot className="h-5 w-5 text-white" />
                  </div>
                  <div className="bg-secondary rounded-lg p-3">
                    <div className="flex gap-1">
                      <div className="w-2 h-2 bg-primary rounded-full animate-bounce" />
                      <div className="w-2 h-2 bg-primary rounded-full animate-bounce delay-100" />
                      <div className="w-2 h-2 bg-primary rounded-full animate-bounce delay-200" />
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </>
          )}
        </div>

        {/* Input Area */}
        <div className="border-t p-4">
          <div className="flex gap-2">
            <Input
              placeholder="Ask about your WAF configuration..."
              value={messageInput}
              onChange={(e) => setMessageInput(e.target.value)}
              onKeyPress={handleKeyPress}
              disabled={sendMessageMutation.isPending}
              className="flex-1"
            />
            <Button
              onClick={handleSendMessage}
              disabled={!messageInput.trim() || sendMessageMutation.isPending}
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </Card>
    </div>
  )
}
