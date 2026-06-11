'use client'

import { useCallback, useEffect, useState } from 'react'
import { Eye, Pause, Play, ScrollText, X } from 'lucide-react'
import { LiveCrawlFeed } from '@/components/crawl/LiveCrawlFeed'
import { PlatformIcon } from '@/components/platforms/PlatformIcon'
import {
  getCrawlViewStatus,
  pauseTargetCrawl,
  resumeTargetCrawl,
  startViewCrawl,
  startViewHistoricalCrawl,
  stopTargetCrawl,
} from '@/lib/api'
import type { Platform } from '@/types'

interface ViewCrawlingPanelProps {
  targetId: string
  username: string
  platform: Platform
  onClose: () => void
}

export function ViewCrawlingPanel({
  targetId,
  username,
  platform,
  onClose,
}: ViewCrawlingPanelProps) {
  const [viewStatus, setViewStatus] = useState<string>('idle')
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const refreshStatus = useCallback(async () => {
    try {
      const st = await getCrawlViewStatus(targetId)
      setViewStatus(st.status)
    } catch {
      /* ignore */
    }
  }, [targetId])

  useEffect(() => {
    refreshStatus()
    const interval = setInterval(refreshStatus, 2000)
    return () => clearInterval(interval)
  }, [refreshStatus])

  async function handleRunCrawl(historical = false) {
    setBusy(true)
    setError(null)
    setMessage(null)
    try {
      const res = historical
        ? await startViewHistoricalCrawl(targetId)
        : await startViewCrawl(targetId)
      setMessage(res.message)
      await refreshStatus()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start view crawl')
    } finally {
      setBusy(false)
    }
  }

  async function handlePause() {
    setError(null)
    try {
      await pauseTargetCrawl(targetId)
      setMessage(`@${username} crawl paused`)
      await refreshStatus()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Pause failed')
    }
  }

  async function handleResume() {
    setError(null)
    try {
      await resumeTargetCrawl(targetId)
      setMessage(`@${username} crawl resumed`)
      await refreshStatus()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Resume failed')
    }
  }

  async function handleStop() {
    setError(null)
    try {
      await stopTargetCrawl(targetId)
      setMessage(`@${username} crawl stopping…`)
      await refreshStatus()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Stop failed')
    }
  }

  const isRunning = viewStatus === 'running'
  const isPaused = viewStatus === 'paused'
  const isActive = isRunning || isPaused

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
      <div className="flex max-h-[90vh] w-full max-w-2xl flex-col overflow-hidden rounded-xl border border-patrol-accent/30 bg-patrol-bg shadow-2xl">
        <div className="flex items-center justify-between border-b border-patrol-border px-4 py-3">
          <div className="flex items-center gap-2">
            <Eye className="h-5 w-5 text-patrol-accent" />
            <div>
              <h2 className="font-mono text-sm font-semibold text-patrol-accent">
                View Crawling
              </h2>
              <p className="flex items-center gap-1.5 text-xs text-patrol-muted">
                <PlatformIcon platform={platform} size="sm" />
                @{username}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1 text-patrol-muted hover:bg-patrol-surface hover:text-patrol-text"
            aria-label="Close"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="border-b border-patrol-border/50 px-4 py-2 text-xs text-patrol-muted">
          Opens a visible Chromium window on this PC while the live feed below shows each
          step and any abusive content detected.
        </div>

        <div className="flex flex-wrap gap-2 border-b border-patrol-border px-4 py-3">
          <button
            type="button"
            disabled={busy || isActive}
            onClick={() => handleRunCrawl(false)}
            className="inline-flex items-center gap-1.5 rounded-lg border border-patrol-accent/40 bg-patrol-accent/10 px-3 py-1.5 text-xs font-medium text-patrol-accent disabled:opacity-50"
          >
            <Play className="h-3.5 w-3.5" />
            Run Crawl
          </button>
          {platform === 'instagram' && (
            <button
              type="button"
              disabled={busy || isActive}
              onClick={() => handleRunCrawl(true)}
              className="inline-flex items-center gap-1.5 rounded-lg border border-amber-500/40 bg-amber-500/10 px-3 py-1.5 text-xs font-medium text-amber-400 disabled:opacity-50"
            >
              <ScrollText className="h-3.5 w-3.5" />
              Crawl History
            </button>
          )}
          <button
            type="button"
            disabled={!isRunning}
            onClick={handlePause}
            className="inline-flex items-center gap-1.5 rounded-lg border border-patrol-border px-3 py-1.5 text-xs text-patrol-muted hover:text-patrol-text disabled:opacity-50"
          >
            <Pause className="h-3.5 w-3.5" />
            Pause
          </button>
          <button
            type="button"
            disabled={!isPaused}
            onClick={handleResume}
            className="inline-flex items-center gap-1.5 rounded-lg border border-green-500/40 bg-green-500/10 px-3 py-1.5 text-xs text-green-400 disabled:opacity-50"
          >
            <Play className="h-3.5 w-3.5" />
            Resume
          </button>
          {isActive && (
            <button
              type="button"
              onClick={handleStop}
              className="ml-auto rounded-lg border border-red-500/40 px-3 py-1.5 text-xs text-red-400 hover:bg-red-500/10"
            >
              Stop
            </button>
          )}
          <span
            className={`ml-auto self-center rounded border px-2 py-0.5 text-[10px] ${
              isRunning
                ? 'border-amber-500/50 text-amber-400'
                : isPaused
                  ? 'border-yellow-500/50 text-yellow-400'
                  : 'border-patrol-muted/40 text-patrol-muted'
            }`}
          >
            {viewStatus}
          </span>
        </div>

        {error && (
          <p className="mx-4 mt-3 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-400">
            {error}
          </p>
        )}
        {message && (
          <p className="mx-4 mt-3 rounded-lg border border-patrol-accent/30 bg-patrol-accent/10 px-3 py-2 text-xs text-patrol-accent">
            {message}
          </p>
        )}

        <div className="flex-1 overflow-y-auto p-4">
          <LiveCrawlFeed targetUsername={username} />
        </div>
      </div>
    </div>
  )
}
