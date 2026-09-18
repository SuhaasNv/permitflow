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

export interface OfficerSection {
  key: string
  title: string
  description: string
  data: Record<string, unknown>
  complete: boolean
}

export interface OfficerIssue {
  code: string
  severity: 'low' | 'medium' | 'high'
  message: string
  evidence?: string | null
  field?: string | null
}

export interface OfficerVerification {
  status: 'pending' | 'running' | 'verified' | 'issues_found' | 'needs_review' | 'unreadable' | 'failed' | 'unavailable'
  summary: string | null
  confidence: number | null
  issues: OfficerIssue[]
  missing_information: string[]
  error_reason: string | null
  provider: string
  model: string | null
  finished_at: string | null
}

export interface OfficerDocument {
  id: string
  document_type: string
  label: string
  original_filename: string
  content_type: string
  size_bytes: number
  uploaded_at: string
  in_current_revision: boolean
  verification: OfficerVerification | null
}

export interface Revision {
  id: string
  number: number
  submitted_at: string
  submitted_by: string
}

export interface OfficerAction {
  target: string
  label: string
  enabled: boolean
  reason: string | null
  requires_note: boolean
}

export interface VerificationSummary {
  total: number
  verified: number
  issues_found: number
  needs_review: number
  checking: number
  other: number
}

export interface FeedbackItem {
  id: string
  target_type: 'section' | 'document'
  section_key: string | null
  document_type: string | null
  target_label: string
  message: string
  template_key: string | null
  resolution: 'open' | 'addressed' | 'resolved' | 'withdrawn'
  raised_in_revision: number
  author_name: string
  created_at: string
  released_to_operator_at: string | null
  addressed_in_revision: number | null
  resolved_at: string | null
}

export interface FeedbackTemplate {
  key: string
  title: string
  target_type: 'section' | 'document'
  section_key: string | null
  document_type: string | null
  message: string
}

export interface FeedbackInput {
  target_type: 'section' | 'document'
  section_key?: string | null
  document_type?: string | null
  message: string
  template_key?: string | null
}

export interface OfficerApplication {
  id: string
  reference_no: string
  licence_title: string
  status: string
  status_label: string
  status_tone: Tone
  applicant: { id: string; full_name: string; email: string }
  business_name: string | null
  premises_summary: string | null
  sections: OfficerSection[]
  documents: OfficerDocument[]
  missing_document_types: string[]
  verification_summary: VerificationSummary
  revisions: Revision[]
  current_revision_number: number
  previous_revision_number: number | null
  changed_sections: string[]
  changed_document_types: string[]
  addressed_unresolved_count: number
  feedback: FeedbackItem[]
  open_feedback_count: number
  feedback_editable: boolean
  feedback_locked_reason: string | null
  actions: OfficerAction[]
  decision_note: string | null
  version: number
  created_at: string
  updated_at: string
}

export function getQueue(): Promise<Queue> {
  return request<Queue>('/officer/applications')
}

export function getOfficerApplication(id: string): Promise<OfficerApplication> {
  return request<OfficerApplication>(`/officer/applications/${id}`)
}

export function transitionApplication(
  id: string,
  body: { target: string; note?: string; expected_version: number },
): Promise<OfficerApplication> {
  return request<OfficerApplication>(`/officer/applications/${id}/transition`, { method: 'POST', body })
}

export function rerunOfficerCheck(id: string, documentId: string): Promise<OfficerApplication> {
  return request<OfficerApplication>(`/officer/applications/${id}/documents/${documentId}/verify`, { method: 'POST' })
}

export function getFeedbackTemplates(): Promise<FeedbackTemplate[]> {
  return request<FeedbackTemplate[]>('/officer/feedback-templates')
}

export function createFeedback(id: string, body: FeedbackInput): Promise<OfficerApplication> {
  return request<OfficerApplication>(`/officer/applications/${id}/feedback`, { method: 'POST', body })
}

export function withdrawFeedback(id: string, feedbackId: string): Promise<OfficerApplication> {
  return request<OfficerApplication>(`/officer/applications/${id}/feedback/${feedbackId}/withdraw`, { method: 'POST' })
}

export interface FieldChange {
  key: string
  label: string
  old: unknown
  new: unknown
}

export interface Compare {
  application_id: string
  from_revision: number
  to_revision: number
  sections: { key: string; title: string; changed: boolean; fields: FieldChange[] }[]
  documents: {
    type: string
    label: string
    change: 'unchanged' | 'added' | 'removed' | 'replaced'
    old: { id: string; filename: string } | null
    new: { id: string; filename: string } | null
  }[]
  changed_section_count: number
  changed_document_count: number
}

export function compareRevisions(id: string, from: number, to: number): Promise<Compare> {
  return request<Compare>(`/applications/${id}/compare?from=${from}&to=${to}`)
}

export function resolveFeedback(id: string, feedbackId: string): Promise<OfficerApplication> {
  return request<OfficerApplication>(`/officer/applications/${id}/feedback/${feedbackId}/resolve`, { method: 'POST' })
}
