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

// Group nav items by section
const SECTIONS = [
  { label: 'Command', items: ['Overview', 'Targets', 'Website Intake'] },
  { label: 'Intelligence', items: ['Live Monitoring', 'Evidence Feed', 'Region Intel', 'Offenders'] },
  { label: 'Analysis', items: ['Analytics', 'Reports', 'Settings'] },
]

export function Sidebar() {
  const pathname = usePathname()

  return (
    <aside className="flex w-64 flex-col border-r border-patrol-border bg-gradient-to-b from-patrol-surface to-patrol-bg">
      {/* Logo */}
      <div className="border-b border-patrol-border/60 px-5 py-5">
        <div className="flex items-center gap-2.5">
          <span className="relative flex h-2.5 w-2.5">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-patrol-accent opacity-50" />
            <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-patrol-accent shadow-glow-sm" />
          </span>
          <span className="font-mono text-lg font-bold tracking-tight text-patrol-accent drop-shadow-[0_0_8px_rgba(0,230,118,0.3)]">
            शक्ति - SHAKTI
          </span>
        </div>
        <p className="mt-1 text-[11px] font-medium tracking-wider text-patrol-muted-dim uppercase">
          The Third Eye
        </p>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-3 py-4">
        {SECTIONS.map((section) => (
          <div key={section.label} className="mb-4">
            <p className="mb-1.5 px-3 text-[10px] font-semibold uppercase tracking-widest text-patrol-muted-dim">
              {section.label}
            </p>
            {NAV_ITEMS.filter((item) => section.items.includes(item.label)).map((item) => {
              const Icon = ICONS[item.icon]
              const active = pathname === item.path
              return (
                <Link
                  key={item.path}
                  href={item.path}
                  className={`group flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-all duration-150 ${
                    active
                      ? 'bg-patrol-accent/10 text-patrol-accent shadow-glow-sm'
                      : 'text-patrol-muted hover:bg-patrol-card hover:text-patrol-text'
                  }`}
                >
                  {Icon && (
                    <Icon
                      className={`h-4 w-4 shrink-0 transition-colors ${
                        active ? 'text-patrol-accent' : 'text-patrol-muted-dim group-hover:text-patrol-muted'
                      }`}
                    />
                  )}
                  <span className="flex-1 font-medium">{item.label}</span>
                  {'badge' in item && item.badge && (
                    <span className="rounded-full bg-patrol-danger/20 px-1.5 py-0.5 font-mono text-[9px] font-bold text-patrol-danger">
                      {item.badge}
                    </span>
                  )}
                </Link>
              )
            })}
          </div>
        ))}
      </nav>

      {/* Footer */}
      <div className="border-t border-patrol-border/40 px-5 py-3">
        <p className="text-[10px] text-patrol-muted-dim">
          SHAKTI v1.0.0-MVP
        </p>
        <p className="text-[10px] text-patrol-muted-dim">
          AI-Powered Women Safety Platform
        </p>
      </div>
    </aside>
  )
}
