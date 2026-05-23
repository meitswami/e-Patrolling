'use client'

import { useEffect, useState } from 'react'
import { LogOut } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { clearSession, getUser } from '@/lib/auth'
import type { User } from '@/types'

interface HeaderProps {
  title: string
  subtitle?: string
}

export function Header({ title, subtitle }: HeaderProps) {
  const router = useRouter()
  const [mounted, setMounted] = useState(false)
  const [user, setUser] = useState<User | null>(null)

  useEffect(() => {
    setMounted(true)
    setUser(getUser())
  }, [])

  function handleLogout() {
    clearSession()
    router.push('/admin')
  }

  return (
    <header className="flex items-center justify-between border-b border-patrol-border bg-patrol-surface/80 px-6 py-4 backdrop-blur">
      <div>
        <h1 className="font-mono text-xl font-semibold text-patrol-text">{title}</h1>
        {subtitle && <p className="mt-0.5 text-sm text-patrol-muted">{subtitle}</p>}
      </div>
      <div className="flex items-center gap-4">
        {mounted && user && (
          <div className="text-right text-sm">
            <p className="font-medium text-patrol-text">{user.name}</p>
            <p className="text-xs text-patrol-muted">
              {user.role} · {user.email}
            </p>
          </div>
        )}
        <button
          type="button"
          onClick={handleLogout}
          className="flex items-center gap-2 rounded-lg border border-patrol-border px-3 py-2 text-sm text-patrol-muted transition hover:border-red-500/40 hover:text-red-400"
        >
          <LogOut className="h-4 w-4" />
          Sign out
        </button>
      </div>
    </header>
  )
}
