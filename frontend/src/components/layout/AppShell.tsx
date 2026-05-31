'use client'

import { Sidebar } from './Sidebar'
import { Header } from './Header'
import { PerformanceMonitor } from './PerformanceMonitor'

interface AppShellProps {
  title: string
  subtitle?: string
  children: React.ReactNode
}

export function AppShell({ title, subtitle, children }: AppShellProps) {
  return (
    <div className="flex min-h-screen bg-patrol-bg text-patrol-text">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header title={title} subtitle={subtitle} />
        <main className="flex-1 overflow-auto p-6 animate-fade-in">
          <PerformanceMonitor />
          {children}
        </main>
      </div>
    </div>
  )
}
