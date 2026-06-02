'use client'

import { useCallback, useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { AppShell } from '@/components/layout/AppShell'
import { PlatformIcon } from '@/components/platforms/PlatformIcon'
import { isAuthenticated } from '@/lib/auth'
import { API_BASE_URL, API_PREFIX, buildApiUrl } from '@/lib/constants'
import { getToken } from '@/lib/auth'

interface DiscoveredTarget {
  id: string
  platform: string
  username: string
  display_name: string | null
  profile_url: string
  avatar_url: string | null
  bio: string | null
  follower_count: number
  is_verified: boolean
  gender: string
  inferred_region: string | null
  region_confidence: number | null
  discovered_on: string
  is_converted: boolean
  is_dismissed: boolean
  created_at: string | null
}

interface DiscoveryRun {
  id: string
  run_date: string
  platforms: string[]
  total_found: number
  total_converted: number
  status: string
  triggered_by: string
  started_at: string | null
  completed_at: string | null
}

async function apiRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken()
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
  const res = await fetch(buildApiUrl(path), { ...options, headers })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `Request failed (${res.status})`)
  }
  return res.json()
}

function formatDate(iso: string): string {
  const d = new Date(iso)
  if (isNaN(d.getTime())) return iso
  const day = String(d.getDate()).padStart(2, '0')
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const year = d.getFullYear()
  return `${day}/${month}/${year}`
}

