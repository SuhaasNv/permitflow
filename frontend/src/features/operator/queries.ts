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
  return useQuery({ queryKey: applicationKeys.detail(id), queryFn: () => getApplication(id) })
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
