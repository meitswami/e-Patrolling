import { API_BASE_URL } from '@/lib/constants'
import { getToken } from '@/lib/auth'

export type WsMessage =
  | { type: 'connected'; data: { channel: string } }
  | {
      type: 'evidence_created'
      data: {
        evidence_id: string
        severity_level: string
        platform: string
        target_username: string | null
        comment_preview: string
        risk_score: number
      }
    }
  | {
      type: 'crawl_completed'
      data: {
        target_username: string
        comments_new: number
        abusive_detected: number
        success: boolean
      }
    }
  | { type: 'stats_updated'; data: Record<string, number> }

function wsBaseUrl(): string {
  const env = process.env.NEXT_PUBLIC_WS_URL
  if (env) return env.replace(/\/$/, '')
  return API_BASE_URL.replace(/^http/, 'ws')
}

export function connectDashboardWs(
  onMessage: (msg: WsMessage) => void,
  onError?: (err: Event) => void,
): () => void {
  const token = getToken()
  if (!token) return () => {}

  const url = `${wsBaseUrl()}/ws/dashboard?token=${encodeURIComponent(token)}`
  let ws: WebSocket | null = null
  let closed = false

  try {
    ws = new WebSocket(url)
    ws.onmessage = (event) => {
      try {
        onMessage(JSON.parse(event.data) as WsMessage)
      } catch {
        /* ignore malformed */
      }
    }
    ws.onerror = (e) => onError?.(e)
  } catch {
    return () => {}
  }

  return () => {
    closed = true
    ws?.close()
  }
}
