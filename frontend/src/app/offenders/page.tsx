'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
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
  const [search, setSearch] = useState('')

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace('/admin')
      return
    }
    listOffenders()
      .then((data) => setItems(data.items))
      .catch((err) =>
        setError(err instanceof Error ? err.message : 'Failed to load offenders'),
      )
      .finally(() => setLoading(false))
  }, [router])

  const filtered = search.trim()
    ? items.filter((o) =>
        o.username.toLowerCase().includes(search.trim().toLowerCase()),
      )
    : items

  return (
    <AppShell title="Repeat Offenders" subtitle="Confirmed repeat harassment patterns">
      <div className="mb-4 flex flex-wrap gap-3 print:hidden">
        <input
          type="search"
          placeholder="Search by username for full dossier…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="min-w-[240px] flex-1 rounded-lg border border-patrol-border bg-patrol-surface px-3 py-2 text-sm"
        />
        {search.trim() && (
          <Link
            href={`/offenders/dossier/${encodeURIComponent(search.trim().replace(/^@/, ''))}`}
            className="rounded-lg bg-patrol-accent px-4 py-2 text-sm font-medium text-black"
          >
            Open dossier for @{search.trim().replace(/^@/, '')}
          </Link>
        )}
      </div>

      {error && (
        <p className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {error}
        </p>
      )}
      {loading && <p className="text-sm text-patrol-muted">Loading…</p>}
      <div className="space-y-3">
        {filtered.map((o) => (
          <article
            key={o.id}
            className="rounded-xl border border-patrol-border bg-patrol-card p-4"
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex flex-wrap gap-2 text-sm">
                <span className="font-mono text-patrol-accent">@{o.username}</span>
                <span className="text-patrol-muted">{o.platform}</span>
                <span className="rounded border border-red-500/40 bg-red-500/10 px-2 py-0.5 text-xs text-red-400">
                  {o.status}
                </span>
              </div>
              <Link
                href={`/offenders/dossier/${encodeURIComponent(o.username)}`}
                className="rounded-lg border border-patrol-accent/40 px-3 py-1.5 text-xs text-patrol-accent hover:bg-patrol-accent/10"
              >
                Full dossier (all platforms)
              </Link>
            </div>
            <p className="mt-2 text-xs text-patrol-muted">
              {o.total_offenses} offenses · {o.critical_count} critical · priority{' '}
              {o.priority_score}
            </p>
          </article>
        ))}
      </div>
      {!loading && filtered.length === 0 && !error && (
        <p className="text-sm text-patrol-muted">No repeat offenders flagged yet.</p>
      )}
    </AppShell>
  )
}
