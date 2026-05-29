export function Skeleton({ className = '' }: { className?: string }) {
  return (
    <div
      className={`rounded-lg animate-shimmer ${className}`}
      aria-hidden="true"
    />
  )
}

export function CardSkeleton() {
  return (
    <div className="rounded-xl border border-patrol-border bg-patrol-card p-5">
      <Skeleton className="h-3 w-24 mb-3" />
      <Skeleton className="h-8 w-16" />
    </div>
  )
}

export function StatGridSkeleton({ count = 4 }: { count?: number }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {Array.from({ length: count }).map((_, i) => (
        <CardSkeleton key={i} />
      ))}
    </div>
  )
}

export function ListSkeleton({ rows = 3 }: { rows?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="rounded-xl border border-patrol-border bg-patrol-card p-4">
          <Skeleton className="h-4 w-48 mb-2" />
          <Skeleton className="h-3 w-full" />
          <Skeleton className="h-3 w-3/4 mt-1" />
        </div>
      ))}
    </div>
  )
}
