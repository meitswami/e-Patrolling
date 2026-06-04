'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
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

interface LogEntry {
  index: number
  timestamp: string
  message: string
  level: string
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

function formatLogTime(iso: string): string {
  try {
    const d = new Date(iso)
    if (isNaN(d.getTime())) return ''
    return d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  } catch {
    return ''
  }
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

  // Discovery control state
  const [discoveryStatus, setDiscoveryStatus] = useState<'idle' | 'running' | 'paused' | 'stopped'>('idle')
  const [progressCount, setProgressCount] = useState(0)
  const [maxCount, setMaxCount] = useState(25)
  const [customCount, setCustomCount] = useState('')
  const [showCustom, setShowCustom] = useState(false)
  const [logs, setLogs] = useState<LogEntry[]>([])

  const logsEndRef = useRef<HTMLDivElement>(null)

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
    // Fetch initial discovery status
    apiRequest<{ status: string; progress_count: number; max_count: number }>('/discovery/status')
      .then((statusData) => {
        if (statusData.status !== 'idle') {
          setDiscoveryStatus(statusData.status as 'running' | 'paused' | 'stopped')
          setProgressCount(statusData.progress_count)
          setMaxCount(statusData.max_count)
        }
      })
      .catch(() => {})
  }, [router, loadData])

  // Status polling when running or paused
  useEffect(() => {
    if (discoveryStatus !== 'running' && discoveryStatus !== 'paused') return
    const interval = setInterval(async () => {
      try {
        const status = await apiRequest<{ status: string; progress_count: number; max_count: number }>('/discovery/status')
        setDiscoveryStatus(status.status as 'idle' | 'running' | 'paused' | 'stopped')
        setProgressCount(status.progress_count)
        setMaxCount(status.max_count)
        if (status.status === 'idle' || status.status === 'stopped') {
          loadData()
        }
      } catch {}
    }, 2000)
    return () => clearInterval(interval)
  }, [discoveryStatus, loadData])

  // SSE connection using fetch for auth header support
  useEffect(() => {
    if (discoveryStatus !== 'running' && discoveryStatus !== 'paused') return

    let cancelled = false
    const token = getToken()

    async function connectSSE() {
      try {
        const res = await fetch(buildApiUrl('/discovery/logs/stream'), {
          headers: { Authorization: `Bearer ${token || ''}` },
        })
        if (!res.ok || !res.body) return
        const reader = res.body.getReader()
        const decoder = new TextDecoder()

        while (!cancelled) {
          const { done, value } = await reader.read()
          if (done) break
          const text = decoder.decode(value)
          const lines = text.split('\n')
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6))
                if (data.type === 'close') return
                setLogs((prev) => [...prev, data])
              } catch {}
            }
          }
        }
      } catch (err) {
        console.error('SSE connection error:', err)
      }
    }

    connectSSE()
    return () => { cancelled = true }
  }, [discoveryStatus])

  // Auto-scroll logs
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  // Action handlers
  async function handleStart() {
    setError(null)
    setMessage(null)
    setLogs([])
    try {
      await apiRequest('/discovery/run', { method: 'POST', body: JSON.stringify({ max_count: maxCount }) })
      setDiscoveryStatus('running')
      setProgressCount(0)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start')
    }
  }

  async function handlePause() {
    try {
      await apiRequest('/discovery/pause', { method: 'POST' })
      setDiscoveryStatus('paused')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to pause')
    }
  }

  async function handleResume() {
    try {
      await apiRequest('/discovery/resume', { method: 'POST' })
      setDiscoveryStatus('running')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to resume')
    }
  }

  async function handleStop() {
    try {
      await apiRequest('/discovery/stop', { method: 'POST' })
      setDiscoveryStatus('stopped')
      setTimeout(() => {
        setDiscoveryStatus('idle')
        loadData()
      }, 1000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to stop')
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
    window.open(`${url}&token=${token || ''}`, '_blank')
  }

  const totalPages = Math.max(1, Math.ceil(total / 20))
  const presetCounts = [10, 25, 50, 100]
  const progressPercent = maxCount > 0 ? Math.min(100, Math.round((progressCount / maxCount) * 100)) : 0

  return (
    <AppShell
      title="Auto-Discovery"
      subtitle="Female · Blue Tick · 10K+ Followers — Daily Auto-Crawl"
    >
      {/* Date filter + Export */}
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
        <div className="ml-auto">
          <button
            type="button"
            onClick={handleExport}
            className="rounded-lg border border-patrol-border px-4 py-2 text-sm text-patrol-muted hover:text-patrol-accent"
          >
            Export Excel
          </button>
        </div>
      </div>

      {/* Discovery Controls Section */}
      <div className="mb-4 rounded-xl border border-patrol-border bg-patrol-card p-4">
        <div className="flex flex-wrap items-center gap-4">
          {/* Count selector */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-patrol-muted">Count:</span>
            {presetCounts.map((count) => (
              <button
                key={count}
                type="button"
                onClick={() => { setMaxCount(count); setShowCustom(false); setCustomCount('') }}
                className={`rounded-lg border px-3 py-1 text-xs font-medium transition ${
                  maxCount === count && !showCustom
                    ? 'border-patrol-accent/50 bg-patrol-accent/10 text-patrol-accent'
                    : 'border-patrol-border text-patrol-muted hover:text-patrol-text'
                }`}
              >
                {count}
              </button>
            ))}
            <button
              type="button"
              onClick={() => setShowCustom(!showCustom)}
              className={`rounded-lg border px-3 py-1 text-xs font-medium transition ${
                showCustom
                  ? 'border-patrol-accent/50 bg-patrol-accent/10 text-patrol-accent'
                  : 'border-patrol-border text-patrol-muted hover:text-patrol-text'
              }`}
            >
              Custom
            </button>
            {showCustom && (
              <input
                type="number"
                min="1"
                placeholder="e.g. 200"
                value={customCount}
                onChange={(e) => {
                  setCustomCount(e.target.value)
                  const val = parseInt(e.target.value, 10)
                  if (val > 0) setMaxCount(val)
                }}
                className="w-20 rounded-lg border border-patrol-border bg-patrol-surface px-2 py-1 text-xs text-patrol-text"
              />
            )}
          </div>

          {/* Control buttons */}
          <div className="ml-auto flex items-center gap-2">
            {/* Status badge */}
            <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium uppercase ${
              discoveryStatus === 'running'
                ? 'bg-green-500/10 text-green-400 border border-green-500/40'
                : discoveryStatus === 'paused'
                  ? 'bg-amber-500/10 text-amber-400 border border-amber-500/40'
                  : 'bg-patrol-surface text-patrol-muted border border-patrol-border'
            }`}>
              {discoveryStatus}
            </span>

            {/* Play / Pause / Resume / Stop */}
            {(discoveryStatus === 'idle' || discoveryStatus === 'stopped') && (
              <button
                type="button"
                onClick={handleStart}
                className="rounded-lg border border-green-500/40 bg-green-500/10 px-4 py-2 text-sm font-medium text-green-400 hover:bg-green-500/20 transition"
              >
                ▶ Start Discovery
              </button>
            )}
            {discoveryStatus === 'running' && (
              <>
                <button
                  type="button"
                  onClick={handlePause}
                  className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-2 text-sm font-medium text-amber-400 hover:bg-amber-500/20 transition"
                >
                  ⏸ Pause
                </button>
                <button
                  type="button"
                  onClick={handleStop}
                  className="rounded-lg border border-red-500/40 bg-red-500/10 px-4 py-2 text-sm font-medium text-red-400 hover:bg-red-500/20 transition"
                >
                  ⏹ Stop
                </button>
              </>
            )}
            {discoveryStatus === 'paused' && (
              <>
                <button
                  type="button"
                  onClick={handleResume}
                  className="rounded-lg border border-green-500/40 bg-green-500/10 px-4 py-2 text-sm font-medium text-green-400 hover:bg-green-500/20 transition"
                >
                  ▶ Resume
                </button>
                <button
                  type="button"
                  onClick={handleStop}
                  className="rounded-lg border border-red-500/40 bg-red-500/10 px-4 py-2 text-sm font-medium text-red-400 hover:bg-red-500/20 transition"
                >
                  ⏹ Stop
                </button>
              </>
            )}
          </div>
        </div>

        {/* Progress bar */}
        {(discoveryStatus === 'running' || discoveryStatus === 'paused') && (
          <div className="mt-3">
            <p className="mb-1 text-xs text-patrol-muted">
              Discovering: {progressCount}/{maxCount} profiles
            </p>
            <div className="h-2 w-full rounded-full bg-patrol-surface overflow-hidden">
              <div
                className="h-full rounded-full bg-cyan-500 transition-all duration-300"
                style={{ width: `${progressPercent}%` }}
              />
            </div>
          </div>
        )}
      </div>

      {/* Error / Message */}
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

      {/* Live Logs Panel */}
      {logs.length > 0 && (
        <div className="mb-6 rounded-xl border border-patrol-border bg-gray-900 p-4">
          <div className="mb-2 flex items-center justify-between">
            <h3 className="font-mono text-xs text-cyan-400">Live Logs</h3>
            <button
              type="button"
              onClick={() => setLogs([])}
              className="rounded border border-patrol-border px-2 py-0.5 text-[10px] text-patrol-muted hover:text-patrol-text"
            >
              Clear
            </button>
          </div>
          <div className="max-h-64 overflow-y-auto font-mono text-xs">
            {logs.map((log, i) => (
              <div key={i} className={`py-0.5 ${
                log.level === 'error' ? 'text-red-400' :
                log.level === 'warning' ? 'text-amber-400' :
                'text-cyan-300'
              }`}>
                <span className="text-patrol-muted">[{formatLogTime(log.timestamp)}]</span>{' '}
                {log.message}
              </div>
            ))}
            <div ref={logsEndRef} />
          </div>
        </div>
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
      {loading && <p className="text-sm text-patrol-muted">Loading discovered targets...</p>}

      {!loading && items.length === 0 && (
        <div className="rounded-xl border border-dashed border-patrol-border p-12 text-center">
          <p className="font-mono text-patrol-accent">No discovered targets yet</p>
          <p className="mt-2 text-sm text-patrol-muted">
            Click &quot;Start Discovery&quot; to find female verified accounts with 10K+ followers.
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
                  Verified
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
                  {item.inferred_region}
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
                View profile
              </a>
              {!item.is_converted && !item.is_dismissed && (
                <>
                  <button
                    type="button"
                    onClick={() => handleConvert(item.id)}
                    className="rounded-lg border border-patrol-accent/40 bg-patrol-accent/10 px-3 py-1 text-xs font-medium text-patrol-accent"
                  >
                    Add to Monitoring
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
                <span className="text-xs font-medium text-patrol-accent">Monitoring active</span>
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
            Prev
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
            Next
          </button>
        </div>
      )}
    </AppShell>
  )
}
