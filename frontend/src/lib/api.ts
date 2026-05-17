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

  if (res.status === 204) {
    return undefined as T
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

export interface EvidenceDetail extends EvidenceListItem {
  post_url: string | null
  comment_timestamp: string | null
  notes: string | null
  escalated_at: string | null
  target_id: string | null
  accused_id: string | null
}

export async function getEvidence(evidenceId: string): Promise<EvidenceDetail> {
  return request<EvidenceDetail>(`/evidence/${evidenceId}`, {}, true)
}

export async function listEvidence(
  page = 1,
  pageSize = 20,
  filters?: {
    search?: string
    severity?: string
    platform?: string
    is_escalated?: boolean
  },
): Promise<PaginatedResponse<EvidenceListItem>> {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  })
  if (filters?.search) params.set('search', filters.search)
  if (filters?.severity) params.set('severity', filters.severity)
  if (filters?.platform) params.set('platform', filters.platform)
  if (filters?.is_escalated !== undefined) {
    params.set('is_escalated', String(filters.is_escalated))
  }
  return request<PaginatedResponse<EvidenceListItem>>(
    `/evidence?${params.toString()}`,
    {},
    true,
  )
}

export async function escalateEvidence(
  evidenceId: string,
  notes?: string,
): Promise<{ is_escalated: boolean; escalated_at: string }> {
  return request(`/evidence/${evidenceId}/escalate`, {
    method: 'POST',
    body: JSON.stringify({ notes: notes || null }),
  }, true)
}

