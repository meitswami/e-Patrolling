interface AbusiveCommentTextProps {
  text: string
  /** Comment flagged as abusive (evidence / classifier). */
  abusive?: boolean
  /** Matched lexicon / keyword rules (stronger highlight). */
  lexiconMatch?: boolean
  className?: string
  lineClamp?: boolean
}

/**
 * Renders comment body with bold styling for abusive content;
 * lexicon hits get an extra accent so they stand out in the feed.
 */
export function AbusiveCommentText({
  text,
  abusive = false,
  lexiconMatch = false,
  className = '',
  lineClamp = false,
}: AbusiveCommentTextProps) {
  const highlight = abusive || lexiconMatch

  let tone = 'text-patrol-text'
  if (lexiconMatch) {
    tone = 'text-red-300'
  } else if (abusive) {
    tone = 'text-orange-100'
  }

  return (
    <p
      className={[
        'text-sm leading-relaxed',
        lineClamp ? 'line-clamp-3' : '',
        highlight ? 'font-bold' : 'font-normal',
        lexiconMatch ? 'border-l-2 border-red-500/70 bg-red-500/5 pl-3' : '',
        tone,
        className,
      ]
        .filter(Boolean)
        .join(' ')}
    >
      {text}
    </p>
  )
}
