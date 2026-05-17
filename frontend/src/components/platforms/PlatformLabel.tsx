import { PLATFORM_CONFIG } from '@/lib/constants'
import type { Platform } from '@/types'
import { PlatformIcon } from './PlatformIcon'

type PlatformLabelProps = {
  platform: string
  size?: 'sm' | 'md' | 'lg'
  showLabel?: boolean
  className?: string
}

export function getPlatformLabel(platform: string): string {
  const cfg = PLATFORM_CONFIG[platform as Platform]
  if (cfg) return cfg.label
  return platform.charAt(0).toUpperCase() + platform.slice(1)
}

export function PlatformLabel({
  platform,
  size = 'sm',
  showLabel = true,
  className,
}: PlatformLabelProps) {
  return (
    <span className={`inline-flex items-center gap-1.5 ${className ?? ''}`}>
      <PlatformIcon platform={platform} size={size} />
      {showLabel && <span>{getPlatformLabel(platform)}</span>}
    </span>
  )
}
