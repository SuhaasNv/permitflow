import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { createApplication, getApplication, listApplications, submitApplication } from '@/api/applications'
import { getFormSchema } from '@/api/formSchema'
import { updateSection } from '@/api/sections'

export const applicationKeys = {
  all: ['applications'] as const,
  detail: (id: string) => ['application', id] as const,
}

const ACTIVE_VERIFICATION = new Set(['pending', 'running'])
/** Stop polling a check that has been pending or running longer than this; the slot then offers Re-run. */
export const CHECK_STALE_MS = 3 * 60 * 1000

export function isCheckStale(uploadedAt: string, now: number = Date.now()): boolean {
  return now - new Date(uploadedAt).getTime() > CHECK_STALE_MS
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
        (s) => s.document?.verification && ACTIVE_VERIFICATION.has(s.document.verification.status) && !isCheckStale(s.document.uploaded_at),
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
