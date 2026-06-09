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
  runHistoricalCrawl,
  startCrawlTarget,
  updateTarget,
  type RunningCrawlInfo,
  type ProfilePreviewResult,
} from '@/lib/api'
import { isAuthenticated } from '@/lib/auth'
import { getToken } from '@/lib/auth'
import { buildApiUrl } from '@/lib/constants'
import type { Platform, TargetAccount, TargetSource } from '@/types'
import { ProfilePreviewDropdown } from '@/components/ProfilePreviewDropdown'

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
  const [sourceFilter, setSourceFilter] = useState<TargetSource | 'all'>('admin_panel')

  const loadTargets = useCallback(async () => {
    const source = sourceFilter === 'all' ? undefined : sourceFilter
    const data = await listTargets(1, 50, source)
    setItems(data.items)
    setTotal(data.total)
  }, [sourceFilter])

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
      router.replace('/admin')
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
      if (historical) {
        const result = await runHistoricalCrawl(targetId)
        if (result.success) {
          const proof =
            result.evidence_ids && result.evidence_ids.length > 0
              ? ` · ${result.evidence_ids.length} evidence (view in Live Monitoring)`
              : ''
          const hist =
            result.posts_crawled
              ? ` · ${result.posts_crawled} posts scanned`
              : ' · historical crawl'
          setCrawlMessage(
            `@${username}: +${result.comments_new} new, ${result.abusive_detected} abusive${hist}${proof}`,
          )
          if (result.log_id) {
            setCrawlMessage(
              (m) => `${m} — results: /monitoring/log/${result.log_id}`,
            )
          }
        } else {
          setError(result.error ?? `Crawl failed for @${username}`)
        }
      } else {
        const res = await startCrawlTarget(targetId)
        setCrawlMessage(`@${username}: crawl ${res.status} — watch Live Monitoring for results`)
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
      <div className="mb-4 flex flex-wrap gap-2">
        {(
          [
            ['all', 'All targets'],
            ['website_intake', 'From website intake'],
            ['admin_panel', 'Admin panel targets'],
          ] as const
        ).map(([value, label]) => (
          <button
            key={value}
            type="button"
            onClick={() => setSourceFilter(value)}
            className={`rounded-lg border px-3 py-1.5 text-sm ${
              sourceFilter === value
                ? 'border-patrol-accent/50 bg-patrol-accent/10 text-patrol-accent'
                : 'border-patrol-border text-patrol-muted hover:text-patrol-text'
            }`}
          >
            {label}
          </button>
        ))}
        <Link
          href="/website-requests"
          className="ml-auto rounded-lg border border-sky-500/40 px-3 py-1.5 text-sm text-sky-300 hover:bg-sky-500/10"
        >
          Website requests →
        </Link>
      </div>

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
        <Link
          href="/discovery"
          className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-2 text-sm text-amber-400 hover:bg-amber-500/20"
        >
          🔍 Auto-Discovery
        </Link>
        <BulkImportButton onComplete={loadTargets} />
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
              <span className="text-patrol-muted">Username or Profile URL</span>
              <ProfilePreviewDropdown
                value={username}
                onChange={setUsername}
                platform={platform}
                placeholder="handle_without_at or profile URL"
                darkMode={true}
                inputClassName="mt-1 w-full rounded-lg border border-patrol-border bg-patrol-surface px-3 py-2 text-patrol-text"
                onSelect={(profile: ProfilePreviewResult) => {
                  setUsername(profile.username)
                  if (profile.display_name) setDisplayName(profile.display_name)
                  if (profile.profile_url) setProfileUrl(profile.profile_url)
                }}
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
                {item.source === 'website_intake' && (
                  <span className="rounded border border-sky-500/40 bg-sky-500/10 px-2 py-0.5 text-xs text-sky-300">
                    Website intake
                  </span>
                )}
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
                {active && !running && (
                  <>
                    <button
                      type="button"
                      disabled={running}
                      onClick={() => handleCrawl(item.id, item.username, false)}
                      className="rounded-lg border border-patrol-accent/40 bg-patrol-accent/10 px-3 py-1 text-xs font-medium text-patrol-accent disabled:opacity-50"
                    >
                      Run crawl
                    </button>
                    {item.platform === 'instagram' && (
                      <button
                        type="button"
                        disabled={running}
                        onClick={() => handleCrawl(item.id, item.username, true)}
                        className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-3 py-1 text-xs font-medium text-amber-400 disabled:opacity-50"
                        title="Scroll older posts and crawl all comments on each"
                      >
                        Crawl history
                      </button>
                    )}
                  </>
                )}
                {active && running && (
                  <Link
                    href={`/monitoring?target=${item.id}`}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-green-500/40 bg-green-500/10 px-3 py-1 text-xs font-medium text-green-400 hover:bg-green-500/20 transition"
                  >
                    <span className="h-2 w-2 rounded-full bg-green-400 animate-pulse" />
                    Live Monitoring
                  </Link>
                )}
              </div>
            </article>
          )
        })}
      </div>
    </AppShell>
  )
}

