'use client'

import { Sidebar } from './Sidebar'
import { Header } from './Header'

interface AppShellProps {
  title: string
  subtitle?: string
  children: React.ReactNode
}

export function AppShell({ title, subtitle, children }: AppShellProps) {
  return (
    <div
      className="flex min-h-screen bg-patrol-bg text-patrol-text"
      style={{ backgroundColor: '#0a0e1a', color: '#e2e8f0', minHeight: '100vh' }}
    >
      <Sidebar />
      <div className="flex flex-1 flex-col">
        <Header title={title} subtitle={subtitle} />
        <main className="flex-1 overflow-auto p-6">{children}</main>
      </div>
    </div>
  )
}
