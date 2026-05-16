'use client'

import type { PlatformPatrolInfo } from '@/lib/api'
import { PLATFORM_CONFIG } from '@/lib/constants'

interface PlatformMonitorGridProps {
  platforms: PlatformPatrolInfo[]
  demoMode?: boolean
  compact?: boolean
}

export function PlatformMonitorGrid({
  platforms,
  demoMode,
  compact = false,
}: PlatformMonitorGridProps) {
  const active = platforms.filter((p) => p.status === 'active')
  const roadmap = platforms.filter((p) => p.status === 'roadmap')

  return (
    <div className="space-y-4">
      <div className={compact ? 'space-y-2' : 'space-y-3'}>
        <h2 className="font-mono text-sm text-patrol-accent">Patrol & monitoring</h2>
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {active.map((p) => (
            <PlatformCard key={p.id} platform={p} demoMode={demoMode} />
          ))}
        </div>
      </div>

      {roadmap.length > 0 && (
        <div>
          <h3 className="mb-2 text-xs font-medium uppercase tracking-wide text-patrol-muted">
            Planned platforms
          </h3>
          <div className="flex flex-wrap gap-2">
            {roadmap.map((p) => (
              <span
                key={p.id}
                className="rounded-lg border border-dashed border-patrol-border bg-patrol-surface/50 px-3 py-1.5 text-xs text-patrol-muted"
              >
                {p.label} · coming soon
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function PlatformCard({
  platform,
  demoMode,
}: {
  platform: PlatformPatrolInfo
  demoMode?: boolean
}) {
  const cfg = PLATFORM_CONFIG[platform.id as keyof typeof PLATFORM_CONFIG]
  const icon = cfg?.icon ?? '◎'
  const monitoring = platform.monitoring_count > 0

  return (
    <article className="rounded-xl border border-patrol-border bg-patrol-card p-4 transition hover:border-patrol-accent/30">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="text-lg" aria-hidden>
            {icon}
          </span>
          <div>
            <p className="font-medium text-patrol-text">{platform.label}</p>
            <p className="text-xs text-patrol-muted">Patrol enabled</p>
          </div>
        </div>
        <span className="rounded-full border border-patrol-accent/40 bg-patrol-accent/10 px-2 py-0.5 text-[10px] font-medium uppercase text-patrol-accent">
          Active
        </span>
      </div>

      <dl className="mt-3 grid grid-cols-2 gap-2 text-xs">
        <div>
          <dt className="text-patrol-muted">Targets</dt>
          <dd className="font-mono text-patrol-text">{platform.target_count}</dd>
        </div>
        <div>
          <dt className="text-patrol-muted">Monitoring</dt>
          <dd className="font-mono text-patrol-text">{platform.monitoring_count}</dd>
        </div>
      </dl>

      <div className="mt-3 flex items-center gap-2 text-[11px]">
        <span
          className={`h-1.5 w-1.5 rounded-full ${
            monitoring ? 'bg-patrol-accent animate-pulse-dot' : 'bg-patrol-muted'
          }`}
        />
        <span className={monitoring ? 'text-patrol-accent' : 'text-patrol-muted'}>
          {monitoring ? 'Live monitoring' : 'No active watches'}
        </span>
        {demoMode && (
          <>
            <span className="text-patrol-muted">·</span>
            <span className="text-patrol-muted">Demo crawl</span>
          </>
        )}
      </div>
    </article>
  )
}
