'use client'

import { FormEvent, useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { AppShell } from '@/components/layout/AppShell'
import {
  getAiStatus,
  getCrawlerSettings,
  updateCrawlerSettings,
  type AiStatus,
  type CrawlerSettings,
} from '@/lib/api'
import { getUser, isAuthenticated } from '@/lib/auth'

const PASSWORD_PLACEHOLDER = '********'

export default function SettingsPage() {
  const router = useRouter()
  const user = getUser()
  const isAdmin = user?.role === 'ADMIN'

  const [ai, setAi] = useState<AiStatus | null>(null)
  const [crawler, setCrawler] = useState<CrawlerSettings | null>(null)
  const [demoMode, setDemoMode] = useState(true)
  const [igUser, setIgUser] = useState('')
  const [igPassword, setIgPassword] = useState('')
  const [screenshotMode, setScreenshotMode] = useState<'pillow' | 'playwright' | 'both'>('both')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace('/login')
      return
    }
    async function load() {
      try {
        const aiStatus = await getAiStatus()
        setAi(aiStatus)
        if (isAdmin) {
          const crawlerSettings = await getCrawlerSettings()
          setCrawler(crawlerSettings)
          setDemoMode(crawlerSettings.crawler_demo_mode)
          setIgUser(crawlerSettings.instagram_username)
          setScreenshotMode(
            crawlerSettings.evidence_screenshot_mode as 'pillow' | 'playwright' | 'both',
          )
          if (crawlerSettings.instagram_password_set) {
            setIgPassword(PASSWORD_PLACEHOLDER)
          }
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load settings')
      } finally {
        setLoading(false)
      }
    }

    load()
  }, [router, isAdmin])

  async function handleSave(e: FormEvent) {
    e.preventDefault()
    setSaving(true)
    setError(null)
    setSuccess(null)
    try {
      const updated = await updateCrawlerSettings({
        crawler_demo_mode: demoMode,
        instagram_username: igUser.trim() || undefined,
        instagram_password:
          igPassword && igPassword !== PASSWORD_PLACEHOLDER ? igPassword : undefined,
        evidence_screenshot_mode: screenshotMode,
      })
      setCrawler(updated)
      if (updated.instagram_password_set) {
        setIgPassword(PASSWORD_PLACEHOLDER)
      }
      setSuccess('Crawler settings saved to database.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save settings')
    } finally {
      setSaving(false)
    }
  }

  return (
    <AppShell title="Settings" subtitle="AI models and patrol configuration">
      {error && (
        <p className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {error}
        </p>
      )}
      {success && (
        <p className="mb-4 rounded-lg border border-patrol-accent/30 bg-patrol-accent/10 px-4 py-3 text-sm text-patrol-accent">
          {success}
        </p>
      )}

      {!isAdmin && (
        <p className="rounded-lg border border-patrol-border bg-patrol-card px-4 py-3 text-sm text-patrol-muted">
          Crawler configuration requires an administrator account. Contact your admin to change
          Instagram credentials or demo mode.
        </p>
      )}

      {isAdmin && loading && (
        <p className="text-sm text-patrol-muted">Loading settings…</p>
      )}

      {isAdmin && !loading && (
        <form onSubmit={handleSave} className="mb-8 space-y-6">
          <section className="rounded-xl border border-patrol-border bg-patrol-card p-5">
            <h2 className="font-mono text-patrol-accent">Crawler &amp; Instagram</h2>
            <p className="mt-1 text-xs text-patrol-muted">
              Stored in <code className="text-patrol-text">system_settings</code> table
              {crawler?.source === 'database' ? ' (active)' : ' — using .env until saved'}
            </p>

            <label className="mt-4 flex cursor-pointer items-center gap-3 text-sm">
              <input
                type="checkbox"
                checked={demoMode}
                onChange={(e) => setDemoMode(e.target.checked)}
                className="h-4 w-4 rounded border-patrol-border"
              />
              <span className="text-patrol-text">
                Demo mode <span className="text-patrol-muted">(synthetic comments, no browser)</span>
              </span>
            </label>

            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              <label className="block text-sm">
                <span className="text-patrol-muted">Instagram username</span>
                <input
                  value={igUser}
                  onChange={(e) => setIgUser(e.target.value)}
                  autoComplete="off"
                  className="mt-1 w-full rounded-lg border border-patrol-border bg-patrol-surface px-3 py-2 text-patrol-text"
                  placeholder="your_instagram_handle"
                />
              </label>
              <label className="block text-sm">
                <span className="text-patrol-muted">Instagram password</span>
                <input
                  type="password"
                  value={igPassword}
                  onChange={(e) => setIgPassword(e.target.value)}
                  autoComplete="new-password"
                  className="mt-1 w-full rounded-lg border border-patrol-border bg-patrol-surface px-3 py-2 text-patrol-text"
                  placeholder={
                    crawler?.instagram_password_set ? PASSWORD_PLACEHOLDER : 'Enter password'
                  }
                />
                <span className="mt-1 block text-xs text-patrol-muted">
                  Leave as {PASSWORD_PLACEHOLDER} to keep the current password
                </span>
              </label>
            </div>

            <label className="mt-4 block text-sm">
              <span className="text-patrol-muted">Evidence screenshot mode</span>
              <select
                value={screenshotMode}
                onChange={(e) =>
                  setScreenshotMode(e.target.value as 'pillow' | 'playwright' | 'both')
                }
                className="mt-1 w-full max-w-md rounded-lg border border-patrol-border bg-patrol-surface px-3 py-2 text-patrol-text"
              >
                <option value="pillow">Pillow cards only (no browser)</option>
                <option value="playwright">Playwright page capture (live crawl)</option>
                <option value="both">Both (prefer Playwright when live)</option>
              </select>
            </label>

            <p className="mt-3 text-xs text-patrol-muted">
              Live Instagram crawls need demo mode off, valid credentials above, and Playwright
              installed on the server.
            </p>

            <button
              type="submit"
              disabled={saving}
              className="mt-5 rounded-lg bg-patrol-accent px-4 py-2 text-sm font-medium text-patrol-bg disabled:opacity-50"
            >
              {saving ? 'Saving…' : 'Save crawler settings'}
            </button>
          </section>
        </form>
      )}

      {ai && (
        <div className="space-y-4">
          <section className="rounded-xl border border-patrol-border bg-patrol-card p-5">
            <h2 className="font-mono text-patrol-accent">AI classifiers</h2>
            <ul className="mt-3 space-y-2 text-sm text-patrol-muted">
              <li>Keyword engine: {ai.keyword_engine ? 'Active' : 'Off'}</li>
              <li>Local ML: {ai.local_ml ? 'On' : 'Off'}</li>
              <li>HF Inference API: {ai.hf_inference_api ? 'On' : 'Off'}</li>
              <li>HF token configured: {ai.hf_api_configured ? 'Yes' : 'No'}</li>
              <li>Abuse threshold: {ai.abuse_threshold}</li>
            </ul>
          </section>
          <section className="rounded-xl border border-patrol-border bg-patrol-card p-5">
            <h2 className="font-mono text-patrol-accent">Hugging Face models</h2>
            <p className="mt-2 text-sm text-patrol-muted">
              ML options remain in backend <code className="text-patrol-text">.env</code>:{' '}
              USE_ML_CLASSIFIER, USE_HF_INFERENCE_API, HUGGINGFACE_API_TOKEN
            </p>
            {ai.multilingual_model && (
              <p className="mt-2 text-xs">Active local model: {ai.multilingual_model}</p>
            )}
          </section>
        </div>
      )}
    </AppShell>
  )
}
