'use client'

import { FormEvent, useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { AppShell } from '@/components/layout/AppShell'
import { SystemStatusBar } from '@/components/layout/SystemStatusBar'
import { PlatformIcon } from '@/components/platforms/PlatformIcon'
import {
  connectInstagramSession,
  disconnectInstagramSession,
  getAiSettings,
  getAiStatus,
  getCrawlerSettings,
  getDashboardStats,
  getHealth,
  updateAiSettings,
  updateCrawlerSettings,
  validateInstagramCredentials,
  type AiStatus,
  type CrawlerSettings,
  type InstagramValidationResult,
} from '@/lib/api'
import { getUser, isAuthenticated } from '@/lib/auth'
import { connectDashboardWs, type WsMessage } from '@/lib/ws'
import type { DashboardStats, HealthResponse } from '@/types'

const PASSWORD_PLACEHOLDER = '********'

export default function SettingsPage() {
  const router = useRouter()
  const [mounted, setMounted] = useState(false)
  const [isAdmin, setIsAdmin] = useState(false)

  const [ai, setAi] = useState<AiStatus | null>(null)
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [wsConnected, setWsConnected] = useState(false)
  const [crawler, setCrawler] = useState<CrawlerSettings | null>(null)
  const [fbEmail, setFbEmail] = useState('')
  const [fbPassword, setFbPassword] = useState('')
  const [screenshotMode, setScreenshotMode] = useState<'pillow' | 'playwright' | 'both'>('both')
  const [useMl, setUseMl] = useState(false)
  const [useHfApi, setUseHfApi] = useState(false)
  const [abuseThreshold, setAbuseThreshold] = useState(0.65)
  const [savingAi, setSavingAi] = useState(false)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [connecting, setConnecting] = useState(false)
  const [testing, setTesting] = useState(false)
  const [connectionResult, setConnectionResult] = useState<InstagramValidationResult | null>(
    null,
  )
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  async function refreshCrawlerSettings() {
    const crawlerSettings = await getCrawlerSettings()
    setCrawler(crawlerSettings)
  }

  useEffect(() => {
    setMounted(true)
    if (!isAuthenticated()) {
      router.replace('/admin')
      return
    }
    const admin = getUser()?.role === 'ADMIN'
    setIsAdmin(admin)

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
        if (admin) {
          const [crawlerSettings, aiSettings] = await Promise.all([
            getCrawlerSettings(),
            getAiSettings(),
          ])
          setCrawler(crawlerSettings)
          setScreenshotMode(
            crawlerSettings.evidence_screenshot_mode as 'pillow' | 'playwright' | 'both',
          )
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
  }, [router])

  async function handleSave(e: FormEvent) {
    e.preventDefault()
    setSaving(true)
    setError(null)
    setSuccess(null)
    try {
      const updated = await updateCrawlerSettings({
        facebook_email: fbEmail.trim() || undefined,
        facebook_password:
          fbPassword && fbPassword !== PASSWORD_PLACEHOLDER ? fbPassword : undefined,
        evidence_screenshot_mode: screenshotMode,
      })
      setCrawler(updated)
      if (updated.facebook_password_set) {
        setFbPassword(PASSWORD_PLACEHOLDER)
      }
      setSuccess('Crawler settings saved.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save settings')
    } finally {
      setSaving(false)
    }
  }

  const igConnected =
    crawler?.instagram_session_connected ?? crawler?.instagram_auth_configured ?? false
  const igUsername = crawler?.instagram_username?.trim()

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

      {!mounted && (
        <p className="text-sm text-patrol-muted">Loading settings…</p>
      )}

      {mounted && !isAdmin && (
        <p className="rounded-lg border border-patrol-border bg-patrol-card px-4 py-3 text-sm text-patrol-muted">
          Crawler configuration requires an administrator account. Contact your admin to connect
          Instagram.
        </p>
      )}

      {mounted && isAdmin && loading && (
        <p className="text-sm text-patrol-muted">Loading settings…</p>
      )}

      {mounted && isAdmin && !loading && (
        <form onSubmit={handleSave} className="mb-8 space-y-6">
          <section className="rounded-xl border border-patrol-border bg-patrol-card p-5">
            <h2 className="font-mono text-patrol-accent">Crawler platforms</h2>
            <p className="mt-1 text-xs text-patrol-muted">
              Instagram uses saved browser session cookies (no password stored in PATROL).
            </p>

            <p className="mt-3 inline-flex items-center gap-2 rounded-lg border border-patrol-accent/40 bg-patrol-accent/10 px-3 py-1.5 text-sm text-patrol-accent">
              Live mode — real browser crawls only
            </p>

            <div className="mt-4 rounded-lg border border-patrol-border bg-patrol-surface/50 p-4">
              <div className="flex items-center gap-2 font-mono text-sm text-patrol-accent">
                <PlatformIcon platform="instagram" size="sm" />
                Instagram
              </div>
              <p className="mt-2 text-sm text-patrol-muted">
                {igConnected
                  ? igUsername
                    ? `Connected as @${igUsername} — session cookies saved on server.`
                    : 'Connected — session cookies saved on server.'
                  : 'Not connected. Click below to open Instagram in a browser and log in manually.'}
              </p>
              <p className="mt-2 text-xs text-patrol-muted">
                A Chrome/Edge window opens on this machine (where the API runs). Log in on
                instagram.com, complete 2FA if asked, then return here when your feed loads.
              </p>

              {connectionResult && (
                <p
                  className={`mt-3 whitespace-pre-wrap rounded-lg border px-3 py-2 text-sm ${
                    connectionResult.success
                      ? 'border-green-500/40 bg-green-500/10 text-green-400'
                      : 'border-red-500/40 bg-red-500/10 text-red-400'
                  }`}
                >
                  {connectionResult.message}
                </p>
              )}

              <div className="mt-4 flex flex-wrap gap-3">
                <button
                  type="button"
                  disabled={connecting || testing}
                  onClick={async () => {
                    setConnecting(true)
                    setError(null)
                    setSuccess(null)
                    setConnectionResult(null)
                    try {
                      setSuccess(
                        'Browser opening… Log in on Instagram in that window (up to 5 minutes).',
                      )
                      const result = await connectInstagramSession()
                      setConnectionResult(result)
                      await refreshCrawlerSettings()
                      if (result.success) {
                        setSuccess(result.message)
                        setError(null)
                      } else {
                        setError(result.message)
                        setSuccess(null)
                      }
                    } catch (err) {
                      setError(err instanceof Error ? err.message : 'Connect failed')
                      setSuccess(null)
                    } finally {
                      setConnecting(false)
                    }
                  }}
                  className="rounded-lg bg-patrol-accent px-4 py-2 text-sm font-medium text-patrol-bg disabled:opacity-50"
                >
                  {connecting ? 'Waiting for login…' : 'Connect Instagram'}
                </button>
                <button
                  type="button"
                  disabled={testing || connecting || !igConnected}
                  onClick={async () => {
                    setTesting(true)
                    setError(null)
                    setConnectionResult(null)
                    try {
                      const result = await validateInstagramCredentials()
                      setConnectionResult(result)
                      if (result.success) {
                        setSuccess(result.message)
                      } else {
                        setError(result.message)
                      }
                    } catch (err) {
                      setError(err instanceof Error ? err.message : 'Session check failed')
                    } finally {
                      setTesting(false)
                    }
                  }}
                  className="rounded-lg border border-patrol-accent/50 px-4 py-2 text-sm text-patrol-accent disabled:opacity-50"
                >
                  {testing ? 'Checking…' : 'Verify session'}
                </button>
                <button
                  type="button"
                  disabled={connecting || !igConnected}
                  onClick={async () => {
                    setError(null)
                    setSuccess(null)
                    try {
                      const result = await disconnectInstagramSession()
                      setConnectionResult(result)
                      await refreshCrawlerSettings()
                      setSuccess(result.message)
                    } catch (err) {
                      setError(err instanceof Error ? err.message : 'Disconnect failed')
                    }
                  }}
                  className="rounded-lg border border-red-500/40 px-4 py-2 text-sm text-red-400 disabled:opacity-50"
                >
                  Disconnect
                </button>
              </div>
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
              Uses the same Instagram session cookies above.
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
              Live Instagram crawls require a connected session and Playwright on the server.
            </p>

            <div className="mt-5">
              <button
                type="submit"
                disabled={saving}
                className="rounded-lg border border-patrol-accent/50 px-4 py-2 text-sm text-patrol-accent disabled:opacity-50"
              >
                {saving ? 'Saving…' : 'Save Facebook & screenshot settings'}
              </button>
            </div>
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
            {mounted && isAdmin && !loading && (
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
