export interface AbuseExplanationItem {
  kind: 'phrase' | 'term' | 'category' | string
  title: string
  meaning_en: string
  offender_implication: string
  related_categories?: string[]
}

interface AbuseExplanationPanelProps {
  explanations: AbuseExplanationItem[]
  className?: string
}

const KIND_LABEL: Record<string, string> = {
  phrase: 'Phrase',
  term: 'Term',
  category: 'Category',
}

export function AbuseExplanationPanel({
  explanations,
  className = '',
}: AbuseExplanationPanelProps) {
  if (!explanations.length) return null

  return (
    <div
      className={`mt-3 space-y-3 rounded-lg border border-patrol-border/80 bg-patrol-surface/60 p-3 ${className}`}
    >
      <p className="text-xs font-semibold uppercase tracking-wide text-patrol-muted">
        What this means (context for investigators)
      </p>
      {explanations.map((ex, idx) => (
        <div
          key={`${ex.kind}-${ex.title}-${idx}`}
          className="border-l-2 border-patrol-accent/50 pl-3 text-sm"
        >
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-bold text-patrol-text">{ex.title}</span>
            <span className="rounded bg-patrol-bg/80 px-1.5 py-0.5 text-[10px] uppercase text-patrol-muted">
              {KIND_LABEL[ex.kind] ?? ex.kind}
            </span>
          </div>
          <p className="mt-1.5 leading-relaxed text-patrol-muted">
            <span className="font-medium text-patrol-text">Meaning: </span>
            {ex.meaning_en}
          </p>
          <p className="mt-1.5 leading-relaxed text-orange-200/90">
            <span className="font-medium text-orange-300">What the offender implies: </span>
            {ex.offender_implication}
          </p>
        </div>
      ))}
    </div>
  )
}
