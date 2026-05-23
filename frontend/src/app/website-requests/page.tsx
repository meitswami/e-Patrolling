'use client'

import { useCallback, useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { AppShell } from '@/components/layout/AppShell'
import { PlatformIcon } from '@/components/platforms/PlatformIcon'
import {
  convertWebsiteRequest,
  listWebsiteRequests,
  updateWebsiteRequest,
} from '@/lib/api'
import { isAuthenticated } from '@/lib/auth'
import type { Platform, WebsiteRequestStatus, WebsiteSafetyRequest } from '@/types'

const STATUS_LABELS: Record<WebsiteRequestStatus, string> = {
  pending: 'Pending',
  reviewed: 'Reviewed',
  converted: 'Converted',
  dismissed: 'Dismissed',
}

export default function WebsiteRequestsPage() {
  const router = useRouter()
  const [items, setItems] = useState<WebsiteSafetyRequest[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [convertingId, setConvertingId] = useState<string | null>(null)

  const load = useCallback(async () => {
    const data = await listWebsiteRequests(1, 50, statusFilter || undefined)
    setItems(data.items)
  }, [statusFilter])

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace('/admin')
      return
    }
    load()
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load'))
      .finally(() => setLoading(false))
  }, [router, load])

  async function handleConvert(id: string) {
    setConvertingId(id)
    setError(null)
    setMessage(null)
    try {
      const targets = await convertWebsiteRequest(id)
      setMessage(`Created ${targets.length} target(s) from website intake. Enable monitoring on Targets page.`)
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Convert failed')
    } finally {
      setConvertingId(null)
    }
  }

  async function handleDismiss(id: string) {
    try {
      await updateWebsiteRequest(id, { status: 'dismissed' })
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Update failed')
    }
  }

  return (
    <AppShell
      title="Website Intake"
      subtitle="Public “Want to be Safe” form — separate from admin-created targets"
    >
      <p className="mb-4 text-xs text-patrol-muted">
        These profiles come from the public website. Use <strong className="text-patrol-text">Convert to targets</strong>{' '}
        to add them as monitored accounts (source: website intake). Targets you add manually on the Targets page are
        admin panel only.
      </p>

      <div className="mb-4 flex flex-wrap gap-2">
        {['', 'pending', 'converted', 'dismissed'].map((s) => (
          <button
            key={s || 'all'}
            type="button"
            onClick={() => {
              setStatusFilter(s)
              setLoading(true)
              listWebsiteRequests(1, 50, s || undefined)
                .then((data) => setItems(data.items))
                .finally(() => setLoading(false))
            }}
            className={`rounded-lg border px-3 py-1.5 text-sm ${
              statusFilter === s
                ? 'border-patrol-accent/50 bg-patrol-accent/10 text-patrol-accent'
                : 'border-patrol-border text-patrol-muted hover:text-patrol-text'
            }`}
          >
            {s ? STATUS_LABELS[s as WebsiteRequestStatus] : 'All'}
          </button>
        ))}
      </div>

      {error && (
        <p className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {error}
        </p>
      )}
      {message && (
        <p className="mb-4 rounded-lg border border-patrol-accent/30 bg-patrol-accent/10 px-4 py-3 text-sm text-patrol-accent">
          {message}
        </p>
      )}

      {loading && <p className="text-sm text-patrol-muted">Loading…</p>}

      {!loading && items.length === 0 && (
        <p className="text-sm text-patrol-muted">No website requests yet.</p>
      )}

      <ul className="space-y-4">
        {items.map((req) => (
          <li
            key={req.id}
            className="rounded-xl border border-patrol-border bg-patrol-card p-4"
          >
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <span className="rounded bg-sky-500/20 px-2 py-0.5 text-xs font-medium text-sky-300">
                  {STATUS_LABELS[req.status]}
                </span>
                <p className="mt-2 text-sm text-patrol-muted">
                  {req.state}, {req.city} · {new Date(req.created_at).toLocaleString()}
                </p>
                {(req.contact_name || req.contact_email) && (
                  <p className="mt-1 text-sm text-patrol-text">
                    {req.contact_name}
                    {req.contact_email && ` · ${req.contact_email}`}
                    {req.contact_phone && ` · ${req.contact_phone}`}
                  </p>
                )}
              </div>
              {req.status === 'pending' && (
                <div className="flex gap-2">
                  <button
                    type="button"
                    disabled={convertingId === req.id}
                    onClick={() => handleConvert(req.id)}
                    className="rounded-lg bg-patrol-accent px-3 py-1.5 text-xs font-medium text-patrol-bg disabled:opacity-50"
                  >
                    {convertingId === req.id ? 'Converting…' : 'Convert to targets'}
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDismiss(req.id)}
                    className="rounded-lg border border-patrol-border px-3 py-1.5 text-xs text-patrol-muted"
                  >
                    Dismiss
                  </button>
                </div>
              )}
            </div>
            <ul className="mt-3 space-y-2">
              {req.profile_entries.map((entry, i) => (
                <li
                  key={i}
                  className="flex items-center gap-2 text-sm"
                >
                  <PlatformIcon platform={entry.platform as Platform} size="sm" />
                  <a
                    href={entry.profile_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-patrol-accent hover:underline"
                  >
                    @{entry.username}
                  </a>
                  <span className="text-patrol-muted">({entry.platform})</span>
                </li>
              ))}
            </ul>
            {req.message && (
              <p className="mt-2 text-sm text-patrol-muted italic">{req.message}</p>
            )}
          </li>
        ))}
      </ul>
    </AppShell>
  )
}
