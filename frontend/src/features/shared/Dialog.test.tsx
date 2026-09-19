import { fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { Dialog } from './Dialog'

function renderDialog(over: Partial<Parameters<typeof Dialog>[0]> = {}) {
  const onConfirm = vi.fn()
  const onCancel = vi.fn()
  render(
    <Dialog open title="Remove this document?" confirmLabel="Remove" onConfirm={onConfirm} onCancel={onCancel} {...over}>
      <p>It will be removed from this application.</p>
    </Dialog>,
  )
  return { onConfirm, onCancel }
}

describe('Dialog (S-22 pattern: question, consequence, one primary action)', () => {
  it('names itself by its title, focuses the primary action, and confirms or cancels', async () => {
    const { onConfirm, onCancel } = renderDialog()
    const dialog = screen.getByRole('dialog', { name: 'Remove this document?' })
    expect(dialog).toHaveAccessibleDescription(/removed from this application/)
    expect(screen.getByRole('button', { name: 'Remove' })).toHaveFocus()
    await userEvent.click(screen.getByRole('button', { name: 'Remove' }))
    expect(onConfirm).toHaveBeenCalledTimes(1)
    await userEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(onCancel).toHaveBeenCalledTimes(1)
  })

  it('puts focus on Cancel for a dangerous action so Enter cannot destroy by accident', () => {
    renderDialog({ danger: true, confirmLabel: 'Delete draft' })
    expect(screen.getByRole('button', { name: 'Cancel' })).toHaveFocus()
  })

  it('closes on Escape unless it is busy', () => {
    const { onCancel } = renderDialog({ busy: true })
    fireEvent(screen.getByRole('dialog'), new Event('cancel', { cancelable: true }))
    expect(onCancel).not.toHaveBeenCalled()
    expect(screen.getByRole('button', { name: 'Cancel' })).toBeDisabled()
  })

  it('reports Escape as cancel when idle', () => {
    const { onCancel } = renderDialog()
    fireEvent(screen.getByRole('dialog'), new Event('cancel', { cancelable: true }))
    expect(onCancel).toHaveBeenCalledTimes(1)
  })
})
