'use client'

import { useQuery } from '@tanstack/react-query'
import { checkWafHealth, checkAnalyzerHealth, checkChatbotHealth, checkWebAppHealth } from '@/lib/service-health'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { LoadingSpinner } from '@/components/ui/loading-spinner'
import { Server, CheckCircle, XCircle, AlertCircle, Activity } from 'lucide-react'

interface ServiceStatus {
  name: string
  url: string
  status: 'online' | 'offline' | 'checking'
  icon: any
  color: string
  description: string
}

export default function ServicesPage() {
  // Check WAF service
  const { data: wafStatus, isLoading: wafLoading } = useQuery({
    queryKey: ['service-waf'],
    queryFn: async () => {
      const health = await checkWafHealth()
      return health.status
    },
    refetchInterval: 30000, // Refetch every 30 seconds
  })

  // Check Analyzer service
  const { data: analyzerStatus, isLoading: analyzerLoading } = useQuery({
    queryKey: ['service-analyzer'],
    queryFn: async () => {
      const health = await checkAnalyzerHealth()
      return health.status
    },
    refetchInterval: 30000,
  })

  // Check Chatbot service
  const { data: chatbotStatus, isLoading: chatbotLoading } = useQuery({
    queryKey: ['service-chatbot'],
    queryFn: async () => {
      const health = await checkChatbotHealth()
      return health.status
    },
    refetchInterval: 30000,
  })

  // Check Web App service
  const { data: webAppStatus, isLoading: webAppLoading } = useQuery({
    queryKey: ['service-webapp'],
    queryFn: async () => {
      const health = await checkWebAppHealth()
      return health.status
    },
    refetchInterval: 30000,
  })

  const services: ServiceStatus[] = [
    {
      name: 'FastAPI (Web App)',
      url: process.env.NEXT_PUBLIC_WEB_APP_API_URL || 'http://localhost:8000',
      status: webAppLoading ? 'checking' : (webAppStatus as any || 'offline'),
      icon: Server,
      color: 'blue',
      description: 'Main API service for configuration management',
    },
    {
      name: 'Chatbot Service',
      url: process.env.NEXT_PUBLIC_CHATBOT_API_URL || 'http://localhost:8005',
      status: chatbotLoading ? 'checking' : (chatbotStatus as any || 'offline'),
      icon: Activity,
      color: 'purple',
      description: 'AI chatbot with LangGraph integration',
    },
    {
      name: 'Analyzer Service',
      url: process.env.NEXT_PUBLIC_ANALYZER_API_URL || 'http://localhost:8001',
      status: analyzerLoading ? 'checking' : (analyzerStatus as any || 'offline'),
      icon: Server,
      color: 'green',
      description: 'Configuration analysis and parsing service',
    },
    {
      name: 'WAF Service',
      url: process.env.NEXT_PUBLIC_WAF_API_URL || 'http://localhost:9090',
      status: wafLoading ? 'checking' : (wafStatus as any || 'offline'),
      icon: Server,
      color: 'orange',
      description: 'Apache WAF configuration dump service',
    },
  ]

  const getStatusIcon = (status: string) => {
    if (status === 'checking') return <LoadingSpinner size="sm" />
    if (status === 'online') return <CheckCircle className="h-5 w-5 text-green-600" />
    return <XCircle className="h-5 w-5 text-red-600" />
  }

  const getStatusBadge = (status: string) => {
    if (status === 'checking') {
      return (
        <span className="text-xs bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200 px-2 py-1 rounded">
          Checking...
        </span>
      )
    }
    if (status === 'online') {
      return (
        <span className="text-xs bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200 px-2 py-1 rounded">
          Online
        </span>
      )
    }
    return (
      <span className="text-xs bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200 px-2 py-1 rounded">
        Offline
      </span>
    )
  }

  const onlineCount = services.filter(s => s.status === 'online').length
  const offlineCount = services.filter(s => s.status === 'offline').length

  return (
    <div className="space-y-6 max-w-6xl">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold flex items-center gap-2">
          <Server className="h-8 w-8" />
          System Services
        </h1>
        <p className="text-muted-foreground">
          Monitor the status of all WAF-GUARD backend services
        </p>
      </div>

      {/* Overview Stats */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Services</CardTitle>
            <Server className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{services.length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Online</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{onlineCount}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Offline</CardTitle>
            <XCircle className="h-4 w-4 text-red-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{offlineCount}</div>
          </CardContent>
        </Card>
      </div>

      {/* Services List */}
      <div className="space-y-4">
        <h2 className="text-xl font-semibold">Service Status</h2>
        {services.map((service) => {
          const Icon = service.icon
          return (
            <Card key={service.name} className={service.status === 'offline' ? 'border-red-200 dark:border-red-900' : ''}>
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-lg bg-${service.color}-50 dark:bg-${service.color}-950`}>
                      <Icon className={`h-5 w-5 text-${service.color}-600`} />
                    </div>
                    <div>
                      <CardTitle className="flex items-center gap-2">
                        {service.name}
                        {getStatusIcon(service.status)}
                      </CardTitle>
                      <CardDescription className="mt-1">
                        {service.description}
                      </CardDescription>
                    </div>
                  </div>
                  {getStatusBadge(service.status)}
                </div>
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <span className="font-medium">URL:</span>
                  <code className="bg-secondary px-2 py-1 rounded text-xs">{service.url}</code>
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>

      {/* Warning if services are down */}
      {offlineCount > 0 && (
        <Card className="border-orange-500 bg-orange-50 dark:bg-orange-950">
          <CardContent className="flex items-start gap-3 p-4">
            <AlertCircle className="h-5 w-5 text-orange-600 mt-0.5" />
            <div className="space-y-1">
              <p className="font-semibold text-orange-900 dark:text-orange-100">
                Some services are offline
              </p>
              <p className="text-sm text-orange-800 dark:text-orange-200">
                {offlineCount} service{offlineCount > 1 ? 's are' : ' is'} currently unavailable. 
                Please check your Docker containers are running with <code className="bg-orange-200 dark:bg-orange-900 px-1 rounded">docker ps</code>.
              </p>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
