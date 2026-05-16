'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { AppShell } from '@/components/layout/AppShell'
import { PLATFORM_CONFIG } from '@/lib/constants'
import { getAnalyticsOverview, type AnalyticsOverview } from '@/lib/api'
import { isAuthenticated } from '@/lib/auth'
import type { Platform } from '@/types'

export default function AnalyticsPage() {
  const router = useRouter()
  const [data, setData] = useState<AnalyticsOverview | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace('/login')
      return
    }
    getAnalyticsOverview()
      .then(setData)
      .catch((err) =>
        setError(err instanceof Error ? err.message : 'Failed to load analytics'),
      )
  }, [router])

  const sev = data?.by_severity
  const platforms = data?.by_platform ?? []

  return (
    <AppShell title="Analytics" subtitle="Severity and platform breakdown">
      {error && (
        <p className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {error}
        </p>
      )}

      {sev && (
        <div className="mb-6 grid gap-4 sm:grid-cols-4">
          {(['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'] as const).map((level) => (
            <div
              key={level}
              className="rounded-xl border border-patrol-border bg-patrol-card p-4"
            >
              <p className="text-xs text-patrol-muted">{level}</p>
              <p className="mt-1 font-mono text-2xl text-patrol-text">{sev[level]}</p>
            </div>
          ))}
        </div>
      )}

      <div className="rounded-xl border border-patrol-border bg-patrol-card p-4">
        <h2 className="font-mono text-sm text-patrol-accent">By platform</h2>
        <ul className="mt-3 space-y-2">
          {platforms.map((p) => {
            const cfg = PLATFORM_CONFIG[p.platform as Platform]
            return (
              <li
                key={p.platform}
                className="flex items-center justify-between text-sm"
              >
                <span>
                  {cfg?.icon} {cfg?.label ?? p.platform}
                </span>
                <span className="font-mono text-patrol-accent">{p.count}</span>
              </li>
            )
          })}
          {platforms.length === 0 && (
            <li className="text-sm text-patrol-muted">No evidence data yet.</li>
          )}
        </ul>
      </div>
    </AppShell>
  )
}
