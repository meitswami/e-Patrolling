'use client'

import { useCallback, useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { Activity, AlertTriangle, ArrowUpRight, Shield, Users } from 'lucide-react'
import { StatGridSkeleton } from '@/components/ui/Skeleton'
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
      router.replace('/admin')
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
        { label: 'Active targets', value: stats.active_targets, icon: Users, href: '/targets' },
        { label: 'Evidence (24h)', value: stats.evidence_24h, icon: Shield, href: '/evidence' },
        { label: 'Critical alerts', value: stats.critical_total, icon: AlertTriangle, href: '/evidence?severity=CRITICAL' },
        { label: 'Repeat offenders', value: stats.repeat_offenders, icon: Activity, href: '/offenders' },
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
            <Link
              key={stat.label}
              href={stat.href}
              className="group relative overflow-hidden rounded-xl border border-patrol-border bg-gradient-card p-5 shadow-card transition-all duration-200 hover:border-patrol-accent/30 hover:shadow-card-hover cursor-pointer"
            >
              <div className="absolute inset-0 bg-gradient-subtle opacity-0 transition-opacity group-hover:opacity-100" />
              <div className="relative flex items-start justify-between">
                <div>
                  <p className="text-xs font-medium uppercase tracking-wider text-patrol-muted">{stat.label}</p>
                  <p className="mt-2 font-mono text-3xl font-bold text-patrol-text">{stat.value}</p>
                </div>
                <div className="rounded-lg bg-patrol-accent/10 p-2">
                  <Icon className="h-5 w-5 text-patrol-accent" />
                </div>
              </div>
              <div className="absolute bottom-3 right-3 opacity-0 transition-opacity group-hover:opacity-100">
                <ArrowUpRight className="h-4 w-4 text-patrol-accent" />
              </div>
            </Link>
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
        <div className="mt-4">
          <StatGridSkeleton />
        </div>
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
