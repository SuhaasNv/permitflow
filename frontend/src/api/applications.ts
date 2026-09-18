import { request } from './client'
import type { DocumentView } from './documents'
import type { Tone } from '@/features/shared/StatusBadge'

export interface ApplicationSummary {
  id: string
  reference_no: string
  licence_title: string
  status_label: string
  status_tone: Tone
  business_name: string | null
  premises_summary: string | null
  percent: number
  revision_count: number
  needs_operator_action: boolean
  created_at: string
  updated_at: string
}

export interface SectionView {
  key: string
  title: string
  description: string
  data: Record<string, unknown>
  complete: boolean
  started: boolean
  errors: Record<string, string>
  editable: boolean
}

export interface DocumentSlotView {
  type: string
  label: string
  present: boolean
  editable: boolean
  document: DocumentView | null
}

export interface Completeness {
  percent: number
  is_complete: boolean
  sections_complete: number
  sections_total: number
  documents_present: number
  documents_total: number
  missing: string[]
}

export interface OperatorFeedback {
  id: string
  target_type: 'section' | 'document'
  section_key: string | null
  document_type: string | null
  target_label: string
  message: string
  resolution: 'open' | 'addressed' | 'resolved'
  round: number
  released_at: string
  addressed_in_revision: number | null
}

export interface ResubmitReadiness {
  can_resubmit: boolean
  changed_sections: string[]
  changed_document_types: string[]
  untouched_targets: string[]
  reason: string | null
}

export interface ApplicationView {
  id: string
  reference_no: string
  licence_title: string
  status_label: string
  status_tone: Tone
  status_explanation: string
  can_edit: boolean
  can_submit: boolean
  sections: SectionView[]
  document_slots: DocumentSlotView[]
  completeness: Completeness
  revision_count: number
  needs_operator_action: boolean
  feedback: OperatorFeedback[]
  resubmit: ResubmitReadiness | null
  created_at: string
  updated_at: string
}

export function listApplications(): Promise<ApplicationSummary[]> {
  return request<ApplicationSummary[]>('/applications')
}

export function createApplication(): Promise<ApplicationView> {
  return request<ApplicationView>('/applications', { method: 'POST' })
}

export function getApplication(id: string): Promise<ApplicationView> {
  return request<ApplicationView>(`/applications/${id}`)
}

export function submitApplication(id: string): Promise<ApplicationView> {
  return request<ApplicationView>(`/applications/${id}/submit`, { method: 'POST' })
}

export function resubmitApplication(id: string): Promise<ApplicationView> {
  return request<ApplicationView>(`/applications/${id}/resubmit`, { method: 'POST' })
}
