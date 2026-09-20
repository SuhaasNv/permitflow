import { request } from './client'

export interface ClarificationRequest {
  id: string
  round_no: number
  message: string
  released_at: string
}

export interface ClarificationAttachment {
  id: string
  original_filename: string
  content_type: string
  size_bytes: number
  uploaded_at: string
}

export interface ClarificationResponse {
  id: string
  round_no: number
  message: string
  created_at: string
  sent_at: string | null
  attachments: ClarificationAttachment[]
}

/** Operator words only: Waiting for your response, Sent, Clarified, No longer needed. */
export type ClarificationItemStatus = 'Waiting for your response' | 'Sent' | 'Clarified' | 'No longer needed'

export interface ClarificationItem {
  item_id: string
  key: string
  title: string
  guidance: string
  status: ClarificationItemStatus | string
  round_no: number
  requests: ClarificationRequest[]
  responses: ClarificationResponse[]
  can_respond: boolean
}

export interface ClarificationView {
  application_id: string
  visit_no: number | null
  items: ClarificationItem[]
  open_count: number
  answered_count: number
  resolved_count: number
  round: number
  can_respond: boolean
  can_send: boolean
}

/** The block on the operator's application view (US-064). */
export interface ClarificationBlock {
  can_respond: boolean
  open_count: number
  answered_count: number
  round: number
}

export function getClarifications(id: string): Promise<ClarificationView> {
  return request<ClarificationView>(`/applications/${id}/clarifications`)
}
