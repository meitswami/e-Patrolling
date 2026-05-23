'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { AppShell } from '@/components/layout/AppShell'
import { listRegions, type RegionSummary } from '@/lib/api'
import { isAuthenticated } from '@/lib/auth'

export default function RegionsPage() {
  const router = useRouter()
  const [items, setItems] = useState<RegionSummary[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace('/admin')
      return
    }
    listRegions()
      .then(setItems)
      .catch((err) =>
        setError(err instanceof Error ? err.message : 'Failed to load regions'),
      )
  }, [router])

  return (
    <AppShell title="Region Intel" subtitle="Geographic signals from targets and accused">
      {error && (
        <p className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {error}
        </p>
      )}
      <div className="grid gap-3 sm:grid-cols-2">
        {items.map((r) => (
          <article
            key={r.region}
            className="rounded-xl border border-patrol-border bg-patrol-card p-4"
          >
            <h2 className="font-mono text-patrol-accent">{r.region}</h2>
            <p className="mt-2 text-sm text-patrol-muted">
              {r.target_count} targets · {r.accused_count} accused
            </p>
            <p className="mt-1 text-xs text-patrol-muted">
              Avg confidence {(r.avg_confidence * 100).toFixed(0)}%
            </p>
          </article>
        ))}
      </div>
      {items.length === 0 && !error && (
        <p className="text-sm text-patrol-muted">
          No region data yet. Add inferred_region on targets during monitoring.
        </p>
      )}
    </AppShell>
  )
}
