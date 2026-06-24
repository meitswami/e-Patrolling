'use client'

import Link from 'next/link'
import { useParams, useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
import { AppShell } from '@/components/layout/AppShell'
import { AbuseCategoryBadges } from '@/components/abuse/AbuseCategoryBadges'
import { AbuseExplanationPanel } from '@/components/abuse/AbuseExplanationPanel'
import { AbusiveCommentText } from '@/components/abuse/AbusiveCommentText'
import { API_BASE_URL, API_PREFIX, SEVERITY_CONFIG } from '@/lib/constants'
import { getCrawlLogResults } from '@/lib/api'
import { isAuthenticated, getToken } from '@/lib/auth'
import { durationFromTimestamps } from '@/lib/duration'
import type { CrawlLogResults, CrawlSessionActivity } from '@/lib/api'

function evidenceImageUrl(screenshotPath: string | null): string | null {
  if (!screenshotPath) return null
  const base = API_BASE_URL.replace(/\/$/, '')
  const clean = screenshotPath.replace(/^\/+/, '').replace(/^storage\//, '')
  return `${base}/storage/${clean}`
}

function downloadSessionPdf(logId: string, filename: string, setError: (m: string | null) => void) {
  const token = getToken()
  if (!token) return
  setError(null)
  fetch(`${API_BASE_URL}${API_PREFIX}/crawlers/logs/${logId}/export.pdf`, {
    headers: { Authorization: `Bearer ${token}` },
  })
    .then(async (res) => {
      if (!res.ok) throw new Error(`PDF export failed (${res.status})`)
      const blob = await res.blob()
      const a = document.createElement('a')
      a.href = URL.createObjectURL(blob)
      a.download = filename
      a.click()
      URL.revokeObjectURL(a.href)
    })
    .catch((err) => setError(err instanceof Error ? err.message : 'PDF export failed'))
}

export default function CrawlLogResultsPage() {
  const params = useParams()
  const router = useRouter()
  const logId = params.id as string
  const [data, setData] = useState<CrawlLogResults | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [downloading, setDownloading] = useState(false)

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace('/admin')
      return
    }
    async function load() {
      try {
        const results = await getCrawlLogResults(logId)
        setData(results)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load crawl results')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [router, logId])

  const scrollToEvidence = () => {
    document.getElementById('evidence-section')?.scrollIntoView({ behavior: 'smooth' })
  }

  const duration =
    data?.duration_formatted ||
    durationFromTimestamps(data?.started_at, data?.completed_at ?? null, data?.duration_seconds)

  const session = data?.session_data
  const activityLog = session?.activity_log ?? []
  const specs = session?.system_specs ?? {}
  const perf = session?.performance
  const spikes = perf?.spikes ?? []

  return (
    <AppShell
      title="Crawl Session Report"
      subtitle={
        data?.target_username
          ? `@${data.target_username} · ${data.platform}`
          : 'Live extraction proof'
      }
    >
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <Link
          href="/monitoring"
          className="text-sm text-patrol-accent hover:underline"
        >
          ← Live Monitoring
        </Link>
        {data?.target_id && (
          <Link
            href={`/monitoring/target/${data.target_id}/history`}
            className="text-sm text-patrol-muted hover:text-patrol-accent"
          >
            Crawl Done History
          </Link>
        )}
        {data && (
          <button
            type="button"
            disabled={downloading}
            onClick={() => {
              setDownloading(true)
              const stamp = data.started_at.slice(0, 10)
              const user = data.target_username || 'target'
              downloadSessionPdf(
                logId,
                `patrol_crawl_${user}_${stamp}.pdf`,
                setError,
              )
              setTimeout(() => setDownloading(false), 1500)
            }}
            className="rounded-lg border border-patrol-accent/40 bg-patrol-accent/10 px-3 py-1.5 text-xs font-medium text-patrol-accent disabled:opacity-50"
          >
            {downloading ? 'Generating PDF…' : 'Download PDF Report'}
          </button>
        )}
      </div>

      {error && (
        <p className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {error}
        </p>
      )}

      {loading && <p className="text-sm text-patrol-muted">Loading results…</p>}

      {data && (
        <>
          <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
            <Stat label="Status" value={data.success ? 'OK' : 'Failed'} />
            <Stat label="Duration" value={duration} />
            <Stat
              label="New comments"
              value={String(data.comments_new)}
              onClick={() => {
                if (data.evidence.length > 0) scrollToEvidence()
                else {
                  const params = new URLSearchParams()
                  if (data.target_username) params.set('target', data.target_username)
                  if (data.target_id) params.set('target_id', data.target_id)
                  router.push(`/evidence?${params.toString()}`)
                }
              }}
              clickable
            />
            <Stat
              label="Abusive captured"
              value={String(data.abusive_detected)}
              onClick={() => {
                if (data.evidence.length > 0) scrollToEvidence()
                else {
                  const params = new URLSearchParams()
                  if (data.target_username) params.set('target', data.target_username)
                  if (data.target_id) params.set('target_id', data.target_id)
                  router.push(`/evidence?${params.toString()}`)
                }
              }}
              clickable
            />
            <Stat label="Run time" value={formatRunTime(data.started_at)} />
          </div>

          {(data.crawl_mode || data.pages_crawled > 0 || data.error_message) && (
            <div className="mb-6 rounded-xl border border-patrol-border bg-patrol-card p-4 text-sm">
              <h2 className="font-mono text-xs text-patrol-accent">Session details</h2>
              <dl className="mt-2 grid gap-1 sm:grid-cols-2">
                {data.crawl_mode && (
                  <>
                    <dt className="text-patrol-muted">Crawl mode</dt>
                    <dd className="text-patrol-text">{data.crawl_mode.replace(/_/g, ' ')}</dd>
                  </>
                )}
                <dt className="text-patrol-muted">Pages crawled</dt>
                <dd className="text-patrol-text">{data.pages_crawled}</dd>
                <dt className="text-patrol-muted">Comments found</dt>
                <dd className="text-patrol-text">{data.comments_found}</dd>
                <dt className="text-patrol-muted">Critical detected</dt>
                <dd className="text-patrol-text">{data.critical_detected}</dd>
                {data.completed_at && (
                  <>
                    <dt className="text-patrol-muted">Completed</dt>
                    <dd className="text-patrol-text">{formatRunTime(data.completed_at)}</dd>
                  </>
                )}
              </dl>
              {data.error_message && (
                <p className="mt-2 text-xs text-red-400">{data.error_message}</p>
              )}
            </div>
          )}

          {Object.keys(specs).length > 0 && (
            <section className="mb-6 rounded-xl border border-patrol-border bg-patrol-card p-4">
              <h2 className="font-mono text-sm text-patrol-accent">System specs (at crawl start)</h2>
              <dl className="mt-3 grid gap-2 text-xs sm:grid-cols-2 lg:grid-cols-3">
                {(
                  [
                    ['Hostname', specs.hostname],
                    ['OS', `${specs.os} ${specs.os_release || ''}`.trim()],
                    ['Architecture', specs.architecture],
                    ['Processor', specs.processor],
                    ['CPU cores', specs.cpu_count],
                    ['Python', specs.python_version],
                    ['RAM total', specs.ram_total_mb ? `${specs.ram_total_mb} MB` : null],
                    ['Disk total', specs.disk_total_gb ? `${specs.disk_total_gb} GB` : null],
                  ] as [string, string | number | null | undefined][]
                ).map(([label, value]) =>
                  value != null && value !== '' ? (
                    <div key={label}>
                      <dt className="text-patrol-muted">{label}</dt>
                      <dd className="font-mono text-patrol-text">{String(value)}</dd>
                    </div>
                  ) : null,
                )}
              </dl>
            </section>
          )}

          {perf && (
            <section className="mb-6 rounded-xl border border-patrol-border bg-patrol-card p-4">
              <h2 className="font-mono text-sm text-patrol-accent">Performance during crawl</h2>
              <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                {(['ram_percent', 'cpu_percent', 'swap_percent', 'disk_percent'] as const).map((key) => (
                  <div key={key} className="rounded-lg border border-patrol-border/60 p-3">
                    <p className="text-[10px] uppercase text-patrol-muted">
                      {key.replace('_percent', '')}
                    </p>
                    <p className="mt-1 font-mono text-sm text-patrol-text">
                      Peak {perf.peak?.[key] ?? 0}% · Avg {perf.average?.[key] ?? 0}%
                    </p>
                  </div>
                ))}
              </div>
              <p className="mt-3 text-xs text-patrol-muted">
                {perf.sample_count ?? 0} samples every {perf.sample_interval_sec ?? 3}s ·{' '}
                {spikes.length} spike(s) ≥ {perf.spike_threshold_percent ?? 95}%
              </p>
              {spikes.length > 0 && (
                <ul className="mt-2 max-h-32 space-y-1 overflow-y-auto text-xs text-amber-400">
                  {spikes.map((spike, i) => (
                    <li key={i}>
                      {spike.metric} {spike.value}% @{' '}
                      {spike.timestamp ? new Date(spike.timestamp).toLocaleTimeString() : '—'}
                    </li>
                  ))}
                </ul>
              )}
            </section>
          )}

          {activityLog.length > 0 && (
            <section className="mb-6 rounded-xl border border-patrol-border bg-[#0a1628] p-4">
              <h2 className="font-mono text-sm text-patrol-accent">
                Saved live activity ({activityLog.length})
              </h2>
              <p className="mt-1 text-xs text-patrol-muted">
                Events captured during this crawl session from Live Monitoring.
              </p>
              <div className="mt-3 max-h-72 space-y-1 overflow-y-auto font-mono text-xs">
                {activityLog.map((entry, i) => (
                  <ActivityLine key={i} entry={entry} />
                ))}
              </div>
            </section>
          )}

          {data.evidence.length === 0 ? (
            <p className="rounded-xl border border-dashed border-patrol-border p-8 text-center text-sm text-patrol-muted">
              No abusive evidence captured in this run. Check Evidence Feed for older items.
            </p>
          ) : (
            <div id="evidence-section" className="space-y-4">
              <h2 className="font-mono text-sm text-patrol-accent">
                Abusive results & proof ({data.evidence.length})
              </h2>
              <p className="text-xs text-patrol-muted">
                Click any card to view full evidence details, or click an inner link for a specific page.
              </p>
              {data.evidence.map((ev) => {
                const sev = SEVERITY_CONFIG[ev.severity as keyof typeof SEVERITY_CONFIG]
                const img = evidenceImageUrl(ev.screenshot_path)
                return (
                  <article
                    key={ev.evidence_id}
                    onClick={() => router.push(`/evidence/${ev.uuid}`)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault()
                        router.push(`/evidence/${ev.uuid}`)
                      }
                    }}
                    role="button"
                    tabIndex={0}
                    aria-label={`View full evidence ${ev.evidence_id}`}
                    className="cursor-pointer rounded-xl border border-patrol-border bg-patrol-card p-4 transition hover:border-patrol-accent/50 hover:bg-patrol-card/80 focus:outline-none focus:ring-2 focus:ring-patrol-accent/40"
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <AbuseCategoryBadges categories={ev.abuse_categories ?? []} />
                      {sev && (
                        <span
                          className={`rounded border px-2 py-0.5 text-xs font-medium ${sev.className}`}
                        >
                          {sev.label}
                        </span>
                      )}
                      <span className="font-mono text-sm text-patrol-accent">
                        {ev.evidence_id}
                      </span>
                      <span className="text-xs text-patrol-muted">
                        Risk {ev.risk_score}
                      </span>
                      <span className="ml-auto text-xs text-patrol-accent/80">
                        View details →
                      </span>
                    </div>
                    {ev.accused_username && (
                      <p className="mt-2 text-sm">
                        Offender:{' '}
                        <Link
                          href={`/offenders/dossier/${encodeURIComponent(ev.accused_username)}`}
                          onClick={(e) => e.stopPropagation()}
                          className="font-mono text-patrol-accent hover:underline"
                        >
                          @{ev.accused_username}
                        </Link>
                      </p>
                    )}
                    <AbusiveCommentText
                      className="mt-2"
                      text={ev.comment_preview}
                      abusive={ev.is_abusive ?? true}
                      lexiconMatch={ev.is_lexicon_match}
                    />
                    <AbuseExplanationPanel explanations={ev.abuse_explanations ?? []} />
                    {img && (
                      <a
                        href={img}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        className="mt-3 block"
                      >
                        <img
                          src={img}
                          alt="Evidence screenshot"
                          className="max-h-48 rounded-lg border border-patrol-border object-contain"
                        />
                      </a>
                    )}
                    <div className="mt-3 flex flex-wrap gap-3">
                      <Link
                        href={`/evidence/${ev.uuid}`}
                        onClick={(e) => e.stopPropagation()}
                        className="text-xs text-patrol-accent hover:underline"
                      >
                        View full evidence ({ev.evidence_id}) →
                      </Link>
                      {ev.accused_username && (
                        <Link
                          href={`/offenders/dossier/${encodeURIComponent(ev.accused_username)}`}
                          onClick={(e) => e.stopPropagation()}
                          className="text-xs text-patrol-muted hover:text-patrol-accent"
                        >
                          Offender dossier →
                        </Link>
                      )}
                    </div>
                  </article>
                )
              })}
            </div>
          )}
        </>
      )}
    </AppShell>
  )
}

function ActivityLine({ entry }: { entry: CrawlSessionActivity }) {
  const ts = entry.timestamp
    ? new Date(entry.timestamp).toLocaleTimeString(undefined, {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      })
    : ''
  return (
    <div className="flex gap-2 text-patrol-muted">
      <span className="shrink-0 text-patrol-accent/60">{ts}</span>
      <span className="text-patrol-text">{entry.message}</span>
      {entry.detail && (
        <span className="truncate text-patrol-muted/80">· {entry.detail}</span>
      )}
    </div>
  )
}

function formatRunTime(isoString: string): string {
  const d = new Date(isoString)
  if (Number.isNaN(d.getTime())) return isoString
  const day = String(d.getDate()).padStart(2, '0')
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const year = d.getFullYear()
  let hours = d.getHours()
  const minutes = String(d.getMinutes()).padStart(2, '0')
  const seconds = String(d.getSeconds()).padStart(2, '0')
  const ampm = hours >= 12 ? 'PM' : 'AM'
  hours = hours % 12 || 12
  const hh = String(hours).padStart(2, '0')
  return `${day}/${month}/${year} ${hh}:${minutes}:${seconds} ${ampm}`
}

function Stat({
  label,
  value,
  onClick,
  clickable,
}: {
  label: string
  value: string
  onClick?: () => void
  clickable?: boolean
}) {
  const baseClass =
    'rounded-xl border border-patrol-border bg-patrol-card p-4 transition'
  const interactiveClass = clickable
    ? 'cursor-pointer hover:border-patrol-accent/50 hover:bg-patrol-card/80 focus:outline-none focus:ring-2 focus:ring-patrol-accent/40'
    : ''

  if (clickable && onClick) {
    return (
      <button
        type="button"
        onClick={onClick}
        className={`${baseClass} ${interactiveClass} text-left`}
      >
        <p className="text-xs text-patrol-muted">{label}</p>
        <p className="mt-1 text-sm text-patrol-text">{value}</p>
      </button>
    )
  }

  return (
    <div className={baseClass}>
      <p className="text-xs text-patrol-muted">{label}</p>
      <p className="mt-1 text-sm text-patrol-text">{value}</p>
    </div>
  )
}
