/**
 * App-wide "there are unsaved changes" flag. Pages with a dirty form set it; the shell reads it before
 * sign-out and the window warns before unload. Tiny on purpose: one boolean, no framework.
 */
let dirty = false

export function setUnsaved(value: boolean): void {
  dirty = value
}

export function hasUnsaved(): boolean {
  return dirty
}

/** Browser "leave site?" prompt while there are unsaved changes. Returns the cleanup for useEffect. */
export function guardUnload(): () => void {
  const onBeforeUnload = (e: BeforeUnloadEvent) => {
    if (!dirty) return
    e.preventDefault()
    // Legacy browsers need a return value to show the prompt; the text itself is not shown.
    e.returnValue = ''
  }
  window.addEventListener('beforeunload', onBeforeUnload)
  return () => window.removeEventListener('beforeunload', onBeforeUnload)
}