function BulkImportButton({ onComplete }: { onComplete: () => Promise<void> }) {
  const [showModal, setShowModal] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [result, setResult] = useState<{
    imported: number
    skipped: number
    message: string
    errors?: { row: number; error: string }[]
  } | null>(null)
  const [importError, setImportError] = useState<string | null>(null)

  function handleDownloadTemplate() {
    const token = getToken()
    const url = buildApiUrl('/targets/import/template.xlsx')
    // Open with auth header via anchor
    const a = document.createElement('a')
    a.href = url
    a.download = 'shakti_target_import_template.xlsx'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
  }

  async function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    setImportError(null)
    setResult(null)

    const formData = new FormData()
    formData.append('file', file)

    try {
      const token = getToken()
      const res = await fetch(buildApiUrl('/targets/import/import'), {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: formData,
      })
      const body = await res.json()
      if (!res.ok) {
        setImportError(body.detail || `Import failed (${res.status})`)
      } else {
        setResult(body)
        await onComplete()
      }
    } catch (err) {
      setImportError(err instanceof Error ? err.message : 'Upload failed')
    } finally {
      setUploading(false)
      // Reset input
      e.target.value = ''
    }
  }

  return (
    <>
      <button
        type="button"
        onClick={() => setShowModal(true)}
        className="rounded-lg border border-sky-500/40 bg-sky-500/10 px-4 py-2 text-sm text-sky-300 hover:bg-sky-500/20"
      >
        📄 Bulk Import
      </button>

      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="w-full max-w-lg rounded-xl border border-patrol-border bg-patrol-bg p-6">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold text-patrol-text">Bulk Import Targets</h2>
              <button
                type="button"
                onClick={() => { setShowModal(false); setResult(null); setImportError(null) }}
                className="text-patrol-muted hover:text-patrol-text"
              >
                ✕
              </button>
            </div>

            <div className="mt-4 space-y-4">
              {/* Step 1: Download template */}
              <div className="rounded-lg border border-patrol-border bg-patrol-surface p-4">
                <p className="text-sm font-medium text-patrol-text">Step 1: Download Template</p>
                <p className="mt-1 text-xs text-patrol-muted">
                  Download the sample Excel template to understand the column format.
                </p>
                <button
                  type="button"
                  onClick={handleDownloadTemplate}
                  className="mt-2 rounded-lg border border-patrol-accent/40 bg-patrol-accent/10 px-3 py-1.5 text-xs font-medium text-patrol-accent"
                >
                  📥 Download Template (.xlsx)
                </button>
              </div>

              {/* Step 2: Upload file */}
              <div className="rounded-lg border border-patrol-border bg-patrol-surface p-4">
                <p className="text-sm font-medium text-patrol-text">Step 2: Upload Filled Excel</p>
                <p className="mt-1 text-xs text-patrol-muted">
                  Fill in your targets in the template and upload. Max 500 rows per import.
                </p>
                <label className="mt-2 block">
                  <input
                    type="file"
                    accept=".xlsx,.xls"
                    onChange={handleFileUpload}
                    disabled={uploading}
                    className="block w-full text-sm text-patrol-muted file:mr-3 file:rounded-lg file:border file:border-patrol-accent/40 file:bg-patrol-accent/10 file:px-3 file:py-1.5 file:text-xs file:font-medium file:text-patrol-accent disabled:opacity-50"
                  />
                </label>
                {uploading && (
                  <p className="mt-2 text-xs text-patrol-accent">Uploading and importing…</p>
                )}
              </div>

              {/* Error */}
              {importError && (
                <p className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-400">
                  {importError}
                </p>
              )}

              {/* Result */}
              {result && (
                <div className="rounded-lg border border-patrol-accent/30 bg-patrol-accent/10 p-4">
                  <p className="text-sm font-medium text-patrol-accent">{result.message}</p>
                  <div className="mt-2 grid grid-cols-2 gap-2 text-xs">
                    <p className="text-patrol-text">✓ Imported: {result.imported}</p>
                    <p className="text-patrol-muted">⏭ Skipped: {result.skipped}</p>
                  </div>
                  {result.errors && result.errors.length > 0 && (
                    <details className="mt-2">
                      <summary className="cursor-pointer text-xs text-patrol-muted">
                        View errors ({result.errors.length})
                      </summary>
                      <ul className="mt-1 space-y-0.5 text-xs text-red-400">
                        {result.errors.map((err, i) => (
                          <li key={i}>Row {err.row}: {err.error}</li>
                        ))}
                      </ul>
                    </details>
                  )}
                </div>
              )}

              {/* Template columns info */}
              <div className="text-xs text-patrol-muted">
                <p className="font-medium text-patrol-text">Required columns:</p>
                <p>username · platform · profile_url</p>
                <p className="mt-1 font-medium text-patrol-text">Optional columns:</p>
                <p>display_name · follower_count · is_verified · gender · region · notes</p>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
