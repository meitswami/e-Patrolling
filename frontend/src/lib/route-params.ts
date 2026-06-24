'use client'

import { useParams, usePathname } from 'next/navigation'
import { useMemo } from 'react'

/** Build-time placeholder for Next.js static export (`generateStaticParams`). */
const STATIC_PLACEHOLDER = '_'

/**
 * Resolve a dynamic route param on static-export hosts.
 * nginx serves the `_` shell page; the real id is in the browser URL.
 */
export function useRouteParam(paramName: string, pattern: RegExp, group = 1): string {
  const params = useParams()
  const pathname = usePathname()

  return useMemo(() => {
    const fromParams = String(params[paramName] ?? '')
    if (fromParams && fromParams !== STATIC_PLACEHOLDER) {
      return decodeURIComponent(fromParams)
    }
    const match = pathname.match(pattern)
    if (match?.[group]) {
      return decodeURIComponent(match[group])
    }
    return fromParams
  }, [params, pathname, paramName, pattern, group])
}

export function useTargetIdParam(): string {
  return useRouteParam('targetId', /^\/monitoring\/target\/([^/]+)\/history\/?$/)
}

export function useLogIdParam(): string {
  return useRouteParam('id', /^\/monitoring\/log\/([^/]+)\/?$/)
}

export function useEvidenceIdParam(): string {
  return useRouteParam('id', /^\/evidence\/([^/]+)\/?$/)
}

export function useDossierUsernameParam(): string {
  return useRouteParam('username', /^\/offenders\/dossier\/([^/]+)\/?$/)
}
