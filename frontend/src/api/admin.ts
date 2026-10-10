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
  dead: number
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
  /** The signed-in administrator's own password (step-up). */
  admin_password: string
}

export interface UserCreate {
  email: string
  full_name: string
  role: Role
  /** The new account's password. */
  password: string
  /** The signed-in administrator's own password (step-up). */
  admin_password: string
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

// ---- US-101: platform settings ----

export type SettingValue = number | boolean | string
export type SettingKind = 'int' | 'bool' | 'choice'

export interface PlatformSetting {
  key: string
  label: string
  description: string
  group: string
  kind: SettingKind
  unit: string
  /** In force right now. */
  value: SettingValue
  /** What applies with no override: the environment value. */
  default: SettingValue
  overridden: boolean
  minimum: number | null
  maximum: number | null
  max_source: 'env' | 'cap' | 'none'
  choices: string[]
  /** False while the consumer is a later story: the value is stored and audited but nothing reads it yet. */
  in_use: boolean
  updated_by_name: string | null
  updated_at: string | null
  reason: string | null
}

export interface PlatformSettings {
  settings: PlatformSetting[]
  environment: string
}

export interface SettingHistoryEntry {
  id: string
  kind: 'changed' | 'reverted'
  key: string
  label: string
  old: SettingValue
  new: SettingValue
  old_was_default: boolean
  reason: string
  actor_name: string | null
  created_at: string
  reverted_event_id: string | null
}

export interface SettingsHistory {
  entries: SettingHistoryEntry[]
  next_cursor: string | null
}

/** The reason and the signed-in administrator's own password (step-up) travel with every write. */
export interface SettingWrite {
  reason: string
  password: string
}

export function getPlatformSettings(): Promise<PlatformSettings> {
  return request<PlatformSettings>('/admin/settings')
}

export function getSettingsHistory(key?: string | null, before?: string | null, limit = 10): Promise<SettingsHistory> {
  const params = new URLSearchParams({ limit: String(limit) })
  if (key) params.set('key', key)
  if (before) params.set('before', before)
  return request<SettingsHistory>(`/admin/settings/history?${params.toString()}`)
}

export function changePlatformSetting(key: string, body: SettingWrite & { value: SettingValue }): Promise<PlatformSetting> {
  return request<PlatformSetting>(`/admin/settings/${encodeURIComponent(key)}`, { method: 'PUT', body })
}

export function revertSettingChange(entryId: string, body: SettingWrite): Promise<PlatformSetting> {
  return request<PlatformSetting>(`/admin/settings/history/${encodeURIComponent(entryId)}/revert`, { method: 'POST', body })
}
