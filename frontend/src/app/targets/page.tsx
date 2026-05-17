'use client'

import { FormEvent, useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { AppShell } from '@/components/layout/AppShell'
import { PlatformIcon } from '@/components/platforms/PlatformIcon'
import { ACTIVE_PATROL_PLATFORMS, PLATFORM_CONFIG } from '@/lib/constants'
import { createTarget, listTargets, runCrawlTarget } from '@/lib/api'
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
  const [crawlingId, setCrawlingId] = useState<string | null>(null)
  const [crawlMessage, setCrawlMessage] = useState<string | null>(null)

  const [username, setUsername] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [platform, setPlatform] = useState<Platform>('instagram')
  const [profileUrl, setProfileUrl] = useState('')

  async function loadTargets() {
    const data = await listTargets(1, 50)
    setItems(data.items)
    setTotal(data.total)
  }

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace('/login')
      return
    }

    async function load() {
      try {
        await loadTargets()
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load targets')
      } finally {
        setLoading(false)
      }
    }

    load()
  }, [router])

  async function handleCrawl(targetId: string, username: string) {
    setCrawlingId(targetId)
    setCrawlMessage(null)
    setError(null)
    try {
      const result = await runCrawlTarget(targetId)
      if (result.success) {
        setCrawlMessage(
          `@${username}: +${result.comments_new} new, ${result.abusive_detected} abusive`,
        )
      } else {
        setError(result.error ?? `Crawl failed for @${username}`)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Crawl failed')
    } finally {
      setCrawlingId(null)
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

  return (
    <AppShell
      title="Target Accounts"
      subtitle={`${total} account(s) under monitoring`}
    >
      <div className="mb-4 flex justify-end">
        <button
          type="button"
          onClick={() => setShowForm((v) => !v)}
          className="rounded-lg border border-patrol-accent/40 bg-patrol-accent/10 px-4 py-2 text-sm font-medium text-patrol-accent transition hover:bg-patrol-accent/20"
        >
          {showForm ? 'Cancel' : 'Add target'}
        </button>
      </div>

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
            Add accounts to monitor, or run{' '}
            <code className="text-patrol-text">python scripts/seed_demo.py</code> for sample data.
          </p>
        </div>
      )}

      <div className="space-y-3">
        {items.map((item) => {
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
                    item.is_active && item.monitoring_enabled
                      ? 'border-patrol-accent/40 bg-patrol-accent/10 text-patrol-accent'
                      : 'border-patrol-muted/40 text-patrol-muted'
                  }`}
                >
                  {item.is_active && item.monitoring_enabled ? 'Monitoring' : 'Paused'}
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
                {item.is_active && item.monitoring_enabled && (
                  <button
                    type="button"
                    disabled={crawlingId === item.id}
                    onClick={() => handleCrawl(item.id, item.username)}
                    className="rounded-lg border border-patrol-accent/40 bg-patrol-accent/10 px-3 py-1 text-xs font-medium text-patrol-accent disabled:opacity-50"
                  >
                    {crawlingId === item.id ? 'Crawling…' : 'Run crawl'}
                  </button>
                )}
              </div>
            </article>
          )
        })}
      </div>
    </AppShell>
  )
}
