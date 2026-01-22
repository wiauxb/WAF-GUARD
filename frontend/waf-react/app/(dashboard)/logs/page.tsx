'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { LoadingSpinner } from '@/components/ui/loading-spinner'
import { 
  Upload, 
  FileText, 
  Trash2, 
  Eye,
  BarChart3,
  Clock
} from 'lucide-react'
import toast from 'react-hot-toast'
import { LogAnalysisSessionResponse, LogClassificationResponse } from '@/types'
import { formatDate } from '@/lib/utils'
import { useConfigStore } from '@/stores/config'
import { useRouter } from 'next/navigation'

export default function LogsPage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false)
  const queryClient = useQueryClient()
  const { selectedConfig } = useConfigStore()
  const router = useRouter()

  // Fetch user's log sessions
  const { data: sessions, isLoading } = useQuery({
    queryKey: ['log-sessions'],
    queryFn: async () => {
      const response = await api.post<LogAnalysisSessionResponse[]>('/logs/sessions', {
        limit: 50,
        offset: 0
      })
      return response.data
    },
  })

  // Upload mutation
  const uploadMutation = useMutation({
    mutationFn: async () => {
      const formData = new FormData()
      formData.append('file', selectedFile!)
      
      const url = selectedConfig 
        ? `/logs/classify?configuration_id=${selectedConfig.id}`
        : '/logs/classify'
      
      const response = await api.post<LogClassificationResponse>(url, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      return response.data
    },
    onSuccess: (data) => {
      toast.success('Log file classified successfully!')
      queryClient.invalidateQueries({ queryKey: ['log-sessions'] })
      setUploadDialogOpen(false)
      setSelectedFile(null)
      // Navigate to the session details page
      router.push(`/logs/${data.session_id}`)
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to classify log file')
    },
  })

  // Delete session mutation
  const deleteMutation = useMutation({
    mutationFn: async (sessionId: string) => {
      const response = await api.delete(`/logs/sessions/${sessionId}`)
      return response.data
    },
    onSuccess: () => {
      toast.success('Session deleted!')
      queryClient.invalidateQueries({ queryKey: ['log-sessions'] })
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to delete session')
    },
  })

  const handleUpload = () => {
    if (!selectedFile) {
      toast.error('Please select a file')
      return
    }
    uploadMutation.mutate()
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold">Log Analysis</h1>
          <p className="text-muted-foreground">Upload and analyze WAF log files</p>
        </div>
      </div>

      {/* Upload Section */}
      <Card className="border-2 border-dashed">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Upload className="h-5 w-5" />
            Upload Log File
          </CardTitle>
          <CardDescription>
            Upload .san, .txt, or audit.log files for AI-powered classification
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col gap-4">
            <div className="flex items-center gap-4">
              <Input
                type="file"
                accept=".san,.txt,.log"
                onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                className="flex-1"
              />
              <Button
                onClick={handleUpload}
                disabled={uploadMutation.isPending || !selectedFile}
              >
                {uploadMutation.isPending ? (
                  <>
                    <LoadingSpinner />
                    Analyzing...
                  </>
                ) : (
                  <>
                    <Upload className="h-4 w-4 mr-2" />
                    Upload & Analyze
                  </>
                )}
              </Button>
            </div>
            {selectedConfig && (
              <p className="text-xs text-muted-foreground">
                This log will be linked to configuration: <strong>{selectedConfig.name}</strong>
              </p>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Sessions List */}
      <div>
        <h2 className="text-xl font-semibold mb-4">Analysis Sessions</h2>
        {isLoading ? (
          <LoadingSpinner />
        ) : sessions?.length === 0 ? (
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-12">
              <FileText className="h-16 w-16 text-muted-foreground mb-4" />
              <p className="text-muted-foreground text-center">
                No log analysis sessions yet. Upload a log file to get started.
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {sessions?.map((session) => (
              <Card key={session.session_id} className="hover:shadow-lg transition-shadow">
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-2">
                      <FileText className="h-5 w-5 text-primary" />
                      <CardTitle className="text-base">{session.filename}</CardTitle>
                    </div>
                  </div>
                  <CardDescription>
                    <div className="flex items-center gap-1 text-xs">
                      <Clock className="h-3 w-3" />
                      {formatDate(session.created_at)}
                    </div>
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div>
                      <p className="text-muted-foreground">Total Logs</p>
                      <p className="font-semibold">{session.total_logs.toLocaleString()}</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Categories</p>
                      <p className="font-semibold">
                        {session.categories ? Object.keys(session.categories).length : 0}
                      </p>
                    </div>
                  </div>
                  
                  {session.categories && (
                    <div className="flex flex-wrap gap-1 pt-2 border-t">
                      {Object.entries(session.categories).slice(0, 3).map(([category, count]) => (
                        <span
                          key={category}
                          className="text-xs px-2 py-1 bg-primary/10 text-primary rounded"
                        >
                          {category}: {count}
                        </span>
                      ))}
                      {Object.keys(session.categories).length > 3 && (
                        <span className="text-xs px-2 py-1 bg-muted text-muted-foreground rounded">
                          +{Object.keys(session.categories).length - 3} more
                        </span>
                      )}
                    </div>
                  )}

                  <div className="flex gap-2 pt-2">
                    <Button
                      size="sm"
                      variant="outline"
                      className="flex-1"
                      onClick={() => router.push(`/logs/${session.session_id}`)}
                    >
                      <Eye className="h-4 w-4 mr-1" />
                      View
                    </Button>
                    <Button
                      size="sm"
                      variant="destructive"
                      onClick={() => {
                        if (confirm('Are you sure you want to delete this session?')) {
                          deleteMutation.mutate(session.session_id)
                        }
                      }}
                      disabled={deleteMutation.isPending}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
