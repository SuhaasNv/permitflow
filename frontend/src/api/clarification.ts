import type { StorageView } from './applications'
import { API_URL, AppError, notifyUnauthorized, request } from './client'
import { uploadToken } from './documents'

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
  /** The application's storage room (US-085), for the line above the file picker. */
  storage: StorageView | null
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

export function respondToClarification(id: string, itemId: string, message: string): Promise<ClarificationView> {
  return request<ClarificationView>(`/applications/${id}/clarifications/${itemId}/responses`, { method: 'POST', body: { message } })
}

export interface AttachResult {
  view: ClarificationView
  unchanged: boolean
}

/** A file on a drafted answer: the document rules, three per answer. Multipart through the shared client. */
export function attachToResponse(id: string, responseId: string, file: File): Promise<AttachResult> {
  const formData = new FormData()
  formData.append('file', file)
  return request<AttachResult>(`/applications/${id}/clarifications/responses/${responseId}/attachments`, { method: 'POST', formData })
}

export function removeAttachment(id: string, responseId: string, attachmentId: string): Promise<ClarificationView> {
  return request<ClarificationView>(`/applications/${id}/clarifications/responses/${responseId}/attachments/${attachmentId}`, {
    method: 'DELETE',
  })
}

export function sendClarifications(id: string): Promise<ClarificationView> {
  return request<ClarificationView>(`/applications/${id}/clarifications/send`, { method: 'POST' })
}

/** Downloads an attachment for the owner, an officer or an admin (same path for every role). */
export async function downloadAttachment(applicationId: string, attachmentId: string, filename: string): Promise<void> {
  const token = uploadToken()
  const res = await fetch(`${API_URL}/applications/${applicationId}/clarifications/attachments/${attachmentId}/download`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!res.ok) {
    if (res.status === 401) notifyUnauthorized()
    throw new AppError(res.status, {
      code: 'http_error',
      message: res.status === 404 ? 'This file is no longer available.' : 'Could not download this file.',
    })
  }
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  setTimeout(() => URL.revokeObjectURL(url), 1500)
}

// Officer side (US-066) ------------------------------------------------------------------------------

export interface ThreadRequest {
  id: string
  round_no: number
  message: string
  author_name: string
  created_at: string
  released_at: string | null
  withdrawn_at: string | null
  response: ClarificationResponse | null
}

export type ThreadStatus = 'open' | 'answered' | 'resolved' | 'withdrawn'

export interface ClarificationThread {
  item_id: string
  key: string
  title: string
  result: string
  comment: string | null
  status: ThreadStatus | string
  round_no: number
  requests: ThreadRequest[]
  can_resolve: boolean
  can_reopen: boolean
  can_withdraw: boolean
  pending_release: boolean
}

export interface ClarificationOfficerView {
  visit_no: number
  round: number
  open_count: number
  answered_count: number
  resolved_count: number
  withdrawn_count: number
  unreleased_count: number
  turn: string
  items: ClarificationThread[]
}
