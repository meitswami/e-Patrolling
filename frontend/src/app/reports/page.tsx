'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { AppShell } from '@/components/layout/AppShell'
import { API_BASE_URL, API_PREFIX } from '@/lib/constants'
import { getToken, isAuthenticated } from '@/lib/auth'

function downloadFile(path: string, filename: string, setError: (m: string | null) => void) {
  const token = getToken()
  if (!token) return
  setError(null)
  fetch(`${API_BASE_URL}${API_PREFIX}${path}`, {
    headers: { Authorization: `Bearer ${token}` },
  })
    .then(async (res) => {
      if (!res.ok) throw new Error(`Export failed (${res.status})`)
      const blob = await res.blob()
      const a = document.createElement('a')
      a.href = URL.createObjectURL(blob)
      a.download = filename
      a.click()
      URL.revokeObjectURL(a.href)
    })
    .catch((err) => setError(err instanceof Error ? err.message : 'Export failed'))
}

export default function ReportsPage() {
  const router = useRouter()
  const [error, setError] = useState<string | null>(null)
  const stamp = new Date().toISOString().slice(0, 10)

  useEffect(() => {
    if (!isAuthenticated()) router.replace('/login')
  }, [router])

  return (
    <AppShell title="Reports" subtitle="Export evidence for case files">
      {error && (
        <p className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {error}
        </p>
      )}
      <div className="space-y-4">
        <div className="rounded-xl border border-patrol-border bg-patrol-card p-6">
          <h2 className="font-mono text-patrol-accent">CSV export</h2>
          <p className="mt-2 text-sm text-patrol-muted">
            Full evidence table (up to 5,000 rows) for spreadsheets.
          </p>
          <button
            type="button"
            onClick={() =>
              downloadFile(
                '/reports/evidence/export.csv',
                `patrol_evidence_${stamp}.csv`,
                setError,
              )
            }
            className="mt-4 rounded-lg bg-patrol-accent px-4 py-2 text-sm font-medium text-patrol-bg"
          >
            Download CSV
          </button>
        </div>
        <div className="rounded-xl border border-patrol-border bg-patrol-card p-6">
          <h2 className="font-mono text-patrol-accent">PDF summary</h2>
          <p className="mt-2 text-sm text-patrol-muted">
            Printable summary (latest 200 evidence items). Requires reportlab on server.
          </p>
          <button
            type="button"
            onClick={() =>
              downloadFile(
                '/reports/evidence/export.pdf',
                `patrol_evidence_${stamp}.pdf`,
                setError,
              )
            }
            className="mt-4 rounded-lg border border-patrol-accent/40 px-4 py-2 text-sm text-patrol-accent"
          >
            Download PDF
          </button>
        </div>
      </div>
    </AppShell>
  )
}
