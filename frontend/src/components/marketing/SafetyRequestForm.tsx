'use client'

import { FormEvent, useEffect, useState } from 'react'
import { Plus, Trash2 } from 'lucide-react'
import { getIndiaLocations, submitSafetyRequest, type ProfilePreviewResult } from '@/lib/api'
import { ProfilePreviewDropdown } from '@/components/ProfilePreviewDropdown'

export function SafetyRequestForm() {
  const [profiles, setProfiles] = useState([''])
  const [state, setState] = useState('')
  const [city, setCity] = useState('')
  const [contactName, setContactName] = useState('')
  const [contactEmail, setContactEmail] = useState('')
  const [contactPhone, setContactPhone] = useState('')
  const [message, setMessage] = useState('')
  const [states, setStates] = useState<string[]>([])
  const [citiesByState, setCitiesByState] = useState<Record<string, string[]>>({})
  const [loadingLoc, setLoadingLoc] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getIndiaLocations()
      .then((data) => {
        setStates(data.states)
        setCitiesByState(data.cities_by_state)
      })
      .catch(() => setError('Could not load state and city list. Please try again later.'))
      .finally(() => setLoadingLoc(false))
  }, [])

  const cities = state ? citiesByState[state] ?? [] : []

  function addProfileRow() {
    if (profiles.length >= 10) return
    setProfiles((p) => [...p, ''])
  }

  function removeProfileRow(index: number) {
    if (profiles.length <= 1) return
    setProfiles((p) => p.filter((_, i) => i !== index))
  }

  function updateProfile(index: number, value: string) {
    setProfiles((p) => p.map((row, i) => (i === index ? value : row)))
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setSuccess(false)
    const entries = profiles.map((v) => v.trim()).filter(Boolean)
    if (!entries.length) {
      setError('Add at least one profile username or link.')
      return
    }
    if (!state || !city) {
      setError('Please select your state and city.')
      return
    }

    setSubmitting(true)
    try {
      await submitSafetyRequest({
        profile_entries: entries.map((value) => ({ value })),
        state,
        city,
        contact_name: contactName || undefined,
        contact_email: contactEmail || undefined,
        contact_phone: contactPhone || undefined,
        message: message || undefined,
      })
      setSuccess(true)
      setProfiles([''])
      setState('')
      setCity('')
      setContactName('')
      setContactEmail('')
      setContactPhone('')
      setMessage('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Submission failed')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6 rounded-2xl border border-sky-100 bg-white p-6 shadow-sm md:p-8">
      <div>
        <h3 className="text-xl font-semibold text-sky-900">Want to be Safe</h3>
        <p className="mt-2 text-sm leading-relaxed text-slate-600">
          Leave it to us to track abusers, trollers, and offenders — keeping an eye on your social
          media profile so you can focus on what matters.
        </p>
      </div>

      <div className="space-y-3">
        <label className="block text-sm font-medium text-slate-700">
          Profile username or profile link
        </label>
        {profiles.map((value, index) => (
          <div key={index} className="flex gap-2">
            <ProfilePreviewDropdown
              value={value}
              onChange={(v) => updateProfile(index, v)}
              placeholder="e.g. @username or https://instagram.com/username"
              darkMode={false}
              inputClassName="flex-1 rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-sky-400 focus:ring-2 focus:ring-sky-100"
              className="flex-1"
              onSelect={(profile: ProfilePreviewResult) => {
                updateProfile(index, profile.profile_url || `@${profile.username}`)
              }}
            />
            {profiles.length > 1 && (
              <button
                type="button"
                onClick={() => removeProfileRow(index)}
                className="rounded-lg border border-slate-200 p-2.5 text-slate-500 hover:bg-red-50 hover:text-red-600"
                aria-label="Remove profile"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            )}
          </div>
        ))}
        {profiles.length < 10 && (
          <button
            type="button"
            onClick={addProfileRow}
            className="inline-flex items-center gap-1.5 text-sm font-medium text-sky-700 hover:text-sky-900"
          >
            <Plus className="h-4 w-4" />
            Add another profile URL
          </button>
        )}
        <p className="text-xs text-slate-500">
          One person may have multiple accounts — add Instagram, Facebook, X, or Threads links.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label htmlFor="state" className="mb-1.5 block text-sm font-medium text-slate-700">
            State / UT
          </label>
          <select
            id="state"
            value={state}
            disabled={loadingLoc}
            onChange={(e) => {
              setState(e.target.value)
              setCity('')
            }}
            required
            className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm outline-none focus:border-sky-400 focus:ring-2 focus:ring-sky-100"
          >
            <option value="">Select state</option>
            {states.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="city" className="mb-1.5 block text-sm font-medium text-slate-700">
            City
          </label>
          <select
            id="city"
            value={city}
            disabled={!state || loadingLoc}
            onChange={(e) => setCity(e.target.value)}
            required
            className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm outline-none focus:border-sky-400 focus:ring-2 focus:ring-sky-100 disabled:bg-slate-50"
          >
            <option value="">Select city</option>
            {cities.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label className="mb-1.5 block text-sm font-medium text-slate-700">Your name (optional)</label>
          <input
            type="text"
            value={contactName}
            onChange={(e) => setContactName(e.target.value)}
            className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-sky-400 focus:ring-2 focus:ring-sky-100"
          />
        </div>
        <div>
          <label className="mb-1.5 block text-sm font-medium text-slate-700">Email (optional)</label>
          <input
            type="email"
            value={contactEmail}
            onChange={(e) => setContactEmail(e.target.value)}
            className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-sky-400 focus:ring-2 focus:ring-sky-100"
          />
        </div>
      </div>

      <div>
        <label className="mb-1.5 block text-sm font-medium text-slate-700">Phone (optional)</label>
        <input
          type="tel"
          value={contactPhone}
          onChange={(e) => setContactPhone(e.target.value)}
          className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-sky-400 focus:ring-2 focus:ring-sky-100"
        />
      </div>

      <div>
        <label className="mb-1.5 block text-sm font-medium text-slate-700">Message (optional)</label>
        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          rows={3}
          className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-sky-400 focus:ring-2 focus:ring-sky-100"
          placeholder="Anything else we should know?"
        />
      </div>

      {error && (
        <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}
      {success && (
        <p className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
          Thank you. Your request was received. Our team will review your profiles shortly.
        </p>
      )}

      <button
        type="submit"
        disabled={submitting || loadingLoc}
        className="w-full rounded-xl bg-sky-600 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-sky-700 disabled:opacity-50"
      >
        {submitting ? 'Submitting…' : 'Submit — Want to be Safe'}
      </button>
    </form>
  )
}
