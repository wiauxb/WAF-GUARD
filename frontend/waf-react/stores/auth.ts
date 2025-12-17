import { create } from 'zustand'
import { UserInfo } from '@/types'

interface AuthStore {
  user: UserInfo | null
  token: string | null
  setAuth: (user: UserInfo, token: string) => void
  logout: () => void
  isAuthenticated: boolean
}

export const useAuthStore = create<AuthStore>((set) => ({
  user: null,
  token: typeof window !== 'undefined' ? localStorage.getItem('token') : null,
  isAuthenticated: false,
  setAuth: (user, token) => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('token', token)
    }
    set({ user, token, isAuthenticated: true })
  },
  logout: () => {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('token')
    }
    set({ user: null, token: null, isAuthenticated: false })
  },
}))
