'use client'

import { useEffect, useState, ReactNode } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/stores/auth'
import { LoadingSpinner } from '@/components/ui/loading-spinner'

interface ProtectedRouteProps {
  children: ReactNode
}

/**
 * Gate for authenticated pages.
 *
 * The auth token is read from localStorage, which does not exist during server
 * rendering — so `token` is null on the server and set on the client. Branching on it
 * directly made the server and the first client render produce different trees
 * (the server put <Toaster> where the client put the dashboard layout), which React
 * reported as a hydration failure and recovered from by re-rendering the whole tree.
 *
 * Rendering the same placeholder on the server AND the first client render, then
 * switching once mounted, keeps hydration consistent.
 */
export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const router = useRouter()
  const { token } = useAuthStore()
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  useEffect(() => {
    if (mounted && !token) {
      router.push('/login')
    }
  }, [mounted, token, router])

  // Same output server-side and on the first client render.
  if (!mounted) {
    return (
      <div className="flex h-screen items-center justify-center">
        <LoadingSpinner />
      </div>
    )
  }

  // Mounted but unauthenticated: the redirect above is in flight.
  if (!token) {
    return null
  }

  return <>{children}</>
}
