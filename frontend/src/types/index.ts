// PATROL — TypeScript types (matches backend models)

export type Platform = 'instagram' | 'facebook' | 'twitter' | 'threads' | 'telegram' | 'whatsapp'
export type SeverityLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
export type Language = 'hindi' | 'english' | 'hinglish' | 'unknown'
export type UserRole = 'ADMIN' | 'ANALYST' | 'VIEWER'
export type OffenderStatus = 'SUSPECTED' | 'CONFIRMED' | 'ESCALATED' | 'REPORTED'

export interface User {
  id: string
  email: string
  name: string
  role: UserRole
  is_active: boolean
  last_login_at: string | null
  created_at: string
}

export interface DashboardStats {
  active_targets: number
  evidence_24h: number
  critical_total: number
  repeat_offenders: number
  total_evidence: number
  live_monitoring: boolean
}

export interface ApiError {
  error: string
  detail?: string
  path?: string
}

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

export interface HealthResponse {
  status: string
  service: string
  version: string
  environment: string
  redis: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface EvidenceListItem {
  id: string
  evidence_id: string
  platform: Platform
  comment_text: string
  severity_level: SeverityLevel
  risk_score: number
  capture_timestamp: string
  created_at: string
  is_escalated: boolean
  screenshot_path: string | null
  target_username: string | null
  accused_username: string | null
  abuse_categories: string[]
  is_abusive: boolean
  is_lexicon_match: boolean
  abuse_explanations: AbuseExplanationItem[]
  verification_status?: 'pending' | 'verified_abusive' | 'false_positive' | null
}

export interface AbuseExplanationItem {
  kind: string
  title: string
  meaning_en: string
  offender_implication: string
  related_categories?: string[]
}

export type TargetSource = 'admin_panel' | 'website_intake'

export type WebsiteRequestStatus = 'pending' | 'reviewed' | 'converted' | 'dismissed'

export interface TargetAccount {
  id: string
  username: string
  display_name: string | null
  platform: Platform
  profile_url: string
  is_active: boolean
  monitoring_enabled: boolean
  source?: TargetSource
  website_request_id?: string | null
  created_at: string
}

export interface WebsiteSafetyRequest {
  id: string
  contact_name: string | null
  contact_email: string | null
  contact_phone: string | null
  profile_entries: Array<{
    raw?: string
    platform: string
    username: string
    profile_url: string
  }>
  state: string
  city: string
  message: string | null
  status: WebsiteRequestStatus
  admin_notes: string | null
  created_at: string
  reviewed_at: string | null
}

export interface IndiaLocations {
  states: string[]
  cities_by_state: Record<string, string[]>
}
