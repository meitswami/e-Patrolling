'use client'

import Link from 'next/link'
import { FormEvent, useCallback, useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { AppShell } from '@/components/layout/AppShell'
import { PlatformIcon } from '@/components/platforms/PlatformIcon'
import { ACTIVE_PATROL_PLATFORMS, PLATFORM_CONFIG } from '@/lib/constants'
import {
  createTarget,
  getCrawlerStatus,
  listTargets,
  runCrawlTarget,
  runHistoricalCrawl,
  updateTarget,
  type RunningCrawlInfo,
} from '@/lib/api'
import { isAuthenticated } from '@/lib/auth'
import type { Platform, TargetAccount } from '@/types'

const PLATFORMS = ACTIVE_PATROL_PLATFORMS

export default function TargetsPage() {
  const router = useRouter()
  const [items, setItems] = useState<TargetAccount[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [crawlingIds, setCrawlingIds] = useState<Set<string>>(new Set())
  const [crawlMessage, setCrawlMessage] = useState<string | null>(null)
  const [runningTargets, setRunningTargets] = useState<RunningCrawlInfo[]>([])

  const [username, setUsername] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [platform, setPlatform] = useState<Platform>('instagram')
  const [profileUrl, setProfileUrl] = useState('')

  const loadTargets = useCallback(async () => {
    const data = await listTargets(1, 50)
    setItems(data.items)
    setTotal(data.total)
  }, [])

  const refreshStatus = useCallback(async () => {
    try {
      const st = await getCrawlerStatus()
      setRunningTargets(st.running_targets ?? [])
    } catch {
      /* ignore */
    }
  }, [])

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace('/login')
      return
    }

    async function load() {
      try {
        await Promise.all([loadTargets(), refreshStatus()])
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load targets')
      } finally {
        setLoading(false)
      }
    }

    load()
    const interval = setInterval(refreshStatus, 4000)
    return () => clearInterval(interval)
  }, [router, loadTargets, refreshStatus])

  function isTargetRunning(targetId: string) {
    return runningTargets.some((r) => r.target_id === targetId) || crawlingIds.has(targetId)
  }

  async function handleCrawl(targetId: string, username: string, historical = false) {
    if (isTargetRunning(targetId)) return
    setCrawlingIds((prev) => new Set(prev).add(targetId))
    setCrawlMessage(null)
    setError(null)
    try {
      const result = historical
        ? await runHistoricalCrawl(targetId)
        : await runCrawlTarget(targetId)
      if (result.success) {
        const proof =
          result.evidence_ids && result.evidence_ids.length > 0
            ? ` · ${result.evidence_ids.length} evidence (view in Live Monitoring)`
            : ''
        const hist =
          result.historical && result.posts_crawled
            ? ` · ${result.posts_crawled} posts scanned`
            : result.historical
              ? ' · historical crawl'
              : ''
        setCrawlMessage(
          `@${username}: +${result.comments_new} new, ${result.abusive_detected} abusive${hist}${proof}`,
        )
        if (result.log_id) {
          setCrawlMessage(
            (m) =>
              `${m} — ` +
              `results: /monitoring/log/${result.log_id}`,
          )
        }
      } else {
        setError(result.error ?? `Crawl failed for @${username}`)
      }
      await refreshStatus()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Crawl failed')
    } finally {
      setCrawlingIds((prev) => {
        const next = new Set(prev)
        next.delete(targetId)
        return next
      })
    }
  }

  async function handleTogglePause(item: TargetAccount) {
    const pausing = item.is_active && item.monitoring_enabled
    setError(null)
    try {
      await updateTarget(item.id, { monitoring_enabled: !pausing })
      await loadTargets()
      setCrawlMessage(
        pausing
          ? `@${item.username} paused — will not be included in crawl-all`
          : `@${item.username} resumed monitoring`,
      )
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update target')
    }
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setSubmitting(true)
    setError(null)
    try {
      await createTarget({
        username: username.trim(),
        display_name: displayName.trim() || undefined,
        platform,
        profile_url: profileUrl.trim(),
      })
      setUsername('')
      setDisplayName('')
      setProfileUrl('')
      setShowForm(false)
      await loadTargets()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create target')
    } finally {
      setSubmitting(false)
    }
  }

  const monitoringCount = items.filter((i) => i.is_active && i.monitoring_enabled).length

  return (
    <AppShell
      title="Target Accounts"
      subtitle={`${monitoringCount} of ${total} account(s) actively monitored`}
    >
      <p className="mb-4 text-xs text-patrol-muted">
        <strong className="text-patrol-text">Run crawl</strong> checks recent activity on the profile.
        <strong className="ml-2 text-patrol-text">Crawl history</strong> scrolls older posts and reads
        comments on each (Instagram; takes longer).
      </p>
      <div className="mb-4 flex flex-wrap justify-end gap-2">
        <Link
          href="/monitoring"
          className="rounded-lg border border-patrol-border px-4 py-2 text-sm text-patrol-muted hover:text-patrol-accent"
        >
          Live Monitoring
        </Link>
        <button
          type="button"
          onClick={() => setShowForm((v) => !v)}
          className="rounded-lg border border-patrol-accent/40 bg-patrol-accent/10 px-4 py-2 text-sm font-medium text-patrol-accent transition hover:bg-patrol-accent/20"
        >
          {showForm ? 'Cancel' : 'Add target'}
        </button>
      </div>

      {runningTargets.length > 0 && (
        <div className="mb-4 rounded-lg border border-patrol-accent/30 bg-patrol-accent/10 px-4 py-3 text-sm">
          <p className="font-medium text-patrol-accent">Crawlers running:</p>
          <ul className="mt-1 text-patrol-text">
            {runningTargets.map((r) => (
              <li key={r.target_id}>@{r.target_username} ({r.platform})</li>
            ))}
          </ul>
        </div>
      )}

      {error && (
        <p className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {error}
        </p>
      )}
      {crawlMessage && (
        <p className="mb-4 rounded-lg border border-patrol-accent/30 bg-patrol-accent/10 px-4 py-3 text-sm text-patrol-accent">
          {crawlMessage}
        </p>
      )}

      {showForm && (
        <form
          onSubmit={handleSubmit}
          className="mb-6 rounded-xl border border-patrol-border bg-patrol-card p-4"
        >
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block text-sm">
              <span className="text-patrol-muted">Username</span>
              <input
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="mt-1 w-full rounded-lg border border-patrol-border bg-patrol-surface px-3 py-2 text-patrol-text"
                placeholder="handle_without_at"
              />
            </label>
            <label className="block text-sm">
              <span className="text-patrol-muted">Display name</span>
              <input
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                className="mt-1 w-full rounded-lg border border-patrol-border bg-patrol-surface px-3 py-2 text-patrol-text"
              />
            </label>
            <label className="block text-sm">
              <span className="inline-flex items-center gap-1.5 text-patrol-muted">
                <PlatformIcon platform={platform} size="sm" />
                Platform
              </span>
              <select
                value={platform}
                onChange={(e) => setPlatform(e.target.value as Platform)}
                className="mt-1 w-full rounded-lg border border-patrol-border bg-patrol-surface px-3 py-2 text-patrol-text"
              >
                {PLATFORMS.map((p) => (
                  <option key={p} value={p}>
                    {PLATFORM_CONFIG[p].label}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-sm">
              <span className="text-patrol-muted">Profile URL</span>
              <input
                required
                type="url"
                value={profileUrl}
                onChange={(e) => setProfileUrl(e.target.value)}
                className="mt-1 w-full rounded-lg border border-patrol-border bg-patrol-surface px-3 py-2 text-patrol-text"
                placeholder="https://instagram.com/..."
              />
            </label>
          </div>
          <button
            type="submit"
            disabled={submitting}
            className="mt-4 rounded-lg bg-patrol-accent px-4 py-2 text-sm font-medium text-patrol-bg disabled:opacity-50"
          >
            {submitting ? 'Saving…' : 'Save target'}
          </button>
        </form>
      )}

      {loading && <p className="text-sm text-patrol-muted">Loading targets…</p>}

      {!loading && items.length === 0 && !error && (
        <div className="rounded-xl border border-dashed border-patrol-border p-12 text-center">
          <p className="font-mono text-patrol-accent">No targets yet</p>
          <p className="mt-2 text-sm text-patrol-muted">
            Add Instagram or other accounts to monitor with live crawlers.
          </p>
        </div>
      )}

      <div className="space-y-3">
        {items.map((item) => {
          const active = item.is_active && item.monitoring_enabled
          const running = isTargetRunning(item.id)
          return (
            <article
              key={item.id}
              className="rounded-xl border border-patrol-border bg-patrol-card p-4 transition hover:border-patrol-accent/20"
            >
              <div className="flex flex-wrap items-center gap-2">
                <PlatformIcon platform={item.platform} size="lg" />
                <span className="font-mono text-patrol-accent">@{item.username}</span>
                {item.display_name && (
                  <span className="text-sm text-patrol-text">{item.display_name}</span>
                )}
                <span
                  className={`rounded border px-2 py-0.5 text-xs ${
                    running
                      ? 'border-amber-500/50 bg-amber-500/10 text-amber-400'
                      : active
                        ? 'border-patrol-accent/40 bg-patrol-accent/10 text-patrol-accent'
                        : 'border-patrol-muted/40 text-patrol-muted'
                  }`}
                >
                  {running ? 'Crawling…' : active ? 'Monitoring' : 'Paused'}
                </span>
              </div>
              <div className="mt-3 flex flex-wrap items-center gap-3">
                <a
                  href={item.profile_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="truncate text-xs text-patrol-muted hover:text-patrol-accent"
                >
                  {item.profile_url}
                </a>
                <button
                  type="button"
                  onClick={() => handleTogglePause(item)}
                  className="rounded-lg border border-patrol-border px-3 py-1 text-xs text-patrol-muted hover:border-patrol-accent/40 hover:text-patrol-accent"
                >
                  {active ? 'Pause' : 'Resume'}
                </button>
                {active && (
                  <>
                    <button
                      type="button"
                      disabled={running}
                      onClick={() => handleCrawl(item.id, item.username, false)}
                      className="rounded-lg border border-patrol-accent/40 bg-patrol-accent/10 px-3 py-1 text-xs font-medium text-patrol-accent disabled:opacity-50"
                    >
                      {running ? 'Crawling…' : 'Run crawl'}
                    </button>
                    {item.platform === 'instagram' && (
                      <button
                        type="button"
                        disabled={running}
                        onClick={() => handleCrawl(item.id, item.username, true)}
                        className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-3 py-1 text-xs font-medium text-amber-400 disabled:opacity-50"
                        title="Scroll older posts and crawl all comments on each"
                      >
                        {running ? 'Crawling…' : 'Crawl history'}
                      </button>
                    )}
                  </>
                )}
              </div>
            </article>
          )
        })}
      </div>
    </AppShell>
  )
}
