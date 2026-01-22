'use client'

import { useState, useEffect } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { LoadingSpinner } from '@/components/ui/loading-spinner'
import { 
  ArrowLeft, 
  BarChart3, 
  Filter,
  X,
  Plus,
  Trash2,
  RefreshCw,
  FileText,
  Hash,
  ArrowRight
} from 'lucide-react'
import toast from 'react-hot-toast'
import { 
  FilteredLogsResponse, 
  LogFilter, 
  LogCategoryResponse
} from '@/types'
import { useRouter } from 'next/navigation'
import { use } from 'react'
import { motion } from 'framer-motion'

export default function LogSessionPage({ params }: { params: Promise<{ sessionId: string }> }) {
  const [showFilters, setShowFilters] = useState(false)
  const [filters, setFilters] = useState<LogFilter>({ columns: [] })
  const router = useRouter()
  const resolvedParams = use(params)
  const sessionId = resolvedParams.sessionId

  console.log('Session ID:', sessionId)

  // Fetch filtered logs
  const { data: logsData, isLoading, refetch } = useQuery({
    queryKey: ['log-session', sessionId, filters],
    queryFn: async () => {
      const response = await api.post<FilteredLogsResponse>(
        `/logs/sessions/${sessionId}/filter`,
        filters
      )
      return response.data
    },
  })

  // Handle category click - navigate to details page
  const handleCategoryClick = (categoryData: LogCategoryResponse) => {
    // Store in localStorage for the details page
    localStorage.setItem(`category_${sessionId}`, JSON.stringify({
      category: categoryData.category,
      count: categoryData.count,
      log_indices: categoryData.log_indices || []
    }))
    // Navigate to category details page
    router.push(`/logs/category/${sessionId}?category=${encodeURIComponent(categoryData.category)}`)
  }

  const addColumnFilter = () => {
    setFilters(prev => ({
      ...prev,
      columns: [
        ...(prev.columns || []),
        { name: '', value: '', type: 'contains' }
      ]
    }))
  }

  const updateColumnFilter = (index: number, field: string, value: string) => {
    setFilters(prev => ({
      ...prev,
      columns: (prev.columns || []).map((col, i) =>
        i === index ? { ...col, [field]: value } : col
      )
    }))
  }

  const removeColumnFilter = (index: number) => {
    setFilters(prev => ({
      ...prev,
      columns: (prev.columns || []).filter((_, i) => i !== index)
    }))
  }

  const clearFilters = () => {
    setFilters({ columns: [] })
  }

  const getCategoryColor = (index: number) => {
    const colors = [
      'bg-blue-100 border-blue-300 text-blue-800',
      'bg-green-100 border-green-300 text-green-800',
      'bg-purple-100 border-purple-300 text-purple-800',
      'bg-orange-100 border-orange-300 text-orange-800',
      'bg-pink-100 border-pink-300 text-pink-800',
      'bg-indigo-100 border-indigo-300 text-indigo-800',
    ]
    return colors[index % colors.length]
  }

  if (isLoading) {
    return (
      <main className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100 flex items-center justify-center">
        <Card className="p-8 shadow-xl border-0 bg-white/80 backdrop-blur-sm">
          <div className="text-center">
            <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <p className="text-lg text-slate-600">Loading log analysis...</p>
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
              onClick={() => router.push('/logs')}
              variant="outline"
              className="mb-4 bg-white/80 backdrop-blur-sm border-slate-200 hover:bg-white"
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Sessions
            </Button>
            <h1 className="text-4xl font-bold text-slate-800 mb-2">
              Log Analysis Results
            </h1>
            <p className="text-slate-600 text-lg">
              AI-powered analysis and categorization of your log file
            </p>
          </div>
          <Button
            onClick={() => refetch()}
            variant="outline"
            className="bg-white/80 backdrop-blur-sm border-slate-200 hover:bg-white"
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        </motion.div>

        {/* Filters Section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.05 }}
        >
          <Card className="shadow-xl border-0 bg-white/80 backdrop-blur-sm">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2 text-xl">
                  <Filter className="h-6 w-6 text-blue-600" />
                  Log Filters
                </CardTitle>
                <Button
                  onClick={() => setShowFilters(!showFilters)}
                  variant="outline"
                  size="sm"
                >
                  {showFilters ? <X className="h-4 w-4" /> : <Filter className="h-4 w-4" />}
                  {showFilters ? 'Hide' : 'Show'} Filters
                </Button>
              </div>
            </CardHeader>
            {showFilters && (
              <CardContent className="space-y-4">
                {/* Time Filters */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm font-medium mb-2 block">Start Time</label>
                    <Input
                      type="datetime-local"
                      value={filters.start_time || ''}
                      onChange={(e) => setFilters(prev => ({ ...prev, start_time: e.target.value || undefined }))}
                      className="bg-white"
                    />
                  </div>
                  <div>
                    <label className="text-sm font-medium mb-2 block">End Time</label>
                    <Input
                      type="datetime-local"
                      value={filters.end_time || ''}
                      onChange={(e) => setFilters(prev => ({ ...prev, end_time: e.target.value || undefined }))}
                      className="bg-white"
                    />
                  </div>
                </div>

                {/* Column Filters */}
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <label className="text-sm font-medium">Column Filters</label>
                    <Button onClick={addColumnFilter} variant="outline" size="sm">
                      <Plus className="h-4 w-4 mr-2" />
                      Add Filter
                    </Button>
                  </div>

                  {filters.columns && filters.columns.length > 0 ? (
                    <div className="space-y-3">
                      {filters.columns.map((col, index) => (
                        <div key={index} className="grid grid-cols-1 md:grid-cols-4 gap-3 p-3 border rounded-lg bg-white">
                          <Input
                            placeholder="Column name"
                            value={col.name}
                            onChange={(e) => updateColumnFilter(index, 'name', e.target.value)}
                            className="bg-white"
                          />
                          <select
                            className="flex h-9 w-full rounded-md border border-input bg-white px-3 py-1 text-sm"
                            value={col.type}
                            onChange={(e) => updateColumnFilter(index, 'type', e.target.value)}
                          >
                            <option value="exact">Exact</option>
                            <option value="contains">Contains</option>
                            <option value="greater_than">Greater Than</option>
                            <option value="less_than">Less Than</option>
                          </select>
                          <Input
                            placeholder="Value"
                            value={col.value}
                            onChange={(e) => updateColumnFilter(index, 'value', e.target.value)}
                            className="bg-white"
                          />
                          <Button
                            onClick={() => removeColumnFilter(index)}
                            variant="outline"
                            size="sm"
                            className="bg-white border-red-200 text-red-600 hover:bg-red-50"
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground text-center py-4">
                      No column filters added yet
                    </p>
                  )}
                </div>

                <div className="flex gap-2 pt-4">
                  <Button onClick={() => refetch()} className="flex-1 bg-blue-600 hover:bg-blue-700 text-white">
                    <Filter className="h-4 w-4 mr-2" />
                    Apply Filters
                  </Button>
                  <Button onClick={clearFilters} variant="outline">
                    <X className="h-4 w-4 mr-2" />
                    Clear Filters
                  </Button>
                </div>
              </CardContent>
            )}
          </Card>
        </motion.div>

        {/* Statistics */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15 }}
          className="grid grid-cols-1 md:grid-cols-4 gap-4"
        >
          <Card className="bg-gradient-to-r from-blue-500 to-blue-600 text-white border-0 shadow-lg">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-blue-100 text-sm font-medium">Total Logs</p>
                  <p className="text-3xl font-bold">{logsData?.total_logs.toLocaleString()}</p>
                </div>
                <FileText className="h-10 w-10 text-blue-200" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-r from-green-500 to-green-600 text-white border-0 shadow-lg">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-green-100 text-sm font-medium">Filtered Count</p>
                  <p className="text-3xl font-bold">{logsData?.filtered_logs.toLocaleString()}</p>
                </div>
                <BarChart3 className="h-10 w-10 text-green-200" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-r from-purple-500 to-purple-600 text-white border-0 shadow-lg">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-purple-100 text-sm font-medium">Categories</p>
                  <p className="text-3xl font-bold">{logsData?.categories.length}</p>
                </div>
                <BarChart3 className="h-10 w-10 text-purple-200" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-r from-orange-500 to-orange-600 text-white border-0 shadow-lg">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-orange-100 text-sm font-medium">Columns</p>
                  <p className="text-3xl font-bold">{logsData?.columns.length}</p>
                </div>
                <Hash className="h-10 w-10 text-orange-200" />
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Categories */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.25 }}
        >
          <Card className="shadow-xl border-0 bg-white/80 backdrop-blur-sm">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-xl">
                <BarChart3 className="h-6 w-6 text-blue-600" />
                Classification Results
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {logsData?.categories.map((category, index) => (
                  <motion.div
                    key={category.category}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.1 }}
                    onClick={() => handleCategoryClick(category)}
                    className={`p-4 rounded-lg border-2 cursor-pointer transition-all duration-200 hover:shadow-md hover:scale-[1.02] ${getCategoryColor(index)}`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <h3 className="font-semibold text-lg mb-1">
                          {category.category}
                        </h3>
                        <p className="text-sm opacity-80">
                          {category.count} logs ({category.percentage.toFixed(1)}%)
                        </p>
                      </div>
                      <div className="flex items-center space-x-3">
                        <div className="text-right">
                          <div className="text-2xl font-bold">
                            {category.count}
                          </div>
                          <div className="text-xs opacity-70">
                            entries
                          </div>
                        </div>
                        <ArrowRight className="h-5 w-5 opacity-60" />
                      </div>
                    </div>
                    
                    {/* Progress bar */}
                    <div className="mt-3 w-full bg-white bg-opacity-30 rounded-full h-2">
                      <div 
                        className="bg-current h-2 rounded-full transition-all duration-500"
                        style={{ 
                          width: `${category.percentage}%`,
                          opacity: 0.7 
                        }}
                      />
                    </div>
                  </motion.div>
                ))}
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </main>
  )
}
