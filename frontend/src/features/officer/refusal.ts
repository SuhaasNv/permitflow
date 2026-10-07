import { useQueryClient } from '@tanstack/react-query'

import { AppError } from '@/api/client'
import { useToast } from '@/features/shared/Toast'
import { officerKeys } from './queries'

/** One sentence for every side action refused because the case moved under the officer (another officer,
 * another device, the operator): the rails never show the server's reason for a race, they reload. */
export const MOVED_ON = 'This application changed since you opened it. Showing the latest.'

/**
 * The error handler for a side action on a case (feedback, appointment, clarification): field errors are
 * the caller's to render (nothing shown here), a 409 reloads the case with the shared sentence, anything
 * else shows the server's message under the given title.
 */
export function useCaseRefusal(id: string): (title: string) => (e: Error) => void {
  const toast = useToast()
  const queryClient = useQueryClient()
  return (title) => (e) => {
    if (e instanceof AppError && e.status === 422 && e.details && typeof e.details.fields === 'object') return
    if (e instanceof AppError && e.status === 409) {
      toast.push({ title, body: MOVED_ON, tone: 'error' })
      void queryClient.invalidateQueries({ queryKey: officerKeys.case(id) })
      return
    }
    toast.push({ title, body: e.message, tone: 'error' })
  }
}
