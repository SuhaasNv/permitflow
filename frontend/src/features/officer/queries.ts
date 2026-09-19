import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import type { FeedbackInput } from '@/api/officer'
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

/** Polls every 2 s while any document check is still running, so the officer sees results land. */
export function useOfficerApplication(id: string) {
  return useQuery({
    queryKey: officerKeys.case(id),
    queryFn: () => getOfficerApplication(id),
    refetchOnWindowFocus: true,
    refetchInterval: (query) => (query.state.data && query.state.data.verification_summary.checking > 0 ? 2000 : false),
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
