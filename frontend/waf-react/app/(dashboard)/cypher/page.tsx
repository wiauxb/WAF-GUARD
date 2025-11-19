'use client'

import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { webAppApi } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { CodeEditor } from '@/components/editor/CodeEditor'
import { LoadingSpinner } from '@/components/ui/loading-spinner'
import { Play, Table as TableIcon, Network } from 'lucide-react'
import toast from 'react-hot-toast'

const exampleQueries = [
  {
    title: 'All SecRules',
    query: 'MATCH (n:secrule) RETURN n LIMIT 25'
  },
  {
    title: 'Rules with Tags',
    query: 'MATCH (r:secrule)-[:Has]->(t:Tag) RETURN r, t LIMIT 25'
  },
  {
    title: 'VirtualHosts',
    query: 'MATCH (v:VirtualHost) RETURN v'
  },
  {
    title: 'Removed Rules',
    query: 'MATCH (r:secruleremovebyid)-[:DoesRemove]->(i:Id) RETURN r, i LIMIT 25'
  },
]

export default function CypherPage() {
  const [query, setQuery] = useState(exampleQueries[0].query)
  const [graphHtml, setGraphHtml] = useState('')
  const [tableData, setTableData] = useState<any[]>([])

  const runGraphMutation = useMutation({
    mutationFn: async (cypherQuery: string) => {
      const response = await webAppApi.post('/cypher/run', { query: cypherQuery })
      return response.data
    },
    onSuccess: (data) => {
      setGraphHtml(data.html)
      toast.success('Query executed successfully!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to execute query')
    },
  })

  const runTableMutation = useMutation({
    mutationFn: async (cypherQuery: string) => {
      const response = await webAppApi.post('/cypher/to_json', { query: cypherQuery })
      return response.data
    },
    onSuccess: (data) => {
      setTableData(data.df || [])
      toast.success('Query executed successfully!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to execute query')
    },
  })

  const handleRunQuery = (asGraph: boolean) => {
    if (!query.trim()) {
      toast.error('Please enter a query')
      return
    }
    if (asGraph) {
      runGraphMutation.mutate(query)
    } else {
      runTableMutation.mutate(query)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold flex items-center gap-2">
          <Network className="h-8 w-8" />
          Cypher Query Interface
        </h1>
        <p className="text-muted-foreground">
          Query your WAF configuration graph database using Cypher
        </p>
      </div>

      {/* Example Queries */}
      <Card>
        <CardHeader>
          <CardTitle>Example Queries</CardTitle>
          <CardDescription>Click to load an example query</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            {exampleQueries.map((example) => (
              <Button
                key={example.title}
                variant="outline"
                size="sm"
                onClick={() => setQuery(example.query)}
                className="justify-start"
              >
                {example.title}
              </Button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Query Editor */}
      <Card>
        <CardHeader>
          <div className="flex justify-between items-center">
            <CardTitle>Query Editor</CardTitle>
            <div className="flex gap-2">
              <Button
                onClick={() => handleRunQuery(false)}
                disabled={runTableMutation.isPending}
                variant="outline"
              >
                <TableIcon className="h-4 w-4 mr-2" />
                Run as Table
              </Button>
              <Button
                onClick={() => handleRunQuery(true)}
                disabled={runGraphMutation.isPending}
              >
                <Play className="h-4 w-4 mr-2" />
                Run as Graph
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <CodeEditor
            value={query}
            onChange={(value: string | undefined) => setQuery(value || '')}
            language="cypher"
            height="200px"
          />
        </CardContent>
      </Card>

      {/* Results */}
      <Tabs defaultValue="graph" className="w-full">
        <TabsList>
          <TabsTrigger value="graph">
            <Network className="h-4 w-4 mr-2" />
            Graph View
          </TabsTrigger>
          <TabsTrigger value="table">
            <TableIcon className="h-4 w-4 mr-2" />
            Table View
          </TabsTrigger>
        </TabsList>

        <TabsContent value="graph">
          <Card>
            <CardHeader>
              <CardTitle>Graph Visualization</CardTitle>
            </CardHeader>
            <CardContent>
              {runGraphMutation.isPending ? (
                <LoadingSpinner />
              ) : graphHtml ? (
                <div 
                  className="w-full h-[600px] border rounded-lg overflow-hidden"
                  dangerouslySetInnerHTML={{ __html: graphHtml }}
                />
              ) : (
                <div className="h-[400px] flex items-center justify-center text-muted-foreground">
                  Run a query to see the graph visualization
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="table">
          <Card>
            <CardHeader>
              <CardTitle>Table Results</CardTitle>
            </CardHeader>
            <CardContent>
              {runTableMutation.isPending ? (
                <LoadingSpinner />
              ) : tableData.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full border-collapse">
                    <thead>
                      <tr className="border-b">
                        {Object.keys(tableData[0]).map((key) => (
                          <th key={key} className="text-left p-2 font-semibold">
                            {key}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {tableData.map((row, idx) => (
                        <tr key={idx} className="border-b hover:bg-accent">
                          {Object.values(row).map((value: any, cellIdx) => (
                            <td key={cellIdx} className="p-2">
                              {typeof value === 'object'
                                ? JSON.stringify(value)
                                : String(value)}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="h-[400px] flex items-center justify-center text-muted-foreground">
                  Run a query to see table results
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
