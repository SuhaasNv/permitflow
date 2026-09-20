import type { Role } from './auth'
import { request } from './client'
import type { Tone } from '@/features/shared/StatusBadge'

// ---- US-070: the operations overview ----

export type Turn = 'draft' | 'office' | 'operator' | 'decided'

export interface StatusCount {
  status: string
  label: string
  tone: Tone
  turn: Turn
  count: number
}

export interface Totals {
  applications: number
  submitted: number
  drafts: number
  with_office: number
  waiting_on_operators: number
  idle_over_7_days: number
}

export interface IdleApplication {
  id: string
  reference_no: string
  business_name: string | null
  status: string
  label: string
  tone: Tone
  days_idle: number
  last_activity_at: string
}

export interface Today {
  day: string
  submissions: number
  resubmissions: number
  checklists_submitted: number
  clarification_rounds: number
  runs_today: number
  runs_per_day_quota: number
}

export interface Checks {
  runs: number
  verified: number
  issues_found: number
  needs_review: number
  unreadable: number
  failed_or_unavailable: number
  still_running: number
  average_seconds: number | null
  p95_seconds: number | null
  provider: string
  model: string | null
}

export interface AdminOverview {
  as_of: string
  totals: Totals
  counts: StatusCount[]
  idle: IdleApplication[]
  today: Today
  checks: Checks
}

export function getAdminOverview(): Promise<AdminOverview> {
  return request<AdminOverview>('/admin/overview')
}

// ---- US-072: the activity feed ----

export interface FeedEvent {
  id: string
  event_type: string
  summary: string
  actor_name: string | null
  actor_role: string | null
  application_id: string | null
  reference_no: string | null
  created_at: string
}

export interface AuditFeed {
  events: FeedEvent[]
  next_cursor: string | null
}

export function getAuditFeed(before?: string | null, limit = 50): Promise<AuditFeed> {
  const params = new URLSearchParams({ limit: String(limit) })
  if (before) params.set('before', before)
  return request<AuditFeed>(`/admin/audit-feed?${params.toString()}`)
}

// ---- US-073: users ----

export interface AdminUser {
  id: string
  email: string
  full_name: string
  role: Role
  is_active: boolean
  is_protected: boolean
  created_at: string
}

export interface AdminUsers {
  users: AdminUser[]
  self_id: string
}

export interface UserPatch {
  role?: Role
  is_active?: boolean
}

export interface UserCreate {
  email: string
  full_name: string
  role: Role
  password: string
}

export function getAdminUsers(): Promise<AdminUsers> {
  return request<AdminUsers>('/admin/users')
}

export function patchAdminUser(id: string, body: UserPatch): Promise<AdminUser> {
  return request<AdminUser>(`/admin/users/${id}`, { method: 'PATCH', body })
}

export function createAdminUser(body: UserCreate): Promise<AdminUser> {
  return request<AdminUser>('/admin/users', { method: 'POST', body })
}
