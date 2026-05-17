'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useParams, useRouter } from 'next/navigation'
import { AppShell } from '@/components/layout/AppShell'
import { API_BASE_URL, SEVERITY_CONFIG } from '@/lib/constants'
import {
  deleteEvidence,
  escalateEvidence,
  getEvidence,
  type EvidenceDetail,
} from '@/lib/api'
import { getUser, isAuthenticated } from '@/lib/auth'

function evidenceImageUrl(screenshotPath: string | null): string | null {
  if (!screenshotPath) return null
  const base = API_BASE_URL.replace(/\/$/, '')
  const clean = screenshotPath.replace(/^\/+/, '').replace(/^storage\//, '')
  return `${base}/storage/${clean}`
}

export default function EvidenceDetailPage() {
  const router = useRouter()
  const params = useParams()
  const id = params.id as string
  const user = getUser()
  const canEscalate = user?.role === 'ADMIN' || user?.role === 'ANALYST'
  const canDelete = user?.role === 'ADMIN'

  const [item, setItem] = useState<EvidenceDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [notes, setNotes] = useState('')
  const [acting, setActing] = useState(false)

  async function load() {
    const data = await getEvidence(id)
    setItem(data)
    setNotes(data.notes || '')
  }

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace('/login')
      return
    }
    if (!id) return

    load().catch((err) => {
      setError(err instanceof Error ? err.message : 'Evidence not found')
    }).finally(() => setLoading(false))
  }, [router, id])

  async function handleEscalate() {
    if (!item) return
    setActing(true)
    setError(null)
    try {
      await escalateEvidence(id, notes)
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Escalation failed')
    } finally {
      setActing(false)
    }
  }

  async function handleDelete() {
    if (!confirm('Permanently delete this evidence record?')) return
    setActing(true)
    setError(null)
    try {
      await deleteEvidence(id)
      router.push('/evidence')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Delete failed')
      setActing(false)
    }
  }

  const imgUrl = item ? evidenceImageUrl(item.screenshot_path) : null
  const sev = item ? SEVERITY_CONFIG[item.severity_level] : null

  return (
    <AppShell title="Evidence detail" subtitle={item?.evidence_id ?? 'Loading…'}>
      <Link
        href="/evidence"
        className="mb-4 inline-block text-sm text-patrol-accent hover:underline"
      >
        ← Back to evidence feed
      </Link>

      {error && (
        <p className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {error}
        </p>
      )}

      {loading && <p className="text-sm text-patrol-muted">Loading evidence…</p>}

      {item && sev && (
        <article className="rounded-xl border border-patrol-border bg-patrol-card p-6">
          <div className="flex flex-wrap gap-2 text-xs">
            <span className="font-mono text-lg text-patrol-accent">{item.evidence_id}</span>
            <span className={`rounded border px-2 py-0.5 ${sev.className}`}>{sev.label}</span>
            {item.is_escalated && (
              <span className="rounded border border-red-500/40 bg-red-500/10 px-2 py-0.5 text-red-400">
                Escalated
              </span>
            )}
            <span className="text-patrol-muted">{item.platform}</span>
            <span className="text-patrol-muted">Risk {item.risk_score}</span>
          </div>

          {imgUrl && (
            <a
              href={imgUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-4 block overflow-hidden rounded-lg border border-patrol-border"
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={imgUrl}
                alt={`Evidence ${item.evidence_id}`}
                className="max-h-96 w-full object-contain bg-patrol-surface"
              />
            </a>
          )}

          <p className="mt-4 text-sm leading-relaxed text-patrol-text">{item.comment_text}</p>

          <dl className="mt-6 grid gap-3 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-patrol-muted">Target</dt>
              <dd className="text-patrol-text">@{item.target_username ?? '—'}</dd>
            </div>
            <div>
              <dt className="text-patrol-muted">Accused</dt>
              <dd className="text-patrol-text">@{item.accused_username ?? '—'}</dd>
            </div>
            <div>
              <dt className="text-patrol-muted">Captured</dt>
              <dd className="text-patrol-text">
                {new Date(item.capture_timestamp).toLocaleString()}
              </dd>
            </div>
            {item.escalated_at && (
              <div>
                <dt className="text-patrol-muted">Escalated</dt>
                <dd className="text-patrol-text">
                  {new Date(item.escalated_at).toLocaleString()}
                </dd>
              </div>
            )}
            {item.post_url && (
              <div className="sm:col-span-2">
                <dt className="text-patrol-muted">Post URL</dt>
                <dd>
                  <a
                    href={item.post_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="break-all text-patrol-accent hover:underline"
                  >
                    {item.post_url}
                  </a>
                </dd>
              </div>
            )}
          </dl>

          {canEscalate && (
            <div className="mt-6 border-t border-patrol-border pt-4">
              <label className="block text-sm">
                <span className="text-patrol-muted">Analyst notes</span>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  rows={3}
                  className="mt-1 w-full rounded-lg border border-patrol-border bg-patrol-surface px-3 py-2 text-sm text-patrol-text"
                  placeholder="Escalation notes for cyber cell…"
                />
              </label>
              <div className="mt-3 flex flex-wrap gap-2">
                <button
                  type="button"
                  disabled={acting || item.is_escalated}
                  onClick={handleEscalate}
                  className="rounded-lg bg-patrol-accent px-4 py-2 text-sm font-medium text-patrol-bg disabled:opacity-50"
                >
                  {item.is_escalated ? 'Already escalated' : 'Escalate for review'}
                </button>
                {canDelete && (
                  <button
                    type="button"
                    disabled={acting}
                    onClick={handleDelete}
                    className="rounded-lg border border-red-500/40 px-4 py-2 text-sm text-red-400 disabled:opacity-50"
                  >
                    Delete evidence
                  </button>
                )}
              </div>
            </div>
          )}
        </article>
      )}
    </AppShell>
  )
}
