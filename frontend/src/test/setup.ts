import '@testing-library/jest-dom/vitest'
import { afterEach } from 'vitest'

// Pages keep unsaved entries on the device (lib/localDraft); one test's leftovers must not reach the next.
afterEach(() => {
  try {
    localStorage.clear()
  } catch {
    // No storage in this environment.
  }
})

// jsdom does not implement <dialog>; stub the modal API so confirmation dialogs can be exercised.
if (typeof HTMLDialogElement !== 'undefined' && !HTMLDialogElement.prototype.showModal) {
  HTMLDialogElement.prototype.showModal = function showModal(this: HTMLDialogElement) {
    this.setAttribute('open', '')
  }
  HTMLDialogElement.prototype.close = function close(this: HTMLDialogElement) {
    this.removeAttribute('open')
  }
}

// jsdom has no matchMedia; the checklist reads one query to stretch its result buttons below 1100 px.
if (typeof window !== 'undefined' && typeof window.matchMedia !== 'function') {
  window.matchMedia = (query: string): MediaQueryList =>
    ({
      matches: false,
      media: query,
      onchange: null,
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
      addListener: () => undefined,
      removeListener: () => undefined,
      dispatchEvent: () => false,
    }) as MediaQueryList
}
