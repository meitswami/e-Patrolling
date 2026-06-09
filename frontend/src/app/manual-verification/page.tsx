'use client'

import { Suspense, useCallback, useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { CheckCircle, XCircle } from 'lucide-react'
import { AppShell } from '@/components/layout/AppShell'
import { PlatformLabel } from '@/components/platforms/PlatformLabel'
import { AbuseCategoryBadges } from '@/components/abuse/AbuseCategoryBadges'
import { AbuseExplanationPanel } from '@/components/abuse/AbuseExplanationPanel'
import { AbusiveCommentText } from '@/components/abuse/AbusiveCommentText'
import { API_BASE_URL, SEVERITY_CONFIG, ABUSE_CATEGORY_CONFIG } from '@/lib/constants'
import { listUnverifiedEvidence, verifyEvidence } from '@/lib/api'
import { isAuthenticated } from '@/lib/auth'
import type { EvidenceListItem, SeverityLevel } from '@/types'

function evidenceImageUrl(screenshotPath: string | null): string | null {
  if (!screenshotPath) return null
  const base = API_BASE_URL.replace(/\/$/, '')
  const clean = screenshotPath.replace(/^\/+/, '').replace(/^storage\//, '')
  return `${base}/storage/${clean}`
}

export default function ManualVerificationPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-sm text-patrol-muted">Loading verification queue...</div>}>
      <ManualVerificationContent />
    </Suspense>
  )
}

