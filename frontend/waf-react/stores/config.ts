import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { ConfigurationResponse } from '@/types'

interface ConfigStore {
  selectedConfig: ConfigurationResponse | null
  selectedConfigId: number | null
  configs: ConfigurationResponse[]
  setSelectedConfig: (config: ConfigurationResponse | null) => void
  setSelectedConfigId: (id: number | null) => void
  setConfigs: (configs: ConfigurationResponse[]) => void
}

export const useConfigStore = create<ConfigStore>()(
  persist(
    (set) => ({
      selectedConfig: null,
      selectedConfigId: null,
      configs: [],
      setSelectedConfig: (config) => set({ 
        selectedConfig: config,
        selectedConfigId: config?.id || null 
      }),
      setSelectedConfigId: (id) => set({ selectedConfigId: id }),
      setConfigs: (configs) => set({ configs }),
    }),
    {
      name: 'waf-config-storage', // localStorage key
      partialize: (state) => ({ 
        selectedConfigId: state.selectedConfigId // Only persist the ID
      }),
    }
  )
)
