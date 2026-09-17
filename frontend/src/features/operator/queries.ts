import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { createApplication, getApplication, listApplications } from '@/api/applications'

export const applicationKeys = {
  all: ['applications'] as const,
  detail: (id: string) => ['application', id] as const,
}

export function useApplications() {
  return useQuery({ queryKey: applicationKeys.all, queryFn: listApplications })
}

export function useApplication(id: string) {
  return useQuery({
    queryKey: applicationKeys.detail(id),
    queryFn: () => getApplication(id),
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

import { getFormSchema } from '@/api/formSchema'
import { updateSection } from '@/api/sections'

export function useFormSchema() {
  return useQuery({
    queryKey: ['form-schema'],
    queryFn: getFormSchema,
    staleTime: Infinity,
  })
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
