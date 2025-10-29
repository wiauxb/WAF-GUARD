'use client'

import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { webAppApi } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { LoadingSpinner } from '@/components/ui/loading-spinner'
import { Database, Download, Upload, AlertCircle } from 'lucide-react'
import toast from 'react-hot-toast'

export default function DatabasePage() {
  const [exportName, setExportName] = useState('')
  const [importName, setImportName] = useState('')

  const exportMutation = useMutation({
    mutationFn: async (configName: string) => {
      const response = await webAppApi.post(`/database/export/${configName}`)
      return response.data
    },
    onSuccess: (data) => {
      toast.success(data.message || 'Database exported successfully!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Export failed')
    },
  })

  const importMutation = useMutation({
    mutationFn: async (configName: string) => {
      const response = await webAppApi.post(`/database/import/${configName}`)
      return response.data
    },
    onSuccess: (data) => {
      toast.success(data.message || 'Database imported successfully!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Import failed')
    },
  })

  const handleExport = () => {
    if (!exportName.trim()) {
      toast.error('Please enter an export name')
      return
    }
    if (confirm(`Export database to "${exportName}"? This will create a backup of Neo4j and PostgreSQL databases.`)) {
      exportMutation.mutate(exportName)
    }
  }

  const handleImport = () => {
    if (!importName.trim()) {
      toast.error('Please enter an import name')
      return
    }
    if (confirm(`Import database from "${importName}"? This will REPLACE all current data!`)) {
      importMutation.mutate(importName)
    }
  }

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold flex items-center gap-2">
          <Database className="h-8 w-8" />
          Database Management
        </h1>
        <p className="text-muted-foreground">
          Export and import your database configurations
        </p>
      </div>

      {/* Warning Banner */}
      <Card className="border-orange-500 bg-orange-50 dark:bg-orange-950">
        <CardContent className="flex items-start gap-3 p-4">
          <AlertCircle className="h-5 w-5 text-orange-600 mt-0.5" />
          <div className="space-y-1">
            <p className="font-semibold text-orange-900 dark:text-orange-100">
              Important Notice
            </p>
            <p className="text-sm text-orange-800 dark:text-orange-200">
              Importing a database will completely replace your current Neo4j and PostgreSQL data.
              Always export your current data before importing to avoid data loss.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Export Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Download className="h-5 w-5" />
            Export Database
          </CardTitle>
          <CardDescription>
            Create a backup of your current database configuration
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">Export Name</label>
            <Input
              placeholder="e.g., production-backup-2024"
              value={exportName}
              onChange={(e) => setExportName(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              This name will be used to identify the export for future imports
            </p>
          </div>
          <Button
            onClick={handleExport}
            disabled={exportMutation.isPending || !exportName.trim()}
            className="w-full"
          >
            {exportMutation.isPending ? (
              <>
                <LoadingSpinner className="mr-2" size="sm" />
                Exporting...
              </>
            ) : (
              <>
                <Download className="h-4 w-4 mr-2" />
                Export Database
              </>
            )}
          </Button>
        </CardContent>
      </Card>

      {/* Import Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Upload className="h-5 w-5" />
            Import Database
          </CardTitle>
          <CardDescription>
            Restore a database from a previous export
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">Import Name</label>
            <Input
              placeholder="e.g., production-backup-2024"
              value={importName}
              onChange={(e) => setImportName(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              Enter the name of a previously exported database
            </p>
          </div>
          <Button
            onClick={handleImport}
            disabled={importMutation.isPending || !importName.trim()}
            variant="destructive"
            className="w-full"
          >
            {importMutation.isPending ? (
              <>
                <LoadingSpinner className="mr-2" size="sm" />
                Importing...
              </>
            ) : (
              <>
                <Upload className="h-4 w-4 mr-2" />
                Import Database
              </>
            )}
          </Button>
        </CardContent>
      </Card>

      {/* Database Status */}
      <Card>
        <CardHeader>
          <CardTitle>Database Status</CardTitle>
          <CardDescription>Current system status</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="flex items-center justify-between p-3 bg-secondary rounded-lg">
              <div className="flex items-center gap-3">
                <div className="h-3 w-3 bg-green-500 rounded-full animate-pulse" />
                <span className="font-medium">Neo4j Graph Database</span>
              </div>
              <span className="text-sm text-green-600 dark:text-green-400">Connected</span>
            </div>
            <div className="flex items-center justify-between p-3 bg-secondary rounded-lg">
              <div className="flex items-center gap-3">
                <div className="h-3 w-3 bg-green-500 rounded-full animate-pulse" />
                <span className="font-medium">PostgreSQL Database</span>
              </div>
              <span className="text-sm text-green-600 dark:text-green-400">Connected</span>
            </div>
            <div className="flex items-center justify-between p-3 bg-secondary rounded-lg">
              <div className="flex items-center gap-3">
                <div className="h-3 w-3 bg-green-500 rounded-full animate-pulse" />
                <span className="font-medium">Analyzer Service</span>
              </div>
              <span className="text-sm text-green-600 dark:text-green-400">Online</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
