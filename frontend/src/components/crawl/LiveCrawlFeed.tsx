'use client'

import { useEffect, useRef, useState } from 'react'
import { Activity, AlertTriangle, Eye, Loader2, Search, Terminal } from 'lucide-react'
import { connectDashboardWs, type WsMessage } from '@/lib/ws'
import { isAuthenticated } from '@/lib/auth'

interface CrawlActivity {
  id: string
  target_username: string
  platform: string
  activity_type: string
  message: string
  detail: string | null
  timestamp: string
}

const ACTIVITY_ICONS: Record<string, { icon: typeof Activity; color: string }> = {
  crawl_started: { icon: Loader2, color: 'text-patrol-accent' },
  navigating_profile: { icon: Eye, color: 'text-blue-400' },
  collecting_posts: { icon: Search, color: 'text-cyan-400' },
  opening_post: { icon: Eye, color: 'text-blue-400' },
  expanding_comments: { icon: Loader2, color: 'text-yellow-400' },
  comments_found: { icon: Terminal, color: 'text-green-400' },
  comment_abusive: { icon: AlertTriangle, color: 'text-red-400' },
  post_complete: { icon: Activity, color: 'text-patrol-accent' },
  crawl_finished: { icon: Activity, color: 'text-green-400' },
  crawl_error: { icon: AlertTriangle, color: 'text-red-500' },
}

const MAX_ENTRIES = 50

export function LiveCrawlFeed({ targetUsername }: { targetUsername?: string | null }) {
  const [activities, setActivities] = useState<CrawlActivity[]>([])
  const [connected, setConnected] = useState(false)
  const feedRef = useRef<HTMLDivElement>(null)
  const autoScrollRef = useRef(true)

  useEffect(() => {
    if (!isAuthenticated()) return

    const disconnect = connectDashboardWs((msg: WsMessage) => {
      if (msg.type === 'connected') {
        setConnected(true)
        return
      }
      if (msg.type === 'crawl_activity') {
        if (targetUsername && msg.data.target_username !== targetUsername) return
        const entry: CrawlActivity = {
          id: `${msg.data.timestamp}-${msg.data.activity_type}-${Math.random().toString(36).slice(2, 8)}`,
          ...msg.data,
        }
        setActivities((prev) => [...prev, entry].slice(-MAX_ENTRIES))
      }
      if (msg.type === 'crawl_completed') {
        if (targetUsername && msg.data.target_username !== targetUsername) return
        const entry: CrawlActivity = {
          id: `completed-${Date.now()}`,
          target_username: msg.data.target_username,
          platform: 'instagram',
          activity_type: 'crawl_finished',
          message: `Crawl finished: +${msg.data.comments_new} comments, ${msg.data.abusive_detected} abusive`,
          detail: msg.data.success ? 'Success' : 'Failed',
          timestamp: new Date().toISOString(),
        }
        setActivities((prev) => [...prev, entry].slice(-MAX_ENTRIES))
      }
    })

    return disconnect
  }, [targetUsername])

  // Auto-scroll to bottom when new entries arrive
  useEffect(() => {
    if (autoScrollRef.current && feedRef.current) {
      feedRef.current.scrollTop = feedRef.current.scrollHeight
    }
  }, [activities])

  const handleScroll = () => {
    if (!feedRef.current) return
    const { scrollTop, scrollHeight, clientHeight } = feedRef.current
    autoScrollRef.current = scrollHeight - scrollTop - clientHeight < 40
  }

  return (
    <div className="rounded-xl border border-patrol-border bg-patrol-card overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-patrol-border/50 px-4 py-3">
        <div className="flex items-center gap-2">
          <Terminal className="h-4 w-4 text-patrol-accent" />
          <h3 className="font-mono text-sm font-semibold text-patrol-accent">
            Live Crawl Activity
          </h3>
          {connected && (
            <span className="flex items-center gap-1 rounded-full border border-green-500/30 bg-green-500/10 px-2 py-0.5 text-[10px] text-green-400">
              <span className="h-1.5 w-1.5 rounded-full bg-green-400 animate-pulse" />
              Connected
            </span>
          )}
        </div>
        <p className="text-[10px] text-patrol-muted">
          Real-time crawler actions (replaces visible browser window)
        </p>
      </div>

      {/* Feed */}
      <div
        ref={feedRef}
        onScroll={handleScroll}
        className="h-64 overflow-y-auto bg-patrol-bg/30 px-3 py-2 font-mono text-xs"
      >
        {activities.length === 0 ? (
          <div className="flex h-full items-center justify-center">
            <p className="text-patrol-muted">
              {connected
                ? 'Waiting for crawl activity... Start a crawl from the Targets page.'
                : 'Connecting to live feed...'}
            </p>
          </div>
        ) : (
          <ul className="space-y-1">
            {activities.map((entry) => {
              const config = ACTIVITY_ICONS[entry.activity_type] || {
                icon: Activity,
                color: 'text-patrol-muted',
              }
              const Icon = config.icon
              const isAbusive = entry.activity_type === 'comment_abusive'
              const isError = entry.activity_type === 'crawl_error'
              const isFinished = entry.activity_type === 'crawl_finished'

              return (
                <li
                  key={entry.id}
                  className={`flex items-start gap-2 rounded px-2 py-1 ${
                    isAbusive
                      ? 'bg-red-500/10 border-l-2 border-red-500'
                      : isError
                        ? 'bg-red-500/5 border-l-2 border-red-500/50'
                        : isFinished
                          ? 'bg-green-500/10 border-l-2 border-green-500'
                          : 'hover:bg-patrol-surface/20'
                  }`}
                >
                  <Icon
                    className={`mt-0.5 h-3 w-3 shrink-0 ${config.color} ${
                      entry.activity_type === 'crawl_started' ||
                      entry.activity_type === 'expanding_comments'
                        ? 'animate-spin'
                        : ''
                    }`}
                  />
                  <div className="min-w-0 flex-1">
                    <span className="text-patrol-text">{entry.message}</span>
                    {entry.detail && (
                      <span className="ml-2 text-patrol-muted truncate">
                        {entry.detail}
                      </span>
                    )}
                  </div>
                  <span className="shrink-0 text-[10px] text-patrol-muted/60">
                    {new Date(entry.timestamp).toLocaleTimeString()}
                  </span>
                </li>
              )
            })}
          </ul>
        )}
      </div>
    </div>
  )
}
