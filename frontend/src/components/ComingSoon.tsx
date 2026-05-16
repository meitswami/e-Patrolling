'use client'

import { AppShell } from '@/components/layout/AppShell'

export function ComingSoon({ title }: { title: string }) {
  return (
    <AppShell title={title} subtitle="Module in development">
      <div className="rounded-xl border border-dashed border-patrol-border bg-patrol-card/50 p-12 text-center">
        <p className="font-mono text-patrol-accent">{title}</p>
        <p className="mt-2 text-sm text-patrol-muted">This section will be available in a future sprint.</p>
      </div>
    </AppShell>
  )
}
