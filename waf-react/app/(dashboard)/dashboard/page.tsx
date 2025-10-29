'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { FileCode, MessageSquare, Database, Shield, Activity, TrendingUp } from 'lucide-react'
import Link from 'next/link'
import { useQuery } from '@tanstack/react-query'
import { webAppApi, chatbotApi } from '@/lib/api'
import { LoadingSpinner } from '@/components/ui/loading-spinner'
import { useConfigStore } from '@/stores/config'
import { useEffect } from 'react'
import { Config, ConfigArray } from '@/types'

// Helper function to convert array to Config object
const parseConfigArray = (arr: ConfigArray): Config => ({
  id: arr[0],
  nickname: arr[1],
  parsed: arr[2],
  created_at: arr[3],
})

export default function DashboardPage() {
  const { setConfigs, setSelectedConfig } = useConfigStore()

  const { data: configsData, isLoading: configsLoading } = useQuery({
    queryKey: ['configs'],
    queryFn: async () => {
      const response = await webAppApi.get<{ configs: ConfigArray[] }>('/configs')
      // Convert array format to object format
      const parsedConfigs = response.data.configs.map(parseConfigArray)
      return { configs: parsedConfigs }
    },
  })

  const { data: selectedConfigData } = useQuery({
    queryKey: ['selected-config'],
    queryFn: async () => {
      const response = await webAppApi.get('/configs/selected')
      return response.data
    },
  })

  const { data: threadsData } = useQuery({
    queryKey: ['threads'],
    queryFn: async () => {
      const response = await chatbotApi.get('/chat/threads')
      return response.data
    },
  })

  useEffect(() => {
    if (configsData?.configs) {
      setConfigs(configsData.configs)
    }
    if (selectedConfigData?.selected_config) {
      const selectedId = selectedConfigData.selected_config.config_id
      const selected = configsData?.configs?.find((c: Config) => c.id === selectedId)
      setSelectedConfig(selected || null)
    }
  }, [configsData, selectedConfigData, setConfigs, setSelectedConfig])

  const stats = [
    {
      title: 'Configurations',
      value: configsData?.configs?.length || 0,
      icon: FileCode,
      description: 'Total WAF configs',
      href: '/configs',
      color: 'text-blue-600',
      bgColor: 'bg-blue-50 dark:bg-blue-950',
    },
    {
      title: 'Chat Threads',
      value: threadsData?.length || 0,
      icon: MessageSquare,
      description: 'Active conversations',
      href: '/chatbot',
      color: 'text-purple-600',
      bgColor: 'bg-purple-50 dark:bg-purple-950',
    },
    {
      title: 'Parsed Configs',
      value: configsData?.configs?.filter((c: Config) => c.parsed).length || 0,
      icon: Activity,
      description: 'Analyzed configurations',
      href: '/configs',
      color: 'text-green-600',
      bgColor: 'bg-green-50 dark:bg-green-950',
    },
    {
      title: 'Database Status',
      value: 'Active',
      icon: Database,
      description: 'System operational',
      href: '/database',
      color: 'text-orange-600',
      bgColor: 'bg-orange-50 dark:bg-orange-950',
    },
  ]

  const quickActions = [
    {
      title: 'Upload Configuration',
      description: 'Add a new WAF configuration file',
      icon: FileCode,
      href: '/configs',
      color: 'from-blue-600 to-blue-400',
    },
    {
      title: 'Start Chat',
      description: 'Ask questions about your configurations',
      icon: MessageSquare,
      href: '/chatbot',
      color: 'from-purple-600 to-purple-400',
    },
    {
      title: 'Query Graph',
      description: 'Run Cypher queries on the graph database',
      icon: Database,
      href: '/cypher',
      color: 'from-green-600 to-green-400',
    },
    {
      title: 'Search Directives',
      description: 'Find and analyze WAF directives',
      icon: Shield,
      href: '/directives',
      color: 'from-orange-600 to-orange-400',
    },
  ]

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div>
        <h1 className="text-4xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent mb-2">
          Welcome to WAF-GUARD
        </h1>
        <p className="text-muted-foreground text-lg">
          Manage and analyze your Web Application Firewall configurations
        </p>
      </div>

      {/* Stats Grid */}
      {configsLoading ? (
        <LoadingSpinner />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {stats.map((stat) => {
            const Icon = stat.icon
            return (
              <Link key={stat.title} href={stat.href}>
                <Card className="hover:shadow-lg transition-all cursor-pointer border-l-4 border-l-transparent hover:border-l-primary">
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium">{stat.title}</CardTitle>
                    <div className={`p-2 rounded-lg ${stat.bgColor}`}>
                      <Icon className={`h-5 w-5 ${stat.color}`} />
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="text-3xl font-bold">{stat.value}</div>
                    <p className="text-xs text-muted-foreground mt-1">{stat.description}</p>
                  </CardContent>
                </Card>
              </Link>
            )
          })}
        </div>
      )}

      {/* Quick Actions */}
      <div>
        <h2 className="text-2xl font-bold mb-4">Quick Actions</h2>
        <div className="grid gap-4 md:grid-cols-2">
          {quickActions.map((action) => {
            const Icon = action.icon
            return (
              <Link key={action.title} href={action.href}>
                <Card className="hover:shadow-xl transition-all cursor-pointer group">
                  <CardHeader>
                    <div className="flex items-center gap-4">
                      <div className={`p-3 rounded-xl bg-gradient-to-br ${action.color} group-hover:scale-110 transition-transform`}>
                        <Icon className="h-6 w-6 text-white" />
                      </div>
                      <div>
                        <CardTitle className="group-hover:text-primary transition-colors">
                          {action.title}
                        </CardTitle>
                        <CardDescription>{action.description}</CardDescription>
                      </div>
                    </div>
                  </CardHeader>
                </Card>
              </Link>
            )
          })}
        </div>
      </div>

      {/* Recent Activity */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5" />
            System Status
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="flex items-center justify-between p-3 bg-secondary rounded-lg">
              <span className="text-sm font-medium">Neo4j Database</span>
              <span className="text-xs bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200 px-2 py-1 rounded">
                Connected
              </span>
            </div>
            <div className="flex items-center justify-between p-3 bg-secondary rounded-lg">
              <span className="text-sm font-medium">PostgreSQL Database</span>
              <span className="text-xs bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200 px-2 py-1 rounded">
                Connected
              </span>
            </div>
            <div className="flex items-center justify-between p-3 bg-secondary rounded-lg">
              <span className="text-sm font-medium">Chatbot Service</span>
              <span className="text-xs bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200 px-2 py-1 rounded">
                Online
              </span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
