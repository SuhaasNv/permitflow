import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { DocumentSlotView } from '@/api/applications'
import { AppError } from '@/api/client'
import * as docsApi from '@/api/documents'
import type { DocumentView, UploadResult } from '@/api/documents'
import { AppProviders } from '@/app/providers'
import { DocumentSlot } from './DocumentSlot'

const now = new Date()

function doc(overrides: Partial<DocumentView> = {}, verification: Partial<DocumentView['verification']> = {}): DocumentView {
  return {
    id: 'doc-1',
    document_type: 'floor_plan',
    original_filename: 'plan.pdf',
    content_type: 'application/pdf',
    size_bytes: 2048,
    uploaded_at: now.toISOString(),
    replaces_filename: null,
    verification:
      verification === null
        ? null
        : {
            status: 'verified',
            summary: 'Matches the form.',
            issues: [],
            missing_information: [],
            error_reason: null,
            requested_at: now.toISOString(),
            finished_at: now.toISOString(),
            ...verification,
          },
    ...overrides,
  }
}

function slot(document: DocumentView | null, editable = true): DocumentSlotView {
  return { type: 'floor_plan', label: 'Floor plan', present: document !== null, editable, document }
}

const result: UploadResult = {
  application: { id: 'app-1' } as UploadResult['application'],
  document: doc(),
  unchanged: false,
}

function renderSlot(props: Partial<Parameters<typeof DocumentSlot>[0]> = {}) {
  const onUploaded = vi.fn()
  const onDeleted = vi.fn()
  render(
    <AppProviders>
      <DocumentSlot applicationId="app-1" slot={slot(null)} index={1} canDelete onUploaded={onUploaded} onDeleted={onDeleted} {...props} />
    </AppProviders>,
  )
  return { onUploaded, onDeleted }
}

