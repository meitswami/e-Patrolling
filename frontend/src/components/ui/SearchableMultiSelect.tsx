'use client'

import { useEffect, useRef, useState } from 'react'

interface SearchableMultiSelectProps {
  options: string[]
  selected: string[]
  onChange: (selected: string[]) => void
  placeholder?: string
  label?: string
}

export function SearchableMultiSelect({
  options,
  selected,
  onChange,
  placeholder = 'Search...',
  label,
}: SearchableMultiSelectProps) {
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const filtered = options.filter(
    (opt) =>
      opt.toLowerCase().includes(query.toLowerCase()) && !selected.includes(opt)
  )

  function handleSelect(option: string) {
    onChange([...selected, option])
    setQuery('')
  }

  function handleRemove(option: string) {
    onChange(selected.filter((s) => s !== option))
  }

  return (
    <div ref={containerRef} className="relative w-full">
      {label && (
        <label className="mb-1 block text-xs font-medium text-patrol-muted">
          {label}
        </label>
      )}

      {/* Selected chips */}
      {selected.length > 0 && (
        <div className="mb-1.5 flex flex-wrap gap-1">
          {selected.map((item) => (
            <span
              key={item}
              className="inline-flex items-center gap-1 rounded-md border border-patrol-accent/30 bg-patrol-accent/10 px-2 py-0.5 text-[11px] text-patrol-accent"
            >
              {item}
              <button
                type="button"
                onClick={() => handleRemove(item)}
                className="ml-0.5 text-patrol-accent/70 hover:text-patrol-accent"
              >
                &times;
              </button>
            </span>
          ))}
        </div>
      )}

      {/* Search input */}
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onFocus={() => setOpen(true)}
        placeholder={placeholder}
        className="w-full rounded-lg border border-patrol-border bg-patrol-surface px-3 py-1.5 text-sm text-patrol-text placeholder:text-patrol-muted/60 focus:border-patrol-accent/50 focus:outline-none"
      />

      {/* Dropdown */}
      {open && filtered.length > 0 && (
        <div className="absolute z-50 mt-1 max-h-48 w-full overflow-y-auto rounded-lg border border-patrol-border bg-patrol-card shadow-lg">
          {filtered.slice(0, 50).map((option) => (
            <button
              key={option}
              type="button"
              onClick={() => handleSelect(option)}
              className="block w-full px-3 py-1.5 text-left text-sm text-patrol-text hover:bg-patrol-accent/10 hover:text-patrol-accent"
            >
              {option}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
