'use client'

import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { Sidebar } from '@/components/layout/Sidebar'

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <ProtectedRoute>
      <div className="flex h-screen overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-y-auto lg:ml-64">
          {/* w-full, not `container mx-auto`: the container utility caps at the breakpoint
            width and centres, which left ~100px of dead margin each side on a wide
            screen. Pages here are dense (a 9-column directive table, a chat panel with
            tool output) and want the room. */}
          <div className="w-full p-4 lg:p-6">
            {children}
          </div>
        </main>
      </div>
    </ProtectedRoute>
  )
}
