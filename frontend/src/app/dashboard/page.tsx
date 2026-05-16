'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Activity, AlertTriangle, Shield, Users } from 'lucide-react'
import { AppShell } from '@/components/layout/AppShell'
import { getDashboardStats, getHealth, getMe } from '@/lib/api'
import { isAuthenticated } from '@/lib/auth'
import type { DashboardStats, HealthResponse, User } from '@/types'

export default function DashboardPage() {
  const router = useRouter()
  const [user, setUser] = useState<User | null>(null)
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace('/login')
      return
    }

    async function load() {
      try {
        const [me, apiHealth, dashboard] = await Promise.all([
          getMe(),
          getHealth(),
          getDashboardStats(),
        ])
        setUser(me)
        setHealth(apiHealth)
        setStats(dashboard)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load dashboard')
      }
    }

    load()
  }, [router])

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
      subtitle={user ? `Welcome back, ${user.name}` : 'Loading session…'}
    >
      {error && (
        <p className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {error}
        </p>
      )}

      {health && (
        <div className="mb-6 flex items-center gap-3 rounded-lg border border-patrol-border bg-patrol-card px-4 py-3">
          <span
            className={`h-2.5 w-2.5 rounded-full ${
              health.status === 'healthy' ? 'bg-patrol-accent animate-pulse-dot' : 'bg-red-500'
            }`}
          />
          <div className="text-sm">
            <span className="text-patrol-text">API {health.status}</span>
            <span className="mx-2 text-patrol-muted">·</span>
            <span className="text-patrol-muted">
              {health.service} v{health.version} · Redis: {health.redis}
              {stats?.live_monitoring && (
                <>
                  <span className="mx-2">·</span>
                  <span className="text-patrol-accent">Monitoring active</span>
                </>
              )}
            </span>
          </div>
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

      {!stats && !error && (
        <p className="text-sm text-patrol-muted">Loading statistics from Supabase…</p>
      )}

      {stats && stats.total_evidence === 0 && (
        <div className="mt-6 rounded-xl border border-dashed border-patrol-border bg-patrol-surface/50 p-8 text-center">
          <h2 className="font-mono text-lg text-patrol-accent">No evidence yet</h2>
          <p className="mx-auto mt-2 max-w-lg text-sm text-patrol-muted">
            Add target accounts under Settings, then run crawlers and the AI pipeline to populate
            evidence. Dashboard stats are live from your database.
          </p>
        </div>
      )}
    </AppShell>
  )
}
