import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { Config } from '@/types'

interface ConfigStore {
  selectedConfig: Config | null
  selectedConfigId: number | null
  configs: Config[]
  setSelectedConfig: (config: Config | null) => void
  setSelectedConfigId: (id: number | null) => void
  setConfigs: (configs: Config[]) => void
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
