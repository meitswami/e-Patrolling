import type { Platform, SeverityLevel } from '@/types'

export const NAV_ITEMS = [
  { label: 'Overview', path: '/dashboard', icon: 'LayoutDashboard' as const },
  { label: 'Targets', path: '/targets', icon: 'Crosshair' as const },
  { label: 'Live Monitoring', path: '/monitoring', icon: 'Radio' as const, badge: 'LIVE' },
  { label: 'Evidence Feed', path: '/evidence', icon: 'ShieldAlert' as const },
  { label: 'Region Intel', path: '/regions', icon: 'Map' as const },
  { label: 'Offenders', path: '/offenders', icon: 'UserX' as const },
  { label: 'Analytics', path: '/analytics', icon: 'BarChart3' as const },
  { label: 'Reports', path: '/reports', icon: 'FileDown' as const },
  { label: 'Settings', path: '/settings', icon: 'Settings' as const },
]

export const SEVERITY_CONFIG: Record<SeverityLevel, { label: string; className: string }> = {
  LOW: { label: 'Low', className: 'text-blue-400 border-blue-500/40 bg-blue-500/10' },
  MEDIUM: { label: 'Medium', className: 'text-amber-400 border-amber-500/40 bg-amber-500/10' },
  HIGH: { label: 'High', className: 'text-orange-400 border-orange-500/40 bg-orange-500/10' },
  CRITICAL: { label: 'Critical', className: 'text-red-400 border-red-500/40 bg-red-500/10' },
}

export const PLATFORM_CONFIG: Record<Platform, { label: string; icon: string }> = {
  instagram: { label: 'Instagram', icon: '📷' },
  facebook: { label: 'Facebook', icon: '📘' },
  twitter: { label: 'Twitter / X', icon: '🐦' },
  threads: { label: 'Threads', icon: '🧵' },
  telegram: { label: 'Telegram', icon: '✈️' },
  whatsapp: { label: 'WhatsApp', icon: '💬' },
}

export { ACTIVE_PATROL_PLATFORMS, ROADMAP_PLATFORMS } from '@/lib/platforms'

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
export const API_PREFIX = '/api/v1'