export async function deleteEvidence(evidenceId: string): Promise<void> {
  await request(`/evidence/${evidenceId}`, { method: 'DELETE' }, true)
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

export interface PlatformPatrolInfo {
  id: string
  label: string
  status: 'active' | 'roadmap'
  patrol_enabled: boolean
  target_count: number
  monitoring_count: number
}

export interface CrawlerStatus {
  supported_platforms: string[]
  platforms: PlatformPatrolInfo[]
  redis_enabled: boolean
  scheduler_enabled: boolean
  crawl_interval_seconds: number
  demo_mode: boolean
  scheduler_is_running?: boolean
  scheduler_last_run_at?: string | null
  scheduler_last_run_status?: string | null
  scheduler_last_run_message?: string | null
  evidence_screenshot_mode?: string
  crawl_stop_requested?: boolean
  recent_errors?: { platform: string; error_message: string | null; started_at: string | null }[]
  last_export_at?: string | null
  last_export_path?: string | null
}

export interface CrawlLogItem {
  id: string
  target_id: string | null
  platform: string
  comments_found: number
  comments_new: number
  abusive_detected: number
  critical_detected: number
  success: boolean
  error_message: string | null
  duration_seconds: number | null
  started_at: string
  completed_at: string | null
}

export interface CrawlResultSummary {
  target_id: string
  target_username?: string
  platform?: string
  success: boolean
  comments_new: number
  abusive_detected: number
  critical_detected?: number
  error?: string
}

export async function getCrawlerStatus(): Promise<CrawlerStatus> {
  return request<CrawlerStatus>('/crawlers/status', {}, true)
}

export async function listCrawlLogs(limit = 20): Promise<CrawlLogItem[]> {
  return request<CrawlLogItem[]>(`/crawlers/logs?limit=${limit}`, {}, true)
}

export async function runCrawlAll(): Promise<CrawlResultSummary[]> {
  return request<CrawlResultSummary[]>('/crawlers/run-all', { method: 'POST' }, true)
}

export async function stopCrawlAll(): Promise<{ status: string; message: string }> {
  return request<{ status: string; message: string }>('/crawlers/stop', { method: 'POST' }, true)
}

export async function runCrawlTarget(targetId: string): Promise<CrawlResultSummary> {
  return request<CrawlResultSummary>(`/crawlers/run/${targetId}`, { method: 'POST' }, true)
}

export interface OffenderListItem {
  id: string
  accused_id: string
  username: string
  platform: Platform
  total_offenses: number
  critical_count: number
  priority_score: number
  status: string
  last_offense_at: string | null
}

export interface AnalyticsOverview {
  dashboard: DashboardStats
  by_severity: { LOW: number; MEDIUM: number; HIGH: number; CRITICAL: number }
  by_platform: { platform: string; count: number }[]
}

export interface RegionSummary {
  region: string
  target_count: number
  accused_count: number
  evidence_count?: number
  critical_evidence?: number
  avg_confidence: number
}

export async function getAnalyticsOverview(): Promise<AnalyticsOverview> {
  return request<AnalyticsOverview>('/analytics/overview', {}, true)
}

export async function listRegions(): Promise<RegionSummary[]> {
  return request<RegionSummary[]>('/regions/summary', {}, true)
}

export async function listOffenders(
  page = 1,
  pageSize = 20,
): Promise<PaginatedResponse<OffenderListItem>> {
  return request<PaginatedResponse<OffenderListItem>>(
    `/offenders?page=${page}&page_size=${pageSize}`,
    {},
    true,
  )
}

export interface AccusedProfileItem {
  id: string
  platform: Platform
  username: string
  display_name: string | null
  profile_url: string
  total_incidents: number
  critical_count: number
  high_count: number
  max_risk_score: number
  status: string
  last_seen_at: string | null
}

export interface AccusedDossier {
  username: string
  generated_at: string
  platform_count: number
  platforms: string[]
  profiles: {
    id: string
    platform: string
    username: string
    profile_url: string
    total_incidents: number
    critical_count: number
    max_risk_score: number
    status: string
  }[]
  summary: {
    total_evidence: number
    severity_breakdown: Record<string, number>
    evidence_by_platform: Record<string, number>
    targets_affected: string[]
    targets_affected_count: number
    max_risk_score: number
    composite_risk_score: number
    escalated_count: number
    total_incidents_reported: number
  }
  osint?: OsintReport | null
  affected_posts?: {
    post_url: string | null
    post_id: string | null
    platform: string
    evidence_on_post: number
  }[]
  evidence: {
    evidence_id: string
    platform: string
    severity: string
    risk_score: number
    target_username: string | null
    comment_text: string
    comment_posted_at: string | null
    evidence_captured_at: string | null
    post_url: string | null
    comment_url: string | null
    direct_comment_link: string | null
    post_id: string | null
    comment_id: string | null
    screenshot_path: string | null
    screenshot_hash: string | null
    is_escalated: boolean
    deletion_resilient?: boolean
  }[]
}

export async function searchAccusedProfiles(username: string): Promise<AccusedProfileItem[]> {
  const q = encodeURIComponent(username.replace(/^@/, ''))
  return request<AccusedProfileItem[]>(`/offenders/search?username=${q}`, {}, true)
}

export async function getAccusedDossier(
  username: string,
  runOsint = false,
): Promise<AccusedDossier> {
  const q = encodeURIComponent(username.replace(/^@/, ''))
  return request<AccusedDossier>(
    `/offenders/dossier/${q}${runOsint ? '?run_osint=true' : ''}`,
    {},
    true,
  )
}

export interface OsintReport {
  username: string
  generated_at: string
  seed_profiles: AccusedDossier['profiles']
  linked_profiles: {
    profile_id: string
    platform: string
    username: string
    profile_url: string
    confidence: number
    match_signals: string[]
    in_database: boolean
    bio?: string | null
    avatar_url?: string | null
  }[]
  platform_candidates: {
    platform: string
    username: string
    profile_url: string
    confidence: number
    match_signals: string[]
    in_database: boolean
    note?: string
  }[]
  network_hints: {
    disclaimer: string
    ip_addresses: string[]
    geo_hints: string[]
    timezone_hints: string[]
  }
  match_summary: {
    database_links: number
    platforms_confirmed: string[]
    candidates_to_verify: number
  }
}

export async function refreshAccusedOsint(username: string): Promise<OsintReport> {
  const q = encodeURIComponent(username.replace(/^@/, ''))
  return request<OsintReport>(`/offenders/dossier/${q}/osint`, { method: 'POST' }, true)
}

export function accusedDossierPdfUrl(username: string): string {
  const q = encodeURIComponent(username.replace(/^@/, ''))
  return `${API_BASE_URL}${API_PREFIX}/reports/accused/${q}/dossier.pdf`
}

export interface AiSettings {
  use_ml_classifier: boolean
  use_hf_inference_api: boolean
  abuse_confidence_threshold: number
  hf_api_configured: boolean
  source: string
}

export interface AiSettingsUpdate {
  use_ml_classifier?: boolean
  use_hf_inference_api?: boolean
  abuse_confidence_threshold?: number
}

export async function getAiSettings(): Promise<AiSettings> {
  return request<AiSettings>('/settings/ai', {}, true)
}

export async function updateAiSettings(body: AiSettingsUpdate): Promise<AiSettings> {
  return request<AiSettings>('/settings/ai', { method: 'PUT', body: JSON.stringify(body) }, true)
}

export interface AiStatus {
  keyword_engine: boolean
  local_ml: boolean
  multilingual_model: string | null
  indic_model: string | null
  hf_inference_api: boolean
  hf_api_configured: boolean
  abuse_threshold: number
}

export interface CrawlerSettings {
  crawler_demo_mode: boolean
  instagram_username: string
  instagram_password_set: boolean
  instagram_password_configured_in_db: boolean
  facebook_email: string
  facebook_password_set: boolean
  facebook_password_configured_in_db: boolean
  facebook_access_token_set: boolean
  threads_uses_instagram_login: boolean
  evidence_screenshot_mode: string
  source: string
}

export interface CrawlerSettingsUpdate {
  crawler_demo_mode?: boolean
  instagram_username?: string
  instagram_password?: string
  facebook_email?: string
  facebook_password?: string
  evidence_screenshot_mode?: 'pillow' | 'playwright' | 'both'
}

export async function getAiStatus(): Promise<AiStatus> {
  return request<AiStatus>('/ai/status', {}, true)
}

export async function getCrawlerSettings(): Promise<CrawlerSettings> {
  return request<CrawlerSettings>('/settings/crawler', {}, true)
}

export async function updateCrawlerSettings(
  body: CrawlerSettingsUpdate,
): Promise<CrawlerSettings> {
  return request<CrawlerSettings>(
    '/settings/crawler',
    { method: 'PUT', body: JSON.stringify(body) },
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
