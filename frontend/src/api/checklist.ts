import { request } from './client'

export type ChecklistResult = 'not_assessed' | 'satisfactory' | 'unsatisfactory' | 'not_applicable'
export type ChecklistStatus = 'draft' | 'submitted'
export type ClarificationStatus = 'none' | 'open' | 'answered' | 'resolved' | 'withdrawn'

export interface ChecklistItemDef {
  key: string
  section: string
  title: string
  guidance: string
  applicable_by_default: boolean
}

export interface ChecklistSection {
  key: string
  title: string
  items: ChecklistItemDef[]
}

export interface ChecklistSchema {
  version: number
  description: string
  sections: ChecklistSection[]
  item_count: number
}

export interface ChecklistItem {
  id: string
  key: string
  section: string
  title: string
  guidance: string
  position: number
  result: ChecklistResult
  comment: string | null
  needs_clarification: boolean
  clarification_status: ClarificationStatus
}

export interface ChecklistCounts {
  total: number
  assessed: number
  flagged: number
  unsatisfactory: number
  not_applicable: number
  /** Unsatisfactory or flagged items without a comment: what still blocks a submit. */
  missing_comments: number
}

export interface Checklist {
  id: string
  application_id: string
  visit_no: number
  schema_version: number
  status: ChecklistStatus
  version: number
  created_by: string
  created_at: string
  updated_at: string | null
  submitted_by: string | null
  submitted_at: string | null
  counts: ChecklistCounts
  /** What still blocks a submit, in a sentence; null when nothing does. */
  remaining: string | null
  items: ChecklistItem[]
}

/** The line the case rail shows (S-31 summary). */
export interface ChecklistSummary {
  visit_no: number
  status: ChecklistStatus
  version: number
  counts: ChecklistCounts
  updated_at: string | null
  submitted_at: string | null
}

export interface ChecklistItemInput {
  key: string
  result: ChecklistResult
  comment: string | null
  needs_clarification: boolean
}

export interface ChecklistSaveInput {
  items: ChecklistItemInput[]
  version: number
  /** Client-generated per save; a replayed one answers with the current state. */
  save_id?: string
}

export function getChecklistSchema(): Promise<ChecklistSchema> {
  return request<ChecklistSchema>('/checklist-schema')
}

/** Creates the current visit's draft on first open, returns it afterwards. */
export function openChecklist(id: string): Promise<Checklist> {
  return request<Checklist>(`/officer/applications/${id}/checklist`, { method: 'POST' })
}

export function getChecklist(id: string, visit?: number): Promise<Checklist> {
  return request<Checklist>(`/officer/applications/${id}/checklist${visit ? `?visit=${visit}` : ''}`)
}

export function saveChecklist(id: string, body: ChecklistSaveInput): Promise<Checklist> {
  return request<Checklist>(`/officer/applications/${id}/checklist`, { method: 'PUT', body })
}
