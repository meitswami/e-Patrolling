'use client'

import { FormEvent, useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Shield } from 'lucide-react'
import { login } from '@/lib/api'
import { isAuthenticated, saveSession } from '@/lib/auth'

export function AdminLogin() {
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (isAuthenticated()) router.replace('/dashboard')
  }, [router])

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const data = await login({ email, password })
      saveSession(data)
      router.push('/dashboard')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-patrol-bg px-4">
      <div className="w-full max-w-md rounded-xl border border-patrol-border bg-patrol-surface p-8 shadow-2xl">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-xl bg-patrol-accent/10">
            <Shield className="h-7 w-7 text-patrol-accent" />
          </div>
          <h1 className="font-mono text-2xl font-bold text-patrol-accent">PATROL Admin</h1>
          <p className="mt-1 text-sm text-patrol-muted">
            Predictive Abuse Tracking &amp; Regional Observation Layer
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="email" className="mb-1.5 block text-sm text-patrol-muted">
              Email
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="username"
              className="w-full rounded-lg border border-patrol-border bg-patrol-card px-3 py-2.5 text-patrol-text outline-none focus:ring-2 focus:ring-patrol-accent/50"
            />
          </div>

          <div>
            <label htmlFor="password" className="mb-1.5 block text-sm text-patrol-muted">
              Password
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
              className="w-full rounded-lg border border-patrol-border bg-patrol-card px-3 py-2.5 text-patrol-text outline-none focus:ring-2 focus:ring-patrol-accent/50"
            />
          </div>

          {error && (
            <p className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-400">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-patrol-accent py-2.5 font-semibold text-patrol-bg transition hover:opacity-90 disabled:opacity-50"
          >
            {loading ? 'Signing in…' : 'Sign in'}
          </button>
        </form>

        <p className="mt-6 text-center text-xs text-patrol-muted">
          <a href="/" className="text-patrol-accent hover:underline">
            ← Back to website
          </a>
        </p>
      </div>
    </div>
  )
}
