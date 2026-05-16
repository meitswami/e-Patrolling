import { API_BASE_URL, API_PREFIX } from '@/lib/constants'
import { getToken, clearSession } from '@/lib/auth'
import type {
  DashboardStats,
  EvidenceListItem,
  HealthResponse,
  LoginRequest,
  PaginatedResponse,
  Platform,
  TargetAccount,
  TokenResponse,
  User,
} from '@/types'

/** Turn FastAPI error JSON into a readable string. */
export function parseApiError(body: unknown, fallback: string): string {
  if (!body || typeof body !== 'object') return fallback
  const record = body as Record<string, unknown>

  if (typeof record.detail === 'string') return record.detail
  if (typeof record.error === 'string') return record.error

  if (Array.isArray(record.detail)) {
    const parts = record.detail.map((item) => {
      if (typeof item === 'string') return item
      if (item && typeof item === 'object' && 'msg' in item) {
        const entry = item as { msg: string; loc?: unknown[] }
        const field = Array.isArray(entry.loc)
          ? entry.loc.filter((x) => x !== 'body').join('.')
          : ''
        return field ? `${field}: ${entry.msg}` : entry.msg
      }
      return JSON.stringify(item)
    })
    return parts.join(' · ') || fallback
  }

  if (record.detail && typeof record.detail === 'object') {
    return JSON.stringify(record.detail)
  }

  return fallback
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  auth = false,
): Promise<T> {
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  }

  if (auth) {
    const token = getToken()
    if (token) {
      ;(headers as Record<string, string>)['Authorization'] = `Bearer ${token}`
    }
  }

  let res: Response
  try {
    res = await fetch(`${API_BASE_URL}${API_PREFIX}${path}`, {
      ...options,
      headers,
    })
  } catch {
    throw new Error(
      `Cannot reach API at ${API_BASE_URL}. Start the backend: cd backend && uvicorn main:app --reload`,
    )
  }

  if (res.status === 401 && auth) {
    clearSession()
    if (typeof window !== 'undefined') {
      window.location.href = '/login'
    }
  }

  if (!res.ok) {
    let body: unknown = null
    try {
      body = await res.json()
    } catch {
      /* ignore */
    }
    throw new Error(parseApiError(body, `Request failed (${res.status})`))
  }

  return res.json() as Promise<T>
}

export async function login(body: LoginRequest): Promise<TokenResponse> {
  return request<TokenResponse>('/auth/login', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function getMe(): Promise<User> {
  return request<User>('/auth/me', {}, true)
}

export async function getDashboardStats(): Promise<DashboardStats> {
  return request<DashboardStats>('/analytics/dashboard', {}, true)
}

export async function listEvidence(
  page = 1,
  pageSize = 20,
): Promise<PaginatedResponse<EvidenceListItem>> {
  return request<PaginatedResponse<EvidenceListItem>>(
    `/evidence?page=${page}&page_size=${pageSize}`,
    {},
    true,
  )
}

export async function listTargets(
  page = 1,
  pageSize = 50,
): Promise<PaginatedResponse<TargetAccount>> {
  return request<PaginatedResponse<TargetAccount>>(
    `/targets?page=${page}&page_size=${pageSize}`,
    {},
    true,
  )
}

export interface CreateTargetPayload {
  username: string
  display_name?: string
  platform: Platform
  profile_url: string
  monitoring_enabled?: boolean
  notes?: string
}

export async function createTarget(body: CreateTargetPayload): Promise<TargetAccount> {
  return request<TargetAccount>(
    '/targets',
    { method: 'POST', body: JSON.stringify(body) },
    true,
  )
}

export async function getHealth(): Promise<HealthResponse> {
  let res: Response
  try {
    res = await fetch(`${API_BASE_URL}/health`)
  } catch {
    throw new Error('API unreachable')
  }
  if (!res.ok) throw new Error('API unreachable')
  return res.json() as Promise<HealthResponse>
}
