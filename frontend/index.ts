// ============================================================
// PATROL — TypeScript Type Definitions
// All interfaces matching the backend Pydantic/DB models
// ============================================================

// ── Enums ────────────────────────────────────────────────────

export type Platform = 'instagram' | 'facebook' | 'twitter' | 'threads' | 'telegram' | 'whatsapp'

export type SeverityLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'

export type Language = 'hindi' | 'english' | 'hinglish' | 'unknown'

export type UserRole = 'ADMIN' | 'ANALYST' | 'VIEWER'

export type OffenderStatus = 'SUSPECTED' | 'CONFIRMED' | 'ESCALATED' | 'REPORTED'

// ── Core Models ──────────────────────────────────────────────

export interface User {
  id: string
  email: string
  name: string
  role: UserRole
  is_active: boolean
  last_login_at: string | null
  created_at: string
}

export interface TargetAccount {
  id: string
  username: string
  display_name: string | null
  platform: Platform
  profile_url: string
  avatar_url: string | null
  follower_count: number | null
  is_verified: boolean
  is_active: boolean
  monitoring_enabled: boolean
  last_crawled_at: string | null
  inferred_region: string | null
  region_confidence: number | null
  created_at: string
}

export interface AccusedProfile {
  id: string
  platform: Platform
  username: string
  display_name: string | null
  profile_url: string
  avatar_url: string | null
  follower_count: number | null
  is_verified: boolean
  total_incidents: number
  critical_count: number
  high_count: number
  avg_severity_score: number
  max_risk_score: number
  status: OffenderStatus
  is_repeat_offender: boolean
  inferred_region: string | null
  region_confidence: number | null
  first_seen_at: string
  last_seen_at: string
}

export interface AIResult {
  id: string
  comment_id: string
  is_abusive: boolean
  is_sexual_harassment: boolean
  is_rape_threat: boolean
  is_stalking: boolean
  is_hate_speech: boolean
  is_threat: boolean
  is_bullying: boolean
  is_doxxing: boolean
  confidence_score: number
  toxicity_score: number
  severity_score: number
  risk_score: number
  severity_level: SeverityLevel
  detected_language: Language
  matched_keywords: string[]
  detected_entities: Record<string, unknown>
  model_used: string | null
  processed_at: string
}

export interface EvidenceReport {
  id: string
  evidence_id: string
  platform: Platform
  post_url: string | null
  comment_text: string
  comment_timestamp: string | null
  severity_level: SeverityLevel
  risk_score: number
  screenshot_path: string | null
  capture_timestamp: string
  is_escalated: boolean
  notes: string | null

  // Joined data
  target?: TargetAccount
  accused?: AccusedProfile
  ai_result?: AIResult
}

export interface RepeatOffender {
  id: string
  accused_id: string
  total_offenses: number
  targets_harassed: number
  platforms_used: Platform[]
  critical_count: number
  high_count: number
  medium_count: number
  low_count: number
  first_offense_at: string | null
  last_offense_at: string | null
  status: OffenderStatus
  priority_score: number
  flagged_at: string

  // Joined
  accused?: AccusedProfile
}

// ── Analytics Models ─────────────────────────────────────────

export interface DashboardStats {
  active_targets: number
  evidence_24h: number
  critical_total: number
  repeat_offenders: number
  total_evidence: number
  live_monitoring: boolean
}

export interface PlatformStats {
  platform: Platform
  count: number
  percentage: number
}

export interface SeverityStats {
  level: SeverityLevel
  count: number
  percentage: number
}

export interface RegionStats {
  region: string
  state: string | null
  incident_count: number
  critical_count: number
  latitude: number | null
  longitude: number | null
}

export interface TrendPoint {
  timestamp: string
  count: number
  critical: number
  high: number
}

export interface TrendingKeyword {
  keyword: string
  count: number
  severity: SeverityLevel
  language: Language
}

export interface AnalyticsDashboard {
  stats: DashboardStats
  by_platform: PlatformStats[]
  by_severity: SeverityStats[]
  by_region: RegionStats[]
  trend_24h: TrendPoint[]
  trending_keywords: TrendingKeyword[]
}

// ── WebSocket Events ─────────────────────────────────────────

export type WSEventType =
  | 'new_evidence'
  | 'critical_alert'
  | 'stats_update'
  | 'offender_flagged'
  | 'crawler_status'
  | 'connection_ack'

export interface WSEvent<T = unknown> {
  type: WSEventType
  data: T
  timestamp: string
}

export interface NewEvidenceEvent {
  evidence_id: string
  platform: Platform
  accused_username: string
  target_username: string
  severity_level: SeverityLevel
  risk_score: number
  comment_preview: string
  screenshot_url: string | null
}

export interface CriticalAlertEvent {
  evidence_id: string
  message: string
  accused_username: string
  target_username: string
  platform: Platform
}

export interface StatsUpdateEvent {
  stats: DashboardStats
}

// ── API Response Types ───────────────────────────────────────

export interface ApiError {
  error: string
  detail?: string
  path?: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface FilterParams {
  platform?: Platform
  severity?: SeverityLevel
  language?: Language
  region?: string
  is_repeat_offender?: boolean
  start_date?: string
  end_date?: string
  search?: string
  page?: number
  page_size?: number
}

// ── Report Types ─────────────────────────────────────────────

export type ReportFormat = 'excel' | 'pdf' | 'json'
export type ReportStatus = 'PENDING' | 'GENERATING' | 'READY' | 'FAILED'

export interface GeneratedReport {
  id: string
  report_type: ReportFormat
  status: ReportStatus
  filters: FilterParams
  file_path: string | null
  file_size_bytes: number | null
  requested_at: string
  completed_at: string | null
  error_message: string | null
}

// ── Auth Types ───────────────────────────────────────────────

export interface LoginRequest {
  email: string
  password: string
}

export interface TokenResponse {
  access_token: string
  token_type: 'bearer'
  expires_in: number
  user: User
}