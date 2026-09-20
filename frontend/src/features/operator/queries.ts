import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  createApplication,
  deleteDraft,
  getApplication,
  listApplications,
  resubmitApplication,
  withdrawApplication,
  submitApplication,
} from '@/api/applications'
import type { ClarificationView } from '@/api/clarification'
import { attachToResponse, getClarifications, removeAttachment, respondToClarification, sendClarifications } from '@/api/clarification'
import { getFormSchema } from '@/api/formSchema'
import type { DateInput } from '@/api/siteVisit'
import { acceptSiteVisit, counterSiteVisit, rescheduleSiteVisitAsOperator } from '@/api/siteVisit'
import { updateSection } from '@/api/sections'

export const applicationKeys = {
  all: ['applications'] as const,
  detail: (id: string) => ['application', id] as const,
}

const ACTIVE_VERIFICATION = new Set(['pending', 'running'])
/** Stop polling a check that has been pending or running longer than this; the slot then offers Re-run. */
export const CHECK_STALE_MS = 3 * 60 * 1000

export function isCheckStale(requestedAt: string, now: number = Date.now()): boolean {
  return now - new Date(requestedAt).getTime() > CHECK_STALE_MS
}

export function useApplications() {
  return useQuery({ queryKey: applicationKeys.all, queryFn: listApplications })
}

/** Polls every 2 s while any document is still being checked (FR-005), only in the visible tab, and stops
 * after CHECK_STALE_MS so a stuck check cannot poll forever. Refetches on focus so another tab's change shows. */
export function useApplication(id: string) {
  return useQuery({
    queryKey: applicationKeys.detail(id),
    queryFn: () => getApplication(id),
    refetchOnWindowFocus: true,
    refetchInterval: (query) => {
      const view = query.state.data
      if (!view) return false
      const active = view.document_slots.some(
        (s) =>
          s.document?.verification &&
          ACTIVE_VERIFICATION.has(s.document.verification.status) &&
          !isCheckStale(s.document.verification.requested_at),
      )
      return active ? 2000 : false
    },
  })
}

export function useCreateApplication() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: createApplication,
    onSuccess: (view) => {
      qc.setQueryData(applicationKeys.detail(view.id), view)
      void qc.invalidateQueries({ queryKey: applicationKeys.all })
    },
  })
}

export function useFormSchema() {
  return useQuery({ queryKey: ['form-schema'], queryFn: getFormSchema, staleTime: Infinity })
}

export function useUpdateSection(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ key, data }: { key: string; data: Record<string, unknown> }) => updateSection(id, key, data),
    onSuccess: (view) => {
      qc.setQueryData(applicationKeys.detail(id), view)
      void qc.invalidateQueries({ queryKey: applicationKeys.all })
    },
  })
}

export function useSubmitApplication(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => submitApplication(id),
    onSuccess: (view) => {
      qc.setQueryData(applicationKeys.detail(id), view)
      void qc.invalidateQueries({ queryKey: applicationKeys.all })
    },
  })
}

export function useResubmitApplication(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => resubmitApplication(id),
    onSuccess: (view) => {
      qc.setQueryData(applicationKeys.detail(id), view)
      void qc.invalidateQueries({ queryKey: applicationKeys.all })
    },
  })
}

export function useWithdrawApplication(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (reason: string | null) => withdrawApplication(id, reason),
    onSuccess: (view) => {
      qc.setQueryData(applicationKeys.detail(id), view)
      void qc.invalidateQueries({ queryKey: applicationKeys.all })
    },
  })
}

export function useDeleteDraft(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => deleteDraft(id),
    // The detail query is left alone: the page navigates away and the cache entry is garbage-collected.
    // Removing it here would make the still-mounted page refetch a row that is gone (404).
    onSuccess: () => void qc.invalidateQueries({ queryKey: applicationKeys.all }),
  })
}

// Site visit appointment (US-084): the reply lands on the application view and the list's Needs your response.

function afterVisitChange(qc: ReturnType<typeof useQueryClient>, id: string, view: unknown) {
  qc.setQueryData(applicationKeys.detail(id), view)
  void qc.invalidateQueries({ queryKey: applicationKeys.all })
}

export function useAcceptSiteVisit(id: string) {
  const qc = useQueryClient()
  return useMutation({ mutationFn: () => acceptSiteVisit(id), onSuccess: (view) => afterVisitChange(qc, id, view) })
}

export function useCounterSiteVisit(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: DateInput) => counterSiteVisit(id, body),
    onSuccess: (view) => afterVisitChange(qc, id, view),
  })
}

export function useRescheduleSiteVisit(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: DateInput) => rescheduleSiteVisitAsOperator(id, body),
    onSuccess: (view) => afterVisitChange(qc, id, view),
  })
}

/** The flagged items with the officer's questions (US-064); refetches on focus so a new round shows. */
export function useClarifications(id: string, enabled = true) {
  return useQuery({
    queryKey: [...applicationKeys.detail(id), 'clarifications'] as const,
    queryFn: () => getClarifications(id),
    enabled,
    refetchOnWindowFocus: true,
  })
}

function afterClarificationChange(qc: ReturnType<typeof useQueryClient>, id: string, view: ClarificationView) {
  qc.setQueryData([...applicationKeys.detail(id), 'clarifications'], view)
  void qc.invalidateQueries({ queryKey: applicationKeys.detail(id), exact: true })
  void qc.invalidateQueries({ queryKey: applicationKeys.all })
}

export function useRespond(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationKey: ['clarification', id],
    mutationFn: ({ itemId, message }: { itemId: string; message: string }) => respondToClarification(id, itemId, message),
    onSuccess: (view) => afterClarificationChange(qc, id, view),
  })
}

export function useAttach(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationKey: ['clarification', id],
    mutationFn: ({ responseId, file }: { responseId: string; file: File }) => attachToResponse(id, responseId, file),
    onSuccess: (result) => afterClarificationChange(qc, id, result.view),
  })
}

export function useRemoveAttachment(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationKey: ['clarification', id],
    mutationFn: ({ responseId, attachmentId }: { responseId: string; attachmentId: string }) =>
      removeAttachment(id, responseId, attachmentId),
    onSuccess: (view) => afterClarificationChange(qc, id, view),
  })
}

export function useSendClarifications(id: string) {
  const qc = useQueryClient()
  return useMutation({ mutationFn: () => sendClarifications(id), onSuccess: (view) => afterClarificationChange(qc, id, view) })
}
