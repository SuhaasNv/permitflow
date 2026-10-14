import { uploadToken } from './documents'
import { API_URL, AppError, authInit, notifyUnauthorized, request } from './client'

// ---- US-100: AI usage and cost ----

export interface AiUsageRow {
  id: string
  created_at: string
  application_id: string | null
  /** Null once a deleted draft's application is gone. */
  reference_no: string | null
  /** Null for a deleted draft. */
  business_name: string | null
  user_id: string | null
  user_name: string | null
  document_type: string
  model: string | null
  input_tokens: number
  output_tokens: number
  /** An exact decimal string, never a float. */
  cost_usd: string
  latency_ms: number
  outcome: string
}

interface Spend {
  runs: number
  input_tokens: number
  output_tokens: number
  cost_usd: string
}

export interface AiUsageTotals extends Spend {
  /** Over the checks that reached a provider; null when none did. */
  avg_latency_ms: number | null
}

export interface AiUsagePage {
  items: AiUsageRow[]
  next_cursor: string | null
  /** Over every row the filters match, not only this page. */
  totals: AiUsageTotals
  /** The Singapore day so far; `runs` are the checks that count toward `daily_cap`. */
  today: Spend & { daily_cap: number }
}

/** Singapore days, both ends included; empty means open-ended. */
export interface AiUsageQuery {
  user: string
  /** An application reference, matched exactly by the server. */
  reference: string
  from: string
  to: string
}

function filterParams(q: AiUsageQuery): URLSearchParams {
  const p = new URLSearchParams()
  if (q.user) p.set('user_id', q.user)
  if (q.reference) p.set('reference', q.reference)
  if (q.from) p.set('from', q.from)
  if (q.to) p.set('to', q.to)
  return p
}

export function getAiUsage(q: AiUsageQuery, before: string | null, limit = 50): Promise<AiUsagePage> {
  const p = filterParams(q)
  p.set('limit', String(limit))
  if (before) p.set('before', before)
  return request<AiUsagePage>(`/admin/ai-usage?${p.toString()}`)
}

/** The same rows as a file, fetched with the session (bearer header or cookie; no token in the URL) and saved as ai-usage.csv. */
export async function downloadAiUsageCsv(q: AiUsageQuery): Promise<void> {
  const res = await fetch(`${API_URL}/admin/ai-usage.csv?${filterParams(q).toString()}`, authInit(uploadToken()))
  if (!res.ok) {
    if (res.status === 401) notifyUnauthorized()
    throw new AppError(res.status, {
      code: 'http_error',
      message: res.status === 400 ? 'The start day is after the end day.' : 'Could not export the checks. Try again.',
    })
  }
  const url = URL.createObjectURL(await res.blob())
  const a = document.createElement('a')
  a.href = url
  a.download = 'ai-usage.csv'
  a.click()
  setTimeout(() => URL.revokeObjectURL(url), 1500)
}
