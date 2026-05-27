'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import {
  Activity,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Cpu,
  HardDrive,
  MemoryStick,
  Trash2,
  Wifi,
} from 'lucide-react'

interface SystemMetrics {
  ram: { total_mb: number; used_mb: number; available_mb: number; percent: number }
  swap: { total_mb: number; used_mb: number; free_mb: number; percent: number }
  cpu: { percent: number }
  disk: { total_gb: number; used_gb: number; free_gb: number; percent: number }
  bandwidth: { rx_kbps: number; tx_kbps: number }
  timestamp: number
}

interface SpikeEntry {
  id: string
  metric: string
  value: number
  timestamp: number
  threshold: number
}

const SPIKE_THRESHOLD = 95 // % — log when usage hits this or higher
const MAX_SPIKE_ENTRIES = 30
const SPIKE_STORAGE_KEY = 'perf-monitor-spikes'

function ProgressBar({ percent, color }: { percent: number; color: string }) {
  const clamp = Math.min(100, Math.max(0, percent))
  return (
    <div className="h-1.5 w-full rounded-full bg-patrol-bg/60 overflow-hidden">
      <div
        className={`h-full rounded-full transition-all duration-700 ease-out ${color}`}
        style={{ width: `${clamp}%` }}
      />
    </div>
  )
}

function getBarColor(percent: number): string {
  if (percent >= 90) return 'bg-red-500'
  if (percent >= 70) return 'bg-amber-500'
  return 'bg-patrol-accent'
}

function MetricCard({
  icon: Icon,
  label,
  value,
  subValue,
  percent,
}: {
  icon: typeof Cpu
  label: string
  value: string
  subValue?: string
  percent: number
}) {
  return (
    <div className="flex flex-col gap-1.5 min-w-[140px]">
      <div className="flex items-center gap-1.5">
        <Icon className="h-3.5 w-3.5 text-patrol-accent/70" />
        <span className="text-[11px] font-medium text-patrol-muted uppercase tracking-wide">{label}</span>
      </div>
      <div className="flex items-baseline gap-1.5">
        <span className="font-mono text-sm font-bold text-patrol-text">{value}</span>
        {subValue && <span className="text-[10px] text-patrol-muted">{subValue}</span>}
      </div>
      <ProgressBar percent={percent} color={getBarColor(percent)} />
    </div>
  )
}

function loadSpikes(): SpikeEntry[] {
  if (typeof window === 'undefined') return []
  try {
    const raw = localStorage.getItem(SPIKE_STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed)) return []
    return parsed.slice(0, MAX_SPIKE_ENTRIES)
  } catch {
    return []
  }
}

function saveSpikes(spikes: SpikeEntry[]) {
  if (typeof window === 'undefined') return
  try {
    localStorage.setItem(SPIKE_STORAGE_KEY, JSON.stringify(spikes.slice(0, MAX_SPIKE_ENTRIES)))
  } catch {
    /* ignore storage errors */
  }
}

