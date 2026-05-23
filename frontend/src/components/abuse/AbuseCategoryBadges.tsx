import { ABUSE_CATEGORY_CONFIG } from '@/lib/constants'

interface AbuseCategoryBadgesProps {
  categories: string[]
  className?: string
}

export function AbuseCategoryBadges({ categories, className = '' }: AbuseCategoryBadgesProps) {
  if (!categories.length) return null

  return (
    <div className={`flex flex-wrap items-center gap-1.5 ${className}`}>
      <span className="rounded border border-red-500/40 bg-red-500/10 px-2 py-0.5 text-xs font-medium text-red-400">
        Abusive
      </span>
      {categories.map((key) => {
        const cfg = ABUSE_CATEGORY_CONFIG[key]
        if (!cfg) {
          return (
            <span
              key={key}
              className="rounded border border-patrol-border bg-patrol-surface px-2 py-0.5 font-mono text-xs text-patrol-muted"
            >
              {key}
            </span>
          )
        }
        return (
          <span
            key={key}
            className="rounded border px-2 py-0.5 font-mono text-xs"
            style={{ borderColor: cfg.color, color: cfg.color, backgroundColor: cfg.bg }}
            title={cfg.description}
          >
            {cfg.label}
          </span>
        )
      })}
    </div>
  )
}

export function abuseCategoriesSummary(categories: string[]): string {
  if (!categories.length) return 'abusive'
  return categories.join(' + ')
}
