'use client'

import Link from 'next/link'
import { Suspense, useCallback, useEffect, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { PlatformLabel } from '@/components/platforms/PlatformLabel'
import { PlatformMonitorGrid } from '@/components/platforms/PlatformMonitorGrid'
import { LiveCrawlFeed } from '@/components/crawl/LiveCrawlFeed'
import { ClientOnly } from '@/components/ClientOnly'
import { AppShell } from '@/components/layout/AppShell'
import {
  clearCrawlErrorLogs,
  getCrawlerStatus,
  listCrawlLogs,
  scheduleCrawlAll,
  stopCrawlAll,
  type CrawlLogItem,
  type CrawlerStatus,
} from '@/lib/api'
import { isAuthenticated } from '@/lib/auth'
import { formatCrawlTimestamp } from '@/lib/duration'

export default function MonitoringPage() {
  return (
    <Suspense fallback={<AppShell title="Live Monitoring" subtitle="Loading..."><p className="text-sm text-patrol-muted">Loading...</p></AppShell>}>
      <MonitoringPageContent />
    </Suspense>
  )
}

function MonitoringPageContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const targetFilter = searchParams.get('target')
  const [status, setStatus] = useState<CrawlerStatus | null>(null)
  const [logs, setLogs] = useState<CrawlLogItem[]>([])
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastRun, setLastRun] = useState<string | null>(null)
  const [stopping, setStopping] = useState(false)
  const [clearingErrors, setClearingErrors] = useState(false)

  const load = useCallback(async () => {
    try {
      const [st, logRows] = await Promise.all([getCrawlerStatus(), listCrawlLogs(15)])
      setStatus(st)
      setLogs(logRows)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load monitoring')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace('/admin')
      return
    }
    load()
    const interval = setInterval(load, 5000)
    return () => clearInterval(interval)
  }, [router, load])

  async function handleStop() {
    setStopping(true)
    setError(null)
    try {
      const res = await stopCrawlAll()
      setLastRun(res.message)
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Stop request failed')
    } finally {
      setStopping(false)
    }
  }

  async function handleRunAll() {
    setRunning(true)
    setError(null)
    try {
      const res = await scheduleCrawlAll()
      setLastRun(res.message || `Crawl-all ${res.status}`)
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Crawl failed')
    } finally {
      setRunning(false)
    }
  }

  const isBusy =
    running || status?.scheduler_is_running || (status?.running_targets?.length ?? 0) > 0

  const runningTargets = targetFilter
    ? (status?.running_targets ?? []).filter((r) => r.target_id === targetFilter)
    : (status?.running_targets ?? [])

  const filteredLogs = targetFilter
    ? logs.filter((l) => l.target_id === targetFilter)
    : logs

  const targetUsername = targetFilter
    ? (runningTargets.find((r) => r.target_id === targetFilter)?.target_username ||
       logs.find((l) => l.target_id === targetFilter)?.target_username ||
       null)
    : null

  return (
    <AppShell title="Live Monitoring" subtitle="Crawler status and recent runs">
      {error && (
        <p className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {error}
        </p>
      )}

      {targetFilter && (
        <div className="mb-4 flex items-center justify-between rounded-lg border border-patrol-accent/40 bg-patrol-accent/10 px-4 py-3">
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-patrol-accent animate-pulse" />
            <span className="text-sm font-medium text-patrol-accent">
              Monitoring: @{targetUsername || targetFilter}
            </span>
          </div>
          <Link
            href="/monitoring"
            className="rounded-lg border border-patrol-border px-3 py-1.5 text-xs text-patrol-muted hover:text-patrol-text hover:border-patrol-accent/40 transition"
          >
            Show All
          </Link>
          <Link
            href={`/monitoring/target/${targetFilter}/history`}
            className="rounded-lg border border-patrol-accent/40 bg-patrol-accent/10 px-3 py-1.5 text-xs text-patrol-accent hover:bg-patrol-accent/20 transition"
          >
            Crawl Done History
          </Link>
        </div>
      )}

      <ClientOnly fallback={<p className="text-sm text-patrol-muted">Loading patrol status…</p>}>
        {status?.platforms && status.platforms.length > 0 && (
          <div className="mb-6">
            <PlatformMonitorGrid platforms={status.platforms} compact />
          </div>
        )}

        {status && (
          <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Stat label="Mode" value="Live" />
            <Stat
              label="Instagram"
              value={
                status.instagram_credentials_configured
                  ? 'Session connected'
                  : 'Connect in Settings'
              }
            />
            <Stat label="Redis" value={status.redis_enabled ? 'On' : 'Off'} />
            <Stat
              label="Scheduler"
              value={
                status.scheduler_enabled
                  ? `Every ${status.crawl_interval_seconds}s`
                  : 'Off'
              }
            />
          </div>
        )}

        {status?.running_targets && status.running_targets.length > 0 && runningTargets.length > 0 && (
          <div className="mb-4 rounded-xl border border-patrol-accent/40 bg-patrol-accent/10 p-4">
            <h2 className="font-mono text-sm text-patrol-accent">Crawlers running now</h2>
            <ul className="mt-2 space-y-1 text-sm text-patrol-text">
              {runningTargets.map((r) => (
                <li key={r.target_id}>
                  <PlatformLabel platform={r.platform} size="sm" className="mr-2 inline" />
                  @{r.target_username}
                  <span className="ml-2 text-xs text-patrol-muted">
                    (
                    {r.mode === 'crawl_all'
                      ? 'crawl-all'
                      : r.mode === 'historical'
                        ? 'history'
                        : 'recent'}
                    )
                  </span>
                </li>
              ))}
            </ul>
            <p className="mt-2 text-xs text-patrol-muted">
              Wait for these to finish before starting another crawl on the same target.
            </p>
          </div>
        )}

        {status?.scheduler_is_running && !status?.running_targets?.length && (
          <p className="mb-4 text-sm text-patrol-accent">Crawl-all in progress…</p>
        )}
        {status?.scheduler_last_run_message && !isBusy && (
          <p className="mb-4 text-xs text-patrol-muted">{status.scheduler_last_run_message}</p>
        )}
      </ClientOnly>

      <div className="mb-6 flex flex-wrap items-center gap-3">
        <button
          type="button"
          disabled={isBusy}
          onClick={handleRunAll}
          className="rounded-lg bg-patrol-accent px-4 py-2 text-sm font-medium text-patrol-bg disabled:opacity-50"
        >
          {isBusy ? 'Crawl in progress…' : 'Run crawl now'}
        </button>
        {isBusy && (
          <button
            type="button"
            disabled={stopping}
            onClick={handleStop}
            className="rounded-lg border border-red-500/40 px-4 py-2 text-sm text-red-400 disabled:opacity-50"
          >
            {stopping ? 'Stopping…' : 'Stop crawl'}
          </button>
        )}
        {lastRun && <span className="text-sm text-patrol-muted">{lastRun}</span>}
      </div>

      {/* Live Crawl Activity Feed — real-time crawler actions */}
      <div className="mb-6">
        <LiveCrawlFeed targetUsername={targetUsername} />
      </div>

      {status?.recent_errors && status.recent_errors.length > 0 && (
        <div className="mb-6 rounded-xl border border-red-500/30 bg-red-500/5 p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="font-mono text-sm text-red-400">Recent crawler errors</h2>
            <button
              type="button"
              disabled={clearingErrors}
              onClick={async () => {
                setClearingErrors(true)
                try {
                  await clearCrawlErrorLogs(true)
                  await load()
                  setError(null)
                } catch (err) {
                  setError(err instanceof Error ? err.message : 'Could not clear logs')
                } finally {
                  setClearingErrors(false)
                }
              }}
              className="rounded border border-patrol-border px-3 py-1 text-xs text-patrol-muted hover:text-patrol-text disabled:opacity-50"
            >
              {clearingErrors ? 'Clearing…' : 'Clear old errors'}
            </button>
          </div>
          <ul className="mt-2 space-y-2 text-xs text-patrol-muted">
            {status.recent_errors.map((err, i) => (
              <li key={i}>
                <span className="text-patrol-text">{err.platform}</span>
                {err.started_at && (
                  <span className="ml-2">{new Date(err.started_at).toLocaleString()}</span>
                )}
                <p className="text-red-400">{err.error_message}</p>
              </li>
            ))}
          </ul>
        </div>
      )}

      {loading && <p className="text-sm text-patrol-muted">Loading logs…</p>}

      <div className="space-y-2">
        <h2 className="font-mono text-sm text-patrol-accent">Recent crawl logs</h2>
        <p className="text-xs text-patrol-muted">
          Click a run to see abusive comments, screenshots, and offender names.
        </p>
        {filteredLogs.length === 0 && !loading && (
          <p className="text-sm text-patrol-muted">No crawl runs yet.</p>
        )}
        {filteredLogs.map((log) => (
          <Link
            key={log.id}
            href={`/monitoring/log/${log.id}`}
            className="block rounded-lg border border-patrol-border bg-patrol-card px-4 py-3 text-sm transition hover:border-patrol-accent/40"
          >
            <div className="flex flex-wrap items-center gap-2">
              <PlatformLabel platform={log.platform} size="sm" className="font-mono text-patrol-accent" />
              {log.target_username && (
                <span className="text-patrol-text">@{log.target_username}</span>
              )}
              <span className={log.success ? 'text-green-400' : 'text-red-400'}>
                {log.success ? 'OK' : 'Failed'}
              </span>
              <span className="text-patrol-muted">
                +{log.comments_new} new · {log.abusive_detected} abusive
              </span>
              <span className="ml-auto text-xs text-patrol-accent">View proof →</span>
            </div>
            <p className="mt-1.5 text-xs text-patrol-muted">
              {formatCrawlTimestamp(log.started_at, log.completed_at, log.duration_seconds)}
            </p>
            {log.error_message && (
              <p className="mt-1 text-xs text-red-400">{log.error_message}</p>
            )}
          </Link>
        ))}
      </div>
    </AppShell>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-patrol-border bg-patrol-card p-4">
      <p className="text-xs text-patrol-muted">{label}</p>
      <p className="mt-1 text-sm text-patrol-text">{value}</p>
    </div>
  )
}
