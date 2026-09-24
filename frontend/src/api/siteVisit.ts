import type { ApplicationView } from './applications'
import { request } from './client'
import type { OfficerApplication } from './officer'

export type SiteVisitSlot = 'morning' | 'afternoon'

export const SLOT_OPTIONS: { value: SiteVisitSlot; label: string; times: string }[] = [
  { value: 'morning', label: 'Morning', times: '09:00 to 12:00' },
  { value: 'afternoon', label: 'Afternoon', times: '14:00 to 17:00' },
]

export interface SiteVisitProposal {
  round: number
  author_role: 'officer' | 'operator'
  author_name: string
  date: string
  slot: SiteVisitSlot
  /** "Tuesday 22 September 2026, morning (09:00 to 12:00)", built by the server in Singapore time. */
  when: string
  reason: string | null
  outcome: 'pending' | 'accepted' | 'kept' | 'declined' | 'superseded'
  created_at: string
  decided_at: string | null
}

/** Internal status of the appointment. Officer-only wording comes from the server as `status_label`. */
export type SiteVisitStatus = 'proposed' | 'counter_proposed' | 'confirmed' | 'done'

/** The officer's view: the date on the table, the operator's counter when one waits, every round. */
export interface SiteVisitOfficer {
  visit_no: number
  status: SiteVisitStatus
  status_label: string
  date: string
  slot: SiteVisitSlot
  when: string
  note: string | null
  reply_deadline: string | null
  can_confirm_without_reply: boolean
  confirm_without_reply_reason: string | null
  original: SiteVisitProposal | null
  counter: SiteVisitProposal | null
  can_reschedule: boolean
  /** Proposals both sides may still add (six per visit); at zero only accept or keep remain. */
  rounds_left: number
  round_limit_reason: string | null
  rounds: SiteVisitProposal[]
  /** The confirmed date still stands: confirmed, or the operator asked to move it and the officer has not decided (UC3-0 4a). */
  date_stands: boolean
  /** Mark site visit done and the checklist submit wait for the visit day (Singapore date). */
  visit_day_reached: boolean
  /** False for an earlier visit shown as history. */
  is_current: boolean
}

/** The operator's view: what is proposed, what they can do, every round in their own words. */
export interface SiteVisitOperator {
  visit_no: number
  status: SiteVisitStatus
  status_label: string
  date: string
  slot: SiteVisitSlot
  when: string
  note: string | null
  reply_by: string | null
  can_accept: boolean
  can_counter: boolean
  can_reschedule: boolean
  /** First date the operator may pick (two working days ahead, Singapore time). */
  earliest_date: string
  rounds_left: number
  round_limit_reason: string | null
  rounds: SiteVisitProposal[]
  date_stands: boolean
  /** False for an earlier visit shown as history. */
  is_current: boolean
}

export interface ProposeInput {
  date: string
  slot: SiteVisitSlot
  note?: string | null
  expected_version: number
}

export interface DecideInput {
  action: 'accept_operator' | 'keep_original' | 'propose'
  date?: string
  slot?: SiteVisitSlot
  note?: string | null
}

export interface DateInput {
  date: string
  slot: SiteVisitSlot
  reason?: string | null
}

// Officer ------------------------------------------------------------------------------------------

export function proposeSiteVisit(id: string, body: ProposeInput): Promise<OfficerApplication> {
  return request<OfficerApplication>(`/officer/applications/${id}/site-visit`, { method: 'POST', body })
}

export function decideSiteVisit(id: string, body: DecideInput): Promise<OfficerApplication> {
  return request<OfficerApplication>(`/officer/applications/${id}/site-visit/decide`, { method: 'POST', body })
}

export function confirmSiteVisitWithoutReply(id: string): Promise<OfficerApplication> {
  return request<OfficerApplication>(`/officer/applications/${id}/site-visit/confirm`, { method: 'POST' })
}

export function rescheduleSiteVisitAsOfficer(id: string, body: DateInput): Promise<OfficerApplication> {
  return request<OfficerApplication>(`/officer/applications/${id}/site-visit/reschedule`, { method: 'POST', body })
}

// Operator -----------------------------------------------------------------------------------------

export function acceptSiteVisit(id: string): Promise<ApplicationView> {
  return request<ApplicationView>(`/applications/${id}/site-visit/accept`, { method: 'POST' })
}

export function counterSiteVisit(id: string, body: DateInput): Promise<ApplicationView> {
  return request<ApplicationView>(`/applications/${id}/site-visit/counter`, { method: 'POST', body })
}

export function rescheduleSiteVisitAsOperator(id: string, body: DateInput): Promise<ApplicationView> {
  return request<ApplicationView>(`/applications/${id}/site-visit/reschedule`, { method: 'POST', body })
}
