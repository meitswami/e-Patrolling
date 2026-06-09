'use client'

import { useEffect, useRef, useState } from 'react'
import { Loader2 } from 'lucide-react'
import { previewProfile, type ProfilePreviewResult } from '@/lib/api'

interface Props {
  value: string
  onChange: (value: string) => void
  onSelect?: (profile: ProfilePreviewResult) => void
  platform?: string
  placeholder?: string
  className?: string
  inputClassName?: string
  darkMode?: boolean
}

export function ProfilePreviewDropdown({
  value,
  onChange,
  onSelect,
  platform,
  placeholder = 'e.g. @username or https://instagram.com/username',
  className = '',
  inputClassName = '',
  darkMode = true,
}: Props) {
  const [results, setResults] = useState<ProfilePreviewResult[]>([])
  const [loading, setLoading] = useState(false)
  const [showDropdown, setShowDropdown] = useState(false)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current)

    const query = value.trim().replace(/^@/, '')
    if (query.length < 2) {
      setResults([])
      setShowDropdown(false)
      return
    }

    debounceRef.current = setTimeout(async () => {
      setLoading(true)
      try {
        const data = await previewProfile(query, platform)
        setResults(data)
        setShowDropdown(data.length > 0)
      } catch {
        setResults([])
        setShowDropdown(false)
      } finally {
        setLoading(false)
      }
    }, 500)

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  }, [value, platform])

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setShowDropdown(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  function handleSelect(profile: ProfilePreviewResult) {
    setShowDropdown(false)
    onSelect?.(profile)
  }

  const baseInputClass = darkMode
    ? 'w-full rounded-lg border border-patrol-border bg-patrol-surface px-3 py-2 text-patrol-text'
    : 'w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-sky-400 focus:ring-2 focus:ring-sky-100'

  const dropdownBg = darkMode ? 'bg-patrol-card border-patrol-border' : 'bg-white border-slate-200'
  const itemHover = darkMode ? 'hover:bg-patrol-surface' : 'hover:bg-sky-50'
  const textPrimary = darkMode ? 'text-patrol-text' : 'text-slate-900'
  const textSecondary = darkMode ? 'text-patrol-muted' : 'text-slate-500'

  return (
    <div ref={containerRef} className={`relative ${className}`}>
      <div className="relative">
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onFocus={() => results.length > 0 && setShowDropdown(true)}
          placeholder={placeholder}
          className={inputClassName || baseInputClass}
        />
        {loading && (
          <div className="absolute right-3 top-1/2 -translate-y-1/2">
            <Loader2 className={`h-4 w-4 animate-spin ${darkMode ? 'text-patrol-muted' : 'text-slate-400'}`} />
          </div>
        )}
      </div>

      {showDropdown && results.length > 0 && (
        <div className={`absolute z-50 mt-1 w-full rounded-lg border shadow-lg ${dropdownBg} max-h-80 overflow-y-auto`}>
          {results.map((profile) => (
            <button
              key={`${profile.platform}-${profile.username}`}
              type="button"
              onClick={() => handleSelect(profile)}
              className={`w-full px-3 py-3 text-left transition ${itemHover} border-b last:border-b-0 ${darkMode ? 'border-patrol-border/50' : 'border-slate-100'}`}
            >
              <div className="flex items-start gap-3">
                {/* Avatar */}
                <div className={`h-10 w-10 shrink-0 rounded-full ${darkMode ? 'bg-patrol-surface' : 'bg-slate-100'} flex items-center justify-center overflow-hidden`}>
                  {profile.avatar_url ? (
                    <img
                      src={profile.avatar_url}
                      alt={profile.username}
                      className="h-full w-full object-cover"
                    />
                  ) : (
                    <span className={`text-lg font-bold ${darkMode ? 'text-patrol-accent' : 'text-sky-600'}`}>
                      {profile.username.charAt(0).toUpperCase()}
                    </span>
                  )}
                </div>

                {/* Info */}
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-1.5">
                    <span className={`font-medium truncate ${textPrimary}`}>
                      {profile.display_name || profile.username}
                    </span>
                    {profile.is_verified && (
                      <svg className="h-4 w-4 shrink-0 text-blue-500" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    )}
                  </div>
                  <p className={`text-xs ${textSecondary}`}>@{profile.username}</p>
                  {profile.bio && (
                    <p className={`mt-1 text-xs truncate ${textSecondary}`}>{profile.bio}</p>
                  )}
                  <div className={`mt-1 flex items-center gap-3 text-[10px] ${textSecondary}`}>
                    {profile.follower_count != null && (
                      <span>{profile.follower_count.toLocaleString()} followers</span>
                    )}
                    {profile.platform && (
                      <span className="capitalize">{profile.platform}</span>
                    )}
                  </div>
                </div>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