function formatFollowers(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`
  return String(n)
}

export default function DiscoveryPage() {
  const router = useRouter()
  const [items, setItems] = useState<DiscoveredTarget[]>([])
  const [runs, setRuns] = useState<DiscoveryRun[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [dateFilter, setDateFilter] = useState<string>('')
  const [running, setRunning] = useState(false)

  const loadData = useCallback(async () => {
    try {
      const params = new URLSearchParams({ page: String(page), page_size: '20' })
      if (dateFilter) params.set('run_date', dateFilter)
      const data = await apiRequest<{
        items: DiscoveredTarget[]
        total: number
      }>(`/discovery?${params}`)
      setItems(data.items)
      setTotal(data.total)

      const runData = await apiRequest<DiscoveryRun[]>('/discovery/runs?limit=10')
      setRuns(runData)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load')
    } finally {
      setLoading(false)
    }
  }, [page, dateFilter])

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace('/admin')
      return
    }
    loadData()
  }, [router, loadData])

  async function handleTriggerDiscovery() {
    setRunning(true)
    setError(null)
    setMessage(null)
    try {
      const result = await apiRequest<{ message: string }>('/discovery/run', { method: 'POST' })
      setMessage(result.message)
      await loadData()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Discovery failed')
    } finally {
      setRunning(false)
    }
  }

  async function handleConvert(id: string) {
    setError(null)
    try {
      const result = await apiRequest<{ username: string; platform: string }>(
        `/discovery/${id}/convert`,
        { method: 'POST' },
      )
      setMessage(`@${result.username} (${result.platform}) added to monitored targets`)
      await loadData()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Conversion failed')
    }
  }

  async function handleDismiss(id: string) {
    setError(null)
    try {
      await apiRequest(`/discovery/${id}/dismiss`, { method: 'POST' })
      await loadData()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Dismiss failed')
    }
  }

  function handleExport() {
    const token = getToken()
    const params = dateFilter ? `?run_date=${dateFilter}` : ''
    const url = `${buildApiUrl(`/discovery/export.xlsx${params}`)}`
    const a = document.createElement('a')
    a.href = url
    a.download = 'discovered_targets.xlsx'
    // For authenticated download, open in new tab (token needed)
    window.open(`${url}&token=${token || ''}`, '_blank')
  }

  const totalPages = Math.max(1, Math.ceil(total / 20))

  return (
    <AppShell
      title="Auto-Discovery"
      subtitle="Female · Blue Tick · 10K+ Followers — Daily Auto-Crawl"
    >
      {/* Controls */}
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <label className="text-sm text-patrol-muted">
          Filter by date:
          <input
            type="date"
            value={dateFilter}
            onChange={(e) => {
              setDateFilter(e.target.value)
              setPage(1)
            }}
            className="ml-2 rounded-lg border border-patrol-border bg-patrol-surface px-3 py-1.5 text-sm text-patrol-text"
          />
        </label>
        {dateFilter && (
          <button
            type="button"
            onClick={() => { setDateFilter(''); setPage(1) }}
            className="text-xs text-patrol-muted hover:text-patrol-accent"
          >
            Clear filter
          </button>
        )}
        <div className="ml-auto flex gap-2">
          <button
            type="button"
            onClick={handleExport}
            className="rounded-lg border border-patrol-border px-4 py-2 text-sm text-patrol-muted hover:text-patrol-accent"
          >
            📥 Export Excel
          </button>
          <button
            type="button"
            disabled={running}
            onClick={handleTriggerDiscovery}
            className="rounded-lg border border-patrol-accent/40 bg-patrol-accent/10 px-4 py-2 text-sm font-medium text-patrol-accent disabled:opacity-50"
          >
            {running ? 'Running…' : '🔍 Run Discovery Now'}
          </button>
        </div>
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

      {/* Discovery run history */}
      {runs.length > 0 && (
        <div className="mb-6">
          <h2 className="mb-2 font-mono text-sm text-patrol-accent">Recent Discovery Runs</h2>
          <div className="flex flex-wrap gap-2">
            {runs.map((run) => (
              <button
                key={run.id}
                type="button"
                onClick={() => { setDateFilter(run.run_date); setPage(1) }}
                className={`rounded-lg border px-3 py-1.5 text-xs transition ${
                  dateFilter === run.run_date
                    ? 'border-patrol-accent/50 bg-patrol-accent/10 text-patrol-accent'
                    : 'border-patrol-border text-patrol-muted hover:text-patrol-text'
                }`}
              >
                {formatDate(run.run_date)} · {run.total_found} found · {run.triggered_by}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Main list */}
      {loading && <p className="text-sm text-patrol-muted">Loading discovered targets…</p>}

      {!loading && items.length === 0 && (
        <div className="rounded-xl border border-dashed border-patrol-border p-12 text-center">
          <p className="font-mono text-patrol-accent">No discovered targets yet</p>
          <p className="mt-2 text-sm text-patrol-muted">
            Click "Run Discovery Now" to find female verified accounts with 10K+ followers.
          </p>
        </div>
      )}

      <div className="space-y-3">
        {items.map((item) => (
          <article
            key={item.id}
            className={`rounded-xl border p-4 transition ${
              item.is_converted
                ? 'border-patrol-accent/30 bg-patrol-accent/5'
                : item.is_dismissed
                  ? 'border-patrol-border/50 bg-patrol-surface/30 opacity-60'
                  : 'border-patrol-border bg-patrol-card hover:border-patrol-accent/20'
            }`}
          >
            <div className="flex flex-wrap items-center gap-2">
              <PlatformIcon platform={item.platform} size="md" />
              <span className="font-mono text-patrol-accent">@{item.username}</span>
              {item.display_name && (
                <span className="text-sm text-patrol-text">{item.display_name}</span>
              )}
              {item.is_verified && (
                <span className="rounded border border-blue-500/40 bg-blue-500/10 px-1.5 py-0.5 text-[10px] text-blue-400">
                  ✓ Verified
                </span>
              )}
              <span className="rounded border border-pink-500/40 bg-pink-500/10 px-1.5 py-0.5 text-[10px] text-pink-400">
                {item.gender}
              </span>
              <span className="text-xs text-patrol-muted">
                {formatFollowers(item.follower_count)} followers
              </span>
              {item.inferred_region && (
                <span className="rounded border border-amber-500/40 bg-amber-500/10 px-1.5 py-0.5 text-[10px] text-amber-400">
                  📍 {item.inferred_region}
                </span>
              )}
              <span className="ml-auto text-xs text-patrol-muted">
                {formatDate(item.discovered_on)}
              </span>
            </div>

            {item.bio && (
              <p className="mt-2 text-xs text-patrol-muted line-clamp-2">{item.bio}</p>
            )}

            <div className="mt-3 flex items-center gap-2">
              <a
                href={item.profile_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-patrol-muted hover:text-patrol-accent"
              >
                View profile →
              </a>
              {!item.is_converted && !item.is_dismissed && (
                <>
                  <button
                    type="button"
                    onClick={() => handleConvert(item.id)}
                    className="rounded-lg border border-patrol-accent/40 bg-patrol-accent/10 px-3 py-1 text-xs font-medium text-patrol-accent"
                  >
                    ➕ Add to Monitoring
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDismiss(item.id)}
                    className="rounded-lg border border-patrol-border px-3 py-1 text-xs text-patrol-muted hover:text-red-400"
                  >
                    Dismiss
                  </button>
                </>
              )}
              {item.is_converted && (
                <span className="text-xs font-medium text-patrol-accent">✓ Monitoring active</span>
              )}
              {item.is_dismissed && (
                <span className="text-xs text-patrol-muted">Dismissed</span>
              )}
            </div>
          </article>
        ))}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="mt-6 flex items-center justify-center gap-2">
          <button
            type="button"
            disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}
            className="rounded-lg border border-patrol-border px-3 py-1.5 text-sm text-patrol-muted disabled:opacity-40"
          >
            ← Prev
          </button>
          <span className="text-sm text-patrol-muted">
            Page {page} of {totalPages} ({total} total)
          </span>
          <button
            type="button"
            disabled={page >= totalPages}
            onClick={() => setPage((p) => p + 1)}
            className="rounded-lg border border-patrol-border px-3 py-1.5 text-sm text-patrol-muted disabled:opacity-40"
          >
            Next →
          </button>
        </div>
      )}
    </AppShell>
  )
}
