'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  LayoutDashboard,
  Crosshair,
  Radio,
  ShieldAlert,
  Map,
  UserX,
  BarChart3,
  FileDown,
  Settings,
  Globe,
  type LucideIcon,
} from 'lucide-react'
import { NAV_ITEMS } from '@/lib/constants'

const ICONS: Record<string, LucideIcon> = {
  LayoutDashboard,
  Crosshair,
  Radio,
  ShieldAlert,
  Map,
  UserX,
  BarChart3,
  FileDown,
  Settings,
  Globe,
}

export function Sidebar() {
  const pathname = usePathname()

  return (
    <aside className="flex w-64 flex-col border-r border-patrol-border bg-patrol-surface">
      <div className="border-b border-patrol-border px-5 py-5">
        <div className="flex items-center gap-2">
          <span className="relative flex h-2.5 w-2.5">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-patrol-accent opacity-60" />
            <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-patrol-accent" />
          </span>
          <span className="font-mono text-lg font-bold tracking-tight text-patrol-accent">PATROL</span>
        </div>
        <p className="mt-1 text-xs text-patrol-muted">Intelligence Command</p>
      </div>

      <nav className="flex-1 space-y-0.5 p-3">
        {NAV_ITEMS.map((item) => {
          const Icon = ICONS[item.icon]
          const active = pathname === item.path
          return (
            <Link
              key={item.path}
              href={item.path}
              className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors ${
                active
                  ? 'bg-patrol-accent/10 text-patrol-accent'
                  : 'text-patrol-muted hover:bg-patrol-card hover:text-patrol-text'
              }`}
            >
              {Icon && <Icon className="h-4 w-4 shrink-0" />}
              <span className="flex-1">{item.label}</span>
              {'badge' in item && item.badge && (
                <span className="rounded bg-red-500/20 px-1.5 py-0.5 font-mono text-[10px] text-red-400">
                  {item.badge}
                </span>
              )}
            </Link>
          )
        })}
      </nav>
    </aside>
  )
}
