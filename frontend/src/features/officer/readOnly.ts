import { createContext, useContext } from 'react'

/**
 * An administrator reads a case through the officer screens without acting (US-072, ADR-014): the
 * server answers with no actions and 403 on every mutation, and the components under this context
 * render none of the controls. Provided by the `/admin/applications/:id` routes only.
 */
const ReadOnlyContext = createContext(false)

export const ReadOnlyProvider = ReadOnlyContext.Provider

export function useReadOnly(): boolean {
  return useContext(ReadOnlyContext)
}
