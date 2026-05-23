'use client'

import { useCallback, useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Activity, AlertTriangle, Shield, Users } from 'lucide-react'
import { ClientOnly } from '@/components/ClientOnly'
import { AppShell } from '@/components/layout/AppShell'
import { PlatformMonitorGrid } from '@/components/platforms/PlatformMonitorGrid'
import { getCrawlerStatus, getDashboardStats, getMe } from '@/lib/api'
import type { CrawlerStatus } from '@/lib/api'
import { isAuthenticated } from '@/lib/auth'
import { connectDashboardWs, type WsMessage } from '@/lib/ws'
import type { DashboardStats, User } from '@/types'

export default function DashboardPage() {
  const router = useRouter()
  const [user, setUser] = useState<User | null>(null)
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [liveFeed, setLiveFeed] = useState<string[]>([])
  const [crawlerStatus, setCrawlerStatus] = useState<CrawlerStatus | null>(null)

  const refreshStats = useCallback(async () => {
    try {
      const dashboard = await getDashboardStats()
      setStats(dashboard)
    } catch {
      /* ignore background refresh errors */
    }
  }, [])

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace('/login')
      return
    }

    async function load() {
      try {
        const [me, dashboard, crawlers] = await Promise.all([
          getMe(),
          getDashboardStats(),
          getCrawlerStatus(),
        ])
        setUser(me)
        setStats(dashboard)
        setCrawlerStatus(crawlers)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load dashboard')
      }
    }

    load()

    const disconnect = connectDashboardWs((msg: WsMessage) => {
      if (msg.type === 'connected') {
        return
      }
      if (msg.type === 'evidence_created') {
        setLiveFeed((prev) => [
          `New ${msg.data.severity_level} evidence: ${msg.data.evidence_id}`,
          ...prev.slice(0, 9),
        ])
        refreshStats()
      }
      if (msg.type === 'crawl_completed') {
        setLiveFeed((prev) => [
          `Crawl @${msg.data.target_username}: +${msg.data.comments_new} comments`,
          ...prev.slice(0, 9),
        ])
        refreshStats()
      }
    })

    return disconnect
  }, [router, refreshStats])

  const statCards = stats
    ? [
        { label: 'Active targets', value: stats.active_targets, icon: Users },
        { label: 'Evidence (24h)', value: stats.evidence_24h, icon: Shield },
        { label: 'Critical alerts', value: stats.critical_total, icon: AlertTriangle },
        { label: 'Repeat offenders', value: stats.repeat_offenders, icon: Activity },
      ]
    : []

  return (
    <AppShell
      title="Command Center"
      subtitle={
        user ? `Welcome back, ${user.name}` : 'Loading session…'
      }
    >
      {error && (
        <p className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {error}
        </p>
      )}

      <ClientOnly
        fallback={
          <p className="text-sm text-patrol-muted">Connecting to PATROL API…</p>
        }
      >
      {crawlerStatus?.platforms && crawlerStatus.platforms.length > 0 && (
        <div className="mb-6">
          <PlatformMonitorGrid platforms={crawlerStatus.platforms} />
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {statCards.map((stat) => {
          const Icon = stat.icon
          return (
            <div
              key={stat.label}
              className="rounded-xl border border-patrol-border bg-patrol-card p-5 transition hover:border-patrol-accent/30"
            >
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-sm text-patrol-muted">{stat.label}</p>
                  <p className="mt-2 font-mono text-3xl font-bold text-patrol-text">{stat.value}</p>
                </div>
                <Icon className="h-5 w-5 text-patrol-accent/70" />
              </div>
            </div>
          )
        })}
      </div>

      {liveFeed.length > 0 && (
        <div className="mt-6 rounded-xl border border-patrol-border bg-patrol-card p-4">
          <h2 className="font-mono text-sm text-patrol-accent">Live feed</h2>
          <ul className="mt-2 space-y-1">
            {liveFeed.map((line, i) => (
              <li key={`${line}-${i}`} className="text-xs text-patrol-muted">
                {line}
              </li>
            ))}
          </ul>
        </div>
      )}

      {!stats && !error && (
        <p className="mt-4 text-sm text-patrol-muted">Loading statistics from Supabase…</p>
      )}

      {stats && stats.total_evidence === 0 && (
        <div className="mt-6 rounded-xl border border-dashed border-patrol-border bg-patrol-surface/50 p-8 text-center">
          <h2 className="font-mono text-lg text-patrol-accent">No evidence yet</h2>
          <p className="mx-auto mt-2 max-w-lg text-sm text-patrol-muted">
            Run a crawl from Live Monitoring to populate evidence. Stats update in real time when
            WebSocket is connected.
          </p>
        </div>
      )}
      </ClientOnly>
    </AppShell>
  )
}
