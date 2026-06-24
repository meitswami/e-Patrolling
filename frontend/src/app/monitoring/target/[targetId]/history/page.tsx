'use client'

import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useCallback, useEffect, useState } from 'react'
import { AppShell } from '@/components/layout/AppShell'
import { PlatformLabel } from '@/components/platforms/PlatformLabel'
import { listCrawlLogs, type CrawlLogItem } from '@/lib/api'
import { isAuthenticated } from '@/lib/auth'
import { formatCrawlTimestamp, durationFromTimestamps } from '@/lib/duration'
import { useTargetIdParam } from '@/lib/route-params'

export default function TargetCrawlHistoryPage() {
  const router = useRouter()
  const targetId = useTargetIdParam()
  const [logs, setLogs] = useState<CrawlLogItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    try {
      const rows = await listCrawlLogs(100, targetId)
      setLogs(rows)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load crawl history')
    } finally {
      setLoading(false)
    }
  }, [targetId])

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace('/admin')
      return
    }
    if (!targetId || targetId === '_' || !/^[0-9a-f-]{36}$/i.test(targetId)) {
      return
    }
    load()
  }, [router, load, targetId])

  const username = logs[0]?.target_username
  const successCount = logs.filter((l) => l.success).length
  const totalAbusive = logs.reduce((sum, l) => sum + l.abusive_detected, 0)

  return (
    <AppShell
      title="Crawl Done History"
      subtitle={
        username
          ? `@${username} · ${logs.length} crawl run(s)`
          : 'Past crawl sessions for this target'
      }
    >
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <Link
          href="/monitoring"
          className="text-sm text-patrol-accent hover:underline"
        >
          ← Live Monitoring
        </Link>
        <Link
          href="/targets"
          className="text-sm text-patrol-muted hover:text-patrol-accent"
        >
          Targets
        </Link>
        {username && (
          <Link
            href={`/monitoring?target=${targetId}`}
            className="rounded-lg border border-patrol-accent/40 px-3 py-1 text-xs text-patrol-accent hover:bg-patrol-accent/10"
          >
            Live monitor @{username}
          </Link>
        )}
      </div>

      {error && (
        <p className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {error}
        </p>
      )}

      {!loading && logs.length > 0 && (
        <div className="mb-6 grid gap-4 sm:grid-cols-3">
          <Stat label="Total runs" value={String(logs.length)} />
          <Stat label="Successful" value={String(successCount)} />
          <Stat label="Abusive captured (all runs)" value={String(totalAbusive)} />
        </div>
      )}

      {loading && <p className="text-sm text-patrol-muted">Loading crawl history…</p>}

      {!loading && logs.length === 0 && (
        <p className="rounded-xl border border-dashed border-patrol-border p-8 text-center text-sm text-patrol-muted">
          No crawl runs recorded for this target yet.
        </p>
      )}

      <div className="space-y-2">
        {logs.map((log) => {
          const duration =
            log.duration_formatted ||
            durationFromTimestamps(log.started_at, log.completed_at, log.duration_seconds)
          return (
            <Link
              key={log.id}
              href={`/monitoring/log/${log.id}`}
              className="block rounded-lg border border-patrol-border bg-patrol-card px-4 py-3 text-sm transition hover:border-patrol-accent/40"
            >
              <div className="flex flex-wrap items-center gap-2">
                <PlatformLabel platform={log.platform} size="sm" />
                <span className={log.success ? 'text-green-400' : 'text-red-400'}>
                  {log.success ? 'OK' : 'Failed'}
                </span>
                {log.crawl_mode && (
                  <span className="rounded border border-patrol-border px-1.5 py-0.5 text-[10px] uppercase text-patrol-muted">
                    {log.crawl_mode.replace('_', ' ')}
                  </span>
                )}
                <span className="font-mono text-patrol-accent">{duration}</span>
                <span className="text-patrol-muted">
                  +{log.comments_new} new · {log.abusive_detected} abusive
                </span>
                <span className="ml-auto text-xs text-patrol-accent">View session →</span>
              </div>
              <p className="mt-1.5 text-xs text-patrol-muted">
                {formatCrawlTimestamp(log.started_at, log.completed_at, log.duration_seconds)}
              </p>
              {log.error_message && (
                <p className="mt-1 text-xs text-red-400">{log.error_message}</p>
              )}
            </Link>
          )
        })}
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
