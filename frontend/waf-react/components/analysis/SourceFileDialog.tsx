'use client'

import { useEffect, useMemo, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { FileCode } from 'lucide-react'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { LoadingSpinner } from '@/components/ui/loading-spinner'
import { api } from '@/lib/api'
import { errorMessage } from '@/lib/errors'

/**
 * Read-only view of one ORIGINAL configuration file, opened at a given line.
 *
 * Reached from the Source chain in the directive detail panel. Clicking a frame used to
 * re-filter the directives table by source line, which answered a different question:
 * you wanted to READ the file, and instead got another list to interpret. This opens the
 * file itself, scrolled to the line, so the trail ends where the fix is made.
 *
 * Read-only on purpose. The configurations tab owns editing (with save and re-parse);
 * from an analysis screen the file is evidence, not a document to change.
 */

/**
 * Map a path as the parser records it onto the path the tree endpoint expects.
 *
 * Provenance reports the location inside the WAF container
 * (`/etc/httpd/conf/site/apps/portal.conf`), while the tree API is rooted at the extracted
 * archive (`conf/site/apps/portal.conf`). Everything up to and including `/conf/` is
 * replaced — the same mapping the parser and AnalysisService apply server-side.
 */
export function toArchivePath(dumpPath: string): string {
  const cleaned = (dumpPath || '').replace(/\\/g, '/')
  const marker = cleaned.indexOf('/conf/')
  if (marker !== -1) return 'conf/' + cleaned.slice(marker + '/conf/'.length)
  return cleaned.replace(/^\/+/, '')
}

interface Props {
  configurationId: number
  filePath: string | null
  lineNumber?: number | null
  onClose: () => void
}

export function SourceFileDialog({ configurationId, filePath, lineNumber, onClose }: Props) {
  const archivePath = filePath ? toArchivePath(filePath) : null

  const { data, isLoading, error } = useQuery({
    queryKey: ['source-file', configurationId, archivePath],
    enabled: !!archivePath,
    queryFn: async () => {
      const res = await api.get(`/configurations/${configurationId}/tree`, {
        params: { path: archivePath },
      })
      return res.data as { is_file?: boolean; content?: string | null }
    },
  })

  const lines = useMemo(() => (data?.content ?? '').split('\n'), [data?.content])
  const targetRef = useRef<HTMLDivElement | null>(null)

  // Centre the cited line once the content is in the DOM. `block: 'center'` matters: the
  // interesting part of a macro is the lines around it, not the line alone.
  useEffect(() => {
    if (!targetRef.current) return
    targetRef.current.scrollIntoView({ block: 'center' })
  }, [data?.content, lineNumber])

  return (
    <Dialog open={!!filePath} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-[80vw] w-[80vw] max-h-[85vh] p-0 gap-0 flex flex-col">
        <DialogHeader className="px-5 py-3 border-b flex-shrink-0">
          <DialogTitle className="flex items-center gap-2 text-sm font-mono break-all">
            <FileCode className="h-4 w-4 flex-shrink-0" />
            {archivePath}
            {lineNumber ? (
              <span className="text-muted-foreground font-sans">— ligne {lineNumber}</span>
            ) : null}
          </DialogTitle>
        </DialogHeader>

        <div className="min-h-0 flex-1 overflow-auto">
          {isLoading ? (
            <div className="p-8 flex justify-center"><LoadingSpinner /></div>
          ) : error ? (
            <p className="p-6 text-sm text-destructive">
              {errorMessage(error, 'Impossible de lire ce fichier')}
            </p>
          ) : (
            <pre className="text-xs leading-relaxed font-mono p-0 m-0">
              {lines.map((text, i) => {
                const n = i + 1
                const isTarget = lineNumber != null && n === lineNumber
                return (
                  <div
                    key={n}
                    ref={isTarget ? targetRef : undefined}
                    className={
                      'flex gap-3 px-4 ' +
                      (isTarget ? 'bg-amber-100 border-l-2 border-amber-500' : 'border-l-2 border-transparent')
                    }
                  >
                    <span className="select-none w-12 flex-shrink-0 text-right text-muted-foreground tabular-nums">
                      {n}
                    </span>
                    {/* whitespace-pre-wrap, not overflow-x: a long macro line should wrap
                        rather than push the dialog into horizontal scrolling. */}
                    <span className="whitespace-pre-wrap break-words">{text || ' '}</span>
                  </div>
                )
              })}
            </pre>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
