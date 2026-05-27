'use client'

import Link from 'next/link'
import { useParams, useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
import { AppShell } from '@/components/layout/AppShell'
import { PlatformLabel } from '@/components/platforms/PlatformLabel'
import { AbuseCategoryBadges } from '@/components/abuse/AbuseCategoryBadges'
import { AbuseExplanationPanel } from '@/components/abuse/AbuseExplanationPanel'
import { AbusiveCommentText } from '@/components/abuse/AbusiveCommentText'
import { API_BASE_URL, SEVERITY_CONFIG } from '@/lib/constants'
import { getCrawlLogResults } from '@/lib/api'
import { isAuthenticated } from '@/lib/auth'
import type { CrawlLogResults } from '@/lib/api'

function evidenceImageUrl(screenshotPath: string | null): string | null {
  if (!screenshotPath) return null
  const base = API_BASE_URL.replace(/\/$/, '')
  const clean = screenshotPath.replace(/^\/+/, '').replace(/^storage\//, '')
  return `${base}/storage/${clean}`
}

export default function CrawlLogResultsPage() {
  const params = useParams()
  const router = useRouter()
  const logId = params.id as string
  const [data, setData] = useState<CrawlLogResults | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

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

  return (
    <AppShell
      title="Crawl results"
      subtitle={
        data?.target_username
          ? `@${data.target_username} · ${data.platform}`
          : 'Live extraction proof'
      }
    >
      <Link
        href="/monitoring"
        className="mb-4 inline-block text-sm text-patrol-accent hover:underline"
      >
        ← Back to Live Monitoring
      </Link>

      {error && (
        <p className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {error}
        </p>
      )}

      {loading && <p className="text-sm text-patrol-muted">Loading results…</p>}

      {data && (
        <>
          <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Stat label="Status" value={data.success ? 'OK' : 'Failed'} />
            <Stat
              label="New comments"
              value={String(data.comments_new)}
              onClick={data.evidence.length > 0 ? scrollToEvidence : undefined}
              clickable={data.evidence.length > 0}
            />
            <Stat
              label="Abusive captured"
              value={String(data.abusive_detected)}
              onClick={data.evidence.length > 0 ? scrollToEvidence : undefined}
              clickable={data.evidence.length > 0}
            />
            <Stat
              label="Run time"
              value={new Date(data.started_at).toLocaleString()}
            />
          </div>

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
