import { request } from './client'
import type { Tone } from '@/features/shared/StatusBadge'

export interface QueueItem {
  id: string
  reference_no: string
  licence_title: string
  business_name: string | null
  premises_summary: string | null
  applicant_name: string
  /** Internal status code. Officer-only; never rendered to operators. */
  status: string
  status_label: string
  status_tone: Tone
  next_action: string
  officer_turn: boolean
  decided: boolean
  revision_count: number
  open_feedback_count: number
  documents_attention: number
  documents_checking: number
  submitted_at: string | null
  last_activity_at: string
}

export interface Queue {
  items: QueueItem[]
  officer_turn_count: number
  waiting_on_operator_count: number
  decided_count: number
}

export function getQueue(): Promise<Queue> {
  return request<Queue>('/officer/applications')
}
