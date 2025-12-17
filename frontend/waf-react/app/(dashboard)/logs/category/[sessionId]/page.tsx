'use client'

import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { LoadingSpinner } from '@/components/ui/loading-spinner'
import { 
  ArrowLeft, 
  FileText,
  Globe,
  XCircle,
  CheckCircle,
  Eye,
  ChevronDown,
  ChevronUp,
  BarChart3,
  Hash,
  Server,
  X
} from 'lucide-react'
import toast from 'react-hot-toast'
import { CategoryDetailsResponse } from '@/types'
import { useRouter, useSearchParams } from 'next/navigation'
import { use } from 'react'
import { motion } from 'framer-motion'

export default function CategoryDetailsPage({ params }: { params: Promise<{ sessionId: string }> }) {
  const [categoryData, setCategoryData] = useState<CategoryDetailsResponse | null>(null)
  const [loading, setLoading] = useState<boolean>(true)
  const [expandedLogs, setExpandedLogs] = useState<Set<number>>(new Set())
  const [showAllLogsModal, setShowAllLogsModal] = useState<boolean>(false)
  const router = useRouter()
  const searchParams = useSearchParams()
  const category = searchParams.get('category')
  const resolvedParams = use(params)
  const sessionId = resolvedParams.sessionId

  useEffect(() => {
    if (sessionId && category) {
      fetchCategoryData()
    }
  }, [sessionId, category])

  const fetchCategoryData = async () => {
    try {
      setLoading(true)
      // Get data from localStorage
      const cachedData = localStorage.getItem(`category_${sessionId}`)
      if (!cachedData) {
        toast.error('Category data not found')
        router.push(`/logs/${sessionId}`)
        return
      }

      const categoryEntry = JSON.parse(cachedData)
      
      const response = await api.post<CategoryDetailsResponse>(
        `/logs/sessions/${sessionId}/categories`,
        categoryEntry
      )

      setCategoryData(response.data)
    } catch (error: any) {
      console.error('Error fetching category data:', error)
      const errorMessage = error.response?.data?.detail 
        ? (typeof error.response.data.detail === 'string' 
            ? error.response.data.detail 
            : JSON.stringify(error.response.data.detail))
        : 'Failed to fetch category data'
      toast.error(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  const toggleLogExpansion = (index: number) => {
    const newExpanded = new Set(expandedLogs)
    if (newExpanded.has(index)) {
      newExpanded.delete(index)
    } else {
      newExpanded.add(index)
    }
    setExpandedLogs(newExpanded)
  }

  if (loading) {
    return (
      <main className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100 flex items-center justify-center">
        <Card className="p-8 shadow-xl border-0 bg-white/80 backdrop-blur-sm">
          <div className="text-center">
            <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <p className="text-lg text-slate-600">Loading category details...</p>
          </div>
        </Card>
      </main>
    )
  }

  if (!categoryData) {
    return (
      <main className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100 flex items-center justify-center">
        <Card className="p-8 shadow-xl border-0 bg-white/80 backdrop-blur-sm">
          <div className="text-center">
            <XCircle className="h-16 w-16 text-red-500 mx-auto mb-4" />
            <p className="text-lg text-slate-600">Failed to load category data</p>
            <Button onClick={() => router.push(`/logs/${sessionId}`)} className="mt-4">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Go Back
            </Button>
          </div>
        </Card>
      </main>
    )
  }

  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100 p-4">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center justify-between"
        >
          <div>
            <Button
              onClick={() => router.push(`/logs/${sessionId}`)}
              variant="outline"
              className="mb-4 bg-white/80 backdrop-blur-sm border-slate-200 hover:bg-white"
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Results
            </Button>
            <h1 className="text-4xl font-bold text-slate-800 mb-2">
              Category Details
            </h1>
            <p className="text-slate-600 text-lg">
              Detailed view of logs in the "{category}" category
            </p>
          </div>
        </motion.div>

        {/* Summary Cards */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="grid grid-cols-1 md:grid-cols-3 gap-4"
        >
          <Card className="bg-gradient-to-r from-blue-500 to-blue-600 text-white border-0 shadow-lg">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-blue-100 text-sm font-medium">Category</p>
                  <p className="text-xl font-bold truncate">{category}</p>
                </div>
                <BarChart3 className="h-10 w-10 text-blue-200" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-r from-green-500 to-green-600 text-white border-0 shadow-lg">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-green-100 text-sm font-medium">Total Logs</p>
                  <p className="text-3xl font-bold">{categoryData.logs.length.toLocaleString()}</p>
                </div>
                <FileText className="h-10 w-10 text-green-200" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-r from-purple-500 to-purple-600 text-white border-0 shadow-lg">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-purple-100 text-sm font-medium">Session ID</p>
                  <p className="text-sm font-mono truncate">{sessionId}</p>
                </div>
                <Hash className="h-10 w-10 text-purple-200" />
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Logs Details */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          <Card className="shadow-xl border-0 bg-white/80 backdrop-blur-sm">
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-xl">
                  <Eye className="h-6 w-6 text-blue-600" />
                  Log Entries ({categoryData.logs.length})
                </div>
                <Button
                  onClick={() => setShowAllLogsModal(true)}
                  variant="outline"
                  className="bg-blue-50 hover:bg-blue-100 text-blue-700 border-blue-200"
                >
                  <FileText className="h-4 w-4 mr-2" />
                  View All Logs JSON
                </Button>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {categoryData.logs.map((log, index) => (
                  <motion.div
                    key={index}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.05 }}
                    className="border border-slate-200 rounded-lg p-4 bg-white shadow-sm hover:shadow-md transition-shadow duration-200"
                  >
                    {/* Log Header */}
                    <div 
                      className="flex items-center justify-between cursor-pointer"
                      onClick={() => toggleLogExpansion(index)}
                    >
                      <div className="flex items-center space-x-4 flex-1">
                        <span className="text-sm font-mono text-slate-500">#{index + 1}</span>
                        <span className="font-mono text-sm bg-slate-100 px-2 py-1 rounded">
                          {log.A_transaction_id}
                        </span>
                        <span className="text-sm text-slate-600">
                          {log.time}
                        </span>
                        <span className={`text-xs px-2 py-1 rounded ${
                          log.F_response_status_code >= 200 && log.F_response_status_code < 300 
                            ? 'bg-green-100 text-green-800' 
                            : log.F_response_status_code >= 400 
                            ? 'bg-red-100 text-red-800' 
                            : 'bg-yellow-100 text-yellow-800'
                        }`}>
                          {log.F_response_status_code}
                        </span>
                      </div>
                      <div className="flex items-center space-x-2">
                        <div className="text-xs text-slate-500">
                          {expandedLogs.has(index) ? 'Hide Details' : 'Show Details'}
                        </div>
                        {expandedLogs.has(index) ? 
                          <ChevronUp className="h-4 w-4 text-slate-400" /> : 
                          <ChevronDown className="h-4 w-4 text-slate-400" />
                        }
                      </div>
                    </div>

                    {/* Expanded Log Details */}
                    {expandedLogs.has(index) && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        className="mt-4 space-y-4 border-t pt-4"
                      >
                        {/* Log Information Grid */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          <div className="space-y-3">
                            <h4 className="font-semibold text-slate-700 flex items-center gap-2">
                              <Globe className="h-4 w-4" />
                              Connection Details
                            </h4>
                            <div className="space-y-2 text-sm">
                              <div className="flex justify-between">
                                <span className="text-slate-500">Time:</span>
                                <span className="font-mono">{log.time}</span>
                              </div>
                              <div className="flex justify-between">
                                <span className="text-slate-500">Transaction ID:</span>
                                <span className="font-mono">{log.A_transaction_id}</span>
                              </div>
                              <div className="flex justify-between">
                                <span className="text-slate-500">Remote:</span>
                                <span className="font-mono">{log.A_remote_address}:{log.A_remote_port}</span>
                              </div>
                              <div className="flex justify-between">
                                <span className="text-slate-500">Local:</span>
                                <span className="font-mono">{log.A_local_address}:{log.A_local_port}</span>
                              </div>
                            </div>
                          </div>

                          <div className="space-y-3">
                            <h4 className="font-semibold text-slate-700 flex items-center gap-2">
                              <Server className="h-4 w-4" />
                              Response Information
                            </h4>
                            <div className="space-y-2 text-sm">
                              <div className="flex justify-between">
                                <span className="text-slate-500">Status:</span>
                                <span className="font-mono">{log.F_response_status_code} - {log.F_response_status}</span>
                              </div>
                              <div className="flex justify-between">
                                <span className="text-slate-500">Categories:</span>
                                <span className="font-mono">{log.Z_categories}</span>
                              </div>
                              <div className="flex justify-between">
                                <span className="text-slate-500">Blocked:</span>
                                <span className="font-mono">{log.Z_blocked === "0" ? "No" : "Yes"}</span>
                              </div>
                              <div className="flex justify-between">
                                <span className="text-slate-500">Action:</span>
                                <span className="font-mono">{log.H_action || 'N/A'}</span>
                              </div>
                            </div>
                          </div>
                        </div>

                        {/* Request Details */}
                        <div className="space-y-3">
                          <h4 className="font-semibold text-slate-700">Request Information</h4>
                          <div className="space-y-2 text-sm bg-slate-50 p-3 rounded">
                            <div className="flex justify-between">
                              <span className="text-slate-500">Method:</span>
                              <span className="font-mono">{log.B_http_request}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-slate-500">Host:</span>
                              <span className="font-mono">{log.B_host}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-slate-500">Protocol:</span>
                              <span className="font-mono">{log.B_request_protocol}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-slate-500">User Agent:</span>
                              <span className="font-mono">{log.B_user_agent}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-slate-500">Payloads:</span>
                              <span className="font-mono">{log.payloads}</span>
                            </div>
                          </div>
                        </div>

                        {/* URL */}
                        <div>
                          <h4 className="font-semibold text-slate-700 mb-2">Request URL</h4>
                          <p className="text-sm bg-slate-50 p-3 rounded font-mono text-slate-600 break-all">
                            {log.B_request_url}
                          </p>
                        </div>

                        {/* Messages */}
                        {log.H_messages && Array.isArray(log.H_messages) && log.H_messages.length > 0 && (
                          <div>
                            <h4 className="font-semibold text-slate-700 mb-2">Messages</h4>
                            <div className="space-y-2">
                              {log.H_messages.map((message, msgIndex) => (
                                <div key={msgIndex} className="text-sm bg-slate-50 p-3 rounded">
                                  {message}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Message Tags */}
                        {log.msgtags && log.msgtags.length > 0 && (
                          <div>
                            <h4 className="font-semibold text-slate-700 mb-2">Message Tags</h4>
                            <div className="flex flex-wrap gap-2">
                              {log.msgtags.map((tag, tagIndex) => (
                                <span key={tagIndex} className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
                                  {tag}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Classification Probabilities */}
                        {log.new_categories && log.new_categories.probabilities && (
                          <div>
                            <h4 className="font-semibold text-slate-700 mb-2">Classification Probabilities</h4>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                              {Object.entries(log.new_categories.probabilities[0])
                                .sort(([, a], [, b]) => b - a)
                                .slice(0, 5)
                                .map(([label, prob]) => (
                                  <div key={label} className="flex items-center justify-between bg-slate-50 p-2 rounded">
                                    <span className="text-sm font-medium">{label}</span>
                                    <div className="flex items-center space-x-2">
                                      <div className="w-20 bg-slate-200 rounded-full h-2">
                                        <div 
                                          className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                                          style={{ width: `${prob * 100}%` }}
                                        />
                                      </div>
                                      <span className="text-sm font-mono text-slate-600">
                                        {(prob * 100).toFixed(1)}%
                                      </span>
                                    </div>
                                  </div>
                                ))}
                            </div>
                          </div>
                        )}

                      </motion.div>
                    )}
                  </motion.div>
                ))}
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* All Logs JSON Modal */}
        {showAllLogsModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50"
            onClick={() => setShowAllLogsModal(false)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="bg-white rounded-lg shadow-xl max-w-6xl max-h-[90vh] overflow-hidden w-full"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Modal Header */}
              <div className="flex items-center justify-between p-6 border-b bg-slate-50">
                <div>
                  <h2 className="text-xl font-bold text-slate-800">All Logs JSON</h2>
                  <p className="text-sm text-slate-600">Category: {category}</p>
                </div>
                <Button
                  onClick={() => setShowAllLogsModal(false)}
                  variant="outline"
                  size="sm"
                  className="p-2"
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>

              {/* Modal Content */}
              <div className="p-6 overflow-y-auto max-h-[calc(90vh-120px)]">
                <pre className="text-xs bg-slate-50 p-4 rounded font-mono text-slate-800 overflow-x-auto">
                  {JSON.stringify(categoryData.logs, null, 2)}
                </pre>
              </div>
            </motion.div>
          </motion.div>
        )}
      </div>
    </main>
  )
}