function ManualVerificationContent() {
  const router = useRouter()
  const [items, setItems] = useState<EvidenceListItem[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [successMsg, setSuccessMsg] = useState<string | null>(null)

  // Modal state
  const [confirmModal, setConfirmModal] = useState<{ type: 'abusive' | 'false_positive'; item: EvidenceListItem } | null>(null)
  const [modalLabel, setModalLabel] = useState('')
  const [modalMeaning, setModalMeaning] = useState('')
  const [modalImplication, setModalImplication] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await listUnverifiedEvidence(1, 50)
      setItems(data.items)
      setTotal(data.total)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load unverified evidence')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace('/admin')
      return
    }
    load()
  }, [router, load])

  const openAbusiveModal = (item: EvidenceListItem) => {
    setConfirmModal({ type: 'abusive', item })
    setModalLabel('')
    setModalMeaning('')
    setModalImplication('')
  }

  const openFalsePositiveModal = (item: EvidenceListItem) => {
    setConfirmModal({ type: 'false_positive', item })
  }

  const closeModal = () => {
    setConfirmModal(null)
    setModalLabel('')
    setModalMeaning('')
    setModalImplication('')
  }

  const handleConfirmAbusive = async () => {
    if (!confirmModal) return
    setSubmitting(true)
    try {
      await verifyEvidence(confirmModal.item.id, {
        is_abusive: true,
        add_to_dictionary: true,
        label: modalLabel || undefined,
        meaning_en: modalMeaning || undefined,
        offender_implication: modalImplication || undefined,
      })
      setItems((prev) => prev.filter((i) => i.id !== confirmModal.item.id))
      setTotal((prev) => prev - 1)
      setSuccessMsg('Evidence confirmed as abusive and added to dictionary.')
      closeModal()
      setTimeout(() => setSuccessMsg(null), 4000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Verification failed')
    } finally {
      setSubmitting(false)
    }
  }

  const handleConfirmFalsePositive = async () => {
    if (!confirmModal) return
    setSubmitting(true)
    try {
      await verifyEvidence(confirmModal.item.id, {
        is_abusive: false,
        add_to_dictionary: false,
      })
      setItems((prev) => prev.filter((i) => i.id !== confirmModal.item.id))
      setTotal((prev) => prev - 1)
      setSuccessMsg('Evidence marked as false positive.')
      closeModal()
      setTimeout(() => setSuccessMsg(null), 4000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Verification failed')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AppShell title="Manual Verification" subtitle={`${total} item(s) pending verification`}>
      {successMsg && (
        <p className="mb-4 rounded-lg border border-patrol-accent/30 bg-patrol-accent/10 px-4 py-3 text-sm text-patrol-accent">
          {successMsg}
        </p>
      )}

      {error && (
        <p className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {error}
        </p>
      )}

      {loading && <p className="text-sm text-patrol-muted">Loading unverified evidence...</p>}

      {!loading && items.length === 0 && !error && (
        <div className="rounded-xl border border-dashed border-patrol-border p-12 text-center">
          <p className="font-mono text-patrol-accent">No evidence pending verification</p>
          <p className="mt-2 text-sm text-patrol-muted">
            All detected evidence has been reviewed. New items will appear here when the AI flags content.
          </p>
        </div>
      )}

      <div className="space-y-3">
        {items.map((item) => {
          const sev = SEVERITY_CONFIG[item.severity_level]
          const imgUrl = evidenceImageUrl(item.screenshot_path)
          return (
            <article
              key={item.id}
              className="rounded-xl border border-patrol-border bg-patrol-card p-4 transition hover:border-patrol-accent/20"
            >
              <div className="flex flex-col gap-4 lg:flex-row">
                {imgUrl && (
                  <a
                    href={imgUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block shrink-0 overflow-hidden rounded-lg border border-patrol-border bg-patrol-surface"
                  >
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={imgUrl}
                      alt={`Evidence ${item.evidence_id}`}
                      className="h-36 w-full max-w-xs object-cover object-top lg:h-40"
                    />
                  </a>
                )}
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2 text-xs">
                    <Link
                      href={`/evidence/${item.id}`}
                      className="font-mono text-patrol-accent hover:underline"
                    >
                      {item.evidence_id}
                    </Link>
                    <AbuseCategoryBadges categories={item.abuse_categories ?? []} />
                    <span className={`rounded border px-2 py-0.5 ${sev.className}`}>{sev.label}</span>
                    <PlatformLabel platform={item.platform} size="sm" className="text-patrol-muted" />
                    <span className="text-patrol-muted">Risk {item.risk_score}</span>
                  </div>
                  <AbusiveCommentText
                    className="mt-2"
                    text={item.comment_text}
                    abusive={item.is_abusive}
                    lexiconMatch={item.is_lexicon_match}
                    lineClamp
                  />
                  <AbuseExplanationPanel explanations={item.abuse_explanations ?? []} />
                  <p className="mt-2 text-xs text-patrol-muted">
                    Target: {item.target_username ?? '\u2014'} · Accused:{' '}
                    {item.accused_username ? (
                      <Link
                        href={`/offenders/dossier/${encodeURIComponent(item.accused_username)}`}
                        className="text-patrol-accent hover:underline"
                      >
                        @{item.accused_username}
                      </Link>
                    ) : (
                      '\u2014'
                    )}
                    {' '} · {new Date(item.capture_timestamp).toLocaleString()}
                  </p>
                  {/* Action buttons */}
                  <div className="mt-3 flex items-center justify-end gap-2">
                    <button
                      type="button"
                      onClick={() => openAbusiveModal(item)}
                      className="inline-flex items-center gap-1.5 rounded-lg bg-green-600/20 border border-green-500/40 px-3 py-1.5 text-xs font-medium text-green-400 hover:bg-green-600/30 transition"
                    >
                      <CheckCircle className="h-3.5 w-3.5" />
                      Confirm Abusive
                    </button>
                    <button
                      type="button"
                      onClick={() => openFalsePositiveModal(item)}
                      className="inline-flex items-center gap-1.5 rounded-lg bg-red-600/20 border border-red-500/40 px-3 py-1.5 text-xs font-medium text-red-400 hover:bg-red-600/30 transition"
                    >
                      <XCircle className="h-3.5 w-3.5" />
                      False Positive
                    </button>
                  </div>
                </div>
              </div>
            </article>
          )
        })}
      </div>

      {/* Confirm Abusive Modal */}
      {confirmModal?.type === 'abusive' && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="mx-4 w-full max-w-lg rounded-xl border border-patrol-border bg-patrol-surface p-6 shadow-2xl">
            <h3 className="text-lg font-semibold text-patrol-text">Add to Abuse Dictionary</h3>
            <div className="mt-3 rounded-lg border border-patrol-border bg-patrol-bg p-3">
              <p className="text-sm text-patrol-muted italic">
                &ldquo;{confirmModal.item.comment_text}&rdquo;
              </p>
            </div>
            <div className="mt-4 space-y-3">
              <div>
                <label className="block text-xs font-medium text-patrol-muted mb-1">Category Label</label>
                <select
                  value={modalLabel}
                  onChange={(e) => setModalLabel(e.target.value)}
                  className="w-full rounded-lg border border-patrol-border bg-patrol-bg px-3 py-2 text-sm text-patrol-text"
                >
                  <option value="">Select a category...</option>
                  {Object.keys(ABUSE_CATEGORY_CONFIG).map((key) => (
                    <option key={key} value={key}>
                      {key}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-patrol-muted mb-1">Meaning (English)</label>
                <input
                  type="text"
                  value={modalMeaning}
                  onChange={(e) => setModalMeaning(e.target.value)}
                  placeholder="Optional: English meaning of the term"
                  className="w-full rounded-lg border border-patrol-border bg-patrol-bg px-3 py-2 text-sm text-patrol-text"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-patrol-muted mb-1">What the offender implies</label>
                <input
                  type="text"
                  value={modalImplication}
                  onChange={(e) => setModalImplication(e.target.value)}
                  placeholder="Optional: What the offender implies by this"
                  className="w-full rounded-lg border border-patrol-border bg-patrol-bg px-3 py-2 text-sm text-patrol-text"
                />
              </div>
            </div>
            <div className="mt-5 flex items-center justify-end gap-3">
              <button
                type="button"
                onClick={closeModal}
                disabled={submitting}
                className="rounded-lg border border-patrol-border px-4 py-2 text-sm text-patrol-muted hover:bg-patrol-card transition disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirmAbusive}
                disabled={submitting}
                className="rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700 transition disabled:opacity-50"
              >
                {submitting ? 'Confirming...' : 'Confirm & Add'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* False Positive Modal */}
      {confirmModal?.type === 'false_positive' && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="mx-4 w-full max-w-lg rounded-xl border border-patrol-border bg-patrol-surface p-6 shadow-2xl">
            <h3 className="text-lg font-semibold text-patrol-text">Mark as False Positive</h3>
            <p className="mt-2 text-sm text-patrol-muted">
              This comment will be marked as not abusive. This helps train the AI to avoid similar false detections.
            </p>
            <div className="mt-3 rounded-lg border border-patrol-border bg-patrol-bg p-3">
              <p className="text-sm text-patrol-muted italic">
                &ldquo;{confirmModal.item.comment_text}&rdquo;
              </p>
            </div>
            <div className="mt-5 flex items-center justify-end gap-3">
              <button
                type="button"
                onClick={closeModal}
                disabled={submitting}
                className="rounded-lg border border-patrol-border px-4 py-2 text-sm text-patrol-muted hover:bg-patrol-card transition disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirmFalsePositive}
                disabled={submitting}
                className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 transition disabled:opacity-50"
              >
                {submitting ? 'Confirming...' : 'Confirm False Positive'}
              </button>
            </div>
          </div>
        </div>
      )}
    </AppShell>
  )
}
