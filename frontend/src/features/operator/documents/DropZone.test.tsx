import { fireEvent, render } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { DropZone } from './DropZone'

const pdf = (name: string) => new File(['%PDF'], name, { type: 'application/pdf' })

/** The drop target is the dashed container: the file input's parent. */
function zoneEl(): HTMLElement {
  return (document.querySelector('input[type="file"]') as HTMLInputElement).parentElement as HTMLElement
}

function drop(zone: HTMLElement, files: File[]) {
  fireEvent.drop(zone, { dataTransfer: { files, types: ['Files'] } })
}

describe('DropZone (FR-004 drag-and-drop)', () => {
  it('hands the dropped file up, and reports extra files when more than one is dropped', () => {
    const onFile = vi.fn()
    const onExtraFiles = vi.fn()
    render(<DropZone label="Drop your Floor plan file here, or" onFile={onFile} onExtraFiles={onExtraFiles} />)
    const zone = zoneEl()
    drop(zone, [pdf('a.pdf'), pdf('b.pdf'), pdf('c.pdf')])
    expect(onFile).toHaveBeenCalledTimes(1)
    expect((onFile.mock.calls[0][0] as File).name).toBe('a.pdf')
    expect(onExtraFiles).toHaveBeenCalledWith(2)
  })

  it('highlights while a file is dragged over it and clears when the drag leaves', () => {
    render(<DropZone label="Drop here, or" onFile={vi.fn()} />)
    const zone = zoneEl()
    fireEvent.dragOver(zone, { dataTransfer: { dropEffect: '' } })
    expect(zone.className).toMatch(/bg-surface-3/)
    fireEvent.dragLeave(zone, { relatedTarget: document.body })
    expect(zone.className).not.toMatch(/bg-surface-3/)
  })

  it('ignores drops while disabled', () => {
    const onFile = vi.fn()
    render(<DropZone label="Drop here, or" onFile={onFile} disabled />)
    const zone = zoneEl()
    drop(zone, [pdf('a.pdf')])
    expect(onFile).not.toHaveBeenCalled()
  })

  it('offers a keyboard-reachable picker that hands the chosen file up', async () => {
    const onFile = vi.fn()
    render(<DropZone label="Drop here, or" onFile={onFile} />)
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    await userEvent.upload(input, pdf('picked.pdf'))
    expect((onFile.mock.calls[0][0] as File).name).toBe('picked.pdf')
  })
})
