'use client'

import { useState, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { LoadingSpinner } from '@/components/ui/loading-spinner'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { CodeEditor } from '@/components/editor/CodeEditor'
import { 
  Upload, 
  FileCode, 
  Trash2, 
  Play, 
  CheckCircle, 
  AlertCircle, 
  Clock,
  FolderOpen,
  File,
  Save
} from 'lucide-react'
import toast from 'react-hot-toast'
import { ConfigurationResponse, ConfigContent, ConfigTreeResponse, ConfigTreeNode } from '@/types'
import { useConfigStore } from '@/stores/config'
import { formatDate } from '@/lib/utils'

export default function ConfigsPage() {
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false)
  const [configName, setConfigName] = useState('')
  const [configDescription, setConfigDescription] = useState('')
  const [wafUrl, setWafUrl] = useState('http://waf:80')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [selectedConfigForView, setSelectedConfigForView] = useState<ConfigurationResponse | null>(null)
  const [viewDialogOpen, setViewDialogOpen] = useState(false)
  const [selectedFilePath, setSelectedFilePath] = useState<string>('')
  const [currentPath, setCurrentPath] = useState<string>('')
  const [fileContent, setFileContent] = useState('')
  const [originalFileContent, setOriginalFileContent] = useState('')
  const [isFileModified, setIsFileModified] = useState(false)
  const [fileTree, setFileTree] = useState<ConfigContent[]>([])
  const [isLoadingFiles, setIsLoadingFiles] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const queryClient = useQueryClient()
  const { selectedConfig, selectedConfigId, setSelectedConfig, configs, setConfigs } = useConfigStore()

  // Fetch configs
  const { data: configsData, isLoading } = useQuery({
    queryKey: ['configs'],
    queryFn: async () => {
      const response = await api.get<ConfigurationResponse[]>('/configurations')
      setConfigs(response.data)

      // Restore selected config from localStorage
      if (selectedConfigId) {
        const selected = response.data.find((c) => c.id === selectedConfigId)
        if (selected) {
          setSelectedConfig(selected)
        }
      }

      return { configs: response.data }
    },
  })

  // Fetch selected config from user info
  const { data: userInfo } = useQuery({
    queryKey: ['user-info'],
    queryFn: async () => {
      const response = await api.get('/auth/me')
      if (response.data.active_configuration_id) {
        const selected = configs.find((c) => c.id === response.data.active_configuration_id)
        if (selected) {
          setSelectedConfig(selected)
        }
      }
      return response.data
    },
    enabled: configs.length > 0, // Only run when configs are loaded
  })

  // Upload mutation
  const uploadMutation = useMutation({
    mutationFn: async () => {
      const formData = new FormData()
      formData.append('file', selectedFile!)
      formData.append('name', configName)
      if (configDescription) {
        formData.append('description', configDescription)
      }
      const response = await api.post('/configurations', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      return response.data
    },
    onSuccess: () => {
      toast.success('Configuration uploaded successfully!')
      queryClient.invalidateQueries({ queryKey: ['configs'] })
      setUploadDialogOpen(false)
      setConfigName('')
      setConfigDescription('')
      setSelectedFile(null)
      if (fileInputRef.current) fileInputRef.current.value = ''
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to upload configuration')
    },
  })

  // Select config mutation - only allow parsed configs
  const selectMutation = useMutation({
    mutationFn: async (configId: number) => {
      const config = configs.find((c) => c.id === configId)
      if (config?.parsing_status !== 'parsed') {
        throw new Error('Only analyzed configurations can be selected')
      }
      const response = await api.put('/auth/me/active-config', {
        configuration_id: configId
      })
      return response.data
    },
    onSuccess: (_, configId) => {
      const selected = configs.find((c) => c.id === configId)
      setSelectedConfig(selected || null)
      toast.success('Configuration selected and saved!')
      queryClient.invalidateQueries({ queryKey: ['user-info'] })
    },
    onError: (error: any) => {
      toast.error(error.message || error.response?.data?.detail || 'Failed to select configuration')
    },
  })

  // Delete config mutation
  const deleteMutation = useMutation({
    mutationFn: async (configId: number) => {
      const response = await api.delete(`/configurations/${configId}`)
      return response.data
    },
    onSuccess: () => {
      toast.success('Configuration deleted!')
      queryClient.invalidateQueries({ queryKey: ['configs'] })
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to delete configuration')
    },
  })

  // Parse config mutation
  const parseMutation = useMutation({
    mutationFn: async (configId: number) => {
      const response = await api.post(`/parser/parse/${configId}`)
      return response.data
    },
    onSuccess: () => {
      toast.success('Parsing started! This may take a while.')
      queryClient.invalidateQueries({ queryKey: ['configs'] })
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to start parsing')
    },
  })

  // Save file mutation
  const saveFileMutation = useMutation({
    mutationFn: async () => {
      if (!selectedConfigForView || !selectedFilePath) {
        throw new Error('No file selected')
      }
      const response = await api.put(
        `/configurations/${selectedConfigForView.id}/files/${encodeURIComponent(selectedFilePath)}`,
        {
          content: fileContent,
        }
      )
      return response.data
    },
    onSuccess: () => {
      toast.success('File saved successfully!')
      setOriginalFileContent(fileContent)
      setIsFileModified(false)
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to save file')
    },
  })

  const handleUpload = () => {
    if (!selectedFile || !configName) {
      toast.error('Please provide both file and name')
      return
    }
    uploadMutation.mutate()
  }

  const handleViewConfig = async (config: ConfigurationResponse) => {
    setSelectedConfigForView(config)
    setViewDialogOpen(true)
    setSelectedFilePath('')
    setCurrentPath('')
    setFileContent('')
    setOriginalFileContent('')
    setIsFileModified(false)
    setFileTree([])
    
    // Load root directory files
    await loadConfigFiles(config.id, '')
  }

  const loadConfigFiles = async (configId: number, path: string) => {
    setIsLoadingFiles(true)
    try {
      const response = await api.get<ConfigTreeResponse>(
        `/configurations/${configId}/tree`,
        {
          params: { path: path || '/' }
        }
      )

      // Convert new API response to legacy format for UI compatibility
      if (response.data.is_file) {
        // If it's a file, we shouldn't be here (this is for directory listing)
        // But handle it gracefully
        setFileTree([])
      } else {
        // Convert children array to ConfigContent format
        const legacyFormat: ConfigContent[] = response.data.children?.map((node: ConfigTreeNode) => ({
          filename: node.name,
          is_folder: node.type === 'directory',
          file_content: null
        })) || []
        setFileTree(legacyFormat)
      }
      setCurrentPath(path)
    } catch (error: any) {
      console.error('Failed to load files:', error)
      toast.error(error.response?.data?.detail || 'Failed to load files')
    } finally {
      setIsLoadingFiles(false)
    }
  }

  const handleFileClick = async (item: ConfigContent) => {
    if (!selectedConfigForView) return

    const newPath = currentPath ? `${currentPath}/${item.filename}` : item.filename

    if (item.is_folder) {
      // Load folder contents
      await loadConfigFiles(selectedConfigForView.id, newPath)
    } else {
      // Load file content
      setIsLoadingFiles(true)
      try {
        const response = await api.get<ConfigTreeResponse>(
          `/configurations/${selectedConfigForView.id}/tree`,
          {
            params: { path: newPath }
          }
        )

        if (response.data.is_file && response.data.content) {
          setFileContent(response.data.content)
          setOriginalFileContent(response.data.content)
          setSelectedFilePath(newPath)
          setIsFileModified(false)
        }
      } catch (error: any) {
        console.error('Failed to load file:', error)
        toast.error(error.response?.data?.detail || 'Failed to load file')
      } finally {
        setIsLoadingFiles(false)
      }
    }
  }

  const handleBackNavigation = () => {
    if (!selectedConfigForView || !currentPath) return
    
    const pathParts = currentPath.split('/')
    pathParts.pop()
    const parentPath = pathParts.join('/')
    
    loadConfigFiles(selectedConfigForView.id, parentPath)
  }

  const handleFileContentChange = (value: string | undefined) => {
    const newContent = value || ''
    setFileContent(newContent)
    setIsFileModified(newContent !== originalFileContent)
  }

  const handleSaveFile = () => {
    if (!isFileModified) {
      toast.error('No changes to save')
      return
    }
    saveFileMutation.mutate()
  }

  const getLanguageFromFilename = (filename: string): string => {
    const ext = filename.split('.').pop()?.toLowerCase()
    const languageMap: Record<string, string> = {
      'conf': 'apache',
      'config': 'apache',
      'htaccess': 'apache',
      'json': 'json',
      'xml': 'xml',
      'yaml': 'yaml',
      'yml': 'yaml',
      'sh': 'shell',
      'bash': 'shell',
      'py': 'python',
      'js': 'javascript',
      'ts': 'typescript',
      'html': 'html',
      'css': 'css',
      'md': 'markdown',
      'txt': 'plaintext',
    }
    return languageMap[ext || ''] || 'apache'
  }

  const renderFileTree = () => {
    if (isLoadingFiles) {
      return (
        <div className="flex items-center justify-center py-8">
          <LoadingSpinner />
        </div>
      )
    }

    return (
      <div className="space-y-1">
        {currentPath && (
          <div 
            className="flex items-center gap-2 p-2 hover:bg-accent rounded cursor-pointer text-primary font-medium"
            onClick={handleBackNavigation}
          >
            <FolderOpen className="h-4 w-4" />
            <span className="text-sm">.. (Back)</span>
          </div>
        )}
        {fileTree.map((item, index) => (
          <div 
            key={index}
            className="flex items-center gap-2 p-2 hover:bg-accent rounded cursor-pointer"
            onClick={() => handleFileClick(item)}
          >
            {item.is_folder ? (
              <FolderOpen className="h-4 w-4 text-blue-600" />
            ) : (
              <File className="h-4 w-4 text-gray-600" />
            )}
            <span className="text-sm">{item.filename}</span>
          </div>
        ))}
        {fileTree.length === 0 && !currentPath && (
          <div className="text-sm text-muted-foreground p-2">
            No files found
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold">Configurations</h1>
          <p className="text-muted-foreground">Manage your WAF configuration files</p>
        </div>
        <Dialog open={uploadDialogOpen} onOpenChange={setUploadDialogOpen}>
          <DialogTrigger asChild>
            <Button className="gap-2">
              <Upload className="h-4 w-4" />
              Upload Configuration
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Upload Configuration</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 mt-4">
              <div>
                <label className="text-sm font-medium mb-2 block">Configuration Name</label>
                <Input
                  placeholder="e.g., Production WAF Config"
                  value={configName}
                  onChange={(e) => setConfigName(e.target.value)}
                />
              </div>
              <div>
                <label className="text-sm font-medium mb-2 block">Description (Optional)</label>
                <Input
                  placeholder="e.g., Production environment configuration"
                  value={configDescription}
                  onChange={(e) => setConfigDescription(e.target.value)}
                />
              </div>
              <div>
                <label className="text-sm font-medium mb-2 block">Configuration File (ZIP)</label>
                <Input
                  ref={fileInputRef}
                  type="file"
                  accept=".zip"
                  onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                />
              </div>
              <Button 
                className="w-full" 
                onClick={handleUpload}
                disabled={uploadMutation.isPending}
              >
                {uploadMutation.isPending ? 'Uploading...' : 'Upload'}
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {/* Selected Config Banner - More Prominent */}
      {selectedConfig && (
        <Card className="border-l-4 border-l-primary bg-gradient-to-r from-primary/10 via-primary/5 to-transparent shadow-md">
          <CardContent className="flex items-center justify-between p-6">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-primary/20 rounded-full">
                <CheckCircle className="h-6 w-6 text-primary" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground uppercase tracking-wide font-medium mb-1">
                  Active Configuration
                </p>
                <p className="text-xl font-bold text-foreground">{selectedConfig.name}</p>
                {selectedConfig.description && (
                  <p className="text-sm text-muted-foreground mt-1">{selectedConfig.description}</p>
                )}
                <p className="text-sm text-muted-foreground mt-1">
                  ID: {selectedConfig.id} • Created: {formatDate(selectedConfig.created_at)}
                </p>
              </div>
            </div>
            <div className="flex flex-col items-end gap-2">
              {selectedConfig.parsing_status === 'parsed' && (
                <span className="text-xs bg-green-100 text-green-800 px-3 py-1.5 rounded-full font-medium">
                  ✓ Analyzed
                </span>
              )}
              <span className="text-xs text-muted-foreground">
                Saved in local storage
              </span>
            </div>
          </CardContent>
        </Card>
      )}

      {!selectedConfig && (
        <Card className="border-l-4 border-l-yellow-500 bg-yellow-50">
          <CardContent className="flex items-center gap-3 p-4">
            <AlertCircle className="h-5 w-5 text-yellow-600" />
            <div>
              <p className="font-medium text-yellow-900">No Configuration Selected</p>
              <p className="text-sm text-yellow-700">
                Please select an analyzed configuration to work with
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Configs List */}
      {isLoading ? (
        <LoadingSpinner />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {configsData?.configs?.map((config: ConfigurationResponse) => (
            <Card 
              key={config.id} 
              className={`hover:shadow-lg transition-all relative ${
                selectedConfig?.id === config.id 
                  ? 'ring-2 ring-primary shadow-xl border-primary bg-primary/5' 
                  : ''
              }`}
            >
              {selectedConfig?.id === config.id && (
                <div className="absolute -top-2 -right-2 bg-primary text-primary-foreground px-3 py-1 rounded-full text-xs font-bold shadow-lg">
                  ACTIVE
                </div>
              )}
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2">
                    <FileCode className="h-5 w-5 text-primary" />
                    <CardTitle className="text-lg">{config.name}</CardTitle>
                  </div>
                  <div className="flex items-center gap-2">
                    {config.parsing_status === 'parsed' ? (
                      <span className="flex items-center gap-1 text-xs bg-green-100 text-green-800 px-2 py-1 rounded-full">
                        <CheckCircle className="h-3 w-3" />
                        Analyzed
                      </span>
                    ) : config.parsing_status === 'parsing' ? (
                      <span className="flex items-center gap-1 text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded-full">
                        <Clock className="h-3 w-3" />
                        Parsing
                      </span>
                    ) : config.parsing_status === 'error' ? (
                      <span className="flex items-center gap-1 text-xs bg-red-100 text-red-800 px-2 py-1 rounded-full">
                        <Clock className="h-3 w-3" />
                        Error
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 text-xs bg-gray-100 text-gray-800 px-2 py-1 rounded-full">
                        <Clock className="h-3 w-3" />
                        Not Parsed
                      </span>
                    )}
                  </div>
                </div>
                <CardDescription className="flex items-center justify-between">
                  <span>Created: {formatDate(config.created_at)}</span>
                  <span className="text-xs">ID: {config.id}</span>
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-2">
                <div className="flex flex-wrap gap-2">
                  <Button
                    size="sm"
                    variant={selectedConfig?.id === config.id ? 'default' : 'outline'}
                    onClick={() => selectMutation.mutate(config.id)}
                    disabled={selectMutation.isPending || config.parsing_status !== 'parsed'}
                    title={config.parsing_status !== 'parsed' ? 'Config must be analyzed before selection' : ''}
                  >
                    {selectedConfig?.id === config.id ? (
                      <>
                        <CheckCircle className="h-3 w-3 mr-1" />
                        Selected
                      </>
                    ) : (
                      'Select'
                    )}
                  </Button>
                  {config.parsing_status !== 'parsed' && config.parsing_status !== 'parsing' && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => parseMutation.mutate(config.id)}
                      disabled={parseMutation.isPending}
                    >
                      <Play className="h-4 w-4 mr-1" />
                      Parse
                    </Button>
                  )}
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleViewConfig(config)}
                  >
                    <FolderOpen className="h-4 w-4 mr-1" />
                    View Files
                  </Button>
                  <Button
                    size="sm"
                    variant="destructive"
                    onClick={() => {
                      if (confirm('Are you sure you want to delete this configuration?')) {
                        deleteMutation.mutate(config.id)
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

      {/* View Config Dialog with File Editor */}
      <Dialog open={viewDialogOpen} onOpenChange={setViewDialogOpen}>
        <DialogContent className="max-w-[90vw] w-[90vw] max-h-[90vh] p-0 gap-0">
          <DialogHeader className="px-6 pt-6 pb-4 border-b flex-shrink-0">
            <DialogTitle>
              {selectedConfigForView?.name} - Configuration Files
            </DialogTitle>
          </DialogHeader>
          <div className="flex gap-4 px-6 py-4" style={{ height: 'calc(90vh - 100px)' }}>
            {/* File Tree */}
            <div className="w-64 border-r pr-4 flex flex-col overflow-hidden">
              <h3 className="font-semibold mb-2 flex items-center gap-1 flex-shrink-0">
                <FolderOpen className="h-4 w-4" />
                <span className="truncate text-sm">Files</span>
              </h3>
              {currentPath && (
                <div className="text-xs text-muted-foreground mb-2 truncate flex-shrink-0">
                  Path: {currentPath}
                </div>
              )}
              <div className="flex-1 overflow-y-auto overflow-x-hidden">
                {renderFileTree()}
              </div>
            </div>
            {/* Editor */}
            <div className="flex-1 flex flex-col overflow-hidden">
              {selectedFilePath ? (
                <>
                  <div className="mb-2 flex items-center justify-between flex-shrink-0 gap-4">
                    <span className="text-sm font-medium truncate">{selectedFilePath}</span>
                    <div className="flex gap-2 flex-shrink-0">
                      {isFileModified && (
                        <span className="text-xs bg-orange-100 text-orange-800 px-2 py-1 rounded flex items-center gap-1">
                          <AlertCircle className="h-3 w-3" />
                          Modified
                        </span>
                      )}
                      <Button 
                        size="sm" 
                        variant={isFileModified ? "default" : "outline"}
                        onClick={handleSaveFile}
                        disabled={!isFileModified || saveFileMutation.isPending}
                      >
                        <Save className="h-3 w-3 mr-1" />
                        {saveFileMutation.isPending ? 'Saving...' : 'Save'}
                      </Button>
                    </div>
                  </div>
                  <div className="flex-1 border rounded overflow-hidden bg-white">
                    <CodeEditor
                      value={fileContent}
                      onChange={handleFileContentChange}
                      language={getLanguageFromFilename(selectedFilePath)}
                      height="100%"
                    />
                  </div>
                </>
              ) : (
                <div className="flex-1 flex items-center justify-center text-muted-foreground border rounded bg-gray-50">
                  <div className="text-center">
                    <File className="h-12 w-12 mx-auto mb-2 opacity-50" />
                    <p className="font-medium">Select a file to view its contents</p>
                    {fileTree.length === 0 && !isLoadingFiles && (
                      <p className="text-xs mt-2">Browse files from the tree on the left</p>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Empty State */}
      {!isLoading && configsData?.configs?.length === 0 && (
        <Card className="p-12 text-center">
          <FileCode className="h-16 w-16 mx-auto text-muted-foreground mb-4" />
          <h3 className="text-xl font-semibold mb-2">No Configurations Yet</h3>
          <p className="text-muted-foreground mb-6">
            Get started by uploading your first WAF configuration
          </p>
          <Button onClick={() => setUploadDialogOpen(true)}>
            <Upload className="h-4 w-4 mr-2" />
            Upload Configuration
          </Button>
        </Card>
      )}
    </div>
  )
}
