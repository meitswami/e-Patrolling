'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { AbuseCategoryBadges } from '@/components/abuse/AbuseCategoryBadges'
import { AbuseExplanationPanel } from '@/components/abuse/AbuseExplanationPanel'
import { AbusiveCommentText } from '@/components/abuse/AbusiveCommentText'
import { AppShell } from '@/components/layout/AppShell'
import {
  accusedDossierPdfUrl,
  getAccusedDossier,
  refreshAccusedOsint,
  type AccusedDossier,
} from '@/lib/api'
import { getToken, isAuthenticated } from '@/lib/auth'
import { API_BASE_URL } from '@/lib/constants'
import { useDossierUsernameParam } from '@/lib/route-params'

function severityClass(sev: string): string {
  switch (sev) {
    case 'CRITICAL':
      return 'text-red-400 border-red-500/40 bg-red-500/10'
    case 'HIGH':
      return 'text-orange-400 border-orange-500/40 bg-orange-500/10'
    case 'MEDIUM':
      return 'text-amber-400 border-amber-500/40 bg-amber-500/10'
    default:
      return 'text-patrol-muted border-patrol-border bg-patrol-surface'
  }
}

export default function AccusedDossierPage() {
  const router = useRouter()
  const username = useDossierUsernameParam()
  const [dossier, setDossier] = useState<AccusedDossier | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [downloading, setDownloading] = useState(false)
  const [osintLoading, setOsintLoading] = useState(false)

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace('/admin')
      return
    }
    if (!username || username === '_') return
    getAccusedDossier(username)
      .then(setDossier)
      .catch((err) =>
        setError(err instanceof Error ? err.message : 'Failed to load dossier'),
      )
      .finally(() => setLoading(false))
  }, [router, username])

  async function handleRunOsint() {
    setOsintLoading(true)
    setError(null)
    try {
      await refreshAccusedOsint(username)
      const updated = await getAccusedDossier(username)
      setDossier(updated)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'OSINT lookup failed')
    } finally {
      setOsintLoading(false)
    }
  }

  async function handleDownloadPdf() {
    setDownloading(true)
    try {
      const token = getToken()
      const res = await fetch(accusedDossierPdfUrl(username), {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      })
      if (!res.ok) throw new Error(`PDF export failed (${res.status})`)
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `patrol_dossier_${username}.pdf`
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'PDF download failed')
    } finally {
      setDownloading(false)
    }
  }

  function screenshotUrl(path: string | null): string | null {
    if (!path) return null
    const base = API_BASE_URL.replace(/\/$/, '')
    const clean = path.replace(/^\/+/, '').replace(/^storage\//, '')
    return `${base}/storage/${clean}`
  }

  return (
    <AppShell
      title={`Accused dossier — @${username}`}
      subtitle="Cross-platform harassment report with evidence"
    >
      <div className="mb-6 flex flex-wrap gap-3 print:hidden">
        <Link
          href="/offenders"
          className="rounded-lg border border-patrol-border px-4 py-2 text-sm text-patrol-muted hover:text-white"
        >
          ← Offenders
        </Link>
        <button
          type="button"
          onClick={() => window.print()}
          className="rounded-lg bg-patrol-accent px-4 py-2 text-sm font-medium text-black"
        >
          Print report
        </button>
        <button
          type="button"
          onClick={handleRunOsint}
          disabled={osintLoading}
          className="rounded-lg border border-patrol-border px-4 py-2 text-sm text-patrol-muted hover:text-white disabled:opacity-50"
        >
          {osintLoading ? 'Running OSINT…' : 'Run OSINT lookup'}
        </button>
        <button
          type="button"
          onClick={handleDownloadPdf}
          disabled={downloading || !dossier}
          className="rounded-lg border border-patrol-accent/50 px-4 py-2 text-sm text-patrol-accent disabled:opacity-50"
        >
          {downloading ? 'Generating PDF…' : 'Download PDF'}
        </button>
      </div>

      {error && (
        <p className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {error}
        </p>
      )}
      {loading && <p className="text-sm text-patrol-muted">Loading dossier…</p>}

      {dossier && (
        <article className="dossier-report space-y-8 rounded-xl border border-patrol-border bg-patrol-card p-6 print:border-0 print:bg-white print:text-black">
          <header className="border-b border-patrol-border pb-6 print:border-gray-300">
            <p className="text-xs uppercase tracking-widest text-patrol-muted print:text-gray-600">
              PATROL — Accused person dossier
            </p>
            <h1 className="mt-2 text-2xl font-semibold">@{dossier.username}</h1>
            <p className="mt-1 text-sm text-patrol-muted print:text-gray-600">
              Generated {new Date(dossier.generated_at).toLocaleString()} ·{' '}
              {dossier.platform_count} platform{dossier.platform_count !== 1 ? 's' : ''}:{' '}
              {dossier.platforms.join(', ')}
            </p>
            <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <Stat label="Total evidence" value={String(dossier.summary.total_evidence)} />
              <Stat
                label="Composite risk"
                value={String(dossier.summary.composite_risk_score)}
              />
              <Stat
                label="Targets affected"
                value={String(dossier.summary.targets_affected_count)}
              />
              <Stat
                label="Escalated"
                value={String(dossier.summary.escalated_count)}
              />
            </div>
          </header>

          <section>
            <h2 className="text-lg font-medium">Platform profiles</h2>
            <ul className="mt-3 space-y-2">
              {dossier.profiles.map((p) => (
                <li
                  key={p.id}
                  className="rounded-lg border border-patrol-border bg-patrol-surface px-4 py-3 text-sm print:border-gray-200"
                >
                  <span className="font-mono text-patrol-accent print:text-blue-800">
                    [{p.platform}] @{p.username}
                  </span>
                  <span className="ml-3 text-patrol-muted print:text-gray-600">
                    {p.total_incidents} incidents · max risk {p.max_risk_score} · {p.status}
                  </span>
                  <a
                    href={p.profile_url}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-1 block text-xs text-patrol-muted underline print:text-gray-700"
                  >
                    {p.profile_url}
                  </a>
                </li>
              ))}
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-medium">Severity breakdown</h2>
            <div className="mt-3 flex flex-wrap gap-2">
              {Object.entries(dossier.summary.severity_breakdown).map(([sev, count]) => (
                <span
                  key={sev}
                  className={`rounded border px-3 py-1 text-sm ${severityClass(sev)}`}
                >
                  {sev}: {count}
                </span>
              ))}
            </div>
          </section>

          {dossier.osint && (
            <section className="rounded-lg border border-patrol-accent/30 bg-patrol-accent/5 p-4">
              <h2 className="text-lg font-medium">OSINT — linked identities</h2>
              <p className="mt-1 text-xs text-patrol-muted">
                Matches by same username, display picture hash, bio, or display name across
                platforms.
              </p>
              {dossier.osint.linked_profiles.length > 0 && (
                <ul className="mt-3 space-y-2 text-sm">
                  {dossier.osint.linked_profiles.map((link) => (
                    <li
                      key={link.profile_id}
                      className="rounded border border-patrol-border bg-patrol-surface px-3 py-2"
                    >
                      <span className="font-mono text-patrol-accent">
                        [{link.platform}] @{link.username}
                      </span>
                      <span className="ml-2 text-xs text-patrol-muted">
                        confidence {(link.confidence * 100).toFixed(0)}% ·{' '}
                        {link.match_signals.join(', ')}
                      </span>
                      <a
                        href={link.profile_url}
                        target="_blank"
                        rel="noreferrer"
                        className="mt-1 block text-xs underline"
                      >
                        {link.profile_url}
                      </a>
                    </li>
                  ))}
                </ul>
              )}
              {dossier.osint.platform_candidates.length > 0 && (
                <>
                  <h3 className="mt-4 text-sm font-medium text-patrol-muted">
                    Profiles to verify manually
                  </h3>
                  <ul className="mt-2 space-y-1 text-xs text-patrol-muted">
                    {dossier.osint.platform_candidates.map((c) => (
                      <li key={c.platform}>
                        <a href={c.profile_url} className="text-patrol-accent underline" target="_blank" rel="noreferrer">
                          [{c.platform}] {c.profile_url}
                        </a>
                      </li>
                    ))}
                  </ul>
                </>
              )}
              <div className="mt-4 rounded border border-amber-500/30 bg-amber-500/5 p-3 text-xs text-amber-200/90">
                <p className="font-medium">Network / IP notes</p>
                <p className="mt-1">{dossier.osint.network_hints.disclaimer}</p>
                {dossier.osint.network_hints.geo_hints.length > 0 && (
                  <p className="mt-1">
                    Public geo hints: {dossier.osint.network_hints.geo_hints.join(', ')}
                  </p>
                )}
                {dossier.osint.network_hints.ip_addresses.length > 0 && (
                  <p className="mt-1 font-mono">
                    Recorded metadata: {dossier.osint.network_hints.ip_addresses.join(', ')}
                  </p>
                )}
              </div>
            </section>
          )}

          {dossier.affected_posts && dossier.affected_posts.length > 0 && (
            <section>
              <h2 className="text-lg font-medium">Posts targeted ({dossier.affected_posts.length})</h2>
              <ul className="mt-2 space-y-1 text-sm">
                {dossier.affected_posts.map((post, i) => (
                  <li key={i}>
                    {post.post_url ? (
                      <a
                        href={post.post_url}
                        className="text-patrol-accent underline"
                        target="_blank"
                        rel="noreferrer"
                      >
                        [{post.platform}] {post.post_url}
                      </a>
                    ) : (
                      <span>
                        [{post.platform}] post {post.post_id}
                      </span>
                    )}
                    <span className="ml-2 text-patrol-muted">
                      · {post.evidence_on_post} evidence item(s)
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          <section>
            <h2 className="text-lg font-medium">Targets harassed</h2>
            <p className="mt-2 text-sm text-patrol-muted print:text-gray-700">
              {dossier.summary.targets_affected.length > 0
                ? dossier.summary.targets_affected.map((t) => `@${t}`).join(', ')
                : 'None recorded'}
            </p>
          </section>

          <section>
            <h2 className="text-lg font-medium">Evidence ({dossier.evidence.length})</h2>
            <div className="mt-4 space-y-6">
              {dossier.evidence.map((ev) => {
                const thumb = screenshotUrl(ev.screenshot_path)
                return (
                  <div
                    key={ev.evidence_id}
                    className="break-inside-avoid rounded-lg border border-patrol-border p-4 print:border-gray-300"
                  >
                    <div className="flex flex-wrap items-center gap-2 text-sm">
                      <span className="font-mono font-medium">{ev.evidence_id}</span>
                      <span className={`rounded border px-2 py-0.5 text-xs ${severityClass(ev.severity)}`}>
                        {ev.severity}
                      </span>
                      <span className="text-patrol-muted print:text-gray-600">
                        {ev.platform} · risk {ev.risk_score}
                      </span>
                      {ev.target_username && (
                        <span>→ @{ev.target_username}</span>
                      )}
                    </div>
                    {(ev.abuse_categories?.length ?? 0) > 0 && (
                      <div className="mt-2">
                        <AbuseCategoryBadges categories={ev.abuse_categories ?? []} />
                      </div>
                    )}
                    <AbusiveCommentText
                      className="mt-3 whitespace-pre-wrap"
                      text={ev.comment_text}
                      abusive={ev.is_abusive ?? true}
                      lexiconMatch={ev.is_lexicon_match}
                    />
                    <AbuseExplanationPanel explanations={ev.abuse_explanations ?? []} />
                    <div className="mt-2 flex flex-wrap gap-3 text-xs">
                      {ev.comment_posted_at && (
                        <span className="text-patrol-muted">
                          Comment posted: {new Date(ev.comment_posted_at).toLocaleString()}
                        </span>
                      )}
                      {ev.evidence_captured_at && (
                        <span className="text-patrol-muted">
                          Evidence archived: {new Date(ev.evidence_captured_at).toLocaleString()}
                        </span>
                      )}
                    </div>
                    {ev.direct_comment_link && (
                      <a
                        href={ev.direct_comment_link}
                        className="mt-1 block text-xs font-medium text-patrol-accent underline print:text-blue-800"
                        target="_blank"
                        rel="noreferrer"
                      >
                        Direct link to comment (may break if deleted on platform)
                      </a>
                    )}
                    {ev.post_url && (
                      <a
                        href={ev.post_url}
                        className="mt-1 block text-xs text-patrol-muted underline print:text-gray-700"
                        target="_blank"
                        rel="noreferrer"
                      >
                        Post: {ev.post_url}
                      </a>
                    )}
                    {ev.deletion_resilient && (
                      <p className="mt-1 text-[10px] text-patrol-muted italic">
                        Screenshot + SHA-256 preserved if comment is removed later.
                      </p>
                    )}
                    {ev.screenshot_hash && (
                      <p className="mt-1 font-mono text-[10px] text-patrol-muted print:text-gray-500">
                        SHA-256: {ev.screenshot_hash}
                      </p>
                    )}
                    {thumb && (
                      <img
                        src={thumb}
                        alt={`Evidence ${ev.evidence_id}`}
                        className="mt-3 max-h-64 rounded border border-patrol-border object-contain print:max-h-48"
                      />
                    )}
                  </div>
                )
              })}
            </div>
          </section>

          <footer className="border-t border-patrol-border pt-4 text-xs text-patrol-muted print:border-gray-300 print:text-gray-600">
            Confidential — generated by PATROL for investigative use. Chain-of-custody hashes
            verify screenshot integrity where recorded.
          </footer>
        </article>
      )}

      <style jsx global>{`
        @media print {
          body {
            background: white !important;
            color: black !important;
          }
          aside,
          header nav,
          .print\\:hidden {
            display: none !important;
          }
          .dossier-report {
            box-shadow: none;
          }
        }
      `}</style>
    </AppShell>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-patrol-border bg-patrol-surface px-4 py-3 print:border-gray-200">
      <p className="text-xs text-patrol-muted print:text-gray-600">{label}</p>
      <p className="text-xl font-semibold">{value}</p>
    </div>
  )
}
