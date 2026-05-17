import type { HealthResponse } from '@/types'

type SystemStatusBarProps = {
  health: HealthResponse
  wsConnected?: boolean
  liveMonitoring?: boolean
}

export function SystemStatusBar({
  health,
  wsConnected = false,
  liveMonitoring = false,
}: SystemStatusBarProps) {
  return (
    <div className="mb-6 flex items-center gap-3 rounded-lg border border-patrol-border bg-patrol-card px-4 py-3">
      <span
        className={`h-2.5 w-2.5 shrink-0 rounded-full ${
          health.status === 'healthy' ? 'bg-patrol-accent animate-pulse-dot' : 'bg-red-500'
        }`}
      />
      <div className="min-w-0 text-sm">
        <span className="text-patrol-text">API {health.status}</span>
        <span className="mx-2 text-patrol-muted">·</span>
        <span className="text-patrol-muted">
          {health.service} v{health.version} · Redis: {health.redis}
          {wsConnected && (
            <>
              <span className="mx-2">·</span>
              <span className="text-patrol-accent">Live feed connected</span>
            </>
          )}
          {liveMonitoring && (
            <>
              <span className="mx-2">·</span>
              <span className="text-patrol-accent">Monitoring active</span>
            </>
          )}
        </span>
      </div>
    </div>
  )
}
