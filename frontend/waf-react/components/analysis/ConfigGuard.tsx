'use client'

import { useEffect, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { AlertTriangle, FileCode, Play } from 'lucide-react'
import toast from 'react-hot-toast'
import { api } from '@/lib/api'
import { parseAnalysisError } from '@/lib/analysis'
import { Button } from '@/components/ui/button'
import { EmptyState } from '@/components/ui/empty-state'
import { LoadingSpinner } from '@/components/ui/loading-spinner'

interface ConfigGuardProps {
  error: unknown
  configurationId: number | null
  children?: React.ReactNode
}

/**
 * Turns the analysis API's 400/409 responses into something actionable.
 *
 * The backend already distinguishes the cases precisely:
 *   400 - no configuration selected at all
 *   409 - selected but `parsing_status != 'parsed'`
 *   409 - marked parsed but its graph holds no nodes (needs a re-parse)
 *
 * Rather than surfacing those as a raw toast, show what to do and offer to do it.
 */
export function ConfigGuard({ error, configurationId, children }: ConfigGuardProps) {
  const qc = useQueryClient()
  const [parsing, setParsing] = useState(false)
  const info = parseAnalysisError(error)

  // Poll parser status while a parse we started is running.
  useEffect(() => {
    if (!parsing || !configurationId) return
    const timer = setInterval(async () => {
      try {
        const { data } = await api.get(`/parser/status/${configurationId}`)
        if (data.parsing_status === 'parsed') {
          setParsing(false)
          toast.success('Parsing complete')
          qc.invalidateQueries({ queryKey: ['analysis'] })
          qc.invalidateQueries({ queryKey: ['configs'] })
        } else if (data.parsing_status === 'error') {
          setParsing(false)
          toast.error(data.parsing_error || 'Parsing failed')
        }
      } catch {
        /* keep polling; a transient failure shouldn't stop the watch */
      }
    }, 3000)
    return () => clearInterval(timer)
  }, [parsing, configurationId, qc])

  if (!error) return <>{children}</>

  // No configuration selected — nothing to parse, point at the configs page.
  if (info.noConfig) {
    return (
      <EmptyState
        icon={FileCode}
        variant="warning"
        title="No active configuration"
        description="Analysis runs against your active configuration. Pick one to get started."
        action={
          <Button asChild>
            <a href="/configs">Choose a configuration</a>
          </Button>
        }
      />
    )
  }

  if (info.needsParse) {
    // "empty graph" means it was parsed once but the data is gone — re-parse.
    const isStale = /graph is empty/i.test(info.detail)
    const startParse = async () => {
      if (!configurationId) return
      try {
        setParsing(true)
        await api.post(
          `/parser/${isStale ? 'reparse' : 'parse'}/${configurationId}`,
          isStale ? undefined : { force_reparse: false },
        )
        toast.success('Parsing started — this can take a few minutes')
      } catch (e: any) {
        setParsing(false)
        toast.error(e?.response?.data?.detail || 'Could not start parsing')
      }
    }

    return (
      <EmptyState
        icon={AlertTriangle}
        variant="warning"
        title={isStale ? 'This configuration needs re-parsing' : 'This configuration is not parsed yet'}
        description={
          <>
            <p>{info.detail}</p>
            {isStale && (
              <p className="mt-2">
                Its analysis data was lost while its status still says parsed — usually
                because the graph database was recreated. Re-parsing rebuilds it.
              </p>
            )}
          </>
        }
        action={
          parsing ? (
            <div className="flex items-center gap-2 text-sm text-amber-900">
              <LoadingSpinner />
              Parsing…
            </div>
          ) : (
            <Button onClick={startParse} disabled={!configurationId}>
              <Play className="mr-2 h-4 w-4" />
              {isStale ? 'Re-parse now' : 'Parse now'}
            </Button>
          )
        }
      />
    )
  }

  // Anything else (404, 500, network) — show it plainly.
  return (
    <EmptyState
      icon={AlertTriangle}
      variant="warning"
      title="Could not load results"
      description={info.detail}
    />
  )
}
