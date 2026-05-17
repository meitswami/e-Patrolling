'use client'

import { useCallback, useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { PlatformLabel } from '@/components/platforms/PlatformLabel'
import { PlatformMonitorGrid } from '@/components/platforms/PlatformMonitorGrid'
import { ClientOnly } from '@/components/ClientOnly'
import { AppShell } from '@/components/layout/AppShell'
import {
  getCrawlerStatus,
  listCrawlLogs,
  runCrawlAll,
  stopCrawlAll,
  type CrawlLogItem,
  type CrawlerStatus,
} from '@/lib/api'
import { isAuthenticated } from '@/lib/auth'

export default function MonitoringPage() {
  const router = useRouter()
  const [status, setStatus] = useState<CrawlerStatus | null>(null)
  const [logs, setLogs] = useState<CrawlLogItem[]>([])
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastRun, setLastRun] = useState<string | null>(null)
  const [stopping, setStopping] = useState(false)

  const load = useCallback(async () => {
    try {
      const [st, logRows] = await Promise.all([getCrawlerStatus(), listCrawlLogs(15)])
      setStatus(st)
      setLogs(logRows)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load monitoring')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace('/login')
      return
    }
    load()
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
      const results = await runCrawlAll()
      const ok = results.filter((r) => r.success).length
      setLastRun(`${ok}/${results.length} targets crawled`)
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Crawl failed')
    } finally {
      setRunning(false)
    }
  }

  return (
    <AppShell title="Live Monitoring" subtitle="Crawler status and recent runs">
      {error && (
        <p className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {error}
        </p>
      )}

      <ClientOnly fallback={<p className="text-sm text-patrol-muted">Loading patrol status…</p>}>
        {status?.platforms && status.platforms.length > 0 && (
          <div className="mb-6">
            <PlatformMonitorGrid
              platforms={status.platforms}
              demoMode={status.demo_mode}
              compact
            />
          </div>
        )}

        {status && (
          <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Stat label="Mode" value={status.demo_mode ? 'Demo' : 'Live'} />
            <Stat label="Redis" value={status.redis_enabled ? 'On' : 'Off'} />
            <Stat
              label="Scheduler"
              value={
                status.scheduler_enabled
                  ? `Every ${status.crawl_interval_seconds}s`
                  : 'Off'
              }
            />
            <Stat
              label="Last scheduled run"
              value={
                status.scheduler_last_run_at
                  ? new Date(status.scheduler_last_run_at).toLocaleString()
                  : 'Never'
              }
            />
          </div>
        )}

        {status?.scheduler_is_running && (
          <p className="mb-4 text-sm text-patrol-accent">Crawl-all in progress…</p>
        )}
        {status?.scheduler_last_run_message && !status.scheduler_is_running && (
          <p className="mb-4 text-xs text-patrol-muted">{status.scheduler_last_run_message}</p>
        )}
      </ClientOnly>

      <div className="mb-6 flex flex-wrap items-center gap-3">
        <button
          type="button"
          disabled={running}
          onClick={handleRunAll}
          className="rounded-lg bg-patrol-accent px-4 py-2 text-sm font-medium text-patrol-bg disabled:opacity-50"
        >
          {running ? 'Crawling…' : 'Run crawl now'}
        </button>
        {(running || status?.scheduler_is_running) && (
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

      {status?.recent_errors && status.recent_errors.length > 0 && (
        <div className="mb-6 rounded-xl border border-red-500/30 bg-red-500/5 p-4">
          <h2 className="font-mono text-sm text-red-400">Recent crawler errors</h2>
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
        {logs.length === 0 && !loading && (
          <p className="text-sm text-patrol-muted">No crawl runs yet.</p>
        )}
        {logs.map((log) => (
          <article
            key={log.id}
            className="rounded-lg border border-patrol-border bg-patrol-card px-4 py-3 text-sm"
          >
            <div className="flex flex-wrap gap-2">
              <PlatformLabel platform={log.platform} size="sm" className="font-mono text-patrol-accent" />
              <span className={log.success ? 'text-green-400' : 'text-red-400'}>
                {log.success ? 'OK' : 'Failed'}
              </span>
              <span className="text-patrol-muted">
                +{log.comments_new} new · {log.abusive_detected} abusive
              </span>
            </div>
            {log.error_message && (
              <p className="mt-1 text-xs text-red-400">{log.error_message}</p>
            )}
          </article>
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
