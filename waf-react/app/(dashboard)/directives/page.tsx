'use client'

import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { webAppApi } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { LoadingSpinner } from '@/components/ui/loading-spinner'
import { Search, Shield, Tag, Hash, FileSearch } from 'lucide-react'
import toast from 'react-hot-toast'

export default function DirectivesPage() {
  const [searchId, setSearchId] = useState('')
  const [searchTag, setSearchTag] = useState('')
  const [searchNodeId, setSearchNodeId] = useState('')
  const [results, setResults] = useState<any[]>([])

  const searchByIdMutation = useMutation({
    mutationFn: async (id: string) => {
      const response = await webAppApi.get(`/directives/id`, { params: { id } })
      return response.data
    },
    onSuccess: (data) => {
      setResults(data.results || [])
      toast.success('Search completed!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Search failed')
    },
  })

  const searchByTagMutation = useMutation({
    mutationFn: async (tag: string) => {
      const response = await webAppApi.get(`/directives/tag`, { params: { tag } })
      return response.data
    },
    onSuccess: (data) => {
      setResults(data.results || [])
      toast.success('Search completed!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Search failed')
    },
  })

  const searchByNodeIdMutation = useMutation({
    mutationFn: async (nodeid: string) => {
      const response = await webAppApi.get(`/directives/id/${nodeid}`)
      return response.data
    },
    onSuccess: (data) => {
      setResults(data.results || [])
      toast.success('Search completed!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Search failed')
    },
  })

  const searchRemoversMutation = useMutation({
    mutationFn: async (nodeid: string) => {
      const response = await webAppApi.get(`/directives/removed/${nodeid}`)
      return response.data
    },
    onSuccess: (data) => {
      setResults(data.results || [])
      toast.success('Search completed!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Search failed')
    },
  })

  const renderResults = () => {
    if (results.length === 0) {
      return (
        <div className="text-center py-12 text-muted-foreground">
          No results found
        </div>
      )
    }

    return (
      <div className="space-y-3">
        {results.map((result, idx) => (
          <Card key={idx}>
            <CardContent className="p-4">
              <div className="space-y-2">
                {Object.entries(result).map(([key, value]) => (
                  <div key={key} className="flex gap-2">
                    <span className="font-semibold min-w-32">{key}:</span>
                    <span className="text-muted-foreground break-all">
                      {typeof value === 'object' 
                        ? JSON.stringify(value, null, 2)
                        : value === -1 
                        ? 'null'
                        : String(value)}
                    </span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold flex items-center gap-2">
          <Shield className="h-8 w-8" />
          Directives Search
        </h1>
        <p className="text-muted-foreground">
          Search and analyze WAF directives by ID, tag, or node ID
        </p>
      </div>

      {/* Search Tabs */}
      <Tabs defaultValue="id" className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="id">
            <Hash className="h-4 w-4 mr-2" />
            By ID
          </TabsTrigger>
          <TabsTrigger value="tag">
            <Tag className="h-4 w-4 mr-2" />
            By Tag
          </TabsTrigger>
          <TabsTrigger value="nodeid">
            <FileSearch className="h-4 w-4 mr-2" />
            By Node ID
          </TabsTrigger>
          <TabsTrigger value="removers">
            <Search className="h-4 w-4 mr-2" />
            Removers
          </TabsTrigger>
        </TabsList>

        <TabsContent value="id">
          <Card>
            <CardHeader>
              <CardTitle>Search by Rule ID</CardTitle>
              <CardDescription>
                Find directives with a specific ID
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex gap-2">
                <Input
                  placeholder="Enter rule ID (e.g., 920100)"
                  value={searchId}
                  onChange={(e) => setSearchId(e.target.value)}
                  onKeyPress={(e) => {
                    if (e.key === 'Enter') searchByIdMutation.mutate(searchId)
                  }}
                />
                <Button
                  onClick={() => searchByIdMutation.mutate(searchId)}
                  disabled={!searchId || searchByIdMutation.isPending}
                >
                  <Search className="h-4 w-4 mr-2" />
                  Search
                </Button>
              </div>
              {searchByIdMutation.isPending ? (
                <LoadingSpinner />
              ) : (
                renderResults()
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="tag">
          <Card>
            <CardHeader>
              <CardTitle>Search by Tag</CardTitle>
              <CardDescription>
                Find directives with a specific tag
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex gap-2">
                <Input
                  placeholder="Enter tag (e.g., OWASP_CRS)"
                  value={searchTag}
                  onChange={(e) => setSearchTag(e.target.value)}
                  onKeyPress={(e) => {
                    if (e.key === 'Enter') searchByTagMutation.mutate(searchTag)
                  }}
                />
                <Button
                  onClick={() => searchByTagMutation.mutate(searchTag)}
                  disabled={!searchTag || searchByTagMutation.isPending}
                >
                  <Search className="h-4 w-4 mr-2" />
                  Search
                </Button>
              </div>
              {searchByTagMutation.isPending ? (
                <LoadingSpinner />
              ) : (
                renderResults()
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="nodeid">
          <Card>
            <CardHeader>
              <CardTitle>Search by Node ID</CardTitle>
              <CardDescription>
                Find directive by internal node ID
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex gap-2">
                <Input
                  placeholder="Enter node ID"
                  value={searchNodeId}
                  onChange={(e) => setSearchNodeId(e.target.value)}
                  onKeyPress={(e) => {
                    if (e.key === 'Enter') searchByNodeIdMutation.mutate(searchNodeId)
                  }}
                />
                <Button
                  onClick={() => searchByNodeIdMutation.mutate(searchNodeId)}
                  disabled={!searchNodeId || searchByNodeIdMutation.isPending}
                >
                  <Search className="h-4 w-4 mr-2" />
                  Search
                </Button>
              </div>
              {searchByNodeIdMutation.isPending ? (
                <LoadingSpinner />
              ) : (
                renderResults()
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="removers">
          <Card>
            <CardHeader>
              <CardTitle>Find Remover Directives</CardTitle>
              <CardDescription>
                Find which directives removed a specific node
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex gap-2">
                <Input
                  placeholder="Enter node ID to check"
                  value={searchNodeId}
                  onChange={(e) => setSearchNodeId(e.target.value)}
                  onKeyPress={(e) => {
                    if (e.key === 'Enter') searchRemoversMutation.mutate(searchNodeId)
                  }}
                />
                <Button
                  onClick={() => searchRemoversMutation.mutate(searchNodeId)}
                  disabled={!searchNodeId || searchRemoversMutation.isPending}
                >
                  <Search className="h-4 w-4 mr-2" />
                  Search
                </Button>
              </div>
              {searchRemoversMutation.isPending ? (
                <LoadingSpinner />
              ) : (
                renderResults()
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
