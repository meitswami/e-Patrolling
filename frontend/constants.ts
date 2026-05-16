// ============================================================
// PATROL — Frontend Constants & Configuration
// ============================================================

import { Platform, SeverityLevel } from './index'

// ── Platform Config ───────────────────────────────────────────

export const PLATFORM_CONFIG: Record<Platform, {
  label: string
  color: string
  bgColor: string
  icon: string
  textColor: string
}> = {
  instagram: {
    label: 'Instagram',
    color: '#E1306C',
    bgColor: '#3d0a1a',
    icon: '📷',
    textColor: '#f78ca0',
  },
  facebook: {
    label: 'Facebook',
    color: '#1877F2',
    bgColor: '#071d40',
    icon: '📘',
    textColor: '#74a9f7',
  },
  twitter: {
    label: 'Twitter / X',
    color: '#1DA1F2',
    bgColor: '#051828',
    icon: '🐦',
    textColor: '#7dcbf7',
  },
  threads: {
    label: 'Threads',
    color: '#000000',
    bgColor: '#1a1a1a',
    icon: '🧵',
    textColor: '#a0a0a0',
  },
  telegram: {
    label: 'Telegram',
    color: '#0088CC',
    bgColor: '#00223a',
    icon: '✈️',
    textColor: '#6bc5e8',
  },
  whatsapp: {
    label: 'WhatsApp',
    color: '#25D366',
    bgColor: '#0a2e1a',
    icon: '💬',
    textColor: '#6de69a',
  },
}

// ── Severity Config ───────────────────────────────────────────

export const SEVERITY_CONFIG: Record<SeverityLevel, {
  label: string
  color: string
  bgColor: string
  textColor: string
  borderColor: string
  score_range: [number, number]
  blink: boolean
}> = {
  LOW: {
    label: 'Low',
    color: '#3b82f6',
    bgColor: '#1e3a5f',
    textColor: '#93c5fd',
    borderColor: '#2563eb',
    score_range: [0, 40],
    blink: false,
  },
  MEDIUM: {
    label: 'Medium',
    color: '#f59e0b',
    bgColor: '#3d2608',
    textColor: '#fcd34d',
    borderColor: '#d97706',
    score_range: [41, 65],
    blink: false,
  },
  HIGH: {
    label: 'High',
    color: '#f97316',
    bgColor: '#3d1200',
    textColor: '#fb923c',
    borderColor: '#ea580c',
    score_range: [66, 84],
    blink: false,
  },
  CRITICAL: {
    label: 'Critical',
    color: '#ef4444',
    bgColor: '#3d0505',
    textColor: '#f87171',
    borderColor: '#dc2626',
    score_range: [85, 100],
    blink: true,  // Blinking indicator for critical
  },
}

// ── Navigation ────────────────────────────────────────────────

export const NAV_ITEMS = [
  {
    label: 'Overview',
    path: '/dashboard',
    icon: 'LayoutDashboard',
    description: 'Command center overview',
  },
  {
    label: 'Live Monitoring',
    path: '/monitoring',
    icon: 'Radio',
    description: 'Real-time crawler status',
    badge: 'LIVE',
  },
  {
    label: 'Evidence Feed',
    path: '/evidence',
    icon: 'ShieldAlert',
    description: 'Collected evidence gallery',
  },
  {
    label: 'Region Intel',
    path: '/regions',
    icon: 'Map',
    description: 'Geographic threat intelligence',
  },
  {
    label: 'Offenders',
    path: '/offenders',
    icon: 'UserX',
    description: 'Repeat offender profiles',
  },
  {
    label: 'Analytics',
    path: '/analytics',
    icon: 'BarChart3',
    description: 'Threat analytics & trends',
  },
  {
    label: 'Reports',
    path: '/reports',
    icon: 'FileDown',
    description: 'Export intelligence reports',
  },
  {
    label: 'Settings',
    path: '/settings',
    icon: 'Settings',
    description: 'System configuration',
  },
]

// ── Design Tokens ─────────────────────────────────────────────
// Matches tailwind.config.js custom colors

export const COLORS = {
  // Background
  bg: '#0a0e1a',
  bgSurface: '#111827',
  bgCard: '#161d2e',
  bgBorder: '#1f2d44',

  // Text
  textPrimary: '#e2e8f0',
  textSecondary: '#94a3b8',
  textMuted: '#475569',

  // Accent
  accentGreen: '#00ff88',   // Active monitoring
  accentRed: '#ff3b30',     // Critical
  accentAmber: '#ff9f0a',   // High
  accentBlue: '#3b82f6',    // Info

  // Severity (mirrors SEVERITY_CONFIG)
  low: '#3b82f6',
  medium: '#f59e0b',
  high: '#f97316',
  critical: '#ef4444',
}

// ── API Config ────────────────────────────────────────────────

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
export const WS_BASE_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000'
export const API_PREFIX = '/api/v1'

// ── Pagination ────────────────────────────────────────────────

export const DEFAULT_PAGE_SIZE = 20
export const PAGE_SIZE_OPTIONS = [10, 20, 50, 100]

// ── Refresh Intervals ─────────────────────────────────────────

export const DASHBOARD_REFRESH_MS = 30_000   // 30 seconds
export const LIVE_FEED_ITEMS = 50            // Max items in live feed

// ── Evidence ─────────────────────────────────────────────────

export const EVIDENCE_SCREENSHOT_BASE = `${API_BASE_URL}/storage/evidence`

// ── India Regions (for quick filter UI) ──────────────────────

export const INDIA_STATES = [
  'Andhra Pradesh', 'Arunachal Pradesh', 'Assam', 'Bihar',
  'Chhattisgarh', 'Goa', 'Gujarat', 'Haryana', 'Himachal Pradesh',
  'Jharkhand', 'Karnataka', 'Kerala', 'Madhya Pradesh', 'Maharashtra',
  'Manipur', 'Meghalaya', 'Mizoram', 'Nagaland', 'Odisha', 'Punjab',
  'Rajasthan', 'Sikkim', 'Tamil Nadu', 'Telangana', 'Tripura',
  'Uttar Pradesh', 'Uttarakhand', 'West Bengal',
  'Delhi', 'Jammu & Kashmir', 'Ladakh',
]

export const MAJOR_CITIES = [
  'Mumbai', 'Delhi', 'Bangalore', 'Hyderabad', 'Ahmedabad', 'Chennai',
  'Kolkata', 'Surat', 'Pune', 'Jaipur', 'Lucknow', 'Kanpur',
  'Nagpur', 'Indore', 'Thane', 'Bhopal', 'Visakhapatnam', 'Pimpri',
  'Patna', 'Vadodara', 'Ghaziabad', 'Ludhiana', 'Agra', 'Nashik',
]