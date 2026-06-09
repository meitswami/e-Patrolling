import { API_BASE_URL, API_PREFIX, buildApiUrl } from '@/lib/constants'
import { getToken, clearSession } from '@/lib/auth'
import type {
  AbuseExplanationItem,
  DashboardStats,
  EvidenceListItem,
  HealthResponse,
  LoginRequest,
  PaginatedResponse,
  Platform,
  TargetAccount,
  TargetSource,
  TokenResponse,
  User,
  WebsiteSafetyRequest,
  IndiaLocations,
} from '@/types'

/** Turn FastAPI error JSON into a readable string. */
export function parseApiError(body: unknown, fallback: string): string {
  if (!body || typeof body !== 'object') return fallback
  const record = body as Record<string, unknown>

  if (typeof record.detail === 'string') return record.detail
  if (typeof record.error === 'string') {
    const pathHint =
      typeof record.path === 'string' ? ` (${record.path})` : ''
    return `${record.error}${pathHint}`
  }

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
    res = await fetch(buildApiUrl(path), {
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
      window.location.href = '/admin'
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
    target_id?: string
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
  if (filters?.target_id) params.set('target_id', filters.target_id)
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
  source?: TargetSource,
): Promise<PaginatedResponse<TargetAccount>> {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  })
  if (source) params.set('source', source)
  return request<PaginatedResponse<TargetAccount>>(`/targets?${params}`, {}, true)
}

export async function getIndiaLocations(): Promise<IndiaLocations> {
  return request<IndiaLocations>('/public/locations/india')
}

export interface SubmitSafetyRequestPayload {
  profile_entries: { value: string }[]
  state: string
  city: string
  contact_name?: string
  contact_email?: string
  contact_phone?: string
  message?: string
}

export async function submitSafetyRequest(
  body: SubmitSafetyRequestPayload,
): Promise<WebsiteSafetyRequest> {
  return request<WebsiteSafetyRequest>('/public/safety-request', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function listWebsiteRequests(
  page = 1,
  pageSize = 20,
  status?: string,
): Promise<PaginatedResponse<WebsiteSafetyRequest>> {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  })
  if (status) params.set('status', status)
  return request<PaginatedResponse<WebsiteSafetyRequest>>(
    `/website-requests?${params}`,
    {},
    true,
  )
}

export async function convertWebsiteRequest(requestId: string): Promise<TargetAccount[]> {
  return request<TargetAccount[]>(
    `/website-requests/${requestId}/convert`,
    { method: 'POST' },
    true,
  )
}