export function PerformanceMonitor() {
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null)
  const [collapsed, setCollapsed] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('perf-monitor-collapsed') === 'true'
    }
    return false
  })
  const [error, setError] = useState<string | null>(null)
  const [spikes, setSpikes] = useState<SpikeEntry[]>(() => loadSpikes())
  const [logsExpanded, setLogsExpanded] = useState(false)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const lastSpikeAtRef = useRef<Record<string, number>>({})

  const recordSpike = useCallback((metric: string, value: number) => {
    const now = Date.now()
    // Debounce: don't log the same metric more often than once every 30s
    const lastLogged = lastSpikeAtRef.current[metric] || 0
    if (now - lastLogged < 30_000) return
    lastSpikeAtRef.current[metric] = now

    const entry: SpikeEntry = {
      id: `${metric}-${now}`,
      metric,
      value: Math.round(value * 10) / 10,
      timestamp: now,
      threshold: SPIKE_THRESHOLD,
    }
    setSpikes((prev) => {
      const next = [entry, ...prev].slice(0, MAX_SPIKE_ENTRIES)
      saveSpikes(next)
      return next
    })
  }, [])

  const fetchMetrics = useCallback(async () => {
    try {
      const { getToken } = await import('@/lib/auth')
      const { API_BASE_URL } = await import('@/lib/constants')
      const token = getToken()
      if (!token) return

      const res = await fetch(`${API_BASE_URL}/api/v1/metrics/system-stats`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) {
        if (res.status === 401) return
        throw new Error(`HTTP ${res.status}`)
      }
      const data: SystemMetrics = await res.json()
      setMetrics(data)
      setError(null)

      // Check each metric for spike threshold
      if (data.ram.percent >= SPIKE_THRESHOLD) recordSpike('RAM', data.ram.percent)
      if (data.swap.percent >= SPIKE_THRESHOLD) recordSpike('Swap', data.swap.percent)
      if (data.cpu.percent >= SPIKE_THRESHOLD) recordSpike('CPU', data.cpu.percent)
      if (data.disk.percent >= SPIKE_THRESHOLD) recordSpike('Disk', data.disk.percent)
    } catch {
      setError('Metrics unavailable')
    }
  }, [recordSpike])

  useEffect(() => {
    fetchMetrics()
    intervalRef.current = setInterval(fetchMetrics, 3000) // Poll every 3s
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [fetchMetrics])

  useEffect(() => {
    localStorage.setItem('perf-monitor-collapsed', String(collapsed))
  }, [collapsed])

  const clearSpikes = () => {
    setSpikes([])
    saveSpikes([])
  }

  if (!metrics && !error) return null

  return (
    <div className="mb-4 rounded-lg border border-patrol-border bg-patrol-card/80 backdrop-blur-sm overflow-hidden transition-all duration-300">
      {/* Header — always visible */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="flex w-full items-center justify-between px-4 py-2.5 hover:bg-patrol-surface/30 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Activity className="h-3.5 w-3.5 text-patrol-accent animate-pulse" />
          <span className="text-xs font-semibold text-patrol-accent uppercase tracking-wider">
            Live System Performance
          </span>
          {metrics && !collapsed && (
            <span className="text-[10px] text-patrol-muted ml-2">
              Updated {new Date(metrics.timestamp * 1000).toLocaleTimeString()}
            </span>
          )}
          {spikes.length > 0 && (
            <span className="ml-2 inline-flex items-center gap-1 rounded-full border border-amber-500/40 bg-amber-500/10 px-2 py-0.5 text-[10px] font-medium text-amber-400">
              <AlertTriangle className="h-3 w-3" />
              {spikes.length} spike{spikes.length !== 1 ? 's' : ''}
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          {collapsed && metrics && (
            <div className="flex items-center gap-3 text-[11px] text-patrol-muted">
              <span>RAM <span className="font-mono text-patrol-text">{metrics.ram.percent}%</span></span>
              <span>CPU <span className="font-mono text-patrol-text">{metrics.cpu.percent}%</span></span>
              <span>Disk <span className="font-mono text-patrol-text">{metrics.disk.percent}%</span></span>
            </div>
          )}
          {collapsed ? (
            <ChevronDown className="h-4 w-4 text-patrol-muted" />
          ) : (
            <ChevronUp className="h-4 w-4 text-patrol-muted" />
          )}
        </div>
      </button>

      {/* Expanded content */}
      {!collapsed && (
        <div className="border-t border-patrol-border/50 px-4 py-3">
          {error ? (
            <p className="text-xs text-red-400">{error}</p>
          ) : metrics ? (
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
              <MetricCard
                icon={MemoryStick}
                label="RAM"
                value={`${metrics.ram.percent}%`}
                subValue={`${Math.round(metrics.ram.used_mb)}/${Math.round(metrics.ram.total_mb)} MB`}
                percent={metrics.ram.percent}
              />
              <MetricCard
                icon={MemoryStick}
                label="Swap"
                value={`${metrics.swap.percent}%`}
                subValue={`${Math.round(metrics.swap.used_mb)}/${Math.round(metrics.swap.total_mb)} MB`}
                percent={metrics.swap.percent}
              />
              <MetricCard
                icon={Cpu}
                label="CPU"
                value={`${metrics.cpu.percent}%`}
                subValue="utilization"
                percent={metrics.cpu.percent}
              />
              <MetricCard
                icon={HardDrive}
                label="Disk"
                value={`${metrics.disk.percent}%`}
                subValue={`${metrics.disk.used_gb}/${metrics.disk.total_gb} GB`}
                percent={metrics.disk.percent}
              />
              <MetricCard
                icon={Wifi}
                label="Network"
                value={`${metrics.bandwidth.rx_kbps} KB/s`}
                subValue={`Up: ${metrics.bandwidth.tx_kbps} KB/s`}
                percent={Math.min(100, (metrics.bandwidth.rx_kbps + metrics.bandwidth.tx_kbps) / 10)}
              />
            </div>
          ) : (
            <p className="text-xs text-patrol-muted">Loading metrics...</p>
          )}

          {/* Spike Logs Section */}
          <div className="mt-3 border-t border-patrol-border/50 pt-3">
            <div className="flex items-center justify-between">
              <button
                onClick={() => setLogsExpanded(!logsExpanded)}
                className="flex items-center gap-1.5 text-[11px] font-medium text-patrol-muted hover:text-patrol-text uppercase tracking-wider"
              >
                <AlertTriangle className="h-3 w-3" />
                Spike Log (≥{SPIKE_THRESHOLD}%)
                <span className="text-patrol-muted/60">({spikes.length})</span>
                {logsExpanded ? (
                  <ChevronUp className="h-3 w-3" />
                ) : (
                  <ChevronDown className="h-3 w-3" />
                )}
              </button>
              {spikes.length > 0 && logsExpanded && (
                <button
                  onClick={clearSpikes}
                  className="flex items-center gap-1 text-[10px] text-patrol-muted hover:text-red-400 transition-colors"
                  title="Clear all spike logs"
                >
                  <Trash2 className="h-3 w-3" />
                  Clear
                </button>
              )}
            </div>

            {logsExpanded && (
              <div className="mt-2 max-h-48 overflow-y-auto rounded-md bg-patrol-bg/40 border border-patrol-border/30">
                {spikes.length === 0 ? (
                  <p className="px-3 py-3 text-[11px] text-patrol-muted">
                    No spikes recorded yet. Will appear here when any metric hits {SPIKE_THRESHOLD}% or higher.
                  </p>
                ) : (
                  <ul className="divide-y divide-patrol-border/30">
                    {spikes.map((spike) => (
                      <li
                        key={spike.id}
                        className="flex items-center justify-between px-3 py-1.5 text-[11px] hover:bg-patrol-surface/20"
                      >
                        <div className="flex items-center gap-2">
                          <span
                            className={`inline-block w-2 h-2 rounded-full ${
                              spike.value >= 99 ? 'bg-red-500' : 'bg-amber-500'
                            }`}
                          />
                          <span className="font-mono text-patrol-text font-semibold">
                            {spike.metric}
                          </span>
                          <span className="font-mono text-amber-400">
                            {spike.value}%
                          </span>
                        </div>
                        <span className="font-mono text-patrol-muted">
                          {new Date(spike.timestamp).toLocaleString()}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
