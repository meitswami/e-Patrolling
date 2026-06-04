'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { BadgeCheck, Lock, Loader2, User, AlertCircle } from 'lucide-react'
import { fetchProfilePreview, type ProfilePreviewData } from '@/lib/api'

interface ProfilePreviewDropdownProps {
  /** Current input value */
  value: string
  /** Called when input value changes */
  onChange: (value: string) => void
  /** Called when a profile is selected from the preview dropdown */
  onProfileSelect?: (profile: ProfilePreviewData) => void
  /** Input placeholder */
  placeholder?: string
  /** Style variant: 'light' for public site, 'dark' for admin panel */
  variant?: 'light' | 'dark'
  /** Additional className for the outer wrapper */
  className?: string
  /** Additional className for the input element */
  inputClassName?: string
}

function formatCount(n: number | null | undefined): string {
  if (n == null) return '-'
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`
  return n.toLocaleString()
}

export function ProfilePreviewDropdown({
  value,
  onChange,
  onProfileSelect,
  placeholder = 'e.g. @username or https://instagram.com/username',
  variant = 'light',
  className = '',
  inputClassName = '',
}: ProfilePreviewDropdownProps) {
  const [preview, setPreview] = useState<ProfilePreviewData | null>(null)
  const [loading, setLoading] = useState(false)
  const [showDropdown, setShowDropdown] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // Debounced fetch when input changes
  const fetchPreview = useCallback((query: string) => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current)
    }

    const trimmed = query.trim()
    if (!trimmed || trimmed.length < 2) {
      setPreview(null)
      setShowDropdown(false)
      setError(null)
      setLoading(false)
      return
    }

    setLoading(true)
    setError(null)

    debounceRef.current = setTimeout(async () => {
      try {
        const data = await fetchProfilePreview(trimmed)
        setPreview(data)
        setShowDropdown(true)
        if (!data.found && data.error) {
          setError(data.error)
        } else {
          setError(null)
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Lookup failed')
        setPreview(null)
        setShowDropdown(false)
      } finally {
        setLoading(false)
      }
    }, 600)
  }, [])

  useEffect(() => {
    fetchPreview(value)
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  }, [value, fetchPreview])

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setShowDropdown(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  function handleSelect(profile: ProfilePreviewData) {
    setShowDropdown(false)
    onProfileSelect?.(profile)
  }

  const isLight = variant === 'light'

  // Base input styles per variant
  const baseInputClass = isLight
    ? 'w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-sky-400 focus:ring-2 focus:ring-sky-100'
    : 'w-full rounded-lg border border-patrol-border bg-patrol-surface px-3 py-2 text-patrol-text'

  // Dropdown card styles per variant
  const dropdownClass = isLight
    ? 'absolute z-50 mt-1 w-full rounded-xl border border-slate-200 bg-white shadow-lg overflow-hidden'
    : 'absolute z-50 mt-1 w-full rounded-xl border border-patrol-border bg-patrol-card shadow-lg overflow-hidden'

  return (
    <div ref={containerRef} className={`relative ${className}`}>
      <div className="relative">
        <input
          ref={inputRef}
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onFocus={() => {
            if (preview?.found) setShowDropdown(true)
          }}
          placeholder={placeholder}
          className={`${baseInputClass} ${inputClassName} pr-8`}
        />
        {loading && (
          <div className="absolute right-2.5 top-1/2 -translate-y-1/2">
            <Loader2 className={`h-4 w-4 animate-spin ${isLight ? 'text-sky-500' : 'text-patrol-accent'}`} />
          </div>
        )}
      </div>

      {/* Dropdown Preview Card */}
      {showDropdown && preview && preview.found && (
        <div className={dropdownClass}>
          <button
            type="button"
            onClick={() => handleSelect(preview)}
            className={`w-full p-4 text-left transition ${
              isLight
                ? 'hover:bg-sky-50 focus:bg-sky-50'
                : 'hover:bg-patrol-surface focus:bg-patrol-surface'
            }`}
          >
            {/* Profile Header */}
            <div className="flex items-start gap-3">
              {/* Avatar */}
              <div className="relative h-14 w-14 flex-shrink-0 overflow-hidden rounded-full border-2 border-slate-100">
                {preview.avatar_url ? (
                  <img
                    src={preview.avatar_url}
                    alt={preview.username}
                    className="h-full w-full object-cover"
                    referrerPolicy="no-referrer"
                  />
                ) : (
                  <div className={`flex h-full w-full items-center justify-center ${isLight ? 'bg-slate-100' : 'bg-patrol-surface'}`}>
                    <User className={`h-6 w-6 ${isLight ? 'text-slate-400' : 'text-patrol-muted'}`} />
                  </div>
                )}
              </div>

              {/* Name & Username */}
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-1.5">
                  <span className={`truncate font-semibold ${isLight ? 'text-slate-900' : 'text-patrol-text'}`}>
                    {preview.full_name || preview.username}
                  </span>
                  {preview.is_verified && (
                    <BadgeCheck className="h-4 w-4 flex-shrink-0 text-blue-500" />
                  )}
                  {preview.is_private && (
                    <Lock className={`h-3.5 w-3.5 flex-shrink-0 ${isLight ? 'text-slate-400' : 'text-patrol-muted'}`} />
                  )}
                </div>
                <p className={`text-sm ${isLight ? 'text-slate-500' : 'text-patrol-muted'}`}>
                  @{preview.username}
                  <span className="mx-1.5">·</span>
                  <span className="capitalize">{preview.platform}</span>
                </p>
              </div>
            </div>

            {/* Stats Row */}
            <div className={`mt-3 flex gap-4 border-t pt-3 text-xs ${
              isLight ? 'border-slate-100' : 'border-patrol-border'
            }`}>
              <div className="text-center">
                <p className={`font-bold ${isLight ? 'text-slate-900' : 'text-patrol-text'}`}>
                  {formatCount(preview.posts_count)}
                </p>
                <p className={isLight ? 'text-slate-500' : 'text-patrol-muted'}>Posts</p>
              </div>
              <div className="text-center">
                <p className={`font-bold ${isLight ? 'text-slate-900' : 'text-patrol-text'}`}>
                  {formatCount(preview.followers)}
                </p>
                <p className={isLight ? 'text-slate-500' : 'text-patrol-muted'}>Followers</p>
              </div>
              <div className="text-center">
                <p className={`font-bold ${isLight ? 'text-slate-900' : 'text-patrol-text'}`}>
                  {formatCount(preview.following)}
                </p>
                <p className={isLight ? 'text-slate-500' : 'text-patrol-muted'}>Following</p>
              </div>
            </div>

            {/* Bio */}
            {preview.bio && (
              <p className={`mt-2 line-clamp-2 text-xs leading-relaxed ${
                isLight ? 'text-slate-600' : 'text-patrol-muted'
              }`}>
                {preview.bio}
              </p>
            )}

            {/* Click hint */}
            <p className={`mt-2 text-center text-[10px] ${
              isLight ? 'text-sky-600' : 'text-patrol-accent'
            }`}>
              Click to select this profile
            </p>
          </button>
        </div>
      )}

      {/* Error state in dropdown */}
      {showDropdown && preview && !preview.found && error && (
        <div className={dropdownClass}>
          <div className="flex items-center gap-2 p-3">
            <AlertCircle className={`h-4 w-4 flex-shrink-0 ${isLight ? 'text-amber-500' : 'text-amber-400'}`} />
            <p className={`text-xs ${isLight ? 'text-slate-600' : 'text-patrol-muted'}`}>
              {error}
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
