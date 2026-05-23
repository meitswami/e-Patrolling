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

/** Abuse type labels — match backend lexicon / classifier (sexual_harassment, hate_speech, …). */
export const ABUSE_CATEGORY_CONFIG: Record<
  string,
  { label: string; color: string; bg: string; description: string }
> = {
  sexual_harassment: {
    label: 'sexual_harassment',
    color: '#f472b6',
    bg: 'rgba(244, 114, 182, 0.12)',
    description:
      'Unwanted sexual comments or solicitation — treats the target as a sexual object, not a person to respect.',
  },
  rape_threat: {
    label: 'rape_threat',
    color: '#ef4444',
    bg: 'rgba(239, 68, 68, 0.12)',
    description: 'Rape or sexual violence threat',
  },
  hate_speech: {
    label: 'hate_speech',
    color: '#fb923c',
    bg: 'rgba(251, 146, 60, 0.12)',
    description:
      'Hindi/Hinglish slurs (e.g. bc = behenchod, bsdk, mc) — meant to demean, shock, and provoke, not to argue fairly.',
  },
  threat: {
    label: 'threat',
    color: '#f87171',
    bg: 'rgba(248, 113, 113, 0.12)',
    description: 'Threat of harm or violence',
  },
  stalking: {
    label: 'stalking',
    color: '#a78bfa',
    bg: 'rgba(167, 139, 250, 0.12)',
    description: 'Stalking or persistent harassment',
  },
  bullying: {
    label: 'bullying',
    color: '#fbbf24',
    bg: 'rgba(251, 191, 36, 0.12)',
    description:
      'Shaming or “fake” call-outs — attacks credibility and reputation, often combined with slurs (e.g. fake bc).',
  },
}

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

/** Build API URL; avoids double /api/v1 when NEXT_PUBLIC_API_URL already includes it. */
export function buildApiUrl(path: string): string {
  const base = API_BASE_URL.replace(/\/$/, '')
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  if (base.endsWith('/api/v1')) {
    return `${base}${normalizedPath}`
  }
  return `${base}${API_PREFIX}${normalizedPath}`
}