describe('DocumentSlot', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.useRealTimers()
  })

  it('rejects a disallowed file before any request and explains why', async () => {
    const upload = vi.spyOn(docsApi, 'uploadDocument')
    renderSlot()
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    await userEvent.upload(input, new File(['x'], 'macro.docx', { type: 'application/msword' }), { applyAccept: false })
    expect(await screen.findByText('Upload not accepted')).toBeInTheDocument()
    expect(screen.getByText(/Only PDF, PNG, JPG or TXT/)).toBeInTheDocument()
    expect(upload).not.toHaveBeenCalled()
  })

  it('shows progress while uploading, then hands the result up and toasts', async () => {
    const upload = vi.spyOn(docsApi, 'uploadDocument').mockImplementation(async (_a, _t, _f, onProgress) => {
      onProgress(0.5)
      return result
    })
    const { onUploaded } = renderSlot()
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    await userEvent.upload(input, new File(['%PDF'], 'plan.pdf', { type: 'application/pdf' }))
    await waitFor(() => expect(onUploaded).toHaveBeenCalledWith(result))
    expect(upload).toHaveBeenCalledWith('app-1', 'floor_plan', expect.any(File), expect.any(Function))
    expect(await screen.findByText('Document uploaded')).toBeInTheDocument()
  })

  it('reports an identical re-upload as "No change" (sha256 duplicate)', async () => {
    vi.spyOn(docsApi, 'uploadDocument').mockResolvedValue({ ...result, unchanged: true })
    renderSlot()
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    await userEvent.upload(input, new File(['%PDF'], 'plan.pdf', { type: 'application/pdf' }))
    expect(await screen.findByText('No change')).toBeInTheDocument()
  })

  it('surfaces the server message when the upload is refused', async () => {
    vi.spyOn(docsApi, 'uploadDocument').mockRejectedValue(
      new AppError(415, { code: 'unsupported_type', message: 'The content does not match its type.' }),
    )
    renderSlot()
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    await userEvent.upload(input, new File(['%PDF'], 'plan.pdf', { type: 'application/pdf' }))
    expect(await screen.findByText('Upload did not complete')).toBeInTheDocument()
    expect(screen.getByText('The content does not match its type.')).toBeInTheDocument()
  })

  it('offers Re-run only for terminal checks, and Replace only when editable and not checking', () => {
    const { rerender } = render(
      <AppProviders>
        <DocumentSlot
          applicationId="app-1"
          slot={slot(doc({}, { status: 'running', finished_at: null }))}
          index={1}
          canDelete
          onUploaded={vi.fn()}
          onDeleted={vi.fn()}
        />
      </AppProviders>,
    )
    expect(screen.getByText('Checking')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Re-run check' })).not.toBeInTheDocument()
    expect(screen.queryByText('Replace file')).not.toBeInTheDocument()

    rerender(
      <AppProviders>
        <DocumentSlot
          applicationId="app-1"
          slot={slot(doc({}, { status: 'issues_found' }))}
          index={1}
          canDelete
          onUploaded={vi.fn()}
          onDeleted={vi.fn()}
        />
      </AppProviders>,
    )
    expect(screen.getByRole('button', { name: 'Re-run check' })).toBeInTheDocument()
    expect(screen.getByText('Replace file')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Remove' })).toBeInTheDocument()

    rerender(
      <AppProviders>
        <DocumentSlot
          applicationId="app-1"
          slot={slot(doc({}, { status: 'issues_found' }), false)}
          index={1}
          canDelete={false}
          lockedReason="The licensing officer did not ask for a new copy of this document."
          onUploaded={vi.fn()}
          onDeleted={vi.fn()}
        />
      </AppProviders>,
    )
    expect(screen.queryByRole('button', { name: 'Re-run check' })).not.toBeInTheDocument()
    expect(screen.queryByText('Replace file')).not.toBeInTheDocument()
    expect(screen.getByText(/did not ask for a new copy/)).toBeInTheDocument()
  })

  it('treats a check still running after the staleness window as re-runnable', () => {
    const old = new Date(now.getTime() - 10 * 60 * 1000).toISOString()
    render(
      <AppProviders>
        <DocumentSlot
          applicationId="app-1"
          slot={slot(doc({}, { status: 'running', finished_at: null, requested_at: old }))}
          index={1}
          canDelete
          onUploaded={vi.fn()}
          onDeleted={vi.fn()}
        />
      </AppProviders>,
    )
    expect(screen.getByRole('button', { name: 'Re-run check' })).toBeInTheDocument()
    expect(screen.getByText('Replace file')).toBeInTheDocument()
  })

  it('re-runs through the API and hands the fresh view up; a 409 shows in the slot', async () => {
    const rerun = vi
      .spyOn(docsApi, 'rerunVerification')
      .mockResolvedValueOnce(result)
      .mockRejectedValueOnce(new AppError(409, { code: 'check_in_progress', message: 'A check is already running.' }))
    const { onUploaded } = renderSlot({ slot: slot(doc({}, { status: 'failed', error_reason: 'interrupted' })) })
    await userEvent.click(screen.getByRole('button', { name: 'Re-run check' }))
    await waitFor(() => expect(onUploaded).toHaveBeenCalledWith(result))
    expect(rerun).toHaveBeenCalledWith('app-1', 'doc-1')
    await userEvent.click(screen.getByRole('button', { name: 'Re-run check' }))
    expect(await screen.findByText('Could not re-run the check')).toBeInTheDocument()
    expect(screen.getByText('A check is already running.')).toBeInTheDocument()
  })

  it('removes only after confirmation and shows the officer request on a flagged slot', async () => {
    const remove = vi.spyOn(docsApi, 'deleteDocument').mockResolvedValue({ id: 'app-1' } as never)
    const { onDeleted } = renderSlot({
      slot: slot(doc()),
      feedback: [
        {
          id: 'f1',
          target_type: 'document',
          section_key: null,
          document_type: 'floor_plan',
          target_label: 'Floor plan',
          message: 'Please upload a plan that marks the kitchen.',
          resolution: 'open',
          round: 1,
          released_at: now.toISOString(),
          addressed_in_revision: null,
        },
      ],
    })
    expect(screen.getByText('The licensing office asked for a new copy')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Remove' }))
    expect(await screen.findByRole('dialog', { name: 'Remove this document?' })).toBeInTheDocument()
    expect(remove).not.toHaveBeenCalled()
    await userEvent.click(screen.getAllByRole('button', { name: 'Remove' }).at(-1)!)
    await waitFor(() => expect(onDeleted).toHaveBeenCalled())
    expect(remove).toHaveBeenCalledWith('app-1', 'doc-1')
  })
})