export async function updateWebsiteRequest(
  requestId: string,
  body: { status?: string; admin_notes?: string },
): Promise<WebsiteSafetyRequest> {
  return request<WebsiteSafetyRequest>(
    `/website-requests/${requestId}`,
    { method: 'PATCH', body: JSON.stringify(body) },
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

export interface UpdateTargetPayload {
  monitoring_enabled?: boolean
  is_active?: boolean
  display_name?: string
  notes?: string
}

export async function updateTarget(
  targetId: string,
  body: UpdateTargetPayload,
): Promise<TargetAccount> {
  return request<TargetAccount>(
    `/targets/${targetId}`,
    { method: 'PATCH', body: JSON.stringify(body) },
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

export interface RunningCrawlInfo {
  target_id: string
  target_username: string
  platform: string
  started_at: string
  mode: string
}

export interface CrawlerStatus {
  supported_platforms: string[]
  platforms: PlatformPatrolInfo[]
  redis_enabled: boolean
  scheduler_enabled: boolean
  crawl_interval_seconds: number
  mode: string
  instagram_credentials_configured?: boolean
  running_targets?: RunningCrawlInfo[]
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
  target_username?: string | null
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
  log_id?: string
  historical?: boolean
  posts_crawled?: number
  success: boolean
  comments_new: number
  abusive_detected: number
  critical_detected?: number
  evidence_ids?: string[]
  error?: string
}

export interface CrawlLogEvidenceItem {
  evidence_id: string
  uuid: string
  accused_username: string | null
  severity: string
  risk_score: number
  comment_preview: string
  screenshot_path: string | null
  abuse_categories: string[]
  is_abusive: boolean
  is_lexicon_match: boolean
  abuse_explanations: AbuseExplanationItem[]
}

export interface EvidenceBackfillResult {
  total: number
  updated: number
  message: string
}

export async function backfillEvidenceCategories(): Promise<EvidenceBackfillResult> {
  return request<EvidenceBackfillResult>(
    '/evidence/backfill-categories',
    { method: 'POST' },
    true,
  )
}

export interface CrawlLogResults {
  log_id: string
  target_id: string | null
  target_username: string | null
  platform: string
  success: boolean
  comments_new: number
  abusive_detected: number
  started_at: string
  completed_at: string | null
  evidence: CrawlLogEvidenceItem[]
}

export async function getCrawlerStatus(): Promise<CrawlerStatus> {
  return request<CrawlerStatus>('/crawlers/status', {}, true)
}

export async function clearCrawlErrorLogs(allFailed = false): Promise<{ removed: number; message: string }> {
  const q = allFailed ? '?all_failed=true' : ''
  return request<{ removed: number; message: string }>(
    `/crawlers/logs/clear-errors${q}`,
    { method: 'POST' },
    true,
  )
}

export async function listCrawlLogs(limit = 20): Promise<CrawlLogItem[]> {
  return request<CrawlLogItem[]>(`/crawlers/logs?limit=${limit}`, {}, true)
}

export async function getCrawlLogResults(logId: string): Promise<CrawlLogResults> {
  return request<CrawlLogResults>(`/crawlers/logs/${logId}/results`, {}, true)
}

/** Blocking — holds API for minutes; avoid on production. Prefer scheduleCrawlAll. */
export async function runCrawlAll(): Promise<CrawlResultSummary[]> {
  return request<CrawlResultSummary[]>('/crawlers/run-all', { method: 'POST' }, true)
}

export async function scheduleCrawlAll(): Promise<{ status: string; message: string }> {
  return request<{ status: string; message: string }>(
    '/crawlers/schedule-all',
    { method: 'POST' },
    true,
  )
}

export async function startCrawlTarget(
  targetId: string,
): Promise<{ status: string; message: string; target_id?: string }> {
  return request<{ status: string; message: string; target_id?: string }>(
    `/crawlers/start/${targetId}`,
    { method: 'POST' },
    true,
  )
}

export async function stopCrawlAll(): Promise<{ status: string; message: string }> {
  return request<{ status: string; message: string }>('/crawlers/stop', { method: 'POST' }, true)
}

export async function runCrawlTarget(targetId: string): Promise<CrawlResultSummary> {
  return request<CrawlResultSummary>(`/crawlers/run/${targetId}`, { method: 'POST' }, true)
}

/** Scroll older posts and crawl comments on each (Instagram). */
export async function runHistoricalCrawl(targetId: string): Promise<CrawlResultSummary> {
  return request<CrawlResultSummary>(
    `/crawlers/run/${targetId}/historical`,
    { method: 'POST' },
    true,
  )
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
    abuse_categories?: string[]
    abuse_explanations?: AbuseExplanationItem[]
    is_abusive?: boolean
    is_lexicon_match?: boolean
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

export interface InstagramValidationResult {
  success: boolean
  message: string
  username: string | null
}

export interface CrawlerSettings {
  crawler_demo_mode: boolean
  mode?: string
  instagram_session_connected?: boolean
  instagram_auth_configured?: boolean
  instagram_credentials_configured?: boolean
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

export async function validateInstagramCredentials(): Promise<InstagramValidationResult> {
  return request<InstagramValidationResult>(
    '/settings/crawler/verify-instagram-session',
    { method: 'POST' },
    true,
  )
}

/** Opens a browser on the server; user logs in on instagram.com (up to 5 min). */
export async function connectInstagramSession(): Promise<InstagramValidationResult> {
  const headers: HeadersInit = { 'Content-Type': 'application/json' }
  const token = getToken()
  if (token) headers['Authorization'] = `Bearer ${token}`

  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), 360000)
  try {
    const res = await fetch(buildApiUrl('/settings/crawler/connect-instagram'), {
      method: 'POST',
      headers,
      signal: controller.signal,
    })
    const body = await res.json().catch(() => ({}))
    if (!res.ok) {
      throw new Error(parseApiError(body, 'Instagram connect failed'))
    }
    return body as InstagramValidationResult
  } catch (err) {
    if (err instanceof Error && err.name === 'AbortError') {
      throw new Error('Connect timed out after 6 minutes. Try again and finish login in the browser.')
    }
    throw err
  } finally {
    clearTimeout(timer)
  }
}

export async function disconnectInstagramSession(): Promise<InstagramValidationResult> {
  return request<InstagramValidationResult>(
    '/settings/crawler/disconnect-instagram',
    { method: 'POST' },
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

// ── Abuse Dictionary / Lexicon API ───────────────────────────

export interface LexiconPattern {
  regex: string
  score: number
  label: string
}

export interface GlossaryTerm {
  id: string
  detect: string
  display: string
  categories: string[]
  meaning_en: string
  offender_implication: string
  also_blocks?: string[]
}

export interface FullDictionary {
  lexicon_version: string
  glossary_version: string
  total_patterns: number
  total_terms: number
  total_phrases: number
  patterns: LexiconPattern[]
  terms: GlossaryTerm[]
  phrases: GlossaryTerm[]
  models: Record<string, { id: string; task: string; notes: string; languages?: string[] }>
}

export interface AddTermPayload {
  word: string
  regex: string
  score: number
  label: string
  meaning_en?: string
  offender_implication?: string
}

export async function getFullDictionary(): Promise<FullDictionary> {
  return request<FullDictionary>('/lexicon/full', {}, true)
}

export async function addDictionaryTerm(body: AddTermPayload): Promise<{ success: boolean; message: string; term_id: string; total_patterns: number }> {
  return request('/lexicon/add-term', { method: 'POST', body: JSON.stringify(body) }, true)
}

export async function removeDictionaryTerm(id: string): Promise<{ success: boolean; message: string }> {
  return request('/lexicon/remove-term', { method: 'DELETE', body: JSON.stringify({ id }) }, true)
}

// ── Manual Verification API ───────────────────────────

export async function listUnverifiedEvidence(
  page = 1,
  pageSize = 20,
  filters?: {
    search?: string
    severity?: string
    platform?: string
  },
): Promise<PaginatedResponse<EvidenceListItem>> {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  })
  if (filters?.search) params.set('search', filters.search)
  if (filters?.severity) params.set('severity', filters.severity)
  if (filters?.platform) params.set('platform', filters.platform)
  return request<PaginatedResponse<EvidenceListItem>>(
    `/verification/unverified?${params.toString()}`,
    {},
    true,
  )
}

export interface VerifyEvidencePayload {
  is_abusive: boolean
  add_to_dictionary: boolean
  label?: string
  meaning_en?: string
  offender_implication?: string
}

export async function verifyEvidence(
  evidenceId: string,
  body: VerifyEvidencePayload,
): Promise<{ id: string; evidence_id: string; verification_status: string; verified_at: string; added_to_dictionary: boolean; term_id: string | null }> {
  return request(
    `/verification/${evidenceId}/verify`,
    { method: 'POST', body: JSON.stringify(body) },
    true,
  )
}
