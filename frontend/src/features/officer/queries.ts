import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import type { FeedbackInput } from '@/api/officer'
import {
  createFeedback,
  getFeedbackTemplates,
  getOfficerApplication,
  getQueue,
  rerunOfficerCheck,
  transitionApplication,
  withdrawFeedback,
} from '@/api/officer'

export const officerKeys = {
  queue: ['officer', 'queue'] as const,
  case: (id: string) => ['officer', 'case', id] as const,
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
    onSuccess: (view) => {
      qc.setQueryData(officerKeys.case(id), view)
      void qc.invalidateQueries({ queryKey: officerKeys.queue })
    },
  })
}

export function useRerunCheck(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (documentId: string) => rerunOfficerCheck(id, documentId),
    onSuccess: (view) => {
      qc.setQueryData(officerKeys.case(id), view)
      void qc.invalidateQueries({ queryKey: officerKeys.queue })
    },
  })
}

export function useFeedbackTemplates() {
  return useQuery({ queryKey: ['officer', 'feedback-templates'], queryFn: getFeedbackTemplates, staleTime: Infinity })
}

export function useCreateFeedback(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: FeedbackInput) => createFeedback(id, body),
    onSuccess: (view) => {
      qc.setQueryData(officerKeys.case(id), view)
      void qc.invalidateQueries({ queryKey: officerKeys.queue })
    },
  })
}

export function useWithdrawFeedback(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (feedbackId: string) => withdrawFeedback(id, feedbackId),
    onSuccess: (view) => {
      qc.setQueryData(officerKeys.case(id), view)
      void qc.invalidateQueries({ queryKey: officerKeys.queue })
    },
  })
}
