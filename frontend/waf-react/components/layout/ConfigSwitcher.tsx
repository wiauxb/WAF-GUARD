'use client'

import { errorMessage } from '@/lib/errors'
import { useEffect } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, ChevronsUpDown, Database } from 'lucide-react'
import toast from 'react-hot-toast'
import { api } from '@/lib/api'
import { cn } from '@/lib/utils'
import { useConfigStore } from '@/stores/config'
import type { ConfigurationResponse, UserInfo } from '@/types'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

/**
 * Active-configuration indicator and switcher for the sidebar.
 *
 * Every analysis query runs against the *server-side* active configuration
 * (users.active_configuration_id), so this hydrates from /auth/me rather than trusting
 * the localStorage copy — previously only the configs page re-synced, letting the two
 * drift apart.
 *
 * Only parsed configurations can be selected, matching the backend, which returns 409
 * for anything else.
 */
export function ConfigSwitcher() {
  const qc = useQueryClient()
  const { selectedConfig, setSelectedConfig, setConfigs } = useConfigStore()

  const { data: configs } = useQuery({
    queryKey: ['configs'],
    queryFn: async () => {
      const { data } = await api.get<ConfigurationResponse[]>('/configurations')
      setConfigs(data)
      return data
    },
  })

  const { data: user } = useQuery({
    queryKey: ['user-info'],
    queryFn: async () => {
      const { data } = await api.get<UserInfo>('/auth/me')
      return data
    },
  })

  // The server is the source of truth; reconcile the local store to it.
  useEffect(() => {
    if (!Array.isArray(configs) || !user) return
    const active = user.active_configuration_id
      ? configs.find((c) => c.id === user.active_configuration_id) ?? null
      : null
    if (active?.id !== selectedConfig?.id) setSelectedConfig(active)
  }, [configs, user, selectedConfig?.id, setSelectedConfig])

  const select = useMutation({
    mutationFn: async (id: number) => {
      await api.put('/auth/me/active-config', { configuration_id: id })
      return id
    },
    onSuccess: (id) => {
      setSelectedConfig(configs?.find((c) => c.id === id) ?? null)
      qc.invalidateQueries({ queryKey: ['user-info'] })
      // Results everywhere depend on this — drop the cached analysis data.
      qc.invalidateQueries({ queryKey: ['analysis'] })
      toast.success('Active configuration changed')
    },
    onError: (e: any) =>
      toast.error(errorMessage(e, 'Could not switch configuration')),
  })

  // Array.isArray rather than `?? []`: the ['configs'] key is shared with the dashboard
  // and configs pages, so a queryFn returning a different shape would crash this
  // component — and it lives in the layout, so that takes down every page. All three
  // return the plain array now; this keeps a future divergence from white-screening.
  const parsed = Array.isArray(configs)
    ? configs.filter((c) => c.parsing_status === 'parsed')
    : []
  const allConfigs = Array.isArray(configs) ? configs : []

  return (
    <div className="border-b px-4 py-3">
      <p className="mb-1.5 flex items-center gap-1.5 text-xs uppercase tracking-wide text-muted-foreground">
        <Database className="h-3 w-3" />
        Active configuration
      </p>

      {parsed.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          {allConfigs.length ? 'None analyzed yet' : 'No configurations'}
        </p>
      ) : (
        <Select
          value={selectedConfig ? String(selectedConfig.id) : undefined}
          onValueChange={(v) => select.mutate(Number(v))}
          disabled={select.isPending}
        >
          <SelectTrigger className="h-9 w-full">
            <SelectValue placeholder="Select a configuration">
              {selectedConfig && (
                <span className="flex items-center gap-2 truncate">
                  <span
                    className={cn(
                      'h-2 w-2 shrink-0 rounded-full',
                      selectedConfig.parsing_status === 'parsed'
                        ? 'bg-green-500'
                        : 'bg-amber-500'
                    )}
                  />
                  <span className="truncate">{selectedConfig.name}</span>
                </span>
              )}
            </SelectValue>
          </SelectTrigger>
          <SelectContent>
            {parsed.map((c) => (
              <SelectItem key={c.id} value={String(c.id)}>
                <span className="flex items-center gap-2">
                  <span className="truncate">{c.name}</span>
                  <span className="text-xs text-muted-foreground">#{c.id}</span>
                  {selectedConfig?.id === c.id && <Check className="h-3 w-3" />}
                </span>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      )}

      {allConfigs.length > parsed.length && (
        <p className="mt-1.5 text-xs text-muted-foreground">
          {allConfigs.length - parsed.length} not analyzed yet
        </p>
      )}
    </div>
  )
}
