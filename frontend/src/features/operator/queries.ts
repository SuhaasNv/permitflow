import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { createApplication, getApplication, listApplications } from '@/api/applications'
import { getFormSchema } from '@/api/formSchema'
import { updateSection } from '@/api/sections'

export const applicationKeys = {
  all: ['applications'] as const,
  detail: (id: string) => ['application', id] as const,
}

const ACTIVE_VERIFICATION = new Set(['pending', 'running'])

export function useApplications() {
  return useQuery({ queryKey: applicationKeys.all, queryFn: listApplications })
}

/** Polls every 2 s while any document is still being checked (FR-005), then stops. */
export function useApplication(id: string) {
  return useQuery({
    queryKey: applicationKeys.detail(id),
    queryFn: () => getApplication(id),
    refetchIntervalInBackground: true,
    refetchInterval: (query) => {
      const view = query.state.data
      if (!view) return false
      const active = view.document_slots.some((s) => s.document?.verification && ACTIVE_VERIFICATION.has(s.document.verification.status))
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
