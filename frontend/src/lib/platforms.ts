import type { Platform } from '@/types'

/** Platforms with working crawlers in this release */
export const ACTIVE_PATROL_PLATFORMS: Platform[] = [
  'instagram',
  'facebook',
  'twitter',
  'threads',
]

export const ROADMAP_PLATFORMS = [
  { id: 'linkedin', label: 'LinkedIn' },
  { id: 'telegram', label: 'Telegram' },
  { id: 'whatsapp', label: 'WhatsApp' },
  { id: 'signal', label: 'Signal' },
  { id: 'threema', label: 'Threema' },
] as const

export function isPatrolPlatform(platform: string): boolean {
  return (ACTIVE_PATROL_PLATFORMS as readonly string[]).includes(platform)
}
