import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import type { FeedbackInput, OfficerApplication } from '@/api/officer'
import {
  compareRevisions,
  createFeedback,
  getAuditTrail,
  getFeedbackTemplates,
  getOfficerApplication,
  getQueue,
  rerunOfficerCheck,
  resolveFeedback,
  reopenFeedback,
  restoreFeedback,
  transitionApplication,
  withdrawFeedback,
} from '@/api/officer'
import type { DateInput, DecideInput, ProposeInput } from '@/api/siteVisit'
import { confirmSiteVisitWithoutReply, decideSiteVisit, proposeSiteVisit, rescheduleSiteVisitAsOfficer } from '@/api/siteVisit'
import { isCheckStale } from '@/features/operator/queries'

export const officerKeys = {
  queue: ['officer', 'queue'] as const,
  case: (id: string) => ['officer', 'case', id] as const,
  audit: (id: string) => ['officer', 'audit', id] as const,
}

/** Every officer action writes audit rows, so the open trail is refetched along with the queue. */
function afterCaseChange(qc: ReturnType<typeof useQueryClient>, id: string, view: unknown) {
  qc.setQueryData(officerKeys.case(id), view)
  void qc.invalidateQueries({ queryKey: officerKeys.queue })
  void qc.invalidateQueries({ queryKey: officerKeys.audit(id) })
}

/** The queue refreshes every 30 s while open so new submissions appear without a reload. */
export function useQueue() {
  return useQuery({ queryKey: officerKeys.queue, queryFn: getQueue, refetchInterval: 30_000 })
}

/** True while a check is pending or running and younger than the staleness window (same rule as the operator side). */
export function hasLiveCheck(view: OfficerApplication, now: number = Date.now()): boolean {
  return view.documents.some((d) => {
    const v = d.verification
    return v !== null && (v.status === 'pending' || v.status === 'running') && !isCheckStale(v.requested_at, now)
  })
}

/** Polls every 2 s while any document check is still running, so the officer sees results land; stops after
 * CHECK_STALE_MS so a check stuck in the backend cannot keep the tab polling forever. */
export function useOfficerApplication(id: string) {
  return useQuery({
    queryKey: officerKeys.case(id),
    queryFn: () => getOfficerApplication(id),
    refetchOnWindowFocus: true,
    refetchInterval: (query) => (query.state.data && hasLiveCheck(query.state.data) ? 2000 : false),
  })
}

export function useTransition(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: { target: string; note?: string; expected_version: number }) => transitionApplication(id, body),
    onSuccess: (view) => afterCaseChange(qc, id, view),
  })
}

export function useRerunCheck(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (documentId: string) => rerunOfficerCheck(id, documentId),
    onSuccess: (view) => afterCaseChange(qc, id, view),
  })
}

export function useFeedbackTemplates() {
  return useQuery({ queryKey: ['officer', 'feedback-templates'], queryFn: getFeedbackTemplates, staleTime: Infinity })
}

export function useCreateFeedback(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: FeedbackInput) => createFeedback(id, body),
    onSuccess: (view) => afterCaseChange(qc, id, view),
  })
}

export function useWithdrawFeedback(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (feedbackId: string) => withdrawFeedback(id, feedbackId),
    onSuccess: (view) => afterCaseChange(qc, id, view),
  })
}

export function useCompare(id: string, from: number | null, to: number | null) {
  return useQuery({
    queryKey: ['officer', 'compare', id, from, to],
    queryFn: () => compareRevisions(id, from ?? 1, to ?? 1),
    enabled: from !== null && to !== null && from !== to,
    staleTime: Infinity,
  })
}

export function useResolveFeedback(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (feedbackId: string) => resolveFeedback(id, feedbackId),
    onSuccess: (view) => afterCaseChange(qc, id, view),
  })
}

export function useReopenFeedback(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (feedbackId: string) => reopenFeedback(id, feedbackId),
    onSuccess: (view) => afterCaseChange(qc, id, view),
  })
}

export function useRestoreFeedback(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (feedbackId: string) => restoreFeedback(id, feedbackId),
    onSuccess: (view) => afterCaseChange(qc, id, view),
  })
}

export function useAuditTrail(id: string, enabled: boolean) {
  return useQuery({ queryKey: officerKeys.audit(id), queryFn: () => getAuditTrail(id), enabled, staleTime: 10_000 })
}

// Site visit appointment (US-084). Every call returns the refreshed case, like a transition.

export function useProposeSiteVisit(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: ProposeInput) => proposeSiteVisit(id, body),
    onSuccess: (view) => afterCaseChange(qc, id, view),
  })
}

export function useDecideSiteVisit(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: DecideInput) => decideSiteVisit(id, body),
    onSuccess: (view) => afterCaseChange(qc, id, view),
  })
}

export function useConfirmSiteVisitWithoutReply(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => confirmSiteVisitWithoutReply(id),
    onSuccess: (view) => afterCaseChange(qc, id, view),
  })
}

export function useRescheduleSiteVisitAsOfficer(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: DateInput) => rescheduleSiteVisitAsOfficer(id, body),
    onSuccess: (view) => afterCaseChange(qc, id, view),
  })
}
