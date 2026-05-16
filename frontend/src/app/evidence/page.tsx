'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { AppShell } from '@/components/layout/AppShell'
import { SEVERITY_CONFIG } from '@/lib/constants'
import { listEvidence } from '@/lib/api'
import { isAuthenticated } from '@/lib/auth'
import type { EvidenceListItem } from '@/types'

export default function EvidencePage() {
  const router = useRouter()
  const [items, setItems] = useState<EvidenceListItem[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace('/login')
      return
    }

    async function load() {
      try {
        const data = await listEvidence(1, 50)
        setItems(data.items)
        setTotal(data.total)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load evidence')
      } finally {
        setLoading(false)
      }
    }

    load()
  }, [router])

  return (
    <AppShell title="Evidence Feed" subtitle={`${total} report(s) in database`}>
      {error && (
        <p className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {error}
        </p>
      )}

      {loading && <p className="text-sm text-patrol-muted">Loading evidence…</p>}

      {!loading && items.length === 0 && !error && (
        <div className="rounded-xl border border-dashed border-patrol-border p-12 text-center">
          <p className="font-mono text-patrol-accent">No evidence collected yet</p>
          <p className="mt-2 text-sm text-patrol-muted">
            Evidence appears after crawlers and the AI pipeline flag abusive content.
          </p>
        </div>
      )}

      <div className="space-y-3">
        {items.map((item) => {
          const sev = SEVERITY_CONFIG[item.severity_level]
          return (
            <article
              key={item.id}
              className="rounded-xl border border-patrol-border bg-patrol-card p-4 transition hover:border-patrol-accent/20"
            >
              <div className="flex flex-wrap items-center gap-2 text-xs">
                <span className="font-mono text-patrol-accent">{item.evidence_id}</span>
                <span className={`rounded border px-2 py-0.5 ${sev.className}`}>{sev.label}</span>
                <span className="text-patrol-muted">{item.platform}</span>
                <span className="text-patrol-muted">Risk {item.risk_score}</span>
              </div>
              <p className="mt-2 line-clamp-2 text-sm text-patrol-text">{item.comment_text}</p>
              <p className="mt-2 text-xs text-patrol-muted">
                Target: {item.target_username ?? '—'} · Accused: {item.accused_username ?? '—'}
              </p>
            </article>
          )
        })}
      </div>
    </AppShell>
  )
}
