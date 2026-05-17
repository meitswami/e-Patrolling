'use client'

import { FormEvent, useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { AppShell } from '@/components/layout/AppShell'
import { SystemStatusBar } from '@/components/layout/SystemStatusBar'
import { PlatformIcon } from '@/components/platforms/PlatformIcon'
import {
  getAiSettings,
  getAiStatus,
  getCrawlerSettings,
  getDashboardStats,
  getHealth,
  updateAiSettings,
  updateCrawlerSettings,
  type AiStatus,
  type CrawlerSettings,
} from '@/lib/api'
import { getUser, isAuthenticated } from '@/lib/auth'
import { connectDashboardWs, type WsMessage } from '@/lib/ws'
import type { DashboardStats, HealthResponse } from '@/types'

const PASSWORD_PLACEHOLDER = '********'

export default function SettingsPage() {
  const router = useRouter()
  const user = getUser()
  const isAdmin = user?.role === 'ADMIN'

  const [ai, setAi] = useState<AiStatus | null>(null)
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [wsConnected, setWsConnected] = useState(false)
  const [crawler, setCrawler] = useState<CrawlerSettings | null>(null)
  const [demoMode, setDemoMode] = useState(true)
  const [igUser, setIgUser] = useState('')
  const [igPassword, setIgPassword] = useState('')
  const [fbEmail, setFbEmail] = useState('')
  const [fbPassword, setFbPassword] = useState('')
  const [screenshotMode, setScreenshotMode] = useState<'pillow' | 'playwright' | 'both'>('both')
  const [useMl, setUseMl] = useState(false)
  const [useHfApi, setUseHfApi] = useState(false)
  const [abuseThreshold, setAbuseThreshold] = useState(0.65)
  const [savingAi, setSavingAi] = useState(false)
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
        const [aiStatus, apiHealth, dashboard] = await Promise.all([
          getAiStatus(),
          getHealth(),
          getDashboardStats(),
        ])
        setAi(aiStatus)
        setHealth(apiHealth)
        setStats(dashboard)
        if (isAdmin) {
          const [crawlerSettings, aiSettings] = await Promise.all([
            getCrawlerSettings(),
            getAiSettings(),
          ])
          setCrawler(crawlerSettings)
          setDemoMode(crawlerSettings.crawler_demo_mode)
          setIgUser(crawlerSettings.instagram_username)
          setScreenshotMode(
            crawlerSettings.evidence_screenshot_mode as 'pillow' | 'playwright' | 'both',
          )
          if (crawlerSettings.instagram_password_set) {
            setIgPassword(PASSWORD_PLACEHOLDER)
          }
          setFbEmail(crawlerSettings.facebook_email)
          if (crawlerSettings.facebook_password_set) {
            setFbPassword(PASSWORD_PLACEHOLDER)
          }
          setUseMl(aiSettings.use_ml_classifier)
          setUseHfApi(aiSettings.use_hf_inference_api)
          setAbuseThreshold(aiSettings.abuse_confidence_threshold)
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load settings')
      } finally {
        setLoading(false)
      }
    }

    load()

    const disconnect = connectDashboardWs((msg: WsMessage) => {
      if (msg.type === 'connected') {
        setWsConnected(true)
      }
    })

    return disconnect
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
        facebook_email: fbEmail.trim() || undefined,
        facebook_password:
          fbPassword && fbPassword !== PASSWORD_PLACEHOLDER ? fbPassword : undefined,
        evidence_screenshot_mode: screenshotMode,
      })
      setCrawler(updated)
      if (updated.instagram_password_set) {
        setIgPassword(PASSWORD_PLACEHOLDER)
      }
      if (updated.facebook_password_set) {
        setFbPassword(PASSWORD_PLACEHOLDER)
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

      {health && (
        <SystemStatusBar
          health={health}
          wsConnected={wsConnected}
          liveMonitoring={stats?.live_monitoring}
        />
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
            <h2 className="font-mono text-patrol-accent">Crawler platforms</h2>
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
                <span className="inline-flex items-center gap-1.5 text-patrol-muted">
                  <PlatformIcon platform="instagram" size="sm" />
                  Instagram username
                </span>
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

            <h3 className="mt-6 flex items-center gap-2 font-mono text-sm text-patrol-accent">
              <PlatformIcon platform="facebook" size="sm" />
              Facebook
            </h3>
            <p className="mt-1 text-xs text-patrol-muted">
              Playwright login below, or set FACEBOOK_ACCESS_TOKEN in .env for Graph API (Pages).
              {crawler?.facebook_access_token_set && ' Token detected in .env.'}
            </p>
            <div className="mt-3 grid gap-4 sm:grid-cols-2">
              <label className="block text-sm">
                <span className="text-patrol-muted">Facebook email</span>
                <input
                  value={fbEmail}
                  onChange={(e) => setFbEmail(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-patrol-border bg-patrol-surface px-3 py-2 text-patrol-text"
                />
              </label>
              <label className="block text-sm">
                <span className="text-patrol-muted">Facebook password</span>
                <input
                  type="password"
                  value={fbPassword}
                  onChange={(e) => setFbPassword(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-patrol-border bg-patrol-surface px-3 py-2 text-patrol-text"
                />
              </label>
            </div>

            <h3 className="mt-6 flex items-center gap-2 font-mono text-sm text-patrol-accent">
              <PlatformIcon platform="threads" size="sm" />
              Threads
            </h3>
            <p className="mt-1 text-xs text-patrol-muted">
              Uses Instagram login above (Meta SSO on threads.net).
            </p>

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
              Live crawls need demo mode off, platform credentials, and Playwright on the server.
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
            {isAdmin && !loading && (
              <div className="mt-4 space-y-3 border-t border-patrol-border pt-4">
                <label className="flex items-center gap-3 text-sm">
                  <input
                    type="checkbox"
                    checked={useMl}
                    onChange={(e) => setUseMl(e.target.checked)}
                    className="h-4 w-4"
                  />
                  <span>Use local ML classifier (downloads models on first run)</span>
                </label>
                <label className="flex items-center gap-3 text-sm">
                  <input
                    type="checkbox"
                    checked={useHfApi}
                    onChange={(e) => setUseHfApi(e.target.checked)}
                    className="h-4 w-4"
                  />
                  <span>Use Hugging Face Inference API</span>
                </label>
                <label className="block text-sm">
                  <span className="text-patrol-muted">Abuse confidence threshold</span>
                  <input
                    type="number"
                    min={0.1}
                    max={1}
                    step={0.05}
                    value={abuseThreshold}
                    onChange={(e) => setAbuseThreshold(parseFloat(e.target.value))}
                    className="mt-1 w-full max-w-xs rounded-lg border border-patrol-border bg-patrol-surface px-3 py-2"
                  />
                </label>
                <button
                  type="button"
                  disabled={savingAi}
                  onClick={async () => {
                    setSavingAi(true)
                    setError(null)
                    setSuccess(null)
                    try {
                      await updateAiSettings({
                        use_ml_classifier: useMl,
                        use_hf_inference_api: useHfApi,
                        abuse_confidence_threshold: abuseThreshold,
                      })
                      const aiStatus = await getAiStatus()
                      setAi(aiStatus)
                      setSuccess('AI settings saved')
                    } catch (err) {
                      setError(err instanceof Error ? err.message : 'Failed to save AI settings')
                    } finally {
                      setSavingAi(false)
                    }
                  }}
                  className="rounded-lg border border-patrol-accent/50 px-4 py-2 text-sm text-patrol-accent disabled:opacity-50"
                >
                  {savingAi ? 'Saving…' : 'Save AI settings'}
                </button>
              </div>
            )}
          </section>
          {ai.multilingual_model && (
            <p className="text-xs text-patrol-muted">Local model: {ai.multilingual_model}</p>
          )}
        </div>
      )}
    </AppShell>
  )
}
