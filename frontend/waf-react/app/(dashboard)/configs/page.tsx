'use client'

import { useState, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { webAppApi } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
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
  Save,
  Plus,
  ChevronRight,
  ChevronLeft,
  Code,
  Settings
} from 'lucide-react'
import toast from 'react-hot-toast'
import { Config, ConfigContent, ConfigTreeResponse, ConfigTreeNode } from '@/types'
import { useConfigStore } from '@/stores/config'
import { formatDate } from '@/lib/utils'

export default function ConfigsPage() {
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false)
  const [configNickname, setConfigNickname] = useState('')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [selectedConfigForView, setSelectedConfigForView] = useState<Config | null>(null)
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

  // Create config dialog state
  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  const [createStep, setCreateStep] = useState(1)
  const [createFormData, setCreateFormData] = useState({
    name: '',
    description: '',
    stack: '',
    crsVersion: '',
    apps: {
      wordpress: false,
      drupal: false,
      nextcloud: false,
      dokuwiki: false,
      cpanel: false,
      xenforo: false,
    },
    customRules: '',
  })

  // Mock data - will be fetched from backend
  const STACKS = [
    { value: 'apache-modsecurity', label: 'Apache + ModSecurity' },
    { value: 'nginx-modsecurity', label: 'Nginx + ModSecurity' },
    { value: 'nginx-naxsi', label: 'Nginx + NAXSI' },
    { value: 'haproxy', label: 'HAProxy' },
    { value: 'cloudflare', label: 'Cloudflare WAF' },
  ] as const

  const CRS_VERSIONS = [
    { value: '4.0.0', label: 'CRS 4.0.0 (Latest)' },
    { value: '3.3.5', label: 'CRS 3.3.5' },
    { value: '3.3.4', label: 'CRS 3.3.4' },
    { value: '3.3.2', label: 'CRS 3.3.2' },
    { value: '3.2.0', label: 'CRS 3.2.0 (Legacy)' },
  ] as const

  const APPS = [
    { key: 'wordpress', label: 'WordPress', description: 'CMS exclusion rules for WordPress core, plugins, and themes' },
    { key: 'drupal', label: 'Drupal', description: 'CMS exclusion rules for Drupal core and modules' },
    { key: 'nextcloud', label: 'Nextcloud', description: 'File sync and share platform exclusion rules' },
    { key: 'dokuwiki', label: 'DokuWiki', description: 'Wiki software exclusion rules' },
    { key: 'cpanel', label: 'cPanel', description: 'Web hosting control panel exclusion rules' },
    { key: 'xenforo', label: 'XenForo', description: 'Forum software exclusion rules' },
  ] as const

  // Fetch configs
  const { data: configsData, isLoading } = useQuery({
    queryKey: ['configs'],
    queryFn: async () => {
      const response = await webAppApi.get<Config[]>('/api/v1/configurations')
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
      const response = await webAppApi.get('/api/v1/auth/me')
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
      formData.append('name', configNickname)
      const response = await webAppApi.post('/api/v1/configurations', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      return response.data
    },
    onSuccess: () => {
      toast.success('Configuration uploaded successfully!')
      queryClient.invalidateQueries({ queryKey: ['configs'] })
      setUploadDialogOpen(false)
      setConfigNickname('')
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
      const response = await webAppApi.put('/api/v1/auth/me/active-config', {
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
      const response = await webAppApi.delete(`/api/v1/configurations/${configId}`)
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

  // Analyze config mutation
  const analyzeMutation = useMutation({
    mutationFn: async (configId: number) => {
      const response = await webAppApi.post(`/configs/analyze/${configId}`)
      return response.data
    },
    onSuccess: () => {
      toast.success('Analysis started! This may take a while.')
      queryClient.invalidateQueries({ queryKey: ['configs'] })
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to start analysis')
    },
  })

  // Save file mutation
  const saveFileMutation = useMutation({
    mutationFn: async () => {
      if (!selectedConfigForView || !selectedFilePath) {
        throw new Error('No file selected')
      }
      const response = await webAppApi.put(
        `/api/v1/configurations/${selectedConfigForView.id}/files/${selectedFilePath}`,
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

  // Create config mutation
  const createConfigMutation = useMutation({
    mutationFn: async () => {
      const response = await webAppApi.post('/api/v1/configurations/create', {
        name: createFormData.name,
        description: createFormData.description,
        stack: createFormData.stack,
        crs_version: createFormData.crsVersion,
        apps: createFormData.apps,
        custom_rules: createFormData.customRules,
      })
      return response.data
    },
    onSuccess: () => {
      toast.success('Configuration created successfully!')
      queryClient.invalidateQueries({ queryKey: ['configs'] })
      handleCloseCreateDialog()
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to create configuration')
    },
  })

  const handleCloseCreateDialog = () => {
    setCreateDialogOpen(false)
    setCreateStep(1)
    setCreateFormData({
      name: '',
      description: '',
      stack: '',
      crsVersion: '',
      apps: {
        wordpress: false,
        drupal: false,
        nextcloud: false,
        dokuwiki: false,
        cpanel: false,
        xenforo: false,
      },
      customRules: '',
    })
  }

  const handleAppToggle = (appKey: string) => {
    setCreateFormData(prev => ({
      ...prev,
      apps: {
        ...prev.apps,
        [appKey]: !prev.apps[appKey as keyof typeof prev.apps],
      },
    }))
  }

  const getEnabledAppsCount = () => {
    return Object.values(createFormData.apps).filter(Boolean).length
  }

  const handleNextStep = () => {
    if (createStep === 1 && !createFormData.name.trim()) {
      toast.error('Please provide a configuration name')
      return
    }
    if (createStep === 2 && (!createFormData.stack || !createFormData.crsVersion)) {
      toast.error('Please select a stack and CRS version')
      return
    }
    if (createStep < 4) {
      setCreateStep(prev => prev + 1)
    }
  }

  const handlePrevStep = () => {
    if (createStep > 1) {
      setCreateStep(prev => prev - 1)
    }
  }

  const handleCreateConfig = () => {
    createConfigMutation.mutate()
  }

  const handleUpload = () => {
    if (!selectedFile || !configNickname) {
      toast.error('Please provide both file and nickname')
      return
    }
    uploadMutation.mutate()
  }

  const handleViewConfig = async (config: Config) => {
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
      const response = await webAppApi.get<ConfigTreeResponse>(
        `/api/v1/configurations/${configId}/tree`,
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
        const response = await webAppApi.get<ConfigTreeResponse>(
          `/api/v1/configurations/${selectedConfigForView.id}/tree`,
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

  // Simplified step indicator component
  const StepIndicator = ({ currentStep, totalSteps }: { currentStep: number; totalSteps: number }) => (
    <div className="flex items-center justify-center gap-2 mb-6">
      {Array.from({ length: totalSteps }, (_, i) => i + 1).map((step, index) => (
        <div key={step} className="flex items-center">
          <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-colors ${
            step <= currentStep ? 'bg-primary text-primary-foreground' : 'bg-gray-200 text-gray-600'
          }`}>
            {step < currentStep ? <CheckCircle className="h-4 w-4" /> : step}
          </div>
          {index < totalSteps - 1 && (
            <div className={`w-12 h-1 mx-1 transition-colors ${
              step < currentStep ? 'bg-primary' : 'bg-gray-200'
            }`} />
          )}
        </div>
      ))}
    </div>
  )

  // Consolidated config status banner component
  const ConfigStatusBanner = () => {
    if (!selectedConfig) {
      return (
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
      )
    }

    return (
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
              <p className="text-sm text-muted-foreground mt-1">
                ID: {selectedConfig.id} • Created: {formatDate(selectedConfig.created_at)}
              </p>
            </div>
          </div>
          <div className="flex flex-col items-end gap-2">
            {selectedConfig.parsed && (
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
        <div className="flex gap-2">
          <Button variant="outline" className="gap-2" onClick={() => setCreateDialogOpen(true)}>
            <Plus className="h-4 w-4" />
            Create Config
          </Button>
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
                <label className="text-sm font-medium mb-2 block">Configuration Nickname</label>
                <Input
                  placeholder="e.g., Production WAF Config"
                  value={configNickname}
                  onChange={(e) => setConfigNickname(e.target.value)}
                />
              </div>
              <div>
                <label className="text-sm font-medium mb-2 block">Configuration File (ZIP/TAR)</label>
                <Input
                  ref={fileInputRef}
                  type="file"
                  accept=".zip,.tar,.tar.gz"
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
      </div>

      {/* Create Config Multi-Phase Dialog */}
      <Dialog open={createDialogOpen} onOpenChange={(open) => !open && handleCloseCreateDialog()}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Settings className="h-5 w-5" />
              Create Configuration - Step {createStep} of 4
            </DialogTitle>
          </DialogHeader>

          {/* Progress Steps - Simplified */}
          <StepIndicator currentStep={createStep} totalSteps={4} />

          {/* Step 1: Basic Info */}
          {createStep === 1 && (
            <div className="space-y-4">
              <div className="flex items-center gap-2 mb-4">
                <FileCode className="h-5 w-5 text-primary" />
                <h3 className="text-lg font-semibold">Basic Information</h3>
              </div>
              <div>
                <label className="text-sm font-medium mb-2 block">Configuration Name *</label>
                <Input
                  placeholder="e.g., Production WAF Rules"
                  value={createFormData.name}
                  onChange={(e) => setCreateFormData(prev => ({ ...prev, name: e.target.value }))}
                />
              </div>
              <div>
                <label className="text-sm font-medium mb-2 block">Description</label>
                <textarea
                  className="w-full min-h-[100px] px-3 py-2 border border-input rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                  placeholder="Describe the purpose of this configuration..."
                  value={createFormData.description}
                  onChange={(e) => setCreateFormData(prev => ({ ...prev, description: e.target.value }))}
                />
              </div>
            </div>
          )}

          {/* Step 2: Stack & Apps Configuration */}
          {createStep === 2 && (
            <div className="space-y-6">
              <div className="flex items-center gap-2 mb-4">
                <Settings className="h-5 w-5 text-primary" />
                <h3 className="text-lg font-semibold">Stack & Apps Configuration</h3>
              </div>

              {/* Stack Selection */}
              <div className="space-y-2">
                <label className="text-sm font-medium">Stack *</label>
                <Select
                  value={createFormData.stack}
                  onValueChange={(value) => setCreateFormData(prev => ({ ...prev, stack: value }))}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select a stack..." />
                  </SelectTrigger>
                  <SelectContent>
                    {STACKS.map((stack) => (
                      <SelectItem key={stack.value} value={stack.value}>
                        {stack.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* CRS Version Selection */}
              <div className="space-y-2">
                <label className="text-sm font-medium">CRS Version *</label>
                <Select
                  value={createFormData.crsVersion}
                  onValueChange={(value) => setCreateFormData(prev => ({ ...prev, crsVersion: value }))}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select CRS version..." />
                  </SelectTrigger>
                  <SelectContent>
                    {CRS_VERSIONS.map((version) => (
                      <SelectItem key={version.value} value={version.value}>
                        {version.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Apps Section */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <label className="text-sm font-medium">Application Exclusion Rules</label>
                  <span className="text-sm text-muted-foreground">
                    {getEnabledAppsCount()} of {APPS.length} enabled
                  </span>
                </div>
                <p className="text-xs text-muted-foreground">
                  Enable exclusion rules for specific applications to reduce false positives.
                </p>
                <div className="grid gap-3 max-h-[200px] overflow-y-auto pr-2">
                  {APPS.map((app) => (
                    <div
                      key={app.key}
                      className={`flex items-center justify-between p-3 border rounded-lg transition-colors ${
                        createFormData.apps[app.key as keyof typeof createFormData.apps]
                          ? 'border-primary bg-primary/5'
                          : 'border-gray-200 hover:border-gray-300'
                      }`}
                    >
                      <div className="flex-1 cursor-pointer" onClick={() => handleAppToggle(app.key)}>
                        <p className="font-medium text-sm">{app.label}</p>
                        <p className="text-xs text-muted-foreground">{app.description}</p>
                      </div>
                      <Switch
                        checked={createFormData.apps[app.key as keyof typeof createFormData.apps]}
                        onCheckedChange={() => handleAppToggle(app.key)}
                      />
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Step 3: Custom Rules */}
          {createStep === 3 && (
            <div className="space-y-4">
              <div className="flex items-center gap-2 mb-4">
                <Code className="h-5 w-5 text-primary" />
                <h3 className="text-lg font-semibold">Custom Rules (Optional)</h3>
              </div>
              <p className="text-sm text-muted-foreground">
                Add custom ModSecurity rules below. Leave empty to use only the standard rules selected in the previous step.
              </p>
              <textarea
                className="w-full min-h-[250px] px-3 py-2 border border-input rounded-md text-sm font-mono focus:outline-none focus:ring-2 focus:ring-ring"
                placeholder={`# Example custom rule:
SecRule REQUEST_URI "@contains /admin" "id:100001,phase:1,deny,status:403,msg:'Admin access blocked'"

# Add your custom ModSecurity rules here...`}
                value={createFormData.customRules}
                onChange={(e) => setCreateFormData(prev => ({ ...prev, customRules: e.target.value }))}
              />
            </div>
          )}

          {/* Step 4: Review */}
          {createStep === 4 && (
            <div className="space-y-4">
              <div className="flex items-center gap-2 mb-4">
                <CheckCircle className="h-5 w-5 text-primary" />
                <h3 className="text-lg font-semibold">Review Configuration</h3>
              </div>
              <div className="space-y-4 bg-gray-50 p-4 rounded-lg">
                <div>
                  <p className="text-xs text-muted-foreground uppercase tracking-wide">Name</p>
                  <p className="font-medium">{createFormData.name}</p>
                </div>
                {createFormData.description && (
                  <div>
                    <p className="text-xs text-muted-foreground uppercase tracking-wide">Description</p>
                    <p className="text-sm">{createFormData.description}</p>
                  </div>
                )}
                <div>
                  <p className="text-xs text-muted-foreground uppercase tracking-wide">Stack</p>
                  <p className="font-medium">{STACKS.find(s => s.value === createFormData.stack)?.label || createFormData.stack}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground uppercase tracking-wide">CRS Version</p>
                  <p className="font-medium">{CRS_VERSIONS.find(v => v.value === createFormData.crsVersion)?.label || createFormData.crsVersion}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground uppercase tracking-wide mb-2">Enabled Apps</p>
                  <div className="flex flex-wrap gap-2">
                    {APPS.filter(app => createFormData.apps[app.key as keyof typeof createFormData.apps]).map(app => (
                      <span key={app.key} className="text-xs bg-primary/10 text-primary px-2 py-1 rounded-full">
                        {app.label}
                      </span>
                    ))}
                    {Object.values(createFormData.apps).every(v => !v) && (
                      <span className="text-xs text-muted-foreground">No apps selected</span>
                    )}
                  </div>
                </div>
                {createFormData.customRules && (
                  <div>
                    <p className="text-xs text-muted-foreground uppercase tracking-wide">Custom Rules</p>
                    <p className="text-sm text-green-600">{createFormData.customRules.split('\n').filter(l => l.trim() && !l.trim().startsWith('#')).length} custom rule(s) defined</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Navigation Buttons */}
          <div className="flex justify-between mt-6 pt-4 border-t">
            <Button
              variant="outline"
              onClick={handlePrevStep}
              disabled={createStep === 1}
              className="gap-2"
            >
              <ChevronLeft className="h-4 w-4" />
              Previous
            </Button>
            {createStep < 4 ? (
              <Button onClick={handleNextStep} className="gap-2">
                Next
                <ChevronRight className="h-4 w-4" />
              </Button>
            ) : (
              <Button
                onClick={handleCreateConfig}
                disabled={createConfigMutation.isPending}
                className="gap-2"
              >
                {createConfigMutation.isPending ? 'Creating...' : 'Create Configuration'}
                <CheckCircle className="h-4 w-4" />
              </Button>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Consolidated Config Status Banner */}
      <ConfigStatusBanner />

      {/* Configs List */}
      {isLoading ? (
        <LoadingSpinner />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {configsData?.configs?.map((config: Config) => (
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
                  {config.parsing_status !== 'parsed' && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => analyzeMutation.mutate(config.id)}
                      disabled={analyzeMutation.isPending}
                    >
                      <Play className="h-4 w-4 mr-1" />
                      Analyze
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
