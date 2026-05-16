'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { AppShell } from '@/components/layout/AppShell'
import { listOffenders } from '@/lib/api'
import { isAuthenticated } from '@/lib/auth'

export default function OffendersPage() {
  const router = useRouter()
  const [items, setItems] = useState<
    Awaited<ReturnType<typeof listOffenders>>['items']
  >([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace('/login')
      return
    }
    listOffenders()
      .then((data) => setItems(data.items))
      .catch((err) =>
        setError(err instanceof Error ? err.message : 'Failed to load offenders'),
      )
      .finally(() => setLoading(false))
  }, [router])

  return (
    <AppShell title="Repeat Offenders" subtitle="Confirmed repeat harassment patterns">
      {error && (
        <p className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {error}
        </p>
      )}
      {loading && <p className="text-sm text-patrol-muted">Loading…</p>}
      <div className="space-y-3">
        {items.map((o) => (
          <article
            key={o.id}
            className="rounded-xl border border-patrol-border bg-patrol-card p-4"
          >
            <div className="flex flex-wrap gap-2 text-sm">
              <span className="font-mono text-patrol-accent">@{o.username}</span>
              <span className="text-patrol-muted">{o.platform}</span>
              <span className="rounded border border-red-500/40 bg-red-500/10 px-2 py-0.5 text-xs text-red-400">
                {o.status}
              </span>
            </div>
            <p className="mt-2 text-xs text-patrol-muted">
              {o.total_offenses} offenses · {o.critical_count} critical · priority{' '}
              {o.priority_score}
            </p>
          </article>
        ))}
      </div>
      {!loading && items.length === 0 && !error && (
        <p className="text-sm text-patrol-muted">No repeat offenders flagged yet.</p>
      )}
    </AppShell>
  )
}
