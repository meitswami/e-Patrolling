'use client'

import { useEffect, useState } from 'react'

/** Renders children only after mount — avoids SSR/hydration mismatches for browser-only UI. */
export function ClientOnly({
  children,
  fallback = null,
}: {
  children: React.ReactNode
  fallback?: React.ReactNode
}) {
  const [mounted, setMounted] = useState(false)
  useEffect(() => setMounted(true), [])
  if (!mounted) return <>{fallback}</>
  return <>{children}</>
}
