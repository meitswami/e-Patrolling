/** Format seconds as "00 D 03H 42M 13S". */
export function formatDuration(totalSeconds: number | null | undefined): string {
  if (totalSeconds == null || totalSeconds < 0 || Number.isNaN(totalSeconds)) {
    return '00 D 00H 00M 00S'
  }
  const secs = Math.round(totalSeconds)
  const days = Math.floor(secs / 86400)
  const hours = Math.floor((secs % 86400) / 3600)
  const minutes = Math.floor((secs % 3600) / 60)
  const seconds = secs % 60
  return `${String(days).padStart(2, '0')} D ${String(hours).padStart(2, '0')}H ${String(minutes).padStart(2, '0')}M ${String(seconds).padStart(2, '0')}S`
}

export function durationFromTimestamps(
  startedAt: string | null | undefined,
  completedAt: string | null | undefined,
  durationSeconds?: number | null,
): string {
  if (durationSeconds != null && durationSeconds >= 0) {
    return formatDuration(durationSeconds)
  }
  if (startedAt && completedAt) {
    const start = new Date(startedAt).getTime()
    const end = new Date(completedAt).getTime()
    if (!Number.isNaN(start) && !Number.isNaN(end) && end >= start) {
      return formatDuration((end - start) / 1000)
    }
  }
  return '00 D 00H 00M 00S'
}

export function formatCrawlTimestamp(
  startedAt: string,
  completedAt: string | null,
  durationSeconds?: number | null,
): string {
  const start = new Date(startedAt)
  if (Number.isNaN(start.getTime())) return startedAt
  const datePart = start.toLocaleDateString(undefined, {
    weekday: 'short',
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
  const timePart = start.toLocaleTimeString(undefined, {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
  const duration = durationFromTimestamps(startedAt, completedAt, durationSeconds)
  return `${datePart} · ${timePart} · ${duration}`
}
